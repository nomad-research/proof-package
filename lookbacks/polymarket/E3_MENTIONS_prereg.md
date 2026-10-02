# E3: mention markets, every eligible event in the clean window (registration, written before the frame is built)

Tests candidate E3 (`docs/EDGE_LEDGER.md`): on "What will … say" markets, the model's NO picks beat other mention NOs of the same price.

It uses BT-T2's design, script and session format (`BT_T2_prereg.md` with addenda A1 to A3; `BT_T2_pass2_prereg.md` with A1 and A2), except as stated here. This file is committed before any event is drawn, any price is read, any session runs or any outcome is read.

## 1. Where the hypothesis came from

- BT-T2 pass 1 and pass 2 together drew four mention events.
- On those four, the model's NO positions scored +15.9¢ against same-side, same-cost contracts of the same session format (95% +5.8 to +29.4; `BT_T2_pass2_RESULT.md`).
- Four events is too few to read, and the subset was named after looking. So this test uses every other eligible mention event in the window, and none of those four.

## 2. The frame

| | Value | Based on |
|---|---|---|
| Events | Every event whose title matches `\bsay\b\|\bmention` (case-insensitive) | Pass 2's "mention" group, word for word, so the test is that group and nothing tuned |
| Excluded | The four mention events drawn in BT-T2 passes 1 and 2 | They produced the hypothesis |
| Crawl | `closed_2026-01-01_2026-10-01_v10000_scoped.json.gz` (sha `929ddee7…`) | As BT-T2 |
| Cleaning | BT-T2's: maker, `clean` (disputed and unresolved events dropped), leak flags, two-market events | As BT-T2. Limit: `clean` drops disputed events, and a dispute is known only after the lock. 29 mention events go this way. This is recorded, not changed, so the test stays comparable with the passes it follows up |
| Session format | `percent` only (one chance per contract) | One eligible event is a count ladder (`terminal`). A count is not a mention market, and one event cannot be read |
| Lock grid | **Daily at 12:00 UTC from 2026-07-01** (BT-T2 used every 7 days) | Mention markets often open a few days before the speech. Counted from created and end times only (no prices, no outcomes): the weekly grid admits 33 of the eligible events, the daily grid 48 |
| Lock chosen | One at random among the event's schedule-valid locks with at least 3 priced contracts (multi-market events) or 1 (single-market events) | As BT-T2. Seed 20261005 |
| Window start | 2026-07-01 | BT-A (`BT_A_RESULT.md`) |
| Price | Last trade at or before the lock, 7-day window | BT-T2 addendum A1 |

**A known bias against the model.** On a "this week" event the lock can fall after some words are already said. The market prices those near 1 and the cold session cannot know. Such words are usually closed early and drop out as not open at the lock. Any that remain cost the model's NO picks money. Nothing is done about it, and it works against the claim.

## 3. The main statistic

Pass 2's E1 statistic, computed on this frame:
- **Positions.** NO positions on every scored contract, where the session's chance of NO (one minus the upper bound of its YES chance) is above the all-in cost of NO (price plus 0.01 slippage plus fee).
- **Score per position.** (hit − all-in cost) minus the mean (hit − all-in cost) of every NO side of every other contract in this frame, with all-in cost within 0.05. The position's own event is excluded.
- **The comparison.** Because every contract here is a mention contract, the comparison is other mention NOs at the same price. This separates the model's choosing from any habit of mention markets as a whole.
- **Reading (decision 7).**
  - **Confirmed** if the 95% interval of the mean (4,000 bootstrap draws, resampled by event) lies above zero.
  - **Killed** if it lies below zero.
  - Otherwise direction only.

## 4. Secondary (declaring nothing)

- **NO money (hit − all-in cost) on the model's NO picks.** This is what a trader would earn.
- **Blind NO.** Money on the NO side of every contract in the frame. This checks for a market habit: if blind NO earns as much as the picks, the edge belongs to the market, not to Nomad. It would go in the ledger as a market fact.
- YES positions against the same-side base.
- NO by price of NO (under 50¢ and 50¢ or more) and by size of disagreement (0–0.1, 0.1–0.2, 0.2–0.4, 0.4 and above), as in pass 2.
- NO by speaker group, by a title rule written before the draw:
  - "Trump" in the title;
  - "earnings call" in the title;
  - everything else.
- The log score against price, and calibration.

## 5. Integrity and budget

- Sessions are cold, price-blind and given no evidence, as in BT-T2.
- 6 events a session, so about 8 sessions.
- Mention contracts each carry their own rules, so prompts are long. Every session is sent the paged instruction (`INSTRUCTION_PAGED`, pass 2 addendum A2) from the start. The audit's read check (pass 2 addendum A1) applies.
- Every transcript is audited. Voids are re-authored and counted.
- Answers are frozen by hash and committed before any outcome is read.
- Code changes to `bt_t2.py` before the frame:
  - options for a title filter, a lock step, a session-format filter and a prompt prefix;
  - the blind-NO and speaker-group secondaries.

  The defaults leave passes 1 and 2 unchanged.
