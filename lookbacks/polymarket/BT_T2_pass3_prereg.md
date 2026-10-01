# BT-T2 pass 3: the NO edge (E1) in the earlier window (registration, written before the frame is built)

E1 has read direction only on its registered test: pass 2 gave +2.6¢ (−2.7 to +8.0), and pooled with pass 1 it is +3.4¢ (−0.3 to +7.2) (`BT_T2_pass2_RESULT.md`). BT-A pass 2 opened the backtest window at 2026-04-01 under the loose gate (`BT_A_pass2_RESULT.md`). That makes April to June available for a third independent pass, as `BT_A_pass2_prereg.md` §3 set out.

Same design, script, session format, audit and freeze as `BT_T2_pass2_prereg.md` (with addenda A1 and A2), except as stated here. Committed before any event is drawn, any session runs or any outcome is read.

## 1. What changes from pass 2

| | Pass 2 | Pass 3 | Why |
|---|---|---|---|
| Locks | 7-day grid from 2026-07-01 | **7-day grid from 2026-04-01 to 2026-06-30** | The newly opened window; no overlap with passes 1 and 2 |
| Events | 150 multi-market | **150 multi-market** | As pass 2 |
| Excluded | Pass 1 | Every event in BT-T2 passes 1 and 2, E3 passes 1 and 2, and BT-A passes 1 and 2 | Fresh events |
| Seed | 20261004 | 20261009 | A fresh draw |
| Output | `bt/t2_pass2/` | `bt/t2_pass3/` | Kept apart |
| Instruction | Single read, paged on re-authoring | **Paged from the start** | Pass 2 lost three sessions to the read cap |

## 2. Statistics

- **Main: E1, exactly as pass 2 §2.** The model's NO positions are scored against NO sides of other contracts of the same event class with cost within 0.05, own event excluded, resampled by event, and read by decision 7.
- **Secondary, as pass 2 §3, plus:**
  - **By lock month.** June alone is the strict-gate window. If May's reading differs sharply from April's and June's, that is reported as a possible knowledge leak.
  - **Pooled with passes 1 and 2.** E1 over all three passes. This declares nothing.
  - **The both-sides statistic (S1), by event class.** It is the statistic that replicated on mention markets (`E3_MENTIONS_pass2_RESULT.md`), and this asks whether it holds anywhere else.

## 3. Reading across passes

- If pass 3 confirms E1, E1 has a registered confirmation on backtests and goes to the forward sweep for its forward confirmation.
- If pass 3 kills it, E1 is dropped from design and stays in the ledger as a lesson.
- If direction only, E1 rests on the forward sweep.

## 4. Budget

About 25 sessions of 6 events, about 2.2 million subagent tokens.
