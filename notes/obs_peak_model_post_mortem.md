# obs_peak_model — Post-Mortem & Fix Log

**Date:** 2026-03-22
**Model:** `obs_peak_model` (v9 multinomial peak-passed signal)
**True P&L at audit:** -$431.53 (stored was +$643 due to settlement bug)

---

## Why It Failed

### Bug 1: strike_type not passed to TradeRequest (root cause of phantom wins)
`obs_peak_model_trader.py` built a `TradeRequest` without setting `strike_type`, `floor_strike`, or `cap_strike`. The `_parse_ticker_meta()` fallback in `db.py` always defaulted T-prefix tickers to `strike_type="greater"`. When `settle_all.py` resolved these trades, it used the wrong stored strike_type — `greater` instead of `less` — causing T-less markets (e.g. "Will Chicago stay below 63°F?") to be settled as wins when they actually lost.

**Result:** 11 phantom wins across March 17–21. Stored P&L overstated by ~$1,075.

**Fix:** Pass `strike_type`, `floor_strike`, `cap_strike` explicitly from the trader. Now enforced system-wide: `TradeRequest.__post_init__` raises `ValueError` if `strike_type is None`. (commit `5e2e5e3`)

### Bug 2: Time gate missing from push event handler
`scan_and_trade()` had a local-hour gate (10am–9:30pm). `on_peak_push_event()` did not. This caused trades to fire on wethr push events at 1am, 8am local time — before the daily peak had formed.

**Result:** Trades like ID 8308 (Boston, 1:55am local) — structurally invalid.

**Fix:** Added `if not (10.0 <= local_h <= 21.5): return` to `on_peak_push_event()`. (commit `25a404d`)

### Bug 3: less/YES gate was absent
The v9 model fires on `less` strike markets with `direction=yes` (bet the high stays below cap). Without a gate, it traded when `p2plus` (P(peak not yet passed)) was 0.76–0.94 — the model itself was saying the peak almost certainly hadn't formed yet. The market was often pricing YES at 1–4¢ (99%+ confident the high would exceed cap), and the model disagreed based on a local feature that wasn't calibrated for this use case.

**Result:** 20+ loss trades. The model was being applied to situations it wasn't designed for.

---

## How We Diagnosed It

1. Ian noticed dashboard showed a Chicago trade as +$377 won, but knew Chicago hit 77°F when the market was "below 63°F"
2. Traced through TradeRequest → _parse_ticker_meta fallback → settle_all resolution logic
3. Re-ran full Kalshi API audit on all 56 settled obs_peak_model trades to find all phantom wins/missed wins
4. Analyzed p2plus and fill price distributions across 27 settled less/YES trades

---

## DB Corrections Made (2026-03-22)

**Voided (phantom wins — settled wrong or made due to bugs):**
- 6236, 8308, 8316, 8317, 8347, 8356, 8661, 8701, 8786, 8788, 8812 — phantom wins (strike_type bug)
- 4368 — v8b era trade, entered 3:30am local (time gate bug)

**Corrected (missed wins):**
- 8703 (LAX T76 less): -$18.50 → +$70.25 (genuine win, LAX stayed below 76°F)
- 8984 (HOU T87 less): -$24.15 → +$1.77 (genuine win, Houston stayed below 87°F)

**Final portfolio after corrections:** balance=$500.00 (reset), realized_pnl=-$431.53 (preserved as historical record)

---

## Gate Calibration (2026-03-22)

Analyzed 27 settled less/YES trades. Found:

| Gate | Trades | WR | P&L |
|---|---|---|---|
| No gate (all) | 27 | 18.5% | -$242 |
| p2plus ≤ 0.20 only | 5 | 80% | +$24 |
| fill ≥ 0.15 only | 9 | 55.6% | +$50 |
| **fill ≥ 0.15 AND p2plus ≤ 0.50** | **6** | **83.3%** | **+$95** |

NWS forecast (nws_high vs cap) was useless — running max already exceeded NWS forecast at trade time on nearly every trade.
Gap (cap - running_max) alone was also useless — 25% WR regardless of gap size.

**Gate implemented:** `less/YES` requires `yes_ask ≥ 0.15 AND p2plus ≤ 0.50` (commit `38e20fc`)

The fill price captures independent information — when the crowd is pricing YES at 15¢+, they see a real case for the high staying below cap.

---

## What Still Needs Watching

1. **27 trades is a small sample.** The one remaining loss (ID 7479, fill=0.69, p2+=0.11) shows that even a "clean" signal can lose. Gate is calibrated on the only data we have.
2. **Dedup**: rejected trades (FOK) are not blocked from retrying. Low priority (no money lost) but creates DB clutter.
3. **om_peak_h logging**: not stored for obs_peak_model trades. Ian suggested timing relative to predicted peak hour as a potential future feature. Need to add to notes/metadata.
4. **Model itself**: v9 was designed for peak-passed detection generally. The less/YES use case is a specific application that may need its own features or model.

---

## Commits
- `5e2e5e3` — strike_type required in TradeRequest, all traders fixed
- `25a404d` — time gate on push events, initial p2plus>0.20 gate (later corrected)
- `38e20fc` — final gate: fill≥0.15 AND p2plus≤0.50
- `b4c46d3`, `ff9c618` — DB corrections (void phantom wins, fix missed wins)

---

## Full Trade History (pre-reset, exported 2026-03-22)

440 total trades (362 rejected FOK, 34 lost, 21 won, 12 voided, 11 expired)

| ID | ticker | dir | status | fill | pnl | entered_at | notes |
|---|---|---|---|---|---|---|---|
| 3649 | KXHIGHTHOU-26MAR13-B75.5 | yes | won | 0.74 | +8.78 | 2026-03-13 20:36 | peak_passed_v8b: v8b=0.964 nws_high=75°F peak=24°C [75,76]°F strike=between/75.0 |
| 3663 | KXHIGHTPHX-26MAR13-B93.5 | no | lost | 0.22 | -11.85 | 2026-03-13 21:49 | peak_passed_v8b: v8b=0.702 nws_high=89°F peak=32°C [89,90]°F strike=between/93.0 |
| 3666 | KXHIGHTBOS-26MAR13-B42.5 | yes | won | 0.71 | +10.21 | 2026-03-13 23:10 | peak_passed_v8b: v8b=0.999 nws_high=42°F peak=6°C [42,43]°F strike=between/42.0/ |
| 3851 | KXHIGHTDC-26MAR14-B57.5 | yes | lost | 0.25 | -63.52 | 2026-03-14 16:37 | peak_passed_v8b: v8b=0.626 nws_high=57°F peak=14°C [57,58]°F strike=between/57.0 |
| 3869 | KXHIGHDEN-26MAR14-B75.5 | no | won | 0.41 | +7.22 | 2026-03-14 18:47 | peak_passed_v8b: v8b=0.563 nws_high=73°F peak=23°C [73,74]°F strike=between/75.0 |
| 3870 | KXHIGHDEN-26MAR14-B73.5 | yes | won | 0.38 | +52.90 | 2026-03-14 18:47 | peak_passed_v8b: v8b=0.563 nws_high=73°F peak=23°C [73,74]°F strike=between/73.0 |
| 3871 | KXHIGHTATL-26MAR14-B76.5 | yes | lost | 0.15 | -60.93 | 2026-03-14 18:58 | peak_passed_v8b: v8b=0.876 nws_high=77°F peak=25°C [77,77]°F strike=between/76.0 |
| 3951 | KXHIGHTATL-26MAR14-B78.5 | yes | won | 0.70 | +22.20 | 2026-03-14 19:54 | peak_passed_v8b: v8b=0.979 nws_high=78°F peak=26°C [78,79]°F strike=between/78.0 |
| 3952 | KXHIGHTDAL-26MAR14-B80.5 | yes | won | 0.56 | +34.59 | 2026-03-14 20:22 | peak_passed_v8b: v8b=0.988 nws_high=80°F peak=27°C [80,81]°F strike=between/80.0 |
| 3953 | KXHIGHTSATX-26MAR14-B85.5 | yes | lost | 0.30 | -37.42 | 2026-03-14 20:22 | peak_passed_v8b: v8b=0.928 nws_high=86°F peak=30°C [86,86]°F strike=between/85.0 |
| 3954 | KXHIGHAUS-26MAR14-B84.5 | yes | lost | 0.29 | -31.80 | 2026-03-14 20:27 | peak_passed_v8b: v8b=0.971 nws_high=84°F peak=29°C [84,85]°F strike=between/84.0 |
| 3956 | KXHIGHTLV-26MAR14-B87.5 | yes | won | 0.74 | +9.50 | 2026-03-14 21:27 | peak_passed_v8b: v8b=0.903 nws_high=87°F peak=31°C [87,88]°F strike=between/87.0 |
| 3961 | KXHIGHAUS-26MAR14-B86.5 | yes | won | 0.95 | +1.21 | 2026-03-14 21:52 | peak_passed_v8b: v8b=0.987 nws_high=86°F peak=30°C [86,86]°F strike=between/86.0 |
| 3963 | KXHIGHTPHX-26MAR14-B91.5 | yes | won | 0.75 | +6.51 | 2026-03-14 22:07 | peak_passed_v8b: v8b=0.956 nws_high=91°F peak=33°C [91,92]°F strike=between/91.0 |
| 3983 | KXHIGHTOKC-26MAR15-B67.5 | yes | won | 0.71 | +1.79 | 2026-03-15 07:27 | peak_passed_v8b: v8b=0.756 nws_high=68°F peak=20°C [68,68]°F strike=between/67.0 |
| 4149 | KXHIGHTATL-26MAR15-B73.5 | yes | lost | 0.54 | -12.36 | 2026-03-15 17:13 | peak_passed_v8b: v8b=0.591 nws_high=73°F peak=23°C [73,74]°F strike=between/73.0 |
| 4242 | KXHIGHTLV-26MAR15-B80.5 | yes | won | 0.89 | +7.99 | 2026-03-15 22:02 | peak_passed_v8b: v8b=0.961 nws_high=80°F peak=27°C [80,81]°F strike=between/80.0 |
| 4243 | KXHIGHTDC-26MAR15-B57.5 | yes | lost | 0.88 | -54.93 | 2026-03-15 22:22 | peak_passed_v8b: v8b=0.992 nws_high=57°F peak=14°C [57,58]°F strike=between/57.0 |
| 4251 | KXHIGHTSFO-26MAR15-B78.5 | yes | won | 0.91 | +4.62 | 2026-03-15 23:08 | peak_passed_v8b: v8b=0.997 nws_high=78°F peak=26°C [78,79]°F strike=between/78.0 |
| 4345 | KXHIGHTDC-26MAR15-B59.5 | yes | won | 0.92 | +3.45 | 2026-03-16 03:32 | peak_passed_v8b: v8b=0.996 nws_high=59°F peak=15°C [59,59]°F strike=between/59.0 |
| 4368 | KXHIGHTATL-26MAR16-B69.5 | yes | voided | 0.73 | — | 2026-03-16 07:28 | peak_passed_v8b: v8b=0.897 nws_high=70°F peak=21°C [69,70]°F strike=between/69.0 |
| 4453 | KXHIGHMIA-26MAR16-B82.5 | yes | rejected | — | — | 2026-03-16 15:12 | peak_passed_v8b: v8b=0.784 nws_high=82°F peak=28°C [82,83]°F strike=between/82.0 |
| 4745 | KXHIGHMIA-26MAR16-B86.5 | no | expired | 0.28 | +0.00 | 2026-03-16 15:48 | peak_passed_v8b: v8b=0.631 nws_high=84°F peak=29°C [84,85]°F strike=between/86.0 |
| 4746 | KXHIGHMIA-26MAR16-B84.5 | yes | expired | 0.26 | +0.00 | 2026-03-16 15:48 | peak_passed_v8b: v8b=0.631 nws_high=84°F peak=29°C [84,85]°F strike=between/84.0 |
| 4954 | KXHIGHPHIL-26MAR16-B67.5 | yes | expired | 0.38 | +0.00 | 2026-03-16 18:00 | peak_passed_v8b: v8b=0.778 nws_high=68°F peak=20°C [68,68]°F strike=between/67.0 |
| 5020 | KXHIGHTSFO-26MAR16-T76 | yes | lost | 0.02 | -14.07 | 2026-03-16 19:00 | v9=[p0:0.09,p1:0.04,p2+:0.87] hi_f=67 nws_high=66°F running_max=19°C / spread=±9 |
| 5126 | KXHIGHTSATX-26MAR16-B58.5 | yes | won | 0.84 | +13.10 | 2026-03-16 20:37 | peak_passed_v8b: v8b=0.931 nws_high=59°F peak=15°C [59,59]°F strike=between/58.0 |
| 5127 | KXHIGHDEN-26MAR16-T51 | yes | rejected | — | — | 2026-03-16 21:05 | v9=[p0:0.81,p1:0.10,p2+:0.09] hi_f=49 nws_high=48°F running_max=9°C / spread=±7. |
| 5129 | KXHIGHTPHX-26MAR16-B91.5 | yes | lost | 0.38 | -37.22 | 2026-03-16 21:07 | peak_passed_v8b: v8b=0.601 nws_high=91°F peak=33°C [91,92]°F strike=between/91.0 |
| 5130 | KXHIGHTPHX-26MAR16-B93.5 | no | lost | 0.38 | -2.87 | 2026-03-16 21:17 | peak_passed_v8b: v8b=0.601 nws_high=91°F peak=33°C [91,92]°F strike=between/93.0 |
| 5131 | KXHIGHTSFO-26MAR16-B78.5 | yes | lost | 0.25 | -56.56 | 2026-03-16 21:22 | peak_passed_v8b: v8b=0.732 nws_high=78°F peak=26°C [78,79]°F strike=between/78.0 |
| 5138 | KXHIGHTLV-26MAR16-T82 | yes | rejected | — | — | 2026-03-16 21:36 | v9=[p0:0.89,p1:0.06,p2+:0.05] hi_f=81 nws_high=80°F running_max=27°C / spread=±4 |
| 5142 | KXHIGHDEN-26MAR16-B51.5 | yes | won | 0.84 | +9.16 | 2026-03-16 22:02 | peak_passed_v8b: v8b=0.975 nws_high=51°F peak=11°C [51,52]°F strike=between/51.0 |
| 5181 | KXHIGHTSFO-26MAR16-B82.5 | yes | won | 0.78 | +11.52 | 2026-03-16 23:08 | peak_passed_v8b: v8b=0.996 nws_high=82°F peak=28°C [82,83]°F strike=between/82.0 |
| 5693 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 16:17 | v9=[p0:0.15,p1:0.03,p2+:0.82] hi_f=61 nws_high=60°F running_max=16°C / spread=±1 |
| 5694 | KXHIGHTATL-26MAR17-T45 | yes | rejected | — | — | 2026-03-17 16:18 | v9=[p0:0.48,p1:0.29,p2+:0.23] hi_f=41 nws_high=41°F running_max=5°C / spread=±2. |
| 5702 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 16:24 | v9=[p0:0.14,p1:0.03,p2+:0.83] hi_f=54 nws_high=53°F running_max=12°C / spread=±1 |
| 5704 | KXHIGHTDC-26MAR17-T42 | yes | rejected | — | — | 2026-03-17 16:25 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=41 nws_high=41°F running_max=5°C / spread=±3. |
| 5739 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 17:41 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5740 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 17:42 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5741 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 17:43 | v9=[p0:0.07,p1:0.05,p2+:0.88] hi_f=14 nws_high=14°F running_max=-10°C / spread=± |
| 5742 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 17:43 | v9=[p0:0.17,p1:0.03,p2+:0.80] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5744 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 17:47 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5745 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 17:48 | v9=[p0:0.23,p1:0.03,p2+:0.75] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5746 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 17:52 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5747 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 17:58 | v9=[p0:0.23,p1:0.03,p2+:0.75] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5748 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 17:58 | v9=[p0:0.23,p1:0.03,p2+:0.75] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5765 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:02 | v9=[p0:0.27,p1:0.03,p2+:0.70] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5766 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:03 | v9=[p0:0.17,p1:0.04,p2+:0.79] hi_f=61 nws_high=60°F running_max=16°C / spread=±0 |
| 5767 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 18:03 | v9=[p0:0.30,p1:0.04,p2+:0.66] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5768 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:04 | v9=[p0:0.16,p1:0.03,p2+:0.81] hi_f=59 nws_high=59°F running_max=15°C / spread=±2 |
| 5769 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:04 | v9=[p0:0.27,p1:0.03,p2+:0.70] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5770 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 18:07 | v9=[p0:0.30,p1:0.04,p2+:0.66] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5771 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:08 | v9=[p0:0.27,p1:0.03,p2+:0.70] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5772 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:08 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5773 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 18:09 | v9=[p0:0.30,p1:0.04,p2+:0.66] hi_f=49 nws_high=48°F running_max=9°C / spread=±4. |
| 5774 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:09 | v9=[p0:0.27,p1:0.03,p2+:0.70] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 5775 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:09 | v9=[p0:0.51,p1:0.15,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5776 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:13 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5777 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:17 | v9=[p0:0.18,p1:0.03,p2+:0.79] hi_f=59 nws_high=59°F running_max=15°C / spread=±2 |
| 5778 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:18 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5779 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:20 | v9=[p0:0.10,p1:0.03,p2+:0.87] hi_f=67 nws_high=66°F running_max=19°C / spread=±1 |
| 5780 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:23 | v9=[p0:0.10,p1:0.03,p2+:0.87] hi_f=67 nws_high=66°F running_max=19°C / spread=±1 |
| 5781 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:23 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5782 | KXHIGHAUS-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:23 | v9=[p0:0.39,p1:0.24,p2+:0.38] hi_f=63 nws_high=62°F running_max=17°C / spread=±3 |
| 5783 | KXHIGHAUS-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:27 | v9=[p0:0.39,p1:0.24,p2+:0.36] hi_f=63 nws_high=62°F running_max=17°C / spread=±3 |
| 5784 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 18:28 | v9=[p0:0.10,p1:0.03,p2+:0.87] hi_f=67 nws_high=66°F running_max=19°C / spread=±1 |
| 5785 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:28 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5786 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:33 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5787 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:38 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5788 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 18:38 | v9=[p0:0.28,p1:0.24,p2+:0.48] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5789 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:39 | v9=[p0:0.43,p1:0.29,p2+:0.27] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5790 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:39 | v9=[p0:0.39,p1:0.26,p2+:0.35] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5791 | KXHIGHTDAL-26MAR17-T63 | yes | rejected | — | — | 2026-03-17 18:40 | v9=[p0:0.20,p1:0.08,p2+:0.72] hi_f=59 nws_high=59°F running_max=15°C / spread=±2 |
| 5792 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:40 | v9=[p0:0.51,p1:0.16,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5793 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 18:42 | v9=[p0:0.17,p1:0.22,p2+:0.61] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5794 | KXHIGHTDAL-26MAR17-T63 | yes | rejected | — | — | 2026-03-17 18:42 | v9=[p0:0.25,p1:0.10,p2+:0.64] hi_f=59 nws_high=59°F running_max=15°C / spread=±2 |
| 5795 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:42 | v9=[p0:0.43,p1:0.30,p2+:0.27] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5796 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:43 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5797 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:47 | v9=[p0:0.43,p1:0.30,p2+:0.27] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5798 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 18:48 | v9=[p0:0.49,p1:0.17,p2+:0.34] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5800 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:52 | v9=[p0:0.44,p1:0.32,p2+:0.24] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5801 | KXHIGHTOKC-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 18:54 | v9=[p0:0.44,p1:0.32,p2+:0.24] hi_f=63 nws_high=62°F running_max=17°C / spread=±0 |
| 5802 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 18:57 | v9=[p0:0.33,p1:0.24,p2+:0.43] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5803 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 18:57 | v9=[p0:0.28,p1:0.11,p2+:0.61] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5891 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:00 | v9=[p0:0.39,p1:0.22,p2+:0.40] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5897 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:02 | v9=[p0:0.40,p1:0.22,p2+:0.38] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5898 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:02 | v9=[p0:0.34,p1:0.03,p2+:0.63] hi_f=50 nws_high=50°F running_max=10°C / spread=±4 |
| 5899 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:02 | v9=[p0:0.42,p1:0.07,p2+:0.52] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5901 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 19:04 | v9=[p0:0.35,p1:0.03,p2+:0.61] hi_f=16 nws_high=15°F running_max=-9°C / spread=±3 |
| 5905 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:07 | v9=[p0:0.40,p1:0.22,p2+:0.38] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5906 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:07 | v9=[p0:0.42,p1:0.07,p2+:0.52] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5907 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:07 | v9=[p0:0.38,p1:0.03,p2+:0.59] hi_f=50 nws_high=50°F running_max=10°C / spread=±4 |
| 5909 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:09 | v9=[p0:0.27,p1:0.06,p2+:0.67] hi_f=68 nws_high=68°F running_max=20°C / spread=±4 |
| 5910 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:09 | v9=[p0:0.42,p1:0.07,p2+:0.51] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5911 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 19:09 | v9=[p0:0.38,p1:0.06,p2+:0.56] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 5912 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:09 | v9=[p0:0.38,p1:0.03,p2+:0.59] hi_f=50 nws_high=50°F running_max=10°C / spread=±4 |
| 5913 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 19:09 | v9=[p0:0.38,p1:0.06,p2+:0.56] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 5915 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:12 | v9=[p0:0.40,p1:0.22,p2+:0.38] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5916 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:12 | v9=[p0:0.38,p1:0.03,p2+:0.59] hi_f=50 nws_high=50°F running_max=10°C / spread=±4 |
| 5924 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:17 | v9=[p0:0.38,p1:0.03,p2+:0.59] hi_f=50 nws_high=50°F running_max=10°C / spread=±4 |
| 5925 | KXHIGHTSATX-26MAR17-T64 | yes | rejected | — | — | 2026-03-17 19:17 | v9=[p0:0.38,p1:0.06,p2+:0.55] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 5926 | KXHIGHTDAL-26MAR17-T63 | yes | rejected | — | — | 2026-03-17 19:20 | v9=[p0:0.80,p1:0.16,p2+:0.03] hi_f=61 nws_high=60°F running_max=16°C / spread=±2 |
| 5927 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:22 | v9=[p0:0.42,p1:0.21,p2+:0.37] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5928 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:22 | v9=[p0:0.43,p1:0.06,p2+:0.51] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5930 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:23 | v9=[p0:0.35,p1:0.04,p2+:0.61] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5932 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:27 | v9=[p0:0.35,p1:0.04,p2+:0.61] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5962 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:32 | v9=[p0:0.49,p1:0.18,p2+:0.33] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5963 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:32 | v9=[p0:0.35,p1:0.04,p2+:0.61] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5965 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:37 | v9=[p0:0.35,p1:0.04,p2+:0.61] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5967 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:39 | v9=[p0:0.39,p1:0.05,p2+:0.56] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5969 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:42 | v9=[p0:0.35,p1:0.04,p2+:0.61] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5970 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 19:43 | v9=[p0:0.49,p1:0.21,p2+:0.30] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5974 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 19:47 | v9=[p0:0.57,p1:0.16,p2+:0.27] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 5975 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 19:48 | v9=[p0:0.50,p1:0.22,p2+:0.28] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5977 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:52 | v9=[p0:0.43,p1:0.06,p2+:0.51] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5978 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:52 | v9=[p0:0.45,p1:0.04,p2+:0.50] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5979 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 19:53 | v9=[p0:0.59,p1:0.15,p2+:0.25] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5982 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 19:56 | v9=[p0:0.59,p1:0.15,p2+:0.25] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 5983 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 19:56 | v9=[p0:0.45,p1:0.04,p2+:0.50] hi_f=58 nws_high=57°F running_max=14°C / spread=±3 |
| 5984 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 19:56 | v9=[p0:0.43,p1:0.05,p2+:0.51] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 5985 | KXHIGHTSEA-26MAR17-B53.5 | no | rejected | — | — | 2026-03-17 19:58 | v9=[p0:0.59,p1:0.15,p2+:0.26] hi_f=52 nws_high=52°F running_max=11°C / spread=±0 |
| 6001 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 20:02 | v9=[p0:0.76,p1:0.09,p2+:0.15] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 6002 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 20:02 | v9=[p0:0.41,p1:0.04,p2+:0.55] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 6005 | KXHIGHDEN-26MAR17-T69 | yes | rejected | — | — | 2026-03-17 20:09 | v9=[p0:0.50,p1:0.04,p2+:0.46] hi_f=68 nws_high=68°F running_max=20°C / spread=±3 |
| 6006 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 20:09 | v9=[p0:0.44,p1:0.04,p2+:0.51] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 6008 | KXHIGHTPHX-26MAR17-T93 | yes | rejected | — | — | 2026-03-17 20:17 | v9=[p0:0.24,p1:0.03,p2+:0.72] hi_f=92 nws_high=91°F running_max=33°C / spread=±2 |
| 6009 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 20:20 | v9=[p0:0.19,p1:0.03,p2+:0.78] hi_f=85 nws_high=84°F running_max=29°C / spread=±3 |
| 6010 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 20:22 | v9=[p0:0.26,p1:0.04,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6011 | KXHIGHTPHX-26MAR17-T93 | yes | rejected | — | — | 2026-03-17 20:22 | v9=[p0:0.24,p1:0.03,p2+:0.73] hi_f=92 nws_high=91°F running_max=33°C / spread=±2 |
| 6012 | KXHIGHTNOLA-26MAR17-T54 | yes | rejected | — | — | 2026-03-17 20:23 | v9=[p0:0.47,p1:0.04,p2+:0.49] hi_f=52 nws_high=51°F running_max=11°C / spread=±4 |
| 6013 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 20:23 | v9=[p0:0.24,p1:0.04,p2+:0.72] hi_f=85 nws_high=84°F running_max=29°C / spread=±3 |
| 6014 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 20:27 | v9=[p0:0.80,p1:0.07,p2+:0.13] hi_f=59 nws_high=59°F running_max=15°C / spread=±3 |
| 6015 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 20:27 | v9=[p0:0.23,p1:0.04,p2+:0.74] hi_f=85 nws_high=84°F running_max=29°C / spread=±3 |
| 6017 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 20:37 | v9=[p0:0.80,p1:0.07,p2+:0.13] hi_f=59 nws_high=59°F running_max=15°C / spread=±3 |
| 6019 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 20:39 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=59 nws_high=59°F running_max=15°C / spread=±2 |
| 6027 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 21:06 | v9=[p0:0.33,p1:0.04,p2+:0.63] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6028 | KXHIGHTPHX-26MAR17-B95.5 | no | rejected | — | — | 2026-03-17 21:07 | v9=[p0:0.47,p1:0.04,p2+:0.49] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6037 | KXHIGHTPHX-26MAR17-B95.5 | no | rejected | — | — | 2026-03-17 21:17 | v9=[p0:0.44,p1:0.03,p2+:0.53] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6041 | KXHIGHTPHX-26MAR17-B95.5 | no | rejected | — | — | 2026-03-17 21:22 | v9=[p0:0.44,p1:0.03,p2+:0.53] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6043 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:22 | v9=[p0:0.87,p1:0.04,p2+:0.08] hi_f=59 nws_high=59°F running_max=15°C / spread=±4 |
| 6045 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 21:25 | v9=[p0:0.32,p1:0.04,p2+:0.64] hi_f=74 nws_high=73°F running_max=23°C / spread=±1 |
| 6047 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:27 | v9=[p0:0.87,p1:0.04,p2+:0.09] hi_f=59 nws_high=59°F running_max=15°C / spread=±4 |
| 6048 | KXHIGHTPHX-26MAR17-B95.5 | no | rejected | — | — | 2026-03-17 21:32 | v9=[p0:0.51,p1:0.03,p2+:0.46] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6052 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 21:35 | v9=[p0:0.38,p1:0.03,p2+:0.58] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6057 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:37 | v9=[p0:0.84,p1:0.04,p2+:0.12] hi_f=59 nws_high=59°F running_max=15°C / spread=±4 |
| 6060 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:38 | v9=[p0:0.82,p1:0.04,p2+:0.14] hi_f=59 nws_high=59°F running_max=15°C / spread=±4 |
| 6063 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:39 | v9=[p0:0.89,p1:0.04,p2+:0.06] hi_f=59 nws_high=59°F running_max=15°C / spread=±3 |
| 6066 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 21:40 | v9=[p0:0.32,p1:0.04,p2+:0.64] hi_f=76 nws_high=75°F running_max=24°C / spread=±1 |
| 6067 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 21:42 | v9=[p0:0.42,p1:0.03,p2+:0.55] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6069 | KXHIGHTHOU-26MAR17-T60 | yes | rejected | — | — | 2026-03-17 21:57 | v9=[p0:0.82,p1:0.04,p2+:0.14] hi_f=59 nws_high=59°F running_max=15°C / spread=±4 |
| 6070 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 21:58 | v9=[p0:0.45,p1:0.03,p2+:0.52] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6071 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 21:58 | v9=[p0:0.45,p1:0.03,p2+:0.52] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6086 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 22:02 | v9=[p0:0.50,p1:0.02,p2+:0.47] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6087 | KXHIGHTLV-26MAR17-T88 | yes | rejected | — | — | 2026-03-17 22:06 | v9=[p0:0.50,p1:0.02,p2+:0.48] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 6095 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:17 | v9=[p0:0.48,p1:0.04,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6099 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:23 | v9=[p0:0.48,p1:0.04,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6102 | KXHIGHTSFO-26MAR17-T79 | yes | rejected | — | — | 2026-03-17 22:24 | v9=[p0:0.35,p1:0.03,p2+:0.62] hi_f=77 nws_high=77°F running_max=25°C / spread=±1 |
| 6104 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:27 | v9=[p0:0.85,p1:0.06,p2+:0.10] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6138 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:33 | v9=[p0:0.48,p1:0.04,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6140 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:38 | v9=[p0:0.48,p1:0.04,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6141 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:38 | v9=[p0:0.84,p1:0.05,p2+:0.10] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6144 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:43 | v9=[p0:0.84,p1:0.06,p2+:0.10] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6146 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:47 | v9=[p0:0.84,p1:0.06,p2+:0.10] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6148 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:53 | v9=[p0:0.48,p1:0.04,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6149 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:55 | v9=[p0:0.84,p1:0.06,p2+:0.10] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6150 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 22:58 | v9=[p0:0.83,p1:0.06,p2+:0.11] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6151 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:03 | v9=[p0:0.82,p1:0.06,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6156 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:07 | v9=[p0:0.82,p1:0.06,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6157 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:08 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6158 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:13 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6163 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:18 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6166 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:23 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6169 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:27 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6170 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:33 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6173 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:38 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6174 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:38 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6175 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:43 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6176 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:47 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6177 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:53 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6178 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:55 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6181 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-17 23:57 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6198 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:08 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6204 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:08 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6205 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:13 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6212 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:18 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6213 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:23 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6215 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:27 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6216 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:32 | v9=[p0:0.47,p1:0.03,p2+:0.50] hi_f=18 nws_high=17°F running_max=-8°C / spread=±6 |
| 6221 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:38 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6228 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:38 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6229 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:43 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6231 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:48 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6232 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:55 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6233 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 00:58 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6235 | KXHIGHTMIN-26MAR17-T19 | yes | rejected | — | — | 2026-03-18 01:03 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6236 | KXHIGHTMIN-26MAR17-T19 | yes | voided | 0.34 | — | 2026-03-18 01:06 | v9=[p0:0.83,p1:0.05,p2+:0.12] hi_f=18 nws_high=17°F running_max=-8°C / spread=±4 |
| 6361 | KXHIGHTATL-26MAR18-T51 | yes | lost | 0.01 | -11.26 | 2026-03-18 12:02 | v9=[p0:0.13,p1:0.01,p2+:0.87] hi_f=43 nws_high=42°F running_max=6°C / spread=±5. |
| 6368 | KXHIGHTDC-26MAR18-T41 | yes | rejected | — | — | 2026-03-18 13:03 | v9=[p0:0.26,p1:0.01,p2+:0.72] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6369 | KXHIGHTDC-26MAR18-T41 | yes | lost | 0.12 | -23.57 | 2026-03-18 13:17 | v9=[p0:0.26,p1:0.01,p2+:0.72] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6490 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:37 | v9=[p0:0.26,p1:0.01,p2+:0.73] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6492 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:42 | v9=[p0:0.26,p1:0.02,p2+:0.73] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6493 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:47 | v9=[p0:0.27,p1:0.01,p2+:0.71] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6494 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:52 | v9=[p0:0.27,p1:0.01,p2+:0.72] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6495 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:56 | v9=[p0:0.27,p1:0.01,p2+:0.72] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6496 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 15:57 | v9=[p0:0.27,p1:0.01,p2+:0.72] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6517 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:02 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6519 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 16:02 | v9=[p0:0.31,p1:0.02,p2+:0.67] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6520 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 16:07 | v9=[p0:0.31,p1:0.02,p2+:0.67] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6521 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:07 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6522 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 16:08 | v9=[p0:0.31,p1:0.02,p2+:0.67] hi_f=63 nws_high=62°F running_max=17°C / spread=±3 |
| 6523 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:09 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6526 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 16:12 | v9=[p0:0.31,p1:0.02,p2+:0.67] hi_f=63 nws_high=62°F running_max=17°C / spread=±2 |
| 6528 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:12 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6530 | KXHIGHDEN-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 16:16 | v9=[p0:0.28,p1:0.02,p2+:0.70] hi_f=70 nws_high=69°F running_max=21°C / spread=±2 |
| 6532 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:22 | v9=[p0:0.26,p1:0.02,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6534 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:23 | v9=[p0:0.26,p1:0.02,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6535 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:27 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6580 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:32 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6581 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:37 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6582 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:42 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6583 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:47 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6585 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:52 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6586 | KXHIGHLAX-26MAR18-T82 | yes | rejected | — | — | 2026-03-18 16:54 | v9=[p0:0.21,p1:0.24,p2+:0.55] hi_f=81 nws_high=80°F running_max=27°C / spread=±1 |
| 6587 | KXHIGHLAX-26MAR18-T82 | yes | rejected | — | — | 2026-03-18 16:55 | v9=[p0:0.21,p1:0.24,p2+:0.55] hi_f=81 nws_high=80°F running_max=27°C / spread=±1 |
| 6590 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 16:58 | v9=[p0:0.24,p1:0.02,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6592 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:03 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6593 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:03 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6596 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:08 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6597 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:09 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6598 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:09 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6600 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:11 | v9=[p0:0.26,p1:0.07,p2+:0.67] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6602 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:12 | v9=[p0:0.29,p1:0.02,p2+:0.69] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6603 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:18 | v9=[p0:0.28,p1:0.08,p2+:0.64] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6604 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:18 | v9=[p0:0.26,p1:0.02,p2+:0.71] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6605 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:22 | v9=[p0:0.26,p1:0.07,p2+:0.66] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6606 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:27 | v9=[p0:0.13,p1:0.03,p2+:0.85] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6607 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:28 | v9=[p0:0.29,p1:0.08,p2+:0.63] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6609 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:32 | v9=[p0:0.29,p1:0.08,p2+:0.63] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6610 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:32 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6611 | KXHIGHCHI-26MAR18-T40 | yes | rejected | — | — | 2026-03-18 17:36 | v9=[p0:0.05,p1:0.04,p2+:0.91] hi_f=38 nws_high=37°F running_max=3°C / spread=±7. |
| 6612 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:37 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6613 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:39 | v9=[p0:0.13,p1:0.03,p2+:0.85] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6614 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:43 | v9=[p0:0.30,p1:0.08,p2+:0.62] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6615 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:43 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6616 | KXHIGHTMIN-26MAR18-T40 | yes | rejected | — | — | 2026-03-18 17:43 | v9=[p0:0.34,p1:0.22,p2+:0.44] hi_f=38 nws_high=37°F running_max=3°C / spread=±14 |
| 6617 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:47 | v9=[p0:0.31,p1:0.12,p2+:0.57] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6618 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:47 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6619 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:53 | v9=[p0:0.34,p1:0.07,p2+:0.59] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 6620 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:53 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6621 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:56 | v9=[p0:0.34,p1:0.07,p2+:0.59] hi_f=38 nws_high=38°F running_max=3°C / spread=±3. |
| 6622 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 17:56 | v9=[p0:0.34,p1:0.07,p2+:0.59] hi_f=38 nws_high=38°F running_max=3°C / spread=±3. |
| 6624 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 17:58 | v9=[p0:0.13,p1:0.02,p2+:0.84] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6640 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 18:00 | v9=[p0:0.47,p1:0.04,p2+:0.48] hi_f=38 nws_high=38°F running_max=3°C / spread=±3. |
| 6641 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:01 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6642 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 18:02 | v9=[p0:0.47,p1:0.04,p2+:0.49] hi_f=38 nws_high=38°F running_max=3°C / spread=±3. |
| 6643 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:02 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6644 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:03 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6646 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:06 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6647 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:07 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6648 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:07 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6649 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:08 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±0. |
| 6650 | KXHIGHTNOLA-26MAR18-T63 | yes | rejected | — | — | 2026-03-18 18:09 | v9=[p0:0.25,p1:0.04,p2+:0.72] hi_f=61 nws_high=60°F running_max=16°C / spread=±5 |
| 6651 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:09 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6652 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:09 | v9=[p0:0.17,p1:0.03,p2+:0.80] hi_f=74 nws_high=73°F running_max=23°C / spread=±6 |
| 6653 | KXHIGHTNOLA-26MAR18-T63 | yes | rejected | — | — | 2026-03-18 18:12 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=61 nws_high=60°F running_max=16°C / spread=±6 |
| 6654 | KXHIGHPHIL-26MAR18-T39 | yes | rejected | — | — | 2026-03-18 18:13 | v9=[p0:0.47,p1:0.04,p2+:0.49] hi_f=38 nws_high=38°F running_max=3°C / spread=±3. |
| 6655 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:13 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6656 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:17 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6657 | KXHIGHTNOLA-26MAR18-T63 | yes | rejected | — | — | 2026-03-18 18:17 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=61 nws_high=60°F running_max=16°C / spread=±6 |
| 6659 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:18 | v9=[p0:0.24,p1:0.03,p2+:0.74] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6660 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:22 | v9=[p0:0.83,p1:0.14,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6661 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:22 | v9=[p0:0.24,p1:0.04,p2+:0.72] hi_f=74 nws_high=73°F running_max=23°C / spread=±6 |
| 6662 | KXHIGHTNOLA-26MAR18-T63 | yes | rejected | — | — | 2026-03-18 18:22 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=61 nws_high=60°F running_max=16°C / spread=±6 |
| 6664 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:23 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6665 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:26 | v9=[p0:0.43,p1:0.28,p2+:0.29] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6666 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:27 | v9=[p0:0.85,p1:0.12,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6668 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:28 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6669 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:32 | v9=[p0:0.85,p1:0.12,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6670 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:32 | v9=[p0:0.26,p1:0.04,p2+:0.70] hi_f=74 nws_high=73°F running_max=23°C / spread=±6 |
| 6671 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 18:32 | v9=[p0:0.18,p1:0.04,p2+:0.78] hi_f=68 nws_high=68°F running_max=20°C / spread=±2 |
| 6672 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:32 | v9=[p0:0.44,p1:0.28,p2+:0.28] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6674 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:33 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6675 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:37 | v9=[p0:0.85,p1:0.12,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6676 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:37 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6677 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:38 | v9=[p0:0.82,p1:0.15,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±0. |
| 6678 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 18:38 | v9=[p0:0.22,p1:0.04,p2+:0.74] hi_f=68 nws_high=68°F running_max=20°C / spread=±3 |
| 6680 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:39 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=74 nws_high=73°F running_max=23°C / spread=±3 |
| 6681 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:39 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6682 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:39 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6684 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:42 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6685 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 18:42 | v9=[p0:0.49,p1:0.32,p2+:0.19] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6686 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 18:43 | v9=[p0:0.11,p1:0.03,p2+:0.86] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6687 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:47 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6689 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:52 | v9=[p0:0.85,p1:0.12,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6690 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 18:52 | v9=[p0:0.14,p1:0.03,p2+:0.83] hi_f=70 nws_high=69°F running_max=21°C / spread=±2 |
| 6693 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 18:55 | v9=[p0:0.16,p1:0.04,p2+:0.80] hi_f=70 nws_high=69°F running_max=21°C / spread=±2 |
| 6694 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:56 | v9=[p0:0.88,p1:0.08,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6695 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:56 | v9=[p0:0.88,p1:0.08,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6696 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 18:57 | v9=[p0:0.88,p1:0.08,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6699 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:01 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6700 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:02 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6701 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:03 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6705 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:06 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6706 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:07 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6709 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:08 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6710 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:08 | v9=[p0:0.86,p1:0.11,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±0. |
| 6713 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:09 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6714 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:10 | v9=[p0:0.60,p1:0.11,p2+:0.30] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6715 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:12 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6716 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:12 | v9=[p0:0.90,p1:0.07,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6717 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:13 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6718 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:17 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6719 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 19:17 | v9=[p0:0.34,p1:0.04,p2+:0.62] hi_f=72 nws_high=71°F running_max=22°C / spread=±2 |
| 6720 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:17 | v9=[p0:0.91,p1:0.07,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6722 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:18 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6723 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:18 | v9=[p0:0.23,p1:0.04,p2+:0.73] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6724 | KXHIGHTPHX-26MAR18-T99 | yes | rejected | — | — | 2026-03-18 19:22 | v9=[p0:0.22,p1:0.03,p2+:0.75] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6725 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:22 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6726 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 19:22 | v9=[p0:0.33,p1:0.04,p2+:0.63] hi_f=72 nws_high=71°F running_max=22°C / spread=±2 |
| 6727 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:22 | v9=[p0:0.36,p1:0.04,p2+:0.60] hi_f=76 nws_high=75°F running_max=24°C / spread=±6 |
| 6728 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:22 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6729 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:23 | v9=[p0:0.16,p1:0.04,p2+:0.80] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6730 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:27 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6731 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 19:27 | v9=[p0:0.33,p1:0.04,p2+:0.63] hi_f=72 nws_high=71°F running_max=22°C / spread=±2 |
| 6732 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:27 | v9=[p0:0.91,p1:0.07,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6734 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:28 | v9=[p0:0.16,p1:0.04,p2+:0.80] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6762 | KXHIGHTPHX-26MAR18-T99 | yes | rejected | — | — | 2026-03-18 19:32 | v9=[p0:0.27,p1:0.03,p2+:0.70] hi_f=94 nws_high=93°F running_max=34°C / spread=±2 |
| 6763 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:32 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6764 | KXHIGHTOKC-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:32 | v9=[p0:0.35,p1:0.03,p2+:0.62] hi_f=76 nws_high=75°F running_max=24°C / spread=±6 |
| 6765 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:32 | v9=[p0:0.92,p1:0.06,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6766 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:33 | v9=[p0:0.16,p1:0.04,p2+:0.80] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6767 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:35 | v9=[p0:0.16,p1:0.04,p2+:0.80] hi_f=70 nws_high=69°F running_max=21°C / spread=±1 |
| 6768 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:37 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6769 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:37 | v9=[p0:0.91,p1:0.07,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6771 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:38 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±0. |
| 6773 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:39 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±3 |
| 6774 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 19:42 | v9=[p0:0.91,p1:0.06,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6775 | KXHIGHAUS-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:42 | v9=[p0:0.93,p1:0.05,p2+:0.02] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6777 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:49 | v9=[p0:0.13,p1:0.04,p2+:0.83] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6778 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:52 | v9=[p0:0.81,p1:0.16,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6779 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 19:53 | v9=[p0:0.13,p1:0.04,p2+:0.83] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6780 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:53 | v9=[p0:0.81,p1:0.16,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6781 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:56 | v9=[p0:0.82,p1:0.14,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6782 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 19:57 | v9=[p0:0.82,p1:0.14,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6801 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 20:00 | v9=[p0:0.87,p1:0.09,p2+:0.04] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6802 | KXHIGHTPHX-26MAR18-T99 | yes | rejected | — | — | 2026-03-18 20:02 | v9=[p0:0.23,p1:0.03,p2+:0.73] hi_f=97 nws_high=96°F running_max=36°C / spread=±2 |
| 6804 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 20:02 | v9=[p0:0.88,p1:0.08,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6807 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 20:03 | v9=[p0:0.24,p1:0.04,p2+:0.73] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6808 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 20:04 | v9=[p0:0.24,p1:0.04,p2+:0.73] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6809 | KXHIGHTPHX-26MAR18-T99 | yes | rejected | — | — | 2026-03-18 20:07 | v9=[p0:0.25,p1:0.03,p2+:0.72] hi_f=97 nws_high=96°F running_max=36°C / spread=±2 |
| 6811 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 20:07 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6813 | KXHIGHTPHX-26MAR18-T99 | yes | rejected | — | — | 2026-03-18 20:09 | v9=[p0:0.22,p1:0.03,p2+:0.75] hi_f=97 nws_high=96°F running_max=36°C / spread=±1 |
| 6814 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 20:09 | v9=[p0:0.89,p1:0.07,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±3 |
| 6815 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 20:09 | v9=[p0:0.24,p1:0.04,p2+:0.73] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6816 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 20:12 | v9=[p0:0.87,p1:0.09,p2+:0.04] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6817 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 20:12 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6820 | KXHIGHTDAL-26MAR18-T75 | yes | rejected | — | — | 2026-03-18 20:17 | v9=[p0:0.88,p1:0.09,p2+:0.03] hi_f=74 nws_high=73°F running_max=23°C / spread=±2 |
| 6821 | KXHIGHTSATX-26MAR18-T77 | yes | rejected | — | — | 2026-03-18 20:17 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 6824 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 20:23 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6826 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 20:27 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6827 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 20:28 | v9=[p0:0.25,p1:0.04,p2+:0.71] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 6828 | KXHIGHTBOS-26MAR18-T37 | yes | rejected | — | — | 2026-03-18 20:32 | v9=[p0:0.92,p1:0.05,p2+:0.03] hi_f=36 nws_high=36°F running_max=2°C / spread=±2. |
| 6829 | KXHIGHTLV-26MAR18-T92 | yes | rejected | — | — | 2026-03-18 20:35 | v9=[p0:0.22,p1:0.03,p2+:0.75] hi_f=90 nws_high=89°F running_max=32°C / spread=±2 |
| 6841 | KXHIGHTPHX-26MAR18-B101.5 | no | rejected | — | — | 2026-03-18 21:02 | v9=[p0:0.48,p1:0.03,p2+:0.49] hi_f=99 nws_high=98°F running_max=37°C / spread=±2 |
| 6843 | KXHIGHTPHX-26MAR18-B101.5 | no | rejected | — | — | 2026-03-18 21:07 | v9=[p0:0.48,p1:0.02,p2+:0.49] hi_f=99 nws_high=98°F running_max=37°C / spread=±2 |
| 6855 | KXHIGHTPHX-26MAR18-B101.5 | no | rejected | — | — | 2026-03-18 21:17 | v9=[p0:0.50,p1:0.03,p2+:0.48] hi_f=99 nws_high=98°F running_max=37°C / spread=±2 |
| 6860 | KXHIGHTPHX-26MAR18-B101.5 | no | rejected | — | — | 2026-03-18 21:22 | v9=[p0:0.48,p1:0.02,p2+:0.49] hi_f=99 nws_high=98°F running_max=37°C / spread=±2 |
| 6861 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 21:24 | v9=[p0:0.34,p1:0.04,p2+:0.62] hi_f=74 nws_high=73°F running_max=23°C / spread=±1 |
| 6863 | KXHIGHTPHX-26MAR18-B101.5 | no | rejected | — | — | 2026-03-18 21:27 | v9=[p0:0.50,p1:0.03,p2+:0.48] hi_f=99 nws_high=98°F running_max=37°C / spread=±2 |
| 6867 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 21:34 | v9=[p0:0.34,p1:0.04,p2+:0.62] hi_f=76 nws_high=75°F running_max=24°C / spread=±1 |
| 7104 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 22:04 | v9=[p0:0.88,p1:0.08,p2+:0.04] hi_f=77 nws_high=77°F running_max=25°C / spread=±1 |
| 7107 | KXHIGHTSFO-26MAR18-T79 | yes | rejected | — | — | 2026-03-18 22:06 | v9=[p0:0.89,p1:0.08,p2+:0.03] hi_f=77 nws_high=77°F running_max=25°C / spread=±1 |
| 7288 | KXHIGHTATL-26MAR19-T64 | yes | lost | 0.02 | -16.86 | 2026-03-19 12:02 | v9=[p0:0.14,p1:0.01,p2+:0.85] hi_f=54 nws_high=53°F running_max=12°C / spread=±2 |
| 7356 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:02 | v9=[p0:0.12,p1:0.04,p2+:0.84] hi_f=36 nws_high=35°F running_max=2°C / spread=±3. |
| 7357 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:03 | v9=[p0:0.17,p1:0.04,p2+:0.80] hi_f=36 nws_high=35°F running_max=2°C / spread=±3. |
| 7358 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:08 | v9=[p0:0.28,p1:0.03,p2+:0.69] hi_f=36 nws_high=35°F running_max=2°C / spread=±1. |
| 7359 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:12 | v9=[p0:0.28,p1:0.03,p2+:0.69] hi_f=36 nws_high=35°F running_max=2°C / spread=±3. |
| 7360 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:17 | v9=[p0:0.28,p1:0.03,p2+:0.69] hi_f=36 nws_high=35°F running_max=2°C / spread=±3. |
| 7361 | KXHIGHTBOS-26MAR19-T39 | yes | rejected | — | — | 2026-03-19 15:22 | v9=[p0:0.23,p1:0.03,p2+:0.74] hi_f=36 nws_high=35°F running_max=2°C / spread=±3. |
| 7457 | KXHIGHTDC-26MAR19-T52 | yes | rejected | — | — | 2026-03-19 16:34 | v9=[p0:0.05,p1:0.05,p2+:0.90] hi_f=50 nws_high=50°F running_max=10°C / spread=±3 |
| 7458 | KXHIGHTSEA-26MAR19-T53 | yes | rejected | — | — | 2026-03-19 16:41 | v9=[p0:0.37,p1:0.22,p2+:0.41] hi_f=52 nws_high=51°F running_max=11°C / spread=±2 |
| 7459 | KXHIGHTDC-26MAR19-T52 | yes | rejected | — | — | 2026-03-19 16:42 | v9=[p0:0.06,p1:0.04,p2+:0.90] hi_f=50 nws_high=50°F running_max=10°C / spread=±3 |
| 7463 | KXHIGHTBOS-26MAR19-T39 | yes | lost | 0.14 | -32.23 | 2026-03-19 17:49 | v9=[p0:0.34,p1:0.11,p2+:0.55] hi_f=38 nws_high=37°F running_max=3°C / spread=±3. |
| 7464 | KXHIGHAUS-26MAR19-T83 | yes | lost | 0.02 | -8.60 | 2026-03-19 17:51 | v9=[p0:0.05,p1:0.05,p2+:0.90] hi_f=79 nws_high=78°F running_max=26°C / spread=±3 |
| 7472 | KXHIGHTSATX-26MAR19-T81 | yes | lost | 0.02 | -16.05 | 2026-03-19 18:04 | v9=[p0:0.13,p1:0.03,p2+:0.84] hi_f=76 nws_high=75°F running_max=24°C / spread=±4 |
| 7473 | KXHIGHTSFO-26MAR19-T78 | yes | lost | 0.08 | -11.02 | 2026-03-19 18:06 | v9=[p0:0.11,p1:0.03,p2+:0.86] hi_f=65 nws_high=64°F running_max=18°C / spread=±9 |
| 7474 | KXHIGHDEN-26MAR19-T82 | yes | lost | 0.06 | -5.63 | 2026-03-19 18:14 | v9=[p0:0.05,p1:0.06,p2+:0.89] hi_f=79 nws_high=78°F running_max=26°C / spread=±0 |
| 7475 | KXHIGHTOKC-26MAR19-T87 | yes | lost | 0.04 | -20.43 | 2026-03-19 18:36 | v9=[p0:0.19,p1:0.03,p2+:0.78] hi_f=85 nws_high=84°F running_max=29°C / spread=±6 |
| 7476 | KXHIGHPHIL-26MAR19-T48 | yes | lost | 0.14 | -32.47 | 2026-03-19 18:58 | v9=[p0:0.41,p1:0.03,p2+:0.57] hi_f=47 nws_high=46°F running_max=8°C / spread=±1. |
| 7477 | KXHIGHTDAL-26MAR19-T87 | yes | won | 0.64 | +30.63 | 2026-03-19 19:11 | v9=[p0:0.79,p1:0.09,p2+:0.12] hi_f=83 nws_high=82°F running_max=28°C / spread=±2 |
| 7478 | KXHIGHTPHX-26MAR19-T101 | yes | rejected | — | — | 2026-03-19 19:18 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=99 nws_high=98°F running_max=37°C / spread=±1 |
| 7479 | KXHIGHTHOU-26MAR19-T80 | yes | lost | 0.69 | -25.86 | 2026-03-19 19:26 | v9=[p0:0.79,p1:0.09,p2+:0.11] hi_f=79 nws_high=78°F running_max=26°C / spread=±6 |
| 7480 | KXHIGHTPHX-26MAR19-T101 | yes | rejected | — | — | 2026-03-19 19:27 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=99 nws_high=98°F running_max=37°C / spread=±1 |
| 7508 | KXHIGHTPHX-26MAR19-T101 | yes | lost | 0.04 | -3.32 | 2026-03-19 19:32 | v9=[p0:0.03,p1:0.03,p2+:0.93] hi_f=99 nws_high=98°F running_max=37°C / spread=±1 |
| 7520 | KXHIGHTLV-26MAR19-T93 | yes | lost | 0.08 | -15.13 | 2026-03-19 20:37 | v9=[p0:0.26,p1:0.05,p2+:0.69] hi_f=92 nws_high=91°F running_max=33°C / spread=±2 |
| 7672 | KXHIGHTATL-26MAR20-T72 | yes | lost | 0.03 | -19.70 | 2026-03-20 14:22 | v9=[p0:0.23,p1:0.02,p2+:0.75] hi_f=70 nws_high=69°F running_max=21°C / spread=±2 |
| 7803 | KXHIGHTDC-26MAR20-T64 | yes | rejected | — | — | 2026-03-20 15:52 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=58 nws_high=57°F running_max=14°C / spread=±6 |
| 7876 | KXHIGHTSFO-26MAR20-T76 | yes | lost | 0.05 | -3.60 | 2026-03-20 17:22 | v9=[p0:0.06,p1:0.03,p2+:0.91] hi_f=70 nws_high=70°F running_max=21°C / spread=±1 |
| 7884 | KXHIGHAUS-26MAR20-T88 | yes | lost | 0.02 | -49.67 | 2026-03-20 18:22 | v9=[p0:0.43,p1:0.29,p2+:0.28] hi_f=85 nws_high=84°F running_max=29°C / spread=±3 |
| 7889 | KXHIGHTSATX-26MAR20-T87 | yes | lost | 0.29 | -21.14 | 2026-03-20 19:18 | v9=[p0:0.37,p1:0.05,p2+:0.58] hi_f=86 nws_high=86°F running_max=30°C / spread=±4 |
| 7921 | KXHIGHTHOU-26MAR20-T83 | yes | lost | 0.25 | -20.31 | 2026-03-20 19:27 | v9=[p0:0.44,p1:0.04,p2+:0.52] hi_f=81 nws_high=80°F running_max=27°C / spread=±4 |
| 7922 | KXHIGHTHOU-26MAR20-B83.5 | no | lost | 0.37 | -15.21 | 2026-03-20 19:27 | v9=[p0:0.44,p1:0.04,p2+:0.52] hi_f=81 nws_high=80°F running_max=27°C / spread=±4 |
| 7924 | KXHIGHTDAL-26MAR20-T91 | yes | won | 0.68 | +16.13 | 2026-03-20 19:29 | v9=[p0:0.86,p1:0.08,p2+:0.05] hi_f=88 nws_high=87°F running_max=31°C / spread=±0 |
| 7981 | KXHIGHTPHX-26MAR20-T104 | yes | lost | 0.08 | -6.33 | 2026-03-20 20:07 | v9=[p0:0.17,p1:0.03,p2+:0.80] hi_f=101 nws_high=100°F running_max=38°C / spread= |
| 8000 | KXHIGHTLV-26MAR20-T96 | yes | lost | 0.20 | -3.12 | 2026-03-20 20:22 | v9=[p0:0.21,p1:0.04,p2+:0.75] hi_f=92 nws_high=91°F running_max=33°C / spread=±3 |
| 8106 | KXHIGHTNOLA-26MAR20-T77 | yes | rejected | — | — | 2026-03-20 21:32 | v9=[p0:0.88,p1:0.04,p2+:0.07] hi_f=76 nws_high=76°F running_max=24°C / spread=±5 |
| 8111 | KXHIGHTNOLA-26MAR20-T77 | yes | won | 0.87 | +1.82 | 2026-03-20 21:58 | v9=[p0:0.90,p1:0.04,p2+:0.05] hi_f=76 nws_high=76°F running_max=24°C / spread=±4 |
| 8308 | KXHIGHTBOS-26MAR21-T50 | yes | voided | 0.26 | — | 2026-03-21 05:52 | v9=[p0:0.32,p1:0.08,p2+:0.59] hi_f=47 nws_high=46°F running_max=8°C / spread=±3. |
| 8316 | KXHIGHTATL-26MAR21-T80 | yes | voided | 0.03 | — | 2026-03-21 12:02 | v9=[p0:0.09,p1:0.01,p2+:0.90] hi_f=77 nws_high=77°F running_max=25°C / spread=±3 |
| 8317 | KXHIGHMIA-26MAR21-T75 | yes | voided | 0.01 | — | 2026-03-21 12:03 | v9=[p0:0.06,p1:0.01,p2+:0.94] hi_f=72 nws_high=72°F running_max=22°C / spread=±2 |
| 8347 | KXHIGHTDAL-26MAR21-T90 | yes | voided | 0.10 | — | 2026-03-21 14:02 | v9=[p0:0.20,p1:0.01,p2+:0.80] hi_f=72 nws_high=71°F running_max=22°C / spread=±1 |
| 8356 | KXHIGHTSFO-26MAR21-T66 | yes | voided | 0.04 | — | 2026-03-21 15:00 | v9=[p0:0.07,p1:0.01,p2+:0.92] hi_f=65 nws_high=65°F running_max=18°C / spread=±1 |
| 8661 | KXHIGHCHI-26MAR21-T63 | yes | voided | 0.01 | — | 2026-03-21 16:29 | v9=[p0:0.04,p1:0.04,p2+:0.92] hi_f=58 nws_high=57°F running_max=14°C / spread=±8 |
| 8700 | KXHIGHTDC-26MAR21-T68 | no | lost | 0.34 | -9.54 | 2026-03-21 17:08 | v9=[p0:0.56,p1:0.32,p2+:0.12] hi_f=68 nws_high=68°F running_max=20°C / spread=±6 |
| 8701 | KXHIGHTSATX-26MAR21-T90 | yes | voided | 0.02 | — | 2026-03-21 17:10 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=79 nws_high=78°F running_max=26°C / spread=±3 |
| 8703 | KXHIGHLAX-26MAR21-T76 | yes | won | 0.21 | +70.25 | 2026-03-21 17:14 | v9=[p0:0.26,p1:0.24,p2+:0.49] hi_f=74 nws_high=73°F running_max=23°C / spread=±1 |
| 8786 | KXHIGHAUS-26MAR21-T91 | yes | voided | 0.10 | — | 2026-03-21 18:01 | v9=[p0:0.16,p1:0.07,p2+:0.76] hi_f=85 nws_high=84°F running_max=29°C / spread=±4 |
| 8788 | KXHIGHTOKC-26MAR21-T93 | yes | voided | 0.08 | — | 2026-03-21 18:02 | v9=[p0:0.17,p1:0.03,p2+:0.80] hi_f=90 nws_high=89°F running_max=32°C / spread=±2 |
| 8792 | KXHIGHDEN-26MAR21-T86 | yes | lost | 0.03 | -2.29 | 2026-03-21 18:18 | v9=[p0:0.04,p1:0.05,p2+:0.92] hi_f=83 nws_high=82°F running_max=28°C / spread=±2 |
| 8812 | KXHIGHTPHX-26MAR21-T103 | yes | voided | 0.05 | — | 2026-03-21 19:02 | v9=[p0:0.05,p1:0.04,p2+:0.91] hi_f=97 nws_high=96°F running_max=36°C / spread=±1 |
| 8984 | KXHIGHTHOU-26MAR21-T87 | yes | won | 0.93 | +1.77 | 2026-03-21 21:22 | v9=[p0:0.99,p1:0.01,p2+:0.00] hi_f=86 nws_high=86°F running_max=30°C / spread=±3 |
| 9185 | KXHIGHTATL-26MAR22-T82 | yes | expired | 0.03 | +0.00 | 2026-03-22 12:03 | v9=[p0:0.07,p1:0.01,p2+:0.93] hi_f=70 nws_high=69°F running_max=21°C / spread=±2 |
| 9211 | KXHIGHTDAL-26MAR22-T91 | yes | expired | 0.08 | +0.00 | 2026-03-22 14:02 | v9=[p0:0.18,p1:0.01,p2+:0.81] hi_f=76 nws_high=75°F running_max=24°C / spread=±2 |
| 9212 | KXHIGHTSATX-26MAR22-T90 | yes | expired | 0.06 | +0.00 | 2026-03-22 14:03 | v9=[p0:0.16,p1:0.00,p2+:0.83] hi_f=72 nws_high=71°F running_max=22°C / spread=±3 |
| 9291 | KXHIGHPHIL-26MAR22-T71 | yes | rejected | — | — | 2026-03-22 15:01 | v9=[p0:0.05,p1:0.03,p2+:0.92] hi_f=56 nws_high=55°F running_max=13°C / spread=±9 |
| 9294 | KXHIGHTDC-26MAR22-T78 | yes | rejected | — | — | 2026-03-22 15:05 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=61 nws_high=60°F running_max=16°C / spread=±8 |
| 9498 | KXHIGHTDC-26MAR22-T78 | yes | rejected | — | — | 2026-03-22 15:34 | v9=[p0:0.03,p1:0.03,p2+:0.94] hi_f=63 nws_high=62°F running_max=17°C / spread=±8 |
| 9542 | KXHIGHTDC-26MAR22-T78 | yes | expired | 0.04 | +0.00 | 2026-03-22 16:07 | v9=[p0:0.05,p1:0.03,p2+:0.92] hi_f=65 nws_high=64°F running_max=18°C / spread=±8 |
| 9547 | KXHIGHAUS-26MAR22-T90 | yes | expired | 0.01 | +0.00 | 2026-03-22 16:14 | v9=[p0:0.02,p1:0.03,p2+:0.96] hi_f=77 nws_high=77°F running_max=25°C / spread=±3 |
| 9556 | KXHIGHTNOLA-26MAR22-T78 | yes | rejected | — | — | 2026-03-22 16:21 | v9=[p0:0.02,p1:0.03,p2+:0.95] hi_f=76 nws_high=75°F running_max=24°C / spread=±3 |
| 9606 | KXHIGHPHIL-26MAR22-T71 | yes | rejected | — | — | 2026-03-22 17:05 | v9=[p0:0.15,p1:0.04,p2+:0.82] hi_f=63 nws_high=62°F running_max=17°C / spread=±9 |
| 9609 | KXHIGHTNOLA-26MAR22-T78 | yes | rejected | — | — | 2026-03-22 17:07 | v9=[p0:0.05,p1:0.03,p2+:0.92] hi_f=77 nws_high=77°F running_max=25°C / spread=±3 |
| 9693 | KXHIGHPHIL-26MAR22-T71 | yes | rejected | — | — | 2026-03-22 17:37 | v9=[p0:0.15,p1:0.04,p2+:0.81] hi_f=65 nws_high=64°F running_max=18°C / spread=±9 |
| 9728 | KXHIGHPHIL-26MAR22-T71 | yes | expired | 0.11 | +0.00 | 2026-03-22 18:02 | v9=[p0:0.30,p1:0.03,p2+:0.67] hi_f=67 nws_high=66°F running_max=19°C / spread=±9 |
| 9741 | KXHIGHTBOS-26MAR22-T49 | yes | rejected | — | — | 2026-03-22 18:21 | v9=[p0:0.82,p1:0.10,p2+:0.08] hi_f=45 nws_high=45°F running_max=7°C / spread=±2. |
| 9752 | KXHIGHTHOU-26MAR22-T84 | yes | rejected | — | — | 2026-03-22 18:35 | v9=[p0:0.44,p1:0.32,p2+:0.24] hi_f=83 nws_high=82°F running_max=28°C / spread=±4 |
| 9755 | KXHIGHTHOU-26MAR22-T84 | yes | rejected | — | — | 2026-03-22 18:36 | v9=[p0:0.44,p1:0.32,p2+:0.24] hi_f=83 nws_high=82°F running_max=28°C / spread=±4 |
| 9759 | KXHIGHTBOS-26MAR22-T49 | yes | expired | 0.87 | +0.00 | 2026-03-22 18:51 | v9=[p0:0.82,p1:0.09,p2+:0.09] hi_f=45 nws_high=45°F running_max=7°C / spread=±2. |
| 9838 | KXHIGHTLV-26MAR22-T91 | yes | expired | 0.05 | +0.00 | 2026-03-22 19:32 | v9=[p0:0.04,p1:0.05,p2+:0.91] hi_f=86 nws_high=86°F running_max=30°C / spread=±2 |