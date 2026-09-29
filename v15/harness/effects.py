"""v15 §A/§F/§G: the effect DAG.

**The effect, not the leg, is the unit.** Two diagnoses collapsed into one change:

* A round is a snapshot and should be a walk. The facts that generate *direction* do not exist at lock — that is the
  whole content of the force majeure letter, the restart date, the caption, the results print. What exists at lock is
  enough to say what will **not** move and structurally not enough to say what will. That is 0/14 in one sentence.
* A leg carries one sign and the world does not. A concentrate buyer facing a smelter outage has higher input cost
  **and** volume shortfall **and** a delivery obligation it may not meet **and**, if diversified, better pricing on its
  own competing output. Four effects, different magnitudes, different timings, different carriers, some opposed.

They are the same object, because an effect is what makes the next holder reachable: output falls (d1) → the buyer's
input cost rises (d2) → that buyer's customer's price rises (d3). The chain is not holder→holder with effects
attached; **the chain is effects, and holders are where each effect lands.** And `d1 → d3` need not route through the
same `d2` as `d1 → d2`, so the structure is a **DAG over effects** and depth is depth in that DAG rather than hops
between companies. Two effects on the same holder can sit at different depths, which the leg model could not express
at all.

An effect row is deliberately the same shape as a call: it **is** a claim, with a carrier and a falsifier, scored on
its own. A holder with five effects has five chances to be wrong, not five chances to be right.

**There is no sign field anywhere** (§A3). Sign is a projection applied at generation time, which is the worst possible
moment for it: it forces the answer before the work and discards everything that does not fit. Net direction is
derived late, over the holding window, from magnitudes and dates already recorded."""
import sqlite3

from . import config
from .db import append, get_row, insert_mutable
from .util import uuid7
from .errors import ValidationError
from .util import dumps, loads

KINDS = config.EFFECT_KINDS_V15

# `effects` is a ledger table, so append() fills every column and a NOT NULL one must be supplied on every write.
EFFECT_DEFAULTS = {"migrated": 0, "eliminated": 0}


def _append_effect(conn: sqlite3.Connection, row: dict) -> dict:
    return append(conn, "effects", {**EFFECT_DEFAULTS, **row})


# ---- §I: relations, transforms and node kinds -------------------------------------------------------------------

def node_upsert(conn: sqlite3.Connection, node: str, node_kind: str, attribute_kind: str | None = None,
                basis: str | None = None) -> dict:
    """§I1: a node is an event node or an attribute node. Listing venue, reporting currency, index membership, sector
    and size bucket are attribute nodes: positions on them are real and they never propose an effect."""
    if node_kind not in config.NODE_KINDS:
        raise ValidationError(f"node_kind must be one of {config.NODE_KINDS}")
    if node_kind == "attribute" and attribute_kind not in config.ATTRIBUTE_KINDS:
        raise ValidationError(f"an attribute node names which attribute: {config.ATTRIBUTE_KINDS}")
    key = f"node.{node.strip().lower()}"
    row = conn.execute("SELECT * FROM nodes WHERE key = ?", (key,)).fetchone()
    if row:
        conn.execute("UPDATE nodes SET node_kind = ?, attribute_kind = ?, basis = ? WHERE key = ?",
                     (node_kind, attribute_kind, basis or row["basis"], key))
        return {"node_id": row["id"], "node": node, "node_kind": node_kind, "created": False}
    r = insert_mutable(conn, "nodes", {"key": key, "node": node, "node_kind": node_kind,
                                       "attribute_kind": attribute_kind, "basis": basis})
    return {"node_id": r["id"], "node": node, "node_kind": node_kind, "created": True}


def node_kind_of(conn: sqlite3.Connection, node: str) -> str:
    """Unregistered nodes read as event nodes: the store's silence is not a claim that a node is an attribute."""
    r = conn.execute("SELECT node_kind FROM nodes WHERE key = ?", (f"node.{(node or '').strip().lower()}",)).fetchone()
    return r["node_kind"] if r else "event"


def relation_upsert(conn: sqlite3.Connection, from_holder_id: str | None, to_holder_id: str | None, relation_type: str,
                    basis: str, node: str | None = None, source: str | None = None,
                    knowable_from: str | None = None, mode: str | None = None) -> dict:
    """§I2: `transmits` is a property of the edge. True for physical, contractual and accounting relations: they may
    carry an effect and support a resolution. False for attribute edges: co-movement only.

    This weakens an existing claim on purpose. "Orthogonal is known, not assumed" was only ever true of factors
    modelled as transmission paths — precisely the ones the basket was built around. The correlations that hurt live
    in edges nobody drew, and splitting the edge types stops the graph treating its own silence as evidence."""
    mode = mode or config.RELATION_TYPES.get(relation_type)
    if mode is None:
        raise ValidationError(f"unknown relation_type {relation_type!r}; known: {sorted(config.RELATION_TYPES)}. "
                              "State the mode explicitly to add one, and say why in the basis.")
    if mode not in config.RELATION_MODES:
        raise ValidationError(f"mode must be one of {config.RELATION_MODES}")
    transmits = int(mode in config.TRANSMITTING_MODES)
    key = f"rel.{relation_type}.{from_holder_id or '-'}.{to_holder_id or '-'}.{(node or '-').lower()}"
    row = conn.execute("SELECT * FROM relations WHERE key = ?", (key,)).fetchone()
    if row:
        return {"relation_id": row["id"], "transmits": bool(row["transmits"]), "mode": row["mode"], "created": False}
    r = insert_mutable(conn, "relations", {
        "key": key, "from_holder_id": from_holder_id, "to_holder_id": to_holder_id, "node": node,
        "relation_type": relation_type, "mode": mode, "transmits": transmits,
        "hop_discount": config.HOP_DISCOUNT.get(relation_type, config.DEFAULT_HOP_DISCOUNT),
        "basis": basis, "source": source, "knowable_from": knowable_from})
    return {"relation_id": r["id"], "transmits": bool(transmits), "mode": mode, "created": True}


def seed_transforms(conn: sqlite3.Connection) -> dict:
    """§A4: seed the transform table from the pre-registered map. Absent entries are zero — a transform must be stated
    to exist — which is what makes this table smaller and more honest than a sign matrix."""
    n = 0
    for (rt, fk, tk), w in config.TRANSFORM_SEED.items():
        key = f"tf.{rt}.{fk}.{tk}"
        if conn.execute("SELECT 1 FROM transforms WHERE key = ?", (key,)).fetchone():
            continue
        insert_mutable(conn, "transforms", {"key": key, "relation_type": rt, "from_kind": fk, "to_kind": tk,
                                            "weight": w, "basis": "v15 §A4 pre-registered seed"})
        n += 1
    return {"seeded": n, "total": conn.execute("SELECT COUNT(*) FROM transforms").fetchone()[0]}


def transform_propose(conn: sqlite3.Connection, relation_type: str, from_kind: str, to_kind: str, weight: float,
                      reason: str, proposed_by: str = "operator") -> dict:
    """§A4: the operator may state a transform with a reason where the table has none, and that is **logged as a
    proposal**. It is not merged into the seed and it is visible as an operator move in every report that reads it."""
    for k in (from_kind, to_kind):
        if k not in KINDS:
            raise ValidationError(f"effect kind must be one of {KINDS}")
    key = f"tf.{relation_type}.{from_kind}.{to_kind}"
    if conn.execute("SELECT 1 FROM transforms WHERE key = ?", (key,)).fetchone():
        raise ValidationError(f"{key} already exists; a stated transform does not overwrite the seed")
    r = insert_mutable(conn, "transforms", {"key": key, "relation_type": relation_type, "from_kind": from_kind,
                                            "to_kind": to_kind, "weight": float(weight),
                                            "basis": reason, "proposed_by": proposed_by})
    return {"transform_id": r["id"], "key": key, "weight": weight, "proposed_by": proposed_by,
            "note": "logged as a proposal: a stated transform is an operator move, not a seeded fact"}


def transform_for(conn: sqlite3.Connection, relation_type: str, from_kind: str, to_kind: str) -> dict:
    """The mapping for one composition. Absent means zero: does not transmit."""
    r = conn.execute("SELECT * FROM transforms WHERE key = ?", (f"tf.{relation_type}.{from_kind}.{to_kind}",)).fetchone()
    if not r:
        return {"transform_id": None, "weight": 0.0, "basis": "no entry: does not transmit", "proposed_by": None}
    return {"transform_id": r["id"], "weight": r["weight"], "basis": r["basis"], "proposed_by": r["proposed_by"]}


# ---- §A1: the effect row ------------------------------------------------------------------------------------------

def _require(d: dict, *keys):
    missing = [k for k in keys if not d.get(k)]
    if missing:
        raise ValidationError(f"an effect is a claim and needs {missing}: without a carrier and a falsifier it is a "
                              "sentence, not a call")


def add_root(conn: sqlite3.Connection, round_id: str, node: str, effect_kind: str, carrier: str, falsifier: str,
             holder_id: str | None = None, magnitude: float | None = None, magnitude_basis: str | None = None,
             due_at: str | None = None, mechanism_ids: list[str] | None = None, ack_id: str | None = None,
             basis: str | None = None, origin: str = "event", carried_by: str | None = None,
             segment_id: str | None = None) -> dict:
    """A root effect: parent null, the event itself is the parent. Depth 1 by construction (the event is depth 0)."""
    if effect_kind not in KINDS:
        raise ValidationError(f"effect_kind must be one of {KINDS}")
    _require({"carrier": carrier, "falsifier": falsifier}, "carrier", "falsifier")
    get_row(conn, "rounds", round_id, "round")
    eid = uuid7()          # a root effect is its own root, and the ledger is append-only: no row is updated after
    row = _append_effect(conn, {
        "id": eid, "round_id": round_id, "parent_effect_id": None, "holder_id": holder_id, "node": node,
        "effect_kind": effect_kind, "magnitude": magnitude, "magnitude_basis": magnitude_basis,
        "carrier": carrier, "due_at": due_at, "falsifier": falsifier, "depth": 1, "root_effect_id": eid,
        "attenuated_support": 1.0, "root_depth": 0, "mechanism_ids": dumps(mechanism_ids or []),
        "ack_id": ack_id, "origin": origin, "basis": basis, "carried_by": carried_by, "segment_id": segment_id})
    return {"effect_id": row["id"], "depth": 1, "attenuated_support": 1.0, "root_depth": 0}


def compose(conn: sqlite3.Connection, round_id: str, parent_effect_id: str, relation_id: str, effect_kind: str,
            holder_id: str | None, node: str, carrier: str, falsifier: str, magnitude: float | None = None,
            magnitude_basis: str | None = None, due_at: str | None = None, ack_id: str | None = None,
            mechanism_ids: list[str] | None = None, basis: str | None = None, origin: str = "composition",
            carried_by: str | None = None, segment_id: str | None = None, write: bool = True) -> dict:
    """§A4 + §A6: compose a child effect through a relation.

    The transform is a property of the **relation type**, and a zero weight means the effect does not transmit that
    way at all — a supply shortfall maps to the buyer's cost effect strongly, its volume effect strongly, and its
    delivery obligation not at all. Attenuation is per effect hop and there is no depth limit (§A6): decay is the
    limit, and it is a limit the world imposes rather than one we pick."""
    if effect_kind not in KINDS:
        raise ValidationError(f"effect_kind must be one of {KINDS}")
    _require({"carrier": carrier, "falsifier": falsifier}, "carrier", "falsifier")
    parent = get_row(conn, "effects", parent_effect_id, "effect")
    rel = get_row(conn, "relations", relation_id, "relation")
    if not rel["transmits"]:
        # §I2/§6.4 in the data structure rather than in a reviewer's head.
        raise ValidationError(
            f"relation {rel['relation_type']!r} is mode {rel['mode']!r} and does not transmit: it may be summed in "
            "construction and may never carry an effect. A shared currency is not a transmission path.")
    tf = transform_for(conn, rel["relation_type"], parent["effect_kind"], effect_kind)
    if tf["weight"] <= 0.0:
        raise ValidationError(
            f"no transform for {rel['relation_type']}: {parent['effect_kind']} -> {effect_kind} ({tf['basis']}). "
            "Most entries in the table are 'does not transmit'. State one with a reason if you mean it "
            "(nomad_transform_propose) and it is logged as a proposal.")
    hop = rel["hop_discount"] if rel["hop_discount"] is not None else config.DEFAULT_HOP_DISCOUNT
    support = round((parent["attenuated_support"] or 1.0) * hop * tf["weight"], 6)
    depth = parent["depth"] + 1
    rec = {"round_id": round_id, "parent_effect_id": parent_effect_id, "holder_id": holder_id, "node": node,
           "effect_kind": effect_kind, "magnitude": magnitude, "magnitude_basis": magnitude_basis,
           "carrier": carrier, "due_at": due_at, "falsifier": falsifier, "relation_id": relation_id,
           "relation_type": rel["relation_type"], "transform_id": tf["transform_id"],
           "transform_weight": tf["weight"], "depth": depth, "attenuated_support": support,
           "root_effect_id": parent["root_effect_id"] or parent_effect_id,
           "root_depth": (parent["root_depth"] or 0), "mechanism_ids": dumps(mechanism_ids or []),
           "ack_id": ack_id, "origin": origin, "basis": basis, "carried_by": carried_by, "segment_id": segment_id}
    if not write:
        return {"effect_id": None, "depth": depth, "attenuated_support": support, "transform_weight": tf["weight"],
                "hop_discount": hop, "would_write": rec}
    check = frontier_check(conn, round_id, adding=1)
    if not check["within_bound"]:
        raise ValidationError(check["refusal"])
    row = _append_effect(conn, rec)
    return {"effect_id": row["id"], "depth": depth, "attenuated_support": support,
            "transform_weight": tf["weight"], "hop_discount": hop,
            "root_effect_id": rec["root_effect_id"], "root_depth": rec["root_depth"],
            "transform_proposed_by": tf["proposed_by"]}


def reroot(conn: sqlite3.Connection, effect_id: str, carried_by: str, basis: str,
           evidence_id: str | None = None) -> dict:
    """§A7: an effect resets attenuation **only** where that effect is carried by its own document — the buyer's own
    filing states the cost rise, not our inference that it must have risen. Then the chain is evidence rather than
    inference, and `root_effect_id` changes.

    Re-rooting on inference is inference laundering and is **refused, not discouraged**."""
    e = get_row(conn, "effects", effect_id, "effect")
    if not carried_by or not carried_by.strip():
        raise ValidationError("re-rooting needs the document that carries this effect independently; without one "
                              "this is inference laundering and is refused")
    if not basis or len(basis.strip()) < 12:
        raise ValidationError("say what the document states, in its own terms")
    eid = uuid7()          # a re-rooted effect becomes its own root
    row = _append_effect(conn, {
        "id": eid, "round_id": e["round_id"], "parent_effect_id": e["parent_effect_id"], "holder_id": e["holder_id"],
        "node": e["node"], "effect_kind": e["effect_kind"], "magnitude": e["magnitude"],
        "magnitude_basis": e["magnitude_basis"], "carrier": e["carrier"], "due_at": e["due_at"],
        "falsifier": e["falsifier"], "relation_id": e["relation_id"], "relation_type": e["relation_type"],
        "transform_id": e["transform_id"], "transform_weight": e["transform_weight"], "depth": e["depth"],
        "attenuated_support": 1.0, "root_effect_id": eid, "root_depth": (e["root_depth"] or 0) + 1,
        "mechanism_ids": e["mechanism_ids"], "ack_id": e["ack_id"], "segment_id": e["segment_id"],
        "origin": "reroot", "basis": basis, "carried_by": carried_by, "supersedes": effect_id})
    return {"effect_id": row["id"], "supersedes": effect_id, "attenuated_support": 1.0,
            "root_depth": (e["root_depth"] or 0) + 1, "carried_by": carried_by,
            "note": "attenuation reset because this effect is independently carried; root_depth is now on the ledger "
                    "and the round report shows how many effects reach the event through zero re-roots"}


def eliminate(conn: sqlite3.Connection, effect_id: str, basis: str) -> dict:
    """§A5: anchors run per effect. An effect dies where it has no path *for that effect kind*, where the receiving
    market has slack *for that effect*, where it is immaterial, or where it is already priced."""
    e = get_row(conn, "effects", effect_id, "effect")
    if not basis or len(basis.strip()) < 8:
        raise ValidationError("an elimination states which anchor fired and on what")
    row = _append_effect(conn, {k: e[k] for k in (
        "round_id", "parent_effect_id", "holder_id", "node", "effect_kind", "magnitude", "magnitude_basis",
        "carrier", "due_at", "falsifier", "relation_id", "relation_type", "transform_id", "transform_weight",
        "depth", "attenuated_support", "root_effect_id", "root_depth", "mechanism_ids", "ack_id", "segment_id",
        "origin", "carried_by", "migrated")} | {"eliminated": 1, "elimination_basis": basis,
                                                "basis": e["basis"], "supersedes": effect_id})
    return {"effect_id": row["id"], "supersedes": effect_id, "eliminated": True, "basis": basis}


# ---- reading the DAG ------------------------------------------------------------------------------------------

def _live(rows: list[dict]) -> list[dict]:
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r["id"] not in superseded]


def list_effects(conn: sqlite3.Connection, round_id: str, include_eliminated: bool = True) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM effects WHERE round_id = ? ORDER BY rowid", (round_id,))]
    out = _live(rows)
    for r in out:
        r["mechanism_ids"] = loads(r["mechanism_ids"]) if r["mechanism_ids"] else []
        r["eliminated"] = bool(r["eliminated"])
        r["migrated"] = bool(r["migrated"])
    return out if include_eliminated else [r for r in out if not r["eliminated"]]


def path_to_root(conn: sqlite3.Connection, effect_id: str, by_id: dict | None = None) -> list[dict]:
    """The chain of effects from this one back to its root, transmitting edges only (§F4). The chain is effects."""
    if by_id is None:
        e = get_row(conn, "effects", effect_id, "effect")
        by_id = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM effects WHERE round_id = ?", (e["round_id"],))}
    out, seen, cur = [], set(), effect_id
    while cur and cur in by_id and cur not in seen:
        seen.add(cur)
        out.append(by_id[cur])
        cur = by_id[cur]["parent_effect_id"]
    return list(reversed(out))


def frontier_check(conn: sqlite3.Connection, round_id: str, adding: int = 0) -> dict:
    """§A9: one event x four root effects x three children each is 40 nodes by depth three. Anchors run per effect and
    most die on generation; if elimination does not hold the width, the pre-registered bound is what stops it."""
    live = [e for e in list_effects(conn, round_id) if not e["eliminated"]]
    n = len(live) + adding
    within = n <= config.FRONTIER_BOUND
    return {"round_id": round_id, "live_effects": len(live), "would_be": n, "bound": config.FRONTIER_BOUND,
            "within_bound": within,
            "refusal": (None if within else
                        f"frontier bound {config.FRONTIER_BOUND} exceeded ({n} live effects would result). The "
                        "branches that would have opened are listed in `would_open`; eliminate before widening. The "
                        "bound is appetite: it is not raised because a round needed it."),
            "would_open": ([] if within else
                           [{"holder_id": e["holder_id"], "node": e["node"], "effect_kind": e["effect_kind"],
                             "depth": e["depth"]} for e in live[-10:]])}


def width(conn: sqlite3.Connection, round_id: str) -> dict:
    """§A9: `generation_width` and `elimination_rate` per depth."""
    all_ = list_effects(conn, round_id)
    depths = sorted({e["depth"] for e in all_})
    per = {}
    for d in depths:
        xs = [e for e in all_ if e["depth"] == d]
        elim = [e for e in xs if e["eliminated"]]
        per[d] = {"generated": len(xs), "eliminated": len(elim),
                  "elimination_rate": round(len(elim) / len(xs), 4) if xs else None,
                  "live": len(xs) - len(elim)}
    zero = [e for e in all_ if (e["root_depth"] or 0) == 0]
    return {"round_id": round_id, "generation_width": len(all_),
            "elimination_rate": round(sum(1 for e in all_ if e["eliminated"]) / len(all_), 4) if all_ else None,
            "by_depth": per, "max_depth": max(depths) if depths else 0,
            # §A7: if the interesting effects are all three re-roots deep, we have built a machine for justifying
            # distance, and the ledger must show it immediately.
            "root_depth": {"zero_rerooots": len(zero), "one_or_more": len(all_) - len(zero),
                           "distribution": {d: sum(1 for e in all_ if (e["root_depth"] or 0) == d)
                                            for d in sorted({(e["root_depth"] or 0) for e in all_})}},
            "frontier": frontier_check(conn, round_id)}


# ---- §A3: net direction is derived late ---------------------------------------------------------------------------

def net_direction(conn: sqlite3.Connection, round_id: str, holder_id: str, window_start: str,
                  window_end: str) -> dict:
    """§A3: there is no sign field. Net direction is derived **over a holding window**, from the magnitudes and dates
    already recorded. A holder whose effects net to zero over one window and to something over another is exactly
    what the leg model could not see.

    Effects opposed inside the window are returned as opposed (§A8): two effects pointing opposite ways and resolving
    at different ACKs is a signal, not an error, and §D handles it as an internal contradiction."""
    xs = [e for e in list_effects(conn, round_id, include_eliminated=False) if e["holder_id"] == holder_id]
    inside = [e for e in xs if e["due_at"] and window_start <= e["due_at"] <= window_end]
    outside = [e for e in xs if e not in inside]
    signed = [e for e in inside if e["magnitude"] is not None]
    net = round(sum(e["magnitude"] * (e["attenuated_support"] or 1.0) for e in signed), 4) if signed else None
    pos = [e for e in signed if e["magnitude"] > 0]
    neg = [e for e in signed if e["magnitude"] < 0]
    return {"round_id": round_id, "holder_id": holder_id, "window": [window_start, window_end],
            "effects_in_window": len(inside), "effects_outside_window": len(outside),
            "net": net, "opposed": bool(pos and neg),
            "components": [{"effect_id": e["id"], "kind": e["effect_kind"], "magnitude": e["magnitude"],
                            "support": e["attenuated_support"], "due_at": e["due_at"], "carrier": e["carrier"]}
                           for e in inside],
            "uncomputable": [e["id"] for e in inside if e["magnitude"] is None],
            "note": ("derived late and over this window only: a different window is a different answer, which is the "
                     "point of not writing a sign at generation time")}


# ---- §F: support, independence and the implicit position ----------------------------------------------------------

def _mrca_depth(a: list[dict], b: list[dict]) -> int:
    """Depth of the most recent common ancestor of two paths, walking transmitting edges only. Paths that split early
    and reconverge are two pieces of evidence; paths that split at the last node are one with a rounding error."""
    common = 0
    for x, y in zip(a, b):
        if x["id"] != y["id"]:
            break
        common += 1
    return common


def _independence(mrca: int, shorter: int) -> float:
    """§F4: 1.0 where the paths split at the root; falling toward the leaf value where they split at the last node."""
    if shorter <= 1:
        return config.INDEPENDENCE_DISCOUNT_AT_ROOT if mrca <= 1 else config.INDEPENDENCE_DISCOUNT_AT_LEAF
    frac = max(0.0, min(1.0, (mrca - 1) / (shorter - 1)))
    lo, hi = config.INDEPENDENCE_DISCOUNT_AT_LEAF, config.INDEPENDENCE_DISCOUNT_AT_ROOT
    return round(hi - frac * (hi - lo), 6)


def support(conn: sqlite3.Connection, round_id: str, holder_id: str | None = None,
            effect_kind: str | None = None) -> dict:
    """§F3/§F4: cross-membership is convergent implication. An effect reached by two paths for different reasons is
    independent derivation of one conclusion — and the walk is the generator that finally produces such paths.

    §F7: both rankings are written every round, with and without the independence discount. **If they agree, the
    discount is doing nothing and the paths were never independent.**"""
    live = list_effects(conn, round_id, include_eliminated=False)
    by_id = {e["id"]: e for e in live}
    groups: dict[tuple, list[dict]] = {}
    for e in live:
        if holder_id and e["holder_id"] != holder_id:
            continue
        if effect_kind and e["effect_kind"] != effect_kind:
            continue
        groups.setdefault((e["holder_id"], e["node"], e["effect_kind"]), []).append(e)
    rows = []
    for (hid, node, kind), es in groups.items():
        paths = [path_to_root(conn, e["id"], by_id) for e in es]
        raw = round(sum(e["attenuated_support"] or 0.0 for e in es), 6)
        disc = 0.0
        pairs = []
        for i, e in enumerate(es):
            d = 1.0
            for j in range(i):
                m = _mrca_depth(paths[i], paths[j])
                ind = _independence(m, min(len(paths[i]), len(paths[j])))
                d = min(d, ind)
                pairs.append({"a": es[i]["id"], "b": es[j]["id"], "mrca_depth": m, "independence": ind})
            disc += (e["attenuated_support"] or 0.0) * d
        h = conn.execute("SELECT canonical_name, listed FROM holders WHERE id = ?", (hid,)).fetchone() if hid else None
        rows.append({"holder_id": hid, "holder": (h["canonical_name"] if h else None), "node": node,
                     "effect_kind": kind, "n_paths": len(es), "effect_ids": [e["id"] for e in es],
                     "support_discounted": round(disc, 6), "support_undiscounted": raw,
                     "listed": bool(h["listed"]) if h else False, "pairs": pairs,
                     "max_magnitude": max([e["magnitude"] for e in es if e["magnitude"] is not None], default=None)})
    with_d = [r["holder_id"] for r in sorted(rows, key=lambda r: -r["support_discounted"])]
    without_d = [r["holder_id"] for r in sorted(rows, key=lambda r: -r["support_undiscounted"])]
    return {"round_id": round_id, "rows": sorted(rows, key=lambda r: -r["support_discounted"]),
            "ranking_discounted": with_d, "ranking_undiscounted": without_d,
            "rankings_agree": with_d == without_d,
            "note": ("§F7: the two rankings agree, so the independence discount is doing nothing here and the paths "
                     "were never independent -- read cross-membership as one derivation, not two"
                     if with_d == without_d and len(rows) > 1 else
                     "§F7: the rankings differ, so the discount is separating convergent derivations from restatements")}


def implicit_position(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """§F6: the implicit position needs support **and** stake.

    The most cross-supported effect may be robust because it is **inert**: if nothing touches a holder, every path
    trivially implies "nothing happens here" and it sits at maximum support with zero stake. That is the null record
    dressed as consensus, and it is returned as `inert` rather than as a position."""
    from .surviving import latest_for_round
    s = support(conn, round_id)
    stakes = {}
    for rec in latest_for_round(conn, round_id).values():
        v = loads(rec["vector"]) if rec.get("vector") else {}
        st = (v.get("terms") or {}).get("stake")
        if rec.get("holder_id"):
            stakes.setdefault(rec["holder_id"], st if st is not None else stakes.get(rec["holder_id"]))
    held, inert, thin = [], [], []
    for r in s["rows"]:
        st = stakes.get(r["holder_id"])
        row = dict(r, stake=st)
        if r["support_discounted"] < config.SUPPORT_THRESHOLD:
            thin.append(row)
        elif st is None or st <= config.INERT_STAKE_MAX:
            row["why_inert"] = ("nothing is at issue on this holder, so every path trivially implies nothing happens "
                                "here: maximum support, zero stake" if st is not None else
                                "stake is not computable on this holder, so support cannot be read as a position")
            inert.append(row)
        else:
            held.append(row)
    return {"round_id": round_id, "as_of": as_of, "position": held, "inert": inert, "below_support": thin,
            "support_threshold": config.SUPPORT_THRESHOLD, "inert_stake_max": config.INERT_STAKE_MAX,
            "rankings_agree": s["rankings_agree"],
            "note": "support says how conditional an effect is; stake says whether it is worth being unconditional "
                    "about. Both, always."}


# ---- §G: bridges fall out of the DAG ------------------------------------------------------------------------------

def bridge_paths(conn: sqlite3.Connection, round_id: str) -> dict:
    """§G1: **there is no bridge object.** An effect path is a position when some node in it clears expression and
    some ancestor of that node has stake. No new mechanism, no hop limit — the existing synthetics were instances of
    it, and round 13's pair at support 5.13 was bridging an unholdable structural claim to holdable instruments while
    we scored it as a leg and wondered why it did not arm.

    §G2: **this is not a loosening.** The path stays admissible at every hop, the expression endpoint stays real,
    anchors still run on every effect in the chain, attenuation still applies. What changes is only that stake and
    expression need not be properties of the same node. Written down explicitly, because the drift risk is "we allow
    weaker paths when we need a position", which is the thing the whole system exists to prevent."""
    from .surviving import latest_for_round
    live = list_effects(conn, round_id, include_eliminated=False)
    by_id = {e["id"]: e for e in live}
    recs = latest_for_round(conn, round_id)
    terms_by_holder: dict[str, dict] = {}
    for rec in recs.values():
        v = loads(rec["vector"]) if rec.get("vector") else {}
        t = v.get("terms") or {}
        if rec.get("holder_id"):
            cur = terms_by_holder.setdefault(rec["holder_id"], {"stake": None, "expression": None})
            for k in ("stake", "expression"):
                if t.get(k) is not None and (cur[k] is None or t[k] > cur[k]):
                    cur[k] = t[k]

    def clears(hid, term):
        t = (terms_by_holder.get(hid) or {}).get(term)
        return (t is not None and t >= config.APPETITE[term]), t

    out, near = [], []
    for e in live:
        ok_expr, expr = clears(e["holder_id"], "expression")
        if not ok_expr:
            continue
        chain = path_to_root(conn, e["id"], by_id)
        for anc in chain[:-1]:
            ok_stake, stake = clears(anc["holder_id"], "stake")
            row = {"round_id": round_id, "ancestor_effect_id": anc["id"], "ancestor_holder_id": anc["holder_id"],
                   "descendant_effect_id": e["id"], "descendant_holder_id": e["holder_id"],
                   "hops": e["depth"] - anc["depth"], "stake": stake, "expression": expr,
                   "total_attenuation": round((e["attenuated_support"] or 0.0) / (anc["attenuated_support"] or 1.0), 6),
                   "chain": [{"effect_id": c["id"], "holder_id": c["holder_id"], "kind": c["effect_kind"],
                              "relation_type": c["relation_type"], "support": c["attenuated_support"],
                              "root_depth": c["root_depth"]} for c in chain]}
            (out if ok_stake else near).append(row)
    return {"round_id": round_id, "bridge_paths": out, "n": len(out),
            "near_misses": near[:20], "n_near_misses": len(near),
            "empty_is_an_answer": not out,
            "note": ("no path in this round has a stake-clearing ancestor and an expression-clearing descendant. "
                     "Empty is a valid and reportable answer; if it stays empty across the next several rounds the "
                     "anti-correlation is a law and the answer is credit instruments or a forecasting product."
                     if not out else
                     f"{len(out)} path(s) bridge the two walls; admissibility held at every hop and attenuation is "
                     "reported per path")}


# ---- §A2: migration -----------------------------------------------------------------------------------------------

def migrate_legs(conn: sqlite3.Connection, round_id: str | None = None, write: bool = True) -> dict:
    """§A2: every existing `(holder, node)` leg becomes a single effect of kind `direction` at depth 1, so rounds 1–14
    remain readable and the wall map re-runs. `predictions.position_id` gains `effect_id`; the old column stays."""
    from .basket import round_legs
    rounds_ = ([round_id] if round_id else
               [r["id"] for r in conn.execute("SELECT r.id FROM rounds r JOIN round_state s ON s.round_id = r.id "
                                              "WHERE s.state != 'void' ORDER BY r.rowid")])
    made, skipped, per_round = 0, 0, {}
    for rid in rounds_:
        have = {(e["holder_id"], (e["node"] or "").lower()) for e in list_effects(conn, rid)}
        n = 0
        for leg in round_legs(conn, rid):
            key = (leg["holder_id"], (leg["node"] or "").lower())
            if key in have:
                skipped += 1
                continue
            if not write:
                n += 1
                made += 1
                continue
            eid = uuid7()
            row = _append_effect(conn, {
                "id": eid, "round_id": rid, "parent_effect_id": None, "holder_id": leg["holder_id"],
                "node": leg["node"], "root_effect_id": eid,
                "effect_kind": "direction", "depth": 1, "attenuated_support": 1.0, "root_depth": 0,
                "carrier": "migrated from the leg row; the leg's own carrier lives on its calls",
                "falsifier": "the leg's calls carry the falsifiers; this row exists so the DAG can read rounds 1-14",
                "mechanism_ids": dumps(leg.get("mechanism_ids") or []), "origin": "migration",
                "basis": f"v15 A2 migration of leg ({leg['holder']}, {leg['node']})", "migrated": 1})
            have.add(key)
            n += 1
            made += 1
        per_round[rid] = n
    return {"rounds": len(rounds_), "effects_created": made, "already_present": skipped, "per_round": per_round,
            "write": write,
            "note": ("every migrated leg is a depth-1 `direction` effect with no sign. `predictions` and "
                     "`surviving_risk` are append-only, so historic rows are NOT rewritten to carry effect_id: the "
                     "old position_id stays and the link is derived (effect_for_position). New calls carry effect_id "
                     "directly.")}


def effect_for_position(conn: sqlite3.Connection, round_id: str, position_id: str) -> str | None:
    """§A2: the link from a historic (holder, node) leg to its migrated effect, derived rather than written back.
    The ledger is append-only, so history is read through this rather than rewritten under it."""
    p = conn.execute("SELECT holder_id, node FROM positions WHERE id = ?", (position_id,)).fetchone()
    if not p:
        return None
    for e in list_effects(conn, round_id):
        if e["holder_id"] == p["holder_id"] and (e["node"] or "").lower() == (p["node"] or "").lower():
            return e["id"]
    return None
