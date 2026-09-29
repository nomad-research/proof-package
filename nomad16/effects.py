"""The effect DAG and the transform table (§6).

Composition through a relation is a mapping, not a sign flip. A child refused for a
zero or missing transform is **written** as an effect vetoed ``no_path`` (§21), so the
veto is recorded and counted. A relation with no entries at all, the frontier bound and
the attenuation floor still refuse.
"""
from __future__ import annotations

from . import config
from .db import DB, Refused

EFFECT_KINDS = {"volume", "cost", "price", "revenue", "obligation", "availability", "credit",
                "margin", "demand", "timing", "direction"}  # timing and direction carried from v15


def transform_add(db: DB, relation: str, from_kind: str, to_kind: str, value: float, basis: str) -> dict:
    for k in (from_kind, to_kind):
        if k not in EFFECT_KINDS:
            raise Refused(f"effect kind {k} is not one of {sorted(EFFECT_KINDS)}")
    return db.upsert("transforms", f"tf.{relation}.{from_kind}.{to_kind}", relation=relation,
                     from_kind=from_kind, to_kind=to_kind, value=float(value), basis=basis)


def hop_discount(relation: str) -> tuple[float, str]:
    hd = config.get("HOP_DISCOUNT")
    if relation in hd:
        return float(hd[relation]), "HOP_DISCOUNT"
    hb = config.get("HOP_DISCOUNT_BUILDER")
    if relation in hb:
        return float(hb[relation]), "HOP_DISCOUNT_BUILDER"
    return float(config.get("DEFAULT_HOP_DISCOUNT")), "DEFAULT_HOP_DISCOUNT"


def _next_id(db, round_id):
    return f"{round_id}:E{len(db.rows('effects', 'round_id=?', (round_id,))) + 1:03d}"


def _check_common(db, round_id, holder_id, effect_kind, sign):
    from .rounds import require_pre_lock
    require_pre_lock(db, round_id)
    if db.get("holders", holder_id) is None:
        raise Refused(f"no holder {holder_id}")
    if effect_kind not in EFFECT_KINDS:
        raise Refused(f"effect kind must be one of {sorted(EFFECT_KINDS)}")
    if sign not in (-1, 1):
        raise Refused("sign is +1 or -1 for the holder, over the holding window")
    if len(db.rows("effects", "round_id=?", (round_id,))) >= int(config.get("FRONTIER_BOUND")):
        raise Refused("FRONTIER_BOUND reached")


def effect_root(db: DB, round_id: str, holder_id: str, node: str, effect_kind: str, sign: int,
                evidence_ids: list, magnitude_pct: float | None = None, cited_rules: list | None = None,
                position_ids: list | None = None, ack_id: str | None = None,
                outcome_id: str | None = None, asset_ref: str | None = None) -> dict:
    from .rounds import current_segment
    _check_common(db, round_id, holder_id, effect_kind, sign)
    seg = current_segment(db, round_id)
    eid = _next_id(db, round_id)
    return db.append("effects", effect_id=eid, round_id=round_id, segment_idx=seg["idx"],
                     holder_id=holder_id, node=node, asset_ref=asset_ref, effect_kind=effect_kind,
                     sign=sign, magnitude_pct=magnitude_pct, parent_effect_id=None, relation=None,
                     depth=0, root_effect_id=eid, transmission=1.0, ack_id=ack_id,
                     outcome_id=outcome_id, cited_rules=cited_rules or [],
                     position_ids=position_ids or [], evidence_ids=evidence_ids or [],
                     vetoed_by=None, carried_by="root")


def effect_compose(db: DB, parent_effect_id: str, relation: str, holder_id: str, to_kind: str,
                   sign: int, magnitude_pct: float | None = None, cited_rules: list | None = None,
                   position_ids: list | None = None, evidence_ids: list | None = None,
                   outcome_id: str | None = None, node: str | None = None,
                   asset_ref: str | None = None) -> dict:
    from .rounds import current_segment
    p = db.one("effects", "effect_id=?", (parent_effect_id,))
    if p is None:
        raise Refused(f"no effect {parent_effect_id}")
    if p.get("vetoed_by"):
        raise Refused(f"parent {parent_effect_id} is vetoed ({p['vetoed_by']}); nothing composes from it")
    round_id = p["round_id"]
    _check_common(db, round_id, holder_id, to_kind, sign)
    rel_entries = [t for t in db.rows("transforms") if t["relation"] == relation]
    if not rel_entries:
        raise Refused(f"relation '{relation}' has no transform entries: it does not transmit")
    t = db.get("transforms", f"tf.{relation}.{p['effect_kind']}.{to_kind}")
    value = float(t["value"]) if t else 0.0
    hd, _ = hop_discount(relation)
    support = float(p["transmission"] or 0) * value * hd
    seg = current_segment(db, round_id)
    eid = _next_id(db, round_id)
    vetoed = "no_path" if value <= 0 else None
    if vetoed is None and support < float(config.get("SUPPORT_THRESHOLD")):
        raise Refused(f"attenuation: support {support:.3f} would fall below SUPPORT_THRESHOLD; the chain stops "
                      f"(ATTENUATION_RULE)")
    row = db.append("effects", effect_id=eid, round_id=round_id, segment_idx=seg["idx"],
                    holder_id=holder_id, node=node or p["node"], asset_ref=asset_ref,
                    effect_kind=to_kind, sign=sign, magnitude_pct=magnitude_pct,
                    parent_effect_id=parent_effect_id, relation=relation, depth=int(p["depth"]) + 1,
                    root_effect_id=p["root_effect_id"], transmission=support if not vetoed else 0.0,
                    ack_id=p["ack_id"], outcome_id=outcome_id if outcome_id is not None else p["outcome_id"],
                    cited_rules=cited_rules or [], position_ids=position_ids or [],
                    evidence_ids=evidence_ids or [], vetoed_by=vetoed,
                    carried_by=f"tf.{relation}.{p['effect_kind']}.{to_kind}")
    if vetoed:
        row["note"] = (f"transform tf.{relation}.{p['effect_kind']}.{to_kind} is "
                       f"{'zero' if t else 'absent'}: written as an effect vetoed no_path (§21)")
    return row
