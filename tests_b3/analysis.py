"""Test B-3: the same macro blocks, measured against rates instead of SPY.

Order is fixed by the pre-registration and is not negotiable:

  Step 1  VALIDITY for every block and every outcome, reported before anything
          else is computed. A block that fails validity is UNREADABLE and its
          predictable-component coefficient is not interpreted.
  Step 2  Predictable component, only for blocks that passed.
  Step 3  Pre/post-2012 split, only for B1 and only if it passed.
  Step 4  Influence diagnostic on every reported coefficient.

Outputs: tests_b3/results.md, tests_b3/validity.csv
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from nomad.infra.config_logger import ConfigLogger, summarise, trial_count
from nomad.infra.deflated_sharpe import haircut_hurdle_t
from tests_b import analysis as B
from .rates import build as build_rates

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HURDLE = haircut_hurdle_t()
LOG = ConfigLogger("B3", path=ROOT / "config_log.jsonl")
SPLIT = pd.Timestamp("2012-01-01")

BLOCKS = {
    "B1_INDPRO": {"cfg": B.B1, "min_train": 60, "role": "the prize - only block spanning 2012"},
    "B2_CFNAI": {"cfg": B.B2, "min_train": 60, "role": "positive control - passed validity on SPY"},
    "B2ext_COREPCE": {
        "cfg": {"target": ("PCEPILFE", "logdiff"),
                "predictors": [("CPILFESL", "logdiff"), ("CPIAUCSL", "logdiff")],
                "start": "2000-08-01", "label": "B2ext_COREPCE"},
        "min_train": 36, "role": "weak analogue (R2 0.28) but has the sample"},
}

# preregistration §4: expected sign of the SURPRISE coefficient
EXPECTED_SIGN = {"DGS2": +1, "TLT_on": -1, "TLT_cc": -1, "IEF_on": -1, "IEF_cc": -1}
PRIMARY_OUTCOME = "DGS2"
PRIMARY_WINDOW_OUTCOMES = ("TLT_on", "IEF_on")


def attach_outcome(d: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """Attach one outcome to the release dates. Non-trading release dates drop."""
    s = series.dropna(subset=["value"]).set_index("date")["value"]
    out = d.copy()
    rel = pd.to_datetime(out["target_release"]).dt.normalize()
    out["outcome"] = rel.map(s)
    return out.dropna(subset=["outcome"])


def regress(d: pd.DataFrame, label: str, params: dict, interaction: bool = False,
            reported: bool = True) -> dict:
    dd = d.dropna(subset=["outcome", "predicted_z", "surprise_z"]).copy()
    res = {"label": label, "n_obs": len(dd)}
    if len(dd) < 40:
        res["note"] = "insufficient observations"
        LOG.log(params, description=label, outcome=res, status="skipped:insufficient_n")
        return res

    X = pd.DataFrame({"predicted_z": dd["predicted_z"], "surprise_z": dd["surprise_z"]})
    if interaction:
        post = (pd.to_datetime(dd["target_release"]) >= SPLIT).astype(float)
        X["predicted_z_post"] = X["predicted_z"] * post
        X["surprise_z_post"] = X["surprise_z"] * post
        X["post"] = post
    X = sm.add_constant(X)
    m = sm.OLS(dd["outcome"].astype(float), X.astype(float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 3})

    res.update({
        "b1_predicted": float(m.params["predicted_z"]), "t_b1": float(m.tvalues["predicted_z"]),
        "b2_surprise": float(m.params["surprise_z"]), "t_b2": float(m.tvalues["surprise_z"]),
        "r2": float(m.rsquared),
        "b1_passes": bool(abs(float(m.tvalues["predicted_z"])) > HURDLE),
        "b2_passes": bool(abs(float(m.tvalues["surprise_z"])) > HURDLE),
    })
    if interaction:
        res.update({
            "b1_post_interaction": float(m.params["predicted_z_post"]),
            "t_b1_post": float(m.tvalues["predicted_z_post"]),
            "decay_detected": bool(
                abs(float(m.tvalues["predicted_z_post"])) > HURDLE
                and np.sign(m.params["predicted_z_post"]) != np.sign(m.params["predicted_z"])),
        })
    LOG.log(params, description=label, outcome=res, reported=reported)
    return res


def influence(d: pd.DataFrame, label: str, params: dict) -> dict:
    dd = d.dropna(subset=["outcome", "predicted_z", "surprise_z"]).copy()
    if len(dd) < 40:
        return {"note": "insufficient observations"}
    X = sm.add_constant(dd[["predicted_z", "surprise_z"]].astype(float))
    y = dd["outcome"].astype(float)
    cooks = sm.OLS(y, X).fit().get_influence().cooks_distance[0]
    order = np.argsort(-cooks)
    out = {"t_full": float(sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
                           .tvalues["predicted_z"])}
    for k in (1, 2, 3, 5):
        keep = np.ones(len(dd), dtype=bool); keep[order[:k]] = False
        out[f"t_drop{k}"] = float(sm.OLS(y.values[keep], X.values[keep])
                                  .fit(cov_type="HAC", cov_kwds={"maxlags": 3}).tvalues[1])
    out["most_influential_dates"] = [
        str(pd.Timestamp(dd["target_release"].iloc[i]).date()) for i in order[:3]]
    LOG.log({**params, "diagnostic": "influence"}, description=f"{label} influence",
            outcome=out, reported=True)
    return out


def main() -> None:
    print("Building announcement panels (cached vintages, unchanged from B/B-2)...")
    rates = build_rates()
    panels = {}
    for name, spec in BLOCKS.items():
        panel, drops = B.build_panel(spec["cfg"])
        d = B.add_predictions(panel, spec["cfg"], min_train=spec["min_train"])
        panels[name] = {"data": d, "drops": drops,
                        "mean_r2": float(d["train_r2"].mean()), "role": spec["role"]}
        print(f"  {name}: {len(d)} announcements, mean prediction R2 = {panels[name]['mean_r2']:.3f}")

    # ---------------- STEP 1: VALIDITY, BEFORE ANYTHING ELSE ----------------
    print("\n" + "=" * 72)
    print("STEP 1 - VALIDITY. Does the rates instrument see genuine surprise?")
    print("=" * 72)
    rows = []
    for name, p in panels.items():
        for oc, series in rates.items():
            d = attach_outcome(p["data"], series)
            r = regress(d, f"{name} / {oc} validity",
                        {"test": "B3", "block": name, "outcome": oc, "step": "validity"})
            if "t_b2" not in r:
                continue
            exp = EXPECTED_SIGN[oc]
            sign_ok = np.sign(r["b2_surprise"]) == exp
            rows.append({
                "block": name, "outcome": oc, "window": series["window"].iloc[0],
                "n": r["n_obs"], "b2_surprise": r["b2_surprise"], "t_b2": r["t_b2"],
                "expected_sign": "+" if exp > 0 else "-",
                "sign_ok": sign_ok,
                "validity_pass": bool(abs(r["t_b2"]) > HURDLE and sign_ok),
                "t_b1_withheld": r["t_b1"],
            })
    val = pd.DataFrame(rows)
    val.to_csv(OUT / "validity.csv", index=False)

    print(f"\n{'block':16}{'outcome':9}{'window':16}{'n':>5}{'t(surprise)':>13}"
          f"{'sign':>6}{'PASS':>7}")
    for _, r in val.iterrows():
        print(f"{r['block']:16}{r['outcome']:9}{r['window']:16}{r['n']:>5}"
              f"{r['t_b2']:>13.2f}{('ok' if r['sign_ok'] else 'WRONG'):>6}"
              f"{('YES' if r['validity_pass'] else 'no'):>7}")

    passing = val[val["validity_pass"]]
    print(f"\nValidity passes: {len(passing)} of {len(val)} block-outcome combinations.")

    # coherence check (preregistration §4)
    print("\nCoherence check - yields and bond prices must move oppositely:")
    for name in panels:
        sub = val[val["block"] == name]
        if sub.empty:
            continue
        dg = sub[sub["outcome"] == "DGS2"]["b2_surprise"]
        tl = sub[sub["outcome"] == "TLT_cc"]["b2_surprise"]
        if len(dg) and len(tl):
            ok = np.sign(dg.iloc[0]) != np.sign(tl.iloc[0])
            print(f"  {name:16} DGS2 {dg.iloc[0]:+.4g} bp vs TLT {tl.iloc[0]:+.5f}  "
                  f"-> {'coherent' if ok else 'INCOHERENT'}")

    # ---------------- STEP 2 and 3: only for blocks that passed ----------------
    print("\n" + "=" * 72)
    print("STEP 2/3 - predictable component, only where validity passed")
    print("=" * 72)
    results = {}
    if passing.empty:
        print("  No block-outcome combination passed validity.")
        print("  Per the pre-registration, NO b1 coefficient is interpreted.")
    else:
        for _, r in passing.iterrows():
            name, oc = r["block"], r["outcome"]
            d = attach_outcome(panels[name]["data"], rates[oc])
            base = {"test": "B3", "block": name, "outcome": oc}
            k = f"{name}|{oc}"
            results[k] = {
                "full": regress(d, f"{k} predictable", {**base, "step": "predictable"}),
                "influence": influence(d, k, base),
            }
            rel = pd.to_datetime(d["target_release"])
            if (rel < SPLIT).sum() >= 40 and (rel >= SPLIT).sum() >= 40:
                results[k]["pre2012"] = regress(d[rel < SPLIT], f"{k} pre-2012",
                                                {**base, "step": "pre2012"})
                results[k]["post2012"] = regress(d[rel >= SPLIT], f"{k} post-2012",
                                                 {**base, "step": "post2012"})
                results[k]["interaction"] = regress(d, f"{k} interaction",
                                                    {**base, "step": "interaction"},
                                                    interaction=True)
                results[k]["influence_pre"] = influence(d[rel < SPLIT], f"{k} pre",
                                                        {**base, "step": "pre2012"})
                results[k]["influence_post"] = influence(d[rel >= SPLIT], f"{k} post",
                                                         {**base, "step": "post2012"})
            f = results[k]["full"]
            print(f"  {k:28} b1 t={f['t_b1']:>6.2f}  drop2 t="
                  f"{results[k]['influence'].get('t_drop2', float('nan')):>6.2f}"
                  + (f"  | pre {results[k]['pre2012']['t_b1']:>6.2f}"
                     f"  post {results[k]['post2012']['t_b1']:>6.2f}"
                     f"  interaction {results[k]['interaction']['t_b1_post']:>6.2f}"
                     if "interaction" in results[k] else "  | no split (sample)"))

    from .report import render
    render(OUT / "results.md", panels, val, results,
           summarise(ROOT / "config_log.jsonl"),
           trial_count(ROOT / "config_log.jsonl"))
    print(f"\nWrote {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
