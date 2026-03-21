"""
btc15m_backtest.py — Pull historical 15-min market data + BTC prices, build analysis dataset.

For each settled window:
  - 1-min candlesticks (yes_ask, yes_bid, volume)
  - BTC 1-min close prices from Binance
  - Result (YES/NO), floor_strike

Output: notes/btc15m_history.csv
"""
import sys, requests, time, json, csv, datetime
sys.path.insert(0, '/data/workspace/trading')
from kalshi_client import kalshi_auth_headers, BASE

OUT_CSV = "/data/workspace/notes/btc15m_history.csv"
N_EVENTS = 9100  # full history — ~9,041 total settled events since Dec 2025 launch

# ── Step 1: Fetch settled events ─────────────────────────────────
print(f"Fetching {N_EVENTS} settled KXBTC15M events...")
all_events = []
cursor = None
while len(all_events) < N_EVENTS:
    params = {"series_ticker": "KXBTC15M", "limit": 200, "status": "settled"}
    if cursor: params["cursor"] = cursor
    r = requests.get(f"{BASE}/events", headers=kalshi_auth_headers("GET", "/events"), params=params, timeout=10)
    d = r.json()
    batch = d.get("events", [])
    all_events.extend(batch)
    cursor = d.get("cursor")
    if not cursor or len(batch) == 0: break
    time.sleep(0.2)

events = all_events[:N_EVENTS]
print(f"Got {len(events)} events. Date range: {events[-1]['event_ticker']} → {events[0]['event_ticker']}")

# ── Step 2: Get floor_strike + result for each event ─────────────
print("Fetching market results...")
event_meta = {}  # event_ticker → {result, floor, close_ts}
for i, ev in enumerate(events):
    et = ev["event_ticker"]
    close_str = ev.get("strike_date", "")
    close_ts = int(datetime.datetime.fromisoformat(close_str.replace("Z", "+00:00")).timestamp()) if close_str else None
    for attempt in range(4):
        try:
            mr = requests.get(f"{BASE}/markets", headers=kalshi_auth_headers("GET", "/markets"),
                              params={"event_ticker": et}, timeout=8)
            mkts = mr.json().get("markets", [])
            break
        except Exception:
            time.sleep(2 ** attempt)
            mkts = []
    if mkts:
        m = mkts[0]
        event_meta[et] = {
            "result": m.get("result"),
            "floor": m.get("floor_strike"),
            "close_ts": close_ts,
            "open_ts": close_ts - 900 if close_ts else None,
        }
    if i % 50 == 0: print(f"  {i}/{len(events)}")
    time.sleep(0.07)

print(f"Got meta for {len(event_meta)} events")

# ── Step 3: Build BTC price cache from Binance ───────────────────
# Find time range needed
ts_list = [v["open_ts"] for v in event_meta.values() if v.get("open_ts")]
ts_min, ts_max = min(ts_list), max(ts_list) + 1800
print(f"\nFetching BTC 1-min prices ({datetime.datetime.utcfromtimestamp(ts_min).strftime('%Y-%m-%d')} → {datetime.datetime.utcfromtimestamp(ts_max).strftime('%Y-%m-%d')})...")

btc_prices = {}  # unix_minute → close_price
cur_ts = ts_min
while cur_ts < ts_max:
    r = requests.get("https://api.binance.us/api/v3/klines", params={
        "symbol": "BTCUSD", "interval": "1m",
        "startTime": cur_ts * 1000,
        "limit": 1000
    }, timeout=10)
    klines = r.json()
    if not klines: break
    for k in klines:
        minute_ts = k[0] // 1000  # open time in seconds
        btc_prices[minute_ts] = float(k[4])  # close price
    cur_ts = klines[-1][0] // 1000 + 60
    print(f"  Cached through {datetime.datetime.utcfromtimestamp(cur_ts).strftime('%Y-%m-%d %H:%M')}, {len(btc_prices)} minutes")
    time.sleep(0.15)

print(f"BTC cache: {len(btc_prices)} minutes")

# ── Step 4: Fetch candlesticks and build rows ─────────────────────
print(f"\nFetching candlesticks for {len(event_meta)} events...")
rows = []
for i, (et, meta) in enumerate(event_meta.items()):
    if not meta.get("close_ts"): continue
    close_ts = meta["close_ts"]
    start_ts = close_ts - 1000

    cs_path = f"/series/KXBTC15M/events/{et}/candlesticks"
    candles = []
    for attempt in range(4):
        try:
            cs = requests.get(f"{BASE}/series/KXBTC15M/events/{et}/candlesticks",
                              headers=kalshi_auth_headers("GET", cs_path),
                              params={"period_interval": 1, "start_ts": start_ts, "end_ts": close_ts + 60},
                              timeout=10)
            candles = cs.json().get("market_candlesticks", [[]])[0] if cs.ok else []
            break
        except Exception:
            time.sleep(2 ** attempt)

    floor = meta.get("floor")
    result = meta.get("result")
    outcome = 1 if result == "yes" else 0

    btc_miss = 0
    for c in candles:
        ts = c.get("end_period_ts")
        if not ts: continue
        ya_str = c.get("yes_ask", {}).get("close_dollars")
        yb_str = c.get("yes_bid", {}).get("close_dollars")
        vol = float(c.get("volume_fp") or 0)
        if not ya_str or not yb_str: continue
        ya = float(ya_str)
        yb = float(yb_str)
        if ya <= 0 or yb <= 0 or ya > 0.99: continue  # skip settled/dead candles

        mid = (ya + yb) / 2
        spread = ya - yb
        remaining_s = close_ts - ts
        remaining_min = remaining_s / 60.0

        # BTC price: kline that OPENED at ts-60 has CLOSE = BTC at ts (no look-ahead)
        # Fallback only to ts-120 (1 min stale) — never ts (that's 1 min ahead)
        btc_primary = btc_prices.get(ts - 60)
        btc = btc_primary or btc_prices.get(ts - 120)
        if not btc_primary and btc: btc_miss += 1
        btc_vs_ref = (btc - floor) if (btc and floor) else None
        btc_vs_ref_pct = (btc_vs_ref / floor * 100) if (btc_vs_ref is not None and floor) else None

        rows.append({
            "event": et,
            "ts": ts,
            "remaining_min": round(remaining_min, 2),
            "floor": floor,
            "btc": btc,
            "btc_vs_ref": round(btc_vs_ref, 2) if btc_vs_ref is not None else None,
            "btc_vs_ref_pct": round(btc_vs_ref_pct, 4) if btc_vs_ref_pct is not None else None,
            "yes_ask": ya,
            "yes_bid": yb,
            "mid": round(mid, 4),
            "spread": round(spread, 4),
            "volume": vol,
            "outcome": outcome,  # 1=YES won, 0=NO won
        })

    if i % 50 == 0: print(f"  {i}/{len(event_meta)} | rows so far: {len(rows)}")
    if btc_miss: print(f"    ^ {btc_miss} candles used stale BTC fallback (ts-120)")
    time.sleep(0.12)

# ── Step 5: Write CSV ─────────────────────────────────────────────
if rows:
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nDone. {len(rows)} rows → {OUT_CSV}")
else:
    print("No rows collected!")
