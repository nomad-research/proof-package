"""Deflated Sharpe Ratio and Probability of Backtest Overfitting (spec section 5.2).

Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio: Correcting for
Selection Bias, Backtest Overfitting and Non-Normality", Journal of Portfolio
Management 40(5).

Bailey, Borwein, Lopez de Prado & Zhu (2016), "The Probability of Backtest
Overfitting", Journal of Computational Finance 20(4) -- CSCV method.

The trial count N is read from config_log.jsonl rather than passed by hand, so
the deflation cannot quietly be computed against a smaller denominator than the
number of evaluations actually run.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, asdict
from typing import Sequence

import numpy as np
from scipy import stats

from .config_logger import DEFAULT_LOG, trial_count, trial_sharpes

EULER_MASCHERONI = 0.5772156649015329


@dataclass
class SharpeStats:
    sharpe: float          # per-observation (not annualised)
    n_obs: int
    skew: float
    kurtosis: float        # non-excess (normal == 3)

    def annualised(self, periods_per_year: int = 252) -> float:
        return self.sharpe * math.sqrt(periods_per_year)


def sharpe_stats(returns: Sequence[float]) -> SharpeStats:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if r.size < 2 or r.std(ddof=1) == 0:
        return SharpeStats(sharpe=0.0, n_obs=int(r.size), skew=0.0, kurtosis=3.0)
    return SharpeStats(
        sharpe=float(r.mean() / r.std(ddof=1)),
        n_obs=int(r.size),
        skew=float(stats.skew(r, bias=False)),
        kurtosis=float(stats.kurtosis(r, fisher=False, bias=False)),
    )


def expected_max_sharpe(n_trials: int, sharpe_variance: float) -> float:
    """E[max SR] under the null that every trial has true SR == 0.

    Bailey & Lopez de Prado eq. for SR*: the expected maximum of N independent
    draws, approximated via the Gumbel limit.
    """
    if n_trials < 2:
        return 0.0
    sd = math.sqrt(max(sharpe_variance, 0.0))
    if sd == 0.0:
        return 0.0
    g = EULER_MASCHERONI
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return sd * ((1.0 - g) * z1 + g * z2)


def probabilistic_sharpe_ratio(st: SharpeStats, benchmark_sr: float = 0.0) -> float:
    """PSR: P(true SR > benchmark), adjusting for skew and kurtosis.

    All Sharpe inputs are per-observation, matching st.sharpe.
    """
    if st.n_obs < 3:
        return float("nan")
    denom = 1.0 - st.skew * st.sharpe + ((st.kurtosis - 1.0) / 4.0) * st.sharpe ** 2
    if denom <= 0:
        return float("nan")
    z = (st.sharpe - benchmark_sr) * math.sqrt(st.n_obs - 1) / math.sqrt(denom)
    return float(stats.norm.cdf(z))


@dataclass
class DSRResult:
    deflated_sharpe: float          # probability the true SR exceeds the selection-bias hurdle
    probabilistic_sharpe: float     # PSR against SR == 0, no selection adjustment
    sharpe_per_obs: float
    sharpe_annualised: float
    expected_max_sharpe: float      # SR*, the hurdle
    n_trials: int
    n_obs: int
    skew: float
    kurtosis: float
    sharpe_variance_source: str

    def passes(self, threshold: float = 0.95) -> bool:
        return self.deflated_sharpe > threshold

    def to_dict(self) -> dict:
        return asdict(self)


def deflated_sharpe_ratio(
    returns: Sequence[float],
    *,
    n_trials: int | None = None,
    sharpe_variance: float | None = None,
    log_path=DEFAULT_LOG,
    test: str | None = None,
    periods_per_year: int = 252,
) -> DSRResult:
    """Deflated Sharpe Ratio for a return stream.

    n_trials defaults to the number of evaluations in config_log.jsonl.
    sharpe_variance defaults to the observed variance of logged trial Sharpes; if
    fewer than two are available it falls back to the analytic variance of an
    estimated Sharpe under the null, 1/(n_obs-1), which is the conservative
    substitute Bailey & Lopez de Prado suggest when the trial distribution is
    unavailable.
    """
    st = sharpe_stats(returns)

    if n_trials is None:
        n_trials = max(trial_count(log_path, test=test), 1)

    if sharpe_variance is None:
        observed = trial_sharpes(log_path, test=test)
        if len(observed) >= 2:
            sharpe_variance = float(np.var(observed, ddof=1))
            source = f"variance of {len(observed)} logged trial sharpes"
        else:
            sharpe_variance = 1.0 / max(st.n_obs - 1, 1)
            source = "analytic 1/(n_obs-1) fallback; <2 logged trial sharpes"
    else:
        source = "caller supplied"

    sr_star = expected_max_sharpe(n_trials, sharpe_variance)
    dsr = probabilistic_sharpe_ratio(st, benchmark_sr=sr_star)
    psr = probabilistic_sharpe_ratio(st, benchmark_sr=0.0)

    return DSRResult(
        deflated_sharpe=dsr,
        probabilistic_sharpe=psr,
        sharpe_per_obs=st.sharpe,
        sharpe_annualised=st.annualised(periods_per_year),
        expected_max_sharpe=sr_star,
        n_trials=n_trials,
        n_obs=st.n_obs,
        skew=st.skew,
        kurtosis=st.kurtosis,
        sharpe_variance_source=source,
    )


def probability_of_backtest_overfitting(
    returns_matrix: np.ndarray,
    n_splits: int = 10,
    max_combinations: int | None = 5000,
) -> dict:
    """CSCV probability of backtest overfitting.

    returns_matrix: shape (T observations, N strategy configurations).

    Splits the sample into n_splits contiguous blocks, takes every balanced
    combination of blocks as in-sample, selects the best config in-sample, and
    records its relative rank out-of-sample. PBO is the share of combinations in
    which the in-sample winner lands in the bottom half out-of-sample.
    """
    M = np.asarray(returns_matrix, dtype=float)
    if M.ndim != 2 or M.shape[1] < 2:
        return {"pbo": float("nan"), "n_combinations": 0,
                "note": "needs >= 2 configurations"}

    T, N = M.shape
    if n_splits % 2 != 0:
        n_splits += 1
    if T < n_splits * 2:
        return {"pbo": float("nan"), "n_combinations": 0,
                "note": f"needs >= {n_splits * 2} observations, has {T}"}

    blocks = np.array_split(np.arange(T), n_splits)
    half = n_splits // 2
    combos = list(itertools.combinations(range(n_splits), half))
    if max_combinations is not None and len(combos) > max_combinations:
        rng = np.random.default_rng(0)  # fixed seed: the subsample must be reproducible
        idx = rng.choice(len(combos), size=max_combinations, replace=False)
        combos = [combos[i] for i in sorted(idx)]

    logits = []
    n_below = 0
    for c in combos:
        is_idx = np.concatenate([blocks[i] for i in c])
        oos_idx = np.concatenate([blocks[i] for i in range(n_splits) if i not in c])

        is_sr = _sharpe_columns(M[is_idx])
        oos_sr = _sharpe_columns(M[oos_idx])
        if not np.isfinite(is_sr).any() or not np.isfinite(oos_sr).any():
            continue

        best = int(np.nanargmax(is_sr))
        # relative rank of the in-sample winner among out-of-sample results
        rank = float(stats.rankdata(oos_sr)[best]) / (N + 1)
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(math.log(rank / (1 - rank)))
        if rank < 0.5:
            n_below += 1

    if not logits:
        return {"pbo": float("nan"), "n_combinations": 0, "note": "no usable combinations"}

    return {
        "pbo": n_below / len(logits),
        "median_logit": float(np.median(logits)),
        "n_combinations": len(logits),
        "n_configurations": N,
        "n_splits": n_splits,
    }


def _sharpe_columns(block: np.ndarray) -> np.ndarray:
    mu = np.nanmean(block, axis=0)
    sd = np.nanstd(block, axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sr = np.where(sd > 0, mu / sd, np.nan)
    return sr


def haircut_hurdle_t() -> float:
    """Harvey, Liu & Zhu (2016) multiple-testing hurdle used throughout (spec 1.3)."""
    return 2.78
