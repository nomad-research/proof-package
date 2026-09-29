"""Tightening brief Part A: A1-A12."""
from datetime import date

import pytest

from harness import config, hypotheses, library, predicates, rounds, scorer
from harness.db import GENESIS_HASH, append, chain_heads, hash_row_v1, verify_chain
from harness.errors import ValidationError
from harness.hook import decide, is_retrieval_tool
from harness.util import canonical_json

from conftest import TEST_MODEL, TODAY, dated_evidence, make_round, make_rule, play_round, pred, res


# A1 / A2 / A3 --------------------------------------------------------------------

def test_q2_is_computed_and_classification_follows(conn):
    r = rounds.submit_event(conn, "ev", "2026-07-15", "s", "r", 0, {"Q1": "pass", "Q2": "pass: claimed by caller"},
                            operator_model=TEST_MODEL, today=TODAY)
    assert (r["round_class"], r["contamination"]) == ("clean", "none") and r["q2"].startswith("pass: computed")
    # event on or before cutoff -> q2_fail -> learning, automatically
    r = rounds.submit_event(conn, "old", "2026-06-30", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)
    assert (r["round_class"], r["contamination"]) == ("learning", "q2_fail")
    # unknown operator -> q2_unknown -> learning
    r = rounds.submit_event(conn, "who", "2026-07-15", "s", "r", 0, {"Q1": "pass"}, operator_model="mystery-model", today=TODAY)
    assert (r["round_class"], r["contamination"]) == ("learning", "q2_unknown") and r["operator_cutoff"] is None
    # clean cannot be claimed
    with pytest.raises(ValidationError, match="computed"):
        rounds.submit_event(conn, "x", "2026-07-15", "s", "r", 0, {"Q1": "pass"}, round_class="clean",
                            operator_model=TEST_MODEL, today=TODAY)


def test_clean_window_enforced_at_intake(conn):
    w = rounds.event_window(conn, TEST_MODEL, TODAY)
    assert (w["window_start"], w["window_end"]) == ("2026-07-01", "2026-08-10")
    with pytest.raises(ValidationError, match="outside the clean window"):
        rounds.submit_event(conn, "too recent", "2026-09-01", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)
    r = rounds.submit_event(conn, "too recent", "2026-09-01", "s", "r", 0, {"Q1": "pass"}, round_class="learning",
                            operator_model=TEST_MODEL, today=TODAY)
    assert (r["round_class"], r["contamination"]) == ("learning", "none")
    assert rounds.classification(conn, r["round_id"])["reason"].startswith("declared learning")


def test_peeked_voids_and_classification_supersedes(conn):
    rid = make_round(conn)
    rounds.void_round(conn, rid, "operator searched before lock", peeked=True)
    c = rounds.classification(conn, rid)
    assert c["contamination"] == "peeked" and rounds.round_state(conn, rid) == "void"
    hist = rounds.list_classifications(conn, rid)
    assert len(hist) == 2 and hist[1]["supersedes"] == hist[0]["id"]


def test_programme_stats_clean_by_default(conn):
    rule = make_rule(conn)
    play_round(conn, [pred(rule)], lambda ids: [res(ids[0])])
    play_round(conn, [pred(rule)], lambda ids: [res(ids[0], "miss", "wrong")], date="2026-06-01")   # learning
    clean = scorer.programme_stats(conn)
    both = scorer.programme_stats(conn, include_learning=True)
    assert (clean["rounds_scored"], clean["rounds_scored_clean"], clean["rounds_scored_learning"]) == (1, 1, 1)
    assert both["rounds_scored"] == 2 and sorted(both["mechanism_score"]["values"]) == [0.0, 1.0]


# A4 ----------------------------------------------------------------------------------

def test_falsifier_window_required_and_computed(conn):
    rid = make_round(conn)
    with pytest.raises(ValidationError, match="falsifier_window"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="null", target="none", claim="no-mechanism: x", falsifier_window=None)])
    with pytest.raises(ValidationError, match="falsifier_window must be"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="null", target="none", claim="no-mechanism: x", falsifier_window="soon")])
    rounds.lock_predictions(conn, rid, [
        pred(None, call_type="null", target="none", claim="no-mechanism: a", falsifier_window="days:10"),
        pred(None, call_type="predicate", claim="no-mechanism: b", falsifier_window="until:2026-12-31"),
        pred(None, claim="no-mechanism: c", lag_band="months"),
        pred(None, claim="no-mechanism: d", lag_band="never"),
    ])
    ends = [p["falsifier_window_end"] for p in rounds.list_predictions(conn, rid)]
    assert ends == ["2026-07-25", "2026-12-31", "2027-01-14", None]


def test_late_falsifier_recorded(conn):
    rule = make_rule(conn)
    rid, ids, card = play_round(conn, [pred(rule, call_type="null", target="none", claim="nothing", falsifier=None)],
                                lambda ids: [res(ids[0], late_falsifier=True, scorer_note="demerger after window")])
    r = rounds.latest_resolutions(conn, rid)[ids[0]]
    assert r["late_falsifier"] == 1 and r["scorer_note"].startswith("late_falsifier: ")
    assert card["per_call"][0]["late_falsifier"] is True


# A6 ----------------------------------------------------------------------------------

def test_source_coverage_required_on_miss_and_unverified(conn):
    rule = make_rule(conn)
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(rule)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    with pytest.raises(ValidationError, match="source_coverage is required"):
        scorer.score_round(conn, rid, [res(ids[0], "miss", "wrong", source_coverage=None)])
    with pytest.raises(ValidationError, match="cannot rest on source_coverage none"):
        scorer.score_round(conn, rid, [res(ids[0], "hit", source_coverage="none")])
    card = scorer.score_round(conn, rid, [res(ids[0], "miss", "wrong", source_coverage="english_only")])
    assert card["per_call"][0]["source_coverage"] == "english_only"


# A7 ----------------------------------------------------------------------------------

def test_first_traversal_needs_scope(conn):
    predicates.predicate_add(conn, "first traversal (event and node)", "arming", "s", "t", key="pred.arm.first_traversal")
    rid = make_round(conn)
    with pytest.raises(ValidationError, match="scope"):
        predicates.predicate_check(conn, rid, [{"predicate_id": "pred.arm.first_traversal", "claimed": "holds", "basis": "no prior news"}])
    r = predicates.predicate_check(conn, rid, [{"predicate_id": "pred.arm.first_traversal", "claimed": "holds", "scope": "event", "basis": "no site news in prior 30 days"},
                                               {"predicate_id": "pred.arm.first_traversal", "claimed": "fails", "scope": "node", "basis": "strike in March at the same dock"}])
    assert [c["scope"] for c in r["checks"]] == ["event", "node"]
    ev = rounds.submit_event(conn, "with node note", "2026-07-16", "s", "r", 0, {"Q1": "pass"},
                             node_recent_incidents="strike in March; leak in July", operator_model=TEST_MODEL, today=TODAY)
    assert rounds.export_round(conn, ev["round_id"])["event"]["node_recent_incidents"].startswith("strike")


# A9 / A11 --------------------------------------------------------------------------------

def test_criteria_supersede_and_chain_heads(conn):
    rid = make_round(conn)
    eid = rounds.round_status(conn, rid)["event_id"]
    r = rounds.criteria_supersede(conn, eid, {"Q1": "pass", "Q7": "pass: port notices were a carrier"}, "Q7 asks for a carrier, not a listed party")
    cur = rounds.current_criteria(conn, eid)
    assert cur["current"]["Q7"].startswith("pass") and cur["intake"].get("Q7") is None and len(cur["history"]) == 1
    r2 = rounds.criteria_supersede(conn, eid, {"Q1": "fail"}, "again")
    assert r2["supersedes"] == r["criteria_id"]
    exp = rounds.export_round(conn, rid)
    assert exp["event"]["criteria_json"]["Q1"] == "fail" and len(exp["criteria_history"]) == 2
    assert exp["chain_heads"] == chain_heads(conn) and exp["chain_heads"]["event_criteria"] == exp["criteria_history"][-1]["row_hash"]


# A12 ----------------------------------------------------------------------------------------

def test_quality_factors(conn):
    assert scorer.quality_hit("clean", "self", "adequate", "sign", "stated_dated") == pytest.approx(0.6)
    # v12 0.5: the round_class factor is gone. v11 A1 excludes learning resolutions from weights entirely, so scaling
    # them was dead code pretending to be a policy; a learning hit that reaches a weight at all would be a bug.
    assert scorer.quality_hit("learning", "self", "adequate", "sign", "stated_dated") == pytest.approx(0.6)
    assert scorer.quality_hit("clean", "human", "adequate", "sign", "stated_dated") == pytest.approx(1.0)
    assert scorer.quality_hit("clean", "self", "english_only", "null", "inferred") == pytest.approx(0.6 * 0.7 * 0.2 * 0.7)
    assert scorer.quality_miss("english_only", "sign", "none") == pytest.approx(0.49)
    assert scorer.quality_miss("adequate", "sign", "stated_dated") == pytest.approx(1.0)


def test_weight_propagates_and_validation_reads_it(conn):
    a = make_rule(conn)
    # clean, self-scored, dated evidence: 0.6 per hit
    for _ in range(2):
        rid = make_round(conn, text=f"e{_}")
        ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        e = dated_evidence(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[e])])
    r = library.get_rule(conn, a)
    assert r["weight"] == pytest.approx(1.2) and r["clean_hit_rounds"] == 2 and r["status"] == "validated"
    log = [dict(x) for x in conn.execute("SELECT * FROM narrowing_log WHERE object_id = ?", (a,))]
    assert log and log[-1]["decision"] == "candidate->validated" and log[-1]["weight_read"] == pytest.approx(1.2)
    # a discounted miss subtracts weight but does not block; an undiscounted miss blocks
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "wrong", source_coverage="english_only")], text="m1")
    r = library.get_rule(conn, a)
    assert r["weight"] == pytest.approx(1.2 - 0.49) and r["status"] == "candidate"   # weight fell under threshold
    rid = make_round(conn, text="e3")
    ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
    assert library.get_rule(conn, a)["weight"] == pytest.approx(1.31) and library.get_rule(conn, a)["status"] == "validated"
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "wrong")], text="m2")   # adequate coverage -> undiscounted
    assert library.get_rule(conn, a)["status"] == "candidate"


def test_learning_hits_and_nulls_do_not_validate(conn):
    a = make_rule(conn)
    for i in range(3):   # v11 A1: learning rounds are scored and recorded, and never enter a rule's weight
        rid = make_round(conn, text=f"l{i}", date="2026-05-01")
        ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
        assert rounds.latest_resolutions(conn, rid)[ids[0]]["outcome"] == "hit"      # the call is scored
    r = library.get_rule(conn, a)
    assert r["weight"] == 0.0 and r["trials"] == 0 and r["clean_hit_rounds"] == 0 and r["status"] == "candidate"
    b = make_rule(conn, "nulls only")
    for i in range(6):   # six clean null hits: 0.6*0.2*0.7 = 0.084 each -> never a positive hit
        play_round(conn, [pred(b, call_type="null", target="none", claim="nothing", falsifier=None)],
                   lambda ids: [res(ids[0])], text=f"n{i}")
    r = library.get_rule(conn, b)
    assert r["hits"] == 6 and r["status"] == "candidate" and r["weight"] < config.VALIDATION_THRESHOLD


def test_composition_capped_at_weakest_part(conn):
    a, b = make_rule(conn, "part a"), make_rule(conn, "part b")
    c = make_rule(conn, "composition of a and b", composed_of=[a, b])
    for i in range(2):
        rid = make_round(conn, text=f"c{i}")
        ids = rounds.lock_predictions(conn, rid, [pred(c), pred(a, target="a")])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        e = dated_evidence(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[e]), res(ids[1], evidence_ids=[e])])
    ra, rb, rc = (library.get_rule(conn, x) for x in (a, b, c))
    assert ra["weight"] == pytest.approx(1.2) and rb["weight"] == 0.0
    assert rc["weight"] == 0.0 and rc["status"] == "candidate"      # own 1.2, capped by b at 0


def test_hypothesis_arms_only_with_support(conn):
    arm = predicates.predicate_add(conn, "arm", "arming", "s", "t")["predicate_id"]
    weak = make_rule(conn, "weak rule")
    h = hypotheses.hypothesis_open(conn, "h", [], [weak], [arm], [], "f", "g")["hypothesis_id"]
    assert hypotheses.get_hypothesis(conn, h)["support_weight"] == 0.0
    r = hypotheses.hypothesis_check(conn, h, [{"predicate_id": arm, "observed": "holds"}])
    assert r["status"] == "open" and "not armed" in r["arming_note"]
    for i in range(2):
        rid = make_round(conn, text=f"w{i}")
        ids = rounds.lock_predictions(conn, rid, [pred(weak)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
    assert hypotheses.get_hypothesis(conn, h)["support_weight"] == pytest.approx(1.2)
    r = hypotheses.hypothesis_check(conn, h, [{"predicate_id": arm, "observed": "holds"}])
    assert r["status"] == "armed"
    # a later miss drops support under threshold; rebuild disarms and logs it
    play_round(conn, [pred(weak)], lambda ids: [res(ids[0], "miss", "wrong")], text="w-miss")
    hy = hypotheses.get_hypothesis(conn, h)
    assert hy["status"] == "open" and hy["arming_note"].startswith("disarmed")
    assert conn.execute("SELECT COUNT(*) FROM narrowing_log WHERE object_type='hypothesis' AND object_id=?", (h,)).fetchone()[0] >= 2
    # no mechanisms -> no support -> cannot arm
    h2 = hypotheses.hypothesis_open(conn, "h2", [], [], [arm], [], "f", "g")["hypothesis_id"]
    assert hypotheses.hypothesis_check(conn, h2, [{"predicate_id": arm, "observed": "holds"}])["status"] == "open"


def test_supersede_resolution_recomputes(conn):
    rule = make_rule(conn)
    rid, ids, card = play_round(conn, [pred(rule), pred(rule, target="b")],
                                lambda ids: [res(ids[0], "miss", "wrong"), res(ids[1])])
    assert card["mechanism_score"] == 0.5
    old = rounds.latest_resolutions(conn, rid)[ids[0]]["id"]
    with pytest.raises(ValidationError, match="supersedes must name"):
        scorer.supersede_resolution(conn, rid, res(ids[0], supersedes="wrong-id", scorer_note="x"))
    card2 = scorer.supersede_resolution(conn, rid, res(ids[0], late_falsifier=True, supersedes=old, scorer_note="falsifier fired outside window"))
    assert card2["mechanism_score"] == 1.0 and card2["superseded"] == old
    assert rounds.latest_resolutions(conn, rid)[ids[0]]["supersedes"] == old
    assert conn.execute("SELECT COUNT(*) FROM resolutions").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM scorecards WHERE round_id = ?", (rid,)).fetchone()[0] == 2
    assert library.get_rule(conn, rule)["misses"] == 0 and rounds.latest_scorecard(conn, rid)["mechanism_score"] == 1.0


# A10 ------------------------------------------------------------------------------------------

def test_hypothesis_schedule_and_due(conn):
    arm = predicates.predicate_add(conn, "arm", "arming", "s", "t")["predicate_id"]
    h = hypotheses.hypothesis_open(conn, "h", [], [], [arm], [], "f", "g")["hypothesis_id"]
    hypotheses.hypothesis_schedule(conn, h, "2026-09-14", "2026-10-28", 7)
    due = hypotheses.hypotheses_due(conn, today=date(2026, 9, 10))
    assert due["hypotheses"][0]["due"] is False and hypotheses.hypotheses_due(conn, today=date(2026, 9, 10), due_only=True)["count"] == 0
    assert hypotheses.hypotheses_due(conn, today=date(2026, 9, 14))["hypotheses"][0]["due"] is True
    hypotheses.hypothesis_check(conn, h, [{"predicate_id": arm, "observed": "unknown"}], today=date(2026, 9, 14))
    assert hypotheses.get_hypothesis(conn, h)["next_check_at"] == "2026-09-21"
    assert hypotheses.hypotheses_due(conn, today=date(2026, 11, 1))["hypotheses"][0]["hard_stop_passed"] is True


# A8 ---------------------------------------------------------------------------------------------

def test_hook_covers_mcp_surfaces_and_logs(tmp_path):
    from harness.db import connect
    db = tmp_path / "h.db"
    c = connect(db)
    rounds.model_cutoff_set(c, TEST_MODEL, "2026-06-30")
    assert is_retrieval_tool("WebFetch") and is_retrieval_tool("mcp__notion__notion-fetch") and is_retrieval_tool("mcp__Claude_Browser__navigate")
    assert not is_retrieval_tool("mcp__nomad__nomad_round_status") and not is_retrieval_tool("Read")
    assert decide(str(db), "Read") is None
    d = decide(str(db), "mcp__alphaxiv__discover_papers")
    assert d["hookSpecificOutput"]["permissionDecision"] == "deny" and "no rounds exist" in d["hookSpecificOutput"]["permissionDecisionReason"]
    rid = make_round(c)
    rule = make_rule(c)
    rounds.lock_predictions(c, rid, [pred(rule)])
    assert decide(str(db), "WebSearch")["hookSpecificOutput"]["permissionDecision"] == "deny"
    rounds.open_retrieval(c, rid)
    assert decide(str(db), "WebSearch") is None and decide(str(db), "mcp__notion__notion-search") is None
    denials = [dict(r) for r in c.execute("SELECT * FROM hook_denials ORDER BY rowid")]
    assert [x["tool"] for x in denials] == ["mcp__alphaxiv__discover_papers", "WebSearch"] and denials[1]["round_id"] == rid
    assert verify_chain(c, "hook_denials")["ok"]


# hash form compatibility --------------------------------------------------------------------------

def test_legacy_v1_rows_still_verify(conn):
    # write an orphan row the way the pre-tightening code did (all v1 columns, NULLs kept)
    row = {"id": "legacy-1", "raw_string": "X", "raw_norm": "x", "context": None, "round_id": None,
           "recorded_at": "2026-09-06T00:00:00Z"}
    h = hash_row_v1(GENESIS_HASH, row, "orphans")
    conn.execute("INSERT INTO orphans (id, raw_string, raw_norm, context, round_id, recorded_at, prev_row_hash, row_hash) "
                 "VALUES (?,?,?,?,?,?,?,?)", ("legacy-1", "X", "x", None, None, "2026-09-06T00:00:00Z", GENESIS_HASH, h))
    append(conn, "orphans", {"raw_string": "Y", "raw_norm": "y"})
    v = verify_chain(conn, "orphans")
    assert v["ok"] and v["tables"]["orphans"]["legacy_form_rows"] == 1
    conn.execute("DROP TRIGGER no_update_orphans")
    conn.execute("UPDATE orphans SET raw_string = 'tampered' WHERE id = 'legacy-1'")
    assert verify_chain(conn, "orphans")["first_break"]["id"] == "legacy-1"
