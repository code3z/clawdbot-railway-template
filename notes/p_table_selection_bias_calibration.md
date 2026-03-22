# P_TABLE Selection Bias Calibration
**Date:** 2026-03-22  
**Author:** Trady  
**Status:** Analysis only — no P_TABLE changes deployed

---

## The Question

The P_TABLE was calibrated on all available (city, date, market) combinations. But twc_morning_trader only trades when it has edge: `P_TABLE[cell] - noon_price >= MIN_EDGE (0.08)`. This creates selection bias — the markets we actually trade are a non-random subset of the training population, specifically the ones the crowd is least confident about. Are we winning as often as the P_TABLE predicts on that subset?

**The self-consistent P\* condition:**  
`P*(cell) = win_rate(rows where noon_price < P* − MIN_EDGE, type=cell)`

---

## Data

- **Training rows:** 3,282 (Feb 27 – Mar 20, 22 unique target dates)
- **Missing:** 558 rows skipped due to no noon price (primarily Feb 22–26 and Mar 21)
- **Full dataset would be:** ~28 dates (~4,100 rows estimated)
- **Lead-hours window:** 30–48h, closest to 36h per (city, date)

---

## Method

For each P_TABLE cell, filter training rows to those where `noon_price < P_TABLE[cell] − 0.08` (the rows we'd actually trade given current settings) and compute the actual win rate. The gap `WR − P_TABLE` shows how much we're over/understating our edge.

This is the raw (zero-iteration) version — the most interpretable and least assumption-dependent.

---

## Results: Key Cells (N_trade ≥ 8)

| Key | P_TABLE | Threshold | N_trade | WR@trade | Gap | Note |
|-----|---------|-----------|---------|----------|-----|------|
| high/no/between/above/1 | 0.745 | 0.665 | 26 | **42.3%** | −0.322 | 🔴 |
| high/no/between/above/2 | 0.814 | 0.734 | 26 | **57.7%** | −0.237 | 🔴 |
| high/no/between/above/3 | 0.916 | 0.836 | 35 | 88.6% | −0.030 | ok |
| high/no/between/above/4 | 0.945 | 0.865 | 13 | 100.0% | +0.055 | 🟢 |
| high/no/between/above/5 | 0.974 | 0.894 | 10 | 90.0% | −0.074 | 🔴 |
| high/no/between/below/1 | 0.737 | 0.657 | 24 | **54.2%** | −0.195 | 🔴 |
| high/no/between/below/2 | 0.814 | 0.734 | 41 | 73.2% | −0.082 | 🔴 |
| high/no/between/below/3 | 0.893 | 0.813 | 42 | 85.7% | −0.036 | ok |
| high/no/between/below/4 | 0.921 | 0.841 | 23 | **65.2%** | −0.269 | 🔴 |
| high/no/between/below/5 | 0.936 | 0.856 | 19 | 73.7% | −0.199 | 🔴 |
| high/no/less/2 | 0.885 | 0.805 | 10 | 70.0% | −0.185 | 🔴 |
| high/no/less/3 | 0.936 | 0.856 | 10 | 100.0% | +0.064 | 🟢 |
| high/no/less/4 | 0.969 | 0.889 | 8 | 87.5% | −0.094 | 🔴 |
| high/no/less/5 | 0.990 | 0.910 | 11 | 90.9% | −0.081 | 🔴 |
| high/yes/less/1 | 0.535 | 0.455 | 8 | **12.5%** | −0.410 | 🔴🔴 |
| low/no/between/above/1 | 0.759 | 0.679 | 13 | 76.9% | +0.010 | ok |
| low/no/between/above/2 | 0.874 | 0.794 | 32 | **100.0%** | +0.126 | 🟢 |
| low/no/between/above/3 | 0.933 | 0.853 | 17 | 88.2% | −0.051 | 🔴 |
| low/no/between/above/4 | 0.955 | 0.875 | 20 | 90.0% | −0.055 | 🔴 |
| low/no/between/above/5 | 0.967 | 0.887 | 13 | 100.0% | +0.033 | ok |
| low/no/greater/4 | 0.979 | 0.899 | 8 | 100.0% | +0.021 | ok |
| low/no/less/5 | 0.962 | 0.882 | 11 | 90.9% | −0.053 | 🔴 |
| low/yes/greater/1 | 0.635 | 0.555 | 12 | 75.0% | +0.115 | 🟢 |

**Summary by measure (N_trade ≥ 8):**
- `high` cells: mean gap = **−0.140** (P_TABLE overstates by 14pp on avg), 15 cells evaluated
- `low` cells: mean gap = **+0.018** (essentially correct), 8 cells evaluated

---

## Key Findings

### 1. HIGH markets are systematically overstated

The P_TABLE for `high/no/between` trades claims 74–97% win probability. Among the rows we'd actually trade (noon < P_TABLE − 0.08), the actual win rate is 42–89% — with the largest gaps at **delta 1–2** and **delta 4–5**.

- delta=1: P_TABLE says 74–75%, actual WR is **42–54%** (N=24–26). Major overstate.
- delta=2: P_TABLE says 81%, actual WR is **58–73%** (N=26–41). Significant overstate.
- delta=3: P_TABLE says 89–92%, actual WR is 86–89%. Close — small overstate.
- delta=4: mixed; above/4 overstates by 27pp (23 trades, 65% WR), above/4 undrestates (13 trades, 100%).

### 2. LOW markets are correctly calibrated (or slightly understated)

`low/no/between/above` delta 1–2 have actual WR = 77–100%, essentially matching or exceeding P_TABLE. `low/yes/greater/1` (12 trades, 75% WR) is understated by ~12pp.

### 3. high/yes/less/1 is the worst cell in the table

P_TABLE = 0.535. Among 8 qualifying trades, actual WR = **12.5%**. This cell should either be dropped or heavily revised downward.

This makes conceptual sense: `high/yes/less` means we're betting the high will STAY BELOW some threshold — when the market prices it below 46¢ (our entry threshold), the crowd is already quite skeptical, and they're usually right.

### 4. The self-consistent P\* is not operational for most HIGH cells

When we iterate to find P\* such that WR(noon < P\*−0.08) = P\*, for most HIGH cells the iteration drives P\* down to 0.45–0.65. But at those thresholds, there are **zero training rows** with noon prices that low (min noon in these cells is 0.48–0.84). The fixed point is mathematically valid but physically unreachable — the market never prices these cheaply enough.

This is a definitive signal: **HIGH/no/between trades at delta ≤ 2 do not have MIN_EDGE=0.08 edge**. The trades we're entering at current P_TABLE levels are entering at adverse prices.

For `low` cells, the iteration IS operational — P\* converges to values near the training data minimum noon price, and N@P\* is 13–39 with self-consistent WR.

---

## Limitations / Caveats

1. **22 training dates only.** ~4x more data would significantly tighten these estimates. Many cells with N_trade < 8 have no usable estimate at all.

2. **Selection bias in the bias measure.** The gap is itself biased: conditioning on "market prices us cheaply" selects for harder situations. Some negative gap is expected even with a correctly calibrated P_TABLE. The question is whether the gap is larger than expected from sampling alone.

3. **Sparse cells.** `high/no/greater`, `high/no/less` delta 1–3 have N_trade < 5, so their results are noise.

4. **Delta capping.** Delta ≥ 5 is pooled into the delta=5 bucket. The delta=4 anomaly (high/no/between/below/4 has 23 trades at 65% WR vs P_TABLE=0.921) may partly reflect this mixing.

5. **Missing 6 dates.** Feb 22–26 and Mar 21 are missing noon prices from the cache. Adding them would increase N by ~15% and likely tighten HIGH cell estimates.

---

## Recommended Actions (pending Ian decision)

**Immediate (high confidence):**
- **Lower `high/no/between/above/1–2`** and **`high/no/between/below/1–2`** significantly. P_TABLE says 74–81%, data says 42–73% at current thresholds. Suggest: 0.55–0.65 range.
- **Lower or disable `high/yes/less/1`**. 12.5% WR with P_TABLE=0.535 is not viable.

**Moderate confidence (N=8–25):**
- `high/no/between/below/4–5`: WR = 65–74% vs P_TABLE = 92–94%. Lower to ~0.75.
- `high/no/less/2`: WR = 70% vs P_TABLE = 0.885. Lower to ~0.75.

**Leave for now:**
- All LOW cells — essentially correct or slightly understated.
- `high/no/between/above/3`, `high/no/between/below/3` — small gap (3–4pp), within sampling noise.
- Any cell with N_trade < 8 — insufficient data.

**Future work:**
- Fetch noon prices for Feb 22–26 and Mar 21 (Kalshi candlestick API) to get to 28 dates.
- Rerun this analysis on 36–42h strict forecast window only.
- Weekly rerun as data accumulates (each week adds ~7 dates × 19 cities × ~8 markets/city).

---

## Appendix: Raw table (all cells)

*(Available in the analysis script. Key columns: P_TABLE, thresh, N_total, N_trade, WR@trade, gap, min_noon.)*

Script: run `generate_training_rows()` from `build_forecast_model.py`, then filter by `noon_price < P_TABLE[key] - MIN_EDGE` per cell.
