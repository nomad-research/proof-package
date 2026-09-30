"""Convexity check on FOMC days. Pre-registered in CONVEXITY_PREREG.md before this ran.   python convexity.py"""
import bisect
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
A = "JPM BAC WFC C".split(); H = [x["ticker"] for x in json.load(open(HERE / "hedge_basket.json"))["basket"]]
UNI = ("AAPL MSFT AMZN GOOGL META NVDA TSLA UNH JNJ PFE MRK ABBV LLY PG KO PEP WMT COST HD LOW MCD NKE DIS CMCSA VZ T LIN CAT DE HON UNP UPS DUK SO NEE D AEP O SPG PLD AMT EQIX DHI LEN PHM XOM CVX").split()
UA = {"User-Agent": "Mozilla/5.0 (research)"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf8", "replace")
dates = set()
for u in ["https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm", "https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm"]:
    dates |= set(re.findall(r"monetary(\d{8})a\.htm", get(u)))
D = sorted(f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates if "2019-01-01" <= f"{d[:4]}-{d[4:6]}-{d[6:]}" <= "2026-09-29")


def bars(sym, start="2017-06-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    r = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"))["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if v is not None}


px = {s: bars(s) for s in sorted(set(A + H + UNI + ["SPY", "^FVX"]))}
sd = sorted(set.intersection(*(set(v) for v in px.values())))
P = {s: np.array([px[s][d] for d in sd]) for s in px}; di = {d: i for i, d in enumerate(sd)}
ex = {s: P[s][1:] / P[s][:-1] - 1 - (P["SPY"][1:] / P["SPY"][:-1] - 1) for s in P if s != "^FVX"}
dy = np.diff(P["^FVX"])
ev = [(d, di[d]) for d in D if d in di and di[d] >= 260 and di[d] + 1 < len(sd)]
x = np.array([100 * (P["^FVX"][i] - P["^FVX"][i - 1]) for d, i in ev])
win = lambda names, i: float(np.mean([P[s][i + 1] / P[s][i - 1] - 1 - (P["SPY"][i + 1] / P["SPY"][i - 1] - 1) for s in names]))


def blind(i):
    b = {s: np.cov(ex[s][i - 250:i], dy[i - 250:i])[0, 1] / np.var(dy[i - 250:i], ddof=1) for s in UNI}
    return sorted(b, key=b.get)[:4]


a = np.array([win(A, i) for d, i in ev]); h = np.array([win(H, i) for d, i in ev]); s = np.array([win(blind(i), i) for d, i in ev])
series = {"A banks": a, "H hedge basket": h, "S blind pick": s, "pair A+H": 0.5 * a + 0.5 * h, "pair A+S": 0.5 * a + 0.5 * s, "control 0.5A": 0.5 * a}
X = np.c_[np.ones(len(x)), x, np.abs(x)]
rng = np.random.default_rng(0)


def fit(y, idx=None):
    idx = np.arange(len(x)) if idx is None else idx
    return np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]


print(f"events {len(x)}; x in bp: mean |x| {np.abs(x).mean():.1f}; buckets: <5bp {np.sum(np.abs(x) < 5)}, 5-10bp {np.sum((np.abs(x) >= 5) & (np.abs(x) < 10))}, >=10bp {np.sum(np.abs(x) >= 10)}")
print(f"\n{'series':<16}{'b (slope)':>11}{'c (convexity)':>15}{'c 10th pct':>12}{'<5bp':>9}{'5-10bp':>9}{'>=10bp':>9}{'worst':>9}")
boots = {}
for name, y in series.items():
    b = fit(y)
    cs = [fit(y, rng.integers(0, len(x), len(x)))[2] for _ in range(5000)]
    boots[name] = cs
    bk = [y[m].mean() for m in (np.abs(x) < 5, (np.abs(x) >= 5) & (np.abs(x) < 10), np.abs(x) >= 10)]
    print(f"{name:<16}{b[1]:>11.5f}{b[2]:>15.5f}{np.percentile(cs, 10):>12.5f}{bk[0]:>+9.4f}{bk[1]:>+9.4f}{bk[2]:>+9.4f}{y.min():>+9.4f}")
cp, cA, cH = fit(series["pair A+H"])[2], fit(series["A banks"])[2], fit(series["H hedge basket"])[2]
ok = cp > 0 and np.percentile(boots["pair A+H"], 10) > 0 and cp > max(cA, cH)
print(f"\nverdict (pre-registered): c(pair) {cp:+.5f} > 0 with a 10th percentile above 0 and above max(c(A), c(H)) = {max(cA, cH):+.5f}  ->  {'SHAPE SUPPORTED HERE' if ok else 'NOT SUPPORTED HERE'}")
