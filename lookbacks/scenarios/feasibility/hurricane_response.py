"""Feasibility check (not a test of the mechanism): do Gulf-exposed listed equities respond beyond noise to US Gulf hurricane landfalls?
Events: unique storms with a US Gulf landfall record at >=34 kt since 2010 (NHC HURDAT2). Response: the name's 3-day abnormal return over SPY, around the landfall date, divided by
the std of the same 3-day abnormal return over the prior 250 trading days; compared with the same names on 45 random dates each.
    curl the current HURDAT2 file from https://www.nhc.noaa.gov/data/hurdat/ to /tmp/claude-0/hurdat2.txt, then run this."""
import bisect
import datetime as dt
import json
import re
import urllib.request

import numpy as np

lines = open("/tmp/claude-0/hurdat2.txt").read().splitlines()
ev, cur = {}, None
for ln in lines:
    p = [x.strip() for x in ln.split(",")]
    if re.match(r"^AL\d{6}$", p[0]):
        cur = (p[0], p[1]); continue
    if len(p) >= 7 and p[2] == "L" and cur:
        lat = float(p[4][:-1]); lon = -float(p[5][:-1]) if p[5].endswith("W") else float(p[5][:-1])
        if 24 <= lat <= 31.5 and -98 <= lon <= -80 and p[0] >= "20100101" and int(p[6]) >= 34 and cur[0] not in ev:
            ev[cur[0]] = dict(name=cur[1], date=f"{p[0][:4]}-{p[0][4:6]}-{p[0][6:]}", wind=int(p[6]))
E = sorted(ev.values(), key=lambda x: x["date"])
print("unique storms:", len(E), "hurricanes (>=64 kt):", sum(e["wind"] >= 64 for e in E))


def bars(sym, start="2009-01-01", end="2026-10-01"):
    p1, p2 = (int(dt.datetime.fromisoformat(x).timestamp()) for x in (start, end))
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
    return {dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): v for t, v in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]) if v}


G = {"refiners": "VLO MPC PSX", "chemicals": "LYB WLK OLN", "utilities": "ETR CNP", "insurers": "ALL TRV"}
px = {s: bars(s) for s in ["SPY"] + [x for v in G.values() for x in v.split()]}


def z_for(sym, d0):
    ds = sorted(set(px[sym]) & set(px["SPY"])); i = bisect.bisect_left(ds, d0)
    if i < 260 or i + 2 >= len(ds):
        return None
    ab = lambda a, b: (px[sym][ds[b]] / px[sym][ds[a]] - 1) - (px["SPY"][ds[b]] / px["SPY"][ds[a]] - 1)
    h = np.array([ab(k - 1, k + 2) for k in range(i - 250, i - 5)])
    return ab(i - 1, i + 2) / h.std()


rng = np.random.default_rng(0)
allsd = sorted(set(px["SPY"]))
print(f"{'group':<10}{'name-events':>12}{'|z|>1.64':>10}{'null (random dates)':>21}{'|z|>2.5':>9}")
for g, names in G.items():
    zs, nz = [], []
    for s in names.split():
        zs += [z for z in (z_for(s, e["date"]) for e in E) if z is not None]
        nz += [z for z in (z_for(s, allsd[rng.integers(300, len(allsd) - 10)]) for _ in range(45)) if z is not None]
    zs, nz = np.array(zs), np.array(nz)
    print(f"{g:<10}{len(zs):>12}{np.mean(np.abs(zs) > 1.64):>10.0%}{np.mean(np.abs(nz) > 1.64):>21.0%}{np.mean(np.abs(zs) > 2.5):>9.0%}")
