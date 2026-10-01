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
