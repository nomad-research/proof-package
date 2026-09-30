"""V1 scoring (V1_prereg.md §3 steps 4 and 5, §4 arms, §5 definitions, §6 bar, A5 to A7, A14).

Stage 2, where prices are allowed (price is attentional, R6): the session's stage-1 answers are *expressed* (a tier becomes a rung by lock-time price), sized, and scored on the
resolved outcomes. Nothing here changes what a session said. Arms, all with $100 and the same fees and slippage:
  P  the primary basket alone                       C  $60 primary + $40 hedge, weights from the maximin over the declared reachable set
  D  the primary scaled to C's floor (plain de-risking)   R  $60 primary + $40 spread equally over random menu contracts (200 draws)
  M  (study level) C's hedge of the next round attached to this round's primary                 B  blind statistical hedge: not built (declared infeasible unless 12 rounds can have it)
    python lookbacks/polymarket/v1_score.py --round <event_id>     # scores packets/R<id> (answers present) into results/R<id>.json
    python lookbacks/polymarket/v1_score.py --study                # applies the bar to every results/R*.json
"""
import argparse, collections, gzip, json, math, os, random, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE))); sys.path.insert(0, HERE)
import v1_packet as K
from nomad16 import exact as X
from nomad16 import pmgraph as G

TOTAL, P_BUDGET, H_BUDGET, SLIP, NCAP = 100.0, 60.0, 40.0, 0.01, 6
TIER_TARGET = {"mild": 0.50, "moderate": 0.25, "severe": 0.10}       # V1 values, provisional (A6)
N_R_DRAWS, R_MENU_SUBSET, MAX_STATES, SEED = 200, 100, 2_000_000, 20260930
DOWN = re.compile(r"\b(below|under|less than|fewer than|dip|dips|fall|falls|drop|drops|lower)\b|\(LOW\)", re.I)
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"


def orient(q):
    """'down' if the contract's YES is a fall, dip or low; else 'up'."""
    return "down" if DOWN.search(q or "") else "up"


def strike(q):
    q = re.sub(rf"\b{MON}\s+\d{{1,2}}(,?\s*20\d\d)?", "", q or "", flags=re.I)
    m = re.search(r"\$\s?([\d,]*\.?\d+)\s?(k|m|b|million|billion|t|trillion)?", q, re.I) or re.search(r"\b(\d[\d,]*\.?\d*)\s?(k|m|b|%)?\b", q)
    if not m:
        return None
    return float(m.group(1).replace(",", "")) * {"k": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9, "t": 1e12, "trillion": 1e12}.get((m.group(2) or "").lower(), 1)


# ------------------------------------------------------------------ expression: tier -> rung
def map_tier(contracts, kind, direction, tier, price_of):
    """The rung a tier names, by lock-time YES price (A6). Returns (contract, side, q) or None. ``q`` is the probability of the wanted condition at the lock."""
    tgt = TIER_TARGET[tier]
    best = None
    for c in contracts:
        p, _ = price_of(c["tok_yes"])
        if p is None:
            continue
        if kind == "price ladder":
            want = "up" if direction == "above" else "down"
            side, q = ("YES", p) if orient(c["q"]) == want else ("NO", 1.0 - p)
        elif kind == "touch ladder":
            if orient(c["q"]) != ("up" if direction == "reach" else "down"):
                continue
            side, q = "YES", p
        elif kind == "date ladder":
            side, q = "YES", p
        else:
            return None
        key = (abs(q - tgt), c["label"])
        if best is None or key < best[0]:
            best = (key, c, side, q)
    return None if best is None else (best[1], best[2], best[3])


# ------------------------------------------------------------------ state space
def component(key, kind, cs, full, hidden=False):
    """(components, {cid: (component, predicate)}) for one event's referenced contracts: a coarsening of the event's joint outcome that keeps every payoff exact."""
    comps, preds = {}, {}
    if kind.startswith("partition"):
        other = X.GAP if (kind == "partition open" or hidden) else "__other__"     # a true open slot is a typed gap; unreferenced named slots are just coarsened
        comps[key] = [c["cid"] for c in cs] + ([] if (kind == "partition exact" and full) else [other])
        for c in cs:
            preds[c["cid"]] = (key, lambda v, cid=c["cid"]: v == cid)
        return comps, preds
    if kind == "price ladder":
        ss = sorted({strike(c["q"]) for c in cs}); idx = {s: i + 1 for i, s in enumerate(ss)}
        comps[key] = X.count_states(len(ss))
        for c in cs:
            i = idx[strike(c["q"])]
            preds[c["cid"]] = (key, (lambda v, i=i: v >= i) if orient(c["q"]) == "up" else (lambda v, i=i: v < i))
        return comps, preds
    if kind == "touch ladder":
        for side, rev in (("up", False), ("down", True)):
            grp = [c for c in cs if orient(c["q"]) == side]
            if not grp:
                continue
            ss = sorted({strike(c["q"]) for c in grp}, reverse=rev); idx = {s: i + 1 for i, s in enumerate(ss)}
            comps[f"{key}:{side}"] = X.count_states(len(ss))
            for c in grp:
                preds[c["cid"]] = (f"{key}:{side}", lambda v, i=idx[strike(c["q"])]: v >= i)
        return comps, preds
    if kind == "date ladder":
        ds = sorted({c["end"] or "" for c in cs}); idx = {d: i + 1 for i, d in enumerate(ds)}
        comps[key] = X.count_states(len(ds))                       # k = number of referenced dates that resolve NO; date i is YES iff i > k
        for c in cs:
            preds[c["cid"]] = (key, lambda v, i=idx[c["end"] or ""]: i > v)
        return comps, preds
    raise ValueError(f"no state model for {kind}")


def structure_ok(kind, cs):
    """Does the resolved data respect the structure (one winner; nested)? Returns a problem string or None."""
    yes = {c["cid"]: c["yes_won"] for c in cs}
    if kind.startswith("partition"):
        return "more than one winner" if sum(yes.values()) > 1 else None
    if kind == "price ladder":
        pts = sorted(((strike(c["q"]), yes[c["cid"]] if orient(c["q"]) == "up" else not yes[c["cid"]]) for c in cs))
        return None if all(not (b and not a) for (_, a), (_, b) in zip(pts, pts[1:])) else "not nested"
    if kind == "touch ladder":
        for side, rev in (("up", False), ("down", True)):
            pts = sorted(((strike(c["q"]), yes[c["cid"]]) for c in cs if orient(c["q"]) == side), reverse=rev)
            if not all(not (b and not a) for (_, a), (_, b) in zip(pts, pts[1:])):
                return "not nested"
        return None
    if kind == "date ladder":
        pts = sorted(((c["end"] or "", yes[c["cid"]]) for c in cs))
        return None if all(not (a and not b) for (_, a), (_, b) in zip(pts, pts[1:])) else "not nested"
    return None


# ------------------------------------------------------------------ the round
def score_round(R, price_of, rng_seed=SEED):
    """``R``: the round's inputs.
      primary: {"contracts": {label: contract}, "kind", "total": n markets, "shown": n shown}, ans1a, ans1b,
      menu: {event_label: {"kind", "contracts": [contract...], "total"}}
    A contract is {"label","cid","tok_yes","q","fee","tick","end","yes_won"}. ``price_of(token) -> (yes price or None, age hours)``. Returns the round's result."""
    out = {"round_id": R["round_id"], "flags": []}
    a1, a1b = R["ans1a"], R["ans1b"]
    if a1b.get("no_instrument") or not (a1b.get("hedges") or []):
        return dict(out, status="unscored", reason="no_instrument")
    # ---- primary legs
    pl = []
    for b in a1["primary"]["basket"]:
        c = R["primary"]["contracts"][b["contract"]]; p, _ = price_of(c["tok_yes"])
        if p is None:
            return dict(out, status="unscored", reason="primary_unpriced")
        pp = p if b["side"] == "YES" else 1.0 - p
        pl.append({"c": c, "side": b["side"], "won": c["yes_won"] if b["side"] == "YES" else not c["yes_won"], "cost": X.share_cost(pp, c["fee"], SLIP, c["tick"]), "price": pp})
    # ---- hedge legs (a contract, or a tier mapped to a rung)
    hl, tier_map, gaps = [], {}, []
    for h in a1b["hedges"]:
        if "contract" in h:
            ev = next(e for e, v in R["menu"].items() if any(c["label"] == h["contract"] for c in v["contracts"]))
            c = next(c for c in R["menu"][ev]["contracts"] if c["label"] == h["contract"]); side = h["side"]
            p, _ = price_of(c["tok_yes"])
            if p is None:
                gaps.append(f"hedge {h['contract']} unpriced"); continue
            q = p if side == "YES" else 1.0 - p
        else:
            ev = h["event"]; m = map_tier(R["menu"][ev]["contracts"], R["menu"][ev]["kind"], h["direction"], h["tier"], price_of)
            if m is None:
                gaps.append(f"hedge {ev} {h['direction']} {h['tier']}: no rung"); continue
            c, side, q = m; tier_map[ev + ":" + h["tier"] + ":" + h["direction"]] = {"rung": c["label"], "side": side, "q_lock": round(q, 4)}
        hl.append({"c": c, "event": ev, "side": side, "won": c["yes_won"] if side == "YES" else not c["yes_won"], "cost": X.share_cost(q, c["fee"], SLIP, c["tick"]), "price": q})
    out["tier_map"] = tier_map
    if gaps:
        out["flags"] += gaps
    if not hl:
        return dict(out, status="unscored", reason="no_hedge_priced")
    seen = {}
    for x in hl:
        seen.setdefault((x["c"]["cid"], x["side"]), x)
    hl = list(seen.values())
    # ---- claims -> (antecedent cid, value, consequent cid, value)
    menu_by_label = {c["label"]: (ev, c) for ev, v in R["menu"].items() for c in v["contracts"]}
    claims = []
    for cl in a1b.get("claims") or []:
        i, t = cl["if"], cl["then"]
        ca = R["primary"]["contracts"][i["contract"]]; ya = i["resolves"] == "YES"
        if "contract" in t:
            ev, cb = menu_by_label[t["contract"]]; yb = t["resolves"] == "YES"
        else:
            ev = t["event"]; m = map_tier(R["menu"][ev]["contracts"], R["menu"][ev]["kind"], t["direction"], t["tier"], price_of)
            if m is None:
                out["flags"].append(f"claim consequent {ev} {t.get('direction')} {t.get('tier')}: no rung (claim dropped)"); continue
            cb, side, _ = m; yb = side == "YES"
        claims.append((ca, ya, ev, cb, yb))
    # ---- events referenced -> state space
    refs = collections.OrderedDict()
    def ref(key, kind, c, total, shown):
        e = refs.setdefault(key, {"kind": kind, "cs": {}, "total": total, "shown": shown}); e["cs"][c["cid"]] = c
    P0 = R["primary"]
    for x in pl: ref("P", P0["kind"], x["c"], P0["total"], P0["shown"])
    for ca, _, _, _, _ in claims: ref("P", P0["kind"], ca, P0["total"], P0["shown"])
    for x in hl: ref(x["event"], R["menu"][x["event"]]["kind"], x["c"], R["menu"][x["event"]]["total"], len(R["menu"][x["event"]]["contracts"]))
    for _, _, ev, cb, _ in claims: ref(ev, R["menu"][ev]["kind"], cb, R["menu"][ev]["total"], len(R["menu"][ev]["contracts"]))
    comps, preds = {}, {}
    for key, e in refs.items():
        cs = list(e["cs"].values())
        if e["kind"].endswith("ladder") and any(strike(c["q"]) is None for c in cs) and e["kind"] != "date ladder":
            return dict(out, status="unscored", reason=f"unparseable_ladder:{key}")
        cm, pr = component(key, e["kind"], cs, full=(e["shown"] == e["total"] and len(cs) == e["shown"]), hidden=e["shown"] < e["total"])
        comps.update(cm); preds.update(pr)
        prob = structure_ok(e["kind"], list(P0["contracts"].values()) if key == "P" else R["menu"][key]["contracts"])       # every shown contract, not only the referenced ones
        if prob:
            out["flags"].append(f"structure_violation:{key}:{prob}")
    n_states = int(np.prod([len(v) for v in comps.values()]))
    if n_states > MAX_STATES:
        return dict(out, status="unscored", reason=f"too_many_states:{n_states}")
    sp = X.StateSpace(comps)
    vec = lambda c, side: sp.vec(preds[c["cid"]][0], preds[c["cid"]][1], side)
    excl = [(lambda s, ca=ca, ya=ya, cb=cb, yb=yb: preds[ca["cid"]][1](s[preds[ca["cid"]][0]]) == ya and preds[cb["cid"]][1](s[preds[cb["cid"]][0]]) != yb)
            for ca, ya, ev, cb, yb in claims]
    mask = sp.mask(excl)
    if not mask.any():
        return dict(out, status="unscored", reason="claims_exclude_every_state")
    # ---- arms
    n = len(pl)
    p_unit = sum(((1.0 / n) / x["cost"]) * vec(x["c"], x["side"]) for x in pl)          # payoff per dollar of the primary basket, equal-dollar split
    cands = [{"vec": vec(x["c"], x["side"]), "cost": x["cost"], "label": f"{x['c']['label']} {x['side']}", "won": 1.0 if x["won"] else 0.0} for x in hl]
    mm = X.maximin(p_unit, 1.0, P_BUDGET, cands, H_BUDGET, mask, ncap=NCAP)
    floor_P = float((TOTAL * p_unit[mask] - TOTAL).min())
    floor_C = mm["floor"]
    p_real_unit = sum(((1.0 / n) / x["cost"]) * (1.0 if x["won"] else 0.0) for x in pl) - 1.0     # realised payoff per dollar of the primary basket
    P_real, D_out = TOTAL * p_real_unit, X.equal_floor_outlay(p_unit, 1.0, floor_C, mask, cap=TOTAL)
    H_real = sum(w["shares"] * (w["won"] - w["cost"]) for w in mm["weights"])
    C_real = P_BUDGET * p_real_unit + H_real
    # ---- realised state inside the declared reachable set? (B1) read straight from the resolutions
    violated = [f"{ca['label']}={'YES' if ya else 'NO'} but {cb['label']} did not resolve {'YES' if yb else 'NO'}"
                for ca, ya, ev, cb, yb in claims if ca["yes_won"] == ya and cb["yes_won"] != yb]
    # ---- R: $40 spread equally over random menu contracts, same number as C's hedge legs
    rng = random.Random(f"{rng_seed}:{R['round_id']}")
    pool = [(c, sd) for v in R["menu"].values() for c in v["contracts"] for sd in ("YES", "NO")]
    pool = rng.sample(pool, min(R_MENU_SUBSET, len(pool)))
    priced = []
    for c, sd in pool:
        p, _ = price_of(c["tok_yes"])
        if p is not None:
            q = p if sd == "YES" else 1.0 - p
            priced.append((X.share_cost(q, c["fee"], SLIP, c["tick"]), c["yes_won"] if sd == "YES" else not c["yes_won"]))
    k = max(1, len(mm["weights"]) or len(hl))
    R_real = []
    if len(priced) >= k:
        for _ in range(N_R_DRAWS):
            d = rng.sample(priced, k)
            R_real.append(P_BUDGET * p_real_unit + sum((H_BUDGET / k) / cst * (1.0 if w else 0.0) for cst, w in d) - H_BUDGET)
    out.update(status="scored", lock_states=n_states, reachable_states=int(mask.sum()), claims=len(claims),
               floors={"P": floor_P, "C": floor_C, "D": float((D_out * p_unit[mask] - D_out).min())},
               lift=mm["lift"], open_slot_reachable=any(X.GAP in comps[k] and any(m and s[k] == X.GAP for m, s in zip(mask, sp.states)) for k in comps),
               hedge=[{"leg": w["label"], "shares": w["shares"], "cost": w["cost"]} for w in mm["weights"]],
               realised={"P": P_real, "C": C_real, "D": D_out * p_real_unit, "P60": P_BUDGET * p_real_unit, "H": H_real,
                         "R_median": float(np.median(R_real)) if R_real else None, "R_q05": float(np.percentile(R_real, 5)) if R_real else None,
                         "R_q95": float(np.percentile(R_real, 95)) if R_real else None, "C_above_R": float(np.mean([C_real > r for r in R_real])) if R_real else None,
                         "R_draws": len(R_real)},
               in_reachable_set=not violated, claims_violated=violated, primary_failed=bool(P_real < -0.10 * TOTAL), n_primary=n, n_hedge=len(hl))
    return out


# ------------------------------------------------------------------ study: the bar
def boot_ci(x, seed=SEED, B=4000, q=(5, 95)):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    m = [rng.choice(x, len(x)).mean() for _ in range(B)]
    return float(np.percentile(m, q[0])), float(np.percentile(m, q[1]))


def study(results):
    S = [r for r in results if r["status"] == "scored"]
    rep = {"rounds_total": len(results), "scored": len(S), "unscored": dict(collections.Counter(r["reason"] for r in results if r["status"] != "scored"))}
    n_fail = sum(r["primary_failed"] for r in S)
    rep["gates"] = {"scored_ge_20": len(S) >= 20, "primary_loss_rounds_ge_10": n_fail >= 10, "primary_loss_rounds": n_fail}
    if not S:
        return dict(rep, verdict="inconclusive", why="no scored rounds")
    C = np.array([r["realised"]["C"] for r in S]); D = np.array([r["realised"]["D"] for r in S]); P = np.array([r["realised"]["P"] for r in S])
    in_set = np.mean([r["in_reachable_set"] for r in S])
    diff = C - D; lo, hi = boot_ci(diff)
    order = sorted(range(len(S)), key=lambda i: S[i]["round_id"])
    H = [S[i]["realised"]["H"] for i in order]                                                   # each round's hedge part, realised
    M = np.array([S[order[j]]["realised"]["P60"] + H[(j + 1) % len(order)] for j in range(len(order))])
    Dm = np.array([S[i]["realised"]["D"] for i in order]); mdiff = M - Dm; mlo, mhi = boot_ci(mdiff)
    above = [r["realised"]["C_above_R"] for r in S if r["realised"]["C_above_R"] is not None]
    up = [(r["realised"]["C"] / r["realised"]["P"]) for r in S if r["realised"]["P"] > 0.10 * TOTAL]
    rep.update(B1={"in_set_share": float(in_set), "holds": bool(in_set >= 0.90)},
               B2={"mean_C_minus_D": float(diff.mean()), "ci90": [lo, hi], "holds": bool(diff.mean() > 0 and lo > 0)},
               B3={"mean_M_minus_D": float(mdiff.mean()), "ci90": [mlo, mhi], "M_null_ok": bool(mhi <= 0 or mlo <= 0 <= mhi),
                   "C_above_R_mean": float(np.mean(above)) if above else None, "C_above_R_share_ge_65": bool(above and np.mean(above) >= 0.65)},
               B4={"mean_retention": float(np.mean(up)) if up else None, "n_rounds": len(up), "holds": bool(up and np.mean(up) >= 0.5)},
               means={"P": float(P.mean()), "C": float(C.mean()), "D": float(D.mean())})
    b3 = rep["B3"]["M_null_ok"] and rep["B3"]["C_above_R_share_ge_65"]
    if not (rep["gates"]["scored_ge_20"] and rep["gates"]["primary_loss_rounds_ge_10"]):
        v, why = "inconclusive", "a gate is not met"
    elif not rep["B1"]["holds"]:
        v, why = "dead", "B1: the realised outcome was outside the declared reachable set in more than 10% of rounds"
    elif rep["B2"]["mean_C_minus_D"] <= 0:
        v, why = "dead", "B2: the constructed hedge did not beat plain de-risking at equal floor"
    elif rep["B2"]["holds"] and b3 and rep["B4"]["holds"]:
        v, why = "pass", "B1 to B4 hold: the construction is worth continuing on (not evidence of profit)"
    else:
        v, why = "inconclusive", "B1 holds and B2's mean is positive, but B2's interval, B3 or B4 does not clear"
    return dict(rep, verdict=v, why=why)


# ------------------------------------------------------------------ wiring
def _res(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def contract_of(label, priv, final, fee, tick, end, q=None):
    return {"label": label, "cid": priv["cid"], "tok_yes": priv["token_yes"], "q": q or priv.get("q"), "fee": fee, "tick": tick, "end": end, "yes_won": json.loads(final)[0] == "1"}


def load_round(eid):
    d = os.path.join(HERE, "packets", f"R{eid}")
    pool = {e["id"]: e for e in json.load(open(os.path.join(HERE, "v1_pool.json")))}; e = pool[eid]
    mk = {m["cid"]: m for m in e["markets"]}; dates = json.load(open(os.path.join(HERE, "v1_pool_market_dates.json")))
    priv1, priv2 = json.load(open(f"{d}/private_1a.json")), json.load(open(f"{d}/private_1b.json")) if os.path.exists(f"{d}/private_1b.json") else {}
    pk1 = json.load(open(f"{d}/stage1a.json")); pk2 = json.load(open(f"{d}/stage1b.json")) if os.path.exists(f"{d}/stage1b.json") else {"candidates": []}
    res = _res(os.path.join(HERE, "v1_resolutions.json.gz")); idx = {r["id"]: r for r in K.load_index()}
    R = {"round_id": f"R{eid}", "ans1a": json.load(open(f"{d}/answer_1a.json")), "ans1b": json.load(open(f"{d}/answer_1b.json")), "lock": K.lock_of(e),
         "primary": {"kind": pk1["event"]["kind"], "total": len(e["markets"]), "shown": len(pk1["event"]["contracts"]),
                     "contracts": {lab: contract_of(lab, v, mk[v["cid"]]["final"], mk[v["cid"]]["feeSchedule"], mk[v["cid"]]["tick"], (dates.get(v["cid"]) or {}).get("end")) for lab, v in priv1.items()}},
         "menu": {}}
    for c in pk2["candidates"]:
        ev_id = priv2[c["label"]]["event_id"]; cs = []
        for k in c["contracts"]:
            v = priv2[k["label"]]; r = res[v["cid"]]
            cs.append(contract_of(k["label"], v, r["final"], r["feeSchedule"], r["tick"], r["end"], v.get("q")))
        R["menu"][c["label"]] = {"kind": c["kind"], "contracts": cs, "total": len(idx[ev_id]["markets"])}
    return R, d


def live_price_of(R, d):
    from nomad16 import prices
    from nomad16.db import DB
    db = DB(os.path.join(d, "prices.db"))
    class V:
        manifest = None
        def led(self, t, w="", p=()): return db.rows(t, w, p)
    view, lock, done = V(), R["lock"], {}
    def price_of(tok):
        if tok in done:
            return done[tok]
        for fid in (60, 720):
            try:
                prices.fetch_polymarket(db, tok, lock - 5 * 86400, lock + 1, ceiling_ts=lock + 1, fidelity=fid)
            except Exception:
                continue
            p, age = prices.pm_price_at(view, tok, lock)
            if p is not None:
                done[tok] = (p, age); return done[tok]
        done[tok] = (None, None)
        return done[tok]
    return price_of


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--round"); ap.add_argument("--study", action="store_true")
    a = ap.parse_args(); rd = os.path.join(HERE, "results"); os.makedirs(rd, exist_ok=True)
    if a.round:
        R, d = load_round(a.round); out = score_round(R, live_price_of(R, d))
        json.dump(out, open(f"{rd}/R{a.round}.json", "w"), indent=1, default=str); print(json.dumps(out, indent=1, default=str)[:1800])
    if a.study:
        rs = [json.load(open(f"{rd}/{f}")) for f in sorted(os.listdir(rd)) if f.startswith("R") and f.endswith(".json")]
        rep = study(rs); json.dump(rep, open(f"{HERE}/v1_study_report.json", "w"), indent=1); print(json.dumps(rep, indent=1))
