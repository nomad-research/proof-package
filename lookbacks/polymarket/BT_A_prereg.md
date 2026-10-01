# BT-A: the cutoff audit (registration, written before the draw)

v18 §6.7. Script `bt_audit.py`; crawl `bt_crawl.py`. Committed before any event is drawn, any session runs or any outcome is read.

## 1. The question

The operator model (`claude-opus-5-5`) declares a training cutoff of 2026-06-30. Backtests treat any lock from `BT_WINDOW_START` on as out of sample. BT-A checks that, month by month: does the model, with no evidence and no prices, know how events turned out?

## 2. What a session does

A cold session gets up to 10 events. For each it sees the event's title, its rules text and each contract's question, under opaque labels (E1, E1.C1, ...). It sees no price, volume, liquidity, id, resolution status or outcome.

For every contract, the session gives a whole percent from 1 to 99 that it resolves YES. It also says, per event, whether it recognises how the event actually turned out (`recognised`). Whole percents keep every probability strictly between 0 and 1 (R17), and the instruction sets that resolution.

## 3. Sample (all values fixed here; none is read from data)

| Value | Setting | Basis |
|---|---|---|
| Months | January to September 2026, by **scheduled end** (`endDate`) | `BT_AUDIT_FROM` 2026-01 (v18 §7) to the data date |
| Positive control | January to March 2026 | v18 §6.7 |
| Frame | `bt_crawl.py` output: closed events with a scheduled end in the months, lifetime event volume at least $10,000 (API prefilter), out-of-scope tags and intraday "Up or Down" events dropped at crawl time | The $10k floor is the census's binary floor and V1's per-market floor; the scope list is V1's `EXCL` |
| Exclusions | Not resolved cleanly (V1's rule: every market resolved, decisive, undisputed); anything mentioning Anthropic or Claude (v18 §6.7 rule 6); any event whose text trips V1's leak scan | As cited |
| Price time | 14 days before the earlier of the scheduled end and the actual close | v18 §6.7 says 14 days before resolution. Taking the earlier of the two keeps the price before resolution for events that closed early |
| Contracts scored | Those existing and open at the price time, with a price point within 48 hours before it and at least 10 price points in the 7 days before it; at most 12 per event, in display order | V1 A2 (48 hours), `BT_MIN_POINTS` 10 (v18 §7), V1's cap of 12 |
| Strata | **news** (gated) and **price-level** (reported only): price-level if the event carries any of the tags listed in `bt_audit.PRICE_TAGS` (crypto and stock price, hit-price and finance tags) | Knowledge of news after the cutoff is the threat the gate is for. A month of mostly price-level ladders would look clean even if the model knew its news, so the gate rests on news events only |
| Per month | 40 news events and 10 price-level events, drawn by seed from the eligible pool in shuffled order | 40 is v18's `BT_AUDIT_N`; 10 is one session's worth |
| Seed | 20261001 | |
| Events per session | 10, shuffled across months and strata | v18 §6.7 |

**On power.** 40 news events a month is v18's starting value and fits a budget of about 45 sessions. The gate is an integrity check, and low power can only make it stricter. A small sample widens a month's interval, which puts more of it at or above half the control, which makes the month fail. An underpowered audit therefore shrinks the window; it cannot admit a contaminated month.

## 4. Score

- **Per contract:** log(p ÷ q) on the realised side. If the contract resolved YES, p is the session's probability and q the YES price at the price time. If it resolved NO, they are 1 − p and 1 − q. q is floored at 0.001, Polymarket's smallest tick.
- **Per event:** the mean over its scored contracts. This is v18's "probability on the realised outcome ÷ its price" applied contract by contract, so ladders and partitions are scored the same way.
- **Per month and stratum:** the mean over events, with a 90% interval from 4,000 bootstrap draws over events.

A model with only general priors and no evidence should not beat a price set 14 days out. A model that knows the outcome beats it by a lot. The positive control shows what knowing looks like for this model.

## 5. The gate and the window

- **`BT_AUDIT_GATE` is Rob's value** (components register Part 2), set before `score` runs. v18's starting value is 0.2. The score command refuses to run without it.
- A news month from April to September is **clean** if the probability that its mean excess reaches half the control's mean is at most `BT_AUDIT_GATE`. That probability comes from the joint bootstrap of the month and the control.
- **`BT_WINDOW_START`** is the first day of the earliest month from which every later month is clean. It may land before or after 2026-07-01.
- **If the control shows no recall** (its mean excess is not above zero), the gate cannot be calibrated. Then the declared cutoff stands, labelled unaudited, and nothing is moved.
- **Secondary, gating nothing:** the price-level stratum by month, and the `recognised` rate by month.

## 6. Integrity

- **Session runtime.** Sessions are cold Claude Code subagents on `claude-opus-5-5`. Each is sent one instruction: read the prompt file, which sits outside the repository, and answer. The answer is taken from the session's own hand-back in its transcript. V1's audit (`v1_run.audit_transcript`) runs on every transcript.
- **The audit.** Any tool call other than reading the prompt file voids the session, as does any assistant turn not on the declared model. A voided or invalid session is re-authored by a fresh session with the same prompt; every re-authoring is counted.
- **Freeze before score.** Every answer is hashed into a manifest before `score` reads any outcome.

## 7. Known deviations from v18 §6.7, recorded rather than hidden

1. **The runtime shows the date and the model.** Subagents see today's date (2026-10-01) and their model name and declared cutoff. v18 rule 6 wants both hidden through direct API calls with a fixed prompt, and this machine has no API key. The leak is the same for every session, so it is recorded once here and in each session's record.
2. **Subagents receive the builder's auto-memory index** (`MEMORY.md`): notes on the parked equity harness, no Polymarket outcomes. Nothing about any test's outcomes is written to memory while sessions run.
3. **The PreToolUse hook does not run on this machine.** Its command is `python3`, which resolves to the Microsoft Store stub, so it fails as a non-blocking error. The transcript audit is the enforcement, as it was in V1.
4. **Months are assigned by scheduled end, not by actual resolution.** A close-time rule over-selects events that resolved early, mostly on YES (v18 §6.7; `T0_BASE_RATE.md`).
5. **Invalid answers are re-authored by a fresh session** rather than returned once to the same session.

## 8. Budget

About 45 sessions of 10 events each. A session's fixed overhead measured about 72,000 tokens on this machine (pipeline check, 2026-10-01); a 10-event prompt adds roughly 5,000 to 15,000. Token counts are reported after the run, from the audits.

## Addendum A1 (2026-10-01, before the draw, before any session or outcome): the gate

Rob set the gate (`docs/DECISIONS_2026-10.md`, decision 5): "Looser first and we will do multiple passes to confirm the edge for now."

- **Loose, the first pass: `BT_AUDIT_GATE` = 0.5.** A month is clean if it is more likely than not that its mean excess falls short of half the control's. This window is the one backtests run on first.
- **Strict, the confirming pass: 0.2** (v18's starting value). The audit reports this window too.
- A backtest edge found on the loose window counts as confirmed only if it also holds on the strict window and on forward data (decision 7: the 95% interval above zero).

`score` takes no gate argument now; both values are fixed in `bt_audit.GATES`.
