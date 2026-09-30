"""V1 pool (V1_prereg.md §2). Crawl closed events, apply the declared eligibility, write ``v1_pool.json`` and print its hash for §9. No outcome is read for selection
beyond 'resolved cleanly'; the draw (``--draw``) is a seeded random draw over the frozen pool.

    python lookbacks/polymarket/v1_pool.py --crawl     # network; writes v1_pool.json and v1_pool_meta.json
    python lookbacks/polymarket/v1_pool.py --draw      # offline; reads v1_pool.json; writes v1_draw.json
"""
import argparse, collections, hashlib, json, random, sys, urllib.request
sys.path.insert(0, __file__.rsplit("/lookbacks/", 1)[0])
from nomad16 import pmgraph as G

H = {"User-Agent": "Mozilla/5.0 (research nomad)"}
GAMMA = "https://gamma-api.polymarket.com/events"
CUTOFF = "2026-06-30"            # after the operator model's declared training cutoff
MIN_EVENT_VOL, MIN_MARKET_VOL, MIN_MARKETS = 100_000, 10_000, 3
CLASSES = {"partition_exact", "partition_open", "ladder", "date_ladder"}
EXCL = set("sports,games,esports,soccer,tennis,nfl,nba,nhl,mlb,hockey,ufc,boxing,golf,f1,cricket,rugby,league-of-legends,dota-2,counter-strike-2,valorant,pop-culture,entertainment,music,movies,celebrities,daily-temperature,highest-temperature,uefa-nations-league,unl-matchday".split(","))
SEED, N_DRAW, MAX_CRYPTO, MIN_PARTITIONS = 20260930, 24, 8, 4


def page(url):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read())
    except Exception:
        return None


def crawl_closed():
    out = {}
    for order in ("volume", "endDate", "liquidity", "startDate"):
        for asc in ("false", "true"):
            off = 0
            while off < 2100:
                p = page(f"{GAMMA}?closed=true&order={order}&ascending={asc}&limit=100&offset={off}")
                if not p:
                    break
                for e in p:
                    out[str(e["id"])] = e
                off += 100
    return out


def compact(e):
    def toks(m):
        try:
            return json.loads(m.get("clobTokenIds") or "[]")
        except Exception:
            return []
    return {"id": str(e["id"]), "title": e.get("title"), "tags": [t.get("slug") for t in (e.get("tags") or [])], "start": e.get("startDate"), "end": e.get("endDate"),
            "closed_time": e.get("closedTime"), "negRisk": e.get("negRisk"), "volume": float(e.get("volume") or 0), "description": e.get("description"),
            "markets": [{"cid": m.get("conditionId"), "tokens": toks(m), "q": m.get("question"), "git": m.get("groupItemTitle"), "gthr": m.get("groupItemThreshold"), "nro": m.get("negRiskOther"),
                         "vol": float(m.get("volumeNum") or m.get("volume") or 0), "fee": m.get("feeType"), "feeSchedule": m.get("feeSchedule"), "tick": m.get("orderPriceMinTickSize"),
                         "uma": m.get("umaResolutionStatus"), "uma_all": m.get("umaResolutionStatuses"), "outcomes": m.get("outcomes"), "final": m.get("outcomePrices"),
                         "description": m.get("description")} for m in (e.get("markets") or [])]}


def resolved_cleanly(e):
    """Every market resolved, decisively (1 and 0), and none disputed."""
    for m in e["markets"]:
        if m["uma"] != "resolved":
            return "not_resolved"
        try:
            f = sorted(float(x) for x in json.loads(m["final"] or "[]"))
        except Exception:
            return "no_final_prices"
        if f != [0.0, 1.0]:
            return "not_decisive"
        if "disputed" in json.dumps(m.get("uma_all") or "").lower():
            return "disputed"
    return None


def group(e):
    t = set(e["tags"])
    if t & {"crypto", "bitcoin", "ethereum", "crypto-prices", "solana", "xrp"}:
        return "crypto"
    return "other"


def build_pool():
    raw = crawl_closed()
    tally = collections.Counter(); pool = []
    for eid in sorted(raw):
        e = raw[eid]
        tally["crawled"] += 1
        ct = (e.get("closedTime") or "")[:10]              # the actual resolution time, NOT the scheduled endDate (an event can resolve months before its scheduled end)
        if not ct:
            tally["no_closed_time"] += 1; continue
        if ct <= CUTOFF:
            tally["closed_before_cutoff"] += 1; continue
        if {t.get("slug") for t in (e.get("tags") or [])} & EXCL:
            tally["out_of_scope_tag"] += 1; continue
        c = compact(e)
        if c["volume"] < MIN_EVENT_VOL or sum(m["vol"] >= MIN_MARKET_VOL for m in c["markets"]) < MIN_MARKETS:
            tally["not_usable_liquidity"] += 1; continue
        cls = G.structure(c)
        if cls["class"] not in CLASSES:
            tally[f"class_{cls['class']}"] += 1; continue
        bad = resolved_cleanly(c)
        if bad:
            tally[bad] += 1; continue
        c["class"] = cls["class"]; c["ladder_kind"] = cls.get("kind"); c["group"] = group(c)
        pool.append(c); tally["in_pool"] += 1
    return pool, dict(tally)


def draw(pool):
    rng = random.Random(SEED)
    P = sorted(pool, key=lambda e: e["id"])
    parts = [e for e in P if e["class"].startswith("partition")]
    rest = [e for e in P if e not in parts]
    chosen = rng.sample(parts, min(MIN_PARTITIONS, len(parts)))
    left = [e for e in P if e not in chosen]
    rng.shuffle(left)
    for e in left:
        if len(chosen) >= N_DRAW:
            break
        if e["group"] == "crypto" and sum(x["group"] == "crypto" for x in chosen) >= MAX_CRYPTO:
            continue
        chosen.append(e)
    return sorted(chosen, key=lambda e: e["id"])


N_RESERVE, MAX_CRYPTO_RESERVE, RESERVE_SEED = 12, 4, SEED + 1


def draw_reserve(pool, survivors, chosen):
    """Reserve (V1_prereg.md A12): survivors not already drawn, second seed, at most 4 crypto, in order. Replaces a drawn non-survivor at once and any voided round later."""
    taken = {e["id"] for e in chosen}
    cand = sorted((e for e in pool if e["id"] in survivors and e["id"] not in taken), key=lambda e: e["id"])
    rng = random.Random(RESERVE_SEED); rng.shuffle(cand)
    out = []
    for e in cand:
        if len(out) >= N_RESERVE:
            break
        if e["group"] == "crypto" and sum(x["group"] == "crypto" for x in out) >= MAX_CRYPTO_RESERVE:
            continue
        out.append(e)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--crawl", action="store_true"); ap.add_argument("--draw", action="store_true"); ap.add_argument("--reserve", action="store_true"); ap.add_argument("--rounds", action="store_true")
    a = ap.parse_args(); here = __file__.rsplit("/", 1)[0]
    if a.crawl:
        pool, tally = build_pool()
        blob = json.dumps(pool, sort_keys=True, separators=(",", ":"))
        json.dump(pool, open(f"{here}/v1_pool.json", "w"), sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256(blob.encode()).hexdigest()
        json.dump({"sha256": h, "n": len(pool), "tally": tally, "cutoff": CUTOFF, "by_class": dict(collections.Counter(e["class"] for e in pool)),
                   "by_group": dict(collections.Counter(e["group"] for e in pool))}, open(f"{here}/v1_pool_meta.json", "w"), indent=1)
        print(json.dumps(tally, indent=1)); print("pool", len(pool), "sha256", h)
    if a.draw:
        pool = json.load(open(f"{here}/v1_pool.json"))
        d = draw(pool)
        json.dump([{"id": e["id"], "title": e["title"], "class": e["class"], "group": e["group"]} for e in d], open(f"{here}/v1_draw.json", "w"), indent=1)
        print(len(d), "drawn:", dict(collections.Counter(e["class"] for e in d)), dict(collections.Counter(e["group"] for e in d)))
    if a.reserve:
        pool = json.load(open(f"{here}/v1_pool.json")); d = json.load(open(f"{here}/v1_draw.json")); sv = json.load(open(f"{here}/v1_survivors.json"))
        surv = {r["id"] for r in sv if r["priced"] >= 3 and r["menu_templates"] >= 10}
        chosen = [e for e in pool if e["id"] in {x["id"] for x in d}]
        non = [e["id"] for e in chosen if e["id"] not in surv]
        res = draw_reserve(pool, surv, chosen)
        json.dump({"non_survivors_in_draw": non, "reserve_in_order": [{"id": e["id"], "title": e["title"], "class": e["class"], "group": e["group"]} for e in res]}, open(f"{here}/v1_reserve.json", "w"), indent=1)
        print("non-survivors in the draw:", non, "| reserve:", len(res), dict(collections.Counter(e["class"] for e in res)), dict(collections.Counter(e["group"] for e in res)))
    if a.rounds:
        # the final round list by rule (V1_prereg.md A12 to A14): a drawn event is replaced, in reserve order, if it shows fewer than 3 contracts at its lock or has fewer than 10 live templates
        sys.path.insert(0, here); import v1_packet as K
        pool = {e["id"]: e for e in json.load(open(f"{here}/v1_pool.json"))}; d = [x["id"] for x in json.load(open(f"{here}/v1_draw.json"))]
        res = [x["id"] for x in json.load(open(f"{here}/v1_reserve.json"))["reserve_in_order"]]; rc = {r["id"]: r for r in json.load(open(f"{here}/v1_survivors_recount.json"))}
        idx = K.load_index(); spans = [(K.ts(r["start"]), K.ts(r["closed_time"]), r["id"], K.G.template(r["title"])) for r in idx]
        def why(eid):
            e = pool[eid]; lk = K.lock_of(e); tpl = K.G.template(e["title"])
            live = len({t for (s_, c, i, t) in spans if s_ <= lk <= c and i != eid and t != tpl})
            return [f"shows {rc[eid]['shown']} contracts (<3)"] * (rc[eid]["shown"] < 3) + [f"{live} live templates (<10)"] * (live < 10)
        final, log, reserve = [], [], list(res)
        for eid in d:
            w = why(eid)
            if not w:
                final.append(eid); continue
            while reserve:
                r = reserve.pop(0)
                if not why(r):
                    final.append(r); log.append({"replaced": eid, "reason": w, "by": r}); break
                log.append({"skipped_reserve": r, "reason": why(r)})
        json.dump({"rounds": final, "replacements": log, "reserve_left": reserve}, open(f"{here}/v1_rounds.json", "w"), indent=1)
        print(len(final), "rounds;", len(log), "log entries;", len(reserve), "reserve left"); [print(" ", x) for x in log]
