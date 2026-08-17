"""Unit tests for the shared infrastructure.

Run: python -m pytest nomad/tests_common/test_infra.py -q
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nomad.infra.config_logger import ConfigLogger, trial_count, summarise
from nomad.infra.cost_model import (
    CostParams, apply_costs, corwin_schultz_spread, cost_summary, round_trip_cost_bps,
)
from nomad.infra.deflated_sharpe import (
    deflated_sharpe_ratio, expected_max_sharpe, probability_of_backtest_overfitting,
    sharpe_stats,
)
from nomad.infra.inference_family import (
    InferenceFamily, Link, LinkRegistry, effective_breadth, family_error_correlation,
)
from nomad.infra.pit_corpus import PITCorpus


# ------------------------------------------------------------------ config log

def test_config_logger_counts_every_evaluation_including_failures():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "log.jsonl"
        log = ConfigLogger("A", path=p)
        log.log({"window": 30}, description="first")
        log.log({"window": 60}, description="second")
        with pytest.raises(RuntimeError):
            with log.evaluation({"window": 90}) as ev:
                ev.record(t_stat=1.0)
                raise RuntimeError("boom")
        # the failed evaluation still consumed a degree of freedom
        assert trial_count(p) == 3
        s = summarise(p)
        assert s["failed"] == 1
        assert s["distinct_configs"] == 3


def test_config_logger_is_append_only():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "log.jsonl"
        ConfigLogger("A", path=p).log({"a": 1})
        first = p.read_text()
        ConfigLogger("A", path=p).log({"a": 2})
        assert p.read_text().startswith(first)


# ------------------------------------------------------------------ deflated sharpe

def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(10, 0.01) < expected_max_sharpe(1000, 0.01)
    assert expected_max_sharpe(1, 0.01) == 0.0


def test_dsr_penalises_more_trials():
    rng = np.random.default_rng(0)
    r = rng.normal(0.0006, 0.01, 2000)  # ~SR 0.95 annualised
    few = deflated_sharpe_ratio(r, n_trials=2, sharpe_variance=0.001)
    many = deflated_sharpe_ratio(r, n_trials=10_000, sharpe_variance=0.001)
    assert few.deflated_sharpe > many.deflated_sharpe
    assert many.expected_max_sharpe > few.expected_max_sharpe


def test_dsr_of_pure_noise_is_unimpressive():
    rng = np.random.default_rng(1)
    r = rng.normal(0.0, 0.01, 2000)
    res = deflated_sharpe_ratio(r, n_trials=100, sharpe_variance=0.001)
    assert res.deflated_sharpe < 0.95


def test_sharpe_stats_annualisation():
    rng = np.random.default_rng(2)
    r = rng.normal(0.001, 0.01, 5000)
    st = sharpe_stats(r)
    assert st.annualised(252) == pytest.approx(st.sharpe * math.sqrt(252))


def test_pbo_high_for_pure_noise():
    rng = np.random.default_rng(3)
    M = rng.normal(0, 0.01, (1000, 20))  # 20 configs, none has real edge
    res = probability_of_backtest_overfitting(M, n_splits=8, max_combinations=200)
    assert 0.0 <= res["pbo"] <= 1.0
    assert res["pbo"] > 0.2  # noise-selected winners should not persist


def test_pbo_low_when_one_config_genuinely_dominates():
    rng = np.random.default_rng(4)
    M = rng.normal(0, 0.01, (1000, 10))
    M[:, 3] += 0.004  # config 3 has a large, stable, real edge
    res = probability_of_backtest_overfitting(M, n_splits=8, max_combinations=200)
    assert res["pbo"] < 0.1


# ------------------------------------------------------------------ cost model

def test_corwin_schultz_recovers_a_known_spread():
    # simulate a true price with a fixed proportional spread bouncing the observed
    # high and low outward by half a spread on each side
    rng = np.random.default_rng(5)
    n = 4000
    true_spread = 0.004  # 40bp
    mid = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    intraday_range = np.abs(rng.normal(0, 0.01, n))
    high = mid * (1 + intraday_range) * (1 + true_spread / 2)
    low = mid * (1 - intraday_range) * (1 - true_spread / 2)
    est = corwin_schultz_spread(pd.Series(high), pd.Series(low)).mean()
    # the estimator is noisy; it should land in the right order of magnitude
    assert 0.5 * true_spread < est < 2.0 * true_spread


def test_round_trip_cost_increases_with_participation():
    c_small = round_trip_cost_bps(1.0, 0.01, 0.001)
    c_large = round_trip_cost_bps(1.0, 0.01, 0.10)
    assert c_large > c_small


def test_round_trip_cost_charges_full_spread_both_sides():
    # zero volatility and zero fees isolates the spread term: half-spread twice
    p = CostParams(fee_bps=0.0)
    assert round_trip_cost_bps(10.0, 0.0, 0.0, p) == pytest.approx(10.0)


def test_apply_costs_only_charges_on_trades():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    gross = pd.Series([0.01, 0.0, -0.01, 0.0, 0.02], index=idx)
    traded = pd.Series([1, 0, 1, 0, 1], index=idx)
    out = apply_costs(gross, spread_bps=10.0, sigma_daily=0.01,
                      participation=0.001, traded=traded)
    assert (out.loc[traded == 0, "cost"] == 0).all()
    assert (out.loc[traded == 1, "cost"] > 0).all()
    assert (out["net"] <= out["gross"]).all()


def test_cost_summary_reports_both_gross_and_net():
    idx = pd.date_range("2020-01-01", periods=200, freq="B")
    rng = np.random.default_rng(6)
    gross = pd.Series(rng.normal(0.0005, 0.005, 200), index=idx)
    out = apply_costs(gross, 5.0, 0.01, 0.001)
    s = cost_summary(out)
    assert s["net_mean_bps"] < s["gross_mean_bps"]
    assert set(["gross_sharpe_ann", "net_sharpe_ann", "gross_t", "net_t"]) <= set(s)


# ------------------------------------------------------------------ pit corpus

def test_as_of_query_hides_future_documents():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("old covenant text", known_from="2020-01-01", doc_id="old")
        c.add("future filing text", known_from="2023-01-01", doc_id="new")
        got = {x.doc_id for x in c.as_of("2021-06-01")}
        assert got == {"old"}
        assert {x.doc_id for x in c.as_of("2024-01-01")} == {"old", "new"}


def test_binding_only_requires_valid_from():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("announced but not yet in force", known_from="2020-01-01",
              valid_from="2022-01-01", doc_id="pending")
        assert c.as_of("2021-01-01", binding_only=True) == []
        assert len(c.as_of("2022-06-01", binding_only=True)) == 1


def test_unlocatable_clause_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("the issuer shall not incur additional indebtedness",
              known_from="2020-01-01", doc_id="doc1")
        c.add_clause("doc1", "shall not incur additional indebtedness")
        with pytest.raises(ValueError):
            c.add_clause("doc1", "the trustee may accelerate at its discretion")


def test_recognition_lag_is_stored():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("body", known_from="2020-01-01", doc_id="d1")
        c.mark_recognised("d1", "2020-03-01")
        lags = c.recognition_lags()
        assert len(lags) == 1
        assert lags[0]["lag_days"] == pytest.approx(60, abs=1)


def test_assert_no_lookahead_raises():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("future", known_from="2025-01-01", doc_id="f")
        with pytest.raises(ValueError):
            c.assert_no_lookahead("2020-01-01", c.as_of("2026-01-01"))


def test_fts_search_is_as_of_filtered():
    with tempfile.TemporaryDirectory() as d:
        c = PITCorpus(Path(d) / "c.sqlite")
        c.add("mandatory redemption upon ratings downgrade", known_from="2019-01-01",
              doc_id="a", title="indenture")
        c.add("mandatory redemption upon ratings downgrade", known_from="2024-01-01",
              doc_id="b", title="later indenture")
        assert {x.doc_id for x in c.search("downgrade", as_of="2020-01-01")} == {"a"}


# ------------------------------------------------------------------ inference families

def test_link_requires_family():
    with pytest.raises(ValueError):
        Link(link_id="l1", event_id="e1", family="", destination="XYZ")


def test_verified_link_requires_document_and_clause():
    with pytest.raises(ValueError):
        Link(link_id="l1", event_id="e1", family=InferenceFamily.COVENANT_FORCED_SALE,
             destination="XYZ", verified=True)


def test_quarantined_links_are_recorded_not_dropped():
    with tempfile.TemporaryDirectory() as d:
        reg = LinkRegistry(Path(d) / "links.jsonl")
        reg.add(Link(link_id="l1", event_id="e1",
                     family=InferenceFamily.COVENANT_FORCED_SALE,
                     destination="AAA", verified=True, doc_id="d1", clause_id="c1"))
        reg.quarantine(
            Link(link_id="l2", event_id="e1",
                 family=InferenceFamily.COVENANT_FORCED_SALE, destination="BBB"),
            reason="clause not locatable in retrieved document",
        )
        q = reg.quarantine_rate()
        assert q["n_links"] == 2 and q["n_quarantined"] == 1
        assert q["rate"] == pytest.approx(0.5)
        assert len(reg.active()) == 1


def test_effective_breadth_equals_n_for_independent_errors():
    rng = np.random.default_rng(7)
    e = pd.DataFrame(rng.normal(0, 1, (2000, 10)), columns=[f"l{i}" for i in range(10)])
    res = effective_breadth(e)
    assert res["effective_breadth"] == pytest.approx(10, rel=0.25)


def test_effective_breadth_collapses_for_identical_errors():
    rng = np.random.default_rng(8)
    base = rng.normal(0, 1, 2000)
    e = pd.DataFrame({f"l{i}": base + rng.normal(0, 1e-6, 2000) for i in range(10)})
    res = effective_breadth(e)
    assert res["effective_breadth"] == pytest.approx(1, abs=0.2)
    assert res["sizing_overstatement_factor"] == pytest.approx(math.sqrt(10), rel=0.15)


def test_family_correlation_detects_clustering():
    rng = np.random.default_rng(9)
    n = 3000
    fam_a = rng.normal(0, 1, n)
    fam_b = rng.normal(0, 1, n)
    cols, families = {}, {}
    for i in range(4):
        cols[f"a{i}"] = fam_a + rng.normal(0, 0.2, n)
        families[f"a{i}"] = InferenceFamily.COVENANT_FORCED_SALE
    for i in range(4):
        cols[f"b{i}"] = fam_b + rng.normal(0, 0.2, n)
        families[f"b{i}"] = InferenceFamily.INDEX_RULE_DELETION
    res = family_error_correlation(pd.DataFrame(cols), families)
    assert res["mean_within_family_corr"] > 0.9
    assert abs(res["mean_across_family_corr"]) < 0.1
    assert res["n_families"] == 2
    # 8 links, 2 families, errors clustered -> breadth should be near 2, not 8
    assert res["effective_breadth"] < 3.0
    assert "family count" in res["interpretation"]
