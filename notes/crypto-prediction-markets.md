# Crypto Prediction Markets — Research Notes

_Started: 2026-03-19_

---

## Platforms

### Kalshi (preferred)
- **URL**: https://kalshi.com/category/crypto/frequency/fifteen_min
- **Regulatory**: CFTC-regulated US exchange
- **Resolution**: **CF Benchmarks RTI (CFB)** — average of 60 seconds of data (1 price/sec) from multiple exchanges (Coinbase, Bitstamp, itBit, Kraken, Gemini, LMAX), taken in the final minute before expiry
- **4% annual interest paid on open positions** — materially affects longer-dated market math
- **Launched 15-min markets**: December 2025

### Polymarket (secondary)
- **URL**: https://polymarket.com/crypto/15M (also has 5-min)
- **Resolution**: **Chainlink BTC/USD oracle** — single on-chain price snapshot at expiry
- **Launched**: October 2025
- **Volume**: ~$70M/day across short-term crypto contracts (as of March 2026)
- **Requires**: USDC on Polygon (separate capital pool from Kalshi's USD)

### Available Cryptos (Kalshi)
BTC, ETH, DOGE, SOL, XRP, BNB, HYPE (low liquidity — avoid for algo)

---

## Kalshi Market Structure Taxonomy

| Timeframe | Contract Type | Question Asked | Options Analog |
|---|---|---|---|
| 15-min | **European binary** | "Will BTC be higher/lower in 15 min?" | ATM digital option |
| 1-hour | **European binary** | "Will BTC be above/below $X at end of hour?" | OTM digital option |
| Daily | **European binary** | "Will BTC be above/below $X at end of day?" | OTM digital option |
| Weekly | **European binary** | "Will BTC be above/below $X at end of week?" | OTM digital option |
| Monthly | **Lookback** | "What's the highest BTC will reach this month?" | Lookback call option |
| Annual | **European binary** | "Will BTC be above/below $X at end of year?" | OTM digital option |

**Key**: All markets except monthly resolve at a single point in time (end of period). "Will it reach X" means "will it be at or above X at expiry" — not a touch option.

**Important**: Daily and hourly markets that share the same expiry time (e.g., both end at 5pm EDT) are **the same market** — not two separate contracts. There is no pair to trade against each other across timeframes for the same event.

### Markets are only open during their own period
- Can't pre-trade the next 15-min window
- Kills most traditional calendar spread strategies (those require buying farther-dated options while you still have time)
- Does NOT kill: cross-timeframe arb on markets running simultaneously (hourly + daily are both open at the same time)

---

## Fee Structures

### Kalshi
- **Formula**: `fee = 0.07 × C × P × (1-P)` where C = contracts, P = price
- **Max fee**: **1.75¢ per contract at 50¢** (parabolic shape)
- Near-zero at extremes (good — enables tail trading)
- 4% annual interest on open positions (important for weekly/monthly)
- Deposit: ACH/wire/crypto/PayPal/Venmo = no fee; debit card = 2%

### Polymarket (taker fees, enabled Jan 2026)
- **Formula**: `fee = shares × price × 0.25 × (price × (1-price))²`
- **Max fee**: **~1.56% at 50¢** (quartic curve — much steeper than Kalshi)
- Near-zero at extremes
- **Maker rebate**: 20% of collected fees paid daily in USDC

### Fee Comparison at 50¢ ($100 position)
| Platform | Fee on $100 at 50¢ |
|---|---|
| Kalshi | ~$1.75 (1.75¢ × 100 contracts) |
| Polymarket | ~$1.56 per $100 face value |

Kalshi is marginally cheaper near 50¢; both near-zero at extremes.

---

## Cross-Venue Arbitrage (Kalshi ↔ Polymarket, 15-min only)

### The Concept
When `YES on Kalshi + NO on Polymarket < $1.00` (or vice versa), a box arb exists.

Example: Kalshi YES @ $0.48 + Polymarket NO @ $0.45 = **$0.93 cost → $0.07 gross profit**

### ⚠️ The Oracle Divergence Problem (Critical Risk)
**Polymarket** uses Chainlink (single snapshot) and **Kalshi** uses CFB RTI (60-second average in final minute). These can diverge during sharp BTC moves near expiry.

**Result**: Both contracts can resolve in the same direction → lose both legs simultaneously.  
The open-source bot author calls these **"dead zones"** — caused wipeouts despite overall profitability.

### Open Source Bot
**Repo**: https://github.com/rao/pm-kalshi-arbitrage-bot  
**Runtime**: Bun (v1.0+) | **Status**: Works, made money, not sustainable without dead-zone mitigation

#### Architecture
```
Binance BTC Price Feed ──────────────────────┐
Polymarket WS ──→ Normalize ──┐              │
                               ├──→ Scanner ──┼──→ Guards ──→ Executor
Kalshi WS ──────→ Normalize ──┘              │              ├──→ Leg A (FOK)
Market Discovery ────────────────────────────┘              ├──→ Leg B (FOK)
                                                             └──→ Unwind
```

#### Key Risk Parameters
| Parameter | Value | Notes |
|---|---|---|
| minEdgeNet | $0.04 | Min net edge after fees + slippage |
| slippageBufferPerLeg | $0.005 | Per leg |
| maxLegDelayMs | 500ms | Between Leg A and Leg B |
| maxDailyLoss | $20 | Kill switch |
| preCloseUnwindMs | 70s | Exit before rollover |
| noNewPositionsCutoffMs | 75s | Block new positions before rollover |

#### Scripts
```bash
bun run discover        # Current interval market mapping
bun run dev             # Dry-run (no real trades)
bun run live            # Live trading
bun scripts/sell-all-positions.ts  # Emergency exit
```

---

## Cross-Timeframe Implied Vol Analysis (Kalshi-only)

Since hourly/daily/weekly markets that share an expiry time are the **same market** (not separate), there's no direct cross-timeframe box arb. What exists instead is a **vol surface consistency check** across different expiry times and strikes.

### European Binary Implied Vol (all non-monthly markets)

For a European binary call "will BTC be above $X at expiry?", the Black-Scholes price is:

```
P = N(d₂)
d₂ = [ln(S/X) + (r - σ²/2)T] / (σ√T)

For r≈0:
d₂ = ln(S/X)/(σ√T) - σ√T/2

→ Invert numerically to get σ_implied from observed price P
```

**Key property for European binaries — not monotone in time**:
- **Deep OTM** (BTC well below target $X): longer-dated IS worth more — more time for price to reach X
- **Deep ITM** (BTC well above X): shorter-dated worth MORE — longer-dated has more time to fall back below X
- **At the money**: roughly equal (symmetric distribution)

This is unlike vanilla calls (always worth more with more time). It means you can't make simple directional predictions about whether the weekly or daily should be "higher" without knowing moneyness.

### What You Can Compare

Different expiry times with different strikes but inferable from the same σ:
- If 4pm hourly "BTC above $87k" is at 60¢ and the weekly "BTC above $87k" is at 40¢, extract the σ implied by each and compare to realized BTC vol
- If implied σ from the hourly is 80% annualized but realized is 55%, the hourly is overpriced → buy NO (equivalent to shorting)
- If implied σ from weekly is 30% annualized but realized is 55%, the weekly is underpriced → buy YES

### Monthly Lookback Market
The monthly "highest price BTC reaches" is a **lookback call**. Approximate expected max of a GBM:
```
E[max S_t] ≈ S₀ × (1 + σ√(2T/π))
```
Extract implied σ from weekly markets, price the expected max, compare to Kalshi's offering. If Kalshi's monthly market is cheap relative to weekly-implied vol → buy.

---

## Options Theory That Translates (and What Doesn't)

### ✅ What Translates
| Traditional Strategy | Kalshi Equivalent |
|---|---|
| Vol surface / term structure analysis | Extract implied σ per expiry and strike; compare to realized vol; trade outliers |
| Variance premium capture | Sell short-term contracts where implied σ >> realized BTC vol |
| Lookback option pricing | Monthly "highest price" market vs implied σ from weekly European binaries |

### ❌ What Doesn't Translate
| Traditional Strategy | Why It Fails |
|---|---|
| Calendar spread (classic) | Markets only open during their own period — can't hold across rollovers; same expiry = same market |
| Calendar spread no-arb constraint | Only holds for American/touch options; Kalshi markets (except monthly) are European — no monotone P(T2) ≥ P(T1) |
| Delta hedging across expiries | Each period has its own reference price; no shared rolling underlying |
| VIX roll-down (short near-term vol) | No margin/borrow mechanism — but buying NO is economically equivalent to shorting YES (same payoff, prepaid and capped). Fees may still kill edge near 50¢. |

### The Critical Insight: Different Reference Prices
Each 15-min window has its own reference price. "Will BTC be higher in 15 min?" at 3:00pm and 3:15pm are completely different bets. They can legitimately disagree without any arb.

---

## Strategy Matrix (Kalshi-focused)

| Strategy | Markets Used | Edge Type | Difficulty | Risk |
|---|---|---|---|---|
| Cross-timeframe touch arb | Hourly + daily "reach X" | Pure no-arb | Medium | Leg execution timing |
| Implied vol surface scan | All timeframes | Statistical | High | Model error |
| Monthly lookback pricing | Weekly + monthly | Fundamental | High | Illiquid |
| Late entry near-certain | 15-min | Probability | Low | Late reversal |
| Order book imbalance | 15-min | Microstructure | High | API latency |
| Cross-crypto correlation | BTC + ETH same strike | Statistical | Medium | Correlation breakdown |

### ❌ What Doesn't Work
- Scalping mean reversion near 50¢ — fee curve kills it
- Manual trading on 15-min — too slow
- Trading HYPE or low-liquidity tickers — spread is too wide
- Ignoring oracle divergence on cross-venue arb

---

## Open Questions
- [ ] What strike prices does Kalshi offer for each timeframe — how many levels, how spaced?
- [ ] Does Kalshi have a maker rebate or liquidity incentive program of its own?
- [ ] What's the interest rate accrual mechanism — does 4% apply to 15-min markets or only longer-dated?
- [ ] Monthly lookback: what does it actually pay out — nearest dollar increment, exact max, or a range?
- [ ] Cross-venue (Polymarket/Kalshi) dead zone frequency — needed before scaling 15-min arb
- [ ] Is realized BTC vol materially different across 15-min vs hourly vs daily horizons? (vol of vol effect)
- [ ] What's the bid/ask spread on hourly and weekly markets vs 15-min — is there enough liquidity to extract edge?

---

---

## Full Backtest Analysis — March 20, 2026 (30-day dataset)

### Dataset
- **3,000 settled KXBTC15M windows** (Feb 16 – Mar 20, 2026) — ~32 days
- **37,077 1-minute candle rows** with yes_ask, yes_bid, mid, volume, outcome
- **BTC prices**: Binance BTCUSD 1-min klines (≈0.008% premium vs BRTI — negligible)
- CF Benchmarks BRTI API requires paid license — unusable. Binance is adequate proxy.
- Scripts: `notes/btc15m_backtest.py` → `notes/btc15m_history.csv`

### Key Methodology Note: Market Mid Is the Right Signal
Using BTC-vs-reference% as a signal requires a BTC price source that matches BRTI (the actual settlement index). Instead: the **Kalshi market mid price at window open IS the aggregated BRTI signal** — traders set it by watching BRTI live. No external BTC source needed for the signal.

---

### Finding 1 (RETRACTED): Below-Reference Bias

Original 500-window analysis (5-day data) showed +37% ROI when BTC was 0.1-0.5% below reference. After expanding to 3,000 windows (30 days), this collapsed to only +5.9% net ROI. The 5-day sample was one calm BTC regime; the 30-day dataset includes the drop from $96k to $68k where mean reversion fails.

**Status: Retracted. Not reliable enough to trade.**

---

### Finding 2 (CURRENT): Market Mid Calibration Edge

The market is well-calibrated across most of the price curve. Two bands show systematic mispricing (first-candle-only analysis, N=2,952 unique windows):

| Band | N windows | Win rate | Market mid | Edge | Net ROI | Z | p | Bonferroni |
|---|---|---|---|---|---|---|---|---|
| YES mid 0.45–0.50 | 515 | 51.8% | 47.5% | +4.3% | +3.8% | 1.98 | 0.048 | ❌ fails |
| **YES mid 0.60–0.65** | **295** | **70.2%** | **62.1%** | **+8.1%** | **+8.9%** | **3.02** | **0.0025** | ✅ barely |

**Frequency**: 10% of windows qualify for the 0.60–0.65 band → ~9-10/day

**Mechanism**: When a window opens with BTC slightly above the reference (market ~60-65¢), retail traders sell YES expecting a pullback. But BTC above the reference tends to stay there more than the market prices. The *market's* 62% is consistently wrong — actual win rate is 70%.

---

### Finding 3 (KEY): Edge Is Only at Window Open

The 0.60–0.65 edge exists ONLY in the first 3 minutes. After that, the market reprices:

| Time in window | N | Win rate | Net ROI | Z | p |
|---|---|---|---|---|---|
| **Open (0–3 min)** | **540** | **68.3%** | **+5.9%** | **3.07** | **0.002** ✅ |
| Early (3–7 min) | 773 | 65.5% | +1.0% | 1.80 | 0.072 |
| Mid (7–11 min) | 406 | 62.1% | -4.3% | -0.10 | 0.92 — no edge |
| Late (11–15 min) | 181 | 67.4% | +3.8% | 1.39 | 0.16 |

**Execution requirement**: Must enter within first 3 minutes of each window or the edge is gone.

---

### Finding 4 (CRITICAL): Prior Window = NO Amplifies Edge Massively

Splitting the 0.60–0.65 band by whether the prior window resolved YES or NO:

| Prior window | N | Win rate | Net ROI | Z | p |
|---|---|---|---|---|---|
| **Prior = NO** | **169** | **74.0%** | **+14.9%** | **3.51** | **0.0005** ✅✅ |
| Prior = YES | 126 | 65.1% | +0.9% | 0.69 | 0.49 — no edge |
| All (baseline) | 295 | 70.2% | +8.9% | 3.02 | 0.0025 |

**The entire edge lives in the "Prior = NO" case.** When the prior window resolved YES (BTC stayed above its reference), the current 60–65¢ mid has essentially no edge. When the prior window resolved NO (BTC fell below its reference), the current window opening at 60–65¢ has +14.9% net ROI.

**Mechanism (likely)**: Prior window NO means BTC dipped below the prior reference. Current window opens with BTC having recovered above the new reference (mid 60-65¢). This recovery/bounce pattern — a dip followed by a move back above — tends to have continuation. The market doesn't fully price in this continuation.

This is somewhat counter to pure momentum (prior YES is NOT better), but it's a bounce/recovery play: after a failed window, the correction tends to overshoot.

---

### Finding 5: US Afternoon (14–20 ET) Drives Most Edge

Splitting the 0.60–0.65 band by time of day:

| Session (ET) | N | Win rate | Net ROI | Z | p |
|---|---|---|---|---|---|
| Overnight 00–09 | 116 | 68.1% | +5.8% | 1.39 | 0.17 |
| Morning 09–14 | 64 | 64.1% | -0.8% | 0.31 | 0.76 — no edge |
| **Afternoon 14–20** | **79** | **78.5%** | **+22.0%** | **3.53** | **0.0004** ✅✅ |
| Evening 20–24 | 36 | 69.4% | +7.8% | 0.97 | 0.33 |

**US afternoon (2–8pm ET) is the sweet spot.** The morning session has no edge at all. The afternoon edge is enormous — 78.5% win rate at +22% net ROI.

---

### Trading Signal Summary (As Of March 20)

**Entry conditions (all must be met):**
1. Window just opened (remaining ≥ 13 min — enter in first 3 min)
2. Market YES mid = 0.60–0.65
3. Prior window resolved NO
4. Time: 14:00–20:00 ET (optional but boosts edge significantly)

**Expected edge:**
- All qualifying (prior=NO): N=169, WR=74%, Net ROI **+14.9%**, z=3.51, p=0.0005
- US afternoon + prior=NO: N~50-60 (estimated), Net ROI likely **>20%**

**Frequency estimate:**
- 0.60–0.65 band: 10% of windows × 96/day = ~9-10/day
- Prior=NO condition: ~57% of those (169/295) → ~5-6/day
- US afternoon only (14-20 ET, 24 of 96 windows = 25%): ~1-2/day in the highest-conviction band

**Capital efficiency:**
- $100 deployed → +14.9% → +$14.90 per trade
- 5 trades/day at that rate → +$74.50/day → ~74.5%/day not realistic (not all windows qualify simultaneously)
- Realistic: 2-5 qualifying windows/day at +8-15% each → 1-3% daily returns → ~365-1095% annualized

---

### Caveats & Known Risks

1. **Bonferroni**: 0.60-0.65 base band barely survives (p=0.0025 at threshold). Further splits (prior=NO) reduce N to 169 — now post-hoc on 2 dimensions. True confidence is lower than z=3.51 implies.
2. **30-day sample**: One BTC regime (major downtrend $96k→$68k). Edge may differ in bull or sideways regimes.
3. **Execution gap**: 3-minute entry window. Need automated entry. Manual trading will miss fills.
4. **Entry price**: Analysis uses candle close price. Real fills at ask (+0.5¢ average) reduce ROI slightly.
5. **Fill rate at limit**: If we bid below ask to improve price, fill rate drops. Need to measure vs buy-at-ask tradeoff.

---

### Open Questions
- [ ] Does the prior=NO + afternoon edge hold in different BTC regimes (bull, sideways)?
- [ ] Is the afternoon edge (14-20 ET) due to US liquidity, or institutional BTC activity patterns?
- [ ] What's the mechanism for prior=NO amplifying the edge? (bounce/recovery vs something structural)
- [ ] What exit strategy: hold to window close (binary) or exit early if price moves favorably?
- [ ] Can we run this automatically with limit orders? What's the execution architecture?
- [ ] Does the edge compound? If we enter window N+1 after a NO in window N, does window N+2 after another NO have further edge?

---

## Live Data Analysis — March 20, 2026 (Early / Superseded)

### Data Collected
- 500 settled KXBTC15M windows (March 15–20, 2026)
- 6,262 1-minute candle rows with BTC spot prices joined
- Tools: `notes/btc15m_backtest.py`, `notes/btc15m_history.csv`

### Finding 1: Slightly-Below-Reference Bias (HIGH CONFIDENCE)

**Signal:** BTC is 0.1%–0.5% below the reference price at window open (12–15m remaining)

| Metric | Value |
|---|---|
| N (windows) | 71 unique |
| Market avg YES price | 40.3¢ |
| Actual YES win rate | 56.1% |
| Edge | **+15.8%** |
| EV per contract | **+$0.152** |
| ROI per trade | **+37%** |
| Z-score / p-value | 3.40 / 0.0007 ✅ |
| Frequency | ~14% of windows (~14/day) |

**Mechanism:** When BTC dips slightly below the reference at window open, retail oversells YES (recency/loss-aversion bias). A 0.1–0.5% move is tiny — BTC recovers more than half the time in 15 minutes. Market prices YES at 40¢ when fair value is ~56¢.

**Trade:** Buy YES at ~41¢ (or bid 50¢ and collect whatever fills). Expected +37% ROI per qualifying trade.

**Calibration check passes:** ATM (±0.1%) shows -0.003 edge — market is efficient there. Bias is specific to the slightly-below zone.

**Deep below (-0.5% to -1.5%):** Market correctly prices YES low (6–7¢), actual win rate 0%. No edge there.

### Open Questions
- [ ] Is the +15.8% edge stable across days, or driven by a few windows?
- [ ] Symmetric check: does BTC slightly ABOVE reference create BUY NO edge?
- [ ] Variance premium on daily OTM markets — still untested
- [ ] Bid at 50¢ vs buy at ask — which gets better fills in practice?
- [ ] What's the max size the market can absorb without moving the price?

### Hypothesis Checks (same 500-window dataset)

**H1 — Symmetry (BTC above reference):**
- BTC +0.1% to +0.5% above ref: WR=0.617, mid=0.604, edge=+0.013 → **no edge**
- BUY NO there: ROI=-4.9% → negative
- Bias is **one-directional only** (downside dip = retail panic-sells YES)

**H2 — Momentum:**
- Prior window YES → edge=+0.197 | Prior window NO → edge=+0.099
- Prior 2 YES → edge=+0.219 | Prior 2 NO → edge=+0.091
- Small N (10–36), treat as directional signal only, not reliable standalone

**H3 — Time of Day (in signal zone):**

| Session (ET) | N | WR | Edge | EV/contract |
|---|---|---|---|---|
| 00-09 overnight | 29 | 41.4% | +0.048 | +$0.043 |
| 09-12 US open | 20 | 60.0% | +0.235 | +$0.230 |
| 12-16 midday | 28 | 57.1% | +0.124 | +$0.119 |
| 16-20 after close | 11 | 72.7% | +0.242 | +$0.235 |
| 20-24 evening | 26 | 61.5% | +0.222 | +$0.215 |

**Overnight edge essentially disappears. Trade US hours only (09:00–24:00 ET).**

### ⚠️ Outstanding Validation Questions
- [ ] Are fills actually achievable at yes_ask with $20 position size?
- [ ] Is the edge stable day-by-day or driven by a few windows?
- [ ] Does the 1-min candle price accurately represent what we'd actually pay?
- [ ] Any look-ahead bias in the data join (BTC price timing)?
