"""T0 counter (§4.9): criteria checklist + arming predicates per candidate, counted over a window."""
import sqlite3

from .db import append
from .errors import ValidationError
from .util import dumps


def submit_candidate(conn: sqlite3.Connection, event_id: str, window_label: str, criteria_pass: bool,
                     arming_pass: bool | None = None, arming_pass_pair: bool | None = None,
                     listed_party: str | None = None, pair_holders: list[str] | None = None,
                     carrier: str | None = None, micro_macro_note: str | None = None) -> dict:
    if not event_id.strip() or not window_label.strip():
        raise ValidationError("event_id and window_label are required")
    row = append(conn, "t0_candidates", {
        "event_id": event_id, "window_label": window_label, "criteria_pass": criteria_pass,
        "arming_pass_single": arming_pass, "arming_pass_pair": arming_pass_pair,
        "listed_party": listed_party, "pair_holders": dumps(pair_holders) if pair_holders else None,
        "carrier": carrier, "micro_macro_note": micro_macro_note,
    })
    return {"candidate_id": row["id"], "window_label": window_label}


def count(conn: sqlite3.Connection, window_label: str) -> dict:
    from .predicates import armed_legs, status_counts
    q = lambda sql: conn.execute(sql, (window_label,)).fetchone()[0]
    # D5: armed legs over the window: candidates whose event_id is an event with a round; v9 E: three counts
    legs = 0
    counts = {"armed_dated": 0, "gate_pass_undated": 0, "gate_fail": 0, "unchecked": 0}
    for r in conn.execute("SELECT DISTINCT r.id FROM t0_candidates t JOIN rounds r ON r.event_id = t.event_id WHERE t.window_label = ?",
                          (window_label,)):
        al = armed_legs(conn, r["id"])
        legs += sum(1 for l in al if l["armed"])
        for k, v in status_counts(al).items():
            counts[k] = counts.get(k, 0) + v
    return {
        "armed_legs": legs, "arming_status_counts": counts,
        "window_label": window_label,
        "candidates": q("SELECT COUNT(*) FROM t0_candidates WHERE window_label = ?"),
        "distinct_events": q("SELECT COUNT(DISTINCT event_id) FROM t0_candidates WHERE window_label = ?"),
        "criteria_pass": q("SELECT COUNT(*) FROM t0_candidates WHERE window_label = ? AND criteria_pass = 1"),
        "arming_pass": q("SELECT COUNT(*) FROM t0_candidates WHERE window_label = ? AND arming_pass_single = 1"),
        "arming_pass_pair": q("SELECT COUNT(*) FROM t0_candidates WHERE window_label = ? AND arming_pass_pair = 1"),
        "both_pass": q("SELECT COUNT(*) FROM t0_candidates WHERE window_label = ? AND criteria_pass = 1 AND arming_pass_single = 1"),
        "distinct_triples": q("SELECT COUNT(*) FROM (SELECT DISTINCT event_id, listed_party, carrier "
                              "FROM t0_candidates WHERE window_label = ?)"),
    }
