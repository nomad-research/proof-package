# BT-T2 result, first pass: no evidence, graded format (2026-10-01)

Registration `BT_T2_prereg.md` (addenda A1 to A3). Script `bt_t2.py`. Result `bt/t2/result.json`.

**The run.**
- 173 events: all 83 eligible single-market events and 90 multi-market events drawn from 1,807.
- One lock per event, on the 7-day grid from 2026-07-01 (BT-A's window).
- 29 cold `claude-opus-5-5` sessions, every transcript audited. No re-authorings and no recall flags.
- Answers frozen by hash (manifest `2842bcd7…`, commit `d392715`) before any outcome was read.
- The sessions had the rules text and their own knowledge, which runs to 2026-06-30, and nothing else.

## Registered statistics (decision 7: declared at 5%)

| Statistic | n | Mean | 95% interval | P(positive) | Reading |
|---|---|---|---|---|---|
| **S1 skill:** bets where the view beats the all-in cost, minus contracts of the same class and cost | 674 positions, 148 events | **+0.041** | **+0.010 to +0.072** | 1.00 | **edge shown** |
| S1 money: hit minus all-in cost | 674 | +0.029 | −0.003 to +0.062 | 0.96 | direction only |
| S2 magnitude: session's central value closer than the market's (+1), farther (−1), tie (0) | 90 variables | −0.078 | −0.241 to +0.082 | 0.16 | direction only (21 closer, 28 farther, 41 ties) |

## How much to trust S1: it is real on the registered reading, and fragile (post-hoc checks, declaring nothing)

- **Concentrated.** Five of the 148 events carry about two-thirds of the total skill:
  - two "What will Trump say this week?" mention markets (27 and 15 positions);
  - three monthly or weekly stock touch ladders (HOOD, GOOGL, RKLB).

  **Without those five, skill is +0.015 (95% −0.011 to +0.041).** Weighting each event equally gives +0.034.
- **By cost.**
  - Contracts costing under 0.10, where most positions are (294), show nothing (−0.004).
  - The middle band, 0.30 to 0.70, shows the most: +0.098 (+0.007 to +0.181).
  - Favourites above 0.90 show +0.048 on 24 positions.
- **By lock month,** positive in each: July +0.048 (+0.004 to +0.096), August +0.025, September +0.039.
- **The scorer bug** (addendum A3): before the fix S1 was +0.031 (−0.007 to +0.068). The fix makes the levels and dates answers readable at all. It also raises S1 above the bar, so this result rests on a post-freeze correction, which is stated rather than smoothed over.

## What the other scores say

- **The session's probabilities are less accurate than the market's.** Log score −0.091 per contract (−0.134 to −0.055): edge shown absent. With no evidence after its cutoff, the model's distributions lose to prices, as BT-A predicted.
- **Calibration**, as stated chances against outcomes:
  - **Levels on terminal ladders are too narrow and set too low.** The 50% level was reached 82% of the time (22 variables) and the 25% level 40%.
  - **Touch ladders run the same way.** The high-side 10% level was reached 21% of the time; the low-side 50% level 36%.
  - **Percents are fairly calibrated in the middle.** 40–49% came true 50% of the time, 20–29% 31%, 0–9% 3%.
  - All of this is fixable by relabelling (decision 6) once there is history, and it does not touch S2.
- **Magnitude (S2) shows no skill.** Deadline binaries lean against the session (−0.18, 34 variables; "edge shown absent" within that breakdown, a hypothesis only). Without evidence, the model's timing of when things happen is worse than the market's.
- **The T0 baseline** (direction only, rungs by price): +0.037 skill (−0.068 to +0.143), direction only.

## Reading

1. **On the registered statistic, the first pass shows edge.** Where a no-evidence session's view differs enough from the price to cover costs, its side beat contracts of the same class and cost by about 4 cents per dollar position.
2. **It is not yet a result to lean on.** It is concentrated in a few events, it rests on a post-freeze scorer fix, and the money statistic does not clear 5%. Decision 5 requires confirmation on the strict window (the same window here, so no extra information) and on forward data. Decision 7 treats breakdowns as hypotheses. The concentration in mention markets and stock touch ladders is now one: test it on the next pass.
3. **The model is not better calibrated than the market.** Whatever edge exists is in where it disagrees, not in its probabilities overall. That fits decision 6: score bets and magnitude apart from calibration, and fix calibration by relabelling.
4. **Magnitude without evidence: no skill.** The evidence arm (v18 §5.9) is the test of whether reading adds anything.

## Next passes

- **The weekly walk-forward batch**, registered separately: new locks as weeks pass.
- **The evidence arm**, once the point-in-time bundle exists.
- **BT-A pass 2** (months by actual resolution) would allow locks from April, doubling the window.
- **Forward data:** T3 and V3 from mid-October.
