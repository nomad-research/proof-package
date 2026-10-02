# BT-A result: the cutoff audit (2026-10-01)

Registration `BT_A_prereg.md` (with addenda A1 and A2), script `bt_audit.py`, result `bt/audit/result.json`. 450 events (40 news and 10 price-level a month, January to September 2026), 45 cold `claude-opus-5-5` sessions, every transcript audited. Two sessions were re-authored: S01 (a 0 where 1 to 99 is required) and S39 (the read check, addendum A2). Answers were frozen by hash (manifest `a27678f9…`, commit `64177b4`) before any outcome was read.

## The registered result

The score is log(the session's probability on the realised side ÷ the price 14 days before resolution), averaged over each event's contracts. The table shows news events; 90% intervals are by event.

| Month (scheduled end) | n | Mean excess | 90% interval | Recognised | P(reaches half the control) | Clean, loose 0.5 | Clean, strict 0.2 |
|---|---|---|---|---|---|---|---|
| **Jan to Mar (positive control)** | 120 | **+0.088** | +0.025 to +0.154 | 48 | | | |
| April | 40 | −0.109 | −0.277 to +0.037 | 6 | 0.048 | yes | yes |
| May | 40 | −0.057 | −0.142 to +0.023 | 2 | 0.025 | yes | yes |
| **June** | 40 | **+0.060** | −0.056 to +0.182 | 3 | **0.574** | **no** | **no** |
| July | 40 | −0.100 | −0.219 to +0.009 | 3 | 0.019 | yes | yes |
| August | 40 | −0.233 | −0.380 to −0.109 | 0 | 0.000 | yes | yes |
| September | 40 | −0.189 | −0.297 to −0.094 | 0 | 0.000 | yes | yes |

- **The control is informative.** On January to March the model beats a price set 14 days before resolution (probability positive 0.99). Most of that comes from the events it says it recognises (52 recognised events across the control's news and price strata, mean excess about +0.17). So it knows some outcomes from before its cutoff, as expected.
- **`BT_WINDOW_START` is 2026-07-01 under both gates.** June fails, so the earliest month from which every later month is clean is July. That matches the declared cutoff.
- **From July on, the model with no evidence loses to the price**, and by more each month (−0.10, −0.23, −0.19). That is what a model without knowledge of the outcome should do against a price set two weeks out.
- **The price-level stratum** (reported only) shows nothing like knowledge in any month after March.

## Why June fails: events that resolved months earlier

Every event in June and July that a session marked "recognised" actually resolved long before its scheduled end:

| Assigned month | Event | Actually closed |
|---|---|---|
| June | Paramount–Warner Bros. acquisition announced by June 30? | 2026-02-28 |
| June | U.S. × Iran military engagement by …? | 2026-02-28 |
| June | Khamenei out as Supreme Leader by June 30? | 2026-03-01 |
| July | Netherlands election: 4th-most seats; CDA seats; GroenLinks–PvdA seats | 2025-11-03 |

Months were assigned by scheduled end (registration §7 deviation 4), to avoid the early-YES selection found in `T0_BASE_RATE.md`. For a knowledge audit that was the wrong date to use: what the model could know depends on when the outcome happened, not on when the market was scheduled to end. June's failure is knowledge from February and March, not from after the cutoff.

## Sensitivity (post-hoc, declaring nothing): months by actual resolution

Each event is assigned to the month of the earlier of its scheduled end and its actual close.

| Month | n | Mean excess | Recognised | P(reaches half the control) | Clean at 0.5 and 0.2 |
|---|---|---|---|---|---|
| Control (resolved by March) | 127 | +0.119 | | | |
| April | 40 | −0.096 | 6 | 0.039 | yes |
| May | 45 | −0.016 | 2 | 0.105 | yes |
| June | 36 | −0.112 | 0 | 0.001 | yes |
| July | 34 | −0.170 | 0 | 0.000 | yes |
| August | 41 | −0.248 | 0 | 0.000 | yes |
| September | 37 | −0.137 | 0 | 0.000 | yes |

On this reading every month from April is clean under both gates, which would put the window at 2026-04-01 and roughly double the backtest sample. **It is post-hoc, so it does not move the window.** A second BT-A pass, registered with months by actual resolution and run on events not used here, would settle it (decision 5's multiple passes).

## Other readings

- **"Recognised" is a weak signal.** In April the six events the model claimed to recognise scored −0.61: it was confidently wrong. Self-reported recall is noisy in both directions, which is why the gate uses scores, not the flag.
- **The runtime leak did not create knowledge.** Every session saw today's date (2026-10-01) and its own identity. If knowing that time had passed let it recall outcomes, July to September would show it, and they show the opposite.

## What follows

- BT-T2 runs on locks from 2026-07-01 (loose and strict windows are the same here).
- The next BT-A pass, by actual resolution month, is the cheapest way to double the window. It is about 25 sessions for April to June plus a control re-check.
