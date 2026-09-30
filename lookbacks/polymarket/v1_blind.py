"""V1 arm B, the blind statistical hedge, as registered in V1_prereg.md section 4 (built late: after C was scored; it reads no answer beyond the primary basket).
For each round: the session's primary basket (stage 1a, unchanged); candidate hedges = the menu contracts shown to that round's session that have at least 30 daily price
points in the 60 days before the lock; each held on the side whose daily price change is negatively correlated with the basket's value change; the k most negatively
correlated (k = C's number of hedge legs, else 3; at most one per event); weights over the $40 hedge budget minimising the variance of the combined daily value change
(grid over the simplex, step 0.1). Realised payoff with the scorer's fees and slippage. No narrative, no claims. Output: v1_blind_report.json."""
import json, os, sys, math, itertools, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import numpy as np, v1_score as S, v1_packet as K
from nomad16 import exact as X
from concurrent.futures import ThreadPoolExecutor
DAY, WIN, MINPTS = 86400, 60, 30
CACHE = "/tmp/claude-0/blind_hist"; os.makedirs(CACHE, exist_ok=True)

def hist(tok, lock):
    p = os.path.join(CACHE, f"{tok[:40]}_{lock}.json")
    if os.path.exists(p): return json.load(open(p))
    # the API returns nothing for windows over about 15 days, so the full daily history is fetched and cut to the 60 days before the lock (no point after the lock is kept)
    h = K._history(f"https://clob.polymarket.com/prices-history?market={tok}&interval=max&fidelity=1440").get("history", [])
    s = {}
    for x in h:
        if lock - WIN * DAY <= x["t"] <= lock: s[str(x["t"] // DAY)] = float(x["p"])
    json.dump(s, open(p, "w")); return s

def blind(eid):
    R, d = S.load_round(eid); lock = R["lock"]
    res_p = os.path.join(S.HERE, "results", f"R{eid}.json"); C = json.load(open(res_p)) if os.path.exists(res_p) else None
    k = len(C["hedge"]) if C and C.get("status") == "scored" else 3
    basket = R["ans1a"]["primary"]["basket"]
    legs = [(R["primary"]["contracts"][b["contract"]], b["side"]) for b in basket]
    lh = [hist(c["tok_yes"], lock) for c, _ in legs]
    days = sorted(set.intersection(*[set(h) for h in lh])) if lh else []
    if len(days) < MINPTS: return {"round": eid, "status": "infeasible", "why": f"primary basket has {len(days)} common daily points"}
    bval = np.array([sum((h[t] if sd == "YES" else 1 - h[t]) for h, (_, sd) in zip(lh, legs)) for t in days])
    shown = {v["cid"] for kk, v in json.load(open(f"{d}/private_1b.json")).items() if "." in kk} if os.path.exists(f"{d}/private_1b.json") else set()
    cands = [(ev, c) for ev, v in R["menu"].items() for c in v["contracts"] if c["cid"] in shown]
    with ThreadPoolExecutor(8) as ex: hs = list(ex.map(lambda ec: hist(ec[1]["tok_yes"], lock), cands))
    scored = []
    for (ev, c), h in zip(cands, hs):
        common = [t for t in days if t in h]
        if len(common) < MINPTS: continue
        x = np.diff([h[t] for t in common]); y = np.diff([bval[days.index(t)] for t in common])
        if x.std() == 0 or y.std() == 0: continue
        r = float(np.corrcoef(x, y)[0, 1]); side = "YES" if r < 0 else "NO"
        scored.append((-abs(r), ev, c, side, h))
    if not scored: return {"round": eid, "status": "infeasible", "why": "no menu contract with 30 points"}
    scored.sort(key=lambda z: z[0]); pick, seen = [], set()
    for z in scored:
        if z[1] in seen: continue
        pick.append(z); seen.add(z[1])
        if len(pick) == k: break
    price_of = S.live_price_of(R, "/tmp/claude-0/blind_db_" + eid if os.makedirs("/tmp/claude-0/blind_db_" + eid, exist_ok=True) is None else "")
    pl, p_unit_cost, p_won = [], 0.0, 0.0
    for c, sd in legs:
        p, _ = price_of(c["tok_yes"])
        if p is None: return {"round": eid, "status": "infeasible", "why": "primary unpriced at lock"}
        pp = p if sd == "YES" else 1 - p; cost = X.share_cost(pp, c["fee"], S.SLIP, c["tick"])
        won = c["yes_won"] if sd == "YES" else not c["yes_won"]; pl.append((cost, won))
    # primary: $60 split equally over basket legs (as the scorer's p_vec: one unit of each leg), realised per $ of cost
    unit_cost = sum(cst for cst, _ in pl); unit_pay = sum(1.0 for _, w in pl if w)
    P60 = S.P_BUDGET * (unit_pay / unit_cost - 1.0); P100 = S.TOTAL * (unit_pay / unit_cost - 1.0)
    hp = []
    for _, ev, c, sd, h in pick:
        p, _ = price_of(c["tok_yes"])
        if p is None: continue
        pp = p if sd == "YES" else 1 - p; hp.append((c, sd, X.share_cost(pp, c["fee"], S.SLIP, c["tick"]), pp, h))
    if not hp: return {"round": eid, "status": "infeasible", "why": "hedge unpriced at lock"}
    # min-variance weights on the daily value change of the combined $100 book
    common = [t for t in days if all(t in z[4] for z in hp)]
    by = np.diff([bval[days.index(t)] for t in common]) * (S.P_BUDGET / unit_cost)
    hx = [np.diff([(z[4][t] if z[1] == "YES" else 1 - z[4][t]) for t in common]) / z[2] for z in hp]
    best = None
    for w in itertools.product(range(11), repeat=len(hp)):
        if sum(w) != 10: continue
        v = by + sum((wi / 10) * S.H_BUDGET * xi for wi, xi in zip(w, hx)); var = float(np.var(v))
        if best is None or var < best[0]: best = (var, w)
    w = [wi / 10 for wi in best[1]]
    H = sum(wi * S.H_BUDGET * ((1.0 if (z[0]["yes_won"] if z[1] == "YES" else not z[0]["yes_won"]) else 0.0) / z[2]) for wi, z in zip(w, hp)) - S.H_BUDGET
    out = {"round": eid, "status": "ok", "k": len(hp), "legs": [{"q": z[0]["q"], "side": z[1], "weight": wi} for wi, z in zip(w, hp)], "B": P60 + H, "P": P100, "P60": P60, "H_B": H}
    if C and C.get("status") == "scored":
        out.update(C=C["realised"]["C"], D=C["realised"]["D"], C_P=C["realised"]["P"])
    return out

if __name__ == "__main__":
    BASE = os.environ.get("BLIND_BASE", HERE)                     # v1b: BLIND_BASE=<HERE>/v1b (same frozen scorer, other packets)
    if BASE != HERE:
        S.HERE = BASE
    rf = os.path.join(BASE, "v1_rounds_live.json") if os.path.exists(os.path.join(BASE, "v1_rounds_live.json")) else os.path.join(BASE, "v1_rounds.json")
    rounds = json.load(open(rf))["rounds"]; rows = []
    for eid in rounds:
        try: r = blind(eid)
        except Exception as ex: r = {"round": eid, "status": "error", "why": repr(ex)[:200]}
        rows.append(r); print(eid, r["status"], r.get("why", ""), ("B %.1f" % r["B"]) if "B" in r else "", ("C %.1f D %.1f" % (r["C"], r["D"])) if "C" in r else "", flush=True)
    ok = [r for r in rows if r["status"] == "ok"]; both = [r for r in ok if "C" in r]
    rep = {"rounds": len(rows), "feasible": len(ok), "feasible_rule_met (>=12)": len(ok) >= 12, "rows": rows}
    if both:
        B = np.array([r["B"] for r in both]); C = np.array([r["C"] for r in both]); D = np.array([r["D"] for r in both])
        rep["paired_on_scored_rounds"] = {"n": len(both), "mean_B": float(B.mean()), "mean_C": float(C.mean()), "mean_D": float(D.mean()),
            "mean_C_minus_B": float((C - B).mean()), "ci90_C_minus_B": S.boot_ci(C - B), "mean_B_minus_D": float((B - D).mean()), "ci90_B_minus_D": S.boot_ci(B - D),
            "C_beats_B_rounds": int((C > B).sum())}
    json.dump(rep, open(os.path.join(HERE, "v1b_blind_report.json" if BASE != HERE else "v1_blind_report.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1, default=str))
