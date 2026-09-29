"""B4: knowable-time accrual independent of rounds.

node_facts is an append-only ledger of dated node facts (force majeure notices, port notices, premium assessments,
enforcement actions, outages, restarts, dependencies). ingest_targets names what the ingest is looking for.
`ingest()` pulls RSS/Atom feeds listed in a sources file and appends new items; it never closes a target by itself."""
import json
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from .db import append, get_row, insert_mutable
from .errors import NotFound, ValidationError
from .util import now_iso

FACT_TYPES = ("force_majeure", "allocation", "port_notice", "premium_assessment", "enforcement", "outage", "restart",
              "dependency", "scheduled", "other")   # v8 D3: scheduled = earnings dates, guidance dates, regulatory calendar
DEFAULT_SOURCES = Path(__file__).parent / "ingest_sources.json"


def node_fact_add(conn: sqlite3.Connection, node: str, fact_type: str, text: str, source: str, url: str | None = None,
                  holder_id: str | None = None, source_time: str | None = None, knowable_from: str | None = None) -> dict:
    if fact_type not in FACT_TYPES:
        raise ValidationError(f"fact_type must be one of {FACT_TYPES}")
    if not node.strip() or not text.strip() or not source.strip():
        raise ValidationError("node, text and source are required")
    if holder_id:
        from .names import resolve_holder
        holder_id = resolve_holder(conn, holder_id)["id"]
    if url:
        dup = conn.execute("SELECT id FROM node_facts WHERE url = ? AND node = ?", (url, node.strip())).fetchone()
        if dup:
            return {"fact_id": dup["id"], "node": node.strip(), "created": False}
    row = append(conn, "node_facts", {"node": node.strip(), "holder_id": holder_id, "fact_type": fact_type,
                                      "text": text.strip()[:2000], "url": url, "source": source, "source_time": source_time,
                                      "knowable_from": knowable_from})
    return {"fact_id": row["id"], "node": node.strip(), "created": True}


def node_facts(conn: sqlite3.Connection, node: str | None = None, fact_type: str | None = None,
               since: str | None = None, limit: int = 50) -> list[dict]:
    sql, args = "SELECT * FROM node_facts WHERE 1=1", []
    if node:
        sql += " AND lower(node) = lower(?)"
        args.append(node)
    if fact_type:
        sql += " AND fact_type = ?"
        args.append(fact_type)
    if since:
        sql += " AND COALESCE(source_time, recorded_at) >= ?"
        args.append(since)
    sql += " ORDER BY rowid DESC LIMIT ?"
    args.append(int(limit))
    return [dict(r) for r in conn.execute(sql, args)]


def target_add(conn: sqlite3.Connection, name: str, question: str, node: str | None = None,
               round_id: str | None = None) -> dict:
    if not name.strip() or not question.strip():
        raise ValidationError("name and question are required")
    row = insert_mutable(conn, "ingest_targets", {"name": name.strip(), "question": question.strip(), "node": node,
                                                  "status": "open", "opened_in_round": round_id})
    return {"target_id": row["id"], "name": row["name"], "status": "open"}


def targets(conn: sqlite3.Connection, status: str | None = "open") -> list[dict]:
    if status:
        return [dict(r) for r in conn.execute("SELECT * FROM ingest_targets WHERE status = ? ORDER BY rowid", (status,))]
    return [dict(r) for r in conn.execute("SELECT * FROM ingest_targets ORDER BY rowid")]


def target_close(conn: sqlite3.Connection, target_id: str, status: str, found_fact_id: str | None = None) -> dict:
    get_row(conn, "ingest_targets", target_id, "ingest target")
    if status not in ("found", "expired"):
        raise ValidationError("status must be found or expired")
    if status == "found" and not found_fact_id:
        raise ValidationError("found needs found_fact_id (add the fact with nomad_node_fact_add first)")
    if found_fact_id:
        get_row(conn, "node_facts", found_fact_id, "node fact")
    conn.execute("UPDATE ingest_targets SET status = ?, found_fact_id = ? WHERE id = ?", (status, found_fact_id, target_id))
    return {"target_id": target_id, "status": status, "found_fact_id": found_fact_id}


# ---- feed ingest -------------------------------------------------------------------------

def _fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nomad-harness/0.1 (+node facts ingest)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _text(el, *names) -> str | None:
    for n in names:
        found = el.find(n)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
        for child in el:
            if child.tag.endswith("}" + n) and (child.text or "").strip():
                return child.text.strip()
    return None


def _iso(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).date().isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
    except Exception:
        return None


_HTML_ENTITIES = {"&nbsp;": " ", "&ndash;": "-", "&mdash;": "-", "&rsquo;": "'", "&lsquo;": "'", "&ldquo;": '"',
                  "&rdquo;": '"', "&hellip;": "...", "&euro;": "EUR", "&pound;": "GBP", "&copy;": "(c)", "&auml;": "ae",
                  "&ouml;": "oe", "&uuml;": "ue", "&Auml;": "Ae", "&Ouml;": "Oe", "&Uuml;": "Ue", "&szlig;": "ss"}


def parse_feed(data: bytes) -> list[dict]:
    """RSS 2.0 or Atom -> [{title, link, published, summary}]. Tolerates HTML named entities in feed text."""
    text = data.decode("utf-8", errors="replace")
    for ent, rep in _HTML_ENTITIES.items():
        text = text.replace(ent, rep)
    text = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)
    root = ET.fromstring(text.encode("utf-8"))
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        link = _text(it, "link")
        if link is None:
            for child in it:
                if child.tag.split("}")[-1] == "link" and child.get("href"):
                    link = child.get("href")
                    break
        items.append({"title": _text(it, "title") or "", "link": link,
                      "published": _iso(_text(it, "pubDate", "published", "updated", "date")),
                      "summary": re.sub(r"<[^>]+>", " ", _text(it, "description", "summary", "content") or "")[:400].strip()})
    return items


def ingest(conn: sqlite3.Connection, sources_path: str | Path = DEFAULT_SOURCES, fetch=_fetch) -> dict:
    sources = json.loads(Path(sources_path).read_text(encoding="utf-8"))["sources"]
    open_targets = targets(conn, "open")
    report = {"run_at": now_iso(), "sources": [], "new_facts": 0, "possible_target_matches": []}
    for src in sources:
        entry = {"name": src["name"], "url": src["url"], "ok": False, "items": 0, "new": 0, "error": None}
        try:
            items = parse_feed(fetch(src["url"]))
            entry["ok"] = True
            entry["items"] = len(items)
            for it in items:
                if not it["link"]:
                    continue
                text = it["title"] + (" -- " + it["summary"] if it["summary"] else "")
                r = node_fact_add(conn, src.get("node", src["name"]), src.get("fact_type", "other"), text, src["name"],
                                  url=it["link"], source_time=it["published"], knowable_from=it["published"])
                if r["created"]:
                    entry["new"] += 1
                    report["new_facts"] += 1
                    low = text.lower()
                    for t in open_targets:
                        keys = [k for k in re.split(r"[\s,;/]+", (t["name"] + " " + (t["node"] or "")).lower()) if len(k) > 3]
                        if keys and any(k in low for k in keys):
                            report["possible_target_matches"].append({"target": t["name"], "fact_id": r["fact_id"], "title": it["title"]})
        except Exception as e:  # network, parse: report and continue
            entry["error"] = f"{type(e).__name__}: {e}"[:200]
        report["sources"].append(entry)
    return report
