"""Synthetic-exposure leg test. Pre-registered in synthetic_leg_prereg.md before this ran.  [DH_WINDOW=start,end] python lookbacks/scenarios/synthetic_leg.py"""
import datetime as dt
import json
import os
import urllib.request

import numpy as np
from scipy.optimize import linprog

WIN = os.environ.get("DH_WINDOW", "2019-01-02,2025-12-30").split(",")
A_N = "COP EOG OXY DVN".split(); T1B = "XOM CVX APA FANG".split()
UNI = ("AAPL MSFT AMZN GOOGL META NVDA JPM BAC WFC GS MS BRK-B UNH JNJ PFE MRK ABBV LLY PG KO PEP WMT COST HD LOW MCD NKE DIS CMCSA VZ T LIN CAT DE HON UNP CSX UPS FDX MMM "
       "FCX NUE CF MOS DAL UAL").split()


def bars(sym, start="2018-01-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]) if v}


px, dropped = {}, []
for s in A_N + T1B + UNI + ["CL=F", "SPY"]:
    try:
        px[s] = bars(s)
        if s not in ("CL=F",) and min(px[s]) > "2018-03-01":
            dropped.append(s); del px[s]
    except Exception:
        dropped.append(s)
UNI = [s for s in UNI if s in px]
print("dropped:", dropped or "none", "| universe size", len(UNI))
dates = sorted(set.intersection(*(set(px[s]) for s in px)))
di = {d: i for i, d in enumerate(dates)}
P = {s: np.array([px[s][d] for d in dates]) for s in px}
ret = {s: P[s][1:] / P[s][:-1] - 1 for s in P}          # ret[s][k] is the return from dates[k] to dates[k+1]
cl = px["CL=F"]; cd = sorted(cl)
events, skip = [], ""
for a, b in zip(cd, cd[1:]):
    if not (WIN[0] <= b <= WIN[1]) or ("2020-03-01" <= b <= "2020-07-31") or b <= skip or b not in di:
        continue
    if cl[b] / cl[a] - 1 >= 0.04 and di[b] + 20 < len(dates):
        events.append(di[b]); skip = dates[min(di[b] + 10, len(dates) - 1)]
print(f"events: {len(events)}")


def wret(names, a, b, w=None):
    r = np.array([P[s][b] / P[s][a] - 1 for s in names])
    return r.mean() if w is None else float(np.dot(w, r))


def cvar(x, q=0.25):
    return np.sort(x)[:max(1, int(np.ceil(q * len(x))))].mean()


def reg(y, X):
    Xc = np.c_[np.ones(len(y)), X]
    coef, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return coef[1:], y - Xc @ coef


rng = np.random.default_rng(0)
# ---------------- Part A
Fa, Fb1 = [], []
bA, sA = [], []
for i in events:
    y = np.mean([ret[s][i - 252:i - 2] for s in A_N], axis=0)
    (bc, bm), res = reg(y, np.c_[ret["CL=F"][i - 252:i - 2], ret["SPY"][i - 252:i - 2]])
    bA.append(bc); sA.append(res.std())
cF = np.array([P["CL=F"][i + 20] / P["CL=F"][i + 2] - 1 for i in events])
A_F = np.array([wret(A_N, i + 2, i + 20) for i in events]); B_F = np.array([wret(T1B, i + 2, i + 20) for i in events])
A_R = np.array([wret(A_N, i - 1, i + 2) for i in events])
eA_F = A_F - np.array(bA) * cF                                   # A's fade return net of its crude part
base = cvar(0.5 * A_F + 0.5 * B_F)
print(f"\nPART A (calibration, S has A's crude loading and a residual chain with correlation rho to A's): baseline A+T1b CVaR25(F) {base:+.3f}")
first = None
for rho in (0.9, 0.5, 0.0, -0.5):
    g = []
    for _ in range(500):
        z = rng.standard_normal(len(events))
        eS = rho * eA_F + np.sqrt(1 - rho ** 2) * z * eA_F.std()
        S_F = np.array(bA) * cF + eS
        g.append((cvar(0.5 * A_F + 0.5 * S_F) - base) / abs(base))
    print(f"  rho {rho:+.1f}: pair CVaR25(F) gain vs baseline {np.mean(g):+.0%}   [{'correlated thesis' if rho == 0.9 else 'uncorrelated thesis' if rho == 0.0 else ''}]")
for rho in np.arange(0.95, -0.96, -0.05):
    g = []
    for _ in range(200):
        z = rng.standard_normal(len(events)); eS = rho * eA_F + np.sqrt(1 - rho ** 2) * z * eA_F.std()
        g.append((cvar(0.5 * A_F + 0.5 * (np.array(bA) * cF + eS)) - base) / abs(base))
    if np.mean(g) >= 0.30:
        first = rho; break
print("  first rho (from above) at which the gain reaches 30%:", None if first is None else f"{first:+.2f}")

# ---------------- Part B
Sc_F, Su_F, Sc_R, Su_R, fs, corr_c, corr_u = [], [], [], [], [], [], []
for i in events:
    X = np.c_[ret["CL=F"][i - 252:i - 2], ret["SPY"][i - 252:i - 2]]
    yA = np.mean([ret[s][i - 252:i - 2] for s in A_N], axis=0)
    (bAc, _), eA = reg(yA, X)
    b, r = [], []
    for s in UNI:
        (bc, _), e = reg(ret[s][i - 252:i - 2], X)
        b.append(bc); r.append(np.corrcoef(e, eA)[0, 1])
    b, r, n = np.array(b), np.array(r), len(UNI)
    ub = [(0, 0.15)] * n
    lp1 = linprog(-b, A_ub=[r], b_ub=[0.2], A_eq=[np.ones(n)], b_eq=[1.0], bounds=ub)
    lp2 = linprog(r, A_ub=[b, -b], b_ub=[0.05, 0.05], A_eq=[np.ones(n)], b_eq=[1.0], bounds=ub)
    wc = lp1.x if lp1.success else np.ones(n) / n
    wu = lp2.x if lp2.success else np.ones(n) / n
    fs.append(float(b @ wc) / bAc)
    Sc_F.append(wret(UNI, i + 2, i + 20, wc)); Sc_R.append(wret(UNI, i - 1, i + 2, wc))
    Su_F.append(wret(UNI, i + 2, i + 20, wu)); Su_R.append(wret(UNI, i - 1, i + 2, wu))
Sc_F, Su_F, Sc_R, Su_R = map(np.array, (Sc_F, Su_F, Sc_R, Su_R))
B_R = np.array([wret(T1B, i - 1, i + 2) for i in events])
print(f"\nPART B (real non-energy equities, long-only, unlevered)  f = achievable fraction of A's crude loading: mean {np.mean(fs):.2f}, median {np.median(fs):.2f}")
print(f"{'pair':<10}{'CVaR25(F)':>10}{'gain':>7}{'P(better)':>10}{'own R':>8}{'R share':>9}{'corr(F) w A':>13}")
res = {}
for name, SF, SR in (("A+T1b", B_F, B_R), ("A+S_corr", Sc_F, Sc_R), ("A+S_unc", Su_F, Su_R)):
    pf = 0.5 * A_F + 0.5 * SF
    d = []
    for _ in range(5000):
        ix = rng.integers(0, len(events), len(events)); d.append(cvar(pf[ix]) - cvar((0.5 * A_F + 0.5 * B_F)[ix]))
    res[name] = dict(gain=(cvar(pf) - base) / abs(base), p=float(np.mean(np.array(d) > 0)), share=SR.mean() / B_R.mean())
    print(f"{name:<10}{cvar(pf):>10.3f}{res[name]['gain']:>+7.0%}{res[name]['p']:>10.2f}{SR.mean():>8.3f}{res[name]['share']:>9.2f}{np.corrcoef(A_F, SF)[0, 1]:>13.2f}")
r = res["A+S_corr"]
c = [np.mean(fs) >= 0.5, r["gain"] >= 0.20 and r["p"] >= 0.80, r["share"] >= 0.50 and r["share"] > res["A+S_unc"]["share"]]
print(f"\nverdict for this window (pre-registered; needs both windows): f>=0.50 [{'ok' if c[0] else 'fail'}]; gain>=20% & P>=0.80 [{'ok' if c[1] else 'fail'}]; "
      f"R share>=0.50 and above S_unc's [{'ok' if c[2] else 'fail'}] -> {'SUPPORTED' if all(c) else ('DILUTED' if c[1] else 'NOT SUPPORTED')}")
