"""Illustrative scenario: can two long legs, on different correlated theses, lower the worst case? (Rob, 2026-09-30)

NOT data. The event is shaped on a mine-collapse outage (the kind of thing round 13 was). The outcome probabilities and leg payoffs are
stated assumptions, chosen to be plausible and *not* fitted to what happened. Payoffs are per unit of premium risked (each leg is a
capped-loss long: a call spread, so the worst a leg can do is -1). Legs are priced fairly: expected payoff under the market's
probabilities is about zero, so any lift in the worst case has to come from the structure of the outcomes, not from a free lunch.
    python lookbacks/scenarios/narrative_hedge.py
"""
import numpy as np
from scipy.optimize import linprog

OUT = ["w1: partial restart within 2 weeks", "w2: restart in 2-8 weeks", "w3: over 8 weeks / force majeure"]
P_MKT = np.array([0.50, 0.30, 0.20])
LEGS = {
    "A  long non-Chile miner calls   (story: supply tightness)":  np.array([-1.0, +0.3, +2.0]),
    "B  long Chile-exposed miner     (story: overreaction, quick restart)": np.array([+0.8, -0.5, -1.0]),
    "C  long copper-ETF calls        (story: supply tightness, same as A)": np.array([-0.9, +0.3, +1.8]),
}
A, B, C = LEGS.values()


def maximin(cols, mask):
    """Weights (sum 1, >= 0) maximising the worst payoff over the outcomes in `mask`."""
    M = np.array(cols).T[mask]
    n = M.shape[1]
    c = np.r_[np.zeros(n), -1.0]
    A_ub = np.c_[-M, np.ones(len(M))]
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(len(M)), A_eq=[np.r_[np.ones(n), 0.0]], b_eq=[1.0],
                  bounds=[(0, 1)] * n + [(None, None)])
    return res.x[:n], res.x[-1]


def report(title, cols, names, mask):
    print(f"\n{title}\n  thesis set: " + ", ".join(o.split(":")[0] for o, m in zip(OUT, mask) if m))
    for n, col in zip(names, cols):
        print(f"  {n[0]} alone: worst {col[mask].min():+.2f}  best {col[mask].max():+.2f}  EV(market) {P_MKT @ col:+.2f}")
    w, worst = maximin(cols, mask)
    combo = sum(wi * c for wi, c in zip(w, cols))
    print("  maximin weights " + ", ".join(f"{n[0]}={wi:.2f}" for n, wi in zip(names, w)) +
          f" -> worst {worst:+.2f}  best {combo[mask].max():+.2f}  EV(market) {P_MKT @ combo:+.2f}")
    print("  payoff by outcome: " + "  ".join(f"{o.split(':')[0]} {v:+.2f}" for o, v in zip(OUT, combo)))
    return w, worst


names = list(LEGS)
all3, in2 = np.array([1, 1, 1], bool), np.array([1, 1, 0], bool)
report("1a. Two theses that diverge across outcomes (A + B), nothing excluded", [A, B], names[:2], all3)
w, _ = report("1b. Same legs; an anchor excludes w3 (a documented partial-restart filing and a rebuild bound)", [A, B], names[:2], in2)
report("2.  Two legs on the SAME thesis (A + C): the correlated-theses claim needs the theses to diverge", [A, C], [names[0], names[2]], all3)

# 3. Robustness: the payoffs above are estimates. Perturb every cell of both legs by a lognormal-ish multiplicative error and hold the
#    nominal weights (from 1b). How often does the combined worst case beat the better single leg?
rng = np.random.default_rng(0)
for sd in (0.15, 0.30, 0.50):
    beat, worsts = 0, []
    for _ in range(20000):
        a = A * np.exp(rng.normal(0, sd, 3)); b = B * np.exp(rng.normal(0, sd, 3))
        comb = w[0] * a + w[1] * b
        worsts.append(comb[in2].min())
        beat += comb[in2].min() > max(a[in2].min(), b[in2].min())
    print(f"\n3. Payoff estimation error sd={sd:.2f} (thesis set w1,w2, nominal weights): combined worst case beats the best single leg in "
          f"{beat / 200:.0f}% of draws; median worst {np.median(worsts):+.2f}, 5th percentile {np.percentile(worsts, 5):+.2f}")

# 4. Same test with the sign of B's response to w1 wrong (the leg does not respond the way we said): the hedge is a claim about the response.
Bbad = np.array([-0.2, -0.5, -1.0])
comb = w[0] * A + w[1] * Bbad
print(f"\n4. If B does not actually pay in w1 (its w1 payoff is -0.20, not +0.80): combined worst over w1,w2 = {comb[in2].min():+.2f}")

# 5. Where the money comes from. Scenario 1b maximised the worst case inside the thesis set and left us OWNING w3, the outcome the anchor
#    excluded: a small loss where we said it happens, a gain where we said it does not. The edge (spec §7.2) is being paid for outcomes
#    OUTSIDE the thesis set, so add a leg that is short w3 (a credit spread, capped loss) and let the maximin keep the loss in the
#    excluded outcome inside a cap. Payoffs are priced fairly under the market's probabilities (EV about 0).
D = np.array([+0.30, +0.20, -1.00])         # D  short w3 exposure: collects premium unless a long outage happens; loss capped at -1
P_THESIS = np.array([0.60, 0.40, 0.00])      # what we believe once w3 is excluded
cap = 0.25                                   # the loss we allow in the excluded outcome


def constrained(cols, mask, cap):
    M = np.array(cols).T
    n = M.shape[1]
    rows = [np.r_[-M[i], 1.0] for i in np.where(mask)[0]] + [np.r_[-M[i], 0.0] for i in np.where(~mask)[0]]
    rhs = [0.0] * mask.sum() + [cap] * (~mask).sum()      # payoff in excluded outcomes >= -cap
    res = linprog(np.r_[np.zeros(n), -1.0], A_ub=rows, b_ub=rhs, A_eq=[np.r_[np.ones(n), 0.0]], b_eq=[1.0],
                  bounds=[(0, 1)] * n + [(None, None)])
    return res.x[:n], res.x[-1]


print("\n5. Adding D (short w3), thesis set w1,w2, loss allowed in the excluded outcome w3: %.2f" % cap)
print("  D alone: EV(market) %+.2f, EV(if w3 is excluded) %+.2f, payoff %s" % (P_MKT @ D, P_THESIS @ D, np.round(D, 2)))
w5, worst5 = constrained([A, B, D], in2, cap)
combo5 = w5[0] * A + w5[1] * B + w5[2] * D
print("  maximin weights A=%.2f B=%.2f D=%.2f -> worst in thesis set %+.2f" % (*w5, worst5))
print("  payoff by outcome: " + "  ".join(f"{o.split(':')[0]} {v:+.2f}" for o, v in zip(OUT, combo5)))
print("  EV(market) %+.2f, EV(if w3 is excluded) %+.2f   [1b's basket, if w3 is excluded: %+.2f]" %
      (P_MKT @ combo5, P_THESIS @ combo5, P_THESIS @ (0.5 * A + 0.5 * B)))
