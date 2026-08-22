# Test A-2 — LETF rebalancing in illiquid underlyings: results

**Verdict: FAIL — TEST A CLOSED**

The top decile does not clear the hurdle (t = 0.647) and there is no monotone gradient across deciles (interaction t = -0.0134, Spearman ρ = -0.0667, permutation p = 0.875). The LETF rebalancing mechanic does not pay in the liquid regime and does not pay in the illiquid regime either. Per the pre-registered stopping condition in §8, **Test A is closed permanently and no third regime will be proposed.**

Pre-registration: [`preregistration.md`](preregistration.md), committed before this analysis was run, including the stopping condition in §8.

> **Why this test exists.** Test A read its null as a ceiling — *if perfectly enumerated flow pays nothing, imperfect enumeration cannot pay more.* That collapses two independent variables. The premium from forced flow comes from **scarcity of the other side**, not from difficulty of enumeration, and Test A's universe was maximally liquid and minimally idiosyncratic — the regime McLean & Pontiff (2016) already identify as where alpha does not survive. This test runs the identical mechanic where counterparty scarcity is high.

---

## 1. Headline

| Quantity | Value |
|---|---|
| Sample | 2020-07-01 to 2026-08-14 |
| Underlying-days | 33,285 |
| Underlyings | 23 (19 thin + 4 index controls) |
| **H1 — top-decile β** | **0.0001753**, t = **0.647** |
| **H2 — gradient interaction** | β_g = -1.118e-05, t = **-0.0134** |
| H2 — Spearman ρ (decile vs β) | -0.0667, permutation p = 0.875 |
| Hurdle | 2.78 |
| Top-decile strategy gross | 0.142 bps/day, t = 0.048 |
| Top-decile strategy net | -76.9 bps/day, t = -25.1 |
| Mean round-trip cost | 76.2 bps |
| Mean participation | 0.905% of ADV |
| **Cumulative trials (all tests)** | **96** |
| Deflated Sharpe (cumulative) | 2.871e-129 |

## 2. The decile curve — primary output

All underlying-days pooled and sorted into ten deciles by `|imbalance_ratio|`. The hypothesis is a **monotone** relationship: near zero in low deciles, rising toward the top. Full data in [`decile_curve.csv`](decile_curve.csv).

| Decile | mean \|imb ratio\| | median M/ADV | β | t | effect of 1sd imbalance (bps) | n |
|---|---|---|---|---|---|---|
| 1 | 0.000674 | 0.261 | 0.3849 | 1.53 | 3.06 | 3329 |
| 2 | 0.00249 | 0.458 | 0.1189 | 1.32 | 3.07 | 3328 |
| 3 | 0.0057 | 1.1 | -0.02839 | -0.767 | -1.65 | 3329 |
| 4 | 0.0113 | 2.01 | -0.05044 | -2.14 | -5.81 | 3328 |
| 5 | 0.0202 | 2.93 | -0.02321 | -1.71 | -4.74 | 3329 |
| 6 | 0.0337 | 3.79 | -0.01201 | -1.24 | -4.09 | 3328 |
| 7 | 0.054 | 4.94 | 0.008576 | 1.44 | 4.66 | 3328 |
| 8 | 0.0854 | 6.35 | -0.002437 | -0.568 | -2.09 | 3329 |
| 9 | 0.147 | 8.29 | -0.002434 | -0.936 | -3.62 | 3328 |
| 10 | 0.798 | 18 | 0.0001753 | 0.647 | 2.3 | 3329 |

> **Read the β column with care — and prefer the column beside it.** β is a slope in units of *return per unit of imbalance_ratio*, and mean |imbalance_ratio| runs from 0.00067 in decile 1 to 0.80 in decile 10, a span of more than a thousand times. β therefore shrinks mechanically as imbalance rises, which is why decile 1 shows the largest raw β in the table and decile 10 the smallest. That is an artefact of units, not an effect running backwards. The **effect of a 1sd imbalance**, β × sd(imbalance) within the decile, is the comparable quantity: it is in return units and it is what the hypothesis is actually about. Added post-hoc — see amendment 1 to the pre-registration — and it does not form part of the pass condition.

Deciles individually clearing |t| > 2.78: **0 of 10**.

### Gradient statistics

Two pre-registered statistics for H2, both reported:

1. **Pooled interaction.** `imbalance_ratio × decile_rank` coefficient β_g = -1.118e-05, t = **-0.0134**, n = 33,285. Significant at the hurdle: **no**. Direction as predicted: **yes**.
2. **Spearman rank correlation** between decile and β: ρ = -0.0667, permutation p = 0.875 (10,000 permutations, seed 0).

## 3. Subsamples

| Sample | β | t | n |
|---|---|---|---|
| Pooled (all underlyings) | -2.929e-05 | -0.128 | 33,285 |
| Thin underlyings only | -3.404e-05 | -0.148 | 27,136 |
| Index controls only (Test A's universe) | 0.00221 | 0.835 | 6,149 |
| Excluding 2020 | -2.43e-05 | -0.103 | 30,671 |

The index-controls row is the closest thing here to a re-run of Test A on a shorter sample. It is included so the thin-underlying result can be read against it directly rather than against a differently-constructed number.

## 4. Where the imbalance actually is

The premise of this test is that thin underlyings carry materially larger forced flow relative to their liquidity. That premise is itself measurable, and is reported here before any return result, because if it fails the test has no power regardless of what the regressions say.

| Underlying | median M/ADV | mean \|imb ratio\| | share of top decile | days |
|---|---|---|---|---|
| SEMI | 82.9 | 1.35 | 38.7% | 1,471 |
| TECH | 14.7 | 0.162 | 13.9% | 1,537 |
| INTERNET | 12.8 | 0.167 | 11.7% | 1,470 |
| HOMEBUILD | 9.93 | 0.137 | 9.52% | 1,425 |
| FIN | 9.59 | 0.0798 | 3.03% | 1,510 |
| NDX *(control)* | 8.78 | 0.0879 | 3.66% | 1,537 |
| DJI *(control)* | 7.98 | 0.0565 | 1.86% | 1,537 |
| BIOTECH | 7.05 | 0.115 | 7.6% | 1,471 |
| CHINA | 5.58 | 0.0815 | 3.06% | 1,471 |
| JRGOLD | 4.7 | 0.0901 | 4.18% | 1,466 |
| REGBANK | 4.48 | 0.0605 | 1.44% | 1,471 |
| RUT *(control)* | 3.35 | 0.0361 | 0.0901% | 1,537 |
| REALESTATE | 2.76 | 0.0275 | 0.0901% | 1,534 |
| OILGAS_EP | 2.73 | 0.047 | 0.631% | 1,430 |
| GOLDMINER | 2.57 | 0.0435 | 0.3% | 1,470 |
| SPX *(control)* | 2.02 | 0.0153 | 0% | 1,538 |
| HEALTH | 1.11 | 0.00723 | 0% | 1,534 |
| RETAIL | 0.867 | 0.0181 | 0.18% | 1,454 |
| ENERGY | 0.767 | 0.0112 | 0% | 1,537 |
| BRAZIL | 0.366 | 0.00525 | 0% | 1,364 |
| UTIL | 0.258 | 0.0022 | 0% | 854 |
| MATERIALS | 0.194 | 0.00187 | 0% | 1,534 |
| INDU | 0.192 | 0.00164 | 0% | 1,133 |

> **`M/ADV` is a multiplier, not flow.** Realised forced flow is `M · r / ADV` —
> the multiplier times the day's return. At a 1% move, a multiplier of 82.9 is
> **0.83 days of ADV**, and A-2's top decile averaged **0.80 days of ADV** of
> realised flow across its whole range of 0.001–0.80. So A-2 established that
> **~0.8 days of ADV produces no measurable effect**, and says nothing about 5x,
> 10x or 20x ADV — the regime fire sales and forced liquidations occupy. Any
> screen inheriting the multiplier as though it were flow sets a magnitude bar
> roughly 100x too high and rejects events A-2 never tested.


## 5. Top-decile strategy, gross and net

Fade the predicted flow in the highest-imbalance decile only: at the close, take the opposite side and exit at the next open.

| | Value |
|---|---|
| Positions | 3,319 over 1,377 days |
| Gross | 0.142 bps/day, t = 0.048, Sharpe 0.0205 |
| Net | -76.9 bps/day, t = -25.1, Sharpe -10.7 |
| Mean round-trip cost | 76.2 bps |
| Mean participation | 0.905% of ADV |
| Median notional | $5.96e+06 |

Trade size is `min($10m, 1% of ADV)`, fixed in the pre-registration. A flat $10m in an instrument with $200m ADV would be a 5% participation rate whose square-root impact charge swamps everything; capping participation is the realistic choice and was set before running.

### Cost estimator assignment

Test A found Corwin–Schultz badly upward-biased for mega-cap ETFs, because its identifying assumption fails for instruments that trade millions of times a session. That failure does not apply to thin instruments — which is what this universe is made of. The pre-registered rule assigns per instrument-day by dollar ADV:

| Underlying | % of days on Corwin–Schultz | median CS spread bps | median tick spread bps |
|---|---|---|---|
| SEMI | 81.8% | 43.9 | 1.22 |
| TECH | 36.3% | 31.5 | 2.36 |
| INTERNET | 100% | 33.9 | 0.981 |
| HOMEBUILD | 100% | 45.9 | 2.5 |
| FIN | 0% | 28.9 | 5.26 |
| NDX | 0% | 28.8 | 0.53 |
| DJI | 17.6% | 22.5 | 0.567 |
| BIOTECH | 78.7% | 59.5 | 2.15 |
| CHINA | 54.7% | 15.2 | 5.95 |
| JRGOLD | 100% | 50.7 | 4.43 |
| REGBANK | 89.8% | 52.2 | 3.33 |
| RUT | 0% | 36.3 | 0.973 |
| REALESTATE | 97.1% | 33.3 | 2.12 |
| OILGAS_EP | 94.7% | 56.4 | 1.53 |
| GOLDMINER | 80% | 45.3 | 5.78 |
| SPX | 0% | 21 | 0.442 |
| HEALTH | 26.8% | 28.1 | 1.49 |
| RETAIL | 100% | 43.8 | 2.66 |
| ENERGY | 6.83% | 41.8 | 4.72 |
| BRAZIL | 88% | 34.3 | 6.5 |
| UTIL | 81.6% | 31.2 | 5.27 |
| MATERIALS | 100% | 29.4 | 4.73 |
| INDU | 26.6% | 29.2 | 1.64 |

## 6. Data and the reconstruction this test depends on

Direxion publish no historical NAV or shares-outstanding feed. That was a footnote in Test A; here it would be fatal, because Direxion's 3x sector funds *are* the high-imbalance regime. AUM was therefore reconstructed from **quarterly SEC N-PORT `netAssets`** by propagating each fund's own return and spreading the residual net flow across the quarter.

**The reconstruction is validated, not asserted.** The identical method is applied to ProShares funds, which publish true daily AUM:

| Fund | median abs error % | p90 abs error % | days |
|---|---|---|---|
| TQQQ | 2.95 | 10 | 1,663 |
| SQQQ | 6.29 | 21 | 1,663 |
| UPRO | 2.36 | 7.95 | 1,663 |
| SPXU | 6.14 | 25 | 1,663 |
| URTY | 4.19 | 18.1 | 1,663 |
| SRTY | 5.44 | 16.2 | 1,663 |
| UYG | 0.318 | 1.81 | 1,663 |
| DIG | 2.46 | 8.01 | 1,663 |
| BIB | 1.64 | 6.26 | 1,663 |
| FXP | 3.4 | 14.1 | 1,663 |

Median across funds: **3.2%**. An error of that size cannot move an observation more than about one decile in a variable whose deciles span orders of magnitude.

### Leverage estimated, not assumed

Several Direxion funds cut leverage from 3x to 2x during 2020 (ERX, ERY, NUGT, DUST, JNUG, JDST, GUSH, DRIP). A fixed leverage table would mis-state `L·(L−1)` for those fund-days — the entire signal. Leverage is instead estimated from a rolling 120-day regression of each fund's return on its underlying's, snapped to the nearest half-integer, with fund-days dropped where R² < 0.90 or the snap is ambiguous. This doubles as the fund-to-underlying mapping check.

| Fund | Underlying | median implied L | snapped | median R² | % days usable |
|---|---|---|---|---|---|
| BIB | BIOTECH | 1.28 | 1.5 | 0.848 | 19.9% |
| LABD | BIOTECH | -2.99 | -3 | 0.997 | 93.4% |
| LABU | BIOTECH | 2.98 | 3 | 0.998 | 93.4% |
| BRZU | BRAZIL | 1.94 | 2 | 0.965 | 81.3% |
| BZQ | BRAZIL | -1.91 | -2 | 0.973 | 92.1% |
| FXP | CHINA | -1.97 | -2 | 0.99 | 93.4% |
| XPP | CHINA | 1.96 | 2 | 0.99 | 93.4% |
| YANG | CHINA | -2.95 | -3 | 0.993 | 93.4% |
| YINN | CHINA | 2.94 | 3 | 0.993 | 93.4% |
| DDM | DJI | 1.99 | 2 | 0.997 | 93.4% |
| DXD | DJI | -1.98 | -2 | 0.994 | 93.4% |
| SDOW | DJI | -2.98 | -3 | 0.996 | 93.4% |
| UDOW | DJI | 2.98 | 3 | 0.997 | 93.4% |
| DIG | ENERGY | 1.98 | 2 | 0.991 | 93.4% |
| DUG | ENERGY | -1.97 | -2 | 0.99 | 93.4% |
| ERX | ENERGY | 1.99 | 2 | 0.991 | 93.4% |
| ERY | ENERGY | -2 | -2 | 0.992 | 93.4% |
| FAS | FIN | 2.94 | 3 | 0.989 | 89.4% |
| FAZ | FIN | -2.96 | -3 | 0.988 | 89.4% |
| SKF | FIN | -1.92 | -2 | 0.969 | 91.5% |
| UYG | FIN | 1.92 | 2 | 0.967 | 82.4% |
| DUST | GOLDMINER | -1.98 | -2 | 0.994 | 93.4% |
| NUGT | GOLDMINER | 1.98 | 2 | 0.996 | 91.5% |
| CURE | HEALTH | 2.97 | 3 | 0.993 | 93.4% |
| RXL | HEALTH | 2 | 2 | 0.98 | 93.4% |
| NAIL | HOMEBUILD | 2.98 | 3 | 0.998 | 86.8% |
| DUSL | INDU | 3 | 3 | 0.992 | 89.9% |
| UXI | INDU | 1.99 | 2 | 0.971 | 84.5% |
| WEBL | INTERNET | 2.96 | 3 | 0.998 | 93% |
| WEBS | INTERNET | -3.01 | -3 | 0.996 | 87.9% |
| JDST | JRGOLD | -1.96 | -2 | 0.995 | 93.1% |
| JNUG | JRGOLD | 1.94 | 2 | 0.995 | 86.9% |
| UYM | MATERIALS | 2.02 | 2 | 0.976 | 93.4% |
| QID | NDX | -2 | -2 | 0.997 | 93.4% |
| QLD | NDX | 2 | 2 | 0.999 | 93.4% |
| SQQQ | NDX | -2.98 | -3 | 0.997 | 93.4% |
| TQQQ | NDX | 2.97 | 3 | 0.999 | 93.4% |
| DRIP | OILGAS_EP | -2.02 | -2 | 0.995 | 86.8% |
| GUSH | OILGAS_EP | 2.01 | 2 | 0.997 | 86.8% |
| DRN | REALESTATE | 3 | 3 | 0.978 | 93.2% |
| DRV | REALESTATE | -3.01 | -3 | 0.982 | 93.4% |
| SRS | REALESTATE | -1.98 | -2 | 0.983 | 93.4% |
| URE | REALESTATE | 1.97 | 2 | 0.983 | 93.4% |
| DPST | REGBANK | 2.98 | 3 | 0.996 | 93.4% |
| RETL | RETAIL | 2.95 | 3 | 0.995 | 93.4% |
| SRTY | RUT | -2.98 | -3 | 0.997 | 93.4% |
| TNA | RUT | 2.98 | 3 | 0.998 | 93.4% |
| TWM | RUT | -1.99 | -2 | 0.996 | 93.4% |
| TZA | RUT | -2.99 | -3 | 0.997 | 93.4% |
| URTY | RUT | 2.98 | 3 | 0.998 | 93.4% |
| UWM | RUT | 1.99 | 2 | 0.998 | 93.4% |
| SOXL | SEMI | 2.97 | 3 | 0.998 | 93.4% |
| SOXS | SEMI | -3 | -3 | 0.998 | 90.3% |
| USD | SEMI | 2.01 | 2 | 0.959 | 53.3% |
| SDS | SPX | -1.98 | -2 | 0.993 | 93.4% |
| SPXL | SPX | 2.96 | 3 | 0.997 | 93.4% |
| SPXS | SPX | -2.97 | -3 | 0.995 | 93.4% |
| SPXU | SPX | -2.96 | -3 | 0.993 | 93.4% |
| SSO | SPX | 1.98 | 2 | 0.997 | 93.4% |
| UPRO | SPX | 2.97 | 3 | 0.997 | 93.4% |
| ROM | TECH | 2.02 | 2 | 0.981 | 93.4% |
| TECL | TECH | 2.98 | 3 | 0.999 | 93.4% |
| TECS | TECH | -2.99 | -3 | 0.997 | 93.4% |
| UPW | UTIL | 1.96 | 2 | 0.979 | 93.4% |
| UTSL | UTIL | 2.99 | 3 | 0.988 | 93.4% |

## 7. Limitations, stated in the pre-registration before running

1. **Direxion AUM is quarterly-anchored and reconstructed**, not observed — error quantified above.
2. **Short sample.** 2020-07 onward, set by N-PORT availability. Test A had sixteen years; this has about six, so each decile holds fewer observations.
3. **Issuer coverage is still incomplete.** GraniteShares, Tuttle/T-Rex, Defiance and other single-stock leveraged issuers are absent, so `M` remains a lower bound — though the two issuers covered hold the overwhelming majority of sector LETF assets.
4. **Proxy ETFs are not the funds' exact indices.** The rolling leverage check with an R² floor is what keeps those mappings honest.
5. **COVID is in-sample at the start**; the excluding-2020 row is in §3.

## 8. Verdict

**FAIL — TEST A CLOSED.** The top decile does not clear the hurdle (t = 0.647) and there is no monotone gradient across deciles (interaction t = -0.0134, Spearman ρ = -0.0667, permutation p = 0.875). The LETF rebalancing mechanic does not pay in the liquid regime and does not pay in the illiquid regime either. Per the pre-registered stopping condition in §8, **Test A is closed permanently and no third regime will be proposed.**

### The stopping condition has fired

Pre-registration §8, recorded before this test was run:

> *If the top-decile coefficient is not significant at t > 2.78 AND there is no monotone gradient across deciles, the LETF mechanic is dead in both regimes and Test A is closed permanently. No third regime will be proposed.*

Both conditions are met. Test A is closed. The value of having written that sentence down in advance is precisely that it removes the option of proposing a fourth universe now.

Cumulative evaluations logged across all tests: **96** (A: 32, A2: 19, B: 45). The Deflated Sharpe above is computed against that cumulative count, per Amendment 1 §4.
