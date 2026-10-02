"""The backtests at real prices (V19_REAL_PRICES_prereg.md). Frozen pass folders are read, never written.

    python lookbacks/polymarket/v19_real_prices.py pull [pass ...]    # network: trade prints near each lock -> bt/real_prices/<pass>.json.gz
    python lookbacks/polymarket/v19_real_prices.py score              # no network: writes v19/real_prices_result.json
"""
import collections, datetime as dt, gzip, json, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import numpy as np
import bt_audit as A
import bt_t2 as T
import v19_a2 as V
from nomad16 import exact as X

BT_T2 = ("t2", "t2_pass2", "t2_pass3", "t2_pass4", "t2_pass5"); E3 = ("e3_mentions", "e3_mentions_pass2"); BTA = ("audit", "audit_pass2")
BEFORE, AFTER = 48 * 3600, 24 * 3600                 # the price window (V1 A2's 48 hours); prints kept to 24 hours after the lock
PAGE, MAX_OFFSET = 10000, 10000                      # the trades API's largest page and offset
ARM_COST, ARM_GAP, MIN_USD, SEED = 0.50, 0.20, 100.0, 20261015
RP = os.path.join(HERE, "bt", "real_prices"); OUT = os.path.join(HERE, "v19", "real_prices_result.json")


def iso_ts(s):
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()


def locks_of(d):
    """(condition id, lock time) for every contract the pass could score."""
    if d in BTA:
        return [(c["cid"], e["price_time"]) for e in A.jload(os.path.join(HERE, "bt", d, "draw.json"))["events"] if e["month"] >= "2026-04" for c in e["contracts"]]
    return [(c["cid"], e["lock"]) for e in A.jload(os.path.join(HERE, "bt", d, "frame.json"))["events"] for c in e["contracts"]]


def get(url):
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"}), timeout=60))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            if i == 4:
                raise
            time.sleep(2 ** (i + 1))


def fetch(cid, lock):
    """Prints from 48 hours before to 24 hours after the lock, newest pages first; 'reached' says whether the pull got back past the window's start."""
    keep, n, reached = [], 0, False
    for off in range(0, MAX_OFFSET + 1, PAGE):
        try:
            d = get(f"https://data-api.polymarket.com/trades?market={cid}&limit={PAGE}&offset={off}")
        except Exception as e:                       # the API keeps failing on this market: unreachable (prereg §1), never a crash
            return {"prints": keep, "fetched": n, "reached": False, "error": repr(e)[:200]}
        if not isinstance(d, list):
            break
        n += len(d)
        keep += [{k: x.get(k) for k in ("timestamp", "price", "size", "outcome", "side")} for x in d if lock - BEFORE <= x["timestamp"] <= lock + AFTER]
        if len(d) < PAGE or (d and d[-1]["timestamp"] < lock - BEFORE):
            reached = True; break
    return {"prints": keep, "fetched": n, "reached": reached}


def path_of(d):
    return os.path.join(RP, f"{d}.json.gz")


def load(d):
    p = path_of(d)
    return json.load(gzip.open(p, "rt")) if os.path.exists(p) else {}


def save(d, got):
    os.makedirs(RP, exist_ok=True); tmp = path_of(d) + ".tmp"
    with gzip.open(tmp, "wt") as f:
        json.dump(got, f, sort_keys=True)
    os.replace(tmp, path_of(d))


def cmd_pull(passes):
    for d in passes:
        got = load(d); todo = sorted({f"{c}|{t}" for c, t in locks_of(d)} - set(got)); done = 0
        print(f"{d}: {len(todo)} to pull, {len(got)} already held", flush=True)
        with ThreadPoolExecutor(6) as ex:
            for key, res in zip(todo, ex.map(lambda k: fetch(k.split("|")[0], int(float(k.split("|")[1]))), todo)):
                got[key] = res; done += 1
                if done % 250 == 0:
                    save(d, got); print(f"  {d}: {done}/{len(todo)}", flush=True)
        save(d, got); print(f"{d}: done, {len(got)} held", flush=True)


def real_yes(entry, lock, mode="last", min_usd=0.0):
    """The YES price from the prints at or before the lock within 48 hours; None if there is none."""
    if entry is None:
        return None
    ps = [x for x in entry["prints"] if lock - BEFORE <= x["timestamp"] <= lock and x.get("price") is not None]
    if not ps:
        return None
    yes = lambda x: float(x["price"]) if x["outcome"] == "Yes" else 1 - float(x["price"])
    usd = sum(float(x["size"] or 0) * float(x["price"]) for x in ps)
    if usd < min_usd:
        return None
    if mode == "vwap":
        w = sum(float(x["size"] or 0) for x in ps)
        return sum(float(x["size"] or 0) * yes(x) for x in ps) / w if w > 0 else None
    return yes(max(ps, key=lambda x: x["timestamp"]))


def t2_rows(d, mode, min_usd):
    """bt_t2.cmd_score's positions, with each contract at its real price; contracts without one are dropped from positions and bases."""
    D = os.path.join(HERE, "bt", d); fdoc = A.jload(os.path.join(D, "frame.json")); frame = {e["id"]: e for e in fdoc["events"]}
    man = A.jload(os.path.join(D, "manifest.json")); crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}; got = load(d)
    cov = collections.Counter()
    for ev in frame.values():
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]]); c["orig_yes"] = c["price_yes"]; e = got.get(f"{c['cid']}|{ev['lock']}")
            c["real"] = real_yes(e, ev["lock"], mode, min_usd); cov["contracts"] += 1; cov["real"] += c["real"] is not None
            cov["unreachable"] += bool(e is not None and not e["reached"] and c["real"] is None)
    priced = lambda c: dict(c, price_yes=c["real"])
    base = [(ev["id"], ev["kind"], T.cost(priced(c), yes), float(c["yes"] == yes)) for ev in frame.values() for c in ev["contracts"] if c["real"] is not None for yes in (True, False)]
    base_side = [(ev["id"], ev["kind"], yes, T.cost(priced(c), yes), float(c["yes"] == yes)) for ev in frame.values() for c in ev["contracts"] if c["real"] is not None for yes in (True, False)]
    rows = []
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(D, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{d}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"]:
                continue
            byc = {c["cid"]: c for c in ev["contracts"]}; mtype = V.market_type(ev)
            for cl, cid in L["contracts"].items():
                c = byc[cid]; ch = T.contract_chance(ev, ans, lab, cl, c)
                if ch is None:
                    continue
                lo, hi = ch; mid = (lo + hi) / 2
                for yes, want in ((True, lo), (False, 1 - hi)):
                    oc = T.cost(c, yes); orig = want > oc                                         # the original position, at the frame's price
                    orig_arm = orig and not yes and mtype != "mention" and oc >= ARM_COST and abs(mid - c["orig_yes"]) >= ARM_GAP
                    if c["real"] is None:
                        if orig:
                            rows.append({"pass": d, "dropped": True, "orig_armed": orig_arm, "side": "YES" if yes else "NO"})
                        continue
                    cc = T.cost(priced(c), yes)
                    if not want > cc:
                        if orig:
                            rows.append({"pass": d, "dropped": False, "lost_position": True, "orig_armed": orig_arm, "side": "YES" if yes else "NO"})
                        continue
                    hit = float(c["yes"] == yes)
                    bm = [h - k for (eid, kd, k, h) in base if eid != ev["id"] and kd == ev["kind"] and abs(k - cc) <= T.MATCH_BAND]
                    bs = [h - k for (eid, kd, s, k, h) in base_side if eid != ev["id"] and kd == ev["kind"] and s == yes and abs(k - cc) <= T.MATCH_BAND]
                    gap = abs(mid - c["real"])
                    rows.append({"pass": d, "event": f"{d}/{ev['id']}", "kind": ev["kind"], "mention": mtype == "mention", "mtype": mtype,
                                 "side": "YES" if yes else "NO", "cost": cc, "hit": hit, "money": hit - cc,
                                 "skill": (hit - cc) - (float(np.mean(bm)) if bm else 0.0), "skill_side": (hit - cc) - (float(np.mean(bs)) if bs else 0.0),
                                 "gap": gap, "armed": not yes and mtype != "mention" and cc >= ARM_COST and gap >= ARM_GAP, "orig_armed": orig_arm,
                                 "orig_position": orig, "subject": V.subject_of(ev), "end": V.scheduled_end(ev), "lock": ev["lock"]})
    return rows, cov


def bta_rows(mode, min_usd):
    """v19_bta.py's positions with the real price in place of the draw's."""
    crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"))}
    allc, pos, cov = [], [], collections.Counter()
    for d in BTA:
        draw = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", d, "draw.json"))["events"]}; got = load(d)
        man = A.jload(os.path.join(HERE, "bt", d, "manifest.json"))
        for sid, row in man["sessions"].items():
            rec = A.jload(os.path.join(HERE, "bt", d, "answers", f"{sid}.json"))
            if row.get("status", "ok") != "ok" or A.sha(rec["answers"]) != row["answers_sha256"]:
                continue
            ans = rec["answers"]; L = A.jload(os.path.join(HERE, "bt", d, "sessions", f"{sid}.json"))["labels"]
            for lab, l in L.items():
                ev = draw[l["event_id"]]
                if ev["month"] < "2026-04" or lab not in ans or ans[lab].get("recognised"):
                    continue
                mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
                for cl, cid in l["contracts"].items():
                    m = mk[cid]; q = real_yes(got.get(f"{cid}|{ev['price_time']}"), ev["price_time"], mode, min_usd); cov["contracts"] += 1
                    if q is None:
                        continue
                    cov["real"] += 1; y = A.yes_won(m); p = ans[lab]["p"][cl] / 100
                    for yes in (True, False):
                        cost = X.share_cost(q if yes else 1 - q, m.get("feeSchedule"), 0.01, float(m.get("tick") or 0.001)); hit = float(y == yes)
                        allc.append((f"{d}/{ev['id']}", yes, cost, hit))
                        if (p if yes else 1 - p) > cost:
                            pos.append({"pass": d, "event": f"{d}/{ev['id']}", "kind": "bta", "yes": yes, "side": "YES" if yes else "NO", "cost": cost, "hit": hit,
                                        "gap": abs(p - q), "subject": V.subject_of(ev), "end": iso_ts(ev["end"]) if ev.get("end") else ev["price_time"]})
    for r in pos:
        b = [h - k for e, s, k, h in allc if e != r["event"] and s == r["yes"] and abs(k - r["cost"]) <= 0.05]
        r["money"] = r["hit"] - r["cost"]; r["skill_side"] = r["money"] - (float(np.mean(b)) if b else 0.0)
        r["armed"] = not r["yes"] and r["cost"] >= ARM_COST and r["gap"] >= ARM_GAP
    return pos, cov


def read(rs, key, rng, unit="occ"):
    rs = [r for r in rs if r.get(key) is not None]
    if not rs:
        return None
    g = collections.defaultdict(list)
    for r in rs:
        g[r[unit]].append(r[key])
    ks = list(g); ms = [np.mean(np.concatenate([g[ks[i]] for i in rng.integers(0, len(ks), len(ks))])) for _ in range(4000)]
    lo, hi = np.percentile(ms, [2.5, 97.5])
    return {"n": len(rs), "events": len({r["event"] for r in rs}), "units": len(ks), "mean": float(np.mean([r[key] for r in rs])),
            "ci95": [float(lo), float(hi)], "lost": float(np.mean([1 - r["hit"] for r in rs]))}


def verdict(x):
    return None if not x else "shown at real prices" if x["ci95"][0] > 0 else "shown absent" if x["ci95"][1] < 0 else "direction only"


def occasions(rows):
    V.assign_occasions(rows)
    return rows


def run(mode="last", min_usd=0.0, full=True):
    rng = np.random.default_rng(SEED); t2, cov = [], {}
    for d in BT_T2 + E3:
        rs, cv = t2_rows(d, mode, min_usd); t2 += rs; cov[d] = dict(cv)
    live = [r for r in t2 if "event" in r]
    e1 = occasions([r for r in live if r["pass"] in BT_T2 and r["side"] == "NO"])
    a2 = occasions([r for r in live if r["pass"] in ("t2_pass4", "t2_pass5") and r["armed"]])
    e3b = occasions([r for r in live if r["pass"] in E3])
    s1, s2, s3 = read(e1, "skill_side", rng), read(a2, "skill_side", rng), read(e3b, "skill", rng)
    out = {"mode": mode, "min_usd": min_usd,
           "declared_1_E1": dict(s1, reading=verdict(s1)) if s1 else None,
           "declared_2_A2_passes_4_5": dict(s2, reading=verdict(s2)) if s2 else None,
           "declared_3_E3b": dict(s3, reading=verdict(s3)) if s3 else None}
    if not full:
        return out
    a2all = occasions([r for r in live if r["pass"] in BT_T2 and r["armed"]])
    bta, bcov = bta_rows(mode, min_usd); cov["BT-A (April on)"] = dict(bcov); bta = occasions(bta); bta_arm = [r for r in bta if r["armed"]]
    gone = [r for r in t2 if "event" not in r]
    out.update({
        "coverage": {d: dict(v, share_real=v.get("real", 0) / v["contracts"] if v.get("contracts") else None) for d, v in cov.items()},
        "original_positions_kept": {d: {"kept": sum(1 for r in t2 if r["pass"] == d and r.get("orig_position")),
                                        "dropped_no_real_price": sum(1 for r in gone if r["pass"] == d and r["dropped"]),
                                        "no_longer_a_position": sum(1 for r in gone if r["pass"] == d and r.get("lost_position"))} for d in BT_T2 + E3},
        "original_A2_armed_still_armed": {"orig_armed": sum(1 for r in t2 if r.get("orig_armed")),
                                          "still_armed": sum(1 for r in live if r["orig_armed"] and r["armed"]),
                                          "dropped_no_real_price": sum(1 for r in gone if r["orig_armed"] and r["dropped"])},
        "by_event": {"E1": read(e1, "skill_side", rng, "event"), "A2_passes_4_5": read(a2, "skill_side", rng, "event"), "E3b": read(e3b, "skill", rng, "event")},
        "E1_non_mention": read([r for r in e1 if not r["mention"]], "skill_side", rng), "E1_money": read(e1, "money", rng),
        "A2_passes_1_5": read(a2all, "skill_side", rng), "A2_passes_1_5_money": read(a2all, "money", rng), "A2_passes_4_5_money": read(a2, "money", rng),
        "A2_on_BT_A": read(bta_arm, "skill_side", rng), "A2_on_BT_A_money": read(bta_arm, "money", rng),
        "E1_by_kind": {k: read([r for r in e1 if r["kind"] == k], "skill_side", rng) for k in sorted({r["kind"] for r in e1})},
        "A2_passes_1_5_by_kind": {k: read([r for r in a2all if r["kind"] == k], "skill_side", rng) for k in sorted({r["kind"] for r in a2all})},
        "E1_pick_the_winner_vs_rest": {"partition": read([r for r in e1 if r["kind"] == "partition"], "skill_side", rng),
                                       "rest": read([r for r in e1 if r["kind"] != "partition"], "skill_side", rng)},
        "A2_pick_the_winner_vs_rest": {"partition": read([r for r in a2all if r["kind"] == "partition"], "skill_side", rng),
                                       "rest": read([r for r in a2all if r["kind"] != "partition"], "skill_side", rng)},
        "E3_no_picks": read(occasions([r for r in e3b if r["side"] == "NO"]), "skill_side", rng),
        "sensitivity_vwap": run("vwap", 0.0, full=False),
        "sensitivity_min_100_usd": run("last", MIN_USD, full=False)})
    return out


def cmd_score():
    out = run(); A.jdump(out, OUT); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd_pull(sys.argv[2:] or list(BT_T2 + E3 + BTA)) if sys.argv[1] == "pull" else cmd_score()
