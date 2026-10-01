# T3: cluster sessions, forward (registration, written before any T3 session runs)

v18 §6.4 and §5.3, with the session format of `docs/DECISIONS_2026-10.md` decisions 3, 4 and 6 and the reading rule of decision 7. Script `t3.py`. Answers are frozen by hash, with a commit time, before any of the outcomes they forecast exist.

## 1. The question

When a session reads a group of related open events, with live public evidence, does its view beat the market's price on those events? Two ways:
- **Node views:** the graded view of each event.
- **Claims:** "if A then B", written with both branches.

The claims carry Nomad's strongest earlier signal: in T0, linked events held about 30 points above a kind-and-price matched base when the "if" happened (`T0_BASE_RATE.md`). T3 tests that forward, on events chosen by schedule, with the bet placed before anyone knows whether A happens.

## 2. Clusters (register C4; decision 8: the graph proposes, the session decides)

- **Seeds:** V3's authored events (`v3/v1_rounds.json`) still open at the snapshot, with a horizon of at most 150 days (V3 A2). T3 must be authored by 14 October 2026 to reuse them.
- **Candidates, proposed by the graph:**
  - the open events sharing a rare tag or named entity with the seed (`pmgraph.Graph.edges_from`);
  - link score at least `P_EDGE_MIN` 4.0, strongest first;
  - up to `CLUSTER_MAX_EVENTS` 8 events including the seed.
  - Both are v18 §7 values, used here as stand-ins until C4 is settled. Their basis is v18 §2: coherent clusters of 3 to 8 events at that score in the 2026-09-30 run.
- **The session decides:** it drops any event it judges unrelated, with a one-line reason, and writes nothing for it. The drops are recorded, which is how `P_EDGE_MIN` learns (v18 §7).
- **Overlap is allowed and recorded:** an event may sit in two clusters (the two Venezuela seeds, for example). Each cluster is its own basket (addendum B1 §6). Whether baskets may share a contract is C4's open question; scoring reports overlapping events both ways.
- **Deviation:** v18 §6.4 wants at least one L edge per cluster. The L-edge extractors (`world.py`) are not built, so clusters rest on P edges and the session's judgment.

## 3. What a session writes

- **Node views:** for every kept event, the graded view of decision 6 (as `BT_T2_prereg.md` §3).
- **Claims:** any number, including none.
  - Each claim names an "if" contract and the side it resolves to, and a "then" event in the cluster.
  - The "then" event is written twice, as its own view if A happens and if it does not (addendum B1 §5). P(A) is the session's view of A's own event.
- **Sources:** the pages relied on.

**Retrieval (D42).** The session may search and fetch live public pages.
- Every search must pass the blocked list (prediction-market, betting and odds sites).
- A fetch of a blocked domain voids the session.
- An answer that speaks of a market's or trader's view is invalid (R6) and re-authored by a fresh session, counted.
- Pages that quote odds are counted per session; they void nothing.

## 4. The lock

The lock is each session's hand-back. Prices are read from the public order book (best ask, for YES and for NO) immediately after the answer is ingested, and hashed. A session that retrieves live evidence knows as much as the news up to its end, and the price read just after includes all of it.

**Contracts closed before a session's lock are excluded from its scoring**, so an outcome found while authoring can never score. Packets are built from a fresh snapshot of the open set just before the sessions run.

## 5. Scores (forward, as contracts resolve)

As `BT_T2_prereg.md` §4 and §5, with the lock-time asks as the price and all-in cost from the ask, plus the claims:

- **S1, money and skill, the main statistic.**
  - Positions from node views where the view (or its bound) beats the all-in cost.
  - Skill is (hit − cost) minus the mean (hit − cost) of every other T3 contract of the same event class with cost within 0.05.
  - Clusters are the bootstrap unit, since events inside a cluster are dependent.
- **S2, magnitude, calibration-free:** as BT-T2, clusters as the unit.
- **S3, claims, declared at 5% like S1 and S2.** For every claim, the combined view of B at the lock is P(A)·view(B | A) + (1 − P(A))·view(B | not A), contract by contract, bet where it beats the cost and scored like S1. This is the bettable claim.
- **Secondary:**
  - the conditional reading: when A resolved as stated, B's "if A" view against B's lock price and against the same-cluster placebo of v18 §5.6;
  - calibration;
  - the log score;
  - source against linked nodes;
  - dropped events.
- **Reading (decision 7):** each declared statistic is "edge shown" when its 95% interval is above zero and "shown absent" when below. With three declared statistics the chance of at least one false positive is about 14%. Confirmation is the next forward batch.

## 6. Integrity

As BT-A §6:
- cold `claude-opus-5-5` subagents, one instruction each, prompt files outside the repository;
- answers taken from the transcript's hand-back;
- a retrieval audit on every transcript (`t3.audit_retrieval`): only reading the prompt, loading the web tools, searching with the blocked list and fetching unblocked pages;
- every page fetched is re-read just after hand-back and stored whole, hashed. The fetch tool hands the session a summary rather than the page, so this is the nearest whole-page record.

The runtime shows the date and the model name, which does not matter forward. The auto-memory index is injected (as BT-A §7).

## 7. Budget

25 clusters, one session each, with retrieval: an estimated 100,000 to 200,000 tokens a session. To be measured on the first sessions and reported.

## 8. Added before commit (2026-10-01, after BT-T2's first pass and before any T3 session)

- **E1 in T3.** S1's positions are reported split by side, with NO positions scored against same-side, same-class, same-cost contracts (as `BT_T2_pass2_prereg.md` §2). This is a forward reading of E1 that declares nothing; T3's registered statistics stay S1, S2 and S3.
- **Answers are read with integer chance keys** (`bt_t2.intkeys`; BT-T2 addendum A3), so the scorer bug found in BT-T2 cannot recur here.
- **Calibration** follows `docs/EDGE_LEDGER.md`: within this pipeline only, Platt fitted walk-forward once resolved history exists. It never touches S1's selection or S2's ranks.

## 9. Folded in before any session (2026-10-01, decision 11)

- **Scale of scale.** For every kept question that measures a quantity, count, price, size or date, the session also writes `scale`:
  - the reference class it is using;
  - the percentile (0–100) where its middle view of this instance sits among instances of that class.

  It writes `null` for plain yes/no questions. The data is collected now. Its score (the realised instance's percentile in the class, against the session's, by rank) needs reference-class data and gets its own registration before any T3 outcome is read. It declares nothing in this test.
- **Depth at the lock.** With each best ask, the dollars on offer within 1¢ and 2¢ of it are recorded for YES and NO (C7).
- **The whole prompt must be read.** The retrieval audit also requires the prompt's lines to be reproduced in full by the session's reads (BT-A addendum A2's line-number check). Sessions are told they may read it in parts.
- **T3's instruction line** allows retrieval (`t3.INSTRUCTION_T3`). The backtests' "reading this file is the only tool call you may make" would contradict D42.
