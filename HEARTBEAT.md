# HEARTBEAT.md

## Weather Trading (every heartbeat)
1. Check `polymarket/forecast_logs/` for recent entries and errors
2. Check paper trades DB for any newly settled trades
3. Check launchctl agents for errors: `launchctl list | grep trady`
4. If any trades resolved (status != pending), update Ian with P&L

## Simmer (a few times per day)
If it's been a while since last Simmer check:
1. Health check: `GET /api/sdk/health` (no auth — verify API is reachable)
2. Call briefing: `GET /api/sdk/briefing?since=<last_check_timestamp>`
3. Check risk_alerts — any urgent warnings?
4. Review positions — exit helpers, expiring, significant moves, resolved
5. Check opportunities — high divergence, new markets
6. Update lastSimmerCheck timestamp in memory/heartbeat-state.json

## CLI Confirmed-High Trader (one-time validation task)
This task auto-expires once done. Remove after completion.

First run fires at 4pm ET today (Feb 24). After that, count 8 heartbeats, then:
1. Check `polymarket/forecast_logs/cli_trader_et.stdout.log` (and ct/mt/pt)
2. Check `polymarket/forecast_logs/cli_trader_errors.jsonl` for any errors
3. Check `polymarket/forecast_logs/cli_trader_YYYYMMDD.jsonl` for trade signals/results
4. Fix any errors found
5. Once logs look clean: notify Ian and ask to approve switching from --paper to LIVE
   (remove --paper from plists com.trady.cli-trader-{et,ct,mt,pt}, reload launchctl)
6. After live is approved and running: add a parallel paper version
   (duplicate all 4 plists as com.trady.cli-paper-{et,ct,mt,pt} with --paper flag,
   same schedule, so we can compare live vs paper results)
7. Remove this section from HEARTBEAT.md

Note: agents currently run with --paper flag. DO NOT switch to live without Ian's approval.
Houston is flagged skip_live=True (station verification pending — KIAH vs KHOU).

## Notes
- Paper trades settled by launchctl: `com.trady.trade-settler` (9 AM ET daily)
- Forecast logged by: `com.trady.forecast-logger` (6 AM/noon/6 PM/midnight ET)
- Ensemble trader: `com.trady.ensemble-trader` (6:30 AM/12:30 PM/6:30 PM/12:30 AM ET)
- Intraday ensemble: `com.trady.intraday-ensemble-trader` (6:32 AM/12:32 PM/6:32 PM/12:32 AM ET)
- DB: `polymarket/paper_trades/paper_trades.db`
- Logs: `polymarket/forecast_logs/forecasts.jsonl` and `cli_actuals.jsonl`
- First real paper trade results: Feb 25 9 AM settler run (trades target Feb 24)
