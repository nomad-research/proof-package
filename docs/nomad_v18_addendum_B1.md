# Nomad v18 — Addendum B1: decisions taken, and claims added to 18.0

*2026-10-01, builder, on Rob's instruction: "make a good decision on all following my intent and decide if you want to go straight to 18.1 or add claims to 18 because there's something in there that we're good at." Applies on top of `docs/nomad_v18_updates.md`. Decisions here are taken by the builder under that delegation. Each one is recorded in `docs/RATIFICATIONS.md` as "decided under delegation" and stays open to Rob's reversal.*

## 1. Decisions (D33 to D43)

| Row | Decision | Why, against Rob's intent |
|---|---|---|
| D33 | Proceed on the Polymarket frame | Every test since 2026-09-30 already runs on it |
| D34, D35 | Adopted: positions are sized by log growth at a fraction of Kelly; a thesis is a subgraph | "edge is equivalent to risk"; "positions can be baskets but they are now implicit" |
| D36 | Adopted: beliefs are graded with a learned floor; no view, no position | Hard exclusions caused the worst loss in V1 (329566, −$54.9 against de-risking) |
| D37, D38 | Adopted: narrative coverage plus a two-layer graph | "creates a narrative and models around the narrative ... without needing to predict" |
| D39 | Adopted, with T0 extended (§3) | |
| D40 | **Structural coherence trades stay out**, diagnostic only, until T1 measures how often and how much linked prices disagree | Taking a position because prices disagree uses price as the reason (R6) |
| D41 | Adopted: read for direction first; strict bars only for money and ratification; `DIRECTION_PUSH` 0.80 | "all I see are failure modes with no direction" |
| D42 | Adopted: forward sessions may retrieve live public evidence; every page is stored and hashed; Polymarket and odds sites are blocked | Free public data; the session needs current facts |
| D43 | Adopted: the backtest rules of §6.7 | Results now, without waiting on horizons |

## 2. 18.1 or claims in 18.0: claims go into 18.0; 18.1 waits

**18.1 is not the next step.** Scenario log growth needs weights on joint scenarios. Nothing calibrates those yet: there are no authored probabilities on record and no resolved coverage sets. Sizing on uncalibrated weights is the failure v18 exists to avoid. 18.1 keeps its §11 trigger (a test shows edge).

**The claims are the one result benchmarked against price** (16 triggered: "then" held 12 of 16 against 47% priced; 10 of 14 against 48% de-duplicated). So 18.0 gets a second track, **18.0c**.

**R21 (proposed). A triggered claim is a conditional bet.**
- A claim is a graded causal edge "if A then B".
- When A resolves as stated **before** B resolves, the claim is triggered.
- At that moment Nomad's belief in B is the learned hit rate of triggered claims in B's stratum (§5.8 strata, plus claim kind: same-underlying or cross-entity). That belief is learned from the claims' own track record, prequentially, never from price (R6).
- The sizer compares that belief with B's price at the trigger, after costs, and sizes the binary Kelly bet of Appendix A2.
- Before A resolves, nothing is bet on the claim. 18.1 is what will later carry graded edges into beliefs before resolution.
- **Why this is the right first expression.** By A3, expected profit comes only from node-level belief minus price, and a conditional claim can only earn by changing a node belief. The trigger is the moment the claim changes B's belief without needing P(A). If B's price lags the resolution of A (the propagation premise, §4.3), that lag is the edge.
- **What it does not do.** It buys no conditional contract (none exist), takes no position before evidence, and never uses a price gap as the reason for a position (D40).

## 3. T0 additions (before anything is built)

Retrospective, free, run now on the V1 and V1b claims:

- **T0-c1, trigger lag.** For each claim whose "if" resolved as stated before its "then" contract closed, read the "then" price at the first price point after the "if" closed. Measure the hit rate against that post-trigger price. This is the 18.0c money test on existing data. If the post-trigger price already equals the hit rate, the market propagates instantly and 18.0c has no edge.
- **T0-c2, matched placebo.** For each triggered claim, take the other contracts shown to that session with a lock price within ±0.05 of the consequent's price (single side, the side so priced), under the same antecedent. Compare their hit − price with the claim's. This replaces the two-sided placebo, which is zero by construction.
- **T0-c3, de-duplication.** Each consequent contract is counted once per round.
- **T0-p, picks as coverage sets** and **post-mortems**, as in v18 §6.1.

## 4. Build order (supersedes v18 §11 steps 1 and 2 where they differ)

1. T0 (this addendum §3 plus v18 §6.1), then feasibility checks: Wayback and Wikipedia returned 429 from this container on 2026-10-01; GDELT and EDGAR answered; whether sessions can run without the date and model name.
2. The shared v18 packet, projection and scorer, with the claims track (R21) in the scorer from the start.
3. BT-A, then BT-T2. Their pre-registrations name 18.0c as a second statistic beside coverage.
4. T3 before 14 October, so V3's clusters can be reused; its C edges feed the 18.0c learning store.

## 5. After T0 (2026-10-01): the claims track moves from trigger to lock

T0 (`lookbacks/polymarket/T0_RESULT.md`) confirmed the claims and ruled out the trigger trade:
- Triggered claims beat their lock price by +24 points and a matched placebo by +22 points (P 0.98 and 0.96).
- After the "if" closed, the "then" price had already moved most of the way within about 1.3 hours.
- Half the "then" contracts resolved first.

**18.0c is therefore a pre-resolution claim bet:** belief(B) = P(A)·P(B|A) + (1 − P(A))·P(B|not A), sized against B's price at the lock.
- P(B|A) and P(B|not A) are authored graded C edges, recalibrated from the claims record.
- P(A) is an authored graded node belief.
- 18.0c places no bet until T2 or T3 shows those authored probabilities are calibrated (direction ≥ `DIRECTION_PUSH` on their log score).

**Packet change for T2, T3 and the BT tests:** every C edge must carry both branches (if A, and if not A), and every node in a claim must carry a graded P.

R21 is amended to match. The trigger rule is kept as a descriptive statistic only (T0-c1, 6 tradable claims, P 0.65).

## 6. Each subgraph is a basket (Rob, 2026-10-01)

Rob: "the basket is the set of positions that comprise the subgraph, it is each subgraph." And: "basket isn't sizing."

- **One thesis subgraph, one basket.** A basket is *which* positions: the contracts of that subgraph and the side the thesis takes on each. It says nothing about how much.
- **Links are never traded alone.** An edge is structure inside a subgraph; it decides what the basket holds.
- **Claims** are edges inside subgraphs, carrying both branches, scored for calibration. R21's trading rule (§2, §5) is superseded. The packet requirement of §5 stays.
- **Scoring and evidence.** A basket is scored as a unit once every contract in it has resolved, unsized (each position at one unit, hit minus all-in cost). Tests count baskets, not legs.
- **Sizing is not decided.** It has not been discussed with Rob. v18 §5.5 (Kelly, `KELLY_FRACTION`, the event and cluster caps) and every sizing value in §7 are suspended as proposals, not built, until that discussion. No test depends on sizing.

**Open, for Rob:** whether two baskets may hold the same contract (the 2026-09-30 intent of a hedge as a parallel thesis suggests yes; "independent subgraphs" suggests no).
