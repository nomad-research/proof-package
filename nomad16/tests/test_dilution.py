"""The chain-impact model, the buckets and the bend: synthetic recovery. These test the machinery (that it recovers
what is planted and refuses what it should), not the theory that the world behaves this way."""
import math

import numpy as np
import pytest

from nomad16 import config, dilution as D
from nomad16.db import Refused


def E(a, b, t=1.0, **kw):
    return {"from": a, "to": b, "t": t, **kw}


def test_same_root_is_not_summed_and_independent_roots_are():
    # a diamond: one root reaches d by two routes -> one signal, the strongest route
    edges = [E("r", "x", 0.8), E("r", "y", 0.5), E("x", "d", 1.0), E("y", "d", 1.0)]
    res = D.propagate({"r": 1.0}, edges, lambda e: 0.0)
    assert res["d"]["impact"] == pytest.approx(0.8)
    # two independent roots into the same node add, signed
    res = D.propagate({"r1": 1.0, "r2": -0.3}, [E("r1", "d", 1.0), E("r2", "d", 1.0)], lambda e: 0.0)
    assert res["d"]["impact"] == pytest.approx(0.7)


def test_amplifier_fans_out_undiluted_and_the_pot_splits():
    edges = [E("h", f"c{i}", 1.0) for i in range(4)]
    amp = D.propagate({"h": 2.0}, edges, lambda e: 0.0)
    pot = D.propagate({"h": 2.0}, edges, lambda e: 1.0)
    assert all(amp[f"c{i}"]["impact"] == pytest.approx(2.0) for i in range(4))
    assert all(pot[f"c{i}"]["impact"] == pytest.approx(0.5) for i in range(4))


def test_convergence_concentrates_then_the_next_fan_out_projects_back_out():
    edges = [E("r1", "m", 1.0), E("r2", "m", 1.0)] + [E("m", f"o{i}", 0.9) for i in range(3)]
    res = D.propagate({"r1": 1.0, "r2": 1.0}, edges, lambda e: 0.0)
    assert res["m"]["impact"] == pytest.approx(2.0) and res["m"]["retention"] == pytest.approx(2.0)   # concentrated
    assert all(res[f"o{i}"]["impact"] == pytest.approx(1.8) for i in range(3))                           # not diluted by count


def test_a_cycle_and_a_gain_are_refused():
    with pytest.raises(Refused):
        D.propagate({"a": 1.0}, [E("a", "b"), E("b", "a")], lambda e: 0.0)
    with pytest.raises(Refused):
        D.propagate({"a": 1.0}, [E("a", "b", 1.4)], lambda e: 0.0)


def _planted(alpha_by_bucket, n_each=40, noise=0.05, seed=3):
    rng = np.random.default_rng(seed)
    obs = []
    for b, a in alpha_by_bucket.items():
        for _ in range(n_each):
            n = int(rng.integers(2, 9))
            obs.append({"bucket": b, "n": n, "ratio": math.exp(-a * math.log(n) + rng.normal(0, noise))})
    return obs


def test_fit_recovers_planted_alphas_and_shrinkage_pulls_a_thin_bucket():
    obs = _planted({"amp": 0.0, "half": 0.5, "pot": 1.0})
    r = D.fit_alpha(obs, min_obs=5, shrink_k=1.0)
    for b, a in (("amp", 0.0), ("half", 0.5), ("pot", 1.0)):
        assert r["fits"][b]["alpha"] == pytest.approx(a, abs=0.06)
    thin = obs + [{"bucket": "thin", "n": 8, "ratio": math.exp(-1.0 * math.log(8))}] * 5   # 5 obs of a pot
    strong = D.fit_alpha(thin, min_obs=5, shrink_k=50.0)["fits"]["thin"]
    weak = D.fit_alpha(thin, min_obs=5, shrink_k=0.01)["fits"]["thin"]
    assert strong["alpha"] < weak["alpha"] <= 1.0 + 1e-9        # heavy shrinkage pulls it toward the pooled fit


def test_a_thin_bucket_is_a_gap_and_the_result_is_an_interval_not_a_default():
    obs = _planted({"amp": 0.0}) + [{"bucket": "new", "n": 4, "ratio": 0.25}]
    r = D.fit_alpha(obs, min_obs=5, shrink_k=1.0)
    assert r["fits"]["new"]["status"] == "gap" and r["fits"]["new"]["alpha"] is None
    edges = [E("h", f"c{i}", 1.0, bucket="new") for i in range(4)]
    out = D.propagate_interval({"h": 2.0}, edges, {"new": None})
    assert out["gap_edges"] and out["interval"]["c0"] == (pytest.approx(0.5), pytest.approx(2.0))
    edges1 = [E("h", "c", 1.0, bucket="new")]                        # a fan-out of one makes alpha irrelevant
    assert D.propagate_interval({"h": 2.0}, edges1, {"new": None})["gap_edges"] == []


def test_the_bend_is_found_where_retention_starts_to_fall_and_not_on_a_constant_chain():
    def chain(rs):   # a chain whose per-hop retention is rs[k]
        edges, x = [], "r"
        for k, t in enumerate(rs):
            edges.append(E(x, f"n{k}", t))
            x = f"n{k}"
        return D.profile(D.propagate({"r": 1.0}, edges, lambda e: 0.0))
    steady = D.bend(chain([0.7, 0.7, 0.7, 0.7]), tol=0.1, min_nodes=1)
    assert steady["status"] == "no_bend"                              # geometric decay alone is not a bend
    bent = D.bend(chain([0.7, 0.7, 0.4, 0.2]), tol=0.1, min_nodes=1)
    assert bent["status"] == "bend" and bent["bend_at"] == 3
    assert D.bend(chain([0.7, 0.4]), tol=0.1, min_nodes=1)["status"] == "insufficient"


def test_verdict_governing_values_are_refused_until_set():
    with pytest.raises(config.MissingAppetite):
        D.fit_alpha([{"bucket": "a", "n": 2, "ratio": 0.5}])
    with pytest.raises(config.MissingAppetite):
        D.bend([{"depth": 1, "n": 5, "median_r": 1.0}])


def test_partition_is_versioned_knowable_by_the_cutoff_and_feeds_the_profile(db):
    texts = {"e1": "owns 60% of the subsidiary", "e2": "owns 40% of the affiliate", "e3": "buys the whole output of the plant"}
    prop = D.bucket_propose(texts, threshold=0.3)
    assert prop["status"] == "proposal" and sum(len(v) for v in prop["buckets"].values()) == 3
    asg = {k: {"bucket": "own" if k != "e3" else "offtake", "text": t, "text_knowable_from": "2026-07-01"} for k, t in texts.items()}
    with pytest.raises(Refused):                                       # a text from after the lock forms no bucket
        D.bucket_partition_add(db, "P1", "llm", "m", "2026-01-01", "2026-06-30", asg)
    D.bucket_partition_add(db, "P1", "llm", "m", "2026-01-01", "2026-07-15", asg)
    with pytest.raises(Refused):                                       # never overwritten: a re-grouping is a new version
        D.bucket_partition_add(db, "P1", "llm", "m", "2026-01-01", "2026-07-15", asg)
    edges = [E("h", "a", 1.0, key="e1"), E("h", "b", 1.0, key="e2"), E("h", "c", 1.0, key="e3")]
    out = D.depth_profile(db, {"h": 1.0}, edges, "P1")
    assert len(out["gap_edges"]) == 3                                  # nothing fitted yet: all gaps, interval not a default
    obs = [{"edge_key": "e1", "n": n, "ratio": n ** -0.0} for n in (2, 3, 4, 5, 6)]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "get", lambda k, path=None: {"BUCKET_MIN_OBS": 5, "BUCKET_SHRINK_K": 1.0}[k])
        D.bucket_fit(db, "P1", obs, fitted_on="block-1")
    assert D.latest_alphas(db, "P1")["own"] == pytest.approx(0.0, abs=1e-9)
    assert D.latest_alphas(db, "P1")["offtake"] is None
    assert db.verify_chain() == []
