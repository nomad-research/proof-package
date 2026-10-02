# BT-A pass 2: months by actual resolution (registration, written before the draw)

BT-A's first pass set `BT_WINDOW_START` at 2026-07-01. June failed only on events that had actually resolved in February and March (`BT_A_RESULT.md`). Post-hoc, with months assigned by actual resolution, every month from April was clean under both gates.

This pass registers that reading and tests it on fresh events. If April to June are clean, backtests registered after this result may lock from 2026-04-01, which roughly doubles the window. That gives E1 and E3 a second backtest pass on events no test has used (decision 5: multiple passes).

Same design, script, prompt, audit and gates as `BT_A_prereg.md` with addenda A1 and A2, except as stated here. Committed before any event is drawn, any session runs or any outcome is read.

## 1. What changes

| | First pass | Pass 2 | Why |
|---|---|---|---|
| **Month of an event** | Scheduled end | **The earlier of scheduled end and actual close** | What the model can know depends on when the outcome happened (`BT_A_RESULT.md`) |
| Months drawn | January to September | **Control January to March; tested April to July** | August and September were clean by a wide margin under both readings. July is kept so that the window rule ("every later month clean") is tested across the boundary |
| Events | 40 news and 10 price-level a month | **40 news a month**; no price stratum | The price stratum was reported only and showed nothing |
| Excluded | — | Every event drawn in BT-A pass 1, BT-T2 passes 1 and 2, and E3 | Fresh events |
| Seed | 20261001 | 20261007 | A fresh draw |
| Output | `bt/audit/` | `bt/audit_pass2/` | Kept apart |

The price time stays 14 days before the earlier of scheduled end and actual close, as in the first pass. So the month and the price time now rest on the same date.

## 2. Reading

- **Score, control and gates as before.** The score is log(the session's probability on the realised side ÷ the price), averaged per event. The control is January to March. A month is clean if P(the month's mean reaches half the control's) is at most 0.5 (loose) and at most 0.2 (strict). These are decision 5's gates.
- **The window.** `BT_WINDOW_START` is the first tested month from which every later tested month is clean. August and September stand on the first pass.
- **If the control shows no recall** (mean excess not above zero), the gate cannot be calibrated and the window stays at 2026-07-01.

## 3. What follows from each result

| Result | Consequence |
|---|---|
| April to July clean (loose) | Backtests registered from now on may lock from 2026-04-01. The first such pass: E3 on April to June mention events, then E1 |
| Clean from May or June | The window moves to that month |
| July or later only | The window stays at 2026-07-01 |

## 4. Budget

About 280 events (7 months × 40) in 28 sessions of 10, about 2.5 million subagent tokens.
