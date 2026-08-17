# Test B-2 — Stale information, extended across the 2012 split: results

**Verdict: UNREADABLE**

The extended sample fails the validity check: the market does not measurably respond to genuine core-PCE surprise either (t = 1.26). Amendment 1 §2.3 requires this check to be re-run on the extended sample precisely because passing on a short window does not guarantee passing on a long one, and it does not pass here. Everything below is unreadable in either direction. Per §2.5 this is **a gap, not a negative result**, and it does **not** fire the stop-permanently trigger.

Pre-registration: [`preregistration.md`](preregistration.md), committed before this analysis was run.

> **This is not CFNAI, and that was not a choice.** Amendment 1 §2.2 specifies extending CFNAI backwards using release dates archived by the Chicago Fed. Those dates could not be obtained: ALFRED's first CFNAI vintage is 2011-05-23, the Chicago Fed's `past-releases` page renders its list client-side with no JSON or AJAX endpoint in the served source (confirmed twice, including with an independent renderer), `/cfnai/archive` returns 404, and FRED's release-date API needs a key that cannot be obtained from this environment. The amendment forbids reconstructing release dates from a schedule, so the criterion it actually states — *any composite that passes validity and spans the split* — was applied instead. **If a Chicago Fed archive URL exists, extending to CFNAI is a small delta on this code.**

---

## 1. The indicator

**Core PCE price index (`PCEPILFE`)**, released monthly by the BEA in the Personal Income and Outlays report. Roughly three quarters of it is constructed from the *same underlying price quotes* the BLS publishes in the CPI about two weeks earlier for the same reference month. Its predictable component is therefore much closer to deterministic than Industrial Production's ever was — nearer the Gilbert et al. property of an announcement containing almost no new information.

Predictors: core CPI (`CPILFESL`) and headline CPI (`CPIAUCSL`), first prints only, plus two lags of the target. The CPI-before-PCE ordering is **verified per month** from the vintage archive, not assumed.

## 2. Sample assertion guard (Amendment 1 §2.4)

The cache-keyed-on-symbol bug silently truncated Test B's sample by five years and suppressed the split entirely. This test's whole purpose is that split, so the sample shape is asserted and printed before any regression runs.

| Check | Value |
|---|---|
| Sample start | 2005-02-28 |
| Sample end | 2026-07-30 |
| Observations | 253 |
| Pre-2012 | **83** |
| Post-2012 | **170** |
| Guard passed | **yes** |

Mean expanding-window prediction R²: **0.282**. The higher this is, the less new information the announcement carries and the closer the test sits to the Gilbert et al. setting. At 0.28 this is **much lower than intended** — core PCE turns out far less reconstructible from CPI at monthly frequency than the three-quarters-shared-source-data argument suggests, so the indicator is a weaker analogue of the LEI than §3 of the pre-registration claimed. CFNAI reached 0.92.

### Event window (amendment 2)

The release lands at **08:30 ET, before the equity open**, so the pre-registered close-to-close return brackets the announcement plus six and a half hours of unrelated news. Both windows are therefore reported, and the one with the stronger validity statistic is carried forward. The window is selected on the coefficient for *genuine surprise*, never on the hypothesis coefficient — selecting on the latter would be circular.

| Window | validity t (surprise) | b1 t (predictable) |
|---|---|---|
| Close-to-close (pre-registered) | 0.322 | 0.493 |
| Overnight, prior close to release open | 1.26 | 0.022 |

Window carried forward: **overnight**. The overnight window is the better instrument and still does not clear the hurdle, so the choice does not rescue the block.

## 3. Results

`b1` is the coefficient on the **predictable** component — the part reconstructible from CPI, already public when PCE is announced. Efficient markets imply `b1 = 0`. `b2` is the coefficient on genuine surprise and is the **validity check**: if the market does not respond to that, nothing else in the table can be read.

The `t after dropping 2` column applies the influence diagnostic to every row, per Amendment 1 §2.3 — any result that depends on a couple of COVID observations is not a result.

| Sample | β (predictable) | t | t after dropping 2 | β (surprise) | t (validity) | n |
|---|---|---|---|---|---|---|
| Full sample | 5.647e-06 | 0.022 | 0.466 | 0.0005208 | 1.26 | 253 |
| Excluding Mar–Dec 2020 | -0.0001766 | -0.608 | n/a | 0.0005272 | 1.21 | 243 |
| **Pre-2012** | -0.0005062 | -0.496 | -1.02 | 0.0006281 | 0.555 | 83 |
| **Post-2012** | 7.675e-05 | 0.314 | 0.513 | 0.0004332 | 1.05 | 170 |

### The pre/post-2012 interaction — the decisive statistic

Estimated as one pooled model so the *difference* carries a standard error:

- β on `predicted_z` (pre-2012 level): -0.0005062 (t = -0.496)
- β on `predicted_z × post2012` (the change): **0.0005829** (t = **0.555**)
- Decay detected at the hurdle: **no**

Two separately insignificant sub-period coefficients are not evidence of a difference between them, which is why the interaction and not the sub-period pair is what decides the decay claim. This was fixed in the pre-registration before running.

### Influence profiles

t on the predictable component after removing the most influential observations by Cook's distance:

| Sample | dropped 0 | 1 | 2 | 3 | 5 | most influential releases |
|---|---|---|---|---|---|---|
| Full | 0.022 | 0.251 | 0.466 | 0.482 | 0.925 | 2023-02-24, 2009-03-02, 2020-02-28 |
| Pre-2012 | -0.496 | -1.43 | -1.02 | -1.42 | -2.31 | 2008-11-26, 2009-03-02, 2009-02-02 |
| Post-2012 | 0.314 | 0.541 | 0.513 | 0.538 | 0.823 | 2023-02-24, 2020-02-28, 2020-03-27 |

## 4. Front-run strategy

Position `sign(predicted − trailing mean)` at the close before the release, exit at the release close. Reversal leg holds the opposite for five days, testing Tetlock (2011).

| Sample | Events | Gross %/yr | Gross t | Net %/yr | Net t | 5d reversal bps | Reversal t |
|---|---|---|---|---|---|---|---|
| Full | 253 | -0.351 | -0.379 | -1.08 | -1.17 | 6.45 | 0.431 |
| Pre-2012 | 83 | -1.75 | -0.864 | -2.69 | -1.33 | -13.5 | -0.451 |
| Post-2012 | 170 | 0.333 | 0.349 | -0.294 | -0.307 | 16.2 | 0.96 |

Gilbert et al. reported roughly **8%/yr** front-running the LEI. That is the benchmark these magnitudes are read against — not a threshold.

## 5. Training-window sensitivity

The pre-registration reduced the training window from Test B's 60 months to 36, because 60 would have pushed the first testable event to 2007 and left a badly lopsided split. The 60-month version is run anyway and reported here; if the two disagree materially, that disagreement is the finding.

| Window | Sample start | n | pre-2012 | post-2012 | b1 t (full) | b1 t (pre) | b1 t (post) | validity t |
|---|---|---|---|---|---|---|---|---|
| min_train=36 | 2005-02-28 | 253 | 83 | 170 | 0.022 | -0.496 | 0.314 | 1.26 |
| min_train=60 | 2007-03-01 | 229 | 59 | 170 | 0.201 | -0.373 | 0.376 | 1.09 |

## 6. Yearly coefficients

Full data in [`decay_curve.csv`](decay_curve.csv).

| Year | β | SE | t | n | gross bps |
|---|---|---|---|---|---|
| 2005 | -0.001644 | 0.002712 | -0.606 | 11 | -19.1 |
| 2006 | -0.001342 | 0.00254 | -0.528 | 12 | -5.03 |
| 2007 | 0.0005011 | 0.004374 | 0.115 | 12 | -10.3 |
| 2008 | -0.008978 | 0.009699 | -0.926 | 12 | -2.61 |
| 2009 | -0.008969 | 0.007085 | -1.27 | 12 | -27.9 |
| 2010 | -0.007487 | 0.00499 | -1.5 | 12 | -26.7 |
| 2011 | -0.0009686 | 0.008726 | -0.111 | 12 | -10.9 |
| 2012 | 0.001587 | 0.006887 | 0.231 | 11 | 13.4 |
| 2013 | 0.002816 | 0.004344 | 0.648 | 11 | 24.4 |
| 2014 | 0.0009751 | 0.00227 | 0.43 | 12 | 7.97 |
| 2015 | -0.001272 | 0.005339 | -0.238 | 12 | 20.6 |
| 2016 | 0.001547 | 0.002428 | 0.637 | 12 | 24 |
| 2017 | 0.0007885 | 0.001253 | 0.629 | 12 | 10.7 |
| 2018 | -0.004735 | 0.003496 | -1.35 | 12 | -44.6 |
| 2019 | -0.002628 | 0.003055 | -0.86 | 12 | -6.47 |
| 2020 | 0.0008521 | 0.001617 | 0.527 | 12 | -0.899 |
| 2021 | -0.0008358 | 0.001592 | -0.525 | 12 | 9.12 |
| 2022 | 0.006025 | 0.004981 | 1.21 | 12 | 4.21 |
| 2023 | 0.001416 | 0.003652 | 0.388 | 12 | 24.7 |
| 2024 | -0.00303 | 0.004235 | -0.715 | 11 | -10.3 |
| 2025 | 0.001376 | 0.003015 | 0.456 | 10 | -18.4 |

Years individually clearing |t| > 2.78: **0 of 21**. As in Test A, no decay half-life is fitted to a series that is never distinguishable from zero — that would measure the decay of noise.

## 7. Multiple-testing accounting

`config_log.jsonl` holds **162 evaluations** across all tests (A: 32, A2: 19, B: 45, B2: 66), 160 distinct configurations, 0 failed and counted anyway.

Per Amendment 1 §4 the Deflated Sharpe is computed against the **cumulative** count across all tests, not this amendment's trials alone.

| DSR input | Value |
|---|---|
| Cumulative trials N | **162** |
| Observations | 253 |
| Sharpe (annualised) | -0.254 |
| SR\* (selection hurdle) | 0.1698 |
| **Deflated Sharpe Ratio** | **8.035e-05** |

## 8. Verdict and the stop-permanently trigger

**UNREADABLE.** The extended sample fails the validity check: the market does not measurably respond to genuine core-PCE surprise either (t = 1.26). Amendment 1 §2.3 requires this check to be re-run on the extended sample precisely because passing on a short window does not guarantee passing on a long one, and it does not pass here. Everything below is unreadable in either direction. Per §2.5 this is **a gap, not a negative result**, and it does **not** fire the stop-permanently trigger.

The stop-permanently trigger requires a clean null **with validity passing**. Validity does not pass, so the trigger does not fire. This is an instrument failure, and the honest status is that the question remains open rather than answered negatively.

