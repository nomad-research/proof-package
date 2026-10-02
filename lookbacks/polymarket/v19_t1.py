"""T1: do linked contracts lag each other? (V19_T1_COHERENCE_prereg.md). Frozen files are read, never written.

    python lookbacks/polymarket/v19_t1.py draw            # no network: bt/t1/links.json (titles and rules only)
    python lookbacks/polymarket/v19_t1.py pull [part]     # network: trade prints per contract -> bt/t1/trades_<part>.json.gz (parts 0-2 run in parallel)
    python lookbacks/polymarket/v19_t1.py score           # no network: v19/t1_result.json
"""
import collections, gzip, json, os, random, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T

SEED, PER_COIN, COINS = 20261017, 12, ("bitcoin", "ethereum", "solana", "xrp")
FRESH, COST, SHOCK, AFTER, LONG, STAKE = 30 * 60, 0.02, 0.10, 60 * 60, 30 * 60, 100.0
PAGE, MAX_OFFSET, PARTS = 10000, 10000, 3
D = os.path.join(HERE, "bt", "t1"); CRAWL = "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"
MONEY = r"\$?([\d,]+(?:\.\d+)?)\s*(k|K)?"


def num(s, k):
    return float(s.replace(",", "")) * (1000 if k else 1)


def bracket(q):
    """(low, high) of a 'price on' bracket question, or None."""
    m = re.search(r"less than " + MONEY, q, re.I)
    if m:
        return (0.0, num(*m.groups()))
    m = re.search(r"between " + MONEY + r" and " + MONEY, q, re.I)
    if m:
        g = m.groups(); return (num(g[0], g[1]), num(g[2], g[3]))
    m = re.search(r"(?:greater than|more than|above|over) " + MONEY, q, re.I)
    if m:
        return (num(*m.groups()), float("inf"))
    return None


def threshold(q):
    m = re.search(r"above " + MONEY, q, re.I)
    return num(*m.groups()) if m else None


def cmd_draw():
    crawl = A.jload(os.path.join(HERE, "bt", CRAWL)); on, ab = {}, {}
    p_on = re.compile(r"^(bitcoin|ethereum|solana|xrp) price on (.+?)\??$", re.I); p_ab = re.compile(r"^(bitcoin|ethereum|solana|xrp) above _+ on (.+?)\??$", re.I)
    for e in crawl:
        t = (e.get("title") or "").strip(); a, b = p_on.match(t), p_ab.match(t)
        if a:
            on.setdefault((a.group(1).lower(), a.group(2).lower()), e)
        if b:
            ab.setdefault((b.group(1).lower(), b.group(2).lower()), e)
    pairs = sorted(set(on) & set(ab)); rng = random.Random(SEED); links, contracts = [], {}
    for coin in COINS:
        mine = [p for p in pairs if p[0] == coin]
        for key in sorted(rng.sample(mine, min(PER_COIN, len(mine)))):
            eo, ea = on[key], ab[key]
            if eo["end"] != ea["end"]:
                continue                                          # same resolution moment only
            br = [(bracket(m["q"]), m["cid"]) for m in eo["markets"]]; br = [(b, c) for b, c in br if b]
            th = sorted((threshold(m["q"]), m["cid"]) for m in ea["markets"] if threshold(m["q"]))
            for e_ in (eo, ea):
                for m in e_["markets"]:
                    contracts[m["cid"]] = {"event": e_["id"], "q": m["q"]}
            for (x, cx) in th:
                above = [(b, c) for b, c in br if b[0] >= x]; below = [(b, c) for b, c in br if b[1] <= x]
                if above:
                    b, c = min(above, key=lambda z: z[0][0])
                    links.append({"family": "F1", "kind": "bracket above X <= above X", "i": cx, "j": c, "rel": "le", "unit": f"{coin} {key[1]}"})
                if below:
                    b, c = max(below, key=lambda z: z[0][1])
                    links.append({"family": "F1", "kind": "bracket below X + above X <= 1", "i": cx, "j": c, "rel": "sum", "unit": f"{coin} {key[1]}"})
            for (x1, c1), (x2, c2) in zip(th, th[1:]):
                links.append({"family": "F2", "kind": "above ladder", "i": c1, "j": c2, "rel": "le", "unit": f"{coin} {key[1]}"})
    seen = set()
    for d in ("t2", "t2_pass2", "t2_pass3", "t2_pass4", "t2_pass5"):
        for ev in A.jload(os.path.join(HERE, "bt", d, "frame.json"))["events"]:
            if ev["id"] in seen or ev["kind"] not in ("terminal", "touch", "dates", "dates1"):
                continue
            seen.add(ev["id"]); k = ev["kind"]
            for side in ("up", "down"):
                cs = [c for c in ev["contracts"] if T.rung_value(c, k) is not None and (k in ("dates", "dates1") or T.S.orient(c["q"]) == side)]
                if k in ("dates", "dates1") and side == "down":
                    continue
                cs.sort(key=lambda c: T.rung_value(c, k))
                for a, b in zip(cs, cs[1:]):
                    # the rung that is easier to reach is i (at least as likely as j)
                    if k in ("dates", "dates1"):
                        i, j = b, a                                # by a later date is likelier
                    elif side == "up":
                        i, j = a, b                                # above / reach a lower level is likelier
                    else:
                        i, j = b, a                                # dip to / below: the higher level is likelier
                    links.append({"family": "F3", "kind": k, "i": i["cid"], "j": j["cid"], "rel": "le", "unit": f"{d}/{ev['id']}"})
                    for c in (i, j):
                        contracts[c["cid"]] = {"event": ev["id"], "q": c["q"]}
    os.makedirs(D, exist_ok=True)
    A.jdump({"seed": SEED, "links": links, "contracts": contracts}, os.path.join(D, "links.json"))
    print(json.dumps({"links": collections.Counter(l["family"] for l in links), "contracts": len(contracts),
                      "units": {f: len({l["unit"] for l in links if l["family"] == f}) for f in ("F1", "F2", "F3")}}, default=dict))


def get(url):
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"}), timeout=60))
        except Exception:
            if i == 4:
                return None
            time.sleep(2 ** (i + 1))


def fetch(cid):
    """All prints (newest 20,000 at most) as compact rows: [timestamp, YES price, dollars]."""
    rows, full = [], False
    for off in range(0, MAX_OFFSET + 1, PAGE):
        d = get(f"https://data-api.polymarket.com/trades?market={cid}&limit={PAGE}&offset={off}")
        if not isinstance(d, list):
            return {"rows": rows, "full": False, "error": True}
        for x in d:
            p = float(x["price"]); y = p if x.get("outcome") == "Yes" else 1 - p
            rows.append([int(x["timestamp"]), round(y, 4), round(float(x.get("size") or 0) * p, 2)])
        if len(d) < PAGE:
            full = True; break
    rows.sort()
    return {"rows": rows, "full": full}


def tpath(part):
    return os.path.join(D, f"trades_{part}.json.gz")


def load_trades():
    out = {}
    for p in range(PARTS):
        if os.path.exists(tpath(p)):
            out.update(json.load(gzip.open(tpath(p), "rt")))
    return out


def cmd_pull(part):
    cids = sorted(A.jload(os.path.join(D, "links.json"))["contracts"]); mine = [c for i, c in enumerate(cids) if i % PARTS == part]
    got = json.load(gzip.open(tpath(part), "rt")) if os.path.exists(tpath(part)) else {}
    todo = [c for c in mine if c not in got or got[c].get("error")]; print(f"part {part}: {len(todo)} to pull of {len(mine)}", flush=True)

    def save():
        tmp = tpath(part) + ".tmp"
        with gzip.open(tmp, "wt") as f:
            json.dump(got, f)
        os.replace(tmp, tpath(part))
    with ThreadPoolExecutor(6) as ex:
        for n, (c, r) in enumerate(zip(todo, ex.map(fetch, todo)), 1):
            got[c] = r
            if n % 200 == 0:
                save(); print(f"  part {part}: {n}/{len(todo)}", flush=True)
    save(); print(f"part {part}: done, {len(got)} held", flush=True)


def episodes(link, tr):
    """Walk both legs' prints in time order; return the link's fresh-state count, violating-state count, episodes and shocks."""
    a, b = tr[link["i"]]["rows"], tr[link["j"]]["rows"]
    ev = sorted([(t, 0, p, u) for t, p, u in a] + [(t, 1, p, u) for t, p, u in b])
    last = [None, None]; prev = [None, None]; shocks = []; fresh = viol = 0; eps = []; cur = None
    for t, leg, p, u in ev:
        if prev[leg] is not None and t - prev[leg][0] <= AFTER and abs(p - prev[leg][1]) >= SHOCK:
            shocks.append(t)
        prev[leg] = (t, p); last[leg] = (t, p)
        if last[0] is None or last[1] is None or t - last[0][0] > FRESH or t - last[1][0] > FRESH:
            continue
        pi, pj = last[0][1], last[1][1]
        v = (pj - pi) if link["rel"] == "le" else (pi + pj - 1)
        fresh += 1
        if v > COST:
            viol += 1
            if cur is None:
                cur = {"start": t, "end": None, "max_gap": v, "usd": 0.0}
            cur["max_gap"] = max(cur["max_gap"], v); cur["usd"] += u
        elif cur is not None:
            cur["end"] = t; eps.append(cur); cur = None
    if cur is not None:
        cur["end"] = None; eps.append(cur)
    for e in eps:
        e["censored"] = e["end"] is None; e["minutes"] = ((e["end"] or e["start"]) - e["start"]) / 60
        e["after_shock"] = any(0 <= e["start"] - s <= AFTER for s in shocks)
    return fresh, viol, eps, shocks


def summary(eps, fresh, viol, shocks, shock_hit):
    def med(xs):
        return float(np.median(xs)) if xs else None
    post = [e for e in eps if e["after_shock"]]
    out = {"fresh_states": fresh, "violating_share": viol / fresh if fresh else None, "episodes": len(eps), "censored": sum(e["censored"] for e in eps),
           "shocks": shocks, "shocks_followed_by_an_episode": shock_hit, "share_of_shocks_followed": shock_hit / shocks if shocks else None,
           "all_episodes": {"median_minutes": med([e["minutes"] for e in eps]), "p90_minutes": float(np.percentile([e["minutes"] for e in eps], 90)) if eps else None,
                            "share_30_min_or_more": float(np.mean([e["minutes"] >= LONG / 60 for e in eps])) if eps else None,
                            "median_usd": med([e["usd"] for e in eps]), "median_max_gap": med([e["max_gap"] for e in eps])},
           "after_shock": {"n": len(post), "median_minutes": med([e["minutes"] for e in post]),
                           "p90_minutes": float(np.percentile([e["minutes"] for e in post], 90)) if post else None,
                           "share_30_min_or_more": float(np.mean([e["minutes"] >= LONG / 60 for e in post])) if post else None,
                           "median_usd": med([e["usd"] for e in post]), "share_usd_100_or_more": float(np.mean([e["usd"] >= STAKE for e in post])) if post else None,
                           "median_max_gap": med([e["max_gap"] for e in post])}}
    a = out["after_shock"]
    out["reading"] = (None if not post else "worth building for" if a["median_minutes"] >= LONG / 60 and a["median_usd"] >= STAKE
                      else "kept consistent faster than a reader can act, or too thinly to trade")
    return out


def cmd_score():
    L = A.jload(os.path.join(D, "links.json")); tr = load_trades(); res = collections.defaultdict(lambda: {"eps": [], "fresh": 0, "viol": 0, "shocks": 0, "hit": 0})
    cover = {"contracts": len(L["contracts"]), "pulled": sum(1 for c in L["contracts"] if c in tr), "full_history": sum(1 for c in L["contracts"] if c in tr and tr[c]["full"]),
             "errors": sum(1 for c in L["contracts"] if c in tr and tr[c].get("error"))}
    for l in L["links"]:
        if l["i"] not in tr or l["j"] not in tr:
            continue
        fresh, viol, eps, shocks = episodes(l, tr)
        hit = sum(1 for s in set(shocks) if any(0 <= e["start"] - s <= AFTER for e in eps))
        for key in (l["family"], f"{l['family']} {l['kind']}" if l["family"] == "F3" else None):
            if key:
                r = res[key]; r["eps"] += eps; r["fresh"] += fresh; r["viol"] += viol; r["shocks"] += len(set(shocks)); r["hit"] += hit
    out = {"coverage": cover, "links": dict(collections.Counter(l["family"] for l in L["links"])),
           "by_family": {k: summary(r["eps"], r["fresh"], r["viol"], r["shocks"], r["hit"]) for k, r in sorted(res.items())}}
    A.jdump(out, os.path.join(HERE, "v19", "t1_result.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"draw": cmd_draw, "score": cmd_score}.get(sys.argv[1], lambda: cmd_pull(int(sys.argv[2])))()
