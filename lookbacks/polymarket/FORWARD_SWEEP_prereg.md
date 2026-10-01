# Forward sweep: E1 and E3 on events nobody knows the outcome of (registration, written before the first batch)

This tests two edges forward, on open markets:
- **E1:** the model's NO picks beat same-side, same-price contracts (`BT_T2_pass2_RESULT.md`: direction only; pooled +3.4¢).
- **E3:** the same on mention markets (`E3_MENTIONS_RESULT.md`: edge shown, +7.3¢, concentrated).

Decision 7 asks for confirmation forward before any design leans on either. This file is committed before the first batch's snapshot.

## 1. A batch

| Step | Rule | Based on |
|---|---|---|
| **Snapshot** | Open events from Gamma, scoped as T3's snapshot: lifetime volume of $10,000 or more and the crawl's scope filter. Only events whose open markets all end within **14 days** of the snapshot | BT-T2's holds: median 4.5 days, upper quartile 7.4 days. 14 days covers most of that, and every batch resolves within two weeks |
| **Excluded** | Events in T3's clusters, which are dependent and scored there; events drawn in an earlier batch; maker-excluded events (BT-A's rule); events whose open markets give no session format | |
| **Drawn** | **Every eligible mention event** (title matches `\bsay\b\|\bmention`, as E3), then others at random to make **102 events** (17 sessions of 6) | Mention events are few, about 5 a week in the backtest crawl, so all of them are kept. 102 events a week is about the reading rate assumed in `docs/CAPITAL_READING_2026-10-01.md` |
| **Session** | BT-T2's cold prompt and format, as of the snapshot date. Price-blind, no evidence, the paged instruction | The edges were found cold. A retrieval arm is T3 |
| **Audit** | BT-T2's: V1's transcript audit, with the line-number read check (pass 2 addenda A1 and A2) | |
| **The lock** | The hand-back. The best ask for YES and for NO is read from the order book at ingest, with the dollars on offer within 1¢ and 2¢ (as T3) | |
| **Freeze** | Each batch's answers and lock asks are frozen by hash and committed right after ingest | |

## 2. Scoring (as contracts resolve)

- **Cost.** The ask at the lock plus the taker fee (`exact.share_cost` with no slippage), because the ask is a price someone can actually be filled at.
- **Excluded from scoring:**
  - a contract with no ask on that side;
  - a contract that closed before its session's lock.
- **Positions.** A NO position is taken where the session's chance of NO (one minus the upper bound of its YES chance) is above the cost of NO. YES positions are taken likewise.
- **E1 forward (registered).** Each NO position scores (hit − cost) minus the mean (hit − cost) of the NO side of every other resolved sweep contract (all batches pooled) that has:
  - the same session format;
  - a NO cost within 0.05;
  - a different event.

  Resampled by event, 4,000 draws.
- **E3 forward (registered).** The same, restricted to mention events, with the comparison drawn from mention contracts only.
- **Looks, so that watching a growing sample does not inflate false positives.**

  | Statistic | First look | Second look | Based on |
  |---|---|---|---|
  | E1 | 400 resolved events with a NO position | 800 | Pooled BT-T2 E1 had a standard error of about 1.9¢ on 242 events. At +3.4¢ the lower bound of a 97.5% interval clears zero at about 380 events. At pass 2's +2.6¢ it needs about 800 |
  | E3 | 50 resolved mention events with a NO position | 130 | E3's backtest standard error was about 2.9¢ on 46 events. At +7.3¢ about 40 events suffice. At +3.8¢ (without its top three events) about 130 |

- **Reading at each look:**
  - **Confirmed** if the 97.5% interval is above zero.
  - **Killed** if it is below zero.
  - Otherwise carried to the next look.

  Two looks at 97.5% keep the chance of a false confirmation under 5% (Bonferroni). After the second look the sweep keeps running as a ledger without declaring.

## 3. Secondary (declaring nothing)

- NO money (hit − cost), and the same for NO priced 50¢ or more.
- Blind NO on every contract.
- YES positions against same-side contracts.
- By session format and by speaker group (E3's rule).
- **Capacity.** Money per position if each were sized at the lesser of $150 and the dollars on offer within 2¢ of the ask. This is the first forward reading of C7 (execution).
- The log score against the lock ask's midpoint, where both sides have an ask.

## 4. Cadence and integrity

- **One batch a week.** Batch W01 runs on 2026-10-01.
- **Scheduling.** Running it as a scheduled task is persistent configuration and needs Rob's word. Until then, a batch runs whenever a session is open.
- **Model and harness.** Sessions are cold `claude-opus-5-5` subagents, as in BT-T2. The runtime shows them the date and the model name, which is harmless forward.
- **Staleness.** Forward, the model is about four months past its training cutoff, against one to three months in the backtests. If E1 rests on base rates it should survive this. If it rested on recent knowledge, it will fade, and that is part of what the sweep tests.
- **Budget.** About 17 sessions a week at about 80,000 tokens each.
