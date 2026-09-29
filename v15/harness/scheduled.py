"""v9 §A: scheduled facts get a feed.

Sources, all open: the holder's IR events page via a Wayback snapshot (A1), exchange filings that carry results dates
(EDGAR 8-K item 2.02 by filing date), and manual entry with the same ledger discipline. Facts land in node_facts as
kind `scheduled` with sched_kind, source_time = the scheduled date, knowable_from = snapshot or filing date. Never
overwritten: a moved date is a new row with supersedes. The catalyst-class predicate reads them per leg (A3)."""
import json
import re
import sqlite3
import urllib.request
from datetime import date, timedelta

from . import config
from .db import append, get_row
from .errors import NotFound, StateError, ValidationError
from .util import dumps, loads

KINDS = ("results", "agm", "capital_markets_day", "guidance", "other")
# v10 E1 sources in order; EDGAR 2.02 is hindsight only and never dates a leg
SOURCES = ("announcement", "ir_page", "edgar_202", "manual")
MECHANICAL_KINDS = ("results_announced", "index_rebalance", "expiry", "rebalance_window", "margin_date", "settlement", "other")
_ANNOUNCE = re.compile(r"\b(to|will|plans? to|expects? to|intends? to)\s+(report|release|announce|publish|host|hold)\b.{0,160}?"
                       r"\b(results|earnings|conference call|webcast)\b", re.I | re.S)
UA = "nomad-harness/0.1 (scheduled-facts ingest; contact bato2912@gmail.com)"
_KIND_WORDS = (
    ("agm", re.compile(r"\b(annual (general )?meeting|agm|annual shareholders?)\b", re.I)),
    ("capital_markets_day", re.compile(r"\b(capital markets day|investor day|analyst day|strategy update)\b", re.I)),
    ("guidance", re.compile(r"\b(guidance|outlook|trading (update|statement))\b", re.I)),
    ("results", re.compile(r"\b(earnings|results|quarter(ly)?|q[1-4]|fiscal|half[- ]year|interim|conference call|webcast)\b", re.I)),
)
_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_DATE_RES = (
    re.compile(rf"\b((?:{_MONTHS})[a-z]*\.?)\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I),      # August 5, 2026
    re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+((?:{_MONTHS})[a-z]*\.?)\s+(\d{{4}})\b", re.I),      # 5 August 2026
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),                                                     # 08/05/2026 (US)
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                                                          # 2026-08-05
)
_MONTH_NUM = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _month(tok: str) -> int | None:
    return _MONTH_NUM.get(tok.lower().rstrip(".")[:3])


def parse_dates(text: str) -> list[tuple[str, int]]:
    """All dated mentions in a text: (ISO date, char offset)."""
    out = []
    for i, rx in enumerate(_DATE_RES):
        for m in rx.finditer(text):
            try:
                if i == 0:
                    d = date(int(m.group(3)), _month(m.group(1)) or 0, int(m.group(2)))
                elif i == 1:
                    d = date(int(m.group(3)), _month(m.group(2)) or 0, int(m.group(1)))
                elif i == 2:
                    d = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                else:
                    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            out.append((d.isoformat(), m.start()))
    return sorted(set(out), key=lambda x: x[1])


def parse_events_page(text: str, window: int = 90) -> list[dict]:
    """Dated items on an IR events page: each date with a results/AGM/CMD/guidance word within `window` chars.
    Returns [{kind, date, text}] deduped by (kind, date)."""
    items: dict[tuple[str, str], dict] = {}
    for iso, pos in parse_dates(text):
        start = max(0, pos - window)
        ctx = text[start: pos + window]
        # the kind is the keyword nearest the date, not the first kind in priority order
        best = None
        for k, rx in _KIND_WORDS:
            for m in rx.finditer(ctx):
                dist = abs(start + m.start() - pos)
                if best is None or dist < best[0]:
                    best = (dist, k)
        if not best:
            continue
        kind = best[1]
        key = (kind, iso)
        if key not in items:
            items[key] = {"kind": kind, "date": iso, "text": re.sub(r"\s+", " ", ctx).strip()[:240]}
    return list(items.values())


def parse_announcement(text: str, published: str | None = None) -> list[dict]:
    """E1 first source: a results-date announcement ('to report ... results on August 12, 2026'). The announced date is
    the scheduled fact; the release date is when it became knowable."""
    out = []
    for m in _ANNOUNCE.finditer(text):
        seg = text[m.start(): m.end() + 120]
        for iso, _ in parse_dates(seg):
            if published and iso < published:
                continue
            out.append({"kind": "results", "date": iso, "knowable_from": published, "text": re.sub(r"\s+", " ", seg)[:240],
                        "source": "results-date announcement", "sched_source": "announcement"})
            break
    return out


def edgar_announcements(cik: str, fetch=_get, since: str | None = None, until: str | None = None, read_doc=True) -> list[dict]:
    """E1: 8-K filings whose text announces a results date (item 7.01/8.01 press releases), via EDGAR full-text search,
    by filing date. The primary document is read for the announced date."""
    n = int(re.sub(r"\D", "", cik))
    q = urllib.request.quote('"to report" OR "will report" OR "to release" OR "to announce" OR "conference call"')
    url = (f"https://efts.sec.gov/LATEST/search-index?q={q}&ciks={n:010d}&forms=8-K&dateRange=custom"
           + (f"&startdt={since}" if since else "") + (f"&enddt={until}" if until else ""))
    data = json.loads(fetch(url).decode("utf-8", "replace") or "{}")
    out = []
    for h in (data.get("hits") or {}).get("hits") or []:
        src = h.get("_source") or {}
        fdate = src.get("file_date")
        items = src.get("items") or ""
        if "2.02" in items:
            continue
        acc, _, fname = (h.get("_id") or "").partition(":")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{n}/{acc.replace('-', '')}/{fname}" if acc and fname else None
        if not read_doc or not doc_url:
            out.append({"kind": "results", "date": None, "knowable_from": fdate, "url": doc_url, "text": f"8-K {items} filed {fdate}", "sched_source": "announcement"})
            continue
        try:
            from .pit import _strip_html
            txt = _strip_html(fetch(doc_url).decode("utf-8", "replace"))
            for a in parse_announcement(txt, fdate):
                a.update({"url": doc_url, "source": f"EDGAR 8-K {items or '7.01/8.01'} results-date announcement"})
                out.append(a)
        except Exception as e:
            out.append({"kind": "results", "date": None, "knowable_from": fdate, "url": doc_url, "text": f"unread: {type(e).__name__}", "sched_source": "announcement"})
    return [o for o in out if o.get("date")]


def wire_announcements(items: list[dict], holder_names: list[str]) -> list[dict]:
    """E1: results-date announcements in a wire RSS pull (title + summary) matched to a holder by name."""
    out = []
    names = [n.lower() for n in holder_names if n]
    for it in items:
        text = f"{it.get('title', '')} {it.get('summary', '')}"
        if not any(n in text.lower() for n in names):
            continue
        for a in parse_announcement(text, it.get("published")):
            a.update({"url": it.get("link"), "source": "wire release (results-date announcement)"})
            out.append(a)
    return out


def edgar_results_dates(cik: str, fetch=_get, since: str | None = None, until: str | None = None) -> list[dict]:
    """8-K filings carrying item 2.02 (results of operations) from EDGAR's submissions API, by filing date.
    knowable_from = filing date: the fact that results landed on that date was public then."""
    n = int(re.sub(r"\D", "", cik))
    data = json.loads(fetch(f"https://data.sec.gov/submissions/CIK{n:010d}.json").decode("utf-8", "replace"))
    rec = (data.get("filings") or {}).get("recent") or {}
    out = []
    for form, fdate, items, acc, doc in zip(rec.get("form", []), rec.get("filingDate", []), rec.get("items", []),
                                            rec.get("accessionNumber", []), rec.get("primaryDocument", [])):
        if form not in ("8-K", "8-K/A") or "2.02" not in (items or ""):
            continue
        if since and fdate < since:
            continue
        if until and fdate > until:
            continue      # the time wall: a filing after as_of was not knowable as of as_of
        url = f"https://www.sec.gov/Archives/edgar/data/{n}/{acc.replace('-', '')}/{doc}"
        out.append({"kind": "results", "date": fdate, "knowable_from": fdate, "url": url, "hindsight": True, "sched_source": "edgar_202",
                    "text": f"8-K item 2.02 (results) filed {fdate} ({form}, items {items})", "source": "EDGAR 8-K item 2.02"})
    return out


# ---- ledger ------------------------------------------------------------------------------------------

def _current_scheduled(conn: sqlite3.Connection, holder_id: str | None = None) -> list[dict]:
    sql = "SELECT * FROM node_facts WHERE fact_type IN ('scheduled', 'mechanical')"
    args: list = []
    if holder_id:
        sql += " AND holder_id = ?"
        args.append(holder_id)
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY rowid", args)]
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    for r in rows:
        # rows written before v10 carry no flag: an EDGAR item 2.02 row is hindsight by construction
        if r.get("hindsight") is None:
            r["hindsight"] = int((r.get("source") or "").startswith("EDGAR 8-K item 2.02"))
            r["sched_source"] = r.get("sched_source") or ("edgar_202" if r["hindsight"] else None)
    return [r for r in rows if r["id"] not in superseded]


def scheduled_add(conn: sqlite3.Connection, holder_id: str, kind: str, date_: str, source: str,
                  knowable_from: str | None, url: str | None = None, text: str | None = None,
                  supersedes: str | None = None, node: str | None = None, hindsight: bool = False,
                  sched_source: str = "manual", fact_type: str = "scheduled") -> dict:
    from .names import resolve_holder
    if fact_type == "mechanical":
        if kind not in MECHANICAL_KINDS:
            raise ValidationError(f"a mechanical fact's kind must be one of {MECHANICAL_KINDS}")
    elif kind not in KINDS:
        raise ValidationError(f"kind must be one of {KINDS}")
    if sched_source not in SOURCES:
        raise ValidationError(f"sched_source must be one of {SOURCES}")
    try:
        date.fromisoformat(date_)
    except ValueError:
        raise ValidationError("date must be YYYY-MM-DD")
    if knowable_from:
        try:
            date.fromisoformat(knowable_from)
        except ValueError:
            raise ValidationError("knowable_from must be YYYY-MM-DD")
    if not source.strip():
        raise ValidationError("source is required (which page or filing says so)")
    h = resolve_holder(conn, holder_id)
    node = (node or f"{h.get('key') or h['normalised_name'].replace(' ', '_')}_calendar").strip()
    if supersedes:
        old = get_row(conn, "node_facts", supersedes, "node fact")
        if old["fact_type"] != "scheduled" or old["holder_id"] != h["id"]:
            raise ValidationError("supersedes must name a scheduled fact of the same holder (a moved date is a new row)")
    for r in _current_scheduled(conn, h["id"]):
        if r.get("sched_kind") == kind and r["source_time"] == date_ and r["fact_type"] == fact_type:
            # a forward source arriving after a hindsight row is new information: keep the earlier knowable_from
            if not hindsight and r.get("hindsight") and knowable_from and (r["knowable_from"] or "9999") > knowable_from:
                break
            return {"fact_id": r["id"], "holder_id": h["id"], "kind": kind, "date": date_, "created": False}
    row = append(conn, "node_facts", {
        "node": node, "holder_id": h["id"], "fact_type": fact_type, "sched_kind": kind,
        "text": (text or f"{kind}: {h['canonical_name']} {date_}").strip()[:2000], "url": url, "source": source.strip(),
        "source_time": date_, "knowable_from": knowable_from, "supersedes": supersedes, "hindsight": int(bool(hindsight)),
        "sched_source": sched_source,
    })
    return {"fact_id": row["id"], "holder_id": h["id"], "kind": kind, "date": date_, "created": True, "node": node}


def scheduled_for(conn: sqlite3.Connection, holder_ids: list[str], lo: str, hi: str, knowable_by: str | None = None) -> list[dict]:
    """Current (non-superseded) scheduled facts for holders with lo < date <= hi; knowable_by filters on knowable_from."""
    if not holder_ids:
        return []
    out = []
    for r in _current_scheduled(conn):
        if r["holder_id"] not in holder_ids or not r["source_time"]:
            continue
        if not (lo <= r["source_time"] <= hi):
            continue
        if knowable_by and (r["knowable_from"] or "9999") > knowable_by:
            continue
        h = conn.execute("SELECT canonical_name FROM holders WHERE id = ?", (r["holder_id"],)).fetchone()
        out.append({k: r[k] for k in ("id", "holder_id", "sched_kind", "text", "source", "source_time", "knowable_from", "url", "fact_type")}
                   | {"canonical_name": h["canonical_name"] if h else None, "hindsight": bool(r.get("hindsight")), "sched_source": r.get("sched_source"),
                      "same_day": r["source_time"] == lo})
    return sorted(out, key=lambda x: x["source_time"])


# ---- ingest (A2) -------------------------------------------------------------------------------------------

def _live_round_state(conn: sqlite3.Connection) -> str | None:
    r = conn.execute("SELECT state FROM round_state WHERE state IN ('created','locked','open') ORDER BY state_changed_at DESC LIMIT 1").fetchone()
    return r["state"] if r else None


def ingest_scheduled(conn: sqlite3.Connection, holder_ids: list[str] | None = None, as_of: str | None = None,
                     fetch=_get, sources: tuple[str, ...] = ("announcements", "ir", "edgar"), since_days: int = 400) -> dict:
    """For each listed holder: EDGAR 8-K 2.02 dates (if cik) and the IR events page as of a Wayback snapshot (if ir_url).
    New (holder, kind, date) triples are appended with knowable_from = filing or snapshot date. Existing rows are never
    touched. The IR page is read through Wayback only: live pages are refused while a round is created or locked (the time
    wall), and a Wayback read is dated by construction."""
    from .pit import wayback
    from .names import resolve_holder
    as_of = as_of or date.today().isoformat()
    since = (date.fromisoformat(as_of) - timedelta(days=since_days)).isoformat()
    if holder_ids:
        holders = [resolve_holder(conn, h) for h in holder_ids]
    else:
        holders = [dict(r) for r in conn.execute("SELECT * FROM holders WHERE listed = 1 ORDER BY rowid")]
    report = {"as_of": as_of, "holders": [], "new_facts": 0, "live_round_state": _live_round_state(conn)}
    for h in holders:
        entry = {"holder_id": h["id"], "holder": h["canonical_name"], "cik": h.get("cik"), "ir_url": h.get("ir_url"),
                 "announcements": None, "edgar": None, "ir": None, "new": 0, "items": 0}
        found: list[dict] = []
        if "announcements" in sources and h.get("cik"):
            try:
                items = edgar_announcements(h["cik"], fetch, since, until=as_of)
                found += items
                entry["announcements"] = {"ok": True, "items": len(items)}
            except Exception as e:
                entry["announcements"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
        if "edgar" in sources and h.get("cik"):
            try:
                items = edgar_results_dates(h["cik"], fetch, since, until=as_of)
                found += items
                entry["edgar"] = {"ok": True, "items": len(items), "hindsight": True}
            except Exception as e:
                entry["edgar"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
        if "ir" in sources and h.get("ir_url"):
            try:
                snap = wayback(h["ir_url"], as_of, fetch)
                if snap["found"]:
                    items = parse_events_page(snap["text"])
                    for it in items:
                        it.update({"knowable_from": snap["snapshot_date"], "url": snap["snapshot_url"], "sched_source": "ir_page",
                                   "source": f"IR events page via Wayback snapshot {snap['snapshot_date']}"})
                    found += items
                    entry["ir"] = {"ok": True, "snapshot_date": snap["snapshot_date"], "items": len(items)}
                else:
                    entry["ir"] = {"ok": False, "error": snap.get("reason")}
            except Exception as e:
                entry["ir"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
        entry["items"] = len(found)
        for it in found:
            r = scheduled_add(conn, h["id"], it["kind"], it["date"], it["source"], it.get("knowable_from"),
                              url=it.get("url"), text=it.get("text"), hindsight=bool(it.get("hindsight")),
                              sched_source=it.get("sched_source") or "manual")
            if r["created"]:
                entry["new"] += 1
                report["new_facts"] += 1
        report["holders"].append(entry)
    return report


# ---- A3: catalyst per leg ---------------------------------------------------------------------------------------

def _neighbours(conn: sqlite3.Connection, holder_id: str) -> set[str]:
    out = {holder_id}
    h = conn.execute("SELECT parent_id FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if h and h["parent_id"]:
        out.add(h["parent_id"])
    out.update(r["id"] for r in conn.execute("SELECT id FROM holders WHERE parent_id = ?", (holder_id,)))
    return out


def leg_holders(conn: sqlite3.Connection, round_id: str, leg: dict) -> set[str]:
    """Holders at degree <= 1 on the leg: the leg's holder(s), their parent and children, and every touched-set holder
    at degree <= 1 on the same node. v10 E2: the wide read is deliberate. Every statement by a degree-0/1 holder is
    surfaced; whether it dates the leg is decided by `concerns_node` on the link, and a statement that does not concern
    the node is recorded as a tide candidate rather than hidden."""
    ids: set[str] = set()
    if leg.get("synthetic"):
        for c in leg.get("components", []):
            ids |= _neighbours(conn, c["holder_id"])
    else:
        ids |= _neighbours(conn, leg["holder_id"])
    node = (leg.get("node") or "").lower()
    for r in conn.execute("SELECT holder_id FROM touched_set WHERE round_id = ? AND degree <= 1 AND lower(node) = ?", (round_id, node)):
        ids.add(r["holder_id"])
    return ids


# ---- v10 E2: scheduled links ------------------------------------------------------------------------------------------

def link_fact(conn: sqlite3.Connection, round_id: str, position_id: str, fact_id: str, concerns_node: bool, basis: str) -> dict:
    """Set by the operator at lock with basis: the statement is by a degree-0/1 holder and the node is a named segment
    or material input of that holder (concerns_node = true); otherwise the fact is a tide candidate on the leg."""
    from .rounds import round_state
    if round_state(conn, round_id) in ("scored", "void"):
        raise StateError("links are set on a live round (before or after lock), never on a scored one")
    get_row(conn, "node_facts", fact_id, "node fact")
    if not (conn.execute("SELECT 1 FROM positions WHERE id = ?", (position_id,)).fetchone()
            or conn.execute("SELECT 1 FROM synthetic_legs WHERE id = ?", (position_id,)).fetchone()):
        raise ValidationError("position_id must be a positions row or a synthetic leg")
    if not basis.strip():
        raise ValidationError("basis is required: why the node is (or is not) a named segment or material input of the statement's holder")
    row = append(conn, "scheduled_links", {"round_id": round_id, "position_id": position_id, "fact_id": fact_id,
                                           "concerns_node": int(bool(concerns_node)), "basis": basis.strip()})
    return {"link_id": row["id"], "concerns_node": bool(concerns_node)}


def links_for(conn: sqlite3.Connection, round_id: str, position_ids: list[str]) -> dict[str, dict]:
    """Latest link per fact for the leg's position rows."""
    if not position_ids:
        return {}
    q = ",".join("?" for _ in position_ids)
    out = {}
    for r in conn.execute(f"SELECT * FROM scheduled_links WHERE round_id = ? AND position_id IN ({q}) ORDER BY rowid", [round_id, *position_ids]):
        out[r["fact_id"]] = dict(r)
    return out


def catalyst_for_leg(conn: sqlite3.Connection, round_id: str, leg: dict, event_date: str,
                     window_days: int | None = None) -> dict:
    window_days = window_days or config.SCORING_WINDOW_DAYS[None]
    hi = (date.fromisoformat(event_date) + timedelta(days=window_days)).isoformat()
    ids = sorted(leg_holders(conn, round_id, leg))
    facts = scheduled_for(conn, ids, event_date, hi)
    pos_ids = leg.get("all_position_ids") or leg.get("position_ids") or ([leg["synthetic_id"]] if leg.get("synthetic_id") else [])
    links = links_for(conn, round_id, pos_ids)
    # v10 E1/E2: hindsight rows never date a leg; a scheduled fact dates a positive leg only with concerns_node = true;
    # mechanical facts (I5) date the leg as ACKs do; everything else on the leg is a tide candidate
    dating, tides, undecided, same_day = [], [], [], []
    for f in facts:
        if f["hindsight"]:
            continue
        if f["same_day"]:
            same_day.append(f)          # a statement on the event day is a clock for the event_day cell, never a forward catalyst
            continue
        link = links.get(f["id"])
        if f["fact_type"] == "mechanical" or (link and link["concerns_node"]):
            dating.append(f | {"dated_by": f["fact_type"], "link_basis": link["basis"] if link else None})
        elif link:
            tides.append(f | {"link_basis": link["basis"]})
        else:
            undecided.append(f)
    observed = dating
    claimable = [f for f in observed if (f["knowable_from"] or "9999") <= event_date]
    return {"holders_considered": ids, "window": [event_date, hi], "facts": facts, "dating": dating, "tide_candidates": tides,
            "undecided": undecided, "same_day": same_day, "holds_claimable": bool(claimable), "holds_observed": bool(observed),
            "claimable_basis": (f"computed: {claimable[0]['sched_kind']} ({claimable[0]['dated_by']}) for {claimable[0]['canonical_name']} on {claimable[0]['source_time']} "
                                f"(knowable {claimable[0]['knowable_from']}; concerns_node)" if claimable
                                else ("computed: no scheduled fact concerning the node knowable by the event date"
                                      + (f"; {len(tides)} tide candidate(s)" if tides else "") + (f"; {len(undecided)} fact(s) awaiting a concerns_node link" if undecided else "")
                                      + (f"; {len(same_day)} same-day statement(s)" if same_day else ""))),
            "observed_basis": (f"computed: {observed[0]['sched_kind']} ({observed[0]['dated_by']}) for {observed[0]['canonical_name']} on {observed[0]['source_time']}"
                               if observed else "computed: no fact concerning the node in the window"
                               + (f"; {len(tides)} tide candidate(s)" if tides else ""))}


def catalyst_check(conn: sqlite3.Connection, round_id: str, write: bool = False) -> dict:
    """Per leg (natural and synthetic): does the catalyst-class predicate hold from the scheduled-facts store?
    write=true appends predicate_checks rows (claimed from what was knowable by the event date, observed from
    everything) on a live round; a scored round only ever gets the dry-run report."""
    from .basket import event_basket
    from .predicates import resolve_predicate
    from .rounds import round_state
    state = round_state(conn, round_id)
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    b = event_basket(conn, round_id)
    legs = []
    for l in b["legs"] + b["synthetics"]:
        pid = l["synthetic_id"] if l.get("synthetic") else next(iter(l.get("position_ids") or []), None)
        c = catalyst_for_leg(conn, round_id, l, ev["event_date"])
        cur = l.get("arming_status")
        would = ("armed_dated" if c["holds_observed"] and cur in ("gate_pass_undated", "armed_dated") else cur)
        legs.append({"leg": l.get("holder") or f"synthetic:{l.get('rule')}", "position_id": pid, "synthetic": bool(l.get("synthetic")),
                     "arming_status": cur, "arming_status_if_dated": would, "tide_candidate_count": len(c["tide_candidates"]), **c})
    written = []
    if write:
        if state == "scored":
            raise StateError(f"round {round_id} is scored: the catalyst check is a dry-run report there; nothing is rewritten")
        pred = resolve_predicate(conn, "pred.arm.catalyst_class")
        for l in legs:
            if not l["position_id"]:
                continue
            row = append(conn, "predicate_checks", {
                "round_id": round_id, "predicate_id": pred["id"],
                "claimed": "holds" if l["holds_claimable"] else "fails",
                "observed": "holds" if l["holds_observed"] else "fails",
                "note": "v9 A3 / v10 E2: computed from the scheduled-facts store with concerns_node links"
                        + (f"; tide candidates: {[t['canonical_name'] + ' ' + t['source_time'] for t in l['tide_candidates']]}" if l["tide_candidates"] else ""),
                "scope": None, "basis": l["claimable_basis"] + "; observed: " + l["observed_basis"], "position_id": l["position_id"]})
            written.append(row["id"])
    return {"round_id": round_id, "state": state, "event_date": ev["event_date"], "legs": legs,
            "legs_dated_claimable": sum(1 for l in legs if l["holds_claimable"]),
            "legs_dated_observed": sum(1 for l in legs if l["holds_observed"]),
            "legs_with_tide_candidates": sum(1 for l in legs if l["tide_candidates"]),
            "written": written, "dry_run": not write}


def backfill_report(conn: sqlite3.Connection, round_ids: list[str], fetch=_get, ingest: bool = True,
                    as_of: str | None = None) -> dict:
    """A4: populate scheduled facts for the listed holders those rounds touched (from filings and IR snapshots as of
    each round's event date, so knowable_from is honest), then re-evaluate catalyst per leg. Report only; no rescoring."""
    out = {"rounds": [], "ingest": [], "legs_would_be_dated": 0, "legs_would_be_dated_claimable": 0}
    for rid in round_ids:
        rd = get_row(conn, "rounds", rid, "round")
        ev = get_row(conn, "events", rd["event_id"], "event")
        listed = [r["holder_id"] for r in conn.execute(
            "SELECT DISTINCT t.holder_id FROM touched_set t JOIN holders h ON h.id = t.holder_id WHERE t.round_id = ? AND h.listed = 1", (rid,))]
        if ingest and listed:
            rep = ingest_scheduled(conn, listed, as_of=as_of or (date.fromisoformat(ev["event_date"]) + timedelta(days=config.SCORING_WINDOW_DAYS[None])).isoformat(), fetch=fetch)
            out["ingest"].append({"round_id": rid, "new_facts": rep["new_facts"], "holders": rep["holders"]})
        c = catalyst_check(conn, rid, write=False)
        out["rounds"].append({"round_id": rid, "event_date": ev["event_date"], "listed_holders": len(listed),
                              "legs": len(c["legs"]), "legs_dated_observed": c["legs_dated_observed"],
                              "legs_dated_claimable": c["legs_dated_claimable"],
                              "detail": [{k: l[k] for k in ("leg", "synthetic", "arming_status", "arming_status_if_dated", "holds_claimable", "holds_observed")}
                                         for l in c["legs"]]})
        out["legs_would_be_dated"] += c["legs_dated_observed"]
        out["legs_would_be_dated_claimable"] += c["legs_dated_claimable"]
    out["note"] = "the cost of not having had the feed: legs that would have carried a date; nothing is rescored"
    return out


def coverage(conn: sqlite3.Connection, today: str | None = None) -> dict:
    """F: fraction of listed holders in the names book with >= 1 future scheduled fact in store."""
    today = today or date.today().isoformat()
    listed = [dict(r) for r in conn.execute("SELECT id, canonical_name, key FROM holders WHERE listed = 1 ORDER BY rowid")]
    future = {r["holder_id"] for r in _current_scheduled(conn) if (r["source_time"] or "") > today}
    covered = [h for h in listed if h["id"] in future]
    return {"listed_holders": len(listed), "with_future_scheduled_fact": len(covered),
            "coverage": (round(len(covered) / len(listed), 6) if listed else None),
            "covered": [h["key"] or h["canonical_name"] for h in covered], "as_of": today}
