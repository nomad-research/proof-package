"""Post-hoc (2026-10-01, after BT-A and BT-T2 were scored): is the no-evidence model a better NO predictor than YES predictor? Declares nothing.

Reads BT-A's frozen answers (April to September only: January to March carry recall) and prices 14 days before resolution.
1. Calibration: the model's stated chance against how often the contract came true, beside the market's price.
2. NO bets against YES bets: wherever the model's chance of the side beats that side's all-in cost, hit minus cost, and the same minus every other
   contract on the same side within 0.05 of cost (so the market's own calibration on that side is removed). 95% intervals by event.
"""
import collections, glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import bt_audit as A
from nomad16 import exact as X

crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"))}
draw = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "audit", "draw.json"))["events"]}
pts, allc, pos = [], [], []
for f in glob.glob(os.path.join(HERE, "bt", "audit", "answers", "S*.json")):
    ans = A.jload(f)["answers"]; L = A.jload(f.replace("answers", "sessions"))["labels"]
    for lab, l in L.items():
        ev = draw[l["event_id"]]
        if ev["month"] < "2026-04":
            continue
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for cl, cid in l["contracts"].items():
            m = mk[cid]; q = next(c["price_yes"] for c in ev["contracts"] if c["cid"] == cid); y = A.yes_won(m); p = ans[lab]["p"][cl] / 100
            pts.append((p, float(y), q))
            for yes in (True, False):
                cost = X.share_cost(q if yes else 1 - q, m.get("feeSchedule"), 0.01, float(m.get("tick") or 0.001)); hit = float(y == yes)
                allc.append((ev["id"], yes, cost, hit))
                if (p if yes else 1 - p) > cost:
                    pos.append((ev["id"], yes, cost, hit, abs(p - q)))
rng = np.random.default_rng(9)


def boot(rows, key):
    g = collections.defaultdict(list)
    for r in rows:
        g[r[0]].append(key(r))
    ks = list(g); m = [np.mean([x for i in rng.integers(0, len(ks), len(ks)) for x in g[ks[i]]]) for _ in range(3000)]
    return {"n": len(rows), "events": len(ks), "mean": float(np.mean([key(r) for r in rows])), "ci95": [float(np.quantile(m, .025)), float(np.quantile(m, .975))]}


def base(eid, yes, cost):
    b = [h - k for e, s, k, h in allc if e != eid and s == yes and abs(k - cost) <= 0.05]
    return float(np.mean(b)) if b else 0.0


out = {"calibration": [], "bets": {}}
for lo, hi in ((0, .05), (.05, .15), (.15, .3), (.3, .5), (.5, .7), (.7, .85), (.85, .95), (.95, 1.01)):
    b = [p for p in pts if lo <= p[0] < hi]
    if b:
        out["calibration"].append({"said": [lo, hi], "n": len(b), "mean_said": float(np.mean([x[0] for x in b])), "happened": float(np.mean([x[1] for x in b])),
                                   "market": float(np.mean([x[2] for x in b]))})
for side, name in ((False, "NO"), (True, "YES")):
    s = [r for r in pos if r[1] == side]
    out["bets"][name] = {"money": boot(s, lambda r: r[3] - r[2]), "skill_same_side_same_cost": boot(s, lambda r: (r[3] - r[2]) - base(r[0], r[1], r[2]))}
json.dump(out, open(os.path.join(HERE, "bt", "edge_no_check.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
