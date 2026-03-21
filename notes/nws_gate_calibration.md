# NWS Gate P-Table Calibration
*Written 2026-03-20 after first calibration attempt.*

---

## What we did

Goal: calibrate a separate p-table for `twc_morning_nws_gate_trader` — the subpopulation
of trades where |TWC - NWS| ≥ 4°F. The hypothesis was that TWC might be slightly less
reliable when NWS disagrees, so the p-table should reflect that.

Steps taken:
1. Loaded `reports/100d_markets.json` (BETWEEN markets, Dec 2025–Mar 19) + `forecasts.jsonl`
   (D-1 TWC+NWS data, Feb 26–Mar 19) + `forecast_logs/cli_actuals.jsonl` for outcomes
2. Joined on (city, target_date) to get ~419 pairs with complete data (23-day overlap)
3. Simulated GREATER/LESS trades at every bucket floor/cap threshold in the BETWEEN data
4. Computed win rate by (measure, strike_type, delta, gap bucket)
5. Compared to existing `twc_morning_config.P_TABLE` — found 4 cells with n≥35 and Δ>3%
6. Built `twc_morning_nws_gate_config.py` with those 4 overrides; imported into trader
7. Later: re-ran with REAL GREATER/LESS market thresholds (880 markets fetched for EV analysis)
8. Found n<10 for almost all cells. Reverted to base table. Overrides scrapped.

Also did a separate (more reliable) EV analysis:
- Fetched 880 real GREATER+LESS Kalshi markets (Feb 26–Mar 19) and their 11:15 AM D-1 prices
- Computed actual EV by gap bucket — found gap≥4°F tradeable subset has +23.2% EV vs +16.0%
- This is the real alpha finding; the p-table was a sideshow

---

## Mistakes made

### 1. Used BETWEEN bucket boundaries as GREATER/LESS proxies
Each Kalshi event has ~10 BETWEEN buckets but only ONE GREATER and ONE LESS market.
Using all 10 bucket floors/caps as proxy thresholds inflated n by ~10x within each
(strike_type, delta) cell. The n=39, n=45 numbers I reported were fake. With real thresholds,
almost every cell had n<10.

**Fix next time:** Start with the real GREATER/LESS market data. We already have a script
to fetch it (used in the EV analysis). Use `/tmp/threshold_markets.json` or re-fetch.

### 2. Lead hours filter was slightly wrong
Used `lead ≥ 12h` with "keep smallest lead" preference → selected noon D-1 forecasts
(12h lead) instead of 6 AM D-1 forecasts (18h lead). The noon D-1 run is 45 minutes
AFTER the trader places orders at 11:15 AM — technically look-ahead.

Ian's verdict: 45 minutes is fine, doesn't matter in practice. But the correct filter
is `lead 15–30h` (selects 6 AM D-1 run) to be clean.

### 3. Reported inflated n as sufficient sample sizes
Declared n=39 "adequate for calibration" without checking how many distinct city/date pairs
actually contributed. Should have counted distinct (city, date) pairs per cell, not raw rows.

### 4. Claimed n was inflated by ~10x then said it wasn't, then confirmed it was
Flip-flopped on this mid-session. Root cause: didn't think clearly before speaking. The
right analysis (which Ian prompted): check whether multiple thresholds from the same
city/date land in the SAME delta bucket. They don't — but that doesn't help because we
only have 1 real market per city/date anyway.

---

## Things to ask Ian before running again

1. **How much data do we have?** Check `forecasts.jsonl` — how many city/date pairs have
   both `nws_high` and `twc_high` non-null? Should be `(days since Feb 26) × 20 cities`.
   Minimum viable: ~120 pairs per cell (so ~6 days × 20 cities per delta bucket, gap-filtered).

2. **Do we care about LOW markets too?** LOW series have `nws_low` in forecasts.jsonl.
   Decision was deferred — only HIGH was calibrated this time.

3. **Should we also split by direction of disagreement?** (NWS warmer vs TWC warmer)
   Preliminary evidence suggested direction of NWS gap matters. Didn't pursue because
   sample sizes were too small. Worth revisiting with more data.

4. **Has the base p-table been recalibrated recently?** The overrides are compared against
   `twc_morning_config.P_TABLE`. If that table has been updated, recalibrate against the
   new version.

---

## How long to wait before re-running

**Minimum: 60 more days of NWS data** (so ~83 days total from Feb 26).
That's approximately **late May 2026**.

Why 60 more days:
- With 83 days × 20 cities = 1,660 city/date pairs
- Gap ≥ 4°F: ~25% → ~415 pairs
- 1 GREATER + 1 LESS per pair = 830 threshold observations
- Split by 5 delta buckets → ~166 per bucket
- Filtered to gap ≥ 4°F only → ~83 per cell
- That's enough for meaningful calibration (~50 per cell minimum)

Earlier than 60 more days: not worth it.

---

## What was actually found (keep this)

**The EV analysis with real market prices is the reliable finding:**
- LESS NO, gap ≥ 4°F, tradeable (implied edge ≥8%): WR=100%, mp=76.8¢, EV=+23.2% (n=18)
- LESS NO, gap < 4°F, tradeable: WR=96.2%, mp=80.2¢, EV=+16.0% (n=78)
- Market discounts ~1.7¢ when NWS disagrees; our accuracy doesn't drop proportionally
- The gate selects for real alpha, not just a smaller sample of equal-quality trades
- Gap ≥ 6°F: even stronger (+8.7% EV on LESS NO, 100% WR tradeable subset)

**The p-table calibration is NOT the alpha story. The market price evidence is.**

---

## Relevant files

| File | What it is |
|------|-----------|
| `reports/nws_gate_ptable_notes.md` | Technical methodology notes (detailed) |
| `twc_morning_nws_gate_config.py` | Custom config file — NOT imported; kept for reference |
| `twc_morning_nws_gate_trader.py` | Uses base `twc_morning_config.P_TABLE` directly now |
| `/tmp/threshold_markets.json` | 880 real GREATER+LESS markets Feb 26–Mar 19 (ephemeral) |
| `/tmp/threshold_prices.json` | D-1 11:15 AM prices for those 880 markets (ephemeral) |
| `reports/100d_markets.json` | BETWEEN markets Dec 2025–Mar 19 (5,632 records) |

---

## If you re-run this calibration

Script outline (don't use the BETWEEN proxy approach again):
```python
# 1. Fetch real GREATER+LESS settled markets for all cities, date range
# 2. Load forecasts.jsonl with filter: lead 15-30h, one per (city, target_date)
# 3. For each real market:
#    - Get TWC and NWS from forecast pair
#    - Compute gap, margin, delta
#    - Check CLI actual for outcome
# 4. Compute win rate by (measure, strike_type, delta, gap_bucket)
# 5. Only override base table for cells with n >= 50 and |Δ| > 0.05
# 6. Sanity check: count DISTINCT (city, date) pairs per cell, not raw rows
```
