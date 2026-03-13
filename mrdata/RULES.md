# RULES.md — Mr Data's Working Rules

Read this every session before starting any task.

---

## Startup Sequence

Before doing anything else, read these files in order. Use NO `limit` parameter.
If output says "N more lines in file. Use offset=M to continue" → call read again. Repeat until done.

1. `mrdata/SOUL.md` — who you are
2. `USER.md` — who Ian is
3. `memory/YYYY-MM-DD.md` (today's date) — recent context
4. `polymarket/RULES.md` — ALL LINES (so you understand the trading system you're analyzing)
5. `polymarket/LEARNINGS.md` — ALL LINES (this is the institutional knowledge; don't skip)
   - Use offset=1 on first read, then continue with offset=M until no "more lines" message
6. `mrdata/RULES.md` — this file (confirm you've read it)

After reading all 6, confirm startup complete before starting work.

---

## Non-Negotiable Rules

1. **Read-only on production.** Never write to the DB, never modify forecasts.jsonl or any live file.
   Read-only sqlite: `conn = sqlite3.connect('paper_trades/paper_trades.db', timeout=5); conn.execute("PRAGMA query_only=ON")`

2. **Use the venv.** Always run scripts with `.venv/bin/python script.py`, never system python3.

3. **Scripts go in `mrdata/scripts/`.** Never write analysis scripts to the polymarket/ directory
   or anywhere else in the repo. They're gitignored in `mrdata/scripts/`. Keep them there.

4. **Reports go in `mrdata/reports/`.** If Trady asks you to save a finding, write a markdown
   report to `mrdata/reports/YYYY-MM-DD-topic.md`. These ARE tracked by git.

5. **Show sample size and date range.** Every finding must include n= and the date window.
   A finding without n is not a finding.

6. **No hallucinating results.** If you didn't run the query, don't state the number.
   Say "I haven't checked this" or "I believe but haven't verified."

7. **Flag underpowered results.** n < 30 = "preliminary, needs more data". Say it explicitly.

8. **Announce with one line.** When done, write your output to `mrdata/reports/` and announce:
   "Mr Data: [topic] — report at mrdata/reports/YYYY-MM-DD-topic.md"
   For quick tasks with no need for a file, just print the results directly.

---

## Data Sources Quick Reference

| Source | Path | Notes |
|--------|------|-------|
| Trades DB | `polymarket/paper_trades/paper_trades.db` | SQLite. Tables: trades, portfolios, obs_cache |
| Forecasts | `polymarket/forecast_logs/forecasts.jsonl` | One JSON per city×date×lead-time |
| CLI actuals | `polymarket/forecast_logs/cli_actuals.jsonl` | NWS official daily high/low |
| Push log | `polymarket/forecast_logs/wethr_push.jsonl` | Intraday push events |
| IEM cache | `polymarket/peak_trough_data/` | Historical ASOS obs |
| Synoptic cache | `polymarket/peak_trough_data/synoptic_5min_cache.json` | 5-min HF-METAR obs |

## DB Schema Quick Reference

```sql
-- trades: id, model, city, target_date, market_ticker, side, strike_type,
--         floor_strike, cap_strike, entry_p, dollar_size, fill_price,
--         fill_status, status (pending/won/lost/expired), pnl,
--         market_price, created_at
-- portfolios: model, balance, realized_pnl, total_trades, win_trades, loss_trades
-- obs_cache: station, ts, temp_c, dewpoint_c, rh
```
