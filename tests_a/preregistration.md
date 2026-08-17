# Test A — Leveraged ETF rebalancing decay: pre-registration

**Status:** committed before any analysis code was written.
**Date:** 2026-08-17
**Spec reference:** Nomad Gate Test Specification §2, §1.1–§1.5

Amendments go at the bottom, dated, with a reason. Nothing above the amendment
line is edited after commit.

---

## 1. Hypothesis

Leveraged and inverse ETFs must rebalance daily to maintain constant leverage.
After an underlying return `r`, a fund with leverage `L` and assets `A` must trade

```
Δ = A · L · (L − 1) · r
```

which is positive in `r` for both positive and negative `L` — leveraged and inverse
funds both buy on up days and sell on down days. This flow is concentrated in the
closing auction. Derivation and sign convention per Cheng & Madhavan (2009),
*The Dynamics of Leveraged and Inverse Exchange-Traded Funds*, Journal of
Investment Management Q4 2009 (SSRN 1539120), confirmed independently by algebra
before writing this document.

This is the most perfectly enumerable forced flow that exists: every input is
public, the formula is closed-form, and the execution window is known.

- **H-A1 (impact).** A larger predicted rebalance imbalance produces late-day
  price movement in the underlying, in the direction of the flow.
- **H-A2 (reversal).** A larger predicted rebalance imbalance produces reversal
  in the following morning's return.

**H-A2 is the primary hypothesis.** See §6 for why.

Null in both cases: the coefficient is zero. Enumerated forced flow, even when
perfectly computable by everyone, is not compensated.

## 2. Constructed quantities

For underlying `u` on trading day `t`:

| Symbol | Definition |
|---|---|
| `A[f,t−1]` | AUM of fund `f` at the close of day `t−1`, from the issuer's published daily NAV file |
| `L[f]` | Stated leverage of fund `f` (±2, ±3) |
| `M[u,t]` | `Σ over f in F(u) of A[f,t−1] · L[f] · (L[f] − 1)` — the rebalance multiplier, in dollars |
| `r[u,t]` | `close[u,t] / close[u,t−1] − 1`, underlying index return |
| `Imbalance[u,t]` | `M[u,t] · r[u,t]` — signed dollar rebalance demand at the close of day `t`; positive is net buying |
| `ADV[u,t]` | Trailing 21-trading-day median dollar volume of the underlying's primary index ETF, computed through `t−1` |
| `scale[u,t]` | `M[u,t] / ADV[u,t]` |
| `imbalance_ratio[u,t]` | `Imbalance[u,t] / ADV[u,t]` = `scale[u,t] · r[u,t]` |
| `r_on[u,t+1]` | `open[u,t+1] / close[u,t] − 1`, overnight return of the proxy ETF |
| `r_id[u,t+1]` | `close[u,t+1] / open[u,t+1] − 1`, next-day intraday return of the proxy ETF |

**Point-in-time property.** `A[f,t−1]` is published on the evening of `t−1`.
`ADV[u,t]` uses volume through `t−1`. `r[u,t]` is observable at the close of `t`.
Every input to `imbalance_ratio[u,t]` is therefore available to a trader standing
at 15:30 on day `t`, which is the decision timestamp the specification requires
(§1.4). No restated, as-of-today, or survivorship-filtered input is used.

## 3. Sample definition

**Underlyings and proxy ETFs (primary set, fixed here, 4 underlyings):**

| Underlying | Index series | Proxy ETF | Funds `F(u)` (leverage) |
|---|---|---|---|
| S&P 500 | `^GSPC` | SPY | SSO (+2), SDS (−2), UPRO (+3), SPXU (−3) |
| Nasdaq-100 | `^NDX` | QQQ | QLD (+2), QID (−2), TQQQ (+3), SQQQ (−3) |
| Russell 2000 | `^RUT` | IWM | UWM (+2), TWM (−2), URTY (+3), SRTY (−3) |
| Dow Jones Industrial Average | `^DJI` | DIA | DDM (+2), DXD (−2), UDOW (+3), SDOW (−3) |

**Issuer coverage.** ProShares only. See §7 for the resulting bias and why it is
not corrected.

**Period.** 2010-03-01 through the latest date available at run time. Start is set
by the inception of the 3x funds on these indices (February 2010) plus 21 trading
days of ADV warm-up. This start date is fixed here and will not be moved to
improve a result.

**Trading-day universe.** A day enters the sample for underlying `u` when the
index close for `t` and `t−1` and the proxy ETF open for `t+1` and close for `t`
are all present.

**Expected sample size.** Roughly 4,150 trading days × 4 underlyings ≈ 16,600
underlying-days, before exclusions.

## 4. Test statistics and pass thresholds

### 4.1 Primary test — H-A2, overnight reversal

Pooled OLS across the four underlyings with underlying fixed effects:

```
r_on[u,t+1] = α[u] + β · imbalance_ratio[u,t] + γ · r[u,t] + δ · scale[u,t] + ε[u,t]
```

Because `imbalance_ratio = scale · r`, including `r` and `scale` as main effects
makes `β` the coefficient on their interaction. `β` therefore measures the
*additional* overnight reversal on days when LETF assets are large relative to
liquidity — separating the LETF rebalancing channel from generic short-horizon
reversal, which `γ` absorbs. This separation is the point of the specification and
is fixed here.

- **Test statistic:** t-statistic on `β`, Newey–West HAC standard errors with 5
  lags. Reported alongside standard errors clustered by date as a robustness
  check; the HAC t-statistic is the one that decides the outcome.
- **Predicted sign:** `β < 0`.
- **Pass threshold:** `t(β) < −2.78` (Harvey–Liu–Zhu hurdle, §1.3). A positive and
  significant `β` is reported but does **not** count as a pass — it would be
  continuation, not the predicted reversal.

### 4.2 Secondary test — next-day intraday

Identical specification with `r_id[u,t+1]` as the dependent variable. No directional
prediction is registered. Reported for completeness; not a pass condition.

### 4.3 Secondary test — H-A1, late-day impact (power-limited)

Free intraday history is limited to roughly 730 calendar days of hourly bars, so
H-A1 as written in the specification (15:30→16:00) cannot be tested over
2010–present. It is registered here on the shortened window that is available:

At 15:00 on day `t`, define `r_partial[u,t] = close_15:00[u,t] / close[u,t−1] − 1`
and `imbalance_ratio_partial[u,t] = M[u,t] · r_partial[u,t] / ADV[u,t]`. Regress
the last-hour return `close_16:00 / close_15:00 − 1` on it, controlling for
`r_partial` and `scale`.

- **Predicted sign:** positive (flow pushes price in the direction of the flow).
- **This test is expected to be underpowered** (~500 underlying-days). It is
  registered so that its result cannot be presented as confirmatory after the
  fact. It is **not** a pass condition and it does not gate anything.

### 4.4 Decay curve — the primary deliverable

Estimate `β` separately for each calendar year 2010…2026 using the §4.1
specification within each year. Emit `decay_curve.csv` with columns
`year, beta, se, t_stat, n_obs, gross_mean_bps, net_mean_bps`.

Fit an exponential decay to the yearly coefficients by weighted nonlinear least
squares with weights `1/se²`:

```
β[y] = β₀ · exp(−λ · (y − 2010))
```

Report the half-life `ln(2)/λ` with a bootstrap confidence interval (1,000
resamples of years, seed fixed at 0). If `λ ≤ 0` or the fit does not converge,
report "no decay detected" rather than a half-life — a negative decay rate will
not be reported as a long half-life.

Per §2.5, the decay curve is the primary output of Test A regardless of whether
the pooled coefficient passes.

### 4.5 Tradeable strategy

At the close of day `t`, if `|imbalance_ratio[u,t]| > θ[u,t]`, take a position in
the proxy ETF of sign `−sign(imbalance_ratio[u,t])` (fade the flow) and exit at
the open of `t+1`. Equal notional per position.

`θ[u,t]` is the `p`-th percentile of `|imbalance_ratio[u,·]|` over an **expanding
window using data through `t−1` only**, for `p ∈ {50, 80, 90, 95}`. All four are
evaluated and all four are logged; `p = 90` is designated here as the headline
configuration so that the choice is not made after seeing results.

- **Assumed trade size:** $10,000,000 notional per position, fixed here.
- **Costs (§1.5):** full spread round trip (half-spread each side) with the spread
  estimated from the proxy ETF's own daily high/low via Corwin–Schultz (2012),
  plus a two-sided square-root impact term `η · σ_daily · sqrt(notional/ADV)`
  with `η = 1.0` and `σ` the trailing 21-day realised volatility, plus 0.5bp fees
  per side.
- **Reported:** gross and net mean return in bps, annualised gross and net Sharpe,
  gross and net t-statistics, and the Deflated Sharpe Ratio of the net series.
- **Pass threshold:** net `t > 2.78` on the headline configuration.

### 4.6 Deflated Sharpe Ratio

Computed on the net daily return series of the headline strategy, with the trial
count `N` taken from `config_log.jsonl` at the time of reporting, per §1.3 and
§5.2. The variance of trial Sharpes is taken from the logged trials where two or
more are available.

## 5. Missing data handling — fixed in advance

1. **Fund AUM missing on `t−1`:** forward-fill up to 5 trading days. Beyond 5,
   the fund is excluded from `M[u,t]` for that day and the number of contributing
   funds is recorded.
2. **Fewer than half the expected funds contributing** to `M[u,t]` (i.e. fewer
   than 2 of 4): the underlying-day is dropped.
3. **Missing index close or proxy ETF open/close:** the underlying-day is dropped.
4. **No imputation of returns, ever.** No interpolation of prices.
5. **Non-positive AUM:** treated as missing and handled by rule 1.
6. Every dropped day is counted and the counts are reported in `results.md`.

## 6. Deviation from the specification, and why

The specification (§2.3) asks for intraday marks at 15:30 and 16:00 from 2010 to
present. **No free source provides this.** Yahoo Finance caps 30-minute history at
roughly 60 days and hourly history at roughly 730 days; Stooq blocks automated
access; every vendor with 15 years of intraday index data is paid. The
specification explicitly permits the fallback: *"Daily-only is a weaker but
acceptable fallback."*

Consequences, stated before results are seen:

- H-A1 over the full period is **not testable here**. What survives is the version
  in §4.3, on ~2 years.
- H-A2 is **fully testable** on daily data, because the overnight return
  `close[t] → open[t+1]` needs only daily OHLC. The reversal leg is where the
  specification's own reasoning locates the tradeable effect, and it is the leg
  that survives intact. That is why it is designated primary rather than
  secondary.
- The proxy ETF, not the index, is used for the return legs. Index opening levels
  are computed from staggered constituent opens and are not tradeable; the ETF
  open is both cleaner and the price a strategy would actually receive.

## 7. Known biases, stated in advance

1. **Issuer coverage is incomplete.** Direxion publishes no historical
   shares-outstanding or AUM series (their site returns 403 to automated access
   and their only machine-readable file is a current-day holdings snapshot).
   SPXL/SPXS, TNA/TZA and the Direxion sector complex are therefore absent from
   `M`. Smaller issuers are absent too. `M` is a **lower bound** on true
   rebalance demand. Effect: the level of `imbalance_ratio` is understated, so
   `β` is not interpretable as a total-flow elasticity. If the ProShares share of
   the complex is roughly stable through time, the t-statistic and the shape of
   the decay curve are much less affected than the coefficient magnitude. This is
   documented, not corrected.
2. **ADV proxy.** Index futures dominate index-complex volume, and free futures
   volume history is unavailable. Using the index ETF's dollar volume overstates
   `imbalance_ratio` in level. It is a consistent scaling, not a correction.
3. **Intraday creations/redemptions** move `A` within day `t`; the point-in-time
   estimate uses `A[t−1]` and cannot capture them. This is the right choice for
   realism — a trader at 15:30 does not know the day's creations either — but it
   adds noise to `M`.
4. **Survivorship.** All 16 funds in the primary set were live at the start of the
   sample and remain live; the issuer file gives full history from inception. No
   survivorship filter is applied and none is believed to bite. Per §1.4, if this
   turns out to be wrong the result is upward-biased and will be labelled so.

## 8. Multiple-testing bookkeeping

Every regression variant, every threshold `p`, every subsample and every
abandoned specification is appended to `config_log.jsonl` per §1.2, including
runs that fail. The trial count used for the Deflated Sharpe Ratio is read from
that file and not asserted by hand.

## 9. What each outcome means for Tests B and C

Per specification §2.5 and §8:

- **`β` significant and stable in recent years** → perfectly enumerated public
  forced flow still pays. Strong support; Tests B and C proceed.
- **`β` significant early and decayed to zero** → record the half-life. That
  number replaces the framework's invented "12–36 month" decay figure. Tests B
  and C proceed, with the decay clock applied.
- **`β` never significant** → check the sign convention against Cheng–Madhavan
  before concluding. If the specification is right and the coefficient is still
  absent, this sets the ceiling: imperfect enumeration cannot pay more than
  perfect enumeration, and the framework is in serious trouble. Report and stop.

---

## Amendments

*(none)*
