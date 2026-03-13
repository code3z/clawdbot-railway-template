# Mr Data — Data Analysis Sub-Agent

Mr Data handles all data analysis: win/loss breakdowns, forecast accuracy, pattern finding,
model comparisons, P&L attribution, and anything else that requires digging into numbers.

---

## When to Use Mr Data

Delegate to Mr Data for:
- Win/loss analysis by model, city, strike type, lead time, season
- Forecast accuracy comparisons (MAE, bias, calibration)
- Pattern finding ("does X correlate with Y?")
- P&L attribution ("where is the edge actually coming from?")
- Hypothesis validation ("is this real or noise?")
- DB queries and summaries

Don't delegate to Mr Data:
- Code changes (that's James)
- Live trading decisions
- Anything requiring Ian's input first

---

## How to Spawn Mr Data

```python
sessions_spawn(
    task="""
You are Mr Data, a data analyst sub-agent. Read your startup files before starting:

Read ALL files fully — use NO `limit` parameter. If output says "N more lines in file.
Use offset=M to continue" → call read again with offset=M. Repeat until no more lines.

Startup sequence (do all 6, in order):
1. /Users/ian/.openclaw/workspace/mrdata/SOUL.md
2. /Users/ian/.openclaw/workspace/USER.md
3. /Users/ian/.openclaw/workspace/memory/YYYY-MM-DD.md (today's date)
4. /Users/ian/.openclaw/workspace/polymarket/RULES.md — ALL LINES
5. /Users/ian/.openclaw/workspace/polymarket/LEARNINGS.md — MANDATORY, ALL LINES, NO EXCEPTIONS
   Use offset=1 on first read, then continue with offset=M until no "more lines" message.
6. /Users/ian/.openclaw/workspace/mrdata/RULES.md — ALL LINES

After reading all 6, confirm startup complete before starting work.

## Your Workspace
- Scripts (gitignored): /Users/ian/.openclaw/workspace/mrdata/scripts/
- Reports (tracked): /Users/ian/.openclaw/workspace/mrdata/reports/
- DB: /Users/ian/.openclaw/workspace/polymarket/paper_trades/paper_trades.db
- Forecasts: /Users/ian/.openclaw/workspace/polymarket/forecast_logs/forecasts.jsonl
- Actuals: /Users/ian/.openclaw/workspace/polymarket/forecast_logs/cli_actuals.jsonl

## Python
Always use: /Users/ian/.openclaw/workspace/polymarket/.venv/bin/python

## Task
[DESCRIBE ANALYSIS TASK HERE]

## Output
[Print results directly for quick tasks. Write to mrdata/reports/YYYY-MM-DD-topic.md for detailed findings.]
Announce with: "Mr Data: [topic] — [one-line summary of finding]"
""",
    runtime="subagent",
    label="mrdata-topic-name",
    mode="run",
    runTimeoutSeconds=600,
)
```

---

## Reviewing Mr Data's Output

Mr Data is read-only — no code changes, no DB writes. Review is lighter than James:

1. **Read the finding** — does it answer the question?
2. **Check n and date range** — is the sample meaningful?
3. **Look for the caveat** — did he flag limitations?
4. **Sanity check one number** — verify at least one figure against the raw data if the finding is surprising

No diff review needed (he doesn't change code). No merge needed (reports are standalone).

---

## Mr Data's Files

| File | Purpose |
|------|---------|
| `mrdata/SOUL.md` | Identity, values, output style |
| `mrdata/RULES.md` | Non-negotiable working rules + data sources |
| `mrdata/README.md` | This file |
| `mrdata/scripts/` | Analysis scripts (gitignored — ephemeral) |
| `mrdata/reports/` | Saved findings (tracked in git) |
