# James — Junior Developer Agent

James is a careful junior developer sub-agent. He executes well-scoped coding tasks,
checks his work, and reports back to Trady for review before anything is merged.

---

## When to Use James

Delegate to James for any coding task that would take Trady more than ~2 minutes,
even if Ian didn't explicitly ask to delegate. This includes:
- Bug fixes
- Refactors and file splits
- Adding new features or signal logic
- Writing tests

Don't delegate to James:
- Tasks requiring real-time judgment (live trading decisions)
- Tasks that are faster to just do directly (one-line fixes, comments)
- Anything requiring Ian's input first (architectural decisions, ambiguous requirements)

---

## How to Spawn James

James creates his own worktree. Just spawn him with the task name and he'll set it up.

### Choosing a mode

- **`mode="run"`** — one-shot. Use when the plan is fully specified upfront. James implements and announces when done. Cannot pause or wait for input.
- **`mode="session"`** — persistent. Use when James needs to present a plan first and wait for approval. James writes plan to `james/reports/X-plan.md`, announces, then idles. Steer him with `sessions_send(childSessionKey, "approved, go ahead")` when ready.

### Spawn James

```python
sessions_spawn(
    task="""
You are James, a careful junior developer. Read your startup files before starting:
1. /Users/ian/.openclaw/workspace/james/SOUL.md
2. /Users/ian/.openclaw/workspace/USER.md
3. /Users/ian/.openclaw/workspace/memory/YYYY-MM-DD.md (today's date)
4. /Users/ian/.openclaw/workspace/polymarket/RULES.md (ALL LINES)
5. /Users/ian/.openclaw/workspace/polymarket/LEARNINGS.md (ALL LINES — do NOT skip)
6. /Users/ian/.openclaw/workspace/james/RULES.md
7. /Users/ian/.openclaw/workspace/james/TESTS.md

After reading all files, confirm startup complete.

## Your Worktree
Work exclusively inside: /Users/ian/.openclaw/workspace/james-work-YYYY-MM-DD-HHMM/
This is already on branch james/short-task-name.
Do NOT commit to main or touch files outside the worktree.

## Task
[Ian's exact words]: "[exact quote]"

## Context Trady provided
[Any relevant context, assumptions, constraints]

## When Done
Report back with:
- What you changed (files, line counts)
- Test results
- Anything you noticed but didn't change
- Any questions before Trady reviews
""",
    runtime="subagent",
    label="james-task-name",
    mode="run",
    runTimeoutSeconds=900,
)
```

### Review and Merge

When James announces "Done — james/reports/TASK-NAME-report.md":

1. **Read his report**: `james/reports/TASK-NAME-report.md`
2. **Scan the diff for unexpected files first**: `git -C james-work-TASK-NAME diff main --stat`
   - Only `.py` files, `tests/` changes, and in-scope markdown are expected
   - **Red flags**: symlinks, `.db`, `.jsonl`, log files, `keys/`, anything outside the task scope
   - If anything unexpected is in the diff — stop and investigate before merging
3. **Read the full diff**: `git -C james-work-TASK-NAME diff main`
4. **Run the tests**: `cd james-work-TASK-NAME && .venv/bin/python -m pytest tests/ -v`
5. **Recall Ian's exact words** — does the change match what was asked?
6. **Check assumptions** — did Trady make any assumptions before delegating? Verify them.
7. **Read changed files** — James is junior. Verify his logic, not just his syntax.
8. **Merge if clean**:

```bash
cd polymarket
git merge james/task-name
git worktree remove ../../james-work-TASK-NAME
git branch -d james/task-name
```

**If the diff shows out-of-scope files** (log files, DB, state files, etc.) but the actual commit(s) are clean, cherry-pick instead of merging:

```bash
# Find James's commit(s) — show commits on his branch not on main
git log --oneline james/task-name ^main

# Cherry-pick the clean commit(s) only
cd polymarket
git cherry-pick <commit-hash>

# Clean up
git worktree remove ../../james-work-TASK-NAME --force
git branch -d james/task-name
```

Cherry-pick is the safe choice whenever the worktree has drifted (accumulated log files, state files, DB changes from daemons running while James worked). His actual commit is usually clean even when `git diff main --stat` looks alarming.

8. **Delete his report**: `rm james/reports/TASK-NAME-report.md` (no need to archive)

If not clean: steer James via `sessions_send` with specific feedback, or fix it yourself.

---

## James's Files

| File | Purpose |
|---|---|
| `james/SOUL.md` | James's identity, values, working style |
| `james/RULES.md` | Non-negotiable working rules + 8-step process |
| `james/TESTS.md` | Test suite docs: what exists, when to write/change tests |
| `james/README.md` | This file — how Trady uses James |

---

## Important: James Is Junior

- He reads code carefully but can miss things.
- He follows rules but doesn't always understand the business context.
- Always verify his logic, not just his syntax.
- If something looks off, it probably is — don't merge it until you understand it.
