# Hedge-DAG validation — pre-registration (written before any return was computed)

*2026-09-30. Order agreed with Rob: accept implicit exposures as switches, validate on realised payoffs, and go to structured filing data only if the effect is there.
The claim under test is one component of the mechanism: **given the channel shocks that occurred, do the companies' documented exposures predict which of them did better, and by how
much they diverge?** It does not test whether a thesis can forecast the shocks. Public prices; nothing waits on it. Illustrative at this size.*

## Exposures (documented, quotes verified literally against the stored FY2024 10-Ks; frozen in `exposures.json`, extracted by a cold session that computed nothing)
Coverage first, which is itself a finding: of 12 large oil companies, **5** disclose an unhedged sensitivity of earnings to a commodity or margin (OXY, EOG, XOM, MPC; APA only as revenue),
**3** disclose only for their hedge book (KMI, DVN, FANG), and **4** disclose none (COP, VLO, PSX, CVX).

**Primary set (4 names): OXY, EOG, XOM, MPC.** Sensitivities used, per unit of the shock series, in $M of annual effect, by the metric priority pre-tax income, then pre-tax operating cash flow,
then adjusted EBITDA, then after-tax earnings:
- OXY: crude 250 per $1/bbl (pre-tax income); gas 350 per $1/MMBtu (35 per $0.10/Mcf).
- EOG: crude 204 per $1/bbl (pre-tax operating cash flow, including NGLs); gas 420 per $1/MMBtu (42 per $0.10).
- XOM: crude 650 per $1/bbl Brent (after-tax upstream earnings; Brent proxied by the front-month crude series); gas 750 per $1/MMBtu (75 per $0.10, Henry Hub).
- MPC: refining crack 1,100 per $1/bbl (Refining & Marketing adjusted EBITDA). MPC's gas figure (350 per $1) is **excluded**: the filing gives the size and not the sign, and gas is a cost to a refiner.
Every channel a company does not disclose (a crack for an E&P, a crude price for MPC, differentials for anyone) is an **implicit zero**: this whole study is a *switch*, not support. APA is excluded from the primary (revenue, not income).

## Shocks (realised, from front-month futures; a roll can put a jump in a continuous series, noted and not filtered)
- crude: CL=F, change in $/bbl over the window. gas: NG=F, change in $/MMBtu. crack: the 3-2-1 proxy, (2 x RB=F x 42 + HO=F x 42) / 3 minus CL=F, change in $/bbl.
Differentials are dropped (no series).

## Events and window
The same mechanical rule as the depth tests (CL=F up 4.0% or more in a day, declustered 10 trading days), restricted to **2025-03-01 to 2026-09-29**: after the FY2024 10-Ks became public
(the earliest, KMI, on 2025-02-13; the latest of the four used, 2025-02-27), so the exposures are known before every event. Window R = close(t0-1) to close(t0+2). Read only if at least **8 events**.
Disclosure: the event dates and some of these names' returns in aggregate were seen in the depth tests; these four names' event returns were not computed.

## Prediction and realisation
- **Documented model:** p_it = sum over channels of (sensitivity_ic x realised shock_tc) / market cap_i,t0-1 (price x shares outstanding from the 10-K cover XBRL; if any share count is unavailable, all four are normalised by FY2024 pre-tax income instead).
- **Baseline, the beta model:** q_it = beta_i x (CL=F return over R), beta_i from daily returns on CL=F over the 250 trading days ending at t0-2 (the event is excluded).
- **Realised:** stock return over R minus SPY's, then both p, q and realised are **demeaned within each event** across the four names (so it is divergence, not level, that is scored).

## Statistics and rule (thresholds are the builder's, provisional; amending after the result voids the test)
1. **rho_doc:** pooled correlation of demeaned p with demeaned realised over all (name, event) pairs; bootstrap over events (5,000). **Supported if rho_doc >= 0.30 and the 10th percentile of the bootstrap is above 0.**
2. **rho_beta:** the same for q. **Adds beyond the beta model if rho_doc - rho_beta >= 0.10.**
3. **Spread:** per event, (mean of OXY, EOG, XOM) minus MPC, predicted (documented model) against realised. **Supported if the sign hit rate is >= 65% and the correlation across events is >= 0.40.**
"Divergence predictable" = (1) and (3). "Adds beyond beta" = (2). Fewer than 8 events: unreadable.

## Expectation (builder's, before running)
About 40% for (1), 30% for (2), 45% for (3). The E&Ps' documented exposures rank almost the same as their betas to crude, so the model can only add where the crack shock diverges from crude and MPC
is the odd name out; with one refiner and 12 events that is thin. Rob's expectation: to be added here before the run if he gives one.

## Limits
About 12 events and 4 names; heterogeneous metrics; Brent proxied by WTI; exposures are annual budgeted sensitivities applied to a 3-day window; MPC is the only refiner; implicit zeros dominate the off-channel cells.
