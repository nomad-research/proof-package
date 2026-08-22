"""Rates outcome variables for the B-3 re-run.

Three outcomes, per preregistration §2:
  DGS2  -- 2-year constant-maturity yield. CHANGE IN YIELD, basis points.
           One observation per business day: no open, no close, so the
           overnight window does not exist for it (preregistration §3.1).
  TLT   -- 20y+ Treasury ETF, daily return. Has open and close.
  IEF   -- 7-10y Treasury ETF, daily return. Has open and close.

Sign convention (preregistration §4): a positive activity or inflation surprise
raises yields and lowers bond prices, so the surprise coefficient should be
POSITIVE on DGS2 and NEGATIVE on TLT/IEF. Same-signed coefficients across the
two would mean the instrument is not measuring what it is meant to measure.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def _get(url: str, timeout: int = 90, tries: int = 4) -> str:
    import time
    delay = 2.0
    for _ in range(tries):
        p = subprocess.run(["curl", "-sS", "--max-time", str(timeout), url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"fetch failed: {url}")


def fetch_dgs2(refresh: bool = False) -> pd.DataFrame:
    """2-year CMT yield, daily. Returns date, yield_pct, d_yield_bp."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "rates_DGS2.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    txt = _get(FRED_CSV.format(sid="DGS2"))
    raw = pd.read_csv(io.StringIO(txt))
    raw.columns = ["date", "yield_pct"]
    df = pd.DataFrame({
        "date": pd.to_datetime(raw["date"]),
        # FRED marks holidays with "."; coerce turns them into NaN, which is right
        "yield_pct": pd.to_numeric(raw["yield_pct"], errors="coerce"),
    }).dropna(subset=["yield_pct"]).sort_values("date").reset_index(drop=True)

    # basis points, day over day. This is the close-to-close analogue: H.15 CMT
    # yields are struck from mid-afternoon quotes, so the change brackets the
    # 08:30 release together with a full session of other news.
    df["d_yield_bp"] = df["yield_pct"].diff() * 100.0
    df.to_parquet(path, index=False)
    return df


def fetch_etf(sym: str, refresh: bool = False) -> pd.DataFrame:
    """Daily OHLC for a Treasury ETF, with both event windows."""
    from tests_a.pipeline import fetch_daily
    d = fetch_daily(sym, refresh=refresh, start="2002-01-01").set_index("date").sort_index()
    out = pd.DataFrame(index=d.index)
    out["ret_cc"] = d["close"].pct_change()                       # close to close
    out["ret_on"] = d["open"] / d["close"].shift(1) - 1.0         # overnight
    return out.reset_index()


def build() -> dict[str, pd.DataFrame]:
    """All three outcomes, keyed by the column name the analysis will use."""
    dgs2 = fetch_dgs2()
    out = {"DGS2": dgs2.rename(columns={"d_yield_bp": "value"})[["date", "value"]]
                       .assign(window="day-over-day", units="bp")}
    for sym in ("TLT", "IEF"):
        e = fetch_etf(sym)
        out[f"{sym}_on"] = e.rename(columns={"ret_on": "value"})[["date", "value"]] \
                            .assign(window="overnight", units="return")
        out[f"{sym}_cc"] = e.rename(columns={"ret_cc": "value"})[["date", "value"]] \
                            .assign(window="close-to-close", units="return")
    return out


if __name__ == "__main__":
    for k, v in build().items():
        v = v.dropna(subset=["value"])
        print(f"{k:8} {v['window']. iloc[0]:>14}  n={len(v):>6}  "
              f"{v['date'].min().date()} -> {v['date'].max().date()}  "
              f"sd={v['value'].std():.4g} {v['units'].iloc[0]}")
