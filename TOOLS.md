# TOOLS.md - Environment & Setup Notes

## agent-browser — Browser Automation CLI
- **Binary**: `/opt/homebrew/bin/agent-browser` (in PATH)
- **Use this instead of the `browser` tool** for any web task — no Chrome extension relay needed, call directly via `exec`
- Browser daemon persists across chained calls (use `&&` to chain)
- **Key commands**:
  - `agent-browser open <url>` — navigate
  - `agent-browser snapshot` — accessibility tree with refs (for AI navigation)
  - `agent-browser snapshot -i` — interactive elements only
  - `agent-browser click @e2` — click by ref from snapshot
  - `agent-browser fill @e3 "text"` — fill input
  - `agent-browser get text @e1` — extract text
  - `agent-browser screenshot [path]` — screenshot
  - `agent-browser --auto-connect snapshot` — connect to existing Chrome tab
  - `--session-name <name>` — persist cookies/localStorage across runs
- **Chaining example**: `agent-browser open url && agent-browser wait --load networkidle && agent-browser snapshot`
- **For logged-in sites**: use `--session-name` to save/restore cookies (Kalshi, etc.)

## qmd — Semantic Search
- **Binary**: `/Users/ian/.bun/bin/qmd` (in PATH)
- **Collections**: `workspace` (`~/.openclaw/workspace/**/*.md`), `polymarket` (`polymarket/**/*.md`)
- **Use instead of grep** for conceptual/decision searches
- `qmd query "..."` — hybrid semantic + reranking (~8s, best results)
- `qmd search "..."` — BM25 keyword only (instant, good for exact strings)
- `qmd embed` — re-embed after adding new markdown files
- See AGENTS.md for full usage guide

## Machine
- Host: Ian's MacBook Pro (arm64, macOS 15.1)
- Shell: zsh
- Python: 3.12 (at `/Library/Frameworks/Python.framework/Versions/3.12/`)
- Node: v23.3.0

## Python: Always Use the venv
- **Venv**: `/Users/ian/.openclaw/workspace/polymarket/.venv` (Python 3.13.0)
- **Always run**: `.venv/bin/python script.py` or `.venv/bin/python -m pytest tests/`
- System `python3` is 3.12.8 — different version, different packages. Don't use it.
- Daemons (launchctl) already use `.venv/bin/python` ✅

## Python Packages (installed)
```
requests        2.32.3   # HTTP calls
pandas          2.2.3    # Data manipulation
numpy           2.0.2    # Numerics
youtube-transcript-api  1.2.4  # YouTube transcripts
```

### Packages we still need
```bash
pip install ta           # Technical analysis (ADX, Bollinger Bands for regime filter)
pip install scipy        # Statistical distributions (Poisson for count models)
pip install py-clob-client  # Polymarket CLOB SDK (when ready to trade live)
```

## Paper Trading DB — Field Conventions (READ BEFORE DIAGNOSING BUGS)

The `trades` table uses **different conventions** for live trades vs paper simulator trades:

| Field | Live trades (`twc_morning`, etc.) | Paper simulators (`twc_m_*`) |
|---|---|---|
| `market_price` | YES ask at entry time | **limit price posted** (fill_monitor reads this) |
| `dollar_size` | Kelly-sized ($3–25) | Fixed $50/trade for testing (TWAP: 4×$12.50 slices) |
| `fill_status` | `assumed` / `deferred` / `immediate` | `limit_pending` → `deferred` on fill |
| `fill_price` | Price actually filled at | Set by fill_monitor when Kalshi trade ≤ limit |

**Why `market_price` stores limit price for paper traders**: `paper_trading/fill_monitor.py` reads `market_price` as the limit to check — this is intentional and documented in `paper_trader.py`.

**`twc_m_s15`** is the most patient strategy (bids at `ask - 5¢`). Low fill rate is expected by design — it only fills when the market comes down.

**Legacy records** (pre-paper_trader module): some old trades have `fill_status='filled'` instead of `'deferred'`, and odd dollar_sizes. These are harmless artifacts from before the paper_trader module existed.

---

## Kalshi API — Key Facts (v3.8)

**Base URLs:**
- Live: `https://api.elections.kalshi.com/trade-api/v2`
- Demo: `https://demo.kalshi.co/trade-api/v2` (Cloudflare-protected, blocks scripts without proper User-Agent)

**Auth:** RSA-PSS signed headers — `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, `KALSHI-ACCESS-SIGNATURE`

**Create Order** `POST /portfolio/orders`:
- `side`: `"yes"` or `"no"`
- `action`: `"buy"` or `"sell"`
- `yes_price`: int cents (1–99) — use for YES orders
- `no_price`: int cents (1–99) — use for NO orders (do NOT invert; LEARNINGS burned us here)
- `time_in_force`: `"fill_or_kill"` | `"good_till_canceled"` | `"immediate_or_cancel"` (NOT "gtd")
- `expiration_ts`: Unix timestamp — use with `good_till_canceled` for GTD behavior
- Returns `{"order": {...}}` with `order_id`

**Order Status** (GET /portfolio/orders/{order_id}):
- `status` values: `"resting"` (on book) | `"executed"` (filled) | `"canceled"` (canceled or GTD expired)
- NOT "filled", NOT "cancelled" (two L's), NOT "expired"
- `fill_count`: int, contracts filled (NOT "filled_count")
- `yes_price` / `no_price`: both always present, int cents — use the one matching your direction
- `remaining_count`: contracts still resting
- No `avg_yes_price` field (that doesn't exist)

**Candlesticks** `GET /series/{series}/events/{event_ticker}/candlesticks`:
- Params: `period_interval` (int minutes: 1 or 60), `start_ts`, `end_ts` (Unix timestamps)
- Returns: `{"market_tickers": [...], "market_candlesticks": [[candle, ...], ...]}`
- Each candle: `{"end_period_ts": int, "yes_ask": {...}, "yes_bid": {...}, "volume_fp": "0.00", "open_interest_fp": "..."}`
- **Price fields use `close_dollars` NOT `close`**: `yes_ask["close_dollars"]`, `yes_bid["close_dollars"]`
- Also: `open_dollars`, `high_dollars`, `low_dollars` in each yes_ask/yes_bid sub-object
- Candles with no activity still appear but price fields will be absent (KeyError if not guarded)
- Use `period_interval=1` for minute-level; hourly (60) returns fewer but price fields can be None if no trades that hour
- **Always use minute-level (1) for order book price history** — hourly only shows trade prices, not resting order prices

**Cancel Order** `DELETE /portfolio/orders/{order_id}`:
- Returns zeroed order (remaining_count=0) not 204
- Check `r.ok` for success

**Order Book** (`GET /markets/{ticker}/orderbook`):
- Returns `{"orderbook": {"yes": [[price_cents, qty], ...], "no": [[price_cents, qty], ...]}}`
- `yes` side = YES bids; `no` side = NO bids
- For NO buys: convert YES bids to implied NO asks via `(100 - yes_bid_cents) / 100.0`

---

## Accounts / Auth Needed
| Service | Status | Notes |
|---------|--------|-------|
| Polymarket | ❌ No account | Need Polygon wallet + USDC.e for live trading |
| Kalshi | ✅ Active ($50) | RSA key at `polymarket/keys/kalshi_private.pem` |
| Polygon wallet | ❌ Not set up | Need private key + USDC.e + POL for gas |
| Simmer | ✅ Registered (unclaimed) | Agent "trady" — API key at `~/.config/simmer/credentials.json`. Claim URL: https://simmer.markets/claim/reef-DZVP |
| Flick Patrol | ❌ No account | ~few $/month, needed for Netflix market model |
| X/Twitter API | ❌ No key | Needed for Elon tweet count tracking ($100/month basic tier) |

## Wethr.net API — ✅ ACTIVE (Developer tier)
- **Key**: `b71980b06c822887095390a536227eebab21f8c2fc6bf0fd23451ffa3224a29a` (also in `polymarket/obs_poller.py` line 39)
- **REST base**: `https://wethr.net/api/v2/observations.php`
- **Push (SSE)**: `https://wethr.net:3443/api/v2/stream?stations=...&api_key=KEY`
- **Auth**: `Authorization: Bearer KEY` (REST) or `api_key=KEY` query param (push)
- **Rate limit**: 300 req/min, 50k/day, unlimited stations on push, 1 connection
- **Docs**: https://wethr.net/edu/api-docs

## Synoptic Data API — ✅ ACTIVE
- **API Key**: `KuTPwfvP4wItgzgMnWRStGQdrsT3oRqLWFpSlDLX3z` (in `polymarket/keys/synoptic_api_key.txt`)
- **Token** (generated from key): `e9971929005e4d0f833d92b4603ea87c` (in `polymarket/keys/synoptic_token.txt`)
- Token generation: `GET https://api.synopticdata.com/v2/auth?apikey=KEY`
- Latest obs: `GET https://api.synopticdata.com/v2/stations/latest?stid=KMIA&vars=air_temp&token=TOKEN`
- Timeseries: `GET https://api.synopticdata.com/v2/stations/timeseries?stid=KMIA&vars=air_temp&start=YYYYMMDDHHMM&end=YYYYMMDDHHMM&token=TOKEN`
- Has 5-min HF-METAR AND hourly METAR (0.1°C precision at :53)
- **Speed vs wethr**: TBD — freshest obs ~12 min old in initial test (need head-to-head vs wethr when it resets)

## Open-Meteo Paid API — ✅ ACTIVE
- **Plan**: Commercial (1M calls/month)
- **Key**: `gj0wtTIZSyVbtQyP` (also in `polymarket/keys/open_meteo_api_key.txt`)

### Which tier to use:
| API | URL | Auth | Use for |
|-----|-----|------|---------|
| Forecast (predictions) | `customer-api.open-meteo.com` | `&apikey=KEY` | Live trading — what OM predicts RIGHT NOW |
| **Historical Forecast** | `historical-forecast-api.open-meteo.com` | **none — free** | **ML training — what OM predicted on a PAST date** |
| Ensemble | `ensemble-api.open-meteo.com` | **none — free tier** | Ensemble spread |
| Archive (actuals) | `archive-api.open-meteo.com` | **none — free** | Ground truth actuals ONLY — NOT for training features |

**Rule: use paid (`customer-*`) for live forecast predictions only. Use free endpoints for ensembles and historical data.**
The `customer-historical-forecast-api.open-meteo.com` endpoint requires Professional plan (we don't have it). Always use the free `historical-forecast-api.open-meteo.com` instead.

### 🔴 CRITICAL: Historical Forecast API ≠ Archive API — DO NOT CONFUSE THESE

**Archive API** (`archive-api.open-meteo.com`): Returns what the weather **actually did** (grid-interpolated observations). Use ONLY for ground truth validation.

**Historical Forecast API** (`historical-forecast-api.open-meteo.com`): Returns what OM's forecast model **predicted** on a past date — exactly what live trading uses. Available from 2022 onward.

**For ML training features that use OM forecast data (e.g. `om_remaining_upside_f`): ALWAYS use Historical Forecast API, NEVER Archive API.** Using Archive creates a train/serve skew: the model learns from actual temperature outcomes but in live trading receives forecast predictions. When OM underestimates the actual high, the model fires on a false "no more upside" signal.

Example — get what OM predicted for Atlanta on March 14, 2026 at hourly resolution:
```python
import requests
r = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", params={
    "latitude": 33.6367, "longitude": -84.4281,
    "start_date": "2026-03-14", "end_date": "2026-03-14",
    "hourly": "temperature_2m",
    "temperature_unit": "fahrenheit",
    "timezone": "America/New_York",
    "models": "best_match",
})
```
This returns what OM's model said would happen on March 14 — matching exactly what `_fetch_om_hourly()` fetches in live trading.

## Tomorrow.io Weather API — ⚠️ UNUSED (key saved from weather_complex.py)
- **Key**: `wmnV7bvl2sPInPcIpRkd9gAG34osPiFd`
- **Endpoint**: `GET https://api.tomorrow.io/v4/weather/forecast`
- **Params**: `location=lat,lon` | `apikey=KEY` | `units=imperial`
- **Hourly**: add `timesteps=1h` — returns `timelines.hourly[].values.temperature`
- **Daily**: default returns `timelines.daily[].values.{temperatureMax,temperatureMin}`
- **Specialty**: proprietary AI model, good for hourly remaining-hours forecasts
- **Status**: ❌ Not integrated — key saved in case we want hourly intraday forecasts

## Foreca Weather API (RapidAPI — upgraded plan, ~10k req/day)
- **What**: Foreca commercial forecast — Finnish company, 200+ employees, well-regarded accuracy
- **API key**: `7f597948dbmsh68be647670eed41p161ed9jsn36087b19f9f9`
- **Host**: `foreca-weather.p.rapidapi.com`
- **Endpoint**: `GET https://foreca-weather.p.rapidapi.com/forecast/daily/{foreca_id}`
  - Params: `periods=7&tempunit=F&lang=en`
  - Returns: `{date, maxTemp, minTemp, ...}` — date is local calendar day ✅
  - Timezone: hourly timestamps include local UTC offset (e.g. `2026-02-23T14:00-05:00`) — safe
- **Foreca city IDs** (verified 2026-02-23):
  - nyc=105128581, chicago=104887398, miami=104164138, austin=104671654, dc=104140963
  - okc=104544349, boston=104930956, denver=105419384, lasvegas=105506956, sfo=105391959
  - seattle=105809844, houston=104699066, philly=104560349, phoenix=105308655, lax=105368361
  - minneapolis=105037649, nola=104335045, sanantonio=104726206, dallas=104684888
- **Status**: ✅ Live in forecast_logger.py as of 2026-02-23

## Visual Crossing Weather API — ✅ LIVE
- **Key**: `6S3FUZ7XZRW2BGWNJQQCT8SRQ`
- **Endpoint**: `GET https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat,lon}/next7days`
- **Params**: `key=KEY&unitGroup=us&elements=datetime,tempmax,tempmin&include=days&contentType=json`
- **Fields**: `days[].datetime` (local YYYY-MM-DD), `days[].tempmax`, `days[].tempmin` (°F)
- **Status**: ✅ Added to forecast_logger.py 2026-02-25 as `vc_high`/`vc_low`
- **Docs**: https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/

## TWC (The Weather Channel) Direct API — ✅ LIVE
- **Key**: `adb6c94f2ec944c4b6c94f2ec9d4c47b` (trial key, full access)
- **Required header**: `Accept-Encoding: gzip`
- **Common params**: `geocode=lat,lon` | `units=e` (Fahrenheit) | `language=en-US` | `format=json` | `apiKey=KEY`
- **Status**: ✅ Live as of 2026-02-23

### Authorized Endpoints (trial key)
| Endpoint | URL | Notes |
|----------|-----|-------|
| Daily 5-day | `GET https://api.weather.com/v3/wx/forecast/daily/5day` | Use `calendarDayTemperatureMax/Min` (midnight-to-midnight). NOT `temperatureMax` (daytime only). |
| Hourly 2-day | `GET https://api.weather.com/v3/wx/forecast/hourly/2day` | Returns 48 hourly slots. `validTimeLocal` for time, `temperature` for °F. |
| 15-minute | `GET https://api.weather.com/v3/wx/forecast/fifteenminute` | Param: `icaoCode=KXXX` (NOT geocode). Returns ~7h of 15-min slots. |
| Intraday 3-day | `GET https://api.weather.com/v1/geocode/{lat}/{lon}/forecast/intraday/3day.json` | Different base URL pattern. |

⚠️ `/v3/wx/forecast/hourly/48hour` does NOT exist on this key — returns 401. Use `/hourly/2day` (same 48 slots).

### Key field notes
- **Date field**: `validTimeLocal[:10]` — includes timezone offset, safe to parse
- **Daily high**: use `calendarDayTemperatureMax` NOT `temperatureMax` — "calendar day" = local midnight-to-midnight ✅
- **15-min endpoint**: requires `icaoCode` (e.g. `KNYC`), not `geocode`

## Weather.com RapidAPI (sangatpuria01) — ❌ DEAD
- Akamai revoked provider credentials — all forecast endpoints return 401. Do not use.

## Open-Meteo APIs (no auth, no account needed)

| API | Base URL | Purpose |
|-----|----------|---------|
| **Forecast** | `https://api.open-meteo.com/v1/forecast` | Current/future hourly forecast |
| **Archive** | `https://archive-api.open-meteo.com/v1/archive` | Actual observed historical data |
| **Historical Forecast** | `https://historical-forecast-api.open-meteo.com/v1/forecast` | What the model *predicted* on a past date |

### Common params (all three endpoints)
```
latitude, longitude, start_date, end_date (YYYY-MM-DD)
hourly=temperature_2m
temperature_unit=fahrenheit
timezone=America/New_York  (use city's IANA tz — avoids UTC offset bugs)
models=best_match|gfs_seamless|ecmwf_ifs025|icon_seamless|gem_seamless
```

### When to use which
- **Forecast**: What OM predicts right now for today/tomorrow → used by `fetch_om_peak_hour()` for OM gate
- **Archive**: Actual observed temperatures (ground truth for backtesting) → used in `backtest_peak_timing_v4.py`
- **Historical Forecast**: What OM *predicted* on a past date (for backtest realism, post-mortems) → use this to see what the model said at 4pm about tonight's temps, not what actually happened

### Example — historical forecast for Atlanta as it looked Feb 27:
```python
requests.get('https://historical-forecast-api.open-meteo.com/v1/forecast', params={
    'latitude': 33.6367, 'longitude': -84.4281,
    'start_date': '2026-02-27', 'end_date': '2026-02-27',
    'hourly': 'temperature_2m',
    'temperature_unit': 'fahrenheit',
    'timezone': 'America/New_York',
    'models': 'best_match',
})
```

---

## IEM ASOS API — ✅ Free, no auth

Two endpoints — **different station ID formats, not interchangeable:**

| Endpoint | URL | Station format | report_type |
|----------|-----|----------------|-------------|
| Hourly ASOS | `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py` | 4-letter ICAO (KLAX) | `3` |
| 1-minute ASOS | `https://mesonet.agron.iastate.edu/cgi-bin/request/asos1min.py` | 3-letter (LAX, MDW, NYC) | n/a |

⚠️ Using KLAX with `asos1min.py` returns HTTP 422 immediately. No error message, just fails.

Common params (hourly): `station=KMIA&data=tmpf&year1=...&month1=...&day1=1&year2=...&month2=...&day2=...&tz=UTC&format=onlycomma&latlon=no&missing=M&trace=T&direct=no&report_type=3`

- `M` = missing — skip those rows
- `tmpf` = °F (integer for hourly, may be float for 1-min)
- Minneapolis (KMSP) has no 1-min archive — hourly only
- Fetch already implemented: `intraday/build_trajectory_model.py` (1-min, LAX) and `intraday/build_low_offset_model_v2.py` (1-min, all cities)
- Cache to `intraday/iem_cache/{STATION}_1min.json` or `{STATION}.json`

## Polymarket API — ✅ ACTIVE
- **API Key**: `019ce842-bcaa-767b-9ff9-b30faa66eb9f`
- **Wallet address**: `0x81e62484b4073c294add56a4529d68da36a33d1a`
- **Auth header**: `Authorization: Bearer <api_key>`
- **Gamma API** (markets/profiles): `https://gamma-api.polymarket.com`
- **CLOB API** (trading/prices): `https://clob.polymarket.com`
- **Data API** (activity/positions): `https://data-api.polymarket.com`
- **Docs**: https://docs.polymarket.com

## Free APIs (no auth, no account needed)
| API | Base URL | What we use it for |
|-----|----------|-------------------|
| Polymarket Gamma | `https://gamma-api.polymarket.com` | Market discovery, metadata |
| Polymarket CLOB | `https://clob.polymarket.com` | Price history, order book |
| Polymarket Data | `https://data-api.polymarket.com` | Trades, leaderboard |
| Kalshi | `https://api.elections.kalshi.com/trade-api/v2` | All Kalshi market data + history |
| Open-Meteo Forecast | `https://api.open-meteo.com/v1/forecast` | Weather forecasts |
| Open-Meteo Archive | `https://archive-api.open-meteo.com/v1/archive` | Historical weather |
| Binance US | `https://api.binance.us/api/v3` | Crypto spot prices (geo-unblocked for US) |
| YouTube Transcript | (python library) | Video transcripts |

## Workspace
- Project root: `/Users/ian/.openclaw/workspace/`
- Polymarket project: `/Users/ian/.openclaw/workspace/polymarket/`
- Paper trade data: `/Users/ian/.openclaw/workspace/polymarket/paper_trades/`
- Memory: `/Users/ian/.openclaw/workspace/memory/`

## Running Processes
Check PIDs in `polymarket/paper_trades/pid.txt` for paper_trader.py.
Other processes (systematic_no.py, weather_oracle.py) — check with `ps aux | grep python`.

## Polymarket Log Map — Where Orders Are Actually Logged

**CLI push trigger** dispatches subprocesses. The trigger's own log (`cli_push_trigger.stdout.log`)
only shows "Firing..." and "done (exit=N)". Actual order output is in per-city files:
- Live orders: `forecast_logs/cli_push_{city}_live.log`
- Paper orders: `forecast_logs/cli_push_{city}_paper.log`

**Standard command to find all live orders placed today:**
```bash
grep "🟢 LIVE ORDER" polymarket/forecast_logs/cli_push_*_live.log
```

**Other trader logs** (output goes directly to their own stdout log):
- TWC morning trader: `forecast_logs/twc_morning_trader.stdout.log`
- Ensemble trader: `forecast_logs/ensemble_trader.stdout.log`
- NWS obs trader: runs in-process inside wethr push client — `forecast_logs/wethr_push_client.stdout.log`

**⚠️ Rule:** Never state "no orders were placed today" without running the standard command above.
Log location must be verified before making any claim about system state.

## Temperature Data Sources Reference
Full details in `polymarket/DATA_SOURCES.md`. Quick summary:
- **Live (real-time):** wethr push (5-min whole-°C, bucket ambiguity), NWS hourly METAR T-group (0.1°C exact), 6-hr METAR max (exact), CLI/DSM (exact settlement values)
- **Training/backtest:** IEM hourly (T-group origin, any °F reachable), IEM 1-min (NCEI original °F, closest to CLI settlement)
- **Key rule:** IEM has finer resolution than live system. To mock live data, map IEM °F → `f_to_c_bucket()` → `asos_display_c_to_f()` interval. Only changes that cross a °C bucket boundary are observable in production.
- **CLI settlement:** 1-minute averages in whole °F, no C→F conversion. IEM 1-min running max ≈ CLI settlement value.
