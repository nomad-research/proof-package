"""§E: synthetic legs. A projection of existing position legs under a pre-registered construction rule; signs only,
no sizing, never hand-built. Support = min(component support) x COMPONENT_DISCOUNT^(n-1)."""
import sqlite3

from . import config
from .db import append, get_row, insert_mutable
from .errors import NotFound, ValidationError
from .util import dumps, loads

RULES: tuple[dict, ...] = (
    {"key": "syn.tradability_opposing", "shape": "tradability",
     "text": "all listed holders at degree <= 2 with opposing sign on the target node, equal weight"},
    {"key": "syn.time_toll_cargo", "shape": "time",
     "text": "the toll-booth leg and the cargo leg of the same chain (from the toll booth learns first)"},
    {"key": "syn.cross_node_event_pair", "shape": "tradability",
     "text": "on an event with >= 2 nodes in its footprint, listed holders with sign + on one node against listed holders with sign - on another; equal weight; shared factor = the event"},
)
SHAPES = ("tradability", "time", "tide", "convexity")


def seed_synthetic_rules(conn: sqlite3.Connection) -> int:
    n = 0
    for r in RULES:
        if conn.execute("SELECT 1 FROM synthetic_rules WHERE key = ?", (r["key"],)).fetchone():
            continue
        insert_mutable(conn, "synthetic_rules", r)
        n += 1
    return n


def list_rules(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM synthetic_rules ORDER BY rowid")]


def resolve_rule(conn: sqlite3.Connection, id_or_key: str) -> dict:
    r = conn.execute("SELECT * FROM synthetic_rules WHERE id = ? OR key = ?", (id_or_key, id_or_key)).fetchone()
    if not r:
        raise NotFound(f"no synthetic rule {id_or_key!r}; see nomad_synthetic_rules")
    return dict(r)


def _sign_position(conn: sqlite3.Connection, position_ids: list[str]) -> str | None:
    for pid in position_ids:
        r = conn.execute("SELECT id FROM positions WHERE id = ? AND attribute = 'sign_of_exposure'", (pid,)).fetchone()
        if r:
            return r["id"]
    return position_ids[0] if position_ids else None


def _components_tradability(conn, legs: list[dict], target_node: str) -> tuple[list[dict], str | None]:
    pool = [l for l in legs if l["listed"] and l["node"].lower() == target_node.lower()
            and (l.get("degree") is None or l["degree"] <= 2) and l["sign"] in ("+", "-")]
    plus = [l for l in pool if l["sign"] == "+"]
    minus = [l for l in pool if l["sign"] == "-"]
    if not plus or not minus:
        return [], (f"no opposing listed pair within degree 2 on {target_node!r}: "
                    f"{len(plus)} listed sign + and {len(minus)} listed sign - among {len(pool)} eligible legs")
    comps = [{"position_id": _sign_position(conn, l["position_ids"]), "holder_id": l["holder_id"], "holder": l["holder"],
              "sign": +1 if l["sign"] == "+" else -1, "support_weight": l["support_weight"]} for l in plus + minus]
    return comps, None


def _components_cross_node(conn, legs: list[dict], target_node: str) -> tuple[list[dict], str | None]:
    """v10 D1: listed sign + on one node against listed sign - on another node of the same event; the target node is
    the + side. Refused when the footprint has one node or every node is one-sided."""
    eligible = [l for l in legs if l["listed"] and (l.get("degree") is None or l["degree"] <= 2) and l["sign"] in ("+", "-")]
    nodes = sorted({l["node"].lower() for l in legs})
    if len(nodes) < 2:
        return [], f"cross-node pair needs >= 2 nodes in the footprint; this event has {len(nodes)}"
    plus = [l for l in eligible if l["sign"] == "+" and l["node"].lower() == target_node.lower()]
    minus = [l for l in eligible if l["sign"] == "-" and l["node"].lower() != target_node.lower()]
    if not plus or not minus:
        return [], (f"no listed cross-node pair: {len(plus)} listed sign + on {target_node!r} and {len(minus)} listed sign - on the other node(s) "
                    f"{[n for n in nodes if n != target_node.lower()]}; every node one-sided")
    comps = [{"position_id": _sign_position(conn, l["position_ids"]), "holder_id": l["holder_id"], "holder": l["holder"], "node": l["node"],
              "sign": +1 if l["sign"] == "+" else -1, "support_weight": l["support_weight"]} for l in plus + minus]
    return comps, None


def _components_time(conn, legs: list[dict], target_node: str) -> tuple[list[dict], str | None]:
    """Toll-booth and cargo legs are tagged on positions: attribute tier with value toll_booth or cargo."""
    tagged: dict[str, list] = {"toll_booth": [], "cargo": []}
    for l in legs:
        if l["node"].lower() != target_node.lower():
            continue
        for pid in l["position_ids"]:
            r = conn.execute("SELECT value FROM positions WHERE id = ? AND attribute = 'tier'", (pid,)).fetchone()
            if r and r["value"] in tagged:
                tagged[r["value"]].append(l)
    if not tagged["toll_booth"] or not tagged["cargo"]:
        return [], (f"no toll-booth/cargo pair tagged on {target_node!r} (positions.tier = toll_booth | cargo): "
                    f"{len(tagged['toll_booth'])} toll-booth, {len(tagged['cargo'])} cargo")
    comps = []
    for role, sgn in (("toll_booth", +1), ("cargo", -1)):
        for l in tagged[role]:
            comps.append({"position_id": _sign_position(conn, l["position_ids"]), "holder_id": l["holder_id"], "holder": l["holder"],
                          "sign": sgn, "role": role, "support_weight": l["support_weight"]})
    return comps, None


def synthetic_build(conn: sqlite3.Connection, round_id: str, target_node: str, rule_id: str, dry_run: bool = False,
                    space: str = "positive") -> dict:
    from .basket import event_basket
    from .errors import StateError
    from .rounds import round_state
    rule = resolve_rule(conn, rule_id)
    get_row(conn, "rounds", round_id, "round")
    if space not in ("positive", "mirror"):
        raise ValidationError("space must be positive or mirror")
    # v9 C1: synthetics are part of the locked set; a build after lock is a post-hoc construction (dry_run reads only)
    state = round_state(conn, round_id)
    if state != "created" and not dry_run:
        raise StateError(f"cannot build a synthetic on round {round_id} in state '{state}': synthetics are built before "
                         "nomad_lock_predictions (a post-lock build is a post-hoc construction). Cite each component's "
                         "mechanism on its touched_set row and build first")
    if not target_node.strip():
        raise ValidationError("target_node is required")
    legs = event_basket(conn, round_id, include_synthetics=False)["legs"]
    cross = rule["key"] == "syn.cross_node_event_pair"
    builder = _components_cross_node if cross else {"tradability": _components_tradability, "time": _components_time}.get(rule["shape"])
    if builder is None:
        raise ValidationError(f"no mechanical builder for shape {rule['shape']!r} yet")
    comps, reason = builder(conn, legs, target_node)
    if reason:
        return {"built": False, "round_id": round_id, "target_node": target_node, "rule": rule["key"], "reason": reason}
    # v9 C1: every component position has a cited mechanism (touched_set.mechanism_ids) before the build
    by_holder = {l["holder_id"]: l for l in legs}
    uncited = [c["holder"] for c in comps if not by_holder.get(c["holder_id"], {}).get("mechanism_ids")]
    if uncited:
        return {"built": False, "round_id": round_id, "target_node": target_node, "rule": rule["key"],
                "reason": f"components without a cited mechanism: {uncited}; put mechanism_ids on their touched_set rows (C1)"}
    weights = [c["support_weight"] for c in comps if c["support_weight"] is not None]
    n = len(comps)
    discount = (config.COMPONENT_DISCOUNT ** (n - 1)) * (config.CROSS_NODE_DISCOUNT if cross else 1.0)
    support = round(min(weights) * discount, 6) if weights else None
    listed = sum(1 for c in comps if conn.execute("SELECT listed FROM holders WHERE id = ?", (c["holder_id"],)).fetchone()["listed"])
    out = {"built": not dry_run, "dry_run": dry_run, "round_id": round_id, "target_node": target_node, "rule": rule["key"],
           "shape": rule["shape"], "components": comps, "n_components": n, "support_weight": support, "cross_node": cross, "space": space,
           "weakest_component": min(weights) if weights else None, "component_discount": config.COMPONENT_DISCOUNT,
           "cross_node_discount": config.CROSS_NODE_DISCOUNT if cross else None, "listed_components": listed}
    if dry_run:
        return out
    row = append(conn, "synthetic_legs", {
        "round_id": round_id, "target_node": target_node, "components": dumps([{k: c.get(k) for k in ("position_id", "holder_id", "sign", "node")} for c in comps]),
        "construction_rule_id": rule["id"], "support_weight": support, "shape": rule["shape"], "listed_components": listed,
        "note": f"built mechanically under {rule['key']}; discount {config.COMPONENT_DISCOUNT}^{n - 1}" + (f" x {config.CROSS_NODE_DISCOUNT} cross-node" if cross else ""),
        "cross_node": int(cross), "space": space,
    })
    out["synthetic_id"] = row["id"]
    return out


def list_synthetics(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    out = []
    for r in conn.execute("SELECT s.*, sr.key AS rule_key FROM synthetic_legs s JOIN synthetic_rules sr ON sr.id = s.construction_rule_id "
                          "WHERE s.round_id = ? ORDER BY s.rowid", (round_id,)):
        d = dict(r)
        d["components"] = loads(d["components"])
        out.append(d)
    return out


def get_synthetic(conn: sqlite3.Connection, synthetic_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM synthetic_legs WHERE id = ?", (synthetic_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["components"] = loads(d["components"])
    return d


def gate_reading(conn: sqlite3.Connection, synthetic: dict) -> dict:
    """E3: the tradability gate's single form reads the synthetic's listed components."""
    listed = []
    for c in synthetic["components"]:
        h = conn.execute("SELECT canonical_name, listed, ticker FROM holders WHERE id = ?", (c["holder_id"],)).fetchone()
        if h and h["listed"]:
            listed.append({"holder": h["canonical_name"], "ticker": h["ticker"], "sign": c["sign"]})
    signs = {c["sign"] for c in listed}
    return {"listed_components": listed, "prima_facie": "holds" if len(listed) >= 2 and signs == {1, -1} else "fails",
            "note": "prima facie only; the operator still checks the gate with a basis"}
