# Depth-hedge test (ETF legs) — pre-registration — SUPERSEDED by depth_hedge_v2_prereg.md (Rob: no funds)

*2026-09-30. Rob's claim: two long legs on the same underlying scenario can hedge each other, not by opposite sign but because the second
leg sits further down the chain, on a node less correlated with the first, so it covers the downside; "divergent on its own effect and
effect degrees". This tests it on real prices. It is a look-back on public history. It does not use the v15 record and nothing waits on it.
It is illustrative at this sample size, not a verdict on the programme.*

## The scenario
"Oil shock persists". The thesis is long; its downside is the fade after the shock.

## Events (a mechanical rule, fixed now, no hindsight in the choice)
Trading days 2019-01-02 to 2025-12-30 on which **USO** (an ETF: no futures-roll artefacts) closes up **4.0% or more**, excluding
2020-03-01 to 2020-07-31 (the negative-price dislocation), then **declustered**: keep the first such day and skip the next 10 trading
days. The count is whatever the rule gives. No threshold is tuned after seeing the count.

## Legs, assigned to a depth by the causal chain from the crude price, fixed now
- **Tier 1** (revenue tied to the crude price): XOP (exploration and production), XLE (energy sector).
- **Tier 2** (one hop on: revenue responds to producers' activity): OIH (oilfield services), AMLP (midstream).
- **Tier 3** (further out: national or economy-wide link to oil income): EWC (Canada), NORW (Norway).
- **Control** (a generic diversifier with no oil link): SPY.
All long, equal weight within a pair, buy-and-hold over the window. Tickers are the ones that exist through the whole period.

## Windows (trading days; t0 is the event day)
- **R, the reaction:** close(t0 - 1) to close(t0 + 2).
- **F, the fade, the downside of the thesis:** close(t0 + 2) to close(t0 + 20).

## Baskets compared (each a 50/50 pair, all on the same events)
T1+T1 (XOP, XLE); T1+T2 (XOP with OIH, XOP with AMLP); T1+T3 (XOP with EWC, XOP with NORW); T1+control (XOP with SPY). A tier's result is the mean over
its pairs.

## Statistics
Per basket over events: mean R, mean F, worst F, and **CVaR25(F)**, the mean F of the worst quarter of events. The cross-event correlation of F between
XOP and the second leg. A bootstrap over events (5,000 resamples) for the difference in CVaR25(F) between a deeper pair and T1+T1.

## Decision rule (thresholds set by the builder, provisional; amending them after the result is seen voids the test)
The depth hedge is **supported for a tier** if all three hold:
1. **Downside:** the tier's CVaR25(F) loss is smaller than T1+T1's by at least **20%** (relative), and the bootstrap probability that it is smaller
   is at least **0.80**.
2. **The thesis is kept:** the tier's mean R is positive and at least **50%** of T1+T1's mean R. A leg that diversifies by not responding is not a hedge of this thesis.
3. **It is not just diversification:** the control pair (XOP+SPY) keeps a smaller share of R than the tier does. If SPY does as well, depth adds nothing an unrelated asset would not.
It is **not supported** for a tier if (1) fails, and **diluted** if (1) holds and (2) fails.

## Expectation (the builder's, before running)
About 65% that Tier 3 comes back **diluted** (a broad Canada index and Norway respond weakly to a one-day oil spike, so (2) fails), and Tier 2 mixed:
they keep R but move with XOP, so (1) is marginal. I expect no tier to satisfy all three. Rob's expectation: to be written here before the run if he gives one.

## Limits
About 30 events from one asset class; equal weights and buy-and-hold, no optimisation; the tier assignment is a causal-chain judgement;
raw returns include the market's direction, which the SPY control only partly handles. The events are past and the builder knows the
broad history, which is why the rule and the legs are fixed above before any computation.
