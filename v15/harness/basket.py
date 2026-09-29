"""D2/D4: event-footprint baskets. The event is the thesis, the ACK is the clock, the positions are the footprint.
v8: synthetic legs listed alongside natural legs (§E), narrative divergence per leg (§F2).
v9: the structural sign is the sign at lock (§C2; later revisions show as revised_sign), every leg carries an
arming_status in {armed_dated, gate_pass_undated, gate_fail, unchecked} (§E), leg support reads the touched-set
citations first (§C1), and a synthetic built after lock is flagged. Nothing here is scored as a whole."""
import sqlite3
from datetime import date, timedelta

from . import config
from .db import get_row
from .errors import NotFound
from .rounds import latest_resolutions, list_predictions, list_touched_set, round_state
from .util import loads


def lock_time(conn: sqlite3.Connection, round_id: str) -> str | None:
    r = conn.execute("SELECT recorded_at FROM round_transitions WHERE round_id = ? AND to_state = 'locked' ORDER BY rowid LIMIT 1",
                     (round_id,)).fetchone()
    return r["recorded_at"] if r else None


def _sign_rows(conn: sqlite3.Connection, holder_id: str, node: str, as_of: str | None = None) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        "SELECT id, attribute, value, supersedes, recorded_at FROM positions WHERE holder_id = ? AND lower(node) = lower(?) ORDER BY rowid",
        (holder_id, node))]
    if as_of:
        rows = [r for r in rows if r["recorded_at"] <= as_of]
    superseded = {r["supersedes"] for r in rows if r["supersedes"]}
    return [r for r in rows if r["id"] not in superseded]


def _sign_of(rows: list[dict]) -> str | None:
    sign_rows = [r for r in rows if r["attribute"] == "sign_of_exposure"]
    signs = {r["value"] for r in sign_rows}
    return "both" if {"+", "-"} <= signs else (sign_rows[-1]["value"] if sign_rows else None)


def _all_position_ids(conn: sqlite3.Connection, holder_id: str, node: str) -> list[str]:
    """Every positions row of the leg, superseded ones included: predicate checks written against a pre-lock row
    still belong to the leg after a post-lock revision supersedes that row."""
    return [r["id"] for r in conn.execute("SELECT id FROM positions WHERE holder_id = ? AND lower(node) = lower(?) ORDER BY rowid", (holder_id, node))]


def _leg_sign(conn: sqlite3.Connection, holder_id: str, node: str, as_of: str | None = None) -> tuple[str | None, list[str], dict | None]:
    """(sign at as_of, current position ids, revised_sign) where revised_sign is the current sign when it differs
    from the sign at as_of (v9 C2: post-lock revisions are new rows shown separately, never the locked sign)."""
    current = _sign_rows(conn, holder_id, node)
    sign_now = _sign_of(current)
    if not as_of:
        return sign_now, [r["id"] for r in current], None
    at = _sign_rows(conn, holder_id, node, as_of)
    sign_at = _sign_of(at)
    revised = None
    if sign_now != sign_at:
        latest = [r for r in current if r["attribute"] == "sign_of_exposure" and r["recorded_at"] > as_of]
        revised = {"sign": sign_now, "recorded_at": latest[-1]["recorded_at"] if latest else None,
                   "position_id": latest[-1]["id"] if latest else None}
    return sign_at, [r["id"] for r in current], revised


def round_legs(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    """Legs = distinct (holder, node) pairs the round touched: touched_set rows (with degree and cited mechanisms),
    factor links, and positions recorded while the round was live (for rounds locked before B3 existed)."""
    rd = get_row(conn, "rounds", round_id, "round")
    locked_at = lock_time(conn, round_id)
    legs: dict[tuple[str, str], dict] = {}

    def add(holder_id: str, node: str, source: str, degree: int | None = None, mechanism_ids: list[str] | None = None):
        key = (holder_id, node.lower())
        if key in legs:
            legs[key]["sources"].add(source)
            if degree is not None and legs[key]["degree"] is None:
                legs[key]["degree"] = degree
            for m in mechanism_ids or []:
                if m not in legs[key]["mechanism_ids"]:
                    legs[key]["mechanism_ids"].append(m)
            return
        h = get_row(conn, "holders", holder_id, "holder")
        sign, pos_ids, revised = _leg_sign(conn, holder_id, node, locked_at)
        legs[key] = {"holder_id": holder_id, "holder": h["canonical_name"], "key": h.get("key"), "listed": bool(h["listed"]),
                     "node": node, "sign": sign, "revised_sign": revised, "position_ids": pos_ids, "round_id": round_id,
                     "all_position_ids": _all_position_ids(conn, holder_id, node), "sources": {source},
                     "degree": degree, "mechanism_ids": list(mechanism_ids or [])}

    for t in list_touched_set(conn, round_id):
        add(t["holder_id"], t["node"], "touched_set", t["degree"], loads(t["mechanism_ids"]) if t.get("mechanism_ids") else None)
    for p in list_predictions(conn, round_id):
        for f in p["factors"]:
            if f["holder_id"] and f["node"]:
                add(f["holder_id"], f["node"], "factor")
    # positions recorded while the round was live: from intake to scoring (or void); never a later round's positions
    end = conn.execute("SELECT recorded_at FROM round_transitions WHERE round_id = ? AND to_state IN ('scored','void') ORDER BY rowid LIMIT 1",
                       (round_id,)).fetchone()
    for r in conn.execute("SELECT DISTINCT holder_id, node FROM positions WHERE recorded_at >= ? AND recorded_at <= ? ORDER BY rowid",
                          (rd["recorded_at"], end["recorded_at"] if end else "9999")):
        add(r["holder_id"], r["node"], "position_recorded_in_round")
    out = list(legs.values())
    for l in out:
        l["sources"] = sorted(l["sources"])
    return out


def _narrative_for_leg(preds: list[dict], res: dict, leg: dict) -> list[dict]:
    """F2: narrative rows that measure this leg, with their outcome and divergence from the structural sign at lock."""
    out = []
    for p in preds:
        if p["call_type"] != "narrative" or p.get("position_id") not in leg.get("all_position_ids", leg["position_ids"]):
            continue
        r = res.get(p["id"])
        out.append({"prediction_id": p["id"], "carrier": p["carrier"], "narrative_sign": p["narrative_sign"],
                    "structural_sign": leg["sign"], "revised_sign": leg.get("revised_sign"),
                    "divergence": leg["sign"] in ("+", "-", "0") and p["narrative_sign"] != leg["sign"],
                    "channel_said_it": (r["outcome"] if r else None)})
    return out


def event_basket(conn: sqlite3.Connection, round_id: str, include_synthetics: bool = True, space: str = "positive") -> dict:
    """space: positive (the covered cells and the operator's calls; the control), mirror (uncovered cells as legs), both."""
    from .db import get_row as _get_row
    from .library import resolve_rule
    from .predicates import ARMING_STATUSES, armed_legs, status_counts
    from .risk import existence_floor_holds, leg_due_at, now_covered, reencode_for_leg, residual_state
    from .scheduled import scheduled_for
    from .synthetic import gate_reading, list_synthetics
    if space not in ("positive", "mirror", "both"):
        raise ValueError("space must be positive, mirror or both")
    round_state(conn, round_id)
    locked_at = lock_time(conn, round_id)
    rd_ = _get_row(conn, "rounds", round_id, "round")
    ev_ = _get_row(conn, "events", rd_["event_id"], "event")
    legs = round_legs(conn, round_id)
    preds = list_predictions(conn, round_id)
    res = latest_resolutions(conn, round_id)
    arming = {a["position_id"]: a for a in armed_legs(conn, round_id)}
    all_rule_ids = sorted({rid for p in preds for rid in p["mechanism_ids"]})

    def weight(rids):
        ws = []
        for rid in rids:
            try:
                ws.append(resolve_rule(conn, rid)["weight"])
            except NotFound:
                pass
        return round(min(ws), 6) if ws else None

    by_node: dict[str, list[int]] = {}
    for i, l in enumerate(legs):
        by_node.setdefault(l["node"].lower(), []).append(i)
    out_legs = []
    for i, l in enumerate(legs):
        cited = sorted({rid for p in preds for f in p["factors"] for rid in p["mechanism_ids"]
                        if (f["holder_id"] == l["holder_id"]) or (f["node"] and f["node"].lower() == l["node"].lower())})
        if l["mechanism_ids"]:
            support, support_from = weight(l["mechanism_ids"]), "touched-set rules"
        elif cited:
            support, support_from = weight(cited), "factor-linked rules"
        else:
            support, support_from = weight(all_rule_ids), ("round rules" if all_rule_ids else None)
        arm = [arming[pid] for pid in l["all_position_ids"] if pid in arming]
        armed = bool(arm) and all(a["armed"] for a in arm)
        dated = any(a["dated"] for a in arm)
        statuses = [a["arming_status"] for a in arm]
        status = ("eliminated" if "eliminated" in statuses           # v13 A6: nothing on the leg comes before any gate
                  else "armed_dated" if statuses and all(s == "armed_dated" for s in statuses)
                  else "gate_fail" if "gate_fail" in statuses
                  else "gate_pass_undated" if "gate_pass_undated" in statuses or "armed_dated" in statuses
                  else "unchecked")
        narrative = _narrative_for_leg(preds, res, l)
        # v12 D3/E: what was already priced on this leg, and whether the fact's class is the price-setter's
        from . import edge as edge_mod
        leg_calls = [p for p in preds if p.get("position_id") in l["all_position_ids"]]
        execs = []
        for p in leg_calls:
            if p["call_type"] not in ("sign", "magnitude_order", "null"):
                continue
            e = edge_mod.executability(p["call_type"], p.get("sign"), p.get("implied_value"), p.get("implied_method"),
                                       edge_mod.expected_move_from(p["claim"]))
            execs.append({"prediction_id": p["id"], "call_type": p["call_type"], "implied": p.get("implied_value"),
                          "implied_method": p.get("implied_method"), **e})
        ann = edge_mod.annotations_for(conn, round_id, l["all_position_ids"])
        # v10 I2/I3: re-encode and residual state, forcing date (earliest due_at or dated fact on the leg)
        due = leg_due_at(conn, round_id, l["all_position_ids"], ev_["event_date"])
        reenc = reencode_for_leg(conn, round_id, l["all_position_ids"], ev_["event_date"], due)
        floor = existence_floor_holds(conn, round_id, l["listed"])
        dated_facts = [f for f in scheduled_for(conn, [l["holder_id"]], ev_["event_date"], due) if not f["hindsight"]]
        forcing = min([due] + [f["source_time"] for f in dated_facts])
        out_legs.append({
            **{k: l[k] for k in ("holder_id", "holder", "key", "listed", "node", "sign", "revised_sign", "position_ids", "all_position_ids", "sources", "degree", "mechanism_ids", "round_id")},
            "synthetic": False,
            "reencode": reenc, "residual_state": residual_state(reenc, floor), "forcing_date": forcing, "due_at": due,
            "support_weight": support, "support_from": support_from,
            "arming": [{k: a[k] for k in ("position_id", "predicates", "armed", "dated", "arming_status")} for a in arm],
            "armed": armed, "dated": dated, "arming_status": status,
            "expression": "directional permitted" if status == "armed_dated" else ("support-branch only" if status == "gate_pass_undated" else None),
            "executability": execs,
            "executable": next((e["executable"] for e in execs if e["executable"] != "no"), "no" if execs else None),
            "class_annotation": ann,
            "class_divergence": (ann["class_divergence"] if ann else None),
            "class_distance": (ann["class_distance"] if ann else None),
            "arming_candidate": (bool(ann["class_divergence"]) if ann else None),
            "correlated_with": [legs[j]["holder"] for j in by_node[l["node"].lower()] if j != i],
            "narrative": narrative,
            "divergence": any(n["divergence"] for n in narrative),
        })
    synthetics = []
    if include_synthetics:
        for s in list_synthetics(conn, round_id):
            arm = arming.get(s["id"])
            status = arm["arming_status"] if arm else "unchecked"
            synthetics.append({
                "synthetic": True, "synthetic_id": s["id"], "node": s["target_node"], "shape": s["shape"], "rule": s["rule_key"],
                "components": s["components"], "n_components": len(s["components"]), "listed_components": s["listed_components"],
                "support_weight": s["support_weight"], "gate": gate_reading(conn, s), "cross_node": bool(s.get("cross_node")), "space": s.get("space") or "positive",
                "built_after_lock": bool(locked_at and s["recorded_at"] > locked_at),
                "arming": [{k: arm[k] for k in ("position_id", "predicates", "armed", "dated", "arming_status")}] if arm else [],
                "armed": bool(arm and arm["armed"]), "dated": bool(arm and arm["dated"]), "arming_status": status,
                "expression": "directional permitted" if status == "armed_dated" else ("support-branch only" if status == "gate_pass_undated" else None),
            })
    n_div = sum(1 for l in out_legs if l["divergence"])
    # v10 K4: grid cells as legs of the requested space
    cells = []
    if space in ("mirror", "both"):
        gate_by_pid = {a["position_id"]: a for a in armed_legs(conn, round_id)}
        for c in conn.execute("SELECT * FROM grid_cells WHERE round_id = ? ORDER BY rowid", (round_id,)):
            c = dict(c)
            if space == "mirror" and c["space"] != "mirror":
                continue
            leg = next((l for l in out_legs if c["position_id"] in l["all_position_ids"]), None)
            arm = next((gate_by_pid[pid] for pid in (leg["all_position_ids"] if leg else [c["position_id"]]) if pid in gate_by_pid), None)
            gate_checked = bool(arm and arm["gate_checked"])
            gate_holds = bool(arm and any(v == "holds" for n, v in arm["predicates"].items() if "tradability" in n.lower()))
            if c["effect_kind"] == "vol":
                opt = conn.execute("SELECT options_listed FROM holders WHERE id = ?", (c["holder_id"],)).fetchone()
                gate_checked, gate_holds = True, bool(opt and opt["options_listed"])
            covered_now = now_covered(conn, c) if c["space"] == "mirror" else None
            uncovered = c["space"] == "mirror" and covered_now is None
            horizon = (date.fromisoformat(ev_["event_date"]) + timedelta(days=config.DUE_AT_MAX_DAYS)).isoformat()
            dated = bool(leg and any((not f["same_day"]) or c["window"] == "event_day"
                                     for f in dated_facts_for(conn, leg, ev_["event_date"], horizon)))
            if not gate_checked:
                st = "unchecked"
            elif not gate_holds:
                st = "gate_fail"
            elif c["space"] == "mirror" and not uncovered:
                st = "gate_fail"          # pred.disarm.now_covered
            elif dated:
                st = "armed_dated"
            else:
                st = "gate_pass_undated"
            cells.append({**{k: c[k] for k in ("id", "position_id", "holder_id", "node", "degree", "factor_kind", "effect_kind", "window", "space", "covering_rule_id", "prediction_id")},
                          "holder": leg["holder"] if leg else None, "arming_status": st, "uncovered": uncovered,
                          "now_covered_by": covered_now["key"] if covered_now else None, "dated": dated,
                          "residual_state": leg.get("residual_state") if leg else None})
    all_status = [l["arming_status"] for l in out_legs] + [s["arming_status"] for s in synthetics]
    return {"round_id": round_id, "space": space, "locked_at": locked_at, "legs": out_legs, "synthetics": synthetics, "n_legs": len(out_legs),
            "cells": cells, "cell_counts": {sp: sum(1 for c in cells if c["space"] == sp) for sp in ("positive", "mirror")},
            "mirror_arming": {st: sum(1 for c in cells if c["space"] == "mirror" and c["arming_status"] == st) for st in ("armed_dated", "gate_pass_undated", "gate_fail", "unchecked")},
            "residual_states": {st: sum(1 for l in out_legs if l["residual_state"] == st) for st in ("recovered", "unrecovered", "no_residual")},
            "executability": {k: sum(1 for l in out_legs if l["executable"] == k) for k in ("fadeable_null", "exceeds_implied", "no")},
            "class_divergent_legs": sum(1 for l in out_legs if l["class_divergence"]),
            "armed_leg_count": sum(1 for l in out_legs if l["armed"]) + sum(1 for s in synthetics if s["armed"]),
            "arming_status_counts": {s: all_status.count(s) for s in ARMING_STATUSES},
            "signs": {s: sum(1 for l in out_legs if l["sign"] == s) for s in ("+", "-", "0", "both", None)},
            "revised_legs": sum(1 for l in out_legs if l["revised_sign"]),
            "divergent_legs": n_div, "legs_with_narrative": sum(1 for l in out_legs if l["narrative"]),
            "note": "a view over the decomposition's positions; signs are the signs at lock; never scored as a whole"}


def dated_facts_for(conn: sqlite3.Connection, leg: dict, event_date: str, due: str, narrow: bool = True) -> list[dict]:
    """Non-hindsight scheduled or mechanical facts that could date this leg's cells (I5: either kind dates a cell).

    narrow (the default, and what a grid cell uses): the leg's own holder plus its parent and children. A statement by
    another holder on the same node is that holder's clock, not this one's. The wide read — every degree-0/1 holder on
    the node — belongs to the catalyst predicate, where `concerns_node` decides what it means."""
    from .scheduled import _neighbours, leg_holders, scheduled_for
    if narrow:
        ids = sorted(_neighbours(conn, leg["holder_id"]))
    else:
        ids = sorted(leg_holders(conn, leg.get("round_id") or "", leg)) if leg.get("round_id") else [leg["holder_id"]]
    return [f for f in scheduled_for(conn, ids, event_date, due) if not f["hindsight"]]


def divergence_stats(conn: sqlite3.Connection, round_ids: list[str]) -> dict:
    """F2 programme stat: fraction of legs with narrative/structure divergence and how each resolved."""
    legs = with_narr = divergent = 0
    resolved: dict[str, int] = {}
    for rid in round_ids:
        b = event_basket(conn, rid, include_synthetics=False)
        legs += b["n_legs"]
        with_narr += b["legs_with_narrative"]
        for l in b["legs"]:
            if l["divergence"]:
                divergent += 1
                for n in l["narrative"]:
                    if n["divergence"]:
                        k = f"channel_said_it={n['channel_said_it']}"
                        resolved[k] = resolved.get(k, 0) + 1
    return {"legs": legs, "legs_with_narrative": with_narr, "divergent_legs": divergent,
            "divergence_frac": (round(divergent / with_narr, 6) if with_narr else None), "resolutions": resolved}


def shared_factors(conn: sqlite3.Connection, round_id: str | None = None, hypothesis_ids: list[str] | None = None) -> dict:
    """D2: pairs of legs (or hypotheses) citing the same node, with each one's sign. Correlation by construction."""
    items: list[dict] = []
    if round_id:
        for l in round_legs(conn, round_id):
            items.append({"kind": "leg", "id": l["holder_id"], "label": l["holder"], "node": l["node"], "sign": l["sign"]})
    for hid in hypothesis_ids or []:
        h = get_row(conn, "hypotheses", hid, "hypothesis")
        node = h.get("node")
        holders = loads(h["holder_ids"]) or []
        if node and holders:
            for hh in holders:
                sign, _, _ = _leg_sign(conn, hh, node)
                items.append({"kind": "hypothesis", "id": hid, "label": h["text"][:60], "node": node, "sign": sign, "holder_id": hh})
        elif node:
            items.append({"kind": "hypothesis", "id": hid, "label": h["text"][:60], "node": node, "sign": None})
    pairs = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a["node"] and b["node"] and a["node"].lower() == b["node"].lower():
                pairs.append({"node": a["node"], "a": {k: a[k] for k in ("kind", "id", "label", "sign")},
                              "b": {k: b[k] for k in ("kind", "id", "label", "sign")},
                              "opposing": a["sign"] in ("+", "-") and b["sign"] in ("+", "-") and a["sign"] != b["sign"]})
    return {"items": len(items), "pairs": pairs, "opposing_pairs": sum(1 for p in pairs if p["opposing"]),
            "nodes": sorted({p["node"] for p in pairs})}
