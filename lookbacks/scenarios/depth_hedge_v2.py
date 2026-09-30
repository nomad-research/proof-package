"""Depth-hedge test v2, equity baskets. Pre-registered in depth_hedge_v2_prereg.md before this ran.  python lookbacks/scenarios/depth_hedge_v2.py"""
import datetime as dt
import json
import urllib.request

import numpy as np

B = {"T1a": "COP EOG OXY DVN", "T1b": "XOM CVX APA FANG", "T2": "SLB HAL BKR KMI", "T3": "TS GATX KEX CFR",
     "control": "JNJ PG KO PEP", "tankers": "STNG DHT INSW TNK", "defence": "LMT NOC GD HII"}
B = {k: v.split() for k, v in B.items()}
PAIRS = {"T1a+T1b": "T1b", "T1a+T2": "T2", "T1a+T3": "T3", "T1a+control": "control", "T1a+tankers*": "tankers", "T1a+defence*": "defence"}


def bars(sym, start="2018-12-01", end="2026-01-05"):
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
    if not ("2019-01-02" <= b <= "2025-12-30") or ("2020-03-01" <= b <= "2020-07-31") or b <= skip or b not in di:
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
print(f"\n{'pair':<15}{'meanR':>8}{'meanF':>8}{'worstF':>8}{'CVaR25(F)':>11}{'2nd own R':>10}{'R share':>8}{'corr(F)':>8}{'P(better)':>10}{'CVaR gain':>10}")
res = {}
for name, k in PAIRS.items():
    f, r_ = pF(k), pR(k)
    diffs = []
    for _ in range(5000):
        ix = rng.integers(0, len(events), len(events))
        diffs.append(cvar(f[ix]) - cvar(base[ix]))
    gain = (cvar(f) - cvar(base)) / abs(cvar(base))
    res[k] = dict(gain=gain, p=float(np.mean(np.array(diffs) > 0)), share=R[k].mean() / R["T1b"].mean(), own=R[k].mean())
    print(f"{name:<15}{r_.mean():>8.3f}{f.mean():>8.3f}{f.min():>8.3f}{cvar(f):>11.3f}{R[k].mean():>10.3f}{res[k]['share']:>8.2f}"
          f"{np.corrcoef(F['T1a'], F[k])[0, 1]:>8.2f}{res[k]['p']:>10.2f}{gain:>+10.0%}")
print("\nverdict per tier (pre-registered rule; * = exploratory, not in the verdict):")
for t in ("T2", "T3"):
    r = res[t]
    c1, c2, c3 = r["gain"] >= 0.20 and r["p"] >= 0.80, r["own"] > 0 and r["share"] >= 0.50, r["share"] > res["control"]["share"]
    v = "SUPPORTED" if (c1 and c2 and c3) else ("DILUTED" if (c1 and not c2) else "NOT SUPPORTED")
    print(f"  {t}: downside gain {r['gain']:+.0%} (P {r['p']:.2f}) [{'ok' if c1 else 'fail'}]; own R share of T1b {r['share']:.2f} [{'ok' if c2 else 'fail'}]; "
          f"beats control's share {res['control']['share']:.2f} [{'ok' if c3 else 'fail'}] -> {v}")
