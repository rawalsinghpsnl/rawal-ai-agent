# rawal-ai-agent installer (npm)

One-command, self-healing installer for the open-source **rawal-ai-agent** workspace.

## One-click install

```bash
npx rawal-ai-agent --mode local --dir rawal-ai-agent
# or with Docker:
npx rawal-ai-agent --mode docker --dir rawal-ai-agent
```

Global install:

```bash
npm i -g rawal-ai-agent
rawal-ai-agent --mode local
```

Windows PowerShell:

```powershell
npx rawal-ai-agent --mode local --dir rawal-ai-agent
```

Termux (Android):

```bash
pkg install python nodejs git
npx rawal-ai-agent --mode local --dir rawal-ai-agent
```

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--mode docker` | yes | `docker compose up --build -d` (falls back to local when Docker is missing) |
| `--mode local` | — | `bash install.sh` / `install.ps1`, then print dev commands |
| `--dir <folder>` | `rawal-ai-agent` | Installation folder |
| `--repo <url>` | public repo | Override source repo / fork |
| `--branch <name>` | — | Branch or tag to clone |
| `--yes` | — | Non-interactive |

## Tokens

Public installs need **no token**. For private forks, export one of
`RAWAL_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` in the environment. The token is
used only for the git operation, redacted from logs, never written to disk.

## After install

1. Edit `backend/.env` → set `DEFAULT_LLM_API_KEY` (and `AUTH_PASSWORD` for public hosts).
2. `make dev` (Linux/macOS) or the two commands printed by `install.ps1` (Windows).
3. Open `http://localhost:5173` (dev) or `http://localhost:8000` (Docker).

See `docs/npm-registry.md` for publishing (`npm publish ./cli`) and versioning.
SPDX-License-Identifier: MIT.
