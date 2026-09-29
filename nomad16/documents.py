"""v17 V1: documents are entities before they are evidence (docs/nomad_v17_open_entity.md §2).

* A cited ``evidence`` row is linked, by content hash, to a **document entity** through the side table
  ``evidence_entities`` (nothing is rewritten; a list fetch of a series is a read, not a document).
* A statement (a position written on a v17 round) is tied to its documents through ``statement_links``. Each
  link is ``states`` or ``component``; ``component`` is the default, and a ``states`` link must carry a **quoted
  span** that occurs in the document's stored text (and, for numeric and enumerated attributes, contains the
  value), or it is stored as ``component``.
* **``knowable_from`` is derived, never typed** (D19): the earliest ``published_at`` among verified ``states``
  links; else the latest among ``component`` links; else the statement's own ``recorded_at``. An operator may
  set ``embargo_until`` later than the derived date, with a reason, never earlier.
* The round's admission record (the Q8 event line and its date) is itself a document, so a round's first
  ``stated`` position can cite something.
"""
from __future__ import annotations

import re

from . import config, pit
from .db import DB, Refused, now_iso, sha
from .entities import ancestors, entity_upsert, scoped_attributes
from .positions import _coerce, append_position
from .rounds import get_round
from .util import ts

DOC_TRANSITIONS = {None: {"draft", "executed", "in_force"}, "draft": {"executed"}, "executed": {"in_force"},
                   "in_force": {"amended", "suspended", "terminated", "expired", "revoked", "superseded"},
                   "amended": {"in_force", "suspended", "terminated", "expired", "revoked", "superseded"},
                   "suspended": {"in_force", "terminated", "expired", "revoked", "superseded"}}


def document_text(db: DB, doc_key: str) -> str:
    """The stored text of a document entity: the file its evidence row points at."""
    e = db.get("entities", doc_key)
    d = (e or {}).get("document") or {}
    if not d.get("path"):
        raise Refused(f"document {doc_key} has no stored text")
    p = pit.ROOT / d["path"]
    if not p.exists():
        raise Refused(f"the stored text of {doc_key} is missing ({d['path']})")
    return p.read_text(errors="replace")


def document_from_evidence(db: DB, evidence_id: str, kind: str = "report", issuer: str | None = None) -> dict:
    """The document entity for an evidence row, keyed by content hash (created once, reused after)."""
    ev = db.one("evidence", "evidence_id=?", (evidence_id,))
    if ev is None:
        raise Refused(f"no evidence {evidence_id}")
    if "document" not in ancestors(db, kind):
        raise Refused(f"{kind} is not a document kind")
    if not ev.get("content_hash"):
        raise Refused("only an evidence row with a content hash can be a document")
    key = f"doc:{ev['content_hash'][:20]}"
    existing = db.get("entities", key)
    if existing is not None:
        if db.one("evidence_entities", "evidence_id=? AND entity_key=?", (evidence_id, key)) is None:
            db.append("evidence_entities", evidence_id=evidence_id, entity_key=key, content_hash=ev["content_hash"])
        return existing
    ent = entity_upsert(db, key, (ev.get("summary") or ev["url"] or key)[:120], kind, state_attributes=["document_state"],
                        exists_from=ev["knowable_from"], exists_from_knowable=ev["knowable_from"],
                        document={"content_hash": ev["content_hash"], "url": ev["url"], "published_at": ev["knowable_from"],
                                  "issuer": issuer, "evidence_id": evidence_id, "path": ev["path"], "source": ev["source"]},
                        round_id=ev["round_id"])
    db.append("evidence_entities", evidence_id=evidence_id, entity_key=key, content_hash=ev["content_hash"])
    return ent


def admission_record(db: DB, round_id: str) -> dict:
    """The event line and its date, as a document (published_at = when the line was knowable, per Q8)."""
    from .rounds import meta
    r = get_round(db, round_id)
    kf = meta(db, round_id, "knowable_from") or r["event_date"]
    text = f"{r['event_line']}\nEvent date: {r['event_date']}\nFirst knowable: {kf}\n"
    eid = pit._save(db, round_id, "admission", "admission.txt", text, f"admission:{round_id}", kf, "admission",
                    f"admission record: {r['event_line']}")
    return document_from_evidence(db, eid, kind="notice", issuer="harness")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def verify_span(text: str, span: str | None, attr_type: str, value) -> tuple[bool, str]:
    """A ``states`` link needs its quoted span in the document text, and for numeric and enumerated attributes
    the span must contain the value."""
    if not span or not span.strip():
        return False, "no span"
    if _norm(span) not in _norm(text):
        return False, "the span does not occur in the document's stored text"
    if attr_type == "numeric":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, "value is not numeric"
        forms = {str(value), f"{v:g}", f"{v:.0f}" if v == int(v) else f"{v}"}
        if not any(re.search(rf"(?<![\d.]){re.escape(f)}(?![\d])", span) for f in forms):
            return False, "the span does not contain the value"
    elif attr_type == "enum":
        if _norm(str(value)) not in _norm(span):
            return False, "the span does not contain the value"
    return True, "verified"


def derive_knowable_from(links: list[dict], stamp: str) -> tuple[str, str]:
    """Pure. ``links``: {role, span_verified, published_at}. The rule of §2.3."""
    states = [l["published_at"] for l in links if l["role"] == "states" and l.get("span_verified")]
    if states:
        return min(states, key=ts), "earliest states link"
    comp = [l["published_at"] for l in links]
    if comp:
        return max(comp, key=ts), "latest component link"
    return stamp, "recorded_at (no links)"


def statement_add(db: DB, round_id: str, holder_id: str, attribute: str, value, confidence: str,
                  links: list | None = None, node: str | None = None, source: str = "", unit: str | None = None,
                  asset_ref: str | None = None, embargo_until: str | None = None, embargo_reason: str | None = None,
                  supersedes: str | None = None, knowable_from: str | None = None) -> dict:
    """A position on a v17 round. ``knowable_from`` is derived from the cited documents and a typed one is refused."""
    r = get_round(db, round_id)
    if r["logic_version"] != "v17":
        raise Refused(f"round {round_id} is {r['logic_version']}: statement_add is for v17 rounds; v16 rounds use position_add")
    if knowable_from is not None:
        raise Refused("a typed knowable_from is refused on a v17 round: it is derived from the cited documents "
                      "(D19). Cite the documents, or set embargo_until with a reason to make it later")
    if confidence not in {"stated", "inferred", "implicit"}:
        raise Refused("confidence is stated, inferred or implicit")
    holder = db.get("entities", holder_id)
    if holder is None:
        raise Refused(f"no entity {holder_id} (entity_upsert first)")
    if node is not None and db.get("entities", node) is None:
        raise Refused(f"no entity {node} for the node (or pass node=null: a statement about the subject's own state)")
    if db.get("position_attributes", attribute) is None:
        raise Refused(f"attribute '{attribute}' is not registered")
    scoped = scoped_attributes(db, holder["kind"])
    if attribute not in scoped:
        raise Refused(f"attribute '{attribute}' is not registered for kind {holder['kind']}"
                      + (" (a person's statements are limited to the public-capacity list, §3.1)"
                         if "person" in ancestors(db, holder["kind"]) else ""))
    attr = db.get("position_attributes", attribute)
    sval, num = _coerce(db, attribute, value)
    resolved = []
    for ln in links or []:
        role = ln.get("role", "component")
        if role not in {"states", "component"}:
            raise Refused("a link's role is states or component")
        if ln.get("evidence_id"):
            doc = document_from_evidence(db, ln["evidence_id"], kind=ln.get("kind", "report"))
        elif ln.get("document"):
            doc = db.get("entities", ln["document"])
            if doc is None or not doc.get("document"):
                raise Refused(f"no document entity {ln['document']}")
        else:
            raise Refused("a link names an evidence_id or a document")
        d = doc["document"]
        ok, why = (False, "role is component")
        if role == "states":
            ok, why = verify_span(document_text(db, doc["key"]), ln.get("span"), attr["type"], value)
        resolved.append({"document": doc["key"], "role": "states" if (role == "states" and ok) else "component",
                         "requested_role": role, "span": ln.get("span"), "span_verified": bool(role == "states" and ok),
                         "published_at": d["published_at"], "note": why if role == "states" and not ok else None,
                         "evidence_id": d.get("evidence_id")})
    if confidence == "stated" and not resolved:
        raise Refused("a stated statement cites at least one document (the round's admission record counts: "
                      "admission_record); inferred and implicit statements are admitted without one")
    stamp = now_iso()
    derived, basis = derive_knowable_from(resolved, stamp)
    if embargo_until:
        if not embargo_reason:
            raise Refused("an embargo carries a reason")
        if ts(embargo_until) < ts(derived):
            raise Refused(f"embargo_until {embargo_until} is earlier than the derived date {derived}: an embargo can only "
                          "make a statement later, never earlier")
        derived, basis = embargo_until, f"embargo ({embargo_reason}); derived was {derived}"
    pos = append_position(db, holder_id, node, attribute, value, source or "v17 statement", derived, confidence,
                          asset_ref=asset_ref, unit=unit, source_document=None, source_time=None, supersedes=supersedes,
                          evidence_ids=[l["evidence_id"] or l["document"] for l in resolved])
    for l in resolved:
        db.append("statement_links", statement_id=pos["position_id"], evidence_entity=l["document"], role=l["role"],
                  span=l["span"], span_verified=l["span_verified"], published_at=l["published_at"], note=l["note"])
    return {"position_id": pos["position_id"], "knowable_from": derived, "basis": basis,
            "links": [{k: l[k] for k in ("document", "role", "requested_role", "span_verified", "published_at", "note")}
                      for l in resolved]}


def document_state_set(db: DB, round_id: str, doc_key: str, state: str, links: list) -> dict:
    """Append a lifecycle statement about a document (a termination notice, a revocation order): evidence required."""
    doc = db.get("entities", doc_key)
    if doc is None or not doc.get("document"):
        raise Refused(f"no document entity {doc_key}")
    if not links:
        raise Refused("a document state change is evidenced by another document (a notice, an order)")
    rows = [p for p in db.rows("positions", "holder_id=? AND attribute='document_state'", (doc_key,))]
    cur = rows[-1]["value"] if rows else None
    if state not in DOC_TRANSITIONS.get(cur, set()):
        raise Refused(f"{cur or 'no state'} -> {state} is not a lifecycle transition "
                      f"(allowed: {sorted(DOC_TRANSITIONS.get(cur, set())) or 'none, it is terminal'})")
    return statement_add(db, round_id, doc_key, "document_state", state, "stated", links=links, node=None,
                         source=f"document state {cur} -> {state}", supersedes=rows[-1]["position_id"] if rows else None)


def dating_report(db: DB) -> dict:
    """For v16 rows: the derived date computed beside the typed one (§2.3). Nothing is rewritten."""
    out, counts = [], {"equal": 0, "differs": 0, "no_evidence": 0}
    for p in db.rows("positions"):
        ids = p.get("evidence_ids") or []
        docs = [db.one("evidence", "evidence_id=?", (i,)) for i in ids]
        docs = [d for d in docs if d]
        if not docs:
            counts["no_evidence"] += 1
            out.append({"position_id": p["position_id"], "attribute": p["attribute"], "typed": p["knowable_from"],
                        "class": "no_evidence", "confidence": p["confidence"]})
            continue
        dates = sorted(d["knowable_from"] for d in docs)
        earliest, latest = dates[0], dates[-1]
        same = str(p["knowable_from"])[:10] == str(earliest)[:10]
        counts["equal" if same else "differs"] += 1
        out.append({"position_id": p["position_id"], "attribute": p["attribute"], "typed": p["knowable_from"],
                    "earliest_cited": earliest, "latest_cited": latest, "n_cited": len(docs),
                    "class": "equal" if same else "differs", "confidence": p["confidence"]})
    return {"counts": counts, "disagreements": [o for o in out if o["class"] == "differs"],
            "no_evidence": [o for o in out if o["class"] == "no_evidence"]}
