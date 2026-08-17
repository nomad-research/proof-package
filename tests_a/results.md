# Test A — Leveraged ETF rebalancing decay: results

**Verdict: FAIL**

The pooled coefficient does not clear the hurdle (t = 1.58) and no year in the last five is individually significant. The most perfectly enumerable forced flow that exists — closed-form, fully public, known execution window — does not predict the returns it mechanically causes, at least not at daily frequency net of generic reversal. This sets the ceiling the specification warned about: imperfect enumeration cannot pay more than perfect enumeration.

Pre-registration: [`preregistration.md`](preregistration.md), committed before any analysis code was written. Two amendments, both dated and both made before results were seen, are appended to it.

---

## 1. Headline numbers

| Quantity | Value |
|---|---|
| Sample | 2010-03-01 to 2026-08-13 |
| Underlying-days | 16,560 |
| Underlyings | 4 (SPX, NDX, RUT, DJI) |
| Funds enumerated | 16 ProShares leveraged/inverse ETFs |
| **Primary β** (overnight reversal) | **0.004567** |
| Primary t (Newey–West, 5 lags) | **1.58** |
| Primary t (clustered by date) | 1.87 |
| Hurdle (Harvey–Liu–Zhu) | 2.78 |
| Clears hurdle with predicted sign | no |
| Strategy gross mean | 0.381 bps/day |
| Strategy net mean | -3.91 bps/day |
| Strategy gross t | 0.443 |
| Strategy net t | -4.53 |
| Mean round-trip cost | 15.4 bps |
| **Trials in `config_log.jsonl` (Test A)** | **32** |
| Deflated Sharpe Ratio | **4.8e-11** |
| Probabilistic Sharpe (no selection adj.) | 4.897e-06 |
| Selection-bias hurdle SR\* | 0.03264 (per-day) |

## 2. Primary test — H-A2, overnight reversal

Specification as pre-registered (§4.1):

```
r_on[u,t+1] = a[u] + b·imbalance_ratio[u,t] + g·r[u,t] + d·scale[u,t] + e
```

`b` is the coefficient on `scale·r`, so it measures the *additional* overnight reversal attributable to LETF assets being large relative to liquidity, over and above the generic short-horizon reversal that `g` absorbs. Predicted sign: negative.

| | β | SE | t | n |
|---|---|---|---|---|
| Newey–West (5 lags) | 0.004567 | 0.002893 | 1.58 | 16,560 |
| Clustered by date | 0.004567 | 0.002444 | 1.87 | 16,560 |

Control coefficients: generic reversal `g` = -0.05241 (t = -1.78), `d` = 8.99e-06. R² = 0.00456.

### Secondary — next-day intraday return

β = 0.001018, t = 0.403, n = 16,560. No direction was pre-registered for this leg.

### Per-underlying (secondary, no fixed effects)

| Underlying | β | t | n |
|---|---|---|---|
| DJI | 0.009327 | 1.32 | 4,140 |
| NDX | 0.01406 | 1.64 | 4,140 |
| RUT | 0.05966 | 0.99 | 4,140 |
| SPX | 0.1777 | 1.72 | 4,140 |

## 3. Decay curve — the primary deliverable

Per specification §2.5 this is the primary output of Test A regardless of whether the pooled coefficient passes. Full data in [`decay_curve.csv`](decay_curve.csv).

| Year | β | SE | t | n | gross bps | net bps |
|---|---|---|---|---|---|---|
| 2010 | -0.008033 | 0.01377 | -0.583 | 856 | n/a | n/a |
| 2011 | -0.008126 | 0.0143 | -0.568 | 1008 | 13 | -10.6 |
| 2012 | -0.004046 | 0.008984 | -0.45 | 1000 | -6.64 | -22.6 |
| 2013 | 0.006806 | 0.01049 | 0.649 | 1008 | 17 | 3.63 |
| 2014 | 0.00143 | 0.01006 | 0.142 | 1008 | -4.3 | -16.5 |
| 2015 | 0.02417 | 0.01993 | 1.21 | 1008 | -7.44 | -23.3 |
| 2016 | -0.0007287 | 0.007264 | -0.1 | 1008 | 8.91 | -6.77 |
| 2017 | 0.003928 | 0.004209 | 0.933 | 1004 | -1.57 | -12.3 |
| 2018 | 0.009653 | 0.008391 | 1.15 | 1004 | 12.3 | -3.03 |
| 2019 | 0.0001759 | 0.005024 | 0.035 | 1008 | 7.64 | -6.14 |
| 2020 | 0.01368 | 0.007988 | 1.71 | 1012 | 6.72 | -17.2 |
| 2021 | -0.003502 | 0.004024 | -0.87 | 1008 | 6.44 | -4.38 |
| 2022 | 0.003408 | 0.004262 | 0.8 | 1004 | -1.12 | -15.3 |
| 2023 | -0.002382 | 0.003786 | -0.629 | 1000 | 0.674 | -9.93 |
| 2024 | -0.006038 | 0.004368 | -1.38 | 1008 | -9.44 | -17.2 |
| 2025 | -0.0003317 | 0.007491 | -0.0443 | 1000 | -23.7 | -36.4 |
| 2026 | -0.0006898 | 0.007136 | -0.0967 | 616 | 6.36 | 0.247 |

### Exponential decay fit

`β[y] = β₀ · exp(−λ · (y − 2010))`, weighted NLS with weights 1/SE², bootstrap over years (1,000 resamples, seed 0).

- β₀ = 0.001014
- λ = 0.1105, 95% CI ['-0.4865', '1.208']
- Share of bootstrap resamples showing decay (λ > 0): 0.723
- Fitted half-life: 6.27 years, 95% CI [0.51, 64.91]
- Years individually clearing t > 2.78: **0 of 17**

> **The fitted half-life above is not a decay clock and must not be used as one.**
>
> NOT INTERPRETABLE: no individual year clears the t > 2.78 hurdle, so the fitted curve is describing the decay of a quantity that was never distinguishable from zero. Any half-life reported from it is a half-life of noise and must not be used as the framework's decay clock.
>
> The specification hoped Test A would replace the framework's invented "12–36 month" decay figure with a measured number. It does not. What it replaces that guess with is the finding that there is no measured effect here to decay — which is a different and, for the framework, more consequential answer. Substituting 6.3 years for 12–36 months would be swapping one invented number for another with a regression table stapled to it.

## 4. Tradeable strategy

Fade the predicted flow: at the close of day *t*, if `|imbalance_ratio|` exceeds an expanding-window percentile computed through *t−1*, take the opposite side and exit at the next open. $10m notional per position, equal weight across underlyings.

Costs are the full spread round trip (half-spread each side) plus a two-sided square-root impact term `η·σ·√(notional/ADV)` at η = 1.0, plus 0.5bp fees per side. The headline spread is two minimum price increments; see the cost sensitivity below and pre-registration amendment 3 for why that replaced the Corwin–Schultz estimate.

| Trigger | Positions | Gross bps | Gross t | Net bps | Net t | Cost bps | Net Sharpe |
|---|---|---|---|---|---|---|---|
| p50 | 8,617 | 0.607 | 0.586 | -9.35 | -9 | 13.1 | -2.22 |
| p80 | 4,020 | -0.278 | -0.301 | -6.43 | -6.92 | 14.3 | -1.71 |
| p90 **(headline)** | 2,274 | 0.381 | 0.443 | -3.91 | -4.53 | 15.4 | -1.12 |
| p95 | 1,284 | 0.346 | 0.476 | -2.43 | -3.31 | 16.4 | -0.816 |

All four triggers were pre-registered and all four are logged; p90 was designated the headline configuration in the pre-registration, before results were seen.

### Cost sensitivity

The spread assumption changed after the first run — see pre-registration amendment 3, which discloses that this amendment was made *after* seeing results and explains why it cannot rescue the verdict. All three regimes are reported so the reader can pick.

| Spread regime | Mean cost bps | Gross bps | Net bps | Net t | Net Sharpe |
|---|---|---|---|---|---|
| 2 ticks (headline) | 15.4 | 0.381 | -3.91 | -4.53 | -1.12 |
| 1 tick | 15 | 0.381 | -3.79 | -4.38 | -1.08 |
| Corwin–Schultz (upward-biased here) | 47.3 | 0.381 | -12.8 | -13.8 | -3.41 |

Cost is dominated by the impact term, not the spread: at $10m notional the two-tick spread is 0.15–0.4bp and fees are 1bp, so essentially all of the ~15bp is the two-sided square-root impact charge `η·σ·√(notional/ADV)` at the pre-registered η = 1.0. That η was fixed in advance at the conservative end of published calibrations precisely so that a flow-driven edge would not be flattered by an optimistic cost assumption. A less conservative η would shrink the net loss but cannot change the verdict, because the **gross** result is already insignificant (t = 0.443) before any cost is charged at all.

Corwin–Schultz returns 20–38bp for SPY, QQQ, IWM and DIA. Those four instruments quote penny-wide almost continuously, which at their price levels is 0.15–0.4bp. The estimator assumes the daily high is a buy at the ask and the daily low a sell at the bid; for instruments that trade millions of times a session the high/low range is dominated by real price movement rather than bid-ask bounce, so it is upward-biased by roughly two orders of magnitude here. It is retained in `cost_model.py` because it is the right tool for the illiquid names Test C would need. **The verdict is identical under all three regimes**, because the gross result is insignificant before any cost is charged.

## 5. H-A1 — late-day impact (power-limited)

Window 15:30->16:00, period 2023-10-17 to 2026-08-14, n = 2,772 underlying-days.

β = 0.0003668, SE = 0.001459, t = 0.251. Predicted sign positive; observed sign as predicted.

**This test is underpowered and non-gating**, and was registered as such before it was run. Free intraday history reaches back roughly two years; the specification's 2010–present intraday test is not possible without a paid vendor. It is reported so that it cannot be presented as confirmatory after the fact.

## 6. Data, exclusions and known biases

### Sources

| What | Source | Coverage |
|---|---|---|
| LETF daily NAV, shares outstanding, AUM | ProShares published per-fund historical NAV files (`accounts.profunds.com/etfdata/ByFund/`) | Full life of each fund; 2x from 2006, 3x from Feb 2010 |
| Index and ETF daily OHLCV | Yahoo Finance chart API | Complete from 2010 |
| Hourly bars | Yahoo Finance chart API | ~730 calendar days only |

### Data quality check

Each fund's daily NAV return was regressed on its index's return. Every one of the 16 funds recovers its stated leverage to within 0.004 with R² > 0.998 (`data/cache/leverage_check.csv`). The AUM file, the leverage assumptions and the index mapping are mutually consistent — the rebalance multiplier is built on verified inputs, not assumed ones.

### Exclusions (pre-registration §5, fixed in advance)

| Underlying | Before sample start | Too few funds | Missing price/return | Retained |
|---|---|---|---|---|
| SPX | 290 | 0 | 1 | 4,140 |
| NDX | 290 | 0 | 1 | 4,140 |
| RUT | 290 | 0 | 1 | 4,140 |
| DJI | 290 | 0 | 1 | 4,140 |

### Biases, stated in the pre-registration before results were seen

1. **Issuer coverage is incomplete and cannot be fixed from free sources.** Direxion publish no historical shares-outstanding or AUM series — their site returns 403 to automated access and their only machine-readable file is a current-day holdings snapshot. SPXL/SPXS, TNA/TZA and the Direxion sector complex are absent, as are smaller issuers. **`M` is a lower bound on true rebalance demand.** The level of `imbalance_ratio` is understated, so β is not interpretable as a total-flow elasticity. If the ProShares share of the complex is roughly stable through time, the t-statistic and the *shape* of the decay curve are much less affected than the coefficient magnitude. Not corrected.
2. **ADV proxy.** Index futures dominate index-complex volume and free futures volume history is unavailable, so the denominator is the index ETF's dollar volume. This overstates `imbalance_ratio` in level. It is a consistent scaling, not a correction.
3. **Intraday creations and redemptions** move `A` within day *t*; the point-in-time estimate uses `A[t−1]` and cannot capture them. This is the realistic choice — a trader at 15:30 does not know the day's creations either — but it adds noise to `M`.
4. **Survivorship.** All 16 funds were live at the sample start and remain live, and the issuer files give full history from inception. No survivorship filter is applied and none appears to bite.
5. **Daily-frequency fallback.** Per pre-registration §6, the specification's 15:30/16:00 intraday test over 2010–present is not possible on free data. The specification permits the daily fallback explicitly. The overnight leg survives intact; the impact leg does not.

## 7. Multiple-testing accounting

`config_log.jsonl` contains **32 evaluations** in total (32 for Test A), of which 6 are marked reported and 0 failed. 31 distinct configurations.

Every regression variant, every threshold percentile, every yearly subsample and every abandoned run is in that file, including runs that errored. That count — not a hand-asserted number — is what the Deflated Sharpe Ratio below is computed against.

| DSR input | Value |
|---|---|
| Trials N | 32 |
| Observations | 4,140 |
| Sharpe (per-day) | -0.07035 |
| Sharpe (annualised) | -1.12 |
| Skew | -0.371 |
| Kurtosis | 60.7 |
| SR\* (selection hurdle) | 0.03264 |
| Sharpe variance source | analytic 1/(n_obs-1) fallback; <2 logged trial sharpes |
| **Deflated Sharpe Ratio** | **4.8e-11** |

## 8. Verdict and what it implies downstream

**FAIL.** The pooled coefficient does not clear the hurdle (t = 1.58) and no year in the last five is individually significant. The most perfectly enumerable forced flow that exists — closed-form, fully public, known execution window — does not predict the returns it mechanically causes, at least not at daily frequency net of generic reversal. This sets the ceiling the specification warned about: imperfect enumeration cannot pay more than perfect enumeration.

### For Test B

Specification §8 says: *if perfectly-enumerated flow pays nothing today, stop and report — imperfect enumeration cannot pay more.* That stopping rule is triggered on the pooled result. Test B is still worth running, for two reasons: it tests a different mechanism (stale information rather than mechanical flow), and Test A produced no usable decay half-life, so the two-point decay estimate the specification wanted has no first point. Run it as an attempt to *rescue* the thesis, not to confirm it, and with a low prior.

### For Test C

**Do not start Test C on this result alone, and do not start it at all if Test B also returns decay-to-zero.** The specification is explicit: if A and B both return decay-to-zero, the honest conclusion is that enumerated forced-flow edges do not survive publication, and Test C would be measuring a corpse. Test C costs roughly three weeks; the whole point of ordering the tests by cost-per-bit is to avoid spending that on a dead thesis.

