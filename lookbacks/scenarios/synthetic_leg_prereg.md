# Synthetic-exposure leg — pre-registration (written before any number was computed)

*2026-09-30. Rob: to isolate the mechanism, make one leg entirely of synthetic exposure: an oil basket, and a synthetic oil-exposure position, run against one correlated and one uncorrelated thesis.
"It won't be marginal when we find it." Equities only, no funds, no derivatives (derivatives later). Public prices; nothing waits on it.*

**Idea.** Give the synthetic leg **the same crude loading** as the oil basket, so the crude channel cannot be the reason it hedges. What is left is the downstream residual chain. Two named conditions:
the **correlated thesis** (the synthetic leg's residual chain moves with the oil basket's, rho high) and the **uncorrelated thesis** (its residual chain is independent, rho near 0).

## Part A: the controlled leg (a calibration, not a test of the world: the arithmetic of diversification is not in doubt; the point is how big the effect is and what a real leg would have to achieve)
- Events: the mechanical rule from the depth tests (CL=F up 4.0% or more, 2020-03-01 to 2020-07-31 excluded, declustered 10 days), main window 2019-01-02 to 2025-12-30 and holdout 2026-01-02 to 2026-09-29.
  Windows: R = close(t0-1) to close(t0+2); F = close(t0+2) to close(t0+20). Basket A = T1a (COP, EOG, OXY, DVN); baseline second basket = T1b (XOM, CVX, APA, FANG).
- Synthetic leg S(rho): its window return = b_A x (the CL=F window return) + e_S, where b_A is A's trailing 250-day beta to CL=F (ending t0-2) and e_S has the same standard deviation as A's own residual over that window and correlation **rho** with it (fresh noise, seeded, 500 repetitions).
- Report the 50/50 pair A+S(rho)'s worst-quarter fade loss (CVaR25(F)) against the A+T1b baseline, for rho in {0.9 (correlated thesis), 0.5, 0.0 (uncorrelated thesis), -0.5}, and the rho at which the gain first reaches 30%. No verdict: it is a calibration.

## Part B: can real equities make such a leg? (this is the test)
Universe, fixed now (non-energy): AAPL MSFT AMZN GOOGL META NVDA JPM BAC WFC GS MS BRK-B UNH JNJ PFE MRK ABBV LLY PG KO PEP WMT COST HD LOW MCD NKE DIS CMCSA VZ T LIN CAT DE HON UNP CSX UPS FDX MMM FCX NUE CF MOS DAL UAL.
A name without history over the whole window is dropped and reported.
- At each event, with data up to t0-2 only: for every name, its beta to CL=F controlling for SPY (250 trading days), and its residual correlation with A's residual (A regressed on CL=F and SPY).
- **S_corr (the correlated-thesis synthetic):** long-only, no leverage, weights summing to 1, each at most 0.15, maximising the portfolio's crude beta subject to the weighted residual correlation with A at most 0.2 (a linear proxy). 
- **S_unc (the uncorrelated-thesis synthetic):** the same constraints, minimising weighted residual correlation with A subject to a crude beta between -0.05 and +0.05.
- Reported per event set: f = S_corr's crude beta divided by A's crude beta (the fraction of the oil loading achievable); each pair 50/50 with A; CVaR25(F) gain against A+T1b with a bootstrap probability over events (5,000); S's own mean R as a share of T1b's own mean R; the fade correlation with A.
- **A real synthetic oil leg exists (supported)** if, in the main window **and** the holdout: f >= 0.50; the A+S_corr pair's CVaR25(F) loss is at least 20% smaller than the baseline's with probability >= 0.80; S_corr's own reaction share of T1b is >= 0.50 and larger than S_unc's.
  **Diluted** if the gain holds and the reaction share or f fails.
- **Expectation (builder's):** about 75% that f is well below 0.5 (non-oil equities have small crude betas), so S_corr comes back diluted, and S_unc gives a downside gain without a reaction.
  Part A will show the effect if the loading could be matched. Rob's expectation: to be added here before the run if he gives one.

## Limits
About 35 and 9 events; the residual-correlation constraint is a linear proxy; a long-only, unlevered synthetic cannot exceed the loading of the names in it (leverage or derivatives would, and are for later); market direction is controlled only through the SPY term in the betas.
