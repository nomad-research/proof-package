# R2 result: asking "will this not happen" (2026-10-02)

Registration `V19_DESIGN_TESTS_prereg.md` §5 (commit `42b85d1`). Prompts commit `6a0f819`:
- 35 of pass 3's 70 percent and partition events were asked in reverse, with seed 20261013;
- every other block is identical to pass 3, which was checked when the prompts were built.

Reading D is 25 cold sessions, all passing V1's transcript audit on `claude-opus-5-5`. It was frozen before any score (manifest `6db3eeb5…`). S18 wrote a 0% and was re-authored once, with the original kept in `superseded/`. Readings B and C are R1's fresh, unreversed readings of the same prompts.

## The registered statistic (reversed events only)

| | Mean | 95% interval | Share above 0 | Reading |
|---|---|---|---|---|
| **A2 armed skill, D minus the mean of B and C** | **+0.6¢** | +0.0 to +2.5 | 0.90 | **direction only** |

## Secondary

| | Reversed events (35) | Control: the same prompts' unreversed events |
|---|---|---|
| Armed positions / events, B · C · D | 30 / 9 · 28 / 9 · 30 / 9 | 82 / 31 · 90 / 35 · 87 / 34 |
| Armed skill, B · C · D | +16.5¢ · +15.3¢ · +16.5¢ | +18.5¢ · +14.2¢ · +17.7¢ |
| Armed skill, D minus mean(B, C) | +0.6¢ (+0.0 to +2.5) | +1.4¢ (−3.3 to +6.6) |
| Log score against price, D minus mean(B, C) | −0.005 (−0.014 to +0.003) | +0.002 (−0.007 to +0.012) |
| Where the reader said 85% to 95%, how often YES happened (B · C · D) | 1 of 1 · 1 of 1 · 1 of 2 | 80% (n 15) · 69% (n 16) · 79% (n 14) |

## Reading

1. **Asking the question in reverse leaves the arming rule's bets almost unchanged.**
   - On the reversed events, reading D arms the same number of positions on the same events with the same skill as the unreversed readings.
   - So A2's bets do not depend on the framing.
   - That is evidence of robustness, and nothing to adopt: the framing is not changed.
2. **It does not help the log score.** −0.005, spanning zero.
3. **The overconfidence fix cannot be judged here.**
   - The reversed events held only 1 to 2 contracts the reader called 85% to 95% likely, too few to read.
   - The control events show the known pattern: "85% to 95%" came true 69% to 80% of the time.
   - A calibration test needs events chosen for high calls, a different design. Calibration stays as the ledger says: within a pipeline, walk-forward Platt, and never touching A2's selection.
