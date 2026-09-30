# V1 — does a thesis-first constructed hedge do better than the alternatives on resolved Polymarket contracts? Pre-registration

*Written 2026-09-30, before any scored round exists. Values below are builder-proposed, `provisional_unratified`, and open to Rob's amendment until the first round is authored. After that they are frozen. D33 is not ratified; this file does not depend on it.*

## 1. Question
Rob's mechanism: a hedge is built thesis-first (a narrative about why the primary basket could fail, then a hedging basket fitted to that narrative), long-only, with no shorts and no funds. On exact payoffs, does that construction give a **higher floor at equal cost of upside** than (a) plain de-risking and (b) a blind hedge, and is the effect absent when the narrative is removed? V1 does **not** test probabilities (that is V2) and does **not** use Prediction Prophet or Laya.

## 2. Pool (fixed before any round is drawn)
Closed events, end date after **2026-06-30** (after the operator model's declared training cutoff), classes from `CENSUS_SPEC.md`: exact partition, partition with an open slot, threshold ladder (terminal price) and touch ladder ("reach", "dip", "hit"; nested on each side separately, never across sides), in the groups geopolitics, politics and elections, economy and finance, technology and science, business and manufacturing, crypto. Usable = event volume ≥ $100k and ≥ 3 markets ≥ $10k. The pool list is frozen by hash before drawing (`v1_pool.json`, hash written into §9). **Keys are condition ids, never question text.** Contracts sharing text under different condition ids are separate keys; placeholder slots ("Party A", "Company B", "Option C", "Other") are typed gaps.
**Eligibility (declared before drawing):** every contract used has a price point on or before the lock, and resolved cleanly (`umaResolutionStatus` resolved, not disputed, both outcomes accounted for). Exclusions are counted and listed. Disputed rounds go in as a labelled sensitivity.
**Draw:** a seeded random draw (seed 20260930) of **24 primary structures**, at most 8 from crypto, at least 4 partitions. Builder has seen titles and volumes of the pool, **not outcomes**.

## 3. A round
1. **Lock** = the midpoint between the event's start and its resolution.
2. **Packet** (built by a script, hashed): for the primary event, its rules text and contract list; a menu of up to 60 other events that were live at the lock (seeded, same groups), each with its rules text and contract list. **No prices, no volumes, no outcomes, no resolved flags, no dates after the lock.**
3. **Cold sessions** (declared operator model `claude-opus-5-5`, trained through 2026-06-30, fresh, no shared context) author, in order and without seeing each other: **(i)** a primary thesis and basket (long-only shares, YES or NO, from the primary event); **(ii)** the primary's failure narrative; **(iii)** a hedge thesis over the failure narrative, a hedging basket from the menu, and the **declared reachable set** (which outcome combinations the session claims cannot both occur, with the reason). Sessions receive no tools. **Enforcement:** transcripts are audited; a round in which a session made any network call or tool call outside the packet is voided and re-authored by a fresh session (count reported).
4. **Prices enter only after authoring.** Entry price = the price-history bucket at or before the lock **plus a slippage of 0.01** (sensitivity 0.00 and 0.03), the same for every arm. Fees: each market's own `feeSchedule` (shares × rate × p(1−p), taker only). Budget: **$100 of outlay** per arm, sized by the script (linear program), not by the session.
5. **Score** on the resolved outcomes: exact payoff of each contract (1 or 0 per share), summed.

## 4. Arms (same $100, same pool, same fees)
- **P**: the primary basket alone.
- **C**: constructed. P plus the hedge basket, weights from the maximin over the declared reachable set (the exact-payoff table; `hedgedag.maximin`). Its **floor** = the worst payoff over the reachable set.
- **D**: plain de-risking. P scaled down (rest in cash) until its floor equals C's floor. This is the equal-floor comparator.
- **R**: random hedge. Same number of hedge contracts and budget as C, drawn 200 times from the menu, weights by the same maximin. Reported as a distribution.
- **M**: mismatched thesis (null control). The hedge thesis and basket authored for a different round's primary is applied to this round's primary by the same script (fixed cyclic shift by one).
- **B**: blind statistical hedge. Contracts in the menu with at least 30 price points in the 60 days before the lock, chosen for lowest correlation with P's, minimum-variance weights. **Available only where history allows; if fewer than 12 rounds can have B, B is reported as infeasible and dropped from the bar.** Expected to be sparse: closed-market history comes back thin.

## 5. Failure and floor definitions (V1-local; `FAILURE_LOSS_PCT` and `BASKET_N_MAX` stay unset in the appetite file)
- **Primary fails** in a state if P's payoff in that state is below −$10 on $100 (V1 value: 10%, provisional).
- **Basket N cap** (V1 value): at most **6** hedge contracts per round, provisional.
- **Retention:** the share of P's realised upside that C keeps in rounds where P finished above +$10.

## 6. Bar (declared now, the same rules for every round)
Gates: at least **20** scored rounds; at least **10** in which P realised a loss of more than $10. Below either gate: **inconclusive**, not passed or dead.
- **B1 (the floor is honest).** Realised outcome inside C's declared reachable set in at least **90%** of rounds. Below 90%: **dead** (the constraint claims are unreliable, and the floor means nothing).
- **B2 (dominance at equal floor).** Paired difference in realised payoff, C minus D, across all scored rounds: mean > 0 and the **90% bootstrap** lower bound > 0.
- **B3 (null controls).** The same statistic for **M** has a 90% interval that includes zero or lies below it, **and** C's realised payoff exceeds the **median of R's draws** in at least **65%** of rounds.
- **B4 (retention).** Mean retention ≥ **0.5**.
- **Verdict:** pass = B1 and B2 and B3 and B4. Dead = B1 fails, or B2's mean is ≤ 0 with the gates met. Otherwise inconclusive. **B** is reported beside the bar and gates nothing unless feasible (then C must also beat B's mean).
- A pass means the **construction is worth continuing on**; it is not evidence of profit, and it is not a licence for real money.

## 7. What is reported whatever the outcome
Every round (packet hash, transcripts, baskets, floors, realised payoffs); exclusions and voids; sensitivities (slippage 0.00 and 0.03, disputed rounds in, crypto out, the second-half rounds alone); the distribution of R; per-round C minus D; which failure narratives were right and which reachable-set claims were violated and why.

## 8. Disclosures
- The V1 class was chosen after the census; builder and Rob saw class counts.
- Slippage and the price-history bucket are approximations: Polymarket keeps no historical books and closed-market history comes back in coarse buckets. No claim about fills.
- Rules text is read as stored now; it may have been edited after the lock. Rounds where a rule edit is visible in the recorder's versions are flagged.
- The operator model's cutoff is declared, not verified. A round where a session's transcript shows knowledge of the outcome is voided and counted.
- The builder ran the pilot in §10, on events not in the pool; nothing from it counts.

## 9. Freeze
Frozen at the commit that carries this file, plus the pool hash (`v1_pool.json`, sha256 recorded here before drawing): *not yet computed.* Scripts (`v1_pool.py`, `v1_score.py`, `v1_packet.py`) are frozen at the commit that introduces them; no round is authored before that commit.

## 10. Pilot
One end-to-end run on a single closed event **not in the pool** (ended before 2026-06-30), authored by the builder, not a blind session. It tests the arithmetic and the data path only. Nothing from it counts (`PILOT_V1.md`).
