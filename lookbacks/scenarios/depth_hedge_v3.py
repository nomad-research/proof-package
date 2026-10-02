"""Depth-hedge test v3, synthetic short at depth. Pre-registered in depth_hedge_v3_prereg.md before this ran.  [DH_WINDOW=start,end] python lookbacks/scenarios/depth_hedge_v3.py"""
import datetime as dt
import json
import os
import urllib.request

import numpy as np

B = {"T1a": "COP EOG OXY DVN", "T1b": "XOM CVX APA FANG", "T3": "TS GATX KEX CFR", "T4": "DAL UAL LUV CCL", "T5": "DHI LEN HD TGT",
     "control": "JNJ PG KO PEP"}
B = {k: v.split() for k, v in B.items()}
WIN = os.environ.get("DH_WINDOW", "2019-01-02,2025-12-30").split(",")


def bars(sym, start="2018-12-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    c = r["indicators"]["adjclose"][0]["adjclose"]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], c) if v}


px, dropped = {}, []
for s in ["CL=F"] + [x for v in B.values() for x in v]:
    try:
        px[s] = bars(s)
        if s != "CL=F" and min(px[s]) > "2019-01-04":
            dropped.append(s); del px[s]
    except Exception as e:
        dropped.append(s)
for k in B:
    B[k] = [s for s in B[k] if s in px]
print("dropped symbols:", dropped or "none", "| basket sizes:", {k: len(v) for k, v in B.items()})
eq = [s for v in B.values() for s in v]
dates = sorted(set.intersection(*(set(px[s]) for s in eq)))
P = {s: np.array([px[s][d] for d in dates]) for s in eq}
di = {d: i for i, d in enumerate(dates)}
cl = px["CL=F"]; cd = sorted(cl)
events, skip = [], ""
for a, b in zip(cd, cd[1:]):
    if not (WIN[0] <= b <= WIN[1]) or ("2020-03-01" <= b <= "2020-07-31") or b <= skip or b not in di:
        continue
    if cl[b] / cl[a] - 1 >= 0.04 and di[b] + 20 < len(dates):
        events.append(di[b])
        skip = dates[min(di[b] + 10, len(dates) - 1)]
print(f"events: {len(events)}  " + ", ".join(dates[i] for i in events))


def bret(name, a, b):
    return np.array([np.mean([P[s][i + b] / P[s][i + a] - 1 for s in B[name]]) for i in events])


R = {k: bret(k, -1, 2) for k in B}
F = {k: bret(k, 2, 20) for k in B}


def cvar(x, q=0.25):
    return np.sort(x)[:max(1, int(np.ceil(q * len(x))))].mean()


rng = np.random.default_rng(0)
pF = lambda k: 0.5 * F["T1a"] + 0.5 * F[k]
pR = lambda k: 0.5 * R["T1a"] + 0.5 * R[k]
base = pF("T1b")
worst = np.argsort(F["T1a"])[:max(1, int(np.ceil(0.25 * len(events))))]
print(f"\n{'tier':<9}{'meanR':>8}{'t(R)':>7}{'%R<0':>6}{'corr(F)':>9}{'F|T1a worst':>12}{'pair CVaR':>10}{'gain':>7}{'P':>6}{'upside given up':>16}")
res = {}
for k in ("T3", "T4", "T5", "control"):
    f = pF(k)
    d = []
    for _ in range(5000):
        ix = rng.integers(0, len(events), len(events))
        d.append(cvar(f[ix]) - cvar(base[ix]))
    t = R[k].mean() / (R[k].std(ddof=1) / np.sqrt(len(events)))
    res[k] = dict(t=t, corr=np.corrcoef(F["T1a"], F[k])[0, 1], cond=F[k][worst].mean(), gain=(cvar(f) - cvar(base)) / abs(cvar(base)), p=float(np.mean(np.array(d) > 0)))
    print(f"{k:<9}{R[k].mean():>8.3f}{t:>7.2f}{np.mean(R[k] < 0):>6.0%}{res[k]['corr']:>9.2f}{res[k]['cond']:>12.3f}{cvar(f):>10.3f}{res[k]['gain']:>+7.0%}{res[k]['p']:>6.2f}"
          f"{1 - pR(k).mean() / R['T1a'].mean():>16.0%}")
print("\nsynthetic-short verdict (pre-registered; all four must hold):")
for k in ("T4", "T5"):
    r = res[k]
    c = [r["t"] <= -2, r["corr"] <= -0.30, r["cond"] > 0, r["gain"] >= 0.20 and r["p"] >= 0.80]
    print(f"  {k}: (1) t(R) {r['t']:.2f} [{'ok' if c[0] else 'fail'}]  (2) corr(F) {r['corr']:.2f} [{'ok' if c[1] else 'fail'}]  "
          f"(3) F in T1a's worst quarter {r['cond']:+.3f} [{'ok' if c[2] else 'fail'}]  (4) gain {r['gain']:+.0%}, P {r['p']:.2f} [{'ok' if c[3] else 'fail'}]  -> "
          f"{'SYNTHETIC SHORT' if all(c) else 'NOT (' + str(sum(c)) + ' of 4)'}")
