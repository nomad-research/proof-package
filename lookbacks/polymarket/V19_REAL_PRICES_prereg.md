# The backtests at real prices (registration, written before any trade print is pulled)

Rob, 2026-10-02: "yeah go ahead with both" (decision 22, step 1).

**Why.**
- A BT-T2 lock price is the last prices-history point within 48 hours before the lock. On a book with no real quotes, that point is the midpoint of an empty book, about 50¢.
- Decision 21 found that 58% of A2's armed positions in BT-T2 passes 1 to 5 sit on such prices. Near the lock, trade prints put those NOs at 91¢ to 100¢.
- This registration re-measures the backtest edges at prices that actually traded.

**What does not change.**
- The frozen answers, read and never rewritten, with each file's hash checked against its manifest.
- The reader's chances (`bt_t2.contract_chance`) and the cost rule (`bt_t2.cost`: price, plus 1¢ slippage, plus fee, on the tick).
- The matched-base rules, A2's thresholds, and the reading rule (decision 7).
- No pass folder is written to. Output: `v19/real_prices_result.json`. Scorer: `v19_real_prices.py`.

## 1. The real price

- **The price** of a contract is its **last trade print at or before the lock, and no more than 48 hours before it.**
  - It comes from `data-api.polymarket.com/trades?market=<condition id>`.
  - A YES print at p gives a YES price of p. A NO print at p gives 1 − p.
  - The 48 hours is the window V1 A2 set for lock prices (`bt_audit.MAX_AGE_H`), now applied to actual prints rather than price-history points.
- **A contract with no print in that window has no real price.**
  - It is dropped, from positions and from every matched base.
  - The share dropped is reported by pass.
- **The pull.**
  - The API returns at most 10,000 prints per page, and its largest offset is 10,000, so a market's newest 20,000 prints are reachable.
  - A contract whose prints do not reach back past the window's start, with that window still empty, is counted as "unreachable" and dropped. These are reported.
  - Only prints from 48 hours before to 24 hours after each lock are kept, in `bt/real_prices/<pass>.json.gz`.
  - Outcomes are read only at scoring, from the crawl, as before.
- **Which passes:**
  - BT-T2 passes 1 to 5 (`t2`, `t2_pass2`, `t2_pass3`, `t2_pass4`, `t2_pass5`);
  - the E3 mention passes 1 and 2;
  - BT-A passes 1 and 2.
  - R1's and R2's readings repeat pass 3's events, so they are left out.

## 2. The declared statistics

All three are at 95%, with 4,000 resamples by occasion (decision 16; `v19_a2.assign_occasions`).
- Occasions are assigned across each statistic's pooled passes together, so one real-world occasion drawn in two passes counts once.
- Events stay distinct, since passes never share an event.
- (Amended before any print was pulled. The first draft said "made unique per pass", which would have counted a shared occasion twice.)

| | Statistic | Positions | Score |
|---|---|---|---|
| **1. E1** | BT-T2 passes 1 to 5, pooled | Every NO position: the reader's NO chance (one minus its YES upper bound) is above the all-in NO cost at the real price | Pass 2's E1 score: (hit − cost) minus the mean (hit − cost) of NO sides of other events' contracts of the same class, cost within 0.05 |
| **2. A2** | BT-T2 passes 4 and 5, pooled (the passes A2 was not fitted on) | A2-armed NO positions on non-mention events: NO costs 50¢ or more, and the reader's midpoint is at least 20 points from the real YES price | The same as E1 |
| **3. E3b** | E3 mention passes 1 and 2, pooled | Every pick on either side whose reader chance is above its all-in cost | S1: (hit − cost) minus the mean (hit − cost) of both sides of other events' contracts, cost within 0.05 |

- **Reading:**
  - above zero: the edge is shown at real prices;
  - below zero: shown absent;
  - otherwise: direction only.
- **False positives.** Three declared statistics: if each had a 5% chance of a false positive and they were independent, the chance of at least one would be about 14%.

## 3. Secondary (declaring nothing)

- **Coverage.** The share of contracts with a real price, and of the original positions that keep one, by pass.
- **The same statistics resampled by event.**
- **E1 on non-mention events only, and the NO money (hit − cost).**
- **A2:**
  - on passes 1 to 5 pooled (1 to 3 are where it was found);
  - on BT-A at real prices (`v19_bta.py`'s positions with the real price in place of the draw's);
  - its money;
  - how many of the original armed positions stay armed.
- **By session kind:**
  - partition, terminal, percent, touch and dates, for E1 and for A2;
  - pick-the-winner (partition) against the rest is the layer-3 candidate of decision 22.
- **E3 (NO picks against mention NOs at the same price),** E3's registered statistic.
- **Two sensitivities:**
  - the volume-weighted average of the window's prints instead of the last print;
  - requiring at least $100 traded in the window. That is about one stake: W01's depth reading is about $100 within 2¢.
- **Not settled here:** the backtest's cost is still the last print plus 1¢, not the ask a buyer would have met. In a thin book the ask can sit well above the last print. The forward test prices at the live ask.

## 4. What follows

- **If E1 is shown at real prices,** E1 stands on the backtests, and the size of the edge is the new figure. A2's thresholds are not re-tuned on these passes; any change to them is a new rule, registered before the forward batches it is scored on.
- **If E1 is direction only or shown absent,** the backtest evidence for E1 does not survive real prices. The forward sweep, which prices at the live ask, is the remaining evidence, and what the reader is for is reopened with Rob.
- **E3b** is read the same way for the mention book.
- **From now on, any new backtest pass prices at the last print in the window, by this rule, and a written 0% counts as 1%** (decision 22's pipeline fix). Passes already frozen are not changed.

## 5. Cost

- About 13,000 contracts, at one or two API requests each, paced. No new sessions.
