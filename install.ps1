# rawal-ai-agent — one-click installer for Windows PowerShell 5.1+.
# SPDX-License-Identifier: MIT
# Usage:  Set-ExecutionPolicy -Scope Process Bypass; .\install.ps1 [-Dev]
param([switch]$Dev)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Require-Version($cmd, $min, $name) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if (-not $c) { throw "$name is required. Install it, then re-run .\install.ps1`n - winget: winget install Python.Python.3.12 OpenJS.NodeJS Git.Git" }
  $v = & $cmd --version 2>&1 | Select-Object -First 1
  Write-Host "Found ${cmd}: $v"
}
Require-Version 'python' '3.11' 'Python 3.11+'
Require-Version 'node' '20' 'Node.js 20+'
Require-Version 'npm' '' 'npm'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required. Install via: winget install Git.Git' }

$VenvPy = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $VenvPy)) {
  Write-Host '→ creating backend\.venv ...'
  python -m venv backend/.venv
}
& $VenvPy -m pip install --upgrade pip
Write-Host '→ installing backend requirements ...'
try {
  & $VenvPy -m pip install -r backend/requirements.txt
} catch {
  Write-Host '  pip retry with --no-cache-dir ...'
  & $VenvPy -m pip install --no-cache-dir -r backend/requirements.txt
}
if ($Dev) {
  try { & $VenvPy -m pip install -r backend/requirements-dev.txt } catch { Write-Host '  (dev extras skipped — continuing)' }
}

Write-Host '→ installing frontend dependencies ...'
try {
  npm --prefix frontend install --no-audit --no-fund
} catch {
  Write-Host '  npm retry with --legacy-peer-deps ...'
  try {
    npm --prefix frontend install --no-audit --no-fund --legacy-peer-deps
  } catch {
    npm cache clean --force
    npm --prefix frontend install --no-audit --no-fund --legacy-peer-deps
  }
}

if (-not (Test-Path backend/.env)) {
  Copy-Item backend/.env.example backend/.env
  try {
    $s1 = python -c 'import secrets; print(secrets.token_urlsafe(48))'
    $s2 = python -c 'import secrets; print(secrets.token_urlsafe(48))'
    $env = Get-Content backend/.env -Raw
    $env = $env -replace '(?m)^SECRET_KEY=.*', "SECRET_KEY=$s1"
    $env = $env -replace '(?m)^JWT_SECRET=.*', "JWT_SECRET=$s2"
    Set-Content backend/.env $env -NoNewline
    Write-Host 'Generated SECRET_KEY/JWT_SECRET in backend\.env'
  } catch { Write-Host 'Could not auto-generate secrets — set SECRET_KEY/JWT_SECRET manually.' }
  Write-Host 'Created backend/.env — add DEFAULT_LLM_API_KEY before starting.'
}

Write-Host ''
Write-Host 'Dependencies installed.'
Write-Host 'Start backend:  backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000  (run from backend\)'
Write-Host 'Start frontend: npm --prefix frontend run dev   (second terminal)'
Write-Host 'Or with Docker: docker compose up --build'
Write-Host 'Web UI: http://localhost:5173 | API docs: http://localhost:8000/api/docs'
Write-Host 'rawal-ai-agent ready.'
