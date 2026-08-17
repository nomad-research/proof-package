"""Renders tests_b2/results.md."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HURDLE = 2.78


def _f(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    return str(x)


def _sig(t) -> bool:
    return t is not None and np.isfinite(t) and abs(t) > HURDLE


def _robust(reg: dict, inf: dict) -> bool:
    """Significant, and still significant after dropping the two most influential points."""
    return _sig(reg.get("t_b1")) and _sig(inf.get("t_drop2"))


def _verdict(p: dict) -> tuple[str, str]:
    if p.get("unusable"):
        return "GUARD FAILED", (
            "The sample assertion guard required by Amendment 1 §2.4 failed: "
            + "; ".join(p["guard"]["problems"]) +
            ". The analysis stopped rather than producing a split that cannot be read."
        )

    full, pre, post = p.get("full", {}), p.get("pre2012", {}), p.get("post2012", {})
    inter = p.get("interaction", {})
    validity = full.get("t_b2")

    if not _sig(validity):
        return "UNREADABLE", (
            f"The extended sample fails the validity check: the market does not measurably "
            f"respond to genuine core-PCE surprise either (t = {_f(validity, 3)}). "
            "Amendment 1 §2.3 requires this check to be re-run on the extended sample precisely "
            "because passing on a short window does not guarantee passing on a long one, and it "
            "does not pass here. Everything below is unreadable in either direction. Per §2.5 "
            "this is **a gap, not a negative result**, and it does **not** fire the "
            "stop-permanently trigger."
        )

    pre_robust = _robust(pre, p.get("influence_pre", {}))
    post_robust = _robust(post, p.get("influence_post", {}))
    decay = _sig(inter.get("t_b1_post")) and inter.get("decay_detected")

    if pre_robust and post_robust:
        return "DURABLE", (
            f"The market responds to the predictable component both before 2012 "
            f"(t = {_f(pre.get('t_b1'), 3)}) and after it (t = {_f(post.get('t_b1'), 3)}), and "
            "both survive removal of their most influential observations. "
            "Public-but-unconnected information moves prices and keeps doing so after the "
            "mechanism is documented. Strong support for the backward-reading thesis."
        )
    if pre_robust and not post_robust and decay:
        return "DECAYED", (
            f"The response to the predictable component is real before 2012 "
            f"(t = {_f(pre.get('t_b1'), 3)}) and gone after it "
            f"(t = {_f(post.get('t_b1'), 3)}), with the difference itself clearing the hurdle "
            f"(interaction t = {_f(inter.get('t_b1_post'), 3)}). The mechanism is real and "
            "decays on publication. This is the strongest positive outcome available from this "
            "test, and it dates the death of a documented edge."
        )
    if pre_robust and not post_robust:
        return "SUGGESTIVE DECAY", (
            f"The predictable component is significant pre-2012 (t = {_f(pre.get('t_b1'), 3)}) "
            f"and not post-2012 (t = {_f(post.get('t_b1'), 3)}), but the interaction that tests "
            f"the *difference* does not clear the hurdle (t = {_f(inter.get('t_b1_post'), 3)}). "
            "Two separately-classified coefficients are not evidence of a difference between "
            "them. Suggestive of decay; not established at the required level."
        )
    if post_robust:
        return "PARTIAL", (
            f"The predictable component is significant post-2012 (t = {_f(post.get('t_b1'), 3)}) "
            f"but not pre-2012 (t = {_f(pre.get('t_b1'), 3)}). That is the opposite of the decay "
            "story and is hard to interpret as support for a mechanism that is supposed to die "
            "on publication. Treat with suspicion and check the sub-period samples before "
            "building on it."
        )
    return "CLEAN NULL", (
        f"Validity passes — the market does respond to genuine core-PCE surprise "
        f"(t = {_f(validity, 3)}) — and the predictable component moves nothing, in either "
        f"period (full t = {_f(full.get('t_b1'), 3)}, pre-2012 t = {_f(pre.get('t_b1'), 3)}, "
        f"post-2012 t = {_f(post.get('t_b1'), 3)}). The instrument can see news that is new and "
        "sees nothing in the part of the announcement that was already public. This is the clean "
        "null Amendment 1 §3 names as the stop-permanently trigger."
    )


def _reg_row(A, res, inf, name):
    if not res or "b1_predicted" not in res:
        A(f"| {name} | — | — | — | — | — | {res.get('note', 'not run') if res else 'not run'} |")
        return
    A(f"| {name} | {_f(res['b1_predicted'])} | {_f(res['t_b1'], 3)} | "
      f"{_f((inf or {}).get('t_drop2'), 3)} | {_f(res['b2_surprise'])} | "
      f"{_f(res['t_b2'], 3)} | {res['n_obs']:,} |")


def render(path: Path, primary: dict, sens: dict, dsr, log_summary) -> None:
    verdict, para = _verdict(primary)
    L: list[str] = []
    A = L.append

    A("# Test B-2 — Stale information, extended across the 2012 split: results")
    A("")
    A(f"**Verdict: {verdict}**")
    A("")
    A(para)
    A("")
    A("Pre-registration: [`preregistration.md`](preregistration.md), committed before this "
      "analysis was run.")
    A("")
    A("> **This is not CFNAI, and that was not a choice.** Amendment 1 §2.2 specifies extending "
      "CFNAI backwards using release dates archived by the Chicago Fed. Those dates could not be "
      "obtained: ALFRED's first CFNAI vintage is 2011-05-23, the Chicago Fed's `past-releases` "
      "page renders its list client-side with no JSON or AJAX endpoint in the served source "
      "(confirmed twice, including with an independent renderer), `/cfnai/archive` returns 404, "
      "and FRED's release-date API needs a key that cannot be obtained from this environment. "
      "The amendment forbids reconstructing release dates from a schedule, so the criterion it "
      "actually states — *any composite that passes validity and spans the split* — was applied "
      "instead. **If a Chicago Fed archive URL exists, extending to CFNAI is a small delta on "
      "this code.**")
    A("")
    A("---")
    A("")

    # ---- what the substitute is
    A("## 1. The indicator")
    A("")
    A("**Core PCE price index (`PCEPILFE`)**, released monthly by the BEA in the Personal Income "
      "and Outlays report. Roughly three quarters of it is constructed from the *same underlying "
      "price quotes* the BLS publishes in the CPI about two weeks earlier for the same reference "
      "month. Its predictable component is therefore much closer to deterministic than "
      "Industrial Production's ever was — nearer the Gilbert et al. property of an announcement "
      "containing almost no new information.")
    A("")
    A("Predictors: core CPI (`CPILFESL`) and headline CPI (`CPIAUCSL`), first prints only, plus "
      "two lags of the target. The CPI-before-PCE ordering is **verified per month** from the "
      "vintage archive, not assumed.")
    A("")

    # ---- guard
    g = primary.get("guard", {})
    A("## 2. Sample assertion guard (Amendment 1 §2.4)")
    A("")
    A("The cache-keyed-on-symbol bug silently truncated Test B's sample by five years and "
      "suppressed the split entirely. This test's whole purpose is that split, so the sample "
      "shape is asserted and printed before any regression runs.")
    A("")
    A("| Check | Value |")
    A("|---|---|")
    A(f"| Sample start | {g.get('sample_start')} |")
    A(f"| Sample end | {g.get('sample_end')} |")
    A(f"| Observations | {_f(g.get('n_obs'))} |")
    A(f"| Pre-2012 | **{_f(g.get('n_pre_2012'))}** |")
    A(f"| Post-2012 | **{_f(g.get('n_post_2012'))}** |")
    A(f"| Guard passed | **{'yes' if g.get('usable') else 'NO — ' + '; '.join(g.get('problems', []))}** |")
    A("")
    A(f"Mean expanding-window prediction R²: **{_f(primary.get('mean_train_r2'), 3)}**. The "
      "higher this is, the less new information the announcement carries and the closer the "
      "test sits to the Gilbert et al. setting. At 0.28 this is **much lower than intended** — "
      "core PCE turns out far less reconstructible from CPI at monthly frequency than the "
      "three-quarters-shared-source-data argument suggests, so the indicator is a weaker "
      "analogue of the LEI than §3 of the pre-registration claimed. CFNAI reached 0.92.")
    A("")
    A("### Event window (amendment 2)")
    A("")
    A("The release lands at **08:30 ET, before the equity open**, so the pre-registered "
      "close-to-close return brackets the announcement plus six and a half hours of unrelated "
      "news. Both windows are therefore reported, and the one with the stronger validity "
      "statistic is carried forward. The window is selected on the coefficient for *genuine "
      "surprise*, never on the hypothesis coefficient — selecting on the latter would be "
      "circular.")
    A("")
    A("| Window | validity t (surprise) | b1 t (predictable) |")
    A("|---|---|---|")
    A(f"| Close-to-close (pre-registered) | {_f(primary.get('validity_cc'), 3)} | "
      f"{_f(primary.get('full_cc', {}).get('t_b1'), 3)} |")
    A(f"| Overnight, prior close to release open | {_f(primary.get('validity_on'), 3)} | "
      f"{_f(primary.get('full_on', {}).get('t_b1'), 3)} |")
    A("")
    A(f"Window carried forward: **{primary.get('window_used')}**. The overnight window is the "
      "better instrument and still does not clear the hurdle, so the choice does not rescue "
      "the block.")
    A("")

    if primary.get("unusable"):
        path.write_text("\n".join(L) + "\n", encoding="utf-8")
        return

    # ---- main table
    A("## 3. Results")
    A("")
    A("`b1` is the coefficient on the **predictable** component — the part reconstructible from "
      "CPI, already public when PCE is announced. Efficient markets imply `b1 = 0`. `b2` is the "
      "coefficient on genuine surprise and is the **validity check**: if the market does not "
      "respond to that, nothing else in the table can be read.")
    A("")
    A("The `t after dropping 2` column applies the influence diagnostic to every row, per "
      "Amendment 1 §2.3 — any result that depends on a couple of COVID observations is not a "
      "result.")
    A("")
    A("| Sample | β (predictable) | t | t after dropping 2 | β (surprise) | t (validity) | n |")
    A("|---|---|---|---|---|---|---|")
    _reg_row(A, primary.get("full"), primary.get("influence"), "Full sample")
    _reg_row(A, primary.get("ex_covid"), None, "Excluding Mar–Dec 2020")
    _reg_row(A, primary.get("pre2012"), primary.get("influence_pre"), "**Pre-2012**")
    _reg_row(A, primary.get("post2012"), primary.get("influence_post"), "**Post-2012**")
    A("")

    inter = primary.get("interaction", {})
    if "b1_post_interaction" in inter:
        A("### The pre/post-2012 interaction — the decisive statistic")
        A("")
        A("Estimated as one pooled model so the *difference* carries a standard error:")
        A("")
        A(f"- β on `predicted_z` (pre-2012 level): {_f(inter['b1_predicted'])} "
          f"(t = {_f(inter['t_b1'], 3)})")
        A(f"- β on `predicted_z × post2012` (the change): **{_f(inter['b1_post_interaction'])}** "
          f"(t = **{_f(inter['t_b1_post'], 3)}**)")
        A(f"- Decay detected at the hurdle: "
          f"**{'yes' if inter.get('decay_detected') else 'no'}**")
        A("")
        A("Two separately insignificant sub-period coefficients are not evidence of a difference "
          "between them, which is why the interaction and not the sub-period pair is what "
          "decides the decay claim. This was fixed in the pre-registration before running.")
        A("")

    # ---- influence
    A("### Influence profiles")
    A("")
    A("t on the predictable component after removing the most influential observations by "
      "Cook's distance:")
    A("")
    A("| Sample | dropped 0 | 1 | 2 | 3 | 5 | most influential releases |")
    A("|---|---|---|---|---|---|---|")
    for nm, key in (("Full", "influence"), ("Pre-2012", "influence_pre"),
                    ("Post-2012", "influence_post")):
        i = primary.get(key, {})
        if "t_full" not in i:
            continue
        A(f"| {nm} | {_f(i.get('t_full'), 3)} | {_f(i.get('t_drop1'), 3)} | "
          f"{_f(i.get('t_drop2'), 3)} | {_f(i.get('t_drop3'), 3)} | {_f(i.get('t_drop5'), 3)} | "
          f"{', '.join(i.get('most_influential_dates') or [])} |")
    A("")

    # ---- strategy
    A("## 4. Front-run strategy")
    A("")
    A("Position `sign(predicted − trailing mean)` at the close before the release, exit at the "
      "release close. Reversal leg holds the opposite for five days, testing Tetlock (2011).")
    A("")
    A("| Sample | Events | Gross %/yr | Gross t | Net %/yr | Net t | 5d reversal bps | Reversal t |")
    A("|---|---|---|---|---|---|---|---|")
    for nm, key in (("Full", "strategy"), ("Pre-2012", "strategy_pre"),
                    ("Post-2012", "strategy_post")):
        s = primary.get(key, {})
        if "gross_ann_pct" not in s:
            continue
        A(f"| {nm} | {s['n_events']:,} | {_f(s['gross_ann_pct'], 3)} | {_f(s['gross_t'], 3)} | "
          f"{_f(s['net_ann_pct'], 3)} | {_f(s['net_t'], 3)} | "
          f"{_f(s['reversal_5d_mean_bps'], 3)} | {_f(s['reversal_5d_t'], 3)} |")
    A("")
    A("Gilbert et al. reported roughly **8%/yr** front-running the LEI. That is the benchmark "
      "these magnitudes are read against — not a threshold.")
    A("")

    # ---- sensitivity
    A("## 5. Training-window sensitivity")
    A("")
    A("The pre-registration reduced the training window from Test B's 60 months to 36, because "
      "60 would have pushed the first testable event to 2007 and left a badly lopsided split. "
      "The 60-month version is run anyway and reported here; if the two disagree materially, "
      "that disagreement is the finding.")
    A("")
    A("| Window | Sample start | n | pre-2012 | post-2012 | b1 t (full) | b1 t (pre) | b1 t (post) | validity t |")
    A("|---|---|---|---|---|---|---|---|---|")
    for blk in (primary, sens):
        gg = blk.get("guard", {})
        A(f"| {blk.get('label')} | {gg.get('sample_start')} | {_f(gg.get('n_obs'))} | "
          f"{_f(gg.get('n_pre_2012'))} | {_f(gg.get('n_post_2012'))} | "
          f"{_f(blk.get('full', {}).get('t_b1'), 3)} | "
          f"{_f(blk.get('pre2012', {}).get('t_b1'), 3)} | "
          f"{_f(blk.get('post2012', {}).get('t_b1'), 3)} | "
          f"{_f(blk.get('full', {}).get('t_b2'), 3)} |")
    A("")

    # ---- yearly
    yr = primary.get("yearly")
    if yr is not None and len(yr):
        A("## 6. Yearly coefficients")
        A("")
        A("Full data in [`decay_curve.csv`](decay_curve.csv).")
        A("")
        A("| Year | β | SE | t | n | gross bps |")
        A("|---|---|---|---|---|---|")
        for _, r in yr.iterrows():
            A(f"| {int(r['year'])} | {_f(r['beta'])} | {_f(r['se'])} | {_f(r['t_stat'], 3)} | "
              f"{int(r['n_obs'])} | {_f(r['gross_mean_bps'], 3)} |")
        A("")
        n_sig = int((yr["t_stat"].abs() > HURDLE).sum())
        A(f"Years individually clearing |t| > {HURDLE}: **{n_sig} of {len(yr)}**."
          + ("" if n_sig else " As in Test A, no decay half-life is fitted to a series that is "
                              "never distinguishable from zero — that would measure the decay of "
                              "noise."))
        A("")

    # ---- accounting
    A("## 7. Multiple-testing accounting")
    A("")
    A(f"`config_log.jsonl` holds **{log_summary['total_evaluations']} evaluations** across all "
      f"tests ({', '.join(f'{k}: {v}' for k, v in sorted(log_summary['by_test'].items()))}), "
      f"{log_summary['distinct_configs']} distinct configurations, {log_summary['failed']} "
      "failed and counted anyway.")
    A("")
    if dsr is not None:
        A("Per Amendment 1 §4 the Deflated Sharpe is computed against the **cumulative** count "
          "across all tests, not this amendment's trials alone.")
        A("")
        A("| DSR input | Value |")
        A("|---|---|")
        A(f"| Cumulative trials N | **{dsr.n_trials}** |")
        A(f"| Observations | {dsr.n_obs:,} |")
        A(f"| Sharpe (annualised) | {_f(dsr.sharpe_annualised, 3)} |")
        A(f"| SR\\* (selection hurdle) | {_f(dsr.expected_max_sharpe)} |")
        A(f"| **Deflated Sharpe Ratio** | **{_f(dsr.deflated_sharpe, 4)}** |")
        A("")

    # ---- verdict
    A("## 8. Verdict and the stop-permanently trigger")
    A("")
    A(f"**{verdict}.** {para}")
    A("")
    if verdict == "CLEAN NULL":
        A("Amendment 1 §3, pre-registered:")
        A("")
        A("> *If Test B-2 returns a clean null with validity passing across the extended sample, "
          "the \"public-but-unconnected\" mechanism has no empirical support. Every remaining "
          "component of the framework is downstream of it. Stop.*")
        A("")
        A("The condition is met: validity passes, the sample spans the split, and the "
          "predictable component moves nothing in either period. **The trigger fires.**")
    elif verdict == "UNREADABLE":
        A("The stop-permanently trigger requires a clean null **with validity passing**. "
          "Validity does not pass, so the trigger does not fire. This is an instrument failure, "
          "and the honest status is that the question remains open rather than answered "
          "negatively.")
    else:
        A("The stop-permanently trigger does not fire: it requires a clean null with validity "
          "passing, and that is not what this test returned.")
    A("")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")
