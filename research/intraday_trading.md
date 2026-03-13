# Intraday Trading Strategies — Kalshi Weather Markets

**Date:** 2026-03-13  
**Data:** 480 markets × ~39 hourly bars each (18,677 total hourly bars)  
**Series:** BOS, CHI, MIA, DAL, HOU, ATL, NY, LAX, OKC (DEN had 0 settled markets)  
**Granularity note:** The `/markets/{ticker}/history` endpoint returns 404. Finest available data is 1-hour candles via `/series/{series}/events/{event_ticker}/candlesticks`. All analyses use 1H bars.  

---

## 1. How Often Do Markets Move 2¢+ in a Window?

**In a 1-hour window:**
- Mean absolute move: **2.44¢**
- 29.9% of 1H bars move ≥2¢
- 11.7% of 1H bars move ≥5¢

**In a 2-hour window:**
- Mean absolute move: **3.50¢**
- 37.7% of 2H windows move ≥2¢
- 17.3% of 2H windows move ≥5¢

**Bottom line:** A 2¢ move is not rare — it happens roughly once every 3–4 hours per market. At any given moment there are typically many active markets, so there are frequent opportunities. The question is whether those moves are tradeable.

---

## 2. Momentum vs Mean-Reversion at 1H–2H Scale?

| Window | Autocorrelation | Interpretation |
|--------|----------------|----------------|
| 1H     | **−0.0767**    | Mean-reversion |
| 2H     | +0.0017        | Random walk    |

**Mean-reversion wins at 1H timescale.** An up move in one hour is followed, on average, by a slight down move in the next — and vice versa. The effect is small but consistent across 16,865 observations.

**By price level (1H):**
| Level | Autocorr | n |
|-------|----------|---|
| cheap (<15¢) | −0.0372 | 7,644 |
| mid (15–40¢) | −0.0767 | 8,389 |
| fav (>40¢)   | −0.1346 | 832   |

**Higher-priced contracts show stronger mean-reversion.** Favorites (>40¢) have a −0.13 autocorrelation — meaningful signal but small sample (24 markets). Mid-range contracts show the pattern most cleanly.

**Implication:** The data does NOT support a momentum strategy. It weakly supports buying dips (mean-reversion trade). The 2H window looks like a random walk — any 1H pattern washes out over 2 hours.

---

## 3. UTC Hours with Higher Volatility

| UTC Hour | Mean Abs Move | % Move >2¢ | Note |
|----------|--------------|------------|------|
| **20**   | 3.75¢        | 33.0%      | ~4PM ET — market hours close |
| **16**   | 3.68¢        | 42.8%      | ~Noon ET |
| **19**   | 3.52¢        | 34.6%      | ~3PM ET |
| **18**   | 3.43¢        | 38.7%      | ~2PM ET |
| **22**   | 3.34¢        | 25.5%      | ~6PM ET |
| **7**    | 2.78¢        | 39.8%      | ~3AM ET — GFS model update |
| **6**    | 2.81¢        | 37.9%      | ~2AM ET — GFS model update |
| **15**   | 2.75¢        | 39.4%      | ~11AM ET |
| **13–14**| 2.66¢        | 40% range  | ~9–10AM ET |

**Quietest hours:** UTC 1–3 (1–2AM ET) — only ~1.1–1.3¢ mean moves, ~19% chance of 2¢ move.

**Two distinct high-volatility windows:**
1. **Late evening ET (UTC 13–22, roughly 9AM–6PM ET):** Persistent elevated volatility during US trading day. Makes sense — weather news, model updates, bettors active.
2. **Early morning ET (UTC 5–8, roughly 1–4AM ET):** Another spike. This is the GFS 00Z model cycle update window. Even though GFS moves proved to be informative (not overreactions), there's still elevated price movement here.

**Best scalping hours:** UTC 16–20 (12PM–4PM ET). Highest absolute moves with significant 2¢+ frequency. Also highest n (958–959 bars), so these are the most reliably active periods.

---

## 4. Does the Buy-Dip Strategy Work?

**Setup:** Buy after a ≥2¢ drop in 1 hour. Target: +2¢ exit or force-exit after 4 hours.

| Metric | Value |
|--------|-------|
| Total signals | 2,599 |
| Win rate (≥+2¢) | **49.7%** |
| Avg PnL | **+1.32¢** |
| Median PnL | **+2.00¢** |
| Breakeven or better | **66.6%** |
| Avg hold time | 2.8 hours |

**PnL distribution (¢):**
- 10th pct: −8.0¢ 
- 25th pct: −2.0¢
- 50th pct: +2.0¢
- 75th pct: +4.0¢
- 90th pct: +9.0¢

**By entry price level:**
| Level | n | Win Rate | Avg PnL |
|-------|---|----------|---------|
| cheap (<15¢) | 1,307 | 36.5% | +1.31¢ |
| mid (15–40¢) | 1,034 | 61.7% | **+1.63¢** |
| fav (>40¢)   | 258  | 69.0% | +0.17¢ |

**By drop trigger size:**
| Drop | n | Win Rate | Avg PnL |
|------|---|----------|---------|
| 2–4¢ | 1,239 | 51.7% | +1.28¢ |
| 4–6¢ | 573   | 53.1% | +0.76¢ |
| 6–10¢| 358   | 46.4% | +0.85¢ |
| 10+¢ | 352   | 46.0% | **+2.94¢** |

### Interpretation

The raw numbers look OK on the surface (+1.32¢ avg, 49.7% win rate) but there are serious caveats:

**⚠️ Favorable market behavior bias (major):** The "fav" category (>40¢ markets) show high win rate (69%) but near-zero avg PnL (+0.17¢). This is because high-priced contracts that dip often recover — but the simulator exits at forced 4H maximum into settlement, where the contract goes to $0.01 or $1.00. These terminal bars are included and distort results.

**⚠️ Cheap market mean-reversion is weak:** Cheap contracts (<15¢) only win 36.5% of the time. A drop in a cheap market often means it's going to zero, not recovering.

**✅ The sweet spot appears to be mid-range markets (15–40¢):** 61.7% win rate, +1.63¢ avg PnL. This is the range Ian traded manually (buying at 20¢, selling at 22¢). The data supports this intuition.

**⚠️ Data is hourly, not tick-level.** The real buy-dip strategy uses limit orders at sub-hourly timescales. An hourly candle showing a 2¢ drop might reflect multiple intra-hour moves. The actual fill price in a real strategy would be better (buying inside the candle's range).

**⚠️ No transaction costs modeled for opponents' side.** Kalshi limit orders are fee-free, but the spread is real. On a 2¢ target, crossing the spread to fill eats into PnL.

### Dip Frequency

- 2,599 dip signals in 17,717 total bars
- **14.7% of all hourly bars trigger a dip-buy**
- With 480 tracked markets, that's ~0.15 dips/market/hour
- In active trading window (UTC 13–22), perhaps 1–2 signals per hour across all cities

**At $10/trade and +1.3¢ avg PnL:** that's ~$0.13 per trade × ~10 trades/day = ~$1.30/day gross. Not compelling at current scale.

---

## 5. Cross-City Lag Correlation (Front Propagation)

**Hypothesis:** Miami moves because of a warm front → Dallas/Houston follow 1–2 hours later.

| Metric | Value |
|--------|-------|
| City pairs analyzed | 150 |
| Mean same-hour correlation | 0.005 |
| Mean 1h-lag correlation | −0.015 |
| Mean 1h-reverse lag | 0.003 |

**Top city pairs by same-hour correlation:**
| City 1 | City 2 | Same-hour | Lag |
|--------|--------|-----------|-----|
| BOS | HOU | 0.152 | −0.018 |
| BOS | MIA | 0.071 | −0.119 |
| MIA | HOU | 0.030 | +0.062 |
| DAL | HOU | 0.021 | +0.034 |

**Fraction where 1h-lag > same-hour: 46.7%** (below 50%, i.e., slightly anti-evidence for front propagation)

**Verdict: No meaningful front propagation signal.** Same-hour correlations are near zero (0.005 avg), and lag correlations are slightly negative. The only cities with modest same-hour correlation are BOS–HOU and BOS–MIA, which is geographically surprising (not adjacent cities). This is likely noise.

**Why:** Weather fronts do propagate geographically, but Kalshi market prices are driven by NWP model updates (GFS/NAM), and all cities receive those model updates simultaneously. There's no information lag between cities from a model-update perspective.

---

## 6. Most Promising Intraday Strategy

### Strategy A: Mid-Range Mean-Reversion (Dip-Buyer)

**Mechanism:** Buy mid-range markets (15–40¢) after a ≥2¢ intra-hour dip. Exit at +2¢ recovery or after 4 hours.

**Evidence:** 61.7% win rate, +1.63¢ avg PnL on 1,034 historical signals.

**How to implement with Kalshi limit orders:**
1. Monitor active markets priced 15–40¢
2. When a market drops 2¢+ from its previous-hour price, post a limit buy 1¢ below current ask
3. Set a GTC limit sell at entry + 2¢
4. Cancel if not filled within 4 hours

**Risks:**
- Drop may be informationally driven (new obs, model update), not noise → it keeps falling
- Cheap liquidity at target = hard to exit at exactly +2¢
- Hourly data understates intra-hour volatility; real moves may be bigger/faster

### Strategy B: Evening ET Session Scalping (UTC 16–20)

**Mechanism:** During US afternoon (12PM–4PM ET), when abs moves are 3.3–3.7¢ and 33–43% of hours move ≥2¢, actively post tight limit orders at current bid+1¢, targeting the spread.

**Evidence:** UTC hour 16–20 shows consistently highest volatility in dataset.

**Note:** This is market-making, not directional trading. It requires real-time quote management.

### Strategy C: Watch for 10¢+ Dislocations

**Evidence:** When a market drops ≥10¢ in one hour (352 signals in data), avg PnL is +2.94¢ and win rate is 46%. Losses are larger but average outcome is better in absolute terms.

**Hypothesis:** Big drops (10¢+) often overshoot the new equilibrium, creating a larger mean-reversion opportunity.

---

## Caveats and Limitations

1. **Only 1H granularity available.** The `/history` endpoint returns 404 for weather markets. Tick-level data would be needed to properly analyze 15–30 min patterns, spread dynamics, and intra-hour mean-reversion.

2. **480 markets, 17 event dates.** The cross-city analysis is severely limited (only 17 date groups). The buy-dip analysis is better-powered (2,599 signals) but still not enormous.

3. **Settlement bars contaminate data.** The final 1–3 hours before settlement show extreme price moves (0.01 or 1.00). We excluded last 2 bars but this is imperfect.

4. **Look-ahead bias possible in strategy simulation.** The "exit at +2¢" check uses actual future prices — perfectly achievable with limit orders but in practice subject to fill uncertainty.

5. **The best finding (mid-range, 61.7% win rate) rests on 1,034 signals across 238 markets.** Statistically decent but not conclusive. Each event has its own weather/temperature regime that affects market dynamics.

6. **No account for spread costs.** Kalshi weather markets often have 2–4¢ spreads. Buying at ask and selling at bid to exit quickly could consume most of the expected PnL.

---

## Summary Table

| Question | Answer |
|----------|--------|
| 2¢+ move in 1H window? | 30% of hours. ~Every 3–4 hours per market |
| Momentum at 1H scale? | No. Mild mean-reversion (autocorr = −0.08) |
| Best trading hours (UTC)? | 16–20 (12–4PM ET) and 6–7 (2–3AM ET for GFS) |
| Buy-dip strategy overall? | Avg +1.32¢, 49.7% win rate. Marginal |
| Buy-dip mid-range markets? | **Avg +1.63¢, 61.7% win rate. More promising** |
| Front propagation? | No evidence (lag corr ≈ 0) |
| Most promising strategy? | Mid-range dip-buying during US afternoon hours |
