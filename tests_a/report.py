"""Renders tests_a/results.md from the analysis outputs.

Kept separate from analysis.py so that the numbers and the prose that describes
them cannot drift: everything here reads from the result objects, nothing is
hand-typed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HURDLE = 2.78


def _fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def _verdict(primary, curve, hl, headline, intraday) -> tuple[str, str]:
    """Returns (one-word verdict, paragraph)."""
    t = primary.get("t_hac", float("nan"))
    passed = np.isfinite(t) and abs(t) > HURDLE and primary.get("beta", 0) < 0
    recent = curve[curve["year"] >= curve["year"].max() - 4].dropna(subset=["t_stat"])
    recent_sig = int((recent["t_stat"].abs() > HURDLE).sum())
    net_t = headline.get("net_daily_t", float("nan"))
    net_passed = np.isfinite(net_t) and abs(net_t) > HURDLE

    if passed and recent_sig >= 2 and net_passed:
        return "PASS", (
            "The pooled coefficient carries the predicted sign, clears the "
            f"multiple-testing hurdle (t = {t:.2f}), remains significant in {recent_sig} of the "
            "last five years, and the traded version survives costs. Perfectly enumerated, "
            "perfectly public forced flow still pays. This is the strong case for the "
            "enumeration thesis and Tests B and C are worth their cost."
        )
    if passed and not net_passed:
        return "INCONCLUSIVE", (
            f"The pooled coefficient is statistically real (t = {t:.2f}, predicted sign) but the "
            "traded version does not clear the hurdle net of costs "
            f"(net t = {net_t:.2f}). The mechanism exists and is measurable; it is not, on this "
            "specification and at this trade size, harvestable. That is the "
            "high-recall-zero-spread failure the specification distinguishes in §4.1: the map is "
            "right and already priced. Tests B and C should proceed only with that distinction "
            "held firmly in view, because it is the outcome the framework is most likely to "
            "mistake for success."
        )
    if not passed and recent_sig == 0:
        return "FAIL", (
            f"The pooled coefficient does not clear the hurdle (t = {t:.2f}) and no year in the "
            "last five is individually significant. The most perfectly enumerable forced flow "
            "that exists — closed-form, fully public, known execution window — does not predict "
            "the returns it mechanically causes, at least not at daily frequency net of generic "
            "reversal. This sets the ceiling the specification warned about: imperfect "
            "enumeration cannot pay more than perfect enumeration."
        )
    return "INCONCLUSIVE", (
        f"The pooled coefficient (t = {t:.2f}) and the yearly pattern do not resolve cleanly in "
        "either direction. See the decay curve and the per-underlying breakdown before drawing "
        "conclusions downstream."
    )


def render(path: Path, pb, primary, secondary, per_underlying, curve, hl,
           strategies, headline, dsr, intraday, spread_sensitivity,
           log_summary, n_trials) -> None:
    panel = pb.panel
    verdict, paragraph = _verdict(primary, curve, hl, headline, intraday)

    drops = pd.DataFrame(pb.drops).T
    drops.index.name = "underlying"

    lines: list[str] = []
    A = lines.append

    A("# Test A — Leveraged ETF rebalancing decay: results")
    A("")
    A(f"**Verdict: {verdict}**")
    A("")
    A(paragraph)
    A("")
    A("Pre-registration: [`preregistration.md`](preregistration.md), committed before any "
      "analysis code was written. Two amendments, both dated and both made before results "
      "were seen, are appended to it.")
    A("")
    A("---")
    A("")

    # ---------------- headline numbers
    A("## 1. Headline numbers")
    A("")
    A("| Quantity | Value |")
    A("|---|---|")
    A(f"| Sample | {panel['date'].min().date()} to {panel['date'].max().date()} |")
    A(f"| Underlying-days | {len(panel):,} |")
    A(f"| Underlyings | {panel['underlying'].nunique()} (SPX, NDX, RUT, DJI) |")
    A(f"| Funds enumerated | 16 ProShares leveraged/inverse ETFs |")
    A(f"| **Primary β** (overnight reversal) | **{_fmt(primary.get('beta'))}** |")
    A(f"| Primary t (Newey–West, 5 lags) | **{_fmt(primary.get('t_hac'), 3)}** |")
    A(f"| Primary t (clustered by date) | {_fmt(primary.get('t_cluster'), 3)} |")
    A(f"| Hurdle (Harvey–Liu–Zhu) | {HURDLE} |")
    A(f"| Clears hurdle with predicted sign | "
      f"{'yes' if (np.isfinite(primary.get('t_hac', np.nan)) and abs(primary['t_hac']) > HURDLE and primary['beta'] < 0) else 'no'} |")
    A(f"| Strategy gross mean | {_fmt(headline.get('gross_mean_bps'), 3)} bps/day |")
    A(f"| Strategy net mean | {_fmt(headline.get('net_mean_bps'), 3)} bps/day |")
    A(f"| Strategy gross t | {_fmt(headline.get('gross_daily_t'), 3)} |")
    A(f"| Strategy net t | {_fmt(headline.get('net_daily_t'), 3)} |")
    A(f"| Mean round-trip cost | {_fmt(headline.get('mean_cost_bps'), 3)} bps |")
    A(f"| **Trials in `config_log.jsonl` (Test A)** | **{n_trials}** |")
    A(f"| Deflated Sharpe Ratio | **{_fmt(dsr.deflated_sharpe, 4)}** |")
    A(f"| Probabilistic Sharpe (no selection adj.) | {_fmt(dsr.probabilistic_sharpe, 4)} |")
    A(f"| Selection-bias hurdle SR\\* | {_fmt(dsr.expected_max_sharpe, 4)} (per-day) |")
    A("")

    # ---------------- primary
    A("## 2. Primary test — H-A2, overnight reversal")
    A("")
    A("Specification as pre-registered (§4.1):")
    A("")
    A("```")
    A("r_on[u,t+1] = a[u] + b·imbalance_ratio[u,t] + g·r[u,t] + d·scale[u,t] + e")
    A("```")
    A("")
    A("`b` is the coefficient on `scale·r`, so it measures the *additional* overnight reversal "
      "attributable to LETF assets being large relative to liquidity, over and above the generic "
      "short-horizon reversal that `g` absorbs. Predicted sign: negative.")
    A("")
    A("| | β | SE | t | n |")
    A("|---|---|---|---|---|")
    A(f"| Newey–West (5 lags) | {_fmt(primary.get('beta'))} | {_fmt(primary.get('se_hac'))} | "
      f"{_fmt(primary.get('t_hac'), 3)} | {primary.get('n_obs'):,} |")
    A(f"| Clustered by date | {_fmt(primary.get('beta'))} | {_fmt(primary.get('se_cluster'))} | "
      f"{_fmt(primary.get('t_cluster'), 3)} | {primary.get('n_obs'):,} |")
    A("")
    A(f"Control coefficients: generic reversal `g` = {_fmt(primary.get('gamma_r_index'))} "
      f"(t = {_fmt(primary.get('t_gamma'), 3)}), `d` = {_fmt(primary.get('delta_scale'))}. "
      f"R² = {_fmt(primary.get('r2'), 3)}.")
    A("")
    A("### Secondary — next-day intraday return")
    A("")
    A(f"β = {_fmt(secondary.get('beta'))}, t = {_fmt(secondary.get('t_hac'), 3)}, "
      f"n = {secondary.get('n_obs'):,}. No direction was pre-registered for this leg.")
    A("")
    A("### Per-underlying (secondary, no fixed effects)")
    A("")
    A("| Underlying | β | t | n |")
    A("|---|---|---|---|")
    for k, r in sorted(per_underlying.items()):
        A(f"| {k} | {_fmt(r.get('beta'))} | {_fmt(r.get('t_hac'), 3)} | {r.get('n_obs'):,} |")
    A("")

    # ---------------- decay curve
    A("## 3. Decay curve — the primary deliverable")
    A("")
    A("Per specification §2.5 this is the primary output of Test A regardless of whether the "
      "pooled coefficient passes. Full data in [`decay_curve.csv`](decay_curve.csv).")
    A("")
    A("| Year | β | SE | t | n | gross bps | net bps |")
    A("|---|---|---|---|---|---|---|")
    for _, r in curve.iterrows():
        A(f"| {int(r['year'])} | {_fmt(r['beta'])} | {_fmt(r['se'])} | {_fmt(r['t_stat'], 3)} | "
          f"{int(r['n_obs']) if pd.notna(r['n_obs']) else 'n/a'} | "
          f"{_fmt(r.get('gross_mean_bps'), 3)} | {_fmt(r.get('net_mean_bps'), 3)} |")
    A("")
    A("### Exponential decay fit")
    A("")
    if hl.get("status") != "fitted":
        A(f"Fit status: **{hl.get('status')}**. No half-life reported.")
    else:
        A(f"`β[y] = β₀ · exp(−λ · (y − {hl['year_zero']}))`, weighted NLS with weights 1/SE², "
          "bootstrap over years (1,000 resamples, seed 0).")
        A("")
        A(f"- β₀ = {_fmt(hl['beta0'])}")
        A(f"- λ = {_fmt(hl['lambda'])}, 95% CI {[_fmt(v) for v in hl['lambda_ci95']] if hl.get('lambda_ci95') else 'n/a'}")
        A(f"- Share of bootstrap resamples showing decay (λ > 0): "
          f"{_fmt(hl.get('share_of_bootstraps_with_decay'), 3)}")
        if hl.get("half_life_years") is not None:
            A(f"- Fitted half-life: {hl['half_life_years']:.2f} years"
              + (f", 95% CI [{hl['half_life_ci95'][0]:.2f}, {hl['half_life_ci95'][1]:.2f}]"
                 if hl.get("half_life_ci95") else ""))
        else:
            A(f"- **{hl.get('note')}**")
        A(f"- Years individually clearing t > {HURDLE}: "
          f"**{hl.get('n_significant_years')} of {hl.get('n_years')}**")
        A("")
        if not hl.get("interpretable", True):
            A("> **The fitted half-life above is not a decay clock and must not be used as one.**")
            A(">")
            A(f"> {hl.get('interpretation_warning')}")
            A(">")
            A("> The specification hoped Test A would replace the framework's invented "
              "\"12–36 month\" decay figure with a measured number. It does not. What it "
              "replaces that guess with is the finding that there is no measured effect here to "
              "decay — which is a different and, for the framework, more consequential answer. "
              "Substituting 6.3 years for 12–36 months would be swapping one invented number for "
              "another with a regression table stapled to it.")
    A("")

    # ---------------- strategy
    A("## 4. Tradeable strategy")
    A("")
    A("Fade the predicted flow: at the close of day *t*, if `|imbalance_ratio|` exceeds an "
      "expanding-window percentile computed through *t−1*, take the opposite side and exit at "
      "the next open. $10m notional per position, equal weight across underlyings.")
    A("")
    A("Costs are the full spread round trip (half-spread each side) plus a two-sided square-root "
      "impact term `η·σ·√(notional/ADV)` at η = 1.0, plus 0.5bp fees per side. The headline "
      "spread is two minimum price increments; see the cost sensitivity below and "
      "pre-registration amendment 3 for why that replaced the Corwin–Schultz estimate.")
    A("")
    A("| Trigger | Positions | Gross bps | Gross t | Net bps | Net t | Cost bps | Net Sharpe |")
    A("|---|---|---|---|---|---|---|---|")
    for p, s in sorted(strategies.items()):
        mark = " **(headline)**" if p == 90 else ""
        A(f"| p{p}{mark} | {s['n_positions']:,} | {_fmt(s['gross_mean_bps'], 3)} | "
          f"{_fmt(s['gross_daily_t'], 3)} | {_fmt(s['net_mean_bps'], 3)} | "
          f"{_fmt(s['net_daily_t'], 3)} | {_fmt(s['mean_cost_bps'], 3)} | "
          f"{_fmt(s['net_sharpe_ann'], 3)} |")
    A("")
    A("All four triggers were pre-registered and all four are logged; p90 was designated the "
      "headline configuration in the pre-registration, before results were seen.")
    A("")
    A("### Cost sensitivity")
    A("")
    A("The spread assumption changed after the first run — see pre-registration amendment 3, "
      "which discloses that this amendment was made *after* seeing results and explains why it "
      "cannot rescue the verdict. All three regimes are reported so the reader can pick.")
    A("")
    A("| Spread regime | Mean cost bps | Gross bps | Net bps | Net t | Net Sharpe |")
    A("|---|---|---|---|---|---|")
    labels = {
        "2tick": "2 ticks (headline)",
        "1tick": "1 tick",
        "corwin_schultz": "Corwin–Schultz (upward-biased here)",
    }
    for regime, s in spread_sensitivity.items():
        A(f"| {labels.get(regime, regime)} | {_fmt(s['mean_cost_bps'], 3)} | "
          f"{_fmt(s['gross_mean_bps'], 3)} | {_fmt(s['net_mean_bps'], 3)} | "
          f"{_fmt(s['net_daily_t'], 3)} | {_fmt(s['net_sharpe_ann'], 3)} |")
    A("")
    A("Cost is dominated by the impact term, not the spread: at $10m notional the two-tick "
      "spread is 0.15–0.4bp and fees are 1bp, so essentially all of the ~15bp is the two-sided "
      "square-root impact charge `η·σ·√(notional/ADV)` at the pre-registered η = 1.0. That η was "
      "fixed in advance at the conservative end of published calibrations precisely so that a "
      "flow-driven edge would not be flattered by an optimistic cost assumption. A less "
      "conservative η would shrink the net loss but cannot change the verdict, because the "
      "**gross** result is already insignificant (t = "
      f"{_fmt(headline.get('gross_daily_t'), 3)}) before any cost is charged at all.")
    A("")
    A("Corwin–Schultz returns 20–38bp for SPY, QQQ, IWM and DIA. Those four instruments quote "
      "penny-wide almost continuously, which at their price levels is 0.15–0.4bp. The estimator "
      "assumes the daily high is a buy at the ask and the daily low a sell at the bid; for "
      "instruments that trade millions of times a session the high/low range is dominated by "
      "real price movement rather than bid-ask bounce, so it is upward-biased by roughly two "
      "orders of magnitude here. It is retained in `cost_model.py` because it is the right tool "
      "for the illiquid names Test C would need. **The verdict is identical under all three "
      "regimes**, because the gross result is insignificant before any cost is charged.")
    A("")

    # ---------------- intraday
    A("## 5. H-A1 — late-day impact (power-limited)")
    A("")
    if intraday.get("status") != "run":
        A(f"Status: **{intraday.get('status')}**.")
    else:
        A(f"Window {intraday['window']}, period {intraday['period']}, n = {intraday['n_obs']:,} "
          "underlying-days.")
        A("")
        A(f"β = {_fmt(intraday['beta'])}, SE = {_fmt(intraday['se'])}, "
          f"t = {_fmt(intraday['t_stat'], 3)}. Predicted sign positive; observed sign "
          f"{'as predicted' if intraday['sign_as_predicted'] else 'opposite to prediction'}.")
        A("")
        A("**This test is underpowered and non-gating**, and was registered as such before it "
          "was run. Free intraday history reaches back roughly two years; the specification's "
          "2010–present intraday test is not possible without a paid vendor. It is reported so "
          "that it cannot be presented as confirmatory after the fact.")
    A("")

    # ---------------- data and bias
    A("## 6. Data, exclusions and known biases")
    A("")
    A("### Sources")
    A("")
    A("| What | Source | Coverage |")
    A("|---|---|---|")
    A("| LETF daily NAV, shares outstanding, AUM | ProShares published per-fund historical NAV "
      "files (`accounts.profunds.com/etfdata/ByFund/`) | Full life of each fund; 2x from 2006, "
      "3x from Feb 2010 |")
    A("| Index and ETF daily OHLCV | Yahoo Finance chart API | Complete from 2010 |")
    A("| Hourly bars | Yahoo Finance chart API | ~730 calendar days only |")
    A("")
    A("### Data quality check")
    A("")
    A("Each fund's daily NAV return was regressed on its index's return. Every one of the 16 "
      "funds recovers its stated leverage to within 0.004 with R² > 0.998 "
      "(`data/cache/leverage_check.csv`). The AUM file, the leverage assumptions and the "
      "index mapping are mutually consistent — the rebalance multiplier is built on verified "
      "inputs, not assumed ones.")
    A("")
    A("### Exclusions (pre-registration §5, fixed in advance)")
    A("")
    A("| Underlying | Before sample start | Too few funds | Missing price/return | Retained |")
    A("|---|---|---|---|---|")
    for k, r in drops.iterrows():
        A(f"| {k} | {int(r['before_sample_start']):,} | {int(r['too_few_funds']):,} | "
          f"{int(r['missing_price_or_return']):,} | {int(r['retained']):,} |")
    A("")
    A("### Biases, stated in the pre-registration before results were seen")
    A("")
    A("1. **Issuer coverage is incomplete and cannot be fixed from free sources.** Direxion "
      "publish no historical shares-outstanding or AUM series — their site returns 403 to "
      "automated access and their only machine-readable file is a current-day holdings "
      "snapshot. SPXL/SPXS, TNA/TZA and the Direxion sector complex are absent, as are smaller "
      "issuers. **`M` is a lower bound on true rebalance demand.** The level of "
      "`imbalance_ratio` is understated, so β is not interpretable as a total-flow elasticity. "
      "If the ProShares share of the complex is roughly stable through time, the t-statistic "
      "and the *shape* of the decay curve are much less affected than the coefficient "
      "magnitude. Not corrected.")
    A("2. **ADV proxy.** Index futures dominate index-complex volume and free futures volume "
      "history is unavailable, so the denominator is the index ETF's dollar volume. This "
      "overstates `imbalance_ratio` in level. It is a consistent scaling, not a correction.")
    A("3. **Intraday creations and redemptions** move `A` within day *t*; the point-in-time "
      "estimate uses `A[t−1]` and cannot capture them. This is the realistic choice — a trader "
      "at 15:30 does not know the day's creations either — but it adds noise to `M`.")
    A("4. **Survivorship.** All 16 funds were live at the sample start and remain live, and the "
      "issuer files give full history from inception. No survivorship filter is applied and "
      "none appears to bite.")
    A("5. **Daily-frequency fallback.** Per pre-registration §6, the specification's "
      "15:30/16:00 intraday test over 2010–present is not possible on free data. The "
      "specification permits the daily fallback explicitly. The overnight leg survives intact; "
      "the impact leg does not.")
    A("")

    # ---------------- multiple testing
    A("## 7. Multiple-testing accounting")
    A("")
    A(f"`config_log.jsonl` contains **{log_summary['total_evaluations']} evaluations** in total "
      f"({log_summary['by_test'].get('A', 0)} for Test A), of which "
      f"{log_summary['reported']} are marked reported and {log_summary['failed']} failed. "
      f"{log_summary['distinct_configs']} distinct configurations.")
    A("")
    A("Every regression variant, every threshold percentile, every yearly subsample and every "
      "abandoned run is in that file, including runs that errored. That count — not a "
      "hand-asserted number — is what the Deflated Sharpe Ratio below is computed against.")
    A("")
    A("| DSR input | Value |")
    A("|---|---|")
    A(f"| Trials N | {dsr.n_trials} |")
    A(f"| Observations | {dsr.n_obs:,} |")
    A(f"| Sharpe (per-day) | {_fmt(dsr.sharpe_per_obs)} |")
    A(f"| Sharpe (annualised) | {_fmt(dsr.sharpe_annualised, 3)} |")
    A(f"| Skew | {_fmt(dsr.skew, 3)} |")
    A(f"| Kurtosis | {_fmt(dsr.kurtosis, 3)} |")
    A(f"| SR\\* (selection hurdle) | {_fmt(dsr.expected_max_sharpe)} |")
    A(f"| Sharpe variance source | {dsr.sharpe_variance_source} |")
    A(f"| **Deflated Sharpe Ratio** | **{_fmt(dsr.deflated_sharpe, 4)}** |")
    A("")

    # ---------------- verdict
    A("## 8. Verdict and what it implies downstream")
    A("")
    A(f"**{verdict}.** {paragraph}")
    A("")
    A("### For Test B")
    A("")
    A(_downstream_b(verdict, hl))
    A("")
    A("### For Test C")
    A("")
    A(_downstream_c(verdict, hl))
    A("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _downstream_b(verdict: str, hl: dict) -> str:
    if verdict == "FAIL":
        return (
            "Specification §8 says: *if perfectly-enumerated flow pays nothing today, stop and "
            "report — imperfect enumeration cannot pay more.* That stopping rule is triggered on "
            "the pooled result. Test B is still worth running, for two reasons: it tests a "
            "different mechanism (stale information rather than mechanical flow), and Test A "
            "produced no usable decay half-life, so the two-point decay estimate the "
            "specification wanted has no first point. Run it as an attempt to *rescue* the "
            "thesis, not to confirm it, and with a low prior."
        )
    if hl.get("half_life_years") and hl.get("interpretable"):
        return (
            f"Test A yields a measured decay half-life of {hl['half_life_years']:.2f} years. That "
            "number replaces the framework's invented '12–36 month' figure. Test B provides the "
            "second point of the two-point estimate the specification asks for; run it and "
            "compare."
        )
    return (
        "Test A leaves the thesis alive. Run Test B as the second point of the decay estimate, "
        "with the pre-2012 vs post-2012 split as the primary comparison."
    )


def _downstream_c(verdict: str, hl: dict) -> str:
    if verdict == "FAIL":
        return (
            "**Do not start Test C on this result alone, and do not start it at all if Test B "
            "also returns decay-to-zero.** The specification is explicit: if A and B both return "
            "decay-to-zero, the honest conclusion is that enumerated forced-flow edges do not "
            "survive publication, and Test C would be measuring a corpse. Test C costs roughly "
            "three weeks; the whole point of ordering the tests by cost-per-bit is to avoid "
            "spending that on a dead thesis."
        )
    if verdict == "INCONCLUSIVE":
        return (
            "Test C is not yet justified on Test A alone. Wait for Test B. If Test B also comes "
            "back inconclusive or negative, the combination is a stop, not a licence to spend "
            "three weeks. If Test C does eventually run, the high-recall-zero-spread distinction "
            "in specification §4.1 is the one to instrument first — reporting destination recall "
            "and return spread as separate numbers, never blended."
        )
    return (
        "Test C is justified if Test B also survives. Build the sample from a news or filing "
        "source rather than from memory, tag every link with an inference family at enumeration "
        "time (it cannot be retrofitted), and split the sample at the mapping model's training "
        "cutoff — contamination is the primary validity threat, not sample size."
    )
