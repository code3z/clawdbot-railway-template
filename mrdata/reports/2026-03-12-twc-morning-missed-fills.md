# TWC Morning — Missed Fills Analysis
**Date:** 2026-03-12  
**Period:** 2026-03-06 through 2026-03-13 (7 days)  
**Analyst:** Mr Data

---

## Headline

**76% of expired/cancelled limit orders would have won — but net economic impact is near-zero (+$31). Missed profits ($197) are nearly cancelled by avoided losses ($166). March 6 dominates the sample: 93 of 166 missed fills (56%) came from a single next-day batch placed on March 5 that almost entirely failed to fill.**

---

## Sample Overview

| Metric | Value |
|--------|-------|
| Total twc_morning trades (7 days) | 225 (all is_paper=0) |
| Total missed fills | 166 |
| · expired (hit 10 PM deadline) | 133 |
| · cancelled (proactively, all March 6) | 26 |
| · limit_pending (still resting) | 7 |
| Matched to CLI actuals | 141 / 166 |
| No CLI yet (Mar 12–13) | 25 |

---

## Would They Have Won?

| Outcome | n | % |
|---------|---|---|
| Would have WON | 107 | 75.9% |
| Would have LOST | 34 | 24.1% |
| Total with verdict | 141 | — |

### By fill_status

| fill_status | n | Wins | Win% |
|-------------|---|------|------|
| expired | 115 | 88 | 76.5% |
| cancelled | 26 | 19 | 73.1% |
| limit_pending | — | — | — |

---

## Economic Impact

Using `limit_init` from trade notes as the would-have-been fill price:

| | Trades | Amount |
|--|--------|--------|
| Missed profit (winners) | 91 | +$196.80 |
| Avoided loss (losers) | 33 | -$165.72 |
| **Net missed P&L** | — | **+$31.08** |

**The missed fills are essentially a wash.** The model is right 76% of the time on unfilled trades, but the 24% it's wrong almost exactly cancels out the profit from the 76% it's right — because both sides have similar dollar sizes (~$5-6 avg stake).

---

## Root Cause: Why Didn't They Fill?

All missed fills are **NO/between limit orders**. The mechanic:

- We submit: buy NO at `limit_init` (e.g., 70¢)
- Fill requires: YES_bid ≥ (100¢ - limit_init) = 30¢
- At placement: YES_ask ≈ 30¢, **but YES_bid ≈ 24–26¢** (spread gap ~5–8¢)
- We need YES to tick up from 24–26¢ bid to 30¢ bid
- Most days, the market doesn't move enough → no fill

This is **by design** — we're posting liquidity below market, waiting for the YES price to inch up. In 76% of cases we're right that it won't, but those orders never fill. The orders that WOULD have filled (if we went to market) are exactly the ones where our edge was real.

---

## March 6 Anomaly

**93 of 166 missed fills (56%) are all from a single March 6 batch.**

- All 93 orders placed **March 5, 4:41–4:56 PM ET** as next-day limit orders
- 67 = `fill_status='expired'` (reached 10 PM deadline)
- 26 = `fill_status='cancelled'` (proactively cancelled, same day, same orders)
- Only 1 of 94 placed orders filled (Miami NO, limit=0.59, won ✅)
- **70 would have won (75.3%), 23 would have lost**

This was not a system bug — it appears the March 5 afternoon batch placed next-day orders that never got close enough to fill. All orders for all 20 cities placed simultaneously, all at similar `limit_init` vs `mkt_p` spreads (~0.40 average gap).

---

## By Trade Category

| Category | n | Wins | Win% |
|----------|---|------|------|
| no/between/high | 106 | 77 | 72.6% |
| no/between/low | 30 | 27 | 90.0% |
| no/less/high | 2 | 2 | 100% |
| yes/less/high | 1 | 1 | 100% |
| no/less/low | 1 | 0 | 0% |
| no/greater/low | 1 | 0 | 0% |

**NO/between/low is the strongest category: 90% win rate on missed fills.**  
NO/between/high is the volume driver (106 of 141) at a solid 72.6%.

---

## By TWC Δ (Distance from Boundary)

| Δ | n | Wins | Win% |
|---|---|------|------|
| 1°F | 50 | 35 | 70.0% |
| 2°F | 47 | 35 | 74.5% |
| 3°F | 18 | 15 | 83.3% |
| 4°F | 5 | 5 | 100% |
| 5°F | 3 | 1 | 33.3% |
| 6°F | 1 | 0 | 0% |

As expected: wider TWC margin = better outcome. Δ=1 wins are borderline — the market was actually right that the temp could still land in the bucket.

---

## Cities with Worst Miss Outcomes (Would-Have-Lost)

| City | n | Wins | Win% | Pattern |
|------|---|------|------|---------|
| Boston | 6 | 1 | 16.7% | Temp hit right at bucket edge 3x (actual=35, fl=34–35) |
| Houston | 5 | 1 | 20.0% | Temp hit at fl=84–85, actual=84°F (×3) |
| LAX | 8 | 2 | 25.0% | High hit at fl=73, actual=73°F (×3); Low hit at fl=51–52 (×3) |
| Seattle | 7 | 3 | 42.9% | Actual=50, bucket fl=49–50 (×3) |

**The "losers" have a clear pattern: temperature landed EXACTLY at the floor of the bucket we were betting against.** This is the inherent risk of Δ=1 between-NO bets — the temperature is close enough to the bucket that it sometimes lands right there.

---

## Cities Where Missed Orders Were Pure Money (100% Win Rate)

Austin, Philly, Minneapolis, Phoenix, DC, NOLA, Las Vegas, Denver (partial): 
**All missed fills for these cities would have won.** These are cities where the TWC forecast was clearly off the bucket and the actual temp confirmed it.

---

## By Date

| Date | n | Wins | Win% | Notes |
|------|---|------|------|-------|
| 2026-03-06 | 93 | 70 | 75.3% | Entire next-day batch, single afternoon placement |
| 2026-03-07 | 10 | 7 | 70.0% | |
| 2026-03-08 | 13 | 10 | 76.9% | |
| 2026-03-09 | 12 | 12 | 100.0% | |
| 2026-03-10 | 12 | 7 | 58.3% | More cold-front adjacent losers |
| 2026-03-11 | 1 | 1 | 100.0% | |

---

## What This Means

1. **The model's direction is good** (76% correct on unfilled trades). The missed fills don't represent a calibration problem — the signal is right, the fills just aren't happening.

2. **Net P&L impact is near-zero** — not a crisis, but $197 in potential profit is being left unrealized each week. The losers nearly cancel it, but those are cases where NOT filling protected us.

3. **The limit order mechanics are working as designed** — we're posting below-market limits and waiting. The cost is a low fill rate (~30% historically). The question is whether paying up for fills (tightening to market or using more aggressive limits) would improve overall P&L.

4. **Δ=1 between-NO is structurally risky** — 70% WR, and those 30% losers hit right at the boundary. Worth considering whether Δ=1 trades should be skipped entirely or require a larger edge buffer.

5. **March 6 was not a bug** — it was a normal batch where next-day resting limits across 20 cities almost all failed to fill. This will continue to happen on days when the market doesn't move.

---

## Data Notes

- All 225 trades: `is_paper=0` (live)
- Dollar sizes: $2.87–$16.19 (Kelly-sized, live caps applied)
- 25 trades (March 12–13) excluded from win/loss analysis — CLI not yet published
- P&L estimate: `pnl = dollar_size × (1/limit_init − 1)` for wins; `−dollar_size` for losses
- Settlement rule applied: `between` = floor ≤ actual ≤ cap; `greater` = actual > floor; `less` = actual < cap
