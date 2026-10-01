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
