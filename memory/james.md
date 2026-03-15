# james.md — James's Memory File

Running lessons and notes for the end_of_day_trader / obs subsystem work.

---

## 2026-03-15 — running_min_f source bug

**Lesson:** `obs_cache.lowest_probable_f` is the C→F ambiguity lower bound — NOT an actual temperature. Never use it as a running min. Always use `push_extremes.nws_low_f` as the authoritative running min (it's what NWS confirmed and what Kalshi settles against).

**Why it matters:** 13°C maps to [55°F, 56°F] via `asos_display_c_to_f`. The lower bound (55°F) represents *uncertainty* in the C→F conversion, not a confirmed temperature. The actual NWS-confirmed value was 56°F (`push_extremes.nws_low_f`). Old code used `min(lowest_probable_f)` = 55, which placed the daily min *below* B56.5's floor=56, triggering a wrong NO signal. New code uses only `push_extremes.nws_low_f` = 56, correctly identifying the low as in-range [56,57].

**Canonical sources:**
- `running_min_f` → ONLY `push_extremes.nws_low_f`
- `current_obs_c` → `obs_cache.temp_c` (latest row, for projected_minimum formula input)
- `asos_display_c_to_f` → import directly from `obs_utils`, not via any alias

## 2026-03-15 — import alias cleanup

**Lesson:** Don't create module-level aliases (`f_range_for_c = asos_display_c_to_f` in `nws_obs_trader.py`). Import the canonical function directly from its source (`obs_utils.asos_display_c_to_f`). Aliases add confusion and indirection with no benefit.
