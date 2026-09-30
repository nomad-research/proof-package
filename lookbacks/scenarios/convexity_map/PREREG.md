# Convexity map — pre-registration (written before any number was computed)

*2026-09-30. Rob: combining two long narratives that are each one-sided over a long or short base gives a downside-capped, upside-uncapped composite. A domain-free test, no scenario chosen: across many stocks and many state variables,
do equities show one-sided (kinked) responses that are stable out of sample, and does a composite of two one-sided legs, chosen on the first half only, keep its convex shape in the second half? Equities only as legs; the state variables are
indices and futures used only as x. Public prices. Nothing waits on it.*

## Data (fixed now)
Daily closes 2016-01-04 to 2025-12-31. **Train 2016 to 2020, test 2021 to 2025.**
**Stocks (100):** AAPL MSFT AMZN GOOGL META NVDA TSLA BRK-B JPM V UNH XOM JNJ WMT MA PG HD CVX LLY ABBV MRK KO PEP AVGO COST MCD BAC TMO CSCO ACN ABT CRM ADBE DHR NKE DIS WFC TXN NEE VZ PM LIN UPS CMCSA AMD ORCL INTC RTX HON QCOM UNP LOW T AMGN IBM SPGI CAT GS BA DE BLK MS SBUX MDT GILD ADP LMT AXP CVS ISRG MDLZ TJX PLD C SYK DUK SO MO USB BKNG ZTS CB CI CL FDX EOG SLB COP OXY MPC PSX VLO KMI WMB F GM DAL UAL FCX NEM. A name without history over the whole window is dropped and reported.
**State variables x (8):** the market (^GSPC return), the 5-year yield (^FVX, daily change in percentage points), crude (CL=F return), natural gas (NG=F return), the dollar (DX-Y.NYB return), volatility (^VIX, log change), gold (GC=F return), copper (HG=F return).

## The measure
For stock i and variable x, on daily returns, controlling for the market (its return and its absolute value; no control when x is the market): y = a + b x + c |x| + g m + d |m| + e. **c > 0 is convexity** (a slope that is steeper on the up side than on the down side), **c < 0 concavity**.
The kinked form for the composite: y = a + b_up x+ + b_dn x- + controls, with x+ = max(x, 0) and x- = min(x, 0). t-statistics use heteroskedasticity-robust (HC1) standard errors.

## Part 1: is one-sidedness stable across time?
- The correlation, across all stock-by-variable pairs, of c estimated in the train half against c in the test half. **A stable structure needs this at least 0.20.**
- A pair is a **stable convex leg** if train t(c) >= 3.0 and test t(c) >= 1.65. Its count is compared with a **permutation null**: 200 times, permute x in time within each half (breaking any relation, keeping its distribution), recompute the count.
  **Stable structure is present if the observed count exceeds the 95th percentile of the null.**

## Part 2: the composite of two one-sided narratives (the mechanism, built on the train half only)
Per variable v, on the train half: score each stock U = t(b_up) - |t(b_dn)| (pays when x rises, flat when it falls) and D = -t(b_dn) - |t(b_up)| (pays when x falls, flat when it rises); take the top 4 by each score (disjoint), equal weight, 0.5 U + 0.5 D. Then in the **test half**: the composite's c with a bootstrap (20-day blocks, 2,000 resamples), its worst day, and its rank of c among **500 random pairs** of 4-name baskets from the same universe.
**Supported for v** if the test-half c > 0, its bootstrap 10th percentile > 0, and its rank is at or above the 95th percentile of the random pairs.
**The shape claim is supported in general** only if Part 1 holds **and** at least **3 of the 8** variables are supported in Part 2. If Part 1 fails, Part 2 is read as noise.

## Expectation (builder's, before running)
About 35% that Part 1 holds (most kinks in daily equity returns are estimation noise; the known real ones are in names with leverage or optionality against volatility and rates), and about 15% that Part 2 supports 3 or more variables. If a few variables do (volatility and rates are my guess), that is where the mechanism lives.
Rob's expectation: to be added here before the run if he gives one.

## Limits
Daily returns and a single |x| term; ten years, two halves; a linear market control; 800 tests and a stringent stability rule to limit false positives; equal weights; no transaction costs; survivorship (names that exist today); legs are not restricted to the extremes of x.
