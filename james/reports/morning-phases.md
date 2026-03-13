# Report: morning-phases

## Branch
`james/morning-phases` — worktree at `/Users/ian/.openclaw/james-work-morning-phases/`

## Changes

### 1. New 3-phase wall-clock manage loop (`twc_morning_trader.py`)

Extracted phase logic into a standalone helper:
```python
def _compute_phase_limit(current_ask, max_limit, et_hour) -> (new_limit, note_key):
    if et_hour < 17:   return _cp(min(current_ask - 0.01, max_limit)), "bidb"
    elif et_hour < 21: return _cp(min(current_ask, max_limit)),         "bida"
    else:              return _cp(min(current_ask + 0.01, max_limit)),  "take_it"
```

Replaced the old phase 1/2/3/4 block (hours-elapsed / hours-remaining logic, S15_DROP
special case, `effective_max`) with a call to this helper. `MIN_LIMIT_PRICE` floor still
applied after. All other manage loop logic (`_mark_filled`, deadline expiry,
`_reconcile_with_kalshi`) is unchanged.

The old variables removed: `open_ask`, `hours_elapsed`, `hours_remaining`, `phase`,
`effective_max`. These were only used in the replaced block.

### 2. 1 PM launchctl plist (`launchctl/com.trady.twc-morning-trader-1pm.plist`)

Mirrors `com.trady.twc-morning-trader.plist` with:
- Label: `com.trady.twc-morning-trader-1pm`
- Hour=13, Minute=0
- Extra args: `--run-id 1pm`
- Same stdout/stderr log paths (tagged in output by "1 PM RUN" header)

Added `main_1pm()` in `twc_morning_trader.py`:
1. Fetches `kalshi_balance` via `fetch_kalshi_balance()`
2. Queries DB for `SUM(dollar_size)` where `model=twc_morning AND fill_status IN ('limit_pending', 'deferred') AND target_date=tomorrow`
3. `available = max(0, kalshi_balance - deployed_capital)`
4. If `available < 1.0` → prints "No spare cash to deploy" and exits
5. Calls `scan_and_build_candidates(bankroll_override=available)` and `place_initial_orders(..., available_override=available)`
6. Cities with existing active orders are skipped by the no-duplicate guard (Change 3)

Added `bankroll_override` param to `scan_and_build_candidates` and `available_override` param to `place_initial_orders`. The `--run-id 1pm` flag is detected in `__main__` before the existing command dispatch.

### 3. No-duplicate guard in `place_initial_orders()`

Before placing any order (and before the orderbook fetch), checks the DB:
```sql
SELECT 1 FROM trades
WHERE model=? AND city=? AND target_date=?
  AND fill_status IN ('limit_pending', 'deferred', 'filled')
LIMIT 1
```
If a row exists, skips with:
```
[city] already has active order for {target_date}, skipping
```

## Tests
- 9 new tests in `tests/test_twc_morning_phases.py`
- 8 unit tests for `_compute_phase_limit`: phase boundaries (14→bidb, 17→bida, 21→take_it), boundary hours (16, 20), max_limit capping for all three phases
- 1 unit test for the no-duplicate guard (mocks DB returning a row, asserts result is [])
- **164 total tests pass** (155 original + 9 new)

## Constraints verified
- `max_limit` computation unchanged — new logic reads `o["max_limit"]` directly
- `_mark_filled`, deadline expiry block, `_reconcile_with_kalshi` all untouched
- `twc_morning_sims.py` not touched
- `fetch_kalshi_balance()` not touched

## One thing to flag
`_ask_depth_profile` is now imported but unused in `twc_morning_trader.py`. It was
previously called in the old phase 3/4 depth-logging blocks. It's still imported from
`twc_morning_orders`. Removing the import is one line but I left it since it's out of
stated scope. Trady can clean it up at merge time if preferred.
