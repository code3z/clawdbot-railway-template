# TODOS.md — Open Tasks

## 🔧 Infrastructure

### Get a broader TWC trial key to test additional endpoints
Current key has: standard forecast package + Aviation Core.
**Missing / worth testing:**
- `/v3/wx/forecast/fifteenminute/enterprise` — decimal-precision 15-min forecast (401 on current key)
- Probabilistic forecast package — uncertainty/spread data from TWC's own model
- GRAF (AI/NVIDIA hyper-local) — potentially different model, not just rounded integers
Ask TWC for a trial key with full package access, test whether any of these beat what we already have.

### venv / launchctl cleanup
- **MEDIUM** Clear stale stderr logs (nws_obs_trader, obs_exit_monitor) — full of old netCDF4 errors burying real ones
- **LOW** Document Python version fragility (venv symlink → python3.13) in a SETUP.md

### Weekly model retrain (add cron)
Schedule `build_forecast_model.py --version v1 --no-fetch` and `--version v2 --no-fetch` to run Sunday midnight ET. As data accumulates the static pkl files will go stale — weekly retrain keeps them current. Simple cron job, not urgent yet (only 22 training dates).

---

## 📊 Calibration / Data

### Recalibrate twc_bucket_low p-table ~2026-04-07
City-specific p-values set 2026-03-14 on only 17 days of March data. Run calibration script after 3+ more weeks.
Current values: miami=0.80, chicago=0.80, lax=0.65, nyc=0.50, denver=0.35, austin=0.35

### Rerun α calibration ~2026-03-27
Current α=0.8 is empirically derived. Recheck after more data.
