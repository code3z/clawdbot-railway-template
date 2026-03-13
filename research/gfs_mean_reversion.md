# GFS Mean Reversion Analysis
**Hypothesis test: Do Kalshi weather market prices over-revert at GFS model update times?**

*Analysis run: 2026-03-13 | Data: 480 markets across 8 cities, ~1 month*

---

## The Hypothesis

Ian's thesis: When a new GFS/NBM model run is ingested (~3:30-4:00h, 9:30-10:00h, 15:30-16:00h, 21:30-22:00h UTC), market participants over-update prices. Within 1-2 hours, prices revert as the ensemble view reasserts. **Predicted signal: stronger negative autocorrelation in GFS-update hours vs. non-GFS hours.**

---

## Data Collected

- **Markets:** 480 T-prefix (above-threshold) markets, 8 cities: Boston, Chicago, Miami, Dallas, Houston, Atlanta, NYC, LAX
- **Date range:** February 10 – March 13, 2026 (~1 month)
- **Source:** Kalshi `/series/{series}/markets/{ticker}/candlesticks` — 60-minute OHLC
- **Series used:** KXHIGHTBOS, KXHIGHCHI, KXHIGHMIA, KXHIGHTDAL, KXHIGHTHOU, KXHIGHTATL, KXHIGHNY, KXHIGHLAX
- **Price field:** `yes_ask.close_dollars` (hourly close ask price)
- **Total hourly observations:** ~17,582 price points before filtering
- **GFS availability window:** Hours {3, 4, 9, 10, 15, 16, 21, 22} UTC (run time + ~3.5h processing)

---

## Raw Results

### Autocorrelation (lag-1 hourly returns split by GFS window)

| Group | n | Autocorr (r₁, r₂) |
|---|---|---|
| GFS update hours | 3,612 | **−0.036** |
| Non-GFS hours | 7,081 | **−0.134** |
| Difference | — | **+0.098** |

**Deduplicated** (one T-market per city-date, reduces correlated market inflation):

| Group | n | Autocorr |
|---|---|---|
| GFS hours | 1,908 | **+0.029** |
| Non-GFS hours | 3,775 | **−0.176** |
| Difference | — | **+0.205** |

### 📛 Verdict: Hypothesis is WRONG — the opposite is true.

GFS hours show **weaker** mean reversion than non-GFS hours. In the deduplicated analysis, GFS hours exhibit **slight positive autocorrelation** (momentum), meaning post-GFS moves tend to **continue**, not revert.

---

## Fade Strategy Performance

**Strategy:** After observing a ≥3¢ move in a GFS-update hour, fade (oppose) the move. Exit 1 hour later.

| Setting | GFS hours | Non-GFS hours |
|---|---|---|
| n large moves (|r| > 3¢) | 681 | 1,390 |
| Continued (r₁·r₂ > 0) | 41.3% | 37.1% |
| Reverted (r₁·r₂ < 0) | 41.3% | 46.8% |
| Avg fade PnL/trade | **+0.00150** | **+0.00940** |
| Win rate | **39-40%** | **47-49%** |

**Deduplicated:**

| Setting | GFS hours | Non-GFS hours |
|---|---|---|
| n large moves | 294 | 663 |
| Fade PnL/trade | **+0.00041** | **+0.00899** |
| Reversion rate | 39.5% | 49.0% |

### Multi-hour reversion tracking (GFS large moves only)

Fade a 3¢+ GFS-hour move and hold multiple hours:

| Hold time | Avg fade PnL | Win rate |
|---|---|---|
| +1h | **+0.00146** | **39.0%** |
| +2h | **+0.00217** | **42.0%** |
| +3h | **+0.00173** | ~42% |

The PnL is technically positive (fractional cents) but **win rates are below 50%**, meaning the MEDIAN outcome is a loss. The positive mean is being dragged up by a few outlier reversions.

---

## Per-Hour Autocorrelation Breakdown

| UTC Hour | n | Autocorr | Fade PnL (3¢+) | GFS? |
|---|---|---|---|---|
| 00h | 449 | +0.039 | −0.00333 | |
| 01h | 444 | −0.112 | +0.01608 | |
| 02h | 440 | −0.065 | +0.00853 | |
| **03h** | 436 | **−0.228** | +0.01768 | ✓ |
| **04h** | 414 | **+0.081** | −0.00552 | ✓ |
| 05h | 394 | −0.102 | +0.02191 | |
| 09h | 378 | −0.178 | +0.01574 | ✓ |
| **10h** | 367 | **−0.237** | +0.01574 | ✓ |
| 11h | 366 | **−0.380** | +0.03068 | |
| **15h** | 331 | **+0.072** | −0.00652 | ✓ |
| **16h** | 688 | **+0.025** | −0.00828 | ✓ |
| 17h | 663 | −0.127 | +0.00657 | |
| 18h | 624 | −0.236 | +0.01164 | |
| 20h | 553 | −0.277 | +0.01146 | |
| **21h** | 519 | −0.075 | +0.00859 | ✓ |
| **22h** | 479 | +0.022 | −0.00067 | ✓ |

Key observations:
- Hour 3 (00z GFS availability): −0.228, fade PnL +1.77¢ ← only GFS hour with clear reversion signal
- Hour 4: +0.081 (momentum!) ← the "2nd GFS hour" shows the OPPOSITE of reversion
- Hours 10, 15, 16, 22: mixed, mostly momentum or near-zero
- **The strongest reversion is at hour 11** — 90 minutes AFTER GFS 06z availability — but this is not classified as a GFS window in my setup. The effect may be lagged.
- Hours 15-16 (12z GFS run) show positive autocorrelation — momentum, not reversion

---

## Trading Cost Context

**Bid-ask spread analysis** (354 hourly spread observations):

| Metric | Value |
|---|---|
| Mean spread | 2.67¢ |
| Median spread | 1.00¢ |
| 90th percentile | 6.00¢ |

**Round-trip cost estimate:**
- Entry: cross half spread ≈ 0.5–1.5¢
- Exit: cross half spread ≈ 0.5–1.5¢
- Kalshi fee: 7% of winnings ≈ 7¢ on a 100¢ contract (i.e., on a $1 position)
- **Total round-trip friction: ~3–10¢ per contract**

**The math is brutal:** The GFS fade strategy generates avg PnL of **0.04–0.15¢ per trade**. This needs to exceed ~3-10¢ in round-trip costs. It's **20–250x below** the required threshold.

---

## Statistical Caveat

The ~31-day date range means our temporal diversity is limited. Multiple markets for the same city-date exist, but intra-event correlation was measured at near-zero (−0.002), meaning different strike markets for the same event behave largely independently (which makes sense — a near-ATM market behaves differently from a deep OTM one). The effective n is close to the raw n.

However, **one month of data is a thin basis** for the conclusion. 8 cities × ~30 days = 240 event-days. The deduplicated analysis with n=294 GFS large moves should be considered preliminary.

---

## Could a Narrower Signal Work?

Hour 3 UTC (00z GFS availability window) shows the strongest reversion: autocorr = −0.228, fade PnL +1.77¢/trade. This is worth noting but:

1. **1.77¢ still doesn't cover costs** (round-trip ≈ 3–10¢ per trade)
2. n = 69 large moves at this hour — small sample
3. Hour 4 (same GFS run, one hour later) has the opposite sign (+0.081), suggesting noise not structure
4. Without a causal story for why hour 3 specifically reverting, it's pattern-mining

---

## Why the Hypothesis Fails

Several plausible explanations:

1. **GFS is actually informative.** Model updates move prices in the CORRECT direction. The "overreaction" doesn't exist because GFS skill is real, and market participants know how to calibrate to it.

2. **Prices are mean-reverting everywhere.** The -0.134 autocorrelation in non-GFS hours reflects general binary market dynamics (prices gravitate toward certainty near expiry, or "noise" trades get corrected by market makers). This is **not a GFS signal** — it's structural.

3. **Liquidity effects.** These are thin markets. Large moves may be individual trades (not information) that get corrected whenever the next liquidity provider arrives. This correction isn't time-dependent on GFS.

4. **Spread noise.** Hourly ask close prices are noisy — they reflect the best ask at one moment per hour, not actual transaction prices. What looks like a "move" may be spread noise, not information.

---

## Infrastructure Needed to Implement

For the record, what an actual implementation would require:

- **Real-time GFS data ingestion:** Monitor NOMADS (noaa.gov) for GFS model output (~3.5h after each run)
- **Price feed:** Kalshi WebSocket for continuous yes_ask, yes_bid updates (not hourly candles)
- **Spread monitoring:** Need live bid/ask to know when a "move" represents price discovery vs. spread noise
- **Order placement:** RSA-signed Kalshi API with limit orders, automatic cancellation
- **Timing precision:** Sub-minute — you need to detect the move and enter before the reversion (which, if real, would take 15–30 min)
- **Slippage model:** These are thinly traded; even small orders may impact prices

Estimated dev time: 2-3 weeks for a proper implementation.

---

## Assessment: Pursue, Park, or Kill?

### **KILL** ❌

**The hypothesis is not supported by the data.** Specifically:

1. **GFS hours show the OPPOSITE of the predicted signal** — slight momentum rather than stronger reversion.
2. The best fade strategy performance occurs in **non-GFS hours**, and it's still only 47-49% win rate before costs.
3. **Trading costs alone kill the idea:** avg fade PnL of ~0.04–0.15¢ vs. ~3-10¢ round-trip friction. You'd need the edge to be 20-250x larger than observed.
4. **Win rate below 50% at GFS hours** means even if execution were free, you'd lose money on average by fading GFS moves. The strategy assumes you're more often right than wrong — you're not.

### What might actually be worth testing instead

- **Non-GFS hours mean reversion** (autocorr −0.13 to −0.18): The underlying mean-reversion in non-GFS hours is real. But it's driven by structural market mechanics (expiry pull, spread noise correction), not by anything time-targeted. A market-making strategy that fades all large moves at any time might have some edge — but the effective spread capture would need to exceed 3-10¢ round-trip, and Kalshi's thin books make this impractical.

- **NWS CLI report timing** (something we already trade): The actual observable price-moving event is the morning CLI data release, not GFS model updates. Our existing NWS revision trader is chasing the right signal.

---

## Appendix: Key Numbers Summary

| Metric | Value |
|---|---|
| GFS hours autocorr | −0.036 (all) / +0.029 (dedup) |
| Non-GFS autocorr | −0.134 (all) / −0.176 (dedup) |
| GFS fade win rate | 39-40% |
| Non-GFS fade win rate | 47-49% |
| GFS avg fade PnL/trade | +0.04¢ to +0.15¢ |
| Min required edge (low-end costs) | ~3¢ |
| Ratio edge/cost | 0.01–0.05x (far below 1.0x needed) |
| Data range | Feb 10 – Mar 13, 2026 |
| Markets analyzed | 480 (8 cities × 60 markets) |
| GFS large moves (≥3¢) | 681 (all) / 294 (dedup) |

*Analysis performed by Trady on 2026-03-13 using Kalshi candlestick API.*
