"""v8 brief: §A carriage, §B branches, §C validation and bias, §D carriers and scheduled facts, §E synthetics, §F narrative.
§G smoke tests 1-7."""
import pytest

from harness import basket, carriers, facts, hypotheses, library, names, positions, predicates, rounds, scorer, synthetic
from harness.errors import ValidationError

from conftest import TEST_MODEL, TODAY, dated_evidence, make_round, make_rule, play_round, pred, res


# §G.1 / A2: a sign + call citing an ordering-only rule is refused ---------------------------------------------

def test_g1_citation_refused_by_carriage(conn):
    fm = make_rule(conn, "a producer's force majeure declaration is the fastest public carrier of a plant outage", carries=["ordering"])
    rid = make_round(conn)
    with pytest.raises(ValidationError, match=r"carries \['ordering'\]; this call is \['occurrence'\]"):
        rounds.lock_predictions(conn, rid, [pred(fm, claim="the operator declares force majeure within 14 days")])
    # the same rule on a magnitude_order call (ordering) is accepted
    rounds.lock_predictions(conn, rid, [pred(fm, call_type="magnitude_order", magnitude_rank=1, sign=None,
                                             claim="force majeure notice precedes the first price print")])
    assert library.claim_kinds("sign", "0") == {"absence"} and library.claim_kinds("lag_band", None) == {"duration"}
    with pytest.raises(ValidationError, match="carries is required"):
        library.propose(conn, "a rule with no carriage", "x", 2, "sequence", "test")
    assert library.propose(conn, "an operator note", "x", 2, "operator", "test")["carries"] == []


def test_carriage_retroactive_in_rebuild(conn):
    """A citation on a kind the rule does not carry is not a trial of the rule, even on old rows."""
    a = make_rule(conn, carries=["ordering"])
    rid = make_round(conn)
    # lenient lock (as retro seed rounds do) lets the bad citation through; the rebuild ignores it
    ids = rounds.lock_predictions(conn, rid, [pred(a)], strict=False)["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], "miss", "unknown")])
    r = library.get_rule(conn, a)
    assert r["trials"] == 0 and r["misses"] == 0 and r["weight"] == 0.0
    assert library.rebuild_library_stats(conn)["citations_excluded_by_carriage"] == 1


# §G.2 / B1: branches and conditional rows ------------------------------------------------------------------------

def test_g2_branches_and_conditional_rows(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    with pytest.raises(ValidationError, match=">=2 distinct"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="map", target="map: operator", claim="which operator", falsifier=None, branches=["A"])])
    with pytest.raises(ValidationError, match="must come before"):
        rounds.lock_predictions(conn, rid, [pred(a, target="x", conditional_on={"prediction_ref": "#1", "branch": "A"}),
                                            pred(None, call_type="map", target="map: operator", claim="which operator", falsifier=None, branches=["A", "B"])])
    with pytest.raises(ValidationError, match="not one of"):
        rounds.lock_predictions(conn, rid, [pred(None, call_type="map", target="map: operator", claim="which operator", falsifier=None, branches=["A", "B"]),
                                            pred(a, target="x", conditional_on={"prediction_ref": "#0", "branch": "C"})])
    ids = rounds.lock_predictions(conn, rid, [
        pred(None, call_type="map", target="map: operator", claim="the operator is A", falsifier="B is named", branches=["A", "B"]),
        pred(a, target="A equity", claim="premia rise first", conditional_on={"prediction_ref": "#0", "branch": "A"}),
        pred(a, target="B equity", claim="premia rise first", conditional_on={"prediction_ref": "#0", "branch": "B"}),
        pred(None, call_type="meta", target="one-trade", claim="no-mechanism: short B", carrier=None, falsifier=None,
             conditional_on={"prediction_ref": "#0", "branch": "B"}),
    ])["prediction_ids"]
    p = rounds.list_predictions(conn, rid)
    assert p[0]["branches"] == ["A", "B"] and p[2]["conditional_on"] == {"prediction_id": ids[0], "branch": "B"}
    rounds.open_retrieval(conn, rid)
    with pytest.raises(ValidationError, match="branch_arose"):
        scorer.score_round(conn, rid, [res(ids[0], "hit"), res(ids[1], "hit"), res(ids[2], "miss"), res(ids[3], "untestable")])
    before = library.get_rule(conn, a)["weight"]
    card = scorer.score_round(conn, rid, [
        res(ids[0], "hit", "unknown", branch_arose="A"),
        res(ids[1], "hit", "right"),
        res(ids[2], "miss", "wrong"),          # branch B did not arise: forced untestable at weight 0
        res(ids[3], "hit", "unknown"),
    ])
    r = rounds.latest_resolutions(conn, rid)
    assert r[ids[2]]["outcome"] == "untestable" and r[ids[2]]["weight"] == 0 and "did not arise" in r[ids[2]]["scorer_note"]
    assert r[ids[3]]["outcome"] == "untestable" and r[ids[1]]["outcome"] == "hit"
    assert card["branch_dead_rows"] == 2 and card["map_score"] == 1.0
    rule = library.get_rule(conn, a)
    assert rule["misses"] == 0 and rule["hits"] == 1 and rule["weight"] > before


# §G.3 / C1: validation needs a qualifying positive hit --------------------------------------------------------------

def test_g3_validation_needs_real_positive_hit(conn):
    a = make_rule(conn)
    # two clean absence hits under thin coverage with mechanism unknown: weight crosses, status does not
    for i in range(3):
        play_round(conn, [pred(a, sign="0", claim="no attributable move")],
                   lambda ids: [res(ids[0], "hit", "unknown", evidence_ids=[])], text=f"abs{i}")
    r = library.get_rule(conn, a)
    assert r["weight"] >= 1.0 and r["clean_hit_rounds"] == 3 and r["status"] == "candidate"
    # one clean positive hit, mechanism right, adequate coverage: validates
    rid = make_round(conn, text="pos")
    ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], "hit", "right", evidence_ids=[dated_evidence(conn, rid)])])
    assert library.get_rule(conn, a)["status"] == "validated"


def test_c2_bias_classes(conn):
    a = make_rule(conn)
    rid, ids, _ = play_round(conn, [pred(a), pred(a, target="b"), pred(a, target="c")],
                             lambda ids: [res(ids[0]), res(ids[1]), res(ids[2], "miss", "wrong")])
    scorer.second_score(conn, rid, [
        {"prediction_id": ids[0], "outcome": "miss", "mechanism_outcome": "wrong", "baseline_outcome": "miss", "source_coverage": "adequate"},
        {"prediction_id": ids[1], "outcome": "unverified", "mechanism_outcome": "unknown", "baseline_outcome": "miss", "source_coverage": "thin"},
        {"prediction_id": ids[2], "outcome": "hit", "mechanism_outcome": "right", "baseline_outcome": "miss"},
    ])
    b = scorer.scorer_bias(conn)
    assert b["compared"] == 3 and b["lenient"] == 2 and b["under_informed"] == 2 and b["self_stricter"] == 2
    assert b["counts_toward_discount"] == 2


# §G.4 / D2: carriers registry and Q7 ------------------------------------------------------------------------------

def test_g4_carrier_unreachable_flag(conn):
    a = make_rule(conn)
    chk = carriers.check(conn, ["ICIS Africa PE assessments", "owner statements; trade press", "port notices"])
    assert chk["carrier_unreachable"] == ["ICIS Africa PE assessments"] and chk["q7_computed"].startswith("pass")
    rid = make_round(conn)
    r = rounds.lock_predictions(conn, rid, [pred(a, carrier="ICIS weekly PE assessment"), pred(a, target="b", carrier="ChemWeek report")])
    assert [f["index"] for f in r["carrier_unreachable"]] == [0, 1] and r["q7_computed"].startswith("fail")
    eid = rounds.round_status(conn, rid)["event_id"]
    assert rounds.current_criteria(conn, eid)["current"]["Q7"].startswith("fail") and not rounds.current_criteria(conn, eid)["criteria_pass"]
    assert rounds.list_predictions(conn, rid)[0]["carrier_status"] == "unreachable"
    carriers.carrier_upsert(conn, "ICIS", "price_assessment", "open", note="subscription bought")
    assert carriers.resolve(conn, "ICIS weekly")["status"] == "open"


# §G.5 / E: synthetic legs -----------------------------------------------------------------------------------------

def test_g5_synthetic_build(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    node = "strait_of_hormuz_tanker_transit"
    hs = {n: names.holder_upsert(conn, n, "company", listed=listed, ticker=n[:3].upper())["holder_id"]
          for n, listed in (("Tanker Owner", True), ("Refiner", True), ("Private Trader", False))}
    positions.position_add(conn, hs["Tanker Owner"], node, "sign_of_exposure", "+", "s", "stated")
    positions.position_add(conn, hs["Refiner"], node, "sign_of_exposure", "-", "s", "stated")
    positions.position_add(conn, hs["Private Trader"], node, "sign_of_exposure", "-", "s", "stated")
    rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": d, "node": node, "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}
                                       for h, d in ((hs["Tanker Owner"], 1), (hs["Refiner"], 2), (hs["Private Trader"], 1))])
    r = synthetic.synthetic_build(conn, rid, node, "syn.tradability_opposing")      # v9 C1: before lock
    assert r["built"] and r["n_components"] == 2 and {c["sign"] for c in r["components"]} == {1, -1}
    assert r["support_weight"] == pytest.approx(r["weakest_component"] * 0.85) and r["support_weight"] <= r["weakest_component"]
    b = basket.event_basket(conn, rid)
    assert len(b["synthetics"]) == 1 and b["synthetics"][0]["gate"]["prima_facie"] == "holds" and b["synthetics"][0]["listed_components"] == 2
    # a node with no opposing listed pair reports why
    r2 = synthetic.synthetic_build(conn, rid, "some_other_node", "syn.tradability_opposing")
    assert not r2["built"] and "no opposing listed pair" in r2["reason"]
    r3 = synthetic.synthetic_build(conn, rid, node, "syn.time_toll_cargo")
    assert not r3["built"] and "toll-booth/cargo" in r3["reason"]
    rounds.lock_predictions(conn, rid, [pred(a)])
    # per-leg predicate checks accept the synthetic as a leg
    gate = predicates.predicate_add(conn, "tradability gate (single-name and pair forms)", "arming", "s", "t", key="pred.arm.tradability_gate")["predicate_id"]
    predicates.predicate_check(conn, rid, [{"predicate_id": gate, "claimed": "holds", "basis": "two listed opposing components", "observed": "holds", "position_id": r["synthetic_id"]}])
    b2 = basket.event_basket(conn, rid)
    assert b2["synthetics"][0]["armed"] and b2["armed_leg_count"] >= 1      # v12 0.3: computed gates arm the natural legs too


# §G.6 / F1: narrative rows -----------------------------------------------------------------------------------------

def test_g6_narrative_rows_and_divergence(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True)["holder_id"]
    pid = positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "s", "stated")["position_id"]
    rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": 1, "node": "node x", "position_summary": "x", "substitutability": "low"}])
    def narrative(**kw):
        base = dict(call_type="narrative", target="Alpha Plc on node x", claim="the trade press says Alpha gains from the outage",
                    carrier="trade press commentary", falsifier="no such commentary within the window", narrative_sign="+",
                    position_id=pid, sign=None)
        base.update(kw)
        return pred(None, **base)
    with pytest.raises(ValidationError, match="price series"):
        rounds.lock_predictions(conn, rid, [narrative(carrier="ICIS price assessment")])
    with pytest.raises(ValidationError, match="narrative_sign"):
        rounds.lock_predictions(conn, rid, [narrative(narrative_sign=None)])
    with pytest.raises(ValidationError, match="carry no mechanism"):
        rounds.lock_predictions(conn, rid, [narrative(mechanism_ids=[a])])
    ids = rounds.lock_predictions(conn, rid, [narrative(), pred(a, target="Alpha Plc", sign="-", claim="alpha falls first", position_id=pid)])["prediction_ids"]
    b = basket.event_basket(conn, rid)
    leg = b["legs"][0]
    assert leg["narrative"][0]["divergence"] is True and b["divergent_legs"] == 1 and leg["structural_sign" if False else "sign"] == "-"
    rounds.open_retrieval(conn, rid)
    card = scorer.score_round(conn, rid, [res(ids[0], "hit", "unknown"), res(ids[1], "hit", "right")])
    assert card["narrative_rows"] == 1 and card["narrative_said_it"] == 1
    assert library.get_rule(conn, a)["trials"] == 1      # narrative rows never touch the library
    ps = scorer.programme_stats(conn)
    assert ps["narrative_divergence"]["divergent_legs"] == 1 and ps["narrative_divergence"]["resolutions"] == {"channel_said_it=hit": 1}


# §G.7 / D3: scheduled facts at reveal -------------------------------------------------------------------------------

def test_g7_scheduled_fact_in_reveal(conn):
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True)["holder_id"]
    positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "s", "stated")
    facts.node_fact_add(conn, "alpha_calendar", "scheduled", "FY results release", "company calendar", holder_id=h, source_time="2026-07-18")
    facts.node_fact_add(conn, "alpha_calendar", "scheduled", "AGM", "company calendar", holder_id=h, source_time="2026-09-30")
    rid = rounds.submit_event(conn, "fire at node x", "2026-07-16", "s", "r", 0, {"Q1": "pass"}, node="node x",
                              operator_model=TEST_MODEL, today=TODAY)["round_id"]
    ctx = rounds.reveal_event(conn, rid)["context"]
    assert [f["text"] for f in ctx["scheduled"]] == ["FY results release"]
    assert rounds.latest_reveal_context(conn, rid)["scheduled"][0]["canonical_name"] == "Alpha Plc"


# B2: map candidates at reveal ----------------------------------------------------------------------------------------

def test_b2_map_prior_at_reveal(conn):
    big = names.holder_upsert(conn, "Big Operator", "company", listed=True)["holder_id"]
    small = names.holder_upsert(conn, "Small Operator", "company")["holder_id"]
    for h, share in ((big, "70%"), (small, "30%")):
        positions.position_add(conn, h, "site y", "sign_of_exposure", "-", "s", "stated")
        positions.position_add(conn, h, "site y", "share", share, "s", "stated")
    ctx = rounds.reveal_context_for(conn, "site y", "fire", "2026-07-16")
    assert ctx["map_prior"] == "Big Operator" and len(ctx["map_candidates"]) == 2 and "branches" in ctx["map_note"]


# follow-ups after the human's v8 rulings ---------------------------------------------------------------------------

def test_meta_rows_carry_ordering_and_magnitude(conn):
    """Ruling 2: a 'largest move is physical' meta row is an ordering claim; an absence-only rule cannot be credited by it."""
    absence_only = make_rule(conn, "a cut into a glut is silent", carries=["absence"])
    mag = make_rule(conn, "equity visibility equals event size over tide", carries=["absence", "magnitude"])
    rid = make_round(conn)
    with pytest.raises(ValidationError, match="carries"):
        rounds.lock_predictions(conn, rid, [pred(absence_only, call_type="meta", claim="largest relative move is physical", carrier=None, falsifier=None, sign=None)])
    ids = rounds.lock_predictions(conn, rid, [pred(mag, call_type="meta", claim="largest relative move is physical", carrier=None, falsifier=None, sign=None)])["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], "hit", "right", evidence_ids=[dated_evidence(conn, rid)])])
    r = library.get_rule(conn, mag)
    assert r["trials_as_carried"] == 1 and r["weight_state"] == "tested"
    u = library.get_rule(conn, absence_only)
    assert u["trials_as_carried"] == 0 and u["weight"] == 0.0 and u["weight_state"] == "untested as carried"


def test_intake_carrier_density_and_rejections(conn):
    assert carriers.open_for_kind(conn, "refinery")["qualifies"] and "TCEQ emissions event" in carriers.open_for_kind(conn, "refinery")["open_carriers"]
    assert not carriers.open_for_kind(conn, "other")["qualifies"]
    r = rounds.submit_event(conn, "an outage somewhere", "2026-07-16", "s", "first-qualifier", 0, {"Q1": "pass", "Q7": "unknown"},
                            operator_model=TEST_MODEL, today=TODAY, node_kind="other", rejections=["July 12 mill fire: Q5 fail", "July 14 strike: Q1 fail"])
    assert not r["criteria_pass"] and r["rejections_logged"] == 2 and not r["carrier_density"]["qualifies"]
    notes = [n["note"] for n in rounds.list_notes(conn, r["round_id"])]
    assert any(n.startswith("rejected before this event") for n in notes) and any("carrier density" in n for n in notes)
    ev = rounds.round_status(conn, r["round_id"])["event_id"]
    assert rounds.current_criteria(conn, ev)["current"]["Q7"].startswith("fail: computed at intake")
    assert conn.execute("SELECT rejected_before FROM events WHERE id = ?", (ev,)).fetchone()[0] == 2


def test_pit_fetch_guard_and_log(conn):
    from harness import pit
    rid = rounds.submit_event(conn, "fire at node x", "2026-07-16", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)["round_id"]
    calls = []

    def fake(url, timeout=30):
        calls.append(url)
        if "archive.org/wayback/available" in url:
            return b'{"archived_snapshots": {"closest": {"available": true, "url": "https://web.archive.org/web/20260710/https://x", "timestamp": "20260710120000"}}}'
        if "web.archive.org" in url:
            return b"<html><body><h1>Operator: Alpha Plc</h1><script>x</script></body></html>"
        raise AssertionError(url)
    with pytest.raises(Exception, match="strictly before the event"):
        pit.pit_fetch(conn, "wayback", "https://x", "2026-07-16", "who operates the plant", fetch=fake)
    r = pit.pit_fetch(conn, "wayback", "https://x", "2026-07-15", "who operates the plant", fetch=fake)
    assert r["found"] and r["snapshot_date"] == "2026-07-10" and r["knowable_from"] == "2026-07-10" and "Operator: Alpha Plc" in r["text"] and "script" not in r["text"]
    logged = pit.list_fetches(conn, rid)
    assert len(logged) == 1 and logged[0]["status"] == "found" and logged[0]["reason"] == "who operates the plant"
    with pytest.raises(ValidationError, match="reason"):
        pit.pit_fetch(conn, "wayback", "https://x", "2026-07-15", "", fetch=fake)
    # a snapshot later than as_of is refused
    def late(url, timeout=30):
        return b'{"archived_snapshots": {"closest": {"available": true, "url": "u", "timestamp": "20260720120000"}}}'
    assert not pit.pit_fetch(conn, "wayback", "https://y", "2026-07-15", "check", fetch=late)["found"]
