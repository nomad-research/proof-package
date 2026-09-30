"""Depth-hedge test. Pre-registered in depth_hedge_prereg.md before this ran.   python lookbacks/scenarios/depth_hedge.py"""
import datetime as dt
import json
import urllib.request

import numpy as np

SYMS = ["USO", "XOP", "XLE", "OIH", "AMLP", "EWC", "NORW", "SPY"]
TIERS = {"T1+T1": [("XOP", "XLE")], "T1+T2": [("XOP", "OIH"), ("XOP", "AMLP")], "T1+T3": [("XOP", "EWC"), ("XOP", "NORW")],
         "T1+control": [("XOP", "SPY")]}


def bars(sym, start="2018-12-01", end="2026-01-05"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    c = r["indicators"]["adjclose"][0]["adjclose"]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], c) if v}


px = {s: bars(s) for s in SYMS}
dates = sorted(set.intersection(*(set(px[s]) for s in SYMS)))
P = {s: np.array([px[s][d] for d in dates]) for s in SYMS}
ret = P["USO"][1:] / P["USO"][:-1] - 1
events, skip = [], -1
for i, r in enumerate(ret, start=1):
    d = dates[i]
    if not ("2019-01-02" <= d <= "2025-12-30") or ("2020-03-01" <= d <= "2020-07-31") or i <= skip:
        continue
    if r >= 0.04 and i + 20 < len(dates):
        events.append(i)
        skip = i + 10
print(f"events: {len(events)}  " + ", ".join(dates[i] for i in events))


def win(s, i, a, b):
    return P[s][i + b] / P[s][i + a] - 1


R = {s: np.array([win(s, i, -1, 2) for i in events]) for s in SYMS}
F = {s: np.array([win(s, i, 2, 20) for i in events]) for s in SYMS}


def cvar(x, q=0.25):
    k = max(1, int(np.ceil(q * len(x))))
    return np.sort(x)[:k].mean()


def basket(pairs, W):
    return [0.5 * W[a] + 0.5 * W[b] for a, b in pairs]


rng = np.random.default_rng(0)
base_F = np.mean(basket(TIERS["T1+T1"], F), axis=0)
base_R = np.mean(basket(TIERS["T1+T1"], R), axis=0)
res = {}
print(f"\n{'basket':<11}{'meanR':>8}{'meanF':>8}{'worstF':>8}{'CVaR25(F)':>11}{'R kept':>8}{'corr(F)':>9}{'P(better)':>10}{'CVaR gain':>10}")
for name, pairs in TIERS.items():
    bF, bR = np.mean(basket(pairs, F), axis=0), np.mean(basket(pairs, R), axis=0)
    corr = np.mean([np.corrcoef(F[a], F[b])[0, 1] for a, b in pairs])
    diffs = []
    for _ in range(5000):
        ix = rng.integers(0, len(events), len(events))
        diffs.append(cvar(bF[ix]) - cvar(base_F[ix]))       # positive = the deeper pair's worst quarter is less bad
    gain = (cvar(bF) - cvar(base_F)) / abs(cvar(base_F))
    res[name] = dict(meanR=bR.mean(), Rkept=bR.mean() / base_R.mean(), cvar=cvar(bF), gain=gain, pbetter=float(np.mean(np.array(diffs) > 0)))
    print(f"{name:<11}{bR.mean():>8.3f}{bF.mean():>8.3f}{bF.min():>8.3f}{cvar(bF):>11.3f}{bR.mean() / base_R.mean():>8.2f}{corr:>9.2f}"
          f"{res[name]['pbetter']:>10.2f}{gain:>+10.0%}")

print("\nverdict per tier (pre-registered rule):")
ctrl = res["T1+control"]["Rkept"]
for t in ("T1+T2", "T1+T3"):
    r = res[t]
    c1 = r["gain"] >= 0.20 and r["pbetter"] >= 0.80
    c2 = r["meanR"] > 0 and r["Rkept"] >= 0.50
    c3 = r["Rkept"] > ctrl
    v = "SUPPORTED" if (c1 and c2 and c3) else ("DILUTED" if (c1 and not c2) else "NOT SUPPORTED")
    print(f"  {t}: downside gain {r['gain']:+.0%} (P better {r['pbetter']:.2f}) [{'ok' if c1 else 'fail'}]; R kept {r['Rkept']:.2f} [{'ok' if c2 else 'fail'}]; "
          f"beats control's R kept {ctrl:.2f} [{'ok' if c3 else 'fail'}] -> {v}")
