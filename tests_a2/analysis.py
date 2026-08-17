"""Test A-2 analysis: does forced flow pay where counterparty scarcity is high?

Runs the pre-registered specification in tests_a2/preregistration.md.
Outputs: tests_a2/results.md, tests_a2/decile_curve.csv
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from nomad.infra.config_logger import ConfigLogger, summarise, trial_count
from nomad.infra.cost_model import (
    CostParams, apply_costs, corwin_schultz_spread, cost_summary, realised_volatility,
    tick_spread_bps,
)
from nomad.infra.deflated_sharpe import deflated_sharpe_ratio, haircut_hurdle_t
from .pipeline import build_panel, reconstruction_validation
from .universe import ADV_WINDOW, N_DECILES

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HURDLE = haircut_hurdle_t()
LOG = ConfigLogger("A2", path=ROOT / "config_log.jsonl")

LIQUID_ADV_THRESHOLD = 1_000_000_000.0   # above this, tick-based spread (preregistration §7.6)
MAX_NOTIONAL = 10_000_000.0
MAX_PARTICIPATION = 0.01


def add_costs_inputs(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-instrument spread estimator, per the pre-registered ADV rule."""
    p = panel.copy()
    rows = []
    for key, g in p.groupby("underlying"):
        g = g.sort_values("date")
        cs = corwin_schultz_spread(g["proxy_high"], g["proxy_low"], window=ADV_WINDOW) * 1e4
        tick = tick_spread_bps(g["proxy_close"], ticks=2.0)
        sigma = realised_volatility(g["proxy_close"], ADV_WINDOW)
        g = g.assign(spread_cs_bps=cs.values, spread_tick_bps=np.asarray(tick),
                     sigma=sigma.values)
        g["use_cs"] = g["adv"] <= LIQUID_ADV_THRESHOLD
        g["spread_bps"] = np.where(g["use_cs"], g["spread_cs_bps"], g["spread_tick_bps"])
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def assign_deciles(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.copy()
    p["decile"] = pd.qcut(p["abs_imb"], N_DECILES, labels=False, duplicates="drop") + 1
    return p


def regress(df: pd.DataFrame, label: str, params: dict, reported: bool = False) -> dict:
    d = df.dropna(subset=["r_on_next", "imb_ratio", "r_proxy", "scale"])
    res = {"label": label, "n_obs": len(d)}
    if len(d) < 100:
        res["note"] = "insufficient observations"
        LOG.log(params, description=label, outcome=res, status="skipped:insufficient_n")
        return res
    X = pd.DataFrame({"imb_ratio": d["imb_ratio"], "r_proxy": d["r_proxy"],
                      "scale": d["scale"]})
    if d["underlying"].nunique() > 1:
        X = pd.concat([X, pd.get_dummies(d["underlying"], prefix="u", drop_first=True,
                                         dtype=float).set_index(X.index)], axis=1)
    X = sm.add_constant(X)
    m = sm.OLS(d["r_on_next"].astype(float), X.astype(float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5})
    res.update({
        "beta": float(m.params["imb_ratio"]), "se": float(m.bse["imb_ratio"]),
        "t_stat": float(m.tvalues["imb_ratio"]),
        "passes_hurdle": bool(abs(float(m.tvalues["imb_ratio"])) > HURDLE),
        "sign_as_predicted": bool(float(m.params["imb_ratio"]) < 0),
        "mean_abs_imb": float(d["abs_imb"].mean()),
        "sd_imb": float(d["imb_ratio"].std(ddof=1)),
        "median_scale": float(d["scale"].median()),
    })
    # Economically-scaled effect (amendment 1). beta is a slope in units of
    # "return per unit imbalance_ratio", and mean |imbalance_ratio| spans three
    # orders of magnitude across deciles, so raw beta shrinks mechanically as
    # imbalance rises and cannot be compared across deciles by eye.
    res["effect_1sd_bps"] = float(res["beta"] * res["sd_imb"] * 1e4)
    res["effect_typical_bps"] = float(res["beta"] * res["mean_abs_imb"] * 1e4)
    LOG.log(params, description=label, outcome=res, reported=reported)
    return res


def gradient_test(panel: pd.DataFrame) -> dict:
    """H2: pooled interaction of imbalance_ratio with decile rank."""
    d = panel.dropna(subset=["r_on_next", "imb_ratio", "r_proxy", "scale", "decile"])
    X = pd.DataFrame({
        "imb_ratio": d["imb_ratio"],
        "imb_x_rank": d["imb_ratio"] * d["decile"],
        "r_proxy": d["r_proxy"], "scale": d["scale"], "decile": d["decile"].astype(float),
    })
    X = pd.concat([X, pd.get_dummies(d["underlying"], prefix="u", drop_first=True,
                                     dtype=float).set_index(X.index)], axis=1)
    X = sm.add_constant(X)
    m = sm.OLS(d["r_on_next"].astype(float), X.astype(float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5})
    out = {
        "beta_base": float(m.params["imb_ratio"]),
        "beta_gradient": float(m.params["imb_x_rank"]),
        "t_gradient": float(m.tvalues["imb_x_rank"]),
        "n_obs": len(d),
        "gradient_significant": bool(abs(float(m.tvalues["imb_x_rank"])) > HURDLE),
        "gradient_direction_as_predicted": bool(float(m.params["imb_x_rank"]) < 0),
    }
    LOG.log({"test": "A2", "statistic": "decile_rank_interaction"},
            description="H2 gradient: pooled interaction", outcome=out, reported=True)
    return out


def spearman_gradient(curve: pd.DataFrame, n_perm: int = 10_000, seed: int = 0) -> dict:
    c = curve.dropna(subset=["beta"])
    if len(c) < 5:
        return {"note": "too few deciles"}
    rho = float(stats.spearmanr(c["decile"], c["beta"]).statistic)
    rng = np.random.default_rng(seed)
    b = c["beta"].values
    null = np.array([stats.spearmanr(c["decile"].values, rng.permutation(b)).statistic
                     for _ in range(n_perm)])
    p = float((np.abs(null) >= abs(rho)).mean())
    out = {"spearman_rho": rho, "permutation_p": p, "n_deciles": len(c),
           "n_permutations": n_perm, "seed": seed}
    LOG.log({"test": "A2", "statistic": "spearman_decile_beta"},
            description="H2 gradient: Spearman with permutation p", outcome=out, reported=True)
    return out


def top_decile_strategy(panel: pd.DataFrame, decile: int = N_DECILES,
                        reported: bool = True) -> dict:
    """Fade the flow in the highest-imbalance decile only."""
    d = panel[panel["decile"] == decile].dropna(
        subset=["r_on_next", "imb_ratio", "sigma", "adv", "spread_bps"]).copy()
    if len(d) < 60:
        out = {"note": "insufficient observations", "n_obs": len(d)}
        LOG.log({"test": "A2", "strategy": "fade_top_decile"}, description="top-decile strategy",
                outcome=out, status="skipped:insufficient_n")
        return out

    d["notional"] = np.minimum(MAX_NOTIONAL, MAX_PARTICIPATION * d["adv"])
    d["participation"] = d["notional"] / d["adv"]
    d["gross"] = -np.sign(d["imb_ratio"]) * d["r_on_next"]

    idx = pd.MultiIndex.from_frame(d[["date", "underlying"]])
    costed = apply_costs(
        pd.Series(d["gross"].values, index=idx),
        spread_bps=pd.Series(d["spread_bps"].values, index=idx),
        sigma_daily=pd.Series(d["sigma"].values, index=idx),
        participation=pd.Series(d["participation"].values, index=idx),
        traded=pd.Series(1.0, index=idx),
        params=CostParams(),
    )
    s = cost_summary(costed)
    daily = costed.reset_index()
    daily["date"] = d["date"].values
    dly = daily.groupby("date")[["gross", "net"]].mean()

    out = {
        "n_positions": len(d), "n_days": len(dly),
        "gross_mean_bps": float(dly["gross"].mean() * 1e4),
        "net_mean_bps": float(dly["net"].mean() * 1e4),
        "gross_t": _t(dly["gross"]), "net_t": _t(dly["net"]),
        "gross_sharpe_ann": _sharpe(dly["gross"]), "net_sharpe_ann": _sharpe(dly["net"]),
        "mean_cost_bps": s["mean_cost_bps"],
        "mean_participation_pct": float(d["participation"].mean() * 100),
        "median_notional_usd": float(d["notional"].median()),
        "net_passes_hurdle": bool(abs(_t(dly["net"])) > HURDLE),
    }
    LOG.log({"test": "A2", "strategy": "fade_top_decile", "decile": decile,
             "max_notional": MAX_NOTIONAL, "max_participation": MAX_PARTICIPATION},
            description="top-decile fade strategy", outcome=out, reported=reported)
    return {**out, "daily": dly}


def _t(x) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def _sharpe(x, ppy: int = 252) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(ppy))


def main() -> None:
    print("Building A-2 panel...")
    panel, diag = build_panel()
    panel = add_costs_inputs(panel)
    panel = assign_deciles(panel)
    print(f"\nPanel: {len(panel):,} underlying-days, "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}, "
          f"{panel['underlying'].nunique()} underlyings")

    print("\nReconstruction validation (ProShares, quarterly anchors vs truth):")
    recon = reconstruction_validation()
    print(recon.to_string(index=False))

    print("\nPer-decile regressions...")
    rows = []
    for dec, g in panel.groupby("decile"):
        r = regress(g, f"decile {int(dec)}", {"test": "A2", "subsample": "decile",
                                              "decile": int(dec)})
        rows.append({"decile": int(dec), "beta": r.get("beta"), "se": r.get("se"),
                     "t_stat": r.get("t_stat"), "n_obs": r.get("n_obs"),
                     "mean_abs_imb": r.get("mean_abs_imb"),
                     "sd_imb": r.get("sd_imb"),
                     "effect_1sd_bps": r.get("effect_1sd_bps"),
                     "effect_typical_bps": r.get("effect_typical_bps"),
                     "median_scale": r.get("median_scale")})
        print(f"  d{int(dec):2d}: beta={r.get('beta', float('nan')):>12.5g} "
              f"t={r.get('t_stat', float('nan')):>6.2f} n={r.get('n_obs'):>5}")
    curve = pd.DataFrame(rows).sort_values("decile")
    curve.to_csv(OUT / "decile_curve.csv", index=False)

    top = curve[curve["decile"] == curve["decile"].max()].iloc[0].to_dict()
    print(f"\nH1 top decile: beta={top['beta']:.5g} t={top['t_stat']:.2f}")

    grad = gradient_test(panel)
    print(f"H2 interaction: beta_g={grad['beta_gradient']:.5g} t={grad['t_gradient']:.2f}")
    sp = spearman_gradient(curve)
    print(f"H2 spearman(beta): rho={sp.get('spearman_rho'):.3f} p={sp.get('permutation_p'):.4f}")
    sp_eff = spearman_gradient(curve.rename(columns={"beta": "_b",
                                                     "effect_1sd_bps": "beta"}),
                               )
    sp_eff["basis"] = "effect_1sd_bps (post-hoc, amendment 1)"
    LOG.log({"test": "A2", "statistic": "spearman_decile_effect_posthoc"},
            description="H2 gradient on economically-scaled effect (post-hoc)",
            outcome=sp_eff, reported=True)
    print(f"H2 spearman(effect): rho={sp_eff.get('spearman_rho'):.3f} "
          f"p={sp_eff.get('permutation_p'):.4f}")

    print("\nPooled and control/thin splits...")
    pooled = regress(panel, "pooled all", {"test": "A2", "subsample": "pooled"}, reported=True)
    thin = regress(panel[~panel["control"]], "thin underlyings only",
                   {"test": "A2", "subsample": "thin"}, reported=True)
    ctrl = regress(panel[panel["control"]], "index controls only",
                   {"test": "A2", "subsample": "control"}, reported=True)
    ex2020 = regress(panel[panel["year"] > 2020], "excluding 2020",
                     {"test": "A2", "subsample": "ex2020"}, reported=True)
    for nm, r in (("pooled", pooled), ("thin", thin), ("control", ctrl), ("ex2020", ex2020)):
        print(f"  {nm:8s} beta={r.get('beta', float('nan')):>12.5g} "
              f"t={r.get('t_stat', float('nan')):>6.2f} n={r.get('n_obs')}")

    print("\nTop-decile strategy...")
    strat = top_decile_strategy(panel)
    if "gross_mean_bps" in strat:
        print(f"  gross {strat['gross_mean_bps']:.2f}bps t={strat['gross_t']:.2f} | "
              f"net {strat['net_mean_bps']:.2f}bps t={strat['net_t']:.2f} | "
              f"cost {strat['mean_cost_bps']:.2f}bps | "
              f"participation {strat['mean_participation_pct']:.2f}%")

    dsr = None
    if "daily" in strat:
        dsr = deflated_sharpe_ratio(strat["daily"]["net"].values,
                                    n_trials=trial_count(ROOT / "config_log.jsonl"),
                                    log_path=ROOT / "config_log.jsonl")
        print(f"\nCumulative DSR: trials={dsr.n_trials} DSR={dsr.deflated_sharpe:.4f}")

    from .report import render
    render(OUT / "results.md", panel, diag, recon, curve, top, grad, sp, sp_eff,
           {"pooled": pooled, "thin": thin, "control": ctrl, "ex2020": ex2020},
           strat, dsr, summarise(ROOT / "config_log.jsonl"))
    print(f"\nWrote {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
