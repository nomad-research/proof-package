"""v10 brief: §A live rounds and due dates, §B size band and cap, §C enumeration, §D cross-node synthetic, §E forward
scheduled sources and concerns_node, §I price observations, §J grid, §K mirror. §G smoke tests 1-12."""
import json

import pytest

from harness import basket, enumeration, names, positions, predicates, risk, rounds, scheduled, scorer, synthetic
from harness.errors import StateError, ValidationError

from conftest import TEST_MODEL, TODAY, make_rule, pred, res

NODE_A, NODE_B = "us_trichlor_supply", "sauget_corridor"


@pytest.fixture
def v10(conn):
    """The freeze declared: v10 intake rules on."""
    risk.setting_set(conn, "freeze_started_at", "2026-09-08T00:00:00Z")
    risk.setting_set(conn, "clean_lag_days", "0")
    risk.setting_set(conn, "cap_lookback", "1")
    from harness.cli import bootstrap
    bootstrap(conn)
    for key, name in (("pred.arm.tradability_gate", "tradability gate (single-name and pair forms)"), ("pred.arm.catalyst_class", "catalyst class"),
                      ("pred.arm.existence_floor", "existence floor"), ("pred.arm.uncovered", "uncovered (no active risk rule covers the cell)"),
                      ("pred.disarm.now_covered", "now covered (a rule added since lock covers the cell)")):
        if not conn.execute("SELECT 1 FROM predicates WHERE key = ?", (key,)).fetchone():
            predicates.predicate_add(conn, name, "disarming" if key.startswith("pred.disarm") else "arming", "s", "t", key=key)
    return conn


def submit(conn, text="a fire at a plant", date="2026-09-07", size_band="underread", source="s", **kw):
    """v11: clean rounds need a verifiable selection, so the helper fixes a window and writes one rejection for it."""
    crit = {"Q1a": "pass: nothing on the channel in 30 days", "Q3": "pass: x", "Q4": "pass: x", "Q6": "pass: x", "Q8": "pass: x"}
    crit.update(kw.pop("criteria", {}))
    if "selection_start_date" not in kw:
        start = "2026-08-01"
        if not conn.execute("SELECT 1 FROM selection_windows WHERE source = ? AND start_date = ?", (source, start)).fetchone():
            rounds.selection_window_open(conn, source, start, "test fixture window")
            rounds.reject_event(conn, source, "2026-08-02", "a skipped candidate", "Q5", "trivia", start_date=start)
        kw["selection_start_date"] = start
    return rounds.submit_event(conn, text, date, source, "r", 0, crit, operator_model=TEST_MODEL, today=TODAY, registries=False,
                               size_band=size_band, **kw)


def two_node_round(conn, rule):
    """Round 9's shape: + listed on node A, - listed on node B, touched set with cited mechanisms."""
    r = submit(conn, node=NODE_A, node_kind="chemical")
    rid = r["round_id"]
    H = {}
    for key, name, opt in (("pool", "Pool Corporation", 1), ("oxy", "Occidental Petroleum", 1), ("emn", "Eastman Chemical", 1), ("neu", "NewMarket", 0), ("lesl", "Leslie's", 1)):
        H[key] = names.holder_upsert(conn, name, "company", listed=True, ticker=key.upper(), key=f"holder.{key}")["holder_id"]
        conn.execute("UPDATE holders SET options_listed = ? WHERE id = ?", (opt, H[key]))
    P = {}
    for key, node, sign in (("pool", NODE_A, "+"), ("oxy", NODE_A, "+"), ("lesl", NODE_A, "+"), ("emn", NODE_B, "-"), ("neu", NODE_B, "-")):
        P[key] = positions.position_add(conn, H[key], node, "sign_of_exposure", sign, "s", "inferred")["position_id"]
    rounds.touched_set_add(conn, rid, [{"holder_id": H[k], "degree": d, "node": n, "position_summary": "x", "substitutability": "high", "mechanism_ids": [rule]}
                                       for k, d, n in (("pool", 1, NODE_A), ("oxy", 2, NODE_A), ("lesl", 1, NODE_A), ("emn", 2, NODE_B), ("neu", 2, NODE_B))])
    return rid, H, P


# §G.1 / A1: an event dated yesterday is accepted ---------------------------------------------------------------------------

def test_g1_live_event_accepted_no_age_refusal(v10):
    r = submit(v10, date="2026-09-06")      # TODAY is 2026-09-07 in the fixture
    assert r["round_class"] == "clean" and r["tag"] == "lag_test" and r["clean_window"][1] == "2026-09-07"
    with pytest.raises(ValidationError, match="size_band is required"):
        rounds.submit_event(v10, "x", "2026-09-06", "s", "r", 0, {"Q1a": "pass: y"}, operator_model=TEST_MODEL, today=TODAY, registries=False)
    # v11 §C: the size band is a tag; trivia no longer refuses
    t = submit(v10, text="a small thing", size_band="trivia")
    assert t["size_band"] == "trivia" and rounds.round_tag(v10, t["round_id"])["size_band"] == "trivia"
    # Q3 and Q8 still refuse, and a price move is refused whether or not the human noticed
    with pytest.raises(ValidationError, match="refused .Q3."):
        submit(v10, text="Volkswagen shares fell 8% after the supplier filing", date="2026-09-06",
               criteria={"Q3": "unknown: not assessed"})      # an explicit 'pass: why' from the human still wins
    with pytest.raises(ValidationError, match="refused .Q8."):
        submit(v10, text="a fire at a plant", criteria={"Q8": "fail: the prompt carries the aftermath"})


# §G.2 / A2: due_at required, <= 90 days -------------------------------------------------------------------------------------

def test_g2_due_at_required_and_bounded(v10):
    a = make_rule(v10)
    rid = submit(v10)["round_id"]
    rounds.round_note(v10, rid, "lock", "no-touched-set: test")
    with pytest.raises(ValidationError, match="due_at is required"):
        rounds.lock_predictions(v10, rid, [pred(a)])
    with pytest.raises(ValidationError, match="more than 90 days"):
        rounds.lock_predictions(v10, rid, [pred(a, due_at="2026-12-07")])
    with pytest.raises(ValidationError, match="retired"):
        rounds.lock_predictions(v10, rid, [pred(None, call_type="meta", target="one-trade statement", claim="no-mechanism: the one trade is long x", carrier=None, falsifier=None, sign=None, due_at="2026-09-20")])
    r = rounds.lock_predictions(v10, rid, [pred(a, due_at="2026-09-20")])
    p = rounds.list_predictions(v10, rid)[0]
    # v13 A1: due_at, effect kind and window survive; the grid no longer generates anything at lock
    assert p["due_at"] == "2026-09-20" and p["effect_kind"] == "direction" and p["window"] == "to_due"
    assert r["grid"] is None and p["space"] is None


# §G.3 / A3-A4: narrative first, progressive scoring, calls due ------------------------------------------------------------------

def test_g3_narrative_first_and_partial_scoring(v10):
    a = make_rule(v10)
    rid = submit(v10)["round_id"]
    h = names.holder_upsert(v10, "Owner Plc", "company", listed=True)["holder_id"]
    pid = positions.position_add(v10, h, "node x", "sign_of_exposure", "-", "s", "stated")["position_id"]
    rounds.touched_set_add(v10, rid, [{"holder_id": h, "degree": 0, "node": "node x", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}])
    ids = rounds.lock_predictions(v10, rid, [
        pred(None, call_type="narrative", target="Owner leg", claim="the press says it weighs on the owner", carrier="trade press commentary",
             falsifier="no such framing", narrative_sign="-", position_id=pid, sign=None),                        # due_at defaults to event + 5
        pred(a, target="Owner Plc", sign="0", claim="no attributable move", position_id=pid, due_at="2026-09-20"),
        pred(a, target="other", claim="premia rise first", due_at="2026-10-30"),
    ])["prediction_ids"]
    preds = rounds.list_predictions(v10, rid)
    assert preds[0]["due_at"] == "2026-09-12"
    rounds.open_retrieval(v10, rid)
    # the structural call is not due yet
    with pytest.raises(ValidationError, match="not due until"):
        scorer.score_round(v10, rid, [res(ids[1], "hit", "right")], today="2026-09-15")
    # due, but the leg's narrative row is due and unscored: refused
    with pytest.raises(ValidationError, match="narrative first"):
        scorer.score_round(v10, rid, [res(ids[1], "hit", "right")], today="2026-09-21")
    card = scorer.score_call(v10, rid, res(ids[0], "miss", "unknown"), today="2026-09-21")
    assert card["state"] == "partially_scored" and len(card["remaining_calls"]) == 2
    assert rounds.round_state(v10, rid) == "partially_scored"
    card = scorer.score_call(v10, rid, res(ids[1], "hit", "right"), today="2026-09-21")
    assert card["state"] == "partially_scored" and [c["prediction_id"] for c in card["remaining_calls"]] == [ids[2]]
    due = scorer.calls_due(v10, before="2026-10-30")
    assert [d["prediction_id"] for d in due["due"]] == [ids[2]] and due["not_yet_due"] == 0
    assert scorer.calls_due(v10, before="2026-10-01")["not_yet_due"] == 1
    # early resolution needs the flag
    with pytest.raises(ValidationError, match="early=true"):
        scorer.score_call(v10, rid, res(ids[2], "hit", "right"), today="2026-10-01")
    # the second scorer sees only the final batch
    v = scorer.second_scorer_view(v10, rid)
    assert {p["id"] for p in v["predictions"]} == {ids[0], ids[1]}
    with pytest.raises(ValidationError, match="no final operator resolution"):
        scorer.second_score(v10, rid, [{"prediction_id": ids[2], "outcome": "hit", "mechanism_outcome": "right", "baseline_outcome": "miss"}])
    scorer.second_score(v10, rid, [{"prediction_id": ids[0], "outcome": "miss", "mechanism_outcome": "unknown", "baseline_outcome": "hit", "source_coverage": "thin"}])
    assert {p["id"] for p in scorer.second_scorer_view(v10, rid)["predictions"]} == {ids[1]}
    # expiry closes the round: the remaining absence-free call goes unverified
    card = scorer.close_round(v10, rid, today="2026-10-31")
    assert card["state"] == "scored" and card["expired"][0]["outcome"] == "unverified" and card["n_expired"] == 1
    assert rounds.round_state(v10, rid) == "scored"
    # an expired absence claim is a hit at thin coverage
    rid2 = submit(v10, text="another")["round_id"]
    rounds.round_note(v10, rid2, "lock", "no-touched-set: test")
    ids2 = rounds.lock_predictions(v10, rid2, [pred(a, call_type="null", target="none", sign=None, claim="no notice", falsifier_window="days:10", due_at="2026-09-17")])["prediction_ids"]
    rounds.open_retrieval(v10, rid2)
    card = scorer.close_round(v10, rid2, today="2026-09-18")
    r2 = rounds.latest_resolutions(v10, rid2)[ids2[0]]
    assert r2["outcome"] == "hit" and r2["source_coverage"] == "thin" and r2["expired"]


# §G.4 / C: enumeration --------------------------------------------------------------------------------------------------------

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Fire at a chemical plant in Sauget forces shelter-in-place | Local News</title><link>https://x/1</link><pubDate>Wed, 02 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
<item><title>Refinery explosion shuts crude unit at Baytown</title><link>https://x/2</link><pubDate>Thu, 03 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
<item><title>Port of Antwerp closes dock after bunker spill</title><link>https://x/3</link><pubDate>Fri, 04 Sep 2026 10:00:00 GMT</pubDate><description>x</description></item>
<item><title>Port of Antwerp closes dock after bunker spill</title><link>https://x/3b</link><pubDate>Fri, 04 Sep 2026 12:00:00 GMT</pubDate><description>dup</description></item>
<item><title>Refinery fire at Baytown last month</title><link>https://x/0</link><pubDate>Mon, 10 Aug 2026 10:00:00 GMT</pubDate><description>prior</description></item>
<item><title>Company reports strong quarter</title><link>https://x/4</link><pubDate>Fri, 04 Sep 2026 10:00:00 GMT</pubDate><description>not an incident</description></item>
</channel></rss>"""


def test_g4_enumerate_select_decide(v10):
    enumeration.feed_add(v10, "feed.test", "Test feed", "https://feed.test/rss", "rss", "rss", "test", "chemical", "trade_press", confirmed=True)
    fetch = lambda url, timeout=30: RSS
    r = enumeration.enumerate_window(v10, "test", "2026-09-01", "2026-09-05", fetch=fetch, operator_model=TEST_MODEL, today=TODAY)
    assert len(r["candidates"]) == 3 and r["written"] == 3
    c = {x["title"][:20]: x for x in r["candidates"]}
    bay = c["Refinery explosion s"]
    assert bay["prompt"] == "September 3, 2026: Refinery explosion shuts crude unit at Baytown." and bay["node_kind_guess"] == "refinery" and bay["q2"].startswith("pass") and bay["q7"].startswith("pass")
    assert bay["q1a_basis"].startswith("fail: 1 prior item")          # the August Baytown item shares two tokens
    assert c["Fire at a chemical p"]["q1a_basis"].startswith("pass") and c["Fire at a chemical p"]["prompt"].endswith("shelter-in-place.")
    assert "| Local News" not in c["Fire at a chemical p"]["prompt"] and c["Fire at a chemical p"]["size_hint"] == "underread"
    # select next, reject, next, accept
    n = enumeration.select_next(v10, "test", "2026-09-01", "2026-09-05")
    assert n["candidate"]["event_date"] == "2026-09-02" and n["remaining"] == 3
    with pytest.raises(ValidationError, match="failing question"):
        enumeration.decide(v10, n["candidate"]["id"], "reject", reason="meh")
    d = enumeration.decide(v10, n["candidate"]["id"], "reject", reason="Q1b: recurring node")
    assert d["failing_q"] == "Q1b" and v10.execute("SELECT COUNT(*) FROM event_rejections").fetchone()[0] == 1
    n = enumeration.select_next(v10, "test", "2026-09-01", "2026-09-05")
    assert n["candidate"]["event_date"] == "2026-09-03" and n["remaining"] == 2
    with pytest.raises(ValidationError, match="Q3 missing"):
        enumeration.decide(v10, n["candidate"]["id"], "accept", size_band="underread")
    d = enumeration.decide(v10, n["candidate"]["id"], "accept", size_band="headline", criteria={q: "pass: confirmed" for q in ("Q3", "Q4", "Q6", "Q8")},
                           operator_model=TEST_MODEL, today=TODAY)
    rd = d["round"]
    assert rd["q9"]["text"].startswith("pass") and not rd["criteria_pass"] and rd["tag"] == "late_headline"      # Q1a failed on the prior item
    t = rounds.round_tag(v10, rd["round_id"])
    assert t["size_band"] == "headline" and t["tags"] == ["late_headline", "headline"]
    assert v10.execute("SELECT candidate_id FROM events WHERE id = ?", (rd["event_id"],)).fetchone()[0]
    assert enumeration.select_next(v10, "test", "2026-09-01", "2026-09-05")["remaining"] == 1
    # v11 §C: Q9 is a gate on clean rounds; a hand-supplied event is refused, and the rejection is written
    with pytest.raises(ValidationError, match="refused .Q9."):
        rounds.submit_event(v10, "hand-supplied", "2026-09-07", "nowhere", "r", 0,
                            {"Q1a": "pass: y", "Q3": "pass: x", "Q8": "pass: x"}, operator_model=TEST_MODEL, today=TODAY,
                            registries=False, size_band="underread")
    assert v10.execute("SELECT COUNT(*) FROM event_rejections WHERE failing_q = 'Q9'").fetchone()[0] >= 1
    # the same event with a fixed window and its rejections on the ledger passes Q9 without the enumeration tooling
    rounds.selection_window_open(v10, "human sweep", "2026-09-01", "logged by hand")
    rounds.reject_event(v10, "human sweep", "2026-09-02", "another candidate", "Q5", "trivia", start_date="2026-09-01")
    h = submit(v10, text="hand-supplied event", source="human sweep", selection_start_date="2026-09-01", window_events_seen=2)
    assert h["q9"]["text"].startswith("pass") and h["criteria_pass"]


def test_b2_cap_two_consecutive_and_mix(v10):
    from harness import facts
    facts.node_fact_add(v10, "n_weather", "outage", "an outage", "ledger", source_time="2026-08-20")
    w = submit(v10, text="w1", node="n_weather")
    assert w["tag"] == "weather"
    w2 = submit(v10, text="w2", node="n_weather")           # v11 §C: the cap warns, never refuses
    assert w2["tag"] == "weather" and w2["cap"]["blocked"] is True
    assert any(n["kind"] == "cap" for n in rounds.list_notes(v10, w2["round_id"]))
    submit(v10, text="l1", node="n_l1")
    assert submit(v10, text="w3", node="n_weather")["tag"] == "weather"
    m = rounds.mix_status(v10)
    assert m["freeze"] and m["admitted_under_freeze"] == 4 and m["still_needed"]["headline"] == 4
    assert m["warning"]      # the remaining rounds cannot deliver the mix
    r = submit(v10, text="l2", node="n_l2", size_band="headline")
    assert any("mix warning" in n["note"] for n in rounds.list_notes(v10, r["round_id"]))


# §G.5 / D: cross-node synthetic ---------------------------------------------------------------------------------------------

def test_g5_cross_node_synthetic(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    r = synthetic.synthetic_build(v10, rid, NODE_A, "syn.cross_node_event_pair", dry_run=True)
    assert r["dry_run"] and not r["built"] and r["cross_node"] and r["n_components"] == 5
    assert {c["holder"] for c in r["components"]} == {"Pool Corporation", "Occidental Petroleum", "Leslie's", "Eastman Chemical", "NewMarket"}
    assert r["support_weight"] == pytest.approx(r["weakest_component"] * 0.85 ** 4 * 0.85) and r["support_weight"] <= r["weakest_component"] * 0.85 ** 3
    r2 = synthetic.synthetic_build(v10, rid, NODE_A, "syn.cross_node_event_pair")
    assert r2["built"] and v10.execute("SELECT cross_node FROM synthetic_legs WHERE id = ?", (r2["synthetic_id"],)).fetchone()[0] == 1
    # same-node rule still refuses on one-sided nodes with the explicit message
    r3 = synthetic.synthetic_build(v10, rid, NODE_A, "syn.tradability_opposing")
    assert not r3["built"] and "no opposing listed pair" in r3["reason"]
    # one node only: refused
    rid1 = submit(v10, text="one node", node="n1")["round_id"]
    h = names.holder_upsert(v10, "Solo Plc", "company", listed=True)["holder_id"]
    positions.position_add(v10, h, "n1", "sign_of_exposure", "+", "s", "stated")
    rounds.touched_set_add(v10, rid1, [{"holder_id": h, "degree": 1, "node": "n1", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}])
    r4 = synthetic.synthetic_build(v10, rid1, "n1", "syn.cross_node_event_pair")
    assert not r4["built"] and ">= 2 nodes" in r4["reason"]
    b = basket.event_basket(v10, rid)
    assert b["synthetics"][0]["cross_node"] is True


# §G.6 / E: concerns_node and tide candidates -----------------------------------------------------------------------------------

def test_g6_tide_candidate_when_fact_does_not_concern_node(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    f = scheduled.scheduled_add(v10, H["lesl"], "results", "2026-09-12", "results-date announcement", "2026-09-01", sched_source="announcement")
    c = scheduled.catalyst_check(v10, rid)
    lesl = next(l for l in c["legs"] if l["leg"] == "Leslie's")
    assert not lesl["holds_claimable"] and len(lesl["undecided"]) == 1
    scheduled.link_fact(v10, rid, P["lesl"], f["fact_id"], False, "trichlor is a rounding error in the retailer's sales; the results do not concern the node")
    c = scheduled.catalyst_check(v10, rid, write=True)
    lesl = next(l for l in c["legs"] if l["leg"] == "Leslie's")
    assert not lesl["holds_observed"] and lesl["tide_candidate_count"] == 1 and "tide candidate" in lesl["claimable_basis"]
    chk = [x for x in predicates.round_checks(v10, rid) if x["position_id"] == P["lesl"]][-1]
    assert chk["claimed"] == "fails" and "tide candidates" in chk["note"]
    # the same fact on the POOL leg (degree-1 holder on the node) is surfaced there too: the wide read
    pool = next(l for l in c["legs"] if l["leg"] == "Pool Corporation")
    assert any(x["canonical_name"] == "Leslie's" for x in pool["facts"])
    # hindsight EDGAR rows never date
    scheduled.scheduled_add(v10, H["pool"], "results", "2026-09-20", "EDGAR 8-K item 2.02", "2026-09-20", hindsight=True, sched_source="edgar_202")
    c = scheduled.catalyst_check(v10, rid)
    pool = next(l for l in c["legs"] if l["leg"] == "Pool Corporation")
    assert not pool["holds_observed"]
    # announcement parser
    items = scheduled.parse_announcement("Leslie's, Inc. today announced that it will report third quarter 2026 financial results after market close on Wednesday, August 12, 2026.", "2026-08-05")
    assert items and items[0]["date"] == "2026-08-12" and items[0]["knowable_from"] == "2026-08-05"


# §G.8 / I1: price observations ---------------------------------------------------------------------------------------------------

def test_g8_price_observation_guards(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    closes = [100 + (i % 3) for i in range(22)]
    with pytest.raises(StateError, match="post-lock"):
        risk.price_observe(v10, rid, P["pool"], "close", "2026-09-08", 101.0, False, closes=closes)
    ids = rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20")])["prediction_ids"]
    rounds.open_retrieval(v10, rid)
    with pytest.raises(StateError, match="not due yet"):
        risk.price_observe(v10, rid, P["pool"], "close", "2026-09-08", 101.0, False, closes=closes, today="2026-09-10")
    r = risk.price_observe(v10, rid, P["pool"], "close", "2026-09-15", 130.0, False, closes=closes, today="2026-09-21")
    # v13 B1: the band is the empirical trailing distribution now, so a 30% jump is outside it and the reference close
    # sits inside it; the parametric form stays available behind config.BAND_METHOD for reproducing an old row
    assert r["out_of_band"] and r["band"][0] <= closes[-1] <= r["band"][1]
    with pytest.raises(ValidationError, match="attribution_evidence_id"):
        risk.price_observe(v10, rid, P["pool"], "close", "2026-09-16", 130.0, True, closes=closes, today="2026-09-22")
    e = rounds.add_evidence(v10, rid, "https://x", "press cites the event", "e", source_time="2026-09-16")["evidence_id"]
    r = risk.price_observe(v10, rid, P["pool"], "close", "2026-09-16", 130.0, True, attribution_evidence_id=e, closes=closes, today="2026-09-22")
    assert r["attributed"]
    obs = v10.execute("SELECT band_method FROM price_observations ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "empirical band" in obs          # v13 B1
    # I2/I3: the leg re-encodes on the attributed out-of-band observation; unattributed one did not count
    b = basket.event_basket(v10, rid)
    pool = next(l for l in b["legs"] if l["holder"] == "Pool Corporation")
    assert pool["reencode"]["reencode_date"] == "2026-09-16" and pool["residual_state"] == "recovered"
    oxy = next(l for l in b["legs"] if l["holder"] == "Occidental Petroleum")
    assert oxy["residual_state"] == "unrecovered" and oxy["forcing_date"] <= "2026-12-06"
    # scoring=true lets the scorer write while resolving
    assert risk.price_observe(v10, rid, P["oxy"], "close", "2026-09-10", 50.0, False, closes=closes, today="2026-09-10", scoring=True)["observation_id"]


# §G.9 / K1: grid at lock, frozen ----------------------------------------------------------------------------------------------------

def test_g9_grid_retired_as_a_generator(v10):
    """v13 A1: cell enumeration no longer produces legs (smoke test 5). The rule engine that classified the cells is
    kept — the eliminators run on the same rules — so its coverage logic is still checked here, read-only."""
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    r = rounds.lock_predictions(v10, rid, [
        pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20", falsifier_window="days:5"),
        pred(a, target="EMN", sign="0", claim="no attributable move", position_id=P["emn"], due_at="2026-09-20", effect_kind="vol", window="event_day"),
    ])
    assert risk.grid_cells(v10, rid) == [] and r["grid"] is None and r["stamped_cells"] == 0
    assert all(p["space"] is None and p["grid_cell_id"] is None for p in rounds.list_predictions(v10, rid))
    cells = risk.dry_run_grid(v10, rid, as_of="2026-09-07")["cells"]
    assert len(cells) == 5 * 4 * 4
    # equity legs: direction covered by the tide rule on every window; timing at degree 0/1 to_due covered by catalyst-about-node
    pool_cells = [c for c in cells if c["holder_id"] == H["pool"]]      # from the read-only dry run
    assert all(c["space"] == "positive" for c in pool_cells if c["effect_kind"] == "direction")
    assert all(c["space"] == "mirror" for c in pool_cells if c["effect_kind"] == "vol")
    assert next(c for c in pool_cells if c["effect_kind"] == "volume" and c["window"] == "event_day")["space"] == "mirror"
    assert next(c for c in pool_cells if c["effect_kind"] == "volume" and c["window"] == "weeks")["space"] == "positive"     # risk.weather
    # v11 A2: coverage is assigned as of the event date, so a rule knowable only from 8 September does not cover a
    # 7 September event: the catalyst-about-node rule leaves the timing cells in the mirror
    assert next(c for c in pool_cells if c["effect_kind"] == "timing" and c["window"] == "to_due")["space"] == "mirror"
    covered = sum(1 for c in cells if c["space"] == "positive")
    assert sum(1 for c in cells if c["space"] == "mirror") == len(cells) - covered
    b = basket.event_basket(v10, rid, space="both")
    assert b["cell_counts"] == {"positive": 0, "mirror": 0}


# §G.10 / K3: coverage migrations ------------------------------------------------------------------------------------------------------

def test_g10_risk_rule_add_writes_migration(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20")])
    with pytest.raises(StateError, match="between rounds"):
        risk.risk_rule_add(v10, "risk.test_vol", "vol on equities is covered", "veto", {"effect_kinds": ["vol"], "factor_kinds": ["equity"]}, "2026-09-08")
    rounds.open_retrieval(v10, rid)
    risk.assign_grid(v10, rid, as_of="2026-09-07")     # v13 A1: assignment is explicit now, never a side effect of lock
    before = [c for c in risk.grid_cells(v10, rid, "mirror") if c["effect_kind"] == "vol"]
    r = risk.risk_rule_add(v10, "risk.test_vol", "vol on equities is covered", "veto", {"effect_kinds": ["vol"], "factor_kinds": ["equity"]}, "2026-09-08")
    assert len(r["migrations"]) == len(before) == 20
    assert all(c["space"] == "mirror" for c in risk.grid_cells(v10, rid, "mirror") if c["effect_kind"] == "vol")       # locked row unchanged
    m = risk.migrations_for(v10, rid)
    assert len(m) == 20 and m[0]["rule_key"] == "risk.test_vol"
    b = basket.event_basket(v10, rid, space="mirror")
    vol = [c for c in b["cells"] if c["effect_kind"] == "vol"]
    assert all(c["now_covered_by"] == "risk.test_vol" and c["arming_status"] == "gate_fail" for c in vol)     # pred.disarm.now_covered
    with pytest.raises(ValidationError, match="frozen"):
        risk.risk_rule_add(v10, "risk.bad", "x", "veto", {"effect_kinds": ["liquidity"]}, "2026-09-08")


# §G.11 / K6: the worked check --------------------------------------------------------------------------------------------------------

def test_g11_mirror_dry_run_lesl_vol_event_day(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    gate = v10.execute("SELECT id FROM predicates WHERE key = 'pred.arm.tradability_gate'").fetchone()[0]
    rounds.lock_predictions(v10, rid, [pred(a, target="LESL", sign="0", claim="no attributable move", position_id=P["lesl"], due_at="2026-09-20")])
    predicates.predicate_check(v10, rid, [{"predicate_id": gate, "claimed": "fails", "observed": "fails", "basis": "below visibility", "position_id": P["lesl"]}])
    scheduled.scheduled_add(v10, H["lesl"], "results_announced", "2026-09-12", "results-date announcement", "2026-09-01", fact_type="mechanical", sched_source="announcement")
    d = risk.mirror_dry_run(v10, rid, holder="Leslie")
    cell = next(c for c in d["cells"] if c["effect_kind"] == "vol" and c["window"] == "event_day")
    assert cell["space"] == "mirror" and cell["arming_status"] == "armed_dated" and cell["dated_by"][0][0] == "mechanical"
    direction = next(c for c in d["cells"] if c["effect_kind"] == "direction" and c["window"] == "event_day")
    assert direction["space"] == "positive" and direction["covering_rule"] == "risk.tide_visibility" and direction["arming_status"] == "gate_fail"
    # NewMarket has no listed options: its vol cells fail the gate
    d2 = risk.mirror_dry_run(v10, rid, holder="NewMarket")
    assert all(c["arming_status"] == "gate_fail" for c in d2["cells"] if c["effect_kind"] == "vol")


# §G.12 / I4: exposure ---------------------------------------------------------------------------------------------------------------

def test_g12_exposure_over_unrecovered(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-20")])
    rounds.open_retrieval(v10, rid)
    x = risk.exposure(v10)
    assert rid in x["rounds"]
    by = {f["node"]: f for f in x["factors"]}
    assert by[NODE_A]["sum_sign_x_support"] == pytest.approx(3 * 0.0) and len(by[NODE_A]["legs"]) == 3 and by[NODE_B]["earliest_forcing_date"]
    e = rounds.add_evidence(v10, rid, "https://x", "cites", "e", source_time="2026-09-15")["evidence_id"]
    risk.price_observe(v10, rid, P["pool"], "close", "2026-09-15", 200.0, True, attribution_evidence_id=e, closes=[100.0 + i % 2 for i in range(22)], today="2026-09-21")
    by = {f["node"]: f for f in risk.exposure(v10, rid)["factors"]}
    assert len(by[NODE_A]["legs"]) == 2        # the recovered leg has left the exposure


# notebook rows carry I3 and K5 ---------------------------------------------------------------------------------------------------------

def test_notebook_rows_k5(v10):
    a = make_rule(v10)
    rid, H, P = two_node_round(v10, a)
    ids = rounds.lock_predictions(v10, rid, [pred(a, target="POOL", sign="0", claim="no attributable move", position_id=P["pool"], due_at="2026-09-10")])["prediction_ids"]
    risk.assign_grid(v10, rid, as_of="2026-09-07")     # v13 A1: the K5 denominator is history, not a lock product
    rounds.open_retrieval(v10, rid)
    scorer.score_call(v10, rid, res(ids[0], "hit", "right"), today="2026-09-11")
    nb = scorer.latest_notebook_rows(v10, rid)
    assert nb["K5"]["positive"]["cells"] + nb["K5"]["mirror"]["cells"] == 80 and nb["I3"]["counts"]["unrecovered"] == 5
    ps = scorer.programme_stats(v10)
    assert rid in ps["k5_by_round"] and ps["mix"]["freeze"]
