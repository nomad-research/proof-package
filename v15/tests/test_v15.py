"""v15 §J smoke tests: the effect DAG, the ACK graph, the walk, contradictions, convergence, bridges, basket
totality and the factor graph — plus §0b's five silent-failure defects, which the migration moves all of."""
import pytest

from harness import acks, contradiction, effects, exposure, names, positions, rounds, scorer, surviving, vector, walk
from harness.errors import StateError, ValidationError

from conftest import make_rule, pred
from test_v10 import NODE_A, NODE_B, submit, two_node_round, v10      # noqa: F401
from test_v12 import _chart, _series                                   # noqa: F401
from test_v13 import _claims, v13                                      # noqa: F401


# ---- fixtures -------------------------------------------------------------------------------------------------

def _round(conn):
    rid = submit(conn, node=NODE_A, node_kind="chemical")["round_id"]
    rounds.round_note(conn, rid, "lock", "no-touched-set: v15 generates effects, not legs")
    return rid


def _holders(conn):
    smelter = names.holder_upsert(conn, "A Smelter On The Node", "plant", key="h.smelter")["holder_id"]
    buyer = names.holder_upsert(conn, "A Concentrate Buyer", "company", listed=True, ticker="BUY",
                                key="h.buyer")["holder_id"]
    downstream = names.holder_upsert(conn, "The Buyer's Own Customer", "company", listed=True, ticker="DWN",
                                     key="h.down")["holder_id"]
    return smelter, buyer, downstream


def _root(conn, rid, node=NODE_A, holder_id=None, kind="volume", **kw):
    return effects.add_root(conn, rid, node, kind, carrier="the operator's own stoppage statement",
                            falsifier="the operator states output was unaffected", holder_id=holder_id, **kw)


# ---- §J1: migration -------------------------------------------------------------------------------------------

def test_j1_migration_every_leg_becomes_a_depth_one_direction_effect(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    before = surviving.assess_round(v13, rid, write=False)
    m = effects.migrate_legs(v13, rid)
    assert m["effects_created"] == before["legs"]
    rows = effects.list_effects(v13, rid)
    assert rows and all(r["depth"] == 1 and r["effect_kind"] == "direction" and r["migrated"] for r in rows)
    assert all(r["parent_effect_id"] is None and r["root_effect_id"] == r["id"] for r in rows)
    # the wall map re-runs and reproduces the same numbers: migration adds rows, it does not move any
    after = surviving.assess_round(v13, rid, write=False)
    assert after["legs"] == before["legs"]
    assert after["binding_terms"]["unassessable"] == before["binding_terms"]["unassessable"]
    # idempotent
    assert effects.migrate_legs(v13, rid)["effects_created"] == 0


# ---- §J2: four kinds on one holder, no sign field anywhere ----------------------------------------------------

def test_j2_four_effect_kinds_on_one_holder_each_with_its_own_carrier_and_falsifier(v13):
    rid = _round(v13)
    _s, buyer, _d = _holders(v13)
    made = []
    for kind, carrier, due in (("cost", "the buyer's own quarterly filing", "2026-11-01"),
                               ("volume", "the buyer's shipment disclosure", "2026-10-01"),
                               ("obligation", "a force majeure letter on its own offtake", "2026-09-30"),
                               ("timing", "the restart statement", "2026-10-15")):
        r = effects.add_root(v13, rid, NODE_A, kind, carrier=carrier,
                             falsifier=f"the {carrier} says otherwise", holder_id=buyer, due_at=due)
        made.append(r["effect_id"])
    rows = [e for e in effects.list_effects(v13, rid) if e["holder_id"] == buyer]
    assert len(rows) == 4
    assert {r["effect_kind"] for r in rows} == {"cost", "volume", "obligation", "timing"}
    assert len({r["carrier"] for r in rows}) == 4 and len({r["due_at"] for r in rows}) == 4
    assert all(r["falsifier"] for r in rows)
    # A3: there is no sign field anywhere
    cols = {c[1] for c in v13.execute("PRAGMA table_info(effects)")}
    assert "sign" not in cols and "narrative_sign" not in cols and "sign_of_exposure" not in cols
    # an effect is a claim: without a carrier and a falsifier it is a sentence
    with pytest.raises(ValidationError):
        effects.add_root(v13, rid, NODE_A, "cost", carrier="", falsifier="x", holder_id=buyer)


# ---- §J3: composition through an offtake relation -------------------------------------------------------------

def test_j3_offtake_transmits_cost_and_volume_and_not_obligation(v13):
    rid = _round(v13)
    smelter, buyer, _d = _holders(v13)
    effects.seed_transforms(v13)
    rel = effects.relation_upsert(v13, smelter, buyer, "offtake",
                                  "the buyer takes concentrate from this smelter under a term contract",
                                  node=NODE_A)["relation_id"]
    root = _root(v13, rid, holder_id=smelter, kind="volume", magnitude=-40.0,
                 magnitude_basis="the whole of the asset's output")["effect_id"]
    cost = effects.compose(v13, rid, root, rel, "cost", buyer, NODE_A,
                           carrier="the buyer's own filing", falsifier="input cost flat in the filing")
    vol = effects.compose(v13, rid, root, rel, "volume", buyer, NODE_A,
                          carrier="the buyer's shipment disclosure", falsifier="shipments unchanged")
    assert cost["transform_weight"] == 0.8 and vol["transform_weight"] == 0.9
    assert cost["depth"] == 2 and cost["attenuated_support"] < 1.0
    # the obligation does not transmit through an offtake, and the refusal says so
    with pytest.raises(ValidationError, match="does not transmit"):
        effects.compose(v13, rid, root, rel, "obligation", buyer, NODE_A,
                        carrier="a letter", falsifier="no letter")
    rows = {e["id"]: e for e in effects.list_effects(v13, rid)}
    assert rows[cost["effect_id"]]["transform_id"] and rows[cost["effect_id"]]["relation_type"] == "offtake"


# ---- §J4: two paths to one effect, discounted by MRCA depth ---------------------------------------------------

def test_j4_support_reflects_both_paths_and_early_splits_beat_late_ones(v13):
    rid = _round(v13)
    smelter, buyer, down = _holders(v13)
    effects.seed_transforms(v13)
    r_off = effects.relation_upsert(v13, smelter, buyer, "offtake", "term offtake", node=NODE_A)["relation_id"]
    r_log = effects.relation_upsert(v13, smelter, buyer, "logistics", "shares the same berth", node=NODE_A)["relation_id"]
    r_in = effects.relation_upsert(v13, buyer, down, "input_cost", "sells to this customer", node=NODE_A)["relation_id"]
    # two roots that split at the event: independent derivations
    a = _root(v13, rid, holder_id=smelter, kind="volume")["effect_id"]
    b = _root(v13, rid, holder_id=smelter, kind="timing")["effect_id"]
    effects.compose(v13, rid, a, r_off, "cost", buyer, NODE_A, carrier="filing", falsifier="flat")
    effects.compose(v13, rid, b, r_log, "timing", buyer, NODE_A, carrier="berth schedule", falsifier="on time")
    early = effects.support(v13, rid, holder_id=buyer)
    # and a pair that splits at the last node: one derivation with a rounding error
    c = _root(v13, rid, holder_id=smelter, kind="cost")["effect_id"]
    mid = effects.compose(v13, rid, c, r_off, "cost", buyer, NODE_A, carrier="filing", falsifier="flat")["effect_id"]
    effects.compose(v13, rid, mid, r_in, "cost", down, NODE_A, carrier="its price list", falsifier="prices flat")
    effects.compose(v13, rid, mid, r_in, "direction", down, NODE_A, carrier="its own guidance", falsifier="unchanged")
    late = [r for r in effects.support(v13, rid, holder_id=down)["rows"]]
    assert early["rows"] and late
    # both rankings are written every round (§F7)
    s = effects.support(v13, rid)
    assert "ranking_discounted" in s and "ranking_undiscounted" in s and "rankings_agree" in s
    pairs = [p for r in late for p in r["pairs"]]
    assert all(p["independence"] <= 1.0 for p in pairs)
    deep = [p for r in s["rows"] for p in r["pairs"] if p["mrca_depth"] >= 2]
    shallow = [p for r in s["rows"] for p in r["pairs"] if p["mrca_depth"] <= 1]
    if deep and shallow:
        assert min(p["independence"] for p in deep) <= min(p["independence"] for p in shallow)


# ---- §J5: re-rooting needs an independent carrier --------------------------------------------------------------

def test_j5_reroot_refused_without_a_carrier_and_resets_attenuation_with_one(v13):
    rid = _round(v13)
    smelter, buyer, _d = _holders(v13)
    effects.seed_transforms(v13)
    rel = effects.relation_upsert(v13, smelter, buyer, "offtake", "term offtake", node=NODE_A)["relation_id"]
    root = _root(v13, rid, holder_id=smelter, kind="volume")["effect_id"]
    child = effects.compose(v13, rid, root, rel, "cost", buyer, NODE_A, carrier="filing", falsifier="flat")
    assert child["attenuated_support"] < 1.0
    with pytest.raises(ValidationError, match="laundering"):
        effects.reroot(v13, child["effect_id"], carried_by="", basis="it must have risen")
    r = effects.reroot(v13, child["effect_id"], carried_by="the buyer's own 6-K, 2026-09-20",
                       basis="the filing states input cost rose 14% on the quarter, in its own terms")
    assert r["attenuated_support"] == 1.0 and r["root_depth"] == 1
    w = effects.width(v13, rid)
    assert w["root_depth"]["one_or_more"] >= 1 and "zero_rerooots" in w["root_depth"]


# ---- §J6: the standing ACK graph, before any event -------------------------------------------------------------

def test_j6_standing_ack_graph_and_a_forced_ack_carries_an_obligation_and_no_date(v13):
    a = acks.ack_add(v13, NODE_A, "scheduled", "quarterly results", "the issuer's IR calendar", due_at="2026-11-04")
    assert a["created"] and a["dated"]
    f = acks.ack_add(v13, NODE_A, "forced", "a force majeure letter on contracted offtake",
                     "the producer, to its counterparties",
                     obligation="a producer that cannot serve contracted offtake must notify its counterparties")
    assert f["created"] and not f["dated"]
    # a forced ACK with a date is a calendar entry wearing the wrong label, and is refused
    with pytest.raises(ValidationError, match="no public date"):
        acks.ack_add(v13, NODE_A, "forced", "a restart statement", "the operator",
                     obligation="it must say when it restarts", due_at="2026-10-01")
    with pytest.raises(ValidationError, match="calendared"):
        acks.ack_add(v13, NODE_A, "scheduled", "an undated thing", "somewhere")
    g = acks.graph_for_node(v13, NODE_A, as_of="2026-09-01")
    assert len(g["scheduled"]) == 1 and len(g["forced"]) == 1
    assert g["next"]["due_at"] == "2026-11-04"
    assert g["undated_obligations"][0]["obligation"]


# ---- §J7: firing delivers a fact, or it prunes -----------------------------------------------------------------

def test_j7_firing_names_successors_and_a_delivering_nothing_terminates(v13):
    rid = _round(v13)
    _s, buyer, _d = _holders(v13)
    e = _root(v13, rid, holder_id=buyer, kind="volume")["effect_id"]
    a = acks.ack_add(v13, NODE_A, "forced", "a stoppage statement", "the operator",
                     obligation="an operator whose plant is down must say so", round_id=rid)["ack_id"]
    seg0 = walk.lock_segment(v13, rid, "these effects survive until the stoppage statement", [e])
    fired = acks.fire(v13, a, "2026-08-25", True, round_id=rid,
                      delivered_fact="the operator confirmed the halt and named Q3",
                      implied="a halt is confirmed within 14 days",
                      successor_acks=[{"node": NODE_A, "ack_kind": "forced", "fact": "a restart date",
                                       "source": "the operator",
                                       "obligation": "a halted operator must state when it restarts"}],
                      successor_query="operator IR press page, 2026-08-25", segment_id=seg0["segment_id"])
    assert fired["delivered"] and len(fired["successor_ack_ids"]) == 1 and fired["gap"]
    seg1 = walk.lock_segment(v13, rid, "these effects survive until the restart date is named", [e],
                             opened_by_ack_id=a, opened_by_firing_id=fired["firing_id"])
    segs = walk.segments(v13, rid)
    assert [s["idx"] for s in segs] == [0, 1] and segs[1]["parent_segment_id"] == segs[0]["id"]
    assert segs[0]["claim"] != segs[1]["claim"]                     # nothing is rewritten
    # a firing that delivers nothing prunes and may not open a successor
    b = acks.ack_add(v13, NODE_A, "scheduled", "a regulator's statutory answer", "the regulator",
                     due_at="2026-09-15", round_id=rid)["ack_id"]
    with pytest.raises(ValidationError, match="terminates"):
        acks.fire(v13, b, "2026-09-15", False, round_id=rid,
                  successor_acks=[{"node": NODE_A, "ack_kind": "scheduled", "fact": "x", "source": "y",
                                   "due_at": "2026-10-01"}])
    n = acks.fire(v13, b, "2026-09-15", False, round_id=rid)
    assert n["prunes"] and not n["successor_ack_ids"]
    with pytest.raises(ValidationError, match="already fired"):
        acks.fire(v13, b, "2026-09-16", True, delivered_fact="late")


# ---- §J8: the calendar chooses the branch ----------------------------------------------------------------------

def test_j8_advancing_an_unfired_branch_is_refused(v13):
    rid = _round(v13)
    _s, buyer, _d = _holders(v13)
    _root(v13, rid, holder_id=buyer, kind="volume")
    a = acks.ack_add(v13, NODE_A, "scheduled", "results", "IR calendar", due_at="2026-10-01", round_id=rid)["ack_id"]
    b = acks.ack_add(v13, NODE_A, "scheduled", "an index review", "the index provider", due_at="2026-11-20",
                     round_id=rid)["ack_id"]
    with pytest.raises(StateError, match="has not fired"):
        walk.advance(v13, rid, b, as_of="2026-09-20")
    cal = acks.calendar(v13, rid, "2026-09-20")
    assert cal["next_to_fire"]["id"] == a
    acks.fire(v13, a, "2026-10-01", True, round_id=rid, delivered_fact="results printed")
    adv = walk.advance(v13, rid, a, as_of="2026-10-02")
    assert adv["delivered_fact"] == "results printed"
    # an ACK that delivered nothing cannot be advanced on either
    acks.fire(v13, b, "2026-11-20", False, round_id=rid)
    with pytest.raises(StateError, match="delivered nothing"):
        walk.advance(v13, rid, b, as_of="2026-11-21")


# ---- §J9: contradictions are computable, and generate edge hypotheses ------------------------------------------

def test_j9_opposite_implications_at_one_ack_are_detected_without_operator_input(v13):
    rid = _round(v13)
    smelter, buyer, down = _holders(v13)
    effects.seed_transforms(v13)
    rel = effects.relation_upsert(v13, smelter, buyer, "offtake", "term offtake", node=NODE_A)["relation_id"]
    ack = acks.ack_add(v13, NODE_A, "scheduled", "the buyer's results", "IR calendar", due_at="2026-11-04",
                       round_id=rid)["ack_id"]
    root = _root(v13, rid, holder_id=smelter, kind="volume")["effect_id"]
    effects.compose(v13, rid, root, rel, "cost", buyer, NODE_A, carrier="filing", falsifier="flat",
                    ack_id=ack, magnitude=6.0, basis="input cost rises at the results print")
    effects.compose(v13, rid, root, rel, "volume", buyer, NODE_A, carrier="shipments", falsifier="unchanged",
                    ack_id=ack, magnitude=-4.0, basis="no input cost rise at the results print")
    d = contradiction.detect(v13, rid)
    assert d["n"] >= 1
    c = d["contradictions"][0]
    assert c["ack_id"] == ack and c["dated_at"] == "2026-11-04"      # dated by construction (§D4)
    assert c["common_set"] and c["edge_hypotheses"]                  # shared ancestry is anchor-grade
    assert c["kind"] in ("internal", "opposed_on_holder")
    anch = contradiction.common_set_anchors(v13, rid)
    assert anch["n"] >= 1 and anch["anchors"][0]["required_by_n_contradictions"] >= 1
    rec = contradiction.record(v13, rid, ack, c["kind"], c["path_a"], c["path_b"], c["implies_a"], c["implies_b"],
                               c["common_set"], c["gap"], c["edge_hypotheses"])
    assert rec["dated_at"] == "2026-11-04"


# ---- §J10: exit is the first attention ACK after the structural one --------------------------------------------

def test_j10_structural_ack_with_no_attention_ack_leaves_the_divergence_open(v13):
    rid = _round(v13)
    s = acks.ack_add(v13, NODE_A, "forced", "an allocation notice", "the producer",
                     obligation="a producer short of product must allocate", round_id=rid)["ack_id"]
    acks.fire(v13, s, "2026-09-10", True, round_id=rid, delivered_fact="allocation went to 70%")
    x = contradiction.exit_ack(v13, rid, s)
    assert x["open"] and x["exit_ack"] is None and "changes nothing" in x["note"]
    acks.ack_add(v13, NODE_A, "scheduled", "sell-side note picks it up", "a covering broker", due_at="2026-09-24",
                 round_id=rid, participant_class="equity_specialist", attention=True)
    y = contradiction.exit_ack(v13, rid, s)
    assert not y["open"] and y["latency_days"] == 14


# ---- §J11: divergence_held, and pruning the converged only -----------------------------------------------------

def test_j11_converged_branches_prune_and_divergent_ones_are_refused(v13):
    a = make_rule(v13)
    rid = _round(v13)
    _s, buyer, _d = _holders(v13)
    pid = positions.position_add(v13, buyer, NODE_A, "sign_of_exposure", "-", "the buyer's own filing",
                                 "stated")["position_id"]
    near = _root(v13, rid, holder_id=buyer, kind="direction", magnitude=1.1)["effect_id"]
    far = _root(v13, rid, holder_id=buyer, kind="cost", magnitude=9.0)["effect_id"]
    ids = rounds.lock_predictions(v13, rid, [
        pred(a, target="BUY", sign="0", claim="inside its band", position_id=pid, due_at="2026-09-20",
             effect_id=near),
        pred(a, target="BUY", sign="+", claim="the cost effect shows", position_id=pid, due_at="2026-09-20",
             effect_id=far)],
        leg_claims=[{"position_id": pid, "effect_kind": "vol",
                     "no_claim": "no-claim: no option chain reading is taken on this leg in a test fixture"}])["prediction_ids"]
    assert len(ids) == 2
    c = walk.convergence(v13, rid, as_of="2026-09-01")
    assert c["divergence_held"] == 1 and len(c["converged"]) == 1
    with pytest.raises(ValidationError, match="divergent"):
        walk.prune(v13, rid, [far])
    walk.prune(v13, rid, [near])
    after = walk.convergence(v13, rid, as_of="2026-09-01")
    assert after["divergence_held"] == 1 and not after["converged"]
    assert not after["zero_divergence_held"]


# ---- §J12: bridge paths on a real round ------------------------------------------------------------------------

def test_j12_bridge_paths_reported_and_empty_is_a_valid_answer(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    effects.migrate_legs(v13, rid)
    surviving.assess_round(v13, rid)
    b = effects.bridge_paths(v13, rid)
    assert "bridge_paths" in b and "n" in b and "empty_is_an_answer" in b
    if not b["bridge_paths"]:
        assert "Empty is a valid and reportable answer" in b["note"]


# ---- §J13: both support rankings are written -------------------------------------------------------------------

def test_j13_support_written_with_and_without_the_independence_discount(v13):
    rid = _round(v13)
    smelter, buyer, down = _holders(v13)
    effects.seed_transforms(v13)
    rel = effects.relation_upsert(v13, smelter, buyer, "offtake", "term offtake", node=NODE_A)["relation_id"]
    root = _root(v13, rid, holder_id=smelter, kind="volume")["effect_id"]
    effects.compose(v13, rid, root, rel, "cost", buyer, NODE_A, carrier="filing", falsifier="flat")
    effects.compose(v13, rid, root, rel, "volume", buyer, NODE_A, carrier="shipments", falsifier="flat")
    s = effects.support(v13, rid)
    for row in s["rows"]:
        assert row["support_discounted"] <= row["support_undiscounted"] + 1e-9
    assert isinstance(s["rankings_agree"], bool)
    ip = effects.implicit_position(v13, rid)
    # nothing is at issue on these holders, so support without stake reads inert, not consensus
    assert not ip["position"]
    assert ip["inert"] or ip["below_support"]


# ---- §J14: declared synthetic exposure, coverage, and the basket_stake floor ------------------------------------

def test_j14_shared_currency_and_venue_are_declared_and_a_low_basket_stake_is_a_wall(v13):
    rid = _round(v13)
    _s, buyer, down = _holders(v13)
    effects.node_upsert(v13, "usd_reporting", "attribute", "reporting_currency", "both report in USD")
    effects.node_upsert(v13, "us_listing", "attribute", "listing_venue", "both listed in the US")
    for h in (buyer, down):
        positions.position_add(v13, h, "usd_reporting", "sign_of_exposure", "+", "the filings", "stated")
        positions.position_add(v13, h, "us_listing", "sign_of_exposure", "+", "the exchange", "stated")
    d = exposure.declare(v13, rid, [{"attribute_node": "usd_reporting", "net_sign": "+", "magnitude": 0.6},
                                    {"attribute_node": "us_listing", "net_sign": "+", "magnitude": 0.5}],
                         intended_residual=0.4,
                         basis="both legs report in USD and list in the US; the pair does not cancel either",
                         holder_ids=[buyer, down])
    assert d["floor"] is True and d["declared_exposure"] == 1.1
    assert d["basket_stake"] == pytest.approx(0.3636, abs=1e-3) and d["below_floor"] and d["wall"]
    assert d["attribute_coverage"] is not None
    # an unregistered attribute node is refused: the graph must know it is a loading, never a path
    with pytest.raises(ValidationError, match="not registered as an attribute node"):
        exposure.declare(v13, rid, [{"attribute_node": "something_undeclared", "net_sign": "+", "magnitude": 1.0}],
                         intended_residual=2.0, basis="a loading nobody registered")
    with pytest.raises(ValidationError, match="cannot be named"):
        exposure.declare(v13, rid, [], intended_residual=1.0, basis="nothing to say about it")


# ---- §J15: traversal refuses a non-transmitting edge, construction sums over both ------------------------------

def test_j15_attribute_edges_are_summed_and_never_traversed(v13):
    rid = _round(v13)
    _s, buyer, down = _holders(v13)
    effects.seed_transforms(v13)
    attr = effects.relation_upsert(v13, buyer, down, "reporting_currency", "both report in USD")
    assert not attr["transmits"] and attr["mode"] == "attribute"
    root = _root(v13, rid, holder_id=buyer, kind="cost")["effect_id"]
    with pytest.raises(ValidationError, match="does not transmit"):
        effects.compose(v13, rid, root, attr["relation_id"], "cost", down, NODE_A,
                        carrier="its price list", falsifier="flat")
    t = exposure.traverse_or_sum(v13, attr["relation_id"])
    assert t["may_traverse"] is False and t["summed_in_construction"] is True
    ok = effects.relation_upsert(v13, buyer, down, "input_cost", "sells to this customer")
    assert exposure.traverse_or_sum(v13, ok["relation_id"])["may_traverse"] is True


# ---- §J16: the frontier bound refuses, and lists what would have opened -----------------------------------------

def test_j16_frontier_bound_refuses_and_names_the_branches(v13, monkeypatch):
    from harness import config
    monkeypatch.setattr(config, "FRONTIER_BOUND", 3)
    rid = _round(v13)
    smelter, buyer, _d = _holders(v13)
    effects.seed_transforms(v13)
    rel = effects.relation_upsert(v13, smelter, buyer, "offtake", "term offtake", node=NODE_A)["relation_id"]
    root = _root(v13, rid, holder_id=smelter, kind="volume")["effect_id"]
    effects.compose(v13, rid, root, rel, "cost", buyer, NODE_A, carrier="filing", falsifier="flat")
    effects.compose(v13, rid, root, rel, "volume", buyer, NODE_A, carrier="shipments", falsifier="flat")
    with pytest.raises(ValidationError, match="frontier bound"):
        effects.compose(v13, rid, root, rel, "timing", buyer, NODE_A, carrier="berth", falsifier="on time")
    fc = effects.frontier_check(v13, rid, adding=1)
    assert not fc["within_bound"] and fc["would_open"]


# ---- §0b.1 / §J17: the D2 wall cannot fail silently ------------------------------------------------------------

def test_j17_reencode_lookup_failure_reads_unevaluable_and_the_leg_cannot_clear(v13, monkeypatch):
    from harness import risk
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    leg = {"holder_id": H["pool"], "node": NODE_A, "all_position_ids": [P["pool"]]}
    props = surviving.leg_properties(v13, rid, leg, "2026-07-15")
    ok, _ = vector.pricedness_term(v13, props, rid, leg)
    assert ok is not None

    def boom(*a_, **k_):
        raise RuntimeError("the re-encode lookup fell over")
    monkeypatch.setattr(risk, "reencode_for_leg", boom)
    val, basis = vector.pricedness_term(v13, props, rid, leg)
    assert val is None and "unevaluable" in basis and "the re-encode lookup failed" in basis
    v = vector.leg_vector(v13, rid, leg, props)
    assert v["terms"]["pricedness"] is None
    assert "pricedness" in v["unknown_terms"]
    assert v["clears_appetite"] is False


# ---- §0b.2 / §J18: an unresolvable rule id costs the leg, and shows in the blind view ---------------------------

def test_j18_unresolved_rule_penalises_structural_and_appears_in_the_blind_view(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    leg = {"holder_id": H["pool"], "node": NODE_A, "all_position_ids": [P["pool"]]}
    props = surviving.leg_properties(v13, rid, leg, "2026-07-15")
    v13.execute("UPDATE library_rules SET weight = 4.0 WHERE id = ?", (a,))   # a rule whose weight can be seen
    good, gbasis = vector.structural_term(v13, dict(props, mechanisms=[a]), leg)
    bad, bbasis = vector.structural_term(v13, dict(props, mechanisms=[a, "lib.no-such-rule"]), leg)
    assert "rule_unresolved" in bbasis and "no rule cited" in bbasis
    assert bad < good                                   # it costs something; it is not free
    assert "rule_unresolved" not in gbasis
    # and the second scorer is shown the id it could not resolve, rather than nothing (§0b.4)
    rid2 = _round(v13)
    ids = rounds.lock_predictions(v13, rid2, [pred(a, due_at="2026-09-20")])["prediction_ids"]
    rounds.open_retrieval(v13, rid2, event_date_confirmed="2026-09-07", date_source="test fixture")
    scorer.score_round(v13, rid2, [{"prediction_id": ids[0], "outcome": "hit", "mechanism_outcome": "unknown",
                                    "baseline_outcome": "miss", "evidence_ids": [], "scorer_note": "resolved early in a fixture", "early": True}])

    def gone(conn_, rid_):
        raise KeyError(f"the store cannot resolve {rid_}")
    import harness.scorer as sc
    real = sc.resolve_rule
    try:
        sc.resolve_rule = gone
        view = sc.second_scorer_view(v13, rid2)
    finally:
        sc.resolve_rule = real
    cited = view["predictions"][0]["cited_rules"]
    assert cited and cited[0]["status"] == "unresolved" and cited[0]["id"] == a
    assert "score its mechanism_outcome unknown" in cited[0]["note"]


# ---- §0b.3 / §J19: a round that cannot be viewed is reported, not dropped ---------------------------------------

def test_j19_second_scorer_batch_returns_its_failures(v13, monkeypatch):
    from harness import scorer as sc
    a = make_rule(v13)
    rid = _round(v13)
    ids = rounds.lock_predictions(v13, rid, [pred(a, due_at="2026-09-20")])["prediction_ids"]
    rounds.open_retrieval(v13, rid, event_date_confirmed="2026-09-07", date_source="test fixture")
    sc.score_round(v13, rid, [{"prediction_id": ids[0], "outcome": "hit", "mechanism_outcome": "right",
                               "baseline_outcome": "miss", "evidence_ids": [], "scorer_note": "resolved early in a fixture", "early": True}])
    good = sc.second_scorer_batch(v13)
    assert good["n_failures"] == 0 and rid in good["rounds"]

    real = sc.second_scorer_view

    def boom(conn, round_id, nodes=None):
        if round_id == rid:
            raise RuntimeError("the blind view fell over")
        return real(conn, round_id, nodes)
    monkeypatch.setattr(sc, "second_scorer_view", boom)
    bad = sc.second_scorer_batch(v13)
    assert bad["n_failures"] == 1 and bad["failures"][0]["round_id"] == rid
    assert "the blind view fell over" in bad["failures"][0]["error"]
    assert "WARNING" in bad["note"] and rid not in bad["rounds"]


# ---- §0b.5 / §J20: unknown stake means the binding term is unassessable ------------------------------------------

def test_j20_binding_term_is_unassessable_when_an_unknown_term_could_bind_lower(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    leg = {"holder_id": H["pool"], "node": NODE_A, "all_position_ids": [P["pool"]]}
    props = surviving.leg_properties(v13, rid, leg, "2026-07-15")
    v = vector.leg_vector(v13, rid, leg, dict(props, expected_move_pct=None, band_pct=4.0))
    assert v["terms"]["stake"] is None and "stake" in v["unknown_terms"]
    assert v["binding_term"] == "unassessable"
    assert v["lowest_computable_term"] in ("structural", "pricedness", "operator", "expression")
    assert v["binding_value"] is None and "cannot be named" in v["binding_basis"]
    # an unknown term cannot bind below zero, so a term already at zero still binds
    z = vector.leg_vector(v13, rid, leg, dict(props, expected_move_pct=None, band_pct=None, listed=False,
                                              options_listed=False))
    if z["ratio_to_appetite"]["expression"] == 0.0:
        assert z["binding_term"] == "expression"
    # summarise buckets them separately and reports what could not be computed at all
    rows = [{"vector": v}, {"vector": z}]
    s = vector.summarise(rows)
    assert s["unassessable"] >= 1 and s["uncomputable"]["stake"] == 2 and s["n"] == 2
    assert sum(s[t] for t in ("stake", "structural", "pricedness", "operator", "expression")) + s["unassessable"] \
        + s["none"] == 2


# ---- the assessed round still reads, and reports the corrected distribution ------------------------------------

def test_wall_map_reruns_after_the_binding_term_fix(v13):
    a = make_rule(v13)
    rid, H, P = two_node_round(v13, a)
    r = surviving.assess_round(v13, rid, write=False)
    bt = r["binding_terms"]
    assert "unassessable" in bt and "uncomputable" in bt and bt["n"] == r["legs"]
    # nothing is attributed to a computable term while an unknown one could bind lower
    for res in r["results"]:
        unknown = [t for t, val in res["terms"].items() if val is None]
        if unknown and min(v for v in res["ratio"].values() if v is not None) > 0:
            assert res["binding_term"] == "unassessable"


# ---- §E: an unreadable frontier is not a converged one ---------------------------------------------------------

def test_convergence_distinguishes_unreadable_from_converged(v13):
    """Round 15 found this live: divergence_held read 0 with nothing readable, and the note said the frontier had
    converged to price. It had never been compared to price. Unevaluable is a value, not a verdict -- and it is
    certainly not convergence."""
    rid = _round(v13)
    _s, buyer, _d = _holders(v13)
    _root(v13, rid, holder_id=buyer, kind="direction", magnitude=4.0)
    c = walk.convergence(v13, rid, as_of="2026-09-01")
    assert c["divergence_held"] == 0
    assert c["state"] == "unreadable" and c["divergence_unevaluable"] is True
    assert c["zero_divergence_held"] is False           # the failure verdict must not fire on missing data
    assert "NOTHING WAS READABLE" in c["note"] and c["unreadable_branches"] == 1
