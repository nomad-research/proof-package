"""v14 §A2: permissive generation.

Round 13 ran the elimination half correctly — eight of ten legs killed before retrieval, every survivor named in
advance, the prices agreeing — and the generation half badly: ten legs decomposed by hand. Strong constraints over a
narrow space give nothing. The anchors are only worth having if there is a space wide enough for them to cut.

So generation is mechanical and wide at lock: every holder with any position on the event's nodes, at every degree the
store can reach, plus everything one hop away from those (parent, child, same-node counterparty, chain-adjacent). An
analogy, a remembered pattern or the operator's sense that this looks like that may **propose** a leg into the space
and may never support one. Only anchors and fetched facts keep it there. A wrong analogy costs an eliminated leg
rather than a scored miss, which is the whole point of moving the operator's intuition to the generation side.

This supersedes v11 §A3's refusal to generate legs on a clean round. That rule existed because mechanical legs were a
substitute for the operator's decomposition on a round where the outcome was known. Under v14 the decomposition is not
the operator's job at all: generation is wide by construction and the operator's judgement moves into the elimination
and the vector, both of which are recorded per leg."""
import sqlite3

from . import config
from .db import get_row
from .errors import ValidationError


def _holders_on(conn: sqlite3.Connection, node: str) -> list[str]:
    return [r["holder_id"] for r in conn.execute(
        "SELECT DISTINCT holder_id FROM positions WHERE lower(node) = lower(?) ORDER BY rowid", (node,))]


def _degree_for(conn: sqlite3.Connection, holder_id: str, origin: str) -> int:
    """Degree from the store, not from the operator: a plant or facility on the node is the node, a company with kin on
    it is one step out, a hop is one step further than whatever it hopped from."""
    h = conn.execute("SELECT kind, parent_id FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h:
        return 3
    if origin.startswith("hop"):
        return 2
    if h["kind"] in ("plant", "facility"):
        return 0
    kin = conn.execute("SELECT COUNT(*) FROM holders WHERE parent_id = ? OR id = ?", (holder_id, h["parent_id"] or "")).fetchone()[0]
    return 1 if kin else 2


def one_hop(conn: sqlite3.Connection, holder_id: str, node: str) -> list[dict]:
    """Everything one hop from a leg: the holder's parent, its children, anyone else holding a position on the same
    node, and anyone sharing a node with it elsewhere (chain-adjacent)."""
    out: list[dict] = []
    h = conn.execute("SELECT parent_id, canonical_name FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h:
        return out
    if h["parent_id"]:
        out.append({"holder_id": h["parent_id"], "node": node, "origin": "hop_parent",
                    "basis": f"parent of {h['canonical_name']}, which holds a position on {node}"})
    for c in conn.execute("SELECT id, canonical_name FROM holders WHERE parent_id = ?", (holder_id,)):
        out.append({"holder_id": c["id"], "node": node, "origin": "hop_child",
                    "basis": f"subsidiary of {h['canonical_name']} on {node}"})
    for r in conn.execute("SELECT DISTINCT holder_id FROM positions WHERE lower(node) = lower(?) AND holder_id != ?", (node, holder_id)):
        out.append({"holder_id": r["holder_id"], "node": node, "origin": "hop_counterparty",
                    "basis": f"holds a position on {node} alongside {h['canonical_name']}"})
    for r in conn.execute(
            "SELECT DISTINCT p2.holder_id, p2.node FROM positions p1 JOIN positions p2 ON p2.node = p1.node "
            "WHERE p1.holder_id = ? AND p2.holder_id != ? AND lower(p1.node) != lower(?)", (holder_id, holder_id, node)):
        out.append({"holder_id": r["holder_id"], "node": r["node"], "origin": "hop_chain",
                    "basis": f"shares node {r['node']} with {h['canonical_name']}, which is on {node}"})
    return out


def generate_space(conn: sqlite3.Connection, round_id: str, nodes: list[str] | None = None,
                   proposals: list[dict] | None = None, hops: bool = True, write: bool = True,
                   mechanism_ids: list[str] | None = None) -> dict:
    """A2: the whole candidate space for a round, before any elimination. `generation_width` is what it returns."""
    from .rounds import list_touched_set, touched_set_add
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    from .effects import node_kind_of
    nodes = [n.strip() for n in (nodes or ([ev["node"]] if ev.get("node") else [])) if n and n.strip()]
    if not nodes:
        raise ValidationError("no node on the event and none passed: name the node(s) to generate from")
    # v15 §I1: attribute nodes are positions, and they are summed in construction -- they never propose an effect and
    # never put a leg on the board. A shared listing venue is a loading, not a transmission path.
    attribute_nodes = [n for n in nodes if node_kind_of(conn, n) == "attribute"]
    nodes = [n for n in nodes if n not in attribute_nodes]
    if not nodes:
        raise ValidationError(f"every node passed is an attribute node ({attribute_nodes}). An attribute node never "
                              "proposes an effect: it is summed in construction and traversed never.")
    existing = {(t["holder_id"], (t["node"] or "").lower()) for t in list_touched_set(conn, round_id)}
    space: dict[tuple[str, str], dict] = {}

    def add(holder_id: str, node: str, origin: str, basis: str, proposed_by: str | None = None):
        key = (holder_id, node.lower())
        if key in space:
            return
        h = conn.execute("SELECT canonical_name FROM holders WHERE id = ?", (holder_id,)).fetchone()
        if not h:
            return
        space[key] = {"holder_id": holder_id, "holder": h["canonical_name"], "node": node, "origin": origin,
                      "basis": basis, "proposed_by": proposed_by, "degree": _degree_for(conn, holder_id, origin),
                      "already_on_round": key in existing}

    for node in nodes:
        for hid in _holders_on(conn, node):
            add(hid, node, "position", f"holds a position on {node} in the positions store")
    if hops:
        for (hid, node) in list(space):
            for hop in one_hop(conn, hid, space[(hid, node)]["node"]):
                if node_kind_of(conn, hop["node"]) == "attribute":
                    continue        # §I1: a hop onto a shared loading is co-movement, not a path
                add(hop["holder_id"], hop["node"], hop["origin"], hop["basis"])
    for i, pr in enumerate(proposals or []):
        pr = dict(pr)
        missing = {"holder_id", "node", "reason"} - set(pr)
        if missing:
            raise ValidationError(f"proposals[{i}] needs {sorted(missing)}: a proposal names what it puts on the board and why")
        add(pr["holder_id"], pr["node"], pr.get("origin") or "analogy", pr["reason"], proposed_by=pr.get("proposed_by") or "operator")

    rows = [v for v in space.values() if not v["already_on_round"]]
    written = 0
    if write and rows:
        written = touched_set_add(conn, round_id, [
            {"holder_id": r["holder_id"], "degree": r["degree"], "node": r["node"],
             "position_summary": f"[{r['origin']}] {r['basis']}"[:400], "substitutability": "unknown",
             "mechanism_ids": mechanism_ids or []} for r in rows], leg_source="generated")["count"]
    by_origin: dict[str, int] = {}
    for v in space.values():
        by_origin[v["origin"]] = by_origin.get(v["origin"], 0) + 1
    return {"round_id": round_id, "nodes": nodes, "attribute_nodes_skipped": attribute_nodes,
            "generation_width": len(space), "written": written,
            "already_on_round": sum(1 for v in space.values() if v["already_on_round"]),
            "by_origin": by_origin, "by_degree": {d: sum(1 for v in space.values() if v["degree"] == d) for d in sorted({v["degree"] for v in space.values()})},
            "legs": sorted(space.values(), key=lambda x: (x["degree"], x["holder"])),
            "narrow": len(space) < config.GENERATION_MIN_WIDTH,
            "note": ("generation is narrower than round 13's hand decomposition, which is the number to beat: widen the "
                     "nodes or add proposals" if len(space) < config.GENERATION_MIN_WIDTH else None)}


def adjacent(conn: sqlite3.Connection, holder_id: str, node: str, round_id: str | None = None) -> dict:
    """A6a: what shares factors with this leg, and what the hop costs. No ranking, no recommendation, no objective
    function — a path-finder trained on thirteen contingent propagations would encode cascade priors that are limiting
    and wrong on the world's own terms, and would only ever surface paths already walked. The walking is the operator's."""
    h = conn.execute("SELECT canonical_name FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h:
        raise ValidationError(f"no holder {holder_id!r}")
    out = []
    for hop in one_hop(conn, holder_id, node):
        hh = conn.execute("SELECT canonical_name, listed, options_listed FROM holders WHERE id = ?", (hop["holder_id"],)).fetchone()
        if not hh:
            continue
        cost = {"degree_step": 1,
                "structural": "a further step from the event, so the path has one more link to be admissible about",
                "expression": ("an instrument exists" if hh["listed"] else "unlisted: nothing to hold"),
                "same_node": hop["origin"] in ("hop_counterparty", "hop_parent", "hop_child")}
        out.append({"holder_id": hop["holder_id"], "holder": hh["canonical_name"], "node": hop["node"],
                    "relation": hop["origin"], "basis": hop["basis"], "listed": bool(hh["listed"]), "cost": cost})
    return {"from": {"holder_id": holder_id, "holder": h["canonical_name"], "node": node},
            "neighbours": out, "n": len(out),
            "note": "neighbours and hop costs only; the harness does not rank them and does not recommend one"}
