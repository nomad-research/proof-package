"""The hedge DAG: one sink, one-way, acyclic, ex-ante effect vectors, typed gaps. Synthetic; tests the machinery, not the theory."""
import numpy as np
import pytest

from nomad16 import hedgedag as H
from nomad16.db import Refused

OUT = ["short", "long", "severe"]
# channels the thesis shocks per outcome: the crude price and the refined-product crack (band units). Crude persists in "long"; the product side spikes in "short" and "severe".
SHOCKS = [{"crude": 0.5, "crack": 2.0}, {"crude": 2.0, "crack": -0.4}, {"crude": 3.0, "crack": 1.5}]


def dag(hedge_expo, thesis_expo=None, extra_edges=()):
    return {"thesis": "T", "nodes": {"T": {"kind": "thesis", "exposure": thesis_expo or {"crude": 1.0, "crack": 0.0}},
                                    "H": {"kind": "hedge", "exposure": hedge_expo, "depth": 2}},
            "edges": [{"from": "H", "to": "T"}, *extra_edges]}


def test_both_stay_long_and_a_divergent_effect_vector_lifts_the_worst_case():
    r = H.evaluate(dag({"crude": 0.2, "crack": 1.0}), OUT, SHOCKS)
    v_t, v_h = np.array(r["thesis_vector"]), np.array(r["hedges"]["H"]["vector"])
    assert (v_t > 0).all() and v_h[[0, 2]].min() > 0             # a thesis that never goes short: it is long in every outcome
    assert r["hedges"]["H"]["cosine_to_thesis"] < 0.95
    assert r["maximin"]["worst_case"] >= r["thesis_worst_alone"] - 1e-9


def test_a_hedge_with_the_same_exposure_buys_nothing():
    r = H.evaluate(dag({"crude": 1.0, "crack": 0.0}), OUT, SHOCKS)
    assert r["hedges"]["H"]["cosine_to_thesis"] == pytest.approx(1.0)
    assert r["maximin"]["lift_over_thesis_alone"] == pytest.approx(0.0, abs=1e-9)


def test_unknown_exposure_is_a_typed_gap_and_never_a_zero():
    r = H.evaluate(dag({"crude": 0.2}), OUT, SHOCKS)             # no documented exposure to the crack channel that the thesis shocks
    assert r["gaps"] == {"H": ["crack"]} and "maximin" not in r


def test_the_dag_is_one_way_single_sink_and_acyclic():
    d = dag({"crude": 0.2, "crack": 1.0})
    for bad in ({"from": "T", "to": "H"}, {"from": "H", "to": "H"}):
        with pytest.raises(Refused):
            H.evaluate({**d, "edges": d["edges"] + [bad]}, OUT, SHOCKS)
    two = dag({"crude": 0.2, "crack": 1.0})
    two["nodes"]["T2"] = {"kind": "thesis", "exposure": {"crude": 1.0, "crack": 0.0}}
    with pytest.raises(Refused):                                  # a second thesis in the DAG is a cross-reference
        H.evaluate(two, OUT, SHOCKS)


def test_alignment_decay_by_depth_is_reported():
    d = dag({"crude": 0.2, "crack": 1.0})
    d["nodes"]["H2"] = {"kind": "hedge", "exposure": {"crude": 0.6, "crack": 0.3}, "depth": 1}
    d["edges"].append({"from": "H2", "to": "T"})
    a = H.evaluate(d, OUT, SHOCKS)["alignment_by_depth"]
    assert set(a) == {1, 2} and a[2] < a[1]                      # the deeper hedge is the less aligned one


def test_the_thesis_set_narrows_the_worst_case():
    r_all = H.evaluate(dag({"crude": 0.2, "crack": 1.0}), OUT, SHOCKS)
    r_two = H.evaluate(dag({"crude": 0.2, "crack": 1.0}), OUT, SHOCKS, thesis_set=["long", "severe"])
    assert r_two["thesis_worst_alone"] >= r_all["thesis_worst_alone"]


def test_an_implicit_exposure_is_a_gap_unless_allowed_and_then_it_is_labelled_a_switch():
    d = dag({"crude": 0.2, "crack": {"value": 1.0, "basis": "implicit"}})
    assert H.evaluate(d, OUT, SHOCKS)["gaps"] == {"H": ["crack"]}
    r = H.evaluate(d, OUT, SHOCKS, allow_implicit=True)
    assert r["implicit_used"] == ["H"] and r["status"].startswith("switch") and r["supports"] is False and "maximin" in r
