# Refiners against producers — pre-registration (written before any number was computed)

*2026-09-30. The candidate from the synthetic-leg result: a hedge that differs in kind on the fade, by sitting on a different channel. Refiners are long the crack spread, which tends to widen when crude retraces. Equities only,
no funds, no derivatives. Public prices; nothing waits on it. Continues the depth tests: same events, windows, producer basket and baseline.*

## Baskets (equal weight, buy-and-hold, fixed now)
T1a producers (COP, EOG, OXY, DVN) as the primary; T1b (XOM, CVX, APA, FANG) as the baseline second basket; **REF** refiners (VLO, MPC, PSX, PBF). A name without history over the whole window is dropped and reported.

## Events and windows: exactly as before
CL=F up 4.0% or more in a day, 2020-03-01 to 2020-07-31 excluded, declustered 10 trading days; main 2019-01-02 to 2025-12-30 and holdout 2026-01-02 to 2026-09-29 (read only with at least 8 events).
R = close(t0-1) to close(t0+2); F = close(t0+2) to close(t0+20). Channel series (futures): the crack is the 3-2-1 proxy, (2 x RB=F x 42 + HO=F x 42) / 3 minus CL=F. A roll can put a jump in a continuous series; noted, not filtered.
**Disclosure:** the event dates and the producer baskets' returns were seen in earlier runs; the refiner basket's have not been computed on any window.

## What is measured
- Pair A+REF and the baseline A+T1b (50/50): CVaR25(F) (mean fade of the worst quarter), the gain against the baseline with a bootstrap probability over events (5,000), mean R (the upside kept).
- **Loading-matched control:** a pair of A with T1b scaled down by lambda = clip(b_REF / b_T1b, 0, 1) and the rest in cash (zero return), where b is the basket's trailing 250-day beta to CL=F controlling for SPY (data to t0-2). It gives the gain that a lower crude loading alone would buy.
- **The channel:** corr(REF's F, the change in the crack over F); corr(the change in the crack over F, the change in CL=F over F) across events; REF's mean F in the worst quarter of A's fades.

## Decision rule (builder's thresholds, provisional; amending after the result voids the test). **Supported** only if all four hold in the main window and again in the holdout
1. **Downside:** A+REF's CVaR25(F) loss is at least **20%** smaller than the baseline's, with bootstrap probability of improvement at least **0.80**.
2. **More than de-risking:** its gain exceeds the loading-matched control's gain by at least **10 percentage points**.
3. **The channel is the reason:** corr(REF F, the crack's change over F) is at least **+0.30**, and corr(the crack's change, crude's change over F) is at most **-0.20**.
4. **The reaction is kept:** A+REF's mean R is at least **60%** of the baseline pair's.
**De-risking only** if (1) holds and (2) fails. **Not supported** if (1) fails.

## Expectation (builder's, before running)
About 55% that (1) holds, 40% that (2) holds, 50% that (3) holds, and about 20% that all four hold in both windows. Refiners' crude beta is probably well below the producers', so much of the gain may be de-risking; and refiners' margins depend on the product
side and on crude differentials, not the crack proxy alone. Rob's expectation: to be added here before the run if he gives one.

## Limits
About 35 and 9 events; equal weights; a futures crack proxy for four refiners with different slates; raw returns include market direction (the loading control uses SPY in the beta only); the worst quarter is 9 events, or 3 in the holdout.
