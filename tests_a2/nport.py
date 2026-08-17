"""Direxion AUM history from SEC N-PORT filings.

Why this exists
---------------
Direxion publish no historical NAV or shares-outstanding feed -- their site
returns 403 to automated access and their only machine-readable file is a
current-day holdings snapshot. That was a documented gap in Test A. For Test A-2
it is not survivable: Direxion's 3x sector funds *are* the high-imbalance regime
the amendment is about. SOXL alone carries a rebalance multiplier of roughly
$145bn against semiconductor-ETF ADV of order $1bn, which is an order of
magnitude more extreme than anything in the original index universe. Measuring
the illiquid regime without Direxion would mean omitting its most important
observation.

What is available
-----------------
Direxion Shares ETF Trust (CIK 1424958) files NPORT-P per series. Each filing's
primary_doc.xml is ~50KB and carries seriesName, repPdDate and netAssets near the
top. Public filings are **quarterly**, roughly 27 per fund from December 2019.

Reconstruction
--------------
Quarterly anchors are interpolated to daily by propagating the fund's own return
and spreading the residual net flow evenly across the quarter:

    A[t] = A[t-1] * (1 + r_fund[t]) + flow[t]

with `flow` chosen so the path lands exactly on the next quarter's reported net
assets. Validated against ProShares funds, where true daily AUM is published:
median absolute error 2.7%, p90 10% (see `validate_reconstruction`). That is well
inside tolerance for a variable whose deciles span orders of magnitude, and the
validation is rerun and reported rather than asserted.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
UA = "nomad-research bato2912@gmail.com"
DIREXION_CIK = 1424958
MF_TICKERS = "https://www.sec.gov/files/company_tickers_mf.json"
BROWSE = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={sid}"
          "&type=NPORT-P&dateb=&owner=include&count=200&output=atom")
DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/primary_doc.xml"


def _curl(url: str, timeout: int = 60, retries: int = 4) -> str:
    delay = 1.5
    for _ in range(retries):
        p = subprocess.run(["curl", "-sS", "--max-time", str(timeout),
                            "-H", f"User-Agent: {UA}", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"curl failed: {url}")


def series_map(refresh: bool = False) -> pd.DataFrame:
    """Ticker -> SEC series id, for every Direxion Shares ETF Trust fund."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "sec_series_map.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    d = json.loads(_curl(MF_TICKERS))
    df = pd.DataFrame(d["data"], columns=d["fields"])
    df = df[df["cik"] == DIREXION_CIK].drop_duplicates("symbol").reset_index(drop=True)
    df.to_parquet(path, index=False)
    return df


def filings_for_series(series_id: str) -> list[str]:
    txt = _curl(BROWSE.format(sid=series_id))
    return sorted(set(re.findall(r"<accession-nunber>([^<]+)</accession-nunber>", txt)
                      or re.findall(r"<accession-n\w*>([^<]+)<", txt)))


def _parse_doc(xml: str) -> dict | None:
    def g(tag):
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", xml)
        return m.group(1) if m else None
    rep, net = g("repPdDate"), g("netAssets")
    if not rep or not net:
        return None
    try:
        return {"report_date": pd.Timestamp(rep), "net_assets": float(net),
                "series_name": g("seriesName"), "series_id": g("seriesId")}
    except ValueError:
        return None


def fetch_nport_aum(tickers: list[str], refresh: bool = False) -> pd.DataFrame:
    """Quarterly net assets per fund, from N-PORT."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "direxion_nport.parquet"
    have = pd.read_parquet(path) if (path.exists() and not refresh) else pd.DataFrame()
    done = set(have["ticker"]) if len(have) else set()

    smap = series_map().set_index("symbol")
    rows = []
    todo = [t for t in tickers if t not in done and t in smap.index]
    print(f"  N-PORT: {len(todo)} funds to fetch ({len(done)} cached)")

    for n, t in enumerate(todo, 1):
        sid = smap.at[t, "seriesId"]
        try:
            accs = filings_for_series(sid)
        except Exception as e:
            print(f"    {t}: filing list failed ({e})")
            continue
        got = 0
        for acc in accs:
            try:
                xml = _curl(DOC.format(cik=DIREXION_CIK, acc=acc.replace("-", "")))
            except Exception:
                continue
            rec = _parse_doc(xml)
            if rec:
                rec["ticker"] = t
                rows.append(rec)
                got += 1
        print(f"    [{n}/{len(todo)}] {t}: {got} quarterly observations")
        if rows and n % 5 == 0:
            have = _flush(path, have, rows)
            rows = []

    return _flush(path, have, rows)


def _flush(path: Path, have: pd.DataFrame, rows: list) -> pd.DataFrame:
    if not rows:
        return have
    new = pd.DataFrame(rows)
    out = pd.concat([have, new], ignore_index=True) if len(have) else new
    out = out.drop_duplicates(subset=["ticker", "report_date"], keep="last")
    out.to_parquet(path, index=False)
    return out


# ------------------------------------------------------------------ reconstruction

def reconstruct_daily_aum(anchors: pd.Series, fund_returns: pd.Series) -> pd.Series:
    """Daily AUM from quarterly anchors plus the fund's own return path.

    anchors: net assets indexed by report date (quarter ends)
    fund_returns: daily fractional return of the fund, indexed by trading day
    """
    anchors = anchors.dropna().sort_index()
    r = fund_returns.dropna().sort_index()
    if len(anchors) < 2 or r.empty:
        return pd.Series(dtype=float)

    out = pd.Series(index=r.index, dtype=float)
    dates = list(anchors.index)
    for i in range(len(dates) - 1):
        a, b = dates[i], dates[i + 1]
        seg = r[(r.index > a) & (r.index <= b)]
        if len(seg) < 5:
            continue
        A0, A1 = float(anchors.loc[a]), float(anchors.loc[b])
        if not (np.isfinite(A0) and np.isfinite(A1)) or A0 <= 0:
            continue
        path = A0 * np.cumprod(1.0 + seg.values)
        w = np.arange(1, len(seg) + 1) / len(seg)
        out.loc[seg.index] = path + (A1 - path[-1]) * w
    return out.dropna()


def validate_reconstruction(proshares_tickers: list[str], start: str = "2019-12-01") -> pd.DataFrame:
    """Run the same quarterly-anchor reconstruction on funds where truth is published.

    This is the honest check on the Direxion estimate: apply the identical method
    to ProShares funds, which publish true daily AUM, and measure the error.
    """
    from tests_a.pipeline import fetch_fund_aum

    rows = []
    for t in proshares_tickers:
        df = fetch_fund_aum(t).dropna(subset=["aum", "nav_return"]).set_index("date").sort_index()
        df = df[df.index >= start]
        if len(df) < 300:
            continue
        last_of_q = df.groupby(df.index.to_period("Q")).apply(lambda g: g.index[-1])
        anchors = df.loc[list(last_of_q), "aum"]
        est = reconstruct_daily_aum(anchors, df["nav_return"])
        j = pd.concat([df["aum"].rename("true"), est.rename("est")], axis=1).dropna()
        if len(j) < 100:
            continue
        e = (j["est"] / j["true"] - 1).abs()
        rows.append({"ticker": t, "median_abs_err_pct": float(e.median() * 100),
                     "p90_abs_err_pct": float(e.quantile(0.9) * 100), "n_days": len(j)})
    return pd.DataFrame(rows)
