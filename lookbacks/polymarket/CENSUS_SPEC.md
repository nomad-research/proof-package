# Polymarket catalogue census — definitions (written before the census was run)

*2026-09-30. Purpose (from the review Rob supplied): count which event classes have several related contracts with usable liquidity, so V1 (the hedge mechanism with exact payoffs) runs on a class that exists. D33 is ratified only after this. A census, not a test: no verdict, no thresholds that gate anything except the labels below.*

**Universe.** Every active event, paged to the end; and closed events, two orderings (by volume, descending; by end date, descending), each paged until the API stops (it refuses offsets beyond about 2,100). Events carrying any of the recorder's default excluded tags (sport, gaming, entertainment, daily-temperature) are dropped; the count dropped is reported. The public API is Polymarket's market-metadata endpoint; nothing is written to the ledger.

**Classes** (mechanical, per event, in this order; an event gets the first that fits):
- **Partition, exact:** `negRisk` is true, at least 3 markets, and no market is flagged as an "other" or placeholder slot (`negRiskOther` true, or a title of "Other", "Someone else", or a placeholder such as "Person A"). Exclusive and exhaustive, so the payoff matrix is exact.
- **Partition with an open slot:** `negRisk` true, at least 3 markets, at least one such slot. The slot is a typed gap.
- **Threshold ladder:** at least 3 markets whose `groupItemThreshold` differs, or whose questions differ only by a number (above, below, at least, over, under, a dollar, percent or count figure).
- **Date ladder:** at least 3 markets whose questions differ only by a date (by, before, on or before a date): nested by construction.
- **Conditional chain (low confidence):** a question containing "if", "conditional on", "given that", or "assuming".
- **Other multi-market:** at least 3 markets that fit none of the above.
- **Single or pair:** 1 or 2 markets.

**Usable liquidity.** A market is usable if its volume is at least **$10,000**; a structure is usable if it has at least **3 usable markets** and the event's volume is at least **$100,000**. Sensitivities reported: market volume at least $1,000 and at least $100,000.

**Groups** (by tag, first match in this order): geopolitics (geopolitics, world, war, iran, israel, russia, ukraine, china, taiwan, middle-east, ceasefire, nato, strait-of-hormuz); politics and elections (politics, elections, global-elections, us-presidential-election, midterms, trump, congress); economy and finance (fed, fed-rates, economy, finance, stocks, equities, oil, commodities, inflation, earnings, earn-4, ipo, tariffs, trade); crypto (crypto, bitcoin, ethereum, crypto-prices); technology and science (tech, ai, big-tech, openai, ai-releases, science, space, health, climate, energy, spacex); business and manufacturing (business, manufacturing, companies, ipo); other.

**Reported:** events, markets and total volume by class and group; the share of usable structures; the count of closed events whose end date is after **2026-06-30** (the model cutoff, so clean for a round); the number of exact partitions and date ladders among them; and a first count of **cross-event candidates** (events in the same group sharing at least two title words), unmeasured beyond that.

## Amendments of 2026-09-30, after run 1 and before any conclusion is drawn (coverage and classifier bugs, not threshold changes)
Run 1 output is kept as `census_run1_output.txt` and `census_run1_rows.json`.
1. **Coverage.** Run 1 stopped at the API's offset cap (2,100 for active; two orderings for closed), so "paged to the end" was not true. Run 2 unions five orderings, ascending and descending, for active, and four for closed. It is still not the whole catalogue; the output says so.
2. **Classifier bug.** Run 1 counted a year or a day-of-month as a number, so date ladders ("Trump meets Putin by...?") were labelled threshold ladders. Run 2 removes dates before looking for numbers. The class definitions above are unchanged.
3. No liquidity threshold, group list or class order was changed.
