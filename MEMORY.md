# MEMORY.md — Long-Term Memory

Keep this tight. Details belong in project docs, not here.

---

## ✅ HIGH/LOW Symmetry Check — Do This Before Shipping Any Trading Logic

Whenever I write or modify logic that handles HIGH markets, **immediately ask**: does the LOW branch handle the same cases? And vice versa.

Strike types to check for both HIGH and LOW: `greater`, `less`, `between`.

Confirmed signals that must be handled for each:
- HIGH greater YES: `lo_f > floor`
- HIGH between NO:  `lo_f > cap`
- LOW less YES:     `hi_f <= cap`
- LOW greater NO:   `hi_f <= floor`
- LOW between NO:   `hi_f <= floor` (low confirmed below range floor) ← **this was missing and cost us real trades on 2026-03-04**

Before marking any trading logic done: read through both branches side by side and confirm every strike type is handled.

---

## 📈 Kalshi Is an Open Limit Order Book

Kalshi is NOT a market-maker model. There is no entity "pricing" markets.
- Participants post limit bids/asks in an open order book
- Trades fill when a buy order matches a resting sell order (or vice versa)
- If our buy order doesn't fill, it means there are no sellers at our price — the order rests
- "Market repriced" = other participants already bought up available sell orders, leaving none at our price
- Do NOT say "bots repriced the market" — say "available sell orders were swept before we arrived"

---

## ⏰ Timed Tasks: Use Cron, Not Heartbeat

If Ian asks me to do something "at 3 AM" or any specific time:
- **Use a cron job** (`openclaw cron add`) — don't rely on a heartbeat firing at the right time
- Heartbeats are ~30 min intervals and can be skipped, delayed, or aborted
- A missed heartbeat = a missed task. Cron fires exactly when scheduled.

**How to set a cron job:**
```
openclaw cron add --schedule "0 3 * * *" --message "Execute push migration per PUSH_MIGRATION_PLAN.md"
```
Or use the `sessions_spawn` approach for one-shot tasks at a specific time.

**Lesson (2026-03-03):** Ian asked me to run the wethr push migration at 3 AM. I put it in HEARTBEAT.md but didn't set a cron. The 3 AM heartbeat got aborted (26-line deleted session). The 4:25 AM heartbeat ran but I skimmed HEARTBEAT.md instead of reading the whole thing and said HEARTBEAT_OK. Task never ran. Read. The. Whole. File.

---

## 🔄 Re-use Sub-Agents — Don't Spawn Fresh When One Exists

When a sub-agent needs follow-up work or a fix:
1. Check if its session is still alive: `sessions_list`
2. If alive: use `sessions_send` to steer it — preserves context
3. Only spawn a new one if the original never ran, crashed with no output, or is from a different session tree (visibility=tree blocks it)

Spawning a fresh agent when the original exists wastes context and ignores prior work.

---

## 🔍 Use Your Full Toolbox — Don't Ask When You Can Look

When you're missing context (forgotten promises, prior decisions, what happened overnight):
1. **Check session transcripts first** — `sessions_list` to find recent sessions, then read the raw `.jsonl` at `/Users/ian/.openclaw/agents/main/sessions/<id>.jsonl`
2. **`sessions_history`** works too for structured access
3. **Completed sub-agents still respond** to `sessions_send` — their context is intact
4. The answer is almost always in the transcript. Don't ask Ian before looking.

This applies to: "what did I promise?", "what did the sub-agent find?", "what was that second idea?", any "do you remember?" question.

---

## 🔧 Fix Trivial Problems Immediately — Don't Wait for Ian

If something is broken and the fix is safe and obvious (missing package, crashed daemon, stale file, etc.) — **just fix it**. Don't flag it across three heartbeats while trading time ticks away. Ask yourself: "Would Ian expect me to have already fixed this?" If yes, fix it.

Examples of things to fix without asking:
- `pip install <missing_package>` when a daemon is crash-looping
- Restarting a crashed launchctl agent after fixing the root cause
- Cleaning up stale sentinel files

Only wait if the fix is destructive, expensive, or ambiguous.

---

## ⚠️ Read This First — Every Session, Every Context Compact, Every Heartbeat

**Re-read MEMORY.md and `polymarket/LEARNINGS.md` at the start of every session.
Re-read MEMORY.md at every context compact. If in doubt during a heartbeat, re-read it.**
Memory is shaky. Rules written down and not re-read are the same as rules not written down.

---

## 🌡️ Low Markets: The Asymmetry Rule (non-negotiable)

**The daily LOW can only go DOWN. The daily HIGH can only go UP. This changes everything.**

| | High (can only ↑) | Low (can only ↓) |
|---|---|---|
| Confirmed **above** threshold | ✅ monotonic, trade it | ❌ needs end-of-day |
| Confirmed **below** threshold | ❌ needs end-of-day | ✅ monotonic, trade it |

**For low markets, the only valid intraday confirmed signals are:**
- `greater NO`:  min_upper_f ≤ floor → low is already at/below floor → NO wins
- `between NO` (below range): min_upper_f ≤ floor → low already below range → NO wins
- `less YES`:    min_upper_f ≤ cap → low is already at/below cap → YES wins

**NEVER fire these for lows (they require end-of-day):**
- `greater YES` — "running min is 55°F so low > 54°F" → **WRONG**. It could drop to 45°F tonight.
- `less NO` — "running min is 60°F so low won't drop below 55°F" → **WRONG**. Same reason.
- `between NO` (above range) — same error.

**The failure mode that got caught (2026-03-03):**
Fired `KXLOWTLAX-26MAR03-T54 YES` because running min=55 > floor=54. This was completely
wrong — LAX's low hadn't been set yet. It could have dropped to 48°F overnight.
Caught before any live trade, but would have cost real money if live.

**The mental check:** For a low market signal, ask: "Could the temperature still drop below
this threshold tonight?" If yes → do not trade.

---

## ❌ Confirmed-Fast / obs_exit_monitor — Removed 2026-03-04

**Why it didn't work:**
- `handle_confirmed_fast` placed 99¢ resting limit orders on Kalshi when ASOS obs confirmed a threshold was crossed (e.g. running_max > cap → NO is guaranteed). Same logic applied in reverse via `obs_exit_monitor` (sell at 1¢ when position goes wrong).
- WetHR push stream has ~2 minute lag. Bots are already there. The resting limit order queue at 99¢ on any confirmed market routinely exceeds the daily volume of the market — we were just adding to a pile that never fills.
- Only 4 of ~10 confirmed-fast trades filled on the day we removed it.
- `obs_exit_monitor` exits (sell at 1¢) recovered cents at best, and caused losses when it fired incorrectly on stale obs (CHI −$25, PHX −$17, DAL −$16).

**What to try in the future (needs instant data):**
- Twilio ASOS phone-in: ASOS stations have a phone number you can call for the current reading. Near-instant, no API lag.
- A co-located bot with direct websocket to Kalshi + NWS ASOS feed.
- Until then: our edge is in MODELS (peak_passed, ensemble, trough), not in data speed.

**Files archived:** `obs_exit_monitor.py` → `polymarket/archive/`
**Plist unloaded:** `com.trady.obs-exit-monitor`
**Code removed from:** `nws_obs_trader.py` — `handle_confirmed_fast()`, `_session_traded_live`, `MAX_TRADE_PCT_CONFIRMED`, `MAX_ENTRY_CENTS`

---

## ⛔ CLI REPORTS ISSUED AFTER MIDNIGHT ARE FOR THE PREVIOUS DAY

**NWS CLI reports issued at midnight, 1 AM, 2 AM local time contain YESTERDAY'S data.**
A `cli_low` or `cli_high` event at 12:56 AM on March 4 = March 3 climate data.
Using it for a March 4 market = trading on the wrong day's data.

**The fix**: always check that the CLI report date matches the market's target_date before trading.
This has been explained to me 10+ times. Stop forgetting it.

---

## 📋 twc_morning_trader Limit Order Rules (non-negotiable)

1. **Never bid above max_limit.** max_limit = our_p - MIN_EDGE. If the market is above max_limit, leave the order resting AT max_limit — do not cancel. If market comes back down, we fill at a good price. Cancelling gives up free optionality.
2. **When stepping up prices, cap at min(target_price, max_limit).** Always check edge before moving an order. Never step above max_limit.
3. **Deadline is 10 PM EDT (= 9 PM LST).** After 9 PM LST, other traders can use overnight observations for next-day markets (Kalshi day starts midnight LST = 1 AM EDT). Before that, our TWC forecast model has comparable info. Don't leave orders open past 10 PM EDT.
4. **The manage loop already enforces max_limit via effective_max.** The bug is manual interventions that skip this check.

---

## 🚨 Hard Trading Rules (non-negotiable)

1. **🛑 STATE THE MECHANISM BEFORE BUILDING.** Before any trade logic: write one sentence explaining *why* this makes money or *why* the logic holds in the real world. If you can't write it clearly, stop and ask Ian. Do not implement first and explain later.
   - **The failure mode:** an idea that sounds locally reasonable ("cold air today → cold air tomorrow") but breaks under a real-world sanity check ("fronts pass, temperatures recover"). Ask: *would a domain expert laugh at this?*
   - **Subagent tasks are not a shield.** If a spec describes bad logic, I am responsible for catching it before spawning or accepting the result.
   - This rule is #1 because violating it cost $133 in real money on an obs guard that was physically nonsensical.

2. **NEVER buy a 1¢ contract live.** A 1¢ price means the market is near-certain it won't happen. When I see 96% edge at 1¢ it means my *input data is wrong*, not that the market is wrong. Hard block is in `place_live_order()`. This rule is in memory because I have violated it twice.

3. **Test every code change with a test script before running it on any trader.** No exceptions. If I can't write a test for it, I shouldn't be trading on it.

4. **Max $3/trade, max $6/market/day.** Not $3 × however many markets I feel like. Account size must gate trade count.

5. **Don't think before acting — actually think.** Before placing any trade, ask: "why is the market priced this way?" If I can't answer that, I don't trade. Pattern-matching + executing without sanity-checking is what cost $11 on Feb 25.

6. **Urgency is not an excuse for sloppiness.** Moving fast matters. Writing untested code and immediately running it live is not moving fast — it's moving recklessly. We can do live trading right.

7. **Read `polymarket/LEARNINGS.md` at the start of every session.** The lessons that cost real money are there.

8. **⛔ YOU CANNOT CONFIRM A DAILY HIGH FROM INTRADAY OBS. STOP SAYING YOU CAN.**
   - Intraday obs can confirm the high is ABOVE a threshold (you saw it there → it's at least that high).
   - Intraday obs CANNOT confirm the high is BELOW a threshold, or that it's "inside a range" — it could always go higher.
   - The ONLY intraday confirmations that are valid:
     - HIGH ≥ threshold: obs saw reading ≥ threshold → confirmed above ✅
     - LOW ≤ threshold: obs saw reading ≤ threshold → confirmed below ✅ (daily low only goes lower)
   - INVALID intraday logic (stop writing this):
     - "obs confirms high is inside range" ❌ — high could still go higher
     - "HIGH + between + NO is dead because obs shows temp in range" ❌ — same error
   - Ian has corrected this error multiple times. Do not write it again.

---

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
- **Market structure reference**: `polymarket/MARKET_STRUCTURE.md` — series/market/ticker format, three strike types, settlement rules, pricing fields
- **⚠️ READ `polymarket/LEARNINGS.md` AT THE START OF EVERY SESSION** — it contains hard-won lessons about station types, rounding errors, settlement rules, and edge cases that are NOT all duplicated here.
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
- **cli_strategy/trader.py**: CLI confirmed-high strategy. Three event sources now supported: `cli`, `dsm`, `six_hour_high`. All use the same three-part gate in `check_confidence()`. `valid_hour` is required; `peak_local_hour` optional (Gate 1 skips for DSM/6-hr, Gate 2 OM timing check is always mandatory and never bypassed). Market list cached per (city, date) in `_market_cache` — avoids repeated Kalshi fetches on repeat push events. Always bids at MAX_ENTRY_CENTS (98¢) limit — no orderbook pre-fetch needed.
- **cli_push_trigger.py**: Handles `cli`, `dsm`, `six_hour_high` event types. Dedup: (city, date) for cli/dsm; (city, date, window) for 6hr. DSM buffer: confirmed_high -= 1 (DSM occasionally +1°F above CLI). 6-hr midnight window check: rejects ET's 00Z-06Z window (spans LST midnight). LST_OFFSETS keyed by tz name NOT city name — always use `CITIES[city]["tz"]` first.
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

## NWS Obs Trader Architecture (updated 2026-02-25 evening)
- **Confirmed tier** (our_p=1.0): buy at any entry ≤ 98¢. `max_lower > floor` (greater YES), `max_lower > cap` (between NO), `max_lower >= floor AND max_upper <= cap AND day_over` (between YES — INCLUSIVE bounds)
- **Boundary tier** (our_p=0.30): fires when `max_lower == threshold AND max_upper == threshold+1` (one possible °F wins, one loses). Trade if edge ≥ 5%.
- **1¢ penny block**: if entry would be 1¢, log and skip — market already repriced, we're too late
- **Settlement is CLI-based** (direct °F) — ASOS °C rounding is only OUR uncertainty, not Kalshi's
- **5-minute ASOS can miss 1-minute peaks** (LV: high was 77°F per CLI but obs never showed 25°C all day)
- **"Below floor NO" not implemented**: by the time is_day_over() fires, market already priced it. Also unsafe since 5-min obs might have missed a higher reading.
- **Daemon**: runs every 15 seconds, obs refreshed every 5 minutes. PID in launchctl `com.trady.nws-obs-trader` (KeepAlive=true)
- **Daily max is sticky**: track `max_lower_f` / `max_upper_f` across the day, not just current reading. This is the real edge — markets sometimes look at current temp, we look at daily max.

## Lessons That Cost Money
1. **Kalshi Create Order accepts both `yes_price` and `no_price`.** Use `yes_price` for YES orders, `no_price` for NO orders. Market response `no_ask` = price to buy NO → pass as `no_price`. No conversion. (See LEARNINGS.md for full history of getting this wrong.)
2. **Timezone bugs are silent killers**. UTC midnight ≠ local midnight. Each city needs its own IANA timezone. Code runs fine, places orders, on WRONG data.
3. **When results look too good, verify against ground truth**. Wasted a full day on invalid temporal arb results. Reverted a correct fix TWICE in one day because I panicked.
4. **Verify API field meanings empirically** — don't trust field names (createdAt ≠ event start).
5. **Target boundary markets, not deep ITM**. For confirmed high of 66°F: trade T65 YES + T66 NO (slowest to reprice, most info asymmetry). NOT T61 YES (already obvious, priced quickly by bots). Ian: "you bought 29 or below when they've recorded 33." — markets far from the confirmed high have no info edge.
6. **OM gate**: Only trade if OM hourly forecast predicts today's peak occurred ≥45min before the CLI "VALID TODAY AS OF" time. Miami blocked correctly: OM peak at 4pm, still potentially rising.
7. **⛔ NEVER BUY 1¢ CONTRACTS LIVE. EVER.** (Ian told me this Feb 24. I wrote it down. I ignored it Feb 25 and lost $11. Third time must not happen.)
   - A 1¢ ask means the market is nearly certain this won't happen. The market is usually right.
   - When I see 96% edge at 1¢, it means **my input data is wrong**, not that the market is wrong.
   - Feb 24: bought YES on `less` markets at 1¢ using overnight temperature as confirmed daily high. SA was 61°F at midnight; afternoon hit 87°F. Lost $9.
   - Hard block now in `place_live_order()` and `cli_manual_trade.py` — logs to `penny_blocks.jsonl` for investigation.
   - **The block is for 1¢ BUY orders only** — not 99¢ sells or 99¢ entry prices on the winning side (those are fine or correctly rejected by entry_p >= 1.0).
8. **Morning CLIs are NOT confirmed daily highs.** NWS issues a preliminary CLI at ~7-8 AM local showing overnight temperatures (peak at midnight). The actual afternoon high comes in the afternoon CLI with "VALID TODAY AS OF HH:MM PM". Trading on the morning CLI = trading on the overnight low, not the day's high. Fix: `check_confidence` now blocks CLIs issued before `om_peak + 45min`. If there's no VALID TIME in a CLI and the issued time is before the predicted peak, reject it.
   - Feb 25: Denver morning CLI said 51°F. Afternoon high was 67°F. We bought NO on the 67-68°F range at 73¢. Lost $2.92.
9. **$3/trade budget but must cap daily account exposure too.** $3 × 9 trades = $27 on a $27.70 account = effectively all-in. Always leave a reserve. Ian's rule: $3 max per market. Don't place so many markets at once that you drain the account.
10. **Full technical learnings**: `polymarket/LEARNINGS.md`
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

## Key Testing Rule
**Always import and use real utils when testing them.** Use `from nws_obs_trader import c_to_possible_f` etc. — never reimplement in a test script. Verified correct 2026-02-27.

## °C → °F Disambiguation Formula (verified 2026-02-27)

**Correct formula** (direction: whole °F → °C, NOT °C → °F):
```python
import math
def f_range_for_c(c_whole):
    base = c_whole * 9/5 + 32
    return math.ceil(base - 0.9), math.ceil(base + 0.9) - 1
```
Verified vs wethr.net converter. Old `floor((c-0.5)*9/5+32+0.5)` was wrong for some values.

**Empirical base rates** (49 city-dates, Feb 22-26):
- HI (upper °F): **55%**, LO: **36%**, MISS (1-min peak above 5-min range): **9%**
- HI bias is real and mechanistically correct: CLI high = 1-min peak, not 5-min avg
- NWS API has 5-min history (~7 day rolling window)

Details in `polymarket/LEARNINGS.md`.

## ⚠️ Backtesting Rules (non-negotiable)

1. **Final CLI is published next morning.** For target_date=D, the settled CLI is published on D+1. Never use same-day CLI records for settlement backtesting.
2. **ASOS/IEM fetches must use LOCAL day boundaries.** UTC midnight-to-midnight cuts off PT cities at 4 PM local — misses the afternoon high entirely. Always convert local midnight → UTC for query bounds.
3. **backtest_v3.py CLI vs ASOS gap result (-0.17°F) is wrong** — violated both rules above. Do not cite it. Rerun before using.

## 📋 SOPs — Read These Before Acting

When a task matches one of these, **read the SOP first** before doing anything:

| Task | SOP location |
|---|---|
| Reset a paper trader's state (bug fix, formula change, clean re-test) | `polymarket/RESET_TRADER.md` |

**How SOPs get found:** Either listed here (guaranteed) OR via `qmd query "how to X"` (semantic search). If you're about to do something operational and you're not sure of the right process — search first.

---

## 📋 Open TODOs

### ✅ DST day-boundary bug — FIXED (prior sessions, confirmed 2026-03-07)
`LST_OFFSETS`, `lst_midnight`, `lst_today` implemented in `trading_utils.py` and used
in all critical day-boundary paths (`fetch_obs_cache_today`, `fetch_obs_cache_sequence`,
`fetch_obs_from_push`, `fetch_obs` in nws_obs_trader, CLI peak UTC in cli_strategy/trader).
Remaining `ZoneInfo` usages are civil clock-time gates ("is it past 8 AM?") — correct.
Verified by code audit 2026-03-07 morning. Git history: afdc614, 920ef8f, 4b544a3.

---

### venv / launchctl cleanup (details in `polymarket/TODO_VENV.md`)
1. **HIGH** Copy all 21 installed plists to `polymarket/launchctl/` and commit — only 3 are in the repo, rest only exist in `~/Library/LaunchAgents/` (data loss risk if machine rebuilt)
2. **HIGH** `polymarket/requirements.txt` — run `.venv/bin/pip freeze > requirements.txt` and commit
3. **MEDIUM** Clear stale stderr logs (nws_obs_trader, obs_exit_monitor) — full of old netCDF4 errors burying real ones
4. **LOW** Document Python version fragility (venv symlink → python3.13) in a SETUP.md

---

## What Doesn't Work
- Temporal arb: edge is real but bots price 5m markets in 30-60 seconds. Need VPS infra.
- Complement arb (gabagool): bots arb it away instantly.
- Sports line shopping: Vegas is sharp money too.

## Archived Traders (2026-02-28)
Files moved to `polymarket/archive/`. Launchctl agents unloaded.

- **nws_revision_trader.py** (`nws_revision`): Bet on NWS forecast revisions before market reprices. Archived because: signal frequency too low (requires ≥3°F revision AND new forecast clears threshold by 3°F — rare conjunction). Also the signal isn't highly confident — NWS revising doesn't mean the new forecast is right, just that it changed.

- **kalshi_no_bias.py** (`kalshi_no_bias`): Bet NO on markets where crowd systematically overprices YES (e.g. Trump mentions). Archived because: the underlying idea is valid and has worked for other traders, but our implementation needs to be different. Would need to focus on one specific niche first and build a proper model for it rather than a generic NO bias.

- **kalshi_systematic_no.py** (`historical_climatology`): Used historical climate normals (avg high for that date) as the forecast. Archived because: the premise is wrong — modern NWS/ensemble forecasts already incorporate historical climatology as a baseline. Betting against expert model predictions using only historical averages is a bet that every meteorologist and forecasting company is wrong in a systematic direction. They aren't.

## What Might Work (not yet built)
- Mention markets (MentionHub + transcript analysis) — our sweet spot at small capital
- Netflix #1 weekly (Flick Patrol data) — modelable
- Count/activity markets (Poisson models) — TSA, tweet counts
- Resolution rules arbitrage — nobody reads the fine print
- See `polymarket/STRATEGY_IDEAS.md` for full list


## Dashboard
Always restart the dashboard after making changes to dashboard.py:
```bash
# pkill -f won't work — dashboard runs as Python.app (capital P). Use kill directly:
kill $(launchctl list | grep dashboard | awk '{print $1}' | grep -v -) 2>/dev/null; sleep 1
launchctl kickstart gui/$(id -u)/com.trady.dashboard
```

## Browser Access
**Ask Ian immediately when browser is blocked** — don't silently route around it.
Say exactly: "Browser blocked — can you attach a Chrome tab to the OpenClaw extension?"
If he doesn't respond by the next heartbeat, continue without browser access.

---

## 🔍 Self-Review Before Every Commit (non-negotiable)

Before committing any new file or significant change:

1. **Syntax check**: `python -c "import ast; ast.parse(open('file.py').read())"` — no exceptions.
2. **Import check**: `python -c "import module_name"` — catches NameErrors, missing deps.
3. **Scope check**: Any helper function called across multiple functions must be at MODULE level, not nested inside one function.
4. **P table / lookup table check**: Verify each row uses the correct formula. Symmetric-looking tables are often NOT symmetric (e.g., "high no greater" ≠ complement of "high yes greater at same delta" — different scenarios entirely).
5. **Loop interaction check**: If two loops both sleep and do work, ask "do they block each other?" Sequential retry + management loops means orders go unmanaged during retry sleeps. Merge into one heartbeat.
6. **DB method check**: If calling `Trade.expire()`, `Trade.fill()`, `Trade.settle()` etc., verify those methods actually exist in `paper_trading/db.py` before shipping.

Failures on steps 1-2 are embarrassing. Steps 3-6 are the ones that cost real money.

---

## ⚠️ CLI IS ALWAYS PRELIMINARY — NEVER "FINAL DAILY MAX"

**Ian has corrected this multiple times. Do not say "CLI = official final daily max" ever again.**

- NWS CLI is issued MULTIPLE TIMES per day as new observations come in
- Each issuance shows the high SO FAR — a higher temp CAN still be recorded later
- Kalshi settles against the **FINAL CLI**, published the MORNING AFTER the target date
- The wethr push `cli` event = preliminary CLI issuance — same as what the CLI daemon uses
- DSM = end-of-day confirmed (3 cities only: KNYC, KMSP, KSAT)
- There is NO intraday source that gives the "confirmed final daily max" except next-morning CLI

Source: LEARNINGS.md lines 51-58, 213-217

---

## 🔧 Fix It, Don't Narrate It (2026-03-05)

When I identify a problem, **fix it immediately**. Do not describe the problem, say "I'll keep an eye on it," or flag it for later if the fix is straightforward and safe.

Ian's exact words: "why would you just say the issue and not fix it??"

This applies to: stuck processes, misconfigs, redundant daemons, anything with an obvious safe fix. The bar for acting vs. asking is: would Ian expect me to have already fixed this?

---

## 🔌 Wethr Push Client — Never Double-Restart (2026-03-05)

Wethr server holds connection slot ~20 min after client dies (application-level session tracking, not TCP state). If you restart the push client while a session is still live on the server, you'll get 409 for up to 20 minutes.

**Rule:** Kill once → let launchctl bring it back → do not touch it again for 20 min.
**409 retry** is now 30s (was 300s). Self-heals automatically.
