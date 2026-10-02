"""Construct-then-hedge on FOMC statement days. Pre-registered in PREREG.md; the hedge basket was frozen in hedge_basket.json before this ran.   python evaluate.py"""
import bisect
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
A = "JPM BAC WFC C".split()
H = [x["ticker"] for x in json.load(open(HERE / "hedge_basket.json"))["basket"]]
UNI = ("AAPL MSFT AMZN GOOGL META NVDA TSLA UNH JNJ PFE MRK ABBV LLY PG KO PEP WMT COST HD LOW MCD NKE DIS CMCSA VZ T LIN CAT DE HON UNP UPS DUK SO NEE D AEP O SPG PLD AMT EQIX DHI LEN PHM XOM CVX").split()
UA = {"User-Agent": "Mozilla/5.0 (research)"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf8", "replace")
dates = set()
for u in ["https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm",
          "https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm"]:
    dates |= set(re.findall(r"monetary(\d{8})a\.htm", get(u)))
D = sorted(f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates if "2019-01-01" <= f"{d[:4]}-{d[4:6]}-{d[6:]}" <= "2026-09-29")


def bars(sym, start="2017-06-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"
    r = json.loads(get(u))["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if v is not None}


px = {s: bars(s) for s in sorted(set(A + H + UNI + ["SPY", "^FVX"]))}
sd = sorted(set.intersection(*(set(v) for v in px.values())))
P = {s: np.array([px[s][d] for d in sd]) for s in px}
di = {d: i for i, d in enumerate(sd)}
r1 = lambda s: P[s][1:] / P[s][:-1] - 1                    # r1[s][k]: return from sd[k] to sd[k+1]
ex = {s: r1(s) - r1("SPY") for s in P if s not in ("^FVX",)}
dy = np.diff(P["^FVX"])                                     # daily change in the 5y yield, percentage points
events = []
for d in D:
    if d in di and di[d] >= 260 and di[d] + 1 < len(sd):
        i = di[d]; bp = 100 * (P["^FVX"][i] - P["^FVX"][i - 1])
        events.append((d, i, bp, "hawkish" if bp >= 5 else "dovish" if bp <= -5 else "neutral"))
print(f"events {len(events)}:", {k: sum(e[3] == k for e in events) for k in ("hawkish", "neutral", "dovish")}, "| A", A, "| H", H)
win = lambda names, i: float(np.mean([P[s][i + 1] / P[s][i - 1] - 1 - (P["SPY"][i + 1] / P["SPY"][i - 1] - 1) for s in names]))


def blind(i):
    b = {}
    for s in UNI:
        y = ex[s][i - 250:i]; x = dy[i - 250:i]                # returns from sd[k] to sd[k+1] for k in [i-250, i): all before the statement day
        b[s] = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
    return sorted(b, key=b.get)[:4]


rows = []
for d, i, bp, o in events:
    a, h = win(A, i), win(H, i)
    S = blind(i); s = win(S, i)
    rows.append(dict(d=d, o=o, narr=0.5 * a + 0.5 * h, ctrl=0.5 * a, blind=0.5 * a + 0.5 * s, A=a, overlap=len(set(S) & set(H))))
rng = np.random.default_rng(0)


def boot(x, thr=0.0):
    x = np.array(x)
    return float(np.mean([rng.choice(x, len(x)).mean() > thr for _ in range(5000)]))


print(f"mean overlap between the constructed basket H and the blind pick S: {np.mean([r['overlap'] for r in rows]):.1f} of 4 names")
res = {}
for label, lo, hi in (("2019-01 to 2022-12", "2019-01-01", "2022-12-31"), ("2023-01 to 2026-09", "2023-01-01", "2026-09-29")):
    R = [r for r in rows if lo <= r["d"] <= hi]; dov = [r for r in R if r["o"] == "dovish"]; oth = [r for r in R if r["o"] != "dovish"]
    print(f"\n== {label}: {len(R)} events, {len(dov)} dovish")
    if len(dov) < 8:
        print("  fewer than 8 dovish events: unreadable"); res[label] = None; continue
    dn = [r["narr"] - r["ctrl"] for r in dov]; db = [r["narr"] - r["blind"] for r in dov]; bc = [r["blind"] - r["ctrl"] for r in dov]
    up = np.mean([r["narr"] - r["ctrl"] for r in oth])
    print(f"  dovish events: mean A {np.mean([r['A'] for r in dov]):+.4f}; narrative pair - control {np.mean(dn):+.4f} (P>0 {boot(dn):.2f}); blind pair - control {np.mean(bc):+.4f}; narrative - blind {np.mean(db):+.4f} (P>0 {boot(db):.2f})")
    print(f"  hawkish and neutral events: narrative pair minus control {up:+.4f}")
    c = [np.mean(dn) > 0 and boot(dn) >= 0.80, np.mean(db) >= 0.001 and boot(db) >= 0.80, up >= -0.001]
    print(f"  (1) beats de-risking [{'ok' if c[0] else 'fail'}]  (2) beats the blind statistical hedge [{'ok' if c[1] else 'fail'}]  (3) upside kept [{'ok' if c[2] else 'fail'}]")
    res[label] = c
ok = all(v is not None and all(v) for v in res.values())
print("\nverdict (pre-registered; both halves):", "NARRATIVE GUIDANCE ADDS" if ok else "NOT SUPPORTED", res)
