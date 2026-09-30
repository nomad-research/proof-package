"""Construction: one basket per ratified ACK, maximin over the thesis scenarios (§7.3, §20.5, §20.7).

Reads prices through the segment context and never writes effects, ACKs, reachable
sets or theses. Solved deterministically with HiGHS (``scipy.optimize.linprog``).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import linprog
from scipy.stats import norm as _N

from . import config
from .instruments import LINEAR, OPTION, unit_cost
from .stories import horizon, s_perp
from .util import ts

TIDE_STATES = (("down", -1), ("flat", 0), ("up", 1))


def bs(S, K, T, vol, r, kind):
    if T <= 0 or vol <= 0:
        return max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    d2 = d1 - vol * math.sqrt(T)
    if kind == "call":
        return S * _N.cdf(d1) - K * math.exp(-r * T) * _N.cdf(d2)
    return K * math.exp(-r * T) * _N.cdf(-d2) - S * _N.cdf(-d1)


def bs_delta(S, K, T, vol, r, kind):
    if T <= 0 or vol <= 0:
        return (1.0 if S > K else 0.0) if kind == "call" else (-1.0 if S < K else 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    return _N.cdf(d1) if kind == "call" else _N.cdf(d1) - 1.0


def _positions(ctx, ack, shape, window_end, h, svecs, L, is_switch):
    """Candidate held positions (instrument, side) with per-scenario payoff bands per unit."""
    widen = float(config.get("UNKNOWN_WIDEN"))
    tide_shock = float(config.get("TIDE_SHOCK")) * ctx.tide_sd * math.sqrt(h)
    optm = config.get("OPTION_PRICING_MODEL")
    out = []
    lin_allowed = shape == "directional" and not is_switch
    for j, key in enumerate(ctx.index):
        if not lin_allowed:
            break
        inst = next(i for i in ctx.linear if i["key"] == key)
        st = ctx.stats[key]
        P, mult = st["price"], st["mult"]
        band = ctx.band(key, h)
        for side in (1, -1):
            ml = ctx.stress(key, h, side) * P * mult
            if not (ml > 0):
                continue
            pay = {}
            for w, sv in svecs.items():
                half = band * (1 + widen) ** int(sv["unknown"][j]) * P * mult
                for tn, tv in TIDE_STATES:
                    c = (sv["exp"][j] + st["beta"] * tv * tide_shock) * P * mult
                    lo, hi = c - half, c + half
                    pay[(w, tn)] = (lo, hi) if side == 1 else (-hi, -lo)
            a = {k: side * L[k]["vec"][j] * st["sigma"] * P * mult for k in L}
            a["tide"] = side * st["beta"] * ctx.tide_sd * P * mult
            out.append({"inst": key, "side": side, "kind": inst["kind"], "cap": "stress", "pay": pay,
                        "maxloss": ml, "cost": unit_cost(inst, P, st["adv"], h, side == -1),
                        "a": a, "notional": P * mult, "adv": st["adv"], "modelled": False,
                        "dated": False, "centre_idx": j})
    for inst in ctx.instruments:
        if inst["kind"] not in OPTION:
            continue
        if shape not in {"directional", "long_volatility"}:
            continue
        if inst.get("expiry") and ts(inst["expiry"]) <= ts(window_end):
            continue  # a dated instrument must outlive the ACK window
        u = inst.get("underlying")
        if u not in ctx.stats:
            continue
        j = ctx.index.index(u)
        st = ctx.stats[u]
        P, mult = st["price"], float(inst.get("multiplier") or 100.0)
        K = float(inst["strikes"][0])
        vol = float(np.std(st["raw_hist"][-int(config.get("LOADING_SESSIONS")):], ddof=1)) * math.sqrt(252)
        r = float(optm["rate"])
        T0 = max((ts(inst["expiry"]) - ts(ctx.clock)).days, 0) / 365.0
        Trem = max((ts(inst["expiry"]) - ts(window_end)).days, 0) / 365.0
        prem = bs(P, K, T0, vol, r, inst["kind"])
        if prem <= 0:
            continue
        band = ctx.band(u, h)
        pay = {}
        for w, sv in svecs.items():
            half = band * (1 + widen) ** int(sv["unknown"][j])
            for tn, tv in TIDE_STATES:
                c = sv["exp"][j] + st["beta"] * tv * tide_shock
                vals = [bs(P * (1 + x), K, Trem, vol, r, inst["kind"]) for x in (c - half, c, c + half)]
                pay[(w, tn)] = ((min(vals) - prem) * mult, (max(vals) - prem) * mult)
        d = bs_delta(P, K, T0, vol, r, inst["kind"])
        a = {k: d * L[k]["vec"][j] * st["sigma"] * P * mult for k in L}
        a["tide"] = d * st["beta"] * ctx.tide_sd * P * mult
        out.append({"inst": inst["key"], "side": 1, "kind": inst["kind"], "cap": "hard", "pay": pay,
                    "maxloss": prem * mult, "cost": unit_cost(inst, prem * mult, None, h, False),
                    "a": a, "notional": abs(d) * P * mult, "adv": None, "modelled": True,
                    "dated": True, "premium": prem * mult})
    return out


def _solve(pos, thesis_sc, excl_sc, hedge_keys, hold_keys, B, fams, zero_cost=False, centres=False):
    n = len(pos)
    if n == 0:
        return None
    A, b, Aeq, beq = [], [], [], []

    def lo(p, s):
        l, h = p["pay"][s]
        return (l + h) / 2 if centres else l
    cst = [0.0 if zero_cost else p["cost"] for p in pos]
    for s in thesis_sc:
        A.append([-lo(p, s) + cst[i] for i, p in enumerate(pos)] + [1.0])
        b.append(0.0)
    if "excluded" in fams:
        for s in excl_sc:
            A.append([-lo(p, s) + cst[i] for i, p in enumerate(pos)] + [0.0])
            b.append(float(config.get("EXCLUDED_LOSS_FRAC")) * B)
    if "hedge" in fams:
        eps = float(config.get("HEDGE_EPS"))
        for k in hedge_keys:
            A.append([p["a"].get(k, 0.0) - eps * p["notional"] for p in pos] + [0.0]); b.append(0.0)
            A.append([-p["a"].get(k, 0.0) - eps * p["notional"] for p in pos] + [0.0]); b.append(0.0)
        for k in hold_keys:
            A.append([-p["a"].get(k, 0.0) for p in pos] + [0.0]); b.append(0.0)
    if "liquidity" in fams:
        cap = float(config.get("LIQ_CAP"))
        for inst in sorted({p["inst"] for p in pos if p["adv"]}):
            A.append([1.0 if p["inst"] == inst else 0.0 for p in pos] + [0.0])
            b.append(cap * [p["adv"] for p in pos if p["inst"] == inst][0])
    Aeq.append([p["maxloss"] for p in pos] + [0.0]); beq.append(B)
    bounds = [(0, None)] * n + [(None, None)]
    c = [0.0] * n + [-1.0]
    r = linprog(c, A_ub=A or None, b_ub=b or None, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
    if r.status != 0:
        return {"feasible": False, "status": r.status, "message": r.message}
    return {"feasible": True, "z": float(-r.fun), "x": [float(v) for v in r.x[:n]]}


def build(ctx, ack: dict, reach_rows: list, thesis: list[str], svecs: dict, shp: str, Sbar,
          L: dict, classes: dict, hedge_names: list, H: np.ndarray, held_junction_keys: list,
          B: float, pre_gate_only: bool = False) -> dict:
    """One basket for one ACK. Returns the basket record (status, reason, weights, scenarios)."""
    R = [r["outcome_id"] for r in reach_rows if r["reach"] != "cut"]
    excluded = [w for w in R if w not in thesis]
    window_end = ack.get("window_to") or ack.get("due_at")
    h = horizon(ack, ctx.clock)
    rec = {"ack_id": ack["key"], "shape": shp, "horizon": h, "b_basket": B, "thesis": thesis,
           "excluded": excluded, "is_switch": bool(ack.get("is_switch")), "flags": [], "detail": {}}

    def unbuildable(reason, **detail):
        rec.update(status="unbuildable", reason=reason, weights=[], z_star=None, max_loss=0.0, scenarios=[])
        rec["detail"].update(detail)
        return rec

    if not reach_rows:
        return unbuildable("no_vocabulary")
    if shp == "mixed":
        return unbuildable("shape_mixed")
    pos = _positions(ctx, ack, shp, window_end, h, svecs, L, bool(ack.get("is_switch")))
    undated_allowed = shp == "directional" and not ack.get("is_switch")
    if not pos:
        any_opt = any(i["kind"] in OPTION for i in ctx.instruments)
        if not undated_allowed and any_opt:
            return unbuildable("timing_unexpressible")
        return unbuildable("no_instrument")
    if shp == "directional":
        nonflat = [w for w in thesis if not svecs[w]["flat"]]
        rhos, vis = [], []
        band_vol = float(np.median([ctx.band(k, h) / (ctx.stats[k]["sigma"] * math.sqrt(h)) for k in ctx.index]))
        for w in nonflat:
            S = svecs[w]["S"]
            sp = s_perp(S, H)
            rhos.append(float(np.linalg.norm(sp) / np.linalg.norm(S)) if np.linalg.norm(S) > 0 else 0.0)
            vis.append(float(np.linalg.norm(sp)))
        rec["detail"].update(rho_min=min(rhos) if rhos else None, s_perp_min=min(vis) if vis else None,
                             residual_noise_band=band_vol)
        if not rhos or min(rhos) < float(config.get("RHO_MIN")):
            return unbuildable("rho_too_small")
        if min(vis) < float(config.get("VIS_K")) * band_vol:
            return unbuildable("below_visibility")
    if B <= 0:
        return unbuildable("budget_exhausted")
    if pre_gate_only:
        rec["status"] = "passes_pre_gates"
        return rec
    thesis_sc = [(w, t) for w in thesis for t, _ in TIDE_STATES]
    excl_sc = [(w, t) for w in excluded for t, _ in TIDE_STATES]
    hedge_keys = [k for k in hedge_names if k in L or k == "tide"]
    hold_keys = [k for k, c in classes.items() if c["class"] == "adjacent"] + held_junction_keys \
        if shp == "directional" else []
    for p in pos:  # junction node stories enter through their constructed vectors
        for name in list(hedge_names) + list(held_junction_keys):
            if name.startswith("node:") and name not in p["a"]:
                j = p.get("centre_idx")
                vec = ctx._junction_vecs.get(name) if hasattr(ctx, "_junction_vecs") else None
                if vec is not None and j is not None:
                    st = ctx.stats[p["inst"]]
                    p["a"][name] = p["side"] * vec[j] * st["sigma"] * st["price"] * st["mult"]
                else:
                    p["a"][name] = 0.0
    hedge_keys = [k for k in hedge_names]
    full = {"liquidity", "excluded", "hedge"}
    sol = _solve(pos, thesis_sc, excl_sc, hedge_keys, hold_keys, B, full)
    if sol is None or not sol["feasible"]:
        fams = set()
        for fam, reason in (("liquidity", "liquidity"), ("excluded", "excluded_loss"), ("hedge", "story_rank_deficient")):
            fams.add(fam)
            s = _solve(pos, thesis_sc, excl_sc, hedge_keys, hold_keys, B, fams)
            if s is None or not s["feasible"]:
                return unbuildable(reason)
        return unbuildable("story_rank_deficient")
    z = sol["z"]
    edge, tol = float(config.get("EDGE_MARGIN")), float(config.get("TOLERANCE"))
    x = sol["x"]
    pay_w = {s: sum(x[i] * (pos[i]["pay"][s][0] - pos[i]["cost"]) for i in range(len(pos))) for s in thesis_sc + excl_sc}
    all_hard = all(pos[i]["cap"] == "hard" for i in range(len(pos)) if x[i] > 1e-9)
    pos_share = sum(1 for s in thesis_sc if pay_w[s] > 0) / len(thesis_sc) if thesis_sc else 0.0

    def decide(zv):
        if zv >= edge * B:
            return "built", []
        if zv >= -tol * B and all_hard and pos_share >= float(config.get("POS_SHARE_MIN")):
            return "built", ["capped_tolerance"]
        return None, []

    status, flags = decide(z)
    rec["z_star"] = z
    if status is None:
        # post-solve ladder for a feasible programme below the thresholds
        M = np.array([[(p["pay"][s][0] + p["pay"][s][1]) / 2 for s in thesis_sc] for p in pos])
        opposite = False
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                if np.std(M[i]) > 0 and np.std(M[j]) > 0 and np.corrcoef(M[i], M[j])[0, 1] < 0:
                    opposite = True
                    break
            if opposite:
                break
        modelled = any(pos[i]["modelled"] for i in range(len(pos))) and all(
            p["modelled"] for p in pos)
        reason = None
        if not opposite:
            reason = "no_opposite"
        else:
            s0 = _solve(pos, thesis_sc, excl_sc, hedge_keys, hold_keys, B, full, zero_cost=True)
            if s0 and s0["feasible"] and s0["z"] >= edge * B:
                reason = "costs"
            else:
                s1 = _solve(pos, thesis_sc, excl_sc, hedge_keys, hold_keys, B, full, centres=True)
                if s1 and s1["feasible"] and s1["z"] >= edge * B:
                    reason = "bands_too_wide"
                else:
                    reason = "no_edge"
        if modelled and not ctx.round.get("live") and reason in {"no_edge", "costs"}:
            reason = "modelled_prices"
        rec.update(status="unbuildable", reason=reason, weights=[], max_loss=0.0, scenarios=[])
        rec["detail"]["z_star_if_committed"] = z
        return rec
    weights = []
    for i, p in enumerate(pos):
        if x[i] <= 1e-9:
            continue
        weights.append({"instrument_id": p["inst"], "side": p["side"], "qty": x[i],
                        "w_long": x[i] if p["side"] == 1 else 0.0, "w_short": x[i] if p["side"] == -1 else 0.0,
                        "max_loss_contribution": x[i] * p["maxloss"], "cap": p["cap"], "kind": p["kind"],
                        "modelled": p["modelled"], "unit_cost": p["cost"],
                        "entry_price_model": p.get("premium"),
                        "loadings": {k: v for k, v in p["a"].items()}})
    scen = []
    for (w, t) in thesis_sc + excl_sc:
        scen.append({"scenario_id": f"{w}|{t}", "outcome_id": w, "in_thesis": w in thesis, "tide_state": t,
                     "payoffs": {pos[i]["inst"] + (":S" if pos[i]["side"] < 0 else ""): list(pos[i]["pay"][(w, t)])
                                 for i in range(len(pos)) if x[i] > 1e-9},
                     "payoff_worst": pay_w[(w, t)]})
    adopt = float(config.get("ADOPT_MOVE"))
    upside = {k: sum(wt["qty"] * wt["loadings"].get(k, 0.0) for wt in weights) * adopt * math.sqrt(h)
              for k, c in classes.items() if c["class"] == "adjacent"}
    rec.update(status="built", reason=None, weights=weights, max_loss=sum(w["max_loss_contribution"] for w in weights),
               scenarios=scen, flags=flags, upside_if_adopted=upside)
    return rec


def build_exact(ack: dict, thesis: list[str], primary: dict, cands: list[dict], space, mask, B: float, p_frac: float = 0.6, ncap: int = 6) -> dict:
    """The exact-payoff branch (Polymarket frame; V1 pre-registration): a basket of event contracts whose payoff in every state is arithmetic.

    ``primary`` and each of ``cands`` carry ``instrument_id``, ``vec`` (payoff per joint state of ``space``) and ``cost`` (all-in per share, from
    ``exact.share_cost``). The primary keeps ``p_frac`` of the basket budget ``B``; the rest is allocated to maximise the worst payoff over the reachable
    states ``mask`` (a thesis's declared claims that some combinations cannot occur). Long only: a NO position is a separate instrument. Returns the same record
    shape as ``build``; ``z_star`` is the floor over the reachable set, and the floor is only as honest as the claim that produced ``mask`` (V1 tests that).
    An open slot (a winner that is none of the named contracts) that is reachable and unheld is a typed gap and is flagged, never a zero.
    """
    from . import exact as X
    rec = {"ack_id": ack["key"], "shape": "exact", "horizon": None, "b_basket": B, "thesis": thesis, "excluded": [], "is_switch": False, "flags": [],
           "detail": {}, "weights": [], "z_star": None, "max_loss": 0.0, "scenarios": []}
    if B <= 0:
        rec.update(status="unbuildable", reason="budget_exhausted")
        return rec
    if not cands:
        rec.update(status="unbuildable", reason="no_instrument")
        return rec
    r = X.maximin(primary["vec"], primary["cost"], B * p_frac, cands, B * (1.0 - p_frac), mask, ncap=ncap)
    gaps = sorted({c for c in space.components if X.GAP in space.components[c] and any(m and st[c] == X.GAP for m, st in zip(mask, space.states))})
    rec["detail"].update(floor_primary_alone=r["floor_primary_alone"], lift=r["lift"], reachable_states=int(mask.sum()), states=len(space.states), open_slots_reachable=gaps)
    if gaps:
        rec["flags"].append("open_slot_reachable")
    rec["z_star"] = r["floor"]
    if r["lift"] <= 1e-9:
        rec.update(status="unbuildable", reason="no_lift")          # the claim removes no state in which the primary and every hedge lose together
        return rec
    ids = {c["instrument_id"]: c for c in cands}
    weights = [{"instrument_id": primary["instrument_id"], "side": 1, "qty": r["primary_shares"], "w_long": r["primary_shares"], "w_short": 0.0,
                "max_loss_contribution": r["primary_shares"] * primary["cost"], "cap": "hard", "kind": "event_contract", "modelled": False,
                "unit_cost": primary["cost"], "entry_price_model": None, "loadings": {}, "role": "primary"}]
    for w in r["weights"]:
        weights.append({"instrument_id": w["instrument_id"], "side": 1, "qty": w["shares"], "w_long": w["shares"], "w_short": 0.0,
                        "max_loss_contribution": w["shares"] * w["cost"], "cap": "hard", "kind": "event_contract", "modelled": False,
                        "unit_cost": w["cost"], "entry_price_model": None, "loadings": {}, "role": "hedge"})
    n = np.zeros(len(space.states))
    for w in weights:
        vec = primary["vec"] if w["role"] == "primary" else ids[w["instrument_id"]]["vec"]
        n += w["qty"] * vec
    spent = sum(w["qty"] * w["unit_cost"] for w in weights)
    net = n - spent
    scen = [{"scenario_id": "|".join(f"{k}={v}" for k, v in st.items()), "outcome_id": "|".join(str(v) for v in st.values()), "in_thesis": True, "tide_state": None,
             "payoffs": {}, "payoff_worst": float(net[i])} for i, st in enumerate(space.states) if mask[i]]
    rec.update(status="built", reason=None, weights=weights, max_loss=float(sum(w["max_loss_contribution"] for w in weights)), scenarios=scen, upside_if_adopted={})
    return rec
