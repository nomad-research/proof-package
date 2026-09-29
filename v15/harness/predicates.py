"""Predicate registry (§4.7) and predicate checks (§4.8, A7 scope)."""
import sqlite3

from .db import append, insert_mutable, transaction
from .util import loads
from .errors import NotFound, StateError, ValidationError
from .models import PredicateCheckIn

KINDS = ("arming", "disarming", "exit", "catalyst")
FIRST_TRAVERSAL_KEYS = ("pred.arm.first_traversal", "first traversal (event and node)")


def resolve_predicate(conn: sqlite3.Connection, id_or_name: str) -> dict:
    r = conn.execute("SELECT * FROM predicates WHERE id = ? OR name = ? OR key = ?",
                     (id_or_name, id_or_name, id_or_name)).fetchone()
    if not r:
        raise NotFound(f"no predicate with id, key or name {id_or_name!r}; see nomad_predicate_list")
    return dict(r)


def predicate_add(conn: sqlite3.Connection, name: str, kind: str, source: str, threshold: str,
                  date: str | None = None, role_note: str | None = None, active: bool = True,
                  key: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValidationError(f"kind must be one of {KINDS}")
    if not name.strip() or not source.strip() or not threshold.strip():
        raise ValidationError("name, source (named) and threshold are required")
    if conn.execute("SELECT 1 FROM predicates WHERE name = ?", (name,)).fetchone():
        raise ValidationError(f"predicate {name!r} already exists")
    if key and conn.execute("SELECT 1 FROM predicates WHERE key = ?", (key,)).fetchone():
        raise ValidationError(f"predicate key {key!r} already exists")
    row = insert_mutable(conn, "predicates", {
        "name": name.strip(), "kind": kind, "source": source, "threshold": threshold, "date": date,
        "role_note": role_note, "active": active, "key": key or None,
    })
    return {"predicate_id": row["id"], "name": row["name"], "key": key or None, "kind": kind}


def predicate_list(conn: sqlite3.Connection, kind: str | None = None, include_inactive: bool = False) -> list[dict]:
    sql, args = "SELECT * FROM predicates WHERE 1=1", []
    if kind:
        if kind not in KINDS:
            raise ValidationError(f"kind must be one of {KINDS}")
        sql += " AND kind = ?"
        args.append(kind)
    if not include_inactive:
        sql += " AND active = 1"
    return [dict(r) for r in conn.execute(sql + " ORDER BY kind, rowid", args)]


def predicate_check(conn: sqlite3.Connection, round_id: str, checks: list) -> dict:
    from .rounds import round_state
    state = round_state(conn, round_id)
    if state == "void":
        raise StateError(f"round {round_id} is void; predicate checks are not accepted")
    if not checks:
        raise ValidationError("checks must be a non-empty list")
    parsed = []
    for i, c in enumerate(checks):
        try:
            parsed.append(c if isinstance(c, PredicateCheckIn) else PredicateCheckIn.model_validate(c))
        except Exception as e:
            raise ValidationError(f"check[{i}] invalid: {e}")
    ids = []
    with transaction(conn):
        for c in parsed:
            p = resolve_predicate(conn, c.predicate_id)
            if (p["key"] in FIRST_TRAVERSAL_KEYS or p["name"] in FIRST_TRAVERSAL_KEYS) and not c.scope:
                raise ValidationError("first traversal is one predicate with two observations: pass scope 'event' and scope 'node' as separate checks")
            if c.position_id and not (conn.execute("SELECT 1 FROM positions WHERE id = ?", (c.position_id,)).fetchone()
                                      or conn.execute("SELECT 1 FROM synthetic_legs WHERE id = ?", (c.position_id,)).fetchone()):
                raise ValidationError(f"position_id {c.position_id!r} is not a positions row or a synthetic leg")
            row = append(conn, "predicate_checks", {
                "round_id": round_id, "predicate_id": p["id"], "claimed": c.claimed,
                "observed": c.observed, "note": c.note, "scope": c.scope, "basis": c.basis, "position_id": c.position_id,
            })
            ids.append({"check_id": row["id"], "predicate": p["name"], "kind": p["kind"], "scope": c.scope,
                        "claimed": c.claimed, "observed": c.observed, "position_id": c.position_id})
    return {"round_id": round_id, "state": state, "checks": ids}


def computed_gate(conn: sqlite3.Connection, round_id: str, holder_id: str | None, node: str | None,
                  synthetic_id: str | None = None) -> dict:
    """v12 0.3: arming status is a measurement, so the tradability gate is computed from the positions store when the
    operator wrote no check. Round 11 produced the first genuine opposing listed pair in eleven rounds and the gate was
    never checked per leg: an omission that only an operator could make, which is why it is now mechanical.

    Pair form: the node carries listed holders with opposing signs. Single form: this holder is listed."""
    from .positions import positions_on_node
    if synthetic_id:
        from .synthetic import gate_reading, get_synthetic
        syn = get_synthetic(conn, synthetic_id)
        if not syn:
            return {"gate": "unknown", "form": None, "source": "computed", "basis": "no synthetic row"}
        g = gate_reading(conn, syn)
        return {"gate": g["prima_facie"], "form": "pair (synthetic)", "source": "computed",
                "basis": f"{len(g['listed_components'])} listed components, signs {sorted({c['sign'] for c in g['listed_components']})}"}
    if not node:
        return {"gate": "unknown", "form": None, "source": "computed", "basis": "no node"}
    on = positions_on_node(conn, node)
    pairs = on["pairs"]
    listed_here = next((h for h in on["holders"] if h["holder_id"] == holder_id and h["listed"]), None)
    if pairs:
        return {"gate": "holds", "form": "pair", "source": "computed",
                "basis": f"{len(pairs)} opposing listed pair(s) on {node}: " +
                         "; ".join(f"{p['plus']['name']} (+) against {p['minus']['name']} (-)" for p in pairs[:3])}
    if listed_here:
        return {"gate": "unknown", "form": "single", "source": "computed",
                "basis": f"{listed_here['canonical_name']} is listed but no opposing listed holder sits on {node}: the single form "
                         "needs a visibility reading the store cannot supply"}
    return {"gate": "fails", "form": "single", "source": "computed", "basis": f"no listed holder on {node} for this leg"}


def armed_legs(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    """D3: per position (leg) with per-leg predicate checks: latest observed per arming predicate. A leg is armed when
    every arming predicate checked on it holds and the tradability gate is among them; dated when catalyst class holds."""
    from .config import TRADABILITY_GATE_KEYS
    rows = conn.execute(
        "SELECT pc.position_id, pc.observed, pc.claimed, p.name, p.key, p.kind FROM predicate_checks pc "
        "JOIN predicates p ON p.id = pc.predicate_id WHERE pc.round_id = ? AND pc.position_id IS NOT NULL ORDER BY pc.rowid",
        (round_id,)).fetchall()
    legs: dict[str, dict] = {}
    for r in rows:
        if r["kind"] not in ("arming", "catalyst"):
            continue
        leg = legs.setdefault(r["position_id"], {"position_id": r["position_id"], "predicates": {}, "_kinds": {}, "_keys": {}})
        leg["predicates"][r["name"]] = r["observed"] or f"claimed:{r['claimed']}"
        leg["_kinds"][r["name"]] = r["kind"]
        leg["_keys"][r["name"]] = r["key"]
    # v12 0.3: legs the operator never checked still get a gate reading, computed from the positions store
    if round_id:
        from .basket import round_legs
        for l in round_legs(conn, round_id):
            for pid_ in l["all_position_ids"]:
                if pid_ in legs:
                    break
            else:
                legs.setdefault(l["all_position_ids"][0] if l["all_position_ids"] else l["holder_id"],
                                {"position_id": l["all_position_ids"][0] if l["all_position_ids"] else l["holder_id"],
                                 "predicates": {}, "_kinds": {}, "_keys": {}, "_computed": (l["holder_id"], l["node"])})
        for s in conn.execute("SELECT id FROM synthetic_legs WHERE round_id = ?", (round_id,)):
            legs.setdefault(s["id"], {"position_id": s["id"], "predicates": {}, "_kinds": {}, "_keys": {}, "_computed": (None, None)})
    out = []
    for pid, leg in legs.items():
        computed = leg.pop("_computed", None)
        obs, kinds, keys = leg["predicates"], leg.pop("_kinds"), leg.pop("_keys")
        # v10: on a live round a claim stands until an observation replaces it; the view says which it is reading
        read = {n: (v[len("claimed:"):] if isinstance(v, str) and v.startswith("claimed:") else v) for n, v in obs.items()}
        observed_all = not any(isinstance(v, str) and v.startswith("claimed:") for v in obs.values())
        is_gate = lambda n: n in TRADABILITY_GATE_KEYS or keys.get(n) in TRADABILITY_GATE_KEYS
        gate = any(is_gate(n) for n in read)
        gate_holds = any(is_gate(n) and v == "holds" for n, v in read.items())
        arming_obs = {n: v for n, v in read.items() if kinds.get(n) == "arming"}
        armed = bool(arming_obs) and all(v == "holds" for v in arming_obs.values()) and gate_holds
        dated = any((kinds.get(n) == "catalyst" or "catalyst" in n.lower()) and v == "holds" for n, v in read.items())
        pos = conn.execute("SELECT holder_id, node FROM positions WHERE id = ?", (pid,)).fetchone()
        syn = None if pos else conn.execute("SELECT target_node FROM synthetic_legs WHERE id = ?", (pid,)).fetchone()
        gate_source = "checked" if gate else "computed"
        computed_reading = None
        if not gate:
            computed_reading = computed_gate(conn, round_id, pos["holder_id"] if pos else None,
                                             pos["node"] if pos else (syn["target_node"] if syn else None),
                                             synthetic_id=pid if syn else None)
            gate = computed_reading["gate"] != "unknown"
            gate_holds = computed_reading["gate"] == "holds"
            armed = gate_holds and all(v == "holds" for v in arming_obs.values()) if arming_obs else gate_holds
        # v13 A6: arming now reads surviving risk first. A leg no risk survives is not a leg that failed the gate, it
        # is a leg with nothing on it, and the two were indistinguishable before. `uncovered` (is anyone's rule
        # managing this leg) becomes a second, independent field rather than the primary one.
        sr = surviving_for(conn, round_id, pid)
        unc = uncovered_for(conn, round_id, pos["holder_id"] if pos else None)
        out.append({"position_id": pid, "holder_id": pos["holder_id"] if pos else None,
                    "node": pos["node"] if pos else (syn["target_node"] if syn else None), "synthetic": bool(syn),
                    "predicates": obs, "gate_checked": gate, "armed": armed, "dated": dated, "observed": observed_all,
                    "gate_source": gate_source, "computed_gate": computed_reading,
                    "survives": (None if sr is None else sr["survives"]),
                    "eliminators_fired": (sr["eliminators_fired"] if sr else None),
                    "surviving_magnitude": (sr["magnitude"] if sr else None),
                    # v14 A7: the binding term rides along and gates nothing. Arming still commits no capital; the
                    # point of recording the vector is that the terms can finally be calibrated against outcomes.
                    "binding_term": (sr.get("binding_term") if sr else None),
                    "vector": (loads(sr["vector"]) if sr and sr.get("vector") else None),
                    "assessment_confidence": (sr.get("confidence") if sr else None),
                    "uncovered": unc,
                    "arming_status": arming_status(gate, gate_holds, armed, dated,
                                                   survives=(None if sr is None else sr["survives"]))})
    return out


def surviving_for(conn: sqlite3.Connection, round_id: str, position_id: str) -> dict | None:
    from .surviving import survives_leg
    try:
        return survives_leg(conn, round_id, [position_id])
    except Exception:
        return None


def uncovered_for(conn: sqlite3.Connection, round_id: str, holder_id: str | None) -> bool | None:
    """v13 A6: `pred.arm.uncovered` as a filter on a structurally generated leg, never as a source of one. True when no
    active risk rule manages this leg's direction over the round's own horizon."""
    if not holder_id:
        return None
    from .db import get_row
    from .risk import covering_rule, factor_kind_for
    try:
        rd = get_row(conn, "rounds", round_id, "round")
        ev = get_row(conn, "events", rd["event_id"], "event")
    except Exception:
        return None
    fk = factor_kind_for(conn, holder_id)
    return covering_rule(conn, fk, None, "direction", "to_due", ev["event_date"]) is None


ARMING_STATUSES = ("armed_dated", "gate_pass_undated", "gate_fail", "eliminated", "unchecked")


def arming_status(gate_checked: bool, gate_holds: bool, armed: bool, dated: bool, survives: bool | None = None) -> str:
    """v9 E: three arming categories per leg (plus unchecked), and from v13 a fourth that comes before all of them.

    A leg where no risk survives cannot arm, whatever the gate says: there is nothing on it to express. `eliminated`
    is reported separately from `gate_fail` because they are different findings — one says the leg is untradable, the
    other says the leg is empty."""
    if survives is False:
        return "eliminated"
    if not gate_checked:
        return "unchecked"
    if not gate_holds:
        return "gate_fail"
    if armed and dated:
        return "armed_dated"
    return "gate_pass_undated"


def status_counts(legs: list[dict]) -> dict:
    return {s: sum(1 for l in legs if l.get("arming_status") == s) for s in ARMING_STATUSES}


def round_checks(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT pc.*, p.name, p.kind FROM predicate_checks pc JOIN predicates p ON p.id = pc.predicate_id "
        "WHERE pc.round_id = ? ORDER BY pc.rowid", (round_id,))]
