# BT-T2: single events, backtested, in the graded format (registration, written before the frame is built)

v18 §6.3 and §6.7, with the session format of `docs/DECISIONS_2026-10.md` decisions 4 and 6 (tentative) and the reading rule of decision 7. Script `bt_t2.py` (written after this file). Committed before any (event, lock) is listed, any session runs or any outcome is read.

## 1. The question

At a lock inside the clean window, with no evidence beyond each event's rules, does the session's graded view beat the market's price?
- **Money and skill:** do bets where the view differs from the price, net of costs, beat contracts of the same kind and cost?
- **Magnitude:** is the session's central value closer to what happened than the market's?

This first pass is the **no-evidence arm**: the session has the rules text and its own knowledge, which runs to its declared cutoff of 2026-06-30. The arm with the point-in-time evidence bundle (v18 §5.9) is a later pass, registered separately.

## 2. Population: by schedule, never by outcome (v18 §6.7)

| Rule | Setting | Basis |
|---|---|---|
| Frame | The BT-A crawl (`bt/closed_2026-01-01_2026-10-01_v10000_scoped.json.gz`) | One shared, hashed input |
| Window | Locks from BT-A's **loose** `BT_WINDOW_START` (decision 5) to 2026-09-30, the data date. The confirming pass uses BT-A's **strict** window | Decision 5 |
| Lock grid | Every 7 days from the window start, at 12:00 UTC | `BT_LOCK_STEP` 7 (v18 §7); the hour is fixed arbitrarily, before data |
| Open at the lock | Event created at or before the lock; markets created after the lock removed; markets already closed at the lock removed | v18 §6.7 rule 4 |
| Horizon | The latest scheduled end of the markets open at the lock is at most 75 days after the lock and on or before 2026-09-30 | `T2_HORIZON_DAYS` 75 (v18 §7); the data date |
| Clean | Resolved cleanly (V1's rule); nothing about Anthropic or Claude; no leak flag in the text (V1's scan) | As BT-A |
| Priced at the lock | A contract is shown and scored only if it has a price point within 48 hours before the lock and at least 10 points in the 7 days before it | V1 A2; `BT_MIN_POINTS` 10 |
| Strata | **Multi-market:** at least 3 priced open contracts. **Binary:** a single-market event | `T2_MIN_OPEN_MARKETS` 3 (V3 A3); v18 §6.7 keeps binaries separate |
| One lock per event | Drawn by seed from the event's eligible locks. The other locks are a dependent analysis, reported separately | v18 §6.7 rule 2 |
| Size | Every eligible event, up to 180 per stratum. Above that, a seeded draw | Token budget: 30 sessions of 6 is about the 2.6 million tokens V3 used |
| Seed | 20261002 | |

Lifetime volume is reported as a sensitivity only.

## 3. What a session writes (decision 6, tentative)

The session sees each event's title, rules and contract questions under opaque labels, and an "as of" date (the lock date). It sees no price, volume, id, close time, resolution status or outcome. It has no tools beyond reading its prompt. Six events per session, shuffled across strata.

| Event | The session writes |
|---|---|
| Partition (one outcome wins) | A whole percent per listed outcome, adding up to about 100 |
| Terminal ladder ("X above k on date d") | The levels it gives a 10%, 25%, 50%, 75% and 90% chance of being at or above at resolution, in the units of the rules |
| Touch ladder ("X reaches k by d") | For each side the ladder has: the levels it gives a 10%, 25%, 50%, 75% and 90% chance of being reached |
| Date ladder ("X by d1, by d2 ...") | The dates by which it gives X a 10%, 25%, 50%, 75% and 90% chance of having happened; "not within the horizon" for a chance it does not reach by the last date |
| A single yes/no contract with a deadline ("by d") | As a date ladder: dates at the five chances |
| Any other yes/no contract, including a group of contracts that share one deadline | A whole percent |
| Every event | `recognised`: true if it believes it remembers the real outcome |

A group of yes/no contracts sharing one deadline gets a percent each, because time as the scale only says something where the dates differ. This is an implementation choice under decision 6, recorded here.

**Validation:**
- every label answered;
- percents from 1 to 99;
- levels and dates in the right order across the five chances;
- dates within the horizon or marked "not within the horizon".

An answer that fails is re-authored by a fresh session with the same prompt, and counted.

**The recall flag voids** the (event, lock), counted (v18 §6.7 rule 7).

## 4. From a view to a chance on each contract (fixed here, before data)

- **Percents** are the chance.
- **Levels and dates:**
  - **Between two stated values**, a rung's chance is interpolated linearly in the value, or in time for dates.
  - **Beyond the 10% value** a rung's chance is known only to be below 0.10. Short of the 90% value it is above 0.90. A date after the last stated date and before "not within the horizon" sits between the two chances.
  - **No tail number is invented.** A bounded chance is used as a bound (§5) and, only in the secondary log score, at the bound's midpoint.
- **"Below k" and "dip to k" rungs** take the complement or the low side, as their question reads (V1's `orient`).

## 5. Scores

Prices at the lock come from the public history (V1's 48-hour rule), used for costs and scoring only. **All-in cost** = price + 0.01 slippage, rounded up to the tick, plus the market's own fee (`exact.share_cost`, as V1).

**S1, money and skill, the main statistic (v18 §5.6, unsized as B1 §6).**
- **Positions.** On each scored contract:
  - buy YES if the session's chance (or its lower bound) exceeds the all-in cost of YES;
  - buy NO if one minus its chance (or one minus its upper bound) exceeds the all-in cost of NO;
  - otherwise hold nothing (R18). One share each.
- **Money:** hit minus all-in cost, averaged over an event's positions.
- **Skill:** each position's (hit − cost) minus the mean (hit − cost) of every other priced contract in the frame at the same lock, of the same event class, on either side, whose cost is within 0.05. That removes the market's own calibration and any base rate of the class at that price. The pool's date-ladder base rate (`T0_BASE_RATE.md`) is the reason it matters.
- **Read (decision 7):** edge is shown if the 95% interval of mean skill, resampled by event (4,000 draws), lies above zero; shown absent if it lies below.
- **Chances are taken as stated** on this first pass, since there is no resolved history to relabel from (decision 6). The money and skill figures are marked accordingly.

**S2, magnitude, scored apart from calibration (decision 6).**
- **The market's central value.** For each scaled variable (a terminal ladder, each side of a touch ladder, a date ladder, a deadline binary), the market's implied 50% value: where the rung prices cross 0.5, linear between rungs, after making the rung prices monotone (pool-adjacent violators). A crossing beyond the outermost rung is "beyond" on that side.
- **The comparison.** Is the session's 50% value closer to the realised outcome than the market's?
  - The outcome is known only to the interval between the rungs it fell between, so distance is measured to that interval.
  - Equal distances are ties.
- **Statistic:** (session closer − market closer) ÷ scaled variables, with a 95% interval by event. It reads only the session's central value against the market's, so wrong chance labels cannot move it.
- Declared at 5% like S1. With two declared statistics, the chance that at least one is a false positive is about 10%; the confirming passes are the guard.

**Secondary, declaring nothing:**
- **Calibration.**
  - For levels and dates: the share of outcomes at or beyond each stated value, against the chance it was given, wherever the outcome interval decides it.
  - For percents: the share YES in 10-point buckets.
- **Log score:** log(chance ÷ price) on the realised side of each contract, bounded chances at their midpoint (v18 Appendix A1).
- **The T0 baseline (decision 2):** on each scaled variable, the side of the market's central value where the session's central value lies. Buy the rungs on that side whose prices are nearest 0.50, 0.25 and 0.10 (V1's targets, frozen). Score with S1's money and skill.
- **Breakdowns:** stratum, event class, domain, cost band, and loose against strict window. Each is a hypothesis for the next pass (v18 §6.0).
- **The dependent analysis** over every eligible lock per event.

## 6. Integrity

As BT-A §6 and §7:
- cold `claude-opus-5-5` subagents with one instruction;
- prompt files outside the repository;
- answers taken from the transcript's hand-back;
- V1's audit on every transcript;
- a session that makes any tool call other than reading its prompt is void;
- every answer hashed into a manifest before any outcome is read.

Known deviations are the same as BT-A's:
- the runtime shows today's date and the model name;
- the auto-memory index is injected;
- the hook does not run here.

**The date leak matters more here.** The packet says "as of" the lock date while the runtime shows 2026-10-01. The session can therefore tell that the outcome exists, though its knowledge stops at its cutoff. The recall flag and BT-A are the guards.

## 7. What follows

- A first-pass edge (S1 or S2) is confirmed only by holding on the strict window and on forward data (decision 5).
- Each week a walk-forward batch adds the locks whose scheduled ends have passed (v18 §6.7, rolling). It is registered as a new batch, so this sample's reading never moves.
- After this pass, the evidence arm is registered once the bundle exists.

## Addendum A1 (2026-10-01, before the frame is built, before any session or outcome)

Found while writing the script. No data had been read.

1. **Size, corrected.** §2 said "up to 180 per stratum" but costed 30 sessions of 6, which is 180 events in total. The rule is **up to 90 events per stratum** (180 in total, 30 sessions), with a seeded draw within the stratum above that.
2. **The matched base for S1's skill is pooled across the frame.** It is every other drawn event's priced contracts at their own locks, of the same event class, with cost within 0.05, excluding the event itself. With one lock per event, a base taken "at the same lock" would hold a handful of contracts.
3. **How the one lock per event is drawn.** The event's locks that pass the schedule rules are put in a seeded order. The first that also passes the price rules (§2) is its lock. That is a draw by seed that never reads an outcome, and it fetches prices only for locks that are tried.
4. **Price history requests.** The public endpoint answers a 400 for windows longer than about 15 days, which V1's helper reads as "no history". Every fetch here is a 7-day window ending at the lock (the `BT_MIN_POINTS` window), at 60-minute fidelity, falling back to 12-hour.

## Addendum A2 (2026-10-01, after a first frame build, before any session or outcome)

The first frame build admitted markets whose scheduled end had already passed at the lock but which had not yet closed, because resolution was pending. An example is "… by June 30?" at a 1 July lock. Their outcome was already fixed at the lock, at the model's cutoff. A market is now open at the lock only if it has not closed **and** its scheduled end is after the lock. The frame was rebuilt; the first build is discarded. No outcome was read in either build.
