#!/usr/bin/env python3
"""Polymarket forward recorder. Standard library only (Python 3.9+). Records the public market data whole and never reduces it.

    python3 polymarket_recorder.py --out ./polymarket_record               # run until stopped (Ctrl-C)
    python3 polymarket_recorder.py --out ./polymarket_record --once --top 5   # one pass, for a smoke test

What it writes under --out (all raw response bytes, gzip is lossless and applied on write; nothing is filtered or summarised):
  gamma/events/<YYYY>/<MM>/<DD>/<HHMMSS>_<offset>.json.gz    market metadata pages, every sweep
  gamma/event_snapshots/<event_id>/<sha256>.json.gz           one file per distinct version of an event (resolution rules and prices change; an edit is a new version)
  clob/book/<token_id>/<YYYYMMDD>/<HHMMSS>.json.gz            order book snapshots for the top markets by volume
  clob/history/<token_id>/<YYYYMMDD>.json.gz                  the price-history endpoint, once a day per watched token
  data/trades/<condition_id>.jsonl                            trades, appended, de-duplicated on transactionHash
  manifest.jsonl                                              one line per request: url, retrieved_at (UTC), status, bytes, sha256 of the raw body, path
  state.json                                                  what is being watched and when each thing was last fetched
Public read endpoints only; no keys, no wallet, no orders. Requests are spaced (default 0.25 s) and back off on 429 and 5xx.
Storage: a single pass over 100 events measured about 12 MB raw; expect a few hundred MB a day at the defaults (hourly sweeps, whole pages every 6 hours, a new file only when an event changes, 15-minute books for 300 tokens); lower it with --top, --max-events and --book-every.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA = "https://data-api.polymarket.com"
UA = {"User-Agent": "nomad-research-recorder/0.1 (public data, read only)"}
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Recorder:
    def __init__(self, out: str, spacing: float, raw_pages_every: int = 21600):
        self.out, self.spacing, self.raw_pages_every = out, spacing, raw_pages_every
        os.makedirs(out, exist_ok=True)
        self.manifest = open(os.path.join(out, "manifest.jsonl"), "a", buffering=1)
        self.state_path = os.path.join(out, "state.json")
        self.state = json.load(open(self.state_path)) if os.path.exists(self.state_path) else {"watched": {}, "last": {}, "seen_versions": {}}

    def save_state(self):
        tmp = self.state_path + ".tmp"
        json.dump(self.state, open(tmp, "w"))
        os.replace(tmp, self.state_path)

    def fetch(self, url: str, rel_path: str | None = None) -> bytes | None:
        """One request, with backoff. Returns the raw body; writes it gzipped when rel_path is given; always logs to the manifest."""
        body, status = None, None
        for attempt in range(5):
            time.sleep(self.spacing)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                    body, status = r.read(), r.status
                break
            except urllib.error.HTTPError as e:
                status = e.code
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt * 2)
                    continue
                break
            except Exception as e:                                   # network trouble: back off and retry
                status = f"ERR {type(e).__name__}"
                time.sleep(2 ** attempt * 2)
        rec = {"url": url, "retrieved_at": now().isoformat(), "status": status, "bytes": len(body) if body else 0,
               "sha256": hashlib.sha256(body).hexdigest() if body else None, "path": None}
        if body and rel_path:
            path = os.path.join(self.out, rel_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with gzip.open(path, "wb") as f:
                f.write(body)
            rec["path"] = rel_path
        self.manifest.write(json.dumps(rec) + "\n")
        return body

    # ------------------------------------------------------------------ passes
    def sweep_metadata(self, max_events: int):
        t = now(); day = t.strftime("%Y/%m/%d"); hms = t.strftime("%H%M%S")
        events, offset = [], 0
        keep_pages = t.timestamp() - self.state["last"].get("raw_pages", 0) >= self.raw_pages_every   # pages are kept whole every few hours; every version of an event is kept whole every time it changes
        if keep_pages:
            self.state["last"]["raw_pages"] = t.timestamp()
        while len(events) < max_events and not STOP:
            body = self.fetch(f"{GAMMA}/events?active=true&closed=false&limit=100&offset={offset}&order=volume24hr&ascending=false",
                              f"gamma/events/{day}/{hms}_{offset}.json.gz" if keep_pages else None)
            if not body:
                break
            page = json.loads(body)
            if not page:
                break
            events += page; offset += 100
        watched = {}
        for e in events:
            eid = str(e.get("id"))
            raw = json.dumps(e, sort_keys=True).encode()
            h = hashlib.sha256(raw).hexdigest()
            if self.state["seen_versions"].get(eid) != h:               # a new version of the event: keep it whole
                self.state["seen_versions"][eid] = h
                p = os.path.join(self.out, f"gamma/event_snapshots/{eid}/{h}.json.gz")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with gzip.open(p, "wb") as f:
                    f.write(raw)
            for m in e.get("markets", []):
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                except Exception:
                    toks = []
                vol = float(m.get("volume24hr") or 0)
                for tk in toks:
                    watched[tk] = {"condition_id": m.get("conditionId"), "event_id": eid, "question": m.get("question"), "volume24hr": vol}
        self.state["watched"] = watched
        self.state["last"]["metadata"] = t.timestamp()
        self.save_state()
        return watched

    def snapshot_books(self, top: int):
        t = now(); d = t.strftime("%Y%m%d"); hms = t.strftime("%H%M%S")
        ranked = sorted(self.state["watched"].items(), key=lambda kv: -kv[1]["volume24hr"])[:top]
        for tk, _ in ranked:
            if STOP:
                break
            self.fetch(f"{CLOB}/book?token_id={tk}", f"clob/book/{tk}/{d}/{hms}.json.gz")
        self.state["last"]["books"] = t.timestamp(); self.save_state()

    def daily_history_and_trades(self, top: int):
        t = now(); d = t.strftime("%Y%m%d")
        ranked = sorted(self.state["watched"].items(), key=lambda kv: -kv[1]["volume24hr"])[:top]
        for tk, info in ranked:
            if STOP:
                break
            self.fetch(f"{CLOB}/prices-history?market={tk}&interval=max&fidelity=60", f"clob/history/{tk}/{d}.json.gz")
        seen_cids = set()
        for tk, info in ranked:
            cid = info["condition_id"]
            if STOP or not cid or cid in seen_cids:
                continue
            seen_cids.add(cid)
            body = self.fetch(f"{DATA}/trades?market={cid}&limit=500")
            if not body:
                continue
            path = os.path.join(self.out, f"data/trades/{cid}.jsonl"); os.makedirs(os.path.dirname(path), exist_ok=True)
            have = set()
            if os.path.exists(path):
                with open(path) as f:
                    have = {json.loads(x).get("transactionHash") for x in f if x.strip()}
            with open(path, "a") as f:
                for tr in json.loads(body):
                    if tr.get("transactionHash") not in have:
                        f.write(json.dumps(tr) + "\n")
        self.state["last"]["daily"] = t.timestamp(); self.save_state()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True); ap.add_argument("--once", action="store_true")
    ap.add_argument("--top", type=int, default=300, help="tokens whose books, history and trades are recorded")
    ap.add_argument("--max-events", type=int, default=300, help="events swept per metadata pass")
    ap.add_argument("--meta-every", type=int, default=3600); ap.add_argument("--book-every", type=int, default=900)
    ap.add_argument("--spacing", type=float, default=0.25)
    ap.add_argument("--raw-pages-every", type=int, default=21600, help="seconds between whole metadata pages being kept (the manifest still logs every page hash)")
    a = ap.parse_args()
    signal.signal(signal.SIGINT, _stop); signal.signal(signal.SIGTERM, _stop)
    r = Recorder(a.out, a.spacing, a.raw_pages_every)
    print(f"recording to {a.out} (Ctrl-C to stop)", file=sys.stderr)
    while not STOP:
        t = time.time(); L = r.state["last"]
        if t - L.get("metadata", 0) >= a.meta_every or not r.state["watched"]:
            w = r.sweep_metadata(a.max_events); print(f"{now().isoformat()} metadata: {len(w)} tokens watched", file=sys.stderr)
        if t - L.get("books", 0) >= a.book_every:
            r.snapshot_books(a.top); print(f"{now().isoformat()} books: top {a.top}", file=sys.stderr)
        if t - L.get("daily", 0) >= 86400:
            r.daily_history_and_trades(a.top); print(f"{now().isoformat()} history and trades", file=sys.stderr)
        if a.once:
            break
        for _ in range(30):
            if STOP:
                break
            time.sleep(1)
    r.manifest.close()


if __name__ == "__main__":
    main()
