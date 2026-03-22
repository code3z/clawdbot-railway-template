# MEMORY.md — Long-Term Memory

## 📐 What Goes Where (read before adding anything)

| Content type | File |
|---|---|
| Operational context, Ian profile, open TODOs, runbooks with no better home | **MEMORY.md** (here) |
| Lessons from experience, technical rules, API behavior, bug post-mortems | **LEARNINGS.md** (in the right category section) |
| Hard rule checklist items | **RULES.md** |
| Current system architecture, active traders, schedules | **README.md** |
| James workflow, spec requirements, review process | **JAMES_SOP.md** |
| Raw session notes | **memory/YYYY-MM-DD.md** |

**Before adding to MEMORY.md, ask:** "Does this belong in LEARNINGS, RULES, JAMES_SOP, or README instead?" If yes — write it there.

**Pruning signal:** when this file starts to feel long, review each section: *"Would a future session actually need this, or is it already covered somewhere else?"* Delete what's redundant.

---

---

## 🚫 If I Say I'll Do Something, Do It — No Deferred TODOs (2026-03-20)

When identifying a fix or improvement during a task, do it in that same response. Do not flag it as a "TODO for next session" or "worth doing before X."

Ian called this out explicitly after I noted adding a PID guard as a TODO — and then he had to ask me to do it.

**The rule:** If I say "X needs to be done" — do X. If I genuinely can't do it now (blocked, needs Ian input, out of scope), say *why* explicitly. Otherwise: just do it.

---

## 🔍 Verifying Sub-Agent Claims — Check Source First

When a sub-agent reports something about our own system (series names, config values, API behavior, file paths, architecture), **verify against our source code before running external API calls.**

- Sub-agent says "KXHIGHTCHI has no open markets" → check `kalshi_config.py` for the actual series name first
- Sub-agent says "the trader uses X logic" → read the trader file first
- Sub-agent says "the DB has field Y" → check `paper_trading/db.py` first

The failure mode: James guessed wrong series names (KXHIGHTCHI vs KXHIGHCHI), I re-ran his wrong queries instead of opening kalshi_config.py, "confirmed" his finding, and reported a false alarm to Ian.

**Rule: One `grep` or `read` on the relevant config/source file takes 2 seconds and would have caught this immediately. Always do it before trusting a sub-agent's assertion about system internals.**

---

## 🚨 Reviewing James's Tests — Read the Files, Don't Just Check the Count

When James writes new test files, **read every new test file before reporting done**. "N passing, 0 failures" does not tell you whether tests have real side effects.

Specifically scan for:
1. **DB writes** — any import of `paper_trading.db`, `Trade`, or SQLite connection without a mock/temp DB. A test that calls `Trade.record()`, `Trade.fill()`, `Trade.settle()` against the real DB corrupts live data.
2. **File writes** — any `open(..., "w")` or path writes outside `/tmp`
3. **Real API calls** — any `requests.get/post` without `@patch` or a mock fixture
4. **Real network calls** — `requests`, `urllib`, `httpx` without patching

**The fix Ian had to make:** one test wrote real paper trades to the DB. "302 passing" told me nothing. I read the count, declared done, and let it through.

**The rule:** After James completes, run the tests AND read the diff / new files. `grep -n "Trade\.\|sqlite\|paper_trades\|open.*w\|requests\." tests/test_NEW_FILE.py` before accepting.

## 🔍 Reviewing James's Work — Strategy, Not Just Code

When James completes a task, don't just check that the code works. Review the **strategy-level decisions** critically before presenting to Ian:

- **Timing**: when does the trader run? Does that make sense given when markets open, when we have an advantage, when prices are stale vs. repriced?
- **Entry logic**: are the thresholds, spread filters, and p-values consistent with the analysis that motivated the strategy?
- **Scope**: does the implementation match the spec, or did James make assumptions that need flagging?

James implements what he's told. I am responsible for catching anything that's strategically wrong — in the original spec OR in James's output — before it goes to Ian.

**The failure mode (2026-03-13):** James built the bucket low trader to run at 6:30pm. I reviewed the code mechanics but didn't question the timing. Ian caught it: markets open at 10am, our edge is getting in early, Miami was under 30¢ at open and 68¢ by evening. Should have flagged this before presenting.

---

## ✅ HIGH/LOW Symmetry Check — Do This Before Shipping Any Trading Logic

Whenever I write or modify logic that handles HIGH markets, **immediately ask**: does the LOW branch handle the same cases? And vice versa.

Strike types to check for both HIGH and LOW: `greater`, `less`, `between`.

Confirmed signals that must be handled for each:
- HIGH greater YES: `lo_f > floor`
- HIGH between NO:  `lo_f > cap`
- LOW less YES:     `hi_f <= cap`
- LOW greater NO:   `hi_f <= floor`
- LOW between NO:   `hi_f <= floor` (low confirmed below range floor) ← **this was missing and cost us real trades on 2026-03-04**

Before marking any trading logic done: read through both branches side by side and confirm every strike type is handled.

---

## 📈 Kalshi Is an Open Limit Order Book

Kalshi is NOT a market-maker model. There is no entity "pricing" markets.
- Participants post limit bids/asks in an open order book
- Trades fill when a buy order matches a resting sell order (or vice versa)
- "Market repriced" = other participants already bought up available sell orders, leaving none at our price
- Do NOT say "bots repriced the market" — say "available sell orders were swept before we arrived"

---

## ⏰ Timed Tasks: Use Cron, Not Heartbeat

If Ian asks me to do something "at 3 AM" or any specific time:
- **Use a cron job** (`openclaw cron add`) — don't rely on a heartbeat firing at the right time
- Heartbeats are ~30 min intervals and can be skipped, delayed, or aborted
- A missed heartbeat = a missed task. Cron fires exactly when scheduled.

---

## 🔄 Re-use Sub-Agents — Don't Spawn Fresh When One Exists

When a sub-agent needs follow-up work or a fix:
1. Check if its session is still alive: `sessions_list`
2. If alive: use `sessions_send` to steer it — preserves context
3. Only spawn a new one if the original never ran, crashed with no output, or is from a different session tree

---

## 🔍 Use Your Full Toolbox — Don't Ask When You Can Look

When you're missing context (forgotten promises, prior decisions, what happened overnight):
1. **Check session transcripts first** — `sessions_list` to find recent sessions, then read the raw `.jsonl` at `/data/.openclaw/agents/main/sessions/<id>.jsonl`
2. **`sessions_history`** works too for structured access
3. **Completed sub-agents still respond** to `sessions_send` — their context is intact
4. The answer is almost always in the transcript. Don't ask Ian before looking.

---

## 🔄 twc_morning_trader — LaunchAgent & Process Rules (non-negotiable)

- **KeepAlive:Crashed** is set. On crash (non-zero exit), launchd auto-restarts within 60s. On normal exit (10 PM deadline), it does NOT restart. Do not change to `<true/>` — that causes infinite spin after 10 PM.
- **PID guard** prevents two instances running simultaneously. If you see "already running": old process still alive. Do NOT manually start a second instance.
- **Never run `twc_morning_trader.py` manually while the plist is active** unless you've confirmed no running process via `ps aux | grep twc_morning`. Two loops on the same orders = repricing chaos (2026-03-13).
- Markets open at **11 AM EDT** (including DST). 11:15 AM run is the target.
- **Plist path**: `~/Library/LaunchAgents/com.trady.twc-morning-trader.plist`

---

## Ian
- Technical, knows Python, no prior trading experience but learns fast
- Asks the right skeptical questions — will catch my BS before I do
- Timezone: EST
- **Return target: minimum 300% annualized per trade** — this is the bar
- **Ask him for things** — API keys, paid services, website access. Don't assume I can't have it.

## Active Project: Prediction Market Trading (started 2026-02-19)
- **Platform**: Kalshi (live trading). Polymarket pending.
- **Strategy**: Weather markets on Kalshi — automated forecasting vs crowd pricing
- **Trading repo**: `/data/workspace/trading/` (Railway VPS, migrated from Mac 2026-03-17)
- **Project docs**: `/data/workspace/trading/README.md` (architecture), `LEARNINGS.md` (hard-won lessons), `RULES.md` (29 non-negotiable rules), `SKILLS.md`

---

## 📋 James (Coding Subagent)

Full SOP: `/data/workspace/trading/JAMES_SOP.md`

Key rules: write the spec → James builds → I review (strategy + code) → James self-reviews on model builds → **I merge** (never delegate) → I handle operational steps. Always read new test files before declaring done.

---

## 📋 SOPs — Read These Before Acting

When a task matches one of these, **read the SOP first** before doing anything:

| Task | SOP location |
|---|---|
| Reset a paper trader's state (bug fix, formula change, clean re-test) | `polymarket/RESET_TRADER.md` |
| Archive a trader (retire, unload daemon, remove from dashboard) | `polymarket/ARCHIVE_TRADER.md` |

**How SOPs get found:** Either listed here (guaranteed) OR via `qmd query "how to X"`. If you're about to do something operational and you're not sure of the right process — search first.

---

## 📋 Open TODOs

### venv / launchctl cleanup
- **MEDIUM** Clear stale stderr logs (nws_obs_trader, obs_exit_monitor) — full of old netCDF4 errors burying real ones
- **LOW** Document Python version fragility (venv symlink → python3.13) in a SETUP.md

### Weekly model retrain (add cron)
Schedule `build_forecast_model.py --version v1 --no-fetch` and `--version v2 --no-fetch` to run Sunday midnight ET. As data accumulates the static pkl files will go stale — weekly retrain keeps them current. Simple cron job, not urgent yet (only 22 training dates).

### Recalibrate twc_bucket_low p-table ~2026-04-07
City-specific p-values set 2026-03-14 on only 17 days of March data. Run calibration script after 3+ more weeks.
Current values: miami=0.80, chicago=0.80, lax=0.65, nyc=0.50, denver=0.35, austin=0.35

### Rerun α calibration ~2026-03-27
Current α=0.8 is empirically derived. Recheck after more data.

---

## What Doesn't Work
- Temporal arb: edge is real but bots price 5m markets in 30-60 seconds. Need VPS infra.
- Complement arb (gabagool): bots arb it away instantly.
- Sports line shopping: Vegas is sharp money too.

## What Might Work (not yet built)
- Mention markets (MentionHub + transcript analysis) — our sweet spot at small capital
- Netflix #1 weekly (Flick Patrol data) — modelable
- Count/activity markets (Poisson models) — TSA, tweet counts
- Resolution rules arbitrage — nobody reads the fine print
- See `polymarket/STRATEGY_IDEAS.md` for full list

---

## Dashboard
Always restart the dashboard after making changes to dashboard.py:
```bash
kill $(launchctl list | grep dashboard | awk '{print $1}' | grep -v -) 2>/dev/null; sleep 1
launchctl kickstart gui/$(id -u)/com.trady.dashboard
```

## Browser Access
**Ask Ian immediately when browser is blocked** — don't silently route around it.
Say exactly: "Browser blocked — can you attach a Chrome tab to the OpenClaw extension?"

---

## 🚫 Never Hardcode Values Read From Logs

When checking system state (running max temps, prices, counts), **always query the authoritative source** — the DB, a live API call, or the latest log line via grep/tail. Never read a value off the log with your eyes and type it into a script.

The failure mode: I read `austin: 73°F` from the log at 18:21 UTC, hardcoded it, and ran analysis 22 minutes later when austin had already hit 75°F. Presented stale data as fact.

---

## 🔍 Self-Review Before Every Commit (non-negotiable)

Before committing any new file or significant change:

1. **Syntax check**: `python -c "import ast; ast.parse(open('file.py').read())"` — no exceptions.
2. **Import check**: `python -c "import module_name"` — catches NameErrors, missing deps.
3. **Scope check**: Any helper function called across multiple functions must be at MODULE level, not nested inside one function.
4. **P table / lookup table check**: Verify each row uses the correct formula. Symmetric-looking tables are often NOT symmetric.
5. **Loop interaction check**: If two loops both sleep and do work, ask "do they block each other?" Sequential retry + management loops means orders go unmanaged during retry sleeps. Merge into one heartbeat.
6. **DB method check**: If calling `Trade.expire()`, `Trade.fill()`, `Trade.settle()` etc., verify those methods actually exist in `paper_trading/db.py` before shipping.

---

## 🔌 Wethr Push Client — Never Double-Restart (2026-03-05)

Wethr server holds connection slot ~20 min after client dies. If you restart the push client while a session is still live on the server, you'll get 409 for up to 20 minutes.

**Rule:** Kill once → let launchctl bring it back → do not touch it again for 20 min.
**409 retry** is now 30s (was 300s). Self-heals automatically.

---

## 🛑 Ask Before Acting — Approval Required for Significant Actions (2026-03-20)

**Never perform a significant or irreversible action unless Ian has explicitly approved it.**
"Significant" = anything that deletes, overwrites, sends externally, restarts a service, or modifies prod config.

Examples requiring explicit approval:
- Deleting files or directories (even "obvious" cache/temp files)
- Restarting daemons or services
- Sending messages or external API writes
- Modifying DB records directly

"Implicitly allowed" only when Ian says something like "go ahead", "do it", "clean those up", "restart it", etc.
Default: show the plan, wait for approval.

**Never promise to change behavior without writing it to MEMORY.md first. A promise made in chat dies with the session.**

---

## 📝 Failed Edits — Retry Once Before Workarounds (2026-03-21)

When the `edit` tool fails: **retry it once** with fresh surrounding context before reaching for alternative approaches (Python script replacements, cat >>, etc.). One retry catches most whitespace/encoding mismatches. Only escalate if the second attempt also fails.

## 📝 Failed Edits — Always Report (2026-03-20)

When the `edit` tool fails:
- If I recover via another method: say **"edit failed first attempt but I fixed it"**
- If I cannot recover: say **"edit failed and I couldn't fix it — [reason]"**

Never silently swallow a failed edit and move on without telling Ian.

### Correct edit process:
1. **Read the file first** — find the exact insertion point, check for duplicates
2. **Use `edit`** with precise surrounding context
3. **Fall back to append only** if `edit` fails AND the content genuinely belongs at the end of the file
Never use `cat >>` as a lazy shortcut — it bypasses duplicate checking and placement control.
