"""
btc15m_sampler.py — Live sampler for Kalshi BTC 15-min markets.

Runs continuously, logging every 3 seconds per window:
  - BTC spot price (Binance US)
  - yes_ask, yes_bid, spread, last_price
  - Orderbook depth (top 5 levels each side)
  - Time elapsed / remaining
  - btc vs reference price

Captures N_WINDOWS complete windows then exits.
Output: notes/btc15m_samples.jsonl
"""
import sys, time, json, datetime, requests
sys.path.insert(0, '/data/workspace/trading')
from kalshi_client import kalshi_auth_headers, BASE

SAMPLE_INTERVAL_S = 3
N_WINDOWS = 8
OUT_FILE = "/data/workspace/notes/btc15m_samples.jsonl"

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def next_window_start(dt):
    q = (dt.minute // 15) * 15
    ws = dt.replace(minute=q, second=0, microsecond=0)
    return ws + datetime.timedelta(minutes=15)

def get_btc():
    try:
        r = requests.get("https://api.binance.us/api/v3/ticker/price",
                         params={"symbol": "BTCUSD"}, timeout=3)
        return float(r.json()["price"])
    except:
        return None

def get_active_market(opened_after: datetime.datetime = None):
    """Find current open 15-min market.
    If opened_after is set, only return a market whose open_time >= that timestamp
    (prevents accidentally grabbing the just-closed window at a boundary).
    """
    try:
        r = requests.get(f"{BASE}/events",
                         headers=kalshi_auth_headers("GET", "/events"),
                         params={"series_ticker": "KXBTC15M", "limit": 5, "status": "open"},
                         timeout=5)
        events = r.json().get("events", [])
        for ev in events:
            # Check open_time if we need a fresh window
            if opened_after:
                open_time_str = ev.get("last_updated_ts", "")
                # Use strike_date (close time) to infer open time: close - 15min
                close_str = ev.get("strike_date", "")
                if close_str:
                    close_dt = datetime.datetime.fromisoformat(close_str.replace("Z", "+00:00"))
                    open_dt = close_dt - datetime.timedelta(minutes=15)
                    if open_dt < opened_after - datetime.timedelta(seconds=5):
                        continue  # this market opened before our target boundary, skip it
            mr = requests.get(f"{BASE}/markets",
                              headers=kalshi_auth_headers("GET", "/markets"),
                              params={"event_ticker": ev["event_ticker"], "limit": 5},
                              timeout=5)
            mkts = mr.json().get("markets", [])
            if not mkts: continue
            m = mkts[0]
            return {
                "event_ticker": ev["event_ticker"],
                "ticker": m["ticker"],
                "floor_strike": m.get("floor_strike"),
                "close_time": ev.get("strike_date"),
            }
        return None
    except Exception as e:
        print(f"  [market lookup error] {e}")
        return None

def get_snapshot(ticker):
    """Returns full market snapshot + orderbook."""
    snap = {}
    try:
        path = f"/markets/{ticker}"
        r = requests.get(f"{BASE}/markets/{ticker}",
                         headers=kalshi_auth_headers("GET", path), timeout=5)
        m = r.json().get("market", r.json())
        snap["yes_ask"]   = float(m["yes_ask_dollars"]) if m.get("yes_ask_dollars") else None
        snap["yes_bid"]   = float(m["yes_bid_dollars"]) if m.get("yes_bid_dollars") else None
        snap["no_ask"]    = float(m["no_ask_dollars"])  if m.get("no_ask_dollars")  else None
        snap["no_bid"]    = float(m["no_bid_dollars"])  if m.get("no_bid_dollars")  else None
        snap["last_price"]= float(m["last_price_dollars"]) if m.get("last_price_dollars") else None
        snap["volume"]    = float(m.get("volume_fp", 0) or 0)
        snap["open_int"]  = float(m.get("open_interest_fp", 0) or 0)
    except Exception as e:
        print(f"  [snapshot error] {e}")

    try:
        ob_path = f"/markets/{ticker}/orderbook"
        ob = requests.get(f"{BASE}/markets/{ticker}/orderbook",
                          headers=kalshi_auth_headers("GET", ob_path), timeout=5)
        book = ob.json().get("orderbook_fp", {})
        snap["ob_yes"] = book.get("yes_dollars", [])[:5]   # top 5 YES bids
        snap["ob_no"]  = book.get("no_dollars", [])[:5]    # top 5 NO bids
    except Exception as e:
        snap["ob_yes"] = []
        snap["ob_no"]  = []

    return snap

def get_result(ticker, timeout_s=120):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            path = f"/markets/{ticker}"
            r = requests.get(f"{BASE}/markets/{ticker}",
                             headers=kalshi_auth_headers("GET", path), timeout=5)
            m = r.json().get("market", r.json())
            result = m.get("result")
            if result in ("yes", "no"):
                return result
        except:
            pass
        time.sleep(5)
    return "unknown"

def log(record, fh):
    fh.write(json.dumps(record) + "\n")
    fh.flush()

def main():
    windows_done = 0
    print(f"BTC 15-min sampler — capturing {N_WINDOWS} windows")
    print(f"Output: {OUT_FILE}\n")

    with open(OUT_FILE, "a") as fh:
        while windows_done < N_WINDOWS:
            now = utc_now()
            nws = next_window_start(now)
            wait_s = (nws - now).total_seconds() + 1.5
            print(f"[{now.strftime('%H:%M:%S')}] Next window at {nws.strftime('%H:%M:%S')} UTC — waiting {wait_s:.0f}s")
            if wait_s > 0:
                time.sleep(wait_s)

            window_start = utc_now()
            mkt = None
            for attempt in range(15):
                mkt = get_active_market(opened_after=nws)
                if mkt: break
                print(f"  [t+{attempt*2}s] waiting for fresh market...")
                time.sleep(2)

            if not mkt:
                print("  [WARN] No market found, skipping")
                time.sleep(60)
                windows_done += 1
                continue

            ticker = mkt["ticker"]
            floor  = mkt["floor_strike"]
            btc_at_open = get_btc()
            dist_open = (btc_at_open - floor) if (btc_at_open and floor) else None

            print(f"\n{'='*65}")
            print(f"Window {windows_done+1}/{N_WINDOWS} | {ticker}")
            print(f"  Reference: ${floor or 0:,.2f} | BTC at open: ${btc_at_open or 0:,.2f} ({dist_open or 0:+.2f})")
            log({"_type":"window_open","window":windows_done+1,"ticker":ticker,
                 "floor_strike":floor,"btc_at_open":btc_at_open,"ts":window_start.isoformat()}, fh)

            # Sample until ~30s before close
            window_end = window_start + datetime.timedelta(minutes=14, seconds=30)
            n = 0
            while utc_now() < window_end:
                t = utc_now()
                elapsed = (t - window_start).total_seconds()
                remaining = (window_start + datetime.timedelta(minutes=15) - t).total_seconds()

                btc = get_btc()
                snap = get_snapshot(ticker)

                rec = {
                    "_type": "sample", "window": windows_done+1,
                    "ticker": ticker, "floor_strike": floor,
                    "elapsed_s": round(elapsed, 1),
                    "remaining_s": round(remaining, 1),
                    "btc_spot": btc,
                    "btc_vs_ref": round(btc - floor, 2) if btc else None,
                    "btc_vs_ref_pct": round((btc - floor)/floor*100, 4) if btc else None,
                    **snap, "ts": t.isoformat()
                }
                log(rec, fh)
                n += 1

                # Console: every 10 samples (~30s)
                if n % 10 == 1:
                    ya = snap.get("yes_ask"); yb = snap.get("yes_bid")
                    mid = (ya+yb)/2 if (ya and yb) else None
                    btc_str = f"${btc:,.2f}" if btc else "?"
                    diff_str = f"({btc-floor:+.2f})" if btc else ""
                    mid_str = f"mid={mid:.3f}" if mid else "no price"
                    print(f"  t+{elapsed:>5.0f}s rem={remaining:>4.0f}s | {mid_str} | {btc_str} {diff_str} | vol={snap.get('volume',0):.0f}")

                time.sleep(SAMPLE_INTERVAL_S)

            print(f"  {n} samples captured. Waiting for result...")
            result = get_result(ticker)
            print(f"  Result: {result.upper()} | ref=${floor:,.2f} btc_open={btc_at_open:,.2f}" if btc_at_open else f"  Result: {result.upper()}")
            log({"_type":"window_close","window":windows_done+1,"ticker":ticker,
                 "floor_strike":floor,"result":result,"ts":utc_now().isoformat()}, fh)

            windows_done += 1

    print(f"\nDone. {N_WINDOWS} windows → {OUT_FILE}")

if __name__ == "__main__":
    main()
