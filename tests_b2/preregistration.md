# Test B-2 — Stale information, extended across the 2012 split: pre-registration

**Status:** committed before any B-2 analysis was run.
**Date:** 2026-08-17
**Spec reference:** Gate Spec Amendment 1 §2; original spec §3, §1.1–§1.5

---

## 1. Objective

Amendment 1 §2.1: extend the composite-indicator test far enough back that **the
pre/post-2012 comparison designated primary in the original §3.3 can actually be
read.** Test B could not read it: B1 (Industrial Production) spanned the split but
failed the validity check (t = −0.02 on genuine surprise); B2 (CFNAI) passed
validity but started in 2017.

## 2. Why this is not CFNAI, and what was tried

The amendment specifies extending CFNAI backwards, on the basis that historical
release dates are archived by the Chicago Fed. **They could not be obtained.**
What was attempted, so the operator can correct me if a source exists:

| Attempt | Result |
|---|---|
| ALFRED CFNAI vintages | First vintage **2011-05-23**. No earlier first prints or release dates exist in the archive. |
| `chicagofed.org/research/data/cfnai/past-releases` | Page returns 200 but the release list is rendered client-side; no dates in the served HTML, and no JSON or AJAX endpoint is referenced in the page source. Confirmed a second time via an independent renderer. |
| `chicagofed.org/research/data/cfnai/archive` | 404. |
| FRED release object `rid=219` release-date endpoints | No date list returned by any documented path. |
| FRED/ALFRED release-dates API | Requires an API key; none available and signup is not possible from this environment. |

The amendment is explicit that release dates must be taken from the archive and
**not reconstructed from a schedule**, so reconstructing them was not treated as
an option.

The amendment is equally explicit about what actually matters: *"what is required
is any composite that passes validity and spans the split."* That is the criterion
applied here.

## 3. The substitute: core PCE price index

**Target: `PCEPILFE`** — core personal consumption expenditures price index,
released monthly in the BEA Personal Income and Outlays report.

Why it fits the specification better than the alternatives available free:

1. **Its predictable component is close to deterministic.** Roughly three
   quarters of the core PCE price index is constructed from the *same underlying
   price quotes* the BLS publishes in the CPI, which is released about two weeks
   earlier for the same reference month. This is much nearer the Gilbert et al.
   property — an announcement containing almost no new information — than
   Industrial Production ever was.
2. **It spans the split with monthly frequency.** ALFRED holds 314 vintages from
   2000-08, giving both a pre-2012 and a post-2012 sample.
3. **It moves markets**, so the validity check has a real chance of passing —
   which is exactly where B1 failed.

**Predictors** (all first prints, all released before the target for the same
reference month, and the ordering is *verified per month* rather than assumed):
`CPILFESL` (core CPI), `CPIAUCSL` (headline CPI), plus two lags of the target.

**Sample:** reference months whose PCE release date falls from 2000-08 to the
latest available.

## 4. Deviations from the Test B specification, fixed here

**Training window reduced from 60 months to 36.** Test B's 84-month warm-up
(60 training + 24 for the standardisation window) consumed seven years and was
the mechanical reason B2 started in 2017. With a 2000-08 vintage start, a
60-month window would push the first testable event to 2007-08 and leave roughly
53 pre-2012 observations against 170 post — a split too lopsided to read
comfortably.

36 months is justified on the specific structure here: the CPI-to-core-PCE
mapping is close to mechanical and stable, so the regression does not need a long
window to identify it. **A sensitivity at 60 months is also run and reported**, and
if the two disagree materially that disagreement is the finding rather than
something to resolve by choosing.

Everything else — the standardisation window, the HAC lags, the hurdle, the
influence diagnostic, the cost model — is unchanged from Test B.

## 5. Test statistics and pass thresholds

### 5.1 Validity check — run first, and gating

```
r_rel(m) = a + b1·predicted_z(m) + b2·surprise_z(m) + e(m)
```

**`b2` is examined before `b1`.** If the market does not measurably respond to
genuine surprise (|t(b2)| ≤ 2.78) then the extended sample is **unreadable**, and
that is reported as a gap in the instrument rather than as a negative finding
about markets — the same status B1 received. Amendment 1 §2.3 requires this check
to be re-run on the extended sample specifically, because passing on a short
window does not guarantee passing on a long one.

### 5.2 Primary — H-B1

- **Statistic:** t on `b1`, Newey–West HAC, 3 lags.
- **Null:** `b1 = 0`. The predictable component was public before the release.
- **Pass:** |t(b1)| > 2.78.

### 5.3 Primary comparison — pre/post-2012

Single pooled interaction, so the difference carries a standard error:

```
r_rel = a + b1·predicted_z + b1p·(predicted_z × post2012)
          + b2·surprise_z + b2p·(surprise_z × post2012) + c·post2012 + e
```

- **Decay statistic:** t on `b1p`. **Decay detected** requires |t(b1p)| > 2.78
  with `b1p` opposing `b1` in sign.
- Sub-period regressions are reported too, but the interaction decides, because
  two separately insignificant coefficients are not evidence of a difference.

### 5.4 Influence diagnostic — mandatory

Refit dropping the 1, 2, 3 and 5 observations with the largest Cook's distance.
Amendment 1 §2.3 requires the COVID observations to be reported both included and
excluded; **any result that depends on them is not a result.** Applied to every
sub-period, not selectively.

### 5.5 Front-run strategy

Position `sign(predicted_z)` at the close before the release, exit at the release
close; reversal leg −`sign(predicted_z)` held five days. SPY, `min($10m, 1% of
ADV)`, costed as in Test A-2. Gross and net, split pre/post-2012. Gilbert et al.
reported ~8%/yr on the LEI as the magnitude benchmark.

### 5.6 Deflated Sharpe

Against the **cumulative** trial count across all tests in `config_log.jsonl`, per
Amendment 1 §4 — not against B-2's trials alone.

## 6. Sample assertion guard — required by Amendment 1 §2.4

The cache-keyed-on-symbol bug silently truncated Test B's sample by five years and
suppressed the split entirely. Before any regression runs, the analysis **asserts
and prints**: sample start date, sample end date, observation count, and count
either side of 2012-01-01. If the pre-2012 count is below 40 or the sample start
is later than 2004-01-01, the run **stops and reports** rather than proceeding to
produce a split that cannot be read.

## 7. Missing data — unchanged from Test B

Ordering verified per month and violations dropped and counted; months with any
missing first print dropped; release dates not falling on an equity trading day
dropped rather than shifted; no imputation of any macro value or return.

## 8. Interpretation, per Amendment 1 §2.5

- **Effect pre-2012, absent post-2012** → mechanism real, decays on publication.
- **Effect in both** → public-but-unconnected is durable. Strong support.
- **Absent in both, validity passing** → the mechanism is not there. This fires
  the stop-permanently trigger in Amendment 1 §3.
- **Validity fails on the extended sample** → unreadable; reported as a gap, not
  a negative, and the stop trigger does **not** fire.

---

## Amendments

### Amendment 1 — 2026-08-17, after the guard fired on the first run

**Change.** §6's sample assertion guard drops its second condition — *"stops and
reports if the sample start is later than 2004-01-01"* — and keeps the first,
*"stops and reports if the pre-2012 count is below 40"*. In its place the guard
now verifies directly that the sample start equals the first available vintage
plus the pre-registered warm-up, which is the actual anti-truncation check.

**Reason.** The guard fired on the first run: sample start 2005-02-28, later than
the 2004-01-01 threshold. Inspection shows this is **not** truncation. It is the
exact arithmetic of the pre-registered windows:

| | |
|---|---|
| First `PCEPILFE` vintage | 2000-08-01 |
| Announcements assembled | 318, 2000-08 to 2026-07 |
| Rows after dropping two lags | 316 |
| First prediction | row 36 → 2003-03-03 (= `min_train` 36) |
| First standardised prediction | row 60 → **2005-02-28** (= +24 standardisation months) |

The start date was a **proxy** for "enough pre-2012 observations", and the direct
measure it was standing in for passes comfortably: **83 pre-2012** and 170
post-2012 announcements, against a required 40. The proxy was simply calibrated
without doing the arithmetic first.

**Disclosure — a guard was relaxed after it fired, which is exactly the pattern
that should attract suspicion.** What makes it defensible here, stated so a
reader can check rather than take it on trust:

- The condition removed is redundant, not substantive. The condition that
  actually protects the test — a readable pre-2012 sample — is retained and
  passes by a factor of two.
- The failure mode the guard exists for (Amendment 1 §2.4: silent truncation of
  the kind the cache bug caused) is **ruled out arithmetically** above, not
  assumed away. The first testable event lands exactly where the pre-registered
  warm-up puts it.
- No threshold that bears on a *result* is touched. The hurdle, the validity
  check, the influence diagnostic and the interaction test are all unchanged.

Had the pre-2012 count been the failing condition, the correct response would
have been to stop and report, as §6 requires.

### Amendment 2 — 2026-08-17, **after** the validity check failed

**Change.** Every regression is run under **two event windows** and both are
reported: the pre-registered close-to-close return on the release date, and the
**overnight** return from the prior close to the release-day open. The window
whose validity check is stronger is carried forward to the sub-period tests.

**Reason.** The pre-registered close-to-close window returned a validity
statistic of t = 0.32 — the market shows no measurable reaction to genuine core
PCE surprise. Before accepting that as a property of the announcement, the window
itself deserves scrutiny: **the release lands at 08:30 ET, before the equity
open**, so the close-to-close return brackets the announcement *plus six and a
half hours of unrelated news*. The overnight window brackets the announcement and
almost nothing else, and is available in the same daily data.

**Disclosure — made after seeing a failed validity check, which is the direction
that could manufacture a readable result where none exists.** Fencing:

- Both windows are reported for every row. Nothing is hidden by the selection.
- The selection rule is mechanical (stronger validity statistic wins) and is
  applied identically to both training-window variants.
- The window is chosen on the **validity** statistic — the coefficient on
  *genuine surprise* — never on `b1`, the coefficient the hypothesis is about.
  Choosing an event window by the hypothesis coefficient would be circular;
  choosing it by whether the instrument detects real news is the standard
  event-study calibration.
- **It did not rescue anything.** Validity improves from t = 0.32 to t = 1.26 and
  still does not clear 2.78, so the block remains unreadable and the verdict is
  unchanged.

This amendment is recorded because the reasoning is worth carrying forward even
though the outcome did not move: if this test is rerun on a better indicator, the
overnight window is the right one to start from.
