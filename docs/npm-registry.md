# npm Registry — `rawal-ai-agent` one-click

Package: **`rawal-ai-agent`** (npm, public). Binary: `rawal-ai-agent` (+ alias `rawal`).
Source lives in `cli/` — a tiny installer that clones the full repo, so
`npm i` stays instant and never bundles secrets.

## For users (one click)

```bash
npx rawal-ai-agent --mode local --dir rawal-ai-agent
npx rawal-ai-agent --mode docker --dir rawal-ai-agent
npm i -g rawal-ai-agent && rawal-ai-agent --mode local
```

What it does:

1. Checks `git` (+ `python/node/npm` for `--mode local`, `docker` for `--mode docker`).
2. Shallow-clones `--repo` (default: public `rawal-ai-agent` repo) or `git pull --ff-only` when the folder exists.
3. Runs `install.sh` / `install.ps1` (local) or `docker compose up --build -d` (docker, with local fallback when Docker is missing — e.g. Termux).
4. Prints exact next steps (set `backend/.env → DEFAULT_LLM_API_KEY`, start commands, URLs).

Every failure auto-retries: shallow→full clone, `npm ci`→`npm install`→`--legacy-peer-deps`→cache-clean, pip→`--no-cache-dir`. Re-running is always safe.

## For maintainers (publish)

Prerequisites: `npm login`, version bump in `cli/package.json` (+ keep
`frontend/package.json` and `backend/pyproject.toml` in sync), `LICENSE` present.

```bash
cd cli
node --check index.js
npm pack --dry-run     # shows files: index.js, README.md, LICENSE
npm publish --access public   # package name: rawal-ai-agent
```

Then: tag `vX.Y.Z`, GitHub Release, update [CHANGELOG.md](CHANGELOG.md).

Upstream repo is `https://github.com/rawalsinghpsnl/rawal-ai-agent.git`
(baked into `cli/package.json`, root `package.json`, and `cli/index.js`).
Forks: pass `--repo <fork-url>` or set `RAWAL_REPO` — no code change needed.

## Naming / anti-squatting

- Canonical: `rawal-ai-agent`. Alias `rawal` exists for convenience.
- Do **not** publish `rawal`, `rawal-ai`, `rawal-agent` typosquats claiming to be
  upstream — see `NOTICE`. Report abuse via `npm abuse` + GitHub Issues.
- `cli/package.json` sets `publishConfig.access: public`, `engines.node >= 20`,
  `repository/homepage/bugs`, and `files` limited to installer + license so no
  backend/frontend code or secrets ever ship to npm.

## Troubleshooting installs

| Symptom | Fix |
|---|---|
| `404` on `npx` | Package not yet published or wrong name — check `npm view rawal-ai-agent` |
| `Missing prerequisites` | Follow the printed `winget` / `brew` / `pkg` / `apt` command, re-run |
| `Shallow clone failed` | Wrong `--repo` or no network — pass `--repo <fork-url>` |
| `docker info` fails | Start Docker Desktop, or use `--mode local` |
| npm `EBADENGINE` | Use Node 20–22 (`nvm use 22`) |
| npm `EAI_AGAIN`/timeout | Re-run (auto-retries); check proxy/VPN |
