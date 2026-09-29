"""v11 brief: §A one round type, §B replay, §C gates become tags, §D stratified enumeration, §E batch scoring.
§G smoke tests 1-7."""
import pytest

from harness import basket, enumeration, library, names, positions, predicates, replay, risk, rounds, scorer
from harness.errors import StateError, ValidationError

from conftest import TEST_MODEL, TODAY, make_rule, pred, res
from test_v10 import NODE_A, NODE_B, submit, two_node_round, v10      # noqa: F401  (the v10 fixture is v11's baseline)


# §G.1 / A1+A4: a historical event is an ordinary learning round; its calls never touch the library ---------------------

def test_g1_historical_event_is_a_learning_round(v10):
    a = make_rule(v10)
    r = submit(v10, text="a fire at a plant in 2023", date="2023-05-11", round_class="learning")
    rid = r["round_id"]
    assert r["round_class"] == "learning" and r["contamination"] == "q2_fail" and r["tag"] == "learning"
    h = names.holder_upsert(v10, "Old Co", "company", listed=True)["holder_id"]
    pid = positions.position_add(v10, h, "node 2023", "sign_of_exposure", "-", "s", "stated")["position_id"]
    # A3: on a learning round the legs are generated from the positions store, not selected
    g = rounds.generate_legs(v10, rid, nodes=["node 2023"], mechanism_ids=[a])
    assert g["generated"] == 1 and g["leg_source"] == "mechanical"
    assert [t["leg_source"] for t in rounds.list_touched_set(v10, rid)] == ["mechanical"]
    ids = rounds.lock_predictions(v10, rid, [pred(a, target="Old Co", position_id=pid, due_at="2023-06-01")])["prediction_ids"]
    rounds.open_retrieval(v10, rid)
    before = library.get_rule(v10, a)
    scorer.score_call(v10, rid, res(ids[0], "hit", "right"), today="2023-06-02")
    after = library.get_rule(v10, a)
    assert (after["weight"], after["trials"]) == (before["weight"], before["trials"]) == (0.0, 0)
    assert rounds.latest_resolutions(v10, rid)[ids[0]]["outcome"] == "hit"        # recorded and scored, just not counted
    assert scorer.calibration(v10)["excluded_learning"] >= 1
    # its measurements do count
    rep = replay.replay_round(v10, rid)
    assert rep["cells"] == 16 and rep["replay"] is True
    # a clean round refuses mechanical generation
    with pytest.raises(ValidationError, match="clean round's legs"):
        rounds.generate_legs(v10, submit(v10, text="clean one")["round_id"], nodes=["node 2023"])


# §G.2 / B1: replay writes measurements and never a resolution -----------------------------------------------------------

def test_g2_replay_writes_measurements_only(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    ids = rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20")])["prediction_ids"]
    rounds.open_retrieval(v10, rid)
    dry = replay.replay_round(v10, rid, write=False)
    assert dry["written"] == 0 and dry["legs_measured"] == 0 and len(dry["legs_unmeasured"]) == 5   # no dated observation yet
    # an attributed, out-of-band observation makes the leg measurable and gives it a re-encode
    e = rounds.add_evidence(v10, rid, "https://x", "press cites the event", "e", source_time="2026-09-09")["evidence_id"]
    risk.price_observe(v10, rid, P["pool"], "close", "2026-09-09", 200.0, True, attribution_evidence_id=e,
                       closes=[100.0 + i % 2 for i in range(22)], today="2026-09-21", scoring=True)
    scorer.score_call(v10, rid, res(ids[0], "hit", "right"), today="2026-09-21")
    res_before = [dict(r) for r in v10.execute("SELECT * FROM resolutions")]
    r = replay.replay_round(v10, rid)
    assert r["cells"] == 5 * 16 and r["written"] == r["cells"] and r["legs_measured"] == 1
    rows = [dict(x) for x in v10.execute("SELECT * FROM replay_measurements WHERE round_id = ?", (rid,))]
    assert all(x["replay"] == 1 for x in rows) and [dict(x) for x in v10.execute("SELECT * FROM resolutions")] == res_before
    pool_cells = [dict(c) for c in v10.execute("SELECT * FROM replay_measurements WHERE round_id = ? AND holder_id = ?", (rid, H["pool"]))]
    assert len(pool_cells) == 16 and all(c["reencode_date"] == "2026-09-09" and c["residual_state"] == "recovered" for c in pool_cells)
    assert replay.latency_distribution(v10)["overall"]["median_days"] == 2      # event 7 Sep, re-encode 9 Sep
    # v12: a round may be re-measured under a corrected stack; the readers take the last pass, the earlier one stays
    again = replay.replay_round(v10, rid)
    assert again["prior_measurements"] == r["cells"] and len(replay.latest_measurements(v10)) == r["cells"]


# §G.3 / B3: point-in-time coverage makes the decay curve ------------------------------------------------------------------

def test_g3_coverage_decay_curve(v10):
    a = make_rule(v10)
    # an early event: only the rules knowable then cover anything
    early = submit(v10, text="an early event", date="2026-04-05")["round_id"]
    h = names.holder_upsert(v10, "Early Plc", "company", listed=True)["holder_id"]
    positions.position_add(v10, h, "early node", "sign_of_exposure", "-", "s", "stated")
    rounds.touched_set_add(v10, early, [{"holder_id": h, "degree": 1, "node": "early node", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}])
    rounds.lock_predictions(v10, early, [pred(a, due_at="2026-04-20")])
    rounds.open_retrieval(v10, early)
    late, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, late, [pred(a, target="POOL", position_id=P["pool"], due_at="2026-09-20")])
    rounds.open_retrieval(v10, late)
    e = replay.replay_round(v10, early)
    l = replay.replay_round(v10, late)
    assert e["mirror_share"] > l["mirror_share"]        # coverage decay: the early round is mostly uncovered
    curve = replay.coverage_decay(v10)
    assert [c["round_id"] for c in curve][:1] == [early] and all("mirror_share" in c for c in curve)
    k5 = replay.k5_rates(v10)
    assert k5["mirror"]["cells"] == 0 and "claim" in k5      # no observations: K5 has no denominator on these rounds
    assert replay.latency_distribution(v10)["legs_with_reencode"] == 0


# §G.4 / C: an old-Q1b failure is admitted with a tag ------------------------------------------------------------------------

def test_g4_first_traversal_is_a_tag_not_a_gate(v10):
    from harness import facts
    facts.node_fact_add(v10, "recurring node", "outage", "an outage last month", "ledger", source_time="2026-08-20")
    r = submit(v10, text="another outage at the same node", node="recurring node")
    assert r["tag"] == "weather" and r["q1b"]["value"] == "fail" and r["round_class"] == "clean"
    assert not [x for x in v10.execute("SELECT * FROM event_rejections WHERE event_text = 'another outage at the same node'")]
    # a round with no listed party and no carriers is still admitted: it is a legitimate null generator
    r2 = submit(v10, text="something in a sector with no carriers", node_kind="other")
    assert r2["round_id"] and not r2["carrier_density"]["qualifies"]


# §G.5 / C: a price move is refused ---------------------------------------------------------------------------------------------

def test_g5_price_event_refused(v10):
    for text in ("the DAX index dropped 3% on the announcement",
                 "copper prices surged to a record high",
                 "Volkswagen shares fell 8 percent"):
        with pytest.raises(ValidationError, match="refused .Q3."):
            submit(v10, text=text, criteria={"Q3": "unknown: not assessed"})
    assert v10.execute("SELECT COUNT(*) FROM event_rejections WHERE failing_q = 'Q3'").fetchone()[0] == 3
    assert rounds.looks_like_price_event("shares rose 4% after the ruling")
    assert not rounds.looks_like_price_event("a fire at a chemical plant in Sauget, Illinois")
    # the human can still admit a genuine world event that reads like one, with an explicit pass and a why
    r = submit(v10, text="the exchange suspended trading in the shares", criteria={"Q3": "pass: a suspension is an act, not a price move"})
    assert r["round_id"]


# §G.6 / D: the selector draws by stratum, not by date alone -------------------------------------------------------------------

RSS_A = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Fire at a chemical plant in Ludwigshafen</title><link>https://a/1</link><pubDate>Tue, 01 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
</channel></rss>"""
RSS_B = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Regulator bans a fishing method in the North Sea</title><link>https://b/1</link><pubDate>Wed, 02 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
</channel></rss>"""
RSS_C = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Supplier files for insolvency in Delbrueck</title><link>https://c/1</link><pubDate>Thu, 03 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
</channel></rss>"""


def test_g6_stratified_selection(v10):
    for key, stratum, body in (("feed.a", "chemical", RSS_A), ("feed.b", "regulatory", RSS_B), ("feed.c", "corporate_distress", RSS_C)):
        enumeration.feed_add(v10, key, key, f"https://{key}/rss", "rss", "rss", "strat", None, "trade_press", confirmed=True, stratum=stratum)
    bodies = {"https://feed.a/rss": RSS_A, "https://feed.b/rss": RSS_B, "https://feed.c/rss": RSS_C}
    r = enumeration.enumerate_window(v10, "strat", "2026-09-01", "2026-09-05", fetch=lambda url, timeout=30: bodies[url],
                                     operator_model=TEST_MODEL, today=TODAY)
    assert len(r["candidates"]) == 3
    with pytest.raises(ValidationError, match="stratum must be one of"):
        enumeration.feed_add(v10, "feed.z", "z", "https://z", "rss", "rss", "strat", stratum="not_a_stratum")
    # date order would take the chemical item first; the quota shortfall decides instead
    plain = enumeration.select_next(v10, "strat", "2026-09-01", "2026-09-05", stratified=False)
    assert plain["candidate"]["event_date"] == "2026-09-01"
    n = enumeration.select_next(v10, "strat", "2026-09-01", "2026-09-05")
    assert n["candidate"]["stratum"] == n["strata"]["order"][0]
    assert set(n["pending_by_stratum"]) == {"chemical", "regulatory", "corporate_distress"}
    # a skip is a plain selection note: no manufactured failing question, no rejection row
    before = v10.execute("SELECT COUNT(*) FROM event_rejections").fetchone()[0]
    d = enumeration.decide(v10, n["candidate"]["id"], "skip", reason="the human had already fixed this window's event")
    assert d["decision"] == "skip" and v10.execute("SELECT COUNT(*) FROM event_rejections").fetchone()[0] == before
    # a skip may supersede an earlier reject: the ratification path for a manufactured failing question
    nxt = enumeration.select_next(v10, "strat", "2026-09-01", "2026-09-05")["candidate"]
    enumeration.decide(v10, nxt["id"], "reject", reason="Q5: trivia")
    r2 = enumeration.decide(v10, nxt["id"], "skip", reason="ratified: never assessed, the window's event was already fixed")
    assert r2["decision"] == "skip"
    assert enumeration.select_next(v10, "strat", "2026-09-01", "2026-09-05")["candidate"]["id"] != n["candidate"]["id"]
    sc = enumeration.stratum_counts(v10)
    assert sc["quota"] and set(sc["counts"]) >= set(sc["quota"]) and sc["order"][0] in sc["quota"]


# §G.7 / E: one batch across rounds ------------------------------------------------------------------------------------------------

def test_g7_batch_scoring_across_rounds(v10):
    a = make_rule(v10)
    rids, ids = [], []
    for i in range(3):
        rid = submit(v10, text=f"event {i}")["round_id"]
        rounds.round_note(v10, rid, "lock", "no-touched-set: test")
        pid = rounds.lock_predictions(v10, rid, [pred(a, target=f"t{i}", due_at="2026-09-20")])["prediction_ids"][0]
        rounds.open_retrieval(v10, rid)
        rids.append(rid); ids.append(pid)
    due = scorer.calls_due(v10, before="2026-09-21")
    assert len(due["due"]) == 3 and len(due["rounds"]) == 3
    batch = scorer.score_batch(v10, [res(i, "hit", "right") for i in ids], today="2026-09-21")
    assert batch["scored"] == 3 and len(batch["rounds"]) == 3 and batch["still_due"] == []
    assert all(v["state"] == "scored" for v in batch["rounds"].values())
    view = scorer.second_scorer_batch(v10)
    assert view["n_predictions"] == 3 and len(view["rounds"]) == 3
    scorer.second_score(v10, rids[0], [{"prediction_id": ids[0], "outcome": "miss", "mechanism_outcome": "wrong",
                                        "baseline_outcome": "miss", "source_coverage": "adequate"}])
    d = scorer.disputes_batch(v10)
    assert d["disputes"] == 1 and d["rows"][0]["round_id"] == rids[0] and d["rows"][0]["prediction_id"] == ids[0]
    assert scorer.second_scorer_batch(v10)["n_predictions"] == 2
    cal = scorer.calibration(v10)
    assert cal["overall"]["n"] >= 3 and cal["by_call_type"]["sign"]["rate"] is not None
