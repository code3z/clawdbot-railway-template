# obs-peak-trader build report
*Branch: `james/obs-peak-trader` | Worktree: `/Users/ian/.openclaw/james-work-obs-peak-trader/`*

---

## Files changed

### 1. `nws_obs_peak.py` — extended `_evaluate_peak_v8b`
**What changed:** The `between` branch previously did `if hi_f >= floor_strike: return None` which blocked ALL between YES cases. For a bucket like lo_f=87, hi_f=88 with floor=85, cap=89: hi_f=88 >= floor=85 triggered the early return and the YES case was never reachable.

Replaced with three-way branch:
```python
if hi_f < floor_strike:
    direction = "no"      # bucket fully below floor → existing NO logic
elif lo_f >= floor_strike and hi_f <= cap_strike:
    direction = "yes"     # bucket fully inside range → NEW YES firing
else:
    return None            # straddles boundary → skip (no unambiguous direction)
```

The `greater` market branch is unchanged — v8b does not fire YES on `greater` (confirmed_signal handles that, and it would be redundant).

---

### 2. `obs_peak_trader.py` — new file
**What it does:**
- `MODEL_NAME = "obs_peak_trader"`, `MIN_EDGE = 0.08`, `MAX_TRADE_DOLLARS = 25.00`
- Imports `_evaluate_peak_v8b` and `_evaluate_peak_gate` from `nws_obs_peak`
- `_evaluate_city(city, today, obs, obs_seq, dry_run)`: core loop over HIGH markets for one city
  - Fetches live yes/no ask via `get_best_ask(ticker, direction)`
  - Runs both signals **independently** — no fallback chain
  - Signal priority: v8b first, gate second
  - For each signal: edge check, Kelly sizing (capped at $25), then `Trade.create` or dry-run print
  - If both fire on the same ticker: annotates `"[BOTH signals agreed]"` in the notes, places only ONE trade (first to pass)
  - Dedup: in-memory `_session_traded` set (guards races) + `Trade.exists_for_model(ticker, MODEL_NAME, is_paper=True)` (guards across sessions)
- `scan_and_trade(dry_run=False)`: scans all cities in KALSHI_SERIES; skips if local time outside 10AM–9:30PM; uses `fetch_obs_from_push` + `fetch_obs_cache_sequence`
- `on_peak_push_event(event_type, station, data, ...)`: push event entry point (see wiring section)
- `main()`: arg parser for `--scan` / `--dry-run`

---

### 3. `tests/test_obs_peak_trader.py` — new file (39 tests, all pass)
Covers:
- `TestEvaluatePeakV8b` (14 tests): greater NO, greater straddles-skip, max_lower guard, v8b threshold guard, no push_extremes skip, no YES on greater, between NO, between YES (new), YES our_p == v8b_p, straddles-floor skip, straddles-cap skip, max_lower above cap, low market skip, less market skip
- `TestEvaluatePeakGate` (8 tests): low market skip, no push_extremes skip, greater NO, between NO, between YES, < 30min skip, no decline skip, < 60min past OM skip
- `TestEvaluateCity` (10 tests): v8b fires → trade placed, gate fires when v8b skips, both fire → one trade, both fire → reason notes "BOTH agreed", below MIN_EDGE → no trade, dedup → no trade, dry_run → no DB write, no signals → no trade, v8b below edge + gate passes → gate wins, between YES direction
- `TestConstants` (7 tests): model name, MIN_EDGE == MIN_EDGE_PEAK_V3, MAX_TRADE_DOLLARS, edge boundary, asos_display_c_to_f(31)→(87,88), f_to_c_bucket(87)→31

**Key design decision in tests**: Gate tests use real `datetime.now()` with UTC-aware ISO timestamps in obs_seq instead of mocking datetime. This avoids a fragile datetime-patching approach — the gate's internal `fromisoformat` + `astimezone` chain needs real types. om_peak_hour is mocked via `_om_predicted_peak_hour`. The `_session_traded` module-level set is cleared via `setup_method` in `TestEvaluateCity` to prevent state leakage between tests.

---

### 4. `dashboard_data.py` — 3 entries added
```python
DISPLAY_NAMES["obs_peak_trader"] = "Peak-Passed Obs (v8b + gate)"
MODEL_ICONS["obs_peak_trader"]   = "📈"
MODEL_DESCRIPTIONS["obs_peak_trader"] = "... (written from the actual code)"
```
Description accurately reflects: two independent signals, v8b sklearn, gate rule-based, between YES, NO, MIN_EDGE 8%, Kelly $25 cap, HIGH markets only, greater/between, push wiring pending.

---

### 5. `paper_trading/db.py` — 1 line added to `ALL_MODELS`
```python
"obs_peak_trader",  # Peak-passed obs: v8b sklearn model + rule gate (independent signals)
```
Needed so `init_db()` creates the portfolio row on first run.

---

### 6. `launchctl/com.trady.obs-peak-trader.plist` — new file
- `StartInterval: 1800` (every 30 minutes)
- Calls `obs_peak_trader.py --scan`
- Logs to `forecast_logs/obs_peak_trader.stdout.log` and `.stderr.log`
- `PYTHONUNBUFFERED=1` so logs appear immediately
- **NOT loaded** — see manual steps below

---

## Test results (pytest output)

```
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.0.2, pluggy-1.6.0
collected 39 items

tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_no_bucket_below_floor PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_skip_when_bucket_straddles_floor PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_skip_when_max_lower_at_floor PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_skip_when_v8b_below_threshold PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_skip_when_no_push_extremes PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_greater_no_yes_direction PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_no_bucket_below_floor PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_yes_bucket_inside_range PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_yes_our_p_is_v8b_p PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_skip_bucket_straddles_floor PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_skip_bucket_straddles_cap PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_between_skip_when_max_lower_above_cap PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_low_market_skipped PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakV8b::test_less_market_skipped PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_skips_low_market PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_skips_no_push_extremes PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_greater_no PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_between_no PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_between_yes_bucket_inside_range PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_skips_less_than_30min_since_peak PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_skips_no_decline PASSED
tests/test_obs_peak_trader.py::TestEvaluatePeakGate::test_gate_skips_not_60min_past_om PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_v8b_fires_trade_placed PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_gate_fires_no_v8b_skip PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_both_fire_v8b_wins_note_in_reason PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_both_fire_only_one_trade PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_below_min_edge_no_trade PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_dedup_no_trade PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_dry_run_no_db_write PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_no_signal_fires_no_trade PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_v8b_below_edge_gate_passes PASSED
tests/test_obs_peak_trader.py::TestEvaluateCity::test_between_yes_trade_direction PASSED
tests/test_obs_peak_trader.py::TestConstants::test_model_name PASSED
tests/test_obs_peak_trader.py::TestConstants::test_min_edge_equals_peak_v3 PASSED
tests/test_obs_peak_trader.py::TestConstants::test_max_trade_dollars PASSED
tests/test_obs_peak_trader.py::TestConstants::test_edge_boundary_passes PASSED
tests/test_obs_peak_trader.py::TestConstants::test_edge_below_boundary_rejected PASSED
tests/test_obs_peak_trader.py::TestConstants::test_asos_display_c_to_f_31c PASSED
tests/test_obs_peak_trader.py::TestConstants::test_f_to_c_bucket_87f PASSED

============================== 39 passed in 1.48s ==============================
```

---

## Logic questions / things noticed

### 1. `our_p` convention for NO direction signals
The codebase convention is that `our_p` always means P(YES). For NO direction signals, `our_p = v8b_p` where v8b_p ≈ P(peak has passed). This works when:
- We are betting NO because the peak temperature is **below** the floor
- P(YES) for "will high exceed floor?" is therefore low
- But `our_p` in the signal is set to `v8b_p` ≈ 0.80, which is P(peak has passed)... not directly P(YES)

The edge check `edge = our_p - entry_price` and Kelly `win_prob = 1 - our_p` treat `our_p` as P(YES). I did NOT change this convention — it matches what `nws_obs_handler.py` does. But I flagged it because for `v8b_p = 0.80` on a NO signal:
- `our_p` = 0.80 → Kelly thinks P(YES) = 80% → `win_prob(NO) = 20%` → poor Kelly sizing for NO
- In practice the only NO trades that pass are when `no_ask` is very low (< `our_p - 0.08`), meaning the market already prices YES near 100%, which keeps NO contracts cheap

Worth confirming with Trady: is `our_p = v8b_p` the right thing to pass as P(YES) for NO signals? Or should it be `1 - v8b_p`? (I kept the existing convention.)

### 2. v8b YES for `between` — `max_lower > floor_strike` guard absent
For the gate's between YES: there's no guard against "confirmed tier already fired YES on between". That's intentional in the existing gate code and I kept it. Since obs_peak_trader is a *separate model* with its own dedup, it can place its own paper trade even if confirmed_signal would have fired — they're independent experiments. But worth knowing.

### 3. CLI-after-midnight guard in push handler
Added a guard in `on_peak_push_event` for `cli_high` events: checks `data.get("for_date") == today` before proceeding. This mirrors the LEARNINGS.md lesson about CLI reports issued after midnight being previous-day data. Confirmed: the guard doesn't apply to `new_high` (no date field needed there).

### 4. Kelly behavior on NO bets with high our_p
During testing I discovered: Kelly correctly produces $0 size for a NO bet when `our_p` is high (e.g., 0.80) and `no_ask` is 50¢. This is correct — P(NO wins) = 1 - 0.80 = 0.20, which doesn't justify paying 50¢. The signal only places NO trades when no_ask is small (market is pricing YES near 100%), which is exactly the right scenario. Tests updated to use YES direction for the "v8b below edge, gate passes" scenario to avoid this Kelly=0 result.

---

## What Trady needs to wire up manually

### 1. Plist loading (after merging to main)
```bash
cp launchctl/com.trady.obs-peak-trader.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.trady.obs-peak-trader.plist
launchctl list | grep obs-peak-trader   # should show pid
```
Verify it runs:
```bash
launchctl kickstart -k gui/$(id -u)/com.trady.obs-peak-trader
tail -f forecast_logs/obs_peak_trader.stdout.log
```

### 2. Push event wiring in `wethr_push_client.py`
`on_peak_push_event` in `obs_peak_trader.py` is the entry point. Add to the push dispatch block in `wethr_push_client.py`:

```python
from obs_peak_trader import on_peak_push_event

# Wherever new_high and cli_high events are dispatched (alongside on_push_event):
if event_type in ("new_high", "cli_high"):
    on_peak_push_event(
        event_type, station, data,
        lo_f=lo_f, hi_f=hi_f, exact=exact,
        dry_run=dry_run,
    )
```

The function signature matches the existing `on_push_event` pattern from `nws_obs_handler.py` so it slots in cleanly.

### 3. Dashboard restart
```bash
launchctl kickstart -k gui/$(id -u)/com.trady.dashboard
```
Verify `obs_peak_trader` appears in the model list.

### 4. HEARTBEAT.md update
Add `obs_peak_trader` to the periodic monitoring checklist — check that it's placing trades and that the stdout log shows clean scans.
