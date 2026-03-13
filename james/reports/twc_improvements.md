# TWC Improvements — Final Report

**Branch:** `james/twc-improvements`
**Tests:** 155 passing (was 142 before this branch; added 13 new unit tests)

---

## Part 1 — TWC 15-min Forecast Logging ✅

**Files changed:** `twc_forecast.py`, `forecast_logger.py`

- Added `fetch_twc_15min_snapshot(city, config)` in `forecast_logger.py` — fetches TWC 15-min API (`/v3/wx/forecast/fifteenminute`) and returns `[[ts, temp_f], ...]`.
- Extended `compute_twc_advanced()` in `twc_forecast.py` with `fifteen_snap` optional parameter:
  - `twc_hourly_15min_high`/`twc_hourly_15min_low` are always logged when `fifteen_snap` is available (raw 15-min max/min for the date).
  - If the hourly peak/trough is within the next 6h, `twc_hourly_high`/`twc_hourly_low` are replaced by the 15-min max/min (finer granularity for imminent peaks).
- `forecast_logger.py` fetches the 15-min snap per city, filters to target date, passes to `compute_twc_advanced`.
- **7 new unit tests** in `tests/test_twc_advanced_15min.py`.

---

## Part 2 — Peak Timing Logging ✅

**Files changed:** `forecast_logger.py`, `dashboard_data.py`, `dashboard.py`

New fields in `forecasts.jsonl` (UTC-based local LST hour, 0–23):
- `twc_high_hour` / `twc_low_hour` — from TWC hourly snap for the date
- `om_high_hour` / `om_low_hour` — from OM best_match hourly via new `fetch_om_best_match_hourly()`
- `nws_high_hour` / `nws_low_hour` — from NWS /forecast/hourly via new `fetch_nws_hourly_snap()`

Helper `_peak_hour_lst(snap, want_max, lst_offset_h)`:
- Offset-aware timestamps (TWC): converted to UTC, then shifted by `lst_offset_h`.
- Naive timestamps (OM `timezone=auto`): already local time, `dt.hour` returned directly (fixed a sign bug in the original implementation that would have given wrong hours).

**Dashboard:** New "⏰ Peak Timing" tab in `dashboard.py` rendered by `render_peak_timing_tab()`. Shows MAE in hours per source per lead-time bin. Shows a placeholder message until `cli_actuals.jsonl` includes `cli_high_hour`/`cli_low_hour` fields (CLI timing not yet logged — infrastructure is ready).

`compute_peak_timing_accuracy()` in `dashboard_data.py` includes all three sources (TWC, OM, NWS).

**6 new unit tests** in `tests/test_peak_hour_logging.py`.

---

## Part 3 — `twc_lst` End-Disputed Window Fix ✅

**File changed:** `twc_forecast.py`

The previous run had added "Layer 0 start-disputed window" logic to both `get_twc_forecast()` and `fetch_twc_lst()`. This was out of scope and untested. **Removed entirely** from both functions.

The in-scope fix (Layer 1 — end-disputed window) was already present and remains unchanged: the final 1h of the LST day (midnight LDT → 1 AM LDT during DST) is correctly added to `final_hi`/`final_lo` when `disputed_temps` exist.

---

## Commits

1. `checkpoint: state at resume (prior partial run with Layer 0 out-of-scope code)`
2. `fix: remove out-of-scope Layer 0 start-disputed window from twc_forecast.py`
3. `feat: add nws_high_hour/nws_low_hour peak timing to forecasts.jsonl and dashboard`

---

## Notes / Out-of-Scope Observations

- `cli_actuals.jsonl` does not yet log the hour of the CLI-recorded daily high/low. The Peak Timing accuracy tab infrastructure is complete but will show a placeholder until that field is added by whoever owns the CLI fetcher.
- The "between-NO" and NWS filters for ensemble_trader (from March 12 work) are already in this branch from the checkpoint commit — those are not part of this task and are upstream changes that exist in the branch because the worktree is based on the current state of the repo.
