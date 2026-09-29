"""v12 §0.1: a real daily-close carrier.

Every price observation on rounds 8-10 used 6-10 sessions scraped from whatever closes happened to be in a round's
evidence. A short-window two-sigma band on a small cap is very wide, so the only thing that could register as
out-of-band was a catastrophe: the engine was detecting disasters, not re-encodes. This module fetches real daily
closes so the pre-registered 20-session band can actually be computed.

Price is still an outcome only. Nothing here proposes a leg: it is read after a call's due date or while scoring, and
it is the same measurement a narrative row is."""
import json
import sqlite3
import urllib.request
from datetime import date, datetime, timedelta, timezone

from . import config
from .errors import ValidationError

UA = "Mozilla/5.0 (compatible; nomad-harness/0.1; +price series)"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"
CARRIER_KEY = "carrier.daily_closes"

# exchange -> Yahoo suffix. The names book already carries the exchange for every listed holder.
SUFFIX = {"NYSE": "", "NASDAQ": "", "XETRA": ".DE", "HEL": ".HE", "JSE": ".JO", "OSL": ".OL", "STO": ".ST",
          "WSE": ".WA", "BIT": ".MI", "CPH": ".CO", "LSE": ".L", "Euronext Paris": ".PA", "NSE": ".NS", "SGX": ".SI",
          "Santiago": ".SN", "TSX": ".TO", "ASX": ".AX",
          # v13: the Asian listings round 13 needs. "SSE" is Shanghai here, not Santiago -- the earlier map had it
          # pointing at .SN, which would have silently priced a Chinese respondent off a Chilean ticker.
          "SSE": ".SS", "SZSE": ".SZ", "TYO": ".T", "HKEX": ".HK", "KRX": ".KS", "TWSE": ".TW"}


def _get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def symbol_for(holder: dict) -> str | None:
    """Yahoo symbol from the names book: an explicit price_symbol wins, else ticker + exchange suffix."""
    if holder.get("price_symbol"):
        return holder["price_symbol"]
    t, ex = holder.get("ticker"), holder.get("exchange")
    if not t or ex not in SUFFIX:
        return None
    return t.replace(".", "-") + SUFFIX[ex] if SUFFIX[ex] else t.replace(".", "-")


def series(symbol: str, from_: str, to: str, fetch=_get) -> dict:
    """{currency, rows: [{date, close, volume}]} over [from_, to] inclusive, trading days only.

    v13 B1 needs volume and the listing currency as well as the close: a band is only worth reading on a series that
    trades, and turnover is the only way to say so across listings priced in pesos, pence and dollars."""
    p1 = int(datetime.fromisoformat(from_).replace(tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.fromisoformat(to).replace(tzinfo=timezone.utc).timestamp()) + 86400
    data = json.loads(fetch(CHART.format(sym=urllib.parse.quote(symbol), p1=p1, p2=p2)).decode("utf-8", "replace"))
    res = ((data.get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise ValidationError(f"no chart data for {symbol!r}")
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    vols = q.get("volume") or []
    rows = []
    for i, (t, c) in enumerate(zip(ts, q.get("close") or [])):
        if c is None:
            continue
        v = vols[i] if i < len(vols) else None
        rows.append({"date": datetime.fromtimestamp(t, timezone.utc).date().isoformat(), "close": float(c),
                     "volume": (float(v) if v is not None else None)})
    return {"currency": (res.get("meta") or {}).get("currency"), "rows": rows}


def closes(symbol: str, from_: str, to: str, fetch=_get) -> list[dict]:
    """[{date, close}] over [from_, to] inclusive, trading days only."""
    return series(symbol, from_, to, fetch)["rows"]


def turnover_usd(rows: list[dict], currency: str | None) -> tuple[float | None, str]:
    """Median daily turnover in dollars, for the liquidity qualifier only. The FX table is static and dated: it is
    never allowed near a claim, only near the question of whether a series is thick enough to read."""
    vals = [r["close"] * r["volume"] for r in rows if r.get("volume")]
    if not vals:
        return None, "the series carries no volume, so the turnover floor cannot be applied"
    fx = config.FX_TO_USD.get(currency or "")
    med = sorted(vals)[len(vals) // 2]
    if fx is None:
        return None, f"median daily turnover {round(med):,} {currency or 'in the listing currency'}; no FX for it in the pre-registered table"
    return round(med * fx, 2), f"median daily turnover {round(med * fx):,} USD ({currency} at {fx}, table dated 2026-09-01)"


def band_for(symbol: str, event_date: str, sessions: int | None = None, fetch=_get) -> dict:
    """The pre-registered band from the closes ending on the last trading day before the event.

    v13 B1: the method is the empirical trailing distribution over sixty sessions, with the parametric band kept behind
    `config.BAND_METHOD` so an old row can still be re-derived. The turnover of the same window rides along, because a
    band on a series that barely trades is a number without a claim behind it."""
    from .risk import band_from
    sessions = sessions or (config.BAND_SESSIONS_EMPIRICAL if config.BAND_METHOD == "empirical" else config.BAND_SESSIONS)
    start = (date.fromisoformat(event_date) - timedelta(days=int(sessions * 2.2) + 10)).isoformat()
    ser = series(symbol, start, event_date, fetch)
    prior = [c for c in ser["rows"] if c["date"] < event_date]
    if len(prior) < 11:
        raise ValidationError(f"{symbol}: only {len(prior)} close(s) before {event_date}; cannot compute a band")
    xs = [c["close"] for c in prior][-(sessions + 1):]
    b = band_from(xs)
    turn, turn_basis = turnover_usd(prior[-(sessions + 1):], ser["currency"])
    reliable = None if turn is None else turn >= config.TURNOVER_FLOOR_USD
    b.update({"symbol": symbol, "reference_close": xs[-1], "reference_date": prior[-1]["date"],
              "sessions_available": len(xs) - 1, "pre_registered_sessions": sessions, "currency": ser["currency"],
              "turnover_usd": turn, "turnover_basis": turn_basis, "band_reliable": reliable,
              "band_method": b["band_method"] + f", closes ending {prior[-1]['date']} (pre-registered: {sessions} sessions, "
                                                f"{config.BAND_METHOD}; turnover floor {config.TURNOVER_FLOOR_USD:,.0f} USD)"})
    return b


def window_closes(symbol: str, event_date: str, until: str, fetch=_get) -> list[dict]:
    """Closes from the event date to `until` inclusive: the window a re-encode can happen in."""
    return [c for c in closes(symbol, event_date, until, fetch) if c["date"] >= event_date]


def seed_carrier(conn: sqlite3.Connection) -> dict:
    from .carriers import carrier_upsert, path_set
    r = carrier_upsert(conn, "daily closes (chart API)", "price_assessment", "open",
                       "v12 §0.1: free daily closes for US, German, Nordic, JSE, LSE and Euronext listings; the only "
                       "carrier the pre-registered 20-session band can be computed from", CARRIER_KEY)
    conn.execute("UPDATE carriers SET node_kinds = ?, url = ? WHERE id = ?",
                 (json.dumps(["listed_company", "refinery", "petrochemical", "chemical", "power", "metals", "mining", "shipping"]),
                  "https://query1.finance.yahoo.com/v8/finance/chart/", r["carrier_id"]))
    try:
        path_set(conn, CARRIER_KEY, "live", "ok", url="https://query1.finance.yahoo.com/v8/finance/chart/")
    except Exception:
        pass
    return r


def backfill_round(conn: sqlite3.Connection, round_id: str, fetch=_get, write: bool = True, horizon_days: int | None = None) -> dict:
    """§0.1: for every listed leg of a round, compute the real band and write one observation per trading day in the
    window. Attribution is never invented: these are unattributed observations, so they change bands and out-of-band
    counts, and they can only become re-encodes where the round's evidence attributes a move to the event."""
    from .basket import round_legs
    from .db import get_row
    from .risk import price_observe
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    horizon = (date.fromisoformat(ev["event_date"]) + timedelta(days=horizon_days or config.DUE_AT_MAX_DAYS)).isoformat()
    today = date.today().isoformat()
    until = min(horizon, today)
    out = {"round_id": round_id, "event_date": ev["event_date"], "until": until, "legs": [], "observations": 0, "out_of_band": 0}
    for leg in round_legs(conn, round_id):
        if not leg["listed"]:
            continue
        h = get_row(conn, "holders", leg["holder_id"], "holder")
        sym = symbol_for(h)
        entry = {"holder": leg["holder"], "symbol": sym, "observations": 0, "out_of_band": 0, "error": None}
        if not sym:
            entry["error"] = "no ticker/exchange in the names book"
            out["legs"].append(entry)
            continue
        try:
            b = band_for(sym, ev["event_date"], fetch=fetch)
            # the band is a one-day band: the return distribution from the pre-registered window before the event,
            # applied to the prior close and tested against each day's close. A fixed level band applied across a
            # 90-day window measures drift, not a re-encode, which is what the first cut of this backfill got wrong.
            ser = series(sym, (date.fromisoformat(ev["event_date"]) - timedelta(days=10)).isoformat(), until, fetch=fetch)
            rows = ser["rows"]
            lo_r, hi_r = b.get("pctile_low"), b.get("pctile_high")
            if lo_r is None:      # parametric fallback, kept so an old row can be reproduced
                lo_r, hi_r = -config.BAND_SIGMA * b["stdev"], config.BAND_SIGMA * b["stdev"]
            entry.update({"sessions": b["sessions_available"], "band_pct": round((hi_r - lo_r) / 2 * 100, 3),
                          "currency": b.get("currency"), "turnover_usd": b.get("turnover_usd"),
                          "band_reliable": b.get("band_reliable"), "method": config.BAND_METHOD})
            pid = (leg["all_position_ids"] or [None])[0]
            for i, c in enumerate(rows):
                if c["date"] < ev["event_date"] or i == 0:
                    continue
                prev = rows[i - 1]["close"]
                lo, hi = round(prev * (1 + lo_r), 6), round(prev * (1 + hi_r), 6)
                method = (f"{b['sessions_available']}-session {config.BAND_METHOD} band "
                          f"[{round(lo_r * 100, 3)}%, {round(hi_r * 100, 3)}%] applied to the prior close {prev}")
                if not write:
                    entry["observations"] += 1
                    entry["out_of_band"] += int(c["close"] < lo or c["close"] > hi)
                    continue
                o = price_observe(conn, round_id, pid, f"daily closes ({sym})", c["date"], c["close"], False,
                                  band_low=lo, band_high=hi, band_method=method,
                                  note="v13 §B1 backfill: pre-registered one-day empirical band; unattributed by construction",
                                  scoring=True, band_reliable=b.get("band_reliable"), turnover_usd=b.get("turnover_usd"))
                entry["observations"] += 1
                entry["out_of_band"] += int(o["out_of_band"])
                entry["unreliable"] = entry.get("unreliable", 0) + int(b.get("band_reliable") is False)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"[:160]
        out["legs"].append(entry)
        out["observations"] += entry["observations"]
        out["out_of_band"] += entry["out_of_band"]
    return out
