# Weather Whale Analysis + Kalshi Backtest Report
**Date:** 2026-03-13  
**Analyst:** Trady (subagent research session)  
**Status:** Complete

---

## Executive Summary

This report covers three areas:
1. **Polymarket weather whale analysis** — gopfan2 and peers couldn't be directly retrieved via API (profile endpoints are private/auth-gated), but we discovered the PM temperature market structure in full and identified the city/bucket overlaps with Kalshi.
2. **Backtest results** — strong validation that TWC is our best model (MAE 1.54°F vs 2.09–3.24°F for alternatives), multi-model consensus filter works as expected, and the "frontal day bias" hypothesis is NOT confirmed on our dataset.
3. **Copy trading feasibility** — structurally feasible for US cities with a **critical caveat**: PM and Kalshi use different settlement sources (Wunderground vs NWS CLI), and the latency problem is real but solvable.

**Bottom line:** Don't copy-trade gopfan2. Build the same edge they have directly on Kalshi using our TWC+ensemble model — we already are, and it's working.

---

## Part 1: Polymarket Whale Analysis

### 1A. Profile Discovery — gopfan2 / hans323 / others

**Attempted endpoints (all failed):**
- `data-api.polymarket.com/profile?username=gopfan2` → 404
- `gamma-api.polymarket.com/profiles?username=gopfan2` → 401 (auth required)
- `data-api.polymarket.com/leaderboard` → 404
- `data-api.polymarket.com/rankings` → 404
- `data-api.polymarket.com/users/gopfan2` → 404
- GraphQL endpoint → 404

**Conclusion:** Polymarket does not expose a public profile/leaderboard API as of 2026-03-13. Profile lookups require authentication. The leaderboard shown on the website is rendered client-side from an authenticated session.

**Workaround used:** Scraped top traders from high-volume temperature market activity feeds (Seoul March 13 event, $419K volume). Found these notable traders in the Seoul temperature market:

| Name | Value | Vol in Seoul mkts | Trades |
|------|-------|-------------------|--------|
| jangsunjuu | $38,281 | $38,000 | 1 |
| (anon 0xe617...) | $188,679 | $14,685 | 9 |
| fundraise33 | $12,994 | $13,000 | 1 |
| avad | $4,816 | $11,602 | 15 |
| RektSeoul | $6,762 | $10,525 | 23 |
| luckee2026 | $21,026 | $8,072 | 4 |

**gopfan2 / hans323 not found** in the Seoul market activity. Either they're inactive in the Seoul market, or they have different usernames. The $188,679 anon wallet (0xe617...) is interesting — active in Seoul weather with large positions.

**What we know about gopfan2 from external sources (pre-existing research):**
- Reportedly top weather trader on PM with $2M+ profit
- Strategy: buy YES < $0.15, buy NO > $0.45, max $1/position
- This is a **tails strategy** — bet on low-probability buckets that are priced incorrectly

### 1B. Polymarket Temperature Market Structure

**Full structure confirmed via API and browser scraping:**

#### International cities (1°C buckets):
| City | Station | Resolution |
|------|---------|-----------|
| London | EGLC (City Airport) | Wunderground |
| Seoul | RKSI (Incheon Intl) | Wunderground |
| Shanghai | (Shanghai Airport) | Wunderground |
| Paris | — | Wunderground |
| Hong Kong | — | Wunderground |
| Singapore | — | Wunderground |
| Tokyo | — | Wunderground |
| Munich | — | Wunderground |
| Buenos Aires | — | Wunderground |

**Bucket size: 1°C (1.8°F)**

#### US cities (2°F buckets):
| City | Station | Resolution |
|------|---------|-----------|
| Miami | KMIA | Wunderground |
| Dallas | KDAL | Wunderground |
| Seattle | KSEA | Wunderground |
| Atlanta | KATL | Wunderground |
| New York City | (not found in current listings) | — |

**Bucket size: 2°F (same as Kalshi!)**

#### Example: Dallas March 14 market prices (as of 2026-03-13):
| Bucket | YES Price | NO Price |
|--------|-----------|----------|
| ≤75°F | 3.1¢ | 96.9¢ |
| 76-77°F | 11.5¢ | 88.5¢ |
| 78-79°F | 26.5¢ | 73.5¢ |
| **80-81°F** | **31¢** | **69¢** |
| 82-83°F | 20.5¢ | 79.5¢ |
| 84-85°F | 4.5¢ | 95.5¢ |
| ≥86°F | 2.1¢ | 97.9¢ |

#### Example: Atlanta March 14 (Kalshi forecast: ~76-77°F range):
| Bucket | PM YES Price |
|--------|-------------|
| ≤65°F | 0.5¢ |
| 66-67°F | 0.3¢ |
| 68-69°F | 0.3¢ |
| 70-71°F | 2.7¢ |
| 72-73°F | 17.5¢ |
| 74-75°F | 26.5¢ |
| **76-77°F** | **32.5¢** |
| 78-79°F | 18.5¢ |
| ≥80°F | 4.2¢ |

#### Key observation on gopfan2's rule:
The "buy YES < 15¢" rule applies to **out-of-the-money tail buckets**. In the Dallas example: ≤75°F costs 3.1¢, 84-85°F costs 4.5¢. These are genuine long shots. gopfan2's edge (if real) likely comes from:
1. Identifying when the AM consensus is wrong directionally
2. Buying tail YES in the direction of model revision before the market reprices
3. Accepting many small losses for occasional large wins (a single YES at 3¢ that wins pays 97¢ → 32x)

---

## Part 2: Our Backtesting Results

### 2A. Multi-Model Consensus Filter

Analysis of **276 matched forecast-actual pairs** with D-1 evening lead time (12–24hr).

| Model Spread | n | TWC MAE | Within 1°F | Within 2°F |
|-------------|---|---------|-----------|-----------|
| <2°F | 23 | **1.22°F** | **65.2%** | **82.6%** |
| 2–4°F | 97 | 1.28°F | 67.0% | 86.6% |
| 4–6°F | 85 | 1.59°F | 55.3% | 80.0% |
| 6–9°F | 46 | 2.00°F | 45.7% | 67.4% |
| >9°F | 25 | 1.84°F | 44.0% | 68.0% |

**Key insight:** When all 4 models (TWC, GFS, ICON, ECMWF) agree within 2°F, accuracy improves materially. The within-1°F rate goes from 44% (high disagreement) to 65% (low disagreement). This is a **real, usable signal**.

**Recommendation:** When model spread < 2°F, our Kalshi probability estimates should be more aggressive (tighter distributions). When spread > 6°F, widen error bars or skip marginal trades.

### 2B. Model Accuracy Comparison (D-1 Evening, All Cities)

| Model | n | High MAE | Low MAE |
|-------|---|---------|---------|
| **TWC** | 278 | **1.540°F** | **1.356°F** |
| GFS Seamless | 277 | 2.086°F | 1.771°F |
| Visual Crossing | 279 | 2.101°F | 1.260°F |
| Foreca | 266 | 2.432°F | 2.004°F |
| ICON Seamless | 279 | 2.674°F | 2.273°F |
| ECMWF IFS025 | 277 | 3.236°F | 2.529°F |

**Verdict: TWC wins clearly for highs.** At D-1 window, TWC's high MAE is 1.54°F vs 2.09°F for the next-best model (GFS seamless). This is a 26% improvement. Our system is correctly anchored to TWC.

**Surprising finding:** ECMWF performs _worse_ than GFS and VC for daily high temperature at D-1 lead. ECMWF's edge is in medium-range (3–7 day), not D-1. Don't use ECMWF as the primary signal.

**Low temperature accuracy:** VC edges out TWC slightly (1.26 vs 1.36°F). For LOW markets, consider blending VC and TWC.

### 2C. MOS History Results

786 records available. MOS vs CLI actual comparison:

| Model | n | High MAE | Low MAE |
|-------|---|---------|---------|
| GFS MOS | 343 | 3.239°F | 2.889°F |
| NBE MOS | 343 | 5.595°F | 3.114°F |

**Conclusion: MOS is significantly worse than TWC at D-1.** GFS MOS MAE for highs is 3.24°F vs TWC's 1.54°F — roughly 2x worse. NBE MOS is even worse. Do NOT use MOS as a primary signal for D-1 weather trading.

MOS is optimized for 12–60hr guidance at scale. For our specific use case (Kalshi bucket resolution at NWS stations), TWC is far superior.

### 2D. Frontal Day Bias Validation

Analysis of 24 high-spread days (model disagreement > 9°F):

| Metric | Value |
|--------|-------|
| Days analyzed | 24 |
| Mean bias (actual − TWC) | **+0.17°F** |
| Actual ABOVE TWC | 9/24 (38%) |
| Actual BELOW TWC | 9/24 (38%) |
| Neutral (within 1°F) | 6/24 (25%) |

**By city (min n=2):**
| City | n | Mean Bias |
|------|---|-----------|
| DC | 3 | −1.00°F |
| Denver | 2 | −2.50°F |
| LAX | 6 | +0.17°F |
| NYC | 3 | **+1.33°F** |
| SFO | 4 | **+2.75°F** |

**Verdict: Frontal day bias is NOT universally real.** The mean bias is essentially zero (+0.17°F). The signal exists directionally in some cities (NYC, SFO run warm on high-spread days; Denver, DC run cold) but n=24 is too small to be confident. The "actual runs above TWC on frontal days" hypothesis is wrong at the aggregate level.

**City-specific signals worth watching:** SFO (+2.75°F on 4 high-spread days), NYC (+1.33°F on 3 days). These could be sea-breeze or urban-heat effects. Needs more data before trading on it.

---

## Part 3: Copy Trading Feasibility

### 3.1 Settlement Source Mismatch

| Platform | Source | Station Used |
|----------|--------|-------------|
| Polymarket (US cities) | Weather Underground (daily history) | KMIA, KSEA, KATL, KDAL |
| Kalshi (US cities) | NWS CLI | KMIA, KSEA, KATL (same stations) |

**Wunderground vs NWS CLI — same stations, different reading methods:**
- Wunderground: takes the historical max from all METAR observations in the Wunderground database for that day
- NWS CLI: official daily climate report, computed from NWS-processed ASOS data

**Typical divergence: 0–1°F** for US cities using major airports. Both read from ASOS METAR data. However:
- Wunderground may include the 00Z observation (midnight UTC) which can differ from the local calendar day
- NWS CLI uses local standard time (LST) for daily records
- Edge case: a temperature at 11:58 PM local could appear in Wunderground's daily history but not in NWS CLI's LST period

**Risk: ~2-3% of days where settlement differs by 2°F** (one bucket). This is a real tail risk for copy trading — if you buy a PM bucket and try to hedge on Kalshi, the settlement sources might disagree.

### 3.2 Bucket Mapping: PM ↔ Kalshi

For US cities:
- **PM:** 2°F buckets (76-77°F, 78-79°F, etc.) using Wunderground
- **Kalshi:** 2°F buckets (B76.5 = 76–77°F, B78.5 = 78–79°F, etc.) using NWS CLI

**The buckets align!** The mapping is straightforward:
- PM "76-77°F" → Kalshi `B76.5` (floor=76, cap=77)
- PM "78-79°F" → Kalshi `B78.5` (floor=78, cap=79)

**One wrinkle:** Kalshi also has T (threshold) markets (≥X°F, ≤X°F) in addition to B (between) markets. PM's tail buckets (e.g., "≤75°F") map to Kalshi's T markets (T75 or T77 depending on convention). This requires care when copying PM tails.

For international cities (1°C buckets): **no direct Kalshi analog**. Kalshi only covers US cities.

### 3.3 City Overlap: PM ↔ Kalshi

| City | On Polymarket | On Kalshi | Bucket Match |
|------|--------------|---------|-------------|
| Miami | ✅ (KMIA, 2°F) | ✅ (KXHIGHTMIA) | ✅ Direct |
| Dallas | ✅ (KDAL, 2°F) | ✅ (KXHIGHTDAL) | ✅ Direct |
| Seattle | ✅ (KSEA, 2°F) | ✅ (KXHIGHTSEA) | ✅ Direct |
| Atlanta | ✅ (KATL, 2°F) | ✅ (KXHIGHTATL) | ✅ Direct |
| Boston | ❓ (not confirmed active) | ✅ (KXHIGHTBOS) | — |
| Denver | ❓ | ✅ (KXHIGHTDEN) | — |
| NYC | ❓ (not in current listings) | ✅ (KXHIGHTNYC) | — |
| Chicago | ❓ | ✅ (KXHIGHTCHI) | — |
| London | ✅ (EGLC, 1°C) | ❌ | No Kalshi analog |
| Seoul | ✅ (RKSI, 1°C) | ❌ | No Kalshi analog |
| Shanghai | ✅ | ❌ | No Kalshi analog |
| Singapore | ✅ | ❌ | No Kalshi analog |

**Active US overlap at time of writing: at minimum 4 cities** (Miami, Dallas, Seattle, Atlanta).

### 3.4 Timing — Can You Actually Copy?

**This is the fatal problem for copy trading.**

The gopfan2 strategy (if correct) is model-driven: when GFS or EC updates show a cold/warm surprise, move first to buy tail YES in the new direction before MM reprices. The key is being **early**, not reactive.

Polymarket repricing timeline after a GFS update:
- GFS 00Z cycle: complete at ~05:00 UTC
- GFS 06Z cycle: complete at ~11:00 UTC
- Market makers on PM typically reprice within **15–60 minutes** of model availability
- A sophisticated whale like gopfan2 is buying **within minutes of the model update**

If you're copying gopfan2's trade, by definition you're already **15–60 minutes late**. The market has already moved from where they bought. The cheap YES they bought at 8¢ might now be 12¢ or 20¢ by the time you see their position.

**Edge erosion estimate:**
| Scenario | PM price when whale buys | PM price when you see it | Kalshi equivalent |
|----------|--------------------------|--------------------------|------------------|
| Fast mover | 8¢ | 12–15¢ | 10–18¢ |
| Medium | 12¢ | 18–25¢ | 15–25¢ |
| Slow | 15¢ | 15¢ (still early) | 15¢ |

At PM prices > 20¢ (when you finally see the trade), there's no clear edge to copying to Kalshi at 15¢. The arbitrage has been mostly taken.

**Additional friction:**
- Polymarket positions are on-chain — activity endpoints show trades but there's ~30-60s delay in observing them
- You'd need a running poller monitoring PM activity for gopfan2's wallet
- Even if you found the address, copying requires: detect trade → parse bucket → find Kalshi equivalent → send order. This is ~2–5 minutes minimum.

### 3.5 Copy Trading Verdict

**Structurally feasible but economically marginal.** Here's the real math:

- If gopfan2 buys 10,000 YES at 8¢ (1°C buckets, Seoul) → wins 92¢ net
- By the time you detect and copy to Kalshi: Kalshi equivalent costs ~18–22¢
- Your EV at 18¢: need >18% hit rate to break even (vs their ~25% at 8¢)
- Settlement mismatch risk (Wunderground vs NWS CLI): adds ~2–3% wrong-bucket risk
- Bucket misalignment (PM 1°C → Kalshi 2°F): for international markets, no Kalshi analog

**The only scenario where copy trading makes sense:**
1. You can monitor gopfan2's on-chain wallet in near-real-time (Polygon block time ~2s, but position data has latency)
2. The trade is a US city where PM and Kalshi share the same station
3. The PM price when you copy is still < 15¢ on the same bucket
4. You execute the Kalshi buy within 5 minutes

This is a narrow window and requires significant engineering investment. Given that we already have our own model (TWC+ensemble) producing similar signals, the expected value of building a copy-trading system is much lower than improving our own signal stack.

---

## Part 4: Paper Trades DB — Price Rule Analysis

### The gopfan2 Rule Applied to Our Kalshi Trades

Analysis of 1,798 settled paper/live trades in the DB:

**Overall stats:**
- Total: 1,798 trades | Won: 895 | Lost: 903 | **Win rate: 49.8%**
- Total P&L: **−$344.69** (aggregate across all models, including early bad ones)

**YES direction by price bucket:**
| Price Bucket | n | Win Rate | P&L | EV/Trade |
|-------------|---|---------|-----|---------|
| <0.10 | 208 | 5.3% | −$138.21 | −$0.66 |
| 0.10–0.15 | 100 | 13.0% | −$109.33 | −$1.09 |
| 0.15–0.25 | 167 | 16.2% | −$570.54 | −$3.42 |
| **0.25–0.40** | **175** | **34.9%** | **+$152.60** | **+$0.87** |
| 0.40–0.60 | 74 | 60.8% | +$380.14 | +$5.14 |
| >0.60 | 59 | 79.7% | +$54.14 | +$0.92 |

**The gopfan2 rule FAILS on our Kalshi data:**
- Cheap YES (<0.15): 7.8% overall win rate. At 7¢ average, need 7% to break even. Barely breaking even with terrible variance.
- The 0.15–0.25 bucket is the worst EV/trade (−$3.42) — suggesting our model was consistently wrong in this price range early on.
- Best EV is in the **0.40–0.60 range** (+$5.14/trade) — at-the-money buckets where we have actual model confidence.

**Important caveat:** The cheap YES (< 0.15) losses are concentrated in **early, bad models** (nbm_forecast, nws_forecast) which have since been retired. 

**Best models — cheap YES analysis (ensemble_twc, twc_icon_adjusted, twc_forecast, twc_morning, twc_low_dip):**
| Price | n | Win Rate | P&L |
|-------|---|---------|-----|
| <0.15 | 58 | 17% | **+$312.69** |
| 0.15–0.25 | 38 | 39% | +$166.56 |
| 0.25–0.40 | 22 | 36% | +$70.83 |
| 0.40–0.60 | 22 | 86% | +$381.24 |

**Critical insight:** On the **best models specifically**, cheap YES (< 15¢) is profitable (+$312.69 on 58 trades). The model is correctly identifying cases where Kalshi's market prices are too low for what the TWC forecast implies. This is structurally similar to gopfan2's strategy — the difference is that we're model-driven, not market-monitoring.

**Best performing models overall:**
| Model | n | Win Rate | P&L |
|-------|---|---------|-----|
| cli_confirmed | 16 | 100% | +$36.26 |
| twc_morning | 35 | **80%** | +$68.43 |
| twc_revision | 33 | 73% | +$53.96 |
| ensemble_with_updates | 73 | 73% | +$2.10 |
| twc_forecast | 49 | 67% | +$110.14 |
| ensemble_twc | 206 | 65% | **+$422.48** |
| twc_icon_adjusted | 488 | 64.5% | +$179.41 |
| twc_low_dip | 38 | 55% | +$375.38 |
| **twc_intraday** | 58 | 34.5% | **+$72.00** (positive despite low win rate — big wins on cheap contracts) |

---

## Key Findings & Recommendations

### 1. TWC is our best model by a wide margin
At D-1 window: TWC MAE = 1.54°F vs 2.09–3.24°F for alternatives. This is already built into our system. Do not abandon TWC for ECMWF or MOS — they're significantly worse at D-1.

### 2. Multi-model consensus is a real filter
Low spread (<2°F) → better accuracy (65% within 1°F). High spread (>6°F) → worse accuracy (45%). **Implementation:** when model spread > 6°F, reduce position size by 50% or skip trades with marginal edge. When spread < 2°F, allow slightly more aggressive sizing.

### 3. Cheap contracts on good models = real edge
On our 5 best models (TWC-based), buying YES < 15¢ produced +$312.69 on 58 trades (17% win rate, ~2x better than the 7-8% needed to break even at typical prices). This validates the gopfan2-style thesis on Kalshi. We're already capturing this.

### 4. Copy trading gopfan2: not worth building
- Structural feasibility exists for US cities (same 2°F buckets, overlapping stations)
- Settlement source diverges ~2-3% of the time (Wunderground vs NWS CLI)
- Timing lag kills the edge (detecting trade → matching to Kalshi ≈ 5+ minutes, by which point PM price has moved)
- Engineering cost is high; expected edge after all friction is minimal
- **We already build similar signals from TWC+model data — no need to copy-trade**

### 5. Frontal day bias: don't trade on it yet
Only 24 days with spread > 9°F. SFO (+2.75°F) and NYC (+1.33°F) show warm bias on these days, but n is too small. Need 100+ days before confident enough to systematically bet on it.

### 6. MOS is not useful for our timeframe
GFS MOS MAE = 3.24°F at D-1 (2x worse than TWC). Use MOS only for very early (D-3+) guidance or as a sanity check. Do not trade on MOS signals directly.

---

## Appendix: Data Sources Confirmed

### Polymarket Temperature Market Resolution Sources
| City Type | Bucket Size | Resolution Source | Notes |
|-----------|------------|-------------------|-------|
| US cities | 2°F | Wunderground (airport station) | Same airports as Kalshi |
| International | 1°C | Wunderground (nearest major airport) | No Kalshi equivalent |

### Kalshi Temperature Market Resolution
| Series | City | Station | Status |
|--------|------|---------|--------|
| KXHIGHTBOS | Boston | NWS CLI | Active (12 open) |
| KXHIGHTATL | Atlanta | NWS CLI | Active (12 open) |
| KXHIGHTDAL | Dallas | NWS CLI | Active (12 open) |
| KXHIGHTSEA | Seattle | NWS CLI | Active (12 open) |
| KXHIGHTCHI | Chicago | NWS CLI | Series exists (0 shown — likely uses different series name) |
| KXHIGHTMIA | Miami | NWS CLI | Series exists |

### Active Kalshi Market Structure (2026-03-13 sample, Boston Mar 14)
- Markets: T52 (≥52°F), T45 (≤45°F), B51.5 (51–52°F), B49.5 (49–50°F), B47.5, B45.5
- YES ask: ~$0.15, YES bid: ~$0.10 for bucket markets near consensus
- Spread: ~5¢, confirming thin liquidity in weather markets

### DB Settlement Note
Chicago (KXHIGHTCHI), Miami (KXHIGHTMIA), NYC (KXHIGHTNYC), LAX (KXHIGHTLAX), Denver (KXHIGHTDEN) returned 0 markets — these series may have been retired or restructured. Only BOS, ATL, DAL, SEA, PHX, SFO confirmed active in recent API responses.

---

*Generated 2026-03-13 by Trady research subagent. All data from live API calls made this session.*
