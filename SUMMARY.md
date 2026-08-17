# Nomad gate tests — summary and recommendation

**Date:** 2026-08-17
**Tests run:** A (LETF rebalancing), B (stale information). C is gated and not started.
**Evaluations logged:** 77 (32 for A, 45 for B), zero failures, in `config_log.jsonl`.

---

## The one-paragraph answer

Neither cheap proxy found an effect. Test A says that the most perfectly
enumerable forced flow that exists — closed-form, fully public, known execution
window — does not predict the returns it mechanically causes at daily frequency
(t = 1.58 against a 2.78 hurdle, and the coefficient has the wrong sign). Test B
finds no support for markets responding to the already-public component of a
composite announcement; its one significant coefficient rests on two COVID
observations and collapses to t = 0.44 when they are removed. Specification §8
says that when A and B both come back empty, Test C would be measuring a corpse
and stopping is the legitimate and valuable outcome. **That is the
recommendation.** But the recommendation comes with one honest qualification that
matters: Test B never actually answered the question it was designed around, for
a data reason rather than a market reason. That is a gap, not a negative result,
and §4 below says what it would cost to close.

---

## Test A — Leveraged ETF rebalancing decay

**Verdict: FAIL.** Full detail in [`tests_a/results.md`](tests_a/results.md).

| | |
|---|---|
| Sample | 16,560 underlying-days, 2010-03 to 2026-08, 4 indices, 16 ProShares LETFs |
| Primary coefficient | β = 0.00457, **t = 1.58** (hurdle 2.78), sign opposite to prediction |
| Years individually significant | **0 of 17** |
| Strategy gross | +0.38 bps/day, t = 0.44 |
| Strategy net | −3.91 bps/day, t = −4.53 |
| Deflated Sharpe | ~0 against 32 logged trials |

**Why this result is trustworthy.** The rebalance multiplier is not estimated —
ProShares publish full-life daily NAV, shares outstanding and AUM per fund, so
`A·L·(L−1)·r` is computed from published inputs. As a check, each fund's daily
NAV return was regressed on its index: **all 16 recover their stated leverage to
within 0.004 with R² > 0.998.** The AUM file, the leverage assumptions and the
index mapping are mutually consistent.

**What this does and does not kill.** It kills the tested channel: the overnight
reversal of mechanically forced closing-auction flow, at daily frequency, net of
generic short-horizon reversal. The specification's logic then applies — imperfect
enumeration cannot pay more than perfect enumeration. It does **not** kill the
intraday impact channel over the full period, because free intraday history goes
back roughly two years and no vendor gives fifteen years without payment. On the
two years available the impact coefficient is t = 0.25, consistent with no effect
but underpowered, and it was registered as underpowered and non-gating before it
was run.

**The half-life the framework wanted does not exist.** The specification hoped
Test A would replace the invented "12–36 month" decay figure with a measured
number, and called that potentially more valuable than the trade itself. The
exponential fit does return 6.3 years — with a bootstrap 95% CI of **[0.5, 64.9]
years**, and with **zero of seventeen** yearly coefficients individually
distinguishable from zero. It is flagged NOT INTERPRETABLE in the code and in the
report. Fitting decay to a quantity that was never distinguishable from zero
measures the decay of noise, and substituting 6.3 years for 12–36 months would be
swapping one invented number for another with a regression table stapled to it.

---

## Test B — Stale information / "public but unconnected"

**Verdict: NOT REPLICATED.** Full detail in [`tests_b/results.md`](tests_b/results.md).

The Conference Board LEI is proprietary and unobtainable, so the specification's
permitted substitute was used. Two blocks, because no single free indicator has
both properties needed:

| | B1 — Industrial Production | B2 — CFNAI |
|---|---|---|
| Period | 2003-07 to 2026-07, 275 announcements | 2017-10 to 2026-07, 104 announcements |
| Prediction R² | 0.49 | **0.92** |
| Spans the pre/post-2012 split? | **yes** | no |
| Detects genuine surprise? (validity) | **no** (t = −0.02) | yes (t = 4.51) |
| Predictable component, full sample | t = 0.14 | t = 3.91 |
| …excluding Mar–Dec 2020 | t = −0.10 | t = 0.98 |
| …dropping 2 most influential obs | t = 0.74 | **t = 0.44** |

**B2's significance is two data points.** The influential releases are April and
May 2020, when the COVID collapse in the pre-released components drove the
standardised predictor to −14 standard deviations. Dropping them takes t from
3.91 to 0.44. Two observations are not an effect.

**B1 is blind, and that is the important limitation.** B1 was the only block whose
release history spans 2012, so it was the only one that could test the decay
claim §3.3 designates the primary comparison. It fails the validity check
registered in advance: it does not detect a market reaction even to genuine
industrial-production *surprise* (t = −0.02). Its pre-2012 and post-2012
coefficients are therefore unreadable in either direction. **The primary
comparison this test was designed around went unanswered** — for a data reason,
not a market reason.

**What did work.** The point-in-time machinery is sound and verified rather than
assumed: every macro input is a first print pulled from the ALFRED vintage in
which the reference month first appeared, release dates are measured from the
archive rather than taken from a schedule, and the resulting ordering check
confirms the Employment Situation preceded Industrial Production in **364 of 364
months**, median gap 11 days.

---

## What this means for Test C

**Recommendation: do not start Test C.**

Specification §8: *"If A and B both return decay-to-zero, the honest conclusion is
that enumerated forced-flow edges do not survive publication, and Test C would be
measuring a corpse. That is a legitimate and valuable place to stop."*

Both cheap proxies came back empty, one of them on the most perfectly enumerable
forced flow that exists. Test C costs roughly three weeks. Ordering the tests by
cost-per-bit was done precisely so this decision could be bought for a few days,
and it has been.

**Two corrections to how that conclusion should be stated.** Neither test measured
a *decay*. Test A found no effect at any point in the seventeen years, not an
effect that faded; Test B could not read its decay comparison at all. So the
finding is "neither proxy found an effect to decay", which is a weaker and more
accurate claim than "the edge decayed after publication". The framework's
12–36 month decay clock is not refuted by this work — it is simply still
unsupported, and now demonstrably untested.

**What would change the recommendation,** in ascending order of cost:

1. **Buy LEI vintage data and run the actual Gilbert et al. replication.** This is
   the single highest-value next step. Test B's substitute failed on the validity
   check, not on the hypothesis, so the canonical test remains genuinely open. A
   few hundred dollars of data is a far better use of budget than three weeks of
   Test C.
2. **Buy intraday index data back to 2010** and run Test A's H-A1 impact leg
   properly. The overnight leg is dead; the impact leg is untested before 2023.
3. Only if one of those returns positive: reconsider Test C.

If Test C is ever run, the two things to build in from the start — because
neither can be retrofitted — are inference-family tagging at enumeration time,
and the contamination split at the mapping model's training cutoff. See
[`tests_c/README.md`](tests_c/README.md).

---

## Methodological notes worth carrying forward

- **The config log is the denominator.** 77 evaluations across both tests,
  including every abandoned and unreported variant. The Deflated Sharpe Ratios
  are computed against that count, read from the file rather than asserted.
- **Three amendments were made after seeing results**, and each is dated and
  disclosed in the relevant `preregistration.md` rather than edited in silently.
  All three can only weaken a positive finding, never create one: a cost-model
  correction that *lowers* costs (Test A #3), a citation correction (Test B #1),
  and an influence diagnostic that *removes* significance (Test B #2).
- **One real bug was found and fixed mid-analysis**: the price cache returned a
  file built for a later start date regardless of the start requested, silently
  truncating Test B's sample by five years and suppressing the pre/post-2012
  split entirely. The fix is in `tests_a/pipeline.py`; the lesson is that a cache
  keyed on symbol alone is a correctness bug, not a performance detail.
- **Corwin–Schultz is the wrong spread estimator for liquid instruments.** It
  returned 47bp round-trip on SPY/QQQ/IWM/DIA, off by two orders of magnitude,
  because its identifying assumption fails when an instrument trades millions of
  times a session. It is retained in `cost_model.py` for the illiquid names Test C
  would need, alongside a tick-based estimator for liquid ones.
