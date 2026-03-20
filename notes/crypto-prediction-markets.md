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
