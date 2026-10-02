# Construct-then-hedge on FOMC statement days — result (run 2026-09-30)

Pre-registration `PREREG.md` (commit fff569f); the constructed basket was frozen in `hedge_basket.json` (commit ead9380) before `evaluate.py` ran. Rule and thresholds unchanged.

Hedging thesis and basket, written by a cold session that saw no prices: dovish outcomes lift long-duration, levered, rate-financed equities; basket **DHI, O, AMT, NEE** (homebuilder, two REITs, a levered utility), each tied to a hop (mortgage financing, duration and discounting, leverage and refinancing, financing cost).

```
events 67: {'hawkish': 11, 'neutral': 36, 'dovish': 20} | A ['JPM', 'BAC', 'WFC', 'C'] | H ['DHI', 'O', 'AMT', 'NEE']
mean overlap between the constructed basket H and the blind pick S: 1.7 of 4 names

== 2019-01 to 2022-12: 36 events, 8 dovish
  dovish events: mean A -0.0197; narrative pair - control +0.0026 (P>0 0.81); blind pair - control +0.0024; narrative - blind +0.0002 (P>0 0.52)
  hawkish and neutral events: narrative pair minus control -0.0023
  (1) beats de-risking [ok]  (2) beats the blind statistical hedge [fail]  (3) upside kept [fail]

== 2023-01 to 2026-09: 31 events, 12 dovish
  dovish events: mean A -0.0041; narrative pair - control +0.0042 (P>0 0.98); blind pair - control +0.0114; narrative - blind -0.0072 (P>0 0.00)
  hawkish and neutral events: narrative pair minus control -0.0032
  (1) beats de-risking [ok]  (2) beats the blind statistical hedge [fail]  (3) upside kept [fail]

verdict (pre-registered; both halves): NOT SUPPORTED {'2019-01 to 2022-12': [True, np.False_, np.False_], '2023-01 to 2026-09': [True, np.False_, np.False_]}
```

## Verdict under the pre-registered rule: **not supported** ("narrative guidance adds" needed all three conditions in both halves)
- **(1) It beats plain de-risking on the failure set: yes, in both halves.** On dovish days the narrative pair beat the half-cash control by +0.26% (P 0.81) in 2019 to 2022 and +0.42% (P 0.98) in 2023 to 2026. **A constructed long hedge does work, with no short.**
- **(2) It beats the blind statistical hedge: no.** In 2019 to 2022 they were level (+0.02%, P 0.52). In 2023 to 2026 the blind pick was clearly better (narrative minus blind -0.72%, P 0.00). The two baskets overlapped by 1.7 of 4 names on average.
- **(3) The thesis upside is kept: no, narrowly.** On hawkish and neutral days the narrative pair trailed the control by 0.23% and 0.32% (bar 0.10%): what the hedge costs.
- Builder's expectation (about 50% for (1) in both halves, 25% for (2)): (1) came in, (2) did not.

## What it says
The hedge exists and construction can produce it. The narrative did **not** beat what a blind rate-beta fit picked out of the same universe. Here the channel is one factor (the yield), stable, with plentiful history, which is the case where statistics are strong and a narrative has little to add.
One reading, not shown by this test: guidance should matter where the statistics cannot be estimated, for a rare or new event class, a regime break, or a single-company outcome with no trailing history. That is a hypothesis to test next, not a result.

## Limits
67 events, 8 and 12 dovish in the halves; one constructed thesis, not one per event; a look-back and the constructing session's knowledge reaches mid-2026, so the clean read is the forward decision days; the blind hedge is a strong baseline (trailing yield beta, refreshed every event); excess returns over SPY; a 5-year yield change is one proxy for the surprise.
