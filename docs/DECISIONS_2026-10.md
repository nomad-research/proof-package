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
