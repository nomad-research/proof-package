"""Derived ACKs: obligation templates × positions → forced ACKs, switches, fetch lists (§22.2).

Reads positions, bounds, node facts, the library and ratified procedural states as of
the segment clock. **Never reads prices** (the import linter enforces it: §13, smoke 28).
"""
from __future__ import annotations

import datetime as _dt
import itertools

from . import config
from .conditions import combine, evaluate, visible_positions
from .db import DB, Refused, canon, sha
from .util import day, ts


def scope_nodes(view, node: str) -> list[str]:
    n = view.mget("nodes", node)
    return [node] + list((n or {}).get("neighbours") or [])


def _window(view, clock: str, event_date: str, rule: dict | None) -> tuple[str, str, int | None, bool]:
    """(window_to, basis, window_days, ratified). Capped at DUE_AT_MAX_DAYS after event_date."""
    cap_days = int(config.get("DUE_AT_MAX_DAYS"))
    cap = (ts(event_date) + _dt.timedelta(days=cap_days)).strftime("%Y-%m-%d")
    rule = rule or {"kind": "none"}
    if rule.get("kind") == "statute":
        from .conditions import bound_row
        b = bound_row(view, clock, rule["subject"], rule["quantity"])
        if b is not None:
            to = (ts(clock) + _dt.timedelta(days=float(b["value"]))).strftime("%Y-%m-%d")
            if to > cap:
                return cap, "cap", (ts(cap) - ts(clock)).days, True
            return to, "statute", int(float(b["value"])), True
    return cap, "cap", (ts(cap) - ts(clock)).days, True


def role_candidates(view, clock, nodes, role: dict) -> list[str]:
    rows = visible_positions(view, clock, nodes=nodes)
    holders = sorted({r["holder_id"] for r in rows})
    out = []
    for h in holders:
        hr = view.mget("holders", h) or {}
        if role.get("holder_classes") and hr.get("holder_class") not in role["holder_classes"]:
            continue
        if role.get("entity_kinds") and hr.get("entity_kind") not in role["entity_kinds"]:
            continue
        if role.get("requires_attribute"):
            if not [r for r in rows if r["holder_id"] == h and r["attribute"] == role["requires_attribute"]]:
                continue
        out.append(h)
    return out


def compute(view, round_row: dict, clock: str) -> list[dict]:
    """Pure: every template instance and its result, for one segment clock."""
    node = round_row["node"]
    nodes = scope_nodes(view, node)
    node_type = (view.mget("nodes", node) or {}).get("node_type") or round_row.get("node_type")
    max_b = int(config.get("DERIVATION_BINDINGS_MAX"))
    out = []
    for t in view.mut("obligation_templates"):
        if node_type not in (t.get("node_types") or []):
            continue
        rule = view.mget("library_rules", t["key"])
        if rule is None or rule.get("status") == "retired":
            continue
        roles = t.get("roles") or []
        cands = [role_candidates(view, clock, nodes, r) for r in roles]
        n_bind = 1
        for c in cands:
            n_bind *= max(len(c), 0)
        if n_bind > max_b:
            out.append({"template_id": t["key"], "bindings": {}, "result": "bindings_exceeded",
                        "conditions": [], "fetch_list": [], "n_bindings": n_bind})
            continue
        window_to, basis, wdays, _ = _window(view, clock, round_row["event_date"], t.get("window_rule"))
        ctx = {"window_days": wdays}
        for combo in itertools.product(*cands):
            if len(set(combo)) < len(combo):
                continue
            bindings = {r["role"]: h for r, h in zip(roles, combo)}
            conds = []
            for c in t.get("conditions") or []:
                e = evaluate(view, clock, c, bindings, nodes, ctx)
                conds.append({"condition": c, **e})
            st = combine([c["state"] for c in conds])
            result = {"true": "forced", "unknown": "switch", "false": "none"}[st]
            fetch = [c["condition"] for c in conds if c["state"] == "unknown"] if result == "switch" else []
            out.append({"template_id": t["key"], "bindings": bindings, "result": result,
                        "conditions": conds, "fetch_list": fetch, "notice_kind": t["forces"],
                        "window_to": window_to, "window_basis": basis,
                        "carrier_kinds": t.get("carrier_kinds") or [], "forbids": t.get("forbids")})
    return out


def ack_key(round_id: str, template_id: str, bindings: dict) -> str:
    return f"{round_id}:{template_id}:{sha(canon(bindings))[:8]}"


def derive_acks(db: DB, round_id: str) -> dict:
    """Tool: run derivation for the current segment, write derivations and candidates."""
    from .rounds import current_segment, get_round, require_pre_lock
    from .view import View
    require_pre_lock(db, round_id)
    rnd = get_round(db, round_id)
    seg = current_segment(db, round_id)
    view = View(db)
    res = compute(view, rnd, seg["clock"])
    summary = {"forced": 0, "switch": 0, "none": 0, "bindings_exceeded": 0}
    rows = []
    for r in res:
        summary[r["result"]] = summary.get(r["result"], 0) + 1
        n = len(db.rows("ack_derivations")) + 1
        did = f"D{n:05d}"
        ack_id = None
        if r["result"] in {"forced", "switch"}:
            ack_id = ack_key(round_id, r["template_id"], r["bindings"])
            existing = db.get("ack_nodes", ack_id)
            db.upsert("ack_nodes", ack_id, by="derive", round_id=round_id,
                      segment_idx=(existing or {}).get("segment_idx", seg["idx"]),
                      ack_kind="forced", origin="derived", derivation_id=did,
                      template_id=r["template_id"], notice_kind=r["notice_kind"],
                      obligation=r["forbids"], fact=None, source=",".join(r["carrier_kinds"]),
                      due_at=None, window_to=r["window_to"], window_basis=r["window_basis"],
                      window_ratified=r["window_basis"] == "statute",
                      holder_id=next(iter(r["bindings"].values()), None),
                      bindings=r["bindings"], is_switch=r["result"] == "switch",
                      status=(existing or {}).get("status") or "candidate",
                      fetch_list=r["fetch_list"])
        db.append("ack_derivations", derivation_id=did, round_id=round_id, segment_idx=seg["idx"],
                  clock=seg["clock"], template_id=r["template_id"], bindings=r["bindings"],
                  conditions=[{k: c[k] for k in ("condition", "state", "evidence", "why")}
                              for c in r["conditions"]],
                  result=r["result"], fetch_list=r["fetch_list"], ack_id=ack_id)
        rows.append({"derivation_id": did, "template_id": r["template_id"], "bindings": r["bindings"],
                     "result": r["result"], "ack_id": ack_id,
                     "fetch_list": r["fetch_list"],
                     "conditions": [(c["state"], c["why"]) for c in r["conditions"]]})
    return {"clock": seg["clock"], "segment": seg["idx"], "summary": summary, "derivations": rows}


def ack_ratify(db: DB, ack_id: str, decision: str, reason: str) -> dict:
    from .rounds import require_pre_lock
    a = db.get("ack_nodes", ack_id)
    if a is None:
        raise Refused(f"no ACK {ack_id}")
    require_pre_lock(db, a["round_id"])
    if decision not in {"ratified", "dropped"}:
        raise Refused("decision is 'ratified' or 'dropped'")
    if not reason:
        raise Refused("a ratification carries a reason")
    if decision == "ratified" and a["origin"] == "locator" and not a.get("is_switch") and not a.get("obligation"):
        raise Refused("a locator candidate is ratified as a switch unless its obligation is documented (§25.3)")
    db.upsert("ack_nodes", ack_id, status=decision)
    db.append("ack_status", ack_id=ack_id, status=decision, reason=reason, is_switch=bool(a.get("is_switch")))
    return db.get("ack_nodes", ack_id)


def ack_add(db: DB, round_id: str, ack_kind: str, notice_kind: str, fact: str, source: str,
            bindings: dict, due_at: str | None = None, obligation: str | None = None,
            origin: str = "operator", window_to: str | None = None, window_basis: str | None = None,
            attention: bool = False) -> dict:
    """Operator or calendar ACKs (§22.1). Forced ACKs carry an obligation and never a date."""
    from .rounds import current_segment, get_round, require_pre_lock
    require_pre_lock(db, round_id)
    rnd = get_round(db, round_id)
    if ack_kind not in {"scheduled", "forced"}:
        raise Refused("ack_kind is 'scheduled' or 'forced'; discretionary is conditioning, never an ACK")
    if origin not in {"operator", "calendar", "locator"}:
        raise Refused("derived ACKs arrive through derive_acks")
    if ack_kind == "scheduled" and not due_at:
        raise Refused("a scheduled ACK must have due_at")
    if ack_kind == "forced":
        if due_at:
            raise Refused("a forced ACK must not have a date: a public date is what makes a fact scheduled")
        if not obligation:
            raise Refused("a forced ACK must carry its obligation")
    cap = (ts(rnd["event_date"]) + _dt.timedelta(days=int(config.get("DUE_AT_MAX_DAYS")))).strftime("%Y-%m-%d")
    if ack_kind == "forced":
        if window_to is None:
            window_to, window_basis = cap, "cap"
        elif window_to > cap:
            window_to, window_basis = cap, "cap"
    seg = current_segment(db, round_id)
    n = len([a for a in db.rows("ack_nodes") if a["round_id"] == round_id]) + 1
    key = f"{round_id}:op{n:03d}"
    return db.upsert("ack_nodes", key, round_id=round_id, segment_idx=seg["idx"], ack_kind=ack_kind,
                     origin=origin, notice_kind=notice_kind, fact=fact, source=source,
                     obligation=obligation, due_at=due_at, window_to=window_to,
                     window_basis=window_basis or ("statute" if due_at else None),
                     window_ratified=window_basis in {"statute", "cap"} if window_basis else False,
                     holder_id=next(iter(bindings.values()), None), bindings=bindings,
                     attention=bool(attention), is_switch=False, status="candidate", fetch_list=[])


def ack_window(db: DB, ack_id: str, window_to: str, basis: str) -> dict:
    a = db.get("ack_nodes", ack_id)
    if a is None:
        raise Refused(f"no ACK {ack_id}")
    from .rounds import get_round, require_pre_lock
    require_pre_lock(db, a["round_id"])
    if basis not in {"statute", "procedural_chain", "operator", "cap"}:
        raise Refused("basis is statute, procedural_chain, operator or cap")
    rnd = get_round(db, a["round_id"])
    cap = (ts(rnd["event_date"]) + _dt.timedelta(days=int(config.get("DUE_AT_MAX_DAYS")))).strftime("%Y-%m-%d")
    if day(window_to) > cap:
        raise Refused(f"window_to exceeds the DUE_AT_MAX_DAYS cap ({cap})")
    return db.upsert("ack_nodes", ack_id, window_to=day(window_to), window_basis=basis, window_ratified=True)
