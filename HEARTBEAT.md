# HEARTBEAT.md

## Active Sub-Agents (check every heartbeat)
Run `sessions_list` with `activeMinutes=120`. For any active sub-agent:
- Is it still running or has it completed without announcing?
- If status shows it's done but no announcement came, check its transcript and report results

---

## Weather Trading (every heartbeat)
1. Check `trading/forecast_logs/` for recent entries and errors (dated files: `trader-YYYY-MM-DD.log`)
2. Check paper trades DB for any newly settled trades
3. Check orchestrator: `ps aux | grep orchestrator | grep -v grep`
4. If any trades resolved (status != pending), update Ian with P&L

### ⚠️ Obs date: always use ET date, never UTC
When checking `push_extremes` or any obs table, use the **ET date**:
```python
from zoneinfo import ZoneInfo
from datetime import datetime
ET = ZoneInfo("America/New_York")
date_str = datetime.now(ET).strftime("%Y-%m-%d")  # ✅ correct
# NOT: datetime.utcnow().strftime(...)            # ❌ wrong — UTC date ≠ ET date before 5 AM UTC
```
At 1 AM UTC, ET date is still "yesterday". Checking UTC date will always return 0 rows before midnight ET.

### ⚠️ Displacement prevention: NEVER open a new wethr SSE connection for monitoring
The wethr push client holds one persistent SSE connection per API key.
Opening a second connection (by running `wethr_push_client.py` or calling its `main()`) will
**displace the running daemon** — it loses its connection and takes 5–30s to reconnect, dropping events.
For heartbeat monitoring of obs data: **READ FROM DB ONLY**:
```python
import sqlite3
db = sqlite3.connect("/data/workspace/trading/paper_trades/paper_trades.db")
rows = db.execute("SELECT station, date_str, nws_high_f FROM push_extremes WHERE date_str=?", (date_str,)).fetchall()
```

## Fill Monitor Health (every heartbeat)
```bash
python3 - <<'EOF'
import json, time
from pathlib import Path
h = Path('/Users/ian/.openclaw/workspace/polymarket/forecast_logs/fill_monitor_health.json')
if not h.exists():
    print("❌ fill_monitor_health.json MISSING — fill monitor never wrote health file")
else:
    d = json.loads(h.read_text())
    age_min = (time.time() - time.mktime(__import__('datetime').datetime.fromisoformat(d['ts'].replace('Z','+00:00')).timetuple())) / 60
    print(f"Last sweep: {age_min:.0f} min ago | ok={d['sweep_ok']} | checked={d['n_checked']}")
    if age_min > 10:
        print("❌ STALE — fill monitor may be stuck or crashed")
EOF
```
- Also grep for ERROR lines: `grep ERROR polymarket/forecast_logs/paper_fill_monitor.stderr.log | tail -5`
- Any `FILL_MONITOR API FAILURE` lines = silent API breakage; investigate immediately

## Simmer (a few times per day)
If it's been a while since last Simmer check:
1. Health check: `GET /api/sdk/health` (no auth — verify API is reachable)
2. Call briefing: `GET /api/sdk/briefing?since=<last_check_timestamp>`
3. Check risk_alerts — any urgent warnings?
4. Review positions — exit helpers, expiring, significant moves, resolved
5. Check opportunities — high divergence, new markets
6. Update lastSimmerCheck timestamp in memory/heartbeat-state.json

## CLI Push Trigger (check every heartbeat on trading days)
- CLI trades are triggered by the wethr push daemon (`com.trady.cli-push-trigger`) — NOT scheduled launchd agents
- Scheduled cli-trader-{et,ct,mt,pt} and cli-paper-{et,ct,mt,pt} have been UNLOADED (2026-03-08)
- Just verify `com.trady.cli-push-trigger` is running (PID present in `launchctl list | grep trady`)

## Morning Start-of-Day Check
At first heartbeat of the day (after 8 AM ET):
1. Daemon health: `launchctl list | grep trady` — flag any non-zero exit codes
2. Forecast log freshness: check mtime of `forecast_logs/forecasts.jsonl` — warn if >8h old
3. Log error scan: grep **last 200 lines only** (not whole file) for Traceback/Error/NameError:
   - `tail -200 forecast_logs/wethr_push_client.stdout.log | grep -i "error\|traceback"` ← old errors persist in file
   - (do NOT grep the whole wethr log — it contains pre-fix errors from March 3 that are no longer relevant)
   - `forecast_logs/cli_push_trigger.stdout.log`
   - `forecast_logs/twc_morning_trader.stdout.log`
   - `forecast_logs/between_bucket_trader.stdout.log`
   - NOTE: `nws_obs_trader.stdout.log` is STALE — daemon unloaded, do NOT check
4. DB summary: 7d P&L by model, any 0% win-rate bet types, stale pending trades (target_date < today)
5. ALL_MODELS audit (weekly): models in DB with non-rejected trades that are NOT in ALL_MODELS → they'll never settle
   ```bash
   cd polymarket && .venv/bin/python -c "
   import sqlite3; from paper_trading.db import ALL_MODELS
   db = sqlite3.connect('paper_trades/paper_trades.db'); in_all = set(ALL_MODELS)
   missing = [r[0] for r in db.execute(\"SELECT DISTINCT model FROM trades WHERE fill_status NOT IN ('rejected','cancelled','voided') AND model IS NOT NULL\").fetchall() if r[0] not in in_all]
   print('Missing from ALL_MODELS:', missing or 'none ✅')
   "
   ```
5. Ash report: check `polymarket/reports/` for any `code_review_*.md` with open (🔲) findings not yet brought to Ian — bring these up in morning chat even if Ian doesn't ask

## Between Bucket Trader (check every heartbeat)
- `com.trady.between-bucket-trader` — runs daily at 17:00 UTC (noon LST)
- Posts 6¢ GTD YES limits on HIGH between-markets for tomorrow, OM/TWC ±3°F gate
- **stdout log**: `polymarket/forecast_logs/between_bucket_trader.stdout.log`
- **stderr log**: `polymarket/forecast_logs/between_bucket_trader.stderr.log`
- Check that it ran today: `grep "Done —" polymarket/forecast_logs/between_bucket_trader.stdout.log | tail -1`
- Expect ~50 orders placed per day; warn if 0 or Traceback in stderr
- Unfilled limits expire at midnight LST with P&L=0 (not losses) — settler handles this
- Watch for fills in DB: `SELECT ticker, fill_status, fill_price FROM trades WHERE model='between_bucket' AND fill_status='deferred' ORDER BY id DESC LIMIT 10`

## end_of_day trader (check every heartbeat during evening hours)
- `com.trady.end-of-day-trader` — runs every 30 min via StartInterval=1800
- Activates per city in the last 5h before LST midnight (7pm–midnight LST)
- Signal 1: NO trades on LESS/GREATER/BETWEEN when temp confirmed outside bucket
- Signal 2: YES trades on BETWEEN when CLI confirms the bucket and temp is locked
- Log: `forecast_logs/end_of_day_trader.stdout.log`
- Check: `launchctl list | grep end-of-day` — should show PID during window hours
- Watch for penny_blocks: `tail forecast_logs/penny_blocks.jsonl` (markets with ask ≤ 1¢)

## obs_peak_model + obs_peak_gate (check every heartbeat)
- `com.trady.obs-peak-model` — runs every 30 min + on push events (new_high, cli_high, observation)
- `com.trady.obs-peak-gate` — same schedule; independent hardcoded rule gate
- Log files: `forecast_logs/obs_peak_model_trader.stdout.log`, `forecast_logs/obs_peak_gate_trader.stdout.log`
- Check for errors; confirm both appear in `launchctl list | grep trady`

## Notes
- Paper trades settled by launchctl: `com.trady.trade-settler` (9 AM ET daily)
- Forecast logged by: `com.trady.forecast-logger` (6 AM/noon/6 PM/midnight ET)
- Ensemble trader: `com.trady.ensemble-trader` (6:30 AM/12:30 PM/6:30 PM/12:30 AM ET)
- Position updater: ~~`com.trady.position-updater`~~ **ARCHIVED 2026-03-01**
- DB: `polymarket/paper_trades/paper_trades.db`
- Logs: `polymarket/forecast_logs/forecasts.jsonl` and `cli_actuals.jsonl`
- First real paper trade results: Feb 25 9 AM settler run (trades target Feb 24)

## TODO: Recalibrate twc_bucket_low p-table ~2026-04-07
City-specific p-values set 2026-03-14 on only 17 days of March data.
Run `calibrate_twc_bucket_low.py` (or equivalent) after 3+ more weeks of D-1 evening data.
Current values: miami=0.80, chicago=0.80, lax=0.65, nyc=0.50, denver=0.35, austin=0.35

## TODO: Rerun α calibration ~2026-03-27
Run `twc_calibration.py` (or whichever calibration script) after 2 more weeks of trades.
Current α=0.8 is empirically derived; recheck after more data accumulates.
