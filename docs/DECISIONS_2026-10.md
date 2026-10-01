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
