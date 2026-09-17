#!/usr/bin/env bash
# rawal-ai-agent — one-click installer for Linux, macOS and Termux (Android).
# SPDX-License-Identifier: MIT
# Usage:  bash install.sh [--dev]
# Re-runnable and self-healing: failed pip/npm steps are retried with
# fallbacks (legacy-peer-deps, cache clean) instead of aborting.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

IS_TERMUX=0
[[ -n "${PREFIX:-}" && -d "/data/data/com.termux" ]] && IS_TERMUX=1
WITH_DEV=0
[[ "${1:-}" == "--dev" ]] && WITH_DEV=1
SKIP_DOCKER="${RAWAL_SKIP_DOCKER:-${BHATI_SKIP_DOCKER:-0}}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    if [[ $IS_TERMUX -eq 1 ]]; then
      echo "Termux: run 'pkg install python nodejs git' then re-run bash install.sh" >&2
    elif [[ "$(uname -s)" == "Darwin" ]]; then
      echo "macOS: run 'brew install python@3.12 node git' then re-run bash install.sh" >&2
    else
      echo "Linux: install Python 3.11+, Node.js 20+ and git from your package manager," >&2
      echo "  e.g. 'sudo apt install python3 python3-venv nodejs npm git'" >&2
    fi
    exit 1
  }
}

ver_ge() { # ver_ge HAVE NEED  →  0 when HAVE >= NEED
  python3 -c "import sys; h=list(map(int,'$1'.split('.'))); n=list(map(int,'$2'.split('.'))); L=max(len(h),len(n)); h+= [0]*(L-len(h)); n+=[0]*(L-len(n)); sys.exit(0 if h>=n else 1)"
}

need python3; need node; need npm; need git
[[ $WITH_DEV -eq 1 ]] && need make || true

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
ver_ge "$PY_VER" "3.11.0" || { echo "Python 3.11+ is required (found $PY_VER)." >&2; exit 1; }
NODE_VER="$(node -p 'process.versions.node')"
ver_ge "$NODE_VER" "20.0.0" || { echo "Node.js 20+ is required (found $NODE_VER)." >&2; exit 1; }

if [[ $IS_TERMUX -eq 1 ]]; then
  echo "Termux detected — using local sandbox (Docker is unavailable on Android)."
  SKIP_DOCKER=1
  # Termux venvs often lack ensurepip wheels; prefer system pip when needed.
  export PIP_BREAK_SYSTEM_PACKAGES="${PIP_BREAK_SYSTEM_PACKAGES:-1}"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ ! -x backend/.venv/bin/python ]]; then
  echo "→ creating backend/.venv ..."
  "$PYTHON_BIN" -m venv backend/.venv || python3 -m venv --without-pip backend/.venv
fi
backend/.venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1 || python3 -m pip install --upgrade pip >/dev/null 2>&1 || true

echo "→ installing backend requirements ..."
if ! backend/.venv/bin/pip install -q -r backend/requirements.txt; then
  echo "  pip retry with --no-cache-dir ..."
  backend/.venv/bin/pip install -q --no-cache-dir -r backend/requirements.txt || {
    echo "Backend install failed. Check your network, then re-run bash install.sh" >&2; exit 1;
  }
fi
if [[ $WITH_DEV -eq 1 ]]; then
  backend/.venv/bin/pip install -q -r backend/requirements-dev.txt || echo "  (dev extras skipped — continuing)"
fi

echo "→ installing frontend dependencies ..."
if ! npm --prefix frontend ci --no-audit --no-fund 2>/dev/null; then
  npm --prefix frontend install --no-audit --no-fund || {
    echo "  npm retry with --legacy-peer-deps ..."
    npm --prefix frontend install --no-audit --no-fund --legacy-peer-deps || {
      echo "  npm cache clean + retry ..."
      npm cache clean --force >/dev/null 2>&1 || true
      npm --prefix frontend install --no-audit --no-fund --legacy-peer-deps || {
        echo "Frontend install failed. Re-run bash install.sh (it resumes safely)." >&2; exit 1;
      }
    }
  }
fi

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  # Generate signing secrets automatically so a fresh checkout boots safely.
  if command -v python3 >/dev/null 2>&1; then
    S1="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    S2="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    # Portable in-place secret injection (macOS/BSD + GNU sed).
    if sed --version >/dev/null 2>&1; then SED_I=(sed -i); else SED_I=(sed -i ''); fi
    "${SED_I[@]}" "s/^SECRET_KEY=.*/SECRET_KEY=$S1/" backend/.env
    "${SED_I[@]}" "s/^JWT_SECRET=.*/JWT_SECRET=$S2/" backend/.env
    echo "Generated SECRET_KEY/JWT_SECRET in backend/.env"
  fi
  echo "Created backend/.env — add DEFAULT_LLM_API_KEY before starting."
fi

if command -v docker >/dev/null 2>&1 && [[ "$SKIP_DOCKER" != "1" ]] && docker info >/dev/null 2>&1; then
  echo "Dependencies installed. Start with: docker compose up --build"
else
  echo "Dependencies installed. Start with: make dev   (or: npm run dev)"
fi

echo "Web UI: http://localhost:5173 | API docs: http://localhost:8000/api/docs"
echo "rawal-ai-agent ready."
