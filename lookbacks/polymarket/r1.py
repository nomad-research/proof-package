"""R1: does averaging independent readings sharpen the reader? (registration R1_AVERAGING_prereg.md, written before any R1 session runs)

    python lookbacks/polymarket/r1.py score      # no network: BT-T2 pass 3's frame and crawl, readings A (frozen), B and C (bt/r1/t2_pass3_B, _C)

Readings B and C are fresh cold sessions on BT-T2 pass 3's own 25 prompts, run and ingested with bt_t2.py's tooling:
    python lookbacks/polymarket/bt_t2.py --pass-dir r1/t2_pass3_B --prefix bt2r1p3B publish S01 --paged
    python lookbacks/polymarket/bt_t2.py --pass-dir r1/t2_pass3_B --prefix bt2r1p3B ingest S01 <agent_id> --paged
    python lookbacks/polymarket/bt_t2.py --pass-dir r1/t2_pass3_B --prefix bt2r1p3B freeze
"""
import collections, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T

SRC = os.path.join(HERE, "bt", "t2_pass3")
READINGS = {"A": SRC, "B": os.path.join(HERE, "bt", "r1", "t2_pass3_B"), "C": os.path.join(HERE, "bt", "r1", "t2_pass3_C")}
ARM_COST, ARM_GAP, CLIP, SEED = 0.50, 0.20, 0.005, 20261003


def logit(p):
    p = min(max(p, CLIP), 1 - CLIP); return math.log(p / (1 - p))


def sig(x):
    return 1 / (1 + math.exp(-x))


def load_reading(d):
    """{(event_id, cid): (lo, hi)} and the set of recall-flagged events, from a frozen reading."""
    man = A.jload(os.path.join(d, "manifest.json")); fr = {e["id"]: e for e in A.jload(os.path.join(SRC, "frame.json"))["events"]}
    out, recalled = {}, set()
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(d, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{d}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(d, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = fr[L["event_id"]]
            if ans[lab]["recognised"]:
                recalled.add(ev["id"]); continue
            byc = {c["cid"]: c for c in ev["contracts"]}
            for cl, cid in L["contracts"].items():
                ch = T.contract_chance(ev, ans, lab, cl, byc[cid])
                if ch is not None:
                    out[(ev["id"], cid)] = ch
    return out, recalled


def average(readings):
    """Each contract's bounds averaged in log-odds across the readings that give it."""
    keys = set().union(*readings); out = {}
    for k in keys:
        chs = [r[k] for r in readings if k in r]
        out[k] = (sig(np.mean([logit(lo) for lo, _ in chs])), sig(np.mean([logit(hi) for _, hi in chs])))
    return out


def positions(view, frame, base_side, skip):
    rows = []
    for ev in frame:
        if ev["id"] in skip:
            continue
        for c in ev["contracts"]:
            ch = view.get((ev["id"], c["cid"]))
            if ch is None:
                continue
            lo, hi = ch; mid = (lo + hi) / 2
            for yes, want in ((True, lo), (False, 1 - hi)):
                cc = T.cost(c, yes)
                if want > cc:
                    hit = float(c["yes"] == yes)
                    bs = [h - k for (eid, kd, s, k, h) in base_side if eid != ev["id"] and kd == ev["kind"] and s == yes and abs(k - cc) <= T.MATCH_BAND]
                    rows.append({"event": ev["id"], "cid": c["cid"], "side": "YES" if yes else "NO", "cost": cc, "money": hit - cc, "gap": abs(mid - c["price_yes"]),
                                 "skill_side": (hit - cc) - (float(np.mean(bs)) if bs else 0.0)})
    return rows


def armed(rows):
    return [r for r in rows if r["side"] == "NO" and r["cost"] >= ARM_COST and r["gap"] >= ARM_GAP]


def log_score(view, frame, skip):
    v = []
    for ev in frame:
        if ev["id"] in skip:
            continue
        for c in ev["contracts"]:
            ch = view.get((ev["id"], c["cid"]))
            if ch is None:
                continue
            m = min(max((ch[0] + ch[1]) / 2, 1e-9), 1 - 1e-9); q = min(max(c["price_yes"], A.Q_FLOOR), 1 - A.Q_FLOOR)
            v.append({"event": ev["id"], "v": math.log(m if c["yes"] else 1 - m) - math.log(q if c["yes"] else 1 - q)})
    return v


def boot_mean(byev_list, rng, n=4000):
    """byev_list: list of dicts {event: [values]} sharing one resampling of events; returns the resampled means of each."""
    evs = sorted(set().union(*[set(d) for d in byev_list])); out = [[] for _ in byev_list]
    for _ in range(n):
        s = [evs[i] for i in rng.integers(0, len(evs), len(evs))]
        for j, d in enumerate(byev_list):
            x = [v for e in s for v in d.get(e, [])]
            out[j].append(np.mean(x) if x else np.nan)
    return [np.array(o) for o in out]


def byev(rows, key):
    d = collections.defaultdict(list)
    for r in rows:
        d[r["event"]].append(r[key])
    return d


def summary(x):
    x = x[~np.isnan(x)]
    return {"mean_resampled": float(np.mean(x)), "ci95": [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))], "p_positive": float(np.mean(x > 0))}


def cmd_score():
    fdoc = A.jload(os.path.join(SRC, "frame.json")); crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}
    frame = fdoc["events"]
    for ev in frame:                                            # outcomes are read only here
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
    base_side = [(ev["id"], ev["kind"], yes, T.cost(c, yes), float(c["yes"] == yes)) for ev in frame for c in ev["contracts"] for yes in (True, False)]
    loaded = {k: load_reading(d) for k, d in READINGS.items()}
    skip = set().union(*[r for _, r in loaded.values()])         # an event any reading flags as recalled is left out of every comparison
    views = {k: v for k, (v, _) in loaded.items()}
    views["avg(B,C)"] = average([views["B"], views["C"]]); views["avg(A,B,C)"] = average([views["A"], views["B"], views["C"]])
    pos = {k: positions(v, frame, base_side, skip) for k, v in views.items()}
    arm = {k: armed(p) for k, p in pos.items()}
    rng = np.random.default_rng(SEED)
    # the registered statistic: avg(B,C) against the mean of B alone and C alone, armed skill, paired by event
    m_avg, m_b, m_c = boot_mean([byev(arm["avg(B,C)"], "skill_side"), byev(arm["B"], "skill_side"), byev(arm["C"], "skill_side")], rng)
    diff = m_avg - (m_b + m_c) / 2
    out = {"registered": {"statistic": "armed skill, avg(B,C) minus the mean of B alone and C alone", "point":
                          float(np.mean([r["skill_side"] for r in arm["avg(B,C)"]]) - (np.mean([r["skill_side"] for r in arm["B"]]) + np.mean([r["skill_side"] for r in arm["C"]])) / 2),
                          **summary(diff)}}
    d = summary(diff)
    out["registered"]["reading"] = "edge shown (averaging sharpens)" if d["ci95"][0] > 0 else "shown absent (averaging blunts)" if d["ci95"][1] < 0 else "direction only"
    rng2 = np.random.default_rng(SEED + 1)
    out["readings"] = {}
    for k in ("A", "B", "C", "avg(B,C)", "avg(A,B,C)"):
        a = arm[k]; no = [r for r in pos[k] if r["side"] == "NO"]
        (ma,) = boot_mean([byev(a, "skill_side")], rng2); (mn,) = boot_mean([byev(no, "skill_side")], rng2); (ml,) = boot_mean([byev(log_score(views[k], frame, skip), "v")], rng2)
        out["readings"][k] = {"armed_positions": len(a), "armed_events": len({r["event"] for r in a}), "armed_skill": float(np.mean([r["skill_side"] for r in a])) if a else None,
                              "armed_skill_ci95": summary(ma)["ci95"], "armed_money": float(np.mean([r["money"] for r in a])) if a else None,
                              "all_no_skill": float(np.mean([r["skill_side"] for r in no])) if no else None, "all_no_ci95": summary(mn)["ci95"],
                              "log_score_vs_price": float(np.mean([x["v"] for x in log_score(views[k], frame, skip)])), "log_score_ci95": summary(ml)["ci95"]}
    ids = {k: {(r["event"], r["cid"]) for r in a} for k, a in arm.items()}
    jac = lambda x, y: len(x & y) / len(x | y) if x | y else None
    out["agreement"] = {"armed_B_and_C": jac(ids["B"], ids["C"]), "armed_A_and_B": jac(ids["A"], ids["B"]), "armed_A_and_C": jac(ids["A"], ids["C"]),
                        "events_left_out_for_recall": sorted(skip)}
    A.jdump(out, os.path.join(HERE, "bt", "r1", "result.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] != ["score"]:
        raise SystemExit(__doc__)
    cmd_score()
