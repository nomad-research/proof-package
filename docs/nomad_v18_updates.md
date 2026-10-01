# Nomad v18 — Updates Specification

*Proposed, 2026-10-01. Written against `standard-reference/Nomad-Research`, branch `ccr-1eed6fb5-w9uiin` (PR #20), head `2be8835` (2026-10-01 00:50 UTC, "Evaluation of the evidence"). This is an update set on top of v16 (`docs/nomad_system_spec_v16_final.md`), v17 (`docs/nomad_v17_open_entity.md`), amendments A1 and A2, and the Polymarket frame (D33, `docs/nomad_polymarket_frame.md`). It is not a full re-specification. Everything not named here stands as written. **Revised the same day to add backtests (§5.9, §6.7)** so results arrive now, not only when forward contracts resolve.*

*Names: R14 to R20 are proposed rules (R16 is a rule; R16-001 is the one v16 round). "PM-V1" and "V1" mean the Polymarket hedge study, not v17's phase V1. "V1_prereg A10" names an amendment of that study.*

*Status words used throughout: **proposed** (written down; Rob has not ratified), **builder-set** (a value chosen by the builder, `provisional_unratified`, learning-class under the existing appetite rule), **Rob** (his own words, quoted). Nothing in this file is ratified. Section 12 lists the rows to ratify.*

---

## 0. In one page

**The problem we are attacking.** Nomad makes money only where its probabilities, formed at the lock without seeing price, are *less wrong than Polymarket's price*. Everything else (hedging, baskets, risk limits) is how that difference is sized and combined. If there is no such difference anywhere, the honest output is "bet nothing", and that is a finding.

**What changes.**

1. **Edge and risk are one quantity.** The long-run growth rate of a bankroll sized by Nomad's beliefs equals how far the price is from the truth minus how far Nomad is from the truth (Appendix A1). Edge is that number when Nomad is closer; risk is the same number when it is not. So risk is sized, not gated.
2. **One objective replaces the gates.** For event contracts every position is sized by expected log growth under Nomad's beliefs, after costs, at a fraction of Kelly. A zero size is derived (no growth left after costs); it is not a veto. The only gates left protect integrity: the time wall, R6, the ledger, logical impossibility read from rules text, and scope.
3. **A thesis is a subgraph; positions are implicit.** Events are nodes, typed dependencies are edges, and a thesis is a connected subgraph with a joint belief. The basket is what the sizer returns over every contract in the live subgraphs. There is no primary and no hedge; hedging is a property of the solution.
4. **Two layers.** A **world graph** over the whole open set (structure only, no probabilities, rebuilt daily) and **thesis subgraphs** where Nomad has read something and holds a view. No view, no position.
5. **Narratives cover; they do not pick.** Sessions write several narratives per cluster in parallel. Nomad covers the union of what they imply on each event. The edge lives in what the narratives leave out and what the market charged for it: on one event, edge = P(reality lands in the covered set) − price of that set. P is learned from the track record of comparable sets (strata defined without price), not predicted per event.
6. **Beliefs are graded.** No authored probability is 0 or 1; certainty comes only from logical edges in rules text. A hard "cannot happen" becomes "unlikely": an excluded set keeps a minimum share of probability, learned from how often such claims fail, and a floor can bound a loss but never create a position.
7. **Steer on direction; confirm on bars.** A result is read first for direction: how likely it is that the effect is real and positive, and how big. Work continues and expands in a direction whose probability is high; strict pass bars are kept only for decisions that put money or a ratification at stake. Every miss gets a post-mortem that feeds the next round (R20, §6.0).
8. **New tests replace the hedge tests as the main line.** T0 (free, retrospective): the sessions' own picks and claims from V1 and V1b, priced at the lock as coverage sets and conditional bets, with a post-mortem of every miss. T1: price coherence along logical edges. T2: a forward single-event coverage sweep. T3: forward cluster narratives. T4: sizer comparison, only once a forward test or a backtest shows edge. V1, V1b and V3 stay frozen and keep their own verdicts.
9. **Backtests, so nothing waits in perpetuity.** The operator model's declared training cutoff is 2026-06-30, so a lock from 2026-07-01 on is out of sample for it if that cutoff holds. A cutoff audit (BT-A) checks it, and can move the window later or earlier. BT-T2 and BT-T3 run the T2 and T3 designs on that window now, with a point-in-time evidence bundle, no live web, and no date or model identity in the session's prompt. The window is small today (about 22 to 32 liquid multi-market events, plus binaries that are almost all crypto) and grows by about 10 liquid events a month, so backtests give a first direction read now, seed the learning store, and roll forward weekly; scoring each forward contract as it resolves starts forward results within days (§6.7).

**Why.** The evidence points one way: Nomad's reading carries information worth pushing on.
- When a session's claim was triggered, its consequent held 12 of 16 times (75%) against 47% implied by the unconditional lock price. Counting each consequent contract once, 10 of 14 held against 48%: about a 96% chance the true rate is above that price. This is the one signal benchmarked against price.
- The session's hedge beat a blind statistical hedge in 12 of 15 rounds (not spend-matched; descriptive).
- Hedges paid $9.1 more in rounds where they were needed.
- Reality landed inside the declared sets in 37 of 41 rounds.
- In the equity era, absence calls held 15 of 16 (counting expired, unanswered calls as hits) and v15 beat a naive baseline in 14 of 15 rounds.

One signal points the other way and is analysed, not ignored: betting the sessions' primary picks directly, equal dollars per contract, returned −$2.9 per $100 pooled (90% interval about −14 to +9). Those picks were chosen as "what will happen", never compared with price, so a result near zero after costs is what pricing them at the market's own view would predict. v18 bets only where Nomad's view differs from the price, which V1 never asked for.

What did not work is one way of turning that reading into money: a maximin hedge built on hard claims, compared with holding less at the same floor (`EVALUATION.md`). Appendix A3 shows why that wrapper could not be the source of edge on Polymarket: with single-event contracts only, a basket's expected value is the sum, contract by contract, of belief minus price. v18 keeps the reading and replaces the wrapper: it bets directly where Nomad's view differs from price, sized by how much.

---

## 1. Rob's direction (2026-10-01)

Quoted from the conversation that produced this file:

- "what I want is some form of analysis that gives the problem statement we can actually attack, all I see are failure modes with no direction."
- "if the payoff isn't enough it means risk is a gate rather than a spectrum to be managed which seems wrong to me. edge is equivalent to risk - whatever the assumption is or something like that"
- "i want to model this one as a graph so positions can be baskets but they are now implicit but im sure we can find multiple sets of contracts that affect each other over a graph on polymarket and thus can pick multiple contracts as a thesis"
- On whether to build one world over the open subset or several theses (the builder recommended both layers, with beliefs only in theses): "ok lets roll with the changes we've decided on until here".
- "flip predicting next steps into 'creates a narrative and models around the narrative, in parallel to cover the prediction mode with volume without needing to predict at all'"

Standing instructions that still apply: free data first, nothing paid before validation; do not squash-merge PR #20 and do not merge until it is clear what we are working with; thresholds are learned or set by the builder ("either make them learn or you choose them I don't know enough"); recorder scope is geopolitical and adjacent (no sport, gaming, entertainment or daily temperature); Ohmni stays separate; nothing places an order.

---

## 2. The evidence this rests on

All figures are the repository's unless marked "builder's count".

| Finding | Source | Number |
|---|---|---|
| The equity wall is structural, not noise | `STATE.md` (R16-001) | Effect of the event on the listed parent 0.01% to 0.4%, against a hedged-residual band near 8%; all four baskets `unbuildable` |
| Equity hedge tests | `STATE.md`, `lookbacks/scenarios/` | Nine pre-registered tests, none confirmed; gains came from lower loading, and a narrative-built hedge did not beat a blind statistical one on Fed days |
| PM-V1 | `v1_study_report.json` | Inconclusive: 17 scored (gate 20), 7 primary losses (gate 10); C−D +3.9 (−2.7, +10.7); B1 0.88 |
| V1b | `v1b_study_report.json` | Inconclusive: 24 scored, 8 primary losses (gate 10); C−D +1.8 (−4.8, +8.4); B1 0.92; B4 0.33 |
| Pooled V1 + V1b (post-hoc) | `EVALUATION.md`, `v1_pooled_report.json` | 41 scored, 15 losses: C−D +2.7 (−2.0, +7.5); primary lost −2.6 (−10.9, +4.6); primary held +5.7 (+0.2, +12.1); cross-entity +0.9 (−4.4, +6.0); same-underlying +9.1 (+0.4, +21.8); B1 37 of 41 |
| Verdict on the V1 construction (the repo's) | `EVALUATION.md` | "The mechanism is not supported as a way to beat plain de-risking"; the edge found is "too small, after fees and the cost of the hedge, to beat simply holding less"; V3 is the one confirmatory test left; no spending justified. Builder's reading: the verdict is on the maximin-hedge wrapper; the reading's own signals are below |
| Direct bets on the primary picks | `v1_pooled_report.json` (means) | P, the primary basket alone with equal dollars per contract: −$2.9 per $100 pooled over 41 rounds (builder's 90% bootstrap about −14 to +9); V1 −9.6, V1b +1.9 |
| Claims carry information beyond price | `v1_evidence_report.json` | Of 69 claims, 16 had their "if" happen; their "then" held 12 of 16 (75%) against 47% implied by the lock price; excess +28 points (90% interval +10 to +45). Cross-entity: 60% against 37% on 10 |
| Caveat on that signal | `EVALUATION.md`; `CENSUS_RESULT.md` | The benchmark is the unconditional lock price, so any genuinely correlated pair beats it (`EVALUATION.md`). Polymarket lists no conditional contracts (`CENSUS_RESULT.md`), so the market's conditional is not observable. Two consequent contracts are counted twice (868075, 871083); counted once, 10 of 14 held against a mean price of 0.48 |
| Hard exclusions | builder's count from the round files | As "this joint state will not happen", 4 of 69 claims failed (5.8%); as "if A then B", 4 of the 16 tested failed (25%). One such failure (329566) cost $54.9 against de-risking |
| Hedges pay when needed, weakly | `v1_evidence_report.json` | Hedge payoff +7.5 when the primary lost, −1.7 when it held; difference +9.1, one-sided permutation p 0.063 |
| Session hedge against blind statistical hedge | `v1_blind_pooled.json` | Formally infeasible (11 V1 and 8 V1b rounds had history; 12 needed). Descriptive: session beat blind in 12 of 15, +14.9 (+4.1, +24.3) |
| The M null control is degenerate | `EVALUATION.md`, `v1_score.py` | A cyclic shift leaves the hedges' sum unchanged, so mean(M−D) = mean(C−D) always |
| Skill profile (equity era) | theory v2, as quoted in `docs/nomad_the_system_as_it_stands.md` §A2 "What is established" (the theory file is not in the repository) | Absence calls 15 of 16 (counting expired, unanswered calls as hits), occurrence 8 of 14, map 1 of 5, magnitude systematically timid |
| The venue | `V0_RESULT.md`, `EVALUATION.md` | No-instrument rates 7 of 24 (V1), 5 of 29 (V1b), 4 of 30 (V3); usable open structures 457 of 5,297 active events; thin in commodities, FX and freight; decliners also wanted rates and national-politics markets the venue does not list (`EVALUATION.md`) |
| Open-set clusters exist | builder's run of `pmgraph.Graph` on `v3/v3_index.json.gz` (399 open usable events, 2026-09-30) | Coherent clusters of 3 to 8 events (Romania PM, France, the Levant, Mexico, Brazil governors); crude tag and entity edges also merge unrelated events into a component of 181 |

**The signals to push on, and how strong they are** (strength figures are the builder's arithmetic on the repo's counts):

| Signal | Count | Strength |
|---|---|---|
| Triggered claims hold more often than the unconditional price implies | 12 of 16 held, against 47% implied; counting each consequent once, 10 of 14 against 48% | Deduplicated: about a 96% chance the true rate is above the price (uniform prior), binomial tail about 6.6%; a bootstrap by round puts the excess at +16 to +39 points. Undeduplicated: 98% and 2.4% |
| The session picks better hedges than a blind statistical picker | 12 of 15 rounds | Sign test about 1.8% one-sided; mean +14.9 (+4.1, +24.3). Not spend-matched: the blind arm always spent its full $40 and lost all of it in 8 of the 12; the session's hedge spent under $20 in 6 of them and itself lost money in 6. Descriptive |
| Hedges pay when the primary loses | +7.5 against −1.7 | Difference +9.1, permutation p 0.063; a bootstrap gives about a 95% chance the difference is positive |
| Reality lands inside the declared sets | 37 of 41 rounds | 90%; 4 misses, all on cross-entity claims. Unpriced: the declared sets cover most joint states, so this is a reliability figure, not an edge |
| Ruling out (equity era) | absence calls 15 of 16 | Counting expired, unanswered calls as hits |
| Reading beats a naive baseline (equity era) | 14 of 15 rounds | Theory v2 |

**What the evidence says, in one line (builder's reading).** The reading carries information where it was tested against price (triggered claims against the unconditional price), and its other signals point the same way; the wrapper that turned it into bets did not convert it into money, and the primary picks bet directly broke even before costs. v18 keeps the reading, bets only where it differs from price, and analyses every miss.

**The misses, which are the material for the next round** (each gets a post-mortem in T0): the 4 claims whose "then" failed (two UK ministerial-office claims, 624096 and 674379; the Fed-hike ladder 329566; and the US–Iran ceasefire ladder 871083, which still finished $15.9 ahead of de-risking); the 3 of 15 rounds where the blind hedge beat the session's; and the primary-loss rounds where the hedge did not beat holding less: 3 where it did worse (624096 −29.2, 329566 −54.9, 36307 −15.3) and 6 where it did nothing (no effective hedge); in the other 6 of those 15 it did better.

---

## 3. Principles (proposed rules R14 to R20)

These extend `config/system_model.json` (R1 to R13). R6, R7, R11, R12 and R13 apply unchanged.

**R14. Edge and risk are one quantity.** For a set of exclusive outcomes priced q, Nomad's belief p and the true probabilities r, the growth rate of a bankroll that bets in proportion to p is D(r‖q) − D(r‖p) (Appendix A1). A position exists because Nomad's belief differs from the price; its size is how much that difference is worth after costs and model error. Edge and risk are never computed separately.

**R15. Risk is sized, not gated.** For event contracts, the only construction objective is expected log growth of the bankroll under Nomad's beliefs, after fees, slippage and tick, scaled by `KELLY_FRACTION`, subject to concentration caps. A size of zero is derived: it is what the objective returns when no growth is left after costs. The AND of risk terms (`stake`, `pricedness`, `expression`, `structural`, `operator`) is not applied to event contracts; each of those ideas becomes an input to the one objective (Appendix A5 maps them). Gates remain only for integrity: the time wall, R6, the ledger (R7), logical impossibility read from rules text, scope, and the rule that nothing places an order.

**R16. A thesis is a subgraph; positions are implicit.** A thesis is a connected set of event nodes with a joint belief over them. The basket is the sizer's solution over every contract in the union of live theses. There is no primary and no hedge. For event contracts, R16 supersedes R9 on ratification (R9 still governs any equity work, which is parked). R10 applies: the objective and the set of theses are declared at lock.

**R17. Beliefs are graded.** No authored probability or claim is 0 or 1. Certainty enters only through logical edges extracted from rules text (an outcome that the rules make impossible). A set of joint states that a session says will not happen keeps, in total, at least `EXCLUSION_FLOOR` of probability. Within a graded distribution over an event's n outcomes, each outcome keeps at least `OUTCOME_FLOOR_SHARE` ÷ n. Floors bound the loss a wrong claim can cause in sizing; a position may never exist because of a floor alone (R18).

**R18. No view, no position.** A node without an authored or learned belief gets no position, and an outcome the session did not address gets no position even if a floor gives it probability. Price is never used as a default belief, and no learned belief is a function of price (R6). Abstaining is the default. Null sets used as controls (§6) are scored on paper only.

**R19. Narratives cover; they do not pick.** Sessions write several narratives in parallel for a cluster or event, each with its necessary conditions, and are not asked which one happens. Nomad covers the union of the outcomes the narratives imply on each event. The probability that reality lands inside a covered set is learned from the track record of comparable sets (§5.8), not predicted per event. Authored point probabilities are optional and, when present, are scored separately (T2, T3).

**R20. Steer on direction; confirm on bars; analyse every miss.** Every result is reported first as direction: the effect size, its interval, and the probability that the effect is positive. A direction whose probability reaches `DIRECTION_PUSH` is pushed: built on, scaled up, given more sessions. Strict pass bars apply only to decisions that put money at risk or ratify a value or rule. Every miss (a failed claim, a lost round, a set that did not cover) gets a post-mortem classifying why, and the classes feed the learning store (§5.8) and the next design. A negative portion is analysed, never used on its own to stop a direction that the rest of the evidence supports.

---

## 4. The model

### 4.1 Objects

| Object | What it is | Where it lives |
|---|---|---|
| **Node** | One Polymarket event's outcome, as a variable: a partition is "which slot wins" (open slot is a typed gap); a terminal ladder is one number; a touch ladder is a running maximum or minimum; a date ladder is "when, if at all"; a single binary is yes or no. Every contract in the event is a question about this variable | World graph snapshot |
| **Contract** | A token whose payoff is a deterministic function of its node (1 or 0 per share), with its fee schedule, tick and minimum size (`event_contract_meta`) | Existing tables |
| **Edge, logical (L)** | A dependency that the rules make certain: one market is a function of another (party of the next PM from the next PM), a necessary condition (a new PM before a date needs the incumbent out before it), nesting across events (strikes or dates on the same underlying), mutual exclusion across events | World graph, extracted by script, each with the rules-text spans that justify it |
| **Edge, proposed (P)** | Rare-tag or entity overlap (`pmgraph`). Attention only: it proposes candidates for a session to read and never supports a claim (R4, R5) | World graph |
| **Edge, causal (C)** | "If A, then B becomes more or less likely", with a graded strength. Authored by a session inside a thesis, never stored in the world graph as fact | Thesis record |
| **Edge, common driver (D)** | Two or more nodes move with an unlisted cause (a reshuffle, a war). Represented as a hidden node inside a thesis | Thesis record |
| **Cluster** | A connected component of the world graph under L edges and P edges at or above `P_EDGE_MIN`, capped at `CLUSTER_MAX_EVENTS` | World graph |
| **Narrative** | A joint scenario over a cluster: for each node, a value or a set of values, plus the necessary conditions that must hold for it to stay alive (each a dated, checkable statement in effect terms). No price, no probability | Thesis record |
| **Covered set S_e** | For event e, the union over narratives of the outcomes they imply, computed by script | Thesis record |
| **Belief** | Three forms: coverage beliefs P(outcome ∈ S_e), learned by stratum (§5.8); optional graded distributions per node, authored; graded C edges, authored | Thesis record and learning store |
| **Position** | Shares per contract (Yes or No, long only), returned by the sizer | Paper book |

### 4.2 Relation to the v17 entity model

Events and contracts are entities: events as a new kind `pm_event`; contracts as the existing instrument subkind `event_contract` (`config/system_model.json`); each contract's price series is a dataset with the capability `attentional` (R6). L edges are relations in the R2 sense (unordered participants filling roles; direction is a perspective). Until v17 V2 builds relation rows, the world graph is stored as a snapshot file (`json.gz`), hashed, and referenced from each lock manifest (R7). **No existing ledger table gains a column** (A18). Thesis records, narratives and beliefs are statements (R3) whose `knowable_from` is the lock.

### 4.3 What the market prices and what it does not

Polymarket prices each node's outcomes separately (a partition's slots, a ladder's rungs). It lists no conditional contracts (`CENSUS_RESULT.md`), so it never prices an edge directly. Two consequences:

- **Expected profit comes only from node-level differences** between belief and price (Appendix A3). Edges change the shape of the payoff, not its mean.
- **Edges are where Nomad can get better node beliefs.** Evidence lands on one node, and the thesis carries its implications along edges to the linked nodes. If the market's crowd for each node updates on its own, linked nodes may lag or disagree. That is Nomad's original premise ("links no single participant's book is organised around") in a testable form. The claims result (75% against 47%) is consistent with it but does not show it, because its benchmark is the unconditional price; T1 and T3's edge scoring test it directly.

---

## 5. Components to build

File names are suggestions; the build session may rename them and must record the gap in `STATE.md`.

### 5.1 World graph (`nomad16/world.py`)

- **Input:** the recorder's daily universe file (every open event, in scope by the recorder's tag rule). The universe file holds a hash of each event's rules (`rules_sha`), not the text, so the builder fetches each candidate event's rules text from the public Gamma API, checks it against `rules_sha`, and stores it hashed in the snapshot.
- **Nodes:** every event with at least one open market; class from `pmgraph.structure` (with the A10 ladder rule); outcome variable type; contract list.
- **L edges, by script:** patterns over titles and rules text, each edge carrying the quoted spans it rests on:
  - *function-of*: an event whose outcome is determined by another's (party of the next PM, "which party wins" from "who wins"), detected by shared office or contest and a party or group qualifier;
  - *necessary-condition*: "X out by d" against "next X" or "new X before d";
  - *nested across events*: the same underlying and comparator at different strikes or dates in different events;
  - *exclusive across events*: outcomes that cannot co-occur by the rules (the same office, the same seat).
  Each extractor ships with tests on real examples (the Romania and France clusters from 2026-09-30 are the first fixtures). An L edge that a test cannot confirm is demoted to P.
- **P edges:** `pmgraph.Graph.edges_from`, unchanged, kept only at a score of at least `P_EDGE_MIN` (builder-set 4.0: at that level the 2026-09-30 run gives the coherent small clusters named in §2, but still leaves two large mixed components of 181 and 83 events, which the cluster cap splits; with no threshold one component holds 322 of 399 events), marked proposal.
- **Clusters:** components under L edges and P edges at or above `P_EDGE_MIN`, capped at `CLUSTER_MAX_EVENTS`; a component above the cap is split by the strongest L edges, then by P-edge score. A P edge is never reviewed by hand: it only proposes, and the T3 session reading the cluster may drop events it judges unrelated (recorded). The 2026-09-30 run shows why P edges alone are not enough (a component of 181 joined SpaceX launches with House seats).
- **Output:** `world_<date>.json.gz` (nodes, edges with type and spans, clusters), its sha256, and a one-line summary in the run log. No probabilities and no prices are stored in it.

### 5.2 Coherence monitor (`lookbacks/polymarket/coherence.py`, diagnostic)

For each L edge, the constraint it implies on prices (a function-of edge: the party contract equals the sum of its candidates' contracts, open slots aside; a necessary condition: the dependent event's price is at most the condition's; nesting: monotone across events). Measure each violation net of fees, slippage and tick, its size and how long it lasts, from recorder snapshots. **Diagnostic only.** Taking a position because prices disagree uses price as the reason for the position, which R6 forbids as written; whether such structural trades are in scope is Rob's decision (D40).

### 5.3 Packets and answers (`lookbacks/polymarket/v18_packet.py`)

Reuse the V1 machinery unchanged where possible (`v1_packet.py` functions for rules text, shared rules, opaque labels, `as_of`, leak scan, the 48-hour eligibility rule, and `v1_run.py` for prompt files, transcript ingest and the audit). The V1, V1b and V3 files stay frozen; v18 imports or copies, never edits them.

- **Evidence at the lock (forward tests).** In a forward test the lock is the authoring time and no outcome exists yet, so the time wall is satisfied by construction and a session may retrieve live public evidence while it authors (the hook's open phase). Every page fetched is stored whole and hashed with its fetch time (the evidence record). Polymarket and odds or prediction-market aggregators are blocked; a fetched page that quotes market odds is flagged and the answer is checked for odds-derived language (R6). Retrospective tests (T0) use no new evidence.
- **Sweep packet (one event, or a batch of unrelated events):** the event's rules text and contracts as of the lock, plus retrieval as above. The session writes up to `NARR_MAX` narratives for the event and, for each, the outcomes it implies; optionally a graded distribution over the outcomes.
- **Cluster packet (one cluster):** every event's rules text and contracts, the cluster's L edges stated in words, plus retrieval as above. The session writes up to `NARR_MAX` narratives over the cluster, each with its necessary conditions; graded C edges ("if A, B becomes much more likely"); optionally graded node distributions.
- **What the session never sees in the packet:** price, volume, liquidity, book, token or condition ids, closing time, resolution status, outcome (as in V1).
- **Audit, changed for forward tests:** V1's audit allowed no tool but reading the prompt file. v18 forward sessions may use retrieval tools; the audit checks the declared model, that every tool call is a retrieval or the prompt read, that no blocked domain was reached, and that the evidence record matches the transcript.
- **Language rule, changed for v18 packets only:** probability numbers are now allowed in the designated fields (graded distributions, C-edge strengths). Still refused anywhere: any reference to the market's view ("priced in", "the market implies", "the odds are", implied probability). The `PROB` pattern in `v1_packet.py` is split accordingly in the v18 copy.
- **Validation (an answer that fails is returned once; a second failure voids, as in V1):**
  - a covered set may not be empty, and may not be the whole event (covering everything has zero edge by construction);
  - every narrative must name at least one necessary condition, dated and checkable;
  - a graded distribution sums to 1 within `PROB_SUM_TOL`, is monotone on a ladder, respects L edges, and respects the floors of R17;
  - a C edge names two nodes in the cluster and a direction and strength; no C edge may contradict an L edge;
  - a recall flag (`recalls_outcome`) is recorded; on forward tests it voids nothing (outcomes do not exist yet) and is kept as a record.

### 5.4 Projection and pricing (`lookbacks/polymarket/v18_project.py`)

- **Narratives to covered sets:** for each event, the union of the outcomes the narratives imply. Partitions: the covered slots (an "other" slot only if the event has an "other" contract; otherwise the uncovered remainder is a typed gap). Terminal ladders: a one-sided tail is one rung ("above a" is YES on rung a; "below b" is NO on rung b). A two-sided interval [a, b) cannot be bought long-only as a single $1 claim: YES on rung a plus NO on rung b pays $2 inside the interval and $1 outside, so it is a riskless $1 plus an interval bet priced q_a − q_b. Price it that way (interval cost q_a − q_b plus both legs' fees and slippage, with the riskless $1 counted as locked capital), or cover the interval through its two tails' complement where that is cheaper. Date windows between two dates are the same. Rung nesting is checked per event at the lock with the V1 foundation-check logic (one winner, nested rungs); an event that fails is excluded and counted (in V1b, round 871083's primary event failed this check). Touch ladders: per side, as in V1. Date ladders: "not by d" is NO on rung d; "by d" is YES.
- **Cost C_e:** the cost of a covered set at the lock, using `exact.share_cost` (entry price plus slippage, rounded up to the tick, plus the market's own fee schedule). Forward tests take the lock price from the recorder's books where it records them (the ask for a buy; the recorder keeps books for its top tokens only), otherwise from the public order-book and price endpoints fetched by the harness at the lock and hashed into the vintage store; retrospective tests use the 48-hour history rule as V1 did.
- **Payoff:** buying an equal number of shares of each covered outcome (so dollars in proportion to each outcome's all-in cost) makes the event-level payoff constant inside the set: $1 per share-set, which costs C_e, if the outcome lands inside, nothing otherwise. That turns each event into one binary bet with price C_e.

### 5.5 Sizer (`nomad16/sizer.py`)

- **Objective (R15):** choose shares s over every contract in the live theses (Yes or No, long only, plus cash) to maximise E_b[log W] under Nomad's belief b, after costs, then scale by `KELLY_FRACTION`.
- **Version 18.0 (build first):** per-event coverage bets. For event e with learned coverage probability P_e and cost C_e, the Kelly fraction is (P_e − C_e) ÷ (1 − C_e) (Appendix A2), scaled by `KELLY_FRACTION`, capped by `MAX_EVENT_SHARE` per event and `MAX_CLUSTER_SHARE` per cluster. Events in the same cluster are treated as correlated through the cluster cap; no correlation model yet.
- **Version 18.1 (once T2, T3, BT-T2 or BT-T3 shows edge, as defined in §6.0):** scenario-based log growth. Each cluster's narratives are scenarios over its joint states, plus a residual scenario for "none of the narratives" sampled over the uncovered states. Joint states are never enumerated in full: `exact.StateSpace` materialises the whole product (an 8-event cluster at the median 8 markets is about 4 × 10^7 states, against V1's cap of 2,000,000), so 18.1 works on scenarios and samples, capped at `SCENARIO_CAP`. Scenario weights come from the learning store (§5.8). The sizer solves one problem over the union of all live clusters, so a node shared by two theses is never bet twice and cross-cluster common drivers (D edges) show up as dependence.
- **Comparators (T4):** sizer 18.0, uniform stakes (the same fraction on every covered set), and Kelly without the cluster cap. `exact.maximin` and `exact.equal_floor_outlay` need a primary and hard exclusions, which v18 does not have; they stay in the code for V1, V1b and V3.
- **Report per position:** belief, price, edge, the Kelly fraction before and after scaling and caps, and the reason for every zero (no belief, no edge after costs, cap reached).

### 5.6 Scorer (`lookbacks/polymarket/v18_score.py`)

- **Coverage:** per event, hit (1 if the outcome lands in S_e) and cost C_e. Two statistics: the **money** statistic mean(hit − C_e), and the **skill** statistic mean(hit − C_e) minus the same quantity for matched-cost random sets (§6), which removes the market's own calibration in each cost band and leaves what the reading adds. Plus the log growth of the scaled Kelly bet using P estimated *only from events resolved before the lock* (a prequential score, so the sizing never sees its own outcome).
- **Contract by contract, as they resolve:** a covered set spans contracts that resolve on different dates (a date ladder's rungs, a ladder's weekly levels). Each covered contract is also scored when it resolves, with the event as the bootstrap unit, so forward results start before whole events end. The event-level score stays primary.
- **Graded beliefs, when present:** per event, log(p of the realised outcome ÷ price of the realised outcome), with prices normalised to sum to 1 across the event's outcomes; mean and 90% bootstrap interval. This is the empirical growth rate of Appendix A1.
- **C edges:** for every edge whose antecedent resolved as stated, the consequent's hit rate against (a) its unconditional lock price and (b) an edge placebo: the same antecedents paired with consequents drawn from other nodes of the same cluster, each priced at its own lock price. Each consequent contract is counted once per round. (The hedge-timing permutation in `v1_evidence.py` and arm B need a primary and a hedge and stay with V1.)
- **Breakdowns (reported, gate nothing):** domain, class, price level of the covered set, horizon, number of narratives, source node versus linked node (a node is a *source* if the session cited evidence about it; it is *linked* if it is covered only through edges), and same-underlying versus cross-entity.

### 5.7 Narrative monitor, kill and rotate (`nomad16/narratives.py`, phase 2)

Each narrative's necessary conditions are dated statements. When evidence shows one has failed, the narrative dies, the outcomes only it covered leave S_e, and the sizer re-solves. This is the time dimension of Nomad's strongest skill (ruling out). It needs paper fills against recorded books (`paper.py`, not built) and live evidence intake, so it waits until T2, T3, BT-T2 or BT-T3 shows edge. Until then, narrative deaths are recorded as statements and scored descriptively (did dead narratives' outcomes stop occurring?).

### 5.8 Learning store

Coverage hit rates by stratum, with strata defined only by things known without price (R6): class, domain, horizon band, number of narratives, and the share of the event's outcomes covered. P comes from the finest level of a fallback chain (pooled → class → class × domain → class × domain × horizon) that has at least `COVERAGE_MIN_OBS` resolved sets, shrunk towards its parent level (`COVERAGE_SHRINK_K`). Until the pooled level reaches `COVERAGE_MIN_OBS`, there is no P and the sizer abstains (R18); every set is scored on paper meanwhile. Every update is an appended event (R7); every learned value is a parameter entity with provenance (R11). Each resolved set carries its source (`backtest` or `forward`); §6.7 says how the two are combined.

### 5.9 Point-in-time evidence bundle (`nomad16/bundle.py`)

One builder serves backtests and forward tests, so the two start from the same kind of evidence. For an event or cluster and a lock time, it collects only records knowable at or before the lock, re-checks every record's time in memory (server-side date filters are never trusted, as in `altdata.py`), runs the leak scan on the text, records what it could not find as a typed gap, and writes a hashed bundle file the session reads in the closed phase. The fetch functions in `pit.py` and `altdata.py` are tied to a v16 round today (`bound()` needs a round in pre-lock, walking, live or scored, and records go to that round's `fetched` directory and the evidence ledger), so `bundle.py` factors them out with its own lock bound and writes to the bundle, not to a round. The GDELT probe (`alt_probe`) runs before first use.

| Source | What it gives | Point-in-time rule | State |
|---|---|---|---|
| Wayback Machine | Captures of news pages and official pages | Latest capture at or before the lock, re-checked in memory | Built (`pit.py`) |
| GDELT 2.0 event exports | Dated events and the URLs of the source articles (the exports carry `SOURCEURL`) | Export file timestamp at or before the lock; article bodies only through Wayback captures at or before the lock, never fetched live | Built: reading the exports and the timestamp rule (`altdata.py`). New: an entity or actor filter (today's adapter filters by country or bounding box only and aggregates counts), keeping full source URLs (today it keeps domains only, for at most 50 rows), and reading back from the lock (today it reads forward from the start of its window) |
| Wikipedia | The article on each named entity as it stood at the lock | Latest revision with a timestamp at or before the lock, as raw wikitext (`rvprop=content`), templates not expanded | Port `wikipedia()` from `v15/harness/pit.py` with two fixes: it renders old revisions with `action=parse`, which expands today's templates (a leak), and it bounds by day, which admits edits made later on the lock day. Add a source declaration (R13) |
| EDGAR | Filings | Acceptance time (`acceptanceDateTime`) at or before the lock | Built (`pit.py`), but it compares the filing date by day, which admits filings made later on the lock day; tighten |
| Agency sites (Fed, BLS, Treasury, CFTC) | Releases and calendars | Through Wayback captures at or before the lock | Through the Wayback adapter |

**Blocked in every bundle:** Polymarket and any prediction-market or odds page, and any text quoting market odds (R6). In forward tests the session may also retrieve live (D42); the bundle is still built and stored.

**Rules recovery is a separate harness step, not part of the bundle.** A backtest needs each event's rules text as it stood at the lock. The step reads a Wayback capture of the event page at or before the lock, extracts the rules text only (from the page's embedded data, not its visible text, since `pit.py`'s text extraction strips scripts), leak-scans it, and passes it to the packet. The page itself never enters the bundle, because it shows prices and volume. Where no capture exists, today's text is used and flagged, and any date after the lock or any "clarification" or "update" note in it is flagged too.

---

## 6. Tests

### 6.0 How every test is read (R20)

- **Direction first.** Each test reports, for its main statistic and each breakdown: the effect, its 90% interval, and the probability that the effect is positive (a seeded bootstrap or a Beta posterior on counts, stated in the pre-registration). A direction at or above `DIRECTION_PUSH` is pushed: more sessions, more clusters, the next component built. A direction below it is not dropped; it is kept running at its current size and re-read as data arrives.
- **"Shows edge"** (the trigger used in §5.5, §5.7, §6.5 and §11) means the **skill** statistic (§5.6) of one test, pooled across that test's registered batches, has a direction probability at or above `DIRECTION_PUSH`. A forward test and a backtest are read separately; a backtest counts only on a window BT-A has cleared. A breakdown (one domain, one class) that points up is a hypothesis for the next batch, pushed only when it repeats there, so that searching many breakdowns does not manufacture a direction.
- **Pushing adds batches; it does not move the bar.** A pushed direction gets new, separately registered batches. Each money bar is read at its own pre-registered sample size, never re-read as data trickles in.
- **Bars for money and ratification only.** The bars below decide two things only: whether anything moves from paper to real money, and whether a builder-set value or a rule is put to Rob for ratification. They never stop a direction on their own.
- **Every miss gets a post-mortem.** Each failed claim, uncovered event or losing round is classified: wrong direction (the dependency does not exist); right direction, wrong strength (graded too strongly); timing (the antecedent came too late or too early); resolution quirk (rules wording, a dispute, a relisting); structure (a ladder or partition that was not what it looked like); harness (a menu, mapping or pricing fault). The classes are counted per test and feed the learning store: strengths are regraded, floors relearned, strata reweighted, extractors fixed.

Each test gets its own pre-registration file (R12) committed before any session runs, with its hashes, sample rule, bar and controls. Values marked builder-set are proposals for that file; the power calculation in each pre-registration sets its sample size and is frozen with it. All tests keep V1's integrity rules: cold `claude-opus-5-5` sessions, prompt files outside the repository, answers ingested from transcripts, the per-stage audit, freeze by hash before scoring (forward tests: before outcomes exist), reserve replacement only for data or harness reasons, no price in any packet.

### 6.1 T0. The sessions' own picks and claims, priced (retrospective, descriptive, free, now)

- **Why not the reachable sets:** V1's claims exclude only joint states of the form (A, not B), so each reachable set, projected onto any one event, is the whole event (135 of 135 event projections across the 41 rounds). That carries no coverage information, so T0 does not use it.
- **The sessions' primary picks as coverage sets:** for each of the 41 scored rounds, the outcomes the primary basket bought on its event, as a coverage set (equal shares), priced at the lock from the round's own `prices.db`; hit against cost; money and skill statistics as in §5.6, with the matched-cost null. Broken down by the price level of the pick (favourite or longshot), which the sessions never saw.
- **The claims as conditional bets:** the 16 triggered claims (and the 53 never tested) re-scored with each consequent counted once, against the unconditional price and against the edge placebo of §5.6.
- **Running it:** offline from each round's `prices.db` (the frozen `v1_score.live_price_of` tries the network first, so T0 uses a copy that reads the cache only), and with the V1b data symlinks (absolute paths into another checkout) resolved in T0's own working copy. The frozen files are not edited.
- **Post-mortems (R20):** the 4 failed claims, the 3 rounds where the blind hedge beat the session's, and the primary-loss rounds where the hedge did not beat holding less, each classified as in §6.0.
- **Output:** a table by round and event; the pooled mean of (hit − cost) with the probability it is positive; the post-mortem classes; no gate. If the sets would have paid at their lock prices, the coverage reading of R19 has support on existing data; if they cost more than their hit rate, T2 and T3 start from a warning.

### 6.2 T1. Coherence along logical edges (descriptive)

On world-graph snapshots with recorder prices: how many L edges are violated net of costs, by how much, for how long. Runs where the recorder's data is (Rob's machine) or on synced snapshots. No gate. A market that keeps linked events consistent leaves little room for propagation edge; one that does not is where the graph matters.

### 6.3 T2. Single-event coverage sweep (forward, confirmatory)

- **Population:** every in-scope open event at the lock with at least `T2_MIN_OPEN_MARKETS` open markets and a horizon (latest scheduled market end) of at most `T2_HORIZON_DAYS`; plus, as a separate stratum, binaries (single markets) with the same horizon, whose coverage set is one side; drawn by seed if above the session budget; reserve as in V1.
- **Authoring:** sweep packets; batches of unrelated events per session are allowed (`SWEEP_BATCH`) to control cost; one stage (no menu).
- **Primary statistics:** the money and skill statistics of §5.6 over resolved events, each with a 90% bootstrap interval.
- **Direction (R20):** the probability that the skill statistic is positive and the probability that the money statistic is positive, reported as events resolve; when either reaches `DIRECTION_PUSH`, T2 gets a new batch.
- **Money bar (builder-set; frozen in the pre-registration):** at the pre-registered sample size, the one-sided 90% lower bound of the money statistic above zero **and** of the skill statistic above zero, before any real money. A money result with no skill (the market's own calibration in a price band) is reported, but is not Nomad's edge and does not pass.
- **Controls:**
  - *Matched-cost random coverage:* for each event, random outcome sets with the same cost, 200 draws; if prices are calibrated its expected hit equals its cost, so it measures the market's own calibration in each cost band. Always feasible: it needs no price history.
  - *No-retrieval control:* the same prompt and model with retrieval disabled (rules text only, knowledge up to the model's cutoff), on a seeded half of the events or a separate draw, so the effect of the evidence the session gathered is measured.
- **Secondary (gates nothing):** the graded-distribution log score where given; the breakdowns of §5.6; how often the sets are "everything but a longshot" against moderate sets.

### 6.4 T3. Cluster narratives (forward)

- **Population:** clusters from the world graph at the lock with 2 to `CLUSTER_MAX_EVENTS` events and at least one L edge; V3's 30 open events and their clusters are eligible as seeds (V3's own frozen answers are untouched). **To reuse them before their first horizon, author by 14 October 2026**; otherwise any open clusters serve.
- **Authoring:** cluster packets; one cluster per session; `NARR_MAX` narratives with necessary conditions; graded C edges.
- **Primary statistic:** as T2, per event, pooled over clusters, with clusters as the bootstrap unit (events inside a cluster are dependent).
- **Secondary:** C-edge informativeness against unconditional price and the edge placebo (§5.6); source against linked nodes (the propagation hypothesis: is hit − C larger on linked nodes than on source nodes?); whole-cluster coverage (every event inside).

### 6.5 T4. Sizer comparison (once T2, T3, BT-T2 or BT-T3 shows edge, §6.0)

On the same frozen beliefs: log growth of sizer 18.1 against 18.0, uniform stakes, and Kelly without cluster caps, on paper with recorded books where they exist. Its pre-registration is written only after T2 or T3 reports.

### 6.6 What continues unchanged

V1, V1b and V3 stay frozen and keep their own verdicts. V3 is read as `EVALUATION.md` says: if its cross-entity rounds show C−D clearly above zero with claims holding at 0.90 or more, the hedge verdict is revisited; if not, the thesis-first hedge is dropped as a source of edge and its solver and claim-checking machinery are kept (they are reused here).

### 6.7 Backtests (BT): results now, without waiting for horizons

**Why it is viable.** The operator model (`claude-opus-5-5`) has a declared training cutoff of 2026-06-30. For an event whose lock is on or after `BT_WINDOW_START` and which resolved after its lock, the model should not know anything from after the lock, if the declared cutoff holds; BT-A checks that it does. The window grows as time passes. V1 and V1b already used events resolved after the cutoff, but with locks at the midpoint of each event's life: 23 of the 58 V1 and V1b packets have a lock before 2026-07-01 (builder's count), so for those the model could know what happened between the lock and its cutoff. Backtests put the lock inside the window.

**Eligibility is set by schedule, never by how the event turned out.** An (event, lock) is eligible if the lock is in the window and on a `BT_LOCK_STEP` grid, the event was open at the lock, and the latest scheduled end of its markets open at the lock is at most `T2_HORIZON_DAYS` after the lock **and** on or before the data date. A rule based on the actual close time picks events that resolved early, and those are mostly "it happened" outcomes: counted that way, the window held 78 events and 407 (event, lock) pairs, but 54 of the 78 qualified only because they closed before their scheduled end, and of 33 date ladders 31 closed early on a Yes rung. That count is not used. Early closers whose scheduled end is still in the future are a labelled sensitivity only.

**How much history the window holds now** (builder's count, 2026-10-01, `BT_WINDOW_START` 2026-07-01):
- **Liquid multi-market events** (`v1_live_index.json.gz`: exact partitions, open partitions, ladders and date ladders with event volume at least $100,000, cleanly resolved): **32 events and 130 (event, lock) pairs** with a scheduled horizon of at most 75 days; **22 events and 90 pairs** once the scheduled end must also be on or before 2026-09-30 (9 ladders, 8 open partitions, 3 date ladders, 2 exact partitions). The 30 September census independently lists 29 usable multi-market events with a scheduled end between 2026-07-01 and 2026-09-30.
- **Binaries:** the census lists 173 single markets or pairs with event volume of at least $10,000 and a scheduled end in the window, **170 of them crypto**. That is an upper bound before the clean-resolution and lock-price filters.
- **Growth:** about 10 liquid multi-market events a month at the current rate.

So a backtest gives a first direction read on a few dozen events now, not a large sample. Three levers grow it, each labelled in the results:
1. **Every eligible lock per event**, as a dependent analysis with the event as the bootstrap unit (90 pairs on 22 events today).
2. **BT-A can move the window earlier as well as later.** If months before the declared cutoff show no knowledge under BT-A's conservative gate (the last months before a cutoff are often thin in training data), those months join the window.
3. **A full crawl and a liquidity floor measured at the lock.** The census is a union of capped API orderings, so `bt_crawl.py` crawls closed events in start-date windows small enough to stay under the cap and re-checks each close time in memory. Eligibility uses liquidity knowable at the lock (rule 8), not lifetime volume.

BT-X (older-cutoff models) gives large samples, but for direction on the method only. **Forward is not perpetual either.** Of V3's 151 pool events, 30 have a market ending within 14 days of 30 September, and 12 resolve in full within 30 days and 30 within 45 (V3 market dates). Scoring each covered contract as it resolves (§5.6) starts the forward count within days.

**Rules that keep a backtest honest.**
1. **The window and eligibility** as above. Only clean resolutions are scored; disputes are excluded and counted.
2. **One lock per event** for the primary analysis, drawn by seed from its eligible lock dates. Other locks form the dependent analysis of lever 1, reported separately.
3. **Closed phase.** No live web. Evidence comes only from the point-in-time bundle (§5.9).
4. **The event as of the lock.** A market created after the lock is removed: `bt_crawl.py` records each market's `createdAt`; failing that, V1's rule applies (a market needs a price point in the 48 hours before the lock). Rules text comes from the rules-recovery step (§5.9), flagged where only today's text exists.
5. **Prices at the lock** from the public price history (the 48-hour rule, as V1). They are used for scoring and costs only and are never shown. Costs are slippage `0.01`, the tick and each market's own fee schedule, with no historical books.
6. **The runtime leak.** A session's environment shows today's date and its own model name. Backtest sessions therefore run with a fixed system prompt that carries no current date and no self-identity, where the runtime allows it (direct model calls with a fixed prompt). Where it does not, the leak is recorded per session. Events about the operator model's maker (Anthropic and Claude models) are excluded from backtests either way. The four recall voids in V1 and V1b came from this:
   - three sessions recognised the date and their own model name around Claude-release events;
   - one flag was on a lock before the cutoff.

   None is evidence that the model knows outcomes after its cutoff.
7. **The recall flag still voids** the (event, lock) and is counted. If it fires in a cluster session, the whole cluster is void.
8. **Liquidity at the lock.** Lifetime volume includes trading after the lock and moves with the outcome. So eligibility uses the number of price points in the 7 days before the lock (`BT_MIN_POINTS`) on the event's markets, with lifetime volume reported as a sensitivity.
9. **Same machinery, same order.** The same packets, validation, projection and scorer as the forward tests. Answers are frozen by hash before the scorer reads any resolution, even though the resolutions already exist.
10. **Prequential means resolved before the lock.** The learning-store P used for (event, lock L) comes only from sets whose events resolved before L, whatever order the batches run in.

**BT-A. Cutoff audit (first, before any backtest is read).** The model's cutoff is declared, not verified.
- **Sample:** for each month from `BT_AUDIT_FROM` (2026-01) to 2026-09, `BT_AUDIT_N` events that resolved in that month (anything about Anthropic or Claude excluded).
- **Sessions:** cold, no evidence, no prices, the fixed system prompt of rule 6. Each session gets an event's rules and gives a probability for each outcome. Up to 10 events per session.
- **Score:** per event, the log of (the probability on the realised outcome ÷ the price of that outcome at a fixed point 14 days before resolution). The price is used in scoring only, never shown. A model with only general priors and no evidence cannot beat that price by much; a model that knows the outcome beats it by a lot.
- **Positive control:** the months well before the cutoff (January to March 2026) show what knowing looks like.
- **Gate (an integrity check, so deliberately conservative, and separate from `DIRECTION_PUSH`):** a month is clean only if the probability that its mean excess is at least half the positive control's is at most `BT_AUDIT_GATE` (0.2). `BT_WINDOW_START` is the start of the earliest month from which every later month is clean. It may land earlier than 2026-07-01 or later.

**BT-T2. Single-event coverage, backtested.** T2's design (§6.3) on the window, with the multi-market and binary strata kept separate (forward T2 gets a binary stratum too, so the two can be compared stratum by stratum). Two arms on the full draw: **with the evidence bundle** and **without it** (rules text only). That measures what point-in-time evidence adds. Statistics, controls and breakdowns are as in T2.

**BT-T3. Clusters, backtested.** T3's design (§6.4) on the window. The world graph is rebuilt as of each lock:
- **Events:** those open at the lock (closed now or still open), with markets created at or before the lock.
- **Text:** titles and rules as recovered for the lock. An L edge resting only on today's text is flagged unverified and does not join a cluster on its own.
- **Analysis:** C-edge scoring and the source-against-linked comparison as in T3. This is the fastest route to the propagation question (§4.3); its size follows the window above.

**BT-X. Older-cutoff models (optional).** A model with an earlier declared cutoff extends the clean window back by the difference. Its results stand for that model only. They are labelled and used for direction on the method (does narrative coverage beat price at all, and where?), and never mixed into `claude-opus-5-5` numbers or the learning store.

**How backtest results are used.**
- **Direction (R20):** in full. A backtest direction at or above `DIRECTION_PUSH`, on a window BT-A has cleared, is pushed exactly like a forward one.
- **Learning store:** backtest sets seed the coverage rates by stratum, labelled `backtest`, so the sizer has a P when forward tests start. Forward results update them. If forward and backtest disagree within a stratum (the direction probability of the difference is at or above `DIRECTION_PUSH`), that stratum uses forward data only, and the disagreement gets a post-mortem.
- **Money bar:** read once, on one named, pre-registered backtest sample, not on every weekly batch. It passes only if three things hold:
  - BT-A has cleared that window;
  - the bar of §6.3 holds on it;
  - the forward data in the same strata, once there are at least `COVERAGE_MIN_OBS` resolved sets, have a direction probability of at least 0.5.

  Real money still needs Rob's word, D33 and the terms check, and nothing in the repository places an order.
- **Rolling:** a new batch is registered each week for the (event, lock) pairs whose scheduled ends have now passed (walk-forward). A forward test's own events never re-enter as backtests.

**Limits, stated now.**
- Price history for closed markets is coarse (60-minute points near the lock for most tokens, 12-hour otherwise, some contracts with none), and there are no historical books.
- Wayback coverage is uneven, so a backtest bundle can be thinner than live retrieval. That biases the evidence arm down, not up.
- Rules text may have been edited after the lock (flagged).
- Only clean resolutions are scored.
- The window is short and, in binaries, almost all crypto.
- Even with schedule-based eligibility, a crawl ordered by volume could over-represent eventful events; the date-window crawl is the fix.
- Where the runtime cannot hide the date and model identity, some leak remains (rule 6).
- A model that knows more than its declared cutoff is the main threat; BT-A is the defence.

---

## 7. Values (all builder-set, `provisional_unratified`; how each one learns)

Rob does not set thresholds; each value below is a starting point with a rule for replacing it from data. Any round that reads one is learning-class, as now.

| Key | Builder-set start | What it does | How it learns or gets replaced |
|---|---|---|---|
| `KELLY_FRACTION` | 0.25 | Scales every Kelly size, for model error | After ≥ `COVERAGE_MIN_OBS` × 3 resolved bets, set to the fraction that would have maximised realised log growth on the earlier half, checked on the later half; never above 0.5 |
| `EXCLUSION_FLOOR` | 0.05 | Minimum total probability on a set of joint states a session says will not happen | The shrunk rate at which such exclusions fail (currently 4 of 69 claims, 5.8%; 4 of the 16 whose antecedent happened) |
| `OUTCOME_FLOOR_SHARE` | 0.1 | Within a graded distribution over n outcomes, each outcome keeps at least this ÷ n | Chosen by out-of-sample log score on resolved graded distributions |
| `PROB_SUM_TOL` | 0.01 | Tolerance for an authored distribution summing to 1 | Fixed |
| `P_EDGE_MIN` | 4.0 | Minimum `pmgraph` edge score for a proposed edge to join a cluster | Raised or lowered by how often T3 sessions drop proposed-only events from clusters |
| `SCENARIO_CAP` | 200,000 | Most joint scenarios sizer 18.1 evaluates per problem | Raised if solve times allow |
| `NARR_MAX` | 5 | Narratives per event or cluster | Replaced by the count that maximises hit − C in T2 and T3's breakdowns |
| `CLUSTER_MAX_EVENTS` | 8 | Size cap for a cluster read by one session | Raised if audits show sessions reading larger clusters in full |
| `COVERAGE_MIN_OBS` | 30 | Resolved sets needed before a stratum gets a learned P | Fixed by the power calculation in T2's pre-registration |
| `COVERAGE_SHRINK_K` | 20 | Shrinkage of a stratum's hit rate towards the pooled rate | Chosen by out-of-sample log score on resolved sets |
| `MAX_EVENT_SHARE` | 0.05 of bankroll | Concentration cap per event | Not learned (a cap bounds ruin, which a track record cannot show until it happens); builder-set, Rob may change it |
| `MAX_CLUSTER_SHARE` | 0.15 of bankroll | Concentration cap per cluster | As above |
| `T2_HORIZON_DAYS` | 75 | Latest horizon for T2 events | Set per pre-registration from the open set's horizon distribution |
| `T2_MIN_OPEN_MARKETS` | 3 | As V3 A3 | As V3 |
| `SWEEP_BATCH` | 6 | Unrelated events per sweep session | Lowered if the audit or a variance re-run shows answers depend on batch neighbours |
| `BT_WINDOW_START` | 2026-07-01 | First lock date a backtest may use with `claude-opus-5-5` | Set by BT-A: the start of the earliest month from which every later month is clean; can move earlier or later; resets if the operator model changes |
| `BT_AUDIT_FROM` | 2026-01 | First month sampled by BT-A (January to March is the positive control) | Fixed by BT-A's pre-registration |
| `BT_AUDIT_GATE` | 0.2 | Highest probability that a month's excess over price reaches half the positive control's, for the month to count as clean | Not learned: an integrity gate; builder-set, Rob may change it |
| `BT_LOCK_STEP` | 7 days | Spacing of candidate lock dates in the window | Fixed |
| `BT_MIN_POINTS` | 10 | Price points in the 7 days before the lock, on each covered market, for a backtest event to be eligible (liquidity knowable at the lock) | Fixed by BT-T2's pre-registration; lifetime volume reported as a sensitivity |
| `BT_AUDIT_N` | 40 events per month | Sample size per month for the cutoff audit | Set by BT-A's pre-registration power calculation |
| `DIRECTION_PUSH` | 0.80 | Probability that an effect is positive at which a direction is pushed (R20) | Learned from the record of pushed directions: raised if pushed directions often fail to repeat in their next batch, lowered if they almost always repeat |

---

## 8. Changes to existing code and documents

| Item | Change |
|---|---|
| `v1_*.py`, `v1b/`, `v3/`, their pre-registrations | **No change.** Frozen. v18 imports or copies |
| `nomad16/exact.py` | Add a log-growth objective beside `maximin` (per-event binary Kelly for 18.0; scenario log growth over `StateSpace` for 18.1). `maximin` and `equal_floor_outlay` stay for V1, V1b and V3 |
| `nomad16/pmgraph.py` | No change. `world.py` builds on it |
| `nomad16/prices.py` | Add lock-time prices from recorder book snapshots for forward tests (ask for buys), hashed into the vintage store; the 48-hour history rule stays for retrospective tests |
| `nomad16/world.py`, `sizer.py`, `narratives.py`, `bundle.py` | New (§5). `bundle.py` factors the fetch functions out of `pit.py` (Wayback, EDGAR) and `altdata.py` (GDELT exports) with its own lock bound, extends the GDELT reader (§5.9), ports and fixes v15's Wikipedia adapter, and adds the rules-recovery step; source declarations in `declarations.py` |
| `lookbacks/polymarket/v18_packet.py`, `v18_project.py`, `v18_score.py`, `coherence.py`, `t0_picks_and_claims.py`, `bt_audit.py`, `bt_crawl.py` (closed events crawled in start-date windows under the API's cap, close times re-checked in memory, each market's `createdAt` recorded), `bt_run.py` (the v18 packet, project and score scripts for a past lock, closed phase, fixed system prompt with no date or model identity) | New (§5, §6) |
| Harness hook (`firewall/guard16.py`) | For v18 forward authoring only: retrieval allowed in the open phase with the blocked-domain list and the evidence record (§5.3) |
| `config/system_model.json` | Add R14 to R20 as rule strings, each beginning "(proposed)" (rules carry no status field; the file's own status is "proposed"); on ratification of D35, append "superseded for event contracts by R16" to R9's text |
| `config/appetite.json` | Add the §7 keys, `provisional_unratified`, with basis "v18 builder-set" |
| `docs/RATIFICATIONS.md` | Add D34 to D43 as proposed (§12) |
| `STATE.md` | A dated entry for every gap between this file and what is built (the spec is never rewritten to match the code) |
| `docs/nomad_v18_updates.md` | This file |

---

## 9. What stays

The ledger and its chain; the time wall and the pre-lock hook; cold operator sessions and the transcript audit; pre-registration before any number (R12); R6 (price never forms a belief, a probability or an exposure); typed gaps; R13 source declarations; free data first; the recorder and its scope; the exact-payoff code (`exact.py`), the vintage store and the open-set graph; v17 V0 and V1; PR #20's handling. The equity-era parts stay parked, not deleted.

## 10. What is retired or superseded (on ratification)

- **The primary and hedge split** for event contracts (R9, by R16).
- **The maximin over hard exclusions as the construction objective** (kept as a comparator).
- **Hard reachable-set exclusions**, except L edges from rules text (R17).
- **The ban on probability language** in v18 packets (the ban on the market's view stays).
- **The M null control** (degenerate); replaced by matched-cost random coverage and the edge placebo.
- **Arm B and the hedge-timing permutation** as controls (both need a primary and a hedge); they stay with V1, V1b and V3. v18's controls are matched-cost random sets, the edge placebo and the no-retrieval control.
- **The AND of wall terms** for event contracts (R15); the equity wall stays parked with its terms.
- **"The hedge as a source of edge"**: by Appendix A3 and the evaluation, the hedge is a sizing property, not an edge.

---

## 11. Order of work

1. **Now:** T0 on the 41 scored rounds (data in the repository). Register R14 to R20 and D34 to D43 as proposed; add the §7 keys. Build `v18_packet.py`, `v18_project.py` and `v18_score.py` (shared by forward tests and backtests), `bundle.py` with the rules-recovery step, and `bt_crawl.py`; write the BT-A and BT-T2 pre-registrations.
2. **As soon as those exist (target this week or next):** BT-A, then BT-T2 on the cleared window with both arms. These give the first scored v18 direction reads in days, on a small sample.
3. **Next few days:** `world.py` with the L-edge extractors and their fixtures; a first world snapshot from the recorder's universe file; the same builder run as of past locks for BT-T3; cluster list.
4. **Before 14 October 2026:** T2 and T3 pre-registrations (power calculations, bars, controls), a dress rehearsal on two out-of-scope events as V1 did, then authoring. T3 uses V3's clusters if authored by 14 October.
5. **In parallel:** T1 on recorder data, on Rob's machine. BT-T3 as soon as the past world graphs exist.
6. **Every week from now:** a walk-forward backtest batch on the newly resolved week. **As forward outcomes arrive (from mid-October):** prequential scoring, the learning store (already seeded by the backtests), sizer 18.0 on paper.
7. **Once T2, T3, BT-T2 or BT-T3 shows edge (§6.0):** sizer 18.1, T4, then the narrative monitor and paper fills.

**Cost, rough.** V1 measured about 44k to 47k tokens for a one-stage session. A sweep of 300 events at `SWEEP_BATCH` 6 is about 50 sessions; a T3 run of 30 clusters is 30 longer sessions. BT-A at 10 events per session is about 24 short sessions for 240 events; BT-T2 runs both arms on the full draw, so it costs about twice its own sample size in sessions; at today's window that is small. The pre-registrations should state the budget and run in batches with the token count reported after each, as V1 did.

---

## 12. Decisions for Rob (proposed rows)

| Row | Decision |
|---|---|
| **D34** | Edge and risk are one quantity; event-contract positions are sized by expected log growth at a fraction of Kelly; zero size is derived, not gated (R14, R15) |
| **D35** | A thesis is a subgraph with a joint belief; positions are the sizer's output; R9 superseded for event contracts (R16) |
| **D36** | Beliefs are graded with a learned floor; certainty only from rules-text L edges; no view, no position (R17, R18) |
| **D37** | Narrative coverage is the primary prediction mode; coverage probabilities are learned by stratum, not predicted per event (R19) |
| **D38** | Two layers: a daily world graph over the open set (structure only) and thesis subgraphs (beliefs only there); one sizing over all live theses |
| **D39** | Tests T0 to T4 in the order of §11; V1, V1b and V3 unchanged |
| **D40** | Structural coherence trades (positions taken because linked prices disagree): out of scope under R6 as written, or allowed as a separate, labelled class. Builder's recommendation: keep them out until T1 shows how often and how much prices disagree |
| **D41** | Results are read for direction first; strict bars only for money and ratification; every miss gets a post-mortem (R20); `DIRECTION_PUSH` 0.80 to start |
| **D42** | Forward v18 sessions may retrieve live public evidence while authoring, with every page stored and hashed, Polymarket and odds sites blocked (§5.3) |
| **D43** | Backtests (§6.7): eligibility by schedule, never by outcome; a cutoff audit first, which sets the window; no date or model identity in backtest sessions, and no events about Anthropic or Claude; backtests count fully for direction and seed the learning store; the money bar is read once on a named backtest sample, with forward data in the same strata not pointing the other way |

Also open, unchanged from before: D33 itself (the Polymarket frame) waits for Rob's word; v18 assumes it. Values in §7 are builder-set. Most learn from data; the concentration caps and `BT_AUDIT_GATE` are guards that do not learn, and a few are fixed by their pre-registration. Nothing waits on Rob to set a number.

---

## 13. Risks, and what would stop this

- **T2 and T3 both pointing at or below zero after their samples fill.** That would mean Nomad's coverage sets are not underpriced anywhere. Read the post-mortems first (a fixable harness or strata problem is not a dead direction); if the direction stays negative across strata, move the authoring budget to whichever signal still points up (the conditional claims, on their own, are the next candidate).
- **Correlated tails.** One shock (a war, a surprise election) can land outside many covered sets at once. The cluster caps and, later, sizer 18.1's common-driver nodes are the defence; `KELLY_FRACTION` starts low.
- **Costs at the edges.** A covered set priced at 0.95 has at most 0.05 of edge, and a 0.01 slippage plus a tick can take most of it. T2 reports results by cost band, and the sizer reports zeros caused by costs.
- **Depth.** Order books have not been audited; the recorder holds them on Rob's machine. Paper fills (phase 2) are the check.
- **Calibration of authored probabilities is unknown.** T2 and T3 measure it; until then the sizer uses learned coverage rates, not authored numbers.
- **A model that knows more than its declared cutoff.** It would make backtests look better than they are. BT-A tests for it month by month and sets the window. The recall flag (noisy) and the forward-against-backtest disagreement check (which also picks up the difference between live retrieval and the bundle) may catch some of what BT-A misses. A session's runtime that shows today's date and its own model name is a known leak; backtests remove both where the runtime allows and exclude events about Anthropic or Claude.
- **Recall and staleness.** Forward tests make the training cutoff irrelevant for leakage, but a session without retrieval knows nothing after 2026-06-30; that is why forward authoring retrieves live evidence (D42) and why the no-retrieval control exists. Retrospective T0 inherits V1's protections (resolved after 2026-06-30).
- **Capacity.** The viable open set is small (hundreds of events), so even a real edge is small in money. That bounds the business, not the test.
- **Terms.** Nothing places an order; Polymarket's terms for the user's country are checked before anything ever does.

---

## Appendix A. The arithmetic

**A1. Growth equals relative wrongness.** A complete partition with outcomes i, prices q_i summing to 1 (payoff 1 per share, so odds 1/q_i), Nomad's beliefs p_i and true probabilities r_i. Betting the whole bankroll in proportion to p gives a wealth multiplier p_i ÷ q_i when outcome i happens, so the expected log growth is

  W = Σ r_i log(p_i ÷ q_i) = D(r‖q) − D(r‖p),

where D is the Kullback–Leibler divergence (the horse-race result in Cover and Thomas, *Elements of Information Theory*, chapter 6). Positive exactly when Nomad is closer to the truth than the price. Its empirical estimate on resolved events is the mean of log(p_o ÷ q_o) for the realised outcome o, which is the graded-belief score in §5.6. Fees and the price sum's excess over 1 reduce it.

**A2. One covered set is one binary bet.** Buy equal shares of the covered outcomes, total cost C per $1 of payoff. With coverage probability P, the Kelly fraction is f* = (P − C) ÷ (1 − C). At f* the wealth multiplier is P ÷ C on a hit and (1 − P) ÷ (1 − C) on a miss, so the growth rate expected under Nomad's own P is P log(P ÷ C) + (1 − P) log((1 − P) ÷ (1 − C)) = D(P‖C), which is never negative. Under the true probability r the realised growth is D(r‖C) − D(r‖P), the binary case of A1: positive exactly when P is closer to r than C is. Edge exists exactly when the true r exceeds C and P is a good estimate of it.

**A3. With single-event contracts, a basket's mean is the sum of node edges.** For shares s_i on contracts with belief p_i and cost q_i, E[profit] = Σ s_i (p_i − q_i) − costs. The joint belief over events does not appear: dependence between events changes the variance and the shape of the payoff, not its expectation. So if Nomad's node beliefs equal the prices, every basket, however it is hedged, has zero expected profit before costs and negative after. Joint beliefs earn their place by letting the sizer hold node edges at larger size for the same risk, and by producing better node beliefs through propagation (§4.3). This is why the hedge is not, and cannot be, the source of edge.

**A4. Why hard exclusions break.** Excluding a state is a probability of 0. In log terms a 0 on an outcome that happens is an unbounded loss; in the maximin it is a floor that was never real (329566 lost $54.9 against de-risking when one excluded state happened). Keeping a floor of probability on every excluded set (R17) bounds the damage, at the cost of a lower paper floor.

**A5. The equity wall in the same terms.** For a small edge μ on an instrument with volatility σ, the Kelly growth rate is about μ² ÷ (2σ²). R16-001's largest effect, 0.4% against a band near 8% (used here as a stand-in for σ), gives about (0.05)² ÷ 2 ≈ 0.125% per event at full Kelly before costs; the 0.01% effect gives effectively zero. The spectrum agrees with the old veto on R16-001, but it names the knob: how much of an instrument's movement the event explains. On Polymarket the contract is the event, so that share is all of it.

The wall's five terms map onto this one number: **stake** sets μ (how much the event moves the instrument); **pricedness** reduces μ (the part already in the price is not edge); **expression** sets σ (the movement that has nothing to do with the event); **structural** and **operator** decide whether the position can be held at all and how much model error to allow, which is the cap and `KELLY_FRACTION`.

## Appendix B. Glossary

- **Coverage set:** the outcomes of one event that some narrative reaches; bought as equal shares of each outcome, it pays $1 per share-set if reality lands inside.
- **Hit:** reality landed inside the coverage set.
- **Kelly fraction:** the share of bankroll that maximises long-run log growth for a given edge; scaled down by `KELLY_FRACTION` here.
- **L, P, C, D edges:** logical (certain, from rules text), proposed (attention only), causal (authored, graded), common driver (a hidden node).
- **Prequential:** scored using only information from events that resolved earlier.
- **Source node, linked node:** a node the session cited evidence about, and a node it covered only through edges.
