"""D1/D2: coverage is a property of carriers, not rounds. A registry of the channels calls are scored on, with access."""
import re
import sqlite3

from .db import insert_mutable
from .errors import ValidationError
from .util import now_iso

KINDS = ("price_assessment", "notice_feed", "filing", "newspaper", "index", "transcript")
ACCESS = ("open", "paywalled", "blocked", "unknown")
# v9 D1: per carrier, per fetch path {status, last_checked}. Q7 and the lock-time check read the best path.
PATHS = ("live", "wayback", "pit_api")
PATH_STATUS = ("ok", "blocked", "timeout", "unknown")
PATH_SEED: dict[str, dict] = {
    "carrier.tceq_emissions": {"live": "blocked", "wayback": "ok", "url": "https://www2.tceq.texas.gov/oce/eer/index.cfm"},
    "carrier.company_ir": {"live": "blocked", "wayback": "ok", "url": "https://investor.phillips66.com/events-and-presentations/default.aspx"},
    "carrier.bp_com": {"live": "blocked", "url": "https://www.bp.com/en/global/corporate/news-and-insights.html"},
    "carrier.exchange_filings": {"live": "ok", "pit_api": "ok", "url": "https://data.sec.gov/submissions/CIK0001534701.json"},
    "carrier.eia": {"live": "ok", "url": "https://www.eia.gov/petroleum/weekly/"},
}

# What seven rounds have taught. Names are matched as case-insensitive substrings of a call's carrier text.
NODE_KINDS = ("port", "shipping", "power", "grid", "refinery", "petrochemical", "chemical", "agriculture", "metals", "mining",
              "listed_company", "regulator", "other")

SEED: tuple[dict, ...] = (
    {"key": "carrier.company_ir", "name": "company IR page", "kind": "notice_feed", "access": "open",
     "note": "producers post force majeure and outage notices to their own sites; Wayback snapshots them (free dated notice feed)",
     "node_kinds": ["refinery", "petrochemical", "chemical", "power", "metals", "mining", "listed_company"]},
    {"key": "carrier.tceq_emissions", "name": "TCEQ emissions event", "kind": "notice_feed", "access": "open",
     "note": "Texas STEERS air emissions event reports: dated, unit-level, public", "node_kinds": ["refinery", "petrochemical", "chemical"]},
    {"key": "carrier.eia", "name": "EIA", "kind": "index", "access": "open", "note": "weekly petroleum status, refinery inputs, spot prices",
     "node_kinds": ["refinery", "power"]},
    {"key": "carrier.grid_operator", "name": "grid operator notices", "kind": "notice_feed", "access": "open", "node_kinds": ["power", "grid"]},
    {"key": "carrier.energy_regulator", "name": "energy regulator", "kind": "notice_feed", "access": "open", "node_kinds": ["power", "grid", "regulator"]},
    {"key": "carrier.usda", "name": "USDA", "kind": "notice_feed", "access": "open", "node_kinds": ["agriculture"]},
    {"key": "carrier.lme_cme_delayed", "name": "LME/CME delayed prices", "kind": "price_assessment", "access": "open", "node_kinds": ["metals", "agriculture"]},
    {"key": "carrier.icis", "name": "ICIS", "kind": "price_assessment", "access": "paywalled", "note": "rounds 2, 5, 7: restart, FM and local pricing sit behind it",
     "node_kinds": ["petrochemical", "chemical"]},
    {"key": "carrier.chemweek", "name": "ChemWeek", "kind": "newspaper", "access": "paywalled", "note": "chemical trade press"},
    {"key": "carrier.loadstar", "name": "Loadstar", "kind": "newspaper", "access": "paywalled", "note": "container logistics press"},
    {"key": "carrier.flows", "name": "Flows", "kind": "newspaper", "access": "paywalled", "note": "Antwerp port and logistics press"},
    {"key": "carrier.bp_com", "name": "bp.com", "kind": "filing", "access": "blocked", "note": "round 5: blocked to the fetcher"},
    {"key": "carrier.port_notices", "name": "port notices", "kind": "notice_feed", "access": "open", "note": "port authority and terminal advisories",
     "node_kinds": ["port", "shipping"]},
    {"key": "carrier.terminal_notices", "name": "terminal notices", "kind": "notice_feed", "access": "open"},
    {"key": "carrier.argus_headlines", "name": "Argus", "kind": "price_assessment", "access": "open", "note": "headline tables only"},
    {"key": "carrier.exchange_filings", "name": "exchange filings", "kind": "filing", "access": "open", "note": "SENS, RNS, EDGAR, company releases",
     "node_kinds": ["listed_company", "refinery", "petrochemical", "chemical", "power", "metals", "mining", "shipping"]},
    {"key": "carrier.sens", "name": "SENS", "kind": "filing", "access": "open"},
    {"key": "carrier.owner_statements", "name": "owner statements", "kind": "filing", "access": "open", "note": "company media releases"},
    {"key": "carrier.jse_closes", "name": "JSE close", "kind": "index", "access": "open", "note": "daily closes from public history pages"},
    {"key": "carrier.war_risk_quotes", "name": "war-risk premium quotes", "kind": "price_assessment", "access": "unknown", "note": "round 1: quoted in press, no direct series"},
    {"key": "carrier.trade_press", "name": "trade press", "kind": "newspaper", "access": "unknown", "note": "generic; name the outlet"},
    {"key": "carrier.chemorbis", "name": "ChemOrbis", "kind": "price_assessment", "access": "paywalled", "note": "free view carries headlines only"},
    {"key": "carrier.plastics_sa", "name": "Plastics SA", "kind": "notice_feed", "access": "open", "note": "round 7: silent on the event"},
)


def seed_carriers(conn: sqlite3.Connection) -> int:
    from .util import dumps
    n = 0
    for c in SEED:
        row = dict(c)
        if row.get("node_kinds"):
            row["node_kinds"] = dumps(row["node_kinds"])
        ex = conn.execute("SELECT id, node_kinds FROM carriers WHERE key = ?", (c["key"],)).fetchone()
        if ex:
            if row.get("node_kinds") and not ex["node_kinds"]:
                conn.execute("UPDATE carriers SET node_kinds = ? WHERE id = ?", (row["node_kinds"], ex["id"]))
            continue
        insert_mutable(conn, "carriers", {**row, "last_checked": now_iso()[:10]})
        n += 1
    return n


def seed_fetch_paths(conn: sqlite3.Connection) -> int:
    """D1 seed: round 8's TCEQ and company-IR entries become live blocked, wayback ok. Only fills what is unset."""
    from .util import dumps, loads
    n = 0
    for key, spec in PATH_SEED.items():
        r = conn.execute("SELECT id, fetch_paths, url FROM carriers WHERE key = ?", (key,)).fetchone()
        if not r:
            continue
        paths = loads(r["fetch_paths"]) if r["fetch_paths"] else {}
        changed = False
        for path in PATHS:
            if path in spec and path not in paths:
                paths[path] = {"status": spec[path], "last_checked": "seed"}
                changed = True
        url = r["url"] or spec.get("url")
        if changed or url != r["url"]:
            conn.execute("UPDATE carriers SET fetch_paths = ?, url = ? WHERE id = ?", (dumps(paths), url, r["id"]))
            n += 1
    return n


def fetch_paths(row: dict) -> dict:
    """v13: a reader must not crash on a malformed value. A v12 host registration wrote a bare list here, and every
    caller of open_for_kind died on it a version later, which is how a convenience column takes out enumeration."""
    from .util import loads
    fp = row.get("fetch_paths")
    val = (loads(fp) if isinstance(fp, str) and fp else fp) or {}
    return val if isinstance(val, dict) else {}


def best_path(row: dict) -> dict:
    """The best known fetch path: ok beats unknown beats timeout beats blocked. No recorded path = nominal access."""
    paths = fetch_paths(row)
    rank = {"ok": 3, "unknown": 2, "timeout": 1, "blocked": 0}
    best, best_status = None, None
    for path in PATHS:
        st = (paths.get(path) or {}).get("status")
        if st and (best_status is None or rank.get(st, -1) > rank.get(best_status, -1)):
            best, best_status = path, st
    if best is None:
        return {"path": None, "status": "nominal", "reachable": row.get("access") == "open" and None}
    return {"path": best, "status": best_status, "reachable": best_status == "ok"}


def reachability(row: dict) -> str:
    """open | unreachable | unknown for one carrier, reading the best path before the nominal access."""
    bp = best_path(row)
    if bp["status"] == "ok":
        return "open"
    if bp["path"] is not None:      # paths recorded and none ok
        return "unreachable" if bp["status"] in ("blocked", "timeout") else "unknown"
    return {"open": "open", "paywalled": "unreachable", "blocked": "unreachable"}.get(row.get("access"), "unknown")


def path_set(conn: sqlite3.Connection, key_or_name: str, path: str, status: str, url: str | None = None,
             checked: str | None = None) -> dict:
    from .util import dumps
    if path not in PATHS:
        raise ValidationError(f"path must be one of {PATHS}")
    if status not in PATH_STATUS:
        raise ValidationError(f"status must be one of {PATH_STATUS}")
    r = conn.execute("SELECT * FROM carriers WHERE key = ? OR lower(name) = lower(?)", (key_or_name, key_or_name)).fetchone()
    if not r:
        raise ValidationError(f"no carrier {key_or_name!r}; see nomad_carriers")
    paths = fetch_paths(dict(r))
    paths[path] = {"status": status, "last_checked": checked or now_iso()[:10]}
    conn.execute("UPDATE carriers SET fetch_paths = ?, url = COALESCE(?, url), last_checked = ? WHERE id = ?",
                 (dumps(paths), url, now_iso()[:10], r["id"]))
    row = dict(conn.execute("SELECT * FROM carriers WHERE id = ?", (r["id"],)).fetchone())
    return {"carrier": row["name"], "key": row["key"], "fetch_paths": fetch_paths(row), "best_path": best_path(row), "reachability": reachability(row)}


def probe(conn: sqlite3.Connection, key_or_name: str, url: str | None = None, fetch=None, timeout: int = 15) -> dict:
    """Try the live path and the Wayback availability api for a carrier's url; record both."""
    import urllib.parse
    import urllib.request
    from .pit import _get
    fetch = fetch or _get
    r = conn.execute("SELECT * FROM carriers WHERE key = ? OR lower(name) = lower(?)", (key_or_name, key_or_name)).fetchone()
    if not r:
        raise ValidationError(f"no carrier {key_or_name!r}")
    url = url or r["url"]
    if not url:
        raise ValidationError(f"carrier {r['name']} has no url to probe; pass one")
    out = {"carrier": r["name"], "url": url, "live": None, "wayback": None}
    try:
        fetch(url, timeout)
        out["live"] = "ok"
    except Exception as e:
        out["live"] = "timeout" if "timed out" in str(e).lower() else "blocked"
        out["live_error"] = f"{type(e).__name__}: {e}"[:160]
    try:
        import json
        q = urllib.parse.urlencode({"url": url})
        data = json.loads(fetch(f"https://archive.org/wayback/available?{q}", timeout).decode("utf-8", "replace"))
        out["wayback"] = "ok" if ((data.get("archived_snapshots") or {}).get("closest") or {}).get("available") else "blocked"
    except Exception as e:
        out["wayback"] = "timeout" if "timed out" in str(e).lower() else "blocked"
        out["wayback_error"] = f"{type(e).__name__}: {e}"[:160]
    for path in ("live", "wayback"):
        path_set(conn, key_or_name, path, out[path], url=url)
    row = dict(conn.execute("SELECT * FROM carriers WHERE id = ?", (r["id"],)).fetchone())
    out["best_path"] = best_path(row)
    out["reachability"] = reachability(row)
    return out


def path_health(conn: sqlite3.Connection) -> dict:
    """F: carriers by best-path status."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM carriers ORDER BY name")]
    by: dict[str, list[str]] = {}
    for r in rows:
        bp = best_path(r)
        label = f"{bp['path'] or 'nominal'}:{bp['status']}"
        by.setdefault(label, []).append(r["key"] or r["name"])
    return {"carriers": len(rows), "by_best_path": by,
            "reachable": sum(1 for r in rows if reachability(r) == "open"),
            "unreachable": sum(1 for r in rows if reachability(r) == "unreachable"),
            "unknown": sum(1 for r in rows if reachability(r) == "unknown")}


def open_for_kind(conn: sqlite3.Connection, node_kind: str) -> dict:
    """Selection weights toward carrier density: an event qualifies only if its node kind has open carriers."""
    from .util import loads
    if node_kind not in NODE_KINDS:
        raise ValidationError(f"node_kind must be one of {NODE_KINDS}")
    rows = [dict(r) for r in conn.execute("SELECT * FROM carriers ORDER BY name")]
    for r in rows:
        r["node_kinds"] = loads(r["node_kinds"]) if r["node_kinds"] else []
        r["reachability"] = reachability(r)
    matching = [r for r in rows if node_kind in r["node_kinds"]]
    open_ = [r["name"] for r in matching if r["reachability"] == "open"]
    closed = [r["name"] for r in matching if r["reachability"] == "unreachable"]
    return {"node_kind": node_kind, "open_carriers": open_, "closed_carriers": closed, "qualifies": bool(open_),
            "note": None if open_ else "no open carrier for this node kind in the registry: sacrifice obscurity before scoreability"}


def carrier_upsert(conn: sqlite3.Connection, name: str, kind: str, access: str, note: str | None = None,
                   key: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValidationError(f"kind must be one of {KINDS}")
    if access not in ACCESS:
        raise ValidationError(f"access must be one of {ACCESS}")
    if not name.strip():
        raise ValidationError("name is required")
    r = conn.execute("SELECT id FROM carriers WHERE lower(name) = lower(?) OR (key IS NOT NULL AND key = ?)", (name.strip(), key)).fetchone()
    if r:
        conn.execute("UPDATE carriers SET kind = ?, access = ?, note = COALESCE(?, note), last_checked = ? WHERE id = ?",
                     (kind, access, note, now_iso()[:10], r["id"]))
        return {"carrier_id": r["id"], "name": name.strip(), "access": access, "updated": True}
    row = insert_mutable(conn, "carriers", {"key": key, "name": name.strip(), "kind": kind, "access": access, "note": note,
                                            "last_checked": now_iso()[:10]})
    return {"carrier_id": row["id"], "name": name.strip(), "access": access, "updated": False}


def list_carriers(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM carriers ORDER BY name"):
        d = dict(r)
        d["fetch_paths"] = fetch_paths(d)
        d["best_path"] = best_path(d)
        d["reachability"] = reachability(d)
        out.append(d)
    return out


def resolve(conn: sqlite3.Connection, carrier_text: str | None) -> dict:
    """Match a call's carrier text against the registry. status: open | unreachable | unknown | unregistered."""
    text = (carrier_text or "").lower()
    matched = [dict(r) for r in conn.execute("SELECT * FROM carriers ORDER BY length(name) DESC")
               if r["name"].lower() in text or (r["key"] and r["key"].lower() in text)]
    if not text.strip():
        return {"status": "unregistered", "matched": [], "carrier": carrier_text}
    if not matched:
        return {"status": "unregistered", "matched": [], "carrier": carrier_text}
    # v9 D1: the best fetch path decides, not the nominal access
    reach = {reachability(m) for m in matched}
    if "open" in reach:
        status = "open"
    elif reach == {"unreachable"}:
        status = "unreachable"
    else:
        status = "unknown"
    return {"status": status, "matched": [{"name": m["name"], "kind": m["kind"], "access": m["access"],
                                           "best_path": best_path(m), "reachability": reachability(m)} for m in matched],
            "carrier": carrier_text}


def check(conn: sqlite3.Connection, carriers: list[str]) -> dict:
    rows = [resolve(conn, c) for c in carriers]
    flagged = [r for r in rows if r["status"] == "unreachable"]
    return {"carriers": rows, "carrier_unreachable": [r["carrier"] for r in flagged],
            "q7_computed": q7_for(rows), "note": "name a fallback carrier for each unreachable one before lock"}


def q7_for(rows: list[dict]) -> str | None:
    """fail when a majority of calls have only unreachable carriers; pass when a majority are open; else None."""
    if not rows:
        return None
    n = len(rows)
    unreachable = sum(1 for r in rows if r["status"] == "unreachable")
    open_ = sum(1 for r in rows if r["status"] == "open")
    if unreachable * 2 > n:
        return f"fail: computed at lock; {unreachable} of {n} calls name only paywalled or blocked carriers"
    if open_ * 2 > n:
        return f"pass: computed at lock; {open_} of {n} calls name an open carrier"
    return None


PRICE_SERIES = re.compile(r"\b(price|prices|index|indices|assessment|assessments|close|closes|futures|spread|spreads|"
                          r"rate|rates|quote|quotes|yield|yields|differential|differentials|premia|premium|premiums)\b", re.I)


def is_price_series(conn: sqlite3.Connection | None, carrier_text: str) -> bool:
    """F1: a narrative row's carrier is a channel that says things, never a series that prints numbers."""
    if PRICE_SERIES.search(carrier_text or ""):
        return True
    if conn is not None:
        m = resolve(conn, carrier_text)["matched"]
        if m and all(x["kind"] in ("price_assessment", "index") for x in m):
            return True
    return False
