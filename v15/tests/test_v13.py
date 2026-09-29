"""v13 brief: §A surviving risk (the mirror basket retired as a generator), §B the round-12 fixes. §D smoke tests 1-8."""
import pytest

from harness import basket, predicates, prices, risk, rounds, scorer, surviving
from harness.errors import StateError, ValidationError

from conftest import TEST_MODEL, TODAY, make_rule, pred, res
from test_v10 import NODE_A, NODE_B, submit, two_node_round, v10      # noqa: F401
from test_v12 import _chart, _series                                   # noqa: F401


@pytest.fixture
def v13(v10):
    """v13 switched on for the ledger: the leg template and the surviving-risk assessment run at lock."""
    risk.setting_set(v10, "v13_started_at", "2026-09-01T00:00:00Z")
    risk.set_preconditions(v10)
    return v10


def _claims(P, *keys):
    """A no-claim reason for every slot the test does not fill, so the template check is satisfied deliberately."""
    out = []
    for k in keys:
        out.append({"position_id": P[k], "effect_kind": "direction",
                    "no_claim": "no-claim: this leg is carried for the footprint, not called on, in a test fixture"})
        out.append({"position_id": P[k], "effect_kind": "vol",
                    "no_claim": "no-claim: no option chain reading is taken on this leg in a test fixture"})
    return out


# §D.1: a leg on a large diversified holder with a small event -> tide fires -> the null is a non-position ------------

def test_d1_tide_eliminates_and_the_null_is_reported_as_a_non_position(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    v13.execute("UPDATE holders SET price_symbol = 'POOL' WHERE id = ?", (H["pool"],))
    rows = _series("2026-06-01", 90, 100.0, 3.0)      # a noisy series: the ambient band is wider than the call's move
    fetch = _chart({"POOL": rows})
    claims = _claims(P, "oxy", "lesl", "emn", "neu") + [
        {"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no option chain is read on this leg in the fixture"}]
    rounds.lock_predictions(v13, rid, [
        pred(a, target="POOL", sign="+", claim="POOL moves at least 1% on the event, which is under its own ambient band",
             position_id=P["pool"], due_at="2026-09-20"),
        pred(a, call_type="null", target="none", claim="no attributable move on POOL", carrier="close",
             falsifier="a move", falsifier_window="days:5", due_at="2026-09-20", position_id=P["pool"]),
    ], leg_claims=claims)
    rounds.open_retrieval(v13, rid)
    prices.backfill_round(v13, rid, fetch=fetch)
    r = surviving.assess_round(v13, rid)
    pool = next(x for x in r["results"] if x["holder"] == "Pool Corporation")
    assert "tide" in pool["eliminators_fired"] and pool["survives"] is False
    nb = surviving.null_breakdown(v13, rid)
    assert nb["counts"]["eliminated"] >= 1 and any(x["breakdown"] == "eliminated" for x in nb["rows"])


# §D.2: the filer's own event -> no eliminator fires -------------------------------------------------------------------

def test_d2_degree_zero_leg_survives(v13):
    """Round 10's shape: the event is the holder's own filing, so no tide rule can fire on it (C2's first check)."""
    from harness import names, positions
    rid = submit(v13, node=NODE_A, node_kind="chemical")["round_id"]
    hid = names.holder_upsert(v13, "Pool Corporation", "company", listed=True, ticker="POOL", key="holder.pool")["holder_id"]
    pid = positions.position_add(v13, hid, NODE_A, "sign_of_exposure", "-", "the filer itself", "stated")["position_id"]
    a = make_rule(v13)
    rounds.touched_set_add(v13, rid, [{"holder_id": hid, "degree": 0, "node": NODE_A, "position_summary": "the filer",
                                       "substitutability": "low", "mechanism_ids": [a]}])
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=pid,
                                            due_at="2026-09-20")],
                            leg_claims=[{"position_id": pid, "effect_kind": "vol",
                                         "no_claim": "no-claim: no option chain reading is taken on this leg in the fixture"}])
    r = surviving.assess_round(v13, rid)
    pool = next(x for x in r["results"] if x["holder"] == "Pool Corporation")
    assert pool["survives"] and "tide" not in pool["eliminators_fired"]
    rec = surviving.survives_leg(v13, rid, [pid])
    assert rec and rec["survives"] and "no tide rule can fire" in rec["basis"]


# §D.3: a rule whose precondition does not hold does not cover the leg; uncovered is a separate field -------------------

def test_d3_precondition_scopes_the_rule_and_uncovered_is_independent(v13):
    props_equity = {"factor_kind": "equity", "q1a": "pass", "q1b": "pass", "position_share": None}
    props_physical = {"factor_kind": "physical", "q1a": "fail", "q1b": "pass", "position_share": 0.4}
    assert surviving.precondition_holds("tide", props_equity)[0] is True
    assert surviving.precondition_holds("tide", props_physical)[0] is False
    assert surviving.precondition_holds("traversed", props_physical)[0] is True
    assert surviving.precondition_holds("immaterial_position", props_equity)[0] is False
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"],
                                            due_at="2026-09-20")],
                            leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                            [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no option chain read here"}])
    legs = predicates.armed_legs(v13, rid)
    leg = next(l for l in legs if l["position_id"] == P["pool"])
    assert leg["uncovered"] in (True, False) and "uncovered" in leg


# §D.4: a leg with a direction claim and no second-kind claim and no reason is refused ----------------------------------

def test_d4_leg_template_refuses_a_silent_slot(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    with pytest.raises(ValidationError, match="no-claim"):
        rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move",
                                                position_id=P["pool"], due_at="2026-09-20")])
    # the same lock succeeds once every leg says something, or says why not
    r = rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move",
                                                position_id=P["pool"], due_at="2026-09-20")],
                                leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                                [{"position_id": P["pool"], "effect_kind": "vol",
                                  "no_claim": "no-claim: POOL has no option chain reading at lock in this fixture"}])
    assert r["leg_template"]["legs"] == 5 and r["leg_template"]["no_claim"] >= 5


# §D.5: cell enumeration produces no legs; predictions.space is not written ---------------------------------------------

def test_d5_cell_enumeration_produces_no_legs(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    r = rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move",
                                                position_id=P["pool"], due_at="2026-09-20")],
                                leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                                [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read here"}])
    assert risk.grid_cells(v13, rid) == [] and r["grid"] is None
    assert all(p["space"] is None for p in rounds.list_predictions(v13, rid))
    b = basket.event_basket(v13, rid, space="both")
    assert b["cells"] == [] and b["cell_counts"] == {"positive": 0, "mirror": 0}


# §D.6: below the turnover floor an observation is stored, flagged and excluded from re-encode counts -------------------

def test_d6_turnover_floor_marks_a_band_unreliable(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"],
                                            due_at="2026-09-20")],
                            leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                            [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read here"}])
    rounds.open_retrieval(v13, rid)
    e = rounds.add_evidence(v13, rid, "https://x", "the press attributes the move to the event", "e", source_time="2026-09-15")["evidence_id"]
    closes = [100 + (i % 3) for i in range(22)]
    o = risk.price_observe(v13, rid, P["pool"], "close", "2026-09-15", 130.0, True, attribution_evidence_id=e,
                           closes=closes, today="2026-09-21", band_reliable=False, turnover_usd=41_000.0)
    assert o["out_of_band"] and o["attributed"] and o["counts_as_reencode"] is False
    row = v13.execute("SELECT band_reliable, turnover_usd FROM price_observations WHERE id = ?", (o["observation_id"],)).fetchone()
    assert row["band_reliable"] == 0 and row["turnover_usd"] == 41_000.0          # stored, never deleted
    assert risk.reencode_for_leg(v13, rid, [P["pool"]], "2026-09-07", "2026-09-20")["reencode_date"] is None


# §D.7: an event misdated by a year is voided when Q2 is re-computed at retrieval ---------------------------------------

def test_d7_q2_recomputed_at_retrieval_voids_a_misdated_round(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)          # submitted at 2026-09-07, cutoff 2026-06-30
    rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"],
                                            due_at="2026-09-20")],
                            leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                            [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read here"}])
    r = rounds.open_retrieval(v13, rid, event_date_confirmed="2025-09-07", date_source="the wire that reported it")
    assert r["state"] == "void" and r["q2_recheck"]["voided"] and r["q2_recheck"]["moved"]
    assert rounds.round_state(v13, rid) == "void"
    crit = rounds.current_criteria(v13, rounds.get_row(v13, "rounds", rid, "round")["event_id"])["current"]
    assert crit["Q2"].startswith("fail")


def test_d7b_scoring_refused_until_the_date_is_confirmed(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    ids = rounds.lock_predictions(v13, rid, [pred(a, target="POOL", sign="0", claim="no attributable move",
                                                  position_id=P["pool"], due_at="2026-09-10")],
                                  leg_claims=_claims(P, "oxy", "lesl", "emn", "neu") +
                                  [{"position_id": P["pool"], "effect_kind": "vol", "no_claim": "no-claim: no chain read here"}])["prediction_ids"]
    rounds.open_retrieval(v13, rid)
    with pytest.raises(StateError, match="confirm the event"):
        scorer.score_round(v13, rid, [res(ids[0], "hit", "right")], today="2026-09-11")
    rounds.confirm_event_date(v13, rid, "2026-09-07", "the wire that reported it")
    card = scorer.score_round(v13, rid, [res(ids[0], "hit", "right")], today="2026-09-11")
    assert card["n_resolved"] == 1


# §D.8: Q1b returns unknown where no registry covers the node kind ------------------------------------------------------

def test_d8_q1b_unknown_without_a_registry(v13):
    from harness.history import q1b, registry_coverage
    assert registry_coverage("mining") == [] and registry_coverage("refinery")
    r = q1b(v13, "el_teniente_copper_supply", "2026-07-31", node_kind="mining", registries=False)
    assert r["value"] == "unknown" and "no registry" in r["text"]
    # a node kind a registry does claim to cover still answers pass or fail
    r2 = q1b(v13, "some_quiet_refinery_output", "2026-07-31", node_kind="refinery", registries=False)
    assert r2["value"] == "pass"


# §B4: the conjunction shape round 12's call 6 got through ---------------------------------------------------------------

def test_b4_absence_conjoined_with_its_own_conditional_is_refused(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    with pytest.raises(ValidationError, match="conditional"):
        rounds.lock_predictions(v13, rid, [
            pred(a, target="POOL", sign="0", position_id=P["pool"], due_at="2026-09-20",
                 claim="of the three listed names, none closes outside its own band on the event day, with POOL ranked "
                       "first if any of them were to")])


# §B5: a feed set that cannot span the window says so at enumeration time -------------------------------------------------

def test_b5_feed_reach_is_measured_and_reported(v13):
    from harness import enumeration
    items = [{"title": "a plant fire at the works", "link": "https://x/1", "published": "2026-09-06", "summary": ""}]

    def fetch(url, timeout=30):
        import json as _j
        return _j.dumps({"chart": {}}).encode()

    report = [{"feed": "feed.chemeng", "items": 1, "error": None}]
    feed = {"key": "feed.chemeng"}
    for it in items:
        it["feed"] = feed
    # v14 C8: a feed set that cannot span the window raises at the point of use rather than warning into a log
    with pytest.raises(enumeration.ShortReach, match="does not|reaches"):
        enumeration.measure_reach(v13, report, items, "2026-07-01", "2026-07-08")
    reach = enumeration.measure_reach(v13, report, items, "2026-07-01", "2026-07-08", strict=False)
    assert reach["warning"]
    row = v13.execute("SELECT reach_days FROM feeds WHERE key = 'feed.chemeng'").fetchone()
    assert row["reach_days"] is not None
