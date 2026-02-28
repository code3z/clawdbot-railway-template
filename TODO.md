# TODO.md — Short-term tasks

Update this file whenever tasks are added, completed, or blocked.
Format: `- [ ]` open / `- [x]` done / `- [~]` blocked

---

## In Progress (sub-agents working)
- [ ] **Peak-timing v2 backtest** — sub-agent `139e29cd` researching new qualification methodology (full OM forecast curve shape, not just minutes-past-peak). Will ask before running 60-day backtest.
- [ ] **SFO boundary case study** — cron job `23c0d477` fires at 5 AM ET; researches KSFO 22°C ambiguity, writes `reports/sfo_temp_ambiguity_2026-02-27.md`, adds note to STRATEGY_IDEAS.md

## Build Queue (next trader)
- [ ] **Peak-timing obs trader** — ⚠️ BLOCKED pending morning review. v2 backtest shows 54-57% failure rate (broken — CLI is systematically ~1°F above ASOS obs max in 82% of cases, making most "failures" labeling artifacts). v1 (clean cities, 0/90 at 120+min) is more trustworthy but v2 discrepancy must be understood first. Do NOT build until Ian reviews.
- [ ] **Aviation Weather obs poller** — replace NWS API obs feed with `aviationweather.gov/api/data/metar`. 30-sec latency vs 10-15 min. Gets 0.1°C T-group precision on all stations.

## Testing
- [ ] **Write pytest test files** — `tests/conftest.py` (demo auth fixture), `tests/test_demo_markets.py`, `tests/test_unit.py`
- [ ] **Run `python3 -m pytest -m demo -v`** to verify end-to-end

## Infrastructure
- [ ] **Day-of obs correction** in `forecast_logger.py` — fetch ASOS obs for same-day target dates; apply `max(obs_max, api_high)` correction
- [ ] **Atlanta Foreca ID** — look up KATL (33.6367, -84.4281) Foreca city ID and add to `trading_utils.py` CITIES dict (`foreca_id: None` currently)

## Research
- [ ] **Station research report** — `reports/station_research_2026-02-27.md` written by sub-agent; review it
- [ ] **Ideas 2 and 3** — add to STRATEGY_IDEAS.md (discussed but not written yet)

## ⏸️ Blocked pending morning discussion
- [ ] **Peak-timing trader (trader 2)** — v2 backtest results show 54-57% failure rates but likely a measurement artifact: CLI is systematically ~1°F above IEM 5-min obs max due to 1-min vs 5-min averaging (known from STATIONS.md). V1's use of `obs_max_upper_f` (+1°F buffer) likely handled this correctly. Need to discuss with Ian: should v3 use `obs_max_upper_f + 1` as the comparison threshold? Or revert to v1 methodology (minutes-past-peak) with larger dataset?

## Pending Review
- [ ] **EMOS research results** — sub-agent researching MOS-shifted GEFS ensemble. When it reports back, review with Ian: data alignment, MAE improvement, whether to add to forecast_logger.py. Report: `polymarket/reports/emos_research_2026-02-27.md`

- [ ] **NYC Mesonet research** — Sub-agent `a658b0a0` researching whether NYS Mesonet NYC network station near Central Park can improve NYC obs data (fresher/more accurate than KNYC 37min lag). Report: `polymarket/reports/nyc_mesonet_research_2026-02-27.md`. Key question: does it track Central Park closely enough to use as settlement proxy, and is it faster than our current sources?
