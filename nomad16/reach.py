"""Outcome vocabularies, reachable sets and thesis sets (§7.2, §22.3).

Reads positions, bounds, node facts and ratified procedural states as of T_seg. Never
reads prices: a price never cuts an outcome.
"""
from __future__ import annotations

from .conditions import combine, evaluate, visible_positions
from .db import DB, Refused
from .derive import scope_nodes
from .util import le, ts

STRUCTURAL_FACTS = {"no_sink", "slack"}  # below_band never cuts: it reads prices


def outcome_vocab_add(db: DB, notice_kind: str, outcomes: list[dict], authored_from: str) -> dict:
    """Author a vocabulary. ``other`` is added automatically and sits outside the closed world."""
    ids = [o["outcome_id"] for o in outcomes]
    if "other" in ids:
        raise Refused("'other' is added automatically")
    if len(set(ids)) != len(ids):
        raise Refused("duplicate outcome ids")
    for o in outcomes:
        if not o.get("label"):
            raise Refused(f"outcome {o['outcome_id']} needs a label")
    full = list(outcomes) + [{"outcome_id": "other", "label": "none of the named outcomes",
                              "needs": [], "falsifier": "one of the named outcomes is delivered"}]
    return db.upsert("outcome_vocabs", notice_kind, notice_kind=notice_kind, outcomes=full,
                     authored_from=authored_from)


def _ack(view, ack_id):
    a = view.mget("ack_nodes", ack_id)
    if a is None:
        raise Refused(f"no ACK {ack_id}")
    return a


def window_days(ack, clock) -> int | None:
    end = ack.get("window_to") or ack.get("due_at")
    if not end:
        return None
    return max((ts(end) - ts(clock)).days, 0)


def compute(view, round_row: dict, ack: dict, clock: str) -> list[dict]:
    """Pure: per named outcome, reach = reachable | cut | kept_unknown, with evidence."""
    vocab = view.mget("outcome_vocabs", ack["notice_kind"]) if ack.get("notice_kind") else None
    if vocab is None:
        return []
    nodes = scope_nodes(view, round_row["node"])
    ctx = {"window_days": window_days(ack, clock)}
    bindings = ack.get("bindings") or {}
    out = []
    for o in vocab["outcomes"]:
        if o["outcome_id"] == "other":
            continue
        needs = []
        for nd in o.get("needs") or []:
            e = evaluate(view, clock, nd, bindings, nodes, ctx)
            needs.append({"need": nd, **e})
        st = combine([n["state"] for n in needs]) if needs else "true"
        reach = {"true": "reachable", "unknown": "kept_unknown", "false": "cut"}[st]
        cut_by = [n["why"] for n in needs if n["state"] == "false"]
        ev = sorted({x for n in needs for x in n["evidence"]})
        out.append({"outcome_id": o["outcome_id"], "label": o["label"], "reach": reach,
                    "cut_by": cut_by, "evidence_ids": ev,
                    "need_states": [(n["state"], n["why"]) for n in needs]})
    return out


def reachable(db: DB, ack_id: str) -> dict:
    """Tool: compute and record the reachable set for a ratified ACK at the current clock."""
    from .rounds import current_segment, get_round, require_pre_lock
    from .view import View
    view = View(db)
    ack = _ack(view, ack_id)
    require_pre_lock(db, ack["round_id"])
    if ack.get("status") != "ratified":
        raise Refused(f"ACK {ack_id} is '{ack.get('status')}'; reach runs on ratified ACKs")
    rnd = get_round(db, ack["round_id"])
    seg = current_segment(db, ack["round_id"])
    res = compute(view, rnd, ack, seg["clock"])
    if not res:
        return {"ack_id": ack_id, "outcomes": [], "note": "no vocabulary for this notice kind (no_vocabulary)"}
    for r in res:
        db.append("ack_outcomes", ack_id=ack_id, round_id=ack["round_id"], segment_idx=seg["idx"],
                  outcome_id=r["outcome_id"], reach=r["reach"], cut_by=r["cut_by"],
                  evidence_ids=r["evidence_ids"], need_states=r["need_states"])
    return {"ack_id": ack_id, "clock": seg["clock"], "outcomes": res}


def outcomes(db: DB, ack_id: str) -> dict:
    from .view import View
    view = View(db)
    ack = _ack(view, ack_id)
    vocab = view.mget("outcome_vocabs", ack["notice_kind"]) if ack.get("notice_kind") else None
    return {"ack_id": ack_id, "notice_kind": ack.get("notice_kind"),
            "vocabulary": vocab["outcomes"] if vocab else None}


def validate_thesis(view, round_row: dict, ack: dict, clock: str, in_thesis: list[str],
                    exclusions: dict) -> list[dict]:
    """Refuse a thesis whose exclusions rest on unknowns (§22.3, smoke 18). Returns reach rows."""
    res = compute(view, round_row, ack, clock)
    if not res:
        raise Refused("no vocabulary: a thesis needs an outcome set")
    by = {r["outcome_id"]: r for r in res}
    R = [o for o, r in by.items() if r["reach"] != "cut"]
    for o in in_thesis:
        if o == "other":
            raise Refused("'other' is outside the closed world and can't be in the thesis")
        if o not in by:
            raise Refused(f"{o} is not in the vocabulary")
        if by[o]["reach"] == "cut":
            raise Refused(f"{o} was cut from the reachable set; it can't be kept")
    if not in_thesis:
        raise Refused("the thesis keeps at least one reachable outcome")
    documented = {r["position_id"]: r for r in visible_positions(view, clock) if r["confidence"] == "stated"}
    rules = {r["key"] for r in view.mut("library_rules") if r.get("status") != "retired"}
    bounds = {b["key"] for b in view.mut("bounds") if le(b["knowable_from"], clock)}
    for o in R:
        if o in in_thesis:
            continue
        ex = exclusions.get(o)
        if not ex:
            raise Refused(f"excluded reachable outcome {o} must cite the positions or rules that exclude it")
        pids = ex.get("position_ids") or []
        rids = ex.get("rule_ids") or []
        bids = ex.get("bound_ids") or []
        if not (pids or bids):
            raise Refused(f"exclusion of {o} cites no documented position or bound; "
                          f"an exclusion resting on an unknown is refused and becomes a switch")
        for p in pids:
            if p not in documented:
                raise Refused(f"exclusion of {o} rests on position {p}, which is not documented "
                              f"(stated and knowable by {clock}); refused, it becomes a switch")
        for r in rids:
            if r not in rules:
                raise Refused(f"exclusion of {o} cites rule {r}, which is not in the library")
        for b in bids:
            if b not in bounds:
                raise Refused(f"exclusion of {o} cites bound {b}, which is not knowable by {clock}")
    return res


def thesis_set(db: DB, ack_id: str, in_thesis: list[str], exclusions: dict, basis: str,
               carrier: str, fetch_path: str) -> dict:
    """Tool: the operator's thesis set; registers the ACK's vocabulary as a map call."""
    from .calls import call_add
    from .rounds import current_segment, get_round, require_pre_lock
    from .view import View
    view = View(db)
    ack = _ack(view, ack_id)
    require_pre_lock(db, ack["round_id"])
    if ack.get("status") != "ratified":
        raise Refused("thesis sets are stated on ratified ACKs")
    rnd = get_round(db, ack["round_id"])
    seg = current_segment(db, ack["round_id"])
    validate_thesis(view, rnd, ack, seg["clock"], in_thesis, exclusions)
    row = db.append("thesis_sets", ack_id=ack_id, round_id=ack["round_id"], segment_idx=seg["idx"],
                    in_thesis=sorted(in_thesis), exclusions=exclusions, basis=basis)
    vocab = view.mget("outcome_vocabs", ack["notice_kind"])
    existing = db.one("predictions", "ack_id=? AND call_type='map' AND segment_idx=?", (ack_id, seg["idx"]))
    call = None
    if existing is None:
        branches = [{"branch": o["outcome_id"], "label": o["label"],
                     "falsifier": o.get("falsifier") or f"the delivered notice is not '{o['label']}'"}
                    for o in vocab["outcomes"]]
        call = call_add(db, ack["round_id"], call_type="map", claim_kind="map",
                        claim=f"The {ack['notice_kind']} delivered for {ack_id} is one of the named outcomes; "
                              f"thesis keeps {sorted(in_thesis)}",
                        carrier=carrier, fetch_path=fetch_path,
                        due_at=ack.get("due_at") or ack.get("window_to"),
                        falsifier="the delivered outcome lies outside the thesis set",
                        # an obligation template carries occurrence, not map, so it is not cited here
                        cited_rules=[],
                        branches=branches, ack_id=ack_id)
    return {"thesis": row, "map_call": call}
