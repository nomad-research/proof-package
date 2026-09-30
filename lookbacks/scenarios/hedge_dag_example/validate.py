"""Hedge-DAG validation. Pre-registered in VALIDATION_PREREG.md before this ran.    python lookbacks/scenarios/hedge_dag_example/validate.py"""
import datetime as dt
import json
import urllib.request

import numpy as np

from pathlib import Path
HERE = Path(__file__).parent
NAMES = ["OXY", "EOG", "XOM", "MPC"]
SENS = {"OXY": {"crude": 250, "gas": 350}, "EOG": {"crude": 204, "gas": 420}, "XOM": {"crude": 650, "gas": 750}, "MPC": {"crack": 1100}}
CIK = {"OXY": 797468, "EOG": 821189, "XOM": 34088, "MPC": 1510295}
UA = "research nomad bato2912@gmail.com"
WIN = ("2025-03-01", "2026-09-29")


def bars(sym, start="2024-01-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]) if v}


def shares(t):
    try:
        u = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK[t]:010d}/dei/EntityCommonStockSharesOutstanding.json"
        j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read())
        rows = [x for x in j["units"]["shares"] if "2025-01-01" <= x["end"] <= "2025-04-30"]
        return float(sorted(rows, key=lambda x: x["end"])[-1]["val"])
    except Exception:
        return None


ex = json.load(open(HERE / "exposures.json"))["companies"]
px = {s: bars(s) for s in NAMES + ["SPY", "CL=F", "RB=F", "HO=F", "NG=F"]}
sh = {t: shares(t) for t in NAMES}
use_mcap = all(v for v in sh.values())
print("normaliser:", "market cap (shares from 10-K cover XBRL)" if use_mcap else "FY2024 pre-tax income (a share count was unavailable)", {t: sh[t] for t in NAMES})
dates = sorted(set.intersection(*(set(px[s]) for s in px)))
di = {d: i for i, d in enumerate(dates)}
A = {s: np.array([px[s][d] for d in dates]) for s in px}
crack = (2 * A["RB=F"] * 42 + A["HO=F"] * 42) / 3 - A["CL=F"]
cl = px["CL=F"]; cd = sorted(cl)
events, skip = [], ""
for a, b in zip(cd, cd[1:]):
    if not (WIN[0] <= b <= WIN[1]) or b <= skip or b not in di:
        continue
    if cl[b] / cl[a] - 1 >= 0.04 and di[b] + 2 < len(dates):
        events.append(di[b]); skip = dates[min(di[b] + 10, len(dates) - 1)]
print(f"events: {len(events)}  " + ", ".join(dates[i] for i in events))
if len(events) < 8:
    raise SystemExit("fewer than 8 events: unreadable")
ret = {s: A[s][1:] / A[s][:-1] - 1 for s in A}


def demean(x):
    return x - x.mean()


P, Q, Rr = [], [], []
for i in events:
    a, b = i - 1, i + 2
    shock = {"crude": A["CL=F"][b] - A["CL=F"][a], "gas": A["NG=F"][b] - A["NG=F"][a], "crack": crack[b] - crack[a]}
    p, q, r = [], [], []
    for t in NAMES:
        norm = A[t][a] * sh[t] / 1e6 if use_mcap else ex[t]["pretax_income"]["value"]      # $M
        p.append(sum(v * shock[c] for c, v in SENS[t].items()) / norm)
        y = ret[t][i - 250 - 2:i - 2]; x = ret["CL=F"][i - 250 - 2:i - 2]
        beta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
        q.append(beta * (A["CL=F"][b] / A["CL=F"][a] - 1))
        r.append((A[t][b] / A[t][a] - 1) - (A["SPY"][b] / A["SPY"][a] - 1))
    P.append(demean(np.array(p))); Q.append(demean(np.array(q))); Rr.append(demean(np.array(r)))
P, Q, Rr = np.array(P), np.array(Q), np.array(Rr)
corr = lambda x, y: float(np.corrcoef(x.ravel(), y.ravel())[0, 1])
rho_doc, rho_beta = corr(P, Rr), corr(Q, Rr)
rng = np.random.default_rng(0)
bd, bdiff = [], []
for _ in range(5000):
    ix = rng.integers(0, len(events), len(events))
    bd.append(corr(P[ix], Rr[ix])); bdiff.append(corr(P[ix], Rr[ix]) - corr(Q[ix], Rr[ix]))
print(f"\nrho_doc  (documented-exposure model vs realised, demeaned within event): {rho_doc:+.2f}  bootstrap 10th percentile {np.percentile(bd, 10):+.2f}")
print(f"rho_beta (trailing-beta model): {rho_beta:+.2f}   difference {rho_doc - rho_beta:+.2f}  (bootstrap 10th percentile of the difference {np.percentile(bdiff, 10):+.2f})")
g = lambda M: M[:, :3].mean(axis=1) - M[:, 3]
sp, sr = g(P), g(Rr)
hit = float(np.mean(np.sign(sp) == np.sign(sr)))
rs = float(np.corrcoef(sp, sr)[0, 1])
print(f"spread (E&P mean minus MPC): sign hit rate {hit:.0%}, correlation across events {rs:+.2f}")
c1 = rho_doc >= 0.30 and np.percentile(bd, 10) > 0
c2 = rho_doc - rho_beta >= 0.10
c3 = hit >= 0.65 and rs >= 0.40
print(f"\nverdict (pre-registered): (1) divergence predictable in cross-section [{'ok' if c1 else 'fail'}]; (2) adds beyond beta [{'ok' if c2 else 'fail'}]; (3) spread [{'ok' if c3 else 'fail'}]")
print("=> DIVERGENCE PREDICTABLE" if (c1 and c3) else "=> NOT SUPPORTED")
print("\nper-event: date, predicted spread, realised spread")
for i, a_, b_ in zip(events, sp, sr):
    print(f"  {dates[i]}  {a_:+.4f}  {b_:+.4f}")
