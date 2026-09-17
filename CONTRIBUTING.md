# Contributing to rawal-ai-agent

Thanks for helping! This is an open-source, self-hosted project. Small, focused PRs win.

## Ground rules

- Be kind (see CODE_OF_CONDUCT.md). No harassment, no secret dumping.
- Never commit secrets: `backend/.env`, `.env`, tokens, keys, `data/`, `*.db`.
- Keep the `rawal-ai-agent` attribution (LICENSE/NOTICE headers, UI footer, CLI banner).
- One concern per PR; update docs when you change behavior.

## Local setup (no publish needed)

```bash
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
bash install.sh          # Windows: .\install.ps1
# set backend/.env → DEFAULT_LLM_API_KEY
make dev                 # API :8000 + web :5173
```

Docker alternative: `docker compose up --build` → `http://localhost:8000`.

## Checks before pushing

```bash
cd backend && .venv/bin/python -m pytest -q
.venv/bin/ruff check app/ tests/
cd ../frontend && npm run typecheck && npm run build
cd ../cli && npm pack --dry-run && node --check index.js
```

Windows (no make): run the backend pytest + frontend typecheck/build commands directly.

## PR checklist

- [ ] `npm run typecheck` + `vite build` pass (frontend)
- [ ] `pytest -q` + `ruff` pass (backend)
- [ ] Docs updated (`docs/` + README if user-facing)
- [ ] No secrets, no `data/`, no personal workspaces
- [ ] Storage-key / DB renames keep legacy fallback (`bhati.*` → `rawal.*`)

## Release (maintainers)

1. Bump `cli/package.json`, `frontend/package.json`, `backend/pyproject.toml` together.
2. Update `docs/CHANGELOG.md`.
3. `npm publish ./cli --access public` (package: `rawal-ai-agent`).
4. Tag `vX.Y.Z` + GitHub Release with Render/Vercel notes.
