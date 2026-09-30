# Convexity map — result (run 2026-09-30, after the pre-registration commit 6299019)

Script: `run.py`. One code bug was fixed after the first run crashed in Part 2 (the block-bootstrap indices could run off the end of the sample); it changed no rule or threshold. The descriptive tail was added after the verdict and is not part of it.

```
dropped: none | stocks 100

PART 1: correlation of c between halves (standardised, all 800 pairs) = +0.037  (bar 0.20)
stable convex legs by variable: {'market': 0, 'rates': 0, 'crude': 0, 'gas': 0, 'dollar': 0, 'vol': 0, 'gold': 0, 'copper': 0}   total 0; permutation null mean 0.0, 95th percentile 0.0
Part 1 FAILS

PART 2: composite of two one-sided legs (chosen on train, judged on test)
variable     test c  c 10th pct  rank vs random pairs  worst day     b_up     b_dn  supported
market       0.0377      0.0029                   95%    -0.0554    0.817    0.742  YES   U=['CSCO', 'PLD', 'TMO', 'ABT'] D=['NEM', 'OXY', 'SO', 'DAL']
rates       -0.0118     -0.0286                   20%    -0.0598   -0.016    0.008  no   U=['WFC', 'EOG', 'UNP', 'BLK'] D=['GOOGL', 'HD', 'MA', 'CRM']
crude        0.0359     -0.0017                   97%    -0.0920    0.349    0.277  no   U=['EOG', 'PSX', 'COP', 'OXY'] D=['DHR', 'BLK', 'FDX', 'NVDA']
gas          0.0032     -0.0065                   94%    -0.0563    0.022    0.016  no   U=['GM', 'USB', 'DE', 'UNP'] D=['V', 'IBM', 'GOOGL', 'SBUX']
dollar      -0.2744     -0.4982                   53%    -0.0513   -0.990   -0.441  no   U=['WFC', 'UPS', 'USB', 'COST'] D=['NEM', 'DE', 'CL', 'DUK']
vol          0.0091      0.0027                   74%    -0.0545   -0.087   -0.106  no   U=['SBUX', 'LOW', 'JPM', 'CL'] D=['GILD', 'AMZN', 'AAPL', 'ADBE']
gold        -0.0111     -0.1047                   41%    -0.0622    0.126    0.148  no   U=['KO', 'FCX', 'PM', 'LIN'] D=['WFC', 'UNP', 'F', 'MS']
copper      -0.0177     -0.0903                   56%    -0.0572    0.106    0.141  no   U=['DE', 'CAT', 'BAC', 'GS'] D=['VZ', 'WMT', 'COST', 'LMT']

variables supported: 1 of 8 (need 3), Part 1 fails
verdict (pre-registered): NOT SUPPORTED IN GENERAL

DESCRIPTIVE (post hoc, not the verdict): pairs with train t(c) >= 3, and their test-half t(c)
  market   train t>=3:  0
  rates    train t>=3:  0
  crude    train t>=3:  0
  gas      train t>=3:  0
  dollar   train t>=3:  0
  vol      train t>=3:  0
  gold     train t>=3:  0
  copper   train t>=3:  0
  total train-convex pairs 0 of 800; under no structure about 1.0 would be expected at t >= 3 (one-sided normal)
```

## Verdict under the pre-registered rule: **not supported in general**
- **Part 1 fails, and not narrowly.** The train and test convexity estimates are essentially uncorrelated (+0.037 against a bar of 0.20), and **no** stock-by-variable pair even reached train t(c) >= 3 (about 1 would be expected by chance out of 800). There was nothing to test for stability.
- **Part 2** supported 1 of 8 variables (the market), against a bar of 3, and per the pre-registration it is read as noise once Part 1 fails. (The composite's slopes there are +0.82 up and +0.74 down: a mild asymmetry in a market-beta basket, not a one-sided pair.)
- Builder's expectation (35% for Part 1, 15% for 3 or more variables): the outcome is below even that.

## What it says
At the daily horizon, no large-cap equity in this set shows a detectable convex, one-sided response to any of these eight state variables, in either half. Composites picked on the first half therefore had nothing to keep.
This is the fourth direct look at the shape (the FOMC pair, the maps of stocks against eight variables, and the three that came before on price windows), and none has found the payoff profile you describe in aggregate equity returns.

## Why this is not the end of the question
- The |x| term detects a kink **at zero**. Real kinks sit where a documented feature bites: a hedge strike, a contract floor, a covenant, a capacity limit. A regression over all days blurs those into noise.
- The mechanism, as you describe it, is built from **documented** one-sidedness (a floor here, a take-or-pay contract there), so it should be visible where the feature is active, not on average.
- So the next measurement is **threshold-aware**: the lower-tail response against the upper-tail response per stock (beyond one and a half standard deviations of x), and then the same stability check, with the narrative naming *which* stocks have a documented floor or cap in advance, to see whether the narrative picks kinks the data cannot.

## Limits
Daily returns; one |x| term; large caps that exist today; a single split; 800 tests at a stringent bar (a low bar might find candidates that are mostly noise).

## Post hoc: what the map could detect (`power.py`, run 2026-09-30, after the verdict)
For a typical stock the smallest up-side/down-side beta gap that reaches t = 3 on the train half: volatility 0.06, gas 0.10, rates 0.12, crude 0.13; for the dollar 1.14, gold 0.55, the market 0.44, copper 0.33 (too little power to say anything).
So the absence of a zero-centred kink in rates, crude, gas and volatility is informative. Linear betas are stable in rank across halves (crude +0.88, rates +0.71, gold +0.75, volatility -0.33) but not in level (OXY 0.29 to 0.64, XOM 0.12 to 0.43, PSX 0.08 to 0.39): the exposure itself moves.
Threshold kinks are untested, and a tail-only estimate needs a gap 3 to 4 times larger. This corrects the wording above: the map's null is mostly a real null for kinks at zero, not noise.
