"""Refiners against producers. Pre-registered in refiners_prereg.md before this ran.   [DH_WINDOW=start,end] python lookbacks/scenarios/refiners.py"""
import datetime as dt
import json
import os
import urllib.request

import numpy as np

WIN = os.environ.get("DH_WINDOW", "2019-01-02,2025-12-30").split(",")
B = {"A": "COP EOG OXY DVN", "T1b": "XOM CVX APA FANG", "REF": "VLO MPC PSX PBF"}
B = {k: v.split() for k, v in B.items()}


def bars(sym, start="2018-01-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]) if v}


px, dropped = {}, []
for s in [x for v in B.values() for x in v] + ["CL=F", "RB=F", "HO=F", "SPY"]:
    try:
        px[s] = bars(s)
        if s not in ("CL=F", "RB=F", "HO=F") and min(px[s]) > "2018-03-01":
            dropped.append(s); del px[s]
    except Exception:
        dropped.append(s)
for k in B:
    B[k] = [s for s in B[k] if s in px]
print("dropped:", dropped or "none", "| basket sizes", {k: len(v) for k, v in B.items()})
dates = sorted(set.intersection(*(set(px[s]) for s in px)))
di = {d: i for i, d in enumerate(dates)}
P = {s: np.array([px[s][d] for d in dates]) for s in px}
ret = {s: P[s][1:] / P[s][:-1] - 1 for s in P}
crack = (2 * P["RB=F"] * 42 + P["HO=F"] * 42) / 3 - P["CL=F"]
cl = px["CL=F"]; cd = sorted(cl)
events, skip = [], ""
for a, b in zip(cd, cd[1:]):
    if not (WIN[0] <= b <= WIN[1]) or ("2020-03-01" <= b <= "2020-07-31") or b <= skip or b not in di:
        continue
    if cl[b] / cl[a] - 1 >= 0.04 and di[b] + 20 < len(dates):
        events.append(di[b]); skip = dates[min(di[b] + 10, len(dates) - 1)]
print(f"events: {len(events)}")
if len(events) < 8:
    raise SystemExit("fewer than 8 events: unreadable")
wr = lambda k, a, b: np.array([np.mean([P[s][i + b] / P[s][i + a] - 1 for s in B[k]]) for i in events])
R = {k: wr(k, -1, 2) for k in B}; F = {k: wr(k, 2, 20) for k in B}
dcrack_F = np.array([crack[i + 20] - crack[i + 2] for i in events]); dcl_F = np.array([P["CL=F"][i + 20] - P["CL=F"][i + 2] for i in events])


def cvar(x, q=0.25):
    return np.sort(x)[:max(1, int(np.ceil(q * len(x))))].mean()


def beta(k, i):
    y = np.mean([ret[s][i - 252:i - 2] for s in B[k]], axis=0)
    X = np.c_[np.ones(250), ret["CL=F"][i - 252:i - 2], ret["SPY"][i - 252:i - 2]]
    return np.linalg.lstsq(X, y, rcond=None)[0][1]


bR = np.array([beta("REF", i) for i in events]); bT = np.array([beta("T1b", i) for i in events])
lam = np.clip(bR / bT, 0, 1)
pairF = lambda k: 0.5 * F["A"] + 0.5 * F[k]
pairR = lambda k: 0.5 * R["A"] + 0.5 * R[k]
baseF, baseR = pairF("T1b"), pairR("T1b")
ctrlF = 0.5 * F["A"] + 0.5 * lam * F["T1b"]
rng = np.random.default_rng(0)
d = []
for _ in range(5000):
    ix = rng.integers(0, len(events), len(events)); d.append(cvar(pairF("REF")[ix]) - cvar(baseF[ix]))
gain = (cvar(pairF("REF")) - cvar(baseF)) / abs(cvar(baseF)); pb = float(np.mean(np.array(d) > 0))
gctl = (cvar(ctrlF) - cvar(baseF)) / abs(cvar(baseF))
worst = np.argsort(F["A"])[:max(1, int(np.ceil(0.25 * len(events))))]
c_ref_crack = float(np.corrcoef(F["REF"], dcrack_F)[0, 1]); c_crack_cl = float(np.corrcoef(dcrack_F, dcl_F)[0, 1])
print(f"\ntrailing crude beta (controlling SPY): producers-B {bT.mean():.2f}, refiners {bR.mean():.2f}  (lambda for the loading-matched control {lam.mean():.2f})")
print(f"refiners: mean R {R['REF'].mean():+.3f}, mean F {F['REF'].mean():+.3f}, F in the producers' worst quarter {F['REF'][worst].mean():+.3f}, corr(F) with producers {np.corrcoef(F['A'], F['REF'])[0, 1]:+.2f}")
print(f"baseline A+T1b: CVaR25(F) {cvar(baseF):+.3f}, mean R {baseR.mean():+.3f}")
print(f"A+REF:          CVaR25(F) {cvar(pairF('REF')):+.3f}, gain {gain:+.0%} (P better {pb:.2f}), mean R {pairR('REF').mean():+.3f} ({pairR('REF').mean() / baseR.mean():.0%} of baseline)")
print(f"loading-matched control (T1b scaled by lambda, rest cash): gain {gctl:+.0%}   ->  gain beyond de-risking {100 * (gain - gctl):+.0f} points")
print(f"channel: corr(REF F, change in crack over F) {c_ref_crack:+.2f}; corr(change in crack, change in crude over F) {c_crack_cl:+.2f}; mean crack change over F {dcrack_F.mean():+.2f} $/bbl")
c = [gain >= 0.20 and pb >= 0.80, (gain - gctl) >= 0.10, c_ref_crack >= 0.30 and c_crack_cl <= -0.20, pairR("REF").mean() >= 0.60 * baseR.mean()]
print("\nverdict for this window (needs both windows): (1) downside [%s]  (2) beyond de-risking [%s]  (3) channel [%s]  (4) reaction kept [%s]  -> %s" %
      (*['ok' if x else 'fail' for x in c], "SUPPORTED" if all(c) else ("DE-RISKING ONLY" if (c[0] and not c[1]) else "NOT SUPPORTED" if not c[0] else "PARTIAL")))
