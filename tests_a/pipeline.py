"""Test A data pipeline: fetch and cache LETF AUM and index/ETF prices.

Sources
-------
LETF daily NAV, shares outstanding and AUM
    ProShares publish a per-fund historical NAV file covering the full life of
    each fund:
    https://accounts.profunds.com/etfdata/ByFund/<TICKER>-historical_nav.csv
    Columns: Date, ProShares Name, Ticker, NAV, Prior NAV, NAV Change (%),
             NAV Change ($), Shares Outstanding (000), Assets Under Management

    Direxion publish no historical equivalent -- their site returns 403 to
    automated access and their only machine-readable file is a current-day
    holdings snapshot. This is the coverage gap documented in
    preregistration.md §7.1.

Index and ETF daily OHLCV
    Yahoo Finance chart API. Daily history is complete back to 2010 for every
    symbol used. Intraday history is capped (~60d at 30m, ~730d at 1h), which is
    the constraint behind preregistration.md §6.

Everything is cached under data/cache/ so analysis reruns are offline and
reproducible.
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .universe import ALL_FUNDS, ALL_SYMBOLS, UNIVERSE

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
PROSHARES_URL = "https://accounts.profunds.com/etfdata/ByFund/{ticker}-historical_nav.csv"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nomad-research/1.0)"}


def _get(url: str, params: dict | None = None, retries: int = 4, timeout: int = 60) -> requests.Response:
    delay = 2.0
    last: Exception | None = None
    for _ in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except Exception as e:  # network flake
            last = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"failed after {retries} attempts: {url}") from last


# ------------------------------------------------------------------ LETF AUM

def fetch_fund_aum(ticker: str, refresh: bool = False) -> pd.DataFrame:
    """Daily NAV / shares outstanding / AUM for one ProShares fund, full history."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"aum_{ticker}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    r = _get(PROSHARES_URL.format(ticker=ticker))
    raw = pd.read_csv(io.StringIO(r.text))
    raw.columns = [c.strip() for c in raw.columns]

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["Date"], format="%m/%d/%Y"),
            "ticker": ticker,
            "nav": pd.to_numeric(raw["NAV"], errors="coerce"),
            "prior_nav": pd.to_numeric(raw["Prior NAV"], errors="coerce"),
            "shares_out": pd.to_numeric(raw["Shares Outstanding (000)"], errors="coerce") * 1_000.0,
            "aum": pd.to_numeric(raw["Assets Under Management"], errors="coerce"),
        }
    ).sort_values("date").reset_index(drop=True)

    # NAV return implied by the file, used downstream as a data-quality check
    df["nav_return"] = df["nav"] / df["prior_nav"] - 1.0
    df.loc[~(df["prior_nav"] > 0), "nav_return"] = pd.NA

    # preregistration §5 rule 5: non-positive AUM is missing
    df.loc[~(df["aum"] > 0), "aum"] = pd.NA

    df["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    df.to_parquet(path, index=False)
    return df


def fetch_all_aum(refresh: bool = False) -> pd.DataFrame:
    frames = []
    for t in ALL_FUNDS:
        frames.append(fetch_fund_aum(t, refresh=refresh))
        print(f"  aum {t}: {len(frames[-1])} rows "
              f"{frames[-1]['date'].min().date()} -> {frames[-1]['date'].max().date()}")
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------------ prices

def fetch_daily(symbol: str, refresh: bool = False, start: str = "2009-01-01") -> pd.DataFrame:
    """Daily OHLCV from the Yahoo chart API."""
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("^", "IDX_")
    path = CACHE / f"px_{safe}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int(pd.Timestamp.now(tz="UTC").timestamp())
    r = _get(YAHOO_URL.format(symbol=symbol),
             params={"period1": p1, "period2": p2, "interval": "1d"})
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(
                res["meta"]["exchangeTimezoneName"]
            ).normalize().tz_localize(None),
            "symbol": symbol,
            "open": q["open"],
            "high": q["high"],
            "low": q["low"],
            "close": q["close"],
            "volume": q["volume"],
        }
    ).dropna(subset=["close"]).sort_values("date").reset_index(drop=True)

    df["dollar_volume"] = df["close"] * df["volume"]
    df["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    df.to_parquet(path, index=False)
    return df


def fetch_hourly(symbol: str, refresh: bool = False) -> pd.DataFrame:
    """Hourly bars, ~730 calendar days deep. Used only for the power-limited
    late-day impact test in preregistration.md §4.3."""
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("^", "IDX_")
    path = CACHE / f"px1h_{safe}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    r = _get(YAHOO_URL.format(symbol=symbol), params={"range": "730d", "interval": "1h"})
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    tz = res["meta"]["exchangeTimezoneName"]

    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    df = pd.DataFrame(
        {"ts": ts, "symbol": symbol, "close": q["close"], "volume": q["volume"]}
    ).dropna(subset=["close"]).sort_values("ts").reset_index(drop=True)
    df["date"] = df["ts"].dt.tz_localize(None).dt.normalize()
    df["hour"] = df["ts"].dt.hour
    df["minute"] = df["ts"].dt.minute
    df.to_parquet(path, index=False)
    return df


def fetch_all_prices(refresh: bool = False) -> pd.DataFrame:
    frames = []
    for s in ALL_SYMBOLS:
        frames.append(fetch_daily(s, refresh=refresh))
        print(f"  px {s}: {len(frames[-1])} rows "
              f"{frames[-1]['date'].min().date()} -> {frames[-1]['date'].max().date()}")
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------------ quality

def leverage_check(aum: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Regress each fund's daily NAV return on its index's return.

    The slope should recover the stated leverage. This is the check that the AUM
    file, the leverage assumption and the index mapping are all consistent -- if
    a fund's slope does not land near its stated L, the sign convention or the
    mapping is wrong and the whole test is mis-specified.
    """
    import numpy as np

    px = prices.set_index(["symbol", "date"])["close"]
    rows = []
    for u in UNIVERSE:
        idx = px.loc[u.index_symbol].pct_change().rename("r_index")
        for f in u.funds:
            fa = aum[aum["ticker"] == f.ticker].set_index("date")["nav_return"]
            j = pd.concat([idx, fa.rename("r_fund")], axis=1).dropna()
            j = j[(j["r_index"].abs() < 0.25) & (j["r_fund"].abs() < 0.75)]
            if len(j) < 100:
                rows.append({"ticker": f.ticker, "stated_leverage": f.leverage,
                             "implied_leverage": float("nan"), "r2": float("nan"), "n": len(j)})
                continue
            x, y = j["r_index"].values, j["r_fund"].values
            slope = float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1))
            corr = float(np.corrcoef(x, y)[0, 1])
            rows.append({"ticker": f.ticker, "underlying": u.key,
                         "stated_leverage": f.leverage, "implied_leverage": slope,
                         "r2": corr ** 2, "n": len(j)})
    return pd.DataFrame(rows)


def main() -> None:
    print("Fetching ProShares AUM history...")
    aum = fetch_all_aum()
    print("\nFetching daily prices...")
    prices = fetch_all_prices()

    print("\nLeverage consistency check (implied slope should match stated L):")
    chk = leverage_check(aum, prices)
    print(chk.to_string(index=False))

    bad = chk[(chk["implied_leverage"] - chk["stated_leverage"]).abs() > 0.35]
    if len(bad):
        print("\nWARNING: implied leverage off by >0.35 for:")
        print(bad.to_string(index=False))
    else:
        print("\nAll funds recover their stated leverage within 0.35.")

    CACHE.mkdir(parents=True, exist_ok=True)
    chk.to_csv(CACHE / "leverage_check.csv", index=False)
    print(f"\nCached to {CACHE}")


if __name__ == "__main__":
    main()
