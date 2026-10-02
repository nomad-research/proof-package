"""The v19 design end to end on the backtests, and its label rules (V19_DESIGN_TESTS_prereg.md §3 and §4). Declares nothing.

    python lookbacks/polymarket/v19_design_sim.py t2 t2_pass2 t2_pass3 [t2_pass4]      # no network; writes v19/design_sim.json
"""
import collections, datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import v19_a2 as V

STAKE, WORSE, ARM_COST, ARM_GAP = 150.0, 0.02, 0.50, 0.20
DAY = 86400


def wk(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%G-W%V")


def load(passes):
    rows = []
    for d in passes:
        r = A.jload(os.path.join(HERE, "bt", d, "result.json")); fr = {str(e["id"]): e for e in A.jload(os.path.join(HERE, "bt", d, "frame.json"))["events"]}
        mention_pass = d.startswith("e3_")
        for p in r["rows"]["positions"]:
            e = fr[str(p["event"])]; kind = V.market_type(e)
            if mention_pass:
                if not (p["cost"] >= ARM_COST and p["gap"] >= ARM_GAP):      # the mention book: either side
                    continue
                book, skill = "mention", p["skill"]
            else:
                if p["side"] != "NO" or kind == "mention":
                    continue
                book, skill = "E1", p["skill_side"]
            rows.append({"pass": d, "event": f"{d}/{p['event']}", "book": book, "kind": kind, "lock": e["lock"], "week": wk(e["lock"]),
                         "cost": p["cost"], "gap": p["gap"], "money": p["money"], "skill": skill, "armed": p["cost"] >= ARM_COST and p["gap"] >= ARM_GAP,
                         "subject": V.subject_of(e), "end": V.scheduled_end(e)})
    V.assign_occasions(rows)
    return rows


def mean(xs):
    return float(np.mean(xs)) if xs else None


def book_stats(arm):
    for r in arm:
        r["pnl"] = STAKE / r["cost"] * r["money"]; r["pnl_2c"] = STAKE / (r["cost"] + WORSE) * (r["money"] - WORSE)
    weeks = sorted({r["week"] for r in arm}); wp = {w: sum(r["pnl"] for r in arm if r["week"] == w) for w in weeks}
    cum, peak, dd, path = 0.0, 0.0, 0.0, []
    for w in weeks:
        cum += wp[w]; peak = max(peak, cum); dd = min(dd, cum - peak); path.append((w, round(cum)))
    occ = collections.defaultdict(float)
    for r in arm:
        occ[r["occ"]] += r["pnl"]
    staked = STAKE * len(arm)
    return {"positions": len(arm), "events": len({r["event"] for r in arm}), "staked": staked, "pnl": sum(r["pnl"] for r in arm),
            "return_per_dollar": sum(r["pnl"] for r in arm) / staked if staked else None, "pnl_2c_worse": sum(r["pnl_2c"] for r in arm),
            "return_2c_worse": sum(r["pnl_2c"] for r in arm) / staked if staked else None, "hit_rate": mean([float(r["money"] > 0) for r in arm]),
            "weeks": len(weeks), "losing_weeks": sum(1 for w in weeks if wp[w] < 0), "worst_week": min(wp.items(), key=lambda kv: kv[1]) if wp else None,
            "best_week": max(wp.items(), key=lambda kv: kv[1]) if wp else None, "max_drawdown": dd, "cumulative_path": path,
            "worst_occasions": sorted(occ.items(), key=lambda kv: kv[1])[:5],
            "by_kind": {k: {"positions": len(rs), "return_per_dollar": sum(r["pnl"] for r in rs) / (STAKE * len(rs)), "skill": mean([r["skill"] for r in rs])}
                        for k in sorted({r["kind"] for r in arm}) for rs in [[r for r in arm if r["kind"] == k]]}}


def a3(arm, min_events):
    """Walk-forward: a kind is blocked when its armed record from positions locked at least 14 days earlier is below zero."""
    passed, blocked = [], []
    for r in sorted(arm, key=lambda r: r["lock"]):
        prior = [x for x in arm if x["kind"] == r["kind"] and x["lock"] <= r["lock"] - 14 * DAY]
        if len({x["event"] for x in prior}) >= min_events and np.mean([x["skill"] for x in prior]) < 0:
            blocked.append(r)
        else:
            passed.append(r)
    return {"passed": {"n": len(passed), "skill": mean([r["skill"] for r in passed])}, "blocked": {"n": len(blocked), "skill": mean([r["skill"] for r in blocked]),
            "kinds": dict(collections.Counter(r["kind"] for r in blocked))}}


def exposure(arm):
    occ = collections.defaultdict(float)
    for r in arm:
        occ[r["occ"]] += STAKE
    weeks = sorted({r["week"] for r in arm}); share = []
    for w in weeks:
        wk_rows = [r for r in arm if r["week"] == w]; tot = STAKE * len(wk_rows); o = collections.Counter(r["occ"] for r in wk_rows)
        share.append(max(o.values()) * STAKE / tot)
    kw = []
    for r in arm:                                                # each kind's stake over the 4 weeks ending at each lock
        win = [x for x in arm if x["kind"] == r["kind"] and r["lock"] - 28 * DAY < x["lock"] <= r["lock"]]
        kw.append((r["kind"], r["week"], STAKE * len(win), sum(x["pnl"] for x in win)))
    worst_kw = sorted(set(kw), key=lambda t: t[3])[:5]
    return {"largest_occasion_stake": max(occ.values()) if occ else None, "occasions": len(occ),
            "largest_occasion_share_of_its_week": {"median": float(np.median(share)), "max": float(max(share))} if share else None,
            "worst_kind_4_week_windows": [{"kind": k, "ending": w, "staked": s, "pnl": p} for k, w, s, p in worst_kw]}


def main(passes):
    rows = load(passes + ["e3_mentions", "e3_mentions_pass2"])
    e1 = [r for r in rows if r["book"] == "E1"]; arm = [r for r in e1 if r["armed"]]; men = [r for r in rows if r["book"] == "mention"]
    out = {"passes": passes, "E1_armed": book_stats(arm), "mention_book": book_stats(men), "whole_design": book_stats(arm + men),
           "A3_walk_forward": {"any_prior": a3(arm, 1), "at_least_5_prior_events": a3(arm, 5)},
           "A6_margin_bands": {f"{lo:.2f}-{hi:.2f}": {"n": len(rs), "skill": mean([r["skill"] for r in rs])}
                               for lo, hi in ((0.20, 0.30), (0.30, 0.40), (0.40, 1.01)) for rs in [[r for r in arm if lo <= r["gap"] < hi]]},
           "D1_proxy_near_certain_armed": "none possible: armed NOs cost 50c or more with the reader 20+ points below the lock price, so the YES price is between about 0.20 and 0.50",
           "blocked_by_A2": {"n": len([r for r in e1 if not r["armed"]]), "skill": mean([r["skill"] for r in e1 if not r["armed"]])},
           "exposure": exposure(arm)}
    A.jdump(out, os.path.join(HERE, "v19", "design_sim.json")); print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1:])
