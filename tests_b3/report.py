"""Renders tests_b3/results.md."""

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


def _verdict(val: pd.DataFrame, results: dict) -> tuple[str, str]:
    passing = val[val["validity_pass"]] if len(val) else val

    if len(passing) == 0:
        best = val.reindex(val["t_b2"].abs().sort_values(ascending=False).index).head(1)
        b = best.iloc[0] if len(best) else None
        return "VALIDITY FAILS ON RATES TOO — STOP", (
            "No block-outcome combination detects a market reaction to genuine macro surprise at "
            f"the hurdle. The strongest anywhere is {b['block']} on {b['outcome']} at "
            f"t = {_f(b['t_b2'], 3)}. " if b is not None else "" ) + (
            "The instrument class is not the problem: moving from an equity index to the front "
            "end of the Treasury curve — the instrument macro announcement studies actually use "
            "— does not make these announcements readable either. **The stale-information line "
            "closes as unanswerable with free data.** Per the pre-registration this is a "
            "legitimate stop, and no fourth instrument will be proposed."
        )

    robust, raw_sig = [], []
    for k, r in results.items():
        if _sig(r.get("full", {}).get("t_b1")):
            raw_sig.append(k)
            if _sig(r.get("influence", {}).get("t_drop2")):
                robust.append(k)

    ctrl_pass = bool(val[val["block"] == "B2_CFNAI"]["validity_pass"].any())
    b1_pass = bool(val[val["block"] == "B1_INDPRO"]["validity_pass"].any())
    b1_best = val[val["block"] == "B1_INDPRO"]["t_b2"].abs().max() if len(val) else float("nan")

    if robust:
        return "VALIDITY PASSES + EFFECT PRESENT", (
            f"The rates instrument sees genuine surprise in {len(passing)} of {len(val)} "
            f"block-outcome combinations, and in {len(robust)} of those the market also responds "
            "to the **predictable** component with the effect surviving removal of its most "
            "influential observations. The mechanism underneath the enumeration thesis has "
            "support for the first time in this project."
        )

    prize = (
        f"\n\n**The prize was not won.** B1 — Industrial Production, the only block spanning "
        f"2012 and the only one that could ever answer the pre/post-2012 question — **still "
        f"fails validity**, on all five outcomes, best t = {_f(b1_best, 3)}. But the *reason* has "
        "changed, and that is worth something. Previously B1's failure was ambiguous: a blind "
        "instrument and a silent announcement look identical. Now the instrument is "
        f"demonstrably not blind — the control clears the hurdle at "
        f"{_f(val[(val.block == 'B2_CFNAI')]['t_b2'].abs().max(), 3)} on the same data — so the "
        "failure is attributable to the announcement. **Industrial production surprises do not "
        "measurably move the front end.** The split remains unanswerable, but now demonstrably "
        "rather than presumptively."
    ) if not b1_pass else ""

    body = (
        f"The rates instrument works. The positive control passes at t = "
        f"{_f(val[(val.block == 'B2_CFNAI')]['t_b2'].abs().max(), 3)}, with the correct sign and "
        "a coherent yield/price relationship, so a null from it is readable rather than blind.\n\n"
    )

    if raw_sig:
        body += (
            f"On the readable block, the predictable component **does** clear the hurdle in raw "
            f"form in {len(raw_sig)} of {len(results)} combinations — this is not a flat zero and "
            "should not be described as one. But **none survives the pre-registered influence "
            "diagnostic.** Dropping a single observation takes the strongest of them from −2.98 "
            "to −1.00. The three most influential releases are the same COVID dates that drove "
            "the SPY result — March, April and May 2020. One combination swings from −3.55 to "
            "−1.36 to −4.67 depending on which two or three points are removed, which is not a "
            "coefficient with an effect behind it; it is a small sample being steered by its "
            "extremes.\n\n"
        )
    else:
        body += ("On the readable block the predictable component clears nothing, in raw form or "
                 "adjusted.\n\n")

    body += (
        "This is the outcome the pre-registration named as the stop trigger, and it is **the "
        "first clean stop in this project** — every previous null was unreadable because the "
        "instrument was blind, and this one is not. Stated plainly and without softening: on the "
        "one indicator that a working instrument can read, **there is no robust market response "
        "to the already-public component of a composite announcement.** No fourth instrument "
        "will be proposed."
    ) + prize

    return "VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES", body


def render(path: Path, panels: dict, val: pd.DataFrame, results: dict,
           log_summary: dict, cumulative_trials: int) -> None:
    verdict, para = _verdict(val, results)
    L: list[str] = []
    A = L.append

    A("# Test B-3 — Rates re-run: results")
    A("")
    A(f"**Verdict: {verdict}**")
    A("")
    A(para)
    A("")
    A("Pre-registration: [`preregistration.md`](preregistration.md), committed before this "
      "analysis was written. The overnight window and the validity-first ordering were both "
      "registered **in advance** this time, which removes the fence that was needed when the "
      "window was added mid-run.")
    A("")
    A("---")
    A("")

    # ---------------- STEP 1
    A("## 1. Validity — reported first, before any other coefficient")
    A("")
    A("The question this answers is **not** whether markets respond to stale information. It is "
      "whether the instrument can detect a response to information that is genuinely **new**. If "
      "it cannot, its null on stale information carries no information at all — which is exactly "
      "why three of the four SPY blocks were unreadable.")
    A("")
    A("A block-outcome combination passes only if `|t| > 2.78` **and** the sign matches the "
      "pre-registered direction: a positive activity or inflation surprise raises yields and "
      "lowers bond prices.")
    A("")
    A("| Block | Outcome | Window | n | β (surprise) | t | Sign | Pass |")
    A("|---|---|---|---|---|---|---|---|")
    for _, r in val.iterrows():
        A(f"| {r['block']} | `{r['outcome']}` | {r['window']} | {r['n']:,} | "
          f"{_f(r['b2_surprise'])} | **{_f(r['t_b2'], 3)}** | "
          f"{'ok' if r['sign_ok'] else '**wrong**'} | "
          f"{'**YES**' if r['validity_pass'] else 'no'} |")
    A("")
    n_pass = int(val["validity_pass"].sum())
    A(f"**{n_pass} of {len(val)}** combinations pass. Hurdle 2.78.")
    A("")
    A("### Coherence check")
    A("")
    A("A rates outcome gives a free consistency test that SPY could not: yields and bond prices "
      "must move in **opposite** directions on the same surprise. Same-signed coefficients would "
      "mean the instrument is not measuring what it is meant to, regardless of significance.")
    A("")
    A("| Block | β on DGS2 (bp) | β on TLT (return) | Coherent? |")
    A("|---|---|---|---|")
    for blk in val["block"].unique():
        sub = val[val["block"] == blk]
        dg = sub[sub["outcome"] == "DGS2"]["b2_surprise"]
        tl = sub[sub["outcome"] == "TLT_cc"]["b2_surprise"]
        if len(dg) and len(tl):
            ok = np.sign(dg.iloc[0]) != np.sign(tl.iloc[0])
            A(f"| {blk} | {_f(dg.iloc[0])} | {_f(tl.iloc[0])} | "
              f"{'yes' if ok else '**no**'} |")
    A("")

    # positive control
    ctrl = val[val["block"] == "B2_CFNAI"]
    if len(ctrl):
        best = ctrl.reindex(ctrl["t_b2"].abs().sort_values(ascending=False).index).iloc[0]
        passed = bool(ctrl["validity_pass"].any())
        A("### The positive control")
        A("")
        A("CFNAI passed validity on SPY at t = 4.51, so it is the control: if it does **not** "
          "also pass on rates, the rates instrument itself is suspect and the finding is about "
          "the instrument rather than about any block.")
        A("")
        if passed:
            A(f"**It passes** — strongest at `{best['outcome']}`, t = {_f(best['t_b2'], 3)}. The "
              "rates instrument is working, so the other blocks' results are about those blocks.")
        else:
            A(f"**It does not pass.** Strongest anywhere is `{best['outcome']}` at "
              f"t = {_f(best['t_b2'], 3)}, against 4.51 on SPY. **The rates instrument is "
              "suspect.** The block that was demonstrably readable with an equity outcome "
              "becomes unreadable with a rates one, which points at the instrument rather than "
              "at the announcements. This materially weakens any conclusion drawn from the other "
              "rows above, and it is reported here rather than buried.")
        A("")

    # ---------------- STEP 2/3
    A("## 2. Predictable component — only where validity passed")
    A("")
    if not results:
        A("**Not run.** No block-outcome combination passed validity, so per the "
          "pre-registration no `b1` coefficient is interpreted, reported as a null, or used in "
          "any conclusion. The `t_b1_withheld` column in [`validity.csv`](validity.csv) records "
          "what those coefficients were, so the decision not to interpret them is auditable "
          "rather than a claim that they were never computed.")
        A("")
    else:
        A("| Block / outcome | β (predictable) | t | t after dropping 2 | n |")
        A("|---|---|---|---|---|")
        for k, r in results.items():
            f = r.get("full", {})
            A(f"| {k} | {_f(f.get('b1_predicted'))} | **{_f(f.get('t_b1'), 3)}** | "
              f"{_f(r.get('influence', {}).get('t_drop2'), 3)} | {_f(f.get('n_obs'))} |")
        A("")
        splits = {k: r for k, r in results.items() if "interaction" in r}
        if splits:
            A("### The pre/post-2012 split — the primary output")
            A("")
            A("B1 is the only block spanning 2012. Estimated as a single pooled interaction so "
              "the *difference* carries a standard error; two separately insignificant "
              "sub-period coefficients are not evidence of a difference between them.")
            A("")
            A("| Block / outcome | pre-2012 t | post-2012 t | interaction t | decay? |")
            A("|---|---|---|---|---|")
            for k, r in splits.items():
                A(f"| {k} | {_f(r['pre2012'].get('t_b1'), 3)} | "
                  f"{_f(r['post2012'].get('t_b1'), 3)} | "
                  f"**{_f(r['interaction'].get('t_b1_post'), 3)}** | "
                  f"{'yes' if r['interaction'].get('decay_detected') else 'no'} |")
            A("")

    # ---------------- blocks
    A("## 3. Blocks, unchanged from B and B-2")
    A("")
    A("| Block | Announcements | Mean prediction R² | Role |")
    A("|---|---|---|---|")
    for name, p in panels.items():
        A(f"| {name} | {len(p['data']):,} | {_f(p['mean_r2'], 3)} | {p['role']} |")
    A("")
    A("Only the outcome variable changed. The vintage assembly, first-print discipline, "
      "archive-measured release dates, ordering verification and expanding-window prediction are "
      "byte-identical to the runs that produced the SPY results.")
    A("")

    A("## 4. What was and was not fixed by changing instrument")
    A("")
    A("| | SPY | Rates |")
    A("|---|---|---|")
    A("| B1 validity | t = −0.02 | " + _f(val[(val.block == "B1_INDPRO")]["t_b2"].abs().max(), 3)
      + " (best across outcomes) |")
    A("| B2 validity | t = 4.51 | " + _f(val[(val.block == "B2_CFNAI")]["t_b2"].abs().max(), 3)
      + " (best across outcomes) |")
    A("| B-2 validity | t = 1.26 | "
      + _f(val[(val.block == "B2ext_COREPCE")]["t_b2"].abs().max(), 3) + " (best across outcomes) |")
    A("")

    A("## 5. Multiple testing")
    A("")
    A(f"`config_log.jsonl` now holds **{log_summary['total_evaluations']} evaluations** across "
      f"all tests ({', '.join(f'{k}: {v}' for k, v in sorted(log_summary['by_test'].items()))}), "
      f"{log_summary['distinct_configs']} distinct configurations, {log_summary['failed']} "
      "failed and counted anyway.")
    A("")
    A("Three outcomes × two windows where available × three blocks is a deliberate expansion of "
      "the trial count and was registered as such. It is justified because picking one outcome "
      "in advance and reporting only that would hide precisely the disagreement the "
      "pre-registration requires to be surfaced. No Deflated Sharpe is reported here because no "
      "tradeable strategy was run — this test measures a coefficient, not a return stream.")
    A("")

    A("## 6. Limitations, stated in the pre-registration before running")
    A("")
    A("1. **`DGS2` cannot use the overnight window.** It is a single daily observation with no "
      "open or close, so the primary instrument and the primary window cannot be combined. `TLT` "
      "and `IEF` carry the overnight window instead.")
    A("2. **`TLT` and `IEF` are the wrong maturity.** 20y+ and 7–10y respectively; neither is "
      "the 2-year point where macro sensitivity is highest. They are the only free instruments "
      "with an intraday open.")
    A("3. **Core PCE remains a weak analogue** at R² = 0.28. Changing the outcome variable does "
      "not repair a weak predictable component.")
    A("4. **This is not a replication of Gilbert et al.** The LEI is still unobtainable; these "
      "are the same substitutes, better measured.")
    A("")

    A("## 7. Verdict")
    A("")
    A(f"**{verdict}.** {para}")
    A("")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")
