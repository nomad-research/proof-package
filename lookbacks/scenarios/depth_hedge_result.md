# Depth-hedge test — result (run 2026-09-30, after the pre-registration commit 363e7d9)

Script: `lookbacks/scenarios/depth_hedge.py`. Rule, legs, windows and thresholds are as pre-registered and were not changed.

```
events: 29  2019-01-09, 2019-06-18, 2019-07-10, 2019-08-13, 2019-09-04, 2020-09-16, 2020-10-05, 2020-11-02, 2020-11-24, 2021-01-05, 2021-02-22, 2021-03-24, 2021-08-23, 2021-12-06, 2022-03-01, 2022-03-17, 2022-04-12, 2022-05-04, 2022-07-18, 2022-09-09, 2022-09-28, 2022-11-04, 2023-03-27, 2023-10-09, 2024-07-31, 2024-10-03, 2025-01-10, 2025-04-09, 2025-06-11

basket        meanR   meanF  worstF  CVaR25(F)  R kept  corr(F) P(better) CVaR gain
T1+T1         0.040   0.016  -0.140     -0.074    1.00     0.91      0.00       +0%
T1+T2         0.039   0.018  -0.160     -0.080    0.98     0.83      0.29       -7%
T1+T3         0.031   0.013  -0.123     -0.062    0.77     0.57      0.83      +17%
T1+control    0.028   0.016  -0.111     -0.053    0.70     0.44      0.97      +29%

verdict per tier (pre-registered rule):
  T1+T2: downside gain -7% (P better 0.29) [fail]; R kept 0.98 [ok]; beats control's R kept 0.70 [ok] -> NOT SUPPORTED
  T1+T3: downside gain +17% (P better 0.83) [fail]; R kept 0.77 [ok]; beats control's R kept 0.70 [ok] -> NOT SUPPORTED
```

## Verdict under the pre-registered rule: **not supported for either tier**

- **Tier 2 (oilfield services, midstream):** no downside gain (-7%, P better 0.29). They keep the reaction (R kept 0.98) but move with XOP in the fade (correlation 0.83).
- **Tier 3 (Canada, Norway):** a downside gain of +17% (P better 0.83), a near miss of the 20% bar; R kept 0.77, above the SPY control's 0.70. Fails condition 1 only.

## What the numbers do say

- **The correlation gradient Rob described is there.** Fade-window correlation with XOP falls with depth: 0.91 (Tier 1), 0.83 (Tier 2), 0.57 (Tier 3), 0.44 (an unrelated asset, SPY).
- **Impact falls with it.** R kept falls from 0.98 (Tier 2) to 0.77 (Tier 3) to 0.70 (SPY). Less correlated and less responsive come together, which is the trade-off the dilution model predicts.
- **Net of that, depth did not beat an unrelated asset here.** SPY cut the worst-quarter fade loss by 29% (P better 0.97); Tier 3 cut it by 17% (P 0.83) and kept a little more of the reaction (0.77 against 0.70). The difference in what each keeps is small.

## Limits (read before using any of it)

- 29 events, one asset class; the worst quarter is about 7 events. The bootstrap does not separate Tier 3 from the control.
- Equal-weight buy-and-hold. A maximin optimiser would weight the legs differently, and this test does not.
- **"R kept" is a weak measure of whether a leg keeps the thesis:** half of every pair is XOP, which alone keeps half of the baseline reaction, so a leg with no
  response at all would score about 0.5. A cleaner measure is the second leg's own response in R, and that was not pre-registered, so it is not used for the verdict.
- The Tier 3 legs are broad national indices (Canada includes banks), a loose oil link. A better deeper leg (tankers, a specific service chain) is a different test
  and needs its own pre-registration and events the builder has not seen, ideally forward ones.
- Raw returns include market direction; SPY only partly controls it.
