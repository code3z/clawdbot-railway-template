# Resolution Rules Arb Patterns

## Pattern 1: "Neither happens" / Default resolution

Many multi-outcome markets resolve N-way equally if no qualifying event occurs before the deadline. This creates exploitable mispricings when one outcome is clearly impossible but the market treats it as independent.

**Classic example: Jesus returns before GTA6 (Polymarket, July deadline)**
- Market priced Jesus at ~10% YES
- Correct price: ~50% — if neither GTA6 nor Jesus arrives by July, market resolves 50/50
- Edge: buy YES on Jesus for ~5x return vs fair value
- **Trigger to look for:** markets framed as "X before Y" where neither X nor Y is likely to happen before the deadline

**How to identify:** Read the resolution rules carefully. Does it say "if neither occurs, resolves N/A" or "resolves 50/50 between options"? Many Kalshi/Polymarket "who does X first" markets split equally on no-trigger.

---

## Pattern 2: Subset logic violation

If event A is a strict subset of event B (A can only happen when B does), then P(A) ≤ P(B). Violations mean one market is mispriced.

**Example: Greenland**
- "Will US purchase Greenland from Denmark?" (28¢) — requires financial transaction specifically with Denmark
- "Will US pay any money for Greenland?" (implied ~22¢ from price buckets) — broader, any acquisition with money
- "Purchase from Denmark" ⊆ "any monetary acquisition" → 28¢ > 22¢ is logically impossible → KXGREENLAND-29 slightly overpriced

**How to check:** For any two related markets, ask: "Can A happen without B?" If no, then P(A) ≤ P(B). Price violations = arb.

---

## Pattern 3: Announcement trigger vs. actual completion

Some Kalshi territory/acquisition markets resolve YES on a **joint announcement** even before actual transfer. Others require completed transfer only.

**How to identify:** Look for secondary rules containing: "An announcement by the United States and the entity that controls [territory] that it will happen is also encompassed by the Payout Criterion."

**Edge:** Markets with announcement triggers will resolve earlier and at a lower bar than buyers may expect. The "acquire" market (announcement counts) vs "purchase" market (actual financial transaction required) can diverge significantly on a news event.

---

## Pattern 4: "Can't trade on death" rule (Kalshi-specific)

Kalshi rules prohibit markets that resolve based on a person's death. If a market involves a living person and they die, Kalshi typically settles to **last traded price**, not YES or NO.

**Example: Supreme Leader of Iran death market** — when he died, market settled to last traded price rather than resolving YES. People who shorted the last traded price (betting on resolution) vs held YES positions got burned.

**How to exploit:** If you see a market involving a living person where death is a relevant path to YES resolution, the market may be mispriced because death-path probability isn't being reflected. Check if the resolution rules have a death-carveout.

**Check Kalshi rules at:** https://kalshi.com/legal/market-rules (or similar)

---

## Pattern 5: Source/revision ambiguity

Markets resolving based on data releases often don't specify:
- Which estimate (advance, second, third/final for GDP)
- Which source (BLS vs FRED, seasonally adjusted vs not, annualized vs raw)
- Which exchange/index for crypto/price markets

**Example: GDP >5% market** — rules say "GDP growth above 5%" with no secondary rules. Doesn't specify advance vs final estimate. If the advance estimate is 5.1% but gets revised to 4.9%, does it resolve YES?

**How to find edge:** When a market resolves on a quantitative data release, find the exact source in the rules. If it's not specified, research how Kalshi has resolved similar markets historically (check their resolution history or ask support).

---

## Pattern 6: Cross-platform same-event arb (Kalshi vs Polymarket)

Same underlying event, two platforms, potentially different prices AND different resolution rules.

**Key risks:**
- Resolution rules may differ subtly (one uses advance GDP, other uses final)
- Settlement timing may differ (one closes when event occurs, other has a hard date)
- One platform may add "NaN/N/A" resolution clause the other doesn't
- Counterparty/platform risk: if one platform has issues, you're exposed

**Process:**
1. Confirm both markets resolve on the exact same event/source/date
2. Check for announcement triggers, revision clauses, death carveouts on BOTH
3. If rules are truly identical, price difference = arb (accounting for fees ~2%)
4. Document the exact delta and expected hold time

---

## Pattern 7: "Including/excluding" boundary cases

Watch for markets where the resolution criterion includes a boundary that's ambiguous.

**Examples:**
- "Above 5%" — does 5.000% qualify? Usually means strictly above.
- "Before January 20, 2029" — does January 20 count? Usually means before midnight UTC on that date.
- "At least part of Greenland" — one square meter qualifies?
- Rounding rules: KXGREENLANDPRICE secondary rules specify amounts < $500M round to $0 (resolves "no acquisition" bucket even if technically money changed hands)

**Look for:** Numbers near thresholds, ambiguous prepositions (before/by/through), what happens at exactly the boundary value.

---

## Checklist for analyzing any market pair

1. **What exactly triggers YES? What triggers NO? What triggers N/A or settlement at last price?**
2. **Are there announcement triggers vs. completion triggers?**
3. **What is the resolution source? Which revision/estimate?**
4. **Is there a death carveout, force majeure, or platform discretion clause?**
5. **For cross-market:** Are the two sets of resolution criteria identical? Draw a Venn diagram of scenarios.
6. **Subset check:** Is one market's YES condition a strict subset of the other's? If so, price comparison is constrained.
7. **Default resolution:** What happens if nothing occurs by the deadline? Equal split? N/A? Resolves NO?
8. **Timing:** Do both markets close at the same time? Earlier resolution = less time for your edge to play out.
