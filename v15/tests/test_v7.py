"""v7 brief: §B decomposition and reveal, §C second scorer, §D baskets, and the §E smoke tests."""
import pytest

from harness import basket, facts, hypotheses, library, names, positions, predicates, rounds, scorer
from harness.errors import ValidationError
from harness.models import independent_clauses, is_decomposable
from harness.scorer import derive_composite

from conftest import TEST_MODEL, TODAY, dated_evidence, make_round, make_rule, play_round, pred, res


def lag_factors():
    return [
        {"factor": "decontamination of the dock", "node": "deurganck_dock_container_handling", "estimate": "days", "carrier": "port notices", "falsifier": "decontamination beyond a week", "binding": False, "against": False},
        {"factor": "quay 1718 operations", "node": "deurganck_dock_container_handling", "estimate": "days", "carrier": "terminal notices", "falsifier": "quay closed beyond 3 days", "binding": False, "against": False},
        {"factor": "DP World Antwerp Gateway", "node": "deurganck_dock_container_handling", "estimate": "days", "carrier": "terminal notices", "falsifier": "closed beyond 3 days", "binding": False, "against": False},
        {"factor": "rail operations", "node": "deurganck_dock_container_handling", "estimate": "days", "carrier": "terminal notices", "falsifier": "rail out beyond a week", "binding": False, "against": True},
        {"factor": "north berth with 3 STS cranes", "node": "deurganck_dock_container_handling", "estimate": "weeks", "carrier": "terminal notices; crane repair reports", "falsifier": "berth back within days", "binding": True, "against": True},
    ]


# §E.1: re-decompose round-6 call 2; the harness derives max = weeks -----------------------------

def test_e1_derivation_max_is_weeks():
    factors = [{"idx": i, "binding": f["binding"], "against": f["against"], "estimate": f["estimate"]} for i, f in enumerate(lag_factors())]
    outcomes = {0: {"outcome": "hit", "observed": "days"}, 1: {"outcome": "hit", "observed": "days"},
                2: {"outcome": "hit", "observed": "days"}, 3: {"outcome": "hit", "observed": "days"},
                4: {"outcome": "hit", "observed": "weeks"}}
    d = derive_composite("max", "days", factors, outcomes)
    assert d["derived_band"] == "weeks" and d["outcome"] == "miss"
    d2 = derive_composite("max", "weeks", factors, outcomes)
    assert d2["outcome"] == "hit"
    # a binding factor unverified makes the composite unverified
    outcomes[4] = {"outcome": "unverified", "observed": None}
    assert derive_composite("max", "days", factors, outcomes)["outcome"] == "unverified"
    # extents aggregate all
    ext = [{"idx": 0, "binding": True, "against": False, "estimate": "open"}, {"idx": 1, "binding": False, "against": True, "estimate": "open"}]
    assert derive_composite("all", None, ext, {0: {"outcome": "hit"}, 1: {"outcome": "miss"}})["outcome"] == "miss"
    assert derive_composite("all", None, ext, {0: {"outcome": "hit"}, 1: {"outcome": "hit"}})["outcome"] == "hit"
    with pytest.raises(ValidationError, match="missing"):
        derive_composite("all", None, ext, {0: {"outcome": "hit"}})


# §E.2 / B4: compound claims are refused ---------------------------------------------------------------

def test_e2_split_it(conn):
    rid = make_round(conn)
    compound = ("the leak is from a tank container at the terminal; a safety perimeter closes part of the terminal and the river "
                "approach stays open")
    assert independent_clauses(compound) >= 2
    with pytest.raises(ValidationError, match="split it"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="map", target="map: x", claim=compound, falsifier=None)])
    with pytest.raises(ValidationError, match="split it"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="null", target="none",
                                                 claim="the event fails the tradability gate; the operators are private and every holder is sign minus",
                                                 falsifier_window="days:3")])
    assert independent_clauses("no attributable equity move anywhere within three sessions") == 1
    assert independent_clauses("premia rise first") <= 1


# §E.3 / B1, B2: decomposition required -----------------------------------------------------------------

def test_e3_factors_required_with_binding_and_against(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    assert is_decomposable("lag_band", "x") and is_decomposable("sign", "the terminal is fully operational within 3 days")
    assert not is_decomposable("sign", "premia rise first") and not is_decomposable("null", "no force majeure within 14 days")
    with pytest.raises(ValidationError, match="decompose or don't claim"):
        rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks")])
    no_against = [dict(f, against=False) for f in lag_factors()]
    with pytest.raises(ValidationError, match="against"):
        rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks", factors=no_against)])
    no_binding = [dict(f, binding=False) for f in lag_factors()]
    with pytest.raises(ValidationError, match="binding"):
        rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks", factors=no_binding)])
    with pytest.raises(ValidationError, match="lag band"):
        rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks",
                                                 factors=[dict(lag_factors()[4], estimate="a while")])])
    r = rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks", factors=lag_factors())])
    p = rounds.list_predictions(conn, rid)[0]
    assert p["aggregation"] == "max" and len(p["factors"]) == 5 and p["factors"][4]["binding"] is True
    # factor nodes unknown to the store land in the orphan queue (D1)
    assert names.orphans(conn)["unresolved"] >= 1


def test_composite_is_derived_at_scoring(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks", factors=lag_factors())])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    e = dated_evidence(conn, rid)
    with pytest.raises(ValidationError, match="decomposed"):
        scorer.score_round(conn, rid, [res(ids[0], "hit")])
    fo = [{"factor_index": i, "outcome": "hit", "observed": "days", "evidence_ids": [e]} for i in range(4)]
    fo.append({"factor_index": 4, "outcome": "hit", "observed": "weeks", "evidence_ids": [e]})
    card = scorer.score_round(conn, rid, [res(ids[0], "hit", "right", source_coverage="adequate", factor_outcomes=fo)])
    r = rounds.latest_resolutions(conn, rid)[ids[0]]
    assert r["outcome"] == "miss" and "derived composite=miss" in r["scorer_note"] and card["per_call"][0]["decomposed"]
    assert len(rounds.latest_factor_resolutions(conn, ids[0])) == 5
    assert card["misreads"] == 1 and library.get_rule(conn, a)["misses"] == 0    # A13 still applies to derived misses


# B3: touched set -------------------------------------------------------------------------------------------

def test_touched_set_required_or_declared(conn):
    a = make_rule(conn)
    rid = rounds.submit_event(conn, "ev", "2026-07-16", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)["round_id"]
    with pytest.raises(ValidationError, match="touched_set"):
        rounds.lock_predictions(conn, rid, [pred(a)])
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True, ticker="ALP", key="holder.alp")["holder_id"]
    with pytest.raises(ValidationError, match="substitutability"):
        rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": 0, "node": "node x", "position_summary": "owner", "substitutability": "none"}])
    t = rounds.touched_set_add(conn, rid, [{"holder_id": "holder.alp", "degree": 0, "node": "node x", "position_summary": "owner of the unit", "substitutability": "low", "duration_factor": "repair", "carrier": "owner statements"},
                                          {"holder_id": h, "degree": 1, "node": "node x", "position_summary": "offtaker", "substitutability": "unknown", "duration_factor": "none", "carrier": "none"}])
    assert t["count"] == 2 and rounds.list_touched_set(conn, rid)[1]["duration_factor"] is None
    rounds.lock_predictions(conn, rid, [pred(a)])
    rid2 = rounds.submit_event(conn, "ev2", "2026-07-17", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)["round_id"]
    rounds.lock_predictions(conn, rid2, [pred(a)], lock_note="no-touched-set: nothing on the node in the store yet")
    assert rounds.list_notes(conn, rid2)[0]["kind"] == "lock"


# §E.4 / B5: reveal seeds the work -----------------------------------------------------------------------------

def test_e4_reveal_context(conn):
    port = names.holder_upsert(conn, "Port Authority", "authority")["holder_id"]
    msc = names.holder_upsert(conn, "MSC", "company")["holder_id"]
    mpet = names.holder_upsert(conn, "MPET", "facility", parent_id=msc)["holder_id"]
    for h in (port, mpet):
        positions.position_add(conn, h, "deurganck_dock_container_handling", "sign_of_exposure", "-", "notices", "stated")
    facts.node_fact_add(conn, "deurganck_dock_container_handling", "outage", "April spill closed the dock four days", "port")
    r1 = library.propose(conn, "recurring disruption at a node is priced as weather", "x", 2, "sequence", "Round 3: Antwerp dock", carries=["absence"])
    r2 = library.propose(conn, "the headline names what reopened, not what stayed shut", "x", 3, "sequence", "Round 3: Antwerp Deurganck dock", carries=["duration"])
    rid = rounds.submit_event(conn, "a leak at the dock", "2026-07-14", "s", "r", 0, {"Q1": "pass"}, node="deurganck_dock_container_handling",
                              operator_model=TEST_MODEL, today=TODAY)["round_id"]
    rv = rounds.reveal_event(conn, rid)
    ctx = rv["context"]
    assert {h["holder_id"] for h in ctx["holders"]} == {port, mpet}
    assert [n["holder_id"] for n in ctx["neighbours"]] == [msc] and ctx["neighbours"][0]["relation"] == "parent"
    assert len(ctx["node_facts"]) == 1 and {r["id"] for r in ctx["rules"]} >= {r1["rule_id"], r2["rule_id"]}
    assert rv["context"]["event_kind"] == "leak"
    stored = rounds.latest_reveal_context(conn, rid)
    assert stored["rules"] and stored["node"] == "deurganck_dock_container_handling"
    assert rounds.export_round(conn, rid)["reveal_context"]["holders"]


# §E.5 / A13: misread increments, no rule debit -------------------------------------------------------------------

def test_e5_misread_no_debit(conn):
    a = make_rule(conn)
    before = library.get_rule(conn, a)["weight"]
    rid, ids, card = play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "right")])
    assert card["misreads"] == 1 and library.get_rule(conn, a)["weight"] == before and library.get_rule(conn, a)["misses"] == 0


# §E.6 / C1: a pending dispute keeps a rule from validating -------------------------------------------------------

def test_e6_dispute_blocks_validation(conn):
    a = make_rule(conn)
    rids = []
    for i in range(2):
        rid = make_round(conn, text=f"v{i}")
        ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
        rids.append((rid, ids[0]))
    assert library.get_rule(conn, a)["status"] == "validated"
    d = scorer.second_score(conn, rids[1][0], [{"prediction_id": rids[1][1], "outcome": "unverified", "mechanism_outcome": "unknown",
                                                "baseline_outcome": "unverified", "source_coverage": "thin"}])
    assert d["disputes"] == 1
    r = library.get_rule(conn, a)
    assert r["status"] == "candidate" and r["clean_hit_rounds"] == 1
    assert library.rebuild_library_stats(conn)["disputes_pending"] == 1
    old = rounds.latest_resolutions(conn, rids[1][0])[rids[1][1]]["id"]
    scorer.supersede_resolution(conn, rids[1][0], res(rids[1][1], "hit", "right", scorer="human", supersedes=old, scorer_note="ruled: hit"))
    assert library.get_rule(conn, a)["status"] == "validated" and scorer.score_disputes(conn, rids[1][0])["disputes"] == 0
    bias = scorer.scorer_bias(conn)
    assert bias["compared"] == 1 and bias["under_informed"] == 2 and bias["lenient"] == 0


# C2/C3: blind view carries rule text and reveal context ------------------------------------------------------------

def test_blind_view_rule_text_and_reveal_context(conn):
    a = make_rule(conn, "the toll booth learns before the cargo")
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True)["holder_id"]
    positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "filing", "stated")
    rid = rounds.submit_event(conn, "fire at node x", "2026-07-16", "s", "r", 0, {"Q1": "pass"}, node="node x",
                              operator_model=TEST_MODEL, today=TODAY)["round_id"]
    rounds.reveal_event(conn, rid)
    rounds.round_note(conn, rid, "lock", "no-touched-set: test")
    ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], scorer_note="my private reasoning")])
    view = scorer.second_scorer_view(conn, rid)
    assert view["predictions"][0]["cited_rules"][0]["rule_text"].startswith("the toll booth")
    assert view["reveal_context"]["holders"][0]["holder_id"] == h and "private reasoning" not in str(view)
    assert "did the cited rule" in view["instructions"]


# D1: spawned hypotheses inherit factor quality ---------------------------------------------------------------------

def test_spawned_hypothesis_support(conn):
    a = make_rule(conn)
    arm = predicates.predicate_add(conn, "arm", "arming", "s", "t")["predicate_id"]
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="weeks", claim="out for weeks", falsifier="back in days", factors=lag_factors())])["prediction_ids"]
    h = hypotheses.hypothesis_open(conn, "north berths with damaged cranes stay out for weeks", [], [a], [arm], [], "f", "g",
                                   spawned_from={"prediction_id": ids[0], "factor_index": 4})
    assert h["support_weight"] == 0.0
    rounds.open_retrieval(conn, rid)
    e = dated_evidence(conn, rid)
    fo = [{"factor_index": i, "outcome": "hit", "observed": "days", "evidence_ids": []} for i in range(4)] + \
         [{"factor_index": 4, "outcome": "hit", "observed": "weeks", "evidence_ids": [e]}]
    scorer.score_round(conn, rid, [res(ids[0], "hit", "right", factor_outcomes=fo)])
    assert hypotheses.get_hypothesis(conn, h["hypothesis_id"])["support_weight"] == pytest.approx(0.6)
    with pytest.raises(ValidationError, match="spawned_from"):
        hypotheses.hypothesis_open(conn, "x", [], [a], [arm], [], "f", "g", spawned_from={"prediction_id": ids[0], "factor_index": 9})


# §E.7 / D2, D3, D4, D5: basket, shared factors, per-leg predicates, T0 legs ----------------------------------------

def test_e7_basket_and_shared_factors(conn):
    a = make_rule(conn)
    gate = predicates.predicate_add(conn, "tradability gate (single-name and pair forms)", "arming", "s", "t", key="pred.arm.tradability_gate")["predicate_id"]
    cat = predicates.predicate_add(conn, "catalyst class", "arming", "s", "t", key="pred.arm.catalyst_class")["predicate_id"]
    hs = [names.holder_upsert(conn, f"Holder {i}", "company", listed=(i < 2), ticker=f"H{i}")["holder_id"] for i in range(7)]
    rid = make_round(conn)
    rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": min(i, 3), "node": "deurganck_dock_container_handling",
                                       "position_summary": "uses the dock", "substitutability": "med"} for i, h in enumerate(hs)])
    pos = [positions.position_add(conn, h, "deurganck_dock_container_handling", "sign_of_exposure", "-", "notices", "stated")["position_id"] for h in hs]
    rounds.lock_predictions(conn, rid, [pred(a, call_type="lag_band", lag_band="days", claim="back within days", falsifier="out for weeks", factors=lag_factors())])
    # per-leg checks: leg 0 fully armed and dated; leg 1 gate fails; others unchecked
    predicates.predicate_check(conn, rid, [
        {"predicate_id": gate, "claimed": "holds", "basis": "listed, concentrated", "observed": "holds", "position_id": pos[0]},
        {"predicate_id": cat, "claimed": "holds", "basis": "dated reopening", "observed": "holds", "position_id": pos[0]},
        {"predicate_id": gate, "claimed": "fails", "basis": "small", "observed": "fails", "position_id": pos[1]},
    ])
    b = basket.event_basket(conn, rid)
    assert b["n_legs"] == 7 and b["signs"]["-"] == 7 and b["armed_leg_count"] == 1
    armed = [l for l in b["legs"] if l["armed"]][0]
    assert armed["holder_id"] == hs[0] and armed["dated"] and armed["expression"] == "directional permitted"
    assert all(len(l["correlated_with"]) == 6 for l in b["legs"])
    assert all(l["support_weight"] == 0.0 for l in b["legs"])      # factor-linked node, rule weight 0
    sf = basket.shared_factors(conn, rid)
    assert sf["items"] == 7 and len(sf["pairs"]) == 21 and sf["opposing_pairs"] == 0 and sf["nodes"] == ["deurganck_dock_container_handling"]
    from harness import t0
    eid = rounds.round_status(conn, rid)["event_id"]
    t0.submit_candidate(conn, eid, "w7", True, arming_pass=False)
    assert t0.count(conn, "w7")["armed_legs"] == 1
    rounds.open_retrieval(conn, rid)
    fo = [{"factor_index": i, "outcome": "hit", "observed": "days"} for i in range(4)] + [{"factor_index": 4, "outcome": "hit", "observed": "weeks"}]
    card = scorer.score_round(conn, rid, [res(list(rounds.latest_resolutions(conn, rid).keys())[0] if False else rounds.list_predictions(conn, rid)[0]["id"], "hit", "right", source_coverage="adequate", factor_outcomes=fo)])
    # v12 0.3: legs_checked counts every leg with a gate reading, computed as well as checked
    assert card["armed_leg_count"] == 1 and card["legs_checked"] >= 2


def test_programme_stats_criteria_pass_filter(conn):
    a = make_rule(conn)
    play_round(conn, [pred(a)], lambda ids: [res(ids[0])])
    rid = rounds.submit_event(conn, "q1 fail", "2026-07-18", "s", "first-qualifier", 0, {"Q1": "fail: recurring node"}, operator_model=TEST_MODEL, today=TODAY)["round_id"]
    assert rounds.list_notes(conn, rid)[0]["kind"] == "intake" and "Q1" in rounds.list_notes(conn, rid)[0]["note"]
    rounds.round_note(conn, rid, "lock", "no-touched-set: test")
    ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], "miss", "wrong")])
    assert scorer.programme_stats(conn)["rounds_scored"] == 2
    ps = scorer.programme_stats(conn, criteria_pass_only=True)
    assert ps["rounds_scored"] == 1 and ps["rounds_scored_clean_criteria_pass"] == 1
