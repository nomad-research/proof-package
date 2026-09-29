"""Scorer (§7): A6 coverage, A12 quality, A13 misreads, map calls, B1 factor derivation, C1 dispute awareness,
C2/C3 blind view, C4 scorer bias, the supersession path, and programme stats."""
import sqlite3
from collections import Counter

from . import config
from .config import NULL_CALL_WEIGHT, TRADABILITY_GATE_KEYS
from .db import append, transaction
from .errors import StateError, ValidationError
from .library import rebuild_library_stats, resolve_rule
from .models import FactorOutcomeIn, ResolutionIn, SecondScoreIn
from .rounds import (classification, current_criteria, latest_factor_resolutions, latest_resolutions, latest_reveal_context,
                     latest_scorecard, list_evidence, list_predictions, require_state, transition)
from .util import dumps, loads, now_iso

BANDS = ("days", "weeks", "months", "never")


def weight_for(call_type: str) -> float:
    return NULL_CALL_WEIGHT if call_type == "null" else 1.0


def evidence_class(conn: sqlite3.Connection, evidence_ids: list[str]) -> str:
    if not evidence_ids:
        return "none"
    q = ",".join("?" for _ in evidence_ids)
    dated = conn.execute(f"SELECT 1 FROM evidence WHERE id IN ({q}) AND source_time IS NOT NULL LIMIT 1", evidence_ids).fetchone()
    return "stated_dated" if dated else "inferred"


def quality_hit(round_class: str, scorer: str, coverage: str, call_type: str, ev_class: str) -> float:
    f = config.QUALITY_FACTORS
    q = (f["round_class"][round_class] * f["scorer"][scorer] * f["source_coverage"][coverage]
         * f["call_type"]["null" if call_type == "null" else "positive"] * f["evidence_class"][ev_class])
    return round(q, 6)


def quality_miss(coverage: str, call_type: str, ev_class: str) -> float:
    f = config.QUALITY_FACTORS
    vals = {"source_coverage": f["source_coverage"][coverage], "evidence_class": f["evidence_class"][ev_class],
            "call_type": f["call_type"]["null" if call_type == "null" else "positive"]}
    q = 1.0
    for k in config.MISS_FACTORS:
        q *= vals[k]
    return round(q, 6)


def resolution_quality(round_class: str, outcome: str, quarantined: bool, scorer: str | None, coverage: str | None,
                       call_type: str, ev_class: str) -> float | None:
    scorer = scorer or "self"
    coverage = coverage or "adequate"
    if outcome == "hit" and not quarantined:
        return quality_hit(round_class, scorer, coverage, call_type, ev_class)
    if outcome == "miss":
        return quality_miss(coverage, call_type, ev_class)
    return None


# ---- B1: factor derivation ---------------------------------------------------------------------

def derive_composite(aggregation: str, call_lag_band: str | None, factors: list[dict], outcomes: dict[int, dict]) -> dict:
    """Pure function. factors: [{idx, binding, against, estimate}]; outcomes: {idx: {outcome, observed}}.
    max/min: observed lag bands aggregate to a derived band; composite hits iff derived == the call's band.
    all: hit iff every factor hit; miss if any factor missed; else unverified."""
    missing = [f["idx"] for f in factors if f["idx"] not in outcomes]
    if missing:
        raise ValidationError(f"factor outcomes missing for factor indexes {missing}; every factor is scored")
    if aggregation in ("max", "min"):
        bands, binding_unverified, details = [], False, []
        for f in factors:
            fo = outcomes[f["idx"]]
            if fo["outcome"] in ("unverified", "untestable"):
                binding_unverified |= bool(f["binding"])
                details.append({"idx": f["idx"], "band": None, "outcome": fo["outcome"]})
                continue
            band = fo.get("observed") or (f["estimate"] if fo["outcome"] == "hit" else None)
            if band not in BANDS:
                raise ValidationError(f"factor {f['idx']}: observed must be a lag band (days|weeks|months|never) when the outcome is hit or miss")
            bands.append(band)
            details.append({"idx": f["idx"], "band": band, "outcome": fo["outcome"]})
        if not bands or binding_unverified:
            return {"outcome": "unverified", "derived_band": None, "aggregation": aggregation, "factors": details,
                    "reason": "binding factor unverified" if binding_unverified else "no factor observed"}
        pick = max if aggregation == "max" else min
        derived = pick(bands, key=BANDS.index)
        return {"outcome": "hit" if derived == call_lag_band else "miss", "derived_band": derived,
                "aggregation": aggregation, "factors": details, "claimed_band": call_lag_band}
    outs = [outcomes[f["idx"]]["outcome"] for f in factors]
    if any(o == "miss" for o in outs):
        outcome = "miss"
    elif all(o == "hit" for o in outs):
        outcome = "hit"
    else:
        outcome = "unverified"
    return {"outcome": outcome, "derived_band": None, "aggregation": "all",
            "factors": [{"idx": f["idx"], "outcome": outcomes[f["idx"]]["outcome"]} for f in factors]}


def _score_factors(conn: sqlite3.Connection, pred: dict, factor_outcomes: list[FactorOutcomeIn], scorer: str,
                   ev_ids: set[str]) -> dict:
    factors = pred["factors"]
    outcomes = {}
    for fo in factor_outcomes:
        if fo.factor_index not in {f["idx"] for f in factors}:
            raise ValidationError(f"prediction {pred['id']}: factor_index {fo.factor_index} does not exist")
        bad = [e for e in fo.evidence_ids if e not in ev_ids]
        if bad:
            raise ValidationError(f"factor {fo.factor_index}: evidence ids {bad} do not belong to this round")
        outcomes[fo.factor_index] = {"outcome": fo.outcome, "observed": fo.observed}
    composite = derive_composite(pred["aggregation"] or ("max" if pred["call_type"] == "lag_band" else "all"),
                                 pred["lag_band"], factors, outcomes)
    by_idx = {f["idx"]: f for f in factors}
    for fo in factor_outcomes:
        append(conn, "factor_resolutions", {"factor_id": by_idx[fo.factor_index]["id"], "prediction_id": pred["id"],
                                            "outcome": fo.outcome, "observed": fo.observed, "evidence_ids": dumps(fo.evidence_ids),
                                            "note": fo.note, "scorer": scorer})
    return composite


def _apply_c5(conn, round_id: str, pred: dict, r) -> None:
    noise, why = ordering_is_noise(conn, round_id, pred)
    if noise and r.outcome in ("hit", "miss"):
        r.outcome = "untestable"
        r.scorer_note = f"[v14 C5] {why}. Operator's reading, kept for the record: {r.scorer_note}"


def _resolution_row(conn: sqlite3.Connection, r: ResolutionIn, pred: dict, round_class: str, ev_ids: set[str],
                    branch_missed: str | None = None) -> dict:
    outcome, note = r.outcome, r.scorer_note
    if pred.get("branches"):
        if r.branch_arose not in (pred["branches"] + ["none"]):
            raise ValidationError(f"prediction {pred['id']} is a map call with branches {pred['branches']}: set branch_arose to one of them or 'none'")
    if branch_missed:
        # v8 B1: a row on a branch that did not arise resolves untestable at weight 0 and never touches a rule
        row = {
            "prediction_id": r.prediction_id, "outcome": "untestable", "mechanism_outcome": "unknown", "quarantined": False,
            "baseline_outcome": "unverified", "evidence_ids": dumps(r.evidence_ids),
            "scorer_note": f"branch {pred['conditional_on']['branch']!r} did not arise ({branch_missed}); untestable at weight 0. " + note,
            "weight": 0.0, "null_call_weight": NULL_CALL_WEIGHT, "supersedes": r.supersedes, "source_coverage": "adequate",
            "scorer": r.scorer, "evidence_class": evidence_class(conn, r.evidence_ids), "quality": None, "late_falsifier": False,
            "branch_arose": None,
        }
        return row
    if pred["factors"]:
        if not r.factor_outcomes:
            raise ValidationError(f"prediction {pred['id']} is decomposed: score each factor in factor_outcomes; the composite is derived")
        composite = _score_factors(conn, pred, r.factor_outcomes, r.scorer, ev_ids)
        outcome = composite["outcome"]
        if outcome != r.outcome:
            note = f"derived composite={outcome} (supplied {r.outcome} ignored); " + note
        note = f"derivation={dumps(composite)}; " + note
        if outcome in ("miss", "unverified") and not r.source_coverage:
            raise ValidationError(f"prediction {pred['id']}: derived composite is {outcome}; source_coverage is required")
    ev_class = evidence_class(conn, r.evidence_ids)
    quarantined = outcome == "hit" and r.mechanism_outcome == "wrong"
    coverage = r.source_coverage or ("adequate" if outcome in ("hit", "untestable") else None)
    note = ("late_falsifier: " if r.late_falsifier else "") + note
    return {
        "prediction_id": r.prediction_id, "outcome": outcome, "mechanism_outcome": r.mechanism_outcome,
        "quarantined": quarantined, "baseline_outcome": r.baseline_outcome, "evidence_ids": dumps(r.evidence_ids),
        "scorer_note": note, "weight": weight_for(pred["call_type"]), "null_call_weight": NULL_CALL_WEIGHT,
        "supersedes": r.supersedes, "source_coverage": coverage, "scorer": r.scorer, "evidence_class": ev_class,
        "quality": resolution_quality(round_class, outcome, quarantined, r.scorer, coverage, pred["call_type"], ev_class),
        "late_falsifier": r.late_falsifier, "branch_arose": r.branch_arose,
    }


def _branch_missed(conn: sqlite3.Connection, pred: dict, arose_in_batch: dict[str, str]) -> str | None:
    """For a conditional row: the branch that actually arose when it is not this row's branch, else None."""
    cond = pred.get("conditional_on")
    if not cond:
        return None
    arose = arose_in_batch.get(cond["prediction_id"])
    if arose is None:
        r = conn.execute("SELECT branch_arose FROM resolutions WHERE prediction_id = ? ORDER BY rowid DESC LIMIT 1",
                         (cond["prediction_id"],)).fetchone()
        arose = r["branch_arose"] if r else None
    if arose is None:
        raise ValidationError(f"prediction {pred['id']} is conditional on map call {cond['prediction_id']}: score that map call "
                              "(with branch_arose) in the same batch or before")
    return None if arose == cond["branch"] else arose


# ---- disputes (C1) ---------------------------------------------------------------------------------

def latest_second_scores(conn: sqlite3.Connection, round_id: str) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT s.* FROM second_scores s JOIN predictions p ON p.id = s.prediction_id WHERE p.round_id = ? ORDER BY s.rowid",
        (round_id,)).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        d = dict(r)
        d["evidence_ids"] = loads(d["evidence_ids"])
        out[d["prediction_id"]] = d
    return out


def disputed_predictions(conn: sqlite3.Connection, round_id: str) -> set[str]:
    """Predictions whose latest operator resolution differs from the latest second score and has not been human-ruled."""
    mine, theirs = latest_resolutions(conn, round_id), latest_second_scores(conn, round_id)
    out = set()
    for pid, b in theirs.items():
        a = mine.get(pid)
        if a and a.get("scorer") != "human" and (a["outcome"] != b["outcome"] or a["mechanism_outcome"] != b["mechanism_outcome"]):
            out.add(pid)
    return out


# ---- scorecard -----------------------------------------------------------------------------------------

def compute_scorecard(conn: sqlite3.Connection, round_id: str) -> dict:
    from .predicates import armed_legs
    preds = list_predictions(conn, round_id)
    res = latest_resolutions(conn, round_id)
    cls = classification(conn, round_id)
    disputed = disputed_predictions(conn, round_id)
    sum_w = out = base = 0.0
    sum_w_mech = mech = 0.0
    n_res = n_unv = n_unt = n_q = n_misread = 0
    map_n = map_hits = 0
    narr_n = narr_said = 0
    branch_dead = 0
    per_call = []
    mirror = {"n": 0, "hits": 0, "expired": 0}
    for p in preds:
        r = res.get(p["id"])
        if not r:
            continue
        if p.get("space") == "mirror":
            mirror["n"] += 1
            mirror["hits"] += r["outcome"] == "hit"
            mirror["expired"] += bool(r.get("expired"))
        n_res += 1
        hit = r["outcome"] == "hit"
        q = bool(r["quarantined"])
        misread = r["outcome"] == "miss" and r["mechanism_outcome"] == "right"
        is_map = p["call_type"] == "map"
        is_narr = p["call_type"] == "narrative"
        if r["outcome"] == "untestable" and (r["weight"] or 0) == 0 and p.get("conditional_on"):
            branch_dead += 1
        n_q += q
        n_misread += misread
        per_call.append({"prediction_id": p["id"], "call_type": p["call_type"], "outcome": r["outcome"], "hit": int(hit),
                         "weight": r["weight"], "quarantined": q, "misread": misread, "disputed": p["id"] in disputed,
                         "decomposed": bool(p["factors"]), "baseline_outcome": r["baseline_outcome"],
                         "quality": r.get("quality"), "source_coverage": r.get("source_coverage"),
                         "late_falsifier": bool(r.get("late_falsifier")), "scorer": r.get("scorer")})
        if r["outcome"] == "untestable":
            n_unt += 1
            continue
        if r["outcome"] == "unverified":
            n_unv += 1
        w = r["weight"]
        sum_w += w
        out += hit * w
        base += (r["baseline_outcome"] == "hit") * w
        if is_map:
            map_n += 1
            map_hits += hit
        elif is_narr:
            narr_n += 1
            narr_said += hit
        else:
            sum_w_mech += w
            mech += (hit and not q) * w
    div = (lambda x: round(x / sum_w, 6)) if sum_w else (lambda x: None)
    divm = (lambda x: round(x / sum_w_mech, 6)) if sum_w_mech else (lambda x: None)
    gate_q = ",".join("?" for _ in TRADABILITY_GATE_KEYS)

    def checked(col: str, gate_only: bool) -> bool:
        sql = (f"SELECT 1 FROM predicate_checks pc JOIN predicates p ON p.id = pc.predicate_id "
               f"WHERE pc.round_id = ? AND p.kind = 'arming' AND pc.{col} = 'holds'")
        args: list = [round_id]
        if gate_only:
            sql += f" AND (p.key IN ({gate_q}) OR p.name IN ({gate_q}))"
            args += [*TRADABILITY_GATE_KEYS, *TRADABILITY_GATE_KEYS]
        return bool(conn.execute(sql + " LIMIT 1", args).fetchone())

    from .predicates import status_counts
    legs = armed_legs(conn, round_id)
    n_armed = sum(1 for l in legs if l["armed"])
    arming_counts = status_counts(legs)
    # v8: where per-leg checks exist, the round arms only if a leg armed; a gate holding on one leg is not arming
    gate_claimed, gate_observed = checked("claimed", True), checked("observed", True)
    if legs:
        gate_observed = gate_observed and n_armed > 0
    o, m, b = div(out), divm(mech), div(base)
    return {
        "round_id": round_id, "round_class": cls["round_class"], "contamination": cls["contamination"],
        "outcome_score": o, "mechanism_score": m, "baseline_score": b,
        "edge_vs_baseline": (round(m - b, 6) if m is not None and b is not None else None),
        "map_score": (round(map_hits / map_n, 6) if map_n else None), "n_map_calls": map_n,
        "narrative_rows": narr_n, "narrative_said_it": narr_said, "branch_dead_rows": branch_dead,
        "misreads": n_misread, "misread_frac": (round(n_misread / n_res, 6) if n_res else None),
        "disputes_pending": len(disputed),
        "armed_leg_count": n_armed, "legs_checked": len(legs), "arming_status_counts": arming_counts,
        "null_called": any(p["call_type"] == "null" for p in preds),
        "arming_claimed": gate_claimed, "arming_observed": gate_observed,
        "any_arming_claimed": checked("claimed", False), "any_arming_observed": checked("observed", False),
        "unverified_frac": (round(n_unv / n_res, 6) if n_res else None),
        "untestable_frac": (round(n_unt / n_res, 6) if n_res else None),
        "n_predictions": len(preds), "n_resolved": n_res, "n_quarantined": n_q, "n_expired": sum(1 for r in res.values() if r.get("expired")),
        "mirror_calls": mirror,
        "sum_weight": sum_w, "sum_weight_mechanism": sum_w_mech, "null_call_weight": NULL_CALL_WEIGHT, "per_call": per_call,
    }


def _leg_ids_of(conn: sqlite3.Connection, position_id: str | None) -> list[str]:
    if not position_id:
        return []
    p = conn.execute("SELECT holder_id, node FROM positions WHERE id = ?", (position_id,)).fetchone()
    if not p:
        return [position_id]
    return [r["id"] for r in conn.execute("SELECT id FROM positions WHERE holder_id = ? AND lower(node) = lower(?)", (p["holder_id"], p["node"]))]


def _narrative_gate(conn: sqlite3.Connection, round_id: str, preds: dict, batch_ids: set[str], today: str) -> None:
    """v10 A4: a structural call on a leg is refused while the leg's narrative row is due and unscored (unless scored in the same batch)."""
    res = latest_resolutions(conn, round_id)
    for pid in batch_ids:
        p = preds[pid]
        if p["call_type"] == "narrative" or not p.get("position_id"):
            continue
        leg = set(_leg_ids_of(conn, p["position_id"]))
        for n in preds.values():
            if n["call_type"] == "narrative" and n.get("position_id") in leg and n["id"] not in res and n["id"] not in batch_ids \
                    and n.get("due_at") and n["due_at"] <= today:
                raise ValidationError(f"prediction {pid}: the leg's narrative row {n['id']} is due ({n['due_at']}) and unscored; "
                                      "narrative first (v10 A4): score it before or with this structural call")


def _due_gate(preds: dict, parsed: list, today: str) -> None:
    """v10 A3: a call is scored once its due_at has passed, or when the scorer marks it resolved early."""
    for r in parsed:
        p = preds[r.prediction_id]
        if p.get("due_at") and p["due_at"] > today and not getattr(r, "early", False):
            raise ValidationError(f"prediction {r.prediction_id} is not due until {p['due_at']}; pass early=true (and say why in scorer_note) to resolve it now")


def open_scoring(conn: sqlite3.Connection, round_id: str, call_ids: list[str], note: str | None = None,
                 today: str | None = None) -> dict:
    """v12 0.4: retrieval is permitted only while a scoring session is open, and every fetch is answerable to a call in
    it. `partially_scored` no longer opens general retrieval: that is the hole round 11 fell through."""
    from datetime import date as _d
    from .rounds import list_predictions, require_state
    require_state(conn, round_id, ("open", "partially_scored"), "open a scoring session")
    today = today or _d.today().isoformat()
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    unknown = [c for c in call_ids if c not in preds]
    if unknown:
        raise ValidationError(f"unknown prediction ids on this round: {unknown}")
    if not call_ids:
        raise ValidationError("name the calls you are scoring: a session with no calls cannot account for a fetch")
    res = latest_resolutions(conn, round_id)
    already = [c for c in call_ids if c in res]
    if already:
        raise ValidationError(f"already resolved: {already}; a scoring session is for calls that still need one")
    live = open_session(conn)
    if live:
        raise StateError(f"a scoring session is already open ({live['id']}); close it first so every fetch has one owner")
    row = append(conn, "scoring_sessions", {"round_id": round_id, "call_ids": dumps(list(call_ids)),
                                            "opened_at": now_iso(), "note": note})
    return {"session_id": row["id"], "round_id": round_id, "calls": [{"prediction_id": c, "target": preds[c]["target"],
                                                                      "due_at": preds[c].get("due_at")} for c in call_ids],
            "note": "every fetch while this session is open must be attributable to one of these calls; close it when done"}


def close_scoring(conn: sqlite3.Connection, session_id: str | None = None) -> dict:
    r = conn.execute("SELECT * FROM scoring_sessions WHERE id = ?", (session_id,)).fetchone() if session_id else open_session(conn)
    if not r:
        return {"closed": None, "note": "no open scoring session"}
    r = dict(r)
    # scoring_sessions is append-only: the close is a new row that supersedes by id
    row = append(conn, "scoring_sessions", {"round_id": r["round_id"], "call_ids": r["call_ids"], "opened_at": r["opened_at"],
                                            "closed_at": now_iso(), "note": f"closes {r['id']}" + (f"; {r['note']}" if r["note"] else "")})
    return {"closed": r["id"], "close_row": row["id"], "round_id": r["round_id"]}


def open_session(conn: sqlite3.Connection) -> dict | None:
    rows = [dict(x) for x in conn.execute("SELECT * FROM scoring_sessions ORDER BY rowid")]
    import re as _re
    closed = {m.group(1) for r in rows if r["closed_at"] and r["note"]
              for m in [_re.match(r"closes ([0-9a-fA-F-]+)", r["note"])] if m}
    live = [r for r in rows if not r["closed_at"] and r["id"] not in closed]
    return live[-1] if live else None


def firewall_violation(conn: sqlite3.Connection, tool: str, detail: str, round_id: str | None = None) -> dict:
    s = open_session(conn)
    row = append(conn, "firewall_violations", {"session_id": s["id"] if s else None,
                                               "round_id": round_id or (s["round_id"] if s else None),
                                               "tool": tool, "detail": detail})
    return {"violation_id": row["id"], "session_id": s["id"] if s else None}


def round_of(conn: sqlite3.Connection, prediction_id: str) -> str:
    r = conn.execute("SELECT round_id FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
    if not r:
        raise ValidationError(f"no prediction {prediction_id!r}")
    return r["round_id"]


def score_batch(conn: sqlite3.Connection, resolutions: list, today: str | None = None) -> dict:
    """v11 E: one batch across every open round. Resolutions are grouped by their prediction's round and each round's
    gates (due date, narrative first) apply as usual; the batch reports per round."""
    from datetime import date as _d
    today = today or _d.today().isoformat()
    by_round: dict[str, list] = {}
    for r in resolutions:
        pid = r.prediction_id if hasattr(r, "prediction_id") else r["prediction_id"]
        by_round.setdefault(round_of(conn, pid), []).append(r)
    out = {"today": today, "rounds": {}, "scored": 0}
    for rid, rs in by_round.items():
        card = score_round(conn, rid, rs, today)
        out["rounds"][rid] = {k: card.get(k) for k in ("state", "outcome_score", "mechanism_score", "baseline_score",
                                                       "edge_vs_baseline", "remaining_calls")}
        out["scored"] += len(rs)
    out["still_due"] = calls_due(conn, before=today)["due"]
    return out


def second_scorer_batch(conn: sqlite3.Connection, before: str | None = None, nodes: list[str] | None = None) -> dict:
    """v11 E/A5: one blind view over every call across every live or scored round that has a final operator resolution
    and no second score yet. The second scorer scores the same batch."""
    from datetime import date as _d
    before = before or _d.today().isoformat()
    rounds_ = [r["round_id"] for r in conn.execute(
        "SELECT round_id FROM round_state WHERE state IN ('open','partially_scored','scored') ORDER BY state_changed_at")]
    views, n, failures = [], 0, []
    for rid in rounds_:
        try:
            v = second_scorer_view(conn, rid, nodes)
        except Exception as exc:
            # v15 0b.3: a round whose blind view failed to build used to be dropped in silence while the batch
            # reported success. scorer_bias is a standing statistic and C1 suspends disputed weights on it, so a
            # silently missing round is a silently wrong denominator.
            failures.append({"round_id": rid, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not v["predictions"]:
            continue
        n += len(v["predictions"])
        views.append(v)
    return {"before": before, "rounds": [v["round_id"] for v in views], "n_predictions": n, "views": views,
            "failures": failures, "n_failures": len(failures),
            "instructions": (views[0]["instructions"] if views else "nothing awaiting a second score"),
            "note": ("v11 E: disputes attach to calls, not rounds; score every prediction in every view"
                     + (f" -- WARNING: {len(failures)} round(s) could not be viewed and are missing from this batch"
                        if failures else ""))}


def disputes_batch(conn: sqlite3.Connection) -> dict:
    """v11 E: open disputes per call across rounds."""
    rows, n = [], 0
    for r in conn.execute("SELECT round_id FROM round_state WHERE state IN ('open','partially_scored','scored')"):
        d = score_disputes(conn, r["round_id"])
        for row in d["rows"]:
            if row["status"] == "dispute":
                rows.append({"round_id": r["round_id"], **row})
                n += 1
    return {"disputes": n, "rows": rows,
            "next_step": "the human breaks each with nomad_resolution_supersede (scorer='human')" if n else None}


def calls_due(conn: sqlite3.Connection, before: str | None = None, round_id: str | None = None) -> dict:
    """v10 A3: unresolved calls whose due_at is on or before `before`, across open and partially scored rounds."""
    from datetime import date as _d
    before = before or _d.today().isoformat()
    rows = conn.execute("SELECT s.round_id FROM round_state s WHERE s.state IN ('open','partially_scored')" + (" AND s.round_id = ?" if round_id else ""),
                        ((round_id,) if round_id else ())).fetchall()
    out, later = [], []
    for r in rows:
        res = latest_resolutions(conn, r["round_id"])
        for p in list_predictions(conn, r["round_id"]):
            if p["id"] in res:
                continue
            item = {"round_id": r["round_id"], "prediction_id": p["id"], "call_type": p["call_type"], "target": p["target"], "due_at": p.get("due_at"),
                    "position_id": p.get("position_id"), "space": p.get("space")}
            (out if (p.get("due_at") or "9999") <= before else later).append(item)
    out.sort(key=lambda x: (x["due_at"] or "9999", x["round_id"]))
    return {"before": before, "due": out, "not_yet_due": len(later), "rounds": [r["round_id"] for r in rows]}


def ordering_is_noise(conn, round_id: str, pred: dict) -> tuple[bool, str]:
    """v14 C5: a magnitude_order call where no leg on the round has an attributed move is ranking noise, and ranking
    noise resolves untestable rather than hit or miss. Round 13 ranked IRICO against Corning on a day when IRICO rose
    three per cent after being barred and Corning moved more than that inside its own band."""
    if pred["call_type"] != "magnitude_order":
        return False, ""
    from .db import get_row
    from .rounds import v13_on
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    if not v13_on(conn, ev):
        return False, "round predates the price layer, so the rule does not reach back to it"
    n = conn.execute("SELECT COUNT(*) FROM price_observations WHERE round_id = ? AND attributed = 1", (round_id,)).fetchone()[0]
    if n:
        return False, f"{n} attributed observation(s) on the round"
    return True, ("no attributed move on any leg of this round: an ordering over unattributed noise is not a ranking of "
                  "anything, so it resolves untestable")


def require_date_confirmed(conn, round_id: str) -> None:
    """v13 B2: nothing is scored until the event's date has been re-established from retrieval and Q2 re-computed
    against it. Round 12 was scored for an hour against a date that was a year out; the check costs one call."""
    from .db import get_row
    from .rounds import date_confirmed, v13_on
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    if v13_on(conn, ev) and not date_confirmed(conn, round_id):
        raise StateError("v13 B2: confirm the event's date against retrieval first (nomad_confirm_event_date). Q2 at "
                         "intake tested the date the submitter supplied, which is all intake has; the cutoff test is "
                         "only real once retrieval has established what the event is")


def _validate_resolutions(conn, round_id, preds, resolutions, require_all=True, model=ResolutionIn) -> list:
    parsed = []
    for i, r in enumerate(resolutions or []):
        try:
            parsed.append(r if isinstance(r, model) else model.model_validate(r))
        except Exception as e:
            raise ValidationError(f"resolution[{i}] invalid: {e}")
    given = [r.prediction_id for r in parsed]
    problems = []
    unknown = [g for g in given if g not in preds]
    dups = sorted({g for g in given if given.count(g) > 1})
    if unknown:
        problems.append(f"unknown prediction ids {unknown}")
    if dups:
        problems.append(f"duplicate prediction ids {dups}")
    if require_all:
        missing = [pid for pid in preds if pid not in given]
        if missing:
            problems.append(f"missing resolutions for prediction ids {missing}")
    if problems:
        raise ValidationError("exactly one resolution per prediction is needed: " + "; ".join(problems)
                              + ". Use nomad_round_status / nomad_open_retrieval output for the prediction list.")
    ev_ids = {r["id"] for r in conn.execute("SELECT id FROM evidence WHERE round_id = ?", (round_id,))}
    for r in parsed:
        bad = [e for e in r.evidence_ids if e not in ev_ids]
        if bad:
            raise ValidationError(f"resolution for {r.prediction_id}: evidence ids {bad} do not belong to round {round_id}; "
                                  "add them with nomad_add_evidence first")
    return parsed


def _finish_scoring(conn: sqlite3.Connection, round_id: str, preds: dict, state: str) -> dict:
    """Recompute the card; move open -> partially_scored on the first resolution and -> scored when nothing is left."""
    from .hypotheses import mark_resolved
    res = latest_resolutions(conn, round_id)
    remaining = [p for p in preds.values() if p["id"] not in res]
    card = compute_scorecard(conn, round_id)
    append(conn, "scorecards", {"round_id": round_id, "scorecard_json": dumps(card), "null_call_weight": NULL_CALL_WEIGHT})
    if not remaining:
        transition(conn, round_id, state, "scored", "score_round")
        for p in preds.values():
            if p["hypothesis_id"]:
                mark_resolved(conn, p["hypothesis_id"], round_id)
        card["state"] = "scored"
    elif state == "open":
        transition(conn, round_id, "open", "partially_scored", "score_round (partial)")
        card["state"] = "partially_scored"
    else:
        card["state"] = state
    card["remaining_calls"] = [{"prediction_id": p["id"], "due_at": p.get("due_at"), "target": p["target"]} for p in remaining]
    lib = rebuild_library_stats(conn)
    card["notebook_rows"] = write_notebook_rows(conn, round_id)
    card["library_rebuild"] = lib
    return card


def score_round(conn: sqlite3.Connection, round_id: str, resolutions: list, today: str | None = None) -> dict:
    """v10 A3: the bulk form. Accepts the calls that are due (or marked early); the round closes when every call has a
    resolution. Calls already resolved are refused (use nomad_resolution_supersede)."""
    from datetime import date as _d
    from .risk import setting
    state = require_state(conn, round_id, ("open", "partially_scored"), "score round")
    require_date_confirmed(conn, round_id)
    today = today or _d.today().isoformat()
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    already = latest_resolutions(conn, round_id)
    v10 = bool(setting(conn, "freeze_started_at"))
    parsed = _validate_resolutions(conn, round_id, preds, resolutions, require_all=not v10)
    for r in parsed:                      # v14 C5, applied before anything is written
        _apply_c5(conn, round_id, preds[r.prediction_id], r)
    for r in parsed:
        if r.supersedes:
            raise ValidationError("supersedes is only valid on nomad_resolution_supersede after the round is scored")
        if r.prediction_id in already:
            raise ValidationError(f"prediction {r.prediction_id} already has a resolution; correct it with nomad_resolution_supersede")
    if v10:
        _due_gate(preds, parsed, today)
        _narrative_gate(conn, round_id, preds, {r.prediction_id for r in parsed}, today)
    cls = classification(conn, round_id)
    ev_ids = {r["id"] for r in conn.execute("SELECT id FROM evidence WHERE round_id = ?", (round_id,))}
    arose = {r.prediction_id: r.branch_arose for r in parsed if preds[r.prediction_id].get("branches")}
    with transaction(conn):
        # map calls first so conditional rows can read which branch arose
        ordered = sorted(parsed, key=lambda r: 0 if preds[r.prediction_id]["call_type"] == "map" else 1)
        for r in ordered:
            pred = preds[r.prediction_id]
            append(conn, "resolutions", _resolution_row(conn, r, pred, cls["round_class"], ev_ids,
                                                        branch_missed=_branch_missed(conn, pred, arose)))
        card = _finish_scoring(conn, round_id, preds, state)
    return card


def score_call(conn: sqlite3.Connection, round_id: str, resolution, today: str | None = None) -> dict:
    """v10 A3: score one call. Same gates as the bulk form."""
    return score_round(conn, round_id, [resolution], today)


def close_round(conn: sqlite3.Connection, round_id: str, today: str | None = None, note: str | None = None) -> dict:
    """v10 A3: expire every unresolved call whose due_at has passed: unverified, or hit for absence claims (sign 0,
    null) at coverage thin. Nothing not yet due is touched; the round closes only when nothing remains."""
    from datetime import date as _d
    state = require_state(conn, round_id, ("open", "partially_scored"), "close round")
    today = today or _d.today().isoformat()
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    res = latest_resolutions(conn, round_id)
    cls = classification(conn, round_id)
    expired = []
    with transaction(conn):
        for p in preds.values():
            if p["id"] in res or not p.get("due_at") or p["due_at"] > today:
                continue
            absence = p["call_type"] == "null" or (p["call_type"] == "sign" and p.get("sign") == "0")
            outcome = "hit" if absence else "unverified"
            r = ResolutionIn(prediction_id=p["id"], outcome=outcome, mechanism_outcome="unknown", baseline_outcome="unverified",
                             source_coverage="thin", scorer_note=f"expired at due_at {p['due_at']} without a resolution" + (f"; {note}" if note else ""),
                             factor_outcomes=[FactorOutcomeIn(factor_index=f["idx"], outcome="unverified", note="expired") for f in p["factors"]],
                             branch_arose=("none" if p.get("branches") else None))
            row = _resolution_row(conn, r, p, cls["round_class"], set(), branch_missed=_branch_missed(conn, p, {}) if p.get("conditional_on") else None)
            row["expired"] = True
            append(conn, "resolutions", row)
            expired.append({"prediction_id": p["id"], "outcome": row["outcome"], "due_at": p["due_at"]})
        card = _finish_scoring(conn, round_id, preds, state)
    card["expired"] = expired
    return card


# ---- v9 F: notebook claims get their per-round rows from the basket view ----------------------------------------------

def notebook_rows_for(conn: sqlite3.Connection, round_id: str) -> dict:
    """E4: did a synthetic pass the gate where the natural legs failed, and did it resolve with the target factor?
    F3: on divergent legs, did structure or narrative win? Pure read of the basket and the resolutions."""
    from .basket import event_basket
    b = event_basket(conn, round_id)
    res = latest_resolutions(conn, round_id)
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    natural_gate = [l for l in b["legs"] if l["arming_status"] in ("armed_dated", "gate_pass_undated")]
    syn_gate = [s for s in b["synthetics"] if s["arming_status"] in ("armed_dated", "gate_pass_undated")]
    # a synthetic "resolves with the target factor" when a sign call on it (position_id = synthetic id) hit
    syn_hits = syn_calls = 0
    for s in b["synthetics"]:
        for p in preds.values():
            if p.get("position_id") == s["synthetic_id"] and p["call_type"] == "sign" and p["id"] in res:
                syn_calls += 1
                syn_hits += res[p["id"]]["outcome"] == "hit"
    e4 = {"synthetics": len(b["synthetics"]), "synthetic_gate_pass": len(syn_gate), "natural_gate_pass": len(natural_gate),
          "gate_pass_where_natural_failed": bool(syn_gate) and not natural_gate,
          "synthetic_sign_calls": syn_calls, "synthetic_sign_hits": syn_hits,
          "arming_status": {s["synthetic_id"]: s["arming_status"] for s in b["synthetics"]}}
    f3_legs = []
    for l in b["legs"]:
        if not l["divergence"]:
            continue
        structure = [res[p["id"]]["outcome"] for p in preds.values()
                     if p["call_type"] == "sign" and p.get("position_id") in l.get("all_position_ids", l["position_ids"]) and p["id"] in res]
        f3_legs.append({"holder": l["holder"], "sign_at_lock": l["sign"], "revised_sign": l.get("revised_sign"),
                        "narrative": [{"narrative_sign": n["narrative_sign"], "channel_said_it": n["channel_said_it"]} for n in l["narrative"]],
                        "structure_call_outcomes": structure,
                        "structure_won": (any(o == "hit" for o in structure) if structure else None)})
    f3 = {"divergent_legs": len(f3_legs), "structure_won": sum(1 for x in f3_legs if x["structure_won"]),
          "narrative_won": sum(1 for x in f3_legs if x["structure_won"] is False), "legs": f3_legs}
    e4["synthetic_rules"] = {s["synthetic_id"]: {"rule": s["rule"], "cross_node": bool(s.get("cross_node"))} for s in b["synthetics"]}
    # v10 I3/K5: residual state per leg and the mirror's re-encode rate against the positive basket's
    from .risk import mirror_rates
    residual = {l["holder"] + " @ " + l["node"]: {"residual_state": l.get("residual_state"), "reencode": l.get("reencode"), "forcing_date": l.get("forcing_date")}
                for l in b["legs"]}
    try:
        k5 = mirror_rates(conn, round_id)
    except Exception as e:      # a round locked before v10 has no grid
        k5 = {"note": f"no grid: {type(e).__name__}"}
    k5["migrations"] = conn.execute("SELECT COUNT(*) FROM coverage_migrations WHERE round_id = ?", (round_id,)).fetchone()[0]
    return {"E4": e4, "F3": f3, "I3": {"legs": residual, "counts": {s: sum(1 for v in residual.values() if v["residual_state"] == s)
                                                                     for s in ("recovered", "unrecovered", "no_residual")}}, "K5": k5}


def write_notebook_rows(conn: sqlite3.Connection, round_id: str) -> list[str]:
    rows = notebook_rows_for(conn, round_id)
    ids = []
    for claim, row in rows.items():
        ids.append(append(conn, "notebook_rows", {"round_id": round_id, "claim": claim, "row_json": dumps(row)})["id"])
    return ids


def latest_notebook_rows(conn: sqlite3.Connection, round_id: str) -> dict:
    out = {}
    for r in conn.execute("SELECT claim, row_json FROM notebook_rows WHERE round_id = ? ORDER BY rowid", (round_id,)):
        out[r["claim"]] = loads(r["row_json"])
    return out


def supersede_resolution(conn: sqlite3.Connection, round_id: str, resolution) -> dict:
    require_state(conn, round_id, ("scored", "partially_scored"), "supersede a resolution")
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    r = _validate_resolutions(conn, round_id, preds, [resolution], require_all=False)[0]
    current = latest_resolutions(conn, round_id).get(r.prediction_id)
    if not current:
        raise ValidationError(f"prediction {r.prediction_id} has no resolution to supersede")
    if r.supersedes != current["id"]:
        raise ValidationError(f"supersedes must name the current resolution {current['id']} for prediction {r.prediction_id}")
    if not r.scorer_note.strip():
        raise ValidationError("a scorer_note explaining the correction is required")
    cls = classification(conn, round_id)
    ev_ids = {x["id"] for x in conn.execute("SELECT id FROM evidence WHERE round_id = ?", (round_id,))}
    pred = preds[r.prediction_id]
    if pred["factors"] and not r.factor_outcomes:
        # carry the existing factor resolutions forward; the composite is re-derived from them
        existing = latest_factor_resolutions(conn, pred["id"])
        r.factor_outcomes = [FactorOutcomeIn(factor_index=f["idx"], outcome=existing[f["id"]]["outcome"],
                                             observed=existing[f["id"]]["observed"], evidence_ids=existing[f["id"]]["evidence_ids"],
                                             note="carried forward") for f in pred["factors"] if f["id"] in existing]
    with transaction(conn):
        arose = {r.prediction_id: r.branch_arose} if pred.get("branches") else {}
        row = append(conn, "resolutions", _resolution_row(conn, r, pred, cls["round_class"], ev_ids,
                                                          branch_missed=_branch_missed(conn, pred, arose)))
        card = compute_scorecard(conn, round_id)
        append(conn, "scorecards", {"round_id": round_id, "scorecard_json": dumps(card), "null_call_weight": NULL_CALL_WEIGHT})
        lib = rebuild_library_stats(conn)
    card["library_rebuild"] = lib
    card["resolution_id"] = row["id"]
    card["superseded"] = current["id"]
    return card


# ---- B2: second scorer (C2, C3) ------------------------------------------------------------------

def second_scorer_view(conn: sqlite3.Connection, round_id: str, nodes: list[str] | None = None) -> dict:
    """v10 A5: generated per scoring session; contains only calls whose operator resolution is final (written) and not
    yet second-scored. The second scorer scores the same due batch."""
    require_state(conn, round_id, ("scored", "partially_scored"), "view as second scorer")
    keep = ("id", "call_type", "target", "claim", "carrier", "falsifier", "falsifier_window", "falsifier_window_end",
            "sign", "magnitude_rank", "lag_band", "baseline_claim", "locked_at", "aggregation", "branches", "conditional_on",
            "narrative_sign", "position_id", "carrier_status", "due_at", "effect_kind", "window", "space")
    final = latest_resolutions(conn, round_id)
    seconded = latest_second_scores(conn, round_id)
    preds = []
    for p in list_predictions(conn, round_id):
        if p["id"] not in final or p["id"] in seconded:
            continue
        d = {k: p[k] for k in keep}
        d["factors"] = [{k: f[k] for k in ("idx", "factor", "holder_name", "node", "estimate", "carrier", "falsifier", "binding", "against")}
                        for f in p["factors"]]
        d["cited_rules"] = []
        for rid in p["mechanism_ids"]:
            try:
                rule = resolve_rule(conn, rid)
                d["cited_rules"].append({k: rule[k] for k in ("id", "key", "rule_text", "forbids", "status", "carries", "trials_as_carried")})
            except Exception as exc:
                # v15 0b.4: v7 C2 put rule text in the blind view precisely because every mechanism dispute
                # dissolved once the second scorer could read the rule. A rule quietly omitted reintroduces that
                # dispute class with nobody aware it is back. Say which id could not be resolved.
                d["cited_rules"].append({"id": rid, "key": None, "rule_text": None, "forbids": None,
                                         "status": "unresolved", "carries": None, "trials_as_carried": None,
                                         "unresolved": f"{type(exc).__name__}: {exc}",
                                         "note": "this call cites a rule id the store cannot resolve; score its "
                                                 "mechanism_outcome unknown rather than assuming no rule was cited"})
        preds.append(d)
    ev = [{k: e[k] for k in ("id", "url", "title", "excerpt", "source_time", "knowable_from")} for e in list_evidence(conn, round_id)]
    from .db import get_row
    from .positions import positions_on_node
    rd = get_row(conn, "rounds", round_id, "round")
    evt = get_row(conn, "events", rd["event_id"], "event")
    if nodes is None:
        nodes = [r["node"] for r in conn.execute(
            "SELECT DISTINCT p.node FROM positions p WHERE p.recorded_at >= ? ORDER BY p.rowid", (rd["recorded_at"],))]
        if evt.get("node") and evt["node"] not in nodes:
            nodes.append(evt["node"])
    pos = {n: positions_on_node(conn, n) for n in nodes}
    for n in pos:
        for h in pos[n]["holders"]:
            h.pop("positions", None)
    return {"round_id": round_id, "event_text": evt["event_text"], "event_date": evt["event_date"],
            "predictions": preds, "evidence": ev, "positions": pos, "batch": "calls with a final operator resolution and no second score yet",
            "reveal_context": latest_reveal_context(conn, round_id),
            "instructions": "Score each prediction on its carrier against the evidence: outcome, mechanism_outcome, "
                            "baseline_outcome, evidence_ids, source_coverage (required on miss/unverified), scorer_note; on "
                            "decomposed calls score each factor in factor_outcomes and leave the composite to the harness. "
                            "On a map call with branches set branch_arose; rows conditional on another branch are untestable. "
                            "Narrative rows are scored on whether the named channel said it (hit) or not (miss), never on whether it was right. "
                            "mechanism_outcome means: did the cited rule (rule_text/forbids shown) operate, not whether the "
                            "claim's implied mechanism was right; use unknown when no rule is cited. Map claims are scored on "
                            "the claim text. For calls whose carrier is the positions store, use the positions section and the "
                            "reveal_context (what the operator's own store showed before lock). You are not shown the "
                            "operator's scores or notes."}


def second_score(conn: sqlite3.Connection, round_id: str, resolutions: list, scorer_session: str | None = None) -> dict:
    require_state(conn, round_id, ("scored", "partially_scored"), "second-score")
    preds = {p["id"]: p for p in list_predictions(conn, round_id)}
    parsed = _validate_resolutions(conn, round_id, preds, resolutions, require_all=False, model=SecondScoreIn)
    final = latest_resolutions(conn, round_id)
    for r in parsed:
        if r.prediction_id not in final:
            raise ValidationError(f"prediction {r.prediction_id} has no final operator resolution yet; the second scorer scores the same due batch")
    ev_ids = {x["id"] for x in conn.execute("SELECT id FROM evidence WHERE round_id = ?", (round_id,))}
    for r in parsed:
        if r.outcome in ("miss", "unverified") and not r.source_coverage:
            raise ValidationError(f"second score for {r.prediction_id}: source_coverage is required on {r.outcome}")
    with transaction(conn):
        for r in parsed:
            outcome, note = r.outcome, r.scorer_note
            pred = preds[r.prediction_id]
            if pred["factors"] and r.factor_outcomes:
                composite = _score_factors(conn, pred, r.factor_outcomes, "second", ev_ids)
                outcome = composite["outcome"]
                note = f"derivation={dumps(composite)}; " + note
            append(conn, "second_scores", {
                "prediction_id": r.prediction_id, "outcome": outcome, "mechanism_outcome": r.mechanism_outcome,
                "baseline_outcome": r.baseline_outcome, "evidence_ids": dumps(r.evidence_ids), "scorer_note": note,
                "source_coverage": r.source_coverage, "scorer_session": scorer_session,
            })
        # a new second score can open or close disputes: recompute the scorecard, the library and the notebook rows
        card = compute_scorecard(conn, round_id)
        append(conn, "scorecards", {"round_id": round_id, "scorecard_json": dumps(card), "null_call_weight": NULL_CALL_WEIGHT})
        rebuild_library_stats(conn)
        write_notebook_rows(conn, round_id)
    return score_disputes(conn, round_id)


def score_disputes(conn: sqlite3.Connection, round_id: str) -> dict:
    preds = list_predictions(conn, round_id)
    mine, theirs = latest_resolutions(conn, round_id), latest_second_scores(conn, round_id)
    rows, disputes = [], 0
    for p in preds:
        a, b = mine.get(p["id"]), theirs.get(p["id"])
        if not a or not b:
            rows.append({"prediction_id": p["id"], "target": p["target"], "status": "unscored_by_second" if a else "unscored"})
            continue
        diff = {k: (a[k], b[k]) for k in ("outcome", "mechanism_outcome", "baseline_outcome") if a[k] != b[k]}
        disputed = ("outcome" in diff or "mechanism_outcome" in diff) and a.get("scorer") != "human"
        disputes += disputed
        rows.append({"prediction_id": p["id"], "target": p["target"],
                     "status": "dispute" if disputed else ("ruled" if a.get("scorer") == "human" and diff else "agree"),
                     "differences": diff, "operator": {k: a[k] for k in ("outcome", "mechanism_outcome", "baseline_outcome")},
                     "second": {k: b[k] for k in ("outcome", "mechanism_outcome", "baseline_outcome")},
                     "resolved_by_human": a.get("scorer") == "human"})
    return {"round_id": round_id, "disputes": disputes, "compared": sum(1 for r in rows if r["status"] in ("dispute", "agree", "ruled")),
            "rows": rows, "next_step": "human breaks each dispute with nomad_resolution_supersede (scorer='human')" if disputes else None}


def calibration(conn: sqlite3.Connection, include_learning: bool = False) -> dict:
    """v11 A1: operator calibration over clean rounds only. Learning rounds are recorded and scored but never counted."""
    rows = conn.execute(
        "SELECT p.call_type, p.sign, r.outcome, r.mechanism_outcome, r.quarantined, c.round_class, p.space "
        "FROM predictions p JOIN resolutions r ON r.rowid = (SELECT rowid FROM resolutions WHERE prediction_id = p.id ORDER BY rowid DESC LIMIT 1) "
        "JOIN round_classification c ON c.round_id = p.round_id").fetchall()
    counted = [dict(r) for r in rows if include_learning or r["round_class"] == "clean"]
    def frac(items, pred):
        n = len(items)
        return {"n": n, "hits": sum(1 for x in items if pred(x)), "rate": (round(sum(1 for x in items if pred(x)) / n, 6) if n else None)}
    hit = lambda x: x["outcome"] == "hit"
    return {"include_learning": include_learning, "calls": len(counted),
            "excluded_learning": len(rows) - len(counted),
            "overall": frac(counted, hit),
            "by_call_type": {ct: frac([x for x in counted if x["call_type"] == ct], hit)
                             for ct in sorted({x["call_type"] for x in counted})},
            "absence_vs_occurrence": {"absence": frac([x for x in counted if x["call_type"] == "null" or (x["call_type"] == "sign" and x["sign"] == "0")], hit),
                                      "occurrence": frac([x for x in counted if x["call_type"] == "sign" and x["sign"] in ("+", "-")], hit)},
            "by_space": {sp: frac([x for x in counted if (x["space"] or "positive") == sp], hit) for sp in ("positive", "mirror")},
            "mechanism_right": frac([x for x in counted if x["mechanism_outcome"] != "unknown"], lambda x: x["mechanism_outcome"] == "right")}


def scorer_bias(conn: sqlite3.Connection) -> dict:
    """C4/C2: self-vs-second disagreement over clean rounds, operator's original resolution vs latest second score,
    in three classes. Only `lenient` (second says wrong/miss where self said right/hit) counts toward the self-scoring
    discount at the twenty-round review; `under_informed` (second unknown/unverified) is evidence of a thin blind view;
    `self_stricter` is the reverse."""
    rows = conn.execute(
        "SELECT p.id AS prediction_id, p.round_id FROM predictions p JOIN round_classification c ON c.round_id = p.round_id "
        "WHERE c.round_class = 'clean'").fetchall()
    counts: Counter = Counter()
    classes: Counter = Counter()
    compared = 0
    for r in rows:
        first = conn.execute("SELECT outcome, mechanism_outcome FROM resolutions WHERE prediction_id = ? ORDER BY rowid LIMIT 1",
                             (r["prediction_id"],)).fetchone()
        second = conn.execute("SELECT outcome, mechanism_outcome FROM second_scores WHERE prediction_id = ? ORDER BY rowid DESC LIMIT 1",
                              (r["prediction_id"],)).fetchone()
        if not first or not second:
            continue
        compared += 1
        for field, good, bad, vague in (("outcome", "hit", "miss", ("unverified", "untestable")),
                                        ("mechanism", "right", "wrong", ("unknown",))):
            a = first["outcome" if field == "outcome" else "mechanism_outcome"]
            b = second["outcome" if field == "outcome" else "mechanism_outcome"]
            if a == b:
                continue
            counts[f"{field} self_{a} second_{b}"] += 1
            if a == good and b == bad:
                classes["lenient"] += 1
            elif b in vague:
                classes["under_informed"] += 1
            elif b == good and a != good:
                classes["self_stricter"] += 1
            else:
                classes["other"] += 1
    return {"compared": compared, "directions": dict(counts),
            "lenient": classes["lenient"], "under_informed": classes["under_informed"],
            "self_stricter": classes["self_stricter"], "other": classes["other"],
            "counts_toward_discount": classes["lenient"],
            "note": "only `lenient` counts at the twenty-clean-round review of the self-scorer factor"}


# ---- programme ----------------------------------------------------------------------------

def programme_stats(conn: sqlite3.Connection, include_learning: bool = False, criteria_pass_only: bool = False,
                    tag: str | None = None) -> dict:
    """v9 F: `tag` filters to one round tag (lag_test | weather | late_headline | learning); the lag-hypothesis stats read
    lag_test only. Arming is reported as three counts per tag, with scheduled-facts coverage and fetch-path health."""
    from .predicates import ARMING_STATUSES, armed_legs, status_counts
    from .rounds import round_tag
    from .scheduled import coverage
    from .carriers import path_health
    rows_all = [dict(r) for r in conn.execute(
        "SELECT s.round_id, s.state, c.round_class, c.contamination, r.event_id FROM round_state s "
        "JOIN round_classification c ON c.round_id = s.round_id JOIN rounds r ON r.id = s.round_id "
        "WHERE s.state = 'scored' ORDER BY s.round_id")]
    for r in rows_all:
        r["criteria_pass"] = current_criteria(conn, r["event_id"])["criteria_pass"]
        t = round_tag(conn, r["round_id"])
        r["tag"] = t["tag"] if t else None
    counted = [r for r in rows_all if (include_learning or r["round_class"] == "clean") and (not criteria_pass_only or r["criteria_pass"])
               and (tag is None or r["tag"] == tag)]
    rows, armed, misreads, disputes, armed_legs_total = [], 0, 0, 0, 0
    arming_by_tag: dict[str, dict] = {}
    for r in counted:
        card = latest_scorecard(conn, r["round_id"]) or compute_scorecard(conn, r["round_id"])
        if card["arming_claimed"] and card["arming_observed"]:
            armed += 1
        misreads += card.get("misreads") or 0
        disputes += card.get("disputes_pending") or 0
        armed_legs_total += card.get("armed_leg_count") or 0
        sc = status_counts(armed_legs(conn, r["round_id"]))
        agg = arming_by_tag.setdefault(r["tag"] or "untagged", {"rounds": 0, **{s: 0 for s in ARMING_STATUSES}})
        agg["rounds"] += 1
        for k, v in sc.items():
            agg[k] += v
        rows.append({"round_id": r["round_id"], "round_class": r["round_class"], "contamination": r["contamination"],
                     "criteria_pass": r["criteria_pass"], "tag": r["tag"], "arming_status_counts": sc,
                     **{k: card.get(k) for k in ("outcome_score", "mechanism_score", "baseline_score", "edge_vs_baseline",
                                                 "map_score", "misreads", "disputes_pending", "armed_leg_count", "null_called",
                                                 "arming_claimed", "arming_observed")}})
    ms = [r["mechanism_score"] for r in rows if r["mechanism_score"] is not None]
    voided = conn.execute("SELECT COUNT(*) FROM round_state WHERE state = 'void'").fetchone()[0]
    from .basket import divergence_stats
    divergence = divergence_stats(conn, [r["round_id"] for r in counted])
    total = {k: sum(a[k] for a in arming_by_tag.values()) for k in ARMING_STATUSES}
    from .rounds import mix_status
    k5_rows = {}
    for r in counted:
        nb = latest_notebook_rows(conn, r["round_id"]).get("K5") or {}
        if "positive" in nb:
            k5_rows[r["round_id"]] = {"positive": nb["positive"], "mirror": nb["mirror"], "migrations": nb.get("migrations")}
    migr = conn.execute("SELECT round_id, COUNT(*) AS n FROM coverage_migrations GROUP BY round_id").fetchall()
    from .surviving import null_breakdown
    nb_all = null_breakdown(conn)
    return {
        "mix": mix_status(conn),
        "k5_by_round": k5_rows,
        # v13 A5: an absence call on a leg where an eliminator fired is a non-position, not a win. The 17-of-18 record
        # is reported split, because only the surviving half ever had anything at stake.
        "null_breakdown": {"counts": nb_all["counts"], "hits": nb_all["hits"], "absence_calls": nb_all["absence_calls"]},
        "coverage_migrations_by_round": {r["round_id"]: r["n"] for r in migr},
        "include_learning": include_learning, "criteria_pass_only": criteria_pass_only, "tag": tag,
        "arming_by_tag": arming_by_tag, "arming_counts": total,
        "rounds_by_tag": {t: sum(1 for r in rows_all if r["tag"] == t) for t in ("lag_test", "weather", "late_headline", "learning")},
        "scheduled_facts_coverage": coverage(conn),
        "fetch_path_health": path_health(conn),
        "notebook_rows": {r["round_id"]: latest_notebook_rows(conn, r["round_id"]) for r in counted},
        "rounds_scored": len(counted),
        "rounds_scored_clean": sum(1 for r in rows_all if r["round_class"] == "clean"),
        "rounds_scored_clean_criteria_pass": sum(1 for r in rows_all if r["round_class"] == "clean" and r["criteria_pass"]),
        "rounds_scored_learning": sum(1 for r in rows_all if r["round_class"] != "clean"),
        "rounds_void": voided,
        "arming_rate": (round(armed / len(counted), 6) if counted else None), "rounds_armed": armed,
        "armed_legs_total": armed_legs_total, "misreads_total": misreads, "disputes_pending_total": disputes,
        "mechanism_score": {"mean": (round(sum(ms) / len(ms), 6) if ms else None),
                            "min": (min(ms) if ms else None), "max": (max(ms) if ms else None), "values": ms},
        "narrative_divergence": divergence,
        "rounds": rows, "null_call_weight": NULL_CALL_WEIGHT, "validation_threshold": config.VALIDATION_THRESHOLD,
    }
