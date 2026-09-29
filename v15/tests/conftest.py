from datetime import date

import pytest

from harness import library, rounds
from harness.db import connect

TODAY = date(2026, 9, 7)          # clean window for test-model (cutoff 2026-06-30): 2026-07-01 .. 2026-08-10
TEST_MODEL = "test-model"


@pytest.fixture
def conn():
    c = connect(":memory:")
    rounds.model_cutoff_set(c, TEST_MODEL, "2026-06-30", "test fixture")
    from harness.cli import bootstrap
    bootstrap(c)
    yield c
    c.close()


ALL_KINDS = ["occurrence", "absence", "ordering", "magnitude", "duration"]


def make_rule(conn, text="the toll booth learns before the cargo", layer="sequence", composed_of=None, carries=None):
    return library.propose(conn, text, "cargo repricing before the toll reprices", 3, layer,
                           "test fixture", composed_of, carries=carries or ALL_KINDS)["rule_id"]


def make_round(conn, text="a chokepoint closes to tanker traffic", date="2026-07-15", operator=TEST_MODEL,
               round_class=None, today=TODAY):
    rid = rounds.submit_event(conn, text, date, "test", "first candidate that passes Q1-Q9", 0,
                              {"Q1": "pass", "Q2": "unknown"}, round_class=round_class, operator_model=operator,
                              today=today)["round_id"]
    rounds.round_note(conn, rid, "lock", "no-touched-set: test fixture")     # B3 satisfied by declaration
    return rid


def pred(rule_id, call_type="sign", **kw):
    base = {"call_type": call_type, "target": "route insurance premia", "claim": "premia rise first",
            "carrier": "war-risk premium quotes", "falsifier": "cargo reprices before premia",
            "mechanism_ids": [rule_id] if rule_id else [], "baseline_claim": "no change", "sign": "+"}
    if call_type in ("null", "predicate"):
        base["falsifier_window"] = "scoring_window"
    if call_type == "map":
        # v14 C3: a map call names the document that would settle it
        base["settling_document"] = "the operator's registry page for the node (test fixture)"
        base["settling_document_fetched"] = False
    if call_type in ("sign", "magnitude_order"):
        # v12 D1: a call on a listed leg records what was already priced. The fixture reads the move already made.
        base["implied_at_lock"] = {"method": "realised_since_event", "value": 1.0, "source": "test fixture",
                                   "as_of": "2026-07-16T00:00:00Z", "basis": "the move between the event and lock"}
    base.update(kw)
    return base


def res(pid, outcome="hit", mech="right", base="miss", **kw):
    d = {"prediction_id": pid, "outcome": outcome, "mechanism_outcome": mech, "baseline_outcome": base,
         "evidence_ids": [], "scorer_note": "test"}
    if outcome in ("miss", "unverified"):
        d["source_coverage"] = "adequate"
    d.update(kw)
    return d


def play_round(conn, preds, resolutions_for, **round_kw):
    """Full clean round: submit -> lock -> open -> score."""
    from harness import scorer
    rid = make_round(conn, **round_kw)
    rounds.reveal_event(conn, rid)
    ids = rounds.lock_predictions(conn, rid, preds)["prediction_ids"]
    rounds.open_retrieval(conn, rid)
    card = scorer.score_round(conn, rid, resolutions_for(ids))
    return rid, ids, card


def dated_evidence(conn, rid):
    """One stated-dated evidence row on an open round; returns its id."""
    return rounds.add_evidence(conn, rid, "https://x", "t", "e", source_time="2026-07-20")["evidence_id"]
