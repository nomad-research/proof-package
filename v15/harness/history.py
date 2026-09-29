"""v9 §B1/B2: node-level first traversal is computed, not noted.

`node_history(node, as_of)` returns recorded disruptions on the node from the ledger (prior rounds' events on the node,
node_facts of the disruption kinds) plus whatever the open incident registries the fetcher can read for the node kind
return. Q1b fails on any disruption in the prior 90 days or three or more in the prior 12 months."""
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, timedelta

from .util import loads, normalise_name

DISRUPTION_KINDS = ("outage", "closure", "incident", "strike", "force_majeure")
GENERIC = {"supply", "output", "access", "handling", "port", "node", "market", "sector", "complex", "plant", "site",
           "refinery", "facility", "terminal", "yard", "dock", "the", "and", "of", "at", "in"}
Q1B_RECENT_DAYS = 90
Q1B_YEAR_MAX = 3      # fails at >= this many in 12 months
UA = "nomad-harness/0.1 (incident registry reader)"

# Open incident registries by node kind. Each reader returns dated incidents with a source url, and says which fetch
# path served it. Seeded with the registry round 8 used (TCEQ STEERS air emission events); port notices and grid outage
# logs read the feeds already configured for the daily ingest (they land in node_facts, so the ledger side sees them).
REGISTRIES: tuple[dict, ...] = (
    {"key": "registry.tceq_steers", "name": "TCEQ STEERS air emission events", "node_kinds": ("refinery", "petrochemical", "chemical"),
     "carrier_key": "carrier.tceq_emissions",
     "url": "https://www2.tceq.texas.gov/oce/eer/index.cfm?fuseaction=main.getlist&pgm=EER&search_type=regulated_entity&regulated_entity_name={q}",
     "reader": "tceq"},
    {"key": "registry.port_notices", "name": "port notice archives (ingest feeds)", "node_kinds": ("port", "shipping"),
     "carrier_key": "carrier.port_notices", "url": None, "reader": "ledger_feed"},
    {"key": "registry.grid_outage_log", "name": "grid-operator outage logs (ingest feeds)", "node_kinds": ("power", "grid"),
     "carrier_key": "carrier.grid_operator", "url": None, "reader": "ledger_feed"},
    {"key": "registry.illinois_epa", "name": "Illinois EPA news releases", "node_kinds": ("chemical", "petrochemical", "refinery"),
     "carrier_key": "carrier.illinois_epa", "url": "https://epa.illinois.gov/about-us/news.html", "reader": "ilepa"},
    {"key": "registry.nrc_foia", "name": "National Response Center incident reports (quarterly FOIA spreadsheet)",
     "node_kinds": ("chemical", "petrochemical", "refinery", "port", "shipping"), "carrier_key": "carrier.nrc_reports",
     "url": "https://nrc.uscg.mil/FOIAFiles/Current.xlsx", "reader": "nrc"},
)


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def node_tokens(node: str) -> set[str]:
    toks = {t for t in re.split(r"[\s_\-/,:()]+", (node or "").lower()) if len(t) >= 3}
    return toks - GENERIC


def _matches(query_tokens: set[str], other: str) -> bool:
    ot = node_tokens(other)
    if not query_tokens or not ot:
        return False
    return query_tokens <= ot or ot <= query_tokens


def _holder_ids_for(conn: sqlite3.Connection, node: str) -> set[str]:
    """Holders the node text resolves to (alias match) plus holders holding positions on matching nodes."""
    ids: set[str] = set()
    norm = normalise_name(node)
    if norm:
        ids.update(r["holder_id"] for r in conn.execute("SELECT DISTINCT holder_id FROM aliases WHERE alias_norm = ?", (norm,)))
    q = node_tokens(node)
    for r in conn.execute("SELECT DISTINCT holder_id, node FROM positions"):
        if _matches(q, r["node"]):
            ids.add(r["holder_id"])
    # plants of a matched company and the company of a matched plant
    for hid in list(ids):
        h = conn.execute("SELECT parent_id FROM holders WHERE id = ?", (hid,)).fetchone()
        if h and h["parent_id"]:
            ids.add(h["parent_id"])
    return ids


def _text_mentions(query_tokens: set[str], text: str) -> bool:
    low = (text or "").lower()
    return bool(query_tokens) and all(t in low for t in query_tokens)


# ---- registry readers -----------------------------------------------------------------------------------------

_TCEQ_ROW = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})[^\n]{0,400}?(?:emission|event|upset|startup|shutdown|maintenance|flar)", re.I)


def _strip(html: str) -> str:
    from .pit import _strip_html
    return _strip_html(html)


def read_tceq(query: str, fetch=_get, as_of: str | None = None) -> dict:
    """TCEQ STEERS list page for a regulated entity name: dated rows. Live first; Wayback of the same url if blocked."""
    from .pit import wayback
    url = REGISTRIES[0]["url"].format(q=urllib.parse.quote(query))
    incidents, path, error = [], None, None
    try:
        text = _strip(fetch(url).decode("utf-8", "replace"))
        path = "live"
    except Exception as e:
        error = f"live: {type(e).__name__}: {e}"[:160]
        try:
            snap = wayback(url, as_of or date.today().isoformat(), fetch)
            if snap["found"]:
                text, path = snap["text"], f"wayback:{snap['snapshot_date']}"
            else:
                text, path = "", None
                error += f"; wayback: {snap.get('reason')}"
        except Exception as e2:
            text, path = "", None
            error += f"; wayback: {type(e2).__name__}: {e2}"[:160]
    for m in _TCEQ_ROW.finditer(text):
        mm, dd, yy = m.group(1).split("/")
        try:
            d = date(int(yy), int(mm), int(dd)).isoformat()
        except ValueError:
            continue
        incidents.append({"date": d, "kind": "outage", "text": re.sub(r"\s+", " ", m.group(0))[:240], "url": url,
                          "source": REGISTRIES[0]["name"], "from": "registry"})
    return {"registry": REGISTRIES[0]["key"], "path_served": path, "error": error, "incidents": incidents, "url": url}


_DATE_ANY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b")
_MONTHS = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"))}


def _iso_from_match(m) -> str | None:
    try:
        if m.group(1):
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()
        if m.group(4):
            return date(int(m.group(4)), int(m.group(5)), int(m.group(6))).isoformat()
        return date(int(m.group(9)), _MONTHS[m.group(7)], int(m.group(8))).isoformat()
    except (ValueError, KeyError):
        return None


def _live_or_wayback(url: str, fetch, as_of: str | None) -> tuple[str, str | None, str | None]:
    """(text, path_served, error): live first, the nearest Wayback snapshot on failure (v10 F: Wayback-first for the 403 set is
    the registry marking live blocked; this helper falls back either way)."""
    from .pit import wayback
    try:
        return _strip(fetch(url).decode("utf-8", "replace")), "live", None
    except Exception as e:
        err = f"live: {type(e).__name__}: {e}"[:160]
        try:
            snap = wayback(url, as_of or date.today().isoformat(), fetch)
            if snap["found"]:
                return snap["text"], f"wayback:{snap['snapshot_date']}", err
            return "", None, err + f"; wayback: {snap.get('reason')}"
        except Exception as e2:
            return "", None, err + f"; wayback: {type(e2).__name__}: {e2}"[:120]


def read_ilepa(query: str, fetch=_get, as_of: str | None = None) -> dict:
    """Illinois EPA news releases: dated items mentioning the query tokens (enforcement referrals, incident responses)."""
    reg = next(r for r in REGISTRIES if r["key"] == "registry.illinois_epa")
    text, path, err = _live_or_wayback(reg["url"], fetch, as_of)
    toks = node_tokens(query)
    incidents = []
    for m in _DATE_ANY.finditer(text):
        d = _iso_from_match(m)
        ctx = text[max(0, m.start() - 40): m.end() + 260]
        if d and (not toks or any(t in ctx.lower() for t in toks)) and re.search(r"fire|release|spill|leak|explosion|referral|violation|seal order|incident", ctx, re.I):
            incidents.append({"date": d, "kind": "incident", "text": re.sub(r"\s+", " ", ctx)[:240], "url": reg["url"], "source": reg["name"], "from": "registry"})
    return {"registry": reg["key"], "path_served": path, "error": err, "incidents": incidents, "url": reg["url"]}


def read_nrc(query: str, fetch=_get, as_of: str | None = None, state: str | None = None) -> dict:
    """NRC quarterly FOIA spreadsheet: rows whose location or description carries the query tokens (needs openpyxl)."""
    import io
    reg = next(r for r in REGISTRIES if r["key"] == "registry.nrc_foia")
    incidents, err, path = [], None, None
    try:
        import openpyxl
        data = fetch(reg["url"], 60)
        path = "live"
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        toks = node_tokens(query)
        for ws in wb.worksheets:
            header = None
            for row in ws.iter_rows(values_only=True):
                if header is None:
                    header = [str(c or "").strip().upper() for c in row]
                    continue
                rec = dict(zip(header, row))
                blob = " ".join(str(v) for v in rec.values() if v is not None).lower()
                if state and str(rec.get("LOCATION_STATE") or rec.get("STATE") or "").upper() != state.upper():
                    continue
                if toks and not any(t in blob for t in toks):
                    continue
                raw = rec.get("INCIDENT_DATE_TIME") or rec.get("INCIDENT DATE") or rec.get("DATE_TIME_RECEIVED") or ""
                d = str(raw)[:10].replace("/", "-")
                try:
                    d = date.fromisoformat(d).isoformat()
                except ValueError:
                    m = _DATE_ANY.search(str(raw))
                    d = _iso_from_match(m) if m else None
                if d:
                    incidents.append({"date": d, "kind": "incident", "text": (str(rec.get("DESCRIPTION_OF_INCIDENT") or rec.get("DESCRIPTION") or blob))[:240],
                                      "url": reg["url"], "source": reg["name"] + (f" #{rec.get('SEQNOS')}" if rec.get("SEQNOS") else ""), "from": "registry"})
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:160]
    return {"registry": reg["key"], "path_served": path, "error": err, "incidents": incidents, "url": reg["url"]}


def registry_coverage(node_kind: str | None) -> list[str]:
    """v13 B3: which registries in the reader set claim to cover this node kind. Empty is the answer that matters."""
    if not node_kind:
        return []
    return [r["key"] for r in REGISTRIES if node_kind in r["node_kinds"]]


def read_registries(conn: sqlite3.Connection, node: str, node_kind: str | None, fetch=_get, as_of: str | None = None) -> list[dict]:
    """Readers for the node kind. Feed-backed registries are already in node_facts (ledger side), so they report status only."""
    out = []
    query = " ".join(sorted(node_tokens(node))) or node
    # a resolvable holder name is a better registry query than node tokens
    for hid in _holder_ids_for(conn, node):
        h = conn.execute("SELECT canonical_name, kind FROM holders WHERE id = ?", (hid,)).fetchone()
        if h and h["kind"] in ("plant", "facility"):
            query = h["canonical_name"]
            break
    for reg in REGISTRIES:
        if node_kind and node_kind not in reg["node_kinds"]:
            continue
        if not node_kind and reg["reader"] != "tceq":
            continue
        if reg["reader"] == "tceq":
            out.append(read_tceq(query, fetch, as_of))
        elif reg["reader"] == "ilepa":
            out.append(read_ilepa(query, fetch, as_of))
        elif reg["reader"] == "nrc":
            out.append(read_nrc(query, fetch, as_of))
        else:
            out.append({"registry": reg["key"], "path_served": "ledger", "error": None, "incidents": [],
                        "note": "feed-backed: items arrive through nomad-harness ingest into node_facts and are counted on the ledger side"})
    return out


# ---- the computed history ---------------------------------------------------------------------------------------

def node_history(conn: sqlite3.Connection, node: str, as_of: str | None = None, node_kind: str | None = None,
                 registries: bool = True, fetch=_get, exclude_round_id: str | None = None) -> dict:
    """Recorded disruptions on a node up to as_of (exclusive of as_of itself when it is the event date)."""
    as_of = as_of or date.today().isoformat()
    q = node_tokens(node)
    holders = _holder_ids_for(conn, node)
    incidents: list[dict] = []
    seen: set[tuple] = set()

    def add(d: str | None, kind: str, text: str, url: str | None, source: str, origin: str, round_id: str | None = None):
        if not d or d >= as_of:
            return
        key = (d, (text or "")[:60].lower())
        if key in seen:
            return
        seen.add(key)
        incidents.append({"date": d, "kind": kind, "text": (text or "")[:240], "url": url, "source": source, "from": origin, "round_id": round_id})

    # prior rounds: events on the node (by node field, holder, or text mention)
    for r in conn.execute("SELECT r.id AS round_id, e.* FROM rounds r JOIN events e ON e.id = r.event_id "
                          "JOIN round_state s ON s.round_id = r.id WHERE s.state != 'void' ORDER BY e.event_date"):
        if exclude_round_id and r["round_id"] == exclude_round_id:
            continue
        hit = (r["node"] and _matches(q, r["node"])) or _text_mentions(q, r["event_text"])
        if hit:
            add(r["event_date"], r["event_kind"] or "incident", r["event_text"], None, "ledger: prior round", "ledger", r["round_id"])
    # node facts of the disruption kinds on matching nodes or holders
    ks = ",".join("?" for _ in DISRUPTION_KINDS)
    for f in conn.execute(f"SELECT * FROM node_facts WHERE fact_type IN ({ks}) ORDER BY rowid", DISRUPTION_KINDS):
        if _matches(q, f["node"]) or (f["holder_id"] and f["holder_id"] in holders) or _text_mentions(q, f["text"]):
            add(f["source_time"] or (f["knowable_from"] or "")[:10] or None, f["fact_type"], f["text"], f["url"], f["source"], "ledger")
    reg_reports = []
    if registries:
        if node_kind is None:
            r = conn.execute("SELECT node_kind FROM events WHERE node IS NOT NULL AND node_kind IS NOT NULL ORDER BY rowid DESC").fetchall()
            node_kind = next((x["node_kind"] for x in r if _matches(q, conn.execute("SELECT node FROM events WHERE node_kind = ? LIMIT 1", (x["node_kind"],)).fetchone()["node"])), None)
        try:
            reg_reports = read_registries(conn, node, node_kind, fetch, as_of)
        except Exception as e:
            reg_reports = [{"registry": "error", "error": f"{type(e).__name__}: {e}"[:160], "incidents": [], "path_served": None}]
        for rep in reg_reports:
            for inc in rep.get("incidents", []):
                add(inc["date"], inc["kind"], inc["text"], inc.get("url"), inc["source"], "registry")
    incidents.sort(key=lambda x: x["date"])
    return {"node": node, "as_of": as_of, "tokens": sorted(q), "holders_matched": sorted(holders), "incidents": incidents,
            "registries": [{k: r.get(k) for k in ("registry", "path_served", "error", "note")} | {"incidents": len(r.get("incidents", []))} for r in reg_reports],
            "n": len(incidents)}


def q1b(conn: sqlite3.Connection, node: str, event_date: str, node_kind: str | None = None, registries: bool = True,
        fetch=_get, exclude_round_id: str | None = None, override: dict | None = None) -> dict:
    """B2: fails on any disruption in the prior 90 days or >= 3 in the prior 12 months. A human override needs a basis."""
    hist = node_history(conn, node, event_date, node_kind, registries, fetch, exclude_round_id)
    d = date.fromisoformat(event_date)
    lo90, lo365 = (d - timedelta(days=Q1B_RECENT_DAYS)).isoformat(), (d - timedelta(days=365)).isoformat()
    recent = [i for i in hist["incidents"] if lo90 <= i["date"] < event_date]
    year = [i for i in hist["incidents"] if lo365 <= i["date"] < event_date]
    value = "fail" if (recent or len(year) >= Q1B_YEAR_MAX) else "pass"
    text = (f"{value}: computed; {len(recent)} disruption(s) in the prior {Q1B_RECENT_DAYS} days, {len(year)} in the prior 12 months"
            + ("" if hist["n"] else "; nothing recorded on the ledger" + (" or in reachable registries" if registries else "")))
    # v13 B3: a pass on no data is worse than an unknown. Round 12 returned "nothing in reachable registries" for the
    # node with the year's best-reported mining fatality in its history, because no registry covers mining at all. That
    # is a statement about our reach, and it was phrased as one about the world.
    covered = registry_coverage(node_kind)
    if value == "pass" and not hist["n"] and not covered:
        value = "unknown"
        text = (f"unknown: computed; nothing on the ledger for this node and no registry in the reader set covers node "
                f"kind {node_kind or 'unknown'}, so first traversal at the node is unanswered rather than confirmed")
    out = {"value": value, "computed": value, "text": text, "in_90d": len(recent), "in_12m": len(year),
           "incidents": year or hist["incidents"][-5:], "registries": hist["registries"], "holders_matched": hist["holders_matched"], "override": None}
    if override:
        ov, basis = str(override.get("value", "")).lower(), (override.get("basis") or "").strip()
        if ov not in ("pass", "fail"):
            raise ValueError("q1b override value must be pass or fail")
        if not basis:
            raise ValueError("a Q1b override needs a basis: the specific observation that contradicts the computed count")
        out["value"] = ov
        out["text"] = f"{ov}: human override (computed {value}: {len(recent)} in 90d, {len(year)} in 12m); basis: {basis}"
        out["override"] = {"value": ov, "basis": basis}
    return out
