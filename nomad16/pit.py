"""The point-in-time fetcher (§26 ``nomad_pit_fetch``), bounded by the round's clock.

Pre-lock, nothing dated after the segment clock is fetched, saved or printed. On a
backfilled walk the bound moves one date at a time: a read may go at most one day past
the frontier, and each read advances it (§14). Once the walk has ended (``live``) the
bound lifts for scoring.

Sources: ``nrc_en`` (daily Event Notification Report), ``nrc_status`` (daily Power
Reactor Status Report), ``edgar_filings`` / ``edgar_doc`` (filings by filing date),
``wayback`` (latest capture at or before as_of). Alternative data lives in ``altdata``.
"""
from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re

from .db import DB, ROOT, Refused, sha
from .rounds import clock as seg_clock, current_segment, state
from .util import curl, day, ts

NRC_EN = ("https://www.nrc.gov/documents-reports/document-collections/events-reports-associated-with/"
          "event-notification-reports/{y}/{ymd}en")
NRC_PS = ("https://www.nrc.gov/documents-reports/document-collections/events-reports-associated-with/"
          "power-reactor-status-reports/{y}/{ymd}ps")


SEC_UA = "nomad-research bato2912@gmail.com"  # SEC requires a contact user agent; override with NOMAD_SEC_UA


def sec_ua() -> str:
    return os.environ.get("NOMAD_SEC_UA") or SEC_UA


def bound(db: DB, round_id: str, as_of: str) -> str:
    """Return the effective as_of, or refuse if it is past what the round may read."""
    st = state(db, round_id)
    if st in {"live", "scored"}:
        return as_of
    if st == "pre_lock":
        c = seg_clock(db, round_id)
        if day(as_of) > day(c):
            raise Refused(f"pre-lock: nothing after the segment clock {day(c)} may be read (asked {day(as_of)})")
        return as_of
    if st == "walking":
        from .walk import frontier, pending_hit
        hit = pending_hit(db, round_id)
        if hit and day(as_of) > hit:
            raise Refused(f"walking: a walk_scan hit on {hit} is unresolved. Read that document, then either "
                          f"fire the ACK (ack_fire) or record it as not delivering (walk_read with result "
                          f"not_delivering); nothing after {hit} is readable until then (§14)")
        f = frontier(db, round_id)
        nxt = (ts(day(f)) + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if day(as_of) > nxt:
            raise Refused(f"walking: read forward one date at a time; the frontier is {day(f)}, "
                          f"so the furthest readable date is {nxt} (asked {day(as_of)})")
        return as_of
    raise Refused(f"round is '{st}'; point-in-time reads happen from reveal onward")


def _advance(db, round_id, d, carrier):
    if state(db, round_id) == "walking":
        from .walk import frontier
        if ts(day(d)) > ts(day(frontier(db, round_id))):
            db.append("notes", round_id=round_id, segment_idx=current_segment(db, round_id)["idx"],
                      subject="walk_read", text=f"{day(d)} | {carrier} | read | auto")


def _save(db, round_id, source, name, content: str, url, knowable_from, carrier, summary):
    d = ROOT / "rounds" / round_id / "fetched"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content)
    n = len(db.rows("evidence")) + 1
    eid = f"EV{n:05d}"
    db.append("evidence", evidence_id=eid, round_id=round_id, url=url, source=source,
              source_time=knowable_from, knowable_from=knowable_from, carrier=carrier,
              retrieved_pre_lock=state(db, round_id) == "pre_lock", path=str(p.relative_to(ROOT)),
              content_hash=sha(content), summary=summary[:500])
    return eid


def _log(db, round_id, source, target, as_of, reason, status, evidence_id=None, detail=None):
    db.append("pit_fetches", round_id=round_id, source=source, target=target, as_of=as_of, reason=reason,
              status=status, evidence_id=evidence_id, detail=detail)


def _text(h: str) -> list[str]:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    s = re.sub(r"<(br|/tr|/p|/div|/td|/th|/h\d)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    lines = [re.sub(r"\s+", " ", l).strip() for l in s.splitlines()]
    return [l for l in lines if l]


def parse_en(page: str) -> list[dict]:
    """Split a daily Event Notification Report into events: header fields, the unit-info
    table (power reactors), and the event text whose first line is the event's title."""
    k = page.find("EVENT REPORTS FOR")
    lines = _text(page[k:]) if k >= 0 else []
    end = next((i for i, l in enumerate(lines) if l == "Return to top"), len(lines))
    lines = lines[:end]
    keys = {"Facility", "Licensee", "Rep Org", "Region", "State", "Unit", "RX Type", "NRC Notified By",
            "HQ OPS Officer", "Notification Date", "Notification Time", "Event Date", "Event Time",
            "Last Update Date", "Emergency Class", "10 CFR Section", "City", "County", "License #",
            "Agreement", "Docket", "Person (Organization)"}
    events, cur, mode, pending = [], None, "fields", None
    for i, l in enumerate(lines):
        if l.startswith("Event Number:"):
            if cur:
                events.append(cur)
            cur = {"category": lines[i - 1] if i > 0 else None, "event_number": l.split(":", 1)[1].strip(),
                   "fields": {}, "unit_info": [], "text": []}
            mode, pending = "fields", None
            continue
        if cur is None:
            continue
        if l == "Event Text":
            mode = "text"
            continue
        if mode == "text":
            cur["text"].append(l)
            continue
        if l == "Power Reactor Unit Info":
            mode = "unit"
            continue
        if mode == "unit":
            cur["unit_info"].append(l)
            continue
        m = re.match(r"^([A-Za-z0-9 #/()]+):\s*(.*)$", l)
        if m and m.group(1).strip() in keys:
            key, val = m.group(1).strip(), m.group(2).strip()
            cur["fields"][key] = val
            pending = key if not val else None
        elif pending:
            cur["fields"][pending] = (cur["fields"][pending] + " " + l).strip()
    if cur:
        events.append(cur)
    for e in events:
        e["title"] = e["text"][0] if e["text"] else ""
        e["text"] = "\n".join(e["text"])
        ui = e.pop("unit_info")
        hdr = ["Unit", "SCRAM Code", "RX Crit", "Initial PWR", "Initial RX Mode", "Current PWR", "Current RX Mode"]
        if ui[:len(hdr)] == hdr:
            vals = ui[len(hdr):]
            e["units"] = [dict(zip(hdr, vals[j:j + len(hdr)])) for j in range(0, len(vals) - len(hdr) + 1, len(hdr))]
    return events


def parse_status(page: str) -> list[dict]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S | re.I):
        cells = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        if len(cells) >= 2 and cells[1].isdigit():
            rows.append({"unit": cells[0], "power": int(cells[1]),
                         "down": cells[2] if len(cells) > 2 else "",
                         "reason": cells[3] if len(cells) > 3 else "",
                         "changed": cells[4] if len(cells) > 4 else "",
                         "scrams": cells[5] if len(cells) > 5 else ""})
    return rows


def pit_fetch(db: DB, round_id: str, source: str, target: str, as_of: str, reason: str) -> dict:
    if not reason:
        raise Refused("every point-in-time fetch states its reason")
    as_of = bound(db, round_id, as_of)
    if source in {"nrc_en", "nrc_status"}:
        d = day(target)
        if d > day(as_of):
            raise Refused(f"target date {d} is after as_of {day(as_of)}")
        bound(db, round_id, d)
        url = (NRC_EN if source == "nrc_en" else NRC_PS).format(y=d[:4], ymd=d.replace("-", ""))
        try:
            page = curl(url)
        except Refused as e:
            _log(db, round_id, source, target, as_of, reason, "not_found", detail=str(e))
            _advance(db, round_id, d, source)
            return {"source": source, "date": d, "status": "no report for this date", "detail": str(e)}
        if source == "nrc_en":
            evs = parse_en(page)
            content = json.dumps(evs, indent=1)
            summary = "; ".join(f"{e['event_number']} {e['fields'].get('Facility') or e['fields'].get('Licensee')}: {e['title']}"
                                for e in evs)
            eid = _save(db, round_id, source, f"{d}_en.json", content, url, d, "nrc_event_notification", summary)
            out = {"events": evs}
        else:
            rows = parse_status(page)
            content = json.dumps(rows, indent=1)
            eid = _save(db, round_id, source, f"{d}_ps.json", content, url, d, "nrc_power_reactor_status",
                        f"{len(rows)} units")
            out = {"units": rows}
        _log(db, round_id, source, target, as_of, reason, "ok", eid)
        _advance(db, round_id, d, source)
        return {"source": source, "date": d, "evidence_id": eid, "knowable_from": d, **out}
    if source == "edgar_filings":
        cik = str(int(target))
        doc = json.loads(curl(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", ua=sec_ua()))
        rec = doc.get("filings", {}).get("recent", {})
        rows = []
        for i, fd in enumerate(rec.get("filingDate", [])):
            if fd <= day(as_of):  # filtered in memory: later filings are never saved or printed
                rows.append({"form": rec["form"][i], "filing_date": fd, "accession": rec["accessionNumber"][i],
                             "primary_doc": rec["primaryDocument"][i],
                             "description": rec.get("primaryDocDescription", [""] * (i + 1))[i],
                             "items": rec.get("items", [""] * (i + 1))[i]})
        content = json.dumps({"cik": cik, "name": doc.get("name"), "as_of": day(as_of), "filings": rows[:400]}, indent=1)
        eid = _save(db, round_id, source, f"edgar_{cik}_asof_{day(as_of)}.json", content,
                    f"data.sec.gov/submissions/CIK{int(cik):010d}.json", day(as_of), "edgar",
                    f"{doc.get('name')}: {len(rows)} filings on or before {day(as_of)}")
        _log(db, round_id, source, target, as_of, reason, "ok", eid)
        _advance(db, round_id, as_of, source)
        return {"source": source, "cik": cik, "name": doc.get("name"), "evidence_id": eid,
                "filings": rows[:60], "n": len(rows)}
    if source == "edgar_doc":
        # target: "<cik>/<accession>/<primary_doc>"
        try:
            cik, acc, prim = target.split("/", 2)
        except ValueError:
            raise Refused("edgar_doc target is '<cik>/<accession>/<primary_doc>'")
        doc = json.loads(curl(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", ua=sec_ua()))
        rec = doc.get("filings", {}).get("recent", {})
        fd = None
        for i, a in enumerate(rec.get("accessionNumber", [])):
            if a == acc:
                fd = rec["filingDate"][i]
        if fd is None:
            raise Refused("accession not found in the filer's recent filings; can't verify its filing date")
        if fd > day(as_of):
            _log(db, round_id, source, target, as_of, reason, "refused_post_clock")
            raise Refused(f"filing dated {fd} is after as_of {day(as_of)}; it may not be opened")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{prim}"
        page = curl(url, ua=sec_ua())
        text = "\n".join(_text(page))
        eid = _save(db, round_id, source, f"edgar_{acc}.txt", text, url, fd, "edgar", text[:400])
        _log(db, round_id, source, target, as_of, reason, "ok", eid)
        return {"source": source, "filing_date": fd, "evidence_id": eid, "chars": len(text),
                "text": text[:60000], "truncated": len(text) > 60000}
    if source == "wayback":
        stamp = ts(as_of).strftime("%Y%m%d%H%M%S")
        cdx = curl(f"https://web.archive.org/cdx/search/cdx?url={target}&to={stamp}&output=json&limit=-1&filter=statuscode:200")
        try:
            rows = json.loads(cdx)
        except ValueError:
            rows = []
        if len(rows) < 2:
            _log(db, round_id, source, target, as_of, reason, "not_covered")
            return {"source": source, "status": "not_covered", "detail": "no capture at or before as_of"}
        cap = rows[-1][1]
        if cap > stamp:
            raise Refused("capture after as_of; refused")
        page = curl(f"https://web.archive.org/web/{cap}id_/{target}")
        text = "\n".join(_text(page))
        kf = f"{cap[:4]}-{cap[4:6]}-{cap[6:8]}"
        eid = _save(db, round_id, source, f"wayback_{sha(target)[:10]}_{cap}.txt", text,
                    f"web.archive.org/web/{cap}/{target}", kf, "wayback", text[:400])
        _log(db, round_id, source, target, as_of, reason, "ok", eid)
        return {"source": source, "capture": cap, "knowable_from": kf, "evidence_id": eid,
                "text": text[:60000], "truncated": len(text) > 60000}
    raise Refused(f"unknown source {source}; see also alt_fetch for alternative data")
