"""Swarm Manager — deploy and coordinate groups of subagents.

Strategies: parallel, sequential, map_reduce, hierarchical
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.agent.subagent_manager import (
    AGENT_TYPES,
    PRIORITY_LEVELS,
    spawn_subagent,
    kill_subagent,
    get_subagent_status,
    runtime,
)
from app.core.events import bus
from app.core.logging import get_logger
from app.core.utils import new_id, truncate
from app.db.models import SubAgent, Swarm, Thread, Project
from app.db.session import SessionLocal
from app.tools.base import ToolContext

log = get_logger("app.swarm_manager")

# Track in-flight swarm supervisor tasks so kill/cancel actually stops the
# waiter (previously only the child agents were killed and the supervisor
# kept polling for 5 minutes, looking "stuck").
_swarm_tasks: dict[str, asyncio.Task] = {}

TERMINAL = ("completed", "failed", "killed")

# Per-agent chars kept in the merged swarm report. Full per-agent reports
# stay in the DB + `.agents/<id>.md` files; the merge keeps generous excerpts
# so big research/build outputs are not truncated to 1000 chars anymore.
MERGE_PER_AGENT_CHARS = 8000
MERGE_TOTAL_CHARS = 60_000


def _isolate_prompt(base: str, swarm_id: str, agent_name: str) -> str:
    """Force file isolation so parallel workers never overwrite each other."""
    return (
        f"{base}\n\n## File ownership (mandatory)\n"
        f"Write every file you create under `.swarm/{swarm_id}/{agent_name}/`. "
        "Do NOT write outside that directory except to read existing project files. "
        "If the task is research/writing, still save your full complete output to "
        f"`REPORT.md` inside `.swarm/{swarm_id}/{agent_name}/` AND return it as your "
        "final message verbatim (no truncation, no 'see file' shortcut)."
    )


async def _wait_for_agent(agent_id: str, timeout_s: int = 600, poll_s: float = 2.0) -> dict[str, Any]:
    """Wait for one swarm member without 1-second DB hammering."""
    from app.agent.subagent_manager import get_subagent_status as _status
    deadline = time.time() + max(1, timeout_s)
    last: dict[str, Any] = {}
    while time.time() < deadline:
        s = await _status(agent_id)
        if s and s["status"] in TERMINAL:
            return s
        if s:
            last = s
        await asyncio.sleep(poll_s)
    log.warning("Agent %s timed out", agent_id)
    await kill_subagent(agent_id, force=True)
    await asyncio.sleep(1)
    s = await _status(agent_id)
    if s:
        return s
    return {"status": "failed", "error": "Timeout", "name": agent_id}


async def _persist_swarm_report(thread_id: str, swarm_id: str, result: str, parent_ctx: ToolContext | None) -> str:
    """Save the full merged swarm report to workspace + return its path."""
    path = f".swarms/{swarm_id}.md"
    try:
        if parent_ctx is not None and parent_ctx.sandbox is not None:
            await parent_ctx.sandbox.write_file(path, result)
            return path
        from app.sandbox import sandboxes
        from app.db.models import Thread as _Thread
        # Fall back: resolve via thread's project workspace
        async with SessionLocal() as db2:
            thread2 = await db2.get(_Thread, thread_id)
            if thread2:
                from app.db.models import Project as _Project
                proj = await db2.get(_Project, thread2.project_id)
                if proj:
                    sb = await sandboxes.get(thread_id, proj.workspace_path)
                    await sb.write_file(path, result)
                    return path
    except Exception:
        pass
    return ""


async def deploy_swarm(
    *,
    thread_id: str,
    name: str,
    prompt: str,
    strategy: str = "parallel",
    agent_configs: list[dict[str, Any]] | None = None,
    agent_count: int = 3,
    agent_type: str = "coder",
    priority: str = "normal",
    max_steps: int = 25,
    parent_ctx: ToolContext | None = None,
    timeout_s: int = 600,
) -> Swarm:
    """Deploy a swarm of subagents for a coordinated task."""

    if strategy not in ("parallel", "sequential", "map_reduce", "hierarchical"):
        raise ValueError(f"Unknown strategy: {strategy}")

    async with SessionLocal() as db:
        swarm = Swarm(
            thread_id=thread_id,
            name=name or f"swarm-{new_id('')[:8]}",
            strategy=strategy,
            status="deploying",
            prompt=prompt,
            agent_count=agent_count,
        )
        db.add(swarm)
        await db.commit()
        await db.refresh(swarm)
        swarm_id = swarm.id

    topic = f"thread:{thread_id}"
    await bus.publish(topic, {
        "type": "swarm_deployed",
        "thread_id": thread_id,
        "swarm_id": swarm_id,
        "name": name,
        "strategy": strategy,
        "agent_count": agent_count,
    })

    task = asyncio.create_task(
        _run_swarm(
            swarm_id=swarm_id,
            thread_id=thread_id,
            prompt=prompt,
            strategy=strategy,
            agent_configs=agent_configs,
            agent_count=agent_count,
            agent_type=agent_type,
            priority=priority,
            max_steps=max_steps,
            parent_ctx=parent_ctx,
            timeout_s=timeout_s,
        )
    )
    _swarm_tasks[swarm_id] = task
    task.add_done_callback(lambda _t, _sid=swarm_id: _swarm_tasks.pop(_sid, None))

    return swarm


async def _run_swarm(
    *,
    swarm_id: str,
    thread_id: str,
    prompt: str,
    strategy: str,
    agent_configs: list[dict[str, Any]] | None,
    agent_count: int,
    agent_type: str,
    priority: str,
    max_steps: int,
    parent_ctx: ToolContext | None,
    timeout_s: int = 600,
) -> None:
    topic = f"thread:{thread_id}"
    started_at = time.time()

    try:
        async with SessionLocal() as db:
            swarm = await db.get(Swarm, swarm_id)
            if swarm:
                swarm.status = "running"
                await db.commit()

        await bus.publish(topic, {
            "type": "swarm_status",
            "thread_id": thread_id,
            "swarm_id": swarm_id,
            "status": "running",
        })

        if strategy == "parallel":
            result = await _run_parallel(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s)
        elif strategy == "sequential":
            result = await _run_sequential(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s)
        elif strategy == "map_reduce":
            result = await _run_map_reduce(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s)
        elif strategy == "hierarchical":
            result = await _run_hierarchical(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s)
        else:
            result = f"Unknown strategy: {strategy}"

        duration_ms = int((time.time() - started_at) * 1000)
        report_path = await _persist_swarm_report(thread_id, swarm_id, result, parent_ctx)
        async with SessionLocal() as db:
            swarm = await db.get(Swarm, swarm_id)
            if swarm:
                swarm.status = "completed"
                swarm.result = result
                swarm.meta = swarm.meta or {}
                swarm.meta["duration_ms"] = duration_ms
                if report_path:
                    swarm.meta["report_path"] = report_path
                swarm.meta["result_chars"] = len(result)
                # Update completion counts
                query = select(SubAgent).where(SubAgent.swarm_id == swarm_id)
                agents = (await db.execute(query)).scalars().all()
                swarm.completed_count = sum(1 for a in agents if a.status == "completed")
                swarm.failed_count = sum(1 for a in agents if a.status == "failed")
                await db.commit()

        await bus.publish(topic, {
            "type": "swarm_status",
            "thread_id": thread_id,
            "swarm_id": swarm_id,
            "status": "completed",
            "result_summary": result[:2000] if result else "",
            "duration_ms": duration_ms,
            "report_path": report_path,
        })

    except asyncio.CancelledError:
        async with SessionLocal() as db:
            swarm = await db.get(Swarm, swarm_id)
            if swarm:
                swarm.status = "killed"
                await db.commit()

        await bus.publish(topic, {"type": "swarm_status", "thread_id": thread_id, "swarm_id": swarm_id, "status": "killed"})

    except Exception as exc:
        log.exception("Swarm %s failed", swarm_id)
        async with SessionLocal() as db:
            swarm = await db.get(Swarm, swarm_id)
            if swarm:
                swarm.status = "failed"
                swarm.result = f"Error: {exc}"
                await db.commit()

        await bus.publish(topic, {"type": "swarm_status", "thread_id": thread_id, "swarm_id": swarm_id, "status": "failed", "error": str(exc)})


async def _run_parallel(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s=600) -> str:
    configs = agent_configs or [
        {"agent_type": agent_type, "name": f"worker-{i+1}", "prompt": prompt}
        for i in range(agent_count)
    ]

    agents = []
    for cfg in configs:
        aname = cfg.get("name", f"worker-{len(agents)+1}")
        agent = await spawn_subagent(
            thread_id=thread_id,
            agent_type=cfg.get("agent_type", agent_type),
            name=aname,
            prompt=_isolate_prompt(cfg.get("prompt", prompt), swarm_id, aname),
            priority=cfg.get("priority", priority),
            max_steps=cfg.get("max_steps", max_steps),
            swarm_id=swarm_id,
            parent_ctx=parent_ctx,
        )
        agents.append(agent)

    # Spawn all, then wait concurrently so one slow worker doesn't serialize
    # the timeout budget of the others.
    waited = await asyncio.gather(*[_wait_for_agent(a.id, timeout_s) for a in agents])
    return _merge_results(list(waited), "parallel")


async def _run_sequential(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s=600) -> str:
    configs = agent_configs or [
        {"agent_type": agent_type, "name": f"step-{i+1}", "prompt": prompt}
        for i in range(agent_count)
    ]

    previous_result = ""
    all_results = []

    for i, cfg in enumerate(configs):
        aname = cfg.get("name", f"step-{i+1}")
        enhanced_prompt = cfg.get("prompt", prompt)
        if previous_result:
            # Pass a bounded excerpt to the next step; the full text stays in
            # the DB/files and in the final merge — this avoids context blowup
            # while preserving the chain.
            excerpt = previous_result[:12000]
            enhanced_prompt = f"{enhanced_prompt}\n\n## Previous agent's output (step {i}):\n{excerpt}\n\nContinue from where the previous agent left off."

        agent = await spawn_subagent(
            thread_id=thread_id,
            agent_type=cfg.get("agent_type", agent_type),
            name=aname,
            prompt=_isolate_prompt(enhanced_prompt, swarm_id, aname),
            priority=cfg.get("priority", priority),
            max_steps=cfg.get("max_steps", max_steps),
            swarm_id=swarm_id,
            parent_ctx=parent_ctx,
        )

        status = await _wait_for_agent(agent.id, timeout_s)
        if status.get("status") == "completed":
            previous_result = status.get("result", "")
        else:
            previous_result = "Previous step timed out, continuing with next step."
        all_results.append(status)

    return _merge_results(all_results, "sequential")


async def _run_map_reduce(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s=600) -> str:
    planner = await spawn_subagent(
        thread_id=thread_id,
        agent_type="planner",
        name="map-planner",
        prompt=f"Break this task into {agent_count} independent subtasks. For each subtask, provide:\n1. A clear description\n2. The expected output format\n3. Which directory under `.swarm/{swarm_id}/` that worker owns\n\nTask: {prompt}",
        priority="critical",
        max_steps=15,
        swarm_id=swarm_id,
        parent_ctx=parent_ctx,
    )

    planner_status = await _wait_for_agent(planner.id, timeout_s)
    if planner_status.get("status") != "completed":
        return "Planner phase timed out"
    planner_result = planner_status.get("result", "")

    subtasks = _split_subtasks(planner_result, agent_count)
    workers = []
    for i, subtask in enumerate(subtasks):
        wname = f"map-worker-{i+1}"
        worker = await spawn_subagent(
            thread_id=thread_id,
            agent_type=agent_type,
            name=wname,
            prompt=_isolate_prompt(subtask, swarm_id, wname),
            priority=priority,
            max_steps=max_steps,
            swarm_id=swarm_id,
            parent_ctx=parent_ctx,
        )
        workers.append(worker)

    worker_results = list(await asyncio.gather(*[_wait_for_agent(w.id, timeout_s) for w in workers]))

    # Give the reducer bounded excerpts (full texts are in DB/files and get
    # appended verbatim in the final merge below if reduce fails).
    excerpts = "\n\n---\n\n".join(
        f"Worker {i+1} ({r.get('name', '?')}) result:\n{(r.get('result') or 'No result')[:12000]}"
        for i, r in enumerate(worker_results)
    )
    reducer = await spawn_subagent(
        thread_id=thread_id,
        agent_type="coordinator",
        name="reduce-coordinator",
        prompt=(
            f"Merge and synthesize the following {len(worker_results)} results into a "
            f"coherent final report. Remove duplicates, resolve conflicts, and ensure consistency. "
            f"Keep ALL important detail — do not truncate to a short summary.\n\n"
            f"Original task: {prompt}\n\n"
            f"{excerpts}"
        ),
        priority="high",
        max_steps=20,
        swarm_id=swarm_id,
        parent_ctx=parent_ctx,
    )

    for _ in range(300):
        status = await get_subagent_status(reducer.id)
        if status and status["status"] in ("completed", "failed", "killed"):
            if status.get("status") == "completed" and status.get("result"):
                return status["result"]
            # Reducer failed — fall back to the verbatim worker outputs so no
            # data is lost.
            return _merge_results(worker_results, "map_reduce")
        await asyncio.sleep(2)

    await kill_subagent(reducer.id, force=True)
    return _merge_results(worker_results, "map_reduce") + "\n\n_Note: reduce phase timed out; showing worker outputs verbatim._"


async def _run_hierarchical(swarm_id, thread_id, prompt, agent_configs, agent_count, agent_type, priority, max_steps, parent_ctx, timeout_s=900) -> str:
    coordinator = await spawn_subagent(
        thread_id=thread_id,
        agent_type="coordinator",
        name="hierarchy-coordinator",
        prompt=(
            f"You are coordinating {agent_count} workers for this task:\n{prompt}\n\n"
            f"Break the task into subtasks and assign each to a worker. "
            f"Collect results and produce a final synthesis. "
            f"Give each worker its own directory under `.swarm/{swarm_id}/<worker-name>/` "
            f"and keep every important detail in the final synthesis (no short summary)."
        ),
        priority="critical",
        max_steps=max_steps + 10,
        swarm_id=swarm_id,
        parent_ctx=parent_ctx,
    )

    status = await _wait_for_agent(coordinator.id, timeout_s)
    if status.get("status") == "completed":
        return status.get("result", "Coordinator failed")
    return "Hierarchical swarm timed out"


def _split_subtasks(planner_output: str, count: int) -> list[str]:
    if not planner_output:
        return ["Complete the assigned portion of the task"] * count

    parts = []
    lines = planner_output.strip().split("\n")
    current_chunk = []

    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".):":
            if current_chunk:
                parts.append("\n".join(current_chunk))
                current_chunk = []
        current_chunk.append(line)

    if current_chunk:
        parts.append("\n".join(current_chunk))

    if len(parts) < count:
        chunk_size = max(1, len(planner_output) // count)
        parts = [planner_output[i:i + chunk_size] for i in range(0, len(planner_output), chunk_size)]

    while len(parts) < count:
        parts.append(f"Complete the assigned portion of the task (part {len(parts)+1})")

    return parts[:count]


def _merge_results(results: list[dict[str, Any]], strategy: str) -> str:
    """Merge worker outputs WITHOUT losing big-project data.

    Uses the full `result` (not the 500-char summary) with a generous per-agent
    budget. If the total still exceeds the budget, every agent keeps a fair
    share instead of the first agents eating everything.
    """
    if not results:
        return "No results collected"

    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") == "failed"]
    killed = [r for r in results if r.get("status") == "killed"]

    parts = [f"# Swarm result ({strategy}) — {len(completed)}/{len(results)} completed\n"]

    if completed:
        # Fair-share budgeting across agents.
        per_agent = max(2000, min(MERGE_PER_AGENT_CHARS, MERGE_TOTAL_CHARS // max(1, len(completed))))
        parts.append(f"## Completed Agents ({len(completed)})")
        for i, r in enumerate(completed):
            name = r.get("name", f"agent-{i+1}")
            agent_type = r.get("agent_type", "unknown")
            full = r.get("result") or r.get("result_summary") or "No result"
            report_path = r.get("report_path") or (r.get("meta") or {}).get("report_path", "")
            duration = r.get("duration_ms", 0)
            excerpt = full if len(full) <= per_agent else full[:per_agent] + "\n… (truncated — full text in report file/DB)"
            parts.append(f"### {name} ({agent_type}) — {duration}ms — {len(full)} chars")
            if report_path:
                parts.append(f"Full report: `{report_path}`")
            parts.append(excerpt)
            parts.append("")

    if failed:
        parts.append(f"## Failed Agents ({len(failed)})")
        for r in failed:
            name = r.get("name", "agent")
            error = r.get("error", "Unknown error")
            parts.append(f"- **{name}**: {error}")

    if killed:
        parts.append(f"## Killed Agents ({len(killed)})")
        for r in killed:
            name = r.get("name", "agent")
            parts.append(f"- **{name}**: Killed")

    merged = "\n\n".join(parts)
    if len(merged) > MERGE_TOTAL_CHARS + 2000:
        merged = merged[:MERGE_TOTAL_CHARS] + "\n… (merged report truncated — see per-agent report files for full text)"
    return merged


async def get_swarm_status(swarm_id: str) -> dict[str, Any] | None:
    async with SessionLocal() as db:
        swarm = await db.get(Swarm, swarm_id)
        if not swarm:
            return None

        query = select(SubAgent).where(SubAgent.swarm_id == swarm_id)
        agents = (await db.execute(query)).scalars().all()
        meta = swarm.meta or {}

        return {
            "id": swarm.id,
            "thread_id": swarm.thread_id,
            "name": swarm.name,
            "strategy": swarm.strategy,
            "status": swarm.status,
            "prompt": swarm.prompt,
            "agent_count": swarm.agent_count,
            "completed_count": swarm.completed_count,
            "failed_count": swarm.failed_count,
            "result": swarm.result,
            "result_chars": len(swarm.result or ""),
            "report_path": meta.get("report_path", ""),
            "meta": meta,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "agent_type": a.agent_type,
                    "status": a.status,
                    "priority": a.priority,
                    "result_summary": a.result_summary,
                    "result_chars": len(a.result or ""),
                    "report_path": (a.meta or {}).get("report_path", ""),
                    "error": a.error,
                    "duration_ms": a.duration_ms,
                    "is_live": runtime.is_running(a.id),
                }
                for a in agents
            ],
        }


async def wait_for_swarm(
    swarm_id: str,
    timeout_s: int = 900,
    poll_s: float = 3.0,
    on_progress: Any = None,
) -> dict[str, Any] | None:
    """Block until a swarm reaches a terminal state. One tool call, no step burn."""
    deadline = time.time() + max(1, timeout_s)
    while time.time() < deadline:
        status = await get_swarm_status(swarm_id)
        if status is None:
            return None
        if status["status"] in ("completed", "failed", "killed"):
            return status
        if on_progress is not None:
            try:
                maybe = on_progress(status)
                if asyncio.iscoroutine(maybe):
                    await maybe
            except Exception:
                pass
        await asyncio.sleep(poll_s)
    return await get_swarm_status(swarm_id)


async def list_swarms(thread_id: str) -> list[dict[str, Any]]:
    async with SessionLocal() as db:
        query = select(Swarm).where(Swarm.thread_id == thread_id).order_by(Swarm.created_at.desc())
        swarms = (await db.execute(query)).scalars().all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "strategy": s.strategy,
                "status": s.status,
                "agent_count": s.agent_count,
                "completed_count": s.completed_count,
                "failed_count": s.failed_count,
                "result": s.result[:500] if s.result else "",
            }
            for s in swarms
        ]


async def kill_swarm(swarm_id: str) -> int:
    # Stop the supervisor waiter first so it doesn't keep polling for minutes.
    task = _swarm_tasks.pop(swarm_id, None)
    if task is not None and not task.done():
        task.cancel()
    async with SessionLocal() as db:
        query = select(SubAgent).where(
            SubAgent.swarm_id == swarm_id,
            SubAgent.status.in_(["queued", "spawning", "running", "paused"])
        )
        agents = (await db.execute(query)).scalars().all()

        swarm = await db.get(Swarm, swarm_id)
        if swarm:
            swarm.status = "killed"
            await db.commit()

    count = 0
    for agent in agents:
        if await kill_subagent(agent.id):
            count += 1
    return count
