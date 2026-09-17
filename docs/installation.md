# Installation — Windows / Linux / macOS / Termux

All installers are **re-runnable and self-healing**: failed `pip`/`npm` steps
retry automatically (`--no-cache-dir`, `--legacy-peer-deps`, cache clean).
Nothing is installed on any remote machine — only yours.

Requirements: Python **3.11+**, Node.js **20–22**, npm **10+**, Git.
Docker is optional (recommended for isolation) except on Termux (unavailable).

## One-click (recommended)

```bash
npx rawal-ai-agent --mode local --dir rawal-ai-agent   # local venv + npm
npx rawal-ai-agent --mode docker --dir rawal-ai-agent  # docker compose
```

Global:

```bash
npm i -g rawal-ai-agent
rawal-ai-agent --mode local
```

Flags: `--repo <url>` (fork), `--branch <name>`, `--yes` (non-interactive).
Public repos need **no token**. Private forks: export `RAWAL_GITHUB_TOKEN`
(or `GH_TOKEN`/`GITHUB_TOKEN`) — never paste tokens on the command line.

## Windows 10/11 (PowerShell)

```powershell
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

- `install.ps1` creates `backend\.venv`, installs backend + frontend deps with
  retries, generates `SECRET_KEY`/`JWT_SECRET` in `backend\.env` on first run.
- `make` is **not** required on Windows. Run the two printed commands in two
  terminals (backend uvicorn + `npm --prefix frontend run dev`), or use
  `docker compose up --build` when Docker Desktop is available.
- If `winget` is available: `winget install Python.Python.3.12 OpenJS.NodeJS Git.Git`.

## Linux (Debian/Ubuntu/Fedora/Arch)

```bash
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
bash install.sh
# optional dev extras: bash install.sh --dev
make dev
```

- `install.sh` checks versions, creates `backend/.venv`, retries pip/npm,
  generates signing secrets, and prints the right start command
  (`docker compose up --build` when a daemon is reachable, else `make dev`).
- Skip Docker probing: `RAWAL_SKIP_DOCKER=1 bash install.sh`.

## macOS

```bash
brew install python@3.12 node git
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
bash install.sh
make dev
```

Apple Silicon works out of the box; no Rosetta needed. Docker Desktop is
optional — without it the installer uses the local sandbox.

## Termux (Android)

```bash
pkg update && pkg install python nodejs git
npx rawal-ai-agent --mode local --dir rawal-ai-agent
# or: git clone … && bash install.sh
make dev   # or: npm run dev (see root package.json)
```

Notes: Docker is **unavailable** on Android — the installer forces local mode
automatically. Use the browser/PWA as the frontend. Keep the device awake for
long runs; SQLite persistence is local.

## Verifying

- Backend: `curl http://localhost:8000/api/v1/health`
- Docs: `http://localhost:8000/api/docs`
- Frontend dev: `http://localhost:5173`
- Docker single-origin: `http://localhost:8000`

## Uninstall / clean

```bash
docker compose down          # stop docker stack (data stays in ./data)
make clean                   # remove frontend/dist, node_modules, venv, data (careful!)
```

Never commit `backend/.env`, `.env`, `data/`, or `*.db`. See [security.md](security.md).
