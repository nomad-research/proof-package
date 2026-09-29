"""Round state machine (§5) plus intake, reveal context (B5), touched set (B3), decomposition at lock (B1/B2/B4)."""
import re
import sqlite3
from datetime import date, timedelta
from urllib.parse import urlparse

from . import config
from .db import append, chain_heads, get_row, insert_mutable, transaction
from .errors import NotFound, StateError, ValidationError
from .models import PredictionIn, TouchedSetIn
from .util import dumps, loads, now_iso, sha256_hex

STATES = ("created", "locked", "open", "partially_scored", "scored", "void")
TAGS = ("lag_test", "weather", "late_headline", "learning")
CAP_TAGS = ("weather", "late_headline")
CAP_LOOKBACK = 3          # v9 B4 default; v10 B2 sets settings cap_lookback = 1 (at most one weather/late_headline in any two consecutive admitted)
Q9_SUSPEND_AFTER = 3      # v9 B5: consecutive Q9 fails that suspend the selector
# v11 §0.4: `skip` records a candidate passed over without assessing it, so the selector never has to manufacture a
# failing question to explain a human choice.
FAILING_QS = ("Q1a", "Q1b", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "cap", "skip")
EVENT_KINDS = ("fire", "explosion", "leak", "spill", "strike", "closure", "outage", "ban", "recall", "insolvency",
               "rule_change", "other")
_KIND_WORDS = {
    "explosion": ("explosion", "explod", "blast"), "fire": ("fire", "blaze", "brand"), "leak": ("leak", "lek"),
    "spill": ("spill",), "strike": ("strike", "industrial action", "walkout"), "closure": ("closure", "closes", "closed", "shut"),
    "outage": ("outage", "trip", "shutdown"), "ban": ("ban", "embargo", "sanction"), "recall": ("recall",),
    "insolvency": ("insolven", "bankrupt", "administration"), "rule_change": ("rule", "regulation", "directive", "tariff"),
}


# v11 §C: Q3 is structural — a price event makes the operator's proposal price-derived at the root. Detected as well
# as asked, because it is the one gate a mis-typed prompt can slip through.
PRICE_EVENT = re.compile(
    r"\b(shares?|stock|equit\w+|index|indices|prices?|yields?|spreads?|futures|bonds?|currenc\w+|rates?)\b[^.]{0,60}?"
    r"\b(ros[eu]|fell|fall\w*|jump\w*|plunge\w*|slump\w*|surge\w*|drop\w*|rall\w*|climb\w*|slid|sank|soar\w*|"
    r"gain\w*|lost|tumbl\w*|spike\w*|hit a (record|high|low)|rise|rises|rose)\b|"
    r"\b(ros[eu]|fell|jumped|plunged|slumped|surged|dropped|rallied|climbed|tumbled|spiked)\b[^.]{0,40}?"
    r"\b(percent|per cent|%|basis points|bps)\b", re.I)


def looks_like_price_event(text: str) -> bool:
    return bool(PRICE_EVENT.search(text or ""))


def event_hash(event_text: str, event_date: str) -> str:
    return sha256_hex(f"{event_text}||{event_date}")


def derive_event_kind(text: str) -> str:
    low = text.lower()
    for kind in ("explosion", "fire", "leak", "spill", "strike", "closure", "outage", "recall", "insolvency", "ban", "rule_change"):
        if any(w in low for w in _KIND_WORDS[kind]):
            return kind
    return "other"


def _hint(state: str) -> str:
    return {
        "created": "no predictions are locked yet. Call nomad_lock_predictions with at least one prediction first; the firewall requires the lock before any retrieval.",
        "locked": "predictions are locked but retrieval is not open. Call nomad_open_retrieval to open the round.",
        "open": "retrieval is open and predictions are frozen. Add evidence with nomad_add_evidence, then score calls as they fall due (nomad_score_call / nomad_score_round).",
        "partially_scored": "some calls are scored; the rest wait for their due_at. nomad_calls_due lists them; nomad_close_round expires what is past due.",
        "scored": "the round is scored and frozen entirely. Start a new round with nomad_submit_event.",
        "void": "the round was voided; nothing further is accepted. Start a new round with nomad_submit_event.",
    }[state]


# ---- operator identity and clean window (A2, A3) --------------------------------------

def model_cutoff(conn: sqlite3.Connection, model_id: str) -> str | None:
    r = conn.execute("SELECT cutoff_date FROM model_cutoffs WHERE model_id = ?", (model_id,)).fetchone()
    return r["cutoff_date"] if r else None


def model_cutoff_set(conn: sqlite3.Connection, model_id: str, cutoff_date: str, source: str | None = None) -> dict:
    date.fromisoformat(cutoff_date)
    if conn.execute("SELECT 1 FROM model_cutoffs WHERE model_id = ?", (model_id,)).fetchone():
        conn.execute("UPDATE model_cutoffs SET cutoff_date = ?, source = ? WHERE model_id = ?", (cutoff_date, source, model_id))
        return {"model_id": model_id, "cutoff_date": cutoff_date, "updated": True}
    insert_mutable(conn, "model_cutoffs", {"model_id": model_id, "cutoff_date": cutoff_date, "source": source})
    return {"model_id": model_id, "cutoff_date": cutoff_date, "updated": False}


def model_cutoffs_list(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT model_id, cutoff_date, source, created_at FROM model_cutoffs ORDER BY model_id")]


def event_window(conn: sqlite3.Connection, operator_model: str | None = None, today: date | None = None) -> dict:
    from .risk import setting
    operator = operator_model or config.operator_model()
    cutoff = model_cutoff(conn, operator)
    today = today or date.today()
    lag = int(setting(conn, "clean_lag_days", config.CLEAN_WINDOW_LAG_DAYS))     # v10 A1: 0 once set; [cutoff + 1, today]
    end = today - timedelta(days=lag)
    if not cutoff:
        return {"operator": operator, "cutoff": None, "window_start": None, "window_end": end.isoformat(),
                "today": today.isoformat(), "known": False,
                "note": f"model {operator!r} is not in model_cutoffs; rounds are learning (q2_unknown) until the human sets it "
                        "(nomad-harness model-cutoff set <model_id> <YYYY-MM-DD>)"}
    start = date.fromisoformat(cutoff) + timedelta(days=1)
    return {"operator": operator, "cutoff": cutoff, "window_start": start.isoformat(), "window_end": end.isoformat(),
            "today": today.isoformat(), "known": True, "lag_days": lag}


# ---- state helpers ---------------------------------------------------------------------

def round_state(conn: sqlite3.Connection, round_id: str) -> str:
    r = conn.execute("SELECT state FROM round_state WHERE round_id = ?", (round_id,)).fetchone()
    if not r:
        raise NotFound(f"no round with id {round_id!r}; nomad_submit_event returns the round_id")
    return r["state"]


def classification(conn: sqlite3.Connection, round_id: str) -> dict:
    r = conn.execute("SELECT * FROM round_classification WHERE round_id = ?", (round_id,)).fetchone()
    if not r:
        raise NotFound(f"no round with id {round_id!r}")
    return dict(r)


def require_state(conn: sqlite3.Connection, round_id: str, allowed: tuple[str, ...], action: str) -> str:
    state = round_state(conn, round_id)
    if state not in allowed:
        raise StateError(
            f"cannot {action}: round {round_id} is in state '{state}' (needs {' or '.join(allowed)}). {_hint(state)}")
    return state


def transition(conn: sqlite3.Connection, round_id: str, from_state: str | None, to_state: str, reason: str) -> dict:
    return append(conn, "round_transitions", {"round_id": round_id, "from_state": from_state, "to_state": to_state, "reason": reason})


def classify(conn: sqlite3.Connection, round_id: str, round_class: str, contamination: str, reason: str) -> dict:
    latest = conn.execute("SELECT id FROM round_classifications WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    return append(conn, "round_classifications", {
        "round_id": round_id, "round_class": round_class, "contamination": contamination, "reason": reason,
        "supersedes": latest["id"] if latest else None})


# ---- intake ------------------------------------------------------------------------------

def _parse_criteria(criteria_json) -> dict:
    if isinstance(criteria_json, str):
        try:
            criteria = loads(criteria_json)
        except ValueError:
            raise ValidationError("criteria_json must be a JSON object of Q1..Q9 -> pass|fail|unknown")
    else:
        criteria = criteria_json
    if not isinstance(criteria, dict) or not criteria:
        raise ValidationError("criteria_json must be a non-empty object of Q1..Q9 -> pass|fail|unknown")
    bad = {k: v for k, v in criteria.items()
           if not isinstance(v, str) or not v.strip().lower().startswith(("pass", "fail", "unknown"))}
    if bad:
        raise ValidationError(f"criteria values must start with pass|fail|unknown (a note may follow); got {bad}")
    return criteria


def criteria_pass(criteria: dict) -> bool:
    return not any(str(v).strip().lower().startswith("fail") for v in criteria.values())


# ---- v9 B3/B4/B5: tags, cap, selector -------------------------------------------------------------------------------

def _val(v) -> str:
    return str(v or "unknown").strip().split(":")[0].strip().lower()


def _basis(v) -> str | None:
    s = str(v or "")
    return s.split(":", 1)[1].strip() if ":" in s else None


def compute_tag(q1a: str, q1b: str, contamination: str) -> str:
    if contamination != "none":
        return "learning"
    if q1b == "fail":
        return "weather"
    if q1a == "fail":
        return "late_headline"
    return "lag_test"


def round_tag(conn: sqlite3.Connection, round_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM round_tags WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["q1b_detail"] = loads(d["q1b_detail"]) if d.get("q1b_detail") else None
    d["tags"] = [d["tag"]] + (["headline"] if d.get("size_band") == "headline" else [])
    return d


def list_tags(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM round_tags WHERE round_id = ? ORDER BY rowid", (round_id,))]


def write_tag(conn: sqlite3.Connection, round_id: str, tag: str, q1a: str, q1a_basis: str | None, q1b: str,
              q1b_detail: dict | None, q2: str, reason: str, cap_override: str | None = None, size_band: str | None = None) -> dict:
    if tag not in TAGS:
        raise ValidationError(f"tag must be one of {TAGS}")
    latest = conn.execute("SELECT id FROM round_tags WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    row = append(conn, "round_tags", {"round_id": round_id, "tag": tag, "q1a": q1a, "q1a_basis": q1a_basis, "q1b": q1b,
                                      "q1b_detail": dumps(q1b_detail) if q1b_detail else None, "q2": q2, "size_band": size_band,
                                      "cap_override": cap_override, "reason": reason, "supersedes": latest["id"] if latest else None})
    return {"tag_id": row["id"], "round_id": round_id, "tag": tag, "supersedes": row["supersedes"]}


def retag(conn: sqlite3.Connection, round_id: str, tag: str, reason: str, q1a: str | None = None, q1a_basis: str | None = None,
          q1b: str | None = None, q1b_detail: dict | None = None) -> dict:
    """Human re-tag (§0.2): a new round_tags row with supersedes. Tags are immutable at intake; this is the ledger's correction path."""
    round_state(conn, round_id)
    if not reason.strip():
        raise ValidationError("a reason is required to re-tag a round")
    prev = round_tag(conn, round_id) or {}
    cls = classification(conn, round_id)
    q2 = "pass" if cls["contamination"] == "none" else cls["contamination"]
    return write_tag(conn, round_id, tag, q1a or prev.get("q1a") or "unknown", q1a_basis or prev.get("q1a_basis"),
                     q1b or prev.get("q1b") or "unknown", q1b_detail or prev.get("q1b_detail"), q2, reason, size_band=prev.get("size_band"))


def cap_lookback(conn: sqlite3.Connection) -> int:
    from .risk import setting
    return int(setting(conn, "cap_lookback", CAP_LOOKBACK))


def recent_admitted_tags(conn: sqlite3.Connection, n: int | None = None) -> list[dict]:
    """Tags of the last n admitted (non-void) rounds, newest first."""
    n = n or cap_lookback(conn)
    out = []
    for r in conn.execute("SELECT r.id FROM rounds r JOIN round_state s ON s.round_id = r.id WHERE s.state != 'void' ORDER BY r.rowid DESC"):
        t = round_tag(conn, r["id"])
        if t:
            out.append({"round_id": r["id"], "tag": t["tag"]})
        if len(out) >= n:
            break
    return out


def cap_status(conn: sqlite3.Connection, tag: str) -> dict:
    n = cap_lookback(conn)
    recent = recent_admitted_tags(conn, n)
    blocked = tag in CAP_TAGS and any(t["tag"] in CAP_TAGS for t in recent)
    return {"tag": tag, "recent": recent, "cap_applies": tag in CAP_TAGS, "blocked": blocked,
            "rule": f"at most one weather/late_headline in any {n + 1} consecutive admitted rounds"}


def mix_status(conn: sqlite3.Connection) -> dict:
    """v10 B3: the required mix over the freeze (headline >= 4, lag_test >= 3 of the next seven), tracked from the freeze start."""
    from .risk import setting
    start = setting(conn, "freeze_started_at")
    if not start:
        return {"freeze": False, "note": "no freeze declared (settings freeze_started_at)"}
    rows = [r for r in conn.execute("SELECT r.id, r.recorded_at FROM rounds r JOIN round_state s ON s.round_id = r.id WHERE s.state != 'void' AND r.recorded_at >= ? ORDER BY r.rowid", (start,))]
    counts = {"headline": 0, "lag_test": 0, "weather": 0, "late_headline": 0, "learning": 0}
    for r in rows:
        t = round_tag(conn, r["id"]) or {}
        counts[t.get("tag") or "learning"] = counts.get(t.get("tag") or "learning", 0) + 1
        if t.get("size_band") == "headline":
            counts["headline"] += 1
    admitted = len(rows)
    remaining = max(0, config.FREEZE_ROUNDS - admitted)
    needed = {k: max(0, v - counts.get(k, 0)) for k, v in config.REQUIRED_MIX.items()}
    return {"freeze": True, "freeze_started_at": start, "admitted_under_freeze": admitted, "remaining": remaining, "counts": counts,
            "required": config.REQUIRED_MIX, "still_needed": needed,
            "warning": (f"remaining {remaining} round(s) cannot meet the mix: still needed {needed}" if sum(needed.values()) > remaining else None)}


def reject_event(conn: sqlite3.Connection, source: str, event_date: str, event_text: str, failing_q: str,
                 note: str | None = None, start_date: str | None = None, round_id: str | None = None) -> dict:
    """B5: the selector writes every skipped event with the question it failed (or 'cap')."""
    if failing_q not in FAILING_QS:
        raise ValidationError(f"failing_q must be one of {FAILING_QS}")
    if not source.strip() or not event_text.strip():
        raise ValidationError("source and event_text are required")
    date.fromisoformat(event_date)
    row = append(conn, "event_rejections", {"source": source.strip(), "start_date": start_date, "event_date": event_date,
                                            "event_text": event_text.strip(), "failing_q": failing_q, "note": note, "round_id": round_id})
    return {"rejection_id": row["id"], "source": source.strip(), "event_date": event_date, "failing_q": failing_q}


def selection_window_open(conn: sqlite3.Connection, source: str, start_date: str, note: str | None = None) -> dict:
    """B5/Q9: fix the source and start date before enumerating; written to the ledger."""
    if not source.strip():
        raise ValidationError("source is required")
    date.fromisoformat(start_date)
    row = append(conn, "selection_windows", {"source": source.strip(), "start_date": start_date, "note": note})
    return {"window_id": row["id"], "source": source.strip(), "start_date": start_date}


def _window(conn: sqlite3.Connection, source: str, start_date: str | None) -> dict | None:
    if not start_date:
        return None
    r = conn.execute("SELECT * FROM selection_windows WHERE source = ? AND start_date = ? ORDER BY rowid DESC LIMIT 1",
                     (source.strip(), start_date)).fetchone()
    return dict(r) if r else None


def window_rejections(conn: sqlite3.Connection, source: str, start_date: str | None, since: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM event_rejections WHERE source = ? AND round_id IS NULL", [source.strip()]
    if start_date:
        sql += " AND (start_date = ? OR start_date IS NULL)"
        args.append(start_date)
    if since:
        sql += " AND recorded_at >= ?"
        args.append(since)
    return [dict(r) for r in conn.execute(sql + " ORDER BY rowid", args)]


def selector_status(conn: sqlite3.Connection, key: str = "default") -> dict:
    r = conn.execute("SELECT * FROM selector WHERE key = ?", (key,)).fetchone()
    if not r:
        insert_mutable(conn, "selector", {"key": key, "consecutive_q9_fails": 0, "suspended": 0})
        r = conn.execute("SELECT * FROM selector WHERE key = ?", (key,)).fetchone()
    d = dict(r)
    d["suspended"] = bool(d["suspended"])
    return d


def selector_record_q9(conn: sqlite3.Connection, q9: str, key: str = "default") -> dict:
    st = selector_status(conn, key)
    fails = st["consecutive_q9_fails"] + 1 if q9 == "fail" else (0 if q9 == "pass" else st["consecutive_q9_fails"])
    suspended = st["suspended"] or fails >= Q9_SUSPEND_AFTER
    conn.execute("UPDATE selector SET consecutive_q9_fails = ?, suspended = ?, suspended_at = CASE WHEN ? AND suspended_at IS NULL THEN ? ELSE suspended_at END WHERE key = ?",
                 (fails, int(suspended), int(suspended and not st["suspended"]), now_iso(), key))
    return selector_status(conn, key)


def selector_clear(conn: sqlite3.Connection, reason: str, key: str = "default") -> dict:
    if not reason.strip():
        raise ValidationError("a reason is required to clear the selector")
    selector_status(conn, key)
    conn.execute("UPDATE selector SET suspended = 0, consecutive_q9_fails = 0, cleared_at = ?, cleared_reason = ? WHERE key = ?",
                 (now_iso(), reason.strip(), key))
    return selector_status(conn, key)


def _compute_q9(conn: sqlite3.Connection, criteria: dict, source: str, selection_start_date: str | None,
                window_events_seen: int | None, rejections_written: int) -> tuple[str, dict]:
    """Q9 = fail when the selector fixed a window and wrote no rejections for a window that plainly had more than one event."""
    given = _val(criteria.get("Q9"))
    win = _window(conn, source, selection_start_date)
    if not win:
        text = criteria.get("Q9") or "unknown: no selection window on the ledger (nomad_selection_window before enumerating)"
        return _val(text), {"window": None, "rejections": rejections_written, "text": str(text)}
    n = rejections_written + len(window_rejections(conn, source, selection_start_date, win["recorded_at"]))
    if n > 0:
        text = f"pass: computed; selection window {selection_start_date} on {source}, {n} rejection(s) logged with failing questions"
    elif window_events_seen == 1:
        text = f"pass: computed; selection window {selection_start_date} on {source}: the selector declared a single-event window"
    else:
        seen = "an unstated number of" if window_events_seen is None else str(window_events_seen)
        text = f"fail: computed; selection window {selection_start_date} on {source} had {seen} events and no rejection was written"
    if given == "fail":
        text = "fail: " + str(criteria.get("Q9")).split(":", 1)[-1].strip() + " (also " + text + ")"
    return _val(text), {"window": win["id"], "rejections": n, "text": text, "events_seen": window_events_seen}


def intake_dry_run(conn: sqlite3.Connection, event_text: str, event_date: str, criteria_json, node: str | None = None,
                   node_kind: str | None = None, operator_model: str | None = None, today: date | None = None,
                   registries: bool = True, fetch=None, q1b_override: dict | None = None) -> dict:
    """What intake would compute, without writing: Q1b, Q2, Q7 density, tag, cap. The selector runs this per candidate."""
    from .carriers import open_for_kind
    from .history import q1b as compute_q1b
    criteria = _parse_criteria(criteria_json)
    win = event_window(conn, operator_model, today)
    evd = date.fromisoformat(event_date)
    contamination = ("q2_unknown" if win["cutoff"] is None else "q2_fail" if evd <= date.fromisoformat(win["cutoff"]) else "none")
    q1a_raw = criteria.get("Q1a") or criteria.get("Q1") or "unknown"
    kw = {"fetch": fetch} if fetch else {}
    q1b = (compute_q1b(conn, node, event_date, node_kind, registries, override=q1b_override, **kw) if node
           else {"value": "unknown", "text": "unknown: no node named at intake", "in_90d": None, "in_12m": None, "incidents": [], "registries": []})
    tag = compute_tag(_val(q1a_raw), q1b["value"], contamination)
    density = open_for_kind(conn, node_kind) if node_kind else None
    return {"event_date": event_date, "q1a": _val(q1a_raw), "q1a_basis": _basis(q1a_raw), "q1b": q1b, "q2": contamination,
            "in_clean_window": bool(win["window_start"]) and win["window_start"] <= event_date <= win["window_end"],
            "tag": tag, "cap": cap_status(conn, tag), "carrier_density": density, "selector": selector_status(conn)}


def submit_event(conn: sqlite3.Connection, event_text: str, event_date: str, source: str, selection_rule: str,
                 rejected_before: int, criteria_json, node_recent_incidents: str | None = None,
                 round_class: str | None = None, operator_model: str | None = None, today: date | None = None,
                 node: str | None = None, event_kind: str | None = None, node_kind: str | None = None,
                 rejections: list | None = None, q1b_override: dict | None = None, cap_override: str | None = None,
                 selection_start_date: str | None = None, window_events_seen: int | None = None,
                 registries: bool = True, fetch=None, size_band: str | None = None, via_enumeration: bool = False,
                 candidate_id: str | None = None) -> dict:
    from .carriers import open_for_kind
    from .history import q1b as compute_q1b
    from .risk import setting
    if not event_text.strip() or "\n" in event_text.strip():
        raise ValidationError("event_text must be one non-empty line")
    v10 = bool(setting(conn, "freeze_started_at"))
    if size_band is not None and size_band not in config.SIZE_BANDS:
        raise ValidationError(f"size_band must be one of {config.SIZE_BANDS}")
    if v10 and not size_band:
        raise ValidationError("v11 B1: size_band is required at intake as a tag (underread | headline | trivia)")
    sel = selector_status(conn)
    if sel["suspended"]:
        raise ValidationError(f"selector suspended after {sel['consecutive_q9_fails']} consecutive Q9 fails (since {sel['suspended_at']}); "
                              "the human clears it with nomad_selector_clear before any further intake")
    density = open_for_kind(conn, node_kind) if node_kind else None
    rejections = [str(x) for x in (rejections or [])]
    try:
        evd = date.fromisoformat(event_date)
    except ValueError:
        raise ValidationError("event_date must be an ISO date (YYYY-MM-DD)")
    criteria = _parse_criteria(criteria_json)
    if rejected_before < 0:
        raise ValidationError("rejected_before must be >= 0")
    # v11 §C: only Q3 (not a price event) and Q8 (clean prompt) refuse here; Q9 is checked once the class is known.
    if v10:
        if _val(criteria.get("Q3")) == "fail":
            reject_event(conn, source, event_date, event_text, "Q3", str(criteria.get("Q3")), start_date=selection_start_date)
            raise ValidationError("refused (Q3): not a world event; rejection written")
        if looks_like_price_event(event_text) and _val(criteria.get("Q3")) != "pass":
            reject_event(conn, source, event_date, event_text, "Q3", "computed: the prompt reads as a price move, not a world event",
                         start_date=selection_start_date)
            raise ValidationError("refused (Q3): the prompt reads as a price move ('shares fell', 'index jumped'). Price is an "
                                  "outcome, never a proposer; if this really is a world event, answer Q3 'pass: <why>' explicitly")
        if _val(criteria.get("Q8")) == "fail":
            reject_event(conn, source, event_date, event_text, "Q8", str(criteria.get("Q8")), start_date=selection_start_date)
            raise ValidationError("refused (Q8): the prompt is not clean; rewrite it as bare event and date")
    if rejections and rejected_before == 0:
        rejected_before = len(rejections)
    if density and not density["qualifies"] and not str(criteria.get("Q7", "")).lower().startswith("fail"):
        criteria["Q7"] = f"fail: computed at intake; no open carrier for node kind {node_kind!r} in the registry"
    if round_class not in (None, "learning"):
        raise ValidationError("round_class may only be passed as 'learning'; 'clean' is computed, never claimed")
    if event_kind and event_kind not in EVENT_KINDS:
        raise ValidationError(f"event_kind must be one of {EVENT_KINDS}")
    event_kind = event_kind or derive_event_kind(event_text)

    win = event_window(conn, operator_model, today)
    operator, cutoff = win["operator"], win["cutoff"]
    if cutoff is None:
        contamination = "q2_unknown"
        criteria["Q2"] = f"unknown: computed; operator {operator!r} has no entry in model_cutoffs"
    elif evd <= date.fromisoformat(cutoff):
        contamination = "q2_fail"
        criteria["Q2"] = f"fail: computed; event {event_date} is on or before operator cutoff {cutoff} ({operator})"
    else:
        contamination = "none"
        criteria["Q2"] = f"pass: computed; event {event_date} is after operator cutoff {cutoff} ({operator})"

    # v9 B2/B3: Q1a from the human (with basis), Q1b computed, tag derived
    explicit_q1a = "Q1a" in criteria
    q1a_raw = criteria.get("Q1a") or criteria.get("Q1") or "unknown: not answered"
    criteria.setdefault("Q1a", q1a_raw)
    q1a, q1a_basis = _val(q1a_raw), _basis(q1a_raw)
    if explicit_q1a and q1a in ("pass", "fail") and not q1a_basis:
        raise ValidationError("Q1a (first traversal at the event) needs a basis after the verdict: 'pass: <what the 30-day window search showed>'")
    kw = {"fetch": fetch} if fetch else {}
    try:
        q1b = (compute_q1b(conn, node, event_date, node_kind, registries, override=q1b_override, **kw) if node
               else {"value": "unknown", "text": "unknown: no node named at intake, so node-level first traversal was not computed", "in_90d": None, "in_12m": None, "incidents": [], "registries": [], "override": None})
    except ValueError as e:
        raise ValidationError(str(e))
    criteria["Q1b"] = q1b["text"]
    tag = compute_tag(q1a, q1b["value"], contamination)
    cap = cap_status(conn, tag)      # v11 §C: the cap warns, it no longer refuses; first traversal is a tag
    # v9 B5 / v11 §C: Q9 passes through the enumeration path, or on a fixed window whose rejections are on the ledger.
    q9, q9_detail = _compute_q9(conn, criteria, source, selection_start_date, window_events_seen, len(rejections))
    if v10 and via_enumeration:
        q9, q9_detail = "pass", {**q9_detail, "text": f"pass: computed; accepted through nomad_enumerate / nomad_select_next (candidate {candidate_id})"}
    elif v10 and q9 != "pass":
        q9, q9_detail = "fail", {**q9_detail, "text": "fail: computed; the selection is not verifiable: the event came neither through the "
                                                      "enumeration path nor from a fixed window whose rejections are on the ledger. " + q9_detail["text"]}
    criteria["Q9"] = q9_detail["text"]
    if size_band:
        criteria["Q5"] = f"{'pass' if size_band != 'trivia' else 'fail'}: size band {size_band}" + (f"; {criteria['Q5']}" if criteria.get("Q5") else "")

    in_window = bool(win["window_start"]) and win["window_start"] <= event_date <= win["window_end"]
    if contamination == "none" and not in_window and round_class != "learning":
        raise ValidationError(
            f"event {event_date} is outside the clean window [{win['window_start']}, {win['window_end']}] for operator "
            f"{operator} (cutoff {cutoff}, today {win['today']}, lag {config.CLEAN_WINDOW_LAG_DAYS} days). "
            "Pass round_class='learning' to play it anyway as a learning round.")
    # v11 §C: Q9 is a gate on clean rounds only. A learning round's calls never enter the lag stats, so selection
    # honesty cannot bias them; it is recorded as a tag instead.
    if v10 and q9 == "fail" and contamination == "none" and round_class != "learning":
        reject_event(conn, source, event_date, event_text, "Q9", q9_detail["text"], start_date=selection_start_date)
        selector_record_q9(conn, q9)
        raise ValidationError("refused (Q9): the selection is not verifiable. Either accept the event through "
                              "nomad_enumerate / nomad_select_next / nomad_decide, or fix a window with nomad_selection_window "
                              "and write every skip with nomad_reject_event before submitting. " + q9_detail["text"])
    if contamination != "none":
        cls, reason = "learning", f"contamination {contamination}"
    elif round_class == "learning":
        cls, reason = "learning", "declared learning at intake" + ("" if in_window else " (outside clean window)")
    else:
        cls, reason = "clean", f"event in clean window [{win['window_start']}, {win['window_end']}], Q2 computed pass"

    with transaction(conn):
        ev = append(conn, "events", {
            "event_text": event_text.strip(), "event_date": event_date, "source": source,
            "selection_rule": selection_rule, "rejected_before": rejected_before,
            "criteria_json": dumps(criteria), "event_hash": event_hash(event_text.strip(), event_date),
            "node_recent_incidents": node_recent_incidents, "node": (node or None), "event_kind": event_kind,
            "node_kind": node_kind, "rejections": dumps(rejections) if rejections else None,
            "size_band": size_band, "candidate_id": candidate_id,
        })
        rd = append(conn, "rounds", {
            "event_id": ev["id"], "operator": operator, "operator_cutoff": cutoff or "unknown",
            "state": "created", "state_changed_at": now_iso(), "round_class": cls, "contamination": contamination,
        })
        transition(conn, rd["id"], None, "created", "submit_event")
        classify(conn, rd["id"], cls, contamination, reason)
        write_tag(conn, rd["id"], tag, q1a, q1a_basis, q1b["value"],
                  {"in_90d": q1b.get("in_90d"), "in_12m": q1b.get("in_12m"), "override": q1b.get("override"),
                   "incidents": [{k: i.get(k) for k in ("date", "kind", "text", "source", "from")} for i in (q1b.get("incidents") or [])][:10],
                   "registries": q1b.get("registries")},
                  "pass" if contamination == "none" else contamination, f"set at intake: Q1a {q1a}, Q1b {q1b['value']}, Q2 {contamination}",
                  cap_override=(cap_override or None) if cap["blocked"] else None, size_band=size_band)
        mix = mix_status(conn) if v10 else None
        if mix and mix.get("warning"):
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "intake", "note": "v10 B3 mix warning: " + mix["warning"]})
        if cap["blocked"]:
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "cap",
                                         "note": f"v11 §C cap warning (no refusal): admitted as {tag} with the last {cap_lookback(conn)} admitted "
                                                 f"{[t['tag'] for t in cap['recent']]}" + (f"; human reason: {cap_override.strip()}" if cap_override else "")})
        for text in rejections:
            fq = next((q for q in FAILING_QS if f"{q.lower()} fail" in text.lower() or f"{q.lower()}:" in text.lower()), None)
            reject_event(conn, source, event_date, text, fq or "Q9", "written from the legacy rejections list at intake",
                         start_date=selection_start_date, round_id=rd["id"])
        sel = selector_record_q9(conn, q9)
        if sel["suspended"]:
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "intake",
                                         "note": f"selector suspended: {sel['consecutive_q9_fails']} consecutive Q9 fails; the human clears it with nomad_selector_clear"})
        if not criteria_pass(criteria):
            failing = [k for k, v in criteria.items() if str(v).lower().startswith("fail")]
            gates = [q for q in failing if q in config.INTAKE_GATES]
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "intake",
                                         "note": f"admitted with criteria failing {failing}" + (f" (gates {gates})" if gates else
                                                 " (v11 §C: tags, not gates; filtered at analysis time)")
                                                 + f" under selection rule: {selection_rule}"})
        if rejections:
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "intake",
                                         "note": "rejected before this event (selector): " + " | ".join(rejections)})
        if density:
            append(conn, "round_notes", {"round_id": rd["id"], "kind": "intake",
                                         "note": f"carrier density for node kind {node_kind!r}: open {density['open_carriers']}, "
                                                 f"closed {density['closed_carriers']}"})
    return {"round_id": rd["id"], "event_id": ev["id"], "event_hash": ev["event_hash"], "operator": operator,
            "operator_cutoff": cutoff, "state": "created", "round_class": cls, "contamination": contamination,
            "criteria_pass": criteria_pass(criteria), "event_kind": event_kind, "node": node, "node_kind": node_kind,
            "carrier_density": density, "rejections_logged": len(rejections),
            "q2": criteria["Q2"], "clean_window": [win["window_start"], win["window_end"]],
            "tag": tag, "q1a": q1a, "q1b": {k: q1b.get(k) for k in ("value", "computed", "text", "in_90d", "in_12m", "override")},
            "q1b_registries": q1b.get("registries"), "cap": {"blocked": cap["blocked"], "override": bool(cap_override) if cap["blocked"] else None},
            "q9": q9_detail, "selector": sel, "size_band": size_band, "via_enumeration": via_enumeration,
            "mix": mix_status(conn) if v10 else None}


# ---- reveal with context (B5) -----------------------------------------------------------------

def _rule_tokens(node: str | None, event_kind: str | None) -> list[str]:
    toks = set()
    for t in re.split(r"[_\s\-/]+", (node or "").lower()):
        if len(t) >= 4 and t not in ("supply", "output", "access", "handling", "port", "node"):
            toks.add(t)
    if event_kind and event_kind != "other":
        toks.add(event_kind)
        toks.update({"fire": ("outage", "plant"), "explosion": ("outage", "plant"), "leak": ("closure", "dock"),
                     "spill": ("closure", "port"), "strike": ("port", "closure"), "closure": ("route", "port"),
                     "outage": ("plant", "unit")}.get(event_kind, ()))
    return sorted(toks)


def scheduled_facts(conn: sqlite3.Connection, node: str | None, holder_ids: list[str], event_date: str) -> list[dict]:
    """v8 D3: scheduled statements (earnings, guidance, regulatory calendar) within +-SCHEDULED_WINDOW_DAYS of the event
    for the node itself and every holder passed (degree <= 1 at reveal = holders on the node and their neighbours)."""
    d = date.fromisoformat(event_date)
    lo = (d - timedelta(days=config.SCHEDULED_WINDOW_DAYS)).isoformat()
    hi = (d + timedelta(days=config.SCORING_WINDOW_DAYS[None])).isoformat()      # v9 A3: the full scoring window forward
    q = ",".join("?" for _ in holder_ids) or "''"
    rows = conn.execute(
        f"SELECT f.id, f.node, f.holder_id, h.canonical_name, f.text, f.source, f.source_time FROM node_facts f "
        f"LEFT JOIN holders h ON h.id = f.holder_id WHERE f.fact_type = 'scheduled' AND f.source_time BETWEEN ? AND ? "
        f"AND (lower(f.node) = lower(?) OR f.holder_id IN ({q})) ORDER BY f.source_time",
        [lo, hi, node or "", *holder_ids]).fetchall()
    superseded = {r["supersedes"] for r in conn.execute("SELECT supersedes FROM node_facts WHERE fact_type = 'scheduled' AND supersedes IS NOT NULL")}
    out = []
    for r in rows:
        if r["id"] in superseded:
            continue
        d_ = dict(r)
        d_["knowable_by_event"] = True   # filled below
        out.append(d_)
    kf = {r["id"]: r["knowable_from"] for r in conn.execute("SELECT id, knowable_from FROM node_facts WHERE fact_type = 'scheduled'")}
    for d_ in out:
        d_["knowable_from"] = kf.get(d_["id"])
        d_["knowable_by_event"] = (kf.get(d_["id"]) or "9999") <= event_date
    return out


def reveal_context_for(conn: sqlite3.Connection, node: str | None, event_kind: str | None, event_date: str | None = None) -> dict:
    """Everything the operator's own store holds about the node, its neighbours and the event kind. Read-only."""
    from .facts import node_facts
    from .library import query
    from .names import get_holder
    from .positions import positions_on_node
    ctx: dict = {"node": node, "event_kind": event_kind, "holders": [], "neighbours": [], "node_facts": [], "rules": []}
    if node:
        on = positions_on_node(conn, node)
        ctx["holders"] = on["holders"]
        ctx["pairs"] = on["pairs"]
        ctx["self_hedged"] = on["self_hedged"]
        seen = {h["holder_id"] for h in on["holders"]}
        for h in on["holders"]:
            hd = get_holder(conn, h["holder_id"])
            rel = []
            if hd["parent_id"]:
                rel.append(hd["parent_id"])
            rel += [r["id"] for r in conn.execute("SELECT id FROM holders WHERE parent_id = ?", (h["holder_id"],))]
            for rid in rel:
                if rid in seen:
                    continue
                seen.add(rid)
                nb = get_holder(conn, rid)
                pos = [dict(p) for p in conn.execute(
                    "SELECT node, attribute, value, confidence, knowable_from FROM positions WHERE holder_id = ? ORDER BY rowid", (rid,))]
                ctx["neighbours"].append({"holder_id": rid, "key": nb.get("key"), "canonical_name": nb["canonical_name"],
                                          "kind": nb["kind"], "listed": bool(nb["listed"]), "relation": "parent" if rid == hd["parent_id"] else "child",
                                          "of": h["canonical_name"], "positions": pos})
        ctx["node_facts"] = [{k: f[k] for k in ("id", "fact_type", "text", "source", "source_time", "knowable_from")}
                             for f in node_facts(conn, node, limit=50)]
        # v8 B2: when more than one operator sits at the site, the larger one is the prior
        cands = []
        for h in on["holders"]:
            share = h["attributes"].get("share") or []
            tier = [str(t).lower() for t in (h["attributes"].get("tier") or [])]
            if share or any(t in ("0", "site", "operator", "degree0") for t in tier):
                num = None
                for v in share:
                    try:
                        num = float(str(v).rstrip("%"))
                    except ValueError:
                        pass
                cands.append({"holder_id": h["holder_id"], "canonical_name": h["canonical_name"], "listed": h["listed"],
                              "share": share[-1] if share else None, "share_num": num})
        ctx["map_candidates"] = cands
        with_num = [c for c in cands if c["share_num"] is not None]
        ctx["map_prior"] = (max(with_num, key=lambda c: c["share_num"])["canonical_name"] if with_num
                            else (cands[0]["canonical_name"] if len(cands) == 1 else None))
        if len(cands) >= 2:
            ctx["map_note"] = "more than one operator at degree 0: a map call here needs branches[] and per-branch rows (B1)"
    if event_date:
        ids = [h["holder_id"] for h in ctx["holders"]] + [n["holder_id"] for n in ctx["neighbours"]]
        ctx["scheduled"] = scheduled_facts(conn, node, ids, event_date)
    rules: dict[str, dict] = {}
    for tok in _rule_tokens(node, event_kind):
        for r in query(conn, tok, limit=50):
            rules[r["id"]] = r
    for r in query(conn, status="validated", limit=50):
        rules[r["id"]] = r
    ctx["rules"] = [{k: r[k] for k in ("id", "key", "rule_text", "forbids", "weight", "trials_as_carried", "weight_state", "carries", "status", "layer")}
                    for r in rules.values()]
    ctx["rule_tokens"] = _rule_tokens(node, event_kind)
    return ctx


def reveal_event(conn: sqlite3.Connection, round_id: str) -> dict:
    state = round_state(conn, round_id)
    if state == "void":
        raise StateError(f"round {round_id} is void; nothing to reveal. {_hint('void')}")
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    ctx = reveal_context_for(conn, ev.get("node"), ev.get("event_kind"), ev["event_date"])
    with transaction(conn):
        transition(conn, round_id, state, state, "revealed")
        append(conn, "reveal_context", {"round_id": round_id, "node": ev.get("node"), "event_kind": ev.get("event_kind"),
                                        "context_json": dumps(ctx)})
    return {"round_id": round_id, "event_text": ev["event_text"], "event_date": ev["event_date"], "state": state,
            "context": ctx,
            "context_summary": f"{len(ctx['holders'])} holder(s) on node, {len(ctx['neighbours'])} neighbour(s), "
                               f"{len(ctx['node_facts'])} node fact(s), {len(ctx['rules'])} rule(s) surfaced"}


def latest_reveal_context(conn: sqlite3.Connection, round_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM reveal_context WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    return loads(r["context_json"]) if r else None


# ---- touched set (B3) ----------------------------------------------------------------------------

def generate_legs(conn: sqlite3.Connection, round_id: str, nodes: list[str] | None = None, mechanism_ids: list[str] | None = None) -> dict:
    """v11 A3: on a round where the operator could know the outcome (learning class, or a replay), legs are not
    operator-selected: every holder with a position on the round's node(s) becomes a leg, marked leg_source
    'mechanical'. Degree comes from the positions store (0 for the node's own holders, 1 for their parents/children)."""
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    cls = classification(conn, round_id)
    if cls["round_class"] != "learning":
        raise ValidationError("mechanical leg generation is for learning-class rounds and replays; a clean round's legs are "
                              "the operator's own decomposition (nomad_touched_set)")
    nodes = [n.strip() for n in (nodes or ([ev["node"]] if ev.get("node") else [])) if n and n.strip()]
    if not nodes:
        raise ValidationError("no node on the event and none passed: name the node(s) to generate legs from")
    existing = {(t["holder_id"], t["node"].lower()) for t in list_touched_set(conn, round_id)}
    rows, seen = [], set()
    for node in nodes:
        for r in conn.execute("SELECT DISTINCT holder_id FROM positions WHERE lower(node) = lower(?) ORDER BY rowid", (node,)):
            hid = r["holder_id"]
            if (hid, node.lower()) in existing or (hid, node.lower()) in seen:
                continue
            seen.add((hid, node.lower()))
            h = get_row(conn, "holders", hid, "holder")
            kin = conn.execute("SELECT COUNT(*) FROM holders WHERE parent_id = ? OR id = (SELECT parent_id FROM holders WHERE id = ?)",
                               (hid, hid)).fetchone()[0]
            rows.append({"holder_id": hid, "degree": 0 if h["kind"] in ("plant", "facility") else (1 if kin else 2), "node": node,
                         "position_summary": f"generated from the positions store on {node}", "substitutability": "unknown",
                         "mechanism_ids": mechanism_ids or []})
    if not rows:
        return {"round_id": round_id, "generated": 0, "note": f"no positions on {nodes}"}
    r = touched_set_add(conn, round_id, rows, leg_source="mechanical")
    return {"round_id": round_id, "generated": r["count"], "nodes": nodes, "leg_source": "mechanical", "total": r["total"]}


def touched_set_add(conn: sqlite3.Connection, round_id: str, rows: list, leg_source: str = "operator") -> dict:
    from .library import resolve_rule_ids
    from .names import resolve_holder
    require_state(conn, round_id, ("created", "locked"), "record the touched set")
    parsed = []
    for i, r in enumerate(rows or []):
        try:
            parsed.append(r if isinstance(r, TouchedSetIn) else TouchedSetIn.model_validate(r))
        except Exception as e:
            raise ValidationError(f"touched_set[{i}] invalid: {e}")
    if not parsed:
        raise ValidationError("touched_set rows must be a non-empty list")
    ids = []
    with transaction(conn):
        for t in parsed:
            hid = resolve_holder(conn, t.holder_id)["id"]
            mech = resolve_rule_ids(conn, t.mechanism_ids) if t.mechanism_ids else []
            ids.append(append(conn, "touched_set", {
                "round_id": round_id, "holder_id": hid, "degree": t.degree, "node": t.node.strip(),
                "position_summary": t.position_summary, "substitutability": t.substitutability,
                "duration_factor": t.duration_factor, "carrier": t.carrier, "leg_source": leg_source,
                "mechanism_ids": dumps(mech) if mech else None})["id"])
    return {"round_id": round_id, "touched_set_ids": ids, "count": len(ids), "total": len(list_touched_set(conn, round_id))}


def list_touched_set(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT t.*, h.canonical_name, h.key AS holder_key, h.listed FROM touched_set t JOIN holders h ON h.id = t.holder_id "
        "WHERE t.round_id = ? ORDER BY t.degree, t.rowid", (round_id,))]


# ---- predictions ---------------------------------------------------------------------------

def falsifier_window_end(event_date: str, lag_band: str | None, window: str | None) -> str | None:
    window = window or "scoring_window"
    evd = date.fromisoformat(event_date)
    if window.startswith("until:"):
        return window[6:]
    if window.startswith("days:"):
        return (evd + timedelta(days=int(window[5:]))).isoformat()
    days = config.SCORING_WINDOW_DAYS.get(lag_band)
    return None if days is None else (evd + timedelta(days=days)).isoformat()


def _link_factor(conn: sqlite3.Connection, f, round_id: str) -> tuple[str | None, str | None]:
    """D1: holder strings resolve through the names book; unlinked ones go to the orphan queue."""
    from .names import resolve, resolve_holder
    hid = None
    if f.holder_id:
        try:
            hid = resolve_holder(conn, f.holder_id)["id"]
        except NotFound:
            r = resolve(conn, f.holder_id, context=f"factor holder: {f.factor}", round_id=round_id)
            hid = r["holder_id"] if r["resolved"] else None
    node = f.node.strip() if f.node else None
    if node and not conn.execute("SELECT 1 FROM positions WHERE lower(node) = lower(?) LIMIT 1", (node,)).fetchone() \
            and not conn.execute("SELECT 1 FROM node_facts WHERE lower(node) = lower(?) LIMIT 1", (node,)).fetchone() \
            and not conn.execute("SELECT 1 FROM touched_set WHERE lower(node) = lower(?) LIMIT 1", (node,)).fetchone():
        append(conn, "orphans", {"raw_string": node, "raw_norm": node.lower(), "context": f"factor node: {f.factor}", "round_id": round_id})
    return hid, node


SECOND_KINDS = ("vol", "volume", "timing")


def v13_on(conn: sqlite3.Connection, event_row=None) -> bool:
    """v13 applies to rounds admitted after the marker; nothing is applied retroactively to a locked round."""
    from .risk import setting
    started = setting(conn, "v13_started_at")
    if not started:
        return False
    return True if event_row is None else (event_row["recorded_at"] >= started)


def write_leg_claims(conn: sqlite3.Connection, round_id: str, parsed: list, ids: list[str], leg_claims: list,
                     strict: bool = True, assessment: dict | None = None) -> dict:
    """v13 A1: the effect kinds as a template over legs that already exist, with the touched set's equal-analysis
    discipline. Every leg carries a direction claim and one of vol/volume/timing, or a stated `no-claim:` reason for
    the slot it leaves empty. This was the grid's one real job; enumerating cells as legs was not."""
    from .basket import round_legs
    from .effects import node_kind_of
    # v15 §I1: an attribute node is a shared loading, never a leg with a path. It is summed in construction (§H) and
    # carries no direction claim, because there is no effect on it to claim about.
    legs = [l for l in round_legs(conn, round_id) if node_kind_of(conn, l["node"]) != "attribute"]
    by_pid = {pid: l for l in legs for pid in (l["all_position_ids"] or [])}
    pred_kind = {}
    for p, pid in zip(parsed, ids):
        if p.position_id:
            pred_kind.setdefault(p.position_id, []).append((p.effect_kind or "direction", pid))
    supplied: dict[tuple[str, str], str] = {}
    impacts: dict[str, tuple[float, str]] = {}
    for i, c in enumerate(leg_claims or []):
        c = dict(c)
        unknown = set(c) - {"position_id", "effect_kind", "no_claim", "no_claim_reason", "impact_pct", "impact_basis"}
        if unknown:
            raise ValidationError(f"leg_claims[{i}]: unknown fields {sorted(unknown)}")
        pid = c.get("position_id")
        if pid not in by_pid:
            raise ValidationError(f"leg_claims[{i}]: position_id {pid!r} is not a leg on this round")
        reason = (c.get("no_claim") or c.get("no_claim_reason") or "").strip()
        ek = c.get("effect_kind") or "second"
        slot = "direction" if ek == "direction" else "second"
        if c.get("impact_pct") is not None:
            # v13 (found by §C): the eliminator that the whole absence record turns on had no numerator anywhere in the
            # ledger, because the only per-leg number was the call's own claim and using that makes A5 circular. This is
            # the operator's independent estimate of what the event is worth on this leg, stated at lock.
            if not (c.get("impact_basis") or "").strip():
                raise ValidationError(f"leg_claims[{i}]: impact_pct needs an impact_basis saying where the estimate comes from")
            impacts[by_pid[pid]["all_position_ids"][0]] = (float(c["impact_pct"]), c["impact_basis"].strip())
            if not reason:
                continue
        if not reason.lower().startswith("no-claim:") or len(reason) < 20:
            raise ValidationError(f"leg_claims[{i}]: a slot left empty needs a reason beginning 'no-claim:' saying why "
                                  "nothing can be claimed there (A1: the same equal-analysis discipline as the touched set)")
        supplied[(by_pid[pid]["all_position_ids"][0], slot)] = reason
    # v14 A2/C4: the template is owed by the residue and by any leg the operator called on, not by every generated leg
    killed, no_path = {}, set()
    for r in ((assessment or {}).get("results") or []):
        if not r["survives"]:
            killed[r["position_id"]] = r["eliminators_fired"]
        if "no_path" in (r["eliminators_fired"] or []):
            no_path.add(r["position_id"])
    problems, rows, skipped = [], [], 0
    for l in legs:
        canon = (l["all_position_ids"] or [l["holder_id"]])[0]
        kinds = [k for pid in (l["all_position_ids"] or []) for k, _ in pred_kind.get(pid, [])]
        direction = [(k, pid) for p_ in (l["all_position_ids"] or []) for k, pid in pred_kind.get(p_, []) if k == "direction"]
        second = [(k, pid) for p_ in (l["all_position_ids"] or []) for k, pid in pred_kind.get(p_, []) if k in SECOND_KINDS]
        called_on = bool(direction or second)
        if canon in killed and not called_on:
            skipped += 1
            continue
        # C4: a leg carries an admissible path, or it is not a leg. Half the footprint was padding from a template
        # that forces rows, and widening generation makes that matter more rather than less.
        if strict and called_on and canon in no_path:
            problems.append(f"{l['holder']} on {l['node']}: a call is locked on a leg with no admissible path "
                            "(degree 2 or worse, no cited mechanism, no stated position). Give it a path or drop the call")
        for slot, hits in (("direction", direction), ("second", second)):
            if hits:
                rows.append({"position_id": canon, "effect_kind": hits[0][0], "prediction_id": hits[0][1], "no_claim_reason": None,
                             "holder_id": l["holder_id"], "node": l["node"]})
            elif (canon, slot) in supplied:
                rows.append({"position_id": canon, "effect_kind": (None if slot == "second" else "direction"), "prediction_id": None,
                             "no_claim_reason": supplied[(canon, slot)], "holder_id": l["holder_id"], "node": l["node"]})
            else:
                problems.append(f"{l['holder']} on {l['node']}: no {slot} claim and no 'no-claim:' reason "
                                f"({'a direction claim' if slot == 'direction' else 'a vol, volume or timing claim'} or a stated reason)")
    if problems and strict:
        raise ValidationError("v13 A1 / v14 C4: every surviving leg carries a direction claim and a vol/volume/timing "
                              "claim, or a stated "
                              "'no-claim:' reason for the slot it leaves empty. Missing: " + "; ".join(problems[:8])
                              + (f" (+{len(problems) - 8} more)" if len(problems) > 8 else ""))
    for r in rows:
        imp = impacts.get(r["position_id"])
        append(conn, "leg_claims", {"round_id": round_id, **r,
                                    "impact_pct": (imp[0] if imp else None), "impact_basis": (imp[1] if imp else None)})
    for pid, (pct, basis) in impacts.items():        # an impact stated on a leg that filled both slots with calls
        if not any(r["position_id"] == pid for r in rows):
            l = by_pid.get(pid) or {}
            append(conn, "leg_claims", {"round_id": round_id, "position_id": pid, "holder_id": l.get("holder_id"),
                                        "node": l.get("node"), "effect_kind": None, "prediction_id": None,
                                        "no_claim_reason": None, "impact_pct": pct, "impact_basis": basis})
    return {"round_id": round_id, "rows": len(rows), "legs": len(legs), "problems": problems,
            "eliminated_legs_skipped": skipped,
            "note": "the template is owed by the residue and by any leg the operator called on (v14 A2)"}


def leg_template_status(conn: sqlite3.Connection, round_id: str) -> dict | None:
    rows = [dict(r) for r in conn.execute("SELECT * FROM leg_claims WHERE round_id = ? ORDER BY rowid", (round_id,))]
    if not rows:
        return None
    return {"rows": len(rows), "claimed": sum(1 for r in rows if r["prediction_id"]),
            "no_claim": sum(1 for r in rows if r["no_claim_reason"]),
            "legs": len({r["position_id"] for r in rows})}


def lock_predictions(conn: sqlite3.Connection, round_id: str, predictions: list, lock_note: str | None = None,
                     strict: bool = True, leg_claims: list | None = None) -> dict:
    from . import carriers as carriers_mod
    from .library import check_citation, resolve_rule, resolve_rule_ids
    state = require_state(conn, round_id, ("created", "locked"), "lock predictions")
    if not predictions:
        raise ValidationError("at least one prediction is required to lock")
    # B3: touched set or an explicit reason (passed now, or already on the notes ledger)
    if state == "created" and not list_touched_set(conn, round_id):
        declared = (lock_note or "").strip().lower().startswith("no-touched-set:") or any(
            n["kind"] == "lock" and n["note"].lower().startswith("no-touched-set:") for n in list_notes(conn, round_id))
        if not declared:
            raise ValidationError("no touched_set recorded for this round: call nomad_touched_set first (one row per holder x degree), "
                                  "or pass lock_note starting 'no-touched-set: <why>'")
    parsed: list[PredictionIn] = []
    ctx = None if strict else {"lenient": True}
    for i, p in enumerate(predictions):
        try:
            parsed.append(p if isinstance(p, PredictionIn) else PredictionIn.model_validate(p, context=ctx))
        except Exception as e:
            raise ValidationError(f"prediction[{i}] invalid: {e}")
    # v10 A2/A4/K4: every call names its due date; narrative rows default to event_date + 5; the one-trade meta row is retired
    from . import edge as edge_mod
    from .risk import effect_kind_for, setting, window_for
    rd0 = get_row(conn, "rounds", round_id, "round")
    ev0 = get_row(conn, "events", rd0["event_id"], "event")
    v10 = bool(setting(conn, "freeze_started_at")) and ev0["recorded_at"] >= setting(conn, "freeze_started_at")
    evd = date.fromisoformat(ev0["event_date"])
    max_due = (evd + timedelta(days=config.DUE_AT_MAX_DAYS)).isoformat()
    for i, p in enumerate(parsed):
        if p.call_type == "narrative" and not p.due_at:
            p.due_at = (evd + timedelta(days=config.NARRATIVE_DUE_DAYS)).isoformat()
        if v10 and strict:
            # v12 D1: a sign or magnitude_order call on a listed leg records what was already priced
            if p.call_type in ("sign", "magnitude_order") and p.position_id and p.implied_at_lock is None:
                listed = conn.execute("SELECT h.listed FROM positions p JOIN holders h ON h.id = p.holder_id WHERE p.id = ?",
                                      (p.position_id,)).fetchone()
                if listed and listed["listed"]:
                    raise ValidationError(f"prediction[{i}]: implied_at_lock is required on a {p.call_type} call on a listed leg (v12 D1): "
                                          "{method: option_implied|realised_since_event|none, value, source, as_of, basis}. Edge is the "
                                          "claim minus what is already priced, and only the first term has ever been measured")
            # v12 F3: an occurrence call about what an institution will do cites the frequency it departs from
            if edge_mod.is_institutional(p.call_type, p.sign, p.target, p.claim) and not p.base_rate_id and "no-base-rate:" not in p.claim:
                raise ValidationError(f"prediction[{i}]: this is a claim about institutional behaviour (v12 F3): cite a base_rate_id "
                                      "(nomad_base_rates) or write 'no-base-rate: <why>' in the claim. The call may depart from the rate; "
                                      "it must know that it is departing")
            if not p.due_at:
                raise ValidationError(f"prediction[{i}]: due_at is required (v10 A2): the date by which this call's carrier will have spoken, <= {max_due}")
            if p.call_type == "meta" and ("one trade" in p.claim.lower() or "one-trade" in p.claim.lower() or "one-trade" in p.target.lower()):
                raise ValidationError(f"prediction[{i}]: the meta one-trade control is retired from round 10 (v10 K4); the mirror basket is the derived alternative")
        if p.due_at:
            if p.due_at > max_due:
                raise ValidationError(f"prediction[{i}]: due_at {p.due_at} is more than {config.DUE_AT_MAX_DAYS} days after the event ({max_due})")
            if p.due_at < ev0["event_date"]:
                raise ValidationError(f"prediction[{i}]: due_at {p.due_at} is before the event date")
        if v10:
            if not p.effect_kind:
                p.effect_kind = effect_kind_for(p.call_type)
            if not p.window:
                p.window = window_for(p.falsifier_window, p.lag_band)
    existing = {p["id"]: p for p in list_predictions(conn, round_id)}
    resolved: list[list[str]] = []
    conditionals: list[tuple[str | None, int | None, str] | None] = []
    carrier_status: list[str | None] = []
    for i, p in enumerate(parsed):
        try:
            mech = resolve_rule_ids(conn, p.mechanism_ids)
        except ValidationError as e:
            raise ValidationError(f"prediction[{i}]: {e}")
        # v8 A2: a rule is cited only on the kind of claim it carries
        if strict:
            for rid in mech:
                msg = check_citation(resolve_rule(conn, rid), p.call_type, p.sign)
                if msg:
                    raise ValidationError(f"prediction[{i}]: {msg}")
        resolved.append(mech)
        if p.hypothesis_id and not conn.execute("SELECT 1 FROM hypotheses WHERE id = ?", (p.hypothesis_id,)).fetchone():
            raise ValidationError(f"prediction[{i}]: unknown hypothesis_id {p.hypothesis_id!r}")
        if p.position_id and not (conn.execute("SELECT 1 FROM positions WHERE id = ?", (p.position_id,)).fetchone()
                                  or conn.execute("SELECT 1 FROM synthetic_legs WHERE id = ?", (p.position_id,)).fetchone()):
            raise ValidationError(f"prediction[{i}]: position_id {p.position_id!r} is not a positions row or synthetic leg")
        if p.call_type == "narrative" and strict and carriers_mod.is_price_series(conn, p.carrier or ""):
            raise ValidationError(f"prediction[{i}]: narrative carrier {p.carrier!r} resolves to a price series; name a channel that says things")
        # v8 B1: conditional rows reference a map call with branches, written before them
        cond = None
        if p.conditional_on:
            ref, branch = p.conditional_on.prediction_ref, p.conditional_on.branch
            if ref.startswith("#"):
                try:
                    k = int(ref[1:])
                except ValueError:
                    raise ValidationError(f"prediction[{i}]: conditional_on.prediction_ref {ref!r} must be '#<index>' or a prediction id")
                if not 0 <= k < i:
                    raise ValidationError(f"prediction[{i}]: conditional_on refers to #{k}; the map call must come before its conditional rows in the batch")
                target = parsed[k]
                if target.call_type != "map" or not target.branches:
                    raise ValidationError(f"prediction[{i}]: #{k} is not a map call with branches")
                if branch not in target.branches:
                    raise ValidationError(f"prediction[{i}]: branch {branch!r} is not one of #{k}'s branches {target.branches}")
                cond = (None, k, branch)
            else:
                target = existing.get(ref)
                if not target or target["call_type"] != "map" or not target.get("branches"):
                    raise ValidationError(f"prediction[{i}]: conditional_on.prediction_ref {ref!r} is not a map call with branches on this round")
                if branch not in target["branches"]:
                    raise ValidationError(f"prediction[{i}]: branch {branch!r} is not one of {ref}'s branches {target['branches']}")
                cond = (ref, None, branch)
        conditionals.append(cond)
        # v8 D2: carrier reachability from the registry
        st = carriers_mod.resolve(conn, p.carrier)["status"] if p.call_type != "meta" else None
        carrier_status.append(st)
    flags = [{"index": i, "target": p.target, "carrier": p.carrier} for i, (p, st) in enumerate(zip(parsed, carrier_status)) if st == "unreachable"]
    ids = []
    stamps: list[dict] = []
    with transaction(conn):
        # v13 A1: cell enumeration no longer produces legs. `predictions.space` stays on the old rows for history and
        # is not written again; the effect kinds survive only as a template over legs that already exist (§A1), and the
        # question the mirror was standing in for is now asked directly, per leg, at lock (§A2).
        stamps = [None] * len(parsed)
        base_rate_ids = []
        for p in parsed:
            base_rate_ids.append(edge_mod.resolve_base_rate(conn, p.base_rate_id)["id"] if p.base_rate_id else None)
        if lock_note and lock_note.strip():
            append(conn, "round_notes", {"round_id": round_id, "kind": "lock", "note": lock_note.strip()})
        for i, (p, mech, cond, st) in enumerate(zip(parsed, resolved, conditionals, carrier_status)):
            cond_json = None
            if cond:
                ref_id, k, branch = cond
                cond_json = dumps({"prediction_id": ref_id if ref_id else ids[k], "branch": branch})
            row = append(conn, "predictions", {
                "round_id": round_id, "call_type": p.call_type, "target": p.target, "claim": p.claim,
                "hypothesis_id": p.hypothesis_id, "sign": p.sign, "magnitude_rank": p.magnitude_rank,
                "lag_band": p.lag_band, "carrier": p.carrier, "falsifier": p.falsifier,
                "falsifier_window": p.falsifier_window, "mechanism_ids": dumps(mech),
                "baseline_claim": p.baseline_claim, "confidence_band": p.confidence_band, "locked_at": now_iso(),
                "aggregation": p.aggregation, "branches": dumps(p.branches) if p.branches else None,
                "conditional_on": cond_json, "narrative_sign": p.narrative_sign, "position_id": p.position_id,
                "effect_id": p.effect_id,
                "carrier_status": st, "due_at": p.due_at, "effect_kind": p.effect_kind, "window": p.window,
                "implied_method": (p.implied_at_lock or {}).get("method"),
                "implied_value": (None if (p.implied_at_lock or {}).get("method") in (None, "none") else float(p.implied_at_lock["value"])),
                "implied_source": (p.implied_at_lock or {}).get("source"), "implied_as_of": (p.implied_at_lock or {}).get("as_of"),
                "implied_basis": (p.implied_at_lock or {}).get("basis"), "base_rate_id": base_rate_ids[i],
                "settling_document": p.settling_document, "settling_document_fetched": (None if p.settling_document_fetched is None else int(p.settling_document_fetched)),
                "space": stamps[i]["space"] if stamps[i] else None, "covering_rule_id": stamps[i]["covering_rule_id"] if stamps[i] else None,
                "grid_cell_id": stamps[i]["id"] if stamps[i] else None,
            })
            ids.append(row["id"])
            for idx, f in enumerate(p.factors):
                hid, node = _link_factor(conn, f, round_id)
                append(conn, "prediction_factors", {
                    "prediction_id": row["id"], "idx": idx, "factor": f.factor, "holder_id": hid, "node": node,
                    "estimate": f.estimate, "carrier": f.carrier, "falsifier": f.falsifier,
                    "binding": f.binding, "against": f.against})
        if state == "created":
            transition(conn, round_id, "created", "locked", "lock_predictions")
        if v13_on(conn, ev0):
            # v14: the anchors run over the whole generated space first, because the template and the path requirement
            # apply to what is left standing plus whatever the operator actually called on. A leg an anchor killed is
            # recorded with its reason and is not asked for claims it has no business making.
            from . import surviving as surviving_mod
            assessment = surviving_mod.assess_round(conn, round_id, as_of=ev0["event_date"])
            write_leg_claims(conn, round_id, parsed, ids, leg_claims or [], strict=strict, assessment=assessment)
        # v8 D2: Q7 computed per named carrier over every call locked on the round
        q7 = None
        if strict:
            all_status = [p["carrier_status"] for p in list_predictions(conn, round_id) if p["call_type"] != "meta"]
            q7 = carriers_mod.q7_for([{"status": x} for x in all_status])
            if q7:
                rd = get_row(conn, "rounds", round_id, "round")
                cur = current_criteria(conn, rd["event_id"])["current"]
                if str(cur.get("Q7", "")).split(":")[0].strip().lower() != q7.split(":")[0]:
                    criteria_supersede(conn, rd["event_id"], {**cur, "Q7": q7}, "Q7 computed at lock from the carriers registry (v8 D2)")
    total = conn.execute("SELECT COUNT(*) FROM predictions WHERE round_id = ?", (round_id,)).fetchone()[0]
    grid_counts = None
    if v10:
        gc = conn.execute("SELECT space, COUNT(*) AS n FROM grid_cells WHERE round_id = ? GROUP BY space", (round_id,)).fetchall()
        grid_counts = {r["space"]: r["n"] for r in gc} or None
    risk = None
    if v13_on(conn, ev0):
        from . import surviving
        risk = surviving.assess_round(conn, round_id, as_of=ev0["event_date"])
        risk = {k: risk[k] for k in ("legs", "surviving", "eliminated", "surviving_but_small", "by_eliminator",
                                     "unevaluable", "legs_with_no_evaluable_eliminator")}
    return {"round_id": round_id, "state": "locked", "prediction_ids": ids, "n_locked_total": total, "grid": grid_counts,
            "stamped_cells": sum(1 for c in stamps if c), "surviving_risk": risk,
            "leg_template": leg_template_status(conn, round_id),
            "carrier_unreachable": flags, "q7_computed": q7,
            "carrier_note": ("name a fallback carrier for flagged calls in a further lock; flagged rows stay as locked" if flags else None)}


def list_factors(conn: sqlite3.Connection, prediction_id: str) -> list[dict]:
    out = []
    for r in conn.execute("SELECT f.*, h.canonical_name AS holder_name FROM prediction_factors f LEFT JOIN holders h ON h.id = f.holder_id "
                          "WHERE f.prediction_id = ? ORDER BY f.idx", (prediction_id,)):
        d = dict(r)
        d["binding"], d["against"] = bool(d["binding"]), bool(d["against"])
        out.append(d)
    return out


def list_predictions(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    ev_date = conn.execute("SELECT e.event_date FROM rounds r JOIN events e ON e.id = r.event_id WHERE r.id = ?",
                           (round_id,)).fetchone()
    out = []
    for r in conn.execute("SELECT * FROM predictions WHERE round_id = ? ORDER BY rowid", (round_id,)):
        d = dict(r)
        d["mechanism_ids"] = loads(d["mechanism_ids"])
        d["branches"] = loads(d["branches"]) if d.get("branches") else None
        d["conditional_on"] = loads(d["conditional_on"]) if d.get("conditional_on") else None
        d["falsifier_window_end"] = falsifier_window_end(ev_date["event_date"], d["lag_band"], d["falsifier_window"]) if ev_date else None
        d["factors"] = list_factors(conn, d["id"])
        out.append(d)
    return out


def open_retrieval(conn: sqlite3.Connection, round_id: str, event_date_confirmed: str | None = None,
                   date_source: str | None = None) -> dict:
    """v13 B2: Q2 has never been a cutoff test. It tested the submitter's date claim, which is all intake has, and
    round 12's misdating (2025 submitted as 2026) passed it by construction. The event's date is establishable only
    once retrieval opens, so it is re-computed here against the date retrieval found, and a fail voids the round."""
    require_state(conn, round_id, ("locked",), "open retrieval")
    preds = list_predictions(conn, round_id)
    if not [p for p in preds if p["locked_at"]]:
        raise StateError(f"round {round_id} has no locked predictions; call nomad_lock_predictions first")
    transition(conn, round_id, "locked", "open", "open_retrieval")
    q2 = None
    if event_date_confirmed:
        q2 = confirm_event_date(conn, round_id, event_date_confirmed, date_source or "confirmed at open_retrieval")
        if q2["voided"]:
            return {"round_id": round_id, "state": "void", "q2_recheck": q2, "predictions": []}
    return {"round_id": round_id, "state": "open", "q2_recheck": q2, "predictions": preds,
            "next_step": (None if q2 else "confirm the event's date against retrieval with nomad_confirm_event_date; "
                          "scoring is refused until Q2 has been re-computed against what retrieval found (v13 B2)")}


def confirm_event_date(conn: sqlite3.Connection, round_id: str, event_date: str, source: str) -> dict:
    """B2: record the date retrieval established, re-compute Q2 against it, void on a fail."""
    date.fromisoformat(event_date)
    if not (source or "").strip():
        raise ValidationError("source is required: what established the date")
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    state = round_state(conn, round_id)
    if state in ("created", "locked"):
        raise StateError("the event's date is confirmed from retrieval, so it is confirmed after open_retrieval")
    cutoff = rd["operator_cutoff"] if rd["operator_cutoff"] != "unknown" else None
    fails = bool(cutoff and event_date <= cutoff)
    moved = event_date != ev["event_date"]
    text = (f"fail: re-computed at retrieval (v13 B2); the event is {event_date}"
            + (f", not the {ev['event_date']} supplied at intake" if moved else "")
            + f", on or before the operator cutoff {cutoff}" if fails else
            f"pass: re-computed at retrieval (v13 B2) against the event as established ({event_date}"
            + (f", corrected from the {ev['event_date']} supplied at intake" if moved else "") + f"), after cutoff {cutoff}")
    cur = current_criteria(conn, ev["id"])["current"]
    criteria_supersede(conn, ev["id"], {**cur, "Q2": text}, f"Q2 re-computed at retrieval against the date established by {source.strip()}")
    # the events ledger is append-only and an event row is referenced by its round, so the confirmation is a note on
    # the round rather than an edit to the event: same fact, written where it can be written.
    append(conn, "round_notes", {"round_id": round_id, "kind": "event_date_confirmed",
                                 "note": f"{event_date} | confirmed by {source.strip()}" +
                                         (f" | intake said {ev['event_date']}" if moved else "") + f" | Q2 {text.split(':')[0]}"})
    out = {"round_id": round_id, "event_date_at_intake": ev["event_date"], "event_date_confirmed": event_date,
           "moved": moved, "q2": text, "voided": False}
    if fails:
        void_round(conn, round_id, f"contaminated: Q2 re-computed at retrieval; the event is {event_date}, on or before "
                                   f"the operator cutoff {cutoff} (v13 B2)")
        out["voided"] = True
    return out


def date_confirmed(conn: sqlite3.Connection, round_id: str) -> str | None:
    r = conn.execute("SELECT note FROM round_notes WHERE round_id = ? AND kind = 'event_date_confirmed' "
                     "ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    return r["note"].split("|")[0].strip() if r else None


def evidence_carrier(conn: sqlite3.Connection, url: str, title: str) -> str | None:
    """v12 E6: the brief assumes every round's evidence names its carrier. It did not: evidence held a url and a
    headline, and six of ninety-one rows on rounds 1-11 resolved to a registered carrier, so fact_holder_class could
    not be derived for the class-distance test. Resolve it at write time — the host, then the headline."""
    from .carriers import resolve
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host:
        for r in conn.execute("SELECT name, url, fetch_paths FROM carriers WHERE url IS NOT NULL OR fetch_paths IS NOT NULL"):
            hay = f"{r['url'] or ''} {r['fetch_paths'] or ''}".lower()
            if host in hay:
                return r["name"]
    m = resolve(conn, f"{title} {url}")["matched"]
    return m[0]["name"] if m else None


def add_evidence(conn: sqlite3.Connection, round_id: str, url: str, title: str, excerpt: str,
                 source_time: str | None = None, knowable_from: str | None = None, note: str | None = None) -> dict:
    require_state(conn, round_id, ("open", "partially_scored"), "add evidence")
    if len(excerpt) > 500:
        raise ValidationError(f"excerpt is {len(excerpt)} chars; limit is 500. Trim it to the load-bearing sentence(s).")
    if not url.strip() or not title.strip():
        raise ValidationError("url and title are required")
    row = append(conn, "evidence", {"round_id": round_id, "url": url, "title": title, "source_time": source_time,
                                    "knowable_from": knowable_from, "excerpt": excerpt, "note": note,
                                    "carrier": evidence_carrier(conn, url, title)})
    return {"evidence_id": row["id"], "round_id": round_id, "recorded_at": row["recorded_at"], "carrier": row["carrier"]}


def add_evidence_batch(conn: sqlite3.Connection, round_id: str, items: list[dict]) -> dict:
    require_state(conn, round_id, ("open", "partially_scored"), "add evidence")
    if not items:
        raise ValidationError("items must be a non-empty list")
    problems = []
    for i, e in enumerate(items):
        for k in ("url", "title", "excerpt"):
            if not str(e.get(k, "")).strip():
                problems.append(f"item[{i}]: {k} is required")
        if len(e.get("excerpt", "")) > 500:
            problems.append(f"item[{i}]: excerpt is {len(e['excerpt'])} chars; limit is 500")
        unknown = set(e) - {"url", "title", "excerpt", "source_time", "knowable_from", "note", "carrier"}
        if unknown:
            problems.append(f"item[{i}]: unknown fields {sorted(unknown)}")
    if problems:
        raise ValidationError("evidence batch rejected, nothing written: " + "; ".join(problems))
    ids = []
    with transaction(conn):
        for e in items:
            ids.append(append(conn, "evidence", {"round_id": round_id, "url": e["url"], "title": e["title"],
                                                 "source_time": e.get("source_time"), "knowable_from": e.get("knowable_from"),
                                                 "excerpt": e["excerpt"], "note": e.get("note"),
                                                 "carrier": e.get("carrier") or evidence_carrier(conn, e["url"], e["title"])})["id"])
    return {"round_id": round_id, "evidence_ids": ids, "count": len(ids)}


def round_note(conn: sqlite3.Connection, round_id: str, kind: str, note: str) -> dict:
    round_state(conn, round_id)
    if not kind.strip() or not note.strip():
        raise ValidationError("kind and note are required")
    row = append(conn, "round_notes", {"round_id": round_id, "kind": kind.strip(), "note": note.strip()})
    return {"note_id": row["id"], "round_id": round_id, "kind": kind.strip()}


def list_notes(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM round_notes WHERE round_id = ? ORDER BY rowid", (round_id,))]


def void_round(conn: sqlite3.Connection, round_id: str, reason: str, peeked: bool = False) -> dict:
    state = round_state(conn, round_id)
    if state == "void":
        raise StateError(f"round {round_id} is already void")
    if not reason.strip():
        raise ValidationError("a reason is required to void a round (e.g. 'contaminated')")
    with transaction(conn):
        transition(conn, round_id, state, "void", reason)
        if peeked:
            cls = classification(conn, round_id)
            classify(conn, round_id, cls["round_class"], "peeked", f"voided: {reason}")
    return {"round_id": round_id, "state": "void", "from_state": state, "reason": reason, "peeked": peeked}


# ---- criteria supersession (A9) --------------------------------------------------------------

def criteria_supersede(conn: sqlite3.Connection, event_id: str, criteria_json, reason: str) -> dict:
    get_row(conn, "events", event_id, "event")
    criteria = _parse_criteria(criteria_json)
    if not reason.strip():
        raise ValidationError("a reason is required to supersede criteria")
    latest = conn.execute("SELECT id FROM event_criteria WHERE event_id = ? ORDER BY rowid DESC LIMIT 1", (event_id,)).fetchone()
    row = append(conn, "event_criteria", {"event_id": event_id, "criteria_json": dumps(criteria), "reason": reason,
                                          "supersedes": latest["id"] if latest else None})
    return {"event_id": event_id, "criteria_id": row["id"], "supersedes": row["supersedes"], "criteria": criteria}


def current_criteria(conn: sqlite3.Connection, event_id: str) -> dict:
    ev = get_row(conn, "events", event_id, "event")
    history = [dict(r) for r in conn.execute("SELECT * FROM event_criteria WHERE event_id = ? ORDER BY rowid", (event_id,))]
    for h in history:
        h["criteria_json"] = loads(h["criteria_json"])
    current = history[-1]["criteria_json"] if history else loads(ev["criteria_json"])
    return {"current": current, "intake": loads(ev["criteria_json"]), "history": history, "criteria_pass": criteria_pass(current)}


# ---- reads -----------------------------------------------------------------------------------

def list_evidence(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM evidence WHERE round_id = ? ORDER BY rowid", (round_id,))]


def list_transitions(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM round_transitions WHERE round_id = ? ORDER BY rowid", (round_id,))]


def list_classifications(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM round_classifications WHERE round_id = ? ORDER BY rowid", (round_id,))]


def latest_resolutions(conn: sqlite3.Connection, round_id: str) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT r.* FROM resolutions r JOIN predictions p ON p.id = r.prediction_id WHERE p.round_id = ? ORDER BY r.rowid",
        (round_id,)).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        d = dict(r)
        d["evidence_ids"] = loads(d["evidence_ids"])
        out[d["prediction_id"]] = d
    return out


def latest_factor_resolutions(conn: sqlite3.Connection, prediction_id: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM factor_resolutions WHERE prediction_id = ? ORDER BY rowid", (prediction_id,)):
        d = dict(r)
        d["evidence_ids"] = loads(d["evidence_ids"])
        out[d["factor_id"]] = d
    return out


def latest_scorecard(conn: sqlite3.Connection, round_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM scorecards WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    return loads(r["scorecard_json"]) if r else None


def round_status(conn: sqlite3.Connection, round_id: str) -> dict:
    state = round_state(conn, round_id)
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    n = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE round_id = ?", (round_id,)).fetchone()[0]
    n_res = conn.execute(
        "SELECT COUNT(DISTINCT r.prediction_id) FROM resolutions r JOIN predictions p ON p.id = r.prediction_id WHERE p.round_id = ?",
        (round_id,)).fetchone()[0]
    return {
        "round_id": round_id, "state": state, "classification": classification(conn, round_id),
        "tag": (round_tag(conn, round_id) or {}).get("tag"),
        "criteria_pass": current_criteria(conn, ev["id"])["criteria_pass"],
        "event_id": ev["id"], "event_hash": ev["event_hash"], "event_date": ev["event_date"], "node": ev.get("node"),
        "event_kind": ev.get("event_kind"), "operator": rd["operator"], "operator_cutoff": rd["operator_cutoff"],
        "counts": {"predictions": n("predictions"), "evidence": n("evidence"), "resolutions": n_res,
                   "predicate_checks": n("predicate_checks"), "touched_set": n("touched_set")},
        "transitions": list_transitions(conn, round_id),
        "next_step": _hint(state),
    }


def export_round(conn: sqlite3.Connection, round_id: str) -> dict:
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    crit = current_criteria(conn, ev["id"])
    ev["criteria_json"] = crit["current"]
    checks = [dict(r) for r in conn.execute(
        "SELECT pc.*, p.name AS predicate_name, p.kind AS predicate_kind, p.key AS predicate_key FROM predicate_checks pc "
        "JOIN predicates p ON p.id = pc.predicate_id WHERE pc.round_id = ? ORDER BY pc.rowid", (round_id,))]
    preds = list_predictions(conn, round_id)
    for p in preds:
        p["factor_resolutions"] = list(latest_factor_resolutions(conn, p["id"]).values())
    return {
        "round": dict(rd, state=round_state(conn, round_id)),
        "classification": classification(conn, round_id),
        "classification_history": list_classifications(conn, round_id),
        "tag": round_tag(conn, round_id),
        "tag_history": list_tags(conn, round_id),
        "rejections": [dict(r) for r in conn.execute("SELECT * FROM event_rejections WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "criteria_pass": crit["criteria_pass"],
        "event": ev,
        "criteria_history": crit["history"],
        "reveal_context": latest_reveal_context(conn, round_id),
        "touched_set": list_touched_set(conn, round_id),
        "transitions": list_transitions(conn, round_id),
        "predictions": preds,
        "evidence": list_evidence(conn, round_id),
        "resolutions": list(latest_resolutions(conn, round_id).values()),
        "predicate_checks": checks,
        "notes": list_notes(conn, round_id),
        "scorecard": latest_scorecard(conn, round_id),
        "synthetic_legs": __import__("harness.synthetic", fromlist=["list_synthetics"]).list_synthetics(conn, round_id),
        "pit_fetches": [dict(r) for r in conn.execute("SELECT * FROM pit_fetches WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "notebook_rows": [dict(r) for r in conn.execute("SELECT claim, row_json, recorded_at FROM notebook_rows WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "grid_cells": [dict(r) for r in conn.execute("SELECT * FROM grid_cells WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "scheduled_links": [dict(r) for r in conn.execute("SELECT * FROM scheduled_links WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "price_observations": [dict(r) for r in conn.execute("SELECT * FROM price_observations WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "coverage_migrations": [dict(r) for r in conn.execute("SELECT * FROM coverage_migrations WHERE round_id = ? ORDER BY rowid", (round_id,))],
        "chain_heads": chain_heads(conn),
        "firewall_note": "Claude Code rounds are hook-enforced (hook_denials ledger); chat rounds are soft: the wall is a promise there.",
    }
