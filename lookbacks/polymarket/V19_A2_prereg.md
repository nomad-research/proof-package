# A2 forward: the arming rule on the forward sweep (registration, written before any sweep outcome is read)

Source: `docs/NOMAD_V19_STARTING_POINT.md` §5 (rule A2) and §6, adopted as the starting point in decision 12. Scorer: `v19_a2.py`.

This reads the forward sweep's frozen batches and changes nothing in them. The sweep's registration, its scorer `fwd_sweep.py`, its batches, and its declared statistics (E1, E3, E3b) and their looks are untouched.

**Integrity at commit.**
- No sweep result file exists in the repository.
- `fwd_sweep.py score` has not been run in this session, and the builder has read no W01 resolution.
- Nothing in the repository shows it has been run anywhere else. Rob to confirm for his machine.
- The pace figure in §3 comes from W01's frozen answers and lock asks only, scored against made-up outcomes to exercise the code. No real outcome was read.

## 1. The claim

On events nobody knows the outcome of, NO positions armed by A2 beat other NO contracts of the same session format and the same cost.

## 2. Which positions are armed

A position is armed when it is a sweep NO position (sweep §2: the session's chance of NO, one minus the upper bound of its YES chance, is above NO's all-in cost at the lock ask) and both of these hold:
- **The price condition.** NO's all-in cost (the lock ask plus the taker fee, as the sweep computes it) is **0.50 or more**.
- **The disagreement condition.** The reader is **at least 0.20 surer of NO** than the market: q − m ≥ 0.20.
  - m is the midpoint of the session's chance range for YES.
  - q is the midpoint of the two lock asks, (YES ask + 1 − NO ask) / 2. The sweep already uses this as the market's price for its log score.
- A position without both asks has no q and is not armed. The count is reported.

**How this differs from the backtest.** There the disagreement was measured against the last trade, and the cost was the last trade plus 1¢. Forward, the market's price is the ask midpoint read at the lock and the cost is the actual ask. That is the nearest forward equivalent.

## 3. The statistic, and when it is read

- **Skill: the sweep's E1 skill, unchanged.** (hit − cost) minus the mean (hit − cost) of the NO side of every other resolved sweep contract that counts and has:
  - the same session format;
  - a NO cost within 0.05;
  - a different event.
- **Counted positions:** only those the sweep counts (its addendum A1, the volume rule).
- **Resampling:** by event, 4,000 draws, seed 20261001.
- **Looks:** at **40 and 80** resolved events with an armed NO position. Each is read with a 97.5% interval:
  - **confirmed** if the interval is above zero;
  - **killed** if it is below zero;
  - **carried** otherwise.

  After the second look the statistic keeps running as a ledger without declaring.
- **Basis for 40 and 80.**
  - On the three BT-T2 passes the armed positions read +13.5¢ (+8.0 to +18.4) on 107 events. That is a standard error of about 2.65¢, so about 27¢ per event.
  - With a 97.5% interval, the lower bound clears zero at **40 events if the forward mean is 9.7¢ or more**. The armed rule without its top five events read +10.3¢.
  - At **80 events it clears if the mean is 6.9¢ or more**. Without its top ten events the rule read +7.0¢.
- **Expected pace.** W01 holds 24 armed NO positions on 20 events if every contract resolves; fewer will. At about 20 armed events a batch:
  - the first look comes once about two batches have resolved (late October);
  - the second once about four have (early to mid November).

  Both come before E1's first look.

## 4. Several statistics on one sample

The sweep now declares four statistics: E1, E3, E3b and A2. If each had a 5% chance of a false confirmation and they were independent, the chance of at least one would be about 19%. They overlap, so it is lower.

An A2 confirmation is read with that in mind. The design does not lean on it until the next batch's armed positions point the same way, the same rule as sweep addendum A3.

## 5. Secondary (declaring nothing)

- **A2 without mention events.** Decision 12 keeps this as the E1 book's own reading: the E1 book is non-mention events.
- **The positions A2 blocks:** every counted NO position it does not arm, read with the same skill. This is the starting point's §3 principle 8: a rule stays only while what it lets through beats what it blocks.
- **For the armed positions:**
  - money (hit − cost), hit rate and mean cost;
  - money if each were sized at the lesser of $150 and the dollars on offer within 2¢ of the ask (the sweep's capacity reading).
- **NO priced 50¢ or more, by the size of the disagreement:** 10, 15, 20, 25, 30 and 40 points.
- **By batch.**
- **Mention markets, either side,** scored against every side of other mention contracts (E3b's comparison):
  - a disagreement of 20 points or more at a cost of 50¢ or more (the starting point's mention version of A2);
  - the same disagreement at any cost;
  - the picks this blocks.

  The any-cost version is reported because of the two E3 backtests. Armed at 50¢ or more, the picks read +24.2¢ (+17.4 to +29.7, 65 events). The picks this blocks still earned +8.4¢ (+5.4 to +11.5), and 20-point disagreements under 50¢ earned +15.4¢. So the 50¢ floor may be an E1 finding that does not carry to mention markets (`v19_a2.py backtest`).
- **The count of NO positions without both asks.**

## 6. What this does not change

- The sweep (`FORWARD_SWEEP_prereg.md` and its addenda), its batches and its scorer.
- T3, V1, V1b, V3 and T0.

Each keeps its own registration and reading.

## Addendum A1 (2026-10-01, decision 13, before any sweep outcome is read)

Rob's checks on the registration. Where this addendum and §1 to §5 differ, this addendum holds. `v19_a2.py` implements it.

**1. Declared on the E1 book: non-mention events only.**
- **The change.** The declared statistic now counts armed NO positions on non-mention events only. Mention events are E3's population (decision 12).
- **Why.** From W02 the sweep draws every mention event, about 5 to 10 a batch. On the E3 backtests about 3 armed NOs per mention event (180 on 56 events) read +16.6¢. So mention events could be about a quarter of A2's armed events, and their positions would count in both A2's and E3's declared statistics.
- **What it costs.** On the BT-T2 passes, armed NOs on non-mention events read:

  | | Skill |
  |---|---|
  | All | +12.3¢ (+6.5 to +17.3), 103 events |
  | Without the top five events | +8.7¢ |
  | Without the top ten events | +5.2¢ (−1.1 to +11.2) |

  At 80 events the lower bound of a 97.5% interval clears zero if the forward mean is about 7.0¢ or more (about 28¢ per event). That sits between the two cuts, so a confirmation is less certain than §3 suggested.
- A2 including mention events (the starting point's §6 definition) is reported as a secondary.

**2. Two looks, with different jobs.**
- **At 40 events: a direction read.** It reports the effect, its 97.5% interval and the share of resamples above zero. **It confirms nothing.**
- **At 80 events: the confirmation.** Confirmed if the 97.5% interval is above zero, killed if below, carried otherwise.
- **A kill can be read at either look,** if the 97.5% interval lies wholly below zero. Stopping a losing rule early adds no chance of a false confirmation.
- The second look is the only one that can confirm, so it is not a second chance at the first.
- The 97.5% level is kept for the confirmation. Moving to 95% now that only one look confirms would loosen a threshold (the starting point, §3 principle 7).

**3. The bars are on skill only.**
- **Money is secondary.** Forward, cost is the actual ask plus the fee, and the market's price is the ask midpoint. In the backtest both came from the last trade plus 1¢.
  - Forward money will read lower for that reason alone.
  - The backtest's +23.1¢ is not a forward benchmark for anything.
- **The armed set near the 50¢ line may shift** under the new price definition. Two secondaries show it:
  - armed positions costing 50¢ to 55¢;
  - non-mention NOs with a 20-point disagreement costing 45¢ to 50¢, which the line leaves out.

**4. Weeks, not only events.** About 20 armed events a week share one week's shocks, so two weeks are two tides, not 40 independent events. Reported beside the declared statistic, declaring nothing:
- the statistic by week of resolution (the calendar week the contract resolved; the batch where that is missing) and by batch;
- the statistic resampled by week instead of by event;
- the statistic without its best week.

A confirmation that does not survive losing its best week is read as one tide's result. The design does not lean on it until the next batch agrees (§4).

**5. The mention secondary stays apart from E3.**
- It declares nothing.
- It is never pooled with E3's or E3b's registered statistics. A forward E3 or E3b result is never cited for the floor question, nor this secondary for E3 or E3b.
- Its no-floor version was found by looking at backtests, so it is a hypothesis.

## Addendum A2 (2026-10-02, decision 14, before any sweep outcome is read)

Rob has confirmed that `fwd_sweep.py score` has not been run on his machine. No sweep outcome has been read anywhere, so this registration and addendum A1 stand as clean.

**The halfway look (40 events) can neither confirm nor kill.** This replaces addendum A1's "a kill can be read at either look".
- **Why.** Rob: "No but it should be grounds for revision." Forty events is about two weeks, which can be one unlucky stretch. On paper, carrying on costs nothing.
- **What happens at the halfway look.**
  - It is always reviewed.
  - **If it points the wrong way** (the average skill of the armed positions is below zero), a revised rule is drafted. Zero is the boundary because that is what "the wrong way" means; no other threshold is set.
- **How a revision is handled, so that it cannot become a second chance at this test:**
  - The registered rule keeps running, unchanged, to its final look at 80 events, and is read there as §3 and addendum A1 say.
  - A revised rule is a new rule. It is written down and registered before the batches it is scored on, and scored only on batches frozen after its registration.
  - It has seen the forward data it was drafted from, so that data can never count as its evidence.
  - It runs beside the registered rule in the shadow book. It does not replace it.
- **The final look (80 events) is the only look that can confirm or kill.**

## Addendum A3 (2026-10-02, decision 16, before any sweep outcome is read)

**Events that share one occasion count as one unit.**
- Rob: "lets go with yes", to the question whether events sharing one occasion should count as a single piece of evidence when judging how sure the test is.
- **Why.** 54 of W01's 102 events are Brazil's 4 October election. Resampled by event, its races would count as 54 independent pieces of evidence, though they share one national swing.

**What one occasion is** (`v19_a2.py`: `subject_of`, `assign_occasions`; fixed before any outcome is read).
- **The same kind of market,** from the fixed list of kinds of addendum A2.
- **About the same place or asset:**

  | Kind | Subject |
  |---|---|
  | Elections | The country, from the event's tags; US primaries and US elections count as "united-states" |
  | Crypto | The coin named in the title |
  | Stocks and earnings | The ticker in the title |
  | Post counts | The account named in the title |
  | Macro and commodities | The series: the Fed, inflation, growth, jobs, oil, gold, rates |

  A kind with no such subject (deadlines, weather, other), or an event whose subject cannot be read, is its own occasion.
- **Settling the same week:** events with the same subject whose scheduled ends fall within 7 days of the occasion's first scheduled end. A calendar week was tried first and split Brazil's Sunday vote in two, because some of its markets end on the Monday.

**What changes in the test.**
- **The declared statistic is resampled by occasion,** not by event. Everything else in §3 and addenda A1 and A2 stands.
- **The looks count occasions:** a direction read at 40 resolved occasions with an armed non-mention NO position, the confirmation at 80.
  - Counting occasions is never looser than counting events, since an occasion holds one event or more.
  - On the backtest, 103 armed events make 87 occasions, at about 25¢ per occasion. At 40 occasions the 97.5% lower bound clears zero if the mean is 8.8¢ or more. At 80 it clears at 6.2¢. So 40 and 80 are kept.
- **The statistic resampled by event,** and the occasions holding more than one event, are reported as secondaries.

**The cost: the test takes longer.**
- W01's 24 armed positions sit on 20 events but only 5 occasions: 13 of the events are Brazil's election and 4 are Peru's.
- If later batches give 5 to 10 armed occasions each, the final look at 80 comes after about 8 to 16 batches: from late November to late January. Before this change it was early to mid November.
