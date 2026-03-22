# TODOS.md — Single Source of Truth

Update this file whenever tasks are added, completed, or blocked.
Format: `- [ ]` open / `- [x]` done / `- [~]` blocked

---

## 🔥 High Priority

### TWC Probabilistic Forecast API
- [ ] Investigate why `/v3/wx/forecast/probabilistic` returns 401 (doc lists 401 = "Request rates exceeded", not "unauthorized" — may actually have access)
- [ ] Contact TWC to clarify if our trial key includes this endpoint or what tier is required
- [ ] If accessible: use `probabilities=temperature:threshold,inf` per LST-window hour → P(daily_max > threshold) = 1 − ∏(1 − P_h) — replaces our hand-tuned sigma model with TWC's BMA-calibrated uncertainty

### Get a Broader TWC Trial Key
Current key has: standard forecast package + Aviation Core.
- [ ] Request trial key with full package access from TWC
- [ ] Test `/v3/wx/forecast/fifteenminute/enterprise` — decimal-precision 15-min (401 on current key)
- [ ] Test GRAF raw API — hourly-updating, 3.5km resolution, 5-min intervals for US/Europe; potentially a 5th ensemble member independent from GFS/ECMWF/ICON/GEM
- [ ] Test Probabilistic Forecast package — TWC BMA-calibrated uncertainty

### Real Obs Estimation Trader
**Full spec**: `trading/REAL_OBS_ESTIMATION_TRADER.md`
- [ ] Build real-time METAR fetcher + T-group / 6hr-max / 24hr-max parser
- [ ] Integrate METAR signal into nws_obs_trader.py as boundary resolution layer
- [ ] Historical backtest: how often does METAR resolve °C boundary before CLI?
- [ ] Historical backtest: accuracy of T-group flanking estimate
- [ ] Temperature curve smoothness model (Bayesian prior from flanking readings)
- [ ] Define trade entry rules (confidence threshold, price cap, sizing)
- [ ] Paper trade 30+ days before live

### Backtest Fixes
- [ ] Rerun CLI vs ASOS gap analysis with correct methodology
  - Current result (-0.17°F) is wrong: used preliminary CLI + UTC day boundaries
  - Correct result expected: CLI ~+0.7-1°F above IEM hourly max (due to 1-min vs hourly resolution)

---

## 🟡 Medium Priority

### Bug Fixes
- [ ] M-1: Kelly sizing uses hardcoded $500, should use `Portfolio.get("nws_obs_confirmed").balance`
- [ ] M-3: Signal std dev columns wrong key names in ens_detail lookup
- [ ] M-4: Percentile indices off by 1-3%
- [ ] M-6: Phoenix `kalshi_series_low = None`
- [ ] M-7: Delete duplicate `load_cli_actuals()` in `nws_obs_trader.py`

### Calibration
- [ ] **Recalibrate twc_bucket_low p-table** ~2026-04-07 — city-specific p-values set 2026-03-14 on only 17 days of March data. Run calibration script after 3+ more weeks.
  Current values: miami=0.80, chicago=0.80, lax=0.65, nyc=0.50, denver=0.35, austin=0.35
- [ ] **Rerun α calibration** ~2026-03-27 — current α=0.8 is empirically derived, recheck after more data

### Weekly Model Retrain (cron)
- [ ] Schedule `build_forecast_model.py --version v1 --no-fetch` and `--version v2 --no-fetch` to run Sunday midnight ET
  Not urgent yet (only ~22 training dates), but pkl files will go stale as data accumulates

### Signal Research
- [ ] **near_forecast_signal disambig correction** — for "greater" markets where `lo_f(needed_c) == T`, multiply `p_rise` by `P(hi_f)` from disambig_signal. Currently overstates `our_p` by ~45-55% of rise probability at boundary thresholds (69, 71, 78, 80, 87, 89°F...)
- [ ] **P(peak passed) from obs trajectory** — logistic regression model trained on ASOS obs sequences (actual_decline_f, consecutive readings below peak, rate of decline) matched to CLI ground truth. Complement to current OM-based peak signal.
- [ ] **twc_icon_adjusted model review** after ~50 settled trades — check if win rate is improving or stuck near 50%; compare to twc_forecast on greater-YES only

### Infrastructure
- [ ] **`requirements.txt`** — generate and commit: `cd trading && .venv/bin/pip freeze > requirements.txt`. Critical for recovery if Railway volume is wiped.
- [ ] **Atlanta Foreca ID** — look up KATL (33.6367, -84.4281) Foreca city ID and add to `trading_utils.py` CITIES dict (`foreca_id: None` currently)
- [ ] **Day-of obs correction** in `forecast_logger.py` — fetch ASOS obs for same-day target dates; apply `max(obs_max, api_high)` correction
- [ ] **Settlers** — verify between-market settlement formula across all three settlers (cap_strike check)

---

## 🔧 Low Priority / Someday

### GRAF Reforecast dataset (pre-2024 training only)
TWC publishes historical GRAF runs on public S3 (`s3://twc-graf-reforecast/`, anon access, Zarr format). Data goes 2004–July 2024, ~80-100 runs/year. Miami accuracy looks good (~0.9°F MAE) but:
- Ends July 2024 — no overlap with our trading data
- Chunk structure is (1, 4.8M nodes) — ~1.4s per data point from Railway, ~2GB per run to extract all time steps
- Only useful if we ever want pre-2024 historical GRAF features for model training
- Nearest mesh nodes already computed: miami=350411, chicago=3145565, nyc=3821922, lax=2745497, denver=2899186

- [ ] `historical_climatology`: formally retire (zombie, −$165 P&L, 2/26 wins)
- [ ] `netCDF4`: pip install in `.venv` to activate MADIS integration
- [ ] `ensemble_probability_multi()`: delete or document as unused in `kelly.py`
- [ ] Get 50 CLI versions per city (web `product.php` has them, NWS API only returns ~14)
- [ ] Clear stale stderr logs (`nws_obs_trader`, `obs_exit_monitor`) — full of old netCDF4 errors
- [ ] Document Python version fragility (venv symlink) in a SETUP.md

---

## ⏸️ Deprioritized / Likely Stale

*Kept for reference but likely superseded by current architecture or already resolved.*

### Old Sub-Agent Tasks (sessions from Feb-Mar 2026)
- [ ] **Peak-timing v2 backtest** — sub-agent `139e29cd` researching new qualification methodology. Check if still relevant or superseded by v9 peak model.
- [ ] **SFO boundary case study** — cron job `23c0d477` researched KSFO 22°C ambiguity; report at `reports/sfo_temp_ambiguity_2026-02-27.md`. Review if file exists.
- [ ] **Station research report** — `reports/station_research_2026-02-27.md`; review if file exists.
- [ ] **EMOS research results** — sub-agent researched MOS-shifted GEFS ensemble; report at `reports/emos_research_2026-02-27.md`. Review if file exists.
- [ ] **NYC Mesonet research** — sub-agent `a658b0a0` researched NYS Mesonet NYC station near Central Park; report at `reports/nyc_mesonet_research_2026-02-27.md`. Review if file exists.

### Build Queue Items (may be superseded)
- [ ] **Peak-timing obs trader** — v2 backtest showed 54-57% failure rate (likely labeling artifact: CLI ~1°F above ASOS obs max in 82% of cases). v1 (clean cities, 0/90 at 120+ min) more trustworthy. Do NOT build until reviewed.
- [ ] **Aviation Weather obs poller** — replace NWS API obs feed with `aviationweather.gov/api/data/metar` for 2-min latency vs 10-15 min. Gets 0.1°C T-group precision on all stations. (Superseded by wethr push? Verify.)
- [ ] **Write pytest test files** — `tests/conftest.py` (demo auth fixture), `tests/test_demo_markets.py`, `tests/test_unit.py`. Check if these already exist.

### Wethr Items (may be resolved)
- [ ] Verify `six_hour_high/low` in wethr push `observation` payload — currently assumed NOT present
- [ ] Investigate wethr `mode=wethr_high&logic=nws` — pre-computed daily high; check if it matches our own `max_lower_f` tracking
- [ ] Wethr Developer plan ($70/month) — unlocks 50k/day + Push API with 1-min obs
- [ ] Check `lowest_probable`/`highest_probable` fields in wethr response — are we duplicating with `asos_display_c_to_f()`?

### CLI Trader (likely already resolved)
- [ ] Monitor first successful 98¢ limit order fills — was "tomorrow's ET run" at time of writing
- [ ] Validate paper ≈ live P&L after first settlement
