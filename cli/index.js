#!/usr/bin/env node
/**
 * rawal-ai-agent — one-click installer (npm).
 * SPDX-License-Identifier: MIT
 * Copyright (c) rawal-ai-agent contributors.
 *
 *   npx rawal-ai-agent                 # docker mode (default)
 *   npx rawal-ai-agent --mode local    # local Python venv + npm (Windows/macOS/Linux/Termux)
 *   npm i -g rawal-ai-agent && rawal-ai-agent --mode local --dir rawal-ai-agent
 *
 * Self-healing: missing prerequisites are reported with the exact fix command;
 * failed clones/installs are retried (shallow → full, ci → install →
 * legacy-peer-deps); existing checkouts are updated with `git pull --ff-only`.
 * Public repos need NO token. Private repos optionally accept
 * RAWAL_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN from the environment only
 * (never as a CLI flag, never written to disk, redacted from logs).
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform } from "node:os";

const args = process.argv.slice(2);
const has = (flag) => args.includes(flag);
const value = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith("--") ? args[i + 1] : fallback;
};

const DEFAULT_REPO = "https://github.com/rawalsinghpsnl/rawal-ai-agent.git";
const repo = value("--repo", process.env.RAWAL_REPO || DEFAULT_REPO);
const target = resolve(value("--dir", "rawal-ai-agent"));
const mode = value("--mode", "docker");
const branch = value("--branch", "");
const yes = has("--yes") || has("-y");
const token =
  process.env.RAWAL_GITHUB_TOKEN || process.env.GH_TOKEN || process.env.GITHUB_TOKEN || "";
const isWin = platform() === "win32";
const isTermux =
  !!process.env.PREFIX && process.env.PREFIX.includes("com.termux");

function log(msg) {
  console.log(msg);
}
function warn(msg) {
  console.warn(`⚠ ${msg}`);
}
function fail(msg, code = 1) {
  console.error(`\n✖ ${msg}`);
  process.exit(code);
}

function redact(list) {
  return list.map((a) =>
    typeof a === "string" && a.includes("Authorization: Bearer")
      ? "http.extraheader=Authorization: Bearer [REDACTED]"
      : a,
  );
}

function tryRun(command, commandArgs, cwd = process.cwd()) {
  log(`\n$ ${command} ${redact(commandArgs).join(" ")}`);
  try {
    execFileSync(command, commandArgs, { cwd, stdio: "inherit" });
    return true;
  } catch {
    return false;
  }
}

function mustRun(command, commandArgs, cwd = process.cwd(), hint = "") {
  if (!tryRun(command, commandArgs, cwd)) {
    if (hint) console.error(`\nHint: ${hint}`);
    fail(`Command failed: ${command} ${redact(commandArgs).join(" ")}`);
  }
}

function hasCmd(cmd) {
  try {
    const probe = isWin ? ["where", [cmd]] : ["sh", ["-c", `command -v ${cmd}`]];
    execFileSync(probe[0], probe[1], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function checkPrereqs() {
  const missing = [];
  if (!hasCmd("git")) missing.push("git");
  if (mode === "local") {
    if (!hasCmd("python") && !hasCmd("python3")) missing.push("python (3.11+)");
    if (!hasCmd("node")) missing.push("node (20+)");
    if (!hasCmd("npm")) missing.push("npm");
  }
  if (mode === "docker" && !hasCmd("docker")) {
    warn("Docker not found — falling back to --mode local steps.");
    return "local";
  }
  if (missing.length) {
    console.error(`\nMissing prerequisites: ${missing.join(", ")}`);
    if (isTermux) console.error("Termux: pkg install python nodejs git");
    else if (isWin)
      console.error("Windows: winget install Python.Python.3.12 OpenJS.NodeJS Git.Git");
    else console.error("Install Python 3.11+, Node.js 20+, git, then re-run.");
    process.exit(1);
  }
  return mode;
}

function gitArgs(base) {
  // Token only via env, only for private repos, never logged.
  if (token) return ["-c", `http.extraheader=Authorization: Bearer ${token}`, ...base];
  return base;
}

function cloneOrUpdate() {
  if (existsSync(join(target, ".git"))) {
    log(`\n→ updating existing checkout at ${target}`);
    if (!tryRun("git", gitArgs(["pull", "--ff-only"]), target)) {
      warn("git pull failed — continuing with existing files.");
    }
    return;
  }
  mkdirSync(resolve(target, ".."), { recursive: true });
  const cloneBase = branch
    ? ["clone", "--branch", branch, repo, target]
    : ["clone", repo, target];
  log(`\n→ cloning ${repo}`);
  // Shallow first (fast), fall back to full clone.
  if (!tryRun("git", gitArgs(["clone", "--depth", "1", ...(branch ? ["--branch", branch] : []), repo, target]))) {
    warn("Shallow clone failed — retrying full clone ...");
    mustRun("git", gitArgs(cloneBase), process.cwd(), "Check the --repo URL and your network.");
  }
}

function runLocalInstaller() {
  if (isTermux) log("\n→ Termux detected: Docker unavailable, using local mode.");
  if (isWin) {
    mustRun(
      "powershell",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "install.ps1"],
      target,
      "Run: Set-ExecutionPolicy -Scope Process Bypass; .\\install.ps1",
    );
  } else {
    mustRun("bash", ["install.sh"], target, "Run: bash install.sh");
  }
  log("\n✓ rawal-ai-agent installed (local).");
  log("  1. Edit backend/.env → set DEFAULT_LLM_API_KEY");
  log("  2. Start:  make dev   (Linux/macOS)  or  see install.ps1 output (Windows)");
  log("  Web UI: http://localhost:5173 | API: http://localhost:8000/api/docs");
}

function runDocker() {
  if (isTermux) {
    warn("Termux has no Docker daemon — switching to local install.");
    return runLocalInstaller();
  }
  if (!tryRun("docker", ["info"])) {
    warn("Docker daemon not running — switching to local install.");
    return runLocalInstaller();
  }
  mustRun(
    "docker",
    ["compose", "up", "--build", "-d"],
    target,
    "Start Docker Desktop, then re-run.",
  );
  log("\n✓ rawal-ai-agent is running at http://localhost:8000");
  log("  Logs: docker compose logs -f app   |   Stop: docker compose down");
}

if (has("--help") || has("-h")) {
  console.log(`rawal-ai-agent installer v2.0.1

Usage:
  npx rawal-ai-agent [options]
  npm i -g rawal-ai-agent && rawal-ai-agent [options]

Options:
  --dir <folder>    Installation folder (default: rawal-ai-agent)
  --mode docker     Build + start with Docker Compose (default)
  --mode local      Install venv + npm deps, print dev commands (Windows/Linux/macOS/Termux)
  --repo <url>      Repository URL override (default: public rawal-ai-agent repo)
  --branch <name>   Git branch/tag to clone
  --yes, -y         Non-interactive (assume defaults)
  --help, -h        Show this help

Examples:
  npx rawal-ai-agent --mode local --dir rawal-ai-agent
  rawal-ai-agent --mode docker --dir ./my-agent

No token needed for public installs. For private repos set RAWAL_GITHUB_TOKEN in the
environment (never on the command line).`);
  process.exit(0);
}

if (has("--version") || has("-v")) {
  console.log("rawal-ai-agent installer 2.0.1");
  process.exit(0);
}

if (!yes && repo.includes("YOUR_USERNAME")) {
  log(`\nNOTE: --repo still points at a template URL:\n  ${repo}`);
  log("Pass --repo <your-fork-url> or set RAWAL_REPO to override.");
  log("Continuing anyway ...");
}

const effectiveMode = checkPrereqs();
if (!["docker", "local"].includes(effectiveMode)) {
  fail(`Unknown mode: ${mode}. Use --mode docker or --mode local.`, 2);
}

cloneOrUpdate();
if (effectiveMode === "local") runLocalInstaller();
else runDocker();
