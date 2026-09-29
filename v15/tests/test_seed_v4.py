"""The v4 seed (rounds 1-3, predicates, library, names book, positions, hypotheses) loads through the live API."""
import pytest

from harness import hypotheses, library, names, positions, predicates, rounds, scorer, t0
from harness.config import NULL_CALL_WEIGHT
from harness.db import verify_chain
from harness.errors import NotFound
from harness.seed import DEFAULT_SEED, SEED_DIR, load_seed

from conftest import pred


@pytest.fixture
def seeded(conn):
    rep = load_seed(conn, DEFAULT_SEED)
    return conn, rep


def test_v4_seed_counts_and_chain(seeded):
    conn, rep = seeded
    assert (rep["predicates"], rep["library_rules"], rep["holders"], rep["retro_rounds"], rep["hypotheses"],
            rep["t0_candidates"]) == (14, 32, 25, 3, 3, 3)
    assert rep["positions"] == 26          # 25 rows, one 'both' split into two
    assert rep["chain_ok"] and verify_chain(conn)["ok"]
    assert not [w for w in rep["warnings"] if "harness derived" in w], rep["warnings"]
    states = {r["state"] for r in conn.execute("SELECT state FROM round_state")}
    assert states == {"scored"}
    # idempotent
    rep2 = load_seed(conn, DEFAULT_SEED)
    assert (rep2["predicates"], rep2["library_rules"], rep2["holders"], rep2["positions"], rep2["retro_rounds"],
            rep2["hypotheses"], rep2["t0_candidates"]) == (0, 0, 0, 0, 0, 0, 0)


def test_v4_scorecards_match_session_record(seeded):
    conn, rep = seeded
    r1, r2, r3 = (rep["scorecards"][k] for k in ("round.1", "round.2", "round.3"))
    # round 1: 6 calls; gold/vol untestable -> 5 in denominator; hits: oil (quarantined), tankers, defense
    assert r1["outcome_score"] == pytest.approx(3 / 5)
    assert r1["mechanism_score"] == pytest.approx(2 / 5)
    assert r1["baseline_score"] == pytest.approx(1 / 5)      # defense only (gold baseline hit is untestable row)
    assert not r1["arming_claimed"] and not r1["arming_observed"]   # gate claimed unknown, observed fails
    assert r1["any_arming_claimed"]                                  # first traversal was claimed (and failed)
    # round 2: 8 calls; owner untestable -> 7; hits fm, po_spot, chain, meta_lag
    assert r2["outcome_score"] == pytest.approx(4 / 7) and r2["mechanism_score"] == pytest.approx(4 / 7)
    assert r2["baseline_score"] == pytest.approx(1 / 7)
    assert r2["arming_claimed"] and not r2["arming_observed"]   # gate claimed weakly, observed fails
    assert r2["any_arming_observed"]                            # catalyst class did hold, but it is not the gate
    # round 3: three nulls at 0.2 + two full-weight hits; all hit
    assert r3["null_called"] and r3["outcome_score"] == 1.0 and r3["mechanism_score"] == 1.0
    assert r3["baseline_score"] == 0.0 and not r3["arming_claimed"]
    quarantined = conn.execute("SELECT COUNT(*) FROM resolutions WHERE quarantined = 1").fetchone()[0]
    assert quarantined == 1
    assert conn.execute("SELECT COUNT(*) FROM resolutions WHERE weight = ?", (NULL_CALL_WEIGHT,)).fetchone()[0] == 3
    ps = scorer.programme_stats(conn, include_learning=True)
    assert ps["rounds_scored"] == 3 and ps["rounds_armed"] == 0 and ps["arming_rate"] == 0.0
    assert scorer.programme_stats(conn)["rounds_scored"] == 0     # no clean rounds yet


def test_v4_library_stats_from_ledgers(seeded):
    conn, _ = seeded
    r = library.get_rule(conn, "lib.supply_fear_fade")
    assert (r["trials"], r["hits"], r["misses"], r["status"]) == (0, 0, 0, "candidate")   # v11 A1: learning round, no trial
    r = library.get_rule(conn, "lib.coproduct_collateral")
    assert (r["trials"], r["misses"], r["false_alarms"]) == (0, 0, 0)      # v11 A1: learning rounds are not trials
    r = library.get_rule(conn, "lib.toll_booth_learns_first")
    assert r["trials"] == 0 and r["hits"] == 0 and r["status"] == "candidate"   # v11 A1: both hits are in a learning round
    comp = library.get_rule(conn, "lib.comp.plant_outage_chain")
    assert comp["trials"] == 0 and comp["review_flag"] == 0     # no part of it has a miss on record
    comp2 = library.get_rule(conn, "lib.comp.chokepoint_late_crisis")
    assert comp2["trials"] == 0
    # substitutes_gift: round 1 methanol call was a miss with the mechanism right (a misread, A13: no debit);
    # v11 A1: the retro rounds are learning class, so none of their resolutions is a trial of any rule at all
    assert library.get_rule(conn, "lib.substitutes_gift")["misses"] == 0
    assert [r["key"] for r in library.query(conn, limit=100) if r["status"] == "validated"] == []
    rc = library.get_rule(conn, "lib.route_closure")
    assert (rc["trials"], rc["hits"], rc["misses"], rc["clean_hit_rounds"]) == (0, 0, 0, 0)
    assert rc["weight"] == 0.0 and rc["weight_state"] == "untested as carried"
    assert library.rebuild_library_stats(conn)["citations_excluded_learning"] > 0
    assert {r["contamination"] for r in conn.execute("SELECT contamination FROM round_classification")} == {"q2_unknown"}


def test_v4_names_and_positions(seeded):
    conn, _ = seeded
    assert names.resolve(conn, "Bayport Choate")["holder"]["parent"]["canonical_name"] == "LyondellBasell Industries"
    assert names.resolve(conn, "LYB")["holder"]["key"] == "holder.lyb"
    assert names.resolve(conn, "Deurganckdok")["holder"]["kind"] == "facility"
    assert not names.resolve(conn, "Acme Foam LLC")["resolved"]
    node = positions.positions_on_node(conn, "us_propylene_oxide_supply")
    assert [h["key"] for h in node["self_hedged"]] == ["holder.lyb"]
    pair_keys = {(p["plus"]["holder_id"], p["minus"]["holder_id"]) for p in node["pairs"]}
    plus = {names.get_holder(conn, a)["key"] for a, _ in pair_keys}
    minus = {names.get_holder(conn, b)["key"] for _, b in pair_keys}
    assert plus == {"holder.dow", "holder.hun"} and minus == {"holder.leg", "holder.tpx", "holder.lea", "holder.adnt"}
    assert positions.positions_on_node(conn, "port_of_antwerp_seagoing_access")["pairs"] == []
    c = t0.count(conn, "2026Q2-learning")
    assert (c["candidates"], c["criteria_pass"], c["arming_pass"], c["arming_pass_pair"]) == (2, 1, 0, 0)


def test_v4_hypotheses_and_keys_in_play(seeded):
    conn, _ = seeded
    due = hypotheses.hypotheses_due(conn)
    assert due["count"] == 3
    gate = predicates.resolve_predicate(conn, "pred.arm.tradability_gate")
    assert gate["kind"] == "arming" and gate["key"] == "pred.arm.tradability_gate"
    # a new round can cite library keys and predicate keys directly
    from conftest import TEST_MODEL, TODAY
    rid = rounds.submit_event(conn, "a new event", "2026-08-01", "t", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY)["round_id"]
    rounds.round_note(conn, rid, "lock", "no-touched-set: test")
    lock = rounds.lock_predictions(conn, rid, [pred("lib.toll_booth_learns_first"), pred("lib.comp.chokepoint_late_crisis", target="b")])
    stored = rounds.list_predictions(conn, rid)
    assert stored[0]["mechanism_ids"] == [library.get_rule(conn, "lib.toll_booth_learns_first")["id"]]
    predicates.predicate_check(conn, rid, [{"predicate_id": "pred.arm.tradability_gate", "claimed": "fails", "basis": "no listed holder on the node"}])
    with pytest.raises(NotFound):
        rounds.lock_predictions(conn, "round.1", [pred("lib.route_closure")])   # seed round keys are not round ids


def test_seed_v1_still_loads(conn):
    rep = load_seed(conn, SEED_DIR / "seed_v1.json")
    assert rep["holders"] == 2 and rep["hypotheses"] == 2 and verify_chain(conn)["ok"]
