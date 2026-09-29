"""v17 V0: the open entity (docs/nomad_v17_open_entity.md §1, §3.4, §3.5, §7.6).

One table of things (``entities``); kinds are an open registry and a tree; capabilities replace the closed
holder lists (used by V2 role binding: not wired here); identity is a claim with evidence (merge and split
are appended events); persons are refused unless ``PERSON_INGEST`` is on.

**Openness on what exists, strictness on what counts.** An unseen kind registers ``unreviewed`` and can
propose but never support. Nothing here changes a v16 code path: ``holders``, ``nodes`` and ``node_types``
stay as they are (every old lock manifest reads them) and are mirrored into ``entities`` by ``migrate_v17``
and by the ``holder_upsert``/``node_upsert`` aliases.
"""
from __future__ import annotations

import json
import re

from . import config
from .db import DB, Refused, canon
from .util import le, ts

FORBIDDEN_PERSON = re.compile(r"health|medical|famil|spouse|child|resid|address|home|location|movement|travel|"
                              r"sanction|debar|designat|offen[cs]e|convict|arrest|proceeding|criminal|"
                              r"private|salary_private|personality|motive|intent", re.I)
LEGACY_KIND = {"company": "company", "company_asset": "facility", "sovereign": "sovereign", "agency": "agency",
               "central_bank": "central_bank", "fund": "fund", "index": "index", "commodity": "commodity_grade",
               "currency": "currency", "contract": "contract"}
NODE_TYPE_KIND = {"power_reactor": "reactor_unit", "power_plant": "plant", "refinery": "plant", "smelter": "plant",
                  "chemical_plant": "plant", "mine": "mine", "port": "port", "pipeline": "pipeline",
                  "lng_terminal": "facility", "strait": "strait", "data_centre": "data_centre",
                  "cloud_region": "data_centre", "power_market_zone": "zone"}


# ----------------------------------------------------------------------------- kinds and capabilities
def _kind_row(src, kind):
    return src.get("entity_kinds", kind) if isinstance(src, DB) else src.mget("entity_kinds", kind)


def ancestors(src, kind: str) -> list[str]:
    """The kind, then its parents up the tree. ``src`` is a DB or a View."""
    out, seen = [], set()
    while kind and kind not in seen:
        seen.add(kind)
        out.append(kind)
        kind = (_kind_row(src, kind) or {}).get("parent")
    return out


def kind_add(db: DB, kind: str, parent: str | None = None, description: str = "", scale_attribute: str | None = None,
             capabilities: list | None = None, review: str = "unreviewed", seeded: bool = False) -> dict:
    if review not in {"reviewed", "unreviewed"}:
        raise Refused("review is reviewed or unreviewed")
    if parent and db.get("entity_kinds", parent) is None:
        raise Refused(f"parent kind {parent} is not registered")
    if kind in ancestors(db, parent or ""):
        raise Refused("a kind can't be its own ancestor")
    return db.upsert("entity_kinds", kind, by="entity_kind_add", parent=parent, description=description,
                     scale_attribute=scale_attribute, capabilities=capabilities or [], review=review, seeded=seeded)


def scoped_attributes(db: DB, kind: str, include_wildcard: bool = True) -> list[str]:
    """Attributes registered for the kind or an ancestor. ``*`` covers every kind except person, and is left out
    when ratifying a kind: a kind is reviewed only when something is registered *for it*."""
    chain = set(ancestors(db, kind))
    out = []
    for r in db.rows("attribute_scope"):
        ks = set(r["kinds"] or [])
        if ks & chain or (include_wildcard and "*" in ks and "person" not in chain):
            out.append(r["key"])
    return out


def kind_ratify(db: DB, kind: str, reason: str, scale_attribute: str | None = None,
                capabilities: list | None = None, no_capabilities: bool = False) -> dict:
    """An operator ratifies a kind (§1.3): it needs a scale attribute or an explicit 'none', a capability
    list, and at least one attribute registered for it (or an ancestor)."""
    k = db.get("entity_kinds", kind)
    if k is None:
        raise Refused(f"no kind {kind}")
    if not reason:
        raise Refused("a ratification carries a reason")
    scale = scale_attribute or k.get("scale_attribute")
    if not scale:
        raise Refused("a reviewed kind names its scale attribute, or 'none' explicitly")
    caps = capabilities if capabilities is not None else (k.get("capabilities") or [])
    if not caps and not no_capabilities:
        raise Refused("a reviewed kind has a capability list (pass no_capabilities=true for an explicit empty one)")
    if not scoped_attributes(db, kind, include_wildcard=False):
        raise Refused(f"no attribute is registered for {kind} or an ancestor (attribute_scope_add first); the generic "
                      f"'*' attributes don't count")
    for c in caps:
        if db.get("capabilities", c) is None:
            raise Refused(f"unknown capability {c}")
    return db.upsert("entity_kinds", kind, by="entity_kind_ratify", scale_attribute=scale, capabilities=caps,
                     review="reviewed")


def attribute_scope_add(db: DB, attribute: str, kinds: list, note: str = "") -> dict:
    if db.get("position_attributes", attribute) is None:
        raise Refused(f"attribute {attribute} is not registered (position_attribute_add first)")
    for k in kinds:
        if k != "*" and db.get("entity_kinds", k) is None:
            raise Refused(f"unknown kind {k}")
    if "person" in kinds and FORBIDDEN_PERSON.search(attribute):
        raise Refused(f"attribute '{attribute}' is outside a person's public capacity (health, family, residence, "
                      f"location, sanctions or offence data, motive) and can never be registered for one (§3.1)")
    return db.upsert("attribute_scope", attribute, by="attribute_scope_add", kinds=kinds, note=note)


def kind_can_support(src, kind: str) -> bool:
    """Only a reviewed kind may support a claim; an unreviewed one proposes and never supports (§1.6)."""
    row = _kind_row(src, kind)
    return bool(row and row.get("review") == "reviewed")


def capabilities_of(db: DB, entity_key: str) -> list[str]:
    e = db.get("entities", entity_key)
    if e is None:
        raise Refused(f"no entity {entity_key}")
    caps = set(e.get("declared_capabilities") or [])
    for k in ancestors(db, e["kind"]):
        row = db.get("entity_kinds", k) or {}
        caps |= set(row.get("capabilities") or [])
    return sorted(caps)


# ----------------------------------------------------------------------------- entities
def person_ingest_on() -> bool:
    """Fail closed: a missing or unreadable switch is 'off' (§3.5)."""
    try:
        return str(config.get("PERSON_INGEST")).lower() == "on"
    except Exception:
        return False


def entity_upsert(db: DB, key: str, name: str, kind: str, state_attributes: list | None = None,
                  observable_by: list | None = None, exists_from: str | None = None,
                  exists_from_knowable: str | None = None, exists_to: str | None = None,
                  exists_to_knowable: str | None = None, capabilities: list | None = None,
                  entity_refs: dict | None = None, aliases: list | None = None, legacy: dict | None = None,
                  document: dict | None = None, round_id: str | None = None) -> dict:
    """Register or update an entity of any kind. An unseen kind registers ``unreviewed`` (§1.3).

    The three tests (§1.1): **state** (at least one attribute that can differ over time is named), **observable**
    (a carrier that could read it; without one it is ``unobservable``: it may propose and never support), and
    **relational** (activates with V2's relation rows; until then every entity reads as unlinked)."""
    if kind == "person" or "person" in ancestors(db, kind):
        if not person_ingest_on():
            raise Refused("PERSON_INGEST is off: no person is stored until a legal review and an erasable person "
                          "store exist (§3.5). The schema and templates can describe persons; the tool refuses to "
                          "store one")
    if db.get("entity_kinds", kind) is None:
        kind_add(db, kind, description=f"registered on first use ({key})", review="unreviewed")
    if not state_attributes and not legacy and not document:
        raise Refused("state test: name at least one attribute of this entity that can differ at different times; "
                      "a thing with none is a label, registered as a classificatory tag, never as an entity (§1.1)")
    if exists_from:
        ts(exists_from)
    if exists_to:
        ts(exists_to)
        if exists_from and ts(exists_to) < ts(exists_from):
            raise Refused("exists_to precedes exists_from")
    row = db.upsert("entities", key, by="entity_upsert", canonical_name=name, kind=kind,
                    exists_from=exists_from, exists_from_knowable=exists_from_knowable or exists_from,
                    exists_to=exists_to, exists_to_knowable=exists_to_knowable or exists_to,
                    declared_capabilities=capabilities or [], entity_refs=entity_refs or {},
                    aliases=aliases or [], state_attributes=state_attributes or [],
                    observable="observable" if observable_by else "unobservable", legacy=legacy,
                    document=document, first_seen_round=round_id)
    return row


def _mapped_kind(db: DB, holder: dict) -> tuple[str, list]:
    hc, ek = holder.get("holder_class"), holder.get("entity_kind")
    if hc == "aggregate":
        return "composite", []
    if hc == "authority":
        return "agency", []
    kind = LEGACY_KIND.get(ek, "company")
    caps = ["party_to_contract"]
    if hc == "listed_instrument":
        caps.append("files_reports")
    if hc == "unlisted_operating_asset":
        caps.append("has_operating_scale")
        if ek == "company":
            caps.append("operates_assets")
    return kind, caps


def mirror_holder(db: DB, key: str) -> dict:
    """holders -> entities (compat). The holder row stays the source for v16 paths."""
    h = db.get("holders", key)
    if h is None:
        raise Refused(f"no holder {key}")
    kind, caps = _mapped_kind(db, h)
    state_attrs = sorted({p["attribute"] for p in db.rows("positions", "holder_id=?", (key,))})
    e = entity_upsert(db, key, h["name"], kind, state_attributes=state_attrs or None, capabilities=caps,
                      entity_refs={k: h[k] for k in ("cik", "ticker", "entity_ref") if h.get(k)},
                      legacy={"source": "holders", "holder_class": h["holder_class"], "entity_kind": h["entity_kind"],
                              "listed": h["listed"], "ticker": h["ticker"], "exchange": h["exchange"],
                              "parent_id": h["parent_id"], "options_listed": h["options_listed"], "cik": h["cik"]})
    if db.get("key_map", f"holders:{key}") is None:
        db.upsert("key_map", f"holders:{key}", by="migrate_v17", entity_key=key, source_table="holders", collision=False)
    return e


def mirror_node(db: DB, key: str) -> dict:
    """nodes -> entities (compat), key preserved unless a holder already took it (then suffixed, recorded)."""
    n = db.get("nodes", key)
    if n is None:
        raise Refused(f"no node {key}")
    ek, collision = key, False
    existing = db.get("entities", key)
    if existing is not None and (existing.get("legacy") or {}).get("source") == "holders":
        ek, collision = f"{key}~node", True
    nt = n.get("node_type") or "unknown"
    kind = NODE_TYPE_KIND.get(nt, nt)
    e = entity_upsert(db, ek, n.get("description") or key, kind,
                      legacy={"source": "nodes", "node_kind": n["node_kind"], "node_type": nt,
                              "neighbours": n.get("neighbours") or [],
                              "note": "neighbours become adjacent_to relation rows in V2 (classificatory, scope only)"})
    if db.get("key_map", f"nodes:{key}") is None:
        db.upsert("key_map", f"nodes:{key}", by="migrate_v17", entity_key=ek, source_table="nodes", collision=collision)
    return e


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def compatible_kinds(db: DB, a: str, b: str) -> bool:
    """Two records can be one thing only if their kinds are the same or one refines the other (a plant and its
    reactor_unit). A composite market and the place that is its footprint are two things."""
    return a == b or a in ancestors(db, b) or b in ancestors(db, a)


def migrate_v17(db: DB) -> dict:
    """V0: mirror every holder and node into ``entities`` with a key_map row, and propose (never apply) merges
    where a node and a holder are plausibly one real thing. Idempotent. Ledger rows are not touched."""
    from .seed import seed_v17
    if db.get("entity_kinds", "organisation") is None:
        seed_v17(db)
    holders, nodes = [h["key"] for h in db.rows("holders")], [n["key"] for n in db.rows("nodes")]
    for k in holders:
        mirror_holder(db, k)
    for k in nodes:
        mirror_node(db, k)
    proposals = []
    have = {(tuple(sorted(e["entity_keys"])), e["event_type"]) for e in db.rows("entity_events")}
    for nk in nodes:
        for hk in holders:
            a, b = _norm(nk), _norm(hk)
            if a and b and (b.startswith(a) or a.startswith(b)):
                ek = (db.get("key_map", f"nodes:{nk}") or {}).get("entity_key", nk)
                ke, kh = db.get("entities", ek), db.get("entities", hk)
                if not (ke and kh and compatible_kinds(db, ke["kind"], kh["kind"])):
                    continue
                if (tuple(sorted([hk, ek])), "merge") in have:
                    continue
                proposals.append(_append_event(db, "merge", [hk, ek], {"basis": "alias", "proposed_by": "migrate_v17",
                                 "why": f"node '{nk}' and holder '{hk}' share a name stem"}, [], None, "proposed",
                                 "proposed for operator ratification; never automatic (§7.6)", "migrate_v17"))
    return {"entities": len(db.rows("entities")), "key_map": len(db.rows("key_map")),
            "merge_proposals": [(p["entity_keys"], p["event_id"]) for p in proposals]}


# ----------------------------------------------------------------------------- identity events
def _append_event(db, etype, keys, payload, evidence_ids, knowable_from, status, reason, by, ref_event=None):
    n = len(db.rows("entity_events")) + 1
    return db.append("entity_events", event_id=f"EV{n:05d}", event_type=etype, entity_keys=keys, payload=payload,
                     evidence_ids=evidence_ids or [], knowable_from=knowable_from, status=status, reason=reason,
                     by=by, ref_event=ref_event)


def entity_merge(db: DB, into: str, other: str, basis: str, evidence_ids: list, knowable_from: str,
                 id_type: str | None = None, ratified_by: str | None = None, reason: str = "") -> dict:
    """Two records are one entity. An appended event with its evidence, never an edit (§3.4).

    ``exact_identifier`` needs both entities to carry the same identifier of the same type. ``alias`` needs an
    operator ratification with a reason and is refused for persons: a name alone never merges two persons."""
    a, b = db.get("entities", into), db.get("entities", other)
    if a is None or b is None:
        raise Refused("both entities must exist")
    if not compatible_kinds(db, a["kind"], b["kind"]):
        raise Refused(f"different kinds ({a['kind']} vs {b['kind']}): a merge joins two records of one thing")
    if not evidence_ids:
        raise Refused("a merge carries its evidence")
    ts(knowable_from)
    is_person = "person" in ancestors(db, a["kind"])
    if basis == "exact_identifier":
        ra, rb = a.get("entity_refs") or {}, b.get("entity_refs") or {}
        if not id_type or not ra.get(id_type) or ra.get(id_type) != rb.get(id_type):
            raise Refused("an exact-identifier merge needs both entities to hold the same identifier of that type")
        status = "applied"
    elif basis == "alias":
        if is_person:
            raise Refused("a name alone never merges two persons; exact identifiers only (§3.4)")
        if not (ratified_by and reason):
            raise Refused("an alias merge needs an operator ratification with a reason")
        status = "applied"
    else:
        raise Refused("basis is exact_identifier or alias")
    return _append_event(db, "merge", [into, other], {"basis": basis, "id_type": id_type}, evidence_ids,
                         knowable_from, status, reason, ratified_by or "harness")


def entity_merge_ratify(db: DB, event_id: str, evidence_ids: list, knowable_from: str, ratified_by: str, reason: str) -> dict:
    ev = next((e for e in db.rows("entity_events", "event_id=?", (event_id,))), None)
    if ev is None or ev["event_type"] != "merge" or ev["status"] != "proposed":
        raise Refused("only a proposed merge event can be ratified")
    if not (evidence_ids and ratified_by and reason):
        raise Refused("ratifying a merge needs evidence, the ratifier and a reason")
    ts(knowable_from)
    return _append_event(db, "ratify", ev["entity_keys"], {"of": event_id}, evidence_ids, knowable_from, "applied",
                         reason, ratified_by, ref_event=event_id)


def entity_merge_decline(db: DB, event_id: str, by: str, reason: str) -> dict:
    """Close a proposed merge as not one thing. Appended; the proposal stays on the ledger."""
    ev = next((e for e in db.rows("entity_events", "event_id=?", (event_id,))), None)
    if ev is None or ev["event_type"] != "merge" or ev["status"] != "proposed":
        raise Refused("only a proposed merge event can be declined")
    if not (by and reason):
        raise Refused("declining a merge needs the decliner and a reason")
    return _append_event(db, "decline", ev["entity_keys"], {"of": event_id}, [], None, "declined", reason, by,
                         ref_event=event_id)


def entity_split(db: DB, merge_event_id: str, evidence_ids: list, knowable_from: str, reason: str, by: str) -> dict:
    """Undo a merge by appending a split. The graph as of any earlier clock is still recomputable."""
    ev = next((e for e in db.rows("entity_events", "event_id=?", (merge_event_id,))), None)
    if ev is None or ev["event_type"] not in {"merge", "ratify"}:
        raise Refused("a split undoes a merge (or its ratification)")
    if not (evidence_ids and reason):
        raise Refused("a split carries evidence and a reason")
    ts(knowable_from)
    return _append_event(db, "split", ev["entity_keys"], {"of": merge_event_id}, evidence_ids, knowable_from, "applied",
                         reason, by, ref_event=merge_event_id)


def _visible(ev: dict, clock: str) -> bool:
    return ev["knowable_from"] is not None and le(ev["knowable_from"], clock)


def canonical_map(view, clock: str) -> dict[str, str]:
    """entity key -> canonical key, from the merges applied and not split, whose evidence is knowable by the clock
    and whose ledger row precedes the view's ``ledger_cutoff`` (§3.4). A proposed merge never counts."""
    evs = sorted(view.led("entity_events"), key=lambda e: e["id"])
    by_id = {e["event_id"]: e for e in evs}
    merges, split = {}, set()
    for e in evs:
        if not _visible(e, clock):
            continue
        if e["event_type"] == "merge" and e["status"] == "applied":
            merges[e["event_id"]] = e["entity_keys"]
        elif e["event_type"] == "ratify":
            ref = by_id.get(e["ref_event"])
            if ref is not None:
                merges[ref["event_id"]] = ref["entity_keys"]
        elif e["event_type"] == "split":
            split.add(e["ref_event"])
            ref = by_id.get(e["ref_event"])
            if ref is not None and ref["event_type"] == "ratify":
                split.add(ref["ref_event"])
    parent: dict[str, str] = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for mid, (into, other) in merges.items():
        if mid in split:
            continue
        ri, ro = find(into), find(other)
        if ri != ro:
            parent[ro] = ri
    return {k: find(k) for k in set(parent) | set(parent.values())}


def entities_as_of(view, clock: str) -> list[dict]:
    """Entities that exist at the clock (lifecycle honours both dates), merged ones collapsed."""
    cmap = canonical_map(view, clock)
    out = {}
    for e in view.mut("entities"):
        if e.get("exists_from") and not (le(e["exists_from"], clock) and le(e.get("exists_from_knowable") or e["exists_from"], clock)):
            continue
        if e.get("exists_to") and le(e["exists_to"], clock) and le(e.get("exists_to_knowable") or e["exists_to"], clock):
            continue
        c = cmap.get(e["key"], e["key"])
        out.setdefault(c, {"key": c, "kind": None, "merged_from": []})
        if c == e["key"]:
            out[c].update(kind=e["kind"], name=e["canonical_name"])
        else:
            out[c]["merged_from"].append(e["key"])
    return sorted(out.values(), key=lambda r: r["key"])


def resolve(view, key: str, clock: str) -> str:
    return canonical_map(view, clock).get(key, key)
