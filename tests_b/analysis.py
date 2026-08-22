"""Test B analysis: does the market respond to information that is not new?

Runs the pre-registered specification in tests_b/preregistration.md. Every
evaluation is appended to config_log.jsonl.

Outputs: tests_b/results.md, tests_b/decay_curve.csv
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from nomad.infra.config_logger import ConfigLogger, summarise, trial_count
from nomad.infra.cost_model import CostParams, apply_costs, cost_summary, realised_volatility, tick_spread_bps
from nomad.infra.deflated_sharpe import deflated_sharpe_ratio, haircut_hurdle_t
from tests_a.pipeline import fetch_daily
from .pipeline import fetch_vintage_panel

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HURDLE = haircut_hurdle_t()
LOG = ConfigLogger("B", path=ROOT / "config_log.jsonl")

SPLIT_DATE = pd.Timestamp("2012-01-01")
MIN_TRAIN = 60                 # preregistration §4
TRADE_NOTIONAL = 10_000_000.0
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-12-31"))

# (series, transform) -- how the announced quantity is formed from the vintage
B1 = {"target": ("INDPRO", "logdiff"),
      "predictors": [("AWHMAN", "logdiff"), ("MANEMP", "logdiff")],
      "start": "1997-01-01", "label": "B1_INDPRO"}
B2 = {"target": ("CFNAI", "level"),
      "predictors": [("PAYEMS", "logdiff"), ("INDPRO", "logdiff"),
                     ("UNRATE", "diff"), ("AWHMAN", "logdiff")],
      "start": "2011-01-01", "label": "B2_CFNAI"}


# ------------------------------------------------------------------ vintage → announcement

def announcement_frame(series: str, transform: str) -> pd.DataFrame:
    """Per reference month: the value as first announced, and the date announced.

    Both the current and prior month are read from the *same* vintage, because
    that is the change the release actually reported. Taking the prior month from
    a later vintage would silently mix in revisions that had not happened yet.
    """
    panel = fetch_vintage_panel(series)
    p = panel.dropna(subset=["value"]).copy()
    p["vintage"] = pd.to_datetime(p["vintage"])
    p["obs_date"] = pd.to_datetime(p["obs_date"])

    release = (p.sort_values(["obs_date", "vintage"])
                 .groupby("obs_date", as_index=False)["vintage"].first()
                 .rename(columns={"vintage": "release_date"}))

    piv = p.pivot_table(index="obs_date", columns="vintage", values="value")

    rows = []
    for _, r in release.iterrows():
        m, v = r["obs_date"], r["release_date"]
        prev = m - pd.DateOffset(months=1)
        if v not in piv.columns or m not in piv.index:
            continue
        cur = piv.at[m, v]
        pv = piv.at[prev, v] if prev in piv.index else np.nan
        if not np.isfinite(cur):
            continue
        if transform == "level":
            val = cur
        elif transform == "diff":
            val = cur - pv
        elif transform == "logdiff":
            val = np.log(cur / pv) if (np.isfinite(pv) and pv > 0 and cur > 0) else np.nan
        else:
            raise ValueError(transform)
        rows.append({"obs_date": m, "release_date": v, series: val})

    return pd.DataFrame(rows).dropna(subset=[series])


def build_panel(cfg: dict) -> tuple[pd.DataFrame, dict]:
    tgt, tgt_tf = cfg["target"]
    tgt_df = announcement_frame(tgt, tgt_tf).rename(
        columns={tgt: "y", "release_date": "target_release"})

    drops = {"initial_months": len(tgt_df)}

    df = tgt_df
    for s, tf in cfg["predictors"]:
        pf = announcement_frame(s, tf).rename(columns={"release_date": f"{s}_release"})
        df = df.merge(pf, on="obs_date", how="inner")

    drops["after_predictor_merge"] = len(df)

    # verification, not assumption: every predictor must have been public first
    ok = pd.Series(True, index=df.index)
    for s, _ in cfg["predictors"]:
        ok &= df[f"{s}_release"] < df["target_release"]
    drops["predictor_not_released_first"] = int((~ok).sum())
    df = df[ok].copy()

    df = df[df["target_release"] >= cfg["start"]].sort_values("target_release").reset_index(drop=True)
    drops["after_start_filter"] = len(df)
    return df, drops


# ------------------------------------------------------------------ PIT prediction

def add_predictions(df: pd.DataFrame, cfg: dict, min_train: int | None = None) -> pd.DataFrame:
    """Expanding-window OLS using only months already released at each decision point."""
    min_train = MIN_TRAIN if min_train is None else min_train
    pred_cols = [s for s, _ in cfg["predictors"]]
    d = df.copy()
    d["y_lag1"] = d["y"].shift(1)
    d["y_lag2"] = d["y"].shift(2)
    feats = pred_cols + ["y_lag1", "y_lag2"]
    d = d.dropna(subset=feats + ["y"]).reset_index(drop=True)

    preds = np.full(len(d), np.nan)
    r2s = np.full(len(d), np.nan)
    for i in range(len(d)):
        train = d.iloc[:i]                      # strictly earlier releases only
        if len(train) < min_train:
            continue
        X = sm.add_constant(train[feats].values, has_constant="add")
        beta, *_ = np.linalg.lstsq(X, train["y"].values, rcond=None)
        x = np.concatenate([[1.0], d.loc[i, feats].values.astype(float)])
        preds[i] = float(x @ beta)
        fitted = X @ beta
        ss_res = float(((train["y"].values - fitted) ** 2).sum())
        ss_tot = float(((train["y"].values - train["y"].values.mean()) ** 2).sum())
        r2s[i] = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    d["predicted"] = preds
    d["train_r2"] = r2s
    d["surprise"] = d["y"] - d["predicted"]

    # standardise by expanding statistics through m-1 only
    for c in ("predicted", "surprise"):
        mu = d[c].expanding(min_periods=24).mean().shift(1)
        sd = d[c].expanding(min_periods=24).std().shift(1)
        d[f"{c}_z"] = (d[c] - mu) / sd

    return d


def add_market(d: pd.DataFrame) -> pd.DataFrame:
    spy = fetch_daily("SPY", start="1993-01-01").set_index("date").sort_index()
    spy["ret"] = spy["close"].pct_change()
    spy["sigma"] = realised_volatility(spy["close"], 21)
    spy["adv"] = (spy["close"] * spy["volume"]).shift(1).rolling(21, min_periods=21).median()
    spy["spread_bps"] = tick_spread_bps(spy["close"], ticks=2.0)
    # forward 5-day return from the release close, for the reversal leg
    spy["fwd5"] = spy["close"].shift(-5) / spy["close"] - 1.0
    # Macro releases land at 08:30 ET, before the open. The overnight window
    # (prior close -> release-day open) brackets the announcement; the
    # close-to-close window adds 6.5 hours of unrelated news on top of it.
    spy["ret_on"] = spy["open"] / spy["close"].shift(1) - 1.0

    idx = spy.index
    out = d.copy()
    keep, rec = [], []
    for i, r in out.iterrows():
        rd = pd.Timestamp(r["target_release"]).normalize()
        if rd not in idx:                      # §6 rule 3: no shifting to the next session
            continue
        keep.append(i)
        rec.append({
            "r_rel": spy.at[rd, "ret"], "r_rel_on": spy.at[rd, "ret_on"],
            "fwd5": spy.at[rd, "fwd5"],
            "sigma": spy.at[rd, "sigma"], "adv": spy.at[rd, "adv"],
            "spread_bps": spy.at[rd, "spread_bps"],
        })
    if not rec:
        raise RuntimeError("no release date fell on an equity trading day; check the calendar")
    out = out.loc[keep].reset_index(drop=True)
    for k in rec[0]:
        out[k] = [x[k] for x in rec]
    return out


# ------------------------------------------------------------------ tests

def regress(d: pd.DataFrame, label: str, params: dict, interaction: bool = False,
            reported: bool = False, dep: str = "r_rel") -> dict:
    dd = d.dropna(subset=[dep, "predicted_z", "surprise_z"]).copy()
    res = {"label": label, "n_obs": len(dd), "dep": dep}
    if len(dd) < 40:
        res["note"] = "insufficient observations"
        LOG.log(params, description=label, outcome=res, status="skipped:insufficient_n")
        return res

    X = pd.DataFrame({"predicted_z": dd["predicted_z"], "surprise_z": dd["surprise_z"]})
    if interaction:
        post = (pd.to_datetime(dd["target_release"]) >= SPLIT_DATE).astype(float)
        X["predicted_z_post"] = X["predicted_z"] * post
        X["surprise_z_post"] = X["surprise_z"] * post
        X["post"] = post
    X = sm.add_constant(X)
    m = sm.OLS(dd[dep].astype(float), X.astype(float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 3})

    res.update({
        "b1_predicted": float(m.params["predicted_z"]),
        "t_b1": float(m.tvalues["predicted_z"]),
        "b2_surprise": float(m.params["surprise_z"]),
        "t_b2": float(m.tvalues["surprise_z"]),
        "r2": float(m.rsquared),
        "b1_passes_hurdle": bool(abs(float(m.tvalues["predicted_z"])) > HURDLE),
        "b2_passes_hurdle": bool(abs(float(m.tvalues["surprise_z"])) > HURDLE),
    })
    if interaction:
        res.update({
            "b1_post_interaction": float(m.params["predicted_z_post"]),
            "t_b1_post": float(m.tvalues["predicted_z_post"]),
            "decay_detected": bool(abs(float(m.tvalues["predicted_z_post"])) > HURDLE
                                   and np.sign(m.params["predicted_z_post"]) != np.sign(m.params["predicted_z"])),
        })
    LOG.log(params, description=label, outcome=res, reported=reported)
    return res


def influence_check(d: pd.DataFrame, label: str, params: dict, dep: str = "r_rel") -> dict:
    """How much of the result rests on a handful of observations?

    Refits after dropping the k observations with the largest Cook's distance. A
    coefficient that survives the full sample but collapses when two points are
    removed is leverage, not an effect -- and a macro sample spanning 2020
    contains points with enormous leverage by construction. Added as amendment 2;
    see the pre-registration.
    """
    dd = d.dropna(subset=[dep, "predicted_z", "surprise_z"]).copy()
    if len(dd) < 40:
        return {"note": "insufficient observations"}

    X = sm.add_constant(dd[["predicted_z", "surprise_z"]].astype(float))
    y = dd[dep].astype(float)
    base = sm.OLS(y, X).fit()
    cooks = base.get_influence().cooks_distance[0]
    order = np.argsort(-cooks)

    out = {"t_full": float(sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
                           .tvalues["predicted_z"])}
    for k in (1, 2, 3, 5):
        keep = np.ones(len(dd), dtype=bool)
        keep[order[:k]] = False
        m = sm.OLS(y.values[keep], X.values[keep]).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        out[f"t_drop{k}"] = float(m.tvalues[1])
    out["most_influential_dates"] = [str(pd.Timestamp(dd["target_release"].iloc[i]).date())
                                     for i in order[:3]]
    out["survives_dropping_2"] = bool(abs(out["t_drop2"]) > HURDLE)
    LOG.log({**params, "diagnostic": "influence"}, description=f"{label} influence check",
            outcome=out, reported=True)
    return out


def frontrun_strategy(d: pd.DataFrame, label: str, params: dict,
                      signal: str = "predicted_z", reported: bool = False) -> dict:
    """Position sign(signal) into the release; reverse for 5 days after.

    Two signal definitions are run and both are reported, because the
    pre-registration's `sign(predicted)` is ambiguous between them and they mean
    different things:

    `predicted`   -- the raw predicted growth rate. Industrial production grows in
                     most months, so its sign is almost always +1 and the
                     resulting strategy is a long-only equity position dressed up
                     as a signal. Any profit it shows is the equity risk premium.
    `predicted_z` -- predicted growth relative to its own trailing mean. This is
                     the demeaned version and the economically meaningful one; it
                     is the headline.
    """
    dd = d.dropna(subset=["r_rel", signal, "sigma", "adv", "spread_bps"]).copy()
    if len(dd) < 40:
        out = {"note": "insufficient observations", "n_obs": len(dd)}
        LOG.log({**params, "signal": signal}, description=label, outcome=out,
                status="skipped:insufficient_n")
        return out

    dd["gross"] = np.sign(dd[signal]) * dd["r_rel"]
    dd["participation"] = TRADE_NOTIONAL / dd["adv"]
    costed = apply_costs(dd.set_index("obs_date")["gross"],
                         spread_bps=pd.Series(dd["spread_bps"].values, index=dd["obs_date"]),
                         sigma_daily=pd.Series(dd["sigma"].values, index=dd["obs_date"]),
                         participation=pd.Series(dd["participation"].values, index=dd["obs_date"]),
                         traded=pd.Series(1.0, index=dd["obs_date"]),
                         params=CostParams())
    s = cost_summary(costed, periods_per_year=12)

    rev = dd.dropna(subset=["fwd5"])
    rev_gross = (-np.sign(rev[signal]) * rev["fwd5"])

    out = {
        "n_events": len(dd),
        "gross_mean_bps": float(dd["gross"].mean() * 1e4),
        "net_mean_bps": float(costed["net"].mean() * 1e4),
        "gross_t": _t(dd["gross"]),
        "net_t": _t(costed["net"]),
        "gross_ann_pct": float(dd["gross"].mean() * 12 * 100),
        "net_ann_pct": float(costed["net"].mean() * 12 * 100),
        "mean_cost_bps": s["mean_cost_bps"],
        "net_passes_hurdle": bool(abs(_t(costed["net"])) > HURDLE),
        "reversal_5d_mean_bps": float(rev_gross.mean() * 1e4) if len(rev) else float("nan"),
        "reversal_5d_t": _t(rev_gross) if len(rev) else float("nan"),
        "signal": signal,
    }
    LOG.log({**params, "signal": signal}, description=label, outcome=out, reported=reported)
    return {**out, "net_series": costed["net"]}


def _t(x) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def run_block(cfg: dict) -> dict:
    lbl = cfg["label"]
    print(f"\n=== {lbl} ===")
    panel, drops = build_panel(cfg)
    print(f"  {len(panel)} announcements after ordering verification "
          f"({drops['predictor_not_released_first']} dropped for bad ordering)")
    d = add_predictions(panel, cfg)
    d = add_market(d)
    d = d.dropna(subset=["predicted_z"])
    print(f"  {len(d)} usable events "
          f"{pd.to_datetime(d['target_release']).min().date()} -> "
          f"{pd.to_datetime(d['target_release']).max().date()}")
    print(f"  mean expanding-window prediction R2: {d['train_r2'].mean():.3f}")

    base = {"test_block": lbl, "target": cfg["target"][0]}
    out = {"label": lbl, "n_events": len(d), "drops": drops,
           "mean_train_r2": float(d["train_r2"].mean()),
           "period": (str(pd.to_datetime(d["target_release"]).min().date()),
                      str(pd.to_datetime(d["target_release"]).max().date()))}

    out["full"] = regress(d, f"{lbl} full sample", {**base, "subsample": "full"}, reported=True)
    print(f"  full: b1={out['full'].get('b1_predicted'):.6g} t={out['full'].get('t_b1'):.2f} | "
          f"b2 t={out['full'].get('t_b2'):.2f}")

    no_covid = d[~((pd.to_datetime(d["target_release"]) >= COVID[0]) &
                   (pd.to_datetime(d["target_release"]) <= COVID[1]))]
    out["ex_covid"] = regress(no_covid, f"{lbl} excluding 2020", {**base, "subsample": "ex_covid"},
                              reported=True)
    print(f"  ex-2020: b1 t={out['ex_covid'].get('t_b1'):.2f}")

    rel = pd.to_datetime(d["target_release"])
    if (rel < SPLIT_DATE).sum() >= 40 and (rel >= SPLIT_DATE).sum() >= 40:
        out["pre2012"] = regress(d[rel < SPLIT_DATE], f"{lbl} pre-2012",
                                 {**base, "subsample": "pre2012"}, reported=True)
        out["post2012"] = regress(d[rel >= SPLIT_DATE], f"{lbl} post-2012",
                                  {**base, "subsample": "post2012"}, reported=True)
        out["interaction"] = regress(d, f"{lbl} pre/post-2012 interaction",
                                     {**base, "subsample": "interaction"},
                                     interaction=True, reported=True)
        print(f"  pre-2012: b1 t={out['pre2012'].get('t_b1'):.2f} | "
              f"post-2012: b1 t={out['post2012'].get('t_b1'):.2f} | "
              f"interaction t={out['interaction'].get('t_b1_post'):.2f}")
    else:
        out["split_note"] = "insufficient observations either side of 2012 for a split"

    out["influence"] = influence_check(d, lbl, base)
    inf = out["influence"]
    if "t_full" in inf:
        print(f"  influence: t_full={inf['t_full']:.2f} drop1={inf['t_drop1']:.2f} "
              f"drop2={inf['t_drop2']:.2f} drop3={inf['t_drop3']:.2f}")

    out["strategy"] = frontrun_strategy(d, f"{lbl} front-run (demeaned signal)",
                                        {**base, "strategy": "frontrun"},
                                        signal="predicted_z", reported=True)
    out["strategy_raw"] = frontrun_strategy(d, f"{lbl} front-run (raw signal)",
                                            {**base, "strategy": "frontrun"},
                                            signal="predicted", reported=True)
    st = out["strategy"]
    print(f"  strategy: gross {st.get('gross_ann_pct'):.2f}%/yr t={st.get('gross_t'):.2f} | "
          f"net {st.get('net_ann_pct'):.2f}%/yr t={st.get('net_t'):.2f} | "
          f"reversal t={st.get('reversal_5d_t'):.2f}")

    if "pre2012" in out:
        out["strategy_pre"] = frontrun_strategy(d[rel < SPLIT_DATE], f"{lbl} front-run pre-2012",
                                                {**base, "strategy": "frontrun", "subsample": "pre2012"},
                                                signal="predicted_z")
        out["strategy_post"] = frontrun_strategy(d[rel >= SPLIT_DATE], f"{lbl} front-run post-2012",
                                                 {**base, "strategy": "frontrun", "subsample": "post2012"},
                                                 signal="predicted_z")

    out["yearly"] = yearly_curve(d, lbl)
    out["data"] = d
    return out


def yearly_curve(d: pd.DataFrame, lbl: str) -> pd.DataFrame:
    rows = []
    d = d.copy()
    d["year"] = pd.to_datetime(d["target_release"]).dt.year
    for year, g in d.groupby("year"):
        if len(g) < 8:
            continue
        gg = g.dropna(subset=["r_rel", "predicted_z", "surprise_z"])
        if len(gg) < 8:
            continue
        X = sm.add_constant(gg[["predicted_z", "surprise_z"]])
        try:
            m = sm.OLS(gg["r_rel"].astype(float), X.astype(float)).fit()
        except Exception:
            continue
        row = {"year": int(year), "beta": float(m.params["predicted_z"]),
               "se": float(m.bse["predicted_z"]), "t_stat": float(m.tvalues["predicted_z"]),
               "n_obs": len(gg),
               "gross_mean_bps": float((np.sign(gg["predicted_z"]) * gg["r_rel"]).mean() * 1e4)}
        rows.append(row)
        LOG.log({"test_block": lbl, "subsample": "year", "year": int(year)},
                description=f"{lbl} yearly {year}", outcome=row)
    return pd.DataFrame(rows)


def main() -> None:
    blocks = {}
    for cfg in (B1, B2):
        try:
            blocks[cfg["label"]] = run_block(cfg)
        except Exception as e:
            print(f"  {cfg['label']} FAILED: {type(e).__name__}: {e}")
            LOG.log({"test_block": cfg["label"]}, description="block failed",
                    outcome={"error": str(e)}, status=f"failed:{type(e).__name__}")

    primary = blocks.get("B1_INDPRO")
    if primary and "net_series" in primary["strategy"]:
        dsr = deflated_sharpe_ratio(primary["strategy"]["net_series"].values,
                                    log_path=ROOT / "config_log.jsonl", test="B",
                                    periods_per_year=12)
    else:
        dsr = None

    if primary is not None and len(primary["yearly"]):
        primary["yearly"].to_csv(OUT / "decay_curve.csv", index=False)
        print(f"\nWrote {OUT / 'decay_curve.csv'}")

    from .report import render
    render(OUT / "results.md", blocks, dsr,
           log_summary=summarise(ROOT / "config_log.jsonl"),
           n_trials=trial_count(ROOT / "config_log.jsonl", test="B"))
    print(f"Wrote {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
