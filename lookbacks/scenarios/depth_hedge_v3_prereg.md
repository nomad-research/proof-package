# Depth-hedge test v3 — far enough down the chain that a long is a synthetic short (pre-registration, before any number)

*2026-09-30. Rob's claim: go so far down the chain that a long thesis is actually a synthetic short, through low enough correlation over the downstream effects.
This tests whether a **long basket** of equities at depth, reached only by following the chain and not by choosing an opposite-side holder, behaves as a short of the
primary scenario, and whether pairing it with the producers lowers the worst case. Equities only, no funds, no derivatives. Public price history; nothing waits on it.
Continues `depth_hedge_v2_*`, same events, windows, primary basket and method.*

## Chain (crude price up is the scenario; the sign of a deeper node comes from composing the hops, not from an assumption about it)
Crude up, then: (1) refined-fuel cost up, (2) margins of fuel-intensive users down, (3) real income and inflation pressure up, rates up, (4) rate- and income-sensitive demand down.

- **T4, fuel-intensive users (hops 1 to 2 on the cost side):** DAL, UAL, LUV, CCL.
- **T5, rate- and real-income-sensitive demand (hops 3 to 4):** DHI, LEN, HD, TGT.
- Carried from v2: **T1a** (COP, EOG, OXY, DVN) is the primary; **T1b** (XOM, CVX, APA, FANG) and **T3** (TS, GATX, KEX, CFR) for reference; **control** (JNJ, PG, KO, PEP).
Equal weight, buy-and-hold; a symbol without history over the whole window is dropped and reported.

## Events and windows: exactly as v2
CL=F up 4.0% or more, 2020-03-01 to 2020-07-31 excluded, declustered 10 trading days. R = close(t0-1) to close(t0+2); F = close(t0+2) to close(t0+20).
Windows: **main 2019-01-02 to 2025-12-30**, and **holdout 2026-01-02 to 2026-09-29**, read only if it has at least 8 events. **Disclosure:** the 2026 event dates and the T1a, T3 and control
returns in that holdout were seen in the v2 run, so this holdout is only partly unseen; the T4 and T5 baskets have not been computed on any window.

## A tier is a **synthetic short of the scenario** if all of these hold, in the main window and again in the holdout
1. **Reliably negative reaction:** its own mean R is negative with a t-statistic of **-2 or lower** (mean divided by its standard error over events).
2. **Moves against the primary in the fade:** the correlation of its F with T1a's F is **-0.30 or lower**.
3. **Pays when the thesis's downside happens:** in the worst quarter of events for T1a's F, the tier's mean F is **positive**.
4. **The pair helps:** a 50/50 T1a+tier pair's CVaR25(F) loss is at least **20%** smaller than the T1a+T1b pair's, with a bootstrap probability of improvement of at least **0.80**.
Reported alongside, not in the verdict: the share of T1a's mean R that a 50/50 pair gives up (the cost of the hedge), and the same statistics for T3 and the control.

## Expectation (builder's, before running)
About 70% that **T4 is a synthetic short in the main window** (airlines and cruise fall on oil spikes, so (1) to (3) likely hold) and about 55% that it also replicates in the holdout.
T5 I expect to fail (1): the rate and income channel is real but slow, and on a 4-day window its response is weak and noisy (t around -1). The cost of the T4 hedge, by construction, is a
large share of the upside. Rob's expectation: to be added here before the run if he gives one.

## Limits
About 35 and 9 events; equal weights, no optimiser; the chain assignments are judgements; cruise and airlines carry heavy market beta, so a negative R may be part risk-off; a partly seen holdout;
the pair CVaR of a synthetic short is mostly the tier's own volatility, which is why (1) to (3) are required and not (4) alone.
