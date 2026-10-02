# P5: the safety framework on fresh events (result)

**Process.**
- Registered in `V19_FRAMEWORK_P5_prereg.md` (commit `54da60a`) before the frame was drawn. Scorer `v19_p5.py` (commit `7c4ede0`).
- 180 fresh events and 30 cold sessions, all passing V1's transcript audit.
- S06 and S28 wrote a 0% where 1 to 99 is required. Each was re-authored once, with the original kept in `bt/t2_pass5/superseded/`.
- Frozen by manifest `9cc99b41…` (commit `8ee4724`) before any score.
- Output: `v19/p5_result_t2_pass5.json`.

## 1. The registered result

| Declared statistic | Mean | 95% interval | Reading |
|---|---|---|---|
| 1. Framework-armed skill, by occasion | +20.8¢ | +12.8 to +27.0 | edge shown |
| 2. Framework-passed minus blocked, within A2 | +20.0¢ | +6.6 to +34.4 | edge shown |

**Secondaries (declaring nothing):**

| Set | Positions | Events | Occasions | Skill | Lost |
|---|---|---|---|---|---|
| A2, all | 127 | 59 | 51 | +8.8¢ (−1.7 to +16.7) | 19% |
| Framework | 51 | 17 | 16 | +20.8¢ | 6% |
| Blocked by the framework | 76 | 49 | 42 | +0.8¢ | 28% |
| Tier 1 (reader under 5%) | 34 | 9 | 9 | +23.6¢ | 0% |
| Tier 2 (5% to 10%) | 17 | 12 | 11 | +15.2¢ (−3.6 to +31.0) | 18% |
| Blocked by conviction alone | 29 | 23 | 21 | −2.2¢ | 28% |
| Blocked by timing alone | 16 | 11 | 10 | +17.9¢ (−0.3 to +34.2) | 13% |
| Blocked by shape alone | 6 | 2 | 2 | +14.3¢ | 17% |
| Framework, ladder tails | 34 | 5 | 5 | +21.9¢ | 0% |
| Framework, strict window (locks from 1 June) | 30 | 10 | 9 | +21.2¢ | 3% |

**Paper money** (last trade + 1¢):
- Framework, tiered: $4,250 staked, +$2,399 (+56% per dollar), 2 losing weeks of 13, worst occasion −$57.
- A2: $12,700 staked, +$4,591 (+36%), 5 losing weeks of 22, worst occasion −$400.

**Coverage.** The registration expected about 25 occasions. P5 gave 16, and 34 of the 51 framework positions sit in five crypto "price on a date" ladders (Solana and XRP).

## 2. Most of these positions were priced at numbers nobody could trade (found after scoring)

**The five ladders.**
- Each has 11 brackets, exactly one of which wins, and at the lock every bracket was priced 47¢ to 50¢. The YES prices sum to about 5.1, where a real market sums to about 1.
- A BT-T2 lock price is the last prices-history point within 48 hours (V1 A2). On a book with no real quotes, that point is the midpoint of an empty book, about 50¢.

**The rule** (`v19_price_check.py`, written after scoring, so exploratory). A position is flagged "suspect" when its event is:
- a partition whose YES prices sum to more than 1.3; or
- an event with every contract priced between 40¢ and 55¢.

Of the armed partition events in passes 1 to 5, 53 sum to between 0.9 and 1.3, 15 to between 1.3 and 1.6, and 51 to more than 1.6.

**Trade prints confirm it** (`v19/price_check_trades.json`; data-api trades from 48 hours before to 24 hours after the lock; 12 sampled from each group, seed 1):
- **Suspect positions:** 10 of 12 had trades near the lock. Their median NO price was 91¢ to 100¢, against backtest costs of 53¢ to 79¢. The real market already priced these NOs near certain.
- **Clean positions:** 9 of 12 had trades, mostly around the backtest cost (median NO 57¢ to 76¢ on the five busiest), with a few far off.

**How much of the evidence this touches** (A2-armed non-mention NOs, BT-T2 passes 1 to 5):

| Pass | 1 | 2 | 3 | 4 (P4) | 5 (P5) |
|---|---|---|---|---|---|
| Share on suspect prices | 47% | 64% | 62% | 54% | 57% |

## 3. A2 and the framework re-read on clean prices (exploratory; resampled by occasion; 95%)

| Set | Positions | Events | Skill | Money (hit − cost) | Lost |
|---|---|---|---|---|---|
| A2, all prices | 464 | 199 | +10.9¢ (+5.5 to +15.5) | +21.0¢ | 18% |
| A2, suspect prices | 267 | 69 | +15.8¢ (+11.5 to +19.2) | +29.2¢ | 8% |
| **A2, clean prices** | **197** | **130** | **+4.2¢ (−5.4 to +13.4)** | **+9.8¢ (+0.7 to +18.2)** | **30%** |
| A2 clean: partitions | 64 | 54 | −16.9¢ (−28.6 to −5.2) | −2.1¢ | 41% |
| A2 clean: terminal ladders | 42 | 32 | +23.8¢ (+6.5 to +39.0) | +22.4¢ | 17% |
| A2 clean: percent | 26 | 12 | +30.1¢ (+0.4 to +46.0) | +34.3¢ | 8% |
| A2 clean: touch | 62 | 29 | +1.8¢ | +3.6¢ | 39% |
| Framework clean, passes 1 to 4 (where it was found) | 30 | 26 | +26.3¢ (+17.6 to +34.2) | +32.5¢ | 3% |
| **Framework clean, P5 (out of sample)** | **8** | **7** | **+27.8¢ (−11.2 to +49.2)** | +28.7¢ | 12% |
| Blocked clean, P5 | 47 | 31 | −4.3¢ | +4.7¢ | 36% |

Skill's matched base still includes suspect-priced contracts on other events, so money (hit − cost) is the cleaner column.

## 4. Reading

- **The registered verdicts stand as computed, but they do not show a tradeable edge.**
  - 43 of the 51 framework positions are on suspect prices.
  - On clean prices, the framework has 8 out-of-sample positions: direction only.
- **The same flaw runs through the earlier backtest numbers:**
  - A2's +10¢ to +11.5¢;
  - the design simulation's +29.9% per dollar;
  - the losers note ("ladder tails are safe"; tier 1's loss rates);
  - the edge and capital table given to Rob.
- **On clean prices, A2 reads about +4¢ skill (direction only) and +10¢ money.**
  - It loses on partitions.
  - Ladders and percent questions carry what is left. That is a slice, not a finding.
- **BT-A is not yet checked.** Its draw required liquid events (volume of $100k or more, and 3 or more markets of $10k or more), but 33 of its 360 news events have YES prices summing above 2. It needs the same check.
- **The forward test is not affected on cost.** The sweep prices at the live ask and caps each stake by the depth within 2¢; W01's armed costs run 51¢ to 86¢. But W01 is mostly election partitions, the kind where clean-price A2 lost.

## 5. What follows

- **Under §5 of the registration, the framework would replace A2 in the paper book. That is held.** What it rests on is mostly untradeable prices. Rob decides.
- **Proposed, not done:** re-score every frozen backtest pass at prices that were really there (the trade prints near each lock, or a coherent book), registered before it runs. It needs no new sessions and reads the frozen files without changing them.
