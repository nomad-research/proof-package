"""Post-round-5 review: A13 misreads, map call type, basis on claims, atomic evidence batches, round notes,
the B2 second scorer, and the B4 node-facts ledger and ingest."""
import pytest

from harness import facts, hypotheses, library, predicates, rounds, scorer
from harness.db import GENESIS_HASH, connect, verify_chain
from harness.errors import ValidationError

from conftest import TEST_MODEL, TODAY, dated_evidence, make_round, make_rule, play_round, pred, res


# A13 ---------------------------------------------------------------------------------------

def test_misread_does_not_debit_the_rule(conn):
    a = make_rule(conn)
    rid, ids, card = play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "right", scorer_note="conditional wrong, rule operated")])
    r = library.get_rule(conn, a)
    assert (r["misses"], r["weight"], r["trials"], r["status"]) == (0, 0.0, 1, "candidate")
    assert card["misreads"] == 1 and card["misread_frac"] == 1.0 and card["outcome_score"] == 0.0
    # a real miss (mechanism wrong) still debits
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "wrong")], text="real miss")
    r = library.get_rule(conn, a)
    assert r["misses"] == 1 and r["weight"] == pytest.approx(-0.7)
    assert scorer.programme_stats(conn)["misreads_total"] == 1


def test_misread_leaves_composition_unflagged_and_hypothesis_armable(conn):
    a, b = make_rule(conn, "part a"), make_rule(conn, "part b")
    c = make_rule(conn, "a with b", composed_of=[a, b])
    for i in range(2):
        rid = make_round(conn, text=f"h{i}")
        ids = rounds.lock_predictions(conn, rid, [pred(a)])["prediction_ids"]
        rounds.open_retrieval(conn, rid)
        scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[dated_evidence(conn, rid)])])
    play_round(conn, [pred(a)], lambda ids: [res(ids[0], "miss", "right")], text="misread")
    assert library.get_rule(conn, a)["weight"] == pytest.approx(1.2) and library.get_rule(conn, c)["review_flag"] == 0
    arm = predicates.predicate_add(conn, "arm", "arming", "s", "t")["predicate_id"]
    h = hypotheses.hypothesis_open(conn, "h", [], [a], [arm], [], "f", "g")["hypothesis_id"]
    assert hypotheses.hypothesis_check(conn, h, [{"predicate_id": arm, "observed": "holds"}])["status"] == "armed"


# map call type -----------------------------------------------------------------------------

def test_map_calls_score_outcome_only(conn):
    a = make_rule(conn)
    with pytest.raises(ValidationError, match="carries"):
        rounds.lock_predictions(conn, make_round(conn, text="m0"), [pred(a, call_type="map", target="map: site", falsifier=None)])
    rid, ids, card = play_round(conn, [pred(None, call_type="map", target="map: site", falsifier=None),
                                       pred(None, call_type="map", target="map: owner", falsifier=None),
                                       pred(a)],
                                lambda ids: [res(ids[0]), res(ids[1], "miss", "unknown"), res(ids[2])], text="m1")
    assert card["n_map_calls"] == 2 and card["map_score"] == 0.5
    assert card["outcome_score"] == pytest.approx(2 / 3) and card["mechanism_score"] == 1.0
    assert card["sum_weight_mechanism"] == 1.0 and library.get_rule(conn, a)["trials"] == 1


# basis -------------------------------------------------------------------------------------

def test_claims_need_a_basis(conn):
    p = predicates.predicate_add(conn, "slack", "arming", "s", "t")["predicate_id"]
    rid = make_round(conn)
    with pytest.raises(ValidationError, match="basis is required"):
        predicates.predicate_check(conn, rid, [{"predicate_id": p, "claimed": "fails"}])
    predicates.predicate_check(conn, rid, [{"predicate_id": p, "claimed": "unknown"},
                                           {"predicate_id": p, "claimed": "fails", "basis": "loadings halted since 13 July per Argus"}])
    rows = predicates.round_checks(conn, rid)
    assert rows[0]["basis"] is None and rows[1]["basis"].startswith("loadings")


# atomic evidence ---------------------------------------------------------------------------

def test_evidence_batch_is_atomic(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    rounds.lock_predictions(conn, rid, [pred(a)])
    rounds.open_retrieval(conn, rid)
    with pytest.raises(ValidationError, match="nothing written"):
        rounds.add_evidence_batch(conn, rid, [{"url": "https://a", "title": "a", "excerpt": "ok"},
                                             {"url": "https://b", "title": "b", "excerpt": "x" * 501}])
    assert conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
    r = rounds.add_evidence_batch(conn, rid, [{"url": "https://a", "title": "a", "excerpt": "ok"},
                                             {"url": "https://b", "title": "b", "excerpt": "ok", "source_time": "2026-07-20"}])
    assert r["count"] == 2 and conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2


def test_round_note_recorded_and_exported(conn):
    rid = make_round(conn)
    rounds.round_note(conn, rid, "tide", "Hormuz reinstated the day before; fuel legs sat on a war-priced backdrop")
    exp = rounds.export_round(conn, rid)
    assert [n["kind"] for n in exp["notes"] if n["kind"] == "tide"] == ["tide"] and verify_chain(conn, "round_notes")["ok"]


# B2 ----------------------------------------------------------------------------------------

def test_second_scorer_view_and_disputes(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    ids = rounds.lock_predictions(conn, rid, [pred(a), pred(a, target="b")])["prediction_ids"]
    with pytest.raises(Exception):
        scorer.second_scorer_view(conn, rid)          # not scored yet
    rounds.open_retrieval(conn, rid)
    e = dated_evidence(conn, rid)
    scorer.score_round(conn, rid, [res(ids[0], evidence_ids=[e], scorer_note="operator reasoning"), res(ids[1], "miss", "wrong")])
    view = scorer.second_scorer_view(conn, rid)
    assert "resolutions" not in view and "operator reasoning" not in str(view) and len(view["evidence"]) == 1
    from harness import names, positions
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True, ticker="ALP")["holder_id"]
    positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "filing", "stated")
    view = scorer.second_scorer_view(conn, rid)
    assert list(view["positions"]) == ["node x"] and view["positions"]["node x"]["holders"][0]["signs"] == ["-"]
    assert "positions" not in view["positions"]["node x"]["holders"][0]     # row detail stripped, signs and pairs kept
    d = scorer.second_score(conn, rid, [
        {"prediction_id": ids[0], "outcome": "hit", "mechanism_outcome": "right", "baseline_outcome": "miss", "evidence_ids": [e]},
        {"prediction_id": ids[1], "outcome": "unverified", "mechanism_outcome": "unknown", "baseline_outcome": "unverified", "source_coverage": "thin"},
    ], scorer_session="session-b")
    assert d["disputes"] == 1 and [r["status"] for r in d["rows"]] == ["agree", "dispute"]
    # operator's rows untouched; human breaks the tie
    assert rounds.latest_resolutions(conn, rid)[ids[1]]["outcome"] == "miss"
    old = rounds.latest_resolutions(conn, rid)[ids[1]]["id"]
    scorer.supersede_resolution(conn, rid, res(ids[1], "unverified", "unknown", "unverified", source_coverage="thin",
                                               scorer="human", supersedes=old, scorer_note="tie broken: coverage was thin"))
    d2 = scorer.score_disputes(conn, rid)
    assert d2["disputes"] == 0 and d2["rows"][1]["resolved_by_human"] is True
    assert verify_chain(conn, "second_scores")["ok"]


# B4 ----------------------------------------------------------------------------------------

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>INEOS Phenol lifts force majeure on phenol and acetone</title><link>https://x/1</link>
<pubDate>Tue, 18 Aug 2026 09:00:00 GMT</pubDate><description>&lt;p&gt;Gladbeck supply resumed&lt;/p&gt;</description></item>
<item><title>Port notice: berth 12 closed</title><link>https://x/2</link><pubDate>Wed, 19 Aug 2026 09:00:00 GMT</pubDate></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>a</title>
<entry><title>Gelsenkirchen desulphurisation unit restarts</title><link href="https://y/1"/><updated>2026-08-20T10:00:00Z</updated>
<summary>unit back</summary></entry></feed>"""


def test_node_facts_targets_and_ingest(conn, tmp_path):
    t = facts.target_add(conn, "Gelsenkirchen DHT restart", "when did the diesel desulphurisation unit restart", "bp_gelsenkirchen_scholven_output")
    t2 = facts.target_add(conn, "INEOS phenol force majeure lifted", "when was the phenol/acetone force majeure lifted", "european_chemicals")
    src = tmp_path / "s.json"
    src.write_text('{"sources": [{"name": "feed-rss", "url": "rss://a", "node": "european_chemicals", "fact_type": "force_majeure"},'
                   '{"name": "feed-atom", "url": "atom://b", "node": "global_refining", "fact_type": "restart"},'
                   '{"name": "dead", "url": "dead://c"}]}')
    fetch = lambda url: {"rss://a": RSS, "atom://b": ATOM}[url] if url in ("rss://a", "atom://b") else (_ for _ in ()).throw(OSError("unreachable"))
    rep = facts.ingest(conn, src, fetch=fetch)
    assert rep["new_facts"] == 3 and [s["ok"] for s in rep["sources"]] == [True, True, False]
    assert {m["target"] for m in rep["possible_target_matches"]} == {"INEOS phenol force majeure lifted", "Gelsenkirchen DHT restart"}
    rows = facts.node_facts(conn, "european_chemicals")
    assert rows[0]["fact_type"] == "force_majeure" and any(r["source_time"] == "2026-08-18" for r in rows)
    assert "Gladbeck supply resumed" in [r["text"] for r in rows if r["url"] == "https://x/1"][0]
    rep2 = facts.ingest(conn, src, fetch=fetch)
    assert rep2["new_facts"] == 0                     # dedupe by url + node
    fid = [r["id"] for r in rows if r["url"] == "https://x/1"][0]
    with pytest.raises(ValidationError):
        facts.target_close(conn, t2["target_id"], "found")
    facts.target_close(conn, t2["target_id"], "found", fid)
    assert [x["name"] for x in facts.targets(conn, "open")] == ["Gelsenkirchen DHT restart"]
    assert verify_chain(conn, "node_facts")["ok"]


# schema: CHECK rebuild keeps the chain ---------------------------------------------------------

def test_predictions_table_rebuild_preserves_chain(tmp_path):
    db = tmp_path / "old.db"
    c = connect(db)
    rounds.model_cutoff_set(c, TEST_MODEL, "2026-06-30")
    a = make_rule(c)
    rid = make_round(c)
    # rows written before the v12 columns existed, to match the pre-review DDL this test recreates below
    rounds.lock_predictions(c, rid, [pred(a, implied_at_lock=None), pred(a, target="b", implied_at_lock=None)])
    heads_before = {t: v for t, v in __import__("harness.db", fromlist=["chain_heads"]).chain_heads(c).items()}
    # replace the predictions table with the pre-review DDL (no 'map'), copying rows
    c.execute("PRAGMA foreign_keys = OFF")
    c.executescript("""
        DROP TRIGGER no_update_predictions; DROP TRIGGER no_delete_predictions;
        CREATE TABLE predictions_old AS SELECT * FROM predictions ORDER BY rowid;
        DROP TABLE predictions;
        CREATE TABLE predictions (
          id TEXT PRIMARY KEY, round_id TEXT NOT NULL, call_type TEXT NOT NULL CHECK (call_type IN ('sign','magnitude_order','lag_band','predicate','null','meta')),
          target TEXT NOT NULL, claim TEXT NOT NULL, hypothesis_id TEXT, sign TEXT, magnitude_rank INTEGER, lag_band TEXT, carrier TEXT,
          falsifier TEXT, falsifier_window TEXT, mechanism_ids TEXT NOT NULL, baseline_claim TEXT NOT NULL, confidence_band TEXT,
          locked_at TEXT NOT NULL, recorded_at TEXT NOT NULL, prev_row_hash TEXT NOT NULL, row_hash TEXT NOT NULL, aggregation TEXT, branches TEXT, conditional_on TEXT, narrative_sign TEXT, position_id TEXT, carrier_status TEXT);
        INSERT INTO predictions (id, round_id, call_type, target, claim, hypothesis_id, sign, magnitude_rank, lag_band, carrier, falsifier, falsifier_window, mechanism_ids, baseline_claim, confidence_band, locked_at, recorded_at, prev_row_hash, row_hash, aggregation, branches, conditional_on, narrative_sign, position_id, carrier_status) SELECT id, round_id, call_type, target, claim, hypothesis_id, sign, magnitude_rank, lag_band, carrier, falsifier, falsifier_window, mechanism_ids, baseline_claim, confidence_band, locked_at, recorded_at, prev_row_hash, row_hash, aggregation, branches, conditional_on, narrative_sign, position_id, carrier_status FROM predictions_old ORDER BY rowid; DROP TABLE predictions_old;
    """)
    c.close()
    c2 = connect(db)          # init_schema detects the old CHECK and rebuilds
    assert "'map'" in c2.execute("SELECT sql FROM sqlite_master WHERE name='predictions'").fetchone()[0]
    assert verify_chain(c2)["ok"]
    from harness.db import chain_heads
    assert chain_heads(c2)["predictions"] == heads_before["predictions"]
    rounds.lock_predictions(c2, rid, [pred(None, call_type="map", target="map: x", falsifier=None,
                                           settling_document="the primary document for the node (test fixture)")])
    assert verify_chain(c2, "predictions")["ok"] and len(rounds.list_predictions(c2, rid)) == 3
