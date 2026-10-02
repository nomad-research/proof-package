# R1 result: does averaging independent readings sharpen the reader? (2026-10-02)

Registration `R1_AVERAGING_prereg.md` (commit `4c4199a`). Readings B and C are 25 cold sessions each on BT-T2 pass 3's own prompts. Each was frozen before any R1 score was computed:
- B: manifest `800690ac…`;
- C: manifest `486f136d…`, commit `456a2ba`.

All 50 passed V1's transcript audit on `claude-opus-5-5`. Three wrote a 0% where 1 to 99 is required and were re-authored once, with the originals kept in `superseded/`: B S07, B S24 and C S25. No recall flags.

**One ingest error, recorded.** My first readiness check was wrong. The word it looked for appears in every transcript, so 11 of reading B's sessions were ingested while still running and marked "handed back nothing". Those records were deleted unseen and each session ingested again after its completion notice. No answer was read or changed by the error.

## The registered statistic

| | Mean | 95% interval | Share above 0 | Reading |
|---|---|---|---|---|
| **Armed skill of avg(B, C) minus the mean of B alone and C alone** | **+0.9¢** | −1.3 to +3.4 | 0.79 | **direction only** |

## Each reading (secondary)

| Reading | Armed (positions / events) | Armed skill | Armed money | All NO skill | Log score against price |
|---|---|---|---|---|---|
| A (frozen pass 3) | 108 / 43 | +15.1¢ (+7.4 to +21.6) | +28.0¢ | +4.9¢ | −0.064 |
| **B (fresh)** | 112 / 40 | **+17.9¢ (+11.3 to +23.4)** | +30.6¢ | +4.6¢ | −0.062 |
| **C (fresh)** | 118 / 44 | **+14.5¢ (+7.2 to +20.4)** | +26.6¢ | +3.9¢ | −0.071 |
| avg(B, C) | 114 / 42 | +17.1¢ (+10.3 to +22.5) | +29.8¢ | +4.6¢ | −0.065 |
| avg(A, B, C) | 113 / 43 | +16.1¢ (+9.2 to +22.0) | +28.8¢ | +4.1¢ | −0.064 |

**Agreement between readings (shared share of armed positions):** B and C 0.87, A and B 0.86, A and C 0.82.

## Reading

1. **Averaging does not sharpen the reader enough to matter.** It adds +0.9¢ a position with an interval spanning zero, and the log score does not improve. As registered, the reader stays single. No change is proposed, so §5's repeat on pass 2 (for power, "before any change") is not needed.
2. **The reason is that the reader is consistent.**
   - Fresh, independent sessions on the same questions arm 82% to 87% of the same positions.
   - There is little reading-to-reading noise for an average to cancel.
   - One reading per question is enough, which keeps the reading cost where it is.
3. **The arming rule holds on readings it was not fitted to.** A2's thresholds were chosen on reading A. On fresh readings of the same questions it reads +17.9¢ and +14.5¢, both with intervals well above zero.
   - So A2's backtest edge is not the product of one lucky draw of the reader.
   - It does not show the edge holds on new events: the outcomes and prices are shared with reading A. That is the forward test's job (`V19_A2_prereg.md`).
4. **The "will this not happen" framing (R2) is the remaining elicitation test.** The consistency found here suggests the reader's errors are systematic rather than random. A change in how the question is asked is more likely to move them than repetition is.
