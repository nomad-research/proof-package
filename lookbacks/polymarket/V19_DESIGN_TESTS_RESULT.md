# The v19 design-performance tests: results (2026-10-02)

Registration `V19_DESIGN_TESTS_prereg.md` (commit `42b85d1`), written before any of these data were built or computed.
- Every session was a cold `claude-opus-5-5` subagent that passed V1's transcript audit.
- Every reading was frozen by hash before it was scored:
  - P4: `549eb6e7…`, commit `4cb070c`, no re-authorings;
  - R2: `6db3eeb5…`, one re-authoring, original kept.
- Scripts: `v19_p4.py`, `v19_bta.py`, `r2.py`, `v19_design_sim.py`. Outputs are in `v19/`.

## 1. The declared statistics

| Test | Question | Result | Reading |
|---|---|---|---|
| **P4** | Does A2 hold on 150 fresh events? | **+10.0¢** (−7.7 to +23.6); 101 positions, 37 events, 33 occasions | direction only |
| **A2 on BT-A** | Does the rule hold, unchanged, on a different way of asking and on fresh events? | **+11.5¢** (+3.3 to +19.1); 128 positions, 82 events | **edge shown** |
| **R2** | Does asking "will this not happen" change the reader's bets? | **+0.6¢** (+0.0 to +2.5) | direction only (`R2_FRAMING_RESULT.md`) |

There are three declared statistics, so the chance of at least one false positive is about 14%. One was shown.

## 2. A2 across every sample there is

| Sample | Armed skill | What kind of evidence |
|---|---|---|
| BT-T2 passes 1 to 3, where A2 was found | +13.5¢ (+8.0 to +18.4), 107 events | After the fact |
| Two fresh readings of pass 3 (R1) | +17.9¢ and +14.5¢ | Fresh readings, the same events |
| **BT-A passes 1 and 2** | **+11.5¢ (+3.3 to +19.1), 82 events** | **Registered; fresh events; a different pipeline** |
| **P4** | **+10.0¢ (−7.7 to +23.6), 37 events** | **Registered; fresh events** |
| All four BT-T2 passes pooled | +11.6¢ (+5.3 to +17.2), 140 events | After the fact (pooling not registered) |
| NO positions A2 blocks, all four passes | +0.4¢ (1,162 positions) | |
| NO positions A2 blocks, P4 | −0.8¢ (−6.7 to +4.8) | |

- **Away from the data it was found on, A2 reads about +10¢ to +11.5¢ a position**, against +13.5¢ where it was found.
- **The selection holds everywhere.** What A2 blocks earns about nothing, and what it arms earns about 10¢.
- **In P4 every NO position together (E1) was only +1.7¢ (−4.3 to +6.8).** The edge is in the armed subset, not in NO bets generally.

## 3. The design end to end (declaring nothing)

$150 a position. Prices are the last trade plus 1¢. Ordered by lock week. Money includes any market lean: in April to June every NO earned about +3¢.

| | P4 alone (out of sample) | All four passes |
|---|---|---|
| E1 book: positions / events | 101 / 37 | 337 / 140 |
| Staked | $15,150 | $50,550 |
| Return per dollar | **+29.9%** | +35.2% |
| The same, every fill 2¢ worse | +25.7% | +30.8% |
| Hit rate | 78% | 83% |
| Losing weeks | 6 of 20 | 2 of 27 |
| Worst week / largest drawdown | −$900 / −$900 | −$758 / −$758 |
| With the mention book (E3 passes 1 and 2) | +40.5% | +39.2% |

**By kind,** return per dollar, in P4 and across all four passes:

| Kind | P4 | All four passes |
|---|---|---|
| Crypto price | +64.9% | +54.4% |
| Post counts | +35.3% | +16.2% |
| "Other" | +43.0% | +43.4% |
| Stocks and earnings | −10.2% | +14.1% |
| Macro and commodities | −5.9% | −0.5% |

## 4. The rules

**A3 (block a kind on its own record) does not earn its place.**
- On passes 1 to 3 it looked useful: what it blocked earned −15¢.
- With P4 added, what it blocks earns more than what it lets through:

  | | Blocked | Passed |
  |---|---|---|
  | All four passes | +18.3¢ | +11.2¢ |
  | P4 alone | +39.5¢ | +3.2¢ |

- Post counts, A2's losing kind on passes 1 to 3 (−9.5¢), earned +16.7¢ in P4.
- Records by kind are too noisy to gate on, which agrees with Rob's preference for general edge. A3 stays a label (decision 13).

**A6 (margin after cost).** Skill rises with the size of the reader's disagreement when all four passes are pooled, but not in P4 alone:

| Disagreement | All four passes | P4 |
|---|---|---|
| 20 to 30 points | +5.1¢ | +6.0¢ |
| 30 to 40 points | +17.4¢ | +21.6¢ |
| 40 points or more | +20.0¢ | +4.3¢ |

A higher bar is a hypothesis for the shadow book, registered before data. A2's thresholds are not tuned after looking.

**D1 (news disarm), checked through its proxy.** A2 arms nothing the market treats as decided. That holds by construction.

**Group exposure: one occasion behaves like one bet.**
- P4's worst result was a single interest-rates occasion: six positions lost together, −$900. It was the out-of-sample book's worst week.
- The largest occasion held 18 positions ($2,700).
- In P4 one occasion was often the whole week's armed book.
- This is the correlation Rob asked to find. It supports the occasion caps that bind at real money (decision 13), sized by Rob.

## 5. The reader

- R1: independent readings arm 82% to 87% of the same bets.
- R2: reversed wording arms the same bets.

The reader is stable. Neither averaging nor reframing is adopted.

## 6. Forward (as of 2026-10-02)

| Test | Where it stands |
|---|---|
| A2 forward (`V19_A2_prereg.md`) | 0 occasions resolved. W01's 24 armed positions (5 occasions) settle from 4 October, mostly on Brazil's election. Direction read at 40 occasions; confirmation at 80 (late November to late January) |
| The sweep's E1, E3 and E3b | W01 resolving. E1's first look about mid-November, E3's about December |
| Paper book | 24 armed positions, $2,388, none settled |
| Fills | The watcher runs on Rob's machine; `fills.json` is due weekly |

## 7. What this says about the design

1. **The arming rule (A2) is the design's working core.**
   - It held in direction on every independent sample.
   - It was confirmed on one: BT-A, fresh events asked another way.
   - Plan on about +10¢ a position of skill, not the +13.5¢ it was found at.
2. **Its forward confirmation is still the gate (decision 17).** Neither backtest result replaces it.
3. **The main risk is correlation within an occasion,** now seen out of sample. Occasion caps are needed before real money.
4. **The reader needs no change.** Edge rules by kind (A3) should not bind.
