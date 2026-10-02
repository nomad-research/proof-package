# The Polymarket frame (proposed, 2026-09-30)

*Rob: "we need to get the model right and validate it before I start paying out the nose for stuff; remember this is for Polymarket now; with the Jev or Laya over the modified PredictionProphet angle; free is just to try: go to source and reconstruct so as not to compress while we wait for enriched paid services." Paid sources are allowed when they are the better choice, after validation.*

## 1. What the existing documents say about it (nothing here goes beyond them)
- "A prediction-market contract is an ACK with a price. Nomad's wall disappears there, because the instrument is the event and the loss is capped at the price paid." (`docs/nomad_the_system_as_it_stands.md` B-section on prediction markets; v16 spec §34.)
- "A separate project (a Polymarket agent forked from PredictionProphet) would wire in a decision model and use Nomad as the risk engine, replacing the fork's twenty generated subqueries with the set of relevant first principles gathered by a recursive search chain."
- The fork decomposes a contract into its **necessary conditions**, bounds the probability above by the weakest of them (a **Fréchet bound, summed over alternative routes**), keeps the market price out of the reasoning that produces a thesis or a probability until the gate (price is attentional, R6: never evidence, but it stays in the system for expression, sizing, costs and scoring; Rob, 2026-09-30), and has **Jev judge conditions narrowly**. "This is not specified in this file"; the v16 spec §34 records it as a separate spec.
- Roles (spec §23.4): **Laya** is the small reader model (fine-tuned; it chooses among options it is given, it does not generate them); **Jev** is a frontier-class decision model whose only role is `crowd_mirror`, held. Decision-model output may propose and never enter derivation conditions, reachable or thesis sets, or construction weights.
- The fork's own spec is not in this repository; the points above are all that is documented here.

## 2. Why this is a better place to validate the mechanism
In equities the hard part was the payoff matrix: how an instrument responds by outcome had to be estimated, and every look-back fought that estimate. An event contract's payoff is **exact**: it pays 1 in the states where its condition holds and 0 in the others, and the most that can be lost is the price paid. So in a set of related contracts:
- the payoff matrix over a partition of the states is known, not estimated (a negative-risk multi-outcome event is an exact partition; a threshold ladder is nested);
- the hedge-existence condition (A2, Ville's theorem) and the maximin are exact;
- what remains uncertain is the **probability** of each state, and the logical structure between contracts. Those are exactly what the necessary-condition decomposition and its Fréchet bound address, and what a narrative (a thesis with anchored conditions) supplies.

## 3. The model in the entity view
| Thing | Entity, kind, relation |
|---|---|
| A contract (question, outcomes, end date, resolution rules) | an `instrument` of kind `event_contract`; `references` a **condition** (a thesis-like claim over the states) |
| Yes and No | `outcome` entities of an `outcome_vocab`; the contract `pays_under` each with payoff 1 or 0 (basis: documented, from the resolution rules) |
| A necessary condition | an entity of kind `thesis` (role: condition) related by `requires` to the contract it is necessary for; a **route** is a set of conditions jointly sufficient |
| The upper bound | a statement: probability at most the sum over routes of the smallest necessary-condition probability in the route, capped at 1; basis and evidence links recorded |
| The market price and order book | a `quote` dataset (attentional); **kept out of the reasoning until the gate**: the reasoning record is frozen and hashed before any price is read, which is what a lock does |
| What settles it | a `document_series` carrier named in the resolution rules; the resolution is a `resolution` entity `observed_in` a source |
| A basket of contracts | a `basket` `constructed_for` a thesis; a hedge among contracts is a thesis (role hedge) covering the failure states of the primary, built thesis-first (A1 §7.1) |
| Laya, Jev, a fresh session | `session` entities, `authored_by` on every proposal; a proposal never enters derivation |

Nothing in this table names a domain: a contract on a court ruling and one on a central-bank decision are the same kinds.

## 4. What to validate, free, in this order (each is pre-registered before any run)
- **V1, the hedge mechanism with exact payoffs (no decision model needed for the payoff side).** On resolved Polymarket events with related contracts, does thesis-first construction of a hedge beat a blind statistical hedge (minimum correlation on prior prices), and plain de-risking, on the realised worst case net of prices paid? The narrative side is a fresh session per event, blind to the outcome and, where possible, to the price.
- **V2, the necessary-condition bound.** With the price hidden, does the bound behave as an upper bound (realised frequency at or below it, by bin), how tight is it, and does a price above the bound flag an over-priced Yes? The decision model has a training cutoff, so only contracts resolved **after** it are clean (the spec's rule refuses backfilled use inside the window): recent and forward contracts, paper-traded.
- **V3, record forward.** Polymarket's history for old markets may be incomplete (the price-history endpoint returned nothing for the closed market I probed), so a recorder of market metadata, prices and order books from now is cheap and cannot be recovered later. It needs a host that stays up.
Each carries a **null control** (permuted or shuffled outcomes) and its bar declared before the run.

## 5. Data, free first, and what would earn a paid source
| Need | Free now | Paid, only if V1 or V2 justify it |
|---|---|---|
| Contracts, outcomes, rules, resolutions | Polymarket's public market-metadata API (reachable) | |
| Prices and order books | Polymarket's public price-history and book endpoints (history thin for closed markets); a forward recorder | a vendor with full historical order books |
| Evidence for conditions (the recursive search chain) | EDGAR full-text search, GDELT, Wikipedia and its revisions, agency sites | a search or news API with point-in-time dating |
| Filings, calendars, regulators | SEC (reachable), Fed pages, BLS API, Treasury, CFTC | parsed filing sections |
| Decision model | Laya (CPU, installable); Jev: access to be settled | |
Everything free is fetched from the source and stored **whole**, never reduced at the cache; reductions happen at read time.

## 6. Decisions (Rob's)
1. **Which model first:** Laya (proposes among given options; cheap) or Jev (frontier-class; judges conditions narrowly; access and cutoff to be settled)?
2. **Order:** V1 first (mechanism, exact payoffs), or V2 first (the bound)? I lean V1: it needs no trained model on the payoff side and tests the mechanism you care about.
3. **Host for the forward recorder** (V3).
4. **Ratify the frame** as the expression layer for the Polymarket case (proposed D33).
