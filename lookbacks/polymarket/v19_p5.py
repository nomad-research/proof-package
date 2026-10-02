"""P5: the safety framework on fresh events (V19_FRAMEWORK_P5_prereg.md). No network; reads a frozen, scored-or-not BT-T2 pass and the crawl.

    python lookbacks/polymarket/v19_p5.py t2_pass5          # writes v19/p5_result_<pass>.json
"""
import collections, datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T
import v19_a2 as V

SEED, STRICT, DAY = 20261014, 1780272000, 86400


def positions(d):
    """A2-armed non-mention NO positions with the framework's inputs, exactly as v19_losers.py computes them."""
    D = os.path.join(HERE, "bt", d); fdoc = A.jload(os.path.join(D, "frame.json")); frame = {e["id"]: e for e in fdoc["events"]}
    crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}
    for ev in frame.values():
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
    base_side = [(e["id"], e["kind"], yes, T.cost(c, yes), float(c["yes"] == yes)) for e in frame.values() for c in e["contracts"] for yes in (True, False)]
    man = A.jload(os.path.join(D, "manifest.json")); rows = []
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(D, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{d}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"] or V.market_type(ev) == "mention":
                continue
            byc = {c["cid"]: c for c in ev["contracts"]}
            for cl, cid in L["contracts"].items():
                c = byc[cid]; ch = T.contract_chance(ev, ans, lab, cl, c)
                if ch is None:
                    continue
                lo, hi = ch; mid = (lo + hi) / 2; cc = T.cost(c, False)
                if not (1 - hi > cc and cc >= 0.50 and abs(mid - c["price_yes"]) >= 0.20):
                    continue
                hit = float(not c["yes"])
                bs = [h - k for (eid, kd, s, k, h) in base_side if eid != ev["id"] and kd == ev["kind"] and not s and abs(k - cc) <= T.MATCH_BAND]
                rows.append({"event": f"{d}/{ev['id']}", "skind": ev["kind"], "mtype": V.market_type(ev), "mid": mid, "cost": cc, "hit": hit, "money": hit - cc,
                             "skill": (hit - cc) - (float(np.mean(bs)) if bs else 0.0), "lock": ev["lock"], "days": (V.scheduled_end(ev) - ev["lock"]) / DAY,
                             "week": dt.datetime.fromtimestamp(ev["lock"], dt.timezone.utc).strftime("%G-W%V"), "subject": V.subject_of(ev), "end": V.scheduled_end(ev)})
    V.assign_occasions(rows)
    for r in rows:
        r["conviction"] = r["mid"] < 0.10; r["timing"] = r["days"] >= 3; r["shape"] = r["skind"] != "touch"
        r["framework"] = r["conviction"] and r["timing"] and r["shape"]; r["tier"] = 1 if r["mid"] < 0.05 else 2 if r["mid"] < 0.10 else None
    return rows


def read(rs, key, rng, unit="occ"):
    if not rs:
        return None
    g = collections.defaultdict(list)
    for r in rs:
        g[r[unit]].append(r[key])
    ks = list(g); ms = [np.mean(np.concatenate([g[ks[i]] for i in rng.integers(0, len(ks), len(ks))])) for _ in range(4000)]
    return {"n": len(rs), "events": len({r["event"] for r in rs}), "occasions": len(ks), "mean": float(np.mean([r[key] for r in rs])),
            "ci95": [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))], "loss_rate": float(np.mean([1 - r["hit"] for r in rs]))}


def diff(pas, blk, rng):
    """Mean skill of passed minus blocked, resampling occasions jointly."""
    occ = sorted({r["occ"] for r in pas + blk}); gp, gb = collections.defaultdict(list), collections.defaultdict(list)
    for r in pas:
        gp[r["occ"]].append(r["skill"])
    for r in blk:
        gb[r["occ"]].append(r["skill"])
    ds = []
    for _ in range(4000):
        s = [occ[i] for i in rng.integers(0, len(occ), len(occ))]; a = [v for o in s for v in gp[o]]; b = [v for o in s for v in gb[o]]
        if a and b:
            ds.append(np.mean(a) - np.mean(b))
    point = float(np.mean([r["skill"] for r in pas]) - np.mean([r["skill"] for r in blk])) if pas and blk else None
    return {"point": point, "ci95": [float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))] if ds else None}


def verdict(ci):
    return "edge shown" if ci[0] > 0 else "shown absent" if ci[1] < 0 else "direction only"


def paper(rs, tiered):
    by_w, by_o = collections.defaultdict(float), collections.defaultdict(float)
    for r in rs:
        stake = (50.0 if (tiered and r["tier"] == 2) else 100.0); p = stake / r["cost"] * r["money"]; by_w[r["week"]] += p; by_o[r["occ"]] += p
    staked = sum((50.0 if (tiered and r["tier"] == 2) else 100.0) for r in rs)
    return {"staked": staked, "pnl": sum(by_w.values()), "return_per_dollar": sum(by_w.values()) / staked if staked else None,
            "losing_weeks": sum(1 for v in by_w.values() if v < 0), "weeks": len(by_w), "worst_week": min(by_w.values()) if by_w else None,
            "worst_occasion": min(by_o.values()) if by_o else None}


def main(d):
    rows = positions(d); rng = np.random.default_rng(SEED)
    fw = [r for r in rows if r["framework"]]; blk = [r for r in rows if not r["framework"]]
    s1 = read(fw, "skill", rng); s2 = diff(fw, blk, rng)
    out = {"pass": d,
           "declared_1_framework_skill": dict(s1, reading=verdict(s1["ci95"])) if s1 else None,
           "declared_2_passed_minus_blocked": dict(s2, reading=verdict(s2["ci95"])) if s2["ci95"] else s2,
           "a2_all": read(rows, "skill", rng), "framework": s1, "blocked": read(blk, "skill", rng),
           "tier_1": read([r for r in fw if r["tier"] == 1], "skill", rng), "tier_2": read([r for r in fw if r["tier"] == 2], "skill", rng),
           "blocked_by_conviction_only": read([r for r in rows if not r["conviction"] and r["timing"] and r["shape"]], "skill", rng),
           "blocked_by_timing_only": read([r for r in rows if r["conviction"] and not r["timing"] and r["shape"]], "skill", rng),
           "blocked_by_shape_only": read([r for r in rows if r["conviction"] and r["timing"] and not r["shape"]], "skill", rng),
           "framework_ladder_tails": read([r for r in fw if sum(1 for x in fw if x["event"] == r["event"]) >= 5], "skill", rng),
           "framework_strict_window": read([r for r in fw if r["lock"] >= STRICT], "skill", rng),
           "paper_framework_tiered": paper(fw, True), "paper_a2": paper(rows, False)}
    A.jdump(out, os.path.join(HERE, "v19", f"p5_result_{d}.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
