"""A2 on BT-A's answers (V19_DESIGN_TESTS_prereg.md §2): the arming rule unchanged, on a different pipeline and events A2 never saw.
Positions and the matched base exactly as edge_no_check.py; both BT-A passes; months from April.

    python lookbacks/polymarket/v19_bta.py          # no network
"""
import collections, glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import numpy as np
import bt_audit as A
from nomad16 import exact as X

ARM_COST, ARM_GAP, BAND = 0.50, 0.20, 0.05
crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"))}
allc, pos = [], []
for d in ("audit", "audit_pass2"):
    draw = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", d, "draw.json"))["events"]}
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
                m = mk[cid]; q = next(c["price_yes"] for c in ev["contracts"] if c["cid"] == cid); y = A.yes_won(m); p = ans[lab]["p"][cl] / 100
                for yes in (True, False):
                    cost = X.share_cost(q if yes else 1 - q, m.get("feeSchedule"), 0.01, float(m.get("tick") or 0.001)); hit = float(y == yes)
                    allc.append((f"{d}/{ev['id']}", yes, cost, hit))
                    if (p if yes else 1 - p) > cost:
                        pos.append({"event": f"{d}/{ev['id']}", "pass": d, "month": ev["month"], "yes": yes, "cost": cost, "hit": hit, "gap": abs(p - q)})
for r in pos:
    b = [h - k for e, s, k, h in allc if e != r["event"] and s == r["yes"] and abs(k - r["cost"]) <= BAND]
    r["money"] = r["hit"] - r["cost"]; r["skill"] = r["money"] - (float(np.mean(b)) if b else 0.0)
rng = np.random.default_rng(20261012)


def read(rows, key="skill"):
    if not rows:
        return None
    g = collections.defaultdict(list)
    for r in rows:
        g[r["event"]].append(r[key])
    ks = list(g); m = [np.mean([x for i in rng.integers(0, len(ks), len(ks)) for x in g[ks[i]]]) for _ in range(4000)]
    return {"n": len(rows), "events": len(ks), "mean": float(np.mean([r[key] for r in rows])), "ci95": [float(np.quantile(m, .025)), float(np.quantile(m, .975))]}


no = [r for r in pos if not r["yes"]]
arm = [r for r in no if r["cost"] >= ARM_COST and r["gap"] >= ARM_GAP]
res = read(arm)
out = {"registered": dict(res, reading=("edge shown" if res["ci95"][0] > 0 else "shown absent" if res["ci95"][1] < 0 else "direction only")),
       "armed_money": read(arm, "money"), "all_no": read(no), "blocked_no": read([r for r in no if r not in arm]),
       "armed_by_pass": {d: read([r for r in arm if r["pass"] == d]) for d in ("audit", "audit_pass2")},
       "armed_by_month": {m: read([r for r in arm if r["month"] == m]) for m in sorted({r["month"] for r in arm})},
       "armed_hit_rate": float(np.mean([r["hit"] for r in arm])) if arm else None, "armed_mean_cost": float(np.mean([r["cost"] for r in arm])) if arm else None}
A.jdump(out, os.path.join(HERE, "v19", "bta_result.json")); print(json.dumps(out, indent=1))
