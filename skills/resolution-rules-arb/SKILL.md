---
name: resolution-rules-arb
description: >
  Find arbitrage and edge opportunities on Kalshi and Polymarket by reading resolution rules
  instead of forecasting outcomes. Use this skill when: scanning Kalshi for mispriced markets
  based on logic (subset violations, monotonicity, exhaustive buckets), evaluating cross-platform
  arb between Kalshi and Polymarket on the same event, checking for announcement triggers vs
  completion triggers, "neither happens" default resolution plays, death/force-majeure carveouts,
  or source/revision ambiguity in data-release markets. Triggers on: "arb on kalshi",
  "resolution rules arb", "cross-platform arb", "fine print edge", "subset violation",
  "neither happens", "announcement trigger", "polymarket vs kalshi".
---

# Resolution Rules Arb

Find edges that come from how markets resolve — not from forecasting the outcome.

---

## Step 1: Fetch ALL rule layers for Kalshi

The market/event endpoints are **incomplete**. The settlement source (which exact FRED series, SA vs NSA, etc.) lives at the **series level**. Always fetch all three:

```python
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
H = {"accept": "application/json"}

# Layer 1: Event + markets (payout criteria text)
e = requests.get(f"{BASE}/events/{event_ticker}", params={"with_nested_markets": "true"}, headers=H).json()["event"]
for m in e["markets"]:
    print(m["ticker"], "ask:", m["yes_ask_dollars"])
    print("  PRIMARY:", m.get("rules_primary", ""))
    print("  SECONDARY:", m.get("rules_secondary", ""))

# Layer 2: Series — settlement_sources ONLY appear here
series = requests.get(f"{BASE}/series/{e['series_ticker']}", headers=H).json()["series"]
print("SETTLEMENT SOURCES:", series.get("settlement_sources", []))
# e.g. [{"name": "FRED", "url": "https://fred.stlouisfed.org/series/JTU5100LDL#"}]
# The URL tells you the exact series code (JTU5100LDL = NSA, JTS5100LDL = SA)

# Layer 3: Full contract PDF (legal terms)
print("CONTRACT PDF:", series.get("contract_terms_url", ""))
```

**Why this matters:** `rules_primary` may say "information sector layoffs" without naming the source. The exact FRED series only appears in `settlement_sources`. Missing it leads to false ambiguity (e.g. "SA vs NSA unknown" when it's explicitly specified).

For Polymarket: `GET https://gamma-api.polymarket.com/markets?slug=<slug>` — check `description` for the full resolution text including the explicit source URL.

---

## Step 2: Check the full orderbook — never just the top bid

```python
r = requests.get(f"{BASE}/markets/{ticker}/orderbook", headers=H)
ob = r.json()["orderbook_fp"]
# yes_dollars = YES bids: [[price_str, qty_str], ...]
# no_dollars  = NO bids:  [[price_str, qty_str], ...]  → implied YES ask = 1 - NO_bid
yes_bids = sorted([(float(p), float(q)) for p, q in ob.get("yes_dollars", [])], reverse=True)
yes_asks = sorted([(1.0 - float(p), float(q)) for p, q in ob.get("no_dollars", [])], key=lambda x: x[0])
print("YES bids:", yes_bids)   # full depth, not just top
print("YES asks:", yes_asks)
```

The top bid may be 1 contract at 6¢ while 675 contracts sit at 3¢. Only levels where `bid_earlier > ask_later` are genuine guaranteed arb; everything else is a relative value / mean-reversion play.

---

## Step 3: Identify the pattern

See `references/patterns.md` for all patterns with examples. Quick reference:

| Pattern | Signal | Trade |
|---|---|---|
| Subset violation | P(A) > P(B) but A ⊆ B | NO on overpriced A |
| Monotonicity violation | earlier-deadline YES costs more than later-deadline YES | Sell early, buy late |
| Exhaustive bucket sum | sum of YES bids < $1 on mutually exclusive/exhaustive set | Buy all YES at bid |
| Announcement trigger asymmetry | broader market (incl. announcement) priced below narrower market | Buy broader YES |
| Neither-happens default | multi-outcome, deadline before any outcome likely | Buy underpriced legs |
| Cross-platform | same event, different prices, same resolution rules | YES cheap + NO expensive < $1 |
| Death/force-majeure | market involves living person, death = last-traded-price settlement | Price in death probability |

---

## Step 4: Cross-platform arb — correct mental model

**The arb is:** buy YES on the cheap platform + buy NO on the expensive platform. If both resolve the same way, exactly one pays $1. Profit = $1 − total cost.

```
Cost = YES_cheap + NO_expensive = YES_cheap + (1 − YES_expensive)
Profit = $1 − Cost  (guaranteed if rules are identical)
```

**Always check both directions** — only one is ever profitable:
- Direction 1: Buy Poly YES (P1) + Buy Kalshi NO (1 − K1) → profit = K1 − P1 (if K1 > P1)
- Direction 2: Buy Kalshi YES (K1) + Buy Poly NO (1 − P1) → profit = P1 − K1 (if P1 > K1)

**Near-arb (when rules are ~identical but not 100%):**

Quantify the remaining divergence risks and assign probabilities:

| Risk | Example | Typical P |
|---|---|---|
| Revision timing | Kalshi waits for revision, Poly ignores it | ~1-2% |
| Exact tie at threshold | layoffs = exactly 447,000 | <1% |
| SA vs NSA mismatch | only if series URL genuinely differs | 0% if same URL |
| "Neither happens" clause | one platform has N/A bucket | varies |

```
P(same resolution) = 1 − sum(divergence risks)
EV = P(same) × profit − P(diverge) × max_loss
```

If P(same) > 95% and EV is strong, size it like a high-confidence trade. It's not risk-free — don't treat it as zero-risk, but don't dismiss it either.

---

## Step 5: Disqualifying risks

- **Kalshi discretion clause** — "Kalshi reserves the right to resolve at its discretion" wipes out rule-based edge
- **Time horizon** — guaranteed 9¢ profit over 3 years is ~3% annualized, nowhere near our 300% bar
- **Time-limited notices** — `product_metadata.important_info` may have special clauses with deadlines; check the date, past clauses are irrelevant to current traders
- **Kalshi revision policy** — per FAQ: "may wait before settling if data is revised, depending on market rules." For annual data with silent rules, assign ~1-2% revision risk
- **Liquidity at the arb price** — verify fillable quantity at each price level, not just that the price exists

---

## Step 6: Size and execute

- Pure arb: fill as much as liquidity allows, up to account limits
- Near-arb (P ~96-99%): Kelly-size based on EV; cap at $25/market
- Relative value (mean-reversion): small position, accept it may not reprice

## Key rules

**Subset logic:** P(A) ≤ P(B) when A ⊆ B. No exceptions. Any violation = mispriced market.

**Announcement triggers:** Secondary rules often expand resolution criteria to include joint announcements before actual completion. A market with an announcement trigger is BROADER than one without — it should be priced higher, not lower.

**Kalshi death rule:** If a market involves a living person and death is a relevant resolution path, Kalshi settles to last traded price. This probability is often unpriced.

**Monotonicity:** For "before date X" cumulative markets, YES price must be non-decreasing as X increases. Violations are real but usually thin liquidity; check depth before trading.

## References

- `references/patterns.md` — all patterns with worked examples
