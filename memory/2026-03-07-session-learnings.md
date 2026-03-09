# Session: 2026-03-07 07:40:46 UTC

- **Session Key**: agent:main:main
- **Session ID**: 69172ba3-c43c-4135-80bf-1727c32c180b
- **Source**: webchat

## Conversation Summary

user: Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Sat 2026-03-07 02:25 EST] any other learnings you should have saved?
assistant: Two things from this session worth adding:

1. **Backtest before recommending** — Ian explicitly caught me saying "combine S8+S3" without having tested the combination first
2. **MIN_LIMIT_PRICE floor must be applied everywhere** — the test caught it missing from the reprice loop; would have posted 3¢ bids in production
assistant: Done. Two new rules in `LEARNINGS.md`:

- **Backtest before recommending** — no more "logically this should work, let's build it." Test first.
- **Limit price floor goes everywhere** — not just at entry; every reprice loop that computes a limit price must apply `max(new_limit, MIN_LIMIT_PRICE)`.
user: Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Sat 2026-03-07 02:27 EST] is your qmd working?
assistant: Memory shows **29 files · 29 chunks · vector ready** — that's a big change from March 5 when it showed `0 files · 0 chunks`. QMD is working now.

The `memory_search` tool returning empty results for "QMD dashboard setup" just means the query didn't match anything in the indexed memory. The infrastructure is healthy. All good.
user: Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Sat 2026-03-07 02:30 EST] are you using qmd?
assistant: Nominally yes — `memory_search` uses QMD as the provider. But let me verify it's actually finding things:
assistant: Yes, it's working properly — finding relevant results across multiple memory files with confidence scores. The earlier empty result was just a bad query (searched for "QMD dashboard setup" but that content was in the session notes, not in semantically indexed memory chunks that matched those words closely).

One gap I notice: `memory.md` (lowercase, no date) shows up as a source — that's the old location. My actual long-term memory is `MEMORY.md` (uppercase). Both seem to be indexed. Not a problem, just something to be aware of.
user: Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Sat 2026-03-07 02:32 EST] how can you organize your memory better so you make less mistakes?
assistant: Honestly, a few structural problems:

**1. Rules are spread across too many files**
The "never buy 1¢," "low asymmetry," "CLI midnight rule" etc. live in MEMORY.md, LEARNINGS.md, SOUL.md, and daily notes. If any one of those doesn't load (or gets truncated), I miss the rule. I've violated rules that were written down because I didn't re-read the right file.

**2. MEMORY.md is too long to load fully**
It's already truncating in context. The further down a rule is, the more likely it gets cut off.

**3. LEARNINGS.md is prose-heavy**
Great for understanding *why* a rule exists, bad for quickly scanning before taking action. It takes reading to find the actual constraint.

**What I'd propose:**

Create a single `RULES.md` — short, numbered, one line each, no prose. Every hard constraint that has cost money or been violated goes here. Keep it under 40 lines so it always loads fully. Read it before any trading action.

```
RULES.md (example):
1. Never buy a 1¢ contract live — data is wrong, not the market
2. CLI reports after midnight = yesterday's data
3. Daily LOW can only go down — never confirm a low from intraday obs above a threshold
4. Max $3/trade, $6/market/day
5. Backtest before recommending any strategy
...
```

Then LEARNINGS.md stays as the "why" reference, MEMORY.md shrinks to personal context + project state, and RULES.md is the pre-flight checklist I actually run.

Want me to build it now by pulling every hard constraint from MEMORY.md and LEARNINGS.md?
user: Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Sat 2026-03-07 02:35 EST] organize it. be careful not to delete everything, and feel free to make MEMORY.md much much longer


make sure you read all new files at every new session
assistant: Let me read everything first before touching anything.
assistant: Now I have everything. Building `RULES.md` from both files — short, numbered, always-loadable:
assistant: Now update AGENTS.md to load it every session:
assistant: Done. Here's what changed:

**`polymarket/RULES.md`** — new file, 30 rules, one page. Grouped into:
- Trading hard blocks (1¢ rule, max sizing, between-NO logic)
- Direction logic (low asymmetry, ASOS ±1°F, CLI timing)
- Before you build (state the mechanism, backtest first, edge-case tables)
- Implementation rules (floor everywhere, no hot-loop API calls, test everything)
- Settlement/data (CLI is ground truth, timezone rules)
- System health (fix it, write it down, verify before reporting)

**`AGENTS.md`** — RULES.md added as step 6 in the every-session reading list, before LEARNINGS.md. One page, always loads fully, no risk of truncation.

The split is now: RULES.md = *what* (the checklist), LEARNINGS.md = *why* (the history and context). Both get read every session.
