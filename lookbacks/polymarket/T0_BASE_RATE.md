# T0 against the pool's base rate (2026-10-01, post-hoc)

Not registered; under R20 a hypothesis, not a result. Script `t0_base_rate.py`, data `t0_base_rate.json`. Read-only: each round's cached prices are copied to a temporary directory and nothing is fetched; the frozen scorer is used unchanged; no T0, V1 or V1b file is changed.

## Why this was run

The V1 pool admitted events by their **actual close time** after 2026-06-30 and locked each one halfway between its start and that close (`V1_prereg.md` A9). v18 §6.7 records what a close-time rule does: counted that way, "of 33 date ladders 31 closed early on a Yes rung". Seven of the nine "magnitude" claims behind T0's headline are "happens by a date" claims on the YES side of a date ladder. So the question is how much of T0's claim result the pool produces on its own.

## The base rate: every priced contract shown in V1 and V1b, with no claim

Each contract's YES side at its lock price, primary and menu, 41 rounds. Interval 90%, resampled by round.

| Event kind | Contracts | Mean lock price | Resolved YES minus price | P(positive) |
|---|---|---|---|---|
| Date ladder | 1,741 | 0.48 | **+13 points** (+12 to +15) | 1.00 |
| Date ladder, priced 0.05 to 0.60 (where the tiers landed) | 808 | 0.29 | **+18 points** (+14 to +21) | 1.00 |
| Numeric price ladder | 2,402 | 0.35 | +6 points (+3 to +8) | 1.00 |
| Touch ladder | 2,118 | 0.12 | −2 points | 0.01 |
| Exact partition | 1,435 | 0.14 | −2 points | 0.00 |
| Open partition | 4,648 | 0.10 | −1 point | 0.00 |

**Reading.** In this pool, any "happens by a date" contract bought at the lock beat its price by about 13 points, and by about 18 in the band where the tier mapping put claims. That is the pool's selection, not anyone's skill: an event admitted because it has already closed is, on a date ladder, mostly an event that happened early. Partitions and touch ladders show nothing of the kind.

## The claims against a matched base

Each claim's "then" is compared with every other contract of the same event kind, priced within 0.05 of its lock price, across all 41 rounds.

| Claims | n (rounds) | Claim: hit minus price | Matched base | Claim minus base | P(positive) |
|---|---|---|---|---|---|
| Tier claims, "if" happened, de-duplicated | 9 (9) | +45 points | +16 | **+30 points** (+13 to +48) | 1.00 |
| Named-contract claims, "if" happened | 5 (5) | −16 | −7 | −8 points | 0.25 |
| Tier claims, "if" did not happen | 36 (21) | −4 | 0 | −4 points | 0.27 |
| **Tier claims bought at the lock, either way** | 47 (26) | +8 | +3 | **+4 points** (−7 to +17) | 0.72 |
| Named-contract claims bought at the lock | 22 (15) | −4 | +2 | −6 points (−16 to +1) | 0.10 |

Of the nine tier claims whose "if" happened, seven are date ladders, one a numeric ladder and one a touch ladder.

## What this changes

1. **The conditional result survives the correction, at about +30 points on nine claims.** When the "if" happened, the session's "then" held far more often than other contracts of the same kind and price.
2. **The bettable result mostly does not.** Bought at the lock, before anyone knows whether the "if" happens, the tier claims beat the matched base by +4 points with an interval spanning zero. Most of the earlier +27% to +69% returns on tier claims (`t0_weightings.json`) is the pool's date-ladder base rate.
3. **So what the claims show is a link, not a forecast.** Sessions named pairs of events that move together. Profiting from that needs a calibrated view of whether the "if" happens (P(A)), which is what addendum B1 §5 already says. T0 gives no evidence on P(A).
4. **The timing reading needs care.** "Sessions are good at saying it happens sooner than the market thinks" is not supported once the pool's date-ladder base rate is removed. Whatever timing skill exists has to be shown on events chosen by schedule, as v18's backtests (§6.7) and the forward tests choose them.
5. **Any test drawn the V1 way inherits this.** Any statistic that compares a contract with its own price carries the base rate of the kinds it holds. That includes the hedge comparisons: a hedge holding date-ladder YES rungs gains the base rate over de-risking, which holds none. The post-hoc hedge figures (same-underlying +9.1, session against blind hedge +14.9; `EVALUATION.md`) have not been re-read against it. V1 and V1b's frozen verdicts were inconclusive either way.

## Limits

- Post-hoc and unregistered; nine and five claims.
- The matched base pools all rounds. It does not condition on the claim's "if" having happened, which is itself an outcome. A finer base (rungs in rounds whose primary resolved the same way) would need more rounds than exist.
- Prices are the 48-hour cached points the scorer used, so the base and the claims are priced the same way.
