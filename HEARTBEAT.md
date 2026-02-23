# HEARTBEAT.md

## Weather Trading (every heartbeat)
1. Check `logs/frontrunner.log` and `logs/forecast.log` for errors
2. Run `python3 polymarket/weather_trader.py status` — any resolved trades? P&L update?
3. Check Kalshi balance and open positions
4. If any trades resolved, update Ian with results

## Complex Model (once daily, afternoon)
1. Run `python3 polymarket/weather_complex.py accuracy` — enough data yet?
2. If accuracy report has resolved days, summarize model rankings for Ian

## Simmer (a few times per day)
If it's been a while since last Simmer check:
1. Health check: `GET /api/sdk/health` (no auth — verify API is reachable)
2. Call briefing: `GET /api/sdk/briefing?since=<last_check_timestamp>`
3. Check risk_alerts — any urgent warnings?
4. Review positions — exit helpers, expiring, significant moves, resolved
5. Check opportunities — high divergence, new markets
6. Update lastSimmerCheck timestamp in memory/heartbeat-state.json
