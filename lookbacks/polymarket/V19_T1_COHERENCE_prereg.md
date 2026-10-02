# T1: do linked contracts lag each other? (registration, written before any trade is pulled)

Rob, 2026-10-02: "yeah run it", to running v18's T1 ("coherence along logical edges", `docs/nomad_v18_updates.md` §6.2) before building the news-over-the-graph design (decision 26).

**Why.**
- Decision 26 builds for facts that have not yet reached the contracts they imply.
- If Polymarket keeps linked contracts consistent within minutes, there is nothing downstream to catch.
- v18 planned this measurement and never ran it. Trade prints now make it possible from here, on resolved markets.

**What it can and cannot settle.**
- It measures **logical** links: pairs where one contract's chance is bounded by another's under any belief. These are the links an arbitrage bot can enforce without judgment.
- It does not measure **causal** links ("if A, then B is more likely"). Those need judgment, and price alone cannot test them.
- So **a fast result rules out an edge in logical propagation only.** A slow result means even exact links lag, a strong sign that judgment links lag more.

**Not touched.** No frozen file is written. T3 keeps running. Output goes to `bt/t1/` and `v19/t1_result.json`; the script is `v19_t1.py`.

## 1. The links (drawn from titles and rules only, before any trade is pulled)

| Family | What | Link | Count |
|---|---|---|---|
| **F1, across events, exact** | A coin's "price on [date]" bracket event, and the same coin's "above ___ on [date]" threshold event. Both resolve on the Binance BTC/USDT-style 1-minute candle close at noon ET | For each threshold X: (a) the lowest bracket starting at or above X can be no likelier than "above X"; (b) the highest bracket ending at or below X, plus "above X", can be no more than 1 | 48 coin-dates (12 each for Bitcoin, Ethereum, Solana and XRP), drawn by seed 20261017 from the 856 such pairs in the crawl |
| **F2, within event, exact** | Neighbouring thresholds of the same 48 "above" events | "Above" a higher threshold is no likelier than "above" a lower one | the same 48 events |
| **F3, within event, exact** | Neighbouring rungs of every ladder and date event in BT-T2 passes 1 to 5 (189 terminal, 167 touch, 39 date events; 4,011 contracts) | The rung that is easier to reach is at least as likely (`bt_t2.rung_value`, `orient`) | 395 events |

## 2. The prices: trade prints

- **The source.** Every contract's trades from `data-api.polymarket.com/trades`, the newest 20,000 at most (the API's limit), as YES prices: a NO print at p counts as 1 − p.
  - A market with more than 20,000 prints is covered only for its latest part. Coverage is reported.
- **A link's state** is read at every print on either leg, using each leg's last print.
  - **A leg counts only if it printed within the last 30 minutes.** An older print is not a price anyone could trade at.
  - 30 minutes is also the shortest time a news-reading pipeline could fetch, read and act in.
- **A violation** is a state where the link is broken by more than 2¢. That is 1¢ of slippage per leg, the pipeline's cost rule; fees are not added.
- **An episode** is a run of violating states. It ends at the first fresh state that is not violating. Its length runs from its first violating print to that point; an episode that never ends is marked censored.
- **Traded at a violating price:** the dollar value of prints on either leg during the episode. Someone traded at the inconsistent price, so a counterparty could have been us.
- **A shock** (a stand-in for news arriving): a print that moves a leg's YES price by 10 points or more from that leg's previous print, made within the hour before.
  - An episode is "after a shock" if it starts within 60 minutes after a shock on either leg.

## 3. The reading (declared per family)

**Logical propagation lag is worth building for** if, among the episodes that follow a shock, both hold:
- **the median episode lasts 30 minutes or more.** Basis: the reaction window above.
- **The median dollars traded at violating prices is $100 or more.** Basis: about one stake. W01's depth was about $100 within 2¢.

**Otherwise**, linked contracts are kept consistent faster than a reader can act, or too thinly to trade.

**Reported with it:**
- the share of fresh states that violate;
- the number of shocks, and the share followed by an episode within 60 minutes;
- episode lengths (median, 90th percentile) and the share lasting 30 minutes or more;
- dollars traded at violating prices;
- censored episodes;
- coverage;
- F3 by kind.

There is no bootstrap: this describes what the market did. It is not an estimate of an edge.

## 4. What follows

- **Worth building for (any family):** the graph design keeps logical links as a source of positions, starting with that family. A forward registration follows before any of it is used.
- **Not worth building for (all families):** logical links are dropped as a source of positions. The graph's role narrows to judgment links, tested forward through T3 and the reader, and the habit-question core of decision 26 is unaffected.

**Drawn** (`v19_t1.py draw`, from titles and rules only, before any trade was pulled; `bt/t1/links.json`):
- F1: 1,009 links across 48 coin-dates;
- F2: 482 links;
- F3: 3,460 links in the 361 ladder and date events with orderable rungs;
- 4,955 contracts in all.

Orientation was checked by hand on above, dip-to, at-least and by-date ladders.
