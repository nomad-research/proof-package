"""Exact payoffs and the nonlinear fee (Polymarket frame). Synthetic and pinned to the V1 pilot's arithmetic; tests the machinery, not the theory."""
import numpy as np
import pytest

from nomad16 import exact as X
from nomad16 import instruments as I
from nomad16.db import Refused

CRYPTO = {"exponent": 1, "rate": 0.07, "takerOnly": True, "rebateRate": 0.2}
ECON = {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.25}


def test_fee_is_nonlinear_taker_only_and_absent_when_the_market_has_none():
    assert 100 * X.fee_per_share(0.5, CRYPTO) == pytest.approx(1.75)
    assert 100 * X.fee_per_share(0.9, CRYPTO) == pytest.approx(0.63)
    assert X.fee_per_share(0.0, CRYPTO) == 0.0 and X.fee_per_share(1.0, CRYPTO) == 0.0
    assert X.fee_per_share(0.5, CRYPTO, taker=False) == 0.0
    assert X.fee_per_share(0.5, None) == 0.0 and X.fee_per_share(0.5, {}) == 0.0


def test_share_cost_adds_slippage_rounds_to_the_tick_and_charges_the_fee_at_the_price_paid():
    assert X.share_cost(0.50, CRYPTO, slippage=0.01) == pytest.approx(0.51 + 0.07 * 0.51 * 0.49)
    assert X.entry_price(0.4231, slippage=0.0, tick=0.01) == pytest.approx(0.43)
    assert X.entry_price(0.985, slippage=0.02) == 0.99


def test_a_partition_pays_exactly_one_and_an_open_slot_is_a_typed_gap():
    sp = X.StateSpace({"fed": X.partition_states(["cut50", "cut25", "hold", "hike"])})
    total = sum(sp.vec("fed", lambda v, s=s: v == s) for s in ["cut50", "cut25", "hold", "hike"])
    assert (total == 1.0).all()
    op = X.StateSpace({"race": X.partition_states(["A", "B"], open_slot=True)})
    named = op.vec("race", lambda v: v == "A") + op.vec("race", lambda v: v == "B")
    assert named.tolist() == [1.0, 1.0, 0.0]                       # the gap state pays nothing to a basket that holds no 'Other'
    with pytest.raises(Refused):
        X.partition_states(["A"])


def test_ladders_are_nested_and_yes_plus_no_is_one():
    sp = X.StateSpace({"btc": X.count_states(3)})
    above = [sp.vec("btc", lambda v, i=i: v > i) for i in range(3)]
    assert all((above[i + 1] <= above[i]).all() for i in range(2))
    assert (sp.vec("btc", lambda v: v > 0, "YES") + sp.vec("btc", lambda v: v > 0, "NO") == 1.0).all()


def _toy(excluded):
    sp = X.StateSpace({"A": ["a", "na"], "X": ["x", "nx"]})
    P = sp.vec("A", lambda v: v == "a")
    hedge = {"vec": sp.vec("X", lambda v: v == "x"), "cost": 0.5, "name": "X"}
    mask = sp.mask([lambda s: s["A"] == "na" and s["X"] == "nx"] if excluded else [])
    return sp, P, hedge, mask


def test_the_floor_rises_only_if_the_narrative_removes_a_state():
    sp, P, hedge, mask = _toy(excluded=True)
    r = X.maximin(P, 0.1, 60.0, [hedge], 40.0, mask)
    assert r["floor_primary_alone"] == pytest.approx(-60.0)
    assert r["floor"] == pytest.approx(-20.0) and r["lift"] == pytest.approx(40.0)
    assert r["weights"][0]["shares"] == pytest.approx(80.0) and r["spend"] == pytest.approx(40.0)
    sp, P, hedge, mask = _toy(excluded=False)                      # no claim: the state where both lose is reachable, so a hedge cannot lift the floor
    r0 = X.maximin(P, 0.1, 60.0, [hedge], 40.0, mask)
    assert r0["lift"] == pytest.approx(0.0) and r0["weights"] == []


def test_plain_de_risking_at_equal_floor_and_realised_scoring():
    sp, P, hedge, mask = _toy(excluded=True)
    r = X.maximin(P, 0.1, 60.0, [hedge], 40.0, mask)
    assert X.equal_floor_outlay(P, 0.1, r["floor"], mask) == pytest.approx(20.0)
    w = [{**r["weights"][0], "won": 0.0}]                          # the narrative failed in the world: hedge paid nothing, primary lost
    assert X.realised(r["primary_shares"], 0.1, 0.0, w) == pytest.approx(-100.0)
    w = [{**r["weights"][0], "won": 1.0}]
    assert X.realised(r["primary_shares"], 0.1, 0.0, w) == pytest.approx(-20.0)


def test_cardinality_cap_and_an_empty_reachable_set():
    sp = X.StateSpace({"A": ["a", "na"], "X": ["x", "nx", "y"]})
    P = sp.vec("A", lambda v: v == "a")
    cands = [{"vec": sp.vec("X", lambda v, k=k: v == k), "cost": 0.3, "name": k} for k in ("x", "nx", "y")]
    mask = sp.mask()
    r = X.maximin(P, 0.1, 60.0, cands, 40.0, mask, ncap=1)
    assert len(r["weights"]) <= 1 and r["floor"] >= r["floor_primary_alone"] - 1e-9
    with pytest.raises(Refused):
        X.maximin(P, 0.1, 60.0, cands, 40.0, sp.mask([lambda s: True]))


def test_the_pilot_arithmetic_is_reproduced():
    """V1 pilot (lookbacks/polymarket/PILOT_V1.md): Fed 25 bp cut at 0.0065 (fee 0.05), Bitcoin dip $65k at 0.425 (fee 0.07), slippage 0.01."""
    c_p = X.share_cost(0.0065, ECON, 0.01)
    c_h = X.share_cost(0.425, CRYPTO, 0.01)
    assert c_p == pytest.approx(0.0173, abs=1e-4) and c_h == pytest.approx(0.4522, abs=1e-4)
    sp = X.StateSpace({"fed": X.partition_states(["cut50", "cut25", "hold", "hike"]), "dip": X.count_states(3)})
    P = sp.vec("fed", lambda v: v == "cut25")
    hedge = {"vec": sp.vec("dip", lambda v: v > 2), "cost": c_h, "name": "dip65"}      # 'touched the median strike' pays when the count passes it
    mask = sp.mask([lambda s: s["fed"] == "cut50", lambda s: s["fed"] in ("hold", "hike") and s["dip"] <= 2])
    r = X.maximin(P, c_p, 60.0, [hedge], 40.0, mask)
    assert r["floor"] == pytest.approx(-11.54, abs=0.02)


def test_event_contract_meta_and_the_nonlinear_unit_cost(tmp_path):
    from nomad16.db import DB
    db = DB(str(tmp_path / "t.db"))
    inst = I.instrument_add(db, "ec1", "event_contract", "ETH>2400", "2026-10-01T00:00:00Z", ack_id="ack1", yes_outcomes=["above"])
    with pytest.raises(Refused):
        I.event_contract_meta_add(db, "nope", "0xc", "tok", "YES")
    with pytest.raises(Refused):
        I.event_contract_meta_add(db, "ec1", "0xc", "tok", "MAYBE")
    with pytest.raises(Refused):
        I.event_contract_meta_add(db, "ec1", "0xc", "tok", "YES", slot_kind="mystery")
    meta = I.event_contract_meta_add(db, "ec1", "0xc", "tok", "YES", event_id="1080632", tick_size=0.001, fee_schedule=CRYPTO)
    assert db.get("event_contract_meta", "ec1")["fee_schedule"]["rate"] == 0.07
    held = I.unit_cost(inst, 0.5, None, 3, False, meta=meta, hold_to_resolution=True)
    traded = I.unit_cost(inst, 0.5, None, 3, False, meta=meta)
    assert traded == pytest.approx(2 * held) and held > X.fee_per_share(0.5, CRYPTO)
    assert I.unit_cost(inst, 0.5, None, 3, False) != held          # without meta the old linear model stands


def test_build_exact_returns_the_build_record_shape_and_flags_open_slots():
    from nomad16 import construct
    sp = X.StateSpace({"A": ["a", "na"], "X": ["x", "nx"]})
    P = {"instrument_id": "P", "vec": sp.vec("A", lambda v: v == "a"), "cost": 0.1}
    H = {"instrument_id": "H", "vec": sp.vec("X", lambda v: v == "x"), "cost": 0.5}
    mask = sp.mask([lambda s: s["A"] == "na" and s["X"] == "nx"])
    rec = construct.build_exact({"key": "ack1"}, ["na"], P, [H], sp, mask, 100.0)
    assert rec["status"] == "built" and rec["z_star"] == pytest.approx(-20.0)
    assert {w["role"] for w in rec["weights"]} == {"primary", "hedge"} and rec["max_loss"] == pytest.approx(100.0)
    assert min(s["payoff_worst"] for s in rec["scenarios"]) == pytest.approx(-20.0) and len(rec["scenarios"]) == 3
    none = construct.build_exact({"key": "ack1"}, ["na"], P, [H], sp, sp.mask(), 100.0)
    assert none["status"] == "unbuildable" and none["reason"] == "no_lift"
    assert construct.build_exact({"key": "a"}, [], P, [], sp, mask, 100.0)["reason"] == "no_instrument"
    op = X.StateSpace({"R": X.partition_states(["A", "B"], open_slot=True), "X": ["x", "nx"]})
    Po = {"instrument_id": "PA", "vec": op.vec("R", lambda v: v == "A"), "cost": 0.4}
    Ho = {"instrument_id": "HX", "vec": op.vec("X", lambda v: v == "x"), "cost": 0.5}
    m2 = op.mask([lambda s: s["R"] != "A" and s["X"] == "nx"])
    r2 = construct.build_exact({"key": "ack2"}, ["B"], Po, [Ho], op, m2, 100.0)
    assert "open_slot_reachable" in r2["flags"] and r2["detail"]["open_slots_reachable"] == ["R"]


class _View:
    manifest = None

    def __init__(self, db):
        self.db = db

    def led(self, table, where="", params=()):
        return self.db.rows(table, where, params)


def test_polymarket_vintage_truncates_at_the_lock_verifies_records_drift_and_applies_the_age_rule(tmp_path, monkeypatch):
    import json as _json
    from nomad16 import prices
    from nomad16.db import DB
    db = DB(str(tmp_path / "p.db")); view = _View(db)
    body = {"history": [{"t": 1000, "p": 0.40}, {"t": 2000, "p": 0.42}, {"t": 3000, "p": 0.45}, {"t": 4000, "p": 0.50}]}
    monkeypatch.setattr(prices, "curl", lambda url: _json.dumps(body))
    r = prices.fetch_polymarket(db, "tok1", 0, 5000, ceiling_ts=3000)
    assert r["n_points"] == 2 and r["last"] == 2000                     # points at or after the lock never reach the store
    assert prices.pm_points(view, "tok1") == [(1000, 0.40), (2000, 0.42)]
    assert prices.pm_price_at(view, "tok1", 2500) == (0.42, pytest.approx(500 / 3600))
    assert prices.pm_price_at(view, "tok1", 2000 + 49 * 3600) == (None, None)   # stale beyond 48 hours: no eligible price
    assert prices.pm_price_at(view, "tok1", 500) == (None, None)
    body["history"][1]["p"] = 0.44                                        # a refetch that disagrees is stored with drift_of set, never substituted silently
    r2 = prices.fetch_polymarket(db, "tok1", 0, 5000, ceiling_ts=3000)
    assert r2["drift_of"] == r["vintage_id"] and r2["drift_times"] == [2000]
    for bad in ([{"t": 2, "p": 0.5}, {"t": 1, "p": 0.5}], [{"t": 1, "p": 1.5}], [{"t": 1}]):
        monkeypatch.setattr(prices, "curl", lambda url, b=bad: _json.dumps({"history": b}))
        with pytest.raises(Refused):
            prices.fetch_polymarket(db, "tok2", 0, 5000, None)
    monkeypatch.setattr(prices, "curl", lambda url: "not json")
    with pytest.raises(Refused):
        prices.fetch_polymarket(db, "tok3", 0, 5000, None)
