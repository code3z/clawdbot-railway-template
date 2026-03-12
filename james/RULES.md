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

You always work in a git worktree, never on the main branch.

```bash
# Trady will create the worktree before spawning you:
git -C polymarket worktree add ../james-work-YYYY-MM-DD -b james/task-name

# You work inside: /Users/ian/.openclaw/workspace/james-work-YYYY-MM-DD/
# When done, Trady reviews and merges. You do not merge.
```

When reporting back, always include:
- The worktree path
- The git diff summary (what files changed, +/- line counts)
- Test results
- Any questions or concerns before Trady reviews

---

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
