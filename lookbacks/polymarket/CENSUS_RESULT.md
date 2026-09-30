# Polymarket catalogue census — result (run 2, 2026-09-30)

Definitions: `CENSUS_SPEC.md` (written before the run; two bug amendments listed there). Output: `census_run2_output.txt`. Run 1 (truncated, misclassified date ladders) kept beside it. **Coverage is a union of orderings, not the whole catalogue** (12,573 active and 11,476 closed events; 11,696 dropped as sport, gaming, entertainment or temperature). This is a census, not a test.

**Usable = event volume ≥ $100k and ≥ 3 markets each ≥ $10k.** Multi-market usable structures: 1,194 (1,262 at a $1k market floor, 771 at $100k).

| Class (usable) | Active | Closed | Closed and ending after 2026-06-30 |
|---|---|---|---|
| Partition, exact | 51 | 111 | 19 |
| Partition with an open slot | 85 | 193 | 42 |
| Threshold ladder | 319 | 432 | 142 |
| Date ladder | 1 | 1 | 0 |
| Conditional chain | 0 | 0 | 0 |

Usable closed structures by group: crypto 268, politics and elections 185, geopolitics 172, economy and finance 46, technology and science 42, other 23, business and manufacturing 1. Excluding crypto, 469 of 737 (run 1 count) closed usable structures remain.

## What it says
1. **Threshold ladders are the largest class**, and most are crypto price levels or geopolitical "by date" events. A ladder is nested and monotone, so payoffs are exact, and within one event the contracts are perfectly related, which makes them weak as a *hedge* test (the relation is by construction, not a narrative Nomad found).
2. **Exact partitions are few (111 closed) and open-slot partitions are more (193).** Open slots are typed gaps in construction; they are the common political case.
3. **Conditional chains and other classes are absent.** Polymarket does not list conditional contracts in this catalogue, so a "conditional chain" cannot be a V1 class.
4. **Cross-event relations are not counted.** The 19,229 candidate pairs are crude title-word overlap and mean nothing until a session reads them. A hedge over a thesis lives across events (Rob's mechanism), so this is the count that decides V1 and it is still unmeasured.
5. **Classifier is heuristic.** Sampling found a bug in run 1; run 2 has not had a second sampling. Class labels are not verified beyond that.

## What decides V1
Rob's note (2026-09-30): once the modified PredictionProphet is live, all classes become viable, because the necessary-condition decomposition builds the structure inside a single contract. So the census does not limit the product's scope (singles and pairs are in scope; 520 closed single or pair events have volume ≥ $100k). It only limits **V1**, which needs several already-resolved related contracts with exact payoffs.
The candidate V1 class is therefore **partitions and ladders in geopolitics, politics, economy and finance, and technology, closed after 2025**, with cross-event thesis baskets built by a session from the entity registry, not by title words. Proposed for Rob's confirmation, not ratified. D33 stays proposed until he confirms.

## Correction (2026-09-30, found building the V1 pool)
The column "Closed after 2026-06-30" and the "203 usable" figure used the **scheduled `endDate`**, not the time the event actually resolved, so it counted events that resolved before the model's cutoff. The clean count, filtered on the actual `closedTime`, is **78 events** (see `V1_prereg.md` A9). The other counts (classes by status, groups, sensitivity to the liquidity floor) do not depend on it.
