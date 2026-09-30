"""V1 scoring: tier-to-rung mapping, exact state spaces, the arms, and the study's verdict. Synthetic rounds and a stub price function; no network.
The first test reproduces the V1 pilot's arithmetic (floor -11.54) through the whole pipeline."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lookbacks", "polymarket"))
import v1_score as S  # noqa: E402

CRYPTO = {"exponent": 1, "rate": 0.07, "takerOnly": True, "rebateRate": 0.2}
ECON = {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.25}


def con(label, q, yes_won, fee=CRYPTO, end=None, tick=0.001):
    return {"label": label, "cid": "0x" + label, "tok_yes": "tok" + label, "q": q, "fee": fee, "tick": None, "end": end, "yes_won": yes_won}


def pilot(touched_dips=(True, False, False, False, False), fed_winner="hold", claim_then_tier="mild"):
    fed = [con("C1", "Will the Fed cut 50+ bps?", fed_winner == "cut50", ECON), con("C2", "Will the Fed cut 25 bps?", fed_winner == "cut25", ECON),
           con("C3", "Will the Fed hold?", fed_winner == "hold", ECON), con("C4", "Will the Fed hike?", fed_winner == "hike", ECON)]
    strikes = [75, 70, 65, 60, 55]
    dips = [con(f"E1.{i + 1}", f"Will Bitcoin dip to ${k},000 in April?", touched_dips[i]) for i, k in enumerate(strikes)]
    reach = [con(f"E1.{6 + i}", f"Will Bitcoin reach ${k},000 in April?", False) for i, k in enumerate((80, 85, 90))]
    prices = {"tokC1": 0.0035, "tokC2": 0.0065, "tokC3": 0.9845, "tokC4": 0.0065, "tokE1.1": 0.90, "tokE1.2": 0.80, "tokE1.3": 0.425, "tokE1.4": 0.175, "tokE1.5": 0.075,
              "tokE1.6": 0.225, "tokE1.7": 0.08, "tokE1.8": 0.03}
    R = {"round_id": "Rpilot", "primary": {"kind": "partition exact", "total": 4, "shown": 4, "contracts": {c["label"]: c for c in fed}},
         "ans1a": {"primary": {"basket": [{"contract": "C2", "side": "YES"}]}},
         "ans1b": {"hedges": [{"event": "E1", "direction": "dip", "tier": claim_then_tier}],
                   "claims": [{"if": {"contract": "C2", "resolves": "NO"}, "then": {"event": "E1", "direction": "dip", "tier": claim_then_tier}}]},
         "menu": {"E1": {"kind": "touch ladder", "contracts": dips + reach, "total": 8}}}
    return R, (lambda tok: (prices.get(tok), 1.0) if tok in prices else (None, None))


def test_the_pilot_arithmetic_through_the_whole_pipeline_and_a_wrong_narrative_is_caught():
    R, po = pilot()
    r = S.score_round(R, po)
    assert r["status"] == "scored" and r["tier_map"]["E1:mild:dip"]["rung"] == "E1.3"          # the dip rung whose lock price is nearest 0.50 is the $65k one
    assert r["floors"]["P"] == pytest.approx(-100.0) and r["floors"]["C"] == pytest.approx(-11.54, abs=0.03)
    assert r["floors"]["D"] == pytest.approx(r["floors"]["C"], abs=1e-6)
    assert r["realised"]["P"] == pytest.approx(-100.0) and r["realised"]["C"] == pytest.approx(-100.0, abs=1e-6)     # the narrative failed: only $75k was touched
    assert r["realised"]["D"] == pytest.approx(r["floors"]["C"], abs=0.03)
    assert r["in_reachable_set"] is False and r["claims_violated"] and r["primary_failed"] is True
    assert r["realised"]["R_draws"] == S.N_R_DRAWS and r["lift"] == pytest.approx(r["floors"]["C"] + 100.0 * 0.6, abs=0.05)


def test_when_the_claim_holds_the_hedge_pays_and_the_floor_is_kept():
    R, po = pilot(touched_dips=(True, True, True, False, False))
    r = S.score_round(R, po)
    assert r["in_reachable_set"] is True and r["claims_violated"] == []
    assert r["realised"]["C"] == pytest.approx(r["floors"]["C"], abs=0.03)                     # $65k touched: the hedge pays exactly its floor's worth
    assert r["realised"]["C"] > -100.0
    R2, po2 = pilot(fed_winner="cut25", touched_dips=(False,) * 5)                              # the primary wins; the hedge is a cost, the claim is vacuous
    r2 = S.score_round(R2, po2)
    assert r2["in_reachable_set"] is True and r2["realised"]["P"] > 0 and r2["primary_failed"] is False
    assert r2["realised"]["C"] < r2["realised"]["P"]                                            # upside given up to the hedge and the 60% split


def test_no_claims_means_no_lift_and_the_round_is_still_scored():
    R, po = pilot()
    R["ans1b"]["claims"] = []
    r = S.score_round(R, po)
    assert r["status"] == "scored" and r["lift"] == pytest.approx(0.0, abs=1e-9) and r["floors"]["C"] == pytest.approx(-60.0)
    assert r["hedge"] == [] and r["realised"]["C"] == pytest.approx(-60.0)


def test_unscored_reasons():
    R, po = pilot(); R["ans1b"] = {"hedges": [], "no_instrument": True}
    assert S.score_round(R, po)["reason"] == "no_instrument"
    R, po = pilot()
    assert S.score_round(R, lambda t: (None, None) if t == "tokC2" else po(t))["reason"] == "primary_unpriced"
    assert S.score_round(R, lambda t: (None, None) if t.startswith("tokE") else po(t))["reason"] == "no_hedge_priced"


def test_claims_narrow_the_reachable_set_and_contradictory_claims_can_empty_it():
    R, po = pilot()
    r = S.score_round(R, po)
    assert r["reachable_states"] < r["lock_states"]
    R["ans1b"]["claims"] = [{"if": {"contract": "C2", "resolves": "NO"}, "then": {"contract": "E1.3", "resolves": "YES"}},
                            {"if": {"contract": "C2", "resolves": "NO"}, "then": {"contract": "E1.3", "resolves": "NO"}},
                            {"if": {"contract": "C2", "resolves": "YES"}, "then": {"contract": "E1.3", "resolves": "YES"}},
                            {"if": {"contract": "C2", "resolves": "YES"}, "then": {"contract": "E1.3", "resolves": "NO"}}]
    assert S.score_round(R, po)["reason"] == "claims_exclude_every_state"


def cs(*rows):
    return [con(f"E9.{i + 1}", q, w) for i, (q, w) in enumerate(rows)]


def test_tier_mapping_by_direction_orientation_and_target():
    price = {"tokE9.1": 0.72, "tokE9.2": 0.30, "tokE9.3": 0.20}
    po = lambda t: (price[t], 1.0)
    lad = cs(("Will Bitcoin be above $80,000 on May 1?", False), ("Will Bitcoin be above $90,000 on May 1?", False), ("Will Bitcoin be below $70,000 on May 1?", False))
    c, side, q = S.map_tier(lad, "price ladder", "below", "moderate", po)
    assert (c["label"], side) == ("E9.1", "NO") and q == pytest.approx(0.28)                    # NO on 'above $80k' is 'below', at probability 0.28, nearest 0.25
    c, side, q = S.map_tier(lad, "price ladder", "below", "mild", po)
    assert (c["label"], side) == ("E9.2", "NO") and q == pytest.approx(0.70)
    c, side, q = S.map_tier(lad, "price ladder", "above", "severe", po)
    assert (c["label"], side) == ("E9.2", "YES") and q == pytest.approx(0.30)                        # 'above' wants an up-type YES (0.72, 0.30) or a down-type NO (0.80): nearest 0.10 is 0.30
    tl = cs(("Will X reach $10?", False), ("Will X reach $20?", False), ("Will X dip to $5?", False))
    tp = {"tokE9.1": (0.4, 1), "tokE9.2": (0.1, 1), "tokE9.3": (0.5, 1)}
    assert S.map_tier(tl, "touch ladder", "reach", "mild", lambda t: tp[t])[0]["label"] == "E9.1"        # the dip contract (0.5) is ignored for 'reach'
    dl = cs(("Will it happen by June 30?", False), ("Will it happen by July 31?", False), ("Will it happen by Aug 31?", False), ("Will it happen by Sep 30?", False))
    pr = {"tokE9.1": 0.9, "tokE9.2": 0.6, "tokE9.3": 0.3, "tokE9.4": 0.1}
    assert S.map_tier(dl, "date ladder", "by_date", "severe", lambda t: (pr[t], 1))[0]["label"] == "E9.4"
    assert S.map_tier(dl, "date ladder", "by_date", "mild", lambda t: (pr[t], 1))[0]["label"] == "E9.2"
    assert S.map_tier(dl, "date ladder", "by_date", "mild", lambda t: (None, None)) is None


def test_open_partition_gap_is_flagged_and_structure_violations_are_reported():
    fed = [con("C1", "A?", False), con("C2", "B?", True), con("C3", "C?", True)]                # two winners in a partition: a data anomaly
    R = {"round_id": "Rp", "primary": {"kind": "partition open", "total": 5, "shown": 3, "contracts": {c["label"]: c for c in fed}},
         "ans1a": {"primary": {"basket": [{"contract": "C1", "side": "YES"}]}},
         "ans1b": {"hedges": [{"contract": "E1.1", "side": "YES"}], "claims": [{"if": {"contract": "C1", "resolves": "NO"}, "then": {"contract": "E1.1", "resolves": "YES"}}]},
         "menu": {"E1": {"kind": "partition exact", "total": 2, "contracts": [con("E1.1", "H?", True), con("E1.2", "I?", False)]}}}
    r = S.score_round(R, lambda t: (0.3, 1.0))
    assert r["status"] == "scored" and r["open_slot_reachable"] is True and any(f.startswith("structure_violation:P") for f in r["flags"])


def rr(i, C, D, P, ok=True, Cr=0.7, fail=None):
    return {"round_id": f"R{i:03d}", "status": "scored", "in_reachable_set": ok, "primary_failed": (P < -10) if fail is None else fail,
            "realised": {"C": C, "D": D, "P": P, "P60": 0.6 * P, "H": C - 0.6 * P, "C_above_R": Cr}}


def test_study_verdicts():
    good = [rr(i, C=-20 + 30 * (i % 2) + 5, D=-25 + 20 * (i % 2), P=-100 if i % 2 == 0 else 60) for i in range(24)]
    rep = S.study(good)
    assert rep["gates"]["scored_ge_20"] and rep["gates"]["primary_loss_rounds"] == 12 and rep["B1"]["holds"] and rep["B2"]["mean_C_minus_D"] > 0
    assert rep["verdict"] in ("pass", "inconclusive")                                              # pass needs the null controls too; never 'dead' here
    few = S.study(good[:10]); assert few["verdict"] == "inconclusive" and not few["gates"]["scored_ge_20"]
    bad_set = [rr(i, C=-20, D=-25, P=-100, ok=(i % 3 != 0)) for i in range(24)]
    assert S.study(bad_set)["verdict"] == "dead" and "B1" in S.study(bad_set)["why"]
    worse = [rr(i, C=-50, D=-20, P=-100 if i % 2 == 0 else 60) for i in range(24)]
    assert S.study(worse)["verdict"] == "dead" and "B2" in S.study(worse)["why"]
    assert S.study([{"round_id": "R1", "status": "unscored", "reason": "no_instrument"}])["verdict"] == "inconclusive"


def test_strike_parsing_does_not_read_the_b_of_by_as_a_billion_and_duplicate_rungs_are_not_mapped_to():
    assert S.strike("Will Gold (GC) hit (LOW) $3,400 by end of June?") == 3400
    assert S.strike("Will X reach $2.5m?") == 2_500_000 and S.strike("Will X reach $150k in February?") == 150_000 and S.strike("Will X hit $4 billion by May?") == 4e9
    lad = [con("E9.r1", "Will Gold hit (HIGH) $5,000 by end of June?", False), con("E9.r2", "Will Gold hit (HIGH) $5,000 by end of June?", True),
           con("E9.r3", "Will Gold hit (HIGH) $5,500 by end of June?", False), con("E9.r4", "Will Gold hit (LOW) $4,000 by end of June?", False)]
    uniq, dup = S.unique_rungs(lad, "touch ladder")
    assert [c["label"] for c in uniq] == ["E9.r3", "E9.r4"] and dup == 1                       # both $5,000 contracts are ambiguous; a LOW and a HIGH at different strikes are not
    price = {"tokE9.r1": 0.5, "tokE9.r2": 0.5, "tokE9.r3": 0.2, "tokE9.r4": 0.3}
    c, side, q = S.map_tier(lad, "touch ladder", "reach", "mild", lambda t: (price[t], 1))
    assert c["label"] == "E9.r3"                                                                # the nearer-to-0.5 duplicate is skipped as ambiguous
