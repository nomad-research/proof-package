"""v15 §C/§E: the walk, and why stopping is not a rule.

**The operator walks; the harness records.** The harness holds the store the operator queries, logs every move with
its stated reason, and keeps the ledger of what was considered and dropped. It does **not** generate successors — a
harness that generates them generates from what it can already index, which is the cascade-prior problem the
route-finder was deleted over, and the novel composition never happens. What gets logged is the operator's search, not
machine output.

**The calendar chooses the branch, not the operator** (§C2). Enumerate every ACK on the node's graph in date order;
the walk advances on whichever fires first. If the operator picks which branch to walk toward, that is selection at
generation two and it is the largest fitting risk in this version.

**Segment locking** (§C5). What is locked at each ACK is that *segment*: the set at ACK₀ is a claim about what
survives until ACK₁. When ACK₁ fires a new segment locks with its own claims, falsifiers and carriers, with lineage.
Nothing is rewritten; the set grows a generation. Scoring is per segment — a wrong turn at ACK₁ is a wrong turn and
does not contaminate the round, and a chain reaching generation three with three hits is visibly different from three
independent hits.

**§C7 — why this escapes the wall map's bind.** v14 §B found `stake` and `pricedness` anti-correlated: when stake is
finally high the fact is already in the price. But **stake created by a firing ACK cannot have been pre-priced,
because the fact did not exist to price.** That is the argument for the walk, and it comes from the wall map's own
numbers rather than from enthusiasm about them."""
import sqlite3
from datetime import date as _date

from . import config
from .db import append, get_row
from .errors import StateError, ValidationError
from .util import dumps, loads


# ---- §C5: segments ---------------------------------------------------------------------------------------------

def segments(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM segments WHERE round_id = ? ORDER BY idx, rowid", (round_id,)):
        d = dict(r)
        d["effect_ids"] = loads(d["effect_ids"]) if d["effect_ids"] else []
        d["next_ack_ids"] = loads(d["next_ack_ids"]) if d["next_ack_ids"] else []
        out.append(d)
    return out


def lock_segment(conn: sqlite3.Connection, round_id: str, claim: str, effect_ids: list[str],
                 next_ack_ids: list[str] | None = None, opened_by_ack_id: str | None = None,
                 opened_by_firing_id: str | None = None, locked_at: str | None = None) -> dict:
    """§C5: lock this segment. The set locked here is a claim about **what survives until the next ACK** — not about
    the end of the round. Nothing earlier is rewritten."""
    get_row(conn, "rounds", round_id, "round")
    if not claim or len(claim.strip()) < 12:
        raise ValidationError("a segment states what it claims survives until the next ACK")
    if not effect_ids:
        raise ValidationError("a segment with no effects is not a claim about anything")
    prior = segments(conn, round_id)
    if prior and opened_by_ack_id is None:
        raise ValidationError("segment 0 is locked at the round's lock; every later segment is opened by an ACK "
                              "firing (§C2: the calendar chooses the branch, not the operator)")
    idx = len(prior)
    row = append(conn, "segments", {
        "round_id": round_id, "idx": idx, "parent_segment_id": (prior[-1]["id"] if prior else None),
        "opened_by_ack_id": opened_by_ack_id, "opened_by_firing_id": opened_by_firing_id, "claim": claim,
        "effect_ids": dumps(effect_ids), "next_ack_ids": dumps(next_ack_ids or []),
        "locked_at": locked_at or _date.today().isoformat()})
    # the effect rows are not stamped after the fact: `effects` is append-only, and a segment's membership lives on
    # the segment row, which is what makes "nothing is rewritten; the set grows a generation" literally true
    return {"segment_id": row["id"], "idx": idx, "n_effects": len(effect_ids),
            "parent_segment_id": prior[-1]["id"] if prior else None,
            "note": "scoring is per segment: a wrong turn here is a wrong turn and does not contaminate the round"}


# ---- §C2/§C4: advancing ----------------------------------------------------------------------------------------

def advance(conn: sqlite3.Connection, round_id: str, ack_id: str, as_of: str | None = None) -> dict:
    """§C2 + §C4: refuse to advance a branch whose ACK has not fired, and refuse to advance on any ACK but the one
    the calendar reached first. Depth-first: follow the branch a firing opened to its own next ACK before widening,
    because the interesting content is at generation two and three and breadth-first spends the frontier on shallow
    effects."""
    from . import acks
    as_of = as_of or _date.today().isoformat()
    cal = acks.calendar(conn, round_id, as_of)
    fired = {f["ack_id"] for f in acks.firings(conn) if f["ack_id"]}
    if ack_id not in fired:
        nxt = cal["next_to_fire"]
        raise StateError(
            f"ACK {ack_id} has not fired, so there is nothing to advance on. The calendar chooses the branch: the "
            f"next ACK to fire is {nxt['id'] if nxt else 'none dated'} "
            f"({nxt['fact'] if nxt else 'no dated ACK on this round'}"
            f"{' due ' + nxt['due_at'] if nxt and nxt.get('due_at') else ''}). "
            "Picking which branch to walk toward is selection at generation two, which is the largest fitting risk "
            "in this version.")
    firing = [f for f in acks.firings(conn) if f["ack_id"] == ack_id][0]
    if not firing["delivered"]:
        raise StateError("this ACK delivered nothing (§B5). An absence fact prunes: the branch terminates and no "
                         "successor may be added to it. A walk that cannot terminate is a thesis that cannot be "
                         "killed.")
    # depth-first: any earlier-dated ACK still open is a wider branch, not a deeper one
    earlier = [a for a in cal["in_date_order"]
               if a["due_at"] and firing["fired_at"] and a["due_at"] < firing["fired_at"] and not a["fired"]]
    return {"round_id": round_id, "ack_id": ack_id, "firing_id": firing["id"], "as_of": as_of,
            "delivered_fact": firing["delivered_fact"], "gap": firing["gap"],
            "opens_effect_ids": firing["opens_effect_ids"], "kills_effect_ids": firing["kills_effect_ids"],
            "successor_ack_ids": firing["successor_ack_ids"],
            "unfired_earlier_acks": [{"ack_id": a["id"], "due_at": a["due_at"], "fact": a["fact"]} for a in earlier],
            "note": ("depth-first (§C4): follow this firing's own successors before widening. "
                     + (f"{len(earlier)} earlier-dated ACK(s) are still open and are recorded as skipped width, not "
                        "as a chosen branch" if earlier else "no earlier-dated ACK is still open"))}


# ---- §E: convergence, and why stopping is not a rule -----------------------------------------------------------

def convergence(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """§E1–§E3. As ACKs fire the viable set narrows, and it narrows *toward* the market's interpretation, because
    price is the aggregate compression. **Convergence to price is residual recovery** — the exit condition as a
    property of the DAG rather than a price target.

    So pruning is measured, not scheduled (§E2), and it is measured at each firing rather than on a calendar.

    **And it must be managed or there is no edge** (§E3). Prune everything divergent and the frontier converges to
    price and holds nothing. **The divergent branches are the position.** Convergence prunes the converged, never the
    divergent, and a frontier with zero divergence held reads as failure, not as tidiness."""
    from .effects import list_effects
    from .rounds import list_predictions
    as_of = as_of or _date.today().isoformat()
    implied_by_effect: dict[str, dict] = {}
    from .effects import effect_for_position
    for p in list_predictions(conn, round_id):
        if p.get("implied_value") is None:
            continue
        eid = p.get("effect_id") or (effect_for_position(conn, round_id, p["position_id"]) if p.get("position_id")
                                     else None)
        if eid:
            implied_by_effect[eid] = {"implied": p["implied_value"], "method": p.get("implied_method"),
                                      "as_of": p.get("implied_as_of"), "basis": p.get("implied_basis")}
    converged, divergent, unread = [], [], []
    for e in list_effects(conn, round_id, include_eliminated=False):
        imp = implied_by_effect.get(e["id"])
        row = {"effect_id": e["id"], "holder_id": e["holder_id"], "node": e["node"], "kind": e["effect_kind"],
               "magnitude": e["magnitude"], "depth": e["depth"], "support": e["attenuated_support"]}
        if imp is None or e["magnitude"] is None:
            row["why"] = ("no implied reading on this effect, so the distance from the price-implied path cannot be "
                          "computed: unevaluable is a value, not a verdict")
            unread.append(row)
            continue
        gap = abs(e["magnitude"] - imp["implied"])
        row |= {"implied": imp["implied"], "gap": round(gap, 4), "implied_basis": imp["basis"]}
        (converged if gap < config.CONVERGENCE_THRESHOLD else divergent).append(row)
    held = len(divergent)
    # Unevaluable is a value, not a verdict -- and it is not convergence. A frontier with nothing readable has not
    # converged to price; it has never been compared to price. Reporting those two as one number would let the round
    # claim the tidy failure instead of the honest one.
    readable = len(converged) + held
    if held:
        state, note = "divergence_held", (
            f"{held} divergent branch(es) held; the {len(converged)} converged one(s) may be pruned, and pruning is "
            "measured at each firing rather than scheduled")
    elif readable:
        state, note = "converged_to_price", (
            "divergence_held is 0 over branches that COULD be read: the frontier has converged to price and holds "
            "nothing. That reads as FAILURE, not as tidiness -- convergence prunes the converged and never the "
            "divergent, and the divergent branches ARE the position.")
    else:
        state, note = "unreadable", (
            f"divergence_held is 0 because NOTHING WAS READABLE: {len(unread)} effect(s) carry no implied reading, so "
            "the distance from the price-implied path could not be computed on any of them. This is not convergence "
            "and must not be reported as it -- an unmeasured frontier is not a converged one. Fix the implied "
            "readings before reading anything into this number.")
    return {"round_id": round_id, "as_of": as_of, "threshold": config.CONVERGENCE_THRESHOLD,
            "converged": converged, "divergent": divergent, "unreadable": unread,
            "divergence_held": held, "readable_branches": readable, "unreadable_branches": len(unread),
            "prunable": [r["effect_id"] for r in converged],
            "state": state,
            "zero_divergence_held": held == 0 and readable > 0,
            "divergence_unevaluable": readable == 0,
            "note": note}


def prune(conn: sqlite3.Connection, round_id: str, effect_ids: list[str], as_of: str | None = None) -> dict:
    """§E2/§E3: prune converged branches only. A divergent branch offered for pruning is refused by name."""
    from .effects import eliminate
    c = convergence(conn, round_id, as_of)
    ok = {r["effect_id"] for r in c["converged"]}
    div = {r["effect_id"]: r for r in c["divergent"]}
    bad = [e for e in effect_ids if e in div]
    if bad:
        raise ValidationError(
            f"refused: {bad} are divergent, not converged. Convergence prunes the converged and never the divergent "
            "-- the divergent branches are the position, and pruning them converges the frontier to price and leaves "
            "nothing held.")
    unknown = [e for e in effect_ids if e not in ok]
    if unknown:
        raise ValidationError(f"refused: {unknown} have no implied reading, so convergence is unevaluable on them. "
                              "Unevaluable is a value, not a verdict: it does not license a prune.")
    for e in effect_ids:
        eliminate(conn, e, "pruned: its remaining implications no longer differ materially from the price-implied "
                           "path at the same nodes (§E2), so the residual has been recovered")
    return {"round_id": round_id, "pruned": effect_ids, "divergence_held": c["divergence_held"]}


def walk_report(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """Everything the walk is required to show per round, in one place."""
    from . import acks, contradiction, effects
    as_of = as_of or _date.today().isoformat()
    segs = segments(conn, round_id)
    fs = acks.firings(conn, round_id)
    w = effects.width(conn, round_id)
    conv = convergence(conn, round_id, as_of)
    sup = effects.support(conn, round_id)
    return {"round_id": round_id, "as_of": as_of,
            "segments": [{"idx": s["idx"], "segment_id": s["id"], "claim": s["claim"], "n_effects": len(s["effect_ids"]),
                          "opened_by_ack_id": s["opened_by_ack_id"], "locked_at": s["locked_at"]} for s in segs],
            "generation": len(segs) - 1 if segs else 0,
            "firings": [{"ack_id": f["ack_id"], "fired_at": f["fired_at"], "delivered": f["delivered"],
                         "gap": f["gap"], "successors": len(f["successor_ack_ids"])} for f in fs],
            "delivered": sum(1 for f in fs if f["delivered"]), "pruned_by_absence": sum(1 for f in fs if not f["delivered"]),
            "generation_width": w["generation_width"], "elimination_rate": w["elimination_rate"],
            "by_depth": w["by_depth"], "root_depth": w["root_depth"], "frontier": w["frontier"],
            "divergence_held": conv["divergence_held"], "zero_divergence_held": conv["zero_divergence_held"],
            "divergence_state": conv["state"], "divergence_unevaluable": conv["divergence_unevaluable"],
            "unreadable_branches": conv["unreadable_branches"],
            "support_rankings_agree": sup["rankings_agree"],
            "bridge_paths": effects.bridge_paths(conn, round_id)["n"],
            "contradictions": len(contradiction.detect(conn, round_id)["contradictions"]),
            "calendar_next": acks.calendar(conn, round_id, as_of)["next_to_fire"],
            "watch": {"divergence_held": "converging to price and holding nothing is comfortable and worthless",
                      "support_rankings": "agreement means cross-membership is measuring nothing",
                      "root_depth": "interesting effects all three re-roots deep means we are justifying distance"}}
