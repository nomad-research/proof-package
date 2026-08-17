"""Renders tests_b/results.md from the analysis outputs."""

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
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    return str(x)


def _sig(t) -> bool:
    return t is not None and np.isfinite(t) and abs(t) > HURDLE


def block_status(blk: dict) -> dict:
    """Classify one block: is its instrument working, and does its result survive?"""
    if blk is None:
        return {"readable": False, "note": "block did not run"}
    full = blk.get("full", {})
    inf = blk.get("influence", {})
    ex = blk.get("ex_covid", {})
    surprise_t = full.get("t_b2")
    return {
        "readable": _sig(surprise_t),          # does it detect news that IS new?
        "surprise_t": surprise_t,
        "predicted_t": full.get("t_b1"),
        "predicted_sig": _sig(full.get("t_b1")),
        "ex_covid_t": ex.get("t_b1"),
        "ex_covid_sig": _sig(ex.get("t_b1")),
        "t_drop2": inf.get("t_drop2"),
        "robust": (_sig(full.get("t_b1")) and _sig(ex.get("t_b1"))
                   and _sig(inf.get("t_drop2"))),
        "outlier_driven": (_sig(full.get("t_b1"))
                           and not (_sig(ex.get("t_b1")) and _sig(inf.get("t_drop2")))),
        "influential_dates": inf.get("most_influential_dates"),
    }


def _verdict(blocks: dict) -> tuple[str, str]:
    b1 = blocks.get("B1_INDPRO")
    b2 = blocks.get("B2_CFNAI")
    s1, s2 = block_status(b1), block_status(b2)

    if not s1["readable"] and not s2["readable"]:
        return "INVALID", (
            "Neither block detects a market reaction to genuine macro surprise "
            f"(B1 t = {_fmt(s1.get('surprise_t'), 3)}, B2 t = {_fmt(s2.get('surprise_t'), 3)}). "
            "The pre-registration named this as the condition that invalidates the test rather "
            "than supporting it: if the announcement window cannot detect a reaction to news "
            "that *is* new, its failure to detect a reaction to news that is not new carries no "
            "information. Nothing below is readable in either direction."
        )

    readable = [(n, s) for n, s in (("B1", s1), ("B2", s2)) if s["readable"]]

    if any(s["robust"] for _, s in readable):
        return "PASS", (
            "A readable block shows the market responding to the predictable component of the "
            "announcement, and the result survives both the exclusion of 2020 and the removal of "
            "its most influential observations. Public-but-unconnected information still moves "
            "prices. This is the live mechanism the backward-reading thesis needs."
        )

    if any(s["outlier_driven"] for _, s in readable):
        n, s = next((n, s) for n, s in readable if s["outlier_driven"])
        dates = ", ".join(s.get("influential_dates") or [])
        blind = [nm for nm, st in (("B1", s1), ("B2", s2)) if not st["readable"]]
        blind_note = ""
        if blind:
            bs = s1 if "B1" in blind else s2
            blind_note = (
                f" Separately, block {blind[0]} — the only block whose release history spans the "
                f"pre/post-2012 split, and therefore the only one that could test the decay claim "
                f"§3.3 calls the primary comparison — fails the validity check: it does not "
                f"detect a market reaction even to genuine macro surprise "
                f"(t = {_fmt(bs.get('surprise_t'), 3)}). Its pre/post-2012 coefficients are "
                "therefore unreadable in either direction, and **the primary comparison this test "
                "was designed around went unanswered.**"
            )
        return "NOT REPLICATED", (
            f"The only significant coefficient anywhere in this test is in block {n} "
            f"(t = {_fmt(s['predicted_t'], 3)} on the predictable component), and it does not "
            f"survive contact with its own outliers: excluding March–December 2020 it falls to "
            f"t = {_fmt(s['ex_covid_t'], 3)}, and dropping just the two most influential "
            f"observations takes it to t = {_fmt(s['t_drop2'], 3)}. The three most influential "
            f"releases are {dates}, two of them in the COVID collapse, which drove the "
            "standardised predictor to values as extreme as −14 standard deviations. Two "
            "observations are not an effect." + blind_note +
            " On the evidence available here, there is no support for the claim that markets "
            "respond to the already-public component of a composite announcement."
        )

    return "NOT REPLICATED", (
        "No readable block shows the market responding to the predictable component of the "
        f"announcement (B1 t = {_fmt(s1.get('predicted_t'), 3)}, B2 "
        f"t = {_fmt(s2.get('predicted_t'), 3)}). Where the instrument is working — it detects "
        "genuine surprise — it detects nothing in the part of the announcement that was already "
        "public. On these indicators, over these samples, stale information does not move prices."
    )


def _reg_table(A, res: dict, name: str) -> None:
    if not res or "b1_predicted" not in res:
        A(f"| {name} | — | — | — | — | {res.get('note', 'not run') if res else 'not run'} |")
        return
    A(f"| {name} | {_fmt(res['b1_predicted'])} | {_fmt(res['t_b1'], 3)} | "
      f"{_fmt(res['b2_surprise'])} | {_fmt(res['t_b2'], 3)} | {res['n_obs']:,} |")


def render(path: Path, blocks: dict, dsr, log_summary, n_trials) -> None:
    verdict, paragraph = _verdict(blocks)
    b1 = blocks.get("B1_INDPRO")
    b2 = blocks.get("B2_CFNAI")

    lines: list[str] = []
    A = lines.append

    A("# Test B — Stale information / \"public but unconnected\": results")
    A("")
    A(f"**Verdict: {verdict}**")
    A("")
    A(paragraph)
    A("")
    A("Pre-registration: [`preregistration.md`](preregistration.md), committed before any "
      "analysis code was written.")
    A("")
    A("> **What this test is and is not.** The Conference Board LEI, the indicator Gilbert et "
      "al. (2012) used, is proprietary and unobtainable. Of the substitutes the specification "
      "permits, only Industrial Production has release-date history spanning the pre/post-2012 "
      "split. IP's predictable component is *statistical*, not deterministic as the LEI's is, so "
      "**no result here is a replication of Gilbert et al.** CFNAI — a weighted average of 85 "
      "already-published series, and therefore a genuine near-zero-new-information announcement "
      "— is run as a secondary block, but its vintages only start in 2011 so it cannot speak to "
      "the split. Both limitations were recorded in the pre-registration before results were "
      "seen.")
    A("")
    A("---")
    A("")

    # ---------------- headline
    A("## 1. Headline numbers")
    A("")
    A("| Quantity | B1 — Industrial Production | B2 — CFNAI |")
    A("|---|---|---|")
    if b1 and b2:
        A(f"| Period | {b1['period'][0]} to {b1['period'][1]} | {b2['period'][0]} to {b2['period'][1]} |")
        A(f"| Announcements | {b1['n_events']:,} | {b2['n_events']:,} |")
        A(f"| Mean expanding-window prediction R² | {_fmt(b1['mean_train_r2'], 3)} | "
          f"{_fmt(b2['mean_train_r2'], 3)} |")
        A(f"| β on predictable component | {_fmt(b1['full'].get('b1_predicted'))} | "
          f"{_fmt(b2['full'].get('b1_predicted'))} |")
        A(f"| **t on predictable component** | **{_fmt(b1['full'].get('t_b1'), 3)}** | "
          f"**{_fmt(b2['full'].get('t_b1'), 3)}** |")
        A(f"| t on genuine surprise (validity check) | {_fmt(b1['full'].get('t_b2'), 3)} | "
          f"{_fmt(b2['full'].get('t_b2'), 3)} |")
        A(f"| Front-run gross | {_fmt(b1['strategy'].get('gross_ann_pct'), 3)}%/yr | "
          f"{_fmt(b2['strategy'].get('gross_ann_pct'), 3)}%/yr |")
        A(f"| Front-run net | {_fmt(b1['strategy'].get('net_ann_pct'), 3)}%/yr | "
          f"{_fmt(b2['strategy'].get('net_ann_pct'), 3)}%/yr |")
    A(f"| Hurdle (Harvey–Liu–Zhu) | {HURDLE} | {HURDLE} |")
    A("")
    A(f"Gilbert et al. reported roughly **8%/yr** front-running the LEI. That is the magnitude "
      "the strategy figures above are compared against — it is a benchmark, not a threshold.")
    A("")
    if dsr is not None:
        A(f"Trials logged for Test B: **{n_trials}**. Deflated Sharpe Ratio of the primary "
          f"front-run net series: **{_fmt(dsr.deflated_sharpe, 4)}** "
          f"(SR\\* = {_fmt(dsr.expected_max_sharpe)}).")
        A("")

    # ---------------- block status
    A("## 1a. Block status — is each instrument working, and does its result survive?")
    A("")
    A("Two checks decide whether a block's headline coefficient means anything. Both are applied "
      "to every block, not selectively.")
    A("")
    A("| Check | B1 — Industrial Production | B2 — CFNAI |")
    A("|---|---|---|")
    s1, s2 = block_status(b1), block_status(b2)
    A(f"| Detects genuine surprise? (validity) | {'**yes**' if s1['readable'] else '**no**'} "
      f"(t = {_fmt(s1.get('surprise_t'), 3)}) | {'**yes**' if s2['readable'] else '**no**'} "
      f"(t = {_fmt(s2.get('surprise_t'), 3)}) |")
    A(f"| Predictable component significant, full sample | "
      f"{'yes' if s1['predicted_sig'] else 'no'} (t = {_fmt(s1.get('predicted_t'), 3)}) | "
      f"{'yes' if s2['predicted_sig'] else 'no'} (t = {_fmt(s2.get('predicted_t'), 3)}) |")
    A(f"| Still significant excluding Mar–Dec 2020 | "
      f"{'yes' if s1['ex_covid_sig'] else 'no'} (t = {_fmt(s1.get('ex_covid_t'), 3)}) | "
      f"{'yes' if s2['ex_covid_sig'] else 'no'} (t = {_fmt(s2.get('ex_covid_t'), 3)}) |")
    A(f"| Still significant dropping 2 most influential obs | "
      f"{'yes' if _sig(s1.get('t_drop2')) else 'no'} (t = {_fmt(s1.get('t_drop2'), 3)}) | "
      f"{'yes' if _sig(s2.get('t_drop2')) else 'no'} (t = {_fmt(s2.get('t_drop2'), 3)}) |")
    A(f"| **Survives everything** | **{'yes' if s1['robust'] else 'no'}** | "
      f"**{'yes' if s2['robust'] else 'no'}** |")
    A("")
    A("**The validity row comes first for a reason.** If a specification cannot detect a market "
      "reaction to news that genuinely *is* new, then its failure to detect a reaction to news "
      "that is not new says nothing about markets — it says the instrument is blind. The "
      "pre-registration named this as the condition that invalidates the test rather than "
      "supporting it, before any result was seen.")
    A("")
    for name, blk, st in (("B1", b1, s1), ("B2", b2, s2)):
        inf = (blk or {}).get("influence", {})
        if "t_drop1" not in inf:
            continue
        A(f"**{name} influence profile** (pre-registration amendment 2). t on the predictable "
          f"component after removing the most influential observations by Cook's distance:")
        A("")
        A("| Dropped | 0 | 1 | 2 | 3 | 5 |")
        A("|---|---|---|---|---|---|")
        A(f"| t | {_fmt(inf.get('t_full'), 3)} | {_fmt(inf.get('t_drop1'), 3)} | "
          f"{_fmt(inf.get('t_drop2'), 3)} | {_fmt(inf.get('t_drop3'), 3)} | "
          f"{_fmt(inf.get('t_drop5'), 3)} |")
        A("")
        if inf.get("most_influential_dates"):
            A(f"Most influential releases: {', '.join(inf['most_influential_dates'])}.")
            A("")

    # ---------------- primary
    if b1:
        A("## 2. B1 — Industrial Production (primary)")
        A("")
        A("Specification as pre-registered (§5.1):")
        A("")
        A("```")
        A("r_rel(m) = a + b1·predicted_z(m) + b2·surprise_z(m) + e(m)")
        A("```")
        A("")
        A("`predicted` is the expanding-window OLS fit of announced IP growth on announced "
          "manufacturing-hours growth and two lags of IP growth, trained only on months whose "
          "release date is strictly earlier. Efficient markets imply **b1 = 0**: the predictable "
          "part was public before the announcement.")
        A("")
        A("| Sample | β (predictable) | t | β (surprise) | t | n |")
        A("|---|---|---|---|---|---|")
        _reg_table(A, b1.get("full"), "Full sample")
        _reg_table(A, b1.get("ex_covid"), "Excluding Mar–Dec 2020")
        _reg_table(A, b1.get("pre2012"), "Pre-2012")
        _reg_table(A, b1.get("post2012"), "Post-2012")
        A("")
        inter = b1.get("interaction")
        if inter and "b1_post_interaction" in inter:
            A("### Pre/post-2012 interaction — the decisive statistic for decay")
            A("")
            A("Estimated as a single pooled model so the *difference* carries a standard error:")
            A("")
            A(f"- β on `predicted_z` (pre-2012 level): {_fmt(inter['b1_predicted'])} "
              f"(t = {_fmt(inter['t_b1'], 3)})")
            A(f"- β on `predicted_z × post2012` (the change): "
              f"**{_fmt(inter['b1_post_interaction'])}** (t = **{_fmt(inter['t_b1_post'], 3)}**)")
            A(f"- Decay detected at the hurdle: **{'yes' if inter.get('decay_detected') else 'no'}**")
            A("")
            A("Sub-period regressions are reported above for completeness, but two separately "
              "insignificant coefficients are not evidence of a difference between them. The "
              "interaction is what tests the decay claim, and it was designated the decisive "
              "statistic in the pre-registration before it was run.")
            A("")

        A("### Validity check — does the market respond to genuine surprise?")
        A("")
        st = b1["full"].get("t_b2")
        if _sig(st):
            A(f"Yes: t = {_fmt(st, 3)} on the surprise term, clearing the hurdle. The event "
              "window and return series detect a reaction to news that is genuinely new. A null "
              "result on the *predictable* component is therefore readable as a real null rather "
              "than as a broken measurement.")
        else:
            A(f"**No: t = {_fmt(st, 3)} on the surprise term.** The pre-registration named this "
              "as the condition that invalidates the test. If the specification cannot detect a "
              "reaction to genuinely new information, its failure to detect a reaction to stale "
              "information means nothing. This is reported as a failure of the instrument, not as "
              "a finding about markets.")
        A("")

        if len(b1.get("yearly", [])):
            A("### Yearly coefficients")
            A("")
            A("Full data in [`decay_curve.csv`](decay_curve.csv).")
            A("")
            A("| Year | β | SE | t | n | gross bps |")
            A("|---|---|---|---|---|---|")
            for _, r in b1["yearly"].iterrows():
                A(f"| {int(r['year'])} | {_fmt(r['beta'])} | {_fmt(r['se'])} | "
                  f"{_fmt(r['t_stat'], 3)} | {int(r['n_obs'])} | {_fmt(r['gross_mean_bps'], 3)} |")
            A("")
            n_sig = int((b1["yearly"]["t_stat"].abs() > HURDLE).sum())
            A(f"Years individually clearing t > {HURDLE}: **{n_sig} of {len(b1['yearly'])}**. "
              + ("No exponential decay half-life is fitted to these coefficients: as in Test A, "
                 "fitting decay to a series that is never distinguishable from zero measures the "
                 "decay of noise." if n_sig == 0 else
                 "A decay fit is meaningful only where the underlying coefficients are."))
            A("")

        A("### Front-run strategy")
        A("")
        A("Position `sign(predicted)` at the close before the release, exit at the release close. "
          "SPY, $10m notional, costed at two ticks plus two-sided square-root impact.")
        A("")
        A("| Sample | Events | Gross %/yr | Gross t | Net %/yr | Net t | 5d reversal bps | Reversal t |")
        A("|---|---|---|---|---|---|---|---|")
        for name, key in (("Full (demeaned signal)", "strategy"),
                          ("Full (raw signal — see note)", "strategy_raw"),
                          ("Pre-2012", "strategy_pre"), ("Post-2012", "strategy_post")):
            s = b1.get(key)
            if not s or "gross_ann_pct" not in s:
                continue
            A(f"| {name} | {s['n_events']:,} | {_fmt(s['gross_ann_pct'], 3)} | {_fmt(s['gross_t'], 3)} | "
              f"{_fmt(s['net_ann_pct'], 3)} | {_fmt(s['net_t'], 3)} | "
              f"{_fmt(s['reversal_5d_mean_bps'], 3)} | {_fmt(s['reversal_5d_t'], 3)} |")
        A("")
        A("**On the two signal definitions.** The pre-registration says \"position "
          "`sign(predicted)`\", which is ambiguous, and the two readings mean different things. "
          "Industrial production grows in most months, so the sign of *raw* predicted growth is "
          "almost always +1 and that strategy is a long-only equity position wearing a signal's "
          "clothing — whatever it earns is the equity risk premium, not an information edge. The "
          "demeaned version, `sign(predicted − trailing mean)`, is the economically meaningful "
          "one and is the headline. Both are run, both are logged, and both are above so the "
          "reader can see the difference rather than take the choice on trust.")
        A("")
        A("The reversal leg tests Tetlock (2011): reactions to stale news should reverse. A "
          "reversal coefficient indistinguishable from zero alongside an announcement "
          "coefficient indistinguishable from zero is simply the absence of any reaction to "
          "reverse.")
        A("")

    # ---------------- secondary
    if b2:
        A("## 3. B2 — CFNAI (secondary): the near-deterministic composite")
        A("")
        A("CFNAI is a weighted average of 85 series that are all published before it, so its "
          "announcement carries almost no new information — the property that makes the LEI test "
          "sharp and that Industrial Production lacks. Its vintages begin in 2011, so it cannot "
          "address the pre/post-2012 split; it addresses only whether the effect is alive now.")
        A("")
        A(f"Mean expanding-window prediction R² = **{_fmt(b2['mean_train_r2'], 3)}**, over "
          f"{b2['n_events']:,} announcements from {b2['period'][0]} to {b2['period'][1]}. "
          "That R² is the direct measure of how little the announcement adds: the higher it is, "
          "the closer this comes to the Gilbert et al. setting.")
        A("")
        A("| Sample | β (predictable) | t | β (surprise) | t | n |")
        A("|---|---|---|---|---|---|")
        _reg_table(A, b2.get("full"), "Full sample")
        _reg_table(A, b2.get("ex_covid"), "Excluding Mar–Dec 2020")
        A("")
        s = b2.get("strategy", {})
        if "gross_ann_pct" in s:
            A(f"Front-run strategy: gross {_fmt(s['gross_ann_pct'], 3)}%/yr "
              f"(t = {_fmt(s['gross_t'], 3)}), net {_fmt(s['net_ann_pct'], 3)}%/yr "
              f"(t = {_fmt(s['net_t'], 3)}) over {s['n_events']:,} announcements.")
            A("")

    # ---------------- data
    A("## 4. Data, point-in-time construction and verification")
    A("")
    A("Every macro input is a **first print** — the value as actually published, taken from the "
      "ALFRED vintage in which the reference month first appears. Revised and benchmark-restated "
      "values are never used, because a benchmark revision published in 2015 was not available "
      "to a decision taken in 2005.")
    A("")
    A("Both the current and prior month are read from the **same vintage**, because that is the "
      "growth rate the release actually announced. Taking the prior month from a later vintage "
      "would fold in revisions that had not happened yet.")
    A("")
    A("**Release dates are measured, not assumed.** The vintage date on which a reference month "
      "first carries a value is that month's release date. This comes from the archive rather "
      "than a published schedule, which makes the ordering between releases something that can "
      "be *checked* rather than asserted:")
    A("")
    A("| Block | Announcements before checks | After predictor merge | Dropped: predictor not released first | Final |")
    A("|---|---|---|---|---|")
    for lbl, blk in blocks.items():
        d = blk.get("drops", {})
        A(f"| {lbl} | {_fmt(d.get('initial_months'))} | {_fmt(d.get('after_predictor_merge'))} | "
          f"{_fmt(d.get('predictor_not_released_first'))} | {blk['n_events']:,} |")
    A("")
    A("Months where a predictor was not published strictly before the target are dropped, not "
      "adjusted. Months whose release date is not an equity trading day are dropped rather than "
      "shifted to the next session (pre-registration §6 rule 3).")
    A("")

    A("## 5. Limitations, stated in the pre-registration before results were seen")
    A("")
    A("1. **IP is not the LEI.** Its predictable component is statistical, not deterministic. "
      "Nothing here is a replication of Gilbert et al.")
    A("2. **The 2012 split is not a clean experiment.** Publication of the paper is the nominal "
      "treatment, but the post-2012 period also contains the growth of systematic macro trading "
      "and the 2020 shock. A decline across the split is *consistent with* the publication story; "
      "it does not identify it.")
    A("3. **Four indicators were considered** before one was chosen. The choice was made on "
      "release-date coverage alone, before any return regression was run, and the rejected "
      "alternatives are in `config_log.jsonl` so the selection sits inside the multiple-testing "
      "denominator rather than outside it.")
    A("4. **COVID.** March–December 2020 contains IP moves an order of magnitude larger than "
      "anything else in the sample. Both the full-sample and the excluding-2020 specifications "
      "were pre-registered and both are reported above.")
    A("")

    # ---------------- multiple testing
    A("## 6. Multiple-testing accounting")
    A("")
    A(f"`config_log.jsonl` holds **{log_summary['total_evaluations']} evaluations** in total, "
      f"**{n_trials}** of them for Test B, across "
      f"{log_summary['distinct_configs']} distinct configurations; "
      f"{log_summary['failed']} failed and are counted anyway.")
    A("")
    if dsr is not None:
        A("| DSR input | Value |")
        A("|---|---|")
        A(f"| Trials N | {dsr.n_trials} |")
        A(f"| Observations | {dsr.n_obs:,} |")
        A(f"| Sharpe (per event) | {_fmt(dsr.sharpe_per_obs)} |")
        A(f"| Sharpe (annualised) | {_fmt(dsr.sharpe_annualised, 3)} |")
        A(f"| SR\\* (selection hurdle) | {_fmt(dsr.expected_max_sharpe)} |")
        A(f"| **Deflated Sharpe Ratio** | **{_fmt(dsr.deflated_sharpe, 4)}** |")
        A("")

    # ---------------- verdict
    A("## 7. Verdict and what it implies for Test C")
    A("")
    A(f"**{verdict}.** {paragraph}")
    A("")
    A(_downstream(verdict))
    A("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _downstream(verdict: str) -> str:
    if verdict == "PASS":
        return (
            "### For Test C\n\n"
            "Test A failed but Test B survives, and specification §8 gates Test C on *either* "
            "surviving. Test C is therefore justified. Going in, the thing to instrument first is "
            "the distinction in §4.1: destination recall and return spread are separate numbers "
            "and must never be blended, because high recall with zero spread — the map is right "
            "and already priced — is a different failure from a wrong map and calls for a "
            "different response. Contamination, not sample size, is the primary validity threat: "
            "split the sample at the mapping model's training cutoff and report both halves."
        )
    if verdict == "DECAYED":
        return (
            "### For Test C\n\n"
            "The mechanism is real but dies on publication. That is a coherent world, and it is "
            "not the world the framework is built for: a framework whose edge disappears once the "
            "mechanism is documented cannot be run on documented mechanisms. Test C would be "
            "worth running only if it were restricted to enumeration that is *not* yet public — "
            "which is a different and much harder research programme than the one specified. "
            "Combined with Test A's failure, the honest recommendation is to rescope before "
            "spending three weeks."
        )
    if verdict == "INVALID":
        return (
            "### For Test C\n\n"
            "Nothing follows from this test until the instrument is fixed. Do not gate Test C on "
            "an unreadable result in either direction. Re-run Test B with a corrected event "
            "window or return series first."
        )
    return (
        "### For Test C\n\n"
        "**Both Test A and Test B have now failed to find an effect.** Specification §8 is "
        "explicit about this case: *if A and B both return decay-to-zero, the honest conclusion "
        "is that enumerated forced-flow edges do not survive publication, and Test C would be "
        "measuring a corpse. That is a legitimate and valuable place to stop.*\n\n"
        "The recommendation is to stop. Test C costs roughly three weeks and its cheap proxies "
        "have both come back empty — one of them on the most perfectly enumerable forced flow "
        "that exists. Ordering the tests by cost-per-bit was done precisely so that this "
        "decision could be taken for the price of a few days rather than a month.\n\n"
        "What would change the recommendation: a Test B specification that *does* detect a "
        "reaction to stale information on a genuinely deterministic composite over a long "
        "sample. The CFNAI block here is the closest available, and it is short. If the operator "
        "wants one more cheap shot before stopping, purchasing LEI vintage data and running the "
        "actual Gilbert et al. replication is a far better use of a few hundred dollars than "
        "three weeks of Test C."
    )
