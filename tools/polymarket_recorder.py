#!/usr/bin/env python3
"""Polymarket forward recorder. Standard library only (Python 3.9+). Records the public market data whole and never reduces it.

    python3 polymarket_recorder.py --out ./polymarket_record               # run until stopped (Ctrl-C)
    python3 polymarket_recorder.py --out ./polymarket_record --once --top 5   # one pass, for a smoke test

What it writes under --out (all raw response bytes, gzip is lossless and applied on write; nothing is filtered or summarised):
  gamma/events/<YYYY>/<MM>/<DD>/<HHMMSS>_<offset>.json.gz    market metadata pages, every sweep
  gamma/event_snapshots/<event_id>/<sha256>.json.gz           one file per distinct version of an event (resolution rules and prices change; an edit is a new version)
  clob/book/<token_id>/<YYYYMMDD>/<HHMMSS>.json.gz            order book snapshots for the top markets by volume
  clob/history/<token_id>/<YYYYMMDD>_1d_f1.json.gz            the last day at 1-minute bars, every day (1-minute bars age out after about 7 days);
                                                              _1w_f5 the last week at 5-minute bars, every day; _max_f30 the whole range at 30-minute fidelity, weekly
  (events that leave the active list keep being fetched until closed and every market shows umaResolutionStatus resolved, so proposals, disputes and final prices are kept)
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
# Scope (Rob, 2026-09-30): geopolitical and anything adjacent (finance, STEM, business, manufacturing and so on). Everything is in scope except these tags, which are
# sport, gaming and entertainment, and the recurring daily-temperature ladders. The list is a default, not a rule: every tag seen is counted in state.json so it can be tuned.
DEFAULT_EXCLUDE = ("sports,games,esports,soccer,tennis,nfl,nba,nhl,mlb,hockey,ufc,boxing,golf,f1,cricket,rugby,league-of-legends,dota-2,counter-strike-2,valorant,"
                   "pop-culture,entertainment,music,movies,celebrities,daily-temperature,highest-temperature,uefa-nations-league,unl-matchday")
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Recorder:
    def __init__(self, out: str, spacing: float, raw_pages_every: int = 21600, exclude: str = DEFAULT_EXCLUDE, include: str = ""):
        self.out, self.spacing, self.raw_pages_every = out, spacing, raw_pages_every
        self.exclude = {x for x in exclude.split(",") if x}; self.include = {x for x in include.split(",") if x}
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
    def in_scope(self, e: dict) -> bool:
        slugs = {(t.get("slug") or "") for t in (e.get("tags") or [])}
        for sl in slugs:
            self.state.setdefault("tags_seen", {})
            self.state["tags_seen"][sl] = self.state["tags_seen"].get(sl, 0) + 1
        if self.include and not (slugs & self.include):
            return False
        return not (slugs & self.exclude)

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
            if not self.in_scope(e):
                continue
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
        active_ids = {str(e.get("id")) for e in events}
        gone = [eid for eid in list(self.state["seen_versions"]) if eid not in active_ids and eid not in self.state.setdefault("finalised", {})]
        for eid in gone[:60]:                                          # events no longer active: keep every version until closed and resolved (UMA proposal, challenge, dispute, final prices)
            if STOP:
                break
            body = self.fetch(f"{GAMMA}/events/{eid}")
            if not body:
                continue
            e = json.loads(body); raw = json.dumps(e, sort_keys=True).encode(); h = hashlib.sha256(raw).hexdigest()
            if self.state["seen_versions"].get(eid) != h:
                self.state["seen_versions"][eid] = h
                p = os.path.join(self.out, f"gamma/event_snapshots/{eid}/{h}.json.gz"); os.makedirs(os.path.dirname(p), exist_ok=True)
                with gzip.open(p, "wb") as f:
                    f.write(raw)
            ms = e.get("markets", [])
            if e.get("closed") and ms and all(str(m.get("umaResolutionStatus")) == "resolved" for m in ms):
                self.state["finalised"][eid] = now().isoformat()
        self.state["last"]["metadata"] = t.timestamp()
        self.save_state()
        return watched

    def sweep_universe(self):
        """The whole open set, compactly, once a day: every active event with its structure (tags, dates, negRisk, markets with condition and token ids,
        thresholds, fee schedule, a hash of the rules text). The API caps one ordering at about 2,100 events, so the union of ten orderings is taken; the
        last orderings' new-id counts are logged so coverage can be judged. Nothing is dropped by tag here: scope is applied at analysis, so the graph stays whole."""
        t = now(); rows, added = {}, []
        for order in ("volume24hr", "volume", "liquidity", "endDate", "startDate"):
            for asc in ("false", "true"):
                before, offset = len(rows), 0
                while offset < 2100 and not STOP:
                    body = self.fetch(f"{GAMMA}/events?active=true&closed=false&limit=100&offset={offset}&order={order}&ascending={asc}", None)
                    if not body:
                        break
                    page = json.loads(body)
                    if not page:
                        break
                    for e in page:
                        rows[str(e.get("id"))] = self._compact(e, header_only=bool({x.get("slug") for x in (e.get("tags") or [])} & self.exclude))
                    offset += 100
                added.append((order, asc, len(rows) - before))
        if STOP:
            return
        path = os.path.join(self.out, f"universe/{t.strftime('%Y/%m/%d')}_{t.strftime('%H%M%S')}.jsonl.gz")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with gzip.open(path, "wt") as f:
            for r in rows.values():
                f.write(json.dumps(r, sort_keys=True) + "\n")
        self.state["last"]["universe"] = t.timestamp(); self.state["universe_added"] = added; self.save_state()
        return len(rows), added

    @staticmethod
    def _compact(e, header_only=False):
        def toks(m):
            try:
                return json.loads(m.get("clobTokenIds") or "[]")
            except Exception:
                return []
        if header_only:                       # out-of-scope events stay in the universe as a header, so counts are whole; their markets are not stored
            return {"id": e.get("id"), "title": e.get("title"), "tags": [x.get("slug") for x in (e.get("tags") or [])], "start": e.get("startDate"), "end": e.get("endDate"),
                    "volume": e.get("volume"), "n_markets": len(e.get("markets") or []), "header_only": True}
        return {"id": e.get("id"), "slug": e.get("slug"), "title": e.get("title"), "tags": [x.get("slug") for x in (e.get("tags") or [])], "start": e.get("startDate"),
                "end": e.get("endDate"), "negRisk": e.get("negRisk"), "volume": e.get("volume"), "liquidity": e.get("liquidity"),
                "markets": [{"cid": m.get("conditionId"), "tokens": toks(m), "q": m.get("question"), "git": m.get("groupItemTitle"), "gthr": m.get("groupItemThreshold"),
                             "nro": m.get("negRiskOther"), "vol24": m.get("volume24hr"), "vol": m.get("volumeNum") or m.get("volume"), "fee": m.get("feeType"),
                             "feeSchedule": m.get("feeSchedule"), "tick": m.get("orderPriceMinTickSize"), "closed": m.get("closed"), "uma": m.get("umaResolutionStatus"),
                             "rules_sha": hashlib.sha256((m.get("description") or "").encode()).hexdigest()[:16]} for m in (e.get("markets") or [])]}

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
        weekly = t.timestamp() - self.state["last"].get("history_max", 0) >= 7 * 86400
        for tk, info in ranked:
            if STOP:
                break
            # Polymarket keeps 1-minute bars about 7 days, 5-minute about 60 days, 30-minute about 90 days; older comes back only in 12-hour buckets.
            # So the finest bars are taken every day before they age out, and the whole range at 30-minute fidelity once a week.
            # (the endpoint refuses 1w at fidelity 1 with a 400; 1d at fidelity 1 returns about 1,440 one-minute bars, 1w at fidelity 5 about 2,000 five-minute bars)
            self.fetch(f"{CLOB}/prices-history?market={tk}&interval=1d&fidelity=1", f"clob/history/{tk}/{d}_1d_f1.json.gz")
            self.fetch(f"{CLOB}/prices-history?market={tk}&interval=1w&fidelity=5", f"clob/history/{tk}/{d}_1w_f5.json.gz")
            if weekly:
                self.fetch(f"{CLOB}/prices-history?market={tk}&interval=max&fidelity=30", f"clob/history/{tk}/{d}_max_f30.json.gz")
        if weekly:
            self.state["last"]["history_max"] = t.timestamp()
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
    ap.add_argument("--universe-every", type=int, default=86400, help="seconds between whole-open-set sweeps")
    ap.add_argument("--exclude-tags", default=DEFAULT_EXCLUDE, help="comma-separated tag slugs to leave out")
    ap.add_argument("--include-tags", default="", help="if set, only events with one of these tag slugs are recorded")
    ap.add_argument("--raw-pages-every", type=int, default=21600, help="seconds between whole metadata pages being kept (the manifest still logs every page hash)")
    a = ap.parse_args()
    signal.signal(signal.SIGINT, _stop); signal.signal(signal.SIGTERM, _stop)
    r = Recorder(a.out, a.spacing, a.raw_pages_every, a.exclude_tags, a.include_tags)
    print(f"recording to {a.out} (Ctrl-C to stop)", file=sys.stderr)
    while not STOP:
        t = time.time(); L = r.state["last"]
        if t - L.get("metadata", 0) >= a.meta_every or not r.state["watched"]:
            w = r.sweep_metadata(a.max_events); print(f"{now().isoformat()} metadata: {len(w)} tokens watched", file=sys.stderr)
        if t - L.get("universe", 0) >= a.universe_every:
            u = r.sweep_universe(); print(f"{now().isoformat()} universe: {u[0] if u else 'stopped'} open events; new ids by ordering {u[1] if u else ''}", file=sys.stderr)
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
