# MEMORY.md — Long-Term Memory

Keep this tight. Details belong in project docs, not here.

## Ian
- Technical, knows Python, no prior trading experience but learns fast
- Asks the right skeptical questions — will catch my BS before I do
- Timezone: EST
- **Return target: minimum 300% annualized per trade** — this is the bar
- **Ask him for things** — API keys, paid services, website access. Don't assume I can't have it.

## Active Project: Prediction Market Trading (started 2026-02-19)
- **Platform**: Kalshi ($50 funded, live trading). Polymarket pending (need Simmer wallet).
- **Strategy**: Weather markets on Kalshi — automated forecasting vs crowd pricing
- **Project docs**: `polymarket/README.md` (architecture), `polymarket/LEARNINGS.md` (API gotchas)
- **Research docs**: `polymarket/STRATEGY_IDEAS.md`, `polymarket/SKILLS.md`, `polymarket/EDGE_ASSESSMENT.md`

## Live Trades (as of 2026-02-24 ~9 PM ET)
- **$12 in guaranteed losses** (IDs 76-79): MIA T61 YES ×2 + BOS T30 YES ×2 — strike_type direction bug + duplicate from ET re-run — settle Feb 25 9 AM
- 20 NO bias trades (kalshi_no_bias) — all Trump SotU mention markets, resolve March 2
- Philly B33.5 YES paper trade @ 1¢ — obs_trader calibration; settles Feb 25 9 AM
- PT live run in background; LAX + SEA still polling (~8:30 PM ET, both cities unconfirmed)
- DB: polymarket/paper_trades/paper_trades.db
- Full accountability report: `polymarket/ACCOUNTABILITY_2026-02-24.md`

## Key Architecture (updated 2026-02-25, afternoon)
- **forecast_logger.py**: NWS + TWC + Foreca + 16 OM models + 4 ensembles (GFS/ECMWF/ICON/GEM) for all 19 cities
- **trading_utils.py**: Shared market scan utils (KALSHI_SERIES, fetch/orderbook/fill/parse, forecast loading) — import from here
- **ensemble_trader.py**: Runs at X:30, best-edge-per-city, $25 max. Imports from trading_utils
- **position_updater.py**: Runs at X:30 + 11:30am, model=ensemble_with_updates — same entries as ensemble_trader but exits early on forecast flip (shift >20pp + neg edge); A/B vs ensemble_trader
- **cli_strategy/trader.py**: CLI confirmed-high strategy. Live: com.trady.cli-trader-{et,ct,mt,pt} (no --paper). Paper mirror: com.trady.cli-paper-{et,ct,mt,pt}. First live run 4pm ET Feb 24.
- **obs_exit_monitor.py**: Continuous daemon (KeepAlive launchctl). Polls ASOS every 5min, KNYC every 60min. Hard-exits NO-on-greater when min_lower_f > floor_strike, YES-on-between when min_lower_f > cap_strike. Only checks target_date == local today.
- **paper_trading/**: SQLite SDK with Kelly sizing, calibration tracking, Brier score
- **Kalshi series active**: boston/chicago/dc/houston/lasvegas/miami/minneapolis/okc/philly/sanantonio/sfo/seattle/austin

## CLI Calibration — Real P Values (as of 2026-02-24, 5-7 day sample)
- ⛔ SKIP (P < 85%): austin=83.3%, dc=80.0%, nyc=83.3%, sfo=83.3%
- ✅ Trade: remaining 15 cities @ 85-100%, capped 97%
- Method: compare 4pm preliminary CLI max vs overnight final CLI max
- Re-run calibrate.py in May when seasonal sample grows
- Houston: now uses HOU/KHOU (Hobby Airport) — skip_live removed ✅

## Active Project State (updated 2026-02-25 noon)
- `ensemble_gfs` balance = $0 (overextended from wrong OKC credit; 31 pending Feb 25-26 trades)
- Correct realized P&L: cli_confirmed -$12, ensemble_gfs +$194.36, nws_obs -$25, kalshi_no_bias -$92.76
- CLI trader runs 4 PM ET today; all agents clean; Pydantic SDK bug fixed (raw requests now)
- `CONFIDENCE_P = 0.975` global for all cities — no per-city skip enforced

## Lessons That Cost Money
1. **Kalshi Create Order accepts both `yes_price` and `no_price`.** Use `yes_price` for YES orders, `no_price` for NO orders. Market response `no_ask` = price to buy NO → pass as `no_price`. No conversion. (See LEARNINGS.md for full history of getting this wrong.)
2. **Timezone bugs are silent killers**. UTC midnight ≠ local midnight. Each city needs its own IANA timezone. Code runs fine, places orders, on WRONG data.
3. **When results look too good, verify against ground truth**. Wasted a full day on invalid temporal arb results. Reverted a correct fix TWICE in one day because I panicked.
4. **Verify API field meanings empirically** — don't trust field names (createdAt ≠ event start).
5. **Target boundary markets, not deep ITM**. For confirmed high of 66°F: trade T65 YES + T66 NO (slowest to reprice, most info asymmetry). NOT T61 YES (already obvious, priced quickly by bots). Ian: "you bought 29 or below when they've recorded 33." — markets far from the confirmed high have no info edge.
6. **OM gate**: Only trade if OM hourly forecast predicts today's peak occurred ≥45min before the CLI "VALID TODAY AS OF" time. Miami blocked correctly: OM peak at 4pm, still potentially rising.
7. **Be skeptical of 1¢ deals** (Ian, 2026-02-24). Weather markets are NOT private information. A 1¢ ask means the market almost certainly knows something we don't, or our direction is wrong, or it's fully priced in with no profit on the other side. Today: bought YES on `less` markets at 1¢ = guaranteed loss. The "edge" was an illusion.
8. **Full technical learnings**: `polymarket/LEARNINGS.md`
9. **Never use `pkill python3` during a live trading session.** The CT trader was silently killed at 5 PM ET on Feb 24 during debugging — cost us 5 potentially profitable CT trades (Dallas B72.5, Houston B69.5, NOLA B60.5, OKC B72.5, Minneapolis B37.5 all repriced to 100¢). Use targeted kills: `pkill -f "trader.py --tz ET"`.
10. **Obs monitor MUST be continuous — being first is everything.** Running obs checks 4x/day is wrong. When METAR confirms a position is dead, others see it too. Exit window is minutes to seconds. Daemon polls every 5 min (ASOS) / 60 min (KNYC). Ian: "Most trades must be made in minutes, sometimes in seconds."
11. **KNYC uses 0.1°C precision, NOT whole °C like ASOS.** c_to_possible_f() for ASOS (±0.5°C window) is wrong for KNYC — use ±0.05°C window. KNYC error is ±0.1°F (negligible for whole-degree thresholds). Don't assume all stations have the same rounding.
12. **Today's obs only apply to today's markets.** Filter by `target_date == local_today` before checking exit conditions — or you'll try to invalidate tomorrow's trades using today's temperatures.
13. **T-prefix markets are NOT all `greater` type.** KXHIGHTBOS-26FEB24-T30 has `strike_type=less` (YES if high < 30°F). Always read `strike_type` from the API response. `parse_market` in trading_utils is now protected with an explicit guard.
11. **Parallel city processing is non-negotiable for PT.** LAS → LAX (180-min timeout) → SFO → SEA sequential = SEA never runs. All cities must poll simultaneously via ThreadPoolExecutor.
12. **`question` field must not do double duty.** We used it for both human display and machine-readable settlement encoding (`between|floor=X|cap=Y`). The dashboard showed raw encoding. Fix: dedicated `strike_type`/`floor_strike`/`cap_strike` columns; `question` = Kalshi subtitle + date.
13. **Kalshi `subtitle` is the correct human-readable market name.** T71 = "72° or above" (not "High >71°F"). Always pull from the market API `subtitle` field.
14. **NO trade `entry_p` must be `1 - yes_ask`, not `yes_ask`.** `market_price` always stores the YES ask. For NO trades with no fill_price, using market_price gives wildly wrong P&L (e.g., +$202 instead of +$3 for OKC T75 NO trade at 11¢).
15. **`_credit()` must use `pnl`, not the gross credit amount.** Using credit (dollar_size + pnl) for realized_pnl means losses show $0 and wins are overstated by dollar_size. Cascading effect: inflated bankroll allowed model to over-trade.
16. **Between market with METAR at boundary will hit LCD drift.** Philly: METAR showed max possible [33,34]°F, triggered between-YES signal. Kalshi LCD settled at 35°F (+1°F drift). Always require strictly inside range (`max_lower > floor AND max_upper < cap`), not at edges.
17. **Kalshi Pydantic SDK silently drops cities.** `market_api.get_markets()` raises ValidationError when any market has `category=null` or `risk_limit_cents=null`. DC, Atlanta, Philly-low were silently skipped. Fix: always use raw `requests.get()` for market discovery, not the typed SDK.
18. **Sentinel files** now written by cli trader to `forecast_logs/cli_sentinel_{tz}_{mode}.json` — heartbeat should check for `status: running` stuck past expected end time.

## What Doesn't Work
- Temporal arb: edge is real but bots price 5m markets in 30-60 seconds. Need VPS infra.
- Complement arb (gabagool): bots arb it away instantly.
- Sports line shopping: Vegas is sharp money too.

## What Might Work (not yet built)
- Mention markets (MentionHub + transcript analysis) — our sweet spot at small capital
- Netflix #1 weekly (Flick Patrol data) — modelable
- Count/activity markets (Poisson models) — TSA, tweet counts
- Resolution rules arbitrage — nobody reads the fine print
- See `polymarket/STRATEGY_IDEAS.md` for full list


## Browser Access
**Ask Ian immediately when browser is blocked** — don't silently route around it.
Say exactly: "Browser blocked — can you attach a Chrome tab to the OpenClaw extension?"
If he doesn't respond by the next heartbeat, continue without browser access.
