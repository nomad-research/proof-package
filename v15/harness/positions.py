"""Positions store (§4.12): the nouns the library's verbs act on. Baskets are a projection, not a store."""
import sqlite3
from collections import defaultdict

from .db import append, get_row
from .errors import ValidationError
from .names import resolve_holder

ATTRIBUTES = ("tier", "priority", "substitutability", "share", "duration", "sign_of_exposure")
CONFIDENCE = ("stated", "inferred", "implicit")


def position_add(conn: sqlite3.Connection, holder_id: str, node: str, attribute: str, value, source: str,
                 confidence: str, unit: str | None = None, source_time: str | None = None,
                 knowable_from: str | None = None, supersedes: str | None = None) -> dict:
    holder_id = resolve_holder(conn, holder_id)["id"]
    if attribute not in ATTRIBUTES:
        raise ValidationError(f"attribute must be one of {ATTRIBUTES}")
    if confidence not in CONFIDENCE:
        raise ValidationError(f"confidence must be one of {CONFIDENCE} (the epistemic class of the fact)")
    if not node.strip() or not source.strip():
        raise ValidationError("node and source are required")
    value = str(value).strip()
    if attribute == "sign_of_exposure" and value not in ("+", "-", "0"):
        raise ValidationError("sign_of_exposure value must be '+' (scarcity on the node helps), '-' (hurts) or '0'")
    if supersedes:
        old = get_row(conn, "positions", supersedes, "position")
        if (old["holder_id"], old["node"], old["attribute"]) != (holder_id, node, attribute):
            raise ValidationError("supersedes must point at a position of the same holder, node and attribute")
    row = append(conn, "positions", {
        "holder_id": holder_id, "node": node.strip(), "attribute": attribute, "value": value, "unit": unit,
        "source": source, "source_time": source_time, "knowable_from": knowable_from, "confidence": confidence,
        "supersedes": supersedes,
    })
    return {"position_id": row["id"], "holder_id": holder_id, "node": row["node"], "attribute": attribute, "value": value}


def positions_on_node(conn: sqlite3.Connection, node: str, listed_only: bool = False) -> dict:
    """Current positions on a node (rows not superseded), grouped by holder; flags opposing-sign listed pairs
    (the pair gate's raw material) and self-hedged holders (both signs on the same node)."""
    rows = [dict(r) for r in conn.execute(
        "SELECT p.*, h.canonical_name, h.kind AS holder_kind, h.listed, h.parent_id, h.ticker, h.key AS holder_key FROM positions p "
        "JOIN holders h ON h.id = p.holder_id WHERE lower(p.node) = lower(?) ORDER BY p.rowid", (node.strip(),))]
    superseded = {r["supersedes"] for r in rows if r["supersedes"]}
    current = [r for r in rows if r["id"] not in superseded]
    if listed_only:
        current = [r for r in current if r["listed"]]
    by_holder: dict[str, dict] = {}
    for r in current:
        h = by_holder.setdefault(r["holder_id"], {
            "holder_id": r["holder_id"], "key": r["holder_key"], "canonical_name": r["canonical_name"],
            "kind": r["holder_kind"], "listed": bool(r["listed"]), "ticker": r["ticker"], "parent_id": r["parent_id"],
            "signs": set(), "attributes": defaultdict(list), "positions": []})
        h["positions"].append({k: r[k] for k in ("id", "attribute", "value", "unit", "source", "source_time",
                                                   "knowable_from", "confidence", "recorded_at")})
        if r["attribute"] == "sign_of_exposure":
            h["signs"].add(r["value"])
        else:
            h["attributes"][r["attribute"]].append(r["value"])
    holders = []
    for h in by_holder.values():
        holders.append(dict(h, signs=sorted(h["signs"]), attributes=dict(h["attributes"])))
    self_hedged = [h for h in holders if {"+", "-"} <= set(h["signs"])]
    single = [h for h in holders if h["listed"] and len(set(h["signs"]) & {"+", "-"}) == 1]
    plus = [h for h in single if "+" in h["signs"]]
    minus = [h for h in single if "-" in h["signs"]]
    pairs = []
    for a in plus:
        for b in minus:
            diff = {}
            for attr in ATTRIBUTES[:-1]:
                av, bv = a["attributes"].get(attr), b["attributes"].get(attr)
                if av or bv:
                    diff[attr] = {"plus": av, "minus": bv}
            pairs.append({"plus": {"holder_id": a["holder_id"], "name": a["canonical_name"], "ticker": a["ticker"]},
                          "minus": {"holder_id": b["holder_id"], "name": b["canonical_name"], "ticker": b["ticker"]},
                          "position_difference": diff,
                          "threshold_note": "day one: any difference counts; threshold to be measured"})
    return {
        "node": node.strip(), "n_current_positions": len(current), "holders": holders,
        "pairs": pairs, "pair_gate": bool(pairs),
        "self_hedged": [{"holder_id": h["holder_id"], "key": h["key"], "name": h["canonical_name"], "signs": h["signs"]}
                        for h in self_hedged],
    }
