# Construct-then-hedge on FOMC decision days — pre-registration (written before any thesis was authored and before any return was computed)

*2026-09-30. Rob: change the underlying to whatever works for now. Class chosen from a feasibility pass (`../feasibility/FEASIBILITY.md` and the FOMC check in it): 67 FOMC statement dates 2019-01 to 2026-09 (Fed calendar pages);
outcome measured mechanically as the change in the 5-year Treasury yield (^FVX) on the statement day; sector equities respond in complementary directions (banks +0.28, homebuilders -0.37, REITs -0.32 correlation with that change).
Tests the procedure in `docs/nomad_v17_amendment_A1.md` §7.1: the hedge is **constructed thesis-first**, then the basket is built to fit it, and the narrative must beat a blind statistical hedge. Equities only; no funds, no derivatives. Public prices; nothing waits on it.*

## Outcomes (a typed vocabulary, like an ACK's), measured on the statement day
hawkish: change in the 5-year yield of +5 bp or more; dovish: -5 bp or less; neutral: between. Counts (seen in the feasibility pass): 11 hawkish, 20 dovish, 36 neutral.

## The primary thesis and its failure set (fixed here)
**Primary basket A: JPM, BAC, WFC, C (long).** Thesis: a hawkish or neutral decision (yields up or flat) supports bank net interest income. Thesis set: hawkish + neutral. **Failure set: dovish.**

## Construction, done once by a cold session and frozen before any evaluation
A cold session (no tools, no prices, no files) is given the primary thesis and its failure set, the universe below, and asked to (1) write a **hedging thesis** over the same outcomes that covers the failure set, with the mechanism chain that makes it true (financing cost, duration, leverage, and so on), and every exclusion it makes stated with its reason; (2) choose **exactly four** names from the universe to fit that thesis.
Its output is committed as `hedge_basket.json` before the evaluation script is run. **Contamination, disclosed:** the session's knowledge runs to mid-2026, so it may know how sectors behaved on past decision days; this is a look-back, and the clean read is the forward decision days from now on (accrued the same way).
**Universe (46, no banks, fixed):** AAPL MSFT AMZN GOOGL META NVDA TSLA UNH JNJ PFE MRK ABBV LLY PG KO PEP WMT COST HD LOW MCD NKE DIS CMCSA VZ T LIN CAT DE HON UNP UPS DUK SO NEE D AEP O SPG PLD AMT EQIX DHI LEN PHM XOM CVX.

## The comparators (all on the same events, all long-only equal weight, fixed here)
- **Narrative pair:** 0.5 A + 0.5 the constructed basket H.
- **De-risking control:** 0.5 A + 0.5 cash (zero return). Anything that only reduces bank loading does at least this well.
- **Blind statistical pair:** 0.5 A + 0.5 S, where S is the four names from the universe with the **most negative trailing regression coefficient on the 5-year yield change** (daily excess returns over SPY on the daily change in ^FVX, 250 trading days ending the day before the statement). Same universe, same size, no narrative, refreshed for every event.

## Windows and statistic
Window W = close(t0-1) to close(t0+1), excess over SPY (t0 is the statement date). Per event: the return of each pair. Two time halves: **2019-01 to 2022-12** and **2023-01 to 2026-09** (the rule is applied to each half).

## Decision rule (builder's thresholds, provisional; amending after the result voids the test). "Narrative guidance adds" only if all three hold in **both** halves
1. **Beats plain de-risking on the failure set:** on dovish events, the mean of (narrative pair minus the de-risking control) is positive, with a bootstrap probability over events of at least **0.80**.
2. **Beats the blind statistical hedge:** on dovish events, the mean of (narrative pair minus the blind pair) is at least **+0.10%** (10 bp), with a bootstrap probability of at least 0.80. If the narrative only reproduces what the data would pick, the narrative is decoration.
3. **The thesis upside is kept:** on hawkish and neutral events, the narrative pair's mean is at least the de-risking control's mean minus 0.10%.
Also reported: the same three for the blind pair against the control, and the overlap between H and S (names in common).
A half with fewer than 8 dovish events is unreadable.

## Expectation (builder's, before running)
About 50% that (1) holds in both halves (a hedge that adds a rate-falling winner should beat cash on dovish days), about 25% that (2) holds in both: a blind rate-beta pick will probably choose much of what the narrative names (utilities, REITs, homebuilders), so the
narrative would then add nothing beyond the data. Rob's expectation: to be added here before the run if he gives one.

## Limits
67 events, about 10 dovish per half; equal weights; a single constructed thesis, not one per event; the model's knowledge of the sample period; excess returns over SPY remove the market but leave a market-sensitive basket exposed on rate days; a 5-year yield change is one proxy for the decision's surprise.
