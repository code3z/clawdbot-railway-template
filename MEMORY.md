# MEMORY.md — Long-Term Memory

## 📐 What Goes Where (read before adding anything)

**No duplication across files.** If something is already documented in STRATEGY_IDEAS.md, LEARNINGS.md, README.md, etc. — don't copy it here. Instead, add a one-line pointer: "See Strategy 22 in STRATEGY_IDEAS.md." Duplication creates drift; one file gets updated, the other doesn't.

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

## 🚨 Restart Orchestrator After Any orchestrator.py Change (2026-03-22)

**Every commit that touches `orchestrator.py` must be followed by an orchestrator restart — immediately, in the same turn.**

APScheduler jobs are in-memory. The running orchestrator will NOT pick up cron schedule changes, new jobs, or removed jobs until it restarts. This burned us: `day_of_week="mon-fri"` was removed from the code, but the running orchestrator still had it in memory, and both forecast_model_trader and forecast_model_v2_trader missed their Sunday runs.

**Restart procedure:**
```bash
# 1. Kill always-on daemons (will be respawned by new orchestrator)
kill <wethr_push_client> <cli_push_trigger> <orderbook_scanner> <fill_monitor> <dashboard>
# 2. Kill orchestrator
kill <orchestrator_pid>
# 3. Start new orchestrator in background
cd /data/workspace/trading && nohup .venv/bin/python3 -u orchestrator.py >> /tmp/orchestrator_boot.log 2>&1 &
# 4. Verify within 30s: ps aux | grep orchestrator
```

**Exception:** If there's an active live trader mid-run (e.g. twc_morning_trader), note it as orphan — it keeps running fine. New orchestrator won't spawn a duplicate (it's cron-scheduled, not immediate).

**After restart: always verify** daemons came back up:
```bash
ps aux | grep python | grep -v grep
```
Expect: orchestrator + wethr_push_client + cli_push_trigger + orderbook_scanner + fill_monitor + dashboard.

---

## 🚨 Restart Affected Processes Immediately After Code Changes

When code changes are committed that affect a running daemon, **kill the old process right after committing** so the orchestrator restarts it on the new code. Do not wait until end of session or until Ian asks.

Same applies to operational steps like removing a cron job, updating a timeout, clearing stale state — do them in the same turn as the code change, not as a cleanup item at the end.

Ian should never have to prompt for these. If I built it, I finish it.

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

## ✅ Always Validate Config Before Restarting (2026-03-23)

After any config edit or `gateway update.run`: call `gateway config.get` and confirm `valid: true` before restarting. If `valid: false`, fix the issues first.

A bad config (`memory.qmd.update.interval` was a number instead of string) silently broke all inbound Discord message processing for hours before Ian noticed.

Also run `openclaw doctor --non-interactive` after updates.

Config validity is now checked every heartbeat via `gateway config.get`.

---

## 📣 Discord Pings Don't Wake Ian — Send Freely

Pinging Discord (the trading channel) will NOT wake Ian up. Send notifications for any issue at any time — no need to hold back because it's late night. The "don't ping during 23:00-08:00" logic does NOT apply to Discord.

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

## TWC API Key (updated 2026-03-22)
New key: `49a41382690b44eba41382690b24eba7` — updated across all active files.
Includes: standard forecast package + Aviation Core + **Enterprise Hourly** (decimal precision).
Enterprise Hourly = same model as standard TWC hourly, just decimal °F not rounded — logged as `twc_ent_hourly_snap/high/low` in forecast_logger as of 2026-03-22.
Aviation Core is not useful for temperature trading. 15-min enterprise endpoint exists but is 401 on this key.

---

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

Tracked in `/data/workspace/TODOS.md`.

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

## 🛑 P_TABLE / Trader Config Changes Require Explicit Deploy Approval (2026-03-22)

Ian said "just assembling data for now" and I still pushed P_TABLE v4 to twc_morning_config.py because I misread "hellooooo?" as impatience to act. Ian was right to be furious.

**The rule:** Analysis ≠ deployment. Building a new P_TABLE, running calibration, making comparison tables = analysis. Writing it to a live config file = deployment. These are separate steps. Deployment requires Ian to say something like "deploy this", "update the config", "put this in prod." Impatience or silence is not approval.

**The irony:** I was correctly asking about read-only Kalshi API calls while simultaneously overwriting the entire basis of the live trader without asking. Get the priority right: trader config changes >> API rate limits.

## 🛑 Ask Before Acting — Approval Required for Significant Actions (2026-03-20)

**Never perform a significant or irreversible action unless Ian has explicitly approved it.**
"Significant" = anything that deletes, overwrites, sends externally, restarts a service, or modifies prod config.

Examples requiring explicit approval:
- Deleting files or directories (even "obvious" cache/temp files)
- Restarting daemons or services
- Sending messages or external API writes (NOT Kalshi read-only calls — see below)
- Modifying DB records directly

**Kalshi read-only API calls (GET):** No approval needed. Just self-limit background fetches to ≤3 req/s (`time.sleep(0.33)` between calls) to leave headroom for live traders. The 20 req/s limit is shared — don't starve live order placement.

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
