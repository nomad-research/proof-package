"""Three-valued evaluation of template conditions and outcome needs (§22.2, §22.3).

Pure: reads a ``View`` and a clock, never prices. A condition is ``true`` only when a
documented row (``confidence = stated``, ``knowable_from <= clock``) says so; ``false``
only when such a row documents its negation; ``unknown`` otherwise. Unknown is a value,
not a verdict.

Grammar (JSON):
  {"role": R, "attribute": A, "op": OP, "value": V}
  {"bound": {"subject": S} | {"subject_from": {"role": R, "attribute": A}}, "quantity": Q,
   "op": OP, "value": V}
  {"fact": KIND, "effect_kind": K?}      true if a stated node fact of that kind exists
  V may be {"ref": "window_days"} (the ACK's window length in days).
"""
from __future__ import annotations

from .util import le, ts

OPS = {"<", "<=", ">", ">=", "==", "!=", "in", "not_in"}


def visible_positions(view, clock: str, holder_id: str | None = None,
                      nodes: list[str] | None = None, attribute: str | None = None) -> list[dict]:
    """Rows knowable by the clock, superseded rows removed (among the visible ones)."""
    rows = view.led("positions")
    # v17: a null-node statement is about the subject's own state (a reactor's unit_status, a licence's state);
    # it is included when the read names the subject. v16 rows always carry a node, so nothing changes for them.
    vis = [r for r in rows if le(r["knowable_from"], clock)
           and (holder_id is None or r["holder_id"] == holder_id)
           and (nodes is None or r["node"] in nodes or (r["node"] is None and holder_id is not None))
           and (attribute is None or r["attribute"] == attribute)]
    superseded = {r["supersedes"] for r in vis if r.get("supersedes")}
    return [r for r in vis if r["position_id"] not in superseded]


def position_value(view, clock, holder_id, nodes, attribute):
    """Latest visible row for (holder, attribute) on the first scope node that has one."""
    for n in nodes:
        rows = visible_positions(view, clock, holder_id, [n], attribute)
        if rows:
            return rows[-1]
    return None


def _cmp(a, op, b) -> bool:
    if op in {"in", "not_in"}:
        vals = [str(x) for x in (b if isinstance(b, list) else [b])]
        return (str(a) in vals) == (op == "in")
    try:
        fa, fb = float(a), float(b)
        a, b = fa, fb
    except (TypeError, ValueError):
        a, b = str(a).lower(), str(b).lower()
        if op not in {"==", "!="}:
            return False
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b,
            "==": a == b, "!=": a != b}[op]


def resolve_value(v, ctx: dict):
    if isinstance(v, dict) and "ref" in v:
        ref = v["ref"]
        if ref not in ctx or ctx[ref] is None:
            return None
        return ctx[ref]
    return v


def bound_row(view, clock, subject, quantity):
    best = None
    for b in view.mut("bounds"):
        if b["subject"] == subject and b["quantity"] == quantity and le(b["knowable_from"], clock):
            if best is None or ts(b["knowable_from"]) >= ts(best["knowable_from"]):
                best = b
    return best


def evaluate(view, clock: str, cond: dict, bindings: dict, nodes: list[str], ctx: dict | None = None) -> dict:
    """Return {'state': true|false|unknown, 'evidence': [...], 'why': str}."""
    ctx = ctx or {}
    op = cond.get("op")
    if "fact" in cond:
        facts = [f for f in view.led("node_facts")
                 if f["kind"] == cond["fact"] and f["node"] in nodes and le(f["knowable_from"], clock)
                 and (cond.get("effect_kind") is None or f["effect_kind"] in (None, cond["effect_kind"]))]
        if facts:
            return {"state": "true", "evidence": [f["fact_id"] for f in facts], "why": f"stated {cond['fact']} fact"}
        return {"state": "unknown", "evidence": [], "why": f"no stated {cond['fact']} fact"}
    if op not in OPS:
        return {"state": "unknown", "evidence": [], "why": f"malformed condition op {op!r}"}
    target = resolve_value(cond.get("value"), ctx)
    if target is None:
        return {"state": "unknown", "evidence": [], "why": "reference value unknown"}
    if "bound" in cond:
        spec = cond["bound"]
        subject = spec.get("subject")
        ev = []
        if subject is None and "subject_from" in spec:
            sf = spec["subject_from"]
            hid = bindings.get(sf["role"])
            row = position_value(view, clock, hid, nodes, sf["attribute"]) if hid else None
            if row is None or row["confidence"] != "stated":
                return {"state": "unknown", "evidence": [], "why": "bound subject not documented"}
            subject = row["value"]
            ev.append(row["position_id"])
        b = bound_row(view, clock, subject, spec["quantity"])
        if b is None:
            return {"state": "unknown", "evidence": ev, "why": f"no bound {spec['quantity']} for {subject}"}
        ok = _cmp(b["value"], op, target)
        return {"state": "true" if ok else "false", "evidence": ev + [b["key"]],
                "why": f"bound {b['key']}={b['value']} {op} {target}"}
    role = cond.get("role")
    hid = bindings.get(role)
    if hid is None:
        return {"state": "unknown", "evidence": [], "why": f"role {role} unbound"}
    row = position_value(view, clock, hid, nodes, cond["attribute"])
    if row is None:
        return {"state": "unknown", "evidence": [], "why": f"no position {cond['attribute']} for {hid}"}
    if row["confidence"] != "stated":
        return {"state": "unknown", "evidence": [row["position_id"]],
                "why": f"position {row['position_id']} is {row['confidence']}, not documented"}
    val = row["value_num"] if row["value_num"] is not None else row["value"]
    ok = _cmp(val, op, target)
    return {"state": "true" if ok else "false", "evidence": [row["position_id"]],
            "why": f"{hid}.{cond['attribute']}={val} {op} {target}"}


def combine(states: list[str]) -> str:
    if any(s == "false" for s in states):
        return "false"
    if any(s == "unknown" for s in states):
        return "unknown"
    return "true"
