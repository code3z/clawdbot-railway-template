# TESTS.md — The Trady Test Suite

Read this before touching any test file or deciding whether to write one.

---

## Overview

Tests live in `polymarket/tests/`. Run them with:

```bash
cd /Users/ian/.openclaw/workspace/polymarket
.venv/bin/python -m pytest tests/ -v
```

Run a single file:
```bash
.venv/bin/python -m pytest tests/test_unit_kelly.py -v
```

Run by marker:
```bash
.venv/bin/python -m pytest -m unit -v        # fast unit tests only
.venv/bin/python -m pytest -m integration -v  # tests that hit live APIs
```

---

## Test Files and What They Cover

| File | What it tests | Needs network? |
|---|---|---|
| `test_unit_imports.py` | All major modules import without error | No |
| `test_unit_kelly.py` | Kelly sizing, ensemble probability math | No |
| `test_unit_settlement.py` | Settlement logic, P&L calculation | No |
| `test_place_live_order.py` | `place_live_order()` — API path, auth, penny block | No (mocked) |
| `test_order_placement.py` | Order placement flow, dedup, error handling | No (mocked) |
| `test_disambiguation.py` | Disambiguation model feature builders | No |
| `test_late_night_signal.py` | Late-night confirmed signal logic | No |
| `test_declining_obs.py` | Declining obs / trough signal edge cases | No |
| `test_dsm_6hr.py` | DSM + 6-hour high signal parsing and dedup | No |
| `test_nbm_trader.py` | NBM forecast trader probability math | No |
| `test_obs_cache_integration.py` | Obs cache read/write against a real SQLite DB | No (temp DB) |
| `test_obs_poller.py` | Obs poller signal detection and DB writes | No (temp DB) |
| `conftest.py` | Shared fixtures: `DemoClient` for Kalshi demo API | Yes (demo API) |

---

## Why We Have Tests

This is a live trading system. Bugs cost real money. Tests exist to catch:

1. **Logic regressions** — a refactor that accidentally changes behavior
2. **API contract violations** — calling the wrong endpoint, wrong field name, wrong price direction
3. **Math errors** — Kelly sizing, probability calculations, settlement logic
4. **Import breakage** — a module that silently fails to import after a restructure

Tests are also documentation. `test_place_live_order.py` is the clearest description of what `place_live_order()` must do. Read the tests before reading the implementation.

---

## When to Write New Tests

**Write a test when:**
- You're adding a new public function that contains logic (not just a data fetch wrapper)
- You're fixing a bug — write a test that would have caught it before the fix
- You're adding a new signal type or trading decision path
- Trady explicitly asks you to

**Do NOT write tests when:**
- You're doing a pure refactor with no logic change (just run the existing tests)
- You're renaming or moving a function (update the import in existing tests)
- You're fixing a typo, comment, or docstring
- The function is a thin wrapper over an external API with no logic worth testing

**When in doubt:** ask Trady. Don't add tests speculatively.

---

## When to Modify Existing Tests

- **Renamed function** → update the import/call in the test; don't change assertions
- **Changed function signature** → update the call; preserve the assertion logic
- **Deleted function** → delete its test(s) entirely
- **Changed behavior intentionally** → update the assertion to match the new intended behavior, and explain why in the commit message
- **Test is testing the wrong thing** → flag it to Trady; don't fix it yourself

---

## Test Style

Tests use `pytest`. Follow the patterns already in the test files:

```python
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from my_module import my_function

@pytest.mark.unit
def test_my_function_basic_case():
    result = my_function(input_value)
    assert result == expected_value

@pytest.mark.unit
def test_my_function_edge_case():
    result = my_function(edge_input)
    assert result is None  # or whatever the contract says
```

Markers:
- `@pytest.mark.unit` — no network, fast, run always
- `@pytest.mark.integration` — hits live/demo APIs, run manually

Use `unittest.mock.patch` and `MagicMock` for mocking HTTP calls. See `test_place_live_order.py` for examples.

---

## The Import Smoke Test (always run this)

After any structural change (new file, moved function, renamed import):

```bash
.venv/bin/python -m pytest tests/test_unit_imports.py -v
```

If a module is newly added and heavily used, add it to the parametrize list in `test_unit_imports.py`.

---

## Running Tests in the Worktree

When working in a worktree, run tests from inside it:

```bash
cd /Users/ian/.openclaw/workspace/james-work-YYYY-MM-DD
.venv/bin/python -m pytest tests/ -v
```

The `.venv` is shared (symlinked from polymarket/), so packages are the same.
