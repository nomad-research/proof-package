"""Names book, positions, the attribute registry and bounds (§6, §18.1, §18.3).

Positions are per asset, not per owner, and append-only. ``position_add`` validates the
attribute against ``position_attributes`` (the v15 enum CHECK is replaced by the
registry, so registering an attribute never rebuilds a table).
"""
from __future__ import annotations

from .db import DB, Refused
from .util import ts

HOLDER_CLASSES = {"listed_instrument", "unlisted_operating_asset", "aggregate", "authority"}
ENTITY_KINDS = {"company_asset", "company", "sovereign", "agency", "central_bank", "fund",
                "index", "commodity", "currency", "contract"}
CONFIDENCE = {"stated", "inferred", "implicit"}
ATTR_TYPES = {"numeric", "enum", "bool", "text"}


def _mirror(db: DB, what: str, key: str) -> None:
    """holder_upsert and node_upsert stay as aliases for one release: they write the v16 table and mirror the
    row into ``entities`` once the v17 registry is seeded (before that they behave exactly as in v16)."""
    if db.get("entity_kinds", "organisation") is None:
        return
    from . import entities
    (entities.mirror_holder if what == "holder" else entities.mirror_node)(db, key)


def holder_upsert(db: DB, holder_id: str, name: str, holder_class: str, entity_kind: str,
                  listed: bool = False, ticker: str | None = None, exchange: str | None = None,
                  parent_id: str | None = None, options_listed: bool | None = None,
                  cik: str | None = None, entity_ref: str | None = None) -> dict:
    if holder_class not in HOLDER_CLASSES:
        raise Refused(f"holder_class must be one of {sorted(HOLDER_CLASSES)}")
    if entity_kind not in ENTITY_KINDS:
        raise Refused(f"entity_kind must be one of {sorted(ENTITY_KINDS)}")
    row = db.upsert("holders", holder_id, name=name, holder_class=holder_class,
                    entity_kind=entity_kind, listed=bool(listed), ticker=ticker,
                    exchange=exchange, parent_id=parent_id, options_listed=options_listed,
                    cik=cik, entity_ref=entity_ref)
    _mirror(db, "holder", holder_id)
    return row


def node_upsert(db: DB, node: str, node_type: str, description: str = "",
                node_kind: str = "event", neighbours: list[str] | None = None,
                round_id: str | None = None) -> dict:
    """``node_type`` is a registry, not an enum (§15 fold change 6): unseen types register."""
    if node_kind not in {"event", "attribute"}:
        raise Refused("node_kind is 'event' or 'attribute' (v15 meaning); node_type is the kind of thing")
    if db.get("node_types", node_type) is None:
        db.upsert("node_types", node_type, description=f"registered on first use ({node})",
                  first_seen_round=round_id)
    row = db.upsert("nodes", node, node_kind=node_kind, node_type=node_type,
                    description=description, neighbours=neighbours or [])
    _mirror(db, "node", node)
    return row


def attribute_add(db: DB, attribute: str, type: str, unit: str | None = None,
                  allowed: list | None = None, description: str = "") -> dict:
    if type not in ATTR_TYPES:
        raise Refused(f"type must be one of {sorted(ATTR_TYPES)}")
    return db.upsert("position_attributes", attribute, type=type, unit=unit,
                     allowed=allowed or [], description=description)


def bound_add(db: DB, bound_id: str, subject: str, quantity: str, value: float, unit: str,
              source_document: str, knowable_from: str, authored_by: str = "operator") -> dict:
    if not source_document:
        raise Refused("a bound needs its source document")
    ts(knowable_from)
    return db.upsert("bounds", bound_id, subject=subject, quantity=quantity, value=float(value),
                     unit=unit, source_document=source_document, knowable_from=knowable_from,
                     authored_by=authored_by)


def _coerce(db: DB, attribute: str, value):
    a = db.get("position_attributes", attribute)
    if a is None:
        raise Refused(f"attribute '{attribute}' is not registered; register it with "
                      f"position_attribute_add first (§18.3)")
    t = a["type"]
    if t == "numeric":
        try:
            return str(value), float(value)
        except (TypeError, ValueError):
            raise Refused(f"attribute {attribute} is numeric; got {value!r}")
    if t == "bool":
        v = str(value).lower()
        if v not in {"true", "false"}:
            raise Refused(f"attribute {attribute} is bool; got {value!r}")
        return v, None
    if t == "enum":
        allowed = a.get("allowed") or []
        if str(value) not in [str(x) for x in allowed]:
            raise Refused(f"attribute {attribute} allows {allowed}; got {value!r}")
    return str(value), None


def append_position(db: DB, holder_id: str, node: str | None, attribute: str, value, source: str, knowable_from: str,
                    confidence: str, asset_ref: str | None = None, unit: str | None = None,
                    source_document: str | None = None, source_time: str | None = None,
                    supersedes: str | None = None, evidence_ids: list | None = None) -> dict:
    """The one place a position row is written (v16 ``position_add`` and v17 ``statement_add`` both end here)."""
    sval, num = _coerce(db, attribute, value)
    n = len(db.rows("positions")) + 1
    return db.append("positions", position_id=f"P{n:05d}", holder_id=holder_id, node=node,
                     asset_ref=asset_ref, attribute=attribute, value=sval, value_num=num,
                     unit=unit, source=source, source_document=source_document,
                     source_time=source_time, knowable_from=knowable_from,
                     confidence=confidence, supersedes=supersedes,
                     evidence_ids=evidence_ids or [])


def position_add(db: DB, holder_id: str, node: str, attribute: str, value, source: str,
                 knowable_from: str, confidence: str,
                 asset_ref: str | None = None, unit: str | None = None,
                 source_document: str | None = None, source_time: str | None = None,
                 supersedes: str | None = None, evidence_ids: list | None = None,
                 round_id: str | None = None) -> dict:
    """The v16 write path: a typed ``knowable_from``, on a holder and a node. On a v17 round it is refused."""
    from .rounds import active_logic
    if active_logic(db) == "v17":
        raise Refused("the active round is v17: write positions with statement_add. Its knowable_from is derived from "
                      "the cited documents and a typed one is refused (D19)")
    if db.get("holders", holder_id) is None:
        raise Refused(f"no holder {holder_id}; add it with holder_upsert")
    if db.get("nodes", node) is None:
        raise Refused(f"no node {node}; add it with node_upsert")
    if confidence not in CONFIDENCE:
        raise Refused(f"confidence must be one of {sorted(CONFIDENCE)}; every row is stamped at write")
    if not knowable_from:
        raise Refused("every position row carries knowable_from, stamped at write: the date its source "
                      "became public (v17 checkpoint; v15 left 141 of 200 rows undated and K8/K10 could not read it)")
    if confidence == "stated" and not (source_document or evidence_ids):
        raise Refused("a stated position needs a source document or evidence id")
    ts(knowable_from)
    return append_position(db, holder_id, node, attribute, value, source, knowable_from, confidence, asset_ref, unit,
                           source_document, source_time, supersedes, evidence_ids)


def node_fact_add(db: DB, round_id: str, node: str, kind: str, text: str, knowable_from: str,
                  evidence_ids: list, effect_kind: str | None = None) -> dict:
    """A stated structural fact about a node: slack, no_sink, no_slack, signs_held (§21)."""
    kinds = {"slack", "no_sink", "no_slack", "constrained"}
    if kind not in kinds:
        raise Refused(f"kind must be one of {sorted(kinds)}")
    if not evidence_ids:
        raise Refused("a node fact is a stated fact with evidence; the v15 word match is gone (§21)")
    ts(knowable_from)
    n = len(db.rows("node_facts")) + 1
    return db.append("node_facts", fact_id=f"F{n:04d}", round_id=round_id, node=node, kind=kind,
                     effect_kind=effect_kind, text=text, knowable_from=knowable_from,
                     evidence_ids=evidence_ids)
