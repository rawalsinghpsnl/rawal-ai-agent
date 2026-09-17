"""Agent management tools — spawn, wait, inspect (full results), kill, swarm operations."""

from __future__ import annotations

from app.agent.subagent_manager import AGENT_TYPES, PRIORITY_LEVELS
from app.core.utils import truncate
from app.tools.base import ToolContext, ToolResult, boolean, integer, obj, string
from app.tools.registry import registry

# Chars of a subagent/swarm report handed to the main agent in ONE tool result.
# Big-project outputs must not be squeezed to 2-3k chars anymore; the agent
# loop caps tool results at 30k, so 25k here stays safe while preserving detail.
FULL_RESULT_CHARS = 25_000
STATUS_RESULT_CHARS = 12_000


def _slice(text: str, offset: int = 0, limit: int = FULL_RESULT_CHARS) -> tuple[str, bool, int]:
    total = len(text or "")
    start = max(0, offset)
    window = (text or "")[start:start + max(1, limit)]
    has_more = start + len(window) < total
    return window, has_more, total


@registry.tool(
    "agent_spawn",
    (
        "Spawn a new subagent with a specific type and priority. The agent runs independently "
        "in the background. Use this to delegate work to specialized agents. "
        "Available types: " + ", ".join(f"{k}" for k in AGENT_TYPES.keys())
        + ". IMPORTANT delegation rule: after spawning, do NOT poll agent_status in a loop "
        "(that burns your step budget and hits the execution limit). Instead call `agent_wait` "
        "ONCE with a generous timeout — it blocks efficiently and returns the FULL result. "
        "For big tasks (research, multi-file builds) always delegate and always wait."
    ),
    obj({
        "agent_type": string("Type of subagent to spawn", enum=sorted(AGENT_TYPES.keys())),
        "name": string("Human-readable name for this agent"),
        "prompt": string("Full standalone instructions for the agent. For coding tasks, tell it to write files AND return the complete code verbatim. For research, tell it to return complete notes with links, not a short summary."),
        "priority": string("Priority level: critical, high, normal, low, background", enum=sorted(PRIORITY_LEVELS.keys()), default="normal"),
        "max_steps": integer("Maximum tool steps the agent can take", default=25),
    }, ["agent_type", "name", "prompt"]),
    group="agents",
)
async def agent_spawn(ctx: ToolContext, agent_type: str, name: str, prompt: str, priority: str = "normal", max_steps: int = 25):
    from app.agent.subagent_manager import spawn_subagent
    agent = await spawn_subagent(thread_id=ctx.thread_id, agent_type=agent_type, name=name, prompt=prompt, priority=priority, max_steps=max_steps, parent_ctx=ctx)
    type_config = AGENT_TYPES.get(agent_type, {})
    icon = type_config.get("icon", "🤖")
    return ToolResult(
        content=f"✅ Spawned subagent **{name}** ({icon} {agent_type})\n- **ID**: {agent.id}\n- **Priority**: {priority}\n- **Max Steps**: {max_steps}\n- **Status**: {agent.status}\n\nNext: call `agent_wait` ONCE with agent_id `{agent.id}` and a generous timeout (e.g. 600). Do NOT poll `agent_status` repeatedly.",
        display={"kind": "agent_spawn", "agent_id": agent.id, "agent_type": agent_type, "name": name, "priority": priority, "status": agent.status, "icon": icon},
    )


@registry.tool(
    "agent_wait",
    (
        "Block until a subagent finishes (or the timeout expires) and return its FULL result. "
        "This is ONE tool call no matter how long the agent runs — use it instead of polling "
        "`agent_status`, which burns your step budget and causes execution-limit errors. "
        "Always prefer agent_wait after agent_spawn."
    ),
    obj({
        "agent_id": string("ID of the subagent to wait for"),
        "timeout": integer("Max seconds to wait (1-1800)", default=600),
    }, ["agent_id"]),
    group="agents",
)
async def agent_wait(ctx: ToolContext, agent_id: str, timeout: int = 600):
    import asyncio
    from app.agent.subagent_manager import wait_for_subagent
    timeout = max(1, min(int(timeout or 600), 1800))
    last_emit = 0.0

    async def _progress(status):
        nonlocal last_emit
        import time as _time
        now = _time.time()
        if now - last_emit < 15:
            return
        last_emit = now
        try:
            await ctx.progress(f"Waiting on subagent {status.get('name', agent_id)} ({status.get('status')}, {status.get('steps_completed', 0)}/{status.get('max_steps', 0)} steps)...")
        except Exception:
            pass
        try:
            from app.sandbox import sandboxes as _sb
            _sb.touch(ctx.thread_id)
        except Exception:
            pass

    status = await wait_for_subagent(agent_id, timeout_s=timeout, poll_s=2.0, on_progress=_progress)
    if not status:
        return ToolResult.error(f"Subagent `{agent_id}` not found.")
    state = status.get("status", "unknown")
    if state not in ("completed", "failed", "killed"):
        return ToolResult(
            content=f"⏳ Subagent `{agent_id}` still **{state}** after {timeout}s. Call `agent_wait` again to keep waiting, or `agent_kill` to stop it.",
            display={"kind": "agent_wait", "agent_id": agent_id, "status": state, "timed_out": True},
        )
    result = status.get("result") or status.get("error") or "(no output)"
    window, has_more, total = _slice(result, 0, FULL_RESULT_CHARS)
    tail = f"\n\n… ({total - len(window)} more chars — call `agent_result` with offset={len(window)} to read the rest{'; full file: `' + status.get('report_path', '') + '`' if status.get('report_path') else ''})" if has_more else ""
    report_line = f"\n- **Full report file**: `{status['report_path']}` ({total} chars)" if status.get("report_path") else ""
    return ToolResult(
        content=f"## Subagent {status.get('name', '')} — {state}\n- **ID**: {agent_id}\n- **Steps**: {status.get('steps_completed', 0)}/{status.get('max_steps', 0)}\n- **Duration**: {status.get('duration_ms', 0)}ms{report_line}\n\n### Full result\n{window}{tail}",
        display={"kind": "agent_wait", "agent_id": agent_id, "status": state, "result": result, "report_path": status.get("report_path", ""), "result_chars": total},
    )


@registry.tool(
    "agent_result",
    (
        "Fetch the FULL result of a finished subagent with pagination. `agent_status` shows a "
        "bounded preview; use this when you need everything (big research notes, generated code)."
    ),
    obj({
        "agent_id": string("ID of the subagent"),
        "offset": integer("Character offset to start from", default=0),
        "limit": integer("Max characters to return (1-30000)", default=15000),
    }, ["agent_id"]),
    group="agents",
)
async def agent_result(ctx: ToolContext, agent_id: str, offset: int = 0, limit: int = 15000):
    from app.agent.subagent_manager import get_subagent_status
    status = await get_subagent_status(agent_id)
    if not status:
        return ToolResult.error(f"Subagent `{agent_id}` not found.")
    if status.get("status") not in ("completed", "failed", "killed"):
        return ToolResult(content=f"Subagent `{agent_id}` is still **{status.get('status')}**. Use `agent_wait` to block until it finishes.")
    text = status.get("result") or status.get("error") or ""
    limit = max(1, min(int(limit or 15000), 30000))
    window, has_more, total = _slice(text, int(offset or 0), limit)
    tail = f"\n\n… ({total - (int(offset or 0) + len(window))} more chars, total {total} — call again with offset={int(offset or 0) + len(window)})" if has_more else f"\n\n— end ({total} chars total) —"
    return ToolResult(
        content=f"## {status.get('name', '')} result [{int(offset or 0)}:{int(offset or 0) + len(window)}/{total}]\n{window}{tail}",
        display={"kind": "agent_result", "agent_id": agent_id, "offset": offset, "total": total, "has_more": has_more},
    )


@registry.tool(
    "agent_kill",
    "Kill a running subagent by ID. Use agent_list to find agent IDs.",
    obj({
        "agent_id": string("ID of the subagent to kill"),
        "force": string("Force kill without graceful shutdown", enum=["true", "false"], default="false"),
    }, ["agent_id"]),
    group="agents",
)
async def agent_kill(ctx: ToolContext, agent_id: str, force: str = "false"):
    from app.agent.subagent_manager import kill_subagent
    success = await kill_subagent(agent_id, force=(force == "true"))
    if success:
        return ToolResult(content=f"☠️ Subagent `{agent_id}` has been killed.", display={"kind": "agent_kill", "agent_id": agent_id, "status": "killed"})
    return ToolResult.error(f"Could not kill subagent `{agent_id}`. It may not exist or already be stopped.")


@registry.tool(
    "agent_list",
    "List all subagents for the current thread. Shows status, priority, and result summary.",
    obj({
        "status": string("Filter by status", enum=["queued", "spawning", "running", "paused", "completed", "failed", "killed"], default=""),
    }, []),
    group="agents",
)
async def agent_list(ctx: ToolContext, status: str = ""):
    from app.agent.subagent_manager import list_subagents
    agents = await list_subagents(ctx.thread_id, status=status or None)
    if not agents:
        filter_msg = f" with status '{status}'" if status else ""
        return ToolResult(content=f"No subagents found{filter_msg}.")

    lines = ["## SubAgents\n"]
    for a in agents:
        type_config = AGENT_TYPES.get(a.get("agent_type", ""), {})
        icon = type_config.get("icon", "🤖")
        p_icon = {"critical": "🔴", "high": "🟠", "normal": "🔵", "low": "⚪", "background": "⬛"}.get(a.get("priority", "normal"), "🔵")
        s_icon = {"queued": "⏳", "spawning": "🔄", "running": "▶️", "paused": "⏸️", "completed": "✅", "failed": "❌", "killed": "☠️"}.get(a.get("status", ""), "❓")
        lines.append(f"{s_icon} {icon} **{a.get('name', 'unnamed')}** (`{a.get('id', '')}`)")
        lines.append(f"  - Type: {a.get('agent_type', 'unknown')} | Priority: {p_icon} {a.get('priority', 'normal')} | Status: {a.get('status', 'unknown')}")
        lines.append(f"  - Duration: {a.get('duration_ms', 0)}ms")
        if a.get("result_summary"):
            lines.append(f"  - Result: {truncate(a['result_summary'], 200)}")
        if a.get("error"):
            lines.append(f"  - Error: {a['error']}")
        lines.append("")

    return ToolResult(content="\n".join(lines), display={"kind": "agent_list", "agents": agents})


@registry.tool(
    "agent_status",
    (
        "Get detailed status of a specific subagent. Shows priority, current status, result preview, "
        "error, duration. This is a lightweight poll — do NOT call it in a loop. After spawning, "
        "call `agent_wait` once. Use `agent_result` for the paginated FULL result."
    ),
    obj({
        "agent_id": string("ID of the subagent to inspect"),
        "full": boolean("Return the full result (up to 25k chars) instead of a preview", default=False),
    }, ["agent_id"]),
    group="agents",
)
async def agent_status(ctx: ToolContext, agent_id: str, full: bool = False):
    from app.agent.subagent_manager import get_subagent_status
    status = await get_subagent_status(agent_id)
    if not status:
        return ToolResult.error(f"Subagent `{agent_id}` not found.")

    type_config = AGENT_TYPES.get(status.get("agent_type", ""), {})
    icon = type_config.get("icon", "🤖")
    total = status.get("result_chars", len(status.get("result") or ""))
    lines = [
        f"## {icon} {status.get('name', 'unnamed')} — Detailed Status\n",
        f"- **ID**: {status.get('id', '')}",
        f"- **Type**: {status.get('agent_type', 'unknown')}",
        f"- **Priority**: {status.get('priority', 'normal')}",
        f"- **Status**: {status.get('status', 'unknown')}",
        f"- **Live**: {'Yes' if status.get('is_live') else 'No'}",
        f"- **Max Steps**: {status.get('max_steps', 0)}",
        f"- **Steps Completed**: {status.get('steps_completed', 0)}",
        f"- **Duration**: {status.get('duration_ms', 0)}ms",
        f"- **Result size**: {total} chars",
        f"- **Started**: {status.get('started_at', 'N/A')}",
        f"- **Finished**: {status.get('finished_at', 'N/A')}",
    ]
    if status.get("swarm_id"):
        lines.append(f"- **Swarm**: {status['swarm_id']}")
    if status.get("report_path"):
        lines.append(f"- **Full report file**: `{status['report_path']}` (read with `read_file`)")
    if status.get("result"):
        budget = FULL_RESULT_CHARS if full else STATUS_RESULT_CHARS
        window, has_more, _ = _slice(status["result"], 0, budget)
        lines.append(f"\n### Result\n{window}")
        if has_more:
            lines.append(f"\n… ({total - len(window)} more chars — call `agent_result` with offset={len(window)} or `agent_status` with full=true)")
        elif status.get("status") not in ("completed", "failed", "killed"):
            lines.append("\n_(still running — call `agent_wait` to block until done)_")
    if status.get("error"):
        lines.append(f"\n### Error\n{status['error']}")
    if status.get("tools_blocked"):
        lines.append(f"\n### Blocked Tools\n{', '.join(status['tools_blocked'])}")

    return ToolResult(content="\n".join(lines), display={"kind": "agent_status", "status": status})


@registry.tool(
    "swarm_deploy",
    (
        "Deploy a swarm of coordinated subagents. Strategies:\n"
        "- **parallel**: All agents run simultaneously (different files/topics per worker)\n"
        "- **sequential**: Agents run one after another, each continuing from the previous\n"
        "- **map_reduce**: Planner splits → workers parallel → reducer merges (best for big research/builds)\n"
        "- **hierarchical**: Coordinator delegates to workers\n"
        "\nEach worker writes its files under its own `.swarm/<swarm_id>/<worker>/` directory so "
        "parallel coders never overwrite each other, and every worker returns its COMPLETE output "
        "verbatim. After deploying, call `swarm_wait` ONCE — never poll `swarm_status` in a loop."
    ),
    obj({
        "name": string("Name for this swarm"),
        "prompt": string("The task/prompt for the swarm to work on. For builds: specify files each worker owns. For research: demand complete notes with links, not summaries."),
        "strategy": string("Deployment strategy", enum=["parallel", "sequential", "map_reduce", "hierarchical"], default="parallel"),
        "agent_count": integer("Number of agents to deploy", default=3),
        "agent_type": string("Type of agents to deploy", enum=sorted(AGENT_TYPES.keys()), default="coder"),
        "priority": string("Priority for all agents", enum=sorted(PRIORITY_LEVELS.keys()), default="normal"),
        "max_steps": integer("Max steps per agent", default=25),
        "timeout": integer("Seconds the background swarm may run before members time out (60-3600)", default=600),
    }, ["name", "prompt", "strategy"]),
    group="agents",
)
async def swarm_deploy(ctx: ToolContext, name: str, prompt: str, strategy: str = "parallel", agent_count: int = 3, agent_type: str = "coder", priority: str = "normal", max_steps: int = 25, timeout: int = 600):
    from app.agent.swarm_manager import deploy_swarm
    timeout = max(60, min(int(timeout or 600), 3600))
    agent_count = max(1, min(int(agent_count or 3), 10))
    swarm = await deploy_swarm(thread_id=ctx.thread_id, name=name, prompt=prompt, strategy=strategy, agent_count=agent_count, agent_type=agent_type, priority=priority, max_steps=max_steps, parent_ctx=ctx, timeout_s=timeout)
    strategy_icons = {"parallel": "⚡", "sequential": "🔗", "map_reduce": "🗺️", "hierarchical": "🏗️"}
    icon = strategy_icons.get(strategy, "🐝")
    return ToolResult(
        content=f"{icon} Swarm **{name}** deployed!\n- **ID**: {swarm.id}\n- **Strategy**: {strategy}\n- **Agents**: {agent_count} × {agent_type}\n- **Priority**: {priority}\n- **Status**: {swarm.status}\n\nNext: call `swarm_wait` ONCE with swarm_id `{swarm.id}` (timeout ~{timeout}). It returns the FULL merged result. Do NOT poll `swarm_status` in a loop.",
        display={"kind": "swarm_deploy", "swarm_id": swarm.id, "name": name, "strategy": strategy, "agent_count": agent_count, "status": swarm.status},
    )


@registry.tool(
    "swarm_wait",
    (
        "Block until a swarm finishes (or the timeout expires) and return the FULL merged result. "
        "ONE tool call regardless of duration — this is how you avoid the execution-limit error. "
        "Always use swarm_wait after swarm_deploy."
    ),
    obj({
        "swarm_id": string("ID of the swarm to wait for"),
        "timeout": integer("Max seconds to wait (1-3600)", default=900),
    }, ["swarm_id"]),
    group="agents",
)
async def swarm_wait(ctx: ToolContext, swarm_id: str, timeout: int = 900):
    from app.agent.swarm_manager import wait_for_swarm
    timeout = max(1, min(int(timeout or 900), 3600))
    last_emit = 0.0

    async def _progress(status):
        nonlocal last_emit
        import time as _time
        now = _time.time()
        if now - last_emit < 20:
            return
        last_emit = now
        try:
            await ctx.progress(f"Swarm {status.get('name', swarm_id)}: {status.get('completed_count', 0)}/{status.get('agent_count', 0)} done, status={status.get('status')}...")
        except Exception:
            pass
        try:
            from app.sandbox import sandboxes as _sb
            _sb.touch(ctx.thread_id)
        except Exception:
            pass

    status = await wait_for_swarm(swarm_id, timeout_s=timeout, poll_s=3.0, on_progress=_progress)
    if not status:
        return ToolResult.error(f"Swarm `{swarm_id}` not found.")
    state = status.get("status", "unknown")
    if state not in ("completed", "failed", "killed"):
        return ToolResult(
            content=f"⏳ Swarm `{swarm_id}` still **{state}** after {timeout}s ({status.get('completed_count', 0)}/{status.get('agent_count', 0)} agents done). Call `swarm_wait` again to keep waiting.",
            display={"kind": "swarm_wait", "swarm_id": swarm_id, "status": state, "timed_out": True},
        )
    result = status.get("result") or "(no output)"
    total = status.get("result_chars", len(result))
    window, has_more, _ = _slice(result, 0, FULL_RESULT_CHARS)
    tail = f"\n\n… ({total - len(window)} more chars — call `swarm_result` with offset={len(window)} to read the rest)" if has_more else ""
    report_line = f"\n- **Full report file**: `{status['report_path']}` ({total} chars)" if status.get("report_path") else ""
    agent_lines = "\n".join(
        f"  - {a.get('name', '?')} — {a.get('status')} ({a.get('result_chars', 0)} chars{('; ' + a['report_path']) if a.get('report_path') else ''})"
        for a in (status.get("agents") or [])
    )
    return ToolResult(
        content=f"## Swarm {status.get('name', '')} — {state}\n- **ID**: {swarm_id}\n- **Agents**: {status.get('completed_count', 0)}/{status.get('agent_count', 0)} completed{report_line}\n\n### Agents\n{agent_lines}\n\n### Full merged result\n{window}{tail}",
        display={"kind": "swarm_wait", "swarm_id": swarm_id, "status": state, "result": result, "report_path": status.get("report_path", ""), "result_chars": total},
    )


@registry.tool(
    "swarm_result",
    "Fetch the FULL merged result of a finished swarm with pagination.",
    obj({
        "swarm_id": string("ID of the swarm"),
        "offset": integer("Character offset to start from", default=0),
        "limit": integer("Max characters to return (1-30000)", default=15000),
    }, ["swarm_id"]),
    group="agents",
)
async def swarm_result(ctx: ToolContext, swarm_id: str, offset: int = 0, limit: int = 15000):
    from app.agent.swarm_manager import get_swarm_status
    status = await get_swarm_status(swarm_id)
    if not status:
        return ToolResult.error(f"Swarm `{swarm_id}` not found.")
    if status.get("status") not in ("completed", "failed", "killed"):
        return ToolResult(content=f"Swarm `{swarm_id}` is still **{status.get('status')}**. Use `swarm_wait` to block until it finishes.")
    text = status.get("result") or ""
    limit = max(1, min(int(limit or 15000), 30000))
    window, has_more, total = _slice(text, int(offset or 0), limit)
    tail = f"\n\n… ({total - (int(offset or 0) + len(window))} more chars, total {total} — call again with offset={int(offset or 0) + len(window)})" if has_more else f"\n\n— end ({total} chars total) —"
    return ToolResult(
        content=f"## {status.get('name', '')} result [{int(offset or 0)}:{int(offset or 0) + len(window)}/{total}]\n{window}{tail}",
        display={"kind": "swarm_result", "swarm_id": swarm_id, "offset": offset, "total": total, "has_more": has_more},
    )


@registry.tool(
    "swarm_status",
    (
        "Get status of a swarm including all its agents. Lightweight poll — do NOT call in a loop. "
        "Use `swarm_wait` to block for the full result, `swarm_result` for paginated full text."
    ),
    obj({
        "swarm_id": string("ID of the swarm to inspect"),
        "full": boolean("Include the full merged result (up to 25k chars)", default=False),
    }, ["swarm_id"]),
    group="agents",
)
async def swarm_status(ctx: ToolContext, swarm_id: str, full: bool = False):
    from app.agent.swarm_manager import get_swarm_status
    status = await get_swarm_status(swarm_id)
    if not status:
        return ToolResult.error(f"Swarm `{swarm_id}` not found.")

    strategy_icons = {"parallel": "⚡", "sequential": "🔗", "map_reduce": "🗺️", "hierarchical": "🏗️"}
    icon = strategy_icons.get(status.get("strategy", ""), "🐝")
    total = status.get("result_chars", len(status.get("result") or ""))
    lines = [
        f"## {icon} Swarm: {status.get('name', 'unnamed')}\n",
        f"- **ID**: {status.get('id', '')}",
        f"- **Strategy**: {status.get('strategy', 'unknown')}",
        f"- **Status**: {status.get('status', 'unknown')}",
        f"- **Agents**: {status.get('completed_count', 0)}/{status.get('agent_count', 0)} completed",
        f"- **Result size**: {total} chars",
    ]
    if status.get("report_path"):
        lines.append(f"- **Full report file**: `{status['report_path']}` (read with `read_file`)")
    if status.get("result"):
        budget = FULL_RESULT_CHARS if full else STATUS_RESULT_CHARS
        window, has_more, _ = _slice(status["result"], 0, budget)
        lines.append(f"\n### Result\n{window}")
        if has_more:
            lines.append(f"\n… ({total - len(window)} more chars — call `swarm_result` with offset={len(window)})")

    agents = status.get("agents", [])
    if agents:
        lines.append(f"\n### Agents ({len(agents)})")
        for a in agents:
            a_icon = AGENT_TYPES.get(a.get("agent_type", ""), {}).get("icon", "🤖")
            s_icon = {"queued": "⏳", "spawning": "🔄", "running": "▶️", "paused": "⏸️", "completed": "✅", "failed": "❌", "killed": "☠️"}.get(a.get("status", ""), "❓")
            lines.append(f"  {s_icon} {a_icon} **{a.get('name', 'unnamed')}** — {a.get('status', 'unknown')} | {a.get('priority', 'normal')} | {a.get('duration_ms', 0)}ms | {a.get('result_chars', 0)} chars")
            if a.get("report_path"):
                lines.append(f"    Full: `{a['report_path']}` — use `agent_result` for complete text")
            elif a.get("result_summary"):
                lines.append(f"    Result: {truncate(a['result_summary'], 500)}")
            if a.get("error"):
                lines.append(f"    Error: {a['error']}")

    return ToolResult(content="\n".join(lines), display={"kind": "swarm_status", "status": status})


@registry.tool(
    "swarm_kill",
    "Kill all agents in a swarm and stop the swarm.",
    obj({"swarm_id": string("ID of the swarm to kill")}, ["swarm_id"]),
    group="agents",
)
async def swarm_kill(ctx: ToolContext, swarm_id: str):
    from app.agent.swarm_manager import kill_swarm
    count = await kill_swarm(swarm_id)
    return ToolResult(content=f"☠️ Swarm `{swarm_id}` killed. {count} agent(s) terminated.", display={"kind": "swarm_kill", "swarm_id": swarm_id, "killed_count": count})


@registry.tool(
    "agent_kill_all",
    "Kill all running subagents for the current thread.",
    obj({}, []),
    group="agents",
)
async def agent_kill_all(ctx: ToolContext):
    from app.agent.subagent_manager import kill_all_subagents
    count = await kill_all_subagents(ctx.thread_id)
    return ToolResult(content=f"☠️ Killed {count} running subagent(s).", display={"kind": "agent_kill_all", "killed_count": count})
