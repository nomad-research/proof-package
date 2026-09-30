# Hedge-DAG validation — result (run 2026-09-30, after the pre-registration commit f19898c)

Script: `validate.py`; exposures: `exposures.json` (12 filings, every quote verified literally). Rule, exposures and thresholds as pre-registered; nothing changed.

```
normaliser: market cap (shares from 10-K cover XBRL) {'OXY': 984132678.0, 'EOG': 545787010.0, 'XOM': 4309638821.0, 'MPC': 307213828.0}
events: 13  2025-04-09, 2025-06-11, 2025-10-23, 2026-02-18, 2026-03-05, 2026-03-24, 2026-04-20, 2026-05-12, 2026-06-01, 2026-07-08, 2026-07-23, 2026-08-10, 2026-09-01

rho_doc  (documented-exposure model vs realised, demeaned within event): +0.30  bootstrap 10th percentile +0.11
rho_beta (trailing-beta model): +0.27   difference +0.03  (bootstrap 10th percentile of the difference -0.23)
spread (E&P mean minus MPC): sign hit rate 62%, correlation across events +0.37

verdict (pre-registered): (1) divergence predictable in cross-section [ok]; (2) adds beyond beta [fail]; (3) spread [fail]
=> NOT SUPPORTED

per-event: date, predicted spread, realised spread
  2025-04-09  +0.0578  -0.0076
  2025-06-11  +0.0525  +0.0339
  2025-10-23  -0.0157  -0.0309
  2026-02-18  -0.0046  +0.0685
  2026-03-05  +0.1871  +0.0432
  2026-03-24  +0.0011  -0.0179
  2026-04-20  -0.1140  -0.0002
  2026-05-12  +0.0632  +0.0384
  2026-06-01  +0.0841  -0.0194
  2026-07-08  -0.0447  -0.0653
  2026-07-23  -0.0262  -0.0118
  2026-08-10  -0.0484  -0.1167
  2026-09-01  +0.1353  -0.0313
```

## Verdict under the pre-registered rule: **not supported**
- (1) **Divergence predictable in the cross-section: ok.** rho_doc +0.30 (bar 0.30, borderline), bootstrap 10th percentile +0.11.
- (2) **Adds beyond the beta model: fail.** rho_beta +0.27, difference +0.03 against a bar of +0.10; the bootstrap 10th percentile of the difference is -0.23.
- (3) **Spread, E&Ps against MPC: fail, narrowly.** Sign hit rate 62% (8 of 13; bar 65%), correlation +0.37 (bar 0.40).
"Divergence predictable" needed (1) and (3), so it is not supported. The builder's expectation was 40% / 30% / 45% for the three; (1) came in, (2) and (3) did not.

## What it says
- The documented exposures rank the four names about as well as a trailing beta to crude does. They did not add anything measurable beyond it here. The E&Ps' documented exposures rank almost like their betas, and the one place the model could add
  (a crack shock that diverges from crude, with MPC the odd name out) has one refiner and 13 events.
- The predicted spread is right in sign 8 times in 13 and wrong in size: predicted spreads run several times the realised ones (for example +0.187 against +0.043 on 2026-03-05). An annual sensitivity applied to a 3-day window overstates.
- **Coverage is the larger finding.** Of 12 large oil companies, 4 disclose an unhedged sensitivity in income terms (OXY, EOG, XOM, MPC; APA only as revenue), 3 only for their hedge book, and 4 none (COP, VLO, PSX, CVX).
  Only one of the two large refiners that report on the same basis, MPC, discloses a crack sensitivity. The data that makes chains diverge is mostly not disclosed in one comparable place.

## Limits
13 events, 4 names, one refiner; mixed metrics; Brent proxied by WTI; the crack is a 3-2-1 proxy; the threshold on (1) was met at the bar itself; FY2024 exposures apply cleanly only to events after February 2025.
The result cannot separate "the mechanism is absent" from "the test is too small and the exposure data too thin".
