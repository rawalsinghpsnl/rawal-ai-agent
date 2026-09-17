#!/bin/sh
# rawal-ai-agent — start the agent API.
# Render exposes exactly one public port -> this service.
set -e

APP_PORT="${PORT:-8000}"

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 --port "$APP_PORT" --proxy-headers --no-server-header
