"""Standing-hypothesis notebook (§4.13). Status derives from predicate checks and (A12) from the support weight of the
cited rules; A10 adds a human-set schedule."""
import sqlite3
from datetime import date, timedelta

from . import config
from .db import append, get_row, insert_mutable, transaction
from .errors import NotFound, StateError, ValidationError
from .models import HypothesisCheckIn
from .predicates import resolve_predicate
from .util import dumps, loads, now_iso

TERMINAL = ("falsified", "expired", "resolved", "fired")


def _fmt(r) -> dict:
    d = dict(r)
    for k in ("holder_ids", "position_ids", "mechanism_ids", "arming_predicate_ids", "disarming_predicate_ids"):
        d[k] = loads(d[k])
    return d


def get_hypothesis(conn: sqlite3.Connection, hypothesis_id: str) -> dict:
    return _fmt(get_row(conn, "hypotheses", hypothesis_id, "hypothesis"))


def hypothesis_open(conn: sqlite3.Connection, text: str, holder_ids: list[str], mechanism_ids: list[str],
                    arming_predicate_ids: list[str], disarming_predicate_ids: list[str], falsifier: str,
                    granularity: str, node: str | None = None, position_ids: list[str] | None = None,
                    round_id: str | None = None, supersedes: str | None = None, spawned_from: dict | None = None) -> dict:
    from .library import resolve_rule_ids, rebuild_library_stats
    from .names import resolve_holder
    sp_pred = sp_idx = None
    if spawned_from:
        sp_pred, sp_idx = spawned_from.get("prediction_id"), int(spawned_from.get("factor_index", 0))
        if not conn.execute("SELECT 1 FROM prediction_factors WHERE prediction_id = ? AND idx = ?", (sp_pred, sp_idx)).fetchone():
            raise ValidationError(f"spawned_from: no factor {sp_idx} on prediction {sp_pred!r}")
    if not text.strip():
        raise ValidationError("text is required: one falsifiable sentence")
    if not (falsifier or "").strip():
        raise ValidationError("falsifier is required: what observation kills this hypothesis")
    if not (granularity or "").strip():
        raise ValidationError("granularity is required and is locked at creation (declare the resolution the claim is made at)")
    if not arming_predicate_ids:
        raise ValidationError("at least one arming predicate is required; a standing hypothesis waits on a predicate")
    arming = [resolve_predicate(conn, p) for p in arming_predicate_ids]
    disarming = [resolve_predicate(conn, p) for p in disarming_predicate_ids or []]
    for p in arming:
        if p["kind"] not in ("arming", "catalyst"):
            raise ValidationError(f"predicate {p['name']!r} has kind {p['kind']!r}; arming_predicate_ids need arming or catalyst predicates")
    for p in disarming:
        if p["kind"] not in ("disarming", "exit"):
            raise ValidationError(f"predicate {p['name']!r} has kind {p['kind']!r}; disarming_predicate_ids need disarming or exit predicates")
    holder_ids = [resolve_holder(conn, h)["id"] for h in holder_ids or []]
    mechanism_ids = resolve_rule_ids(conn, list(mechanism_ids or []))
    for pid in position_ids or []:
        get_row(conn, "positions", pid, "position")
    if round_id and not conn.execute("SELECT 1 FROM rounds WHERE id = ?", (round_id,)).fetchone():
        raise NotFound(f"no round {round_id!r}")
    if supersedes:
        get_hypothesis(conn, supersedes)
    with transaction(conn):
        row = insert_mutable(conn, "hypotheses", {
            "text": text.strip(), "node": node, "holder_ids": dumps(list(holder_ids)),
            "position_ids": dumps(list(position_ids)) if position_ids else None,
            "mechanism_ids": dumps(list(mechanism_ids)),
            "arming_predicate_ids": dumps([p["id"] for p in arming]),
            "disarming_predicate_ids": dumps([p["id"] for p in disarming]),
            "falsifier": falsifier.strip(), "granularity": granularity.strip(), "status": "open",
            "opened_in_round": round_id, "spawned_from_prediction_id": sp_pred, "spawned_from_factor_index": sp_idx,
        })
        if supersedes:
            conn.execute("UPDATE hypotheses SET superseded_by = ? WHERE id = ?", (row["id"], supersedes))
        rebuild_library_stats(conn)   # sets support_weight
    h = get_hypothesis(conn, row["id"])
    return {"hypothesis_id": row["id"], "status": "open", "granularity": row["granularity"], "supersedes": supersedes,
            "support_weight": h["support_weight"], "validation_threshold": config.VALIDATION_THRESHOLD}


def latest_observations(conn: sqlite3.Connection, hypothesis_id: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM hypothesis_checks WHERE hypothesis_id = ? ORDER BY rowid", (hypothesis_id,)):
        out[r["predicate_id"]] = dict(r)
    return out


def derive_status(conn: sqlite3.Connection, hyp: dict) -> tuple[str, str | None]:
    """(status, arming_note). Arming requires every arming predicate to hold AND support_weight >= threshold."""
    if hyp["status"] in TERMINAL:
        return hyp["status"], None
    latest = latest_observations(conn, hyp["id"])
    for pid in hyp["disarming_predicate_ids"]:
        if latest.get(pid, {}).get("observed") == "holds":
            return ("expired" if resolve_predicate(conn, pid)["kind"] == "exit" else "falsified"), None
    arming = hyp["arming_predicate_ids"]
    if arming and all(latest.get(pid, {}).get("observed") == "holds" for pid in arming):
        T = config.VALIDATION_THRESHOLD
        support = hyp.get("support_weight")
        if support is not None and support >= T:
            return "armed", f"armed: predicates hold, support_weight {support} >= {T}"
        return "open", f"not armed: predicates hold but support_weight {support} < threshold {T}"
    return "open", None


def hypothesis_check(conn: sqlite3.Connection, hypothesis_id: str, checks: list, today: date | None = None) -> dict:
    from .library import log_narrowing
    hyp = get_hypothesis(conn, hypothesis_id)
    if hyp["status"] == "resolved":
        raise StateError(f"hypothesis {hypothesis_id} is resolved; open a successor with supersedes={hypothesis_id!r} instead")
    if not checks:
        raise ValidationError("checks must be a non-empty list")
    parsed = [c if isinstance(c, HypothesisCheckIn) else HypothesisCheckIn.model_validate(c) for c in checks]
    attached = set(hyp["arming_predicate_ids"]) | set(hyp["disarming_predicate_ids"])
    ids = []
    with transaction(conn):
        for c in parsed:
            p = resolve_predicate(conn, c.predicate_id)
            if p["id"] not in attached:
                raise ValidationError(f"predicate {p['name']!r} is not attached to hypothesis {hypothesis_id}; "
                                      "open a successor hypothesis if the predicate set changed")
            for e in c.evidence_ids:
                get_row(conn, "evidence", e, "evidence")
            row = append(conn, "hypothesis_checks", {"hypothesis_id": hypothesis_id, "predicate_id": p["id"],
                                                     "observed": c.observed, "evidence_ids": dumps(c.evidence_ids), "note": c.note})
            ids.append({"check_id": row["id"], "predicate": p["name"], "kind": p["kind"], "observed": c.observed})
        new, note = derive_status(conn, hyp)
        if new != hyp["status"] or note:
            conn.execute("UPDATE hypotheses SET status = ?, status_changed_at = ?, arming_note = COALESCE(?, arming_note) WHERE id = ?",
                         (new, now_iso(), note, hypothesis_id))
        if note:
            log_narrowing(conn, "hypothesis", hypothesis_id, f"{hyp['status']}->{new}", hyp.get("support_weight"),
                          config.VALIDATION_THRESHOLD, note)
        if hyp.get("check_cadence_days"):
            nxt = (today or date.today()) + timedelta(days=int(hyp["check_cadence_days"]))
            conn.execute("UPDATE hypotheses SET next_check_at = ? WHERE id = ?", (nxt.isoformat(), hypothesis_id))
    return {"hypothesis_id": hypothesis_id, "previous_status": hyp["status"], "status": new, "arming_note": note,
            "support_weight": hyp.get("support_weight"), "checks": ids}


def hypothesis_schedule(conn: sqlite3.Connection, hypothesis_id: str, next_check_at: str | None,
                        hard_stop_at: str | None = None, check_cadence_days: int | None = None) -> dict:
    get_hypothesis(conn, hypothesis_id)
    for d in (next_check_at, hard_stop_at):
        if d:
            date.fromisoformat(d)
    if check_cadence_days is not None and int(check_cadence_days) <= 0:
        raise ValidationError("check_cadence_days must be positive")
    conn.execute("UPDATE hypotheses SET next_check_at = ?, hard_stop_at = COALESCE(?, hard_stop_at), "
                 "check_cadence_days = COALESCE(?, check_cadence_days) WHERE id = ?",
                 (next_check_at, hard_stop_at, check_cadence_days, hypothesis_id))
    h = get_hypothesis(conn, hypothesis_id)
    return {k: h[k] for k in ("id", "status", "next_check_at", "hard_stop_at", "check_cadence_days")}


def mark_resolved(conn: sqlite3.Connection, hypothesis_id: str, round_id: str) -> None:
    conn.execute("UPDATE hypotheses SET status = 'resolved', status_changed_at = ?, resolved_in_round = ? WHERE id = ?",
                 (now_iso(), round_id, hypothesis_id))


def hypotheses_due(conn: sqlite3.Connection, status: str | None = None, limit: int = 50, due_only: bool = False,
                   today: date | None = None) -> dict:
    today = today or date.today()
    statuses = [status] if status else ["open", "armed"]
    q = ",".join("?" for _ in statuses)
    rows = [_fmt(r) for r in conn.execute(
        f"SELECT * FROM hypotheses WHERE status IN ({q}) ORDER BY COALESCE(next_check_at, '0000'), rowid LIMIT ?",
        [*statuses, int(limit)])]
    out = []
    for h in rows:
        last = conn.execute("SELECT hc.*, p.name FROM hypothesis_checks hc JOIN predicates p ON p.id = hc.predicate_id "
                            "WHERE hypothesis_id = ? ORDER BY hc.rowid DESC LIMIT 1", (h["id"],)).fetchone()
        h["last_check"] = dict(last) if last else None
        latest = latest_observations(conn, h["id"])
        h["arming_status"] = {resolve_predicate(conn, pid)["name"]: latest.get(pid, {}).get("observed", "unchecked")
                              for pid in h["arming_predicate_ids"]}
        h["disarming_status"] = {resolve_predicate(conn, pid)["name"]: latest.get(pid, {}).get("observed", "unchecked")
                                 for pid in h["disarming_predicate_ids"]}
        h["due"] = h["next_check_at"] is None or h["next_check_at"] <= today.isoformat()
        h["hard_stop_passed"] = bool(h["hard_stop_at"]) and h["hard_stop_at"] < today.isoformat()
        if due_only and not h["due"]:
            continue
        out.append(h)
    return {"statuses": statuses, "today": today.isoformat(), "count": len(out), "hypotheses": out}
