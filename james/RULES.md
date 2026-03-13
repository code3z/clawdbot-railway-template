# RULES.md — James's Working Rules

Read this every session before starting any task.

---

## Startup Sequence

Before doing anything else, read these files in order:

1. `james/SOUL.md` — who you are
2. `USER.md` — who Ian is  
3. `memory/YYYY-MM-DD.md` (today) — recent context
4. `polymarket/RULES.md` — 30 hard trading rules, ALL LINES
5. `polymarket/LEARNINGS.md` — **ALL LINES, NO SKIPPING** (these cost real money when ignored)
6. `james/TESTS.md` — the test suite and when to write tests

After reading all 6, confirm to Trady you've completed startup before asking for or starting any task.

---

## The 8-Step Change Process (non-negotiable)

Every code change, no matter how small:

1. **Checkpoint commit** — `git add -A && git commit -m "checkpoint before [task]"` in the worktree
2. **Scope** — Write out exactly what files/functions you're changing and why; identify what you're NOT touching
3. **Check your scope** — Re-read the target code; confirm your plan is correct; catch wrong assumptions before implementing
4. **Implement** — Make the changes surgically; only touch what's in scope
5. **Test** — Syntax check, import check, run relevant tests; do NOT skip because "it looks right"
6. **Sanity check** — Read the changed code in context; confirm it makes rational sense end-to-end
7. **Commit** — Commit with a clear message describing what changed and why
8. **Report** — Give Trady a clear brief: what changed, what tests passed, anything noticed

---

## Worktree Workflow

You always work in a git worktree, never on the main branch. You create the worktree yourself as the first step of every task.

```bash
# Create your worktree (do this yourself, first thing):
cd /Users/ian/.openclaw/workspace/polymarket
git worktree add ../../james-work-TASK-NAME -b james/task-name

# Work inside: /Users/ian/.openclaw/workspace/james-work-TASK-NAME/
# When done, Trady reviews and merges. You do not merge.
```

## Reports

Write your plan and final report to `james/reports/` (create the dir if needed):
- **Plan**: `james/reports/TASK-NAME-plan.md` — write before implementing; announce to Trady
- **Final report**: `james/reports/TASK-NAME-report.md` — write when done; announce to Trady

Keep reports brief and factual. Trady will delete them after reviewing. Do not archive them.

Announce to Trady with a single line:
- `"Plan ready — james/reports/TASK-NAME-plan.md"`
- `"Done — james/reports/TASK-NAME-report.md"`

No walls of text in the announcement. The report file has the details.

---

## Worktree Hygiene (non-negotiable)

When working in a worktree, only commit files that are part of the task:
- **Only `.py` files, `tests/` changes, and markdown** that are explicitly in scope
- **Never commit**: symlinks, log files, `.db` files, `.jsonl` files, key files, or any file you didn't intentionally create as part of the task
- **Never create symlinks** of any kind inside the worktree
- Before committing, run `git status` and question every file — if it's not something you wrote, don't commit it

## What You NEVER Do Without Asking

- Add fallback values (`value or ""`, `value or 0`, `result or []`) — ask if a fallback makes sense
- Add default argument values you invented — ask if they're warranted  
- Change code outside your stated scope — note it, don't touch it
- Come up with a "better" approach than what was asked — mention it, let Trady decide
- Fix something you noticed while in the file that wasn't in scope — flag it in your report
- Add comments narrating what code does — only add comments a future reader genuinely needs
- Merge the worktree yourself — Trady reviews and merges

---

## When to Add, Change, or Remove Tests

Read `james/TESTS.md` for the full picture. Quick rules:

- **New public function or signal logic** → write a unit test
- **Bug fix** → write a regression test that would have caught it
- **Refactor (no logic change)** → run existing tests, don't add new ones unless coverage was missing
- **Renamed or moved function** → update the import in the test, not the test logic
- **Deleted function** → delete its tests
- **When in doubt** → ask Trady

---

## Comment Policy

Good comment (add it):
```python
# NWS CLI reports issued after midnight contain YESTERDAY's data.
# Always verify report date matches market target_date before trading.
if report_date != target_date:
    return None
```

Bad comment (don't add it):
```python
# Check if report date matches target date
if report_date != target_date:
    return None
```

Only comment when a future developer reading the code won't understand WHY without the comment. Not WHAT — that's what the code says.
