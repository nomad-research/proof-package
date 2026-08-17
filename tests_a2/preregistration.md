# Test A-2 — LETF rebalancing in illiquid underlyings: pre-registration

**Status:** committed before any A-2 analysis code was run.
**Date:** 2026-08-17
**Spec reference:** Gate Spec Amendment 1 §1; original spec §1.1–§1.5

Amendments go at the bottom, dated, with a reason. Nothing above the amendment
line is edited after commit.

---

## 1. Why this test exists

Test A returned a null and the original specification read that null as a
ceiling: *"if perfectly enumerated flow pays nothing today, imperfect enumeration
cannot pay more."*

That inference collapses two independent variables. The premium from forced flow
comes from **scarcity of the other side**, not from difficulty of enumeration.
Test A's universe — SPX, NDX, Russell 2000 and the Dow — is maximally liquid,
minimally idiosyncratic, and watched by everyone in the most-observed window of
the trading day. Enumeration there is perfect and counterparty scarcity is
approximately zero. A null in that corner bounds nothing about the corner where
counterparty scarcity is high.

McLean & Pontiff (2016) found surviving alpha concentrates in high idiosyncratic
risk and low liquidity, with idiosyncratic risk the only significant driver of
post-publication decline. Test A tested the case that literature already says is
dead. This test runs the identical mechanic where the theory makes a claim.

This is a refinement, not goalpost-moving: the high-idiosyncratic-risk,
low-liquidity prediction predates the original specification. It is the
pre-registered implication the original specification failed to honour.

## 2. Hypothesis

The rebalance-impact and overnight-reversal effects are **increasing in
`imbalance_ratio`** — predicted rebalance notional divided by underlying dollar
ADV. They are absent in the mega-cap index LETFs already tested because
`imbalance_ratio` there is negligible, and should appear where it is material.

- **H1 (level).** In the top decile of `|imbalance_ratio|`, the overnight
  reversal coefficient `β` is negative and clears the hurdle.
- **H2 (gradient).** `β` is monotone in decile: near zero in low deciles, rising
  in magnitude toward the top.

**H2 is the more important claim.** A significant top decile with no gradient
across deciles is weak evidence and will be reported as such — it is what data
mining looks like.

## 3. Universe

Fixed in `tests_a2/universe.py`. Nineteen thin underlyings (semiconductors,
biotech, financials, technology, energy, real estate, utilities, health care,
industrials, materials, China, Brazil, regional banks, home construction, retail,
gold miners, junior gold miners, oil & gas E&P, internet) plus the four mega-cap
index underlyings from Test A **retained as controls** — the decile test needs the
low-imbalance end of the cross-section to establish a gradient.

Both leveraged and inverse funds are included. `L·(L−1)` gives 6 for L = +3 and
**12 for L = −3**, so inverse funds contribute disproportionately.

**AUM floor: $25,000,000.** Funds below it are dropped on the days they are below
it. Tiny funds produce noise, not signal. Floor fixed here, not in code review.

## 4. Data, and the one reconstruction this test depends on

| Source | Coverage |
|---|---|
| ProShares published daily NAV / shares outstanding / AUM | Exact, daily, full fund life |
| Direxion via SEC N-PORT `netAssets` | **Quarterly**, from 2019-12 |
| Proxy ETF daily OHLCV (Yahoo) | Daily |

Direxion publish no historical NAV or shares-outstanding feed. That was a
documented gap in Test A; here it is not survivable, because Direxion's 3x sector
funds *are* the high-imbalance regime. SOXL alone carries a rebalance multiplier
of roughly **$145bn** against semiconductor-ETF ADV of order $1bn — an order of
magnitude more extreme than anything in the original index universe. Omitting it
would mean omitting the single most important observation in the test.

**Reconstruction.** Quarterly N-PORT anchors are interpolated to daily by
propagating the fund's own return and spreading the residual net flow evenly
across the quarter. **Validated by applying the identical method to ProShares
funds, where true daily AUM is published: median absolute error 2.7%, p90 10%.**
That validation is rerun and reported in `results.md` rather than asserted here.
An error of that size cannot move an observation more than about one decile in a
variable whose deciles span orders of magnitude.

**Sample period: 2020-07-01 onward**, fixed here. Two N-PORT anchors are needed
before any Direxion fund can be reconstructed, and the period is held common
across all underlyings so that coverage does not jump mid-sample.

## 5. Leverage is estimated, not assumed

Several Direxion funds changed stated leverage mid-life — the 3x-to-2x reductions
of 2020 hit ERX, ERY, NUGT, DUST, JNUG, JDST, GUSH and DRIP. A fixed leverage
table would silently mis-state `L·(L−1)` for those fund-days, and `L·(L−1)` is
the entire signal.

Each fund's leverage is therefore estimated from a rolling 120-day regression of
its daily return on its underlying proxy's, then snapped to the nearest
half-integer. Fund-days are **dropped** where R² < 0.90 or where
|implied − snapped| > 0.35. This handles the leverage changes automatically and
doubles as the mapping check: a fund whose returns do not track its assigned
underlying is removed rather than trusted.

## 6. Constructed quantities

Identical in form to Test A, with `L` now time-varying and estimated:

| Symbol | Definition |
|---|---|
| `M[u,t]` | `Σ over funds f on u of A[f,t−1] · L[f,t] · (L[f,t] − 1)` |
| `r[u,t]` | Proxy ETF close-to-close return on day `t` |
| `ADV[u,t]` | Trailing 21-day median dollar volume of the proxy ETF, through `t−1` |
| `imbalance_ratio[u,t]` | `M[u,t] · r[u,t] / ADV[u,t]` |
| `scale[u,t]` | `M[u,t] / ADV[u,t]` |
| `r_on[u,t+1]` | Overnight return, proxy ETF close `t` to open `t+1` |

All inputs are known by 15:30 on day `t`. `A[f,t−1]` is the prior close.

## 7. Test statistics and pass thresholds

### 7.1 Decile construction

All underlying-days are pooled and sorted into **10 deciles by
`|imbalance_ratio|`**. Deciles are formed on the pooled sample, not within
underlying, because the hypothesis is about the level of the ratio and not about
each underlying's own distribution.

### 7.2 Within-decile regression

Within each decile, the Test A specification:

```
r_on[u,t+1] = a[u] + β·imbalance_ratio[u,t] + γ·r[u,t] + δ·scale[u,t] + e
```

Newey–West HAC, 5 lags. `β` and its t are reported **per decile**; that table is
the primary output.

### 7.3 H1 — top decile

- **Statistic:** t on `β` in decile 10.
- **Predicted sign:** negative.
- **Pass:** t < −2.78.

### 7.4 H2 — gradient (the more important claim)

Two statistics, both pre-registered, both reported:

1. **Pooled interaction.** Regress with a decile-rank interaction across the full
   pooled sample:
   ```
   r_on = a[u] + β·imb + β_g·(imb · decile_rank) + γ·r + δ·scale + e
   ```
   Gradient statistic: t on `β_g`. **Pass: |t| > 2.78** with `β_g` pushing `β`
   more negative as rank rises.
2. **Spearman rank correlation** between decile number and the per-decile `β`,
   with a permutation p-value (10,000 permutations, seed 0). Reported alongside;
   not a pass condition on its own, because 10 points is thin.

### 7.5 Overall pass condition

**Pass requires H1 and H2 together.** Top decile significant *and* a gradient.
Top decile alone is reported as weak and explicitly labelled as consistent with
data mining.

### 7.6 Costs — which estimator, and why

Test A found Corwin–Schultz badly upward-biased for mega-cap ETFs, because its
identifying assumption (daily high is a buy at the ask, daily low a sell at the
bid) fails for instruments that trade millions of times a session. That failure
does **not** apply to thin instruments, which is exactly what this universe is
made of.

Pre-registered rule, per instrument per day:

- **Dollar ADV > $1bn → tick-based spread** (2 ticks). These quote penny-wide
  more or less continuously.
- **Dollar ADV ≤ $1bn → Corwin–Schultz**, which is the estimator built for the
  case where the spread is genuinely wide and unobserved.

Both estimators are computed for every instrument and the full sensitivity is
reported. The instrument-by-instrument assignment is printed in `results.md`.

**Trade sizing.** `notional = min($10,000,000, 1% of ADV)`. A fixed $10m in an
instrument with $200m ADV is a 5% participation rate and its square-root impact
charge would swamp everything; capping participation at 1% is the realistic
choice and is fixed here. Realised participation statistics are reported.

Impact term unchanged: `η · σ · √(notional/ADV)` at η = 1.0, two-sided, plus
0.5bp fees per side. **A gross-only result in this universe is meaningless** and
will not be presented as a result.

### 7.7 Multiple testing

Every decile regression, every sensitivity and every abandoned variant is
appended to `config_log.jsonl`. The Deflated Sharpe Ratio is computed against the
**cumulative** trial count across all tests to date — the 77 already logged plus
everything added here — not against this amendment's trials alone.

## 8. Stopping condition — pre-registered

**If the top-decile coefficient does not clear t > 2.78 AND there is no monotone
gradient across deciles, the LETF mechanic is dead in both regimes and Test A is
closed permanently. No third regime will be proposed.**

This is recorded here, before running, precisely so that a null cannot be
followed by another universe redefinition.

## 9. Known limitations, stated in advance

1. **Direxion AUM is quarterly-anchored and reconstructed**, not observed. Error
   quantified at ~2.7% median against ProShares truth, and reported.
2. **Sample is short** — 2020-07 onward, roughly six years, set by N-PORT
   availability. Test A had sixteen. Fewer observations per decile.
3. **Issuer coverage is still incomplete.** GraniteShares, Tuttle/T-Rex, Defiance
   and other single-stock and thematic leveraged issuers are absent. `M` remains
   a lower bound, though the two issuers covered are the overwhelming majority of
   sector LETF assets.
4. **The proxy ETF is not the fund's exact index.** SOXL tracks the NYSE
   Semiconductor Index while SOXX tracks ICE Semiconductor; XLF is not precisely
   the Russell 1000 Financial Services index. The rolling leverage check with an
   R² floor of 0.90 is what keeps these mappings honest — a fund whose returns do
   not track the assigned proxy is dropped rather than mis-measured.
5. **The 2020 sample start means COVID is in-sample at the start.** Reported, and
   a robustness excluding 2020 is run and logged.

---

## Amendments

*(none)*
