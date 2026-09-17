# FAQ — rawal-ai-agent

**What is rawal-ai-agent?**
Self-hosted autonomous AI workspace: chat + projects + file editor + terminal +
browser + MCP/connectors + sandbox execution, with your keys staying on your infra.

**One command to install?**
`npx rawal-ai-agent --mode local --dir rawal-ai-agent` (or `--mode docker`).
See [installation.md](installation.md) + [npm-registry.md](npm-registry.md).

**Which LLM do I need?**
Any OpenAI-compatible (`DEFAULT_LLM_BASE_URL` + `DEFAULT_LLM_API_KEY` + `DEFAULT_LLM_MODEL`).
Anthropic-compatible + custom proxies supported; configure more in Settings → Models.

**Why `No model configured`?**
Set `DEFAULT_LLM_API_KEY`/`DEFAULT_LLM_MODEL` in `backend/.env` (or provider in UI).

**Docker or local?**
Docker = one origin + isolation (best local prod). Local processes = fastest dev.
Render = `local` sandbox (no daemon); use Docker locally for untrusted code.

**Render data disappears?**
Set `MONGO_URI`/`DATABASE_NAME` — Render Free filesystem is ephemeral.

**Vercel chat fails but local works?**
Check `VITE_API_URL` (no `/api/v1` suffix) + Render health + exact `CORS_ORIGINS`.

**How is this different from a chatbot?**
Runs are multi-step with tools, permissions, steering, artifacts, and sandbox
execution — not single replies. See [agent-guide.md](agent-guide.md).

**Is my data sent anywhere?**
Only to the LLM provider + integrations you configure. Self-host = you control it.

**Can someone steal credit for my fork?**
Keep `LICENSE` + `NOTICE`, use a distinct fork name (`x (based on rawal-ai-agent)`),
and report npm typosquats. Upstream identity: npm `rawal-ai-agent`, repo `rawal-ai-agent`.

**Where do I report bugs / vulnerabilities?**
Bugs → GitHub Issues. Vulnerabilities → private report only (see `SECURITY.md`).
