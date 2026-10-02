# P5: the safety framework on fresh events (registration, written before the frame is drawn)

Rob, 2026-10-02: "run the safety framework on a fresh pass". The framework is the "exclude the YESes" layer of `V19_LOSERS_NOTE.md`, fixed here exactly as it stood when this file was written. Nothing in it is tuned after this commit. Scorer: `v19_p5.py`.

## 1. The framework (fixed)

A position is armed by the framework when it is an A2 position and three conditions hold.

**A2 position:** a NO position on a non-mention event, costing 50¢ or more, with the reader's midpoint at least 20 points from the lock price.

| Condition | Rule | Based on |
|---|---|---|
| **Conviction** | The reader's YES midpoint for the contract is under 10%. Tier 1 is under 5%; tier 2 is 5% to 10% | Under 5% held on passes 1 to 3, P4 and BT-A (0% to 7% lost). BT-A's calibration: "under 5%" happened 1% of the time |
| **Timing** | The event's last scheduled end is at least 3 days after the lock | Positions ending within 3 days lost 27% (passes 1 to 3) and 35% (P4) |
| **Shape** | Not a touch question ("will it reach X" within a period) | Touch questions lost 59% in P4 |

The same definitions as `v19_losers.py`:
- the reader's midpoint is `contract_chance`'s (lo + hi) / 2;
- days are `scheduled_end(event) − lock`;
- a touch question is BT-T2's session kind `touch`.

## 2. Data and sessions

**Frame.**
- `bt_t2.py --pass-dir t2_pass5 --seed 20261014 --per-stratum 180 --only-stratum multi`, with locks on the 7-day grid from 2026-04-01.
- **Excluded:** every event in BT-T2 passes 1 to 4, E3 passes 1 and 2, and BT-A passes 1 and 2.
- **180 events, against P4's 150.** The framework arms about a quarter as many positions per event as A2 (24.6 against 54.1 per 100 events in passes 1 to 4). 180 events gives about 44 framework positions on about 25 occasions.

**Sessions.**
- 30 cold `claude-opus-5-5` subagents of this cloud session, with BT-T2's prompt and the paged instruction.
- V1's transcript audit with the line-number read check; frozen by hash before any score.
- A session that writes a 0% where 1 to 99 is required is re-authored once, with the original kept.

## 3. The declared statistics (95%, decision 7)

1. **Framework-armed skill.** BT-T2's same-side skill (against same-side, same-class contracts on other events within 0.05), resampled by occasion (`V19_A2_prereg.md` addendum A3).
   - Edge shown if the interval is above zero; shown absent if below; direction only otherwise.
2. **What the framework lets through against what it blocks, within A2.** The mean skill of framework-armed positions minus that of A2 positions the framework blocks, resampled jointly by occasion.
   - Above zero: the framework earns its place (the starting point's §3 principle 8).
   - Below zero: it does not.
   - Otherwise: direction only.

Two declared statistics: if each had a 5% chance of a false positive and they were independent, the chance of at least one would be about 10%.

## 4. Secondary (declaring nothing)

- **Loss rates:** framework-armed, A2-armed, and the blocked positions.
- **Tier 1 alone and tier 2 alone:** skill and loss rate.
- **Each condition's blocks on their own,** among A2 positions: conviction, timing and shape.
- **Money on paper:** $100 a position (tier 2 at $50), prices at the last trade plus 1¢. Weekly paper P&L, worst week and worst occasion, framework against A2.
- **For comparison:** A2's own skill on P5, with ladder tails (5 or more framework-armed positions in one event) and the strict window (locks from 2026-06-01) reported apart.

## 5. What follows

- **If the framework earns its place (statistic 2 above zero)** and keeps an edge (statistic 1), it replaces A2 as the armed book's rule in the paper book. A forward registration follows before it is used on the sweep.
- **If it shows edge but not over what it blocks,** A2 stays, and the framework's conditions stay labels.
- **If it fails,** the conditions stay labels and the losers note is recorded as not replicating.

## 6. Cost

About 30 sessions at roughly 60,000 to 90,000 tokens each (P4's measured range).
