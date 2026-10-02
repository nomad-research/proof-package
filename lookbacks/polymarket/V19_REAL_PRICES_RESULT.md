# The backtests at real prices (result)

**Process.**
- Registered in `V19_REAL_PRICES_prereg.md` (commit `2564bb7`; occasion amendment `22c43de`) before any trade print was pulled.
- Prints were pulled for 11,747 contracts across nine passes (`bt/real_prices/`, commit `15af0c0`).
- Scored by `v19_real_prices.py score` into `v19/real_prices_result.json`. No frozen file was written.

**The real price** is a contract's last trade print at or before the lock, within 48 hours. Contracts with no print in that window are dropped, from positions and from the matched bases.

## 1. The declared statistics (95%, resampled by occasion)

| | Positions | Events | Occasions | Mean | 95% interval | Reading |
|---|---|---|---|---|---|---|
| **1. E1:** every NO position, BT-T2 passes 1 to 5 | 1,324 | 580 | 362 | **+1.1¢** | −1.6 to +3.8 | **direction only** |
| **2. A2:** armed NOs, passes 4 and 5 | 87 | 58 | 52 | **+4.0¢** | −9.2 to +15.8 | **direction only** |
| **3. E3b:** mention picks, both sides, mention passes 1 and 2 | 1,035 | 79 | 79 | **+8.1¢** | +5.1 to +11.3 | **shown at real prices** |

Three declared statistics, so the chance of at least one false positive is about 14%.

## 2. Secondary (declaring nothing)

**Coverage.**
- 65% to 83% of contracts have a real price, by pass:
  - BT-T2: 71%, 77%, 79%, 82%, 77%;
  - mention passes: 65%, 83%;
  - BT-A from April: 73%.
- **A2's original 464 armed positions:**
  - 214 had no trade at all near the lock;
  - 86 stay armed at real prices;
  - the rest are no longer A2 positions once the real price replaces the empty-book midpoint.

**E1 and A2.**

| | Positions | Events | Mean | 95% interval |
|---|---|---|---|---|
| E1, money (hit − cost) | 1,324 | 580 | +3.1¢ | +0.4 to +5.8 |
| E1, non-mention events | 1,293 | 576 | +1.2¢ | −1.7 to +4.0 |
| A2, passes 1 to 5 | 159 | 120 | +3.8¢ | −5.3 to +12.2 |
| A2, passes 1 to 5, money | 159 | 120 | +7.4¢ | −1.7 to +15.9 |
| A2, passes 4 and 5, money | 87 | 58 | +12.9¢ | +0.0 to +24.7 |
| **A2 on BT-A** (the liquid draw: event volume of $100k or more) | 57 | 48 | **+13.4¢** | **+1.8 to +25.5** |
| A2 on BT-A, money | 57 | 48 | +13.3¢ | +1.3 to +24.0 |

**By kind (skill).**

| Kind | E1 | A2, passes 1 to 5 |
|---|---|---|
| Pick-the-winner (partition) | +0.3¢ (−2.6 to +3.3), 297 events | +6.7¢ (−3.4 to +16.1), 69 events |
| Everything else | +1.7¢ (−2.6 to +6.0), 283 events | +0.1¢ (−14.4 to +15.2), 51 events |
| Percent | +8.2¢ (−0.3 to +17.4) | +17.1¢, 8 events |
| Terminal ladders | −0.8¢ | −1.2¢ |
| Touch | +2.4¢ | −4.2¢ |

**Mention.** E3's own registered statistic (NO picks against mention NOs at the same price) reads +6.0¢ (+0.9 to +11.4).

**Sensitivities.**

| | E1 | A2, passes 4 and 5 | E3b |
|---|---|---|---|
| Last print (declared) | +1.1¢ (−1.6 to +3.8) | +4.0¢ (−9.2 to +15.8) | +8.1¢ (+5.1 to +11.3) |
| Volume-weighted price of the window | +0.3¢ (−2.7 to +3.1) | +7.2¢ (−10.1 to +22.0) | +9.5¢ (+6.3 to +12.8) |
| At least $100 traded in the window | +1.1¢ (−2.3 to +4.3) | +4.6¢ (−12.9 to +19.2) | **+3.1¢ (−1.4 to +7.7)** |

## 3. Reading

- **E1 does not survive real prices on the backtests.**
  - The reader's NOs beat same-price NOs by about 1¢, direction only.
  - NOs as a whole earn about 3¢ in money, which is the market's habit rather than the reader's choice.
  - Under §4 of the registration, the forward sweep (live asks) is the remaining evidence for E1, and what the reader is for is reopened with Rob.
- **A2 reads +4¢ on its fresh passes, direction only.**
  - Its one positive sign is on BT-A, the draw that required liquid events: +13.4¢ (+1.8 to +25.5) on 57 positions. BT-A's original confirmation (+11.5¢) holds at real prices, because its prices were mostly real to begin with.
  - It is a secondary, on 48 events, so it is a lead, not a finding.
- **The mention edge survives: E3b is shown at real prices, +8.1¢ (+5.1 to +11.3).**
  - It weakens to +3.1¢ (−1.4 to +7.7), direction only, where at least $100 traded near the lock.
  - The edge sits mostly in thin mention markets, which matches the depth seen before (books of about $60).
- **A correction to decision 21's exploratory reading.** Dropping whole suspect events suggested A2 lost on pick-the-winner events (−16.9¢). At real prices, A2 on pick-the-winner events reads +6.7¢, direction only, against +0.1¢ elsewhere. That warning for W01 does not hold.
- **Not settled here.** Cost is the last print plus 1¢, not the ask a buyer would have met. In a thin book the ask can sit above the last print, and the forward test's live asks settle that.

## 4. What follows (registration §4)

- **E1:** the backtest evidence does not survive real prices. The forward E1 and A2 tests, priced at live asks, are the evidence that remains. What the reader is for is reopened with Rob.
- **E3b:** the mention edge stands on the backtests at about 8¢ a pick, with capacity as the open question.
- **New backtest passes** price at the last print in the window, and a written 0% counts as 1%. Frozen passes are unchanged.
