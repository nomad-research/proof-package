"""Convexity map. Pre-registered in PREREG.md before this ran.   python lookbacks/scenarios/convexity_map/run.py"""
import datetime as dt
import json
import urllib.request

import numpy as np

STK = ("AAPL MSFT AMZN GOOGL META NVDA TSLA BRK-B JPM V UNH XOM JNJ WMT MA PG HD CVX LLY ABBV MRK KO PEP AVGO COST MCD BAC TMO CSCO ACN ABT CRM ADBE DHR NKE DIS WFC TXN NEE VZ PM LIN UPS CMCSA AMD ORCL INTC "
       "RTX HON QCOM UNP LOW T AMGN IBM SPGI CAT GS BA DE BLK MS SBUX MDT GILD ADP LMT AXP CVS ISRG MDLZ TJX PLD C SYK DUK SO MO USB BKNG ZTS CB CI CL FDX EOG SLB COP OXY MPC PSX VLO KMI WMB F GM DAL UAL FCX NEM").split()
VARS = {"market": "^GSPC", "rates": "^FVX", "crude": "CL=F", "gas": "NG=F", "dollar": "DX-Y.NYB", "vol": "^VIX", "gold": "GC=F", "copper": "HG=F"}


def bars(sym, start="2015-12-01", end="2026-01-05"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read())["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]) if v is not None and v > 0 or (v is not None and sym in ("^FVX",))}


px, dropped = {}, []
for s in STK + list(VARS.values()):
    try:
        px[s] = bars(s)
        if min(px[s]) > "2016-01-15":
            dropped.append(s); del px[s]
    except Exception:
        dropped.append(s)
STK = [s for s in STK if s in px]
print("dropped:", dropped or "none", "| stocks", len(STK))
dates = sorted(set.intersection(*(set(px[s]) for s in px)))
dates = [d for d in dates if "2016-01-04" <= d <= "2025-12-31"]
M = {s: np.array([px[s][d] for d in dates]) for s in px}
ret = lambda s: M[s][1:] / M[s][:-1] - 1
dd = dates[1:]
Y = np.array([ret(s) for s in STK]).T                                   # days x stocks
X = {}
for k, s in VARS.items():
    X[k] = np.diff(M[s]) if k == "rates" else (np.diff(np.log(M[s])) if k == "vol" else ret(s))
m = X["market"]
tr = np.array([d < "2021-01-01" for d in dd]); te = ~tr


def design(x, half, control=True, kinked=False):
    xs = x[half]; cols = [np.ones(half.sum())]
    cols += [np.maximum(xs, 0), np.minimum(xs, 0)] if kinked else [xs, np.abs(xs)]
    if control:
        cols += [m[half], np.abs(m[half])]
    return np.column_stack(cols)


def ols(D, Yh):
    beta, *_ = np.linalg.lstsq(D, Yh, rcond=None)
    res = Yh - D @ beta
    XtXi = np.linalg.inv(D.T @ D)
    se = np.empty_like(beta)
    for j in range(Yh.shape[1]):
        meat = (D * (res[:, [j]] ** 2)).T @ D
        cov = XtXi @ meat @ XtXi * len(D) / (len(D) - D.shape[1])
        se[:, j] = np.sqrt(np.diag(cov))
    return beta, beta / se


def c_t(k, half, x=None):
    x = X[k] if x is None else x
    b, t = ols(design(x, half, control=(k != "market")), Y[half])
    return b[2], t[2]


rng = np.random.default_rng(0)
ctr, cte, ttr, tte = {}, {}, {}, {}
for k in VARS:
    ctr[k], ttr[k] = c_t(k, tr); cte[k], tte[k] = c_t(k, te)
allc_tr = np.concatenate([ctr[k] for k in VARS]); allc_te = np.concatenate([cte[k] for k in VARS])
# standardise c within each variable and half before correlating (the variables have different scales)
z = lambda a: (a - a.mean()) / a.std()
rho = float(np.corrcoef(np.concatenate([z(ctr[k]) for k in VARS]), np.concatenate([z(cte[k]) for k in VARS]))[0, 1])
stable = {k: int(np.sum((ttr[k] >= 3.0) & (tte[k] >= 1.65))) for k in VARS}
obs = sum(stable.values())
null = []
for _ in range(200):
    n = 0
    for k in VARS:
        a = rng.permutation(X[k][tr]); b_ = rng.permutation(X[k][te])
        xx = np.zeros(len(dd)); xx[tr] = a; xx[te] = b_
        _, t1 = c_t(k, tr, xx); _, t2 = c_t(k, te, xx)
        n += int(np.sum((t1 >= 3.0) & (t2 >= 1.65)))
    null.append(n)
p95 = float(np.percentile(null, 95))
print(f"\nPART 1: correlation of c between halves (standardised, all {len(STK) * len(VARS)} pairs) = {rho:+.3f}  (bar 0.20)")
print(f"stable convex legs by variable: {stable}   total {obs}; permutation null mean {np.mean(null):.1f}, 95th percentile {p95:.1f}")
p1 = rho >= 0.20 and obs > p95
print(f"Part 1 {'HOLDS' if p1 else 'FAILS'}")


def block_boot(y, x, n=2000, blk=20):
    L = len(y); out = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + blk) for s in rng.integers(0, L - blk + 1, size=L // blk + 1)])[:L]     # blocks never run off the end
        D = np.column_stack([np.ones(L), x[idx], np.abs(x[idx])])
        out.append(np.linalg.lstsq(D, y[idx], rcond=None)[0][2])
    return np.array(out)


print("\nPART 2: composite of two one-sided legs (chosen on train, judged on test)")
print(f"{'variable':<9}{'test c':>10}{'c 10th pct':>12}{'rank vs random pairs':>22}{'worst day':>11}{'b_up':>9}{'b_dn':>9}  supported")
sup = {}
for k in VARS:
    b, t = ols(design(X[k], tr, control=(k != "market"), kinked=True), Y[tr])
    tu, td = t[1], t[2]
    U = np.argsort(-(tu - np.abs(td)))[:4]
    Dn = [j for j in np.argsort(-(-td - np.abs(tu))) if j not in U][:4]
    def comp(Us, Ds, half): return 0.5 * Y[half][:, Us].mean(axis=1) + 0.5 * Y[half][:, Ds].mean(axis=1)
    y = comp(U, Dn, te); x = X[k][te]
    D0 = np.column_stack([np.ones(len(y)), x, np.abs(x)]); c0 = np.linalg.lstsq(D0, y, rcond=None)[0][2]
    bb = block_boot(y, x)
    rnd = []
    for _ in range(500):
        pick = rng.permutation(len(STK))[:8]
        yy = comp(pick[:4], pick[4:], te); rnd.append(np.linalg.lstsq(D0, yy, rcond=None)[0][2])
    rank = float(np.mean(c0 >= np.array(rnd)))
    Dk = np.column_stack([np.ones(len(y)), np.maximum(x, 0), np.minimum(x, 0)]); bk = np.linalg.lstsq(Dk, y, rcond=None)[0]
    ok = c0 > 0 and np.percentile(bb, 10) > 0 and rank >= 0.95
    sup[k] = ok
    print(f"{k:<9}{c0:>10.4f}{np.percentile(bb, 10):>12.4f}{rank:>22.0%}{y.min():>+11.4f}{bk[1]:>9.3f}{bk[2]:>9.3f}  {'YES' if ok else 'no'}   U={[STK[j] for j in U]} D={[STK[j] for j in Dn]}")
n_sup = sum(sup.values())
print(f"\nvariables supported: {n_sup} of 8 (need 3), Part 1 {'holds' if p1 else 'fails'}")
print("verdict (pre-registered):", "SHAPE SUPPORTED IN GENERAL" if (p1 and n_sup >= 3) else "NOT SUPPORTED IN GENERAL")

# Descriptive addition (after the verdict; not part of it): how many train-convex pairs there were, and what happened to them in the test half.
print("\nDESCRIPTIVE (post hoc, not the verdict): pairs with train t(c) >= 3, and their test-half t(c)")
tot = 0
for k in VARS:
    idx = np.where(ttr[k] >= 3.0)[0]
    tot += len(idx)
    if len(idx):
        print(f"  {k:<8} train t>=3: {len(idx):>2}   test t: mean {tte[k][idx].mean():+.2f}, share positive {np.mean(tte[k][idx] > 0):.0%}, share >= 1.65 {np.mean(tte[k][idx] >= 1.65):.0%}")
    else:
        print(f"  {k:<8} train t>=3:  0")
print(f"  total train-convex pairs {tot} of {len(STK) * len(VARS)}; under no structure about {0.0013 * len(STK) * len(VARS):.1f} would be expected at t >= 3 (one-sided normal)")
