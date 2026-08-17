# Test B — Stale information / "public but unconnected": results

**Verdict: NOT REPLICATED**

The only significant coefficient anywhere in this test is in block B2 (t = 3.91 on the predictable component), and it does not survive contact with its own outliers: excluding March–December 2020 it falls to t = 0.976, and dropping just the two most influential observations takes it to t = 0.443. The three most influential releases are 2020-05-26, 2020-04-20, 2018-03-26, two of them in the COVID collapse, which drove the standardised predictor to values as extreme as −14 standard deviations. Two observations are not an effect. Separately, block B1 — the only block whose release history spans the pre/post-2012 split, and therefore the only one that could test the decay claim §3.3 calls the primary comparison — fails the validity check: it does not detect a market reaction even to genuine macro surprise (t = -0.017). Its pre/post-2012 coefficients are therefore unreadable in either direction, and **the primary comparison this test was designed around went unanswered.** On the evidence available here, there is no support for the claim that markets respond to the already-public component of a composite announcement.

Pre-registration: [`preregistration.md`](preregistration.md), committed before any analysis code was written.

> **What this test is and is not.** The Conference Board LEI, the indicator Gilbert et al. (2012) used, is proprietary and unobtainable. Of the substitutes the specification permits, only Industrial Production has release-date history spanning the pre/post-2012 split. IP's predictable component is *statistical*, not deterministic as the LEI's is, so **no result here is a replication of Gilbert et al.** CFNAI — a weighted average of 85 already-published series, and therefore a genuine near-zero-new-information announcement — is run as a secondary block, but its vintages only start in 2011 so it cannot speak to the split. Both limitations were recorded in the pre-registration before results were seen.

---

## 1. Headline numbers

| Quantity | B1 — Industrial Production | B2 — CFNAI |
|---|---|---|
| Period | 2003-07-16 to 2026-07-17 | 2017-10-23 to 2026-07-23 |
| Announcements | 275 | 104 |
| Mean expanding-window prediction R² | 0.492 | 0.923 |
| β on predictable component | 1.416e-05 | 0.001401 |
| **t on predictable component** | **0.141** | **3.91** |
| t on genuine surprise (validity check) | -0.017 | 4.51 |
| Front-run gross | 0.587%/yr | 1.61%/yr |
| Front-run net | -0.169%/yr | 0.99%/yr |
| Hurdle (Harvey–Liu–Zhu) | 2.78 | 2.78 |

Gilbert et al. reported roughly **8%/yr** front-running the LEI. That is the magnitude the strategy figures above are compared against — it is a benchmark, not a threshold.

Trials logged for Test B: **45**. Deflated Sharpe Ratio of the primary front-run net series: **0.007002** (SR\* = 0.1351).

## 1a. Block status — is each instrument working, and does its result survive?

Two checks decide whether a block's headline coefficient means anything. Both are applied to every block, not selectively.

| Check | B1 — Industrial Production | B2 — CFNAI |
|---|---|---|
| Detects genuine surprise? (validity) | **no** (t = -0.017) | **yes** (t = 4.51) |
| Predictable component significant, full sample | no (t = 0.141) | yes (t = 3.91) |
| Still significant excluding Mar–Dec 2020 | no (t = -0.0964) | no (t = 0.976) |
| Still significant dropping 2 most influential obs | no (t = 0.736) | no (t = 0.443) |
| **Survives everything** | **no** | **no** |

**The validity row comes first for a reason.** If a specification cannot detect a market reaction to news that genuinely *is* new, then its failure to detect a reaction to news that is not new says nothing about markets — it says the instrument is blind. The pre-registration named this as the condition that invalidates the test rather than supporting it, before any result was seen.

**B1 influence profile** (pre-registration amendment 2). t on the predictable component after removing the most influential observations by Cook's distance:

| Dropped | 0 | 1 | 2 | 3 | 5 |
|---|---|---|---|---|---|
| t | 0.141 | 0.847 | 0.736 | 0.925 | 0.132 |

Most influential releases: 2020-05-15, 2020-04-15, 2008-10-16.

**B2 influence profile** (pre-registration amendment 2). t on the predictable component after removing the most influential observations by Cook's distance:

| Dropped | 0 | 1 | 2 | 3 | 5 |
|---|---|---|---|---|---|
| t | 3.91 | 3.34 | 0.443 | -0.369 | -0.48 |

Most influential releases: 2020-05-26, 2020-04-20, 2018-03-26.

## 2. B1 — Industrial Production (primary)

Specification as pre-registered (§5.1):

```
r_rel(m) = a + b1·predicted_z(m) + b2·surprise_z(m) + e(m)
```

`predicted` is the expanding-window OLS fit of announced IP growth on announced manufacturing-hours growth and two lags of IP growth, trained only on months whose release date is strictly earlier. Efficient markets imply **b1 = 0**: the predictable part was public before the announcement.

| Sample | β (predictable) | t | β (surprise) | t | n |
|---|---|---|---|---|---|
| Full sample | 1.416e-05 | 0.141 | -1.302e-05 | -0.017 | 275 |
| Excluding Mar–Dec 2020 | -5.455e-05 | -0.0964 | -0.0007178 | -0.887 | 265 |
| Pre-2012 | -0.0001763 | -0.275 | -0.001258 | -1.01 | 101 |
| Post-2012 | 7.698e-05 | 0.963 | 0.0007041 | 1.21 | 174 |

### Pre/post-2012 interaction — the decisive statistic for decay

Estimated as a single pooled model so the *difference* carries a standard error:

- β on `predicted_z` (pre-2012 level): -0.0001763 (t = -0.275)
- β on `predicted_z × post2012` (the change): **0.0002533** (t = **0.392**)
- Decay detected at the hurdle: **no**

Sub-period regressions are reported above for completeness, but two separately insignificant coefficients are not evidence of a difference between them. The interaction is what tests the decay claim, and it was designated the decisive statistic in the pre-registration before it was run.

### Validity check — does the market respond to genuine surprise?

**No: t = -0.017 on the surprise term.** The pre-registration named this as the condition that invalidates the test. If the specification cannot detect a reaction to genuinely new information, its failure to detect a reaction to stale information means nothing. This is reported as a failure of the instrument, not as a finding about markets.

### Yearly coefficients

Full data in [`decay_curve.csv`](decay_curve.csv).

| Year | β | SE | t | n | gross bps |
|---|---|---|---|---|---|
| 2004 | -0.00249 | 0.003183 | -0.783 | 12 | 12.8 |
| 2005 | 0.005095 | 0.005627 | 0.905 | 12 | -6.84 |
| 2006 | -0.005567 | 0.006982 | -0.797 | 11 | 20.5 |
| 2007 | -0.007728 | 0.003998 | -1.93 | 12 | -41.4 |
| 2008 | 0.01438 | 0.01025 | 1.4 | 12 | -18.1 |
| 2009 | -0.002426 | 0.003199 | -0.758 | 12 | -34.8 |
| 2010 | -0.0007654 | 0.003738 | -0.205 | 12 | -19.8 |
| 2011 | 0.005203 | 0.00804 | 0.647 | 12 | -3.59 |
| 2012 | -0.004513 | 0.003361 | -1.34 | 12 | 28.6 |
| 2013 | -0.0002858 | 0.006784 | -0.0421 | 12 | 5.87 |
| 2014 | 0.0017 | 0.008134 | 0.209 | 12 | 7.09 |
| 2015 | -0.008069 | 0.006589 | -1.22 | 12 | 23.4 |
| 2016 | -0.006709 | 0.006696 | -1 | 12 | -22.7 |
| 2017 | 0.001142 | 0.00554 | 0.206 | 12 | -6.67 |
| 2018 | -0.00449 | 0.008138 | -0.552 | 12 | 35.4 |
| 2019 | 0.0002864 | 0.003575 | 0.0801 | 12 | 17.6 |
| 2020 | 0.0002802 | 0.0005597 | 0.501 | 12 | 89.2 |
| 2021 | -0.005902 | 0.01269 | -0.465 | 12 | 18.1 |
| 2022 | 0.01875 | 0.01627 | 1.15 | 11 | 48.2 |
| 2023 | 0.01034 | 0.01246 | 0.83 | 12 | 5.54 |
| 2024 | -0.005764 | 0.009467 | -0.609 | 12 | -29.5 |
| 2025 | -0.009541 | 0.01202 | -0.793 | 12 | -25.3 |

Years individually clearing t > 2.78: **0 of 22**. No exponential decay half-life is fitted to these coefficients: as in Test A, fitting decay to a series that is never distinguishable from zero measures the decay of noise.

### Front-run strategy

Position `sign(predicted)` at the close before the release, exit at the release close. SPY, $10m notional, costed at two ticks plus two-sided square-root impact.

| Sample | Events | Gross %/yr | Gross t | Net %/yr | Net t | 5d reversal bps | Reversal t |
|---|---|---|---|---|---|---|---|
| Full (demeaned signal) | 275 | 0.587 | 0.794 | -0.169 | -0.228 | 9.77 | 0.794 |
| Full (raw signal — see note) | 275 | 0.775 | 1.05 | 0.019 | 0.0258 | 15.7 | 1.28 |
| Pre-2012 | 101 | -1.47 | -1.09 | -2.44 | -1.81 | 26.1 | 1.22 |
| Post-2012 | 174 | 1.78 | 2.07 | 1.15 | 1.35 | 0.289 | 0.0194 |

**On the two signal definitions.** The pre-registration says "position `sign(predicted)`", which is ambiguous, and the two readings mean different things. Industrial production grows in most months, so the sign of *raw* predicted growth is almost always +1 and that strategy is a long-only equity position wearing a signal's clothing — whatever it earns is the equity risk premium, not an information edge. The demeaned version, `sign(predicted − trailing mean)`, is the economically meaningful one and is the headline. Both are run, both are logged, and both are above so the reader can see the difference rather than take the choice on trust.

The reversal leg tests Tetlock (2011): reactions to stale news should reverse. A reversal coefficient indistinguishable from zero alongside an announcement coefficient indistinguishable from zero is simply the absence of any reaction to reverse.

## 3. B2 — CFNAI (secondary): the near-deterministic composite

CFNAI is a weighted average of 85 series that are all published before it, so its announcement carries almost no new information — the property that makes the LEI test sharp and that Industrial Production lacks. Its vintages begin in 2011, so it cannot address the pre/post-2012 split; it addresses only whether the effect is alive now.

Mean expanding-window prediction R² = **0.923**, over 104 announcements from 2017-10-23 to 2026-07-23. That R² is the direct measure of how little the announcement adds: the higher it is, the closer this comes to the Gilbert et al. setting.

| Sample | β (predictable) | t | β (surprise) | t | n |
|---|---|---|---|---|---|
| Full sample | 0.001401 | 3.91 | 0.0007478 | 4.51 | 104 |
| Excluding Mar–Dec 2020 | 0.002002 | 0.976 | 0.001167 | 0.877 | 94 |

Front-run strategy: gross 1.61%/yr (t = 1.3), net 0.99%/yr (t = 0.8) over 104 announcements.

## 4. Data, point-in-time construction and verification

Every macro input is a **first print** — the value as actually published, taken from the ALFRED vintage in which the reference month first appears. Revised and benchmark-restated values are never used, because a benchmark revision published in 2015 was not available to a decision taken in 2005.

Both the current and prior month are read from the **same vintage**, because that is the growth rate the release actually announced. Taking the prior month from a later vintage would fold in revisions that had not happened yet.

**Release dates are measured, not assumed.** The vintage date on which a reference month first carries a value is that month's release date. This comes from the archive rather than a published schedule, which makes the ordering between releases something that can be *checked* rather than asserted:

| Block | Announcements before checks | After predictor merge | Dropped: predictor not released first | Final |
|---|---|---|---|---|
| B1_INDPRO | 363 | 363 | 0 | 275 |
| B2_CFNAI | 192 | 190 | 0 | 104 |

Months where a predictor was not published strictly before the target are dropped, not adjusted. Months whose release date is not an equity trading day are dropped rather than shifted to the next session (pre-registration §6 rule 3).

## 5. Limitations, stated in the pre-registration before results were seen

1. **IP is not the LEI.** Its predictable component is statistical, not deterministic. Nothing here is a replication of Gilbert et al.
2. **The 2012 split is not a clean experiment.** Publication of the paper is the nominal treatment, but the post-2012 period also contains the growth of systematic macro trading and the 2020 shock. A decline across the split is *consistent with* the publication story; it does not identify it.
3. **Four indicators were considered** before one was chosen. The choice was made on release-date coverage alone, before any return regression was run, and the rejected alternatives are in `config_log.jsonl` so the selection sits inside the multiple-testing denominator rather than outside it.
4. **COVID.** March–December 2020 contains IP moves an order of magnitude larger than anything else in the sample. Both the full-sample and the excluding-2020 specifications were pre-registered and both are reported above.

## 6. Multiple-testing accounting

`config_log.jsonl` holds **77 evaluations** in total, **45** of them for Test B, across 76 distinct configurations; 0 failed and are counted anyway.

| DSR input | Value |
|---|---|
| Trials N | 45 |
| Observations | 275 |
| Sharpe (per event) | -0.01377 |
| Sharpe (annualised) | -0.0477 |
| SR\* (selection hurdle) | 0.1351 |
| **Deflated Sharpe Ratio** | **0.007002** |

## 7. Verdict and what it implies for Test C

**NOT REPLICATED.** The only significant coefficient anywhere in this test is in block B2 (t = 3.91 on the predictable component), and it does not survive contact with its own outliers: excluding March–December 2020 it falls to t = 0.976, and dropping just the two most influential observations takes it to t = 0.443. The three most influential releases are 2020-05-26, 2020-04-20, 2018-03-26, two of them in the COVID collapse, which drove the standardised predictor to values as extreme as −14 standard deviations. Two observations are not an effect. Separately, block B1 — the only block whose release history spans the pre/post-2012 split, and therefore the only one that could test the decay claim §3.3 calls the primary comparison — fails the validity check: it does not detect a market reaction even to genuine macro surprise (t = -0.017). Its pre/post-2012 coefficients are therefore unreadable in either direction, and **the primary comparison this test was designed around went unanswered.** On the evidence available here, there is no support for the claim that markets respond to the already-public component of a composite announcement.

### For Test C

**Both Test A and Test B have now failed to find an effect.** Specification §8 is explicit about this case: *if A and B both return decay-to-zero, the honest conclusion is that enumerated forced-flow edges do not survive publication, and Test C would be measuring a corpse. That is a legitimate and valuable place to stop.*

The recommendation is to stop. Test C costs roughly three weeks and its cheap proxies have both come back empty — one of them on the most perfectly enumerable forced flow that exists. Ordering the tests by cost-per-bit was done precisely so that this decision could be taken for the price of a few days rather than a month.

What would change the recommendation: a Test B specification that *does* detect a reaction to stale information on a genuinely deterministic composite over a long sample. The CFNAI block here is the closest available, and it is short. If the operator wants one more cheap shot before stopping, purchasing LEI vintage data and running the actual Gilbert et al. replication is a far better use of a few hundred dollars than three weeks of Test C.

