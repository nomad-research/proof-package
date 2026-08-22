# Nomad gate tests — summary and recommendation

**Updated:** 2026-08-17, after Gate Spec Amendment 1.
**Tests run:** A, B, A-2, B-2, **B-3**. C is gated and never started.
**Cumulative evaluations logged:** 204 (A 32, B 45, A-2 19, B-2 66, B-3 42), zero failures.

| Test | Question | Verdict |
|---|---|---|
| **A** | Does perfectly enumerated forced flow pay in mega-cap indices? | **FAIL** |
| **A-2** | Does it pay where counterparty scarcity is high? | **FAIL — Test A closed permanently** |
| **B** | Does "public but unconnected" survive post-2012? | **NOT REPLICATED** |
| **B-2** | Same, on a sample that spans the split | **UNREADABLE** |
| **B-3** | Same blocks, measured against rates instead of SPY | **VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES** |
| **C** | Do enumerated destinations predict returns? | **not started, gated** |

---

## The one-paragraph answer

The LETF mechanic is dead in both regimes and Test A is closed by its own
pre-registered rule. The stale-information line is now **also** closed, and this
one is a genuine result rather than a gap: B-3 swapped the outcome variable from
SPY to rates, confirmed with a positive control that the new instrument
demonstrably detects macro news (t = 4.68, correct sign, coherent yield/price
relationship), and **still found no robust response to the already-public
component of an announcement.** Every earlier null was unreadable because the
instrument was blind; this one is not. The pre-registered stop trigger fired and
no fourth instrument will be proposed. Two things remain genuinely open and
should not be confused with the above: the pre/post-2012 decay question was never
answered — B1 fails validity even on rates, though the failure is now diagnosed
as the announcement's silence rather than the instrument's — and the actual
Gilbert et al. indicator was never tested, because the LEI is proprietary.

---

## Test A-2 — the amendment's central claim, tested

Amendment 1 §0.1 was right, and the correction is accepted without reservation.
Test A tested SPX, NDX, Russell 2000 and the Dow: perfect enumeration, near-zero
counterparty scarcity, minimum idiosyncratic risk — the regime McLean & Pontiff
(2016) already identify as where alpha does not survive. Reading that null as a
ceiling on the illiquid regime collapsed two independent variables.

**The premise checks out.** The cross-section has real range in the hypothesis
variable, which had to be true for the test to have any power:

| Underlying | median M/ADV |
|---|---|
| Semiconductors | **82.9** |
| Technology | 14.7 |
| Internet | 12.8 |
| Home construction | 9.9 |
| Financials | 9.6 |
| *S&P 500 (control)* | *2.0* |
| Industrials | 0.19 |

> **`M/ADV` is a multiplier, not flow.** Realised forced flow is `M · r / ADV` —
> the multiplier times the day's return. At a 1% move, a multiplier of 82.9 is
> **0.83 days of ADV**, and A-2's top decile averaged **0.80 days of ADV** of
> realised flow across its whole range of 0.001–0.80. So A-2 established that
> **~0.8 days of ADV produces no measurable effect**, and says nothing about 5x,
> 10x or 20x ADV — the regime fire sales and forced liquidations occupy. Any
> screen inheriting the multiplier as though it were flow sets a magnitude bar
> roughly 100x too high and rejects events A-2 never tested.


A 400× span from top to bottom. Semiconductors alone carry a rebalance multiplier
of roughly $145bn against semiconductor-ETF ADV of order $1bn.

**The result is null on every pre-registered statistic:**

| Statistic | Result | Hurdle |
|---|---|---|
| H1 — top-decile β | t = **0.65**, wrong sign | t < −2.78 |
| H2 — pooled decile-rank interaction | t = **−0.01** | \|t\| > 2.78 |
| H2 — Spearman ρ (decile vs β) | −0.067, permutation p = 0.87 | — |
| Thin underlyings only | t = −0.15 | — |
| Top-decile strategy, gross | t = **0.05** | — |
| Deciles individually clearing the hurdle | **0 of 10** | — |

**The stopping condition has fired.** Pre-registration §8, written before the test
ran: *if the top-decile coefficient is not significant AND there is no monotone
gradient, the LETF mechanic is dead in both regimes and Test A is closed
permanently. No third regime will be proposed.* Both conditions are met. The
value of having written that sentence down in advance is precisely that it removes
the option of proposing a fourth universe now.

Two things worth carrying forward from how this was built:

- **Direxion AUM had to be reconstructed**, because they publish no historical NAV
  or shares-outstanding feed and their 3x sector funds *are* the high-imbalance
  regime. Quarterly SEC N-PORT `netAssets` anchors were interpolated to daily via
  each fund's own return path. The method was **validated against ProShares
  funds, where true daily AUM is published: 2.7% median absolute error.**
- **Leverage was estimated, not assumed.** Direxion cut several funds from 3x to
  2x during 2020; a fixed table would have mis-stated `L·(L−1)`, which is the
  whole signal.

---

## Test B-2 — could not be delivered as specified

**CFNAI could not be extended.** Amendment 1 §2.2 assumed the Chicago Fed archives
historical release dates in a retrievable form. Four routes were tried and all
failed: ALFRED's first CFNAI vintage is 2011-05-23; the Chicago Fed
`past-releases` page renders its list client-side with no JSON or AJAX endpoint in
the served source (confirmed twice, including with an independent renderer);
`/cfnai/archive` returns 404; and FRED's release-date API needs a key that cannot
be obtained here. The amendment forbids reconstructing dates from a schedule, so
that was not done. **If a working archive URL exists, extending to CFNAI is a
small delta on the committed code.**

The amendment's actual criterion — *any composite that passes validity and spans
the split* — was applied instead, using the **core PCE price index**. That
delivered the sample the test needed:

| | |
|---|---|
| Sample | 2005-02 to 2026-07, 253 announcements |
| Pre-2012 | **83** |
| Post-2012 | **170** |

**And then failed the validity check.** The market shows no measurable reaction to
genuine core-PCE surprise: t = 0.32 on the pre-registered close-to-close window,
and t = 1.26 on the overnight window that brackets the 08:30 release without six
and a half hours of unrelated news. Neither clears 2.78. Per the pre-registered
rule this is **a gap, not a negative result**, and the stop-permanently trigger
does **not** fire.

Two honest admissions about that block:

- Core PCE was justified in the pre-registration as near-deterministic from CPI.
  Its measured prediction R² is **0.28**, against CFNAI's 0.92. It is a much
  weaker analogue of the LEI than claimed before running.
- The sample guard fired on its own mis-calibrated tripwire (a fixed 2004 start
  date standing in for "enough pre-2012 data"). It was relaxed *after firing* —
  the pattern that should always attract suspicion — and the amendment showing
  the arithmetic is in `tests_b2/preregistration.md`. The substantive condition it
  was proxying for passes by a factor of two.

---

## The real finding: the instrument, not the hypothesis

Across four blocks, the validity check — *does this specification detect a market
reaction to news that genuinely is new?* — has now failed three times:

| Block | Indicator | Validity t | Readable? |
|---|---|---|---|
| B1 | Industrial Production | −0.02 | no |
| B2 | CFNAI | 4.51 | yes, but the pass leans on COVID |
| B-2 (cc) | Core PCE | 0.32 | no |
| B-2 (overnight) | Core PCE | 1.26 | no |

That is a pattern about the **measurement**, not about the indicators. Two causes,
both fixable and neither requiring paid data:

1. **The outcome variable is wrong.** Macro announcement studies use
   interest-rate futures, not equity indices, because the signal-to-noise is far
   higher — the front end reprices sharply on inflation and activity data while
   SPY's day is dominated by everything else. Gilbert et al. used Treasury futures
   alongside the S&P precisely for this reason. Every block here used SPY.
2. **The window is still too wide.** The overnight fix was directionally right —
   validity improved from 0.32 to 1.26 — but 17 hours still swamps a release that
   is priced in seconds.

**This is the highest-value next step in the whole project**, and it costs a day,
not three weeks: re-run Test B's existing machinery with a rates instrument
(TLT/IEF daily, or 2-year yield changes from FRED, both free) as the outcome. The
vintage assembly, the release-date verification, the influence diagnostic and the
cost model are all built and tested. If validity passes there, every block already
run becomes readable — including the pre/post-2012 split that Test B and B-2 were
both built to deliver and neither could.

---

## Where this leaves Test C

**Still gated. Do not start.** Amendment 1 §3: Test C may begin only on a positive
B-2 result or a positive A-2 gradient. Neither occurred. A-2 was decisively null
and B-2 was unreadable.

But note precisely what has and has not been established, because the two
decision rules in the amendment do not cover the outcome that actually happened:

- **Test A is closed permanently** — that rule fired cleanly and is settled.
- **The stop-permanently trigger did not fire.** It requires a clean null *with
  validity passing*. Validity did not pass. The "public but unconnected"
  mechanism has therefore **not** been shown to lack empirical support; it has not
  been tested with a working instrument.

Treating B-2's unreadable result as a negative would be the single easiest
mistake to make from here, and it is the one the pre-registration was written to
prevent.

---

## Methodological notes

- **The config log is the denominator.** 162 evaluations across four tests,
  including every abandoned variant. Deflated Sharpe Ratios are computed against
  that cumulative count, read from the file rather than asserted, per Amendment 1
  §4.
- **Six amendments were made after seeing results.** Each is dated and disclosed
  in the relevant `preregistration.md`, never edited in silently. Five can only
  weaken a positive finding. The two that could have strengthened one — A-2's
  economically-scaled effect column and B-2's dual event window — are fenced
  explicitly: neither is part of a pass condition, both are applied to all rows
  rather than selectively, and neither changed a verdict.
- **A β column can lie.** In A-2 the raw per-decile β runs *backwards* because it
  is a slope whose regressor spans three orders of magnitude across deciles. The
  economically-scaled effect is the comparable quantity. A reader scanning the raw
  column would have drawn the opposite conclusion from the correct one.
- **Corwin–Schultz is the wrong spread estimator for liquid instruments** and the
  right one for illiquid ones; both are retained, assigned per instrument by ADV.
- **One real bug**: the price cache returned a file built for a later start date
  regardless of the start requested, silently truncating Test B's sample by five
  years and suppressing the pre/post-2012 split entirely. A cache keyed on symbol
  alone is a correctness bug, not a performance detail.
