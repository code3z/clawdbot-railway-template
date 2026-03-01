# TOOLS.md - Environment & Setup Notes

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

## Accounts / Auth Needed
| Service | Status | Notes |
|---------|--------|-------|
| Polymarket | ❌ No account | Need Polygon wallet + USDC.e for live trading |
| Kalshi | ✅ Active ($50) | RSA key at `polymarket/keys/kalshi_private.pem` |
| Polygon wallet | ❌ Not set up | Need private key + USDC.e + POL for gas |
| Simmer | ✅ Registered (unclaimed) | Agent "trady" — API key at `~/.config/simmer/credentials.json`. Claim URL: https://simmer.markets/claim/reef-DZVP |
| Flick Patrol | ❌ No account | ~few $/month, needed for Netflix market model |
| X/Twitter API | ❌ No key | Needed for Elon tweet count tracking ($100/month basic tier) |

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
- **Endpoint**: `GET https://api.weather.com/v3/wx/forecast/daily/5day`
- **Required header**: `Accept-Encoding: gzip`
- **Params**: `geocode=lat,lon` | `units=e` (Fahrenheit) | `language=en-US` | `format=json` | `apiKey=KEY`
- **Use `calendarDayTemperatureMax`** NOT `temperatureMax` — "calendar day" = local midnight-to-midnight ✅
  - `temperatureMax` is daytime only (7am-7pm). Wrong for Kalshi settlement.
- **Date field**: `validTimeLocal[:10]` — includes timezone offset, safe to parse
- **Status**: ✅ Live in forecast_logger.py as of 2026-02-23

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
