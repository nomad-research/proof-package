# Test B-3 — Rates re-run: results

**Verdict: VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES**

The rates instrument works. The positive control passes at t = 4.68, with the correct sign and a coherent yield/price relationship, so a null from it is readable rather than blind.

On the readable block, the predictable component **does** clear the hurdle in raw form in 2 of 3 combinations — this is not a flat zero and should not be described as one. But **none survives the pre-registered influence diagnostic.** Dropping a single observation takes the strongest of them from −2.98 to −1.00. The three most influential releases are the same COVID dates that drove the SPY result — March, April and May 2020. One combination swings from −3.55 to −1.36 to −4.67 depending on which two or three points are removed, which is not a coefficient with an effect behind it; it is a small sample being steered by its extremes.

This is the outcome the pre-registration named as the stop trigger, and it is **the first clean stop in this project** — every previous null was unreadable because the instrument was blind, and this one is not. Stated plainly and without softening: on the one indicator that a working instrument can read, **there is no robust market response to the already-public component of a composite announcement.** No fourth instrument will be proposed.

**The prize was not won.** B1 — Industrial Production, the only block spanning 2012 and the only one that could ever answer the pre/post-2012 question — **still fails validity**, on all five outcomes, best t = 2.22. But the *reason* has changed, and that is worth something. Previously B1's failure was ambiguous: a blind instrument and a silent announcement look identical. Now the instrument is demonstrably not blind — the control clears the hurdle at 4.68 on the same data — so the failure is attributable to the announcement. **Industrial production surprises do not measurably move the front end.** The split remains unanswerable, but now demonstrably rather than presumptively.

Pre-registration: [`preregistration.md`](preregistration.md), committed before this analysis was written. The overnight window and the validity-first ordering were both registered **in advance** this time, which removes the fence that was needed when the window was added mid-run.

---

## 1. Validity — reported first, before any other coefficient

The question this answers is **not** whether markets respond to stale information. It is whether the instrument can detect a response to information that is genuinely **new**. If it cannot, its null on stale information carries no information at all — which is exactly why three of the four SPY blocks were unreadable.

A block-outcome combination passes only if `|t| > 2.78` **and** the sign matches the pre-registered direction: a positive activity or inflation surprise raises yields and lowers bond prices.

| Block | Outcome | Window | n | β (surprise) | t | Sign | Pass |
|---|---|---|---|---|---|---|---|
| B1_INDPRO | `DGS2` | day-over-day | 275 | 0.4984 | **1.94** | ok | no |
| B1_INDPRO | `TLT_on` | overnight | 275 | -0.0004444 | **-1.3** | ok | no |
| B1_INDPRO | `TLT_cc` | close-to-close | 275 | -0.0006958 | **-1.36** | ok | no |
| B1_INDPRO | `IEF_on` | overnight | 275 | -0.0002027 | **-1.6** | ok | no |
| B1_INDPRO | `IEF_cc` | close-to-close | 275 | -0.0004043 | **-2.22** | ok | no |
| B2_CFNAI | `DGS2` | day-over-day | 104 | 0.05246 | **0.921** | ok | no |
| B2_CFNAI | `TLT_on` | overnight | 104 | -0.0001803 | **-2.42** | ok | no |
| B2_CFNAI | `TLT_cc` | close-to-close | 104 | -0.0003188 | **-4.68** | ok | **YES** |
| B2_CFNAI | `IEF_on` | overnight | 104 | -7.251e-05 | **-2.79** | ok | **YES** |
| B2_CFNAI | `IEF_cc` | close-to-close | 104 | -0.0001085 | **-4.49** | ok | **YES** |
| B2ext_COREPCE | `DGS2` | day-over-day | 254 | -0.1562 | **-0.428** | **wrong** | no |
| B2ext_COREPCE | `TLT_on` | overnight | 253 | 0.0001279 | **0.35** | **wrong** | no |
| B2ext_COREPCE | `TLT_cc` | close-to-close | 253 | 0.0003831 | **0.555** | **wrong** | no |
| B2ext_COREPCE | `IEF_on` | overnight | 253 | -1.477e-07 | **-0.000804** | ok | no |
| B2ext_COREPCE | `IEF_cc` | close-to-close | 253 | 0.0002703 | **0.96** | **wrong** | no |

**3 of 15** combinations pass. Hurdle 2.78.

### Coherence check

A rates outcome gives a free consistency test that SPY could not: yields and bond prices must move in **opposite** directions on the same surprise. Same-signed coefficients would mean the instrument is not measuring what it is meant to, regardless of significance.

| Block | β on DGS2 (bp) | β on TLT (return) | Coherent? |
|---|---|---|---|
| B1_INDPRO | 0.4984 | -0.0006958 | yes |
| B2_CFNAI | 0.05246 | -0.0003188 | yes |
| B2ext_COREPCE | -0.1562 | 0.0003831 | yes |

### The positive control

CFNAI passed validity on SPY at t = 4.51, so it is the control: if it does **not** also pass on rates, the rates instrument itself is suspect and the finding is about the instrument rather than about any block.

**It passes** — strongest at `TLT_cc`, t = -4.68. The rates instrument is working, so the other blocks' results are about those blocks.

## 2. Predictable component — only where validity passed

| Block / outcome | β (predictable) | t | t after dropping 2 | n |
|---|---|---|---|---|
| B2_CFNAI|TLT_cc | -0.0004347 | **-2.98** | 0.922 | 104 |
| B2_CFNAI|IEF_on | -9.838e-05 | **-1.83** | -0.365 | 104 |
| B2_CFNAI|IEF_cc | -0.0001859 | **-3.55** | -1.36 | 104 |

## 3. Blocks, unchanged from B and B-2

| Block | Announcements | Mean prediction R² | Role |
|---|---|---|---|
| B1_INDPRO | 361 | 0.496 | the prize - only block spanning 2012 |
| B2_CFNAI | 188 | 0.9 | positive control - passed validity on SPY |
| B2ext_COREPCE | 316 | 0.284 | weak analogue (R2 0.28) but has the sample |

Only the outcome variable changed. The vintage assembly, first-print discipline, archive-measured release dates, ordering verification and expanding-window prediction are byte-identical to the runs that produced the SPY results.

## 4. What was and was not fixed by changing instrument

| | SPY | Rates |
|---|---|---|
| B1 validity | t = −0.02 | 2.22 (best across outcomes) |
| B2 validity | t = 4.51 | 4.68 (best across outcomes) |
| B-2 validity | t = 1.26 | 0.96 (best across outcomes) |

## 5. Multiple testing

`config_log.jsonl` now holds **204 evaluations** across all tests (A: 32, A2: 19, B: 45, B2: 66, B3: 42), 181 distinct configurations, 0 failed and counted anyway.

Three outcomes × two windows where available × three blocks is a deliberate expansion of the trial count and was registered as such. It is justified because picking one outcome in advance and reporting only that would hide precisely the disagreement the pre-registration requires to be surfaced. No Deflated Sharpe is reported here because no tradeable strategy was run — this test measures a coefficient, not a return stream.

## 6. Limitations, stated in the pre-registration before running

1. **`DGS2` cannot use the overnight window.** It is a single daily observation with no open or close, so the primary instrument and the primary window cannot be combined. `TLT` and `IEF` carry the overnight window instead.
2. **`TLT` and `IEF` are the wrong maturity.** 20y+ and 7–10y respectively; neither is the 2-year point where macro sensitivity is highest. They are the only free instruments with an intraday open.
3. **Core PCE remains a weak analogue** at R² = 0.28. Changing the outcome variable does not repair a weak predictable component.
4. **This is not a replication of Gilbert et al.** The LEI is still unobtainable; these are the same substitutes, better measured.

## 7. Verdict

**VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES.** The rates instrument works. The positive control passes at t = 4.68, with the correct sign and a coherent yield/price relationship, so a null from it is readable rather than blind.

On the readable block, the predictable component **does** clear the hurdle in raw form in 2 of 3 combinations — this is not a flat zero and should not be described as one. But **none survives the pre-registered influence diagnostic.** Dropping a single observation takes the strongest of them from −2.98 to −1.00. The three most influential releases are the same COVID dates that drove the SPY result — March, April and May 2020. One combination swings from −3.55 to −1.36 to −4.67 depending on which two or three points are removed, which is not a coefficient with an effect behind it; it is a small sample being steered by its extremes.

This is the outcome the pre-registration named as the stop trigger, and it is **the first clean stop in this project** — every previous null was unreadable because the instrument was blind, and this one is not. Stated plainly and without softening: on the one indicator that a working instrument can read, **there is no robust market response to the already-public component of a composite announcement.** No fourth instrument will be proposed.

**The prize was not won.** B1 — Industrial Production, the only block spanning 2012 and the only one that could ever answer the pre/post-2012 question — **still fails validity**, on all five outcomes, best t = 2.22. But the *reason* has changed, and that is worth something. Previously B1's failure was ambiguous: a blind instrument and a silent announcement look identical. Now the instrument is demonstrably not blind — the control clears the hurdle at 4.68 on the same data — so the failure is attributable to the announcement. **Industrial production surprises do not measurably move the front end.** The split remains unanswerable, but now demonstrably rather than presumptively.

