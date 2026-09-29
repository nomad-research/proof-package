"""v15 §B: the ACK graph, indexed by effects.

**Two spaces.** The effect DAG is about the world. The ACK graph is about **knowability**: when a fact becomes
available, from whom, in what form. We have been storing the second as fields on the first (`due_at`,
`catalyst_class`), which is exactly why walks could not happen — *a field cannot branch.*

**ACK nodes are facts-with-dates, and the graph is a DAG.** One fact advances several effects at once: round 2's
force-majeure letter dated the allocation question, the requalification question and the co-product question
simultaneously. A shared ACK is **structural correlation on the time axis**, exactly as a shared factor is on the
exposure axis — and unlike a shared factor it is known before any price exists.

**`scheduled` vs `forced`** is the load-bearing distinction. Scheduled: results dates, regulatory calendars, filing
deadlines, index events. Forced: *the obligation exists and the date does not* — a force majeure letter must come when
a producer cannot serve contracted offtake; a restart statement must come; a regulator must answer inside a statutory
window. **A walk that advances only on calendared facts advances only where the market is already looking**, and would
inherit pricedness by construction. Forced ACKs are the only place a walk can find something a calendar-driven market
has not.

§B4 is built standing, per node, before any event, and is independently valuable even if the rest of v15 fails: legs
have failed the catalyst predicate since round 8 not because no dates existed but because we only ever looked per
round, per leg, at lock."""
import sqlite3
from datetime import date as _date

from . import config
from .db import append, get_row, insert_mutable
from .errors import ValidationError
from .util import dumps, loads

FIRING_DEFAULTS = {"delivered": 0}


def ack_add(conn: sqlite3.Connection, node: str, ack_kind: str, fact: str, source: str,
            due_at: str | None = None, obligation: str | None = None, holder_id: str | None = None,
            form: str | None = None, parent_ack_id: str | None = None, round_id: str | None = None,
            participant_class: str | None = None, attention: bool = False, standing: bool | None = None,
            basis: str | None = None, key: str | None = None) -> dict:
    """§B2/§B3. A scheduled ACK carries a date. **A forced ACK carries the obligation that generates it, not a date** —
    that is the whole content of the distinction, and refusing a date on a forced ACK is what stops the graph
    collapsing back into a calendar."""
    if ack_kind not in ("scheduled", "forced"):
        raise ValidationError("ack_kind is 'scheduled' or 'forced'")
    if ack_kind == "scheduled" and not due_at:
        raise ValidationError("a scheduled ACK is calendared: it needs a date")
    if ack_kind == "forced":
        if not obligation:
            raise ValidationError("a forced ACK carries the obligation that generates it: say what obliges the fact "
                                  "to be produced, and by whom")
        if due_at:
            raise ValidationError("a forced ACK has no public date -- that is what makes it forced. Recording one "
                                  "turns it back into a calendar entry, which is where the market already looks.")
    if not fact or not source:
        raise ValidationError("an ACK names the fact that becomes available and who it becomes available from")
    if participant_class and participant_class not in config.PARTICIPANT_CLASSES:
        raise ValidationError(f"participant_class must be one of {config.PARTICIPANT_CLASSES}")
    standing = (round_id is None) if standing is None else standing
    key = key or f"ack.{node.strip().lower()}.{(holder_id or '-')}.{fact.strip().lower()[:60]}"
    row = conn.execute("SELECT * FROM ack_nodes WHERE key = ?", (key,)).fetchone()
    if row:
        return {"ack_id": row["id"], "key": key, "created": False, "ack_kind": row["ack_kind"]}
    r = insert_mutable(conn, "ack_nodes", {
        "key": key, "node": node, "holder_id": holder_id, "ack_kind": ack_kind, "fact": fact, "source": source,
        "form": form, "due_at": due_at, "obligation": obligation, "parent_ack_id": parent_ack_id,
        "round_id": round_id, "participant_class": participant_class, "attention": int(bool(attention)),
        "standing": int(bool(standing)), "basis": basis})
    return {"ack_id": r["id"], "key": key, "created": True, "ack_kind": ack_kind,
            "dated": bool(due_at), "standing": bool(standing)}


def graph_for_node(conn: sqlite3.Connection, node: str, round_id: str | None = None,
                   as_of: str | None = None) -> dict:
    """§B4: the standing graph on a node, plus anything this round added. **Most of the graph is not about our
    event.**"""
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM ack_nodes WHERE lower(node) = lower(?) AND (round_id IS NULL OR round_id = ?) ORDER BY rowid",
        (node, round_id or ""))]
    fired = {f["ack_id"]: dict(f) for f in conn.execute("SELECT * FROM ack_firings ORDER BY rowid")}
    sched = [r for r in rows if r["ack_kind"] == "scheduled"]
    forced = [r for r in rows if r["ack_kind"] == "forced"]
    for r in rows:
        f = fired.get(r["id"])
        r["fired"] = bool(f)
        r["fired_at"] = f["fired_at"] if f else None
        r["delivered"] = bool(f["delivered"]) if f else None
    upcoming = sorted([r for r in sched if r["due_at"] and (not as_of or r["due_at"] >= as_of) and not r["fired"]],
                      key=lambda r: r["due_at"])
    return {"node": node, "as_of": as_of, "n": len(rows), "scheduled": sched, "forced": forced,
            "upcoming_in_date_order": upcoming,
            "next": (upcoming[0] if upcoming else None),
            "undated_obligations": [{"ack_id": r["id"], "fact": r["fact"], "obligation": r["obligation"],
                                     "source": r["source"]} for r in forced if not r["fired"]],
            "note": ("a walk that advances only on calendared facts advances only where the market is already "
                     "looking; the undated obligations are the half that can find something it has not")}


def calendar(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """§C2: **the calendar chooses the branch, not the operator.** Every ACK on the round's nodes, in date order.
    The walk advances on whichever fires first; if the operator picks which branch to walk toward, that is selection
    at generation two and it is the largest fitting risk in this version."""
    from .effects import list_effects
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    as_of = as_of or _date.today().isoformat()
    nodes = sorted({(e["node"] or "").lower() for e in list_effects(conn, round_id)} | {(ev.get("node") or "").lower()})
    nodes = [n for n in nodes if n]
    seen, rows = set(), []
    for n in nodes:
        g = graph_for_node(conn, n, round_id, as_of)
        for r in g["scheduled"] + g["forced"]:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            rows.append(r)
    open_ = [r for r in rows if not r["fired"]]
    dated = sorted([r for r in open_ if r["due_at"]], key=lambda r: r["due_at"])
    undated = [r for r in open_ if not r["due_at"]]
    eff_by_ack: dict[str, list[str]] = {}
    for e in list_effects(conn, round_id, include_eliminated=False):
        if e["ack_id"]:
            eff_by_ack.setdefault(e["ack_id"], []).append(e["id"])
    for r in rows:
        r["effect_ids"] = eff_by_ack.get(r["id"], [])
        # §B2: a shared ACK is structural correlation on the time axis, known before any price exists
        r["shared_by_n_effects"] = len(r["effect_ids"])
    return {"round_id": round_id, "as_of": as_of, "nodes": nodes, "n_acks": len(rows),
            "next_to_fire": (dated[0] if dated else None),
            "in_date_order": dated, "undated_forced": undated,
            "shared_acks": [r for r in rows if r["shared_by_n_effects"] > 1],
            "fired": [r for r in rows if r["fired"]],
            "note": "the walk advances on whichever ACK fires first; the operator does not choose the branch"}


def fire(conn: sqlite3.Connection, ack_id: str, fired_at: str, delivered: bool, round_id: str | None = None,
         delivered_fact: str | None = None, implied: str | None = None,
         successor_acks: list[dict] | None = None, successor_query: str | None = None,
         opens_effect_ids: list[str] | None = None, kills_effect_ids: list[str] | None = None,
         evidence_ids: list[str] | None = None, segment_id: str | None = None) -> dict:
    """§B5 + §C3 + §C6.

    **A fired ACK must deliver a fact.** "The date passed and nothing was said" is an absence fact: it **prunes**, it
    does not advance. Without that, "advance the walk" becomes "keep the round alive", and a walk that cannot
    terminate is a thesis that cannot be killed.

    **Successors are named at firing** — never afterwards, or the graph grows to fit whatever happened. The query
    that reached them is logged alongside.

    **Direction comes from the gap** (§C6): not from facts at lock, but from the difference between what the ACK
    delivered and what the surviving effects implied it would deliver. Both halves are on the ledger."""
    ack = get_row(conn, "ack_nodes", ack_id, "ACK")
    if conn.execute("SELECT 1 FROM ack_firings WHERE ack_id = ?", (ack_id,)).fetchone():
        raise ValidationError(f"ACK {ack_id} has already fired; a fact becomes available once")
    if delivered and not delivered_fact:
        raise ValidationError("a delivering ACK states the fact it delivered")
    if not delivered and successor_acks:
        raise ValidationError("this ACK delivered nothing, so the branch terminates (§B5): an absence fact prunes and "
                              "may not open a successor. No successor may be added to it later either.")
    gap = None
    if delivered and implied:
        gap = (f"implied: {implied} || delivered: {delivered_fact}")
    made = []
    for i, sc in enumerate(successor_acks or []):
        missing = {"node", "ack_kind", "fact", "source"} - set(sc)
        if missing:
            raise ValidationError(f"successor_acks[{i}] needs {sorted(missing)}")
        made.append(ack_add(conn, parent_ack_id=ack_id, round_id=round_id,
                            **{k: v for k, v in sc.items() if k != "parent_ack_id"})["ack_id"])
    row = append(conn, "ack_firings", {**FIRING_DEFAULTS, **{
        "ack_id": ack_id, "round_id": round_id, "fired_at": fired_at, "delivered": int(bool(delivered)),
        "delivered_fact": delivered_fact, "implied": implied, "gap": gap,
        "evidence_ids": dumps(evidence_ids or []), "opens_effect_ids": dumps(opens_effect_ids or []),
        "kills_effect_ids": dumps(kills_effect_ids or []), "successor_ack_ids": dumps(made),
        "successor_query": successor_query, "segment_id": segment_id}})
    for eid in (kills_effect_ids or []):
        from .effects import eliminate
        eliminate(conn, eid, f"the ACK fired and delivered a fact that closes this effect: {delivered_fact or 'nothing'}")
    return {"firing_id": row["id"], "ack_id": ack_id, "fired_at": fired_at, "delivered": bool(delivered),
            "prunes": not delivered, "gap": gap, "successor_ack_ids": made,
            "note": ("delivered nothing: this is an absence fact, the branch terminates and no successor may be "
                     "added" if not delivered else
                     "direction comes from the gap between what was implied and what was delivered, and the gap is "
                     "dated by the next ACK, which is already in the structure")}


def firings(conn: sqlite3.Connection, round_id: str | None = None) -> list[dict]:
    sql = "SELECT * FROM ack_firings"
    args: list = []
    if round_id:
        sql += " WHERE round_id = ?"
        args.append(round_id)
    out = []
    for r in conn.execute(sql + " ORDER BY rowid", args):
        d = dict(r)
        for k in ("evidence_ids", "opens_effect_ids", "kills_effect_ids", "successor_ack_ids"):
            d[k] = loads(d[k]) if d[k] else []
        d["delivered"] = bool(d["delivered"])
        out.append(d)
    return out


def build_standing(conn: sqlite3.Connection, node: str, holder_ids: list[str] | None = None,
                   as_of: str | None = None) -> dict:
    """§B4: **build the standing graph first.** Most of the graph is not about our event, and this is the piece that
    has blocked catalyst since round 8. Scheduled ACKs come from the scheduled-facts feed and the mechanical facts
    already in the store; forced ACKs are stated by the operator with the obligation that generates them, because an
    obligation is inferable from structure and a date is not."""
    from .scheduled import list_scheduled
    as_of = as_of or _date.today().isoformat()
    made, seen = [], 0
    hids = holder_ids or [r["holder_id"] for r in conn.execute(
        "SELECT DISTINCT holder_id FROM positions WHERE lower(node) = lower(?)", (node,))]
    for hid in hids:
        h = conn.execute("SELECT canonical_name FROM holders WHERE id = ?", (hid,)).fetchone()
        if not h:
            continue
        try:
            facts = list_scheduled(conn, holder_id=hid)
        except Exception:
            facts = []
        for f in facts:
            seen += 1
            if f.get("date") and f["date"] < as_of:
                continue
            r = ack_add(conn, node=node, ack_kind="scheduled", fact=f.get("kind") or "a scheduled statement",
                        source=f.get("source") or h["canonical_name"], due_at=f.get("date"), holder_id=hid,
                        form=f.get("sched_kind"), standing=True,
                        basis=f"standing: from the scheduled-facts feed on {h['canonical_name']}")
            if r["created"]:
                made.append(r["ack_id"])
    return {"node": node, "as_of": as_of, "holders": len(hids), "scheduled_facts_seen": seen,
            "acks_created": len(made), "ack_ids": made,
            "graph": graph_for_node(conn, node, as_of=as_of),
            "note": "standing and independently valuable: legs failed the catalyst predicate since round 8 not "
                    "because no dates existed but because we only ever looked per round, per leg, at lock"}
