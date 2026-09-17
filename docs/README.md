# rawal-ai-agent — Documentation Index

Welcome to the complete docs for **rawal-ai-agent** (v2.0.0): a self-hosted
autonomous AI workspace (FastAPI backend + React/Vite frontend + sandbox).

## Start here

| Doc | What it answers |
|---|---|
| [quickstart.md](quickstart.md) | 5-minute first run (Docker or local) |
| [installation.md](installation.md) | Windows / Linux / macOS / Termux + one-click + offline notes |
| [npm-registry.md](npm-registry.md) | `npx rawal-ai-agent` one-click + `npm publish ./cli` for maintainers |
| [configuration.md](configuration.md) | Every env var, secrets, providers, persistence, sandbox |
| [deployment.md](deployment.md) | Docker, Render backend + Vercel frontend, rollback |
| [render-vercel-checklist.md](render-vercel-checklist.md) | Copy-paste Render/Vercel deploy checklist |
| [architecture.md](architecture.md) | Runtime components, event flow, sandbox model, data boundaries |
| [agent-guide.md](agent-guide.md) | Agent / Plan / Chat modes, permissions, steering, compaction |
| [api-reference.md](api-reference.md) | REST + SSE + WebSocket surface (see also `/api/docs` live) |
| [browser-automation.md](browser-automation.md) | Browser runtime, CDP on Render Free, recovery |
| [security.md](security.md) | Threat model + hardening (pair with root `SECURITY.md`) |
| [troubleshooting.md](troubleshooting.md) | Symptoms → fixes + log locations |
| [faq.md](faq.md) | 30-second answers to the most common questions |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each release |

Root files: `README.md` (overview), `LICENSE`, `NOTICE` (attribution — keeps
credit safe), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.

> Rebrand note: versions before 2.0 used the name *Bhati / bhati-ai*. Storage
> keys (`bhati.*` → `rawal.*`), DB file (`bhati.db` → `rawal.db`), and env
> prefixes (`BHATI_*` → `RAWAL_*`) migrate automatically — old installs keep
> their data. See [CHANGELOG.md](CHANGELOG.md).
