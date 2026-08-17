"""Transaction cost model (spec section 5.4 and 1.5).

Half-spread crossed on entry and on exit, plus a square-root market impact term
parameterised by participation rate (order size / ADV) and volatility.

Every return figure in this project passes through `apply_costs`. A gross-only
number is not a result.

Spreads are estimated from daily high/low via Corwin & Schultz (2012), "A Simple
Way to Estimate Bid-Ask Spreads from Daily High and Low Prices", Journal of
Finance 67(2), rather than assumed, so the cost side is measured on the same data
as the return side. A caller may override with a known spread.

The square-root impact law follows the standard form

    impact = eta * sigma_daily * sqrt(Q / ADV)

with eta an instrument-independent constant. Published calibrations put eta in
roughly 0.3-1.0; the default here is 1.0, the conservative end, because the
hypothesis under test is a flow-driven edge and understating its cost would
flatter it.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

DEFAULT_IMPACT_ETA = 1.0
_CS_K = 3.0 - 2.0 * np.sqrt(2.0)


@dataclass
class CostParams:
    impact_eta: float = DEFAULT_IMPACT_ETA
    spread_floor_bps: float = 0.5      # no instrument trades tighter than this in practice
    spread_cap_bps: float = 500.0      # guards against degenerate Corwin-Schultz output
    fee_bps: float = 0.5               # commission / exchange fees per side
    participation_cap: float = 0.10    # order sizes above 10% of ADV are flagged, not silently priced

    def to_dict(self) -> dict:
        return asdict(self)


def corwin_schultz_spread(high: pd.Series, low: pd.Series, window: int | None = None) -> pd.Series:
    """Effective proportional spread estimated from consecutive daily high/low pairs.

    Returns a series in *fractional* units (0.0001 == 1bp). Negative estimates are
    set to zero as the original paper recommends; if `window` is given the result
    is a rolling mean of the daily estimates, which is what the paper actually
    advises using since the single-pair estimator is very noisy.
    """
    h = pd.to_numeric(high, errors="coerce")
    l = pd.to_numeric(low, errors="coerce")

    hl = np.log(h / l) ** 2
    beta = hl + hl.shift(-1)

    h2 = pd.concat([h, h.shift(-1)], axis=1).max(axis=1)
    l2 = pd.concat([l, l.shift(-1)], axis=1).min(axis=1)
    gamma = np.log(h2 / l2) ** 2

    alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / _CS_K - np.sqrt(gamma / _CS_K)
    spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    spread = spread.where(np.isfinite(spread))
    spread = spread.clip(lower=0.0)

    if window:
        spread = spread.rolling(window, min_periods=max(2, window // 4)).mean()
    return spread


def realised_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    """Daily return volatility, used as the sigma in the impact term."""
    r = pd.to_numeric(close, errors="coerce").pct_change()
    return r.rolling(window, min_periods=max(2, window // 4)).std()


@dataclass
class CostBreakdown:
    spread_cost_bps: float
    impact_cost_bps: float
    fee_bps: float
    total_bps: float

    def to_dict(self) -> dict:
        return asdict(self)


def round_trip_cost_bps(
    spread_bps: float | np.ndarray | pd.Series,
    sigma_daily: float | np.ndarray | pd.Series,
    participation: float | np.ndarray | pd.Series,
    params: CostParams | None = None,
) -> pd.Series | float:
    """Total round-trip cost in basis points.

    spread_bps    -- quoted proportional spread, in bps
    sigma_daily   -- daily return standard deviation, fractional
    participation -- order notional / dollar ADV, fractional

    Cost = half-spread on entry + half-spread on exit  (== one full spread)
           + sqrt impact on entry + sqrt impact on exit
           + fees both sides.
    """
    p = params or CostParams()

    spread = np.clip(np.asarray(spread_bps, dtype=float), p.spread_floor_bps, p.spread_cap_bps)
    sigma = np.asarray(sigma_daily, dtype=float)
    part = np.clip(np.asarray(participation, dtype=float), 0.0, None)

    # half-spread twice == one full spread
    spread_cost = spread
    impact_one_way_bps = p.impact_eta * sigma * np.sqrt(part) * 1e4
    impact_cost = 2.0 * impact_one_way_bps
    fees = 2.0 * p.fee_bps

    total = spread_cost + impact_cost + fees

    if isinstance(spread_bps, pd.Series):
        return pd.Series(total, index=spread_bps.index, name="round_trip_cost_bps")
    if isinstance(sigma_daily, pd.Series):
        return pd.Series(total, index=sigma_daily.index, name="round_trip_cost_bps")
    return float(total) if np.ndim(total) == 0 else total


def apply_costs(
    gross_returns: pd.Series,
    spread_bps: pd.Series | float,
    sigma_daily: pd.Series | float,
    participation: pd.Series | float,
    traded: pd.Series | None = None,
    params: CostParams | None = None,
) -> pd.DataFrame:
    """Net a gross return stream.

    `traded` is a 0/1 (or fractional turnover) series marking observations on
    which a round trip actually occurred; where it is 0 no cost is charged. If
    omitted every non-zero gross return is assumed to be a full round trip.
    """
    p = params or CostParams()
    gross = pd.to_numeric(gross_returns, errors="coerce")

    def _align(x, name):
        if isinstance(x, pd.Series):
            return x.reindex(gross.index)
        return pd.Series(float(x), index=gross.index, name=name)

    spread = _align(spread_bps, "spread_bps")
    sigma = _align(sigma_daily, "sigma")
    part = _align(participation, "participation")

    if traded is None:
        traded = (gross.fillna(0.0) != 0.0).astype(float)
    else:
        traded = traded.reindex(gross.index).fillna(0.0).astype(float)

    cost_bps = round_trip_cost_bps(spread, sigma, part, p)
    cost = (cost_bps / 1e4) * traded

    out = pd.DataFrame(
        {
            "gross": gross,
            "cost": cost,
            "net": gross - cost,
            "cost_bps": cost_bps,
            "traded": traded,
            "participation": part,
            "spread_bps": spread,
            "over_participation_cap": part > p.participation_cap,
        }
    )
    return out


def cost_summary(costed: pd.DataFrame, periods_per_year: int = 252) -> dict:
    g = costed["gross"].dropna()
    n = costed["net"].dropna()
    trades = float(costed["traded"].sum())

    def _sr(x):
        return float(x.mean() / x.std(ddof=1) * np.sqrt(periods_per_year)) if len(x) > 1 and x.std(ddof=1) > 0 else float("nan")

    def _t(x):
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 1 and x.std(ddof=1) > 0 else float("nan")

    return {
        "n_obs": int(len(n)),
        "n_trades": trades,
        "gross_mean_bps": float(g.mean() * 1e4) if len(g) else float("nan"),
        "net_mean_bps": float(n.mean() * 1e4) if len(n) else float("nan"),
        "gross_sharpe_ann": _sr(g),
        "net_sharpe_ann": _sr(n),
        "gross_t": _t(g),
        "net_t": _t(n),
        "mean_cost_bps": float(costed.loc[costed["traded"] > 0, "cost_bps"].mean()) if trades else 0.0,
        "gross_total_return": float((1 + g).prod() - 1) if len(g) else float("nan"),
        "net_total_return": float((1 + n).prod() - 1) if len(n) else float("nan"),
        "obs_over_participation_cap": int(costed["over_participation_cap"].sum()),
    }
