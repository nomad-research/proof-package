# Depth-hedge test v3 (a long at depth that is a synthetic short) — result (run 2026-09-30)

Pre-registration: `depth_hedge_v3_prereg.md` (commit ec95bbd, before any number). Script: `depth_hedge_v3.py`. Rule, baskets and thresholds unchanged. Disclosure in the prereg: the 2026 holdout
was partly seen in v2 (event dates; T1a, T3 and control returns); T4 and T5 had not been computed on any window.

## Main window, 2019-01-02 to 2025-12-30
```
dropped symbols: none | basket sizes: {'T1a': 4, 'T1b': 4, 'T3': 4, 'T4': 4, 'T5': 4, 'control': 4}
events: 35  2019-01-09, 2019-06-20, 2019-07-10, 2019-09-04, 2019-12-04, 2020-09-16, 2020-10-05, 2020-11-09, 2020-11-24, 2021-01-05, 2021-03-04, 2021-03-24, 2021-04-14, 2021-07-21, 2021-08-23, 2021-12-06, 2021-12-21, 2022-02-28, 2022-03-17, 2022-04-04, 2022-05-04, 2022-07-07, 2022-08-29, 2022-09-28, 2022-11-04, 2023-02-07, 2023-03-27, 2023-05-05, 2023-10-09, 2023-11-17, 2024-07-31, 2024-10-03, 2025-04-09, 2025-06-11, 2025-10-23

tier        meanR   t(R)  %R<0  corr(F) F|T1a worst pair CVaR   gain     P upside given up
T3          0.022   3.74   23%     0.78      -0.018    -0.055   +35%  1.00             27%
T4          0.008   0.77   49%     0.42      -0.007    -0.062   +27%  0.99             42%
T5          0.009   2.17   31%    -0.10      -0.005    -0.057   +34%  0.99             41%
control     0.005   1.76   40%     0.19       0.002    -0.044   +48%  1.00             45%

synthetic-short verdict (pre-registered; all four must hold):
  T4: (1) t(R) 0.77 [fail]  (2) corr(F) 0.42 [fail]  (3) F in T1a's worst quarter -0.007 [fail]  (4) gain +27%, P 0.99 [ok]  -> NOT (1 of 4)
  T5: (1) t(R) 2.17 [fail]  (2) corr(F) -0.10 [fail]  (3) F in T1a's worst quarter -0.005 [fail]  (4) gain +34%, P 0.99 [ok]  -> NOT (1 of 4)
```
## Holdout, 2026-01-02 to 2026-09-29
```
dropped symbols: none | basket sizes: {'T1a': 4, 'T1b': 4, 'T3': 4, 'T4': 4, 'T5': 4, 'control': 4}
events: 9  2026-02-18, 2026-03-05, 2026-03-24, 2026-04-20, 2026-05-12, 2026-06-01, 2026-07-08, 2026-07-23, 2026-08-10

tier        meanR   t(R)  %R<0  corr(F) F|T1a worst pair CVaR   gain     P upside given up
T3          0.010   1.33   33%    -0.53       0.032    -0.018   +74%  0.87             35%
T4         -0.028  -2.80   89%    -0.76       0.092    -0.038   +45%  0.73             95%
T5         -0.005  -0.78   67%    -0.70       0.075    -0.018   +75%  0.82             58%
control    -0.004  -0.71   67%    -0.52       0.021    -0.024   +66%  0.93             57%

synthetic-short verdict (pre-registered; all four must hold):
  T4: (1) t(R) -2.80 [ok]  (2) corr(F) -0.76 [ok]  (3) F in T1a's worst quarter +0.092 [ok]  (4) gain +45%, P 0.73 [fail]  -> NOT (3 of 4)
  T5: (1) t(R) -0.78 [fail]  (2) corr(F) -0.70 [ok]  (3) F in T1a's worst quarter +0.075 [ok]  (4) gain +75%, P 0.82 [ok]  -> NOT (3 of 4)
```

## Verdict under the pre-registered rule: **not confirmed**
A tier is a synthetic short only if all four conditions hold in the main window **and** the holdout. Neither tier did.
- **T4 (airlines, cruise):** failed three of four in the main window (mean reaction +0.8%, t 0.77; fade correlation +0.42). In the holdout it met three of four: reaction -2.8% (t -2.80),
  fade correlation -0.76, +9.2% in T1a's worst-quarter fades; it failed only the pair-gain test on probability (P 0.73 against 0.80, on 9 events). This was against the builder's
  expectation (70% for the main window).
- **T5 (homebuilders, big retail):** not reliably negative in either window (t 2.17 then -0.78), as the builder expected.

## Exploratory, post hoc (not part of the verdict; labelled as such)
The sign of the deep node depends on the kind of oil spike. Mean R of T4: 2019 to 2021 **+3.3%**, 2022 to 2025 **-1.7%**, 2026 **-2.8%**; on days the market fell, **-2.2%**; on days it rose, **+1.6%**.
The 2019 to 2021 spikes were mostly demand-recovery days, when everything rose together. So one mechanical rule (crude up 4%) mixes scenarios with opposite signs at depth, and that dilutes any pooled reading.
A follow-up would need to classify events by cause with a rule fixed in advance (for example the market's direction on the event day, or a documented supply cause) and be pre-registered before it is run, ideally on forward events.

## Limits
35 and 9 events; equal weights; chain assignments are judgements; heavy market beta in T4; the holdout was partly seen; the split above was made after the result and must not be used as a verdict.
