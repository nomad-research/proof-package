"""Library store (§4.6): rules, compositions, noun heuristic; stats and weight rebuilt from the ledgers (A5/A12).
v8 §A: every rule declares what it carries; a citation on a call of another kind is refused at lock and ignored at rebuild."""
import re
import sqlite3
from collections import defaultdict

from . import config
from .config import CARRIES, NOUN_ALLOWLIST, SENTENCE_STARTERS
from .db import append, get_row, insert_mutable, transaction
from .errors import NotFound, StateError, ValidationError
from .util import dumps, loads, now_iso

LAYERS = ("sequence", "transmission", "ownership", "operator", "other")
_WORD = re.compile(r"[A-Za-z][A-Za-z\-]*")
_CAP = re.compile(r"[A-Z][A-Za-z]+")

# §A1 backfill for the seeded and harvested rules (the human ratifies this table in one pass). Keyed rules by key,
# unkeyed harvested rules by the start of their text. Operator-layer rules carry nothing: they are records, not citations.
CARRIES_BACKFILL: dict[str, list[str]] = {
    "lib.chokepoint_premium": ["ordering", "occurrence"],
    "lib.supply_fear_fade": ["duration", "occurrence"],
    "lib.substitutes_gift": ["occurrence", "magnitude"],
    "lib.dark_factory_chain": ["ordering", "occurrence"],
    "lib.route_closure": ["occurrence", "magnitude"],
    "lib.escalation_words_cheap": ["occurrence", "duration"],
    "lib.visible_victim_overweight": ["absence", "magnitude"],
    "lib.force_majeure_fast_carrier": ["ordering"],
    "lib.region_locked_concentration": ["occurrence", "duration"],
    "lib.chain_lag": ["ordering", "duration", "occurrence"],
    "lib.coproduct_collateral": ["occurrence", "ordering"],
    "lib.feedstock_backwash": ["occurrence"],
    "lib.demand_slump_mute": ["magnitude"],
    "lib.congestion_memory": ["duration"],
    "lib.liability_periphery": ["absence"],
    "lib.novelty_channels_not_events": ["absence"],
    "lib.recurring_disruption_weather": ["absence"],
    "lib.late_crisis_resolution_side": ["occurrence"],
    "lib.headline_names_what_reopened": ["duration", "map"],
    "lib.cut_into_glut_silent": ["absence"],
    "lib.largest_where_substitution_hardest": ["magnitude", "ordering"],
    "lib.toll_booth_learns_first": ["ordering", "occurrence"],
    "lib.constraint_prices_deescalate_slowest": ["ordering", "duration"],
    "lib.wounded_owner_collects_premium": ["absence"],
    "lib.equity_visibility_ratio": ["absence", "magnitude"],
    "lib.lag_without_pureplay_spectacle": ["absence"],
    "lib.op_freshness_not_market": [],
    "lib.op_specialists_hold_map": [],
    "lib.op_overweights_famous": [],
    "lib.op_underweights_plumbing": [],
    "lib.comp.plant_outage_chain": ["ordering", "magnitude", "occurrence"],
    "lib.comp.chokepoint_late_crisis": ["ordering", "occurrence"],
    "lib.fm_needs_contracted_offtake": ["occurrence", "absence"],
    "lib.map_larger_operator_prior": ["map"],
}
CARRIES_BACKFILL_BY_TEXT: dict[str, list[str]] = {
    "a fatal industrial accident triggers a jurisdiction-wide inspection order": ["occurrence", "absence"],
    "tradability can arrive by corporate action after the event": ["absence"],
    "a plant revived from insolvency runs fewer units than its nameplate": ["map", "duration"],
    "for a fatal accident at a diversified owner, the attributable equity move": ["ordering", "absence"],
    "where offtake is a bilateral utility contract": ["ordering", "absence"],
    "a fire in one unit of an integrated site stops deliveries": ["occurrence", "map"],
    "a pre-existing logistics stop masks an outage": ["absence"],
    "the operator attaches a rule to a call the rule does not carry": [],
    "a single-supplier feedstock link is a hidden node": ["ordering", "occurrence"],
    "a tide sets the price of everything it touches": ["absence"],
    "a toxic release closes the whole shared space": ["map", "magnitude"],
    "knowing the rule is not applying it": [],
    "narrative and price diverge after a small shock": [],
}


def claim_kinds(call_type: str, sign: str | None) -> set[str]:
    """§A2: the kind of claim a call makes. Empty set = no carriage check (meta, narrative)."""
    if call_type == "sign":
        return {"absence"} if sign == "0" else {"occurrence"}
    if call_type == "null":
        return {"absence"}
    if call_type == "magnitude_order":
        return {"ordering", "magnitude"}
    if call_type == "lag_band":
        return {"duration"}
    if call_type == "map":
        return {"map"}
    if call_type == "predicate":
        return {"occurrence", "absence"}
    if call_type == "meta":
        return {"ordering", "magnitude"}   # v8 ruling: a one-trade or "largest move is" statement is an ordering claim
    return set()


def find_proper_nouns(text: str) -> list[str]:
    flagged: list[str] = []
    sentence_start = True
    for m in re.finditer(r"\S+", text):
        tok = m.group()
        word = _WORD.search(tok)
        ends = tok.endswith((".", "!", "?", ":", ";"))
        if word:
            w = word.group()
            if _CAP.fullmatch(w) and w not in NOUN_ALLOWLIST:
                if not (sentence_start and w.lower() in SENTENCE_STARTERS):
                    flagged.append(w)
        sentence_start = ends
    return flagged


def _fmt(r) -> dict:
    d = dict(r)
    d["composed_of"] = loads(d["composed_of"])
    d["carries"] = loads(d["carries"]) if d.get("carries") else None
    # v8 ruling: 0.0 from zero carried trials and 0.0 from a hit and a miss cancelling are different states
    d["trials_as_carried"] = d.get("trials", 0)
    d["weight_state"] = ("untested as carried" if not d.get("trials") else ("netted to zero" if d.get("weight") == 0 else "tested"))
    return d


def resolve_rule(conn: sqlite3.Connection, id_or_key: str) -> dict:
    r = conn.execute("SELECT * FROM library_rules WHERE id = ? OR key = ?", (id_or_key, id_or_key)).fetchone()
    if not r:
        raise NotFound(f"no library rule with id or key {id_or_key!r}; see nomad_library_query")
    return _fmt(r)


def resolve_rule_ids(conn: sqlite3.Connection, ids_or_keys: list[str]) -> list[str]:
    out, unknown = [], []
    for s in ids_or_keys:
        r = conn.execute("SELECT id FROM library_rules WHERE id = ? OR key = ?", (s, s)).fetchone()
        (out.append(r["id"]) if r else unknown.append(s))
    if unknown:
        raise ValidationError(
            f"unknown mechanism ids/keys {unknown}: cite existing library rules (nomad_library_query returns id and key) "
            "or propose them first with nomad_library_propose")
    return out


def backfill_lookup(key: str | None, rule_text: str) -> list[str] | None:
    if key and key in CARRIES_BACKFILL:
        return list(CARRIES_BACKFILL[key])
    low = rule_text.strip().lower()
    for prefix, kinds in CARRIES_BACKFILL_BY_TEXT.items():
        if low.startswith(prefix):
            return list(kinds)
    return None


def _validate_carries(carries, layer: str) -> list[str]:
    carries = [c.strip() for c in (carries or [])]
    bad = [c for c in carries if c not in CARRIES]
    if bad:
        raise ValidationError(f"carries must be drawn from {CARRIES}; got {bad}")
    if not carries and layer != "operator":
        raise ValidationError("carries is required: one or more of occurrence | absence | ordering | magnitude | duration | map "
                              "(what kind of claim this rule can be cited on). Operator-layer rules may carry nothing.")
    return sorted(set(carries))


def propose(conn: sqlite3.Connection, rule_text: str, forbids: str, obscurity: int, layer: str, provenance: str,
            composed_of: list[str] | None = None, round_id: str | None = None, key: str | None = None,
            carries: list[str] | None = None) -> dict:
    if not rule_text.strip():
        raise ValidationError("rule_text is required")
    if not forbids.strip():
        raise ValidationError("forbids is required: say what this rule says cannot happen")
    if not provenance.strip():
        raise ValidationError("provenance is required (nouns go here: which round, which event, which names)")
    if layer not in LAYERS:
        raise ValidationError(f"layer must be one of {LAYERS}")
    if not 1 <= int(obscurity) <= 5:
        raise ValidationError("obscurity must be 1..5")
    nouns = find_proper_nouns(rule_text)
    if nouns:
        raise ValidationError(
            f"rule_text looks like it names things: {nouns}. Rules carry mechanisms, not names. "
            "Move the nouns into provenance and restate the rule generically; if this is a false positive, "
            "write the rule in lower case.")
    if carries is None:
        carries = backfill_lookup(key, rule_text)
    carries = _validate_carries(carries, layer)
    composed_of = list(composed_of or [])
    if composed_of:
        if len(composed_of) < 2:
            raise ValidationError("a composition needs at least two part rule ids in composed_of")
        composed_of = resolve_rule_ids(conn, composed_of)
    if round_id and not conn.execute("SELECT 1 FROM rounds WHERE id = ?", (round_id,)).fetchone():
        raise NotFound(f"no round {round_id!r}")
    if key:
        key = key.strip()
        if conn.execute("SELECT 1 FROM library_rules WHERE key = ?", (key,)).fetchone():
            raise ValidationError(f"library rule key {key!r} already exists")
    row = insert_mutable(conn, "library_rules", {
        "rule_text": rule_text.strip(), "forbids": forbids.strip(), "obscurity": int(obscurity), "layer": layer,
        "status": "candidate", "composed_of": dumps(composed_of), "provenance": provenance.strip(),
        "proposed_in_round": round_id, "key": key or None, "carries": dumps(carries),
    })
    return {"rule_id": row["id"], "key": key or None, "status": "candidate", "is_composition": bool(composed_of), "carries": carries}


def backfill_carries(conn: sqlite3.Connection) -> dict:
    """§A1: set carries on rules that predate it. Returns what was set and what could not be matched."""
    done, unmatched = [], []
    for r in conn.execute("SELECT id, key, rule_text, layer FROM library_rules WHERE carries IS NULL ORDER BY rowid").fetchall():
        kinds = backfill_lookup(r["key"], r["rule_text"])
        if kinds is None and r["layer"] == "operator":
            kinds = []
        if kinds is None:
            unmatched.append({"id": r["id"], "key": r["key"], "rule_text": r["rule_text"][:80]})
            continue
        conn.execute("UPDATE library_rules SET carries = ? WHERE id = ?", (dumps(sorted(set(kinds))), r["id"]))
        done.append({"id": r["id"], "key": r["key"], "carries": sorted(set(kinds))})
    return {"set": done, "unmatched": unmatched}


def set_carries(conn: sqlite3.Connection, rule_id: str, carries: list[str]) -> dict:
    rule = resolve_rule(conn, rule_id)
    carries = _validate_carries(carries, rule["layer"])
    conn.execute("UPDATE library_rules SET carries = ? WHERE id = ?", (dumps(carries), rule["id"]))
    return {"rule_id": rule["id"], "key": rule["key"], "carries": carries}


def check_citation(rule: dict, call_type: str, sign: str | None) -> str | None:
    """§A2: None when the rule carries the call's claim kind; else the refusal message."""
    kinds = claim_kinds(call_type, sign)
    if not kinds:
        return None
    carries = rule.get("carries") or []
    if kinds & set(carries):
        return None
    name = rule.get("key") or rule["id"]
    return (f"rule {name} carries {carries}; this call is {sorted(kinds)}; cite a rule that carries it or use "
            f"'no-mechanism: <why>' in the claim")


def get_rule(conn: sqlite3.Connection, rule_id: str) -> dict:
    return resolve_rule(conn, rule_id)


def query(conn: sqlite3.Connection, text: str | None = None, layer: str | None = None,
          status: str | None = None, limit: int = 20, carries: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM library_rules WHERE 1=1", []
    if text:
        like = f"%{text}%"
        sql += " AND (rule_text LIKE ? OR forbids LIKE ? OR provenance LIKE ? OR key LIKE ?)"
        args += [like, like, like, like]
    if layer:
        sql += " AND layer = ?"
        args.append(layer)
    if status:
        sql += " AND status = ?"
        args.append(status)
    if carries:
        sql += " AND carries LIKE ?"
        args.append(f'%"{carries}"%')
    sql += " ORDER BY rowid LIMIT ?"
    args.append(int(limit))
    return [_fmt(r) for r in conn.execute(sql, args)]


def retire(conn: sqlite3.Connection, rule_id: str, reason: str, superseded_by: str | None = None) -> dict:
    rule = get_rule(conn, rule_id)
    rule_id = rule["id"]
    if rule["status"] == "retired":
        raise StateError(f"rule {rule_id} is already retired ({rule['retired_reason']!r})")
    if not reason.strip():
        raise ValidationError("a reason is required to retire a rule")
    if superseded_by:
        superseded_by = resolve_rule(conn, superseded_by)["id"]
    conn.execute("UPDATE library_rules SET status = 'retired', retired_reason = ?, superseded_by = ? WHERE id = ?",
                 (reason.strip(), superseded_by, rule_id))
    return {"rule_id": rule_id, "key": rule["key"], "status": "retired", "superseded_by": superseded_by}


def log_narrowing(conn: sqlite3.Connection, object_type: str, object_id: str, decision: str,
                  weight_read: float | None, threshold: float | None, detail: str | None = None) -> None:
    append(conn, "narrowing_log", {"object_type": object_type, "object_id": object_id, "decision": decision,
                                   "weight_read": weight_read, "threshold": threshold, "detail": detail})


def _resolved_rows(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """Latest resolution per prediction with the round class and a recomputed quality (pure function of ledgers).
    C1: rows disputed by a second scorer and not human-ruled are returned separately and never enter the stats."""
    from .scorer import evidence_class, resolution_quality
    rows = conn.execute(
        "SELECT p.id AS prediction_id, p.round_id, p.call_type, p.sign, p.mechanism_ids, r.outcome, r.quarantined, r.weight, "
        "r.mechanism_outcome, r.scorer, r.source_coverage, r.evidence_ids, r.evidence_class, c.round_class, "
        "s.outcome AS s_outcome, s.mechanism_outcome AS s_mechanism "
        "FROM predictions p JOIN resolutions r ON r.rowid = ("
        "  SELECT rowid FROM resolutions WHERE prediction_id = p.id ORDER BY rowid DESC LIMIT 1) "
        "JOIN round_classification c ON c.round_id = p.round_id "
        "LEFT JOIN second_scores s ON s.rowid = ("
        "  SELECT rowid FROM second_scores WHERE prediction_id = p.id ORDER BY rowid DESC LIMIT 1)"
    ).fetchall()
    out, disputed = [], []
    for r in rows:
        d = dict(r)
        d["mechanism_ids"] = loads(d["mechanism_ids"]) or []
        ev_class = d["evidence_class"] or evidence_class(conn, loads(d["evidence_ids"]) or [])
        d["evidence_class"] = ev_class
        d["quality"] = resolution_quality(d["round_class"], d["outcome"], bool(d["quarantined"]), d["scorer"],
                                          d["source_coverage"], d["call_type"], ev_class)
        d["undiscounted"] = d["source_coverage"] in (None, "adequate")
        is_disputed = (d["s_outcome"] is not None and d["scorer"] != "human"
                       and (d["s_outcome"] != d["outcome"] or d["s_mechanism"] != d["mechanism_outcome"]))
        (disputed if is_disputed else out).append(d)
    return out, disputed


def rebuild_library_stats(conn: sqlite3.Connection) -> dict:
    """Recompute counters, propagated weight, review flags, candidate/validated status and hypothesis support
    from the ledgers. library_rules is a view over resolutions; this is the only writer of its numbers."""
    T = config.VALIDATION_THRESHOLD
    rows, disputed = _resolved_rows(conn)
    rules = {r["id"]: r for r in (_fmt(x) for x in conn.execute("SELECT * FROM library_rules ORDER BY rowid"))}
    disputes_per_rule: dict[str, int] = defaultdict(int)
    for d in disputed:
        for rid in d["mechanism_ids"]:
            disputes_per_rule[rid] += 1
    blank = lambda: {"hits": 0, "misses": 0, "false_alarms": 0, "trials": 0, "hit_w": 0.0, "miss_w": 0.0,
                     "clean_hit_rounds": set(), "positive_hit": False, "undiscounted_misses": 0, "misreads": 0}
    stats: dict[str, dict] = defaultdict(blank)
    excluded_citations = 0
    excluded_per_rule: dict[str, int] = defaultdict(int)
    learning_excluded = 0
    for r in rows:
        if r["round_class"] != "clean":
            # v11 A1: a learning round's calls are recorded and scored; their resolutions never enter rule weights,
            # validation or calibration. Only their measurements count (risk-engine views, K5).
            learning_excluded += len(r["mechanism_ids"])
            continue
        if (r.get("weight") or 0) == 0 and r["outcome"] == "untestable":
            continue   # B1: rows on a branch that did not arise
        if r["call_type"] == "narrative":
            continue   # v8 F1: a narrative row measures what a channel said; it is never a trial of a rule
        hit = r["outcome"] == "hit"
        miss = r["outcome"] == "miss"
        clean_hit = hit and not r["quarantined"]
        # A13: a miss with the mechanism right is an operator misread; the rule is not debited (mirror of quarantine)
        misread = miss and r["mechanism_outcome"] == "right"
        for rid in r["mechanism_ids"]:
            rule = rules.get(rid)
            # §A2 retroactively: a citation on a kind the rule does not carry is not a trial of the rule
            if rule is None or check_citation(rule, r["call_type"], r["sign"]) is not None:
                excluded_citations += 1
                excluded_per_rule[rid] += 1
                continue
            s = stats[rid]
            s["trials"] += 1
            if clean_hit:
                s["hits"] += 1
                s["hit_w"] += r["quality"] or 0.0
                if r["round_class"] == "clean":
                    s["clean_hit_rounds"].add(r["round_id"])
                # C1: a qualifying positive hit is non-null, mechanism right, adequate coverage, clean round
                if (r["call_type"] != "null" and r["mechanism_outcome"] == "right" and r["undiscounted"]
                        and r["round_class"] == "clean"):
                    s["positive_hit"] = True
            if misread:
                s["misreads"] += 1
            elif miss:
                s["misses"] += 1
                s["miss_w"] += r["quality"] or 0.0
                if r["undiscounted"]:
                    s["undiscounted_misses"] += 1
                if r["call_type"] in ("sign", "magnitude_order"):
                    s["false_alarms"] += 1
    own_weight = {rid: round(stats[rid]["hit_w"] - stats[rid]["miss_w"], 6) if rid in stats else 0.0 for rid in rules}

    def weight_of(rid: str, seen=()) -> float:
        rule = rules[rid]
        w = own_weight[rid]
        if rule["composed_of"] and rid not in seen:
            cap = min(weight_of(p, seen + (rid,)) for p in rule["composed_of"] if p in rules)
            w = min(w, cap)
        return round(w, 6)

    validated, flagged, changes = [], [], []
    with transaction(conn):
        for rid, rule in rules.items():
            s = stats.get(rid, blank())
            w = weight_of(rid)
            if rule["status"] == "retired":
                status = "retired"
            elif (w >= T and len(s["clean_hit_rounds"]) >= 2 and s["undiscounted_misses"] == 0 and s["positive_hit"]):
                status = "validated"
                validated.append(rid)
            else:
                status = "candidate"
            review = 0
            if rule["composed_of"]:
                review = int(any(stats.get(pid, {}).get("misses", 0) > 0 for pid in rule["composed_of"]))
                if review:
                    flagged.append(rid)
            if status != rule["status"]:
                changes.append((rid, rule["status"], status))
                log_narrowing(conn, "library_rule", rid, f"{rule['status']}->{status}", w, T,
                              f"clean_hit_rounds={len(s['clean_hit_rounds'])} undiscounted_misses={s['undiscounted_misses']} "
                              f"qualifying_positive_hit={s['positive_hit']} hit_w={round(s['hit_w'], 6)} miss_w={round(s['miss_w'], 6)} "
                              f"misreads={s['misreads']}")
            conn.execute(
                "UPDATE library_rules SET hits=?, misses=?, false_alarms=?, trials=?, status=?, review_flag=?, weight=?, "
                "clean_hit_rounds=?, citations_excluded=? WHERE id=?",
                (s["hits"], s["misses"], s["false_alarms"], s["trials"], status, review, w, len(s["clean_hit_rounds"]),
                 excluded_per_rule.get(rid, 0), rid))
        # hypotheses: support weight is the weakest cited rule, or (D1) the spawning factor's evidence quality
        demoted = []
        for h in conn.execute("SELECT id, mechanism_ids, status, support_weight, spawned_from_prediction_id, "
                              "spawned_from_factor_index FROM hypotheses").fetchall():
            if h["spawned_from_prediction_id"]:
                support = factor_support(conn, h["spawned_from_prediction_id"], h["spawned_from_factor_index"])
            else:
                mids = [m for m in (loads(h["mechanism_ids"]) or []) if m in rules]
                support = round(min(weight_of(m) for m in mids), 6) if mids else None
            conn.execute("UPDATE hypotheses SET support_weight = ? WHERE id = ?", (support, h["id"]))
            if h["status"] == "armed" and (support is None or support < T):
                conn.execute("UPDATE hypotheses SET status = 'open', status_changed_at = ?, arming_note = ? WHERE id = ?",
                             (now_iso(), f"disarmed: support_weight {support} < threshold {T}", h["id"]))
                log_narrowing(conn, "hypothesis", h["id"], "armed->open", support, T, "support weight below threshold at rebuild")
                demoted.append(h["id"])
    return {"rules": len(rules), "resolved_predictions": len(rows), "disputes_pending": len(disputed),
            "citations_excluded_learning": learning_excluded,
            "disputes_pending_per_rule": {rules[r]["key"] or r: n for r, n in disputes_per_rule.items() if r in rules},
            "citations_excluded_by_carriage": excluded_citations,
            "validated": validated, "review_flagged": flagged, "status_changes": changes, "hypotheses_disarmed": demoted,
            "validation_threshold": T, "rebuilt_at": now_iso()}


def factor_support(conn: sqlite3.Connection, prediction_id: str, factor_index: int | None) -> float | None:
    """D1: a spawned hypothesis inherits the factor's evidence quality, not the parent claim's outcome."""
    from .scorer import evidence_class, quality_hit
    f = conn.execute("SELECT id FROM prediction_factors WHERE prediction_id = ? AND idx = ?", (prediction_id, factor_index or 0)).fetchone()
    if not f:
        return None
    fr = conn.execute("SELECT * FROM factor_resolutions WHERE factor_id = ? ORDER BY rowid DESC LIMIT 1", (f["id"],)).fetchone()
    if not fr:
        return 0.0
    if fr["outcome"] != "hit":
        return 0.0
    cls = conn.execute("SELECT c.round_class FROM predictions p JOIN round_classification c ON c.round_id = p.round_id WHERE p.id = ?",
                       (prediction_id,)).fetchone()
    ev_class = evidence_class(conn, loads(fr["evidence_ids"]) or [])
    return quality_hit(cls["round_class"] if cls else "learning", fr["scorer"] or "self", "adequate", "positive", ev_class)
