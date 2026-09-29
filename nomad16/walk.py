"""The walk (§22.4, §14 backfilled walks).

After a segment locks, the round is ``walking``: the operator reads the ACK carriers
forward from the clock, one date at a time (the PIT fetcher enforces the frontier). The
first delivered fact fires the ACK; its ``knowable_from`` becomes the next segment's
clock and the pre-lock regime moves to it. ``walk_end`` opens live retrieval for scoring.
"""
from __future__ import annotations

from .db import DB, Refused
from .rounds import current_segment, get_round, is_locked, set_state, state
from .util import day, ts


def pending_hit(db: DB, round_id: str) -> str | None:
    """The date of an unresolved walk_scan hit, if any: reads past it are refused until the ACK
    fires or the date is recorded as not delivering (walk_read ... not_delivering)."""
    seg = current_segment(db, round_id)
    hits = db.rows("notes", "round_id=? AND subject='walk_hit' AND segment_idx=?", (round_id, seg["idx"]))
    if not hits:
        return None
    d = hits[-1]["text"].split("|")[0].strip()
    cleared = db.rows("notes", "round_id=? AND subject='walk_hit_cleared' AND segment_idx=?", (round_id, seg["idx"]))
    if any(c["text"].split("|")[0].strip() == d for c in cleared):
        return None
    return d


def frontier(db: DB, round_id: str) -> str:
    """The latest date read forward on the walk (starts at the current segment clock)."""
    seg = current_segment(db, round_id)
    reads = [n for n in db.rows("notes", "round_id=? AND subject='walk_read'", (round_id,))]
    f = seg["clock"]
    for n in reads:
        d = n["text"].split("|")[0].strip()
        if ts(d) > ts(f):
            f = d
    return f


def ack_fire(db: DB, ack_id: str, delivered: bool, knowable_from: str, evidence_ids: list,
             outcome_id: str | None = None, delivered_fact: str | None = None,
             successor_ack_ids: list | None = None) -> dict:
    a = db.get("ack_nodes", ack_id)
    if a is None:
        raise Refused(f"no ACK {ack_id}")
    rid = a["round_id"]
    st = state(db, rid)
    if st not in {"walking", "live"}:
        raise Refused(f"an ACK fires after its segment locks (round is '{st}')")
    if a.get("status") != "ratified":
        raise Refused("only a ratified ACK fires")
    seg = current_segment(db, rid)
    if not is_locked(db, rid, seg["idx"]):
        raise Refused("the current segment is not locked")
    if delivered and not outcome_id:
        raise Refused("a delivered firing names its outcome_id from the vocabulary (smoke 19)")
    if not delivered and successor_ack_ids:
        raise Refused("a non-delivering firing prunes its branch and may not name successors")
    if not evidence_ids:
        raise Refused("a firing cites the document that delivered (or the carrier read silent)")
    if ts(knowable_from) <= ts(seg["clock"]):
        raise Refused("the delivered fact must be knowable after the current clock")
    if delivered:
        vocab = db.get("outcome_vocabs", a["notice_kind"])
        ids = [o["outcome_id"] for o in (vocab or {}).get("outcomes", [])]
        if outcome_id not in ids:
            raise Refused(f"outcome {outcome_id} is not in the {a['notice_kind']} vocabulary {ids}")
    fid = f"{rid}:F{len(db.rows('ack_firings', 'round_id=?', (rid,))) + 1:02d}"
    new_idx = seg["idx"] + 1 if delivered else None
    row = db.append("ack_firings", firing_id=fid, ack_id=ack_id, round_id=rid, fired_at=knowable_from,
                    delivered=bool(delivered), delivered_fact=delivered_fact, outcome_id=outcome_id,
                    knowable_from=knowable_from, successor_ack_ids=successor_ack_ids or [],
                    evidence_ids=evidence_ids, segment_idx_opened=new_idx)
    out = {"firing": fid, "delivered": delivered, "outcome_id": outcome_id}
    hit = pending_hit(db, rid)
    if hit is not None:
        db.append("notes", round_id=rid, segment_idx=seg["idx"], subject="walk_hit_cleared",
                  text=f"{hit} | ack_fire {fid} | {','.join(evidence_ids)}")
    if outcome_id == "other":
        n = len(db.rows("pianos")) + 1
        db.append("pianos", piano_id=f"PI{n:03d}", round_id=rid, basket_id=None,
                  description=f"{ack_id} delivered an outcome outside its vocabulary: {delivered_fact}",
                  outside="vocabulary", cost=None)
        out["piano"] = True
    # mark open baskets at the firing
    from . import paper
    try:
        out["marks"] = paper.mark(db, rid, knowable_from, "ack_fired")
        if a.get("attention"):
            out["attention_exits"] = [paper.exit_basket(db, b, knowable_from, "attention_ack")
                                      for b in sorted({p["basket_id"] for p in paper._open(db, rid)})]
    except Refused as e:
        out["marks"] = f"not marked: {e}"
    if delivered:
        db.append("segments", round_id=rid, idx=new_idx, clock=knowable_from, opened_by_ack_id=ack_id,
                  opened_by_firing_id=fid, locked_at=None, lock_hash=None, manifest_id=None, wall_clock=None)
        set_state(db, rid, "pre_lock", f"{ack_id} fired; segment {new_idx} opens at clock {knowable_from}")
        out["next"] = (f"segment {new_idx} is pre-lock at clock {knowable_from}: add positions the fact changes "
                       f"(knowable_from = the clock), re-derive, re-state theses, then lock the segment")
    return out


def walk_read(db: DB, round_id: str, through: str, carrier: str, result: str, evidence_ids: list) -> dict:
    """Record that a carrier was read in full through a date on the walk (silent or spoke)."""
    if state(db, round_id) != "walking":
        raise Refused("walk reads happen while the round is walking")
    if result not in {"silent", "spoke", "not_delivering"}:
        raise Refused("result is silent, spoke or not_delivering")
    idx = current_segment(db, round_id)["idx"]
    hit = pending_hit(db, round_id)
    if result == "not_delivering":
        if hit is None or day(through) != hit:
            raise Refused("not_delivering clears a pending walk_scan hit, on the hit's own date")
        if not evidence_ids:
            raise Refused("clearing a hit cites the document read")
        db.append("notes", round_id=round_id, segment_idx=idx, subject="walk_hit_cleared",
                  text=f"{hit} | {carrier} | {','.join(evidence_ids)}")
    return db.append("notes", round_id=round_id, segment_idx=idx,
                     subject="walk_read", text=f"{through} | {carrier} | {result} | {','.join(evidence_ids)}")


def walk_end(db: DB, round_id: str, reason: str) -> dict:
    st = state(db, round_id)
    if st != "walking":
        raise Refused(f"the walk ends from 'walking' (round is '{st}')")
    seg = current_segment(db, round_id)
    if not is_locked(db, round_id, seg["idx"]):
        raise Refused("the last segment must be locked before live retrieval opens")
    set_state(db, round_id, "live", f"walk ended: {reason}; live retrieval opens for scoring")
    return {"state": "live", "segments": seg["idx"] + 1}


def walk_scan(db: DB, round_id: str, source: str, until: str, reason: str, unit: str | None = None,
              op: str = ">", value: float = 0, facility: str | None = None, cik: str | None = None,
              forms: list | None = None) -> dict:
    """Read a carrier forward from the frontier one date at a time, stopping at the first date
    whose document matches a predicate declared up front. Mechanical: the operator still
    decides what the matching document delivers, and fires the ACK.

    - ``nrc_status``: stop when ``unit``'s power satisfies ``op value`` (e.g. power > 0).
    - ``nrc_en``: stop at the first report carrying an event for ``facility``.
    - ``edgar_filings``: stop at the first filing by ``cik`` of a form in ``forms`` dated after the frontier.
    """
    import datetime as _dt
    from .pit import pit_fetch
    if state(db, round_id) != "walking":
        raise Refused("walk_scan runs while the round is walking")
    ops = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "==": lambda a, b: a == b}
    if op not in ops:
        raise Refused("op is one of > >= < ==")
    read, hit = [], None
    while True:
        f = frontier(db, round_id)
        d = (ts(f[:10]) + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if ts(d) > ts(until):
            break
        if source == "nrc_status":
            r = pit_fetch(db, round_id, "nrc_status", d, d, reason)
            rows = [u for u in r.get("units", []) if unit and u["unit"].lower() == unit.lower()]
            read.append({"date": d, "evidence_id": r.get("evidence_id"),
                         "unit": rows[0] if rows else None, "status": r.get("status")})
            if rows and ops[op](rows[0]["power"], value):
                hit = read[-1]
                break
        elif source == "nrc_en":
            r = pit_fetch(db, round_id, "nrc_en", d, d, reason)
            evs = [e for e in r.get("events", []) if facility and facility.lower() in
                   str(e["fields"].get("Facility") or e["fields"].get("Licensee") or "").lower()]
            read.append({"date": d, "evidence_id": r.get("evidence_id"), "matches": len(evs)})
            if evs:
                hit = {"date": d, "evidence_id": r.get("evidence_id"), "events": evs}
                break
        elif source == "edgar_filings":
            r = pit_fetch(db, round_id, "edgar_filings", cik, d, reason)
            new = [x for x in r.get("filings", []) if x["filing_date"] == d and (not forms or x["form"] in forms)]
            read.append({"date": d, "evidence_id": r.get("evidence_id"), "matches": len(new)})
            if new:
                hit = {"date": d, "evidence_id": r.get("evidence_id"), "filings": new}
                break
        else:
            raise Refused("walk_scan reads nrc_status, nrc_en or edgar_filings")
    if hit is not None:
        db.append("notes", round_id=round_id, segment_idx=current_segment(db, round_id)["idx"],
                  subject="walk_hit", text=f"{hit['date']} | {source} | {hit.get('evidence_id')}")
    return {"read_through": frontier(db, round_id), "dates_read": len(read), "hit": hit,
            "last_reads": read[-5:],
            "note": "no match through the frontier" if hit is None else
                    "first match: read the document; if it delivers, ack_fire with its outcome and knowable_from"}
