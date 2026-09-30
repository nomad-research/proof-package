"""V1 pilot (not a round; nothing here counts). One closed event pair, builder-authored, to test arithmetic and the data path.
Primary: Fed April decision (event 75478), long YES '25 bps decrease'. Hedge menu: Bitcoin 'hit' ladder for April (event 334550), long YES or NO.
Lock 2026-04-08 12:00 UTC. Thesis (written before prices or outcomes were fetched): the primary fails if the Fed does not cut; if it does not cut, Bitcoin touches a level below
its lock-time median dip level; a 50+ bp cut is not reachable. Disclosure: the builder had seen the April ladder's final outcomes before writing the script."""
import datetime, json, random, urllib.request
import numpy as np
from scipy.optimize import linprog

H = {"User-Agent": "Mozilla/5.0"}
g = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read())
LOCK = int(datetime.datetime(2026, 4, 8, 12, tzinfo=datetime.timezone.utc).timestamp())
SLIP, P_BUDGET, H_BUDGET, NCAP = 0.01, 60.0, 40.0, 6
FED = g("https://gamma-api.polymarket.com/events/75478")["markets"]
BTC = g("https://gamma-api.polymarket.com/events/334550")["markets"]


def lock_price(tok):
    for fid in (60, 720):
        h = g(f"https://clob.polymarket.com/prices-history?market={tok}&startTs={LOCK - 4 * 86400}&endTs={LOCK}&fidelity={fid}")["history"]
        h = [x for x in h if x["t"] <= LOCK]
        if h:
            return h[-1]["p"], LOCK - h[-1]["t"]
    return None, None


def cost(p, rate):
    e = min(p + SLIP, 0.99)
    return e + rate * e * (1 - e)


def mk(m, side):  # side 0 = YES token, 1 = NO token
    toks = json.loads(m["clobTokenIds"]); res = json.loads(m["outcomePrices"])
    p, age = lock_price(toks[0])
    if p is None:
        return None
    p = p if side == 0 else 1 - p
    return dict(title=m["groupItemTitle"], side="YES" if side == 0 else "NO", p=p, age_h=age / 3600, c=cost(p, m["feeSchedule"]["rate"]), won=float(res[side]))


# ---- data
fed = {m["groupItemTitle"]: mk(m, 0) for m in FED}
print("Fed YES prices at lock:", {k: round(v["p"], 4) for k, v in fed.items()}, "| sum", round(sum(v["p"] for v in fed.values()), 4))
dips = sorted([m for m in BTC if m["groupItemTitle"].startswith("↓")], key=lambda m: -float(m["groupItemTitle"][2:].replace(",", "")))  # shallowest first
reach = sorted([m for m in BTC if m["groupItemTitle"].startswith("↑")], key=lambda m: float(m["groupItemTitle"][2:].replace(",", "")))
for nm, L in (("dip", dips), ("reach", reach)):
    pr = [mk(m, 0) for m in L]
    print(nm, "lock YES prices:", [(m["groupItemTitle"], None if p is None else round(p["p"], 3)) for m, p in zip(L, pr)])
    ps = [p["p"] for p in pr if p]
    print("  price ages (hours before lock):", [(m["groupItemTitle"], None if p is None else round(p["age_h"], 1)) for m, p in zip(L, pr)])
    print("  adjacent pairs that break monotonicity:", [(a, b) for a, b in zip(ps, ps[1:]) if a < b - 1e-9])
    print(f"  monotone (each strike no likelier than the shallower one): {all(a >= b - 1e-9 for a, b in zip(ps, ps[1:]))}")
# ---- states: fed outcome x (a reach strikes touched, b dip strikes touched)
FO = [m["groupItemTitle"] for m in FED]
nR, nD = len(reach), len(dips)
states = [(f, a, b) for f in FO for a in range(nR + 1) for b in range(nD + 1)]
NOCUT = {"No change", "25+ bps increase"}
dp = [mk(m, 0) for m in dips]
star = min((i for i, p in enumerate(dp) if p), key=lambda i: abs(dp[i]["p"] - 0.5))  # lock-time median dip strike (price-derived; disclosed)
print("median dip strike at lock:", dips[star]["groupItemTitle"], "price", round(dp[star]["p"], 3))
reachable = [s for s in states if s[0] != "50+ bps decrease" and not (s[0] in NOCUT and s[2] <= star)]
print(f"states {len(states)}, reachable {len(reachable)}")


def pay(kind, idx, side, s):  # contract payoff in state s
    f, a, b = s
    yes = (b > idx) if kind == "dip" else (a > idx)
    return float(yes if side == "YES" else not yes)


menu = []
for kind, L in (("dip", dips), ("reach", reach)):
    for i, m in enumerate(L):
        for sd in (0, 1):
            c = mk(m, sd)
            if c: menu.append(dict(c, kind=kind, idx=i))
print("hedge menu contracts with a lock price:", len(menu), "of", 2 * (nR + nD))
P = fed["25 bps decrease"]; P_sh = P_BUDGET / P["c"]
pP = lambda s: float(s[0] == "25 bps decrease")


def solve(cands, S, pbud):
    """max floor over S: P_sh fixed, hedge budget H_BUDGET across cands."""
    n = len(cands)
    A = np.array([[cd_pay(cd, s) for cd in cands] for s in S]); pp = np.array([P_sh * pP(s) for s in S])
    cs = np.array([cd["c"] for cd in cands])
    # net(s) = pp + A x - pbud - cs.x >= t
    res = linprog(np.r_[np.zeros(n), -1.0], A_ub=np.c_[-(A - cs), np.ones(len(S))], b_ub=pp - pbud, A_eq=None,
                  bounds=[(0, None)] * n + [(None, None)], **{})
    res2 = linprog(np.r_[np.zeros(n), -1.0], A_ub=np.vstack([np.c_[-(A - cs), np.ones(len(S))], np.r_[cs, 0.0]]), b_ub=np.r_[pp - pbud, H_BUDGET],
                   bounds=[(0, None)] * n + [(None, None)])
    return res2.x[:n], res2.x[-1]


cd_pay = lambda cd, s: pay(cd["kind"], cd["idx"], cd["side"], s)
x, t = solve(menu, reachable, P_BUDGET)
top = np.argsort(-x)[:NCAP]; sub = [menu[i] for i in top if x[i] > 1e-9]
x2, t2 = solve(sub, reachable, P_BUDGET)
print(f"\nP alone ($100): floor {-100:.1f} on reachable states; P shares {100 / P['c']:.1f} at cost {P['c']:.4f}")
print(f"C (60 on P, 40 on hedge): floor over reachable {t2:.2f} (unconstrained N {t:.2f}); hedge basket:")
for cd, xi in zip(sub, x2):
    if xi > 1e-6: print(f"   {xi:7.1f} sh  {cd['kind']} {cd['title']} {cd['side']}  p {cd['p']:.3f} cost/sh {cd['c']:.3f}")
# realised outcome: score straight from resolution
real_C = P_sh * P["won"] + sum(xi * cd["won"] for cd, xi in zip(sub, x2)) - (P_BUDGET + sum(xi * cd["c"] for cd, xi in zip(sub, x2)))
real_P = (100 / P["c"]) * P["won"] - 100
sD = min(100.0, max(0.0, -t2)); real_D = (sD / P["c"]) * P["won"] - sD
print(f"D (P scaled to equal floor): outlay {sD:.2f}, floor {-sD:.2f}")
rng = random.Random(20260930); realR = []
for _ in range(200):
    cs_ = rng.sample(menu, NCAP); xr, _ = solve(cs_, reachable, P_BUDGET)
    realR.append(P_sh * P["won"] + sum(xi * cd["won"] for cd, xi in zip(cs_, xr)) - (P_BUDGET + sum(xi * cd["c"] for cd, xi in zip(cs_, xr))))
realR = np.array(realR)
print("\nREALISED (Fed held; scored from resolved outcomes):")
print(f"  P {real_P:8.2f}   C {real_C:8.2f}   D {real_D:8.2f}   R median {np.median(realR):8.2f} (5th-95th {np.percentile(realR, 5):.2f} to {np.percentile(realR, 95):.2f}); C above R in {np.mean(real_C > realR) * 100:.0f}% of draws")
b_real = sum(1 for m in dips if json.loads(m["outcomePrices"])[0] == "1")
realised = (next(k for k, v in fed.items() if v["won"] == 1), sum(1 for m in reach if json.loads(m["outcomePrices"])[0] == "1"), b_real)
print("  realised state:", realised, "inside declared reachable set:", realised in set(reachable))
