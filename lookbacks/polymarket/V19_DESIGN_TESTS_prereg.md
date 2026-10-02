# The v19 design-performance tests (registration, written before any of their data is built, run or computed)

Rob, 2026-10-02: "execute all tests require to gauge pre structured design performance". The design is `docs/NOMAD_V19_STARTING_POINT.md` as amended by decisions 12 to 19. This file registers every test that can run now. The forward tests run on their own registrations (§6).

**Integrity at commit.**
- P4's frame is not built.
- No A2 figure on BT-A's answers has been computed by anyone.
- R2's prompts are not built.
- §3 and §4 reuse passes 1 to 3, whose A2 figures are already known (the starting point, §6). They declare nothing.

**Declared statistics.** P4 (§1), A2 on BT-A (§2) and R2 (§5), each read at 95% by decision 7. If each had a 5% chance of a false positive and they were independent, the chance of at least one would be about 14%. Any result is read with that in mind.

## 1. P4: A2 on fresh events (declared)

**Frame.**
- `bt_t2.py --pass-dir t2_pass4 --seed 20261012 --per-stratum 150 --only-stratum multi`, with locks on the 7-day grid from 2026-04-01.
- **Excluded:** every event in BT-T2 passes 1 to 3, E3 passes 1 and 2, and BT-A passes 1 and 2.
- Locks from 2026-06-01 (the strict-gate window) are reported apart.

**Sessions.**
- 25 cold `claude-opus-5-5` subagents of this cloud session, 6 events each, with BT-T2's prompt and the paged instruction.
- Each is checked by V1's transcript audit with the line-number read check, and the pass is frozen by hash before any score.
- A session that writes a 0% where 1 to 99 is required is re-authored once, with the original kept (as passes 3 and R1).

**The declared statistic: A2 on non-mention events.**
- **Armed positions:** NO positions where the cost is 50¢ or more and the reader's midpoint is at least 20 points from the lock price.
- **Skill:** against same-side, same-class contracts on other events with cost within 0.05 (BT-T2's same-side skill).
- **Resampling:** by occasion (`V19_A2_prereg.md` addendum A3's definition), 95% interval.
- **Basis for power.** Passes 1 to 3 armed about 32 to 43 events each, at about 25¢ per occasion. At 40 occasions the lower bound clears zero if the mean is about 7.8¢ or more.

**Secondary.**
- E1 (every NO position, as passes 2 and 3);
- money;
- the NO positions A2 blocks;
- A2 by kind of market, by lock month, in the strict window, and including mention events;
- pooled with passes 1 to 3.

## 2. A2 on BT-A's answers: the rule unchanged, on a different pipeline (declared)

BT-A asked for one whole percent per contract, with no as-of date, priced 14 days before the end (`BT_A_prereg.md`). It is a different way of asking, so a transfer is not expected to be exact.

- **Data:** BT-A passes 1 and 2, events in months from April (both passes' clean windows). Every one of these events is fresh to A2: none was in BT-T2.
- **Positions:** as `edge_no_check.py`. Each contract's p is set against its price q at BT-A's pricing time, and the cost is q plus 1¢ plus the fee. A NO position is taken where 1 − p beats the cost.
- **Armed:** NO, cost 50¢ or more, and |p − q| of 0.20 or more.
- **Skill:** against same-side contracts of other BT-A events with cost within 0.05 (`edge_no_check.py`'s base). Resampled by event, 95%.

## 3. The rule tests (declaring nothing)

On passes 1 to 3 and P4. Each label rule is read as "what it blocks against what it lets through" (the starting point, §3 principle 8):

| Rule | How it is read |
|---|---|
| A3: the reader's record by kind | Walk-forward. A kind is blocked when the mean skill of its armed positions locked at least 14 days earlier is below zero (14 days: the sweep's horizon, by which time they have resolved). Shown again with at least 5 prior events required |
| A6: margin after cost | Armed positions by the reader's NO chance minus the NO cost: under 10 points, 10 to 20, and 20 or more |
| D1 proxy: already decided at the lock | Contracts priced at 3% or less, or 97% or more, at the lock. By construction A2 arms none, which is checked |
| Group exposure | Each occasion's worst case, and each kind's worst case over a 4-week window (the length of the crypto run, decision 14), as shares of the armed book |

## 4. The design end to end (declaring nothing)

- **The book:**
  - armed non-mention NOs from passes 1 to 4;
  - the mention book's armed positions (either side, 50¢ or more, 20 points or more) from E3 passes 1 and 2.
- **Staking:** $150 a position. That is the sweep's capacity reading; the backtests hold no depth.
- **What is reported**, ordered by lock week:
  - weekly paper P&L and the running total;
  - the largest drawdown, the worst week and the worst occasion;
  - return per dollar by kind;
  - the same with every fill 2¢ worse.
- **Prices:** last trade plus 1¢, as the backtests.

## 5. R2: asking "will this not happen" (declared)

**The change.**
- On BT-T2 pass 3's 25 prompts, half of the percent and partition events, chosen with seed 20261013, are asked in reverse.
  - **Percent:** "your chance that it does NOT resolve YES".
  - **Partition:** "your chance that it is NOT the one that resolves YES; these need not add to any total".
- They are answered under the key `p_not` and converted to YES as 100 − p_not.
- Every other event, and every scaled event, is asked as before.
- **Basis:** `EDGE_LEDGER.md` calibration fix 4b. The reader is overconfident when it says "likely", and R1 found its errors consistent rather than random.

**Sessions:** 25 cold sessions (reading D), audited, re-authoring and freeze as §1.

**The declared statistic.**
- On the reversed events only: A2's armed skill in reading D, minus the mean of the fresh unreversed readings B and C (R1) on the same events.
- Resampled by event, paired, 95%.

**Secondary.**
- The log score on the reversed contracts, D against B and C;
- how often YES happened where the reader said 85% to 95%, D against B and C;
- the unreversed events as a control. D against B and C should read about zero there.

## 6. Forward tests (their own registrations; advanced, not declared, here)

These are read only at their own looks. Here they are run on whatever has resolved, and where each stands is reported:
- A2 forward (`V19_A2_prereg.md`, looks at 40 and 80 occasions);
- the sweep's E1, E3 and E3b (`FORWARD_SWEEP_prereg.md`);
- the paper book (`v19_book.py`);
- fills (`v19_watch_books.py`, on Rob's machine).

## 7. Cost

About 50 sessions (P4 25, R2 25), at roughly 60,000 to 90,000 tokens each, as measured in R1.
