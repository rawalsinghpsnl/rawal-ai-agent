# Changelog — rawal-ai-agent

## 2.0.0 — Open-source release (2026-09-17)

**Rebrand:** `Bhati / bhati-ai` → **`rawal-ai-agent`** across backend, frontend,
installers, Docker, docs, and npm. Auto-migration included:

- Frontend storage `bhati.*` → `rawal.*` (legacy fallback + one-time copy; PIN salt accepts both).
- Backend DB `bhati.db` → `rawal.db` (legacy file reused when canonical missing); `DATABASE_NAME bhati_ai_agent` → `rawal_ai`.
- JWT issuer/audience, `AUTH_USERNAME bhati` → `rawal`, `BHATI_*` env → `RAWAL_*` (old `BHATI_SKIP_DOCKER` still honored), container/label prefixes, User-Agents, GitHub Actions `RAWAL_*` + `rawal-result.json`, OAuth event `rawal:oauth:done` (both accepted during transition), preview cookie `rawal_pv_`, Drive folder `Rawal_AI_Agent_Workspaces`, Android `RawalAiAgent/Projects`.
- Sandbox image `rawal-ai-agent-sandbox:latest` unified (compose, Makefile, config).

**Open-source hardening:** `LICENSE` (MIT) + `NOTICE` (attribution/anti-theft) +
`CONTRIBUTING` + `CODE_OF_CONDUCT` + `SECURITY.md` + `.gitattributes` (LF for `.sh`) +
hardened `.gitignore`; `cli` renamed `rawal` → `rawal-ai-agent` (bin `rawal-ai-agent` + `rawal` alias, public `publishConfig`, `engines.node >= 20`); root `package.json` workspaces + cross-platform scripts; `.nvmrc` (22).

**Deploy/install fixes (no live testing per operator request — verify on your machine):**
`docker-compose.yml` indentation + `env_file` + Windows-safe volume + healthcheck +
`depends_on`; `render.yaml` service `rawal-ai-agent` + 1 GB disk + `ALLOW_ANONYMOUS=false` +
`AUTH_USERNAME` + CORS guidance; `Dockerfile` `VITE_API_URL` ARG + CRLF guard;
root `vercel.json` removed (use `frontend/` Root Directory) + `frontend/vercel.json` → `npm ci`;
`vite.config.ts` `host:true` + preview; `capacitor.config.ts` production-hardened;
`install.sh`/`install.ps1` version checks + Termux/winget guidance + secret auto-gen +
self-healing retries; `Makefile` image name + Windows note; `scripts/dev.sh` `$TMPDIR` run dir;
`.github/workflows/ci.yml` (pytest/ruff/typecheck/build/gitleaks) +
` sandbox-runner.yml` synced to `rawal-*` backend contract; `frontend/package.json`
fixed `build`/`lint` scripts + `engines` + `npx cap`.

**Docs:** new `docs/README.md` index, `quickstart.md`, `installation.md`,
`npm-registry.md`, `render-vercel-checklist.md`, `agent-guide.md`,
`api-reference.md`, `faq.md`, `CHANGELOG.md` (this file); professional README rewrite.

**No predefined data shipped:** no `.env`, no `data/`, no `*.db`; all provider/token
examples are `YOUR_*`/`example.com` placeholders. Historical weak dev secrets quoted
in the archived audit are not live (config defaults are empty + prod-validated).

## 1.0.0 — Private workspace (pre-open-source)

Internal autonomous workspace: agent runtime, sandbox backends, providers/MCP,
PWA + Capacitor shell, Telegram control, Docker/Render/Vercel blueprints.
