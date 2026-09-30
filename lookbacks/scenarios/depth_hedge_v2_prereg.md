# Depth-hedge test v2 — equity baskets (pre-registration, written before any number was computed)

*2026-09-30. Supersedes `depth_hedge_prereg.md` (ETF legs), on Rob's instruction: no funds, baskets of individual equities; derivatives
later. The ETF version's result stays on file, labelled superseded. Same claim (Rob): two long legs on the same underlying scenario can
hedge each other by sitting further down the chain, on less correlated nodes, and covering the downside. Public price history; the v15
record is not used; nothing waits on this. Illustrative at this sample size.*

## Scenario and events
"Oil shock persists"; long; the downside is the fade. **Events, a mechanical rule:** trading days 2019-01-02 to 2025-12-30 on which the
front-month crude futures series (CL=F, not a fund) closes up **4.0% or more**, excluding 2020-03-01 to 2020-07-31, declustered (keep the first,
skip the next 10 trading days). A futures roll can put a spurious jump in a continuous series; that risk is noted and not filtered.

## Baskets of equities, assigned by the causal chain from the crude price, fixed now (equal weight, buy-and-hold)
- **T1a, producers A:** COP, EOG, OXY, DVN. **T1b, producers B (the baseline second basket):** XOM, CVX, APA, FANG.
- **T2, one hop on (revenue follows producers' activity):** SLB, HAL, BKR, KMI.
- **T3, two hops on (suppliers to the services chain, and the regional economy):** TS, GATX, KEX, CFR.
- **Control, an unrelated defensive basket:** JNJ, PG, KO, PEP.
- **Exploratory only, not in the verdict (a different channel to the same scenario):** tankers (STNG, DHT, INSW, TNK); defence (LMT, NOC, GD, HII).
A symbol without price history over the whole window is dropped, and the drop is reported.

## Windows (trading days; t0 = event day)
R, the reaction: close(t0-1) to close(t0+2). F, the fade: close(t0+2) to close(t0+20).

## Pairs (50/50 of two baskets, same events)
T1a+T1b (the baseline), T1a+T2, T1a+T3, T1a+control; exploratory T1a+tankers, T1a+defence.

## Statistics
Per pair: mean R, mean F, worst F, **CVaR25(F)** (mean F of the worst quarter of events), and the cross-event correlation of F between T1a and the second basket.
Per second basket: its **own** mean R (the retention measure). Bootstrap over events (5,000) for the difference in pair CVaR25(F) against the baseline.

## Decision rule (builder's thresholds, provisional; amending after the result voids the test)
A tier (T2, T3) is **supported** if all three hold:
1. **Downside:** its pair's CVaR25(F) loss is at least **20%** smaller than the baseline pair's, and the bootstrap probability of an improvement is at least **0.80**.
2. **The thesis is kept:** the tier basket's own mean R is positive and at least **50%** of T1b's own mean R.
3. **Not just diversification:** the control basket's own mean R, as a share of T1b's, is smaller than the tier's.
**Not supported** if (1) fails; **diluted** if (1) holds and (2) fails.

## Expectation (builder's, before running)
About 60% that T3 is diluted or unsupported: TS, GATX, KEX and CFR respond weakly to a 4-day oil spike, so (2) or (1) fails. T2 keeps its response but correlates
highly with the producers, so (1) fails. Tankers (exploratory) are the ones I would watch: a separate channel, and a strong reaction in some events. Rob's expectation: to be added here
before the run if he gives one.

## Limits
About 30 events; equal weights; the tier assignment is a causal-chain judgement; raw returns include the market's direction, which only the control partly handles; survivorship is
limited by choosing names that traded throughout; the builder knows the broad history, so the rule and the names are fixed above before any computation.

## Addendum, written after the 2019 to 2025 run and before any 2026 number (2026-09-30)
The 2019 to 2025 run was executed (result file `depth_hedge_v2_result.md`). A **holdout** on the same rule, baskets, windows and thresholds, unchanged, over
**2026-01-02 to 2026-09-29** (events need 20 trading days after them, so the last few weeks drop out): it is read only if it has **at least 8 events**; below that it is reported as
too few and carries no verdict. The 2026 prices are ones the builder has not seen. The script takes the window from the environment variable `DH_WINDOW`.
