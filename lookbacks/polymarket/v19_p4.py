"""P4's declared statistic (V19_DESIGN_TESTS_prereg.md §1): A2 on non-mention events, resampled by occasion, from a scored BT-T2 pass.

    python lookbacks/polymarket/v19_p4.py t2_pass4        # after bt_t2.py --pass-dir t2_pass4 score; no network
"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import v19_a2 as V

SEED = 20261012
STRICT = 1780272000                                   # 2026-06-01T00:00:00Z: the strict-gate window


def rows_of(d):
    r = A.jload(os.path.join(HERE, "bt", d, "result.json")); fr = {str(e["id"]): e for e in A.jload(os.path.join(HERE, "bt", d, "frame.json"))["events"]}
    out = []
    for p in r["rows"]["positions"]:
        e = fr[str(p["event"])]
        out.append(dict(p, event=f"{d}/{p['event']}", kind_m=V.market_type(e), mention=V.market_type(e) == "mention", lock=e["lock"],
                        month=__import__("datetime").datetime.fromtimestamp(e["lock"], __import__("datetime").timezone.utc).strftime("%Y-%m"),
                        subject=V.subject_of(e), end=V.scheduled_end(e)))
    V.assign_occasions(out)
    return out


def read(rows, key, unit, rng, level=95):
    if not rows:
        return None
    g = collections.defaultdict(list)
    for r in rows:
        g[r[unit]].append(r[key])
    ks = list(g); ms = [np.mean(np.concatenate([g[ks[i]] for i in rng.integers(0, len(ks), len(ks))])) for _ in range(4000)]
    lo, hi = np.percentile(ms, [(100 - level) / 2, 100 - (100 - level) / 2])
    return {"n": len(rows), "events": len({r["event"] for r in rows}), "units": len(ks), "mean": float(np.mean([r[key] for r in rows])),
            f"ci{level}": [float(lo), float(hi)], "p_positive": float(np.mean(np.array(ms) > 0))}


def main(d, pooled_with=()):
    rows = rows_of(d); rng = np.random.default_rng(SEED)
    no = [r for r in rows if r["side"] == "NO"]
    armed = lambda r: r["cost"] >= 0.50 and r["gap"] >= 0.20
    arm = [r for r in no if armed(r) and not r["mention"]]
    res = read(arm, "skill_side", "occ", rng)
    out = {"pass": d, "registered": dict(res, reading=("edge shown" if res["ci95"][0] > 0 else "shown absent" if res["ci95"][1] < 0 else "direction only")) if res else None,
           "by_event": read(arm, "skill_side", "event", rng), "money": read(arm, "money", "occ", rng),
           "hit_rate": float(np.mean([r["money"] + r["cost"] for r in arm])) if arm else None, "mean_cost": float(np.mean([r["cost"] for r in arm])) if arm else None,
           "blocked_no": read([r for r in no if not armed(r) and not r["mention"]], "skill_side", "occ", rng),
           "all_no_E1": read(no, "skill_side", "event", rng),
           "including_mention": read([r for r in no if armed(r)], "skill_side", "occ", rng),
           "strict_window": read([r for r in arm if r["lock"] >= STRICT], "skill_side", "occ", rng),
           "by_month": {m: read([r for r in arm if r["month"] == m], "skill_side", "occ", rng) for m in sorted({r["month"] for r in arm})},
           "by_kind": {k: read([r for r in arm if r["kind_m"] == k], "skill_side", "occ", rng) for k in sorted({r["kind_m"] for r in arm})}}
    if pooled_with:
        allr = arm + [r for p in pooled_with for r in rows_of(p) if r["side"] == "NO" and armed(r) and not r["mention"]]
        out["pooled_with_" + "+".join(pooled_with)] = read(allr, "skill_side", "occ", rng)
    A.jdump(out, os.path.join(HERE, "v19", f"p4_result_{d}.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], tuple(sys.argv[2:]))
