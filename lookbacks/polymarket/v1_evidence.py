"""Post-hoc evidence (written after V1 and V1b were scored; descriptive, changes no verdict). Output: v1_evidence_report.json.
1. Claim informativeness: for every claim whose antecedent happened, did the consequent hold more often than the market's lock-time price for it implied?
   (A claim that only restates what the market already priced adds nothing.)
2. Does the hedge pay when it is needed: mean realised hedge payoff H in rounds where the primary lost minus rounds where it held, with a permutation p-value.
   This replaces the registered M control, whose mean is identical to C-D by construction (a cyclic shift of hedges leaves their sum unchanged)."""
import json, os, glob, sys, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import numpy as np, v1_score as S

def claims_of(base, eid):
    S.HERE = base; R, d = S.load_round(eid); price_of = S.live_price_of(R, d)
    menu_by_label = {c["label"]: (ev, c) for ev, v in R["menu"].items() for c in v["contracts"]}
    out = []
    if not any(True for _ in (R["ans1b"].get("claims") or [])): return out
    for cl in R["ans1b"].get("claims") or []:
        i, t = cl["if"], cl["then"]
        ca = R["primary"]["contracts"].get(i["contract"]);
        if ca is None: continue
        ya = i["resolves"] == "YES"
        if "contract" in t:
            if t["contract"] not in menu_by_label: continue
            _, cb = menu_by_label[t["contract"]]; yb = t.get("resolves", "YES") == "YES"
        else:
            if t.get("event") not in R["menu"]: continue
            m = S.map_tier(R["menu"][t["event"]]["contracts"], R["menu"][t["event"]]["kind"], t["direction"], t["tier"], price_of)
            if m is None: continue
            cb, side, _ = m; yb = side == "YES"
        p, _ = price_of(cb["tok_yes"]); pa, _ = price_of(ca["tok_yes"])
        if p is None or pa is None: continue
        q_cons = p if yb else 1 - p; q_ante = pa if ya else 1 - pa
        ante = ca["yes_won"] == ya; cons = cb["yes_won"] == yb
        # placebo: every other priced menu contract of the same round (both sides), same antecedent; excess over lock price
        plac = []
        shown = {v["cid"] for k, v in json.load(open(os.path.join(d, "private_1b.json"))).items() if "." in k}
        for ev, v in R["menu"].items():
            for c in v["contracts"]:
                if c["cid"] == cb["cid"] or c["cid"] not in shown: continue
                pc, _ = price_of(c["tok_yes"])
                if pc is None: continue
                for yes in (True, False):
                    plac.append((c["yes_won"] == yes) - (pc if yes else 1 - pc))
        out.append({"round": eid, "antecedent_happened": ante, "consequent_held": cons, "q_consequent_at_lock": q_cons, "q_antecedent_at_lock": q_ante,
                    "placebo_mean_excess": float(np.mean(plac)) if plac else None, "placebo_n": len(plac)})
    return out

def main():
    rows, res = [], []
    for base, tag in ((HERE, "V1"), (os.path.join(HERE, "v1b"), "V1b")):
        for p in sorted(glob.glob(os.path.join(base, "results", "R*.json"))):
            r = json.load(open(p))
            if r.get("status") != "scored": continue
            r["study"] = tag; res.append(r)
            try: rows += [dict(c, study=tag) for c in claims_of(base, r["round_id"][1:])]
            except Exception as ex: print("claims failed", r["round_id"], repr(ex)[:120])
    rep = {"claims_total": len(rows)}
    trig = [c for c in rows if c["antecedent_happened"]]
    if trig:
        hit = np.array([c["consequent_held"] for c in trig], float); q = np.array([c["q_consequent_at_lock"] for c in trig])
        rep["claims_triggered"] = {"n": len(trig), "consequent_hit_rate": float(hit.mean()), "market_implied_rate": float(q.mean()), "excess": float(hit.mean() - q.mean()),
                                   "brier_market": float(np.mean((q - hit) ** 2))}
        rng = np.random.default_rng(0); ex = hit - q
        rep["claims_triggered"]["ci90_excess"] = [float(np.quantile([rng.choice(ex, len(ex)).mean() for _ in range(5000)], a)) for a in (0.05, 0.95)]
    SF = set(json.load(open(os.path.join(HERE, "v1b", "v1b_structural_flags.json")))["S"]) | {"199763", "287395", "481717", "606437", "627355", "680764"}
    for name, keep in (("X", lambda c: c["round"] not in SF), ("S", lambda c: c["round"] in SF)):
        t = [c for c in trig if keep(c)]
        if t:
            h = np.array([c["consequent_held"] for c in t], float); qq = np.array([c["q_consequent_at_lock"] for c in t])
            pl = [c["placebo_mean_excess"] for c in t if c["placebo_mean_excess"] is not None]
            rep[f"claims_triggered_{name}"] = {"n": len(t), "hit_rate": float(h.mean()), "market_implied": float(qq.mean()), "excess": float(h.mean() - qq.mean()),
                                               "placebo_excess_same_antecedent": float(np.mean(pl)) if pl else None}
    pl = [c["placebo_mean_excess"] for c in trig if c["placebo_mean_excess"] is not None]
    rep["claims_triggered"]["placebo_excess_same_antecedent"] = float(np.mean(pl)) if pl else None
    allq = np.array([c["q_consequent_at_lock"] for c in rows]); allh = np.array([c["consequent_held"] for c in rows], float)
    rep["claims_all"] = {"n": len(rows), "consequent_hit_rate": float(allh.mean()), "market_implied_rate": float(allq.mean()), "share_consequent_priced_above_0_8": float((allq > 0.8).mean())}
    H = np.array([r["realised"]["H"] for r in res]); F = np.array([r["primary_failed"] for r in res])
    diff = H[F].mean() - H[~F].mean(); rng = random.Random(0); perm = []
    for _ in range(10000):
        f = F.copy(); rng.shuffle(f); perm.append(H[f].mean() - H[~f].mean())
    rep["hedge_pays_when_needed"] = {"n": len(res), "n_primary_lost": int(F.sum()), "mean_H_primary_lost": float(H[F].mean()), "mean_H_primary_held": float(H[~F].mean()),
                                     "difference": float(diff), "permutation_p_one_sided": float(np.mean(np.array(perm) >= diff))}
    json.dump({"report": rep, "claims": rows}, open(os.path.join(HERE, "v1_evidence_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
main()
