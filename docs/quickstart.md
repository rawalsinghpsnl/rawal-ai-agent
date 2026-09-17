# Quickstart — rawal-ai-agent in 5 minutes

Pick **one** path. No testing/installing happens on anyone else's machine —
everything below runs on yours.

## Option A — Docker (simplest complete stack)

Requirements: Docker Desktop / Engine + Git.

```bash
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
cp backend/.env.example backend/.env
# Edit backend/.env → set DEFAULT_LLM_API_KEY (and SECRET_KEY/JWT_SECRET for prod)
docker compose up --build
```

Open `http://localhost:8000` (API + built frontend, one origin).
Health: `curl http://localhost:8000/api/v1/health`.

## Option B — npm one-click (no git needed)

```bash
npx rawal-ai-agent --mode local --dir rawal-ai-agent
cd rawal-ai-agent
# Edit backend/.env → set DEFAULT_LLM_API_KEY
make dev   # Windows: see install.ps1 output for the two commands
```

Web: `http://localhost:5173` · API docs: `http://localhost:8000/api/docs`.

## Option C — Local manual

Linux / macOS / Termux:

```bash
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
bash install.sh
# backend/.env → DEFAULT_LLM_API_KEY
make dev
```

Windows PowerShell:

```powershell
git clone https://github.com/rawalsinghpsnl/rawal-ai-agent.git
cd rawal-ai-agent
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
# backend\.env → DEFAULT_LLM_API_KEY, then run the two printed commands
```

## First agent run

1. Open the web UI → create a **Project** → new **Thread**.
2. Settings → Models → confirm provider (or rely on `DEFAULT_LLM_*` env).
3. Send a message in **Agent** mode. Use **Plan** first for destructive tasks,
   **ask** permissions on shared/prod work. See [agent-guide.md](agent-guide.md).

## Next steps

- Production: [deployment.md](deployment.md) + [render-vercel-checklist.md](render-vercel-checklist.md)
- All env vars: [configuration.md](configuration.md)
- Stuck? [troubleshooting.md](troubleshooting.md) + [faq.md](faq.md)
