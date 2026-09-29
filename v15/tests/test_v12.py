"""v12 brief: §0 corrections (real bands, practice-dated rules, the gate-check bug, scoped scoring sessions),
§D implied at lock, §E participant-class divergence, §F base rates, §H the A/B. §I smoke tests 1-9."""
import json

import pytest

from harness import basket, edge, enumeration, library, names, positions, predicates, prices, replay, risk, rounds, scorer
from harness.errors import StateError, ValidationError

from conftest import TEST_MODEL, TODAY, make_rule, pred, res
from test_v10 import NODE_A, NODE_B, submit, two_node_round, v10      # noqa: F401


def _chart(closes_by_symbol):
    """A fake chart API: {symbol: [(date, close), ...]}."""
    import datetime as dt
    def fetch(url, timeout=25):
        sym = url.split("/chart/")[1].split("?")[0]
        rows = closes_by_symbol[sym]
        ts = [int(dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp()) for d, _ in rows]
        return json.dumps({"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"close": [c for _, c in rows]}]}}]}}).encode()
    return fetch


def _series(start="2026-08-01", n=40, base=100.0, step=0.2, spike_at=None, spike=1.0):
    import datetime as dt
    d, out = dt.date.fromisoformat(start), []
    for i in range(n):
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        v = base + (i % 3) * step
        if spike_at and d.isoformat() >= spike_at:
            v = base * spike
        out.append((d.isoformat(), round(v, 4)))
        d += dt.timedelta(days=1)
    return out


# §I.1 / 0.1: a real 20-session band, and the re-encode test runs at ordinary magnitudes -------------------------------

def test_i1_real_bands(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)          # event 2026-09-07
    v10.execute("UPDATE holders SET price_symbol = 'POOL' WHERE id = ?", (H["pool"],))
    rows = _series("2026-08-01", 40, 100.0, 0.2, spike_at="2026-09-08", spike=1.06)
    fetch = _chart({"POOL": rows})
    b = prices.band_for("POOL", "2026-09-07", fetch=fetch)
    assert b["sessions_available"] >= 20 and b["reference_date"] < "2026-09-07" and b["band_method"].startswith(f"{b['sessions_available']}-session empirical")
    width = (b["band_high"] - b["band_low"]) / b["reference_close"]
    assert width < 0.10       # a real 20-session band on a quiet series is tight, not catastrophe-only
    rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20")])
    rounds.open_retrieval(v10, rid)
    r = prices.backfill_round(v10, rid, fetch=fetch)
    pool = next(x for x in r["legs"] if x["holder"] == "Pool Corporation")
    assert pool["observations"] > 0 and pool["out_of_band"] > 0 and pool["sessions"] >= 20
    assert all("empirical band" in o["band_method"] and "prior close" in o["band_method"]
               for o in v10.execute("SELECT band_method FROM price_observations WHERE round_id = ?", (rid,)))
    # a 6% move is out of band and is *not* a re-encode, because nothing attributed it to the event
    assert basket.event_basket(v10, rid)["legs"][0]["reencode"]["reencode_date"] is None


# §I.2 / 0.2: practice-dating flattens the curve and `origin` keeps the two mirrors apart ------------------------------

def test_i2_practice_dated_rules(v10):
    before = {r["key"]: r["knowable_from"] for r in risk.list_risk_rules(v10)}
    assert before["risk.tide_visibility"] == "2026-04-03"
    out = risk.practice_date_rules(v10)
    after = {r["key"]: (r["knowable_from"], r["origin"]) for r in risk.list_risk_rules(v10)}
    assert all(v == ("1900-01-01", "practice") for v in after.values()) and len(out["changed"]) == 7
    assert risk.list_risk_rules(v10)[0]["origin"] == "practice"
    # a rule genuinely novel to practice keeps its own date and is marked programme
    risk.risk_rule_add(v10, "risk.novel", "a rule this programme found", "veto", {"effect_kinds": ["vol"]}, "2026-09-08")
    v10.execute("UPDATE risk_rules SET origin = 'programme' WHERE key = 'risk.novel'")
    assert {r["origin"] for r in risk.list_risk_rules(v10)} == {"practice", "programme"}
    # coverage is now flat across event dates for the practice rules
    a = make_rule(v10)
    early = submit(v10, text="early", date="2026-04-05")["round_id"]
    h = names.holder_upsert(v10, "Early Plc", "company", listed=True)["holder_id"]
    positions.position_add(v10, h, "n", "sign_of_exposure", "-", "s", "stated")
    rounds.touched_set_add(v10, early, [{"holder_id": h, "degree": 1, "node": "n", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}])
    rounds.lock_predictions(v10, early, [pred(a, due_at="2026-04-20")])
    rounds.open_retrieval(v10, early)
    late, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, late, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20")])
    rounds.open_retrieval(v10, late)
    before = replay.replay_round(v10, early, write=False, stack="v11")["mirror_share"]
    after = replay.replay_round(v10, early, write=False, stack="v12")["mirror_share"]
    assert after < before      # the early round was mostly mirror only because the rules were dated by our learning


# §I.3 / 0.3: the gate is computed where the operator wrote no check --------------------------------------------------

def test_i3_computed_gate(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, rid, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20")])
    legs = predicates.armed_legs(v10, rid)
    assert legs and all(l["gate_source"] == "computed" for l in legs)
    node_a = [l for l in legs if l["node"] == NODE_A and l["computed_gate"]]
    assert node_a and not any(l["computed_gate"]["gate"] == "holds" for l in node_a)   # one-sided node: no opposing listed pair
    # give the node an opposing listed pair and the computed gate holds on the pair form
    h = names.holder_upsert(v10, "Buyer Plc", "company", listed=True, ticker="BUY")["holder_id"]
    positions.position_add(v10, h, NODE_A, "sign_of_exposure", "-", "s", "inferred")
    g = predicates.computed_gate(v10, rid, H["pool"], NODE_A)
    assert g["gate"] == "holds" and g["form"] == "pair" and "Buyer Plc" in g["basis"]
    # an operator check still wins over the computed reading
    gate = v10.execute("SELECT id FROM predicates WHERE key = 'pred.arm.tradability_gate'").fetchone()[0]
    predicates.predicate_check(v10, rid, [{"predicate_id": gate, "claimed": "fails", "observed": "fails",
                                           "basis": "below visibility", "position_id": P["pool"]}])
    leg = next(l for l in predicates.armed_legs(v10, rid) if l["position_id"] == P["pool"])
    assert leg["gate_source"] == "checked" and leg["arming_status"] == "gate_fail"


# §I.4 / 0.4: retrieval lives inside a scoring session -----------------------------------------------------------------

def test_i4_scoping_scoring_sessions(v10):
    from harness import hook
    a = make_rule(v10)
    rid = submit(v10, text="a scoped round")["round_id"]
    rounds.round_note(v10, rid, "lock", "no-touched-set: test")
    ids = rounds.lock_predictions(v10, rid, [pred(a, due_at="2026-09-20"), pred(a, target="b", due_at="2026-10-20")])["prediction_ids"]
    rounds.open_retrieval(v10, rid)
    scorer.score_call(v10, rid, res(ids[0], "hit", "right"), today="2026-09-21")
    assert rounds.round_state(v10, rid) == "partially_scored"
    s = scorer.open_scoring(v10, rid, [ids[1]], note="scoring the second call")
    assert s["session_id"] and scorer.open_session(v10)["id"] == s["session_id"]
    with pytest.raises(StateError, match="already open"):
        scorer.open_scoring(v10, rid, [ids[1]])
    scorer.close_scoring(v10)
    with pytest.raises(ValidationError, match="already resolved"):
        scorer.open_scoring(v10, rid, [ids[0]])
    v = scorer.firewall_violation(v10, "WebSearch", "a fetch about an event with no call in the session")
    assert v["violation_id"] and v10.execute("SELECT COUNT(*) FROM firewall_violations").fetchone()[0] == 1
    assert scorer.open_session(v10) is None      # closed by the raises-block above


# §I.5-6 / D: implied at lock, and the two executability tests ----------------------------------------------------------

def test_i5_i6_implied_and_executability(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    with pytest.raises(ValidationError, match="implied_at_lock is required"):
        rounds.lock_predictions(v10, rid, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20", implied_at_lock=None)])
    with pytest.raises(ValidationError, match="needs a basis"):
        rounds.lock_predictions(v10, rid, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20",
                                                implied_at_lock={"method": "none"})])
    ids = rounds.lock_predictions(v10, rid, [
        pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20",
             implied_at_lock={"method": "option_implied", "value": 6.5, "source": "listed chain", "as_of": "2026-09-08T00:00:00Z",
                              "basis": "ATM straddle over the window"}),
        pred(a, target="OXY", sign="+", claim="the leg moves more than 3% on the event", position_id=P["oxy"], due_at="2026-09-20",
             implied_at_lock={"method": "realised_since_event", "value": 1.0, "source": "daily closes", "as_of": "2026-09-08T00:00:00Z",
                              "basis": "the move already made between the event and lock"}),
        pred(a, target="LESL", sign="0", claim="no attributable move", position_id=P["lesl"], due_at="2026-09-20",
             implied_at_lock={"method": "realised_since_event", "value": 0.4, "source": "daily closes", "as_of": "2026-09-08T00:00:00Z",
                              "basis": "nothing has moved"}),
    ])["prediction_ids"]
    p = rounds.list_predictions(v10, rid)
    assert p[0]["implied_method"] == "option_implied" and p[0]["implied_value"] == 6.5
    b = basket.event_basket(v10, rid)
    by = {l["holder"]: l for l in b["legs"]}
    assert by["Pool Corporation"]["executable"] == "fadeable_null"        # absence call, implied materially above zero
    assert by["Occidental Petroleum"]["executable"] == "exceeds_implied"  # 3% expected against 1% implied
    assert by["Leslie's"]["executable"] == "no"                           # silence already priced
    assert b["executability"]["fadeable_null"] == 1 and b["executability"]["exceeds_implied"] == 1
    assert edge.executability("sign", "+", 5.0, "option_implied", 3.0)["executable"] == "no"


# §I.7 / E: class divergence, with materiality reported separately --------------------------------------------------------

def test_i7_class_divergence(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    v10.execute("UPDATE carriers SET participant_class = 'contract' WHERE name = 'owner statements'")
    cls, carrier = edge.carrier_class(v10, "owner statements; force majeure letter")
    assert cls == "contract" and carrier == "owner statements"
    assert edge.default_price_setter(v10, H["pool"]) == "equity_generalist"
    r = edge.annotate_leg(v10, rid, P["pool"], "contract", "equity_generalist",
                          basis="the fact arrived in a force majeure letter; the instrument is a large diversified listing")
    assert r["class_divergence"] is True and r["class_distance"] == 3
    b = basket.event_basket(v10, rid)
    leg = next(l for l in b["legs"] if l["holder"] == "Pool Corporation")
    assert leg["class_divergence"] is True and leg["class_distance"] == 3 and b["class_divergent_legs"] == 1
    # a named channel closes the divergence even at distance
    r2 = edge.annotate_leg(v10, rid, P["oxy"], "physical_press", "equity_generalist", basis="trade press to a generalist book",
                           channel_between="sell_side_coverage")
    assert r2["class_divergence"] is False and r2["class_distance"] == 2
    assert edge.class_distance("contract", "contract") == 0 and edge.class_distance("physical_press", "equity_specialist") == 1
    with pytest.raises(ValidationError, match="must be one of"):
        edge.annotate_leg(v10, rid, P["lesl"], "not_a_class", "credit", basis="x")


# §I.8 / F: an institutional occurrence call cites its base rate -----------------------------------------------------------

def test_i8_base_rates(v10):
    a = make_rule(v10)
    edge.base_rate_seed(v10)          # idempotent: bootstrap already seeded it
    assert len(edge.base_rates(v10)) >= 5
    rid, H, P = two_node_round(v10, a)
    inst = dict(target="the regulator", sign="+", claim="the regulator orders a jurisdiction-wide inspection within 30 days",
                due_at="2026-09-20", position_id=None)
    with pytest.raises(ValidationError, match="institutional behaviour"):
        rounds.lock_predictions(v10, rid, [pred(a, **inst)])
    ids = rounds.lock_predictions(v10, rid, [pred(a, base_rate_id="br.fatal_accident_inspection_order", **inst)])["prediction_ids"]
    assert rounds.list_predictions(v10, rid)[0]["base_rate_id"]
    # or say why not
    rounds.lock_predictions(v10, rid, [pred(a, target="the court", sign="+", due_at="2026-09-20",
                                            claim="no-base-rate: the court's own listing practice has no published frequency")])
    assert edge.is_institutional("sign", "+", "the administrator", "files a report") is True
    assert edge.is_institutional("sign", "0", "the administrator", "files a report") is False
    br = edge.base_rates(v10, condition_like="statement of objections")
    assert br and all("phase ii" in b["condition"] for b in br)
    assert edge.resolve_base_rate(v10, "br.repeat_filing_self_administration")["rate"] == 0.05


# §I.9 / H: both stacks run and neither touches a rule weight ---------------------------------------------------------------

def test_i9_stacks(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, rid, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20")])
    rounds.open_retrieval(v10, rid)
    weights_before = {r["key"]: r["weight"] for r in library.query(v10, limit=100)}
    v11 = replay.replay_round(v10, rid, write=False, stack="v11")
    risk.practice_date_rules(v10)
    v12 = replay.replay_round(v10, rid, write=False, stack="v12")
    assert v11["stack"] == "v11" and v12["stack"] == "v12" and v11["cells"] == v12["cells"]
    assert v12["mirror_share"] <= v11["mirror_share"]     # practice dating covers more, so the mirror shrinks
    assert {r["key"]: r["weight"] for r in library.query(v10, limit=100)} == weights_before
