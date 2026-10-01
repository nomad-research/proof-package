# BT-T2 pass 2: the NO edge, on fresh events (registration, written before the frame is built)

Confirms or kills E1 (`docs/EDGE_LEDGER.md`; `docs/DECISIONS_2026-10.md` decision 9). Same design, script and session format as BT-T2's first pass (`BT_T2_prereg.md` with addenda A1 to A3), except as stated here. Committed before any event is drawn, any session runs or any outcome is read.

## 1. What changes from the first pass

| | First pass | Pass 2 | Why |
|---|---|---|---|
| Events | 90 multi-market and all 83 binaries | **150 multi-market events not drawn in the first pass**; no binaries | Every eligible binary in the window was used in the first pass. Reusing an event at another lock would be dependent |
| Seed | 20261002 | 20261004 | A fresh draw |
| Output | `bt/t2/` | `bt/t2_pass2/` | Kept apart |
| **Main statistic** | S1 skill over all positions | **E1: NO positions only**, against **same-side**, same-class, same-cost contracts | Decision 9 |

The window (locks from 2026-07-01 on the 7-day grid), the schedule rules, the price rules, the session format, the audit and the freeze are unchanged. So are the scorer fixes of addendum A3, now in the code before any pass-2 data exists.

## 2. The main statistic: E1

- **A NO position:** on any scored contract, the session's chance of NO (one minus the upper bound of its YES chance) is above the all-in cost of NO. This is the first pass's bet rule restricted to the NO side.
- **Score per position:** (hit − all-in cost) minus the mean (hit − all-in cost) of every **NO** side of every other contract in the pass-2 frame of the **same event class**, with all-in cost within 0.05.
  - Contracts of the position's own event are excluded.
  - The base is taken on the NO side because NO and YES are not priced alike: YES runs slightly rich, so a NO-heavy book would look skilled against a both-sides base for free.
- **Read (decision 7):** E1 is **confirmed** if the 95% interval of the mean, resampled by event (4,000 draws), lies above zero. It is **killed** if it lies below zero. Otherwise it is direction only and carries to the next pass.

## 3. Secondary (declaring nothing)

- **The first pass's S1** (all positions, both-sides base) and the YES positions alone.
- **"Surer than the market" NO positions:** the session's YES chance is further from 0.5 than the price and on the same side. This was the sharpest subset in the first pass (+7.6¢).
- **By event class, and for two named groups:** mention markets ("What will … say") and bucket or count markets (price ranges, post counts, data releases). These carried the first pass's concentration and are hypotheses here.
- **By size of disagreement:** |session − price| in 0–0.1, 0.1–0.2, 0.2–0.4 and above 0.4.
- **Money** (hit minus cost) on NO positions, **calibration** and the **log score**, as in the first pass.

## 4. Integrity and budget

- As the first pass.
- 25 sessions of 6 events, about 2.2 million subagent tokens at the measured 75–115 thousand per session.
- No outcome is read until every answer is frozen by hash and committed.

## Addendum A1 (2026-10-01, while sessions ran, before the freeze and before any outcome is read)

S08's prompt was read in two overlapping chunks: the Read tool stopped at line 489 and the session resumed at 489. BT-A addendum A2's read check (rebuilding the prompt by line number, with every line matching) is added to `bt_t2.py`'s ingest. A session failing V1's exact-join check passes only if that check holds and every other audit condition holds. It applies to every pass-2 session alike.

## Addendum A2 (2026-10-01, while sessions ran, before the freeze and before any outcome is read)

S01's and S04's prompts are over the Read tool's 25,000-token cap. Each first session read once, was cut off, and, holding to "it is the only tool call you may make", answered its last event partly unseen; the audit voided both. Re-authored sessions are sent an instruction that permits reading the prompt in parts (`bt_t2.INSTRUCTION_PAGED`). The prompt file and the audit's requirement that the reads reproduce it exactly (by line number, A1) are unchanged. Every re-authoring is counted in the result.
