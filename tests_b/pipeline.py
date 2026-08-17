"""Test B data pipeline: real-time (vintage) macro data and release dates.

Why vintages
------------
The whole test turns on what was knowable at the moment of an announcement. Using
today's revised values would import benchmark revisions made years afterwards
into a decision that had to be taken in real time -- exactly the restated-data
violation the specification forbids in §1.4. So every macro input here is a
**first print**: the value as it was actually published, taken from the ALFRED
vintage in which it first appeared.

The vintage date on which a reference month first appears *is* that month's
release date. That is how release dates are obtained here, rather than assumed
from a published schedule -- it is measured from the archive itself, and the
ordering between releases can then be verified rather than asserted.

Source
------
ALFRED (archival FRED), St. Louis Fed:
  vintage list  https://alfred.stlouisfed.org/series/downloaddata?seid=<ID>
  vintage data  https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=<ID>&vintage_date=<D>

Fetching goes through curl rather than `requests` because the outbound proxy in
this environment intermittently drops urllib3 connections; curl with retries is
reliable against the same host.
"""

from __future__ import annotations

import io
import re
import subprocess
import time
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
ALFRED_LIST = "https://alfred.stlouisfed.org/series/downloaddata?seid={sid}"
ALFRED_CSV = ("https://alfred.stlouisfed.org/graph/alfredgraph.csv"
              "?id={sid}&vintage_date={vintage}&cosd={cosd}&coed={coed}")

SAMPLE_START = "1997-01-01"     # preregistration §3

# The composite under test and the components published before it.
TARGET = "INDPRO"                       # Industrial Production, total index
COMPONENTS = ("AWHMAN", "MANEMP")       # avg weekly hours + employment, manufacturing
                                        # both from the Employment Situation report
ALL_SERIES = (TARGET,) + COMPONENTS


def _curl(url: str, timeout: int = 90, retries: int = 5) -> str:
    delay = 2.0
    last = ""
    for _ in range(retries):
        p = subprocess.run(["curl", "-sS", "--max-time", str(timeout), url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        last = p.stderr.strip() or f"rc={p.returncode}"
        time.sleep(delay)
        delay = min(delay * 2, 30)
    raise RuntimeError(f"curl failed for {url}: {last}")


# ------------------------------------------------------------------ vintages

def vintage_dates(series: str, refresh: bool = False) -> list[str]:
    """Every vintage date ALFRED holds for a series. These are its release dates."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"vintages_{series}.txt"
    if path.exists() and not refresh:
        return path.read_text().split()
    html = _curl(ALFRED_LIST.format(sid=series), timeout=180)
    dates = sorted(set(re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"', html)))
    if not dates:
        raise RuntimeError(f"no vintage dates parsed for {series}")
    path.write_text("\n".join(dates))
    return dates


def fetch_vintage_panel(series: str, start: str = SAMPLE_START,
                        lookback_months: int = 10, refresh: bool = False) -> pd.DataFrame:
    """One row per (vintage, observation) for every vintage at or after `start`.

    Only a short observation window before each vintage is requested -- the first
    print of a reference month always sits at the end of the series, so there is
    no reason to pull the whole history 380 times.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"vintage_panel_{series}.parquet"
    have = pd.read_parquet(path) if (path.exists() and not refresh) else pd.DataFrame()
    done = set(have["vintage"].astype(str)) if len(have) else set()

    wanted = [v for v in vintage_dates(series) if v >= start]
    todo = [v for v in wanted if v not in done]
    if not todo:
        return have

    print(f"  {series}: {len(todo)} vintages to fetch ({len(done)} cached)")
    rows = []
    for i, v in enumerate(todo, 1):
        vt = pd.Timestamp(v)
        cosd = (vt - pd.DateOffset(months=lookback_months)).strftime("%Y-%m-%d")
        txt = _curl(ALFRED_CSV.format(sid=series, vintage=v, cosd=cosd,
                                      coed=vt.strftime("%Y-%m-%d")))
        try:
            df = pd.read_csv(io.StringIO(txt))
        except Exception:
            print(f"    {series} {v}: unparseable response, skipped")
            continue
        if df.shape[1] < 2:
            continue
        df.columns = ["obs_date", "value"]
        df["obs_date"] = pd.to_datetime(df["obs_date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["obs_date"])
        df["vintage"] = v
        df["series"] = series
        rows.append(df)
        if i % 25 == 0:
            print(f"    {series}: {i}/{len(todo)}")
            _flush(path, have, rows)

    out = _flush(path, have, rows)
    return out


def _flush(path: Path, have: pd.DataFrame, rows: list[pd.DataFrame]) -> pd.DataFrame:
    if not rows:
        return have
    out = pd.concat([have] + rows, ignore_index=True) if len(have) else pd.concat(rows, ignore_index=True)
    out = out.drop_duplicates(subset=["series", "vintage", "obs_date"], keep="last")
    out.to_parquet(path, index=False)
    return out


def first_prints(series: str) -> pd.DataFrame:
    """For each reference month, its first published value and the date it appeared.

    `release_date` is the vintage in which the reference month first has a
    non-null value -- measured from the archive, not taken from a schedule.
    """
    panel = fetch_vintage_panel(series)
    p = panel.dropna(subset=["value"]).copy()
    p["vintage"] = pd.to_datetime(p["vintage"])
    p = p.sort_values(["obs_date", "vintage"])
    fp = p.groupby("obs_date", as_index=False).first()
    return fp.rename(columns={"vintage": "release_date", "value": "first_print"})[
        ["obs_date", "release_date", "first_print"]]


def build() -> dict[str, pd.DataFrame]:
    out = {}
    for s in ALL_SERIES:
        print(f"Fetching {s}...")
        fetch_vintage_panel(s)
        out[s] = first_prints(s)
        print(f"  {s}: {len(out[s])} reference months, "
              f"{out[s]['obs_date'].min().date()} -> {out[s]['obs_date'].max().date()}")
    return out


def main() -> None:
    fp = build()
    # ordering check: is the Employment Situation genuinely published before IP?
    ip = fp[TARGET].set_index("obs_date")["release_date"]
    es = fp[COMPONENTS[0]].set_index("obs_date")["release_date"]
    j = pd.concat([ip.rename("ip_release"), es.rename("es_release")], axis=1).dropna()
    gap = (j["ip_release"] - j["es_release"]).dt.days
    print(f"\nRelease ordering (Employment Situation vs Industrial Production), "
          f"same reference month, n={len(j)}:")
    print(f"  ES before IP in {int((gap > 0).sum())}/{len(j)} months")
    print(f"  median gap {gap.median():.0f} days, min {gap.min():.0f}, max {gap.max():.0f}")
    (CACHE / "release_gap.csv").write_text(
        pd.DataFrame({"obs_date": j.index, "gap_days": gap.values}).to_csv(index=False))


if __name__ == "__main__":
    main()
