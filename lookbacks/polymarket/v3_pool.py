"""V3 forward pool: events OPEN now. Builds (a) the primary pool and (b) the hedge-menu index, both frozen by hash before any session runs.
    python v3_pool.py --crawl     # crawls open events (Gamma), writes v3/v3_open_raw.json.gz and the lock timestamp v3/v3_lock.json (written once)
    python v3_pool.py --build     # writes v3/v3_index.json.gz (menu) and v3/v3_pool.json (primaries) from the crawl
    python v3_pool.py --draw      # seeded draw + reserve -> v3/v3_draw.json, v3/v3_reserve.json"""
import argparse, collections, datetime as dt, gzip, hashlib, json, os, random, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); V3 = os.path.join(HERE, "v3"); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import v1_pool as P, v1_packet as K
from nomad16 import pmgraph as G
SEED, N_DRAW, N_RESERVE, MAX_CRYPTO, MIN_PARTITIONS = 20261001, 30, 10, 8, 4
HORIZON_MIN_D, HORIZON_MAX_D = 14, 75
def sha(o): return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def ts(t): return int(dt.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
def crawl():
    lock_p = os.path.join(V3, "v3_lock.json")
    if os.path.exists(lock_p): sys.exit("lock already written; the crawl is frozen")
    lock = int(time.time()); out = {}
    for order in ("volume", "endDate", "liquidity", "startDate"):
        for asc in ("false", "true"):
            off = 0
            while off < 2100:
                p = P.page(f"{P.GAMMA}?closed=false&order={order}&ascending={asc}&limit=100&offset={off}")
                if not p: break
                for e in p: out[str(e["id"])] = e
                off += 100
    blob = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    with gzip.open(os.path.join(V3, "v3_open_raw.json.gz"), "wb") as f: f.write(blob)
    json.dump({"lock": lock, "as_of": K.as_of(lock), "events": len(out), "raw_sha256": hashlib.sha256(blob).hexdigest()}, open(lock_p, "w"), indent=1)
    print("crawled", len(out), "open events; lock", lock, K.as_of(lock))
def load_raw():
    with gzip.open(os.path.join(V3, "v3_open_raw.json.gz"), "rt") as f: return json.load(f)
def build():
    raw = load_raw(); lock = json.load(open(os.path.join(V3, "v3_lock.json")))["lock"]
    index, pool, dates, tally = [], [], {}, collections.Counter()
    for eid in sorted(raw):
        e = raw[eid]; tally["crawled"] += 1
        if {t.get("slug") for t in (e.get("tags") or [])} & P.EXCL: tally["out_of_scope_tag"] += 1; continue
        if not e.get("startDate") or not e.get("endDate"): tally["no_dates"] += 1; continue
        if e.get("closed"): tally["closed"] += 1; continue
        c = P.compact(e)
        if c["volume"] < P.MIN_EVENT_VOL or sum(m["vol"] >= P.MIN_MARKET_VOL for m in c["markets"]) < P.MIN_MARKETS: tally["not_usable_liquidity"] += 1; continue
        st = G.structure(c); cls = st["class"]
        if cls not in K.CLS: tally[f"class_{cls}"] += 1; continue
        mend = {m.get("conditionId"): m.get("endDate") for m in (e.get("markets") or [])}
        row = K._row(c, cls, {})                                                    # mclosed None: still open
        for m in row["markets"]: m["end"] = mend.get(m["cid"])
        index.append(row); tally["in_index"] += 1
        ends = [ts(x) for x in mend.values() if x]
        if not ends: continue
        H = max(ends)
        if not (lock + HORIZON_MIN_D * 86400 <= H <= lock + HORIZON_MAX_D * 86400): tally["horizon_out_of_window"] += 1; continue
        c["class"] = cls; c["ladder_kind"] = st.get("kind"); c["group"] = P.group(c); c["horizon"] = H
        pool.append(c); tally["in_pool"] += 1
        for cid, end in mend.items(): dates[cid] = {"end": end, "closed": None}
    for path, obj in ((os.path.join(V3, "v3_index.json.gz"), index),):
        blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        with gzip.open(path, "wb") as f: f.write(blob)
        print(os.path.basename(path), len(obj), "sha256", hashlib.sha256(blob).hexdigest())
    json.dump(pool, open(os.path.join(V3, "v3_pool.json"), "w")); json.dump(dates, open(os.path.join(V3, "v3_market_dates.json"), "w"))
    print("pool", len(pool), "sha256", sha(pool)); print(dict(tally))
def draw():
    pool = json.load(open(os.path.join(V3, "v3_pool.json"))); rng = random.Random(SEED)
    Pl = sorted(pool, key=lambda e: e["id"]); parts = [e for e in Pl if e["class"].startswith("partition")]
    chosen = rng.sample(parts, min(MIN_PARTITIONS, len(parts))); left = [e for e in Pl if e not in chosen]; rng.shuffle(left)
    def take(n, into, excl, maxc):
        for e in left:
            if len(into) >= n: break
            if e in into or e in excl: continue
            if e["group"] == "crypto" and sum(x["group"] == "crypto" for x in into) >= maxc: continue
            into.append(e)
        return into
    take(N_DRAW, chosen, [], MAX_CRYPTO); reserve = take(N_RESERVE, [], chosen, 3)
    json.dump([e["id"] for e in sorted(chosen, key=lambda e: e["id"])], open(os.path.join(V3, "v3_draw.json"), "w")); json.dump([e["id"] for e in reserve], open(os.path.join(V3, "v3_reserve.json"), "w"))
    print("drawn", len(chosen), collections.Counter(e["class"] for e in chosen), "crypto", sum(e["group"] == "crypto" for e in chosen), "| reserve", len(reserve))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--crawl", action="store_true"); ap.add_argument("--build", action="store_true"); ap.add_argument("--draw", action="store_true"); a = ap.parse_args()
    if a.crawl: crawl()
    if a.build: build()
    if a.draw: draw()
