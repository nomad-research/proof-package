# E3 pass 2: mention markets in the earlier window (registration, written before BT-A pass 2's result is known)

E3's first pass showed an edge on its registered statistic: +7.3¢ (95% +1.8 to +13.0) on 46 events, leaning on a few of them (`E3_MENTIONS_RESULT.md`). Decision 5 asks for more passes, and the forward sweep finds only a few eligible mention events a week. The fastest independent pass is the months before July, **if** BT-A pass 2 shows the model does not know their outcomes.

This file is committed while BT-A pass 2's sessions are running, before any of its answers is frozen or scored. So the choice to run it, and its design, cannot depend on that result beyond the rule in §1.

## 1. Whether it runs

- **It runs only if** BT-A pass 2 (`BT_A_pass2_prereg.md`) sets `BT_WINDOW_START` before 2026-07-01 under the **loose** gate (decision 5's first-pass gate).
- **Locks** are on the daily grid from that start up to 2026-06-30. Every lock falls in months BT-A pass 2 found clean.
- If the window stays at 2026-07-01, this pass does not run and that is recorded.

## 2. The frame

As E3's first pass (`E3_MENTIONS_prereg.md` §2), except:
- **Locks** from `BT_WINDOW_START` to 2026-06-30, daily at 12:00 UTC.
- **Excluded:** every event in E3's first frame, BT-T2 passes 1 and 2, and BT-A passes 1 and 2.
- **Seed** 20261008.
- **All eligible events are drawn,** in sessions of 6, with the paged instruction.

## 3. Statistics

- **Main:** E3's registered statistic on this frame. The model's NO picks are compared with other mention NOs at the same price (within 0.05), own event excluded, resampled by event, and read by decision 7.
- **Secondary, unchanged from the first pass:**
  - NO money;
  - blind NO;
  - YES against same-side contracts;
  - NO by price (under 50¢, 50¢ or more), by size of disagreement and by speaker;
  - the log score.
- **Also secondary:** the concentration check (without the top three events), and both passes pooled. These declare nothing.

## 4. Reading across passes

- If this pass also shows the edge, E3 counts as confirmed on backtests (two registered passes). It still needs the forward sweep before any design leans on it.
- If this pass shows it absent, the first pass's result is treated as a likely fluke of a few events.
- If this pass gives direction only, E3 is carried to the forward sweep.
