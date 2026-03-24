#!/bin/bash
# Bootstrap script — run automatically by the Railway wrapper on every startup.
# Starts the orchestrator, which owns all trading daemons via keep_alive().

set -e

# /data/bin is the persisted bun global bin dir (qmd lives here).
# Install qmd if missing (first boot or volume wipe); otherwise reuse cached binary + models.
export PATH="/data/bin:$PATH"
export BUN_INSTALL=/data
# Store qmd index + models in /data/qmd so they survive Railway deploys.
# qmd appends "qmd" to XDG_CACHE_HOME, so setting XDG_CACHE_HOME=/data puts index at /data/qmd.
export XDG_CACHE_HOME=/data
mkdir -p /data/qmd
if ! command -v qmd &>/dev/null; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] qmd not found — installing..." >> /data/orchestrator.log
  BUN=/data/npm/bin/bun
  $BUN install -g https://github.com/tobi/qmd --trust-all-dependencies >> /data/orchestrator.log 2>&1
  QMD_DIR=/data/install/global/node_modules/@tobilu/qmd
  # Install dev deps (typescript etc.) and build — bun global install skips devDependencies
  (cd "$QMD_DIR" && $BUN install --dev >> /data/orchestrator.log 2>&1 && $BUN run build >> /data/orchestrator.log 2>&1)
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] qmd installed and built." >> /data/orchestrator.log
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] qmd already present at $(command -v qmd), skipping install." >> /data/orchestrator.log
fi

# Refresh OpenClaw agent's qmd index on every startup.
# OpenClaw uses its own XDG paths (separate from the /data/qmd bootstrap db).
# Collections are memory-root-main, memory-dir-main, workspace-root-main, trading-main.
# Running update+embed here ensures new daily memory files are indexed after each deploy.
OC_QMD_CONFIG="/data/.openclaw/agents/main/qmd/xdg-config"
OC_QMD_CACHE="/data/.openclaw/agents/main/qmd/xdg-cache"
OC_CONFIG="/data/.openclaw/openclaw.json"
if [ -d "$OC_QMD_CONFIG" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] Refreshing OpenClaw qmd index..." >> /data/orchestrator.log
  XDG_CONFIG_HOME="$OC_QMD_CONFIG" XDG_CACHE_HOME="$OC_QMD_CACHE" qmd update >> /data/orchestrator.log 2>&1
  XDG_CONFIG_HOME="$OC_QMD_CONFIG" XDG_CACHE_HOME="$OC_QMD_CACHE" qmd embed >> /data/orchestrator.log 2>&1
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] qmd index refreshed." >> /data/orchestrator.log
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] OpenClaw qmd config not yet present — skipping index refresh (will be created by agent on first run)." >> /data/orchestrator.log
fi

# Ensure correct qmd search settings in openclaw.json (vsearch = fast vector, no 30s query expansion).
# Safe to run on every boot — only updates these two keys if the file exists.
if [ -f "$OC_CONFIG" ]; then
  python3 -c "
import json, sys
with open('$OC_CONFIG') as f:
    d = json.load(f)
q = d.setdefault('memory', {}).setdefault('qmd', {})
changed = []
if q.get('searchMode') != 'vsearch':
    q['searchMode'] = 'vsearch'
    changed.append('searchMode=vsearch')
lim = q.setdefault('limits', {})
if lim.get('timeoutMs') != 20000:
    lim['timeoutMs'] = 20000
    changed.append('timeoutMs=20000')
if changed:
    with open('$OC_CONFIG', 'w') as f:
        json.dump(d, f, indent=2)
    print('Updated:', ', '.join(changed))
else:
    print('Already correct, no changes.')
" >> /data/orchestrator.log 2>&1
fi

TRADING_DIR="/data/workspace/trading"
VENV="$TRADING_DIR/.venv/bin/python"
LOG="/data/orchestrator.log"

# Recreate the venv if it was wiped (e.g. volume reset or first boot).
if [ ! -x "$VENV" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] .venv missing — recreating from requirements.txt..." >> "$LOG"
  cd "$TRADING_DIR"
  python3 -m venv .venv >> "$LOG" 2>&1
  .venv/bin/pip install --upgrade pip >> "$LOG" 2>&1
  .venv/bin/pip install -r requirements.txt >> "$LOG" 2>&1
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] .venv recreated." >> "$LOG"
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] .venv present, skipping install." >> "$LOG"
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] Starting orchestrator (with crash-restart loop)..." >> "$LOG"

cd "$TRADING_DIR"
setsid nohup bash run_orchestrator.sh >> "$LOG" 2>&1 &

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [bootstrap] Orchestrator loop started (pid $!)" >> "$LOG"
