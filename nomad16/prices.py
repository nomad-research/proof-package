"""The price vintage store (§26). Every price the harness computes with comes from a
frozen, hashed vintage, never from a live read used directly.

* The payload is hashed decompressed (canonical JSON of the parsed series), not as
  transferred (Ohmni report 005).
* Every fetch is verified against its own metadata (symbol, granularity, ordering,
  range). A refetch that disagrees with an earlier vintage is stored with
  ``drift_of`` set and reported; nothing is substituted silently.
* Pre-lock, a fetch is truncated to sessions strictly before the segment clock
  **before anything is written or printed** (the ceiling).
"""
from __future__ import annotations

import datetime as _dt
import json

import numpy as np
import pandas as pd

from .db import DB, Refused, canon, now_iso, sha
from .util import curl, day, ts

CHART = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits"


def _epoch(d: str) -> int:
    return int(ts(d).timestamp())


def fetch_yahoo(db: DB, symbol: str, from_date: str, to_date: str, ceiling: str | None) -> dict:
    """Fetch daily bars into a new vintage. ``ceiling`` drops sessions on/after it before storage."""
    url = CHART.format(sym=symbol, p1=_epoch(from_date), p2=_epoch(to_date) + 86400)
    raw = curl(url)
    try:
        doc = json.loads(raw)
        res = doc["chart"]["result"][0]
    except (ValueError, KeyError, TypeError, IndexError):
        err = None
        try:
            err = json.loads(raw)["chart"]["error"]
        except Exception:
            pass
        raise Refused(f"price fetch for {symbol} returned no result ({err or raw[:120]})")
    meta = res.get("meta") or {}
    tz = meta.get("exchangeTimezoneName") or "America/New_York"
    stamps = res.get("timestamp") or []
    q = (res.get("indicators") or {}).get("quote", [{}])[0]
    adj = ((res.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    dates = [pd.Timestamp(s, unit="s", tz="UTC").tz_convert(tz).strftime("%Y-%m-%d") for s in stamps]
    rows = []
    for i, d in enumerate(dates):
        c = (q.get("close") or [None] * len(dates))[i]
        if c is None:
            continue
        if ceiling is not None and d >= day(ceiling):
            continue  # truncated before anything reaches disk
        rows.append({"date": d, "open": (q.get("open") or [None] * len(dates))[i],
                     "high": (q.get("high") or [None] * len(dates))[i],
                     "low": (q.get("low") or [None] * len(dates))[i], "close": c,
                     "adjclose": adj[i] if adj else c,
                     "volume": (q.get("volume") or [None] * len(dates))[i]})
    # verify the payload against its own metadata
    problems = []
    if str(meta.get("symbol", "")).upper() != symbol.upper():
        problems.append(f"metadata symbol {meta.get('symbol')} != requested {symbol}")
    if meta.get("dataGranularity") not in (None, "1d"):
        problems.append(f"granularity {meta.get('dataGranularity')}")
    ds = [r["date"] for r in rows]
    if ds != sorted(set(ds)):
        problems.append("dates not strictly increasing")
    if problems:
        raise Refused(f"price payload for {symbol} failed verification: {problems}")
    payload = {"symbol": symbol, "rows": rows}
    phash = sha(canon(payload))
    md = {k: meta.get(k) for k in ("currency", "exchangeName", "instrumentType", "exchangeTimezoneName",
                                    "dataGranularity", "firstTradeDate")}
    # drift against the latest earlier vintage of this symbol, on overlapping dates
    drift_of, drift = None, []
    prev = db.rows("price_vintages", "symbol=?", (symbol,))
    if prev:
        p = prev[-1]
        old = {r["date"]: r["close"] for r in p["payload"]["rows"]}
        for r in rows:
            o = old.get(r["date"])
            if o is not None and abs(o - r["close"]) > 1e-6 * max(abs(o), 1):
                drift.append(r["date"])
        if drift:
            drift_of = p["vintage_id"]
    vid = f"V{len(db.rows('price_vintages')) + 1:05d}"
    db.append("price_vintages", vintage_id=vid, symbol=symbol, source="yahoo_v8_chart",
              retrieved_at=now_iso(), from_date=from_date,
              to_date=rows[-1]["date"] if rows else None, payload=payload, payload_hash=phash,
              metadata={**md, "ceiling": ceiling, "n": len(rows)}, drift_of=drift_of)
    return {"vintage_id": vid, "symbol": symbol, "n_sessions": len(rows),
            "first": rows[0]["date"] if rows else None, "last": rows[-1]["date"] if rows else None,
            "payload_hash": phash[:16], "drift_of": drift_of, "drift_dates": drift[:10],
            "ceiling": ceiling}


def vintages(view, symbol: str) -> list[dict]:
    rows = view.led("price_vintages", "symbol=?", (symbol,))
    allowed = (view.manifest or {}).get("vintage_ids")
    if allowed is not None:
        rows = [r for r in rows if r["vintage_id"] in allowed]
    return rows


def frame(view, symbol: str, before: str | None = None, after: str | None = None) -> pd.DataFrame:
    """Daily bars for a symbol from its vintages; later vintages win per date. Records use."""
    vs = vintages(view, symbol)
    if not vs:
        return pd.DataFrame(columns=["close", "adjclose", "volume"])
    merged = {}
    used = set()
    for v in vs:
        for r in v["payload"]["rows"]:
            merged[r["date"]] = r
            used.add(v["vintage_id"])
    if not hasattr(view, "read_vintages"):
        view.read_vintages = set()
    view.read_vintages |= used
    if not merged:  # a vintage can be empty (the source had no rows): no series, not a crash
        return pd.DataFrame(columns=["close", "adjclose", "volume"])
    df = pd.DataFrame(sorted(merged.values(), key=lambda r: r["date"])).set_index("date")
    if before is not None:
        df = df[df.index < day(before)]
    if after is not None:
        df = df[df.index > day(after)]
    return df


def returns(view, symbol: str, before: str, n: int | None = None) -> pd.Series:
    df = frame(view, symbol, before=before)
    if df.empty:
        return pd.Series(dtype=float)
    r = df["adjclose"].astype(float).pct_change().dropna()
    return r.iloc[-n:] if n else r


def price_on_or_after(view, symbol: str, d: str, field: str = "close"):
    """First session on/after date d: (date, price)."""
    df = frame(view, symbol)
    df = df[df.index >= day(d)]
    if df.empty:
        return None, None
    return df.index[0], float(df[field].iloc[0])


def last_before(view, symbol: str, d: str, field: str = "close"):
    df = frame(view, symbol, before=d)
    if df.empty:
        return None, None
    return df.index[-1], float(df[field].iloc[-1])


def block_bootstrap_quantile(x: np.ndarray, horizon: int, q: float, block: int, draws: int,
                             seed: int = 16) -> float:
    """Quantile of |sum of `horizon` returns| from a moving-block bootstrap. Deterministic."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < max(block, 2):
        return float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(horizon / block))
    starts = rng.integers(0, len(x) - block + 1, size=(draws, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(draws, -1)[:, :horizon]
    sums = x[idx].sum(axis=1)
    return float(np.quantile(np.abs(sums), q))


def adverse_quantile(x: np.ndarray, horizon: int, q: float, block: int, draws: int, side: int,
                     seed: int = 17) -> float:
    """Stress quantile of the adverse horizon move for a long (side=+1) or short (-1) holding."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < max(block, 2):
        return float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(horizon / block))
    starts = rng.integers(0, len(x) - block + 1, size=(draws, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(draws, -1)[:, :horizon]
    sums = x[idx].sum(axis=1) * side
    return float(max(-np.quantile(sums, 1 - q), 0.0))


def business_days_between(a: str, b: str) -> int:
    return int(np.busday_count(day(a), day(b)))


def next_session_after(view, symbol: str, knowable_from: str) -> tuple:
    """Backfill entry rule: the first close after the fact was public (§19.2).

    With a time-of-day before 16:00 New York, that day's close; otherwise (or date-only,
    where the time is unknown) the next session's close. No entry uses a price from
    before the fact was public (smoke 26).
    """
    t = pd.Timestamp(knowable_from)
    has_time = "T" in str(knowable_from) or " " in str(knowable_from).strip()
    if has_time:
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        ny = t.tz_convert("America/New_York")
        cutoff = ny.normalize() + pd.Timedelta(hours=16)
        first = ny.strftime("%Y-%m-%d") if ny < cutoff else (ny + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        first = (pd.Timestamp(day(knowable_from)) + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    return price_on_or_after(view, symbol, first)
