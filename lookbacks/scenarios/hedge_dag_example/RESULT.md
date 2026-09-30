# Hedge DAG: worked example on real filings (2026-09-30)

Code: `nomad16/hedgedag.py` (report-only; 7 tests), `run.py` here. Filings: FY2024 10-Ks, Occidental (filed 2025-02-18) and Marathon Petroleum (filed 2025-02-27), stored in `filings/`.
Thesis: an oil supply shock. Sink: long OXY. One hedge feeding it: long MPC. Both are long; nothing is short. Not a test.

```
quotes verified literally against the stored filings: 4
documented: OXY +6.14% of pre-tax income per +$1/bbl crude; MPC +18.47% of pre-tax income per +$1/bbl crack spread (the two disclose only their own channel)

== strict: documented exposures only
  refused: the thesis node has no documented exposure to ['crack']: nothing to hedge

== switch: the undisclosed cross-channel exposures set to zero (implicit)
  status: switch: uses implicit exposures, to be checked | gaps: {}
  thesis (OXY) effect vector, % of FY2024 pre-tax income: [18, 74, 154]  worst alone 18
  hedge MPC: vector [111, 74, 148]  cosine to thesis 0.89  worst alone 74
  maximin weights {'thesis': -0.0, 'MPC': 1.0}  worst case 74  lift over the thesis alone 55
```

## What it shows
1. **The pipeline runs end to end on real, literally-verified quotes.** Each exposure is the company's own disclosed sensitivity; the quotes are checked against the stored filing text.
2. **Documents cover one channel per company.** OXY discloses its sensitivity to the oil price and nothing on the refining margin; MPC discloses the crack spread and the crude differentials and no flat-price sensitivity.
   Under the discipline (an unknown never supports), the strict run **refuses**: the thesis has no documented exposure to the crack channel. The disclosed data alone cannot build a cross-channel effect vector.
3. **The switch run (undisclosed cross-channel exposures set to zero, labelled implicit) does produce a vector pair, and it is only a switch to go and check.**
   OXY [18, 74, 154] and MPC [111, 74, 148] (% of FY2024 pre-tax income), cosine 0.89. Both long, and misaligned in the short-outage outcome, as the mechanism describes.
4. **It is not a hedge in this example: MPC beats OXY in the worst outcome (74 against 18), so the optimiser puts all its weight on MPC.** The result is set by the asserted shocks
   and by scaling to pre-tax income, and both are choices in this example. It demonstrates the machinery, not the mechanism.

## Limits, and what this says about the next step
- The shocks are the thesis's assertions ($/bbl per outcome), not documents and not anchored.
- The unit is the effect on annual pre-tax income as a percentage; the payoff to the equity needs a further step (valuation multiple, what is priced in).
- The finding that matters: **the "other pieces of data" that make chains diverge are mostly not in one place.** A company discloses its primary sensitivity. A broader exposure source
  (segment revenue, product slate, hedge books, throughput) is a data-spine question (V5), and until it exists most cross-channel exposures are implicit, so most hedge DAGs are switches.
