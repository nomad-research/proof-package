"""v19 paper fills (decision 17, gate 2): watch the order books of the paper book's own markets, then price every paper fill against them.
Standalone, Python 3.9 or newer, no packages, public read endpoints only (no keys, no wallet, no orders). Run it beside the recorder.

    python3 v19_watch_books.py watch --repo . --record-dir ~/polymarket_record            # every 15 minutes, until stopped
    python3 v19_watch_books.py watch --repo . --record-dir ~/polymarket_record --once     # one pass
    python3 v19_watch_books.py fills --repo . --record-dir ~/polymarket_record            # writes lookbacks/polymarket/v19/fills.json (small; commit it)

Which markets: every open position in lookbacks/polymarket/v19/book.json that is armed, or a shadow NO costing 50c or more (the ones near the
arming line). The recorder keeps books only for its 300 busiest tokens, which the paper book's markets mostly are not.
Books go to <record-dir>/v19_books/<token>/<YYYYMMDD>/<HHMMSS>.json.gz, raw. The recorder's own clob/book/<token>/ snapshots are read too.
Refresh book.json (git pull, or `python lookbacks/polymarket/v19_book.py run`) after each new sweep batch so new positions are watched.
"""
import argparse, datetime as dt, glob, gzip, json, os, signal, time, urllib.request

CLOB = "https://clob.polymarket.com"
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def load_book(repo):
    return json.load(open(os.path.join(repo, "lookbacks", "polymarket", "v19", "book.json"), encoding="utf-8"))["positions"]


def watched(ps):
    return sorted({p["token"] for p in ps if p.get("token") and p.get("status") == "open" and (p["armed"] or (p["side"] == "NO" and p["cost"] >= 0.5))})


def fetch(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nomad-v19-fills"}), timeout=30) as r:
                return r.read()
        except Exception:
            time.sleep(2 ** i)
    return None


def cmd_watch(a):
    signal.signal(signal.SIGINT, _stop); signal.signal(signal.SIGTERM, _stop)
    while not STOP:
        toks = watched(load_book(a.repo)); t = dt.datetime.now(dt.timezone.utc); n = 0
        for tk in toks:
            if STOP:
                break
            body = fetch(f"{CLOB}/book?token_id={tk}")
            if body:
                path = os.path.join(a.record_dir, "v19_books", tk, t.strftime("%Y%m%d"), t.strftime("%H%M%S") + ".json.gz")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with gzip.open(path, "wb") as f:
                    f.write(body)
                n += 1
            time.sleep(0.25)
        print(f"{t:%Y-%m-%d %H:%M:%S} UTC  {n} of {len(toks)} books", flush=True)
        if a.once:
            break
        for _ in range(a.every):
            if STOP:
                break
            time.sleep(1)


def snapshots(record_dir, tk):
    out = []
    for pat in (os.path.join(record_dir, "v19_books", tk, "*", "*.json.gz"), os.path.join(record_dir, "clob", "book", tk, "*", "*.json.gz")):
        for f in glob.glob(pat):
            day, hms = f.split(os.sep)[-2], os.path.basename(f)[:6]
            try:
                ts = dt.datetime.strptime(day + hms, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc).timestamp()
                out.append((ts, json.loads(gzip.open(f).read())))
            except Exception:
                continue
    return sorted(out, key=lambda x: x[0])


def levels(side):
    return [(float(x["price"]), float(x["size"])) for x in (side or [])]


def walk(asks, dollars):
    """Buy `dollars` of shares up the ask side. Returns (average price, dollars filled)."""
    spent = shares = 0.0
    for price, size in sorted(asks):
        take = min(size, (dollars - spent) / price) if price > 0 else size
        spent += take * price; shares += take
        if spent >= dollars - 1e-9:
            break
    return (spent / shares if shares else None), spent


def cmd_fills(a):
    ps = [p for p in load_book(a.repo) if p["armed"] or (p["side"] == "NO" and p["cost"] >= 0.5)]
    rows = []
    for p in ps:
        snaps = snapshots(a.record_dir, p.get("token") or "")
        after = [(ts, b) for ts, b in snaps if ts >= p["lock"]]
        r = {"event": p["event"], "cid": p["cid"], "side": p["side"], "armed": p["armed"], "kind": p["kind"], "occ": p["occ"], "stake": p["stake"],
             "lock_ask": p["ask"], "snapshots": len(snaps), "snapshots_after_lock": len(after)}
        if after:
            ts, b = after[0]; asks, bids = levels(b.get("asks")), levels(b.get("bids"))
            avg, filled = walk(asks, p["stake"]) if p["stake"] else (None, 0.0)
            r.update({"first_after_lock_min": round((ts - p["lock"]) / 60, 1), "best_ask": min(asks)[0] if asks else None, "best_bid": max(bids)[0] if bids else None,
                      "avg_fill": avg, "filled_usd": round(filled, 2), "slippage_vs_lock_ask": (avg - p["ask"]) if avg is not None else None})
            spreads = [min(levels(b2.get("asks")))[0] - max(levels(b2.get("bids")))[0] for _, b2 in after if b2.get("asks") and b2.get("bids")]
            r["spread_median"] = sorted(spreads)[len(spreads) // 2] if spreads else None
            exit_bids = [(t2, max(levels(b2.get("bids")))[0]) for t2, b2 in after if b2.get("bids")]
            r["exit_bid_last"] = exit_bids[-1][1] if exit_bids else None
        rows.append(r)
    out = {"made_at": dt.datetime.now(dt.timezone.utc).isoformat(), "positions": len(rows), "with_books_after_lock": sum(1 for r in rows if r["snapshots_after_lock"]), "rows": rows}
    path = os.path.join(a.repo, "lookbacks", "polymarket", "v19", "fills.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}), "->", path)


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    w = sp.add_parser("watch"); w.add_argument("--repo", default="."); w.add_argument("--record-dir", required=True)
    w.add_argument("--every", type=int, default=900); w.add_argument("--once", action="store_true")
    f = sp.add_parser("fills"); f.add_argument("--repo", default="."); f.add_argument("--record-dir", required=True)
    a = ap.parse_args(); a.record_dir = os.path.expanduser(a.record_dir)
    {"watch": cmd_watch, "fills": cmd_fills}[a.cmd](a)


if __name__ == "__main__":
    main()
