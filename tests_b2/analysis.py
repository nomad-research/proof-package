"""Test B-2: stale information, extended across the 2012 split.

Reuses Test B's machinery -- vintage assembly, point-in-time prediction, the
influence diagnostic, the cost model -- and changes the indicator to one that
both passes the validity check and spans the split.

Outputs: tests_b2/results.md, tests_b2/decay_curve.csv
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from nomad.infra.config_logger import ConfigLogger, summarise, trial_count
from nomad.infra.deflated_sharpe import deflated_sharpe_ratio, haircut_hurdle_t
from tests_b import analysis as B
from tests_b.pipeline import fetch_vintage_panel

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HURDLE = haircut_hurdle_t()
LOG = ConfigLogger("B2", path=ROOT / "config_log.jsonl")
SPLIT = pd.Timestamp("2012-01-01")

# Core PCE: roughly three quarters of it is built from the same price quotes the
# CPI publishes about two weeks earlier for the same reference month.
CFG = {
    "target": ("PCEPILFE", "logdiff"),
    "predictors": [("CPILFESL", "logdiff"), ("CPIAUCSL", "logdiff")],
    "start": "2000-08-01",
    "label": "B2ext_COREPCE",
}
MIN_TRAIN_PRIMARY = 36      # preregistration §4
MIN_TRAIN_SENSITIVITY = 60


def assert_sample(d: pd.DataFrame, label: str, warmup_months: int) -> dict:
    """Amendment 1 §2.4 guard.

    The cache-keyed-on-symbol bug silently truncated Test B's sample by five years
    and suppressed the split entirely. This test's entire purpose is that split,
    so the shape of the sample is asserted and printed before any regression runs.
    """
    rel = pd.to_datetime(d["target_release"])
    info = {
        "label": label,
        "sample_start": str(rel.min().date()),
        "sample_end": str(rel.max().date()),
        "n_obs": int(len(d)),
        "n_pre_2012": int((rel < SPLIT).sum()),
        "n_post_2012": int((rel >= SPLIT).sum()),
    }
    print(f"  SAMPLE GUARD [{label}]: {info['sample_start']} -> {info['sample_end']}, "
          f"n={info['n_obs']} (pre-2012 {info['n_pre_2012']}, post-2012 {info['n_post_2012']})")

    # Substantive condition: is the split readable?
    problems = []
    if info["n_pre_2012"] < 40:
        problems.append(f"only {info['n_pre_2012']} pre-2012 observations (need >= 40)")

    # Anti-truncation condition (amendment 1): the sample must start where the
    # pre-registered warm-up puts it, not earlier and not later. This is the check
    # that would have caught the cache bug; a fixed calendar threshold was a
    # redundant proxy for it and was calibrated without doing the arithmetic.
    vint = pd.to_datetime(fetch_vintage_panel(CFG["target"][0])["vintage"]).min()
    expected = vint + pd.DateOffset(months=warmup_months)
    slack_months = abs((rel.min() - expected).days) / 30.44
    info["first_vintage"] = str(vint.date())
    info["expected_start"] = str(expected.date())
    info["warmup_months"] = warmup_months
    info["start_vs_expected_months"] = round(slack_months, 1)
    if slack_months > 6:
        problems.append(
            f"sample starts {info['sample_start']} but the pre-registered warm-up implies "
            f"{info['expected_start']} — a gap of {slack_months:.1f} months suggests truncation")
    info["problems"] = problems
    info["usable"] = not problems

    LOG.log({"test": "B2ext", "check": "sample_guard", "min_train": label},
            description="sample assertion guard", outcome=info, reported=True)
    if problems:
        print(f"  !! GUARD FAILED: {'; '.join(problems)}")
    return info


def run(min_train: int, label: str, reported: bool = True) -> dict:
    print(f"\n=== {CFG['label']} (min_train={min_train}) ===")
    panel, drops = B.build_panel(CFG)
    print(f"  {len(panel)} announcements after ordering verification "
          f"({drops['predictor_not_released_first']} dropped for bad ordering)")

    d = B.add_predictions(panel, CFG, min_train=min_train)
    d = B.add_market(d)
    d = d.dropna(subset=["predicted_z"])

    guard = assert_sample(d, label, warmup_months=min_train + 24)
    out = {"label": label, "min_train": min_train, "guard": guard, "drops": drops,
           "n_events": len(d), "mean_train_r2": float(d["train_r2"].mean()),
           "period": (guard["sample_start"], guard["sample_end"])}
    print(f"  mean expanding-window prediction R2: {out['mean_train_r2']:.3f}")

    if not guard["usable"]:
        out["unusable"] = True
        return out

    base = {"test": "B2ext", "target": CFG["target"][0], "min_train": min_train}

    # Two event windows (amendment 2). close-to-close is as pre-registered;
    # overnight brackets the 08:30 release without 6.5 hours of unrelated news.
    for w, dep in (("cc", "r_rel"), ("on", "r_rel_on")):
        out[f"full_{w}"] = B.regress(d, f"{label} full [{w}]",
                                     {**base, "subsample": "full", "window": w},
                                     reported=reported, dep=dep)
        print(f"  full [{w}]: b1 t={out[f'full_{w}'].get('t_b1'):.2f} | "
              f"b2 (validity) t={out[f'full_{w}'].get('t_b2'):.2f}")
    # the readable window is the one whose validity check passes
    v_cc = abs(out["full_cc"].get("t_b2") or 0)
    v_on = abs(out["full_on"].get("t_b2") or 0)
    dep_main = "r_rel_on" if v_on > v_cc else "r_rel"
    out["window_used"] = "overnight" if dep_main == "r_rel_on" else "close-to-close"
    out["validity_cc"] = out["full_cc"].get("t_b2")
    out["validity_on"] = out["full_on"].get("t_b2")
    print(f"  -> window carried forward: {out['window_used']}")
    out["full"] = out[f"full_{'on' if dep_main == 'r_rel_on' else 'cc'}"]

    no_covid = d[~((pd.to_datetime(d["target_release"]) >= B.COVID[0]) &
                   (pd.to_datetime(d["target_release"]) <= B.COVID[1]))]
    out["ex_covid"] = B.regress(no_covid, f"{label} ex-2020",
                                {**base, "subsample": "ex_covid"}, reported=reported, dep=dep_main)

    rel = pd.to_datetime(d["target_release"])
    out["pre2012"] = B.regress(d[rel < SPLIT], f"{label} pre-2012",
                               {**base, "subsample": "pre2012"}, reported=reported, dep=dep_main)
    out["post2012"] = B.regress(d[rel >= SPLIT], f"{label} post-2012",
                                {**base, "subsample": "post2012"}, reported=reported, dep=dep_main)
    out["interaction"] = B.regress(d, f"{label} interaction",
                                   {**base, "subsample": "interaction"},
                                   interaction=True, reported=reported, dep=dep_main)
    print(f"  pre-2012 b1 t={out['pre2012'].get('t_b1'):.2f} | "
          f"post-2012 b1 t={out['post2012'].get('t_b1'):.2f} | "
          f"interaction t={out['interaction'].get('t_b1_post'):.2f}")

    out["influence"] = B.influence_check(d, label, base, dep=dep_main)
    out["influence_pre"] = B.influence_check(d[rel < SPLIT], f"{label} pre-2012",
                                             {**base, "subsample": "pre2012"}, dep=dep_main)
    out["influence_post"] = B.influence_check(d[rel >= SPLIT], f"{label} post-2012",
                                              {**base, "subsample": "post2012"}, dep=dep_main)
    inf = out["influence"]
    if "t_full" in inf:
        print(f"  influence: full={inf['t_full']:.2f} drop2={inf['t_drop2']:.2f}")

    out["strategy"] = B.frontrun_strategy(d, f"{label} front-run",
                                          {**base, "strategy": "frontrun"},
                                          signal="predicted_z", reported=reported)
    out["strategy_pre"] = B.frontrun_strategy(d[rel < SPLIT], f"{label} front-run pre",
                                              {**base, "strategy": "frontrun",
                                               "subsample": "pre2012"}, signal="predicted_z")
    out["strategy_post"] = B.frontrun_strategy(d[rel >= SPLIT], f"{label} front-run post",
                                               {**base, "strategy": "frontrun",
                                                "subsample": "post2012"}, signal="predicted_z")
    s = out["strategy"]
    if "gross_ann_pct" in s:
        print(f"  strategy: gross {s['gross_ann_pct']:.2f}%/yr t={s['gross_t']:.2f} | "
              f"net {s['net_ann_pct']:.2f}%/yr t={s['net_t']:.2f}")

    out["yearly"] = B.yearly_curve(d, label)
    out["data"] = d
    return out


def main() -> None:
    # B-2 delegates its regressions to Test B's functions, which carry their own
    # logger. Retag it so evaluations land under B2 rather than inflating B's
    # count -- the cumulative total is unaffected either way, but the per-test
    # breakdown should say which test actually ran them.
    prev_log = B.LOG
    B.LOG = LOG
    try:
        primary = run(MIN_TRAIN_PRIMARY, "min_train=36", reported=True)
        sens = run(MIN_TRAIN_SENSITIVITY, "min_train=60", reported=True)
    finally:
        B.LOG = prev_log

    if len(primary.get("yearly", [])):
        primary["yearly"].to_csv(OUT / "decay_curve.csv", index=False)
        print(f"\nWrote {OUT / 'decay_curve.csv'}")

    dsr = None
    st = primary.get("strategy", {})
    if "net_series" in st:
        dsr = deflated_sharpe_ratio(st["net_series"].values,
                                    n_trials=trial_count(ROOT / "config_log.jsonl"),
                                    log_path=ROOT / "config_log.jsonl", periods_per_year=12)
        print(f"\nCumulative DSR: trials={dsr.n_trials} DSR={dsr.deflated_sharpe:.4f}")

    from .report import render
    render(OUT / "results.md", primary, sens, dsr,
           summarise(ROOT / "config_log.jsonl"))
    print(f"Wrote {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
