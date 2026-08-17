"""Test A analysis: does perfectly enumerated forced flow still pay?

Runs the pre-registered specification in tests_a/preregistration.md. Every
evaluation -- including the ones that are not reported -- is appended to
config_log.jsonl, which is the denominator for the multiple-testing correction.

Outputs: tests_a/results.md, tests_a/decay_curve.csv
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import optimize

from nomad.infra.config_logger import ConfigLogger, summarise, trial_count
from nomad.infra.cost_model import (
    CostParams, apply_costs, corwin_schultz_spread, cost_summary, realised_volatility,
    tick_spread_bps,
)
from nomad.infra.deflated_sharpe import deflated_sharpe_ratio, haircut_hurdle_t
from .pipeline import fetch_all_aum, fetch_all_prices, fetch_hourly
from .universe import ADV_WINDOW, FFILL_LIMIT, MIN_FUNDS_PER_DAY, SAMPLE_START, UNIVERSE

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HURDLE = haircut_hurdle_t()

TRADE_NOTIONAL = 10_000_000.0     # preregistration §4.5
THRESHOLD_PCTILES = (50, 80, 90, 95)
HEADLINE_PCTILE = 90
THRESHOLD_WARMUP = 252            # amendment 2

LOG = ConfigLogger("A", path=ROOT / "config_log.jsonl")


# ------------------------------------------------------------------ panel

@dataclass
class PanelBuild:
    panel: pd.DataFrame
    drops: dict


def build_panel() -> PanelBuild:
    aum = fetch_all_aum()
    prices = fetch_all_prices()

    px = {s: g.set_index("date").sort_index() for s, g in prices.groupby("symbol")}
    frames, drops = [], {}

    for u in UNIVERSE:
        idx = px[u.index_symbol]
        etf = px[u.proxy_etf]
        cal = idx.index

        # --- rebalance multiplier M, from t-1 AUM (preregistration §2) ---
        wide = (
            aum[aum["ticker"].isin([f.ticker for f in u.funds])]
            .pivot_table(index="date", columns="ticker", values="aum")
            .reindex(cal)
            .ffill(limit=FFILL_LIMIT)     # §5 rule 1
            .shift(1)                     # A[t-1]: known before the open of t
        )
        coeffs = pd.Series({f.ticker: f.rebalance_coeff for f in u.funds})
        contrib = wide.mul(coeffs.reindex(wide.columns), axis=1)
        M = contrib.sum(axis=1, min_count=1)
        n_funds = contrib.notna().sum(axis=1)

        # --- prices ---
        r_index = idx["close"].pct_change()
        etf_close, etf_open = etf["close"].reindex(cal), etf["open"].reindex(cal)
        adv = (etf["close"] * etf["volume"]).reindex(cal).shift(1).rolling(
            ADV_WINDOW, min_periods=ADV_WINDOW).median()

        df = pd.DataFrame({
            "underlying": u.key,
            "date": cal,
            "M": M.values,
            "n_funds": n_funds.values,
            "r_index": r_index.values,
            "adv": adv.values,
            "etf_close": etf_close.values,
            "etf_open": etf_open.values,
            "etf_high": etf["high"].reindex(cal).values,
            "etf_low": etf["low"].reindex(cal).values,
        })
        df["r_on_next"] = df["etf_open"].shift(-1) / df["etf_close"] - 1.0
        df["r_id_next"] = df["etf_close"].shift(-1) / df["etf_open"].shift(-1) - 1.0

        # cost inputs, from the proxy ETF's own daily bars (see amendment 3)
        df["spread_cs_bps"] = (corwin_schultz_spread(
            df["etf_high"], df["etf_low"], window=ADV_WINDOW) * 1e4).values
        df["spread_1tick_bps"] = tick_spread_bps(df["etf_close"], ticks=1.0)
        df["spread_2tick_bps"] = tick_spread_bps(df["etf_close"], ticks=2.0)
        df["sigma"] = realised_volatility(df["etf_close"], ADV_WINDOW).values

        n0 = len(df)
        df = df[df["date"] >= SAMPLE_START]
        n1 = len(df)
        df = df[df["n_funds"] >= MIN_FUNDS_PER_DAY]        # §5 rule 2
        n2 = len(df)
        df = df.dropna(subset=["M", "r_index", "adv", "r_on_next",
                               "r_id_next", "etf_close", "etf_open"])   # §5 rule 3
        n3 = len(df)

        drops[u.key] = {
            "before_sample_start": n0 - n1,
            "too_few_funds": n1 - n2,
            "missing_price_or_return": n2 - n3,
            "retained": n3,
        }
        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    panel["scale"] = panel["M"] / panel["adv"]
    panel["imb_ratio"] = panel["M"] * panel["r_index"] / panel["adv"]
    panel["imbalance_usd"] = panel["M"] * panel["r_index"]
    panel["year"] = panel["date"].dt.year
    panel = panel.sort_values(["date", "underlying"]).reset_index(drop=True)
    return PanelBuild(panel, drops)


# ------------------------------------------------------------------ regression

def run_regression(df: pd.DataFrame, dep: str, *, label: str, params: dict,
                   fixed_effects: bool = True, reported: bool = False) -> dict:
    """Pre-registered specification §4.1:

        dep = a[u] + b*imb_ratio + g*r_index + d*scale + e

    b is the coefficient on the interaction scale*r, i.e. the additional reversal
    attributable to LETF size relative to liquidity, net of generic reversal (g).
    """
    d = df.dropna(subset=[dep, "imb_ratio", "r_index", "scale"]).copy()
    result = {"label": label, "dep": dep, "n_obs": len(d)}

    if len(d) < 100:
        result.update({"beta": np.nan, "t_hac": np.nan, "note": "insufficient observations"})
        LOG.log({**params, "dep": dep, "spec": "primary"}, description=label,
                outcome=result, reported=reported, status="skipped:insufficient_n")
        return result

    X = pd.DataFrame({
        "imb_ratio": d["imb_ratio"],
        "r_index": d["r_index"],
        "scale": d["scale"],
    })
    if fixed_effects and d["underlying"].nunique() > 1:
        du = pd.get_dummies(d["underlying"], prefix="u", drop_first=True, dtype=float)
        X = pd.concat([X, du.set_index(X.index)], axis=1)
    X = sm.add_constant(X)
    y = d[dep].astype(float)

    m_hac = sm.OLS(y, X.astype(float)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    m_cl = sm.OLS(y, X.astype(float)).fit(
        cov_type="cluster", cov_kwds={"groups": d["date"].values})

    result.update({
        "beta": float(m_hac.params["imb_ratio"]),
        "se_hac": float(m_hac.bse["imb_ratio"]),
        "t_hac": float(m_hac.tvalues["imb_ratio"]),
        "se_cluster": float(m_cl.bse["imb_ratio"]),
        "t_cluster": float(m_cl.tvalues["imb_ratio"]),
        "gamma_r_index": float(m_hac.params["r_index"]),
        "t_gamma": float(m_hac.tvalues["r_index"]),
        "delta_scale": float(m_hac.params["scale"]),
        "r2": float(m_hac.rsquared),
        "passes_hurdle": bool(abs(float(m_hac.tvalues["imb_ratio"])) > HURDLE),
        "sign_as_predicted": bool(float(m_hac.params["imb_ratio"]) < 0) if dep == "r_on_next" else None,
    })
    LOG.log({**params, "dep": dep, "spec": "primary", "fixed_effects": fixed_effects},
            description=label, outcome=result, reported=reported)
    return result


# ------------------------------------------------------------------ decay curve

def decay_curve(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in panel.groupby("year"):
        res = run_regression(g, "r_on_next", label=f"yearly {year}",
                             params={"subsample": "year", "year": int(year)},
                             fixed_effects=True)
        rows.append({
            "year": int(year), "beta": res.get("beta"), "se": res.get("se_hac"),
            "t_stat": res.get("t_hac"), "n_obs": res.get("n_obs"),
        })
    return pd.DataFrame(rows)


def fit_half_life(curve: pd.DataFrame, n_boot: int = 1000, seed: int = 0) -> dict:
    """Weighted NLS fit of beta[y] = beta0 * exp(-lambda * (y - y0)).

    Reports 'no decay detected' rather than a half-life when lambda <= 0, so a
    strengthening coefficient cannot be dressed up as a long half-life.
    """
    c = curve.dropna(subset=["beta", "se"])
    c = c[c["se"] > 0]
    if len(c) < 4:
        return {"status": "insufficient years", "n_years": len(c)}

    y0 = int(c["year"].min())
    x = (c["year"] - y0).values.astype(float)
    b = c["beta"].values.astype(float)
    w = 1.0 / c["se"].values.astype(float)

    def _fit(xx, bb, ww):
        def resid(p):
            return (bb - p[0] * np.exp(-np.clip(p[1] * xx, -50, 50))) * ww
        p0 = [bb[0] if bb[0] != 0 else np.sign(bb.mean()) * 1e-3, 0.1]
        try:
            sol = optimize.least_squares(resid, p0, bounds=([-np.inf, -2.0], [np.inf, 5.0]),
                                         max_nfev=20000)
            return (float(sol.x[0]), float(sol.x[1])) if sol.success else None
        except Exception:
            return None

    base = _fit(x, b, w)
    if base is None:
        return {"status": "fit did not converge", "n_years": len(c)}
    beta0, lam = base

    rng = np.random.default_rng(seed)
    lams = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(c), len(c))
        r = _fit(x[idx], b[idx], w[idx])
        if r is not None:
            lams.append(r[1])
    lams = np.array(lams)

    out = {
        "status": "fitted", "n_years": len(c), "year_zero": y0,
        "beta0": beta0, "lambda": lam,
        "lambda_ci95": [float(np.percentile(lams, 2.5)), float(np.percentile(lams, 97.5))]
        if len(lams) else None,
        "share_of_bootstraps_with_decay": float((lams > 0).mean()) if len(lams) else None,
    }
    if lam > 0:
        out["half_life_years"] = float(np.log(2) / lam)
        pos = lams[lams > 0]
        if len(pos) > 20:
            hl = np.log(2) / pos
            out["half_life_ci95"] = [float(np.percentile(hl, 2.5)), float(np.percentile(hl, 97.5))]
    else:
        out["half_life_years"] = None
        out["note"] = "lambda <= 0: no decay detected; coefficient is flat or strengthening"

    # A half-life fitted to coefficients that are individually indistinguishable
    # from zero is a half-life of noise. The specification treats this number as
    # potentially more valuable than the trade itself, which makes a spurious one
    # the single most dangerous artefact this test can emit -- so it is flagged
    # here rather than left for the reader to catch.
    n_sig_years = int((c["t_stat"].abs() > HURDLE).sum())
    out["n_significant_years"] = n_sig_years
    out["interpretable"] = bool(n_sig_years > 0)
    if not out["interpretable"]:
        out["interpretation_warning"] = (
            "NOT INTERPRETABLE: no individual year clears the t > 2.78 hurdle, so the fitted "
            "curve is describing the decay of a quantity that was never distinguishable from "
            "zero. Any half-life reported from it is a half-life of noise and must not be used "
            "as the framework's decay clock."
        )

    LOG.log({"analysis": "half_life_fit", "n_boot": n_boot, "seed": seed},
            description="exponential decay fit to yearly betas", outcome=out, reported=True)
    return out


# ------------------------------------------------------------------ strategy

SPREAD_REGIMES = {
    "2tick": "spread_2tick_bps",     # headline (amendment 3)
    "1tick": "spread_1tick_bps",
    "corwin_schultz": "spread_cs_bps",
}
HEADLINE_SPREAD = "2tick"


def run_strategy(panel: pd.DataFrame, pctile: int, spread_regime: str = HEADLINE_SPREAD,
                 reported: bool = False) -> dict:
    """Fade the predicted rebalance flow: enter at close t, exit at open t+1.

    Threshold is an expanding percentile of |imb_ratio| using data through t-1
    only, so the trigger level is point-in-time.
    """
    spread_col = SPREAD_REGIMES[spread_regime]
    p = panel.sort_values(["underlying", "date"]).copy()

    thr = (p.groupby("underlying")["imb_ratio"]
             .transform(lambda s: s.abs().expanding(min_periods=THRESHOLD_WARMUP)
                                  .quantile(pctile / 100.0).shift(1)))
    p["threshold"] = thr
    p["active"] = (p["imb_ratio"].abs() > p["threshold"]) & p["threshold"].notna()
    p["gross"] = np.where(p["active"], -np.sign(p["imb_ratio"]) * p["r_on_next"], 0.0)
    p["participation"] = TRADE_NOTIONAL / p["adv"]

    costed = apply_costs(
        p.set_index(pd.MultiIndex.from_frame(p[["date", "underlying"]]))["gross"],
        spread_bps=pd.Series(p[spread_col].values,
                             index=pd.MultiIndex.from_frame(p[["date", "underlying"]])),
        sigma_daily=pd.Series(p["sigma"].values,
                              index=pd.MultiIndex.from_frame(p[["date", "underlying"]])),
        participation=pd.Series(p["participation"].values,
                                index=pd.MultiIndex.from_frame(p[["date", "underlying"]])),
        traded=pd.Series(p["active"].astype(float).values,
                         index=pd.MultiIndex.from_frame(p[["date", "underlying"]])),
        params=CostParams(),
    ).reset_index()

    costed["date"] = p["date"].values
    costed["year"] = p["year"].values
    costed["active"] = p["active"].values

    # equal-weight across underlyings with an active position that day
    daily = (costed[costed["active"]]
             .groupby("date")[["gross", "net"]].mean()
             .reindex(sorted(panel["date"].unique())).fillna(0.0))

    summary = cost_summary(costed[costed["active"]][["gross", "net", "cost_bps", "traded",
                                                     "participation", "over_participation_cap"]])
    daily_stats = {
        "n_days_traded": int((daily["net"] != 0).sum()),
        "gross_daily_t": _tstat(daily["gross"]),
        "net_daily_t": _tstat(daily["net"]),
        "gross_sharpe_ann": _sharpe(daily["gross"]),
        "net_sharpe_ann": _sharpe(daily["net"]),
        "gross_mean_bps": float(daily["gross"].mean() * 1e4),
        "net_mean_bps": float(daily["net"].mean() * 1e4),
        "mean_cost_bps": summary["mean_cost_bps"],
        "n_positions": int(costed["active"].sum()),
    }
    out = {**daily_stats, "passes_hurdle_net": bool(abs(daily_stats["net_daily_t"]) > HURDLE)}

    LOG.log({"strategy": "fade_letf_rebalance", "pctile": pctile,
             "notional_usd": TRADE_NOTIONAL, "warmup": THRESHOLD_WARMUP,
             "exit": "next_open", "spread_regime": spread_regime},
            description=f"tradeable strategy, {pctile}th percentile trigger, "
                        f"{spread_regime} spreads",
            outcome=out, reported=reported)

    return {**out, "daily": daily, "per_position": costed}


def _tstat(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def _sharpe(x: pd.Series, ppy: int = 252) -> float:
    x = x.dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(ppy))


# ------------------------------------------------------------------ intraday (§4.3, amended)

def intraday_impact_test() -> dict:
    """H-A1 on the ~2 years of hourly bars Yahoo provides.

    Yahoo's hourly bars are stamped at bar open, so the 15:30 bar covers
    15:30->16:00 -- exactly the specification's impact window. The 14:30 bar's
    close is the 15:30 price. See preregistration amendment 1.
    """
    aum = fetch_all_aum()
    all_px = fetch_all_prices()
    rows = []
    for u in UNIVERSE:
        try:
            h = fetch_hourly(u.index_symbol)
        except Exception as e:
            LOG.log({"analysis": "intraday_impact", "underlying": u.key},
                    description="hourly fetch failed", outcome={"error": str(e)},
                    status="failed:fetch")
            continue

        piv = h.pivot_table(index="date", columns="hour", values="close")
        if 14 not in piv.columns or 15 not in piv.columns:
            continue
        px_1530 = piv[14]      # close of the 14:30 bar == price at 15:30
        px_1600 = piv[15]      # close of the 15:30 bar == the 16:00 close
        prev_close = px_1600.shift(1)

        wide = (aum[aum["ticker"].isin([f.ticker for f in u.funds])]
                .pivot_table(index="date", columns="ticker", values="aum")
                .reindex(piv.index).ffill(limit=FFILL_LIMIT).shift(1))
        coeffs = pd.Series({f.ticker: f.rebalance_coeff for f in u.funds})
        M = wide.mul(coeffs.reindex(wide.columns), axis=1).sum(axis=1, min_count=MIN_FUNDS_PER_DAY)

        etf = all_px[all_px["symbol"] == u.proxy_etf].set_index("date")
        adv = (etf["close"] * etf["volume"]).reindex(piv.index).shift(1).rolling(
            ADV_WINDOW, min_periods=ADV_WINDOW).median()

        r_partial = px_1530 / prev_close - 1.0
        r_last30 = px_1600 / px_1530 - 1.0
        rows.append(pd.DataFrame({
            "underlying": u.key, "date": piv.index,
            "r_partial": r_partial.values, "r_last30": r_last30.values,
            "scale": (M / adv).values,
            "imb_ratio_partial": (M * r_partial / adv).values,
        }))

    if not rows:
        return {"status": "no intraday data"}

    d = pd.concat(rows, ignore_index=True).dropna()
    if len(d) < 100:
        return {"status": "insufficient intraday observations", "n_obs": len(d)}

    X = sm.add_constant(pd.get_dummies(d["underlying"], prefix="u", drop_first=True, dtype=float)
                        .join(d[["imb_ratio_partial", "r_partial", "scale"]]))
    m = sm.OLS(d["r_last30"].astype(float), X.astype(float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5})

    out = {
        "status": "run", "n_obs": int(len(d)),
        "window": "15:30->16:00", "period": f"{d['date'].min().date()} to {d['date'].max().date()}",
        "beta": float(m.params["imb_ratio_partial"]),
        "se": float(m.bse["imb_ratio_partial"]),
        "t_stat": float(m.tvalues["imb_ratio_partial"]),
        "sign_as_predicted": bool(float(m.params["imb_ratio_partial"]) > 0),
        "passes_hurdle": bool(abs(float(m.tvalues["imb_ratio_partial"])) > HURDLE),
        "underpowered": True,
    }
    LOG.log({"analysis": "intraday_impact", "window": "1530_1600"},
            description="H-A1 late-day impact, hourly bars", outcome=out, reported=True)
    return out


# ------------------------------------------------------------------ main

def main() -> None:
    print("Building panel...")
    pb = build_panel()
    panel = pb.panel
    print(f"  {len(panel)} underlying-days, "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}")

    print("\nPrimary regression (H-A2, overnight reversal)...")
    primary = run_regression(panel, "r_on_next", label="PRIMARY pooled overnight reversal",
                             params={"subsample": "full", "sample": "primary_4_underlyings"},
                             reported=True)
    print(f"  beta={primary['beta']:.6g}  t_HAC={primary['t_hac']:.2f}  "
          f"t_cluster={primary['t_cluster']:.2f}  n={primary['n_obs']}")

    print("\nSecondary regression (next-day intraday)...")
    secondary = run_regression(panel, "r_id_next", label="SECONDARY next-day intraday",
                               params={"subsample": "full", "sample": "primary_4_underlyings"},
                               reported=True)
    print(f"  beta={secondary['beta']:.6g}  t_HAC={secondary['t_hac']:.2f}")

    print("\nPer-underlying (secondary)...")
    per_underlying = {}
    for key, g in panel.groupby("underlying"):
        r = run_regression(g, "r_on_next", label=f"per-underlying {key}",
                           params={"subsample": "underlying", "underlying": key},
                           fixed_effects=False)
        per_underlying[key] = r
        print(f"  {key}: beta={r['beta']:.6g} t={r['t_hac']:.2f} n={r['n_obs']}")

    print("\nDecay curve...")
    curve = decay_curve(panel)

    print("\nStrategy...")
    strategies = {}
    for p in THRESHOLD_PCTILES:
        strategies[p] = run_strategy(panel, p, HEADLINE_SPREAD,
                                     reported=(p == HEADLINE_PCTILE))
        s = strategies[p]
        print(f"  p{p}: gross {s['gross_mean_bps']:.2f}bps t={s['gross_daily_t']:.2f} | "
              f"net {s['net_mean_bps']:.2f}bps t={s['net_daily_t']:.2f} | "
              f"cost {s['mean_cost_bps']:.2f}bps | {s['n_positions']} positions")

    print("\nCost sensitivity at the headline trigger...")
    spread_sensitivity = {}
    for regime in SPREAD_REGIMES:
        spread_sensitivity[regime] = run_strategy(
            panel, HEADLINE_PCTILE, regime, reported=(regime == HEADLINE_SPREAD))
        s = spread_sensitivity[regime]
        print(f"  {regime}: cost {s['mean_cost_bps']:.2f}bps | "
              f"net {s['net_mean_bps']:.2f}bps t={s['net_daily_t']:.2f}")

    headline = spread_sensitivity[HEADLINE_SPREAD]
    yearly_pnl = (headline["per_position"][headline["per_position"]["active"]]
                  .groupby("year")[["gross", "net"]].mean() * 1e4)
    curve = curve.merge(
        yearly_pnl.rename(columns={"gross": "gross_mean_bps", "net": "net_mean_bps"}),
        left_on="year", right_index=True, how="left")
    curve.to_csv(OUT / "decay_curve.csv", index=False)
    print(f"\n  wrote {OUT / 'decay_curve.csv'}")

    hl = fit_half_life(curve)
    print(f"  half-life fit: {hl.get('status')} lambda={hl.get('lambda')} "
          f"half_life={hl.get('half_life_years')}")

    print("\nIntraday impact test (H-A1, power-limited)...")
    intraday = intraday_impact_test()
    print(f"  {intraday}")

    print("\nDeflated Sharpe Ratio...")
    dsr = deflated_sharpe_ratio(headline["daily"]["net"].values,
                                log_path=ROOT / "config_log.jsonl", test="A")
    print(f"  trials={dsr.n_trials} SR*={dsr.expected_max_sharpe:.4f} DSR={dsr.deflated_sharpe:.4f}")

    from .report import render
    render(OUT / "results.md", pb, primary, secondary, per_underlying, curve, hl,
           strategies, headline, dsr, intraday, spread_sensitivity,
           log_summary=summarise(ROOT / "config_log.jsonl"),
           n_trials=trial_count(ROOT / "config_log.jsonl", test="A"))
    print(f"\nWrote {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
