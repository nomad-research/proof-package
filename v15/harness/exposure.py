"""v15 §H/§I: basket totality, synthetic exposure, and the factor graph.

**A basket carries exposures nobody wrote down.** Components are chosen for their loading on the target and arrive
carrying every other loading. Round 13's pair was constructed for the exclusion-order factor and was also long a
display-glass complex, long US-listed against China-listed, and long a currency pair. This is structural rather than
incidental, and it *sharpens* as construction improves: cancelling the common mode precisely isolates the unintended
residual precisely.

**Basket scoring is three things, and the third makes the first two separable:** did the intended cancellation happen;
did the residual move as claimed; **what did the synthetic exposure do**. Without the third, a basket that "worked"
may have been carried by an unintended exposure and one that "failed" may have had a correct read swamped by one —
the round-2 pattern relocated inside our own construction.

**Declare it at construction.** Naming it at lock makes it a claim we can be wrong about rather than a surprise in the
P&L. **If it cannot be named, the construction is not understood well enough to hold.**

**It is a floor and is typed as one.** The graph sees only modelled loadings, so as attribute coverage grows the floor
rises toward the truth and the gap is honest ignorance rather than hidden risk."""
import sqlite3

from . import config
from .db import append, get_row
from .errors import ValidationError
from .util import dumps, loads


def attribute_coverage(conn: sqlite3.Connection, holder_ids: list[str]) -> dict:
    """§I4: coverage grows by play, with an orphan queue. Reported next to every declared synthetic exposure, because
    until the data layer exists every basket-level number carries the floor caveat."""
    from .effects import node_kind_of
    if not holder_ids:
        return {"holders": 0, "coverage": None, "by_kind": {}, "missing": []}
    seen: dict[str, set] = {}
    for hid in holder_ids:
        for r in conn.execute("SELECT DISTINCT node FROM positions WHERE holder_id = ?", (hid,)):
            if node_kind_of(conn, r["node"]) == "attribute":
                a = conn.execute("SELECT attribute_kind FROM nodes WHERE key = ?",
                                 (f"node.{r['node'].strip().lower()}",)).fetchone()
                if a and a["attribute_kind"]:
                    seen.setdefault(hid, set()).add(a["attribute_kind"])
    kinds = config.ATTRIBUTE_KINDS
    per = {k: sum(1 for hid in holder_ids if k in seen.get(hid, set())) for k in kinds}
    total = len(holder_ids) * len(kinds)
    have = sum(per.values())
    return {"holders": len(holder_ids), "coverage": round(have / total, 4) if total else None,
            "by_kind": per, "attribute_kinds": list(kinds),
            "missing": [{"holder_id": hid, "missing": sorted(set(kinds) - seen.get(hid, set()))}
                        for hid in holder_ids if set(kinds) - seen.get(hid, set())],
            "note": "the graph sees only modelled loadings: this is a floor on what the basket carries, and the gap "
                    "is honest ignorance rather than hidden risk"}


def declare(conn: sqlite3.Connection, round_id: str, declared: list[dict], intended_residual: float,
            basis: str, holder_ids: list[str] | None = None, basket_key: str | None = None) -> dict:
    """§H3/§H5. Every declared row is `{attribute_node, net_sign, magnitude}`.

    `basket_stake = intended residual ÷ declared synthetic exposure`. **Below 1.0 the basket is a position on
    something we did not choose** — a wall, whatever the effect-level reasoning was."""
    from .effects import node_kind_of
    get_row(conn, "rounds", round_id, "round")
    if not declared:
        raise ValidationError("declare the synthetic exposure at construction: if it cannot be named, the "
                              "construction is not understood well enough to hold")
    if not basis or len(basis.strip()) < 12:
        raise ValidationError("say how the exposure was derived; a declaration with no basis is a guess with a schema")
    total = 0.0
    for i, d in enumerate(declared):
        missing = {"attribute_node", "net_sign", "magnitude"} - set(d)
        if missing:
            raise ValidationError(f"declared[{i}] needs {sorted(missing)}")
        if d["net_sign"] not in ("+", "-", "0"):
            raise ValidationError(f"declared[{i}].net_sign is +, - or 0")
        if node_kind_of(conn, d["attribute_node"]) != "attribute":
            raise ValidationError(
                f"declared[{i}].attribute_node {d['attribute_node']!r} is not registered as an attribute node. "
                "Register it (nomad_node_kind) so the graph knows it is a shared loading and never a transmission "
                "path -- an attribute node never proposes an effect and is always summed in construction.")
        total += abs(float(d["magnitude"]))
    cov = attribute_coverage(conn, holder_ids or [])
    stake = round(float(intended_residual) / total, 4) if total else None
    row = append(conn, "synthetic_exposures", {
        "round_id": round_id, "basket_key": basket_key, "declared": dumps(declared),
        "coverage": cov["coverage"], "attribute_coverage": cov["coverage"], "floor": 1,
        "intended_residual": float(intended_residual), "declared_exposure": round(total, 6),
        "basket_stake": stake, "basis": basis})
    below = stake is not None and stake < config.BASKET_STAKE_FLOOR
    return {"synthetic_exposure_id": row["id"], "round_id": round_id, "declared": declared,
            "declared_exposure": round(total, 6), "intended_residual": float(intended_residual),
            "basket_stake": stake, "floor": True, "basket_stake_floor": config.BASKET_STAKE_FLOOR,
            "attribute_coverage": cov["coverage"], "coverage_detail": cov,
            "below_floor": below,
            "wall": ("basket_stake below 1.0: this basket is a position on something nobody chose. That is a wall, "
                     "whatever the effect-level reasoning was." if below else None),
            "note": "typed as a floor: as attribute coverage grows the floor rises toward the truth"}


def for_round(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM synthetic_exposures WHERE round_id = ? ORDER BY rowid", (round_id,)):
        d = dict(r)
        d["declared"] = loads(d["declared"]) if d["declared"] else []
        d["floor"] = bool(d["floor"])
        d["below_floor"] = d["basket_stake"] is not None and d["basket_stake"] < config.BASKET_STAKE_FLOOR
        out.append(d)
    return out


def traverse_or_sum(conn: sqlite3.Connection, relation_id: str) -> dict:
    """§I2: **traverse only transmitting edges; sum over all of them.** One function so the distinction cannot be
    forgotten at a call site."""
    rel = get_row(conn, "relations", relation_id, "relation")
    return {"relation_id": relation_id, "relation_type": rel["relation_type"], "mode": rel["mode"],
            "transmits": bool(rel["transmits"]),
            "may_traverse": bool(rel["transmits"]),
            "summed_in_construction": True,
            "note": ("physical, contractual or accounting: may carry an effect and support a resolution"
                     if rel["transmits"] else
                     "attribute or attentional: co-movement only. It is summed in construction and never traversed "
                     "-- a shared currency is not a transmission path.")}
