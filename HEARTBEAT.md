# HEARTBEAT.md


## Active Sub-Agents (check every heartbeat)
Run `sessions_list` with `activeMinutes=120`. For any active sub-agent:
- Is it still running or has it completed without announcing?
- If status shows it's done but no announcement came, check its transcript and report results

---

## 🚨 Push Migration (active until 10 AM EST — then remove this section)

**Until 3 AM EST:** Check `forecast_logs/wethr_push.jsonl` at every heartbeat:
- Are obs events flowing? Any stations silent?
- Do `new_high`/`new_low` events look correct? Are `[lo_f, hi_f]` ranges sensible?
- Any errors or reconnects in `forecast_logs/wethr_push_client.stdout.log`?
- Report to Ian if anything looks wrong

**At 3 AM EST exactly:** Execute `polymarket/docs/PUSH_MIGRATION_PLAN.md` steps 1–10.
Then run the test plan at the bottom. Report results to Ian.

**After 3 AM until 10 AM EST:** At every heartbeat verify:
- obs_cache populated by push (not old poller)?
- push_trigger updating? nws_obs_trader + obs_exit_monitor waking on it?
- Any trades fired? Fills at correct prices (not at limit ceiling)?
- Day-1 checklist: did `new_high` fire after `cli`? `six_hour_high` in obs payload?
- Errors in stdout logs?

Full plan: `polymarket/docs/PUSH_MIGRATION_PLAN.md`

## Weather Trading (every heartbeat)
1. Check `polymarket/forecast_logs/` for recent entries and errors
2. Check paper trades DB for any newly settled trades
3. Check launchctl agents for errors: `launchctl list | grep trady`
4. If any trades resolved (status != pending), update Ian with P&L
5. **NBM trader** (new 2026-02-27): check `forecast_logs/nbm_forecast_trader.stdout.log`
   - Requires forecast_logger to have run first (NBM data in forecasts.jsonl)
   - Model: truncated normal, σ=XND/1.28, P∈[10%,90%], edge≥8%, $3 max/trade

## Simmer (a few times per day)
If it's been a while since last Simmer check:
1. Health check: `GET /api/sdk/health` (no auth — verify API is reachable)
2. Call briefing: `GET /api/sdk/briefing?since=<last_check_timestamp>`
3. Check risk_alerts — any urgent warnings?
4. Review positions — exit helpers, expiring, significant moves, resolved
5. Check opportunities — high divergence, new markets
6. Update lastSimmerCheck timestamp in memory/heartbeat-state.json

## CLI Live Order Reconciliation (check after any CLI trader run window)
After 6:30 PM, 7:30 PM, 8:30 PM, or 10 PM ET — whenever a CLI tz group should have run:
```python
cd /Users/ian/.openclaw/workspace/polymarket && .venv/bin/python -c "
import sqlite3, requests
from kalshi_client import kalshi_auth_headers
from datetime import date

# Trades our DB thinks were placed live today
db = sqlite3.connect('paper_trades/paper_trades.db')
live_today = db.execute(\"\"\"
    SELECT ticker, direction, fill_price FROM trades
    WHERE model='cli_confirmed' AND date(entered_at)=? AND fill_status != 'assumed'
\"\"\", (str(date.today()),)).fetchall()
print('DB live trades today:', len(live_today))
for t in live_today: print(' ', t)

# What Kalshi actually shows
r = requests.get('https://api.elections.kalshi.com/trade-api/v2/portfolio/orders',
    params={'limit': 50}, headers=kalshi_auth_headers('GET', '/portfolio/orders'), timeout=10)
orders = r.json().get('orders', [])
kalshi_tickers = {o['ticker'] for o in orders if o.get('created_time','')[:10] == str(date.today())}
print('Kalshi orders today:', kalshi_tickers)

# Discrepancies
db_tickers = {t[0] for t in live_today}
missing = db_tickers - kalshi_tickers
if missing: print('⚠️  IN DB BUT NOT ON KALSHI:', missing)
else: print('✅ DB and Kalshi agree')
"
```
If any tickers are in DB but not on Kalshi → orders are silently failing → investigate immediately.

## Open-Meteo Rate Limit (check before 4 PM ET on trading days)
- Run: `curl -s "https://api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.97&hourly=temperature_2m&forecast_days=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'hourly' in d else d.get('reason','?'))"`
- If rate limited: OM gate will block ALL CLI trader cities — flag to Ian immediately
- Root cause if hit: check for hot-loop API calls or unexpected script runs

## CLI Confirmed-High Trader (monitor every heartbeat on trading days)
1. Check sentinel files for silent kills: `ls -la polymarket/forecast_logs/cli_sentinel_*.json`
   - Each file has "status": "running" | "done" | "error"
   - A sentinel stuck on "running" past its expected end time = process was killed
   - Live logs: `polymarket/forecast_logs/cli_trader_et.stdout.log` (and ct/mt/pt)
   - Paper logs: `polymarket/forecast_logs/cli_paper_et.stdout.log` (and ct/mt/pt)
2. Check stderr logs for Python errors
3. Verify paper P&L ≈ live P&L (should be nearly identical)
4. Report results to Ian after first settlement

Note: cli-trader-{et,ct,mt,pt} are NOW LIVE (no --paper flag).
      cli-paper-{et,ct,mt,pt} run in parallel with --paper for comparison.
      Sentinels written to: polymarket/forecast_logs/cli_sentinel_{tz}_{mode}.json
      Expected run windows: ET=4-6:30pm, CT=5-7:30pm, MT=6-8:30pm, PT=7-10pm (all ET)

## Morning Start-of-Day Check
At first heartbeat of the day (after 8 AM ET):
1. Daemon health: `launchctl list | grep trady` — flag any non-zero exit codes
2. Forecast log freshness: check mtime of `forecast_logs/forecasts.jsonl` — warn if >8h old
3. Log error scan: grep last 50 lines of `forecast_logs/ensemble_trader.stdout.log`, `nws_obs_trader.stdout.log`, `obs_exit_monitor.stdout.log` for Traceback/Error
4. DB summary: 7d P&L by model, any 0% win-rate bet types, stale pending trades (target_date < today)
5. Ash report: check `polymarket/reports/` for any `code_review_*.md` with open (🔲) findings not yet brought to Ian — bring these up in morning chat even if Ian doesn't ask

## Notes
- Paper trades settled by launchctl: `com.trady.trade-settler` (9 AM ET daily)
- Forecast logged by: `com.trady.forecast-logger` (6 AM/noon/6 PM/midnight ET)
- Ensemble trader: `com.trady.ensemble-trader` (6:30 AM/12:30 PM/6:30 PM/12:30 AM ET)
- Position updater: ~~`com.trady.position-updater`~~ **ARCHIVED 2026-03-01**
- DB: `polymarket/paper_trades/paper_trades.db`
- Logs: `polymarket/forecast_logs/forecasts.jsonl` and `cli_actuals.jsonl`
- First real paper trade results: Feb 25 9 AM settler run (trades target Feb 24)
