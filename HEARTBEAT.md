# HEARTBEAT.md

All paths relative to `/data/workspace/trading/`. Logs: `forecast_logs/{script}-YYYY-MM-DD.log`.

> ⚠️ **Heartbeats run in an isolated session.** Ian cannot see replies here. If something needs attention, send it to the trading channel: `<#1482107559333859610>`. Do not reply into the heartbeat session expecting Ian to see it.

---

## Active Sub-Agents (check every heartbeat)
Run `sessions_list` with `activeMinutes=120`. For any active sub-agent:
- Is it still running or has it completed without announcing?
- If done but no announcement came, check transcript and report results

---

## Weather Trading (every heartbeat)

### 1. Orchestrator + Daemons
```bash
ps aux | grep python | grep -v grep
```
Expected always-on: `orchestrator.py`, `wethr_push_client.py`, `cli_push_trigger.py`, `orderbook_scanner.py`, `fill_monitor.py`, `dashboard.py`

Flag anything missing.

### 2. Fill Monitor Health
```python
import json, time
from pathlib import Path
h = Path('/data/workspace/trading/forecast_logs/fill_monitor_health.json')
if not h.exists():
    print("❌ fill_monitor_health.json MISSING")
else:
    d = json.loads(h.read_text())
    from datetime import datetime, timezone
    ts = datetime.fromisoformat(d['ts'].replace('Z', '+00:00'))
    age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
    print(f"Last sweep: {age_min:.0f} min ago | ok={d['sweep_ok']} | checked={d['n_checked']}")
    if age_min > 10:
        print("❌ STALE — fill monitor may be stuck or crashed")
```
Check errors: `grep -i "API FAILURE\|ERROR" forecast_logs/fill_monitor-$(date +%Y-%m-%d).log | tail -5`

### 3. Recent Trades
Check paper trades DB for newly settled trades. If any resolved (status != pending), update Ian with P&L.

### 4. ⚠️ Obs date: always use ET date, never UTC
```python
from zoneinfo import ZoneInfo
from datetime import datetime
ET = ZoneInfo("America/New_York")
date_str = datetime.now(ET).strftime("%Y-%m-%d")  # ✅ correct
```
At 1 AM UTC, ET date is still "yesterday". UTC date will return 0 rows before midnight ET.

### 5. ⚠️ Never open a second wethr SSE connection
The wethr push client holds one persistent SSE connection. A second connection displaces the running daemon (drops events for 5–30s). Monitor obs data by **reading from DB only**:
```python
import sqlite3
db = sqlite3.connect("/data/workspace/trading/paper_trades/paper_trades.db")
rows = db.execute("SELECT station, date_str, nws_high_f FROM push_extremes WHERE date_str=?", (date_str,)).fetchall()
```

---

## Morning Start-of-Day Check
At first heartbeat after 8 AM ET:

**1. Daemon health:**
```bash
ps aux | grep python | grep -v grep
```
All 6 daemons should be present. Missing = investigate immediately.

**2. Forecast log freshness:**
```bash
ls -la /data/workspace/trading/forecast_logs/forecast_logger-$(date +%Y-%m-%d).log
```
Warn if missing or >8h old.

**3. Log error scan (last 200 lines only):**
```bash
LOG=/data/workspace/trading/forecast_logs
tail -200 $LOG/wethr_push_client-$(date +%Y-%m-%d).log | grep -i "error\|traceback"
tail -200 $LOG/cli_push_trigger-$(date +%Y-%m-%d).log | grep -i "error\|traceback"
tail -200 $LOG/twc_morning_trader-$(date +%Y-%m-%d).log | grep -i "error\|traceback"
```

**4. DB summary:** 7d P&L by model, any 0% win-rate bet types, stale pending trades (target_date < today)

**5. ALL_MODELS audit (weekly):** models in DB not in ALL_MODELS will never settle:
```bash
cd /data/workspace/trading && .venv/bin/python -c "
import sqlite3; from paper_trading.db import ALL_MODELS
db = sqlite3.connect('paper_trades/paper_trades.db'); in_all = set(ALL_MODELS)
missing = [r[0] for r in db.execute(\"SELECT DISTINCT model FROM trades WHERE fill_status NOT IN ('rejected','cancelled','voided') AND model IS NOT NULL\").fetchall() if r[0] not in in_all]
print('Missing from ALL_MODELS:', missing or 'none ✅')
"
```

**6. Ash report:** check `trading/reports/` for any `code_review_*.md` with open (🔲) findings — bring to Ian even if not asked.

---

## CLI Push Trigger (check every heartbeat on trading days)
Triggered by wethr push events — not scheduled.
```bash
ps aux | grep cli_push_trigger | grep -v grep   # should show PID
tail -20 /data/workspace/trading/forecast_logs/cli_push_trigger-$(date +%Y-%m-%d).log
grep "🟢 LIVE ORDER" /data/workspace/trading/forecast_logs/cli_push_*_live.log 2>/dev/null | tail -10
```

---

## Trader Log Quick-Check Template
```bash
LOG=/data/workspace/trading/forecast_logs
TODAY=$(date +%Y-%m-%d)
# Check any trader:
tail -20 $LOG/twc_morning_trader-$TODAY.log
tail -20 $LOG/between_bucket_trader-$TODAY.log
tail -20 $LOG/end_of_day_trader-$TODAY.log
tail -20 $LOG/obs_peak_model_trader-$TODAY.log
tail -20 $LOG/obs_peak_gate_trader-$TODAY.log
```

---

## TODOs

### Recalibrate twc_bucket_low p-table ~2026-04-07
City-specific p-values set 2026-03-14 on only 17 days of March data.
Run calibration script after 3+ more weeks of D-1 evening data.
Current values: miami=0.80, chicago=0.80, lax=0.65, nyc=0.50, denver=0.35, austin=0.35

### Rerun α calibration ~2026-03-27
Current α=0.8 is empirically derived. Recheck after more data.
