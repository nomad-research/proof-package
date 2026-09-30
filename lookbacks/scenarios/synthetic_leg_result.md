# Synthetic-exposure leg — result (run 2026-09-30, after the pre-registration commit dc52eca)

Script: `synthetic_leg.py`; rule, universe and thresholds unchanged.

## Main window, 2019-01-02 to 2025-12-30 (35 events)
```
dropped: none | universe size 46
events: 35

PART A (calibration, S has A's crude loading and a residual chain with correlation rho to A's): baseline A+T1b CVaR25(F) -0.085
  rho +0.9: pair CVaR25(F) gain vs baseline -3%   [correlated thesis]
  rho +0.5: pair CVaR25(F) gain vs baseline -2%   []
  rho +0.0: pair CVaR25(F) gain vs baseline +2%   [uncorrelated thesis]
  rho -0.5: pair CVaR25(F) gain vs baseline +14%   []
  first rho (from above) at which the gain reaches 30%: -0.95

PART B (real non-energy equities, long-only, unlevered)  f = achievable fraction of A's crude loading: mean 0.32, median 0.32
pair       CVaR25(F)   gain P(better)   own R  R share  corr(F) w A
A+T1b         -0.085    +0%      0.00   0.040     1.00         0.96
A+S_corr      -0.055   +36%      1.00   0.021     0.53         0.55
A+S_unc       -0.047   +45%      1.00   0.005     0.14         0.01

verdict for this window (pre-registered; needs both windows): f>=0.50 [fail]; gain>=20% & P>=0.80 [ok]; R share>=0.50 and above S_unc's [ok] -> DILUTED
```
## Holdout, 2026-01-02 to 2026-09-29 (9 events)
```
dropped: none | universe size 46
events: 9

PART A (calibration, S has A's crude loading and a residual chain with correlation rho to A's): baseline A+T1b CVaR25(F) -0.070
  rho +0.9: pair CVaR25(F) gain vs baseline +2%   [correlated thesis]
  rho +0.5: pair CVaR25(F) gain vs baseline +5%   []
  rho +0.0: pair CVaR25(F) gain vs baseline +7%   [uncorrelated thesis]
  rho -0.5: pair CVaR25(F) gain vs baseline +18%   []
  first rho (from above) at which the gain reaches 30%: None

PART B (real non-energy equities, long-only, unlevered)  f = achievable fraction of A's crude loading: mean 0.30, median 0.29
pair       CVaR25(F)   gain P(better)   own R  R share  corr(F) w A
A+T1b         -0.070    +0%      0.00   0.029     1.00         0.99
A+S_corr      -0.038   +46%      0.83   0.005     0.18         0.09
A+S_unc       -0.036   +48%      0.80  -0.006    -0.22        -0.19

verdict for this window (pre-registered; needs both windows): f>=0.50 [fail]; gain>=20% & P>=0.80 [ok]; R share>=0.50 and above S_unc's [fail] -> DILUTED
```

## Verdict under the pre-registered rule (needs both windows): **not supported; diluted**
- Part B: the best long-only, unlevered non-energy basket reached only **f = 0.32** of the oil basket's crude loading (0.30 in the holdout), below the 0.50 bar. The pair gain cleared the bar in both windows (+36%, +46%);
  the reaction share cleared it only in the main window (0.53, above S_unc's 0.14) and failed in the holdout (0.18). Builder's expectation (about 75% that f falls well short of 0.5): came in.
- The "correlated-thesis" synthetic (S_corr) and the "uncorrelated" one (S_unc) had **about the same downside gain** (+36% against +45%; +46% against +48%). What S_corr kept over S_unc was some of the reaction, in one window.

## What Part A says (the isolating result)
With the synthetic leg carrying **the same crude loading** as the oil basket, its downstream residual chain buys very little: a worst-quarter fade gain of **-3% at rho +0.9, +2% at rho 0, +14% at rho -0.5** (main window; +2%, +7%, +18% in the holdout), and reaching 30% needed rho of about -0.95 (never in the holdout).
The reason is arithmetic and it is the point: in the worst fades the loss is the crude channel itself reversing. A second leg with the same loading on that channel reverses with it, and decorrelating the residual chain only diversifies the small part that is left.

So every downside gain in the depth and synthetic tests (Tier 3, the SPY control, S_corr, S_unc) came from a **lower loading on the crude channel**, which is de-risking, not from decorrelation at a fixed loading.
If the mechanism exists, it cannot be "same exposure through a different residual chain". It has to be a leg whose payoff on the fade is different in kind: a different loading on the channel that fades, or a channel with a different timing or persistence (a margin, a freight rate, a backlog), which is what the outcome-by-outcome scenario in `narrative_hedge.py` assumed and no real test has yet supplied.

## Limits
35 and 9 events; long-only, unlevered equities (leverage or derivatives would raise f and are for later); a linear proxy for the residual-correlation constraint; Part A is arithmetic on real crude moves, not a test of the world.
