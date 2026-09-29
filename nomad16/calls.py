"""Calls and their scoring (§16 step 10, §19.1, §15 override).

Absence claims resolve ``hit`` only on ``carrier_state = silent`` — a carrier read in
full through ``due_at`` that said nothing. ``unread`` and ``not_covered`` never do (D9).
"""
from __future__ import annotations

import datetime as _dt

from . import config
from .db import DB, Refused
from .util import day, ts

CALL_TYPES = {"sign", "magnitude_order", "lag_band", "predicate", "null", "meta", "map", "narrative"}
CLAIM_KINDS = {"occurrence", "absence", "ordering", "magnitude", "duration", "map"}
LAG_BANDS = {"minutes", "hours", "days", "weeks", "months"}  # v16 C2 widens to minutes and hours
OUTCOMES = {"hit", "miss", "unverified", "untestable"}
CARRIER_STATES = {"silent", "spoke", "unread", "not_covered"}


def call_add(db: DB, round_id: str, call_type: str, claim_kind: str, claim: str, carrier: str,
             fetch_path: str, due_at: str, falsifier: str, cited_rules: list | None = None,
             branches: list | None = None, covers: bool = False, lag_band: str | None = None,
             factors: list | None = None, effect_id: str | None = None, ack_id: str | None = None,
             narrative_sign: int | None = None) -> dict:
    from .rounds import current_segment, get_round, require_pre_lock
    require_pre_lock(db, round_id)
    rnd = get_round(db, round_id)
    seg = current_segment(db, round_id)
    if call_type not in CALL_TYPES:
        raise Refused(f"call_type must be one of {sorted(CALL_TYPES)}")
    if claim_kind not in CLAIM_KINDS:
        raise Refused(f"claim_kind must be one of {sorted(CLAIM_KINDS)}")
    if not carrier or not fetch_path:
        raise Refused("every call names a carrier with a working fetch path (Q7)")
    if not falsifier:
        raise Refused("every call has a falsifier")
    if not due_at:
        raise Refused("every call has a due_at")
    cap = ts(rnd["event_date"]) + _dt.timedelta(days=int(config.get("DUE_AT_MAX_DAYS")))
    if ts(due_at) > cap:
        raise Refused(f"due_at {due_at} is past the DUE_AT_MAX_DAYS cap ({day(cap)})")
    if ts(due_at) <= ts(seg["clock"]):
        raise Refused("due_at must be after the segment clock")
    if lag_band is not None and lag_band not in LAG_BANDS:
        raise Refused(f"lag_band must be one of {sorted(LAG_BANDS)}")
    if call_type == "lag_band" and lag_band is None:
        raise Refused("a lag_band call names its band")
    if call_type == "narrative" and narrative_sign not in (-1, 0, 1):
        raise Refused("a narrative row carries narrative_sign in {-1, 0, 1}")
    if call_type == "map" or claim_kind == "map":
        if not branches or len(branches) < 2:
            raise Refused("a map call takes named branches")
        names = [b.get("branch") for b in branches]
        has_other = "other" in names
        if has_other:
            ob = [b for b in branches if b.get("branch") == "other"][0]
            if not ob.get("falsifier"):
                raise Refused("the 'other' branch needs its own falsifier (v16 C1)")
        elif not covers:
            raise Refused("map branches must cover the space (covers=true) or include an 'other' "
                          "branch with its own falsifier (v16 C1)")
    for rid in cited_rules or []:
        r = db.get("library_rules", rid)
        if r is None:
            raise Refused(f"cited rule {rid} is not in the library")
        if claim_kind not in (r.get("carries") or []):
            raise Refused(f"rule {rid} carries {r.get('carries')}, not {claim_kind}; "
                          f"a citation outside a rule's carriage is refused at lock (§3)")
    n = len(db.rows("predictions", "round_id=?", (round_id,))) + 1
    return db.append("predictions", call_id=f"{round_id}:C{n:03d}", round_id=round_id,
                     segment_idx=seg["idx"], call_type=call_type, claim_kind=claim_kind, claim=claim,
                     branches=branches or [], lag_band=lag_band, carrier=carrier,
                     fetch_path=fetch_path, due_at=day(due_at), falsifier=falsifier,
                     cited_rules=cited_rules or [], factors=factors or [], effect_id=effect_id,
                     ack_id=ack_id, narrative_sign=narrative_sign)


def _call(db, call_id):
    c = db.one("predictions", "call_id=?", (call_id,))
    if c is None:
        raise Refused(f"no call {call_id}")
    return c


def is_absence(c: dict) -> bool:
    return c["claim_kind"] == "absence" or c["call_type"] == "null"


def score_call(db: DB, call_id: str, outcome: str, carrier_state: str, basis: str,
               evidence_ids: list | None = None, branch: str | None = None,
               source_coverage: str | None = None) -> dict:
    from .rounds import state
    c = _call(db, call_id)
    st = state(db, c["round_id"])
    if st not in {"walking", "live"}:
        raise Refused(f"calls are scored after lock; round is '{st}'")
    if outcome not in OUTCOMES:
        raise Refused(f"outcome must be one of {sorted(OUTCOMES)}")
    if carrier_state not in CARRIER_STATES:
        raise Refused(f"carrier_state must be one of {sorted(CARRIER_STATES)}")
    if is_absence(c) and outcome == "hit" and carrier_state != "silent":
        raise Refused("an absence claim resolves hit only when its carrier was read in full through "
                      "due_at and said nothing (carrier_state = silent); smoke 10")
    if outcome in {"hit", "miss"} and carrier_state not in {"spoke", "silent"}:
        raise Refused("hit/miss needs a carrier that spoke (or, for absence, was read silent)")
    if outcome == "miss" and is_absence(c) and carrier_state != "spoke":
        raise Refused("an absence claim misses only when its carrier spoke")
    if c["call_type"] == "map" and outcome in {"hit", "miss"} and not branch:
        raise Refused("a map call resolves to a named branch")
    prev = db.one("resolutions", "call_id=?", (call_id,))
    if prev is not None and c["call_type"] == "narrative":
        structural = [r for r in db.rows("resolutions", "round_id=?", (c["round_id"],))
                      if _call(db, r["call_id"])["call_type"] != "narrative"]
        if structural:
            raise Refused("a narrative row is never re-scored after structural resolution")
    return db.append("resolutions", call_id=call_id, round_id=c["round_id"], outcome=outcome,
                     branch=branch, carrier_state=carrier_state, source_coverage=source_coverage,
                     expired=False, quality=None, evidence_ids=evidence_ids or [], basis=basis,
                     supersedes=prev["id"] if prev else None)


def close_round(db: DB, round_id: str, as_of: str) -> dict:
    """Expire every unresolved call due by ``as_of`` under the v16 rule, and report v15's beside it."""
    from .rounds import set_state, state
    st = state(db, round_id)
    if st != "live":
        raise Refused(f"close_round runs once the walk has ended (round is '{st}')")
    calls = db.rows("predictions", "round_id=?", (round_id,))
    resolved = {r["call_id"] for r in db.rows("resolutions", "round_id=?", (round_id,))}
    expired, open_ = [], []
    for c in calls:
        if c["call_id"] in resolved:
            continue
        if ts(c["due_at"]) > ts(as_of):
            open_.append(c["call_id"])
            continue
        db.append("resolutions", call_id=c["call_id"], round_id=round_id, outcome="unverified",
                  branch=None, carrier_state="unread", source_coverage="thin", expired=True,
                  quality=None, evidence_ids=[],
                  basis="expired unresolved; v16: an unread carrier never resolves hit"
                        + (" (v15 would have booked this absence claim as hit)" if is_absence(c) else ""),
                  supersedes=None)
        expired.append(c["call_id"])
    if not open_:
        set_state(db, round_id, "scored", f"every call resolved or expired by {as_of}")
    return {"expired": expired, "still_open": open_, "state": state(db, round_id)}


def absence_record(db: DB, round_id: str | None = None) -> dict:
    """The absence record under both rules (P1 acceptance: both numbers reported)."""
    where, params = ("round_id=?", (round_id,)) if round_id else ("", ())
    latest = {}
    for r in db.rows("resolutions", where, params):
        latest[r["call_id"]] = r
    v16 = {"hit": 0, "miss": 0, "unverified": 0}
    v15 = {"hit": 0, "miss": 0, "unverified": 0}
    for cid, r in latest.items():
        c = _call(db, cid)
        if not is_absence(c):
            continue
        v16[r["outcome"]] = v16.get(r["outcome"], 0) + 1
        v15o = "hit" if (r["expired"] and r["outcome"] == "unverified") else r["outcome"]
        v15[v15o] = v15.get(v15o, 0) + 1
    return {"v16_rule": v16, "v15_rule": v15}
