# API Reference — rawal-ai-agent

Base path: **`/api/v1`**. Live interactive docs: **`/api/docs`** (served by the
backend). This page is the map — payloads live in OpenAPI, not copied here.

## System

| Method + path | Purpose |
|---|---|
| `GET /health` | Liveness (Render health check) |
| `GET /capabilities` | Feature flags + backend info |
| `GET /tools` | Tool groups + counts |

## Projects & threads

`GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`,
`GET/POST /threads`, `GET/PATCH/DELETE /threads/{id}`,
`POST /threads/{id}/truncate`, `POST /threads/{id}/fork`,
`GET /threads/{id}/messages`, `DELETE /threads/{id}/messages`,
`GET /threads/{id}/artifacts`.

## Agent runs (streaming)

- `POST /threads/{id}/messages` — start a run
- `POST /threads/{id}/interrupt` · `/steer` · `/permissions` · `GET /threads/{id}/status`
- `GET /threads/{id}/stream?after=<seq>` — SSE event stream (resume-safe)

## Files / terminal / preview

Thread file read/write/list/upload/download/delete, archive download,
project archive; WebSocket terminal (`/threads/{id}/terminal` + sandbox
lifecycle/exec); preview proxy `/preview/{thread_id}/{port}/{path}` with
short-lived ticket (`GET /preview/ticket?...`) for iframe sub-resources.

## Providers / integrations / MCP

`/providers` CRUD + `/providers/{id}/refresh-models` + `/providers/test` +
`/providers/models`; `/connectors` (+ `/probe`, OAuth url/callback);
`/mcp` (+ presets/restart), `/mcp/registry`, `/mcp/directory`;
GitHub/Vercel/Render/HuggingFace/Telegram routes; `/sandbox/config`.

## Shares / jobs / stats

`/threads/{id}/shares`, `POST /threads/{id}/share`, `DELETE /share/{token}`,
`GET /share/{token}`; artifact comments; `/jobs` (+ `run-now`);
`/stats/overview`, `/stats/by-model`, `/stats/daily`, `/audit`.

Auth: `GET /auth/status`, `POST /auth/login {password}`, `POST /auth/logout`
(Bearer token; empty `AUTH_PASSWORD` = open local mode — never public).
