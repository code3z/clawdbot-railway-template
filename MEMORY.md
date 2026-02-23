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

## Lessons That Cost Money
1. **Kalshi Create Order accepts both `yes_price` and `no_price`.** Use `yes_price` for YES orders, `no_price` for NO orders. Market response `no_ask` = price to buy NO → pass as `no_price`. No conversion. (See LEARNINGS.md for full history of getting this wrong.)
2. **Timezone bugs are silent killers**. UTC midnight ≠ local midnight. Each city needs its own IANA timezone. Code runs fine, places orders, on WRONG data.
3. **When results look too good, verify against ground truth**. Wasted a full day on invalid temporal arb results. Reverted a correct fix TWICE in one day because I panicked.
4. **Verify API field meanings empirically** — don't trust field names (createdAt ≠ event start).
5. **Full technical learnings**: `polymarket/LEARNINGS.md`

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
