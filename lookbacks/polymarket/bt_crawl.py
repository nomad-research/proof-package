"""Backtest crawl (v18 §6.7 lever 3, §8): closed Polymarket events, crawled in scheduled-end windows small enough to stay under the API's offset cap.

    python lookbacks/polymarket/bt_crawl.py --from 2026-01-01 --to 2026-10-01      # network; writes bt/closed_<from>_<to>.json.gz and prints its sha256

Each window asks Gamma for closed events whose scheduled end (`endDate`) falls inside it and pages through them; a window that reaches the offset cap is split
in half and re-crawled, so nothing is lost to the cap. Every event's and market's times are kept as the API gives them (`createdAt`, `startDate`, `endDate`,
`closedTime`) so eligibility can be decided later by schedule (v18 §6.7 rule 4 needs each market's `createdAt`). Nothing here reads a price or filters on how an
event resolved. Scope (sport, gaming, entertainment, temperature) and the Anthropic/Claude exclusion are applied later, by the test that reads the crawl, so the
crawl stays one shared, hashed input.
"""
import argparse, datetime as dt, gzip, hashlib, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "bt")
GAMMA = "https://gamma-api.polymarket.com/events"
H = {"User-Agent": "Mozilla/5.0 (research nomad)"}
PAGE, CAP = 100, 2000                         # page size; offsets at or past CAP are not trusted (the API caps an ordering near 2,100)


def get(url, tries=5):
    for k in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read().decode("utf-8"))
        except Exception as ex:
            if k == tries - 1:
                raise RuntimeError(f"{url}: {ex!r}")
            time.sleep(2 * (k + 1))


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def toks(m):
    try:
        return json.loads(m.get("clobTokenIds") or "[]")
    except Exception:
        return []


def compact(e):
    return {"id": str(e["id"]), "title": e.get("title"), "slug": e.get("slug"), "tags": [t.get("slug") for t in (e.get("tags") or [])],
            "created": e.get("createdAt"), "start": e.get("startDate"), "end": e.get("endDate"), "closed_time": e.get("closedTime"),
            "negRisk": e.get("negRisk"), "volume": float(e.get("volume") or 0), "description": e.get("description"), "resolution_source": e.get("resolutionSource"),
            "markets": [{"cid": m.get("conditionId"), "tokens": toks(m), "q": m.get("question"), "git": m.get("groupItemTitle"), "gthr": m.get("groupItemThreshold"),
                         "nro": m.get("negRiskOther"), "created": m.get("createdAt"), "start": m.get("startDate"), "end": m.get("endDate"), "closed_time": m.get("closedTime"),
                         "vol": float(m.get("volumeNum") or m.get("volume") or 0), "fee": m.get("feeType"), "feeSchedule": m.get("feeSchedule"),
                         "tick": m.get("orderPriceMinTickSize"), "min_size": m.get("orderMinSize"), "uma": m.get("umaResolutionStatus"),
                         "uma_all": m.get("umaResolutionStatuses"), "outcomes": m.get("outcomes"), "final": m.get("outcomePrices"),
                         "description": m.get("description")} for m in (e.get("markets") or [])]}


VOLUME_MIN = 0                                # set by --volume-min; a lifetime-volume prefilter applied by the API (the tests decide liquidity at the lock themselves)
SCOPE = False                                 # set by --scope: drop the recorder's out-of-scope tags (as V1_pool.EXCL) and intraday "Up or Down" markets
EXCL = set("sports,games,esports,soccer,tennis,nfl,nba,nhl,mlb,hockey,ufc,boxing,golf,f1,cricket,rugby,league-of-legends,dota-2,counter-strike-2,valorant,pop-culture,"
           "entertainment,music,movies,celebrities,daily-temperature,highest-temperature,uefa-nations-league,unl-matchday".split(","))   # v1_pool.EXCL, copied
DROPPED = {"out_of_scope_tag": 0, "up_or_down": 0}


def in_scope(e):
    tags = {t.get("slug") for t in (e.get("tags") or [])}
    if tags & EXCL:
        DROPPED["out_of_scope_tag"] += 1; return False
    if "up or down" in (e.get("title") or "").lower() or "up-or-down" in tags:
        DROPPED["up_or_down"] += 1; return False
    return True


def crawl_window(a, b, out, log):
    """Every closed event with a scheduled end in [a, b). Splits the window if a full page is still coming back at the cap."""
    off = 0
    while True:
        vq = f"&volume_min={VOLUME_MIN:g}" if VOLUME_MIN else ""
        p = get(f"{GAMMA}?closed=true&end_date_min={iso(a)}&end_date_max={iso(b)}&order=endDate&ascending=true&limit={PAGE}&offset={off}{vq}")
        for e in p:
            if str(e["id"]) not in out and (not SCOPE or in_scope(e)):
                out[str(e["id"])] = compact(e)
        if len(p) < PAGE:
            log.append({"from": iso(a), "to": iso(b), "events": off + len(p)}); return
        off += PAGE
        if off >= CAP:
            if b - a <= dt.timedelta(minutes=30):
                raise RuntimeError(f"window {iso(a)} to {iso(b)} still exceeds the cap at 30 minutes")
            mid = a + (b - a) / 2
            crawl_window(a, mid, out, log); crawl_window(mid, b, out, log); return
        time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="a", required=True); ap.add_argument("--to", dest="b", required=True)
    ap.add_argument("--step-hours", type=float, default=24.0)
    ap.add_argument("--volume-min", type=float, default=0.0, help="lifetime event volume floor passed to the API (a prefilter; recorded in the meta file)")
    ap.add_argument("--scope", action="store_true", help="drop out-of-scope tags and intraday Up or Down events at crawl time (counted in the meta file)")
    x = ap.parse_args()
    global VOLUME_MIN, SCOPE
    VOLUME_MIN, SCOPE = x.volume_min, x.scope
    a = dt.datetime.fromisoformat(x.a).replace(tzinfo=dt.timezone.utc); b = dt.datetime.fromisoformat(x.b).replace(tzinfo=dt.timezone.utc)
    out, log, t = {}, [], a
    while t < b:
        u = min(t + dt.timedelta(hours=x.step_hours), b)
        crawl_window(t, u, out, log); t = u
        print(f"{iso(u)}  events so far {len(out)}", file=sys.stderr, flush=True)
    os.makedirs(OUT, exist_ok=True)
    rows = sorted(out.values(), key=lambda e: (e.get("end") or "", e["id"]))
    meta = {"crawled_at": iso(dt.datetime.now(dt.timezone.utc)), "from": x.a, "to": x.b, "volume_min": x.volume_min, "scope": x.scope, "dropped": DROPPED,
            "filter": "closed=true, endDate in window" + (f", lifetime event volume >= {x.volume_min:g}" if x.volume_min else "")
                      + (", out-of-scope tags and Up or Down dropped" if x.scope else ""), "events": len(rows), "windows": log}
    path = os.path.join(OUT, f"closed_{x.a}_{x.b}" + (f"_v{x.volume_min:g}" if x.volume_min else "") + ("_scoped" if x.scope else "") + ".json.gz")
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(path, "wb", mtime=0) as fh:
        fh.write(blob)
    meta["sha256_of_json"] = hashlib.sha256(blob).hexdigest()
    json.dump(meta, open(path.replace(".json.gz", "_meta.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: meta[k] for k in ("events", "sha256_of_json", "crawled_at")}))


if __name__ == "__main__":
    main()
