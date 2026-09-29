"""v14 §A6: a glossary and an index, not a map.

No route-finder with an objective function. A path-finder trained on thirteen rounds would encode cascade priors drawn
from thirteen contingent, non-repeating propagations — limiting *and* wrong on the world's own terms — and it would
only ever surface paths already walked. So the harness offers two things and refuses the third:

* **A glossary of moves** (A6a): the callable surface stated plainly, with no claim about which move to use or in what
  order. `nomad_route` is gone; `nomad_adjacent` returns what shares factors with a leg and what the hop costs.
* **An index over the store** (A6b): what exists, what is callable, what is held, what has been done before,
  retrievable by shape rather than by name. The index reports **precedent, never endorsement** — the same distinction
  the library already draws between forbidding and advising.
* Not a recommendation. The walking is the operator's.

And (A6c) every move is logged with the operator's stated reason. The discipline moves off *which tools may be called*
and onto *what gets written and when*: a leg reached by seven deliberate hops is more auditable than one that appears
unexplained, so a richer toolkit improves the record rather than degrading it."""
import sqlite3

from .db import append
from .errors import ValidationError

MOVES: tuple[dict, ...] = (
    {"move": "fetch a document as of a date", "tool": "nomad_pit_fetch",
     "what": "a primary document as it stood at a date, with the fetch path recorded",
     "costs": "time, and a fetch that fails is itself a fact about reach"},
    {"move": "build an opposing pair on a node", "tool": "nomad_synthetic_build",
     "what": "a synthetic leg from listed holders with opposing signs on the same node",
     "costs": "a component discount per leg, and a cross-node hop costs another"},
    {"move": "check what would eliminate this leg", "tool": "nomad_surviving_risk",
     "what": "the anchors run over the leg with their preconditions, and what could not be evaluated",
     "costs": "nothing; it reads the store"},
    {"move": "look up a base rate", "tool": "nomad_base_rates",
     "what": "an institutional frequency with its denominator, source and knowable_from",
     "costs": "nothing; citing one is required on an occurrence call about an institution"},
    {"move": "find holders on a node", "tool": "nomad_positions_on_node",
     "what": "who the store says sits on a node, with signs and listedness",
     "costs": "nothing"},
    {"move": "find legs adjacent to this one and at what cost", "tool": "nomad_adjacent",
     "what": "parents, children, same-node counterparties and chain-adjacent holders, each with the cost of the hop",
     "costs": "a degree step, and whatever the hop does to the structural term"},
    {"move": "ask what settled a claim of this shape before", "tool": "nomad_precedent",
     "what": "the documents and carriers that settled claims of the same shape on the ledger",
     "costs": "nothing; it reports precedent and never endorses it"},
    {"move": "generate the space wide", "tool": "nomad_generate_space",
     "what": "every holder on the nodes, plus one hop, plus anything a hunch proposes",
     "costs": "legs that the anchors then have to cut; a wrong proposal costs an eliminated leg, not a scored miss"},
)


def glossary() -> dict:
    return {"moves": list(MOVES), "n": len(MOVES),
            "note": ("the callable surface, stated plainly. No ordering is implied and none is recommended: a "
                     "route-finder over thirteen contingent propagations would encode cascade priors that are both "
                     "limiting and wrong, and would only ever surface paths already walked")}


def log_move(conn: sqlite3.Connection, move: str, reason: str, round_id: str | None = None, target: str | None = None,
             result: str | None = None, cost: str | None = None) -> dict:
    """A6c: the move, the target, and the operator's stated reason for making it."""
    if not (move or "").strip() or not (reason or "").strip():
        raise ValidationError("a move is logged with what it was and why it was made: both move and reason are required")
    row = append(conn, "move_log", {"round_id": round_id, "move": move.strip(), "target": target,
                                    "reason": reason.strip(), "result": result, "cost": cost})
    return {"move_id": row["id"], "move": move.strip(), "round_id": round_id}


def moves_for(conn: sqlite3.Connection, round_id: str | None = None, limit: int = 100) -> list[dict]:
    sql, args = "SELECT * FROM move_log", []
    if round_id:
        sql += " WHERE round_id = ?"
        args.append(round_id)
    return [dict(r) for r in conn.execute(sql + " ORDER BY rowid DESC LIMIT ?", [*args, limit])]


# ---- A6b: the index -------------------------------------------------------------------------------------------------

def precedent(conn: sqlite3.Connection, call_type: str | None = None, node_kind: str | None = None,
              event_kind: str | None = None, limit: int = 12) -> dict:
    """What settled a claim of this shape before: the carriers that carried the resolution, the documents named, and
    how those calls went. Precedent, never endorsement — this is an index query over the store, not advice."""
    sql = ("SELECT p.call_type, p.target, p.claim, p.carrier, p.settling_document, e.event_kind, e.node_kind, "
           "       r.outcome, r.scorer_note, ev.event_date "
           "FROM predictions p JOIN rounds rd ON rd.id = p.round_id JOIN events ev ON ev.id = rd.event_id "
           "LEFT JOIN resolutions r ON r.prediction_id = p.id LEFT JOIN events e ON e.id = rd.event_id "
           "JOIN round_state s ON s.round_id = rd.id WHERE s.state != 'void'")
    args: list = []
    if call_type:
        sql += " AND p.call_type = ?"
        args.append(call_type)
    if node_kind:
        sql += " AND e.node_kind = ?"
        args.append(node_kind)
    if event_kind:
        sql += " AND e.event_kind = ?"
        args.append(event_kind)
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY ev.event_date DESC LIMIT ?", [*args, limit])]
    carriers: dict[str, int] = {}
    docs = []
    for r in rows:
        if r["carrier"]:
            carriers[r["carrier"]] = carriers.get(r["carrier"], 0) + 1
        if r.get("settling_document"):
            docs.append({"document": r["settling_document"], "call": r["target"], "outcome": r["outcome"]})
    outcomes: dict[str, int] = {}
    for r in rows:
        outcomes[r["outcome"] or "unresolved"] = outcomes.get(r["outcome"] or "unresolved", 0) + 1
    return {"query": {"call_type": call_type, "node_kind": node_kind, "event_kind": event_kind},
            "n": len(rows), "outcomes": outcomes,
            "carriers_that_settled_it": sorted(carriers.items(), key=lambda kv: -kv[1]),
            "settling_documents_named": docs,
            "rows": [{k: r[k] for k in ("event_date", "call_type", "target", "carrier", "outcome")} for r in rows],
            "note": "precedent, not endorsement: this says what settled a claim of this shape, never what to claim"}


def index(conn: sqlite3.Connection) -> dict:
    """A6b: what exists, what is callable, what is held, what has been done before."""
    def n(sql: str) -> int:
        return conn.execute(sql).fetchone()[0]
    return {
        "held": {"holders": n("SELECT COUNT(*) FROM holders"), "listed": n("SELECT COUNT(*) FROM holders WHERE listed = 1"),
                 "positions": n("SELECT COUNT(*) FROM positions"),
                 "nodes": n("SELECT COUNT(DISTINCT lower(node)) FROM positions"),
                 "node_facts": n("SELECT COUNT(*) FROM node_facts"), "carriers": n("SELECT COUNT(*) FROM carriers"),
                 "base_rates": n("SELECT COUNT(*) FROM base_rates"), "library_rules": n("SELECT COUNT(*) FROM library_rules")},
        "done": {"rounds": n("SELECT COUNT(*) FROM rounds"), "void": n("SELECT COUNT(*) FROM round_state WHERE state = 'void'"),
                 "predictions": n("SELECT COUNT(*) FROM predictions"), "resolutions": n("SELECT COUNT(*) FROM resolutions"),
                 "price_observations": n("SELECT COUNT(*) FROM price_observations"),
                 "surviving_risk_rows": n("SELECT COUNT(*) FROM surviving_risk"),
                 "moves_logged": n("SELECT COUNT(*) FROM move_log")},
        "callable": [m["tool"] for m in MOVES],
        "note": "an index over the store, not over strategy",
    }
