# BT-A pass 2 result: months by actual resolution (2026-10-01)

Registration `BT_A_pass2_prereg.md` (commit `96ad75b`). Draw `a0d10a96…` (commit `f82eb5d`). Answers frozen by hash (manifest `eaa1a37d…`, commit `69091ee`) before any outcome was read. Result: `bt/audit_pass2/result.json`.

**The run.**
- 280 fresh news events: 40 a month, January to July. Each event's month is the earlier of its scheduled end and its actual close.
- No event was drawn in BT-A pass 1, BT-T2 or E3.
- 28 cold `claude-opus-5-5` sessions. Every transcript passed the audit. No re-authorings.

## The registered result

| Month (by actual resolution) | n | Mean excess | 90% interval | Recognised | P(reaches half the control) | Clean, loose 0.5 | Clean, strict 0.2 |
|---|---|---|---|---|---|---|---|
| **Jan to Mar (control)** | 120 | **+0.072** | +0.015 to +0.133 | 40 | | | |
| April | 40 | −0.038 | −0.087 to +0.010 | 6 | 0.017 | yes | yes |
| May | 40 | +0.020 | −0.070 to +0.120 | 1 | **0.379** | yes | **no** |
| June | 40 | −0.071 | −0.144 to +0.004 | 0 | 0.017 | yes | yes |
| July | 40 | −0.227 | −0.365 to −0.100 | 0 | 0.000 | yes | yes |

- **The control is informative.** On events that resolved by March the model beats the price (P positive 0.985), as in the first pass.
- **`BT_WINDOW_START`, loose gate (decision 5's first-pass gate): 2026-04-01.** Every tested month from April is clean.
- **Strict gate: 2026-06-01.** May reaches half the control's excess with probability 0.38, above the strict 0.2. Its mean is slightly positive (+0.020), with one recognised event.
- **Against the first pass.** Months by scheduled end put the window at July. The post-hoc reading by actual resolution suggested April. This registered pass confirms April under the loose gate on fresh events. Under the strict gate it stops at June, because May is borderline.

## What follows (as registered)

- **Backtests registered from now on may lock from 2026-04-01 under the loose gate.** Each should also report its locks from 2026-06-01, the strict window, so a reader can see whether May carries anything.
- **E3 pass 2 (`E3_MENTIONS_pass2_prereg.md`) runs.** Its §1 condition is met. Locks run from 2026-04-01 to 2026-06-30.
- May's borderline reading is a reason to read April-to-June results by month as well as pooled.
