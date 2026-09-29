"""Spec §9 tests 1-10 plus the §10 acceptance checks that can run headless."""
import json
import sqlite3

import pytest

from harness import hypotheses, library, names, positions, predicates, rounds, scorer, t0
from harness.config import NULL_CALL_WEIGHT
from harness.db import LEDGER_TABLES, append, verify_chain
from harness.errors import HarnessError, StateError, ValidationError
from harness.library import find_proper_nouns

from conftest import make_round, make_rule, play_round, pred, res


# 1. Append-only ---------------------------------------------------------------

def test_append_only_triggers_block_update_and_delete(conn):
    rid = make_round(conn)
    for table, where in (("events", "1=1"), ("rounds", f"id='{rid}'"), ("round_transitions", "1=1")):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute(f"UPDATE {table} SET recorded_at = 'x' WHERE {where}")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute(f"DELETE FROM {table} WHERE {where}")
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_every_ledger_table_has_triggers(conn):
    names_ = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    for t in LEDGER_TABLES:
        assert f"no_update_{t}" in names_ and f"no_delete_{t}" in names_


def test_no_mutating_tools_on_api_surface():
    from harness.server import mcp
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert tool_names and all(n.startswith("nomad_") for n in tool_names)
    assert not [n for n in tool_names if "update" in n or "delete" in n or "edit" in n]


# 2. Hash chain ----------------------------------------------------------------

def test_hash_chain_detects_tamper_at_right_row(conn):
    for i in range(3):
        make_round(conn, text=f"event {i}")
    assert verify_chain(conn)["ok"]
    conn.execute("DROP TRIGGER no_update_events")
    conn.execute("UPDATE events SET event_text = 'tampered' WHERE rowid = 2")
    r = verify_chain(conn, "events")
    assert not r["ok"]
    assert r["first_break"]["rowid"] == 2 and "tampered" in r["first_break"]["reason"]
    # chained tables are independent: rounds still ok, and the all-tables walk reports the same first break
    assert verify_chain(conn, "rounds")["ok"]
    assert verify_chain(conn)["first_break"]["table"] == "events"


def test_hash_chain_detects_relinking(conn):
    for i in range(3):
        make_round(conn, text=f"event {i}")
    conn.execute("DROP TRIGGER no_update_events")
    conn.execute("UPDATE events SET prev_row_hash = 'f'*64 WHERE rowid = 3")
    r = verify_chain(conn, "events")
    assert r["first_break"]["rowid"] == 3 and "chain broken" in r["first_break"]["reason"]


def test_verify_chain_rejects_non_ledger(conn):
    with pytest.raises(HarnessError):
        verify_chain(conn, "library_rules")


# 3. Firewall ------------------------------------------------------------------

def test_firewall_order(conn):
    rule = make_rule(conn)
    rid = make_round(conn)
    with pytest.raises(StateError, match="nomad_lock_predictions"):
        rounds.open_retrieval(conn, rid)
    rounds.lock_predictions(conn, rid, [pred(rule)])
    assert rounds.round_state(conn, rid) == "locked"
    with pytest.raises(StateError, match="nomad_open_retrieval"):
        rounds.add_evidence(conn, rid, "https://x", "t", "e")
    with pytest.raises(StateError):
        scorer.score_round(conn, rid, [])
    # more predictions may be added while locked
    rounds.lock_predictions(conn, rid, [pred(rule, target="freight")])
    rounds.open_retrieval(conn, rid)
    with pytest.raises(StateError, match="frozen"):
        rounds.lock_predictions(conn, rid, [pred(rule)])
    ev = rounds.add_evidence(conn, rid, "https://x", "t", "e", source_time="2026-09-02")
    assert ev["evidence_id"]
    st = rounds.round_status(conn, rid)
    assert st["state"] == "open" and st["counts"] == {"predictions": 2, "evidence": 1, "resolutions": 0, "predicate_checks": 0, "touched_set": 0}
    assert [t["to_state"] for t in st["transitions"]] == ["created", "locked", "open"]


def test_reveal_returns_only_text_and_date_and_logs(conn):
    rid = make_round(conn)
    r = rounds.reveal_event(conn, rid)
    assert set(r) == {"round_id", "event_text", "event_date", "state", "context", "context_summary"}   # B5: store context, never the web
    assert rounds.list_transitions(conn, rid)[-1]["reason"] == "revealed"
    assert rounds.round_state(conn, rid) == "created"


def test_void_from_any_state_keeps_rows(conn):
    rid = make_round(conn)
    rounds.void_round(conn, rid, "contaminated")
    assert rounds.round_state(conn, rid) == "void"
    with pytest.raises(StateError):
        rounds.lock_predictions(conn, rid, [pred(None, claim="no-mechanism: void test")])
    assert conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0] == 1


def test_prediction_validation(conn):
    rid = make_round(conn)
    with pytest.raises(ValidationError, match="carrier"):
        rounds.lock_predictions(conn, rid, [pred(None, carrier=None, claim="no-mechanism: x")])
    with pytest.raises(ValidationError, match="falsifier"):
        rounds.lock_predictions(conn, rid, [pred(None, falsifier=None, claim="no-mechanism: x")])
    with pytest.raises(ValidationError, match="no-mechanism"):
        rounds.lock_predictions(conn, rid, [pred(None)])
    with pytest.raises(ValidationError, match='target="none"'):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="null", claim="no-mechanism: nothing moves")])
    with pytest.raises(ValidationError, match="unknown mechanism ids"):
        rounds.lock_predictions(conn, rid, [pred("nope")])
    ok = rounds.lock_predictions(conn, rid, [pred(None, call_type="null", target="none", claim="no-mechanism: nothing moves")])
    assert len(ok["prediction_ids"]) == 1


# 4. Scorer --------------------------------------------------------------------

def test_scorer_hand_computation(conn):
    rule = make_rule(conn)
    preds = [pred(rule), pred(rule, target="freight"), pred(rule, target="cargo"),
             pred(rule, call_type="null", target="none", claim="nothing else moves", falsifier=None)]

    def resolutions(ids):
        return [res(ids[0], "hit", "right", "hit"),
                res(ids[1], "miss", "wrong", "miss"),
                res(ids[2], "hit", "wrong", "hit"),       # quarantined
                res(ids[3], "hit", "right", "miss")]      # null hit, weight 0.2

    rid, ids, card = play_round(conn, preds, resolutions)
    assert card["sum_weight"] == pytest.approx(3.2)
    assert card["outcome_score"] == pytest.approx(2.2 / 3.2)
    assert card["mechanism_score"] == pytest.approx(1.2 / 3.2)
    assert card["baseline_score"] == pytest.approx(2.0 / 3.2)
    assert card["edge_vs_baseline"] == pytest.approx(1.2 / 3.2 - 2.0 / 3.2)
    assert [c["weight"] for c in card["per_call"]] == [1.0, 1.0, 1.0, NULL_CALL_WEIGHT]
    assert [c["quarantined"] for c in card["per_call"]] == [False, False, True, False]
    assert card["null_called"] and card["n_quarantined"] == 1 and card["null_call_weight"] == NULL_CALL_WEIGHT
    assert rounds.round_state(conn, rid) == "scored"
    # stored with the round and recomputable from ledgers
    stored = rounds.latest_scorecard(conn, rid)
    recomputed = scorer.compute_scorecard(conn, rid)
    for k in ("outcome_score", "mechanism_score", "baseline_score", "edge_vs_baseline"):
        assert stored[k] == recomputed[k]
    assert conn.execute("SELECT DISTINCT null_call_weight FROM resolutions").fetchall()[0][0] == NULL_CALL_WEIGHT
    assert verify_chain(conn)["ok"]


def test_scorer_requires_one_resolution_per_prediction(conn):
    rule = make_rule(conn)
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(rule), pred(rule, target="b")])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    with pytest.raises(ValidationError, match=ids[1]):
        scorer.score_round(conn, rid, [res(ids[0])])
    with pytest.raises(ValidationError, match="duplicate"):
        scorer.score_round(conn, rid, [res(ids[0]), res(ids[0]), res(ids[1])])
    with pytest.raises(ValidationError, match="evidence ids"):
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=["ghost"]), res(ids[1])])


def test_untestable_excluded_unverified_in_denominator(conn):
    rule = make_rule(conn)
    rid, ids, card = play_round(conn, [pred(rule), pred(rule, target="b"), pred(rule, target="c")],
                                lambda ids: [res(ids[0], "hit"), res(ids[1], "untestable", "unknown", "unverified"),
                                             res(ids[2], "unverified", "unknown", "unverified")])
    assert card["outcome_score"] == pytest.approx(0.5)
    assert card["untestable_frac"] == pytest.approx(1 / 3) and card["unverified_frac"] == pytest.approx(1 / 3)


# 5. Noun heuristic -------------------------------------------------------------

@pytest.mark.parametrize("text,ok", [
    ("The toll booth learns before the cargo", True),
    ("Hormuz insurance repriced first", False),
    ("AI operators wake fresh", True),
    ("Insurance reprices before cargo when Lloyds moves", False),
    ("insurance reprices before cargo", True),
    ("Constraint prices de-escalate slowest. The premium lags.", True),
])
def test_noun_heuristic(conn, text, ok):
    assert (find_proper_nouns(text) == []) is ok
    if ok:
        assert library.propose(conn, text, "x", 2, "sequence", "Hormuz round 1", carries=["occurrence"])["status"] == "candidate"
    else:
        with pytest.raises(ValidationError, match="provenance"):
            library.propose(conn, text, "x", 2, "sequence", "Hormuz round 1", carries=["occurrence"])


# 6. Composition ----------------------------------------------------------------

def test_composition_stats_independent_of_parts(conn):
    a = make_rule(conn, "the toll learns first")
    b = make_rule(conn, "the cargo learns last")
    c = make_rule(conn, "the toll learns first and the cargo last", composed_of=[a, b])
    assert library.get_rule(conn, c)["composed_of"] == [a, b]
    play_round(conn, [pred(c)], lambda ids: [res(ids[0], "hit", "right")])
    ra, rb, rc = (library.get_rule(conn, x) for x in (a, b, c))
    assert (ra["trials"], ra["hits"]) == (0, 0) and (rb["trials"], rb["hits"]) == (0, 0)
    assert (rc["trials"], rc["hits"], rc["misses"], rc["review_flag"]) == (1, 1, 0, 0)
    # a part's miss flags the composition for review, and is a false alarm on a sign call
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "wrong")])
    ra, rc = library.get_rule(conn, a), library.get_rule(conn, c)
    assert (ra["trials"], ra["misses"], ra["false_alarms"]) == (1, 1, 1)
    assert rc["review_flag"] == 1 and rc["hits"] == 1


def test_validation_needs_two_clean_hits_in_two_rounds(conn):
    a = make_rule(conn)
    # undated evidence class: 0.6 * 0.7 = 0.42 per clean self-scored hit
    play_round(conn, [pred(a), pred(a, target="b")], lambda ids: [res(ids[0], "hit"), res(ids[1], "hit")])
    assert library.get_rule(conn, a)["status"] == "candidate"     # 0.84 in one round
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "hit", "wrong")])   # quarantined: not a clean hit
    assert library.get_rule(conn, a)["status"] == "candidate"
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "hit")])
    r = library.get_rule(conn, a)
    assert r["status"] == "validated" and r["weight"] == pytest.approx(1.26) and r["clean_hit_rounds"] == 2
    library.retire(conn, a, "superseded in test")
    assert library.get_rule(conn, a)["status"] == "retired"
    library.rebuild_library_stats(conn)
    assert library.get_rule(conn, a)["status"] == "retired"


# acceptance: stats rebuild from ledgers is a pure function
def test_rebuild_from_scratch_gives_identical_numbers(conn):
    a, b = make_rule(conn, "the toll learns first"), make_rule(conn, "the cargo learns last")
    play_round(conn, [pred(a), pred(b, target="b"), pred(a, target="none", call_type="null", claim="none", falsifier=None)],
               lambda ids: [res(ids[0], "hit"), res(ids[1], "miss", "wrong"), res(ids[2], "hit", "wrong")])
    before = {r["id"]: (r["hits"], r["misses"], r["false_alarms"], r["trials"], r["status"], r["review_flag"])
              for r in library.query(conn)}
    conn.execute("UPDATE library_rules SET hits=0, misses=0, false_alarms=0, trials=0, status='candidate', review_flag=0")
    library.rebuild_library_stats(conn)
    after = {r["id"]: (r["hits"], r["misses"], r["false_alarms"], r["trials"], r["status"], r["review_flag"])
             for r in library.query(conn)}
    # a: one clean hit + one quarantined null hit -> 1 hit, 2 trials; b: a miss on a sign call -> false alarm
    assert before == after and before[a] == (1, 0, 0, 2, "candidate", 0) and before[b] == (0, 1, 1, 1, "candidate", 0)


# 7. T0 count ------------------------------------------------------------------

def test_t0_count(conn):
    t0.submit_candidate(conn, "e1", "w1", True, arming_pass=True, listed_party="P1", carrier="C1")
    t0.submit_candidate(conn, "e2", "w1", True, arming_pass=False, listed_party="P2", carrier="C1")
    t0.submit_candidate(conn, "e1", "w1", False, listed_party="P1", carrier="C1")   # duplicate triple
    t0.submit_candidate(conn, "e9", "w2", True, arming_pass=True, arming_pass_pair=True, listed_party="P9", carrier="C9")
    c = t0.count(conn, "w1")
    assert (c["candidates"], c["criteria_pass"], c["arming_pass"], c["distinct_triples"]) == (3, 2, 1, 2)
    assert c["distinct_events"] == 2 and c["arming_pass_pair"] == 0
    assert t0.count(conn, "w2")["arming_pass_pair"] == 1


# 8. Names book ----------------------------------------------------------------

def test_names_book_resolution(conn):
    lyb = names.holder_upsert(conn, "LyondellBasell Industries N.V.", "company", listed=True, ticker="LYB",
                              aliases=["LyondellBasell"])["holder_id"]
    plant = names.holder_upsert(conn, "Bayport Choate", "plant", parent_id=lyb,
                                aliases=[{"alias": "LyondellBasell Bayport Choate", "alias_kind": "plant_name"}])["holder_id"]
    r = names.resolve(conn, "LyondellBasell Industries N.V.")
    assert r["resolved"] and r["holder_id"] == lyb
    assert names.resolve(conn, "lyondellbasell industries nv")["holder_id"] == lyb
    assert names.resolve(conn, "LYB")["holder_id"] == lyb
    p = names.resolve(conn, "Bayport Choate")
    assert p["resolved"] and p["holder_id"] == plant and p["holder"]["parent"]["holder_id"] == lyb
    o = names.resolve(conn, "Acme Foam LLC", context="round 4 supplier list")
    assert not o["resolved"] and o["status"] == "unresolved" and o["orphan_id"]
    q = names.orphans(conn)
    assert q["unresolved"] == 1 and q["orphans"][0]["raw_string"] == "Acme Foam LLC"
    # clearing the queue: link the name, and it drops out
    acme = names.holder_upsert(conn, "Acme Foam", "company", aliases=["Acme Foam LLC"])["holder_id"]
    assert names.resolve(conn, "Acme Foam LLC")["holder_id"] == acme
    assert names.orphans(conn)["unresolved"] == 0
    # upsert is idempotent and aliases are append-only
    again = names.holder_upsert(conn, "LyondellBasell Industries, N.V.", "company", listed=True)
    assert again["holder_id"] == lyb and not again["created"]
    with pytest.raises(ValidationError, match="already"):
        names.holder_upsert(conn, "Other Co", "company", aliases=["LYB"])
    assert verify_chain(conn, "aliases")["ok"] and verify_chain(conn, "orphans")["ok"]


# 9. Positions + pair gate --------------------------------------------------------

def test_positions_pair_gate_and_self_hedge(conn):
    a = names.holder_upsert(conn, "Alpha Plc", "company", listed=True, ticker="ALP")["holder_id"]
    b = names.holder_upsert(conn, "Beta Inc", "company", listed=True, ticker="BET")["holder_id"]
    c = names.holder_upsert(conn, "Gamma AG", "company", listed=True, ticker="GAM")["holder_id"]
    d = names.holder_upsert(conn, "Delta Private", "company", listed=False)["holder_id"]
    positions.position_add(conn, a, "Node X", "sign_of_exposure", "+", "filing", "stated")
    positions.position_add(conn, a, "node x", "tier", "1", "filing", "stated")
    positions.position_add(conn, b, "node x", "sign_of_exposure", "-", "call", "inferred")
    positions.position_add(conn, c, "node x", "sign_of_exposure", "+", "filing", "stated")
    positions.position_add(conn, c, "node x", "sign_of_exposure", "-", "filing", "stated")   # owner of substitutes
    positions.position_add(conn, d, "node x", "sign_of_exposure", "-", "news", "implicit")
    r = positions.positions_on_node(conn, "node x")
    assert len(r["holders"]) == 4 and r["pair_gate"]
    assert [(p["plus"]["holder_id"], p["minus"]["holder_id"]) for p in r["pairs"]] == [(a, b)]
    assert r["pairs"][0]["position_difference"]["tier"] == {"plus": ["1"], "minus": None}
    assert [h["holder_id"] for h in r["self_hedged"]] == [c]
    assert [h["holder_id"] for h in positions.positions_on_node(conn, "node x", listed_only=True)["holders"]] == [a, b, c]
    # supersession: a new fact replaces the old without an UPDATE
    old = [p for p in r["holders"] if p["holder_id"] == b][0]["positions"][0]["id"]
    positions.position_add(conn, b, "node x", "sign_of_exposure", "+", "restated", "stated", supersedes=old)
    r2 = positions.positions_on_node(conn, "node x")
    assert r2["pairs"] == [] and not r2["pair_gate"]
    with pytest.raises(ValidationError):
        positions.position_add(conn, a, "node x", "sign_of_exposure", "up", "x", "stated")


# 10. Hypothesis lifecycle -------------------------------------------------------

def test_hypothesis_lifecycle(conn):
    from conftest import dated_evidence
    a1 = predicates.predicate_add(conn, "arm_one", "arming", "src", "t")["predicate_id"]
    a2 = predicates.predicate_add(conn, "arm_two", "arming", "src", "t")["predicate_id"]
    d1 = predicates.predicate_add(conn, "disarm_one", "disarming", "src", "t")["predicate_id"]
    with pytest.raises(ValidationError, match="falsifier"):
        hypotheses.hypothesis_open(conn, "x", [], [], [a1], [d1], "", "weekly")
    with pytest.raises(ValidationError, match="granularity"):
        hypotheses.hypothesis_open(conn, "x", [], [], [a1], [d1], "f", " ")
    with pytest.raises(ValidationError, match="kind"):
        hypotheses.hypothesis_open(conn, "x", [], [], [d1], [], "f", "g")
    # a supporting rule with weight above threshold (two clean dated hits = 1.2), so arming can happen
    strong = make_rule(conn, "strong rule")
    for i in range(2):
        rid = make_round(conn, text=f"s{i}")
        ids = rounds.lock_predictions(conn, rid, [pred(strong)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
    h = hypotheses.hypothesis_open(conn, "premia de-escalate slowest", [], [strong], ["arm_one", a2], [d1], "premia lead", "weekly")["hypothesis_id"]
    assert hypotheses.hypothesis_check(conn, h, [{"predicate_id": a1, "observed": "holds"}])["status"] == "open"
    assert hypotheses.hypothesis_check(conn, h, [{"predicate_id": "arm_two", "observed": "holds"}])["status"] == "armed"
    due = hypotheses.hypotheses_due(conn)
    assert due["count"] == 1 and due["hypotheses"][0]["arming_status"] == {"arm_one": "holds", "arm_two": "holds"}
    assert hypotheses.hypothesis_check(conn, h, [{"predicate_id": d1, "observed": "holds"}])["status"] == "falsified"
    assert hypotheses.hypotheses_due(conn)["count"] == 0
    with pytest.raises(ValidationError, match="not attached"):
        hypotheses.hypothesis_check(conn, h, [{"predicate_id": predicates.predicate_add(conn, "stray", "arming", "s", "t")["predicate_id"], "observed": "holds"}])
    # a round resolution referencing a hypothesis resolves it
    h2 = hypotheses.hypothesis_open(conn, "second", [], [], [a1], [], "f", "g")["hypothesis_id"]
    rule = make_rule(conn)
    rid, ids, card = play_round(conn, [pred(rule, hypothesis_id=h2)], lambda ids: [res(ids[0], "hit")], text="resolver")
    hy = hypotheses.get_hypothesis(conn, h2)
    assert hy["status"] == "resolved" and hy["resolved_in_round"] == rid
    with pytest.raises(StateError, match="supersedes"):
        hypotheses.hypothesis_check(conn, h2, [{"predicate_id": a1, "observed": "holds"}])
    h3 = hypotheses.hypothesis_open(conn, "successor", [], [], [a1], [], "f", "g", supersedes=h2)["hypothesis_id"]
    assert hypotheses.get_hypothesis(conn, h2)["superseded_by"] == h3
    assert verify_chain(conn)["ok"]


# invariant 4: bitemporal stamping --------------------------------------------------

def test_recorded_at_is_harness_only(conn):
    with pytest.raises(HarnessError, match="recorded_at"):
        append(conn, "events", {"event_text": "x", "event_date": "2026-01-01", "source": "s", "selection_rule": "r",
                                "rejected_before": 0, "criteria_json": "{}", "event_hash": "h", "recorded_at": "1999"})
    from harness.server import mcp
    for t in mcp._tool_manager.list_tools():
        assert "recorded_at" not in t.parameters.get("properties", {}), t.name
    rid = make_round(conn)
    rule = make_rule(conn)
    rounds.lock_predictions(conn, rid, [pred(rule)])
    rounds.open_retrieval(conn, rid)
    ev = rounds.add_evidence(conn, rid, "https://x", "t", "e", source_time="2026-08-30", knowable_from="2026-08-31")
    row = conn.execute("SELECT * FROM evidence WHERE id = ?", (ev["evidence_id"],)).fetchone()
    assert row["recorded_at"].endswith("Z") and row["source_time"] == "2026-08-30" and row["knowable_from"] == "2026-08-31"
    for t in LEDGER_TABLES:
        assert "recorded_at" in [c[1] for c in conn.execute(f"PRAGMA table_info({t})")]


# predicate checks feed the scorecard ---------------------------------------------

def test_arming_claimed_and_programme_stats(conn):
    gate = predicates.predicate_add(conn, "pair_gate", "arming", "positions", "any difference",
                                    key="pred.arm.tradability_gate")["predicate_id"]
    other = predicates.predicate_add(conn, "slack", "arming", "inventory", "no glut")["predicate_id"]
    rule = make_rule(conn)
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(rule)])["prediction_ids"]
    predicates.predicate_check(conn, rid, [{"predicate_id": "pair_gate", "claimed": "holds", "basis": "two listed holders on the node"}])
    rounds.open_retrieval(conn, rid)
    predicates.predicate_check(conn, rid, [{"predicate_id": gate, "claimed": "holds", "observed": "holds", "basis": "positions store"}])
    card = scorer.score_round(conn, rid, [res(ids[0])])
    assert card["arming_claimed"] and card["arming_observed"]
    # a different arming predicate holding does not arm the round; only the gate does
    rid2 = make_round(conn, text="second")
    ids2 = rounds.lock_predictions(conn, rid2, [pred(rule)])["prediction_ids"]
    predicates.predicate_check(conn, rid2, [{"predicate_id": other, "claimed": "holds", "observed": "holds", "basis": "inventory report"}])
    rounds.open_retrieval(conn, rid2)
    card2 = scorer.score_round(conn, rid2, [res(ids2[0])])
    assert not card2["arming_claimed"] and not card2["arming_observed"] and card2["any_arming_observed"]
    play_round(conn, [pred(rule)], lambda ids: [res(ids[0], "miss", "wrong")], text="third")
    ps = scorer.programme_stats(conn)
    assert ps["rounds_scored"] == 3 and ps["arming_rate"] == pytest.approx(1 / 3)
    assert sorted(ps["mechanism_score"]["values"]) == [0.0, 1.0, 1.0]
    exp = rounds.export_round(conn, rid)
    assert exp["scorecard"]["mechanism_score"] == 1.0 and exp["predicate_checks"][0]["predicate_name"] == "pair_gate"
    assert json.dumps(exp)   # serialisable


# seed --------------------------------------------------------------------------------

def test_seed_v1_loads_and_is_idempotent(conn):
    from harness.seed import SEED_DIR, load_seed
    r1 = load_seed(conn, SEED_DIR / "seed_v1.json")
    assert r1["predicates"] >= 1 and r1["holders"] == 2 and r1["hypotheses"] == 2 and r1["positions"] == 2
    r2 = load_seed(conn, SEED_DIR / "seed_v1.json")
    assert (r2["predicates"], r2["library_rules"], r2["holders"], r2["positions"], r2["hypotheses"]) == (0, 0, 0, 0, 0)
    assert names.resolve(conn, "Bayport Choate")["holder"]["parent"]["canonical_name"] == "LyondellBasell Industries N.V."
    assert verify_chain(conn)["ok"]
