"""Post-hoc (2026-10-01, after T0): the T0 claims and picks bet at the lock under three price-only weightings.
Not registered; R20 hypothesis only. Reads t0_report.json. Output: t0_weightings.json.
Claims are bet on their "then" at the lock whether or not the "if" happened; no fees or slippage on claims (picks use all-in cost)."""
import json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "t0_report.json")))
SETS = {"tier_claims": [(c["hit"], c["q_lock"], c["round"]) for c in R["claims"] if c["kind"] == "tier"],
        "contract_claims": [(c["hit"], c["q_lock"], c["round"]) for c in R["claims"] if c["kind"] == "contract"],
        "picks": [(p["hit"], p["cost"], p["round"]) for p in R["picks"]]}
WEIGHTS = {"equal_shares": lambda q: np.ones_like(q), "equal_variance": lambda q: 1 / np.sqrt(q * (1 - q)), "equal_stake": lambda q: 1 / q}
rng = np.random.default_rng(20261001)

def ros(h, q, w): return float(np.sum(w * (h - q)) / np.sum(w * q))   # return on total money staked

out = {}
for name, s in SETS.items():
    h = np.array([x[0] for x in s], float); q = np.clip(np.array([x[1] for x in s], float), 1e-3, 1 - 1e-3)
    rounds = sorted({x[2] for x in s}); idx = {r: [i for i, x in enumerate(s) if x[2] == r] for r in rounds}
    row = {"n": len(s), "rounds": len(rounds)}
    for wn, wf in WEIGHTS.items():
        w = wf(q); boots = []
        for _ in range(4000):   # resample rounds
            ii = [i for r in rng.choice(rounds, len(rounds)) for i in idx[r]]
            boots.append(ros(h[ii], q[ii], w[ii]))
        boots = np.array(boots)
        row[wn] = {"return_on_stake": ros(h, q, w), "ci90": [float(np.quantile(boots, .05)), float(np.quantile(boots, .95))], "p_positive": float(np.mean(boots > 0))}
    top = np.argsort(-(h / q))[:3]; keep = np.setdiff1d(np.arange(len(s)), top)
    row["equal_stake_without_top3"] = ros(h[keep], q[keep], 1 / q[keep])
    out[name] = row
json.dump(out, open(os.path.join(HERE, "t0_weightings.json"), "w"), indent=1)
for k, v in out.items():
    print(k, v["n"], v["rounds"], {wn: (round(v[wn]["return_on_stake"], 3), [round(x, 2) for x in v[wn]["ci90"]], round(v[wn]["p_positive"], 2)) for wn in WEIGHTS}, "stake w/o top3", round(v["equal_stake_without_top3"], 3))
