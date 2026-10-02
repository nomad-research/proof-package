# Decisions, October 2026

Decisions settled in design discussion, appended in order. Each entry gives the decision, Rob's words, the evidence it rests on, and what is still open.

## 1. The firewall applies to tests, not to design work (2026-10-01)

- **Decision.** The contamination firewall governs test sessions: authoring, locking, and anything a test's answers depend on. Design discussion, where the builder reads finished results, resolutions and prices to decide what the system should be, is outside it.
- **Rob's words.** "The firewall should only apply to tests no system design."
- **Evidence.**
  - The firewall exists to keep a session's answers free of knowledge from after its lock. A design session authors no answers, so nothing it reads can contaminate a result.
  - Design work needs the resolved data. Topic 1 below could not be discussed without reading T0's claim rows, their resolutions and their lock prices.
- **Still open.**
  - **The guard does not implement this yet.** `firewall/guard16.py` takes its phase from `state/phase.json`, which the parked v16 harness writes. It currently reads R16-001, `live`, so everything is allowed. With no round in play, the guard falls back to the blind-run policy of `firewall/guard.py`, which denies WebSearch with no exception. Nothing in the phase file knows when a Polymarket test (T3 authoring, V3 scoring, a BT run) is in progress.
  - **What marks a session as a test**, so the guard knows when to close.
  - **Whether a session that has done design work may later author or lock test answers.** This session has read T0's resolutions and prices.
  - **On this machine the hook cannot run at all.** Its command is `python3`, which resolves to the Microsoft Store stub.

## 2. T3 asks for magnitude in world units (2026-10-01)

Register C3. Question 1 of topic 1.

- **Decision.** T3's packet asks sessions to state magnitude in world units: a measure that can be checked after the event without reference to any market.
  - A date for a timing claim: "signed by 15 November".
  - A level for a size claim: "crude above $95 on 31 December", "at least 12 seats".
  - The tier words (mild, moderate, severe) are not used in T3. T3 is therefore a new test of magnitude, not a replication of T0.
- **Rob's words.** "World units are worth a shot."
- **Evidence.** All from T0 (`lookbacks/polymarket/T0_RESULT.md`, `t0_report.json`, and the V1/V1b `answer_1b.json` files). The split is post-hoc, not registered.
  - Triggered tier claims held 8 of 9 at a mean lock price of 0.43; named-contract claims held 2 of 5 at 0.55.
  - **The evidence is about timing.** Six or seven of the nine tier claims are "by date" claims. One or two are price levels, and one is a touch level: the only miss, a timing error.
  - **The tier word carried little.**
    - Across all V1/V1b claims, sessions wrote "moderate" 34 times, "mild" 17 and "severe" twice.
    - The rung was chosen by lock price (the frozen V1 targets 0.50, 0.25 and 0.10). Sparse ladders put one "mild" on a contract priced 0.815 and one "moderate" on 0.08.
    - So what was scored was partly chosen by price, and magnitude was never scored as magnitude.
  - **The "if" rarely came first.** In at least 5 of the 8 hits, the "then" resolved before the "if".
  - **World units make the value the session's own.** It is compared with the market's price only at expression, which keeps R6.
- **Still open.**
  - The rule that turns a world-unit value into a contract at expression (C3).
  - Whether the scorer also computes the T0 tier mapping from the same claims as a baseline. Proposed; belongs to question 4.
  - How magnitude is scored as magnitude, separately from direction (question 4).
  - Whether a bare value needs a probability or a stated confidence beside it (question 2).
  - What a yes/no event with no scale gets (question 3).
  - Whether the earlier rungs of date ladders resolve YES more often than priced across V1 and V1b. If they do, T0's timing result is a market habit rather than session skill. Not yet checked.

## 3. T3 collects the session's confidence beside every magnitude (2026-10-01)

Register C5. Question 2 of topic 1.

- **Decision.** T3 asks sessions for probabilities, so their calibration can be measured. Every world-unit value carries the session's confidence in it. The form of that confidence is not yet decided.
- **Rob's words.** "I'm fine with probabilities although I wonder if it can be expressed through magnitude so probability then gets tied to risk intrinsically?"
- **Evidence.**
  - **A bare value can't be scored or compared.** "Signed by 15 November" with no confidence can't be scored for calibration. Nor can it be set against the market's rung, which is itself a probability. Without the session's confidence, the builder would have to assume one: an unratified value.
  - **The repo already requires it for claims.** Addendum B1 §5 requires every claim in the T2 and T3 packets to carry both branches and a graded probability on every node, and §6 kept that requirement. This decision confirms it for T3.
  - **Nothing is known yet about sessions' probabilities.** There are none on record (addendum B1 §2), because V1 and V1b asked for none. Collecting them is the only way to learn whether they are calibrated.
- **Still open.**
  - **The form**, which is the next question:
    - (a) a value plus the session's probability, for example "signed by 15 November: 70%";
    - (b) values at fixed chances, where the session gives the value it thinks has a set chance of being reached, at a few set chances. The probability is then carried by the magnitude, which is Rob's question.
  - **Under (b), which chances and how many.** These are missing values and need a basis. One candidate basis is comparability with T0: V1's frozen tier targets 0.50, 0.25 and 0.10 were already fixed chances, read from the market's prices instead of the session.
  - **How many resolved values calibration needs** before it can be read.
  - **Parked, outside topic 1.** Rob called beliefs about where the market's prices go wrong, learned from their own track record, "correct and useful". R6 and D40 currently exclude them, so using them would mean amending R6. Not decided.

## 4. Confidence is carried by magnitude: values at fixed chances (2026-10-01)

Registers C3 and C5. Settles the form left open in decision 3.

- **Decision.** In T3 a session states, for each scaled outcome, the world-unit value it thinks has a fixed chance of being reached, at a few fixed chances. For example, the crude price it thinks is a coin flip, the one it gives 1 in 4, and the one it gives 1 in 10. The session writes only world units; the probability is carried by the question. This form is to be tested.
- **Rob's words.** "Yes let's go with this and test, we need a quick test we can run on new directions to validate or invalidate them quickly as well."
- **Evidence and reasoning.**
  - **It ties confidence to risk at expression without the session seeing a price (R6).** Laid over a ladder, the session's values give each rung its chance of paying. The market gives its payoff multiple (one over the price). The chance of a total loss is one minus the session's chance. That is the position-risk shape C2 needs.
  - **Calibration is a count.** Of the values a session gives at a 1-in-10 chance, about 1 in 10 should be reached.
  - **It is the reverse of T0's tier mapping.** V1's targets (0.50, 0.25, 0.10) were fixed chances whose values the market supplied; here the session supplies them.
- **Caveat found after this decision, being checked.** T0's claim result, and its timing reading (decision 2), may be produced by how V1 chose its events.
  - The V1 pool admitted events by their actual close time after 2026-06-30, and set each lock at the midpoint between start and actual close (`V1_prereg.md` A9).
  - v18 §6.7 records what that rule does to date ladders: counted by actual close time, "of 33 date ladders 31 closed early on a Yes rung".
  - Six or seven of T0's nine triggered tier claims are "happens by a date" claims on the YES side.
  - So the pool may make "it happens sooner than priced" true by construction. Decisions 2 to 4 are about measurement and stand either way; the reason to expect a timing edge does not, until checked.
- **Still open.**
  - Which chances, and how many (missing values; one basis is T0 comparability).
  - Claims double the writing: values for B if A, and if not A.
  - Yes/no nodes with no scale (question 3).
  - How magnitude is scored as magnitude (question 4).
  - **The quick test for new directions (Rob).** Not yet designed. v18's backtests (§6.7) are the nearest existing design: locks inside the window after the model's cutoff, eligibility by schedule rather than outcome, results in days.
- **Result of the check (same day, `lookbacks/polymarket/T0_BASE_RATE.md`).**
  - In the V1/V1b pool, date-ladder rungs bought at the lock beat their price by +13 points with no claim at all, and by +18 in the band where the tiers landed. Partitions and touch ladders show nothing similar.
  - Against a kind-and-price matched base, the nine tier claims whose "if" happened still beat it by +30 points (+13 to +48).
  - The tier claims bought at the lock beat it by only +4 points (−7 to +17).
  - So decisions 2 to 4 stand as measurement choices. What T0 supports is that sessions name linked events, not that they time events better than the market. A timing edge has to be shown on events chosen by schedule.

## 5. The backtest gate: loose first, confirmed by further passes (2026-10-01)

Components register Part 2 (`BT_AUDIT_GATE`, the one integrity value that goes to Rob).

- **Decision.**
  - BT-A's first reading uses a loose gate of **0.5**. A month is clean if it is more likely than not that the model knows it less than half as well as it knows the positive control (January to March). So the point estimate decides.
  - The same audit also reports the window under v18's starting value of **0.2**.
  - An edge found on the loose window is a first pass. It counts as confirmed only when it holds on the strict window and on forward data.
- **Rob's words.** "Looser first and we will do multiple passes to confirm the edge for now."
- **Basis for the numbers.** 0.5 is the point at which the month is more likely clean than not, so it is the loosest gate that still takes a side. 0.2 is v18's starting value (§7), kept as the confirming pass.
- **What it costs.** If the model knows some outcomes after its declared cutoff, a loose window can show edge that is not there; v18 calls that its main threat (§13). The confirming passes are the guard.
- **Still open.** Nothing for BT-A. The value is set before any BT-A answer exists, and is recorded in `BT_A_prereg.md` addendum A1.

## 6. The session format, accepted tentatively, with magnitude scored apart from calibration (2026-10-01)

Registers C3 and C5. Settles questions 3 and 4 of topic 1 for now, and sets the chances left open in decision 4.

- **Decision (tentative).** What a session writes in BT-T2 and T3:
  - **Scaled events** (price levels, "reaches", counts): the values it gives a 10%, 25%, 50%, 75% and 90% chance of being reached.
  - **Yes/no events with a deadline:** time is the scale. The dates by which it gives the event a 10%, 25%, 50%, 75% and 90% chance of having happened, or "not within the horizon".
  - **Yes/no events with no time dimension:** a whole percent.
  - **Partitions:** a whole percent per outcome.
  - **Claims:** B written as above twice, if A and if not A (addendum B1 §5).
- **Rob's words.** "2 accepted tentatively but I don't want to affect magnitude scoring, calibration can be fixed."
- **How scoring honours that. Magnitude and calibration are scored separately, and neither feeds the other.**
  - **Magnitude** is scored on where the session puts its values relative to the market's own implied values for the same event: which side of the market it sits and how far, and whether the outcome lands on the session's side. It does not depend on whether the session's chance labels are right, so a badly calibrated session can still show magnitude skill.
  - **Calibration** is the separate count (do the 1-in-10 values come true about 1 time in 10?). It is fixed by relabelling: each stated chance is mapped to the rate at which such values were reached on events that resolved earlier (prequential).
  - **The money score** (hit minus cost where the session's chance at a rung beats its price) is computed on the relabelled chances, so it does not penalise a fixable calibration error.
  - **T0's method** (direction only, rung picked by price) is computed from the same answers as a baseline.
- **Basis for the chances.** 50, 25 and 10 are V1's tier targets, which keeps comparability with T0. 75 and 90 mirror them, so the session never has to choose a direction in order to write a view.
- **Still open.**
  - **Tentative**, so it can change after BT-T2's first read; any change before T3's authoring costs nothing.
  - **The rule that turns the market's rungs into implied values** (interpolation between rungs, and the tails beyond the outermost rung). It is set in the BT-T2 registration before data.
  - **The departure from v18.** Graded views replace v18's narrative coverage sets (R19) as the main measure.

## 7. Edge is declared at conventional statistical significance; the aim is a standing graph, not a finish line (2026-10-01)

Register C6.

- **Decision.**
  - **Edge shown:** a test shows edge when the 95% interval of its pre-registered main statistic (skill against the market) lies above zero. That is the conventional two-sided 5% level.
  - **Edge shown absent:** when the 95% interval lies below zero, the test shows the reading loses to the market.
  - **Between the two**, the result is reported as direction (effect, interval, probability positive) and the test keeps running.
  - **Breakdowns** (a domain, a class) stay hypotheses for the next pass, as v18 §6.0 already says.
  - Under decision 5, an edge on backtests also needs the confirming passes.
- **Rob's words.** "Just set 3 at whatever is statistically significant for now, optimally there is no finish line and we have an evolving graph of events that feed eachother."
- **Basis.** The conventional 5% significance level. `DIRECTION_PUSH` (0.80) stays a steering value only, for where to put more sessions; it declares nothing.
- **What it implies.**
  - At today's backtest size (about 22 liquid events a month of window), only a large edge reaches significance quickly.
  - Forward data arrives from 15 October and grows from there.
  - Testing several statistics or breakdowns at 5% will produce some false positives, which is why only the registered main statistic declares anything.
- **The aim, in Rob's words, is an evolving graph of events that feed each other.** So there is no end state. Tests become standing passes:
  - a weekly walk-forward backtest on the newly resolved week;
  - forward scoring as contracts resolve;
  - claims kept as calibrated edges between events.
  - Each pass updates the record, and significance marks when a direction has been shown, not when work stops.
- **Still open.** The machinery for the standing graph (v18 §5.1's world graph, the weekly batches, the learning store) is not built.

## 8. T3's clusters: the graph proposes, the session decides (2026-10-01)

Register C4, in part.

- **Decision.**
  - Seeds are V3's authored events still open at T3's snapshot.
  - Candidates are open events sharing a rare tag or named entity with the seed, with link score at least 4.0, up to 8 events per cluster. Both are v18 §7 values, used as stand-ins.
  - The session drops any it judges unrelated, with a reason, and the drops are recorded.
  - An event may sit in two clusters, recorded both ways.
- **Rob's words.** "Let's go ahead with your next steps too please", in answer to the proposal "graph proposes, session decides, unless you say otherwise".
- **Evidence.** v18 §2: coherent clusters of 3 to 8 events at that score in the 2026-09-30 run, and a component of 181 when the graph alone decides. The 2026-10-01 preview of 25 clusters (`lookbacks/polymarket/t3/clusters.json`) showed mostly causal neighbourhoods, with a few same-type lists for the session to prune.
- **Still open.** C4's other questions: what bounds a subgraph in general, and whether baskets may share a contract.

## 9. The NO edge (E1) is the registered main statistic of the next backtest pass (2026-10-01)

- **Decision.** BT-T2 pass 2 runs on fresh events from the same window, with NO positions as its registered main statistic. Those are positions taken on the NO side where the session's chance of NO beats NO's all-in cost, scored against same-side, same-class, same-cost contracts and read at 5%. It is the confirm-or-kill test for E1 (`docs/EDGE_LEDGER.md`).
- **Rob's words.** "I'm realizing nomad in it's pure risk engine form is probably an amazing NO predictor as well in the first place." And: "Let's go ahead with your next steps too please."
- **Evidence.** All post-hoc:
  - BT-A NO bets +7.4¢ money, +3.7¢ against same-side, same-cost (221 events);
  - BT-T2 NO positions +5.0¢ class-matched, and +7.6¢ where the session was surer than the market.
- **Still open.** Whether a NO book's payoff shape (small wins, rare large losses, correlated shocks) fits the global risk numbers (C1), which are Rob's.

## 10. Magnitude means scale of scale, not shift delta (2026-10-01)

Register C3. Refines decisions 4 and 6.

- **Rob's words.** "My definition of magnitude here is scale of scale not shift delta."
- **Reading (builder's; to confirm with Rob).** Magnitude is how big an outcome is relative to the range of sizes outcomes of its kind take: where this instance sits on its own reference scale, an order of magnitude or a percentile of its kind. It is not how far a quantity moves from where it is now.
- **Still open.**
  - Rob's confirmation of the reading.
  - Then the elicitation: the reference class and the instance's place in it.
  - Then the scoring: the instance's realised place against the place the session and the market implied, by rank.

## 11. Fold the day's findings into what runs next (2026-10-01)

- **Rob's words.** "Let's fold in everything from above as well." Said after the explanation of the NO edge, the "scale of scale" reading of magnitude, the calibration comparison and the capital reading.
- **Decision (builder's reading of that instruction; Rob may narrow it).**
  1. **Magnitude.** "Scale of scale" (decision 10) is the working definition: how big this instance is within its kind. T3 collects it from now on: per scaled event, the reference class the session uses and where it expects this instance to sit in that class, as a percentile. Scoring needs reference-class data and is registered separately before any T3 outcome is read.
  2. **Calibration.** The `docs/EDGE_LEDGER.md` method is adopted: within a pipeline only; Platt, walk-forward, switched on only when it beats raw; partial pooling by context. A dedicated calibration pass on resolved events tests the two elicitation fixes (several sessions averaged; half the questions framed as "will not happen").
  3. **The NO edge (E1)** is the line pushed first. BT-T2 pass 2 is its registered backtest test. A forward E1 sweep, registered as a standing weekly pass, is its forward test.
  4. **Capacity.** Every forward lock records the order book's depth within 1¢ and 2¢ of the best ask, so the capital reading moves from one day's sample to every position (C7).
  5. **The ladder-structure hint** (sessions infer location from where the rungs are and which are missing) is recorded in the edge ledger as a framework mechanism. Nothing is changed for it yet.
- **Still open.**
  - **Rob's confirmation** of the scale-of-scale reading.
  - **Whether the weekly forward sweep may run as a scheduled task.** That is standing configuration on Rob's machine and needs his yes.
  - **BT-A pass 2** (window from April) is queued after T3.

## 12. The v19 starting point, and A2 registered forward (2026-10-01)

- **Decision.**
  - `docs/NOMAD_V19_STARTING_POINT.md` is the starting point for designing the new system. Its choices are the builder's, made under Rob's instruction, and stay open to his change. Where it differs from this session's earlier question-1 proposal, the starting point holds.
  - **"Build it out" is read as:** develop the design, and do the §9 steps that need no new system code. Layers 1 to 9 of its stack are not built until the design is agreed (§9).
  - **Its §9 step 1 is done.** A2 is registered as a forward statistic on the sweep, before any sweep outcome is read (`lookbacks/polymarket/V19_A2_prereg.md`, scorer `v19_a2.py`).
    - It is read at 40 and 80 resolved events with an armed NO position, with a 97.5% interval.
    - The sweep's files, its scorer and its E1, E3 and E3b statistics are untouched.
  - **The E1 book is non-mention events.** A2 without mention events is reported beside the declared statistic.
- **Rob's words.** "You choose and we'll take that as our new starting point." Then: "hmm ive got this as a starting point for the new system, let's build it out."
- **Evidence.**
  - **§6 reproduces exactly from the frozen BT-T2 result files** (`v19_a2.py backtest`):
    - armed +13.5¢ (+8.0 to +18.4) on 245 positions and 107 events;
    - not armed +1.2¢;
    - without mention events +12.3¢.
  - **What A2 actually selects.** It arms NOs costing about 50¢ to 80¢; nothing is armed above 85¢. Twenty-point disagreements on NOs under 50¢ earn +0.3¢ (−6.1 to +7.2, 169 events). That supports the starting point's correction: the edge is in NOs the market already leans to, not bets against its favourite.
  - **On the two E3 (mention) backtests, scored both sides against same-price mention contracts:**

    | | Skill | Positions (events) |
    |---|---|---|
    | A2 either side, 50¢ or more | +24.2¢ (+17.4 to +29.7) | 229 (65) |
    | Picks A2 blocks | +8.4¢ (+5.4 to +11.5) | |
    | 20-point disagreements under 50¢ | +15.4¢ (+9.7 to +21.3) | 314 (80) |

    On E1 the blocked positions earn about nothing. On mention markets they keep earning, so the 50¢ floor is an E1 finding that may not carry over. This is reported forward as a secondary; nothing declares on it.
  - **Forward pace.** W01's frozen answers and lock asks give 24 armed NO positions on 20 events if every contract resolves. This was read without any outcome, by scoring the code against made-up outcomes. So A2's first look comes about two resolved batches in (late October) and its second about four in, both ahead of E1's first look.
- **Still open.**
  - **Which rules bind the armed book from the start.** The arming table requires all of A1 to A6, but only A2 has been tested; A1 and A4 have no data yet. That is the "AND over untested rules" which, by the starting point's own principle 8, left v15 arming nothing in 15 rounds. Next question.
  - **D1 (the news disarm).**
    - E1's mechanism is that the market prices salience. A news check that disarms whenever news bears on an outcome may remove the very positions the edge is earned on.
    - "Disarm freely" assumes a false disarm costs one missed trade. A disarm that falls systematically on the edge-bearing cases costs the edge.
    - It cannot be tested on backtests, since news found now would include the outcome. It runs in the shadow book first.
  - **The mention book's arming rule** (the floor question above).
  - **Four statistics now declare on one sample** (E1, E3, E3b, A2): at most about a 19% chance of at least one false confirmation. An A2 confirmation needs the next batch to agree.
  - **The starting point's §8 items:**
    - Rob's four numbers;
    - R6 and an underlying's price;
    - the procedural-against-cascade rule and labels;
    - the statistical baseline;
    - fills;
    - E2's way to money.
  - **Rob to confirm** that `fwd_sweep.py score` has not been run on his machine before this commit.

## 13. Which rules bind: edge rules wait for evidence, risk rules bind at real money (2026-10-01)

Settles the first open item of decision 12, and amends the starting point's §5 and §3 principle 2.

- **Decision.**
  - **A2 alone binds the armed book now.** The armed book is on paper.
  - **Edge rules (A3, A4, A6): labels only.**
    - They are recorded on every shadow-book position.
    - Each binds only once the record shows that what it blocks does worse than what it lets through.
  - **Risk rules (A1, A5 and the shared-driver group caps): labels while on paper.**
    - They bind from the moment real money starts, whatever the shadow book shows.
    - A5 also needs a position size from C2 before it can be computed.
  - **D2 (each position's falsifier)** is a field recorded on every position from day one.
  - **D1 (the news disarm) is narrowed, and is label-only forward until the record shows what it would have blocked.**
    - It now covers only dated official facts that change the mechanics: a date set, a rule amended, the outcome already happened.
    - A topic announced as the subject, coverage, or anything else that is salience does not count.
  - **D3 (staleness)** was not discussed and stays a label, under "the rest start as labels".
  - **Principle 2 ("arm strictly, disarm freely") carries a caveat.** Here a false disarm can cost the edge itself, not just one trade. So a disarm rule is tested like an edge rule before it binds.
  - **The A2 registration gets addendum A1** (`lookbacks/polymarket/V19_A2_prereg.md`):
    - it is declared on non-mention events;
    - 40 events is a direction read and 80 the confirmation;
    - the bars are on skill only;
    - it is reported by week as well as by event;
    - the mention secondary is never pooled with E3 or E3b.
- **Rob's words.**
  - "Edge rules (A3, A4, A6): labels only is right. Binding them untested is the v15 mistake."
  - "A risk rule exists for rare, clustered losses, and a few weeks of paper won't show them. A1 would look useless right up to the day a cascade flips a dozen NOs. So A1 stays a label while on paper, but it and the group caps should bind the moment real money starts, whatever the shadow book says. D2 is just a field, so record it on every position from day one."
  - "'A topic announced as the subject' is salience, which is exactly what E1 gets paid for. I'd narrow D1 to dated official facts that change the mechanics (a date set, a rule amended, the outcome already happened) and keep it label-only forward until we see what it would have blocked."
  - On the registration: "Make sure the 40 and 80 bars are on skill, not the +23¢ money figure." "State now that 40 events is a direction read and 80 is the confirmation." "Report by week as well as by event, because two weeks is two tides, not 40 independent events." "Keep it separate from E3's registered statistic so it isn't counted twice."
- **Evidence.**
  - **The v15 lesson.** Its AND over eight untested rules armed nothing in 15 rounds (the starting point, §3 principle 8).
  - **How the backtest's armed losses cluster** (BT-T2 passes 1 to 3, after the fact): 245 armed positions, 36 losses on 33 events.
    - **Inside an event, losses rarely come together.** Of 51 events with two or more armed positions, 2 lost more than one: Amazon's August price ladder (3) and Microsoft's end-of-July close (2).
    - **Across events, they came together once.** In lock weeks 30 to 32 (late July to early August), 25% to 33% of armed positions lost, against 15% overall.
      - The losses crossed events and entities: post-count markets on five different accounts (Khamenei, NYC's mayor, the White House, Ted Cruz, CZ), and big-tech earnings and price markets (Amazon, Microsoft, Apple).
      - That is one visible cluster in 27 lock weeks. Rob's point holds: a few weeks of paper would most likely not contain one.
      - A group cap counted by event alone would not have caught it.
  - **Non-mention basis for the registration.** Armed non-mention NOs read +12.3¢ (+6.5 to +17.3) on 103 events; +8.7¢ without the top five, +5.2¢ without the top ten.
- **Still open.**
  - **What counts as a shared driver** for the group caps. They now bind at real money, so this needs a written definition before then. Next question.
  - **A written procedural-against-cascade rule for A1,** for the same reason.
  - **Rob's four numbers** (C1).
  - **Rob to confirm** that `fwd_sweep.py score` has not been run on his machine. On Windows, the sign would be a file `lookbacks\polymarket\sweep\result.json`, which that command writes.

## 14. Rob's six answers (2026-10-02)

Answers to the six open choices of decision 13, put to Rob in plain English.

1. **The main test leaves out mention markets.**
   - Rob: "Yes we need general edge, markets where we do better are great but they skew."
   - **The aim is general edge.** A market kind that does better is reported, but is never allowed to carry the main test.
   - So A2 is also reported by market kind and without its best kind (`v19_a2.py`, addendum A2). That uses a first, fixed list of kinds set before any sweep outcome is read.
2. **The halfway look (40 events) neither confirms nor kills. It is grounds for revision.**
   - Rob: "No but it should be grounds for revision."
   - **If it points the wrong way,** a revised rule is drafted.
   - **The revision is a new rule,** registered before the batches it is scored on, and it runs beside the original. The original runs unchanged to its final look at 80 events (`V19_A2_prereg.md` addendum A2).
3. **The sweep's scoring has not been run on Rob's machine.**
   - Rob: "I have not."
   - The A2 registration and both addenda are clean.
4. **Shared drivers are to be found, however obscure.**
   - Rob: "There's some form of correlation here that we need to identify however obscure."
   - **Approach (builder's).** A group is the union of four sources:
     - (a) the same event;
     - (b) the same market kind over a window;
     - (c) links found in the data: kinds whose weekly results move together, and kinds that lose in runs;
     - (d) positions whose recorded falsifiers (D2, now on every position) name the same cause. This catches links too rare for the data to show yet.
   - **Why a union.** For a risk rule, a false link costs capacity and a missed link costs money.
5. **Paper before real money.**
   - Rob: "We need to do paper before we go to real money."
   - The four C1 numbers are set after a paper phase, informed by it. Nothing is needed from Rob for them now.
6. **One-off big events (cascades): never.**
   - Rob: "Never."
   - **Builder's reading, to confirm (corrected in decision 15: Rob meant never rule them out):** never bet on them. With real money they are always excluded. On paper they are still recorded and labelled, so the record shows what the rule leaves out.

**Evidence found while recording these (all after the fact, from frozen files; nothing declares on it).**
- **Forward week one is mostly one occasion.** By the fixed list of kinds:
  - 72 of W01's 102 events are elections. 54 are Brazil's 4 October general election (state governor, senate and presidential first-round markets) and 11 are Quebec's.
  - 22 of W01's 24 armed positions are election markets, so most of W01's A2 evidence settles on one or two election nights.
  - A2 resamples by event, so it treats these as independent. They share one national swing. The sweep's own registered E1 statistic has the same property and stays untouched (a running test).
- **A2's backtest edge leans on crypto.** Armed non-mention NOs by kind (BT-T2 passes 1 to 3):

  | Kind | Positions | Events | Skill |
  |---|---|---|---|
  | Crypto price | 112 | 39 | +17.7¢ (+10.6 to +23.2) |
  | Stocks and earnings | 35 | 19 | +15.2¢ (−2.7 to +31.0) |
  | Post counts | 31 | 15 | −9.5¢ (−24.0 to +1.1) |
  | Elections | 15 | 7 | +6.7¢ (−35.0 to +22.2) |

  - Without crypto: +7.4¢ (−1.1 to +15.0), 64 events. Without crypto and post counts: +13.1¢ (+3.4 to +21.6), 49 events.
  - **So by Rob's standard of general edge, A2 outside crypto is direction only in the backtest.** Its first forward weeks test it mostly on elections, where it has 7 backtest events.
- **Losses come in runs inside one kind, not across kinds in one week.** Market-wide NOs priced 50¢ to 90¢: 1,068 contracts, 346 events, 27 lock weeks.
  - Crypto price NOs lost four weeks running (weeks 26 to 29, −17¢ to −20¢ a week).
  - Stocks and earnings lost two (weeks 30 and 31, −25¢ and −39¢, earnings season).
  - Kinds did not move together week to week (crypto against stocks r −0.02 over 22 weeks). But 27 weeks can show only strong links.
  - A calendar-week group is too short for a run that lasts weeks. The window length is open, to be set from run lengths as data accumulates.

**Still open.**
- **Whether A2's test should count events that share one occasion** (the same kind, place or asset, settling the same week) as one unit when measuring its uncertainty. This has to be settled before anyone runs the sweep's scoring. Next question.
- **Rob to confirm** the reading of answer 6.
- **What the paper phase must show before real money,** and for how long.

## 15. One-off big events are never ruled out (2026-10-02)

Corrects the reading of decision 14, answer 6. Supersedes decision 13's clause that A1 binds at real money, and amends the starting point's §3 principle 1 and the selector in §4.

- **Decision.**
  - **One-off cascades are eligible** (a war escalating, a government falling). They are never excluded, on paper or with real money.
  - **A1 is removed as a rule.** Whether a question is procedural or a cascade may still be recorded as a description, so the record shows how such bets do and whether they lose together. It excludes nothing.
  - **The selector keeps its other limits:** short-dated, attention-driven, specific outcomes.
- **Rob's words.** "It's never rule then out."
- **Evidence.**
  - The exclusion came from v15's theory, not from a test. No event has ever been labelled procedural or cascade, so nothing in the record says cascade bets lose.
  - Rob's earlier concern (decision 13: "A1 would look useless right up to the day a cascade flips a dozen NOs") still describes a real risk. With A1 gone, the group caps and the drawdown stop carry it alone, helped by the falsifier field (decision 14, answer 4, source d).
- **Still open.** Unchanged from decision 14: whether A2's test counts events that share one occasion as one unit.

## 16. One occasion counts as one piece of evidence (2026-10-02)

- **Decision.** A2's test counts events that share one occasion as one unit, both for its uncertainty and for when its looks come.
  - One occasion is the same kind of market, about the same place or asset, settling within the same 7 days (`V19_A2_prereg.md` addendum A3).
  - The looks stay at 40 occasions (a direction read) and 80 (the confirmation).
- **Rob's words.** "lets go with yes."
- **Evidence.**
  - **W01** is 54 events on Brazil's 4 October election. Its 20 armed events are 5 occasions.
  - **On the backtest,** 103 armed events are 87 occasions, at about 25¢ per occasion. At 80 occasions the test confirms if the forward mean is about 6.2¢ or more, against 7.0¢ by events.
- **What it costs.** The final look moves from about early to mid November to somewhere between late November and late January, depending on how many separate occasions each batch holds.
- **Still open.**
  - **What the paper phase must show before real money,** and for how long.
  - **The same weakness in a running test.** The sweep's own E1, E3 and E3b statistics still resample by event. They are a running test and stay untouched. A2's scorer can report E1 by occasion beside them as a secondary, if wanted.

## 17. What paper must show before real money (2026-10-02)

- **Decision.** Real money waits for two things:
  1. **A2's final look confirms** (80 occasions; `V19_A2_prereg.md`).
  2. **Paper fills against the recorded order books show the edge survives real buying costs.**

  The third proposed condition, that the paper book live through a bad run with the money limits applied, is not a gate. The limits will be adapted to the resources available at the time.
- **Rob's words.** "1 and 2 and we'll adapt 3 to whatever resources are available at the time, the stronger the strategy the less the limits apply so lets focus on making the best system possible."
- **Evidence on "the stronger the strategy the less the limits apply"** (BT-T2 passes 1 to 3, after the fact):
  - **Supported where the strategy is strong.**
    - In crypto's four-week market-wide run (lock weeks 26 to 29), the crypto bets A2 armed won 19 of 20: +35.7¢ money, +24.3¢ skill.
    - The crypto NO picks it did not arm lost 53 of 77.
    - The arming rule stepped around the run. But 17 of the 20 armed bets came in one week.
  - **Not supported where it is weak.** The armed book's own cluster (lock weeks 30 to 32: 15 losses on post counts and stocks) fell on post counts, A2's one losing kind (−9.5¢, 15 events).
  - **So the limits matter less where a kind's record is strong and more where it is weak.** One design that follows: size each kind's limit by that kind's own record, rather than one limit for all. Not decided; it waits for forward records by kind.
- **Still open.**
  - **Fills.** The recorder runs on Rob's machine (`~/polymarket_record` in WSL), so the paper-fill check needs its data or a run there.
  - **Where to focus first to make the system as strong as possible** (Rob: "lets focus on making the best system possible"). Next question.

## 18. Run the system on paper now; improve it from what the running shows (2026-10-02)

Supersedes the starting point's §9 line "nothing is built until the design is agreed".

- **Decision.** The v19 system runs now, on paper, and is improved from its own record. Version 0 is `lookbacks/polymarket/v19_book.py`, with its report in `v19/BOOK.md`.
  - **Selector and cold reader:** the forward sweep's frozen batches. They are read only, and nothing in them changes.
  - **Shadow book:** every position the reader produces.
  - **Armed book:** A2 alone binds (decision 13).
  - **Labels recorded:** kind, occasion (decision 16) and depth at the lock (A5). A3, A4, A6, D1, D2 and D3 are marked not yet available.
  - **Execution:** paper fills at the lock ask plus the fee, sized at the lesser of $150 and the dollars on offer within 2¢ (the sweep's capacity reading, §3; C2 has no size yet). A 2¢-worse column sits beside them.
  - **Ledger:** settled from Gamma as contracts resolve. The book declares nothing; A2 is read only at its looks.
- **Gate 2, fills (decision 17).** `lookbacks/polymarket/v19_watch_books.py` runs beside the recorder on Rob's machine.
  - It snapshots, every 15 minutes, the order book of every open armed position and every shadow NO at 50¢ or more.
  - The recorder keeps books only for its 300 busiest tokens, and the paper book's markets are mostly small.
  - `fills` prices each paper fill by walking the recorded book and writes `v19/fills.json` to commit.
- **Rob's words.** "well we cant see how to improve anything without running it." And, on the recorder: "feel free to use whatever you need."
- **What the first run shows** (W01, 2026-10-02 06:56 UTC; outcomes read for the first time, after A2's registration and its three addenda):
  - **Armed book.** 24 positions on 20 events, $2,388 staked, none settled yet.
    - 22 are election markets.
    - **$1,507 (63%) sits on one occasion,** Brazil's 4 October election. Peru's is another $663.
  - **Shadow book.** 900 more positions: 114 NO, 786 YES.
    - 315 sit on contracts priced at 3% or less, or 97% or more, at the lock. 299 of those are YES long shots on asks of a fraction of a cent.
    - All 13 shadow NOs settled so far lost. They were outcomes already decided at the lock (a day's rain, a closing price), bet against by a reader with no news.
    - **A2's 50¢ floor keeps every one of these out of the armed book.** D1's narrowed rule ("the outcome already happened", decision 13) would flag the decided ones.
  - **Reading the ledger early is biased.** A NO that loses usually settles early; one that wins settles at its deadline.
  - **Fills.**
    - **At the lock:** 19 of the 24 armed stakes fit within 1¢ of the ask, and the rest within 2¢.
    - **One live snapshot from this session, 15 hours later:**
      - every armed market had a book, and the median spread across the 61 watched books was 3¢;
      - five thin Brazilian senate books had spreads of 8¢ to 24¢, and on one a $150 order could fill only $95, at an average of 91¢ against a 75¢ best ask;
      - two armed NOs had fallen from 56¢ and 64¢ to 39¢ and 37¢.
    - Exiting before resolution (C8) would pay those spreads.
- **Still open.**
  - **Test 1, sharpening the reader** (several independent sessions averaged, and half the questions framed as "will this not happen"). It is registered before any session runs, on existing backtest events, and can run from this session: transcripts sit where the audit looks.
  - **D2.** The sweep's reader writes no falsifier, and its prompt is frozen. A falsifier needs a v19 reader pass or a separate step.
  - **Rob to start the watcher** on his machine (command in `v19_watch_books.py`).

## 19. Read each question once: averaging readings does not sharpen the reader (2026-10-02)

- **Decision.** The v19 reader stays single: one cold reading per question. Averaging several readings is not adopted.
- **Rob's words.** "1 and 4 look good" (decision 17's options); "feel free to use whatever you need."
- **Evidence** (`lookbacks/polymarket/R1_AVERAGING_RESULT.md`; registered before any session ran; 50 cold sessions, all audited):
  - **Registered:** avg(B, C) beat single readings by +0.9¢ (−1.3 to +3.4). Direction only.
  - **The reader is consistent.** Independent readings arm 82% to 87% of the same positions, so there is little noise to average away.
  - **A2 holds on readings it was not fitted to:** +17.9¢ and +14.5¢ on two fresh readings of pass 3's questions. The same events, so this is not a new-event test.
- **Still open.**
  - **R2,** the "will this not happen" framing. The reader's errors look systematic, so a change of wording is the better lever.
  - **Reading every eligible market each week** (decision 17, option 2).
  - **A statistical second opinion** (option 3).

## 20. What the design-performance tests settle (2026-10-02)

- **Rob's words.** "execute all tests require to gauge pre structured design performance."
- **Decision.**
  - **A2 stays the only binding rule, with its thresholds unchanged.**
    - Out of sample it reads about +10¢ to +11.5¢ a position.
    - It is confirmed on BT-A (+11.5¢, +3.3 to +19.1, 82 fresh events) and direction only on P4 (+10.0¢, −7.7 to +23.6).
    - What it blocks earns about nothing.
  - **A3 does not earn its place and stays a label.** With P4 added, what it would block earns more than what it passes (+18.3¢ against +11.2¢).
  - **A higher disagreement bar (30 points)** is a candidate for the shadow book, registered before data. It is not adopted from the backtests.
  - **The reader is unchanged.** Averaging (R1) and reframing (R2) both read direction only, and the reader's bets proved stable under both.
  - **Occasion caps are confirmed as necessary before real money.** Out of sample, one occasion (six interest-rate positions) lost $900 together, the worst week.
- **Evidence.** `lookbacks/polymarket/V19_DESIGN_TESTS_RESULT.md`, `R1_AVERAGING_RESULT.md`, `R2_FRAMING_RESULT.md`. 100 cold, audited sessions today (R1 50, R2 25, P4 25).
- **Still open.**
  - **The forward tests,** which only time advances: A2 forward (first look at 40 occasions), the sweep's E1, E3 and E3b, and fills.
  - **Rob's occasion cap,** and the money limits after paper (decision 17).

## 21. P5: the framework's registered test passes, but the backtest prices under it were mostly not real (2026-10-02)

- **Rob's words.** "run the safety framework on a fresh pass".
- **Decision.**
  - **P5's registered verdicts stand as computed.**
    - Framework skill: +20.8¢ (+12.8 to +27.0). Edge shown.
    - Framework-passed minus blocked: +20.0¢ (+6.6 to +34.4). Edge shown.
  - **The registration's follow-on is held.** The framework does not replace A2 in the paper book: 43 of its 51 positions were priced at empty-book midpoints that nobody could trade. Rob decides.
  - **The backtest edge figures are no longer taken at face value:** A2's +10¢ to +11.5¢, the design simulation's +29.9% per dollar, the losers note's tiers, and the edge and capital table. Each rests largely on those prices.
- **Evidence** (`lookbacks/polymarket/V19_FRAMEWORK_P5_RESULT.md`, `v19_price_check.py`; exploratory, found after scoring):
  - **The lock prices.** P5's five crypto ladders had every bracket at 47¢ to 50¢, with YES summing to about 5.1 where one bracket wins.
  - **How widespread.** 58% of A2's armed positions in passes 1 to 5 sit on such prices. Near the lock, trade prints put those NOs at 91¢ to 100¢.
  - **On clean prices,** A2 reads:
    - +4.2¢ skill (−5.4 to +13.4) and +9.8¢ money (+0.7 to +18.2);
    - −16.9¢ on partitions;
    - a positive slice on ladders and percent questions.
  - **The framework on clean prices, out of sample:** 8 positions, +27.8¢ (−11.2 to +49.2). Direction only.
- **Still open.**
  - **Re-measure the backtests at prices that were really there,** registered before it runs. These are the trade prints near each lock, or a coherent book. It needs no new sessions, and the frozen files are read, not changed.
  - **BT-A** gets the same price check.
  - **The forward test** prices at the live ask, so it is the clean measurement. W01 is mostly election partitions and settles from 4 October.

## 22. The framework is the design itself; only P5's filter is set aside (2026-10-02)

- **Rob's words.** "The framework can't go in the sense that it's just what we're building, if you want to scrap it in it's current form sure no problem but we can't scrap the concept as refining the design is the framework itself."
- **Decision.**
  - **"The framework" means the whole design around the edge, and refining it continues.**
  - **The three-condition filter that P5 tested is set aside in its current form.** It required the reader under 10%, at least 3 days to the scheduled end, and not a touch question. It is called "the P5 filter" from here.
  - **Its ideas return as candidates in layer 3,** re-tested at real prices.
- **Evidence.** Decision 21 and `lookbacks/polymarket/V19_FRAMEWORK_P5_RESULT.md`. 43 of the P5 filter's 51 positions were priced at empty-book midpoints.
- **The design's layers, as they stand:**
  1. **Is the price real?**
     - New, from decision 21.
     - Forward: the live ask, with each stake capped by the depth within 2¢.
     - Backtests: not yet built in.
  2. **Does the reader disagree enough?** A2, to be re-measured at real prices.
  3. **Which disagreements to trust.** Candidates: conviction, timing and shape (the P5 filter's ideas), and pick-the-winner against other questions. A2 lost on pick-the-winner at real prices (exploratory).
  4. **How much, and how bunched.** Occasion caps and depth. The −$900 rates occasion was on real prices.
  5. **Execution.** Taking the ask against resting orders, once the edge's size at real prices is known.
- **Still open.**
  - **Step 1:** re-score E1, A2, the mention edge and BT-A at real prices, registered before it runs.
  - **Step 2:** non-binding forward labels before W01 settles on 4 October: the P5 filter's conditions, Tier 1, and pick-the-winner against other questions.
