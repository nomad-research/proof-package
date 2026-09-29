"""v14 brief: §A generate wide, eliminate with anchors, diagnose what survives; §C the round-13 fixes. §D smoke tests."""
import pytest

from harness import enumeration, generate, glossary, names, positions, predicates, risk, rounds, scorer, surviving, vector
from harness.errors import ValidationError

from conftest import make_rule, pred, res
from test_v10 import NODE_A, NODE_B, submit, two_node_round, v10      # noqa: F401
from test_v12 import _chart, _series                                   # noqa: F401
from test_v13 import _claims, v13                                      # noqa: F401


# §D.1: generation is wide, and every generated leg either survives or carries an elimination reason ------------------

def test_d1_generation_is_wide_and_every_leg_is_accounted_for(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    # a store with kin and shared nodes, so the hops have something to reach
    parent = names.holder_upsert(v13, "Pool Parent Holdings", "company", key="holder.pool_parent")["holder_id"]
    v13.execute("UPDATE holders SET parent_id = ? WHERE id = ?", (parent, H["pool"]))
    for i in range(4):
        hid = names.holder_upsert(v13, f"Chain Neighbour {i}", "company", key=f"holder.chain{i}")["holder_id"]
        positions.position_add(v13, hid, "a_third_node", "sign_of_exposure", "-", "operator prior", "inferred")
        positions.position_add(v13, H["emn"] if i % 2 else H["oxy"], "a_third_node", "sign_of_exposure", "+", "operator prior", "inferred")
    # a hunch may put a leg on the board; only anchors and fetched facts keep it there
    extra = names.holder_upsert(v13, "A Company The Operator Merely Suspects", "company", key="holder.hunch")["holder_id"]
    positions.position_add(v13, extra, NODE_A, "sign_of_exposure", "-", "operator prior", "inferred")
    g = generate.generate_space(v13, rid, nodes=[NODE_A, NODE_B],
                                proposals=[{"holder_id": extra, "node": NODE_A,
                                            "reason": "this looks like the 2019 episode, which is a proposal and not support"}])
    assert g["generation_width"] > 10 and g["generation_width"] >= len(g["legs"])
    assert "position" in g["by_origin"]
    r = surviving.assess_round(v13, rid, write=False)
    for leg in r["results"]:
        assert leg["survives"] or leg["eliminators_fired"]          # accounted for either way
    assert r["legs"] >= g["generation_width"] - g["already_on_round"]


# §D.2: round 10's filer shape - highest stake, bound by pricedness, and it must not arm ------------------------------

def test_d2_high_stake_leg_binds_on_pricedness_and_does_not_arm(v13):
    """The degree-0 signature: everything at issue, and priced before it was knowable to us. A conjunction would have
    armed this leg and been wrong."""
    rid = submit(v13, node=NODE_A, node_kind="chemical")["round_id"]
    a = make_rule(v13)
    hid = names.holder_upsert(v13, "The Filer", "company", listed=True, ticker="FILR", key="holder.filer")["holder_id"]
    pid = positions.position_add(v13, hid, NODE_A, "sign_of_exposure", "-", "the filer itself", "stated")["position_id"]
    rounds.touched_set_add(v13, rid, [{"holder_id": hid, "degree": 0, "node": NODE_A, "position_summary": "the filer",
                                       "substitutability": "low", "mechanism_ids": [a]}])
    rounds.lock_predictions(v13, rid, [pred(a, target="FILR", sign="0", claim="no attributable move", position_id=pid,
                                            due_at="2026-09-20")],
                            leg_claims=[{"position_id": pid, "impact_pct": 40.0,
                                         "impact_basis": "the filing is the whole of the equity story on this name"},
                                        {"position_id": pid, "effect_kind": "vol",
                                         "no_claim": "no-claim: no option chain reading is taken on this leg in the fixture"}])
    rounds.open_retrieval(v13, rid)
    e = rounds.add_evidence(v13, rid, "https://x", "the press attributes the move to the filing", "e", source_time="2026-09-07")["evidence_id"]
    closes = [100 + (i % 3) for i in range(22)]
    risk.price_observe(v13, rid, pid, "close", "2026-09-07", 40.0, True, attribution_evidence_id=e,
                       closes=closes, today="2026-09-21", band_reliable=True, turnover_usd=50_000_000.0)
    r = surviving.assess_round(v13, rid)
    leg = r["results"][0]
    assert leg["terms"]["stake"] and leg["terms"]["stake"] > 1.0          # the most at issue in the fixture
    assert leg["binding_term"] == "pricedness"                            # and priced before it was knowable
    arm = next(x for x in predicates.armed_legs(v13, rid) if x["position_id"] == pid)
    assert arm["arming_status"] != "armed_dated" and arm["binding_term"] == "pricedness"


# §D.3: round 13's Corning shape - bound by stake, and no adjacency clears it -----------------------------------------

def test_d3_low_stake_leg_binds_on_stake(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    v13.execute("UPDATE holders SET price_symbol = 'POOL' WHERE id = ?", (H["pool"],))
    rows = _series("2026-06-01", 90, 100.0, 3.0)
    fetch = _chart({"POOL": rows})
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move",
                                            position_id=P["pool"], due_at="2026-09-20")],
                            leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                            [{"position_id": P["pool"], "impact_pct": 0.2, "impact_basis": "a fraction of a per cent of a diversified group"},
                             {"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read in the fixture"}])
    rounds.open_retrieval(v13, rid)
    from harness import prices
    prices.backfill_round(v13, rid, fetch=fetch)
    r = surviving.assess_round(v13, rid)
    pool = next(x for x in r["results"] if x["holder"] == "Pool Corporation")
    assert pool["binding_term"] == "stake" and pool["terms"]["stake"] < 1.0
    adj = generate.adjacent(v13, H["pool"], NODE_A)
    assert adj["n"] >= 1 and all("cost" in n_ for n_ in adj["neighbours"])


# §D.4: an anchor with no data is unevaluable, and the rate is reported per anchor -------------------------------------

def test_d4_unevaluable_is_a_value_not_a_verdict(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"],
                                            due_at="2026-09-20")],
                            leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                            [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read in the fixture"}])
    r = surviving.assess_round(v13, rid, write=False)
    leg = next(x for x in r["results"] if x["holder"] == "Pool Corporation")
    # slack has no node fact behind it in the fixture: unevaluable, and the leg is neither passed nor failed on it
    assert leg["eliminators_unevaluable"], "an anchor with no data must be recorded, not silently passed"
    assert not any(e in leg["eliminators_fired"] for e in leg["eliminators_unevaluable"])
    assert not any(e in leg["eliminators_checked"] for e in leg["eliminators_unevaluable"])
    assert r["unevaluable_rate"]["slack"] is not None and r["mean_confidence"] <= 1.0


# §D.5: adjacency returns neighbours and costs and never a ranking ------------------------------------------------------

def test_d5_adjacent_offers_no_ranking(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    adj = generate.adjacent(v13, H["pool"], NODE_A)
    assert "does not rank" in adj["note"] and "does not recommend" in adj["note"]
    for n_ in adj["neighbours"]:
        assert set(n_) >= {"holder_id", "relation", "basis", "cost"}
        assert "score" not in n_ and "rank" not in n_ and "recommended" not in n_
    g = glossary.glossary()
    assert g["n"] >= 6 and all("costs" in m for m in g["moves"])


# §D.6: a map call with no settling document is refused; a call on a leg with no path is refused ------------------------

def test_d6_settling_document_and_path_are_required(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    with pytest.raises(ValidationError, match="settling document|settling_document"):
        rounds.lock_predictions(v13, rid, [pred(None, call_type="map", target="map: x", falsifier=None,
                                                settling_document=None)])
    # a leg at degree 2 with no cited mechanism and no stated position has no admissible path
    orphan = names.holder_upsert(v13, "An Unconnected Company", "company", listed=True, ticker="ORPH", key="holder.orph")["holder_id"]
    opid = positions.position_add(v13, orphan, "some_other_node", "sign_of_exposure", "-", "operator prior", "inferred")["position_id"]
    rounds.touched_set_add(v13, rid, [{"holder_id": orphan, "degree": 3, "node": "some_other_node",
                                       "position_summary": "no path", "substitutability": "unknown", "mechanism_ids": []}])
    with pytest.raises(ValidationError, match="no admissible path"):
        rounds.lock_predictions(v13, rid, [pred(a, target="ORPH", sign="0", claim="no attributable move",
                                                position_id=opid, due_at="2026-09-20")],
                                leg_claims=_claims(P, "pool", "oxy", "lesl", "emn", "neu") +
                                [{"position_id": opid, "effect_kind": "vol", "no_claim": "no-claim: nothing to claim on an orphan"}])


# §D.7: an ordering call with no attributed move on any leg resolves untestable ------------------------------------------

def test_d7_ordering_over_noise_is_untestable(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    ids = rounds.lock_predictions(v13, rid, [
        pred(a, call_type="magnitude_order", target="POOL against OXY", magnitude_rank=1, position_id=P["pool"],
             claim="POOL's relative move is the larger of the two", due_at="2026-09-10")],
        leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
        [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read in the fixture"}])["prediction_ids"]
    rounds.open_retrieval(v13, rid)
    rounds.confirm_event_date(v13, rid, "2026-09-07", "the wire that reported it")
    card = scorer.score_round(v13, rid, [res(ids[0], "hit", "right")], today="2026-09-11")
    r = scorer.latest_resolutions(v13, rid)[ids[0]]
    assert r["outcome"] == "untestable" and "C5" in r["scorer_note"]
    assert card["n_resolved"] == 1


# §D.8: materiality is a number at selection, and a window with nothing above appetite says so --------------------------

def test_d8_materiality_is_a_number_at_selection(v13):
    from harness import config
    hid = names.holder_upsert(v13, "Bandless Holdings", "company", listed=True, ticker="BAND", key="holder.bandless")["holder_id"]
    r = enumeration.materiality_hint(v13, "fire at the Bandless Holdings works", "chemical", "2026-09-07")
    # no price series behind the fixture holder, so the number is not computable and says so rather than reading zero
    assert r["materiality_hint"] is None and "not computable" in r["materiality_basis"]
    assert enumeration.default_impact_pct("mining") > enumeration.default_impact_pct("port")
    assert config.APPETITE["stake"] == 1.0


# §A5: operator risk is computed from the clean ledger, never asserted ---------------------------------------------------

def test_a5_operator_risk_is_computed(v13):
    rates = vector.operator_rates(v13)
    assert set(rates) >= {"absence", "occurrence", "map", "_n"}
    val, basis = vector.operator_term(v13, [{"call_type": "map", "claim": "x", "sign": None, "base_rate_id": None,
                                             "settling_document_fetched": False}], 0, rates)
    assert 0.0 <= val <= 1.0 and "settling document" in basis
