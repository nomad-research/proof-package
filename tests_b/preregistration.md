# Test B — Stale information / "public but unconnected": pre-registration

**Status:** committed before any analysis code was written.
**Date:** 2026-08-17
**Spec reference:** Nomad Gate Test Specification §3, §1.1–§1.5

Amendments go at the bottom, dated, with a reason. Nothing above the amendment
line is edited after commit.

---

## 1. Hypothesis

Markets react to information that is not new. If this still holds post-2012, the
backward-re-reading thesis — finding public documents nobody connected — has a
live mechanism behind it.

Prior art, read before drafting this document and not re-derived:

- **Gilbert, Kogan, Lochstoer & Ozyildirim (2012)**, *Management Science* 58(2).
  The Leading Economic Index is a deterministic function of ten components, most
  released before the LEI itself, so its announcement contains essentially zero
  new information — yet prices move on it, and a front-running strategy earned
  roughly 8%/yr.
- **Huberman & Regev (2001)**, *Journal of Finance* 56(1). The EntreMed case: a
  *New York Times* piece containing nothing not already published in *Nature*
  five months earlier produced a permanent price move.
- **Tetlock (2011)**, *Review of Financial Studies* 24(5). Reactions to stale
  news reverse.
- **Fedyk & Hodson (2023)**, *Journal of Financial Economics* 149(1). Recombined
  old information produces larger moves and larger reversals than straight
  reprints, and the effect increases over time.

- **H-B1 (core).** The market responds on announcement day to the *predictable*
  component of a composite indicator — the part reconstructible from components
  already public at the time.
- **H-B2 (decay).** That response is weaker after 2012 than before it, treating
  the publication of Gilbert et al. as the treatment.

Null in both cases: the coefficient on the predictable component is zero, and the
pre/post difference is zero.

## 2. Choice of indicator, and what is lost

The specification's first choice is the Conference Board LEI. **It is not
obtainable.** The Conference Board took the LEI proprietary; it is not on FRED
and no free archive carries its historical values or vintages.

§3.2 permits the substitute: *"any composite indicator built from pre-released
components — several regional Fed indices qualify."* Three were evaluated
against the requirement in §3.3 that **pre-2012 vs post-2012 is the primary
comparison**, which needs release dates spanning both periods:

| Candidate | True composite of pre-released components? | Earliest ALFRED vintage | Supports the pre/post-2012 split? |
|---|---|---|---|
| CFNAI (Chicago Fed National Activity Index) | Yes — weighted average of 85 already-published series | 2011-05-23 | **No** |
| USPHCI (Philadelphia Fed US coincident index) | Yes — payrolls, manufacturing hours, unemployment, wages | 2010-10-26 | **No** |
| USSLIND (Philadelphia Fed US leading index) | Yes | 2011-02-01 | **No** |
| **INDPRO** (Industrial Production, total index) | Partly — see below | **1927-01-26** | **Yes** (381 in-sample vintages) |

The test is therefore run in two parts.

### B1 — primary: Industrial Production, 1997–2026

Chosen because it is the only candidate whose release-date history spans the
split that §3.3 designates the primary comparison.

**What is weaker about it, stated plainly.** The LEI is a *deterministic*
function of already-published components: its announcement contains literally
zero new information, which is what makes Gilbert et al. so sharp. Industrial
Production is not. The Federal Reserve estimates a large share of the index from
production-worker hours — data published in the Employment Situation report
roughly ten days earlier — but IP also incorporates genuine new physical-output
data. Its predictable component is therefore **statistical, not deterministic**.

H-B1 on IP is consequently a weaker claim: *does the market respond to the
predictable part of the announcement*, rather than *does it respond to an
announcement that contains nothing new*. It is the same regression and the same
efficient-markets null. It is not the same strength of evidence, and no result
from it will be described as a replication of Gilbert et al.

### B2 — secondary: CFNAI, 2011–2026

Run because it preserves the property B1 loses. CFNAI is a weighted average of 85
series that are all published before it, so its announcement genuinely contains
almost no new information. Its vintage history cannot support the pre/post-2012
split, so it answers only the second question: **is the effect alive today in the
closest available analogue of the LEI?** Given the specification's concern that
"fourteen years of post-publication decay are unmeasured", that is the
decision-relevant half.

The R² of the CFNAI prediction is itself reported, as a direct measure of how
little new information the announcement carries.

## 3. Data and point-in-time construction

**Everything is a first print.** For each reference month, the value used is the
one that was actually published, taken from the ALFRED vintage in which that
month first appears. Revised and benchmark-restated values are never used —
that is the restated-fundamentals violation §1.4 forbids.

**Release dates are measured, not assumed.** The vintage date on which a
reference month first carries a value *is* that month's release date. This comes
from the archive rather than from a published schedule, which means the ordering
between two releases can be **verified rather than asserted**. The pipeline
checks, for every reference month, that the Employment Situation release strictly
precedes the Industrial Production release, and drops any month where it does
not.

| Role | Series | Source |
|---|---|---|
| B1 target | INDPRO | ALFRED vintages |
| B1 predictors | AWHMAN, MANEMP (aggregate manufacturing hours) | ALFRED vintages, Employment Situation |
| B2 target | CFNAI | ALFRED vintages |
| B2 predictors | PAYEMS, INDPRO, UNRATE, AWHMAN | ALFRED vintages |
| Market return | SPY daily close | Yahoo Finance |

**Sample.** B1: reference months whose IP release date falls in 1997-01-01 to the
latest available, giving roughly 15 years either side of the 2012 split. B2:
2011-05-23 (first CFNAI vintage) to latest. Both start dates are fixed here and
will not be moved to improve a result.

## 4. Constructed quantities

For reference month `m`, with `v(m)` the vintage that first prints it:

| Symbol | Definition |
|---|---|
| `g(m)` | Announced IP growth: `ln(IP[m] in v(m)) − ln(IP[m−1] in v(m))`. Both values are taken from the **same** vintage, because that is the growth rate the release actually announced |
| `h(m)` | Announced growth in aggregate manufacturing hours: `ln(AWHMAN[m]·MANEMP[m]) − ln(AWHMAN[m−1]·MANEMP[m−1])`, both from the Employment Situation vintage that first prints `m` |
| `predicted(m)` | Fitted value of `g(m)` from an expanding-window OLS on `[1, h(m), g(m−1), g(m−2)]`, estimated **only on months whose IP release date is strictly before `v(m)`**, minimum 60 training months |
| `surprise(m)` | `g(m) − predicted(m)` |
| `predicted_z`, `surprise_z` | Each standardised by its expanding-window mean and standard deviation through `m−1` only |
| `r_rel(m)` | SPY return from the close before the release to the close on the release date |

IP is released at 09:15 ET, before the equity open, so the release-day
close-to-close return is the correct event window and is also exactly what a
front-running position would earn.

## 5. Test statistics and pass thresholds

### 5.1 Primary — H-B1

```
r_rel(m) = a + b1·predicted_z(m) + b2·surprise_z(m) + e(m)
```

- **Test statistic:** t on `b1`, Newey–West HAC with 3 lags.
- **Efficient-markets null:** `b1 = 0`. The predictable component is public before
  the announcement, so it should already be in the price.
- **Pass threshold:** `|t(b1)| > 2.78` (§1.3). No sign is pre-registered — Gilbert
  et al. find a positive response, but the direction is not the claim under test.
- `b2` is reported as a sanity check: the market should respond to genuine
  surprise. A `b2` indistinguishable from zero would mean the event window or the
  return series is wrong, not that markets are inefficient, and would invalidate
  the whole test rather than support it.

### 5.2 Primary comparison — H-B2, pre/post-2012

Estimated as a single pooled interaction so the difference has a standard error:

```
r_rel(m) = a + b1·predicted_z + b1p·(predicted_z · post2012)
             + b2·surprise_z + b2p·(surprise_z · post2012) + c·post2012 + e
```

where `post2012 = 1` when the release date is on or after 2012-01-01.

- **Test statistic for the decay claim:** t on `b1p`.
- **Pass threshold for a *detected decay*:** `|t(b1p)| > 2.78` with `b1p` opposing
  `b1` in sign.
- Sub-period regressions are also reported separately, but the interaction is the
  decisive statistic because it is the one with a valid standard error on the
  difference.

### 5.3 Front-run strategy (§3.3 step 5)

- **Entry:** at the close of the day before the release, take position
  `sign(predicted(m))`.
- **Exit:** at the close on the release date.
- **Reversal leg:** from the release close, hold `−sign(predicted(m))` for 5
  trading days. Tetlock (2011) predicts stale-news reactions reverse; this
  measures whether they do.
- **Instrument:** SPY. **Size:** $10,000,000 notional, fixed here.
- **Costs (§1.5):** full spread round trip with the spread taken as two minimum
  price increments, plus two-sided square-root impact `η·σ·√(notional/ADV)` at
  η = 1.0, plus 0.5bp fees per side.
- **Reported:** gross and net, annualised, with t-statistics, split pre/post-2012.
  Gilbert et al. reported ~8%/yr for the LEI; that is the benchmark the magnitude
  is compared against, not a threshold.
- **Pass threshold:** net `t > 2.78`.

### 5.4 Secondary — B2, CFNAI

Identical specification on the CFNAI sample, with no period split. The prediction
R² is reported alongside, as the measure of how nearly deterministic the
reconstruction is.

### 5.5 Deflated Sharpe Ratio

Computed on the net return series of the front-run strategy, with trial count `N`
read from `config_log.jsonl` at reporting time (§1.3, §5.2).

## 6. Missing data handling — fixed in advance

1. **Employment Situation not strictly before Industrial Production** for a
   reference month: the month is dropped and counted. This is a verification, not
   an assumption, and any failures are reported.
2. **Any first print missing** for the target or a predictor: the month is
   dropped.
3. **No SPY trading day on the release date** (release on a holiday or weekend):
   the month is dropped rather than shifted to the next session.
4. **Fewer than 60 training months** available at `m`: no prediction is made and
   the month is excluded from the tests.
5. **No imputation of any macro value or return, ever.**
6. Every dropped month is counted and the counts appear in `results.md`.

## 7. COVID handling — fixed in advance

March–December 2020 contains IP moves an order of magnitude larger than anything
else in the sample, and would otherwise dominate every coefficient through
leverage alone.

- **Primary specification includes all months**, with `predicted` and `surprise`
  standardised by expanding-window statistics, which limits but does not remove
  the leverage.
- **A robustness specification excluding 2020-03 through 2020-12 is run and
  reported alongside**, and both are logged.
- If the two disagree materially, that disagreement is reported as the finding
  rather than resolved by picking one.

## 8. Known biases and limitations, stated in advance

1. **IP is not the LEI.** Its predictable component is statistical rather than
   deterministic (§2). No result here is a replication of Gilbert et al.
2. **The 2012 split is not a clean experiment.** Publication of the paper is the
   nominal treatment, but the post-2012 period also contains the growth of
   systematic macro trading, decimalisation-era liquidity changes already in
   train, and the 2020 shock. A decline across the split is consistent with the
   publication story but does not identify it. This is stated now so it is not
   claimed later.
3. **Survivorship and selection do not bite here** — the sample is every IP
   release in the window, with no universe construction.
4. **Multiple indicators were considered** (CFNAI, USPHCI, USSLIND, INDPRO) before
   one was chosen. That choice was made on release-date coverage alone, before any
   return regression was run, and the alternatives are logged in
   `config_log.jsonl` as evaluated-and-rejected so the selection is in the
   multiple-testing denominator.

## 9. What each outcome means for Test C

Per specification §3.4 and §8:

- **Effect persists post-2012** → strong. Public-but-unconnected is real and
  durable, and Test C is worth its three weeks even though Test A failed.
- **Effect died after 2012** → the mechanism is real but decays on publication.
  Combined with Test A this would give the two-point decay estimate the
  specification wants — except that Test A produced no interpretable half-life,
  so this would be a one-point estimate and should be described as such.
- **Never replicated** → check the specification against the paper before
  concluding. If it still fails, then combined with Test A's failure the honest
  conclusion is the one §8 names: enumerated forced-flow edges do not survive
  publication, Test C would be measuring a corpse, and the correct action is to
  stop.

---

## Amendments

### Amendment 1 — 2026-08-17, before any analysis was run

**Change.** Citation detail only. The Gilbert, Kogan, Lochstoer & Ozyildirim
(2012) paper is titled **"Investor Inattention and the Market Impact of Summary
Statistics"**, *Management Science* 58(2), 336–350. §1 above describes its
content but does not name it; the specification likewise cited it by journal and
volume without a title.

**Reason.** Verified against the published record while the data was fetching.
No claim in §1 changes — the paper does find that the LEI is a summary statistic
of previously released inputs and that a strategy trading in the direction of the
announcement one day before its release earns significant returns, which is the
design §5.3 already registered.

**Nothing else is altered.** Recorded as an amendment rather than edited in
place, so the file is never silently changed after commit.

### Amendment 2 — 2026-08-17, **after** results were seen

**Change.** An influence diagnostic is added to every block: refit the primary
regression after dropping the 1, 2, 3 and 5 observations with the largest Cook's
distance, and report the resulting t-statistics alongside the full-sample one.

**Reason.** The CFNAI block returned a full-sample coefficient on the predictable
component clearing the hurdle (t = 3.91) while the pre-registered
excluding-2020 specification returned t = 0.98. §7 anticipated exactly this
disagreement and said it must be *reported as the finding rather than resolved by
picking one* — but it did not specify a diagnostic capable of saying **why** the
two disagree. Inspection showed a single April 2020 announcement with a
standardised predictor value of −14, an artefact of the COVID collapse in the
pre-released components. The influence check turns "these two specifications
disagree" into a quantified statement about how many observations the result
rests on.

**Disclosure — made after seeing results.** As with Test A's amendment 3, the
direction matters: this diagnostic can only *weaken* a positive finding, never
create one. It cannot be used to rescue a result. It is applied uniformly to
every block, including the ones where the full-sample coefficient was already
insignificant, so it is not applied selectively to the inconvenient block.

No pre-registered statistic is removed or altered. The full-sample and
excluding-2020 specifications are still reported exactly as registered, and the
pass thresholds are unchanged.
