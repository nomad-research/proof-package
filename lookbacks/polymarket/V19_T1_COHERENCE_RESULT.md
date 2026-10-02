# T1: do linked contracts lag each other? (result)

**Process.**
- Registered in `V19_T1_COHERENCE_prereg.md` (commit `7e0c7c2`) before any trade was pulled.
- Links drawn from titles and rules only.
- Full trade histories for all 4,955 linked contracts (1.2 million prints, no errors; commit `58f641b`).
- Scored by `v19_t1.py score` into `v19/t1_result.json`.

**The rule, briefly.**
- A link is read at every print on either leg, counting only legs that printed in the last 30 minutes.
- A violation is a break of more than 2¢.
- A shock is a 10-point move in a leg within an hour.
- **Worth building for:** after a shock, the median violation episode lasts 30 minutes or more, and has $100 or more traded at the violating prices.

## 1. Results

| | F1: coin brackets against thresholds, across events | F2: neighbouring thresholds | F3: backtest ladders and date events |
|---|---|---|---|
| Links | 1,009 (48 coin-dates) | 482 | 3,460 (361 events) |
| Fresh states that violate | 3.4% | 0.0% | 0.4% |
| Episodes (censored) | 3,753 (4) | 27 (0) | 1,261 (23) |
| Shocks followed by an episode within the hour | 40% of 2,117 | 1% of 893 | 11% of 9,506 |
| **After a shock: median length** | **11 seconds** | 24 minutes (7 episodes) | **4.6 minutes** |
| After a shock: 90th percentile | 6 minutes | 6 hours | 17 hours |
| After a shock: lasting 30 minutes or more | 3% | 43% | 26% |
| **After a shock: median dollars traded at violating prices** | **$38** | $19 | **$15** |
| After a shock: $100 or more traded | 32% | 29% | 18% |
| Median largest gap | 4¢ | 7¢ | 7¢ |
| **Reading** | kept consistent faster than a reader can act, or too thinly | the same | the same |

**F3 by kind** (after a shock):

| | Median length | Median dollars |
|---|---|---|
| Date ladders | 1.3 min | $37 |
| Terminal ladders | 2.0 min | $7 |
| Touch ladders | 8.1 min | $22 |

**The tail** (exploratory, declaring nothing): episodes after a shock that lasted 30 minutes or more *and* had $100 or more traded.

| | Episodes | Where | Median gap | Median traded | Median length |
|---|---|---|---|---|---|
| F1 | 20 | 15 coin-dates | 11¢ | $276 | 56 min |
| F2 | 1 | | | | |
| F3 | 19 | 15 events (6 months) | 8¢ to 21¢ | $175 to $381 | 1 to 5 hours |

Gaps are measured on last prints, so not every one could have been traded at both legs at once. The real tail is smaller than this.

## 2. Reading

- **Polymarket keeps exactly linked contracts consistent.**
  - On the busy coin markets, a break across events is closed in a median of 11 seconds after a move, which is bot speed.
  - On thinner ladders, it is closed in minutes, and the breaks that linger have little money behind them.
- **No family meets the registered bar.** Logical propagation is not a source of positions for a reader that acts in minutes or longer.
- **What this does not settle:** links that need judgment ("if A, then B is more likely"). No bot can enforce those, and price alone cannot measure them. They are tested forward through T3 and the reader.

## 3. What follows (registration §4)

- **Logical links are dropped as a source of positions.**
- **The graph's role narrows to judgment links,** tested forward (T3 and the reader).
- **The habit-question core of decision 26 is unaffected.**
