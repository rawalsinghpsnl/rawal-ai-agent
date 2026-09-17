# Agent Guide — modes, permissions, runs

A **Project** holds **Threads**. Each user turn starts a **run** that streams
events over SSE (`GET /threads/{id}/stream?after=<seq>` with resume).

## Modes

| Mode | Tools | Use when |
|---|---|---|
| **Agent** | Full (files, shell, browser, connectors, artifacts) | Doing the work |
| **Plan** | Read-only | Proposing before destructive/unfamiliar ops |
| **Chat** | None | Q&A without side effects |

Frontend reconnects with sequence-based resume — a network drop never silently
loses events.

## Permissions

- **ask** (default for shared/prod): every mutating tool prompts; approve/deny/`allow_always` per run.
- **auto**: only in a trusted isolated workspace (prefer Docker sandbox).
- Interrupt anytime (`/interrupt`), steer mid-run (`/steer`) without restarting.

## Reliability built-in

Stall watchdog (silent provider streams end visibly), exponential retries,
repeat-tool-call guard, context compaction at `COMPACT_AT_RATIO`, stale-run
recovery after restarts. If the agent looks stuck: check event feed + backend
logs → Interrupt → retry with a healthy provider/model.

## Sandbox backends (`SANDBOX_BACKEND`)

`auto` (default) = Docker when reachable, else path-confined local.
`docker` locally for untrusted code · `local` on Render/hosts without a daemon
· `superserve` for cloud MicroVMs · `github` for heavy background jobs via
Actions runners. See [configuration.md](configuration.md).

## Artifacts & sharing

Agent-created files appear under Artifacts; share via email transcript
(`SMTP_*`) or share links (`/threads/{id}/share`). Preview dev servers through
`/preview/{thread_id}/{port}/{path}` (ticket-cookie auth when login is enabled).
