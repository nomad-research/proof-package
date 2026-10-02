# Depth-hedge test v2 (equity baskets) — result (run 2026-09-30)

Pre-registration: `depth_hedge_v2_prereg.md` (commit e0a44c1; the holdout rule was added in 3790419, before any 2026 number). Script: `depth_hedge_v2.py`.
Thresholds, baskets, windows and the rule were not changed between runs. The ETF version (`depth_hedge_result.md`) is superseded; both are kept, and the
fact that a first design was re-run on Rob's instruction (no funds) is disclosed here: two tests were run on the same claim, and their verdicts differ.

## Main run, 2019-01-02 to 2025-12-30 (35 events)
```
dropped symbols: none | basket sizes: {'T1a': 4, 'T1b': 4, 'T2': 4, 'T3': 4, 'control': 4, 'tankers': 4, 'defence': 4}
events: 35  2019-01-09, 2019-06-20, 2019-07-10, 2019-09-04, 2019-12-04, 2020-09-16, 2020-10-05, 2020-11-09, 2020-11-24, 2021-01-05, 2021-03-04, 2021-03-24, 2021-04-14, 2021-07-21, 2021-08-23, 2021-12-06, 2021-12-21, 2022-02-28, 2022-03-17, 2022-04-04, 2022-05-04, 2022-07-07, 2022-08-29, 2022-09-28, 2022-11-04, 2023-02-07, 2023-03-27, 2023-05-05, 2023-10-09, 2023-11-17, 2024-07-31, 2024-10-03, 2025-04-09, 2025-06-11, 2025-10-23

pair              meanR   meanF  worstF  CVaR25(F) 2nd own R R share corr(F) P(better) CVaR gain
T1a+T1b           0.045   0.014  -0.138     -0.085     0.040    1.00    0.96      0.00       +0%
T1a+T2            0.042   0.016  -0.147     -0.080     0.034    0.86    0.90      0.85       +6%
T1a+T3            0.036   0.019  -0.103     -0.055     0.022    0.57    0.78      1.00      +35%
T1a+control       0.027   0.011  -0.089     -0.044     0.005    0.12    0.19      1.00      +48%
T1a+tankers*      0.041   0.021  -0.154     -0.083     0.033    0.83    0.34      0.55       +3%
T1a+defence*      0.035   0.012  -0.095     -0.058     0.020    0.50    0.41      1.00      +32%

verdict per tier (pre-registered rule; * = exploratory, not in the verdict):
  T2: downside gain +6% (P 0.85) [fail]; own R share of T1b 0.86 [ok]; beats control's share 0.12 [ok] -> NOT SUPPORTED
  T3: downside gain +35% (P 1.00) [ok]; own R share of T1b 0.57 [ok]; beats control's share 0.12 [ok] -> SUPPORTED
```
**T3 supported, T2 not supported** under the pre-registered rule. This was **not** the builder's expectation (60% that T3 would be diluted or unsupported).

## Holdout, 2026-01-02 to 2026-09-29 (9 events, at or above the registered minimum of 8)
```
dropped symbols: none | basket sizes: {'T1a': 4, 'T1b': 4, 'T2': 4, 'T3': 4, 'control': 4, 'tankers': 4, 'defence': 4}
events: 9  2026-02-18, 2026-03-05, 2026-03-24, 2026-04-20, 2026-05-12, 2026-06-01, 2026-07-08, 2026-07-23, 2026-08-10

pair              meanR   meanF  worstF  CVaR25(F) 2nd own R R share corr(F) P(better) CVaR gain
T1a+T1b           0.031   0.033  -0.130     -0.070     0.029    1.00    0.99      0.00       +0%
T1a+T2            0.028   0.017  -0.120     -0.059     0.024    0.81    0.63      0.73      +16%
T1a+T3            0.021   0.016  -0.058     -0.018     0.010    0.33   -0.53      0.88      +74%
T1a+control       0.014   0.018  -0.050     -0.024    -0.004   -0.15   -0.52      0.93      +66%
T1a+tankers*      0.020   0.030  -0.076     -0.041     0.008    0.26    0.33      0.88      +42%
T1a+defence*      0.015   0.001  -0.096     -0.062    -0.001   -0.04    0.15      0.54      +12%

verdict per tier (pre-registered rule; * = exploratory, not in the verdict):
  T2: downside gain +16% (P 0.73) [fail]; own R share of T1b 0.81 [ok]; beats control's share -0.15 [ok] -> NOT SUPPORTED
  T3: downside gain +74% (P 0.88) [ok]; own R share of T1b 0.33 [fail]; beats control's share -0.15 [ok] -> DILUTED
```
**T3 diluted, T2 not supported.** The T3 downside gain replicated in direction and grew (+74%), but its own reaction share fell from 0.57 to 0.33, below the 0.50 bar.

## Read together
- Downside: T3 cut the worst-quarter fade loss in both windows (+35%, +74%). T2 did not (+6%, +16%).
- Keeping the thesis: T3's own reaction share was 0.57, then 0.33 (bar 0.50). It did not hold up out of sample. The unrelated control was 0.12 and -0.15.
- Correlation with the first basket in the fade fell with depth in both windows (T2 0.90, 0.63; T3 0.78, -0.53; control 0.19, -0.52).
- **Verdict of the pair of runs: not confirmed.** Depth bought diversification of the downside, and the thesis response thinned with it, as the dilution model predicts; whether it thins
  past the bar is unstable at this sample size.

## Limits
35 and 9 events; the holdout's worst quarter is 3 events, so its bootstrap probabilities carry little weight; equal weights and buy-and-hold, no optimiser; tiers are causal-chain
judgements; T3 includes a bank and a railcar lessor; raw returns include market direction. A lower-volatility basket cuts the worst quarter on its own, which is why the rule also asks
that the tier keep the thesis response and beat the control on that.
