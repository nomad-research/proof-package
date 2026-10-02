"""Round lifecycle: the firewall state machine (§14).

States written to the ``round_state`` ledger (the spec's phases):

``admitted`` → ``pre_lock`` → (lock) → ``walking`` ⇄ ``pre_lock`` (each ACK firing opens a
segment whose clock is the firing's ``knowable_from``) → ``live`` (walk ended; live
retrieval opens) → ``scored``. ``void`` from anywhere.

The guard hook (``firewall/guard16.py``) reads ``state/phase.json``, which this module
rewrites on every transition, so the hook and the harness always agree.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .db import DB, ROOT, Refused, now_iso

PHASE_FILE = Path(os.environ.get("NOMAD16_PHASE_FILE") or ROOT / "state" / "phase.json")
STATES = {"admitted", "pre_lock", "walking", "live", "scored", "void"}


def get_round(db: DB, round_id: str) -> dict:
    r = db.one("rounds", "round_id=?", (round_id,))
    if r is None:
        raise Refused(f"no round {round_id}")
    return r


def meta(db: DB, round_id: str, field: str, default=None):
    r = db.one("round_meta", "round_id=? AND field=?", (round_id, field))
    return r["value"] if r else default


def set_meta(db: DB, round_id: str, field: str, value):
    prev = db.one("round_meta", "round_id=? AND field=?", (round_id, field))
    db.append("round_meta", round_id=round_id, field=field, value=value,
              supersedes=prev["id"] if prev else None)


def state(db: DB, round_id: str) -> str:
    r = db.one("round_state", "round_id=?", (round_id,))
    return r["state"] if r else "none"


def set_state(db: DB, round_id: str, new: str, reason: str = ""):
    if new not in STATES:
        raise ValueError(new)
    db.append("round_state", round_id=round_id, state=new, reason=reason)
    write_phase(db, round_id)


def segments(db: DB, round_id: str) -> list[dict]:
    return db.rows("segments", "round_id=?", (round_id,), order="id")


def current_segment(db: DB, round_id: str) -> dict:
    segs = segments(db, round_id)
    if not segs:
        raise Refused(f"round {round_id} has no segment")
    # a segment may be recorded twice (opened, then locked); the latest row per idx wins
    latest = {}
    for s in segs:
        latest[s["idx"]] = s
    return latest[max(latest)]


def is_locked(db: DB, round_id: str, idx: int) -> bool:
    return db.one("locks", "round_id=? AND segment_idx=?", (round_id, idx)) is not None


def clock(db: DB, round_id: str) -> str:
    return current_segment(db, round_id)["clock"]


def require_pre_lock(db: DB, round_id: str):
    st = state(db, round_id)
    if st != "pre_lock":
        raise Refused(f"round {round_id} is '{st}'; this is allowed only pre-lock")
    seg = current_segment(db, round_id)
    if is_locked(db, round_id, seg["idx"]):
        raise Refused(f"segment {seg['idx']} of {round_id} is locked; nothing may change it")


def active_logic(db: DB) -> str:
    """The logic_version of the round the phase file names ('v16' when none). v17 rounds refuse typed dates."""
    try:
        rid = json.loads(PHASE_FILE.read_text()).get("round_id")
        r = db.one("rounds", "round_id=?", (rid,)) if rid else None
    except (OSError, ValueError):
        return "v16"
    return (r or {}).get("logic_version") or "v16"


def write_phase(db: DB, round_id: str):
    seg = None
    try:
        seg = current_segment(db, round_id)
    except Refused:
        pass
    doc = {"round_id": round_id, "state": state(db, round_id),
           "segment": seg["idx"] if seg else None, "clock": seg["clock"] if seg else None,
           "written_at": now_iso(),
           "rule": "pre_lock/admitted/walking: live WebSearch and WebFetch denied, quarantined "
                   "paths denied; live/scored: live retrieval open"}
    PHASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PHASE_FILE.write_text(json.dumps(doc, indent=1) + "\n")
