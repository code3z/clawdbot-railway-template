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

## Notes
- Paper trades settled by launchctl: `com.trady.trade-settler` (9 AM ET daily)
- Forecast logged by: `com.trady.forecast-logger` (6 AM/noon/6 PM/midnight ET)
- Ensemble trader: `com.trady.ensemble-trader` (6:30 AM/12:30 PM/6:30 PM/12:30 AM ET)
- DB: `polymarket/paper_trades/paper_trades.db`
- Logs: `polymarket/forecast_logs/forecasts.jsonl` and `cli_actuals.jsonl`
- First real paper trade results: Feb 25 9 AM settler run (trades target Feb 24)
