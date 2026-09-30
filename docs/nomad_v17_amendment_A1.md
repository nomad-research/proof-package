# v17 amendment A1 — one registry, relations seen from a perspective, forward-first gating

*Status: **proposed**. Nothing here is built and nothing is ratified. Written 2026-09-30 after the K14 pilot and Rob's
instructions of the same day. Each numbered decision at the end is Rob's.*

## 1. Why

The K14 pilot showed three things. A hop's direction was ambiguous to the reader and the judge, so the mechanical check passed
a chain the judge did not accept. The kind constraints that would have refused it live in the entity registry and nowhere
in the relation registry. And the look-back is coupled to past results in ways that block forward work: lock-time documents
that no longer exist, a template guard that past result files may have breached, a gate (V3 to V5) that waits on it. This
amendment fixes the first two by design and the third by changing what gates what.

## 2. One registry mechanism (proposed D29)

Entity kinds, relation types, capabilities, effect kinds, instrument kinds and document kinds are rows of one registry
mechanism, not separate lists.

| Column | Meaning |
|---|---|
| `key`, `domain` | `entity`, `relation`, `effect`, `instrument`, `document`, `capability` |
| `parent` | a tree inside a domain (as `entity_kinds` already is) |
| `review` | `unreviewed` or `reviewed`. An unreviewed row proposes and never supports (the rule v17 already applies to kinds) |
| `constraints` | data, per domain: for a relation type, its roles and what may fill each; for an entity kind, its capabilities; for an effect kind, the pairs it transmits to |
| `provenance` | who authored it, when, and what that author had read (see §5), plus the hash at the freeze |

A constraint is a row's own data. A checker asks the registry and does not carry a private list. `entity_kinds`,
`capabilities` and the v17 relation seeds migrate into it; the existing tables stay readable as views for one release.

## 3. Relations have no direction; direction is a perspective (proposed amendment to D18)

**A relation is one fact.** One row, unordered participants, each filling a **role**. The type says what may fill each role
(a kind or a capability). `binds` has a role for the instrument that binds (a document kind) and a role for the bound party
(an entity with `party_to_contract`); a mine can fill neither. That refuses the pilot's defective hop mechanically.

**One-sided relations exist as much as two-sided ones.** A row needs one filled role. The other role can be an open slot,
recorded as a typed gap: the relation is known from one side and the other participant is unknown. An unknown never
eliminates and never supports, as everywhere else.

**Direction comes from where you stand.** A traversal names its starting role. Transmission and hop discount are keyed by
`(relation type, starting role, target role, effect pair)`, so `ownership` can carry one weight seen from the parent and
another from the subsidiary. A symmetric type (`competitor`) has the same role on both sides. The relation is documented
once and read from either side, so one piece of evidence is not counted twice for two directions.

**What becomes mechanical and what does not.** Mechanical: the participants fill roles the type allows; a quote is attached
and occurs in the document; the arithmetic; the kind's review state. Still judgement: that the quote actually shows the
relation. So the blind judge keeps a second pass on each hop, as in the pilot's diagnostic (decision 2).

**Migration.** The 23 transmitting types in `lookbacks/k14/registry.json` have only from-to pairs. Roles for them are authored
once, marked `unreviewed`, and revised on evidence. The v16 types have no stated roles; that authoring is a choice and is
recorded as one.

**Dilution buckets stay separate.** Types are declared and reviewed. Buckets (`nomad16/dilution.py`) are emergent
partitions of relation instances. A bucket may be promoted to a type when the evidence supports it.

## 4. Instruments and expressibility (open, for discussion; no decision proposed here)

K14 (ii) as pre-registered asks whether the found entity is expressible: a listed instrument references it, and a document
says so. Rob's view is that the point of the system is to find the basket that fits the thesis over the forward probability
space and to express it through any set of instruments, synthetic ones included. On that view expressibility is not a
property of the entity. It is whether some instrument set gives the constructed basket a non-flat response to the entity's
outcomes, which is what basket construction already computes.

Two consequences for K14. A reader looking through news pages cannot establish an instrument reference, so (ii) as written
will often fail for a reason unrelated to entities (the pilot). And a "dies" verdict on it would not separate "no useful
entities" from "no way to see instruments". Options: (a) keep (ii) and accept a weak test; (b) replace (ii) with a
harness-computed basket response, where the reader proposes entities and chains and the harness tests whether the
constructed world changes; (c) hold K14 until the instrument model (V4) is settled. Recommendation: (b) or (c), not (a).
V4 (instruments as entities) is held until this is discussed.

## 5. Decoupling forward work from past results (proposed D30)

Today several things wait on results that are about the past. What each depends on, and what would replace it:

| Coupled today | Why it hurts | Proposed |
|---|---|---|
| V3 to V5 wait for K14, and K14 reads v15's rounds | v15's lock-time documents mostly no longer exist (6 of 10 rounds readable, at the floor); the record is mostly operator priors | **K14 is read forward.** New events, documents captured at lock and stored with hashes, so readability holds by construction. The v15 reading stays as a labelled sensitivity and never gates |
| The template and registry authorship guard (rounds 1–4 and 1–7) | A look-back needs it because the events were already seen when the artifacts were written. R16-001 and v15 rounds 5 to 15 are exposed to the K8, K10, K11 and back-fill files | A **forward** event that happens after an artifact is frozen cannot have influenced it. So the guard only ever binds look-backs. Every registry row carries `provenance` and a freeze hash, and a forward block declares its freeze before its first event |
| K8 waits for expectations and the v15 store | The v15 store is the limit; the run is likely unreadable | K8 gates **only** the stock-pair decision. Nothing else waits on it |
| K7 (the census, by hand) | Blocks expression claims | Gates only expression claims. It runs whenever it is done |
| The dilution ratification | Needs real observations | Already forward-only; it waits on no past result |
| V3 to V5 build | Spec: "spend follows a measured block" | Build the schema **dark**, behind switches that are off (as `PERSON_INGEST` is), and let the forward K14 turn them on. This costs effort that is wasted if K14 dies, so build only the cheap parts first |

**Forward K14, as a sketch.** Intake picks events under the existing rule. At lock the harness captures the documents
with content hashes (`evidence`, `pit_fetch` and the document entities already do). A fresh cold session reads each event
twice from a package built by `lookbacks/k14/package.py`; the support script and a blind judge decide the find. A reading
costs about 130k tokens, so forward K14 is much cheaper than a round: it needs events and documents, not an operator. The
rule for readable and for dies is the spec's, restated forward: at least 6 readable forward events, and dies if fewer than
`ceil(X14 × readable)` show a find. The rate at which qualifying events arrive is the limit, and I do not know it.

## 6. Decisions (Rob's)

1. **D29.** One registry mechanism for kinds, relation types, capabilities, effect and instrument kinds: ratify, amend or reject.
2. **D18 amended.** Relations undirected with roles and a perspective; one-sided relations allowed; the judge's second pass
   on each hop kept: ratify, amend or reject.
3. **Expressibility (§4).** Choose (a), (b) or (c), or say how you want it to work.
4. **D30.** Look-backs become non-gating; K14 is read forward; V3 to V5 built dark: ratify, amend or reject. This changes what
   you set today ("V3 to V5 follow K14 as pre-registered"): it keeps K14 as the gate and moves the reading forward.

## 7. The hedge is a parallel thesis; N baskets from the pool (proposed D31, from Rob, 2026-09-30)

**Idea.** A narrative hedge is not a separate mechanism bolted on a basket. It is a **correlated parallel thesis** over the same event:
when a thesis is constructed, so are the theses that hedge it, and N baskets are then built from the whole pool to fit whatever objective is needed.

**What it implies for the design (proposed):**
- A thesis record can carry a `parallel_of` link to a primary thesis. A parallel thesis is a full thesis: it narrows the reachable set,
  cites documented positions and bounds for every exclusion, and an exclusion resting on an unknown is refused. It is not a free-standing story.
- A parallel is *correlated* (same scenario, same ACK chain) and *decorrelating* (Rob, 2026-09-30, correcting the first wording): both stay
  **long**, and neither is a short. What separates them is that, as the chains run downstream from the shared root, other data (each company's
  contracts, hedge book, geography, capital structure, refining or fee share) makes their effects on the companies progressively less aligned. Across the thesis outcomes the
  effect vectors of the two company sets diverge in *magnitude and degree*, not in sign, so one narrative covers the other's weak outcome.
  The measure is the alignment (the cosine, the machinery already behind angle classes and junctions) of the two effect vectors across the thesis outcomes, and how
  it decays with depth. It is ex ante, derived from documented positions along the chain, not read off realised price correlation.
- **The hedge DAG (Rob's structure, proposed).** A thesis that wants a hedge carries **its own DAG whose final node is the thesis**. Every position or effect that
  hedges its narrative feeds into that sink by a cross-reference. The hedging is **one-way**: the thesis is hedged by the others, and the others are not
  thereby hedged by it. A different thesis has a different DAG and may share nodes with it. The graph is acyclic by construction (the thesis is the sink),
  which is what a mesh of mutual references is not.
- **What the depth tests were and were not.** `lookbacks/scenarios/depth_hedge_v2` and `v3` used realised return correlation by depth as a stand-in. They showed
  the correlation gradient and that the sign at depth depends on the cause of the move; they did not test this mechanism, which needs the ex-ante effect vectors.
  The test of the mechanism is whether the *derived* divergence of effect vectors across outcomes predicts the *realised* divergence of payoffs, outcome by outcome (validation of the payoff-matrix estimator).
- **N baskets** are built from the pool, each under an objective (maximin, minimum regret, a loss cap, a shape). The spec's rule stays: balancing
  *within* a basket is construction, balancing *across* baskets is forbidden, because it nets away the divergence.

**Guards I would attach, because the flexibility is the risk.** The number of parallel theses and of baskets multiplies the ways to fit the
outcomes after the fact. So: (1) the list of objectives is declared at lock, not chosen after the payoff matrix is seen; (2) N has a budget
(an unset appetite value, `BASKET_N_MAX`); (3) each basket is scored on its own declared objective, and the set is scored separately; (4) a parallel
thesis has to pass the same anchor checks as the primary. Without (1), "N baskets to fit whatever we need" can always be made to fit.

**Decision (Rob's).** D31: ratify, amend or reject, and set `BASKET_N_MAX` (or say to propose one).

### 7.1 Construction, not search (Rob, 2026-09-30; proposed, not built)

The hedge is **constructed thesis-first**, not found. The narrative and thus the thesis come before the basket and guide it, in both cases:
1. **The position basket** carries its own thesis over the outcome space, and so its **failure set**: the outcomes where its payoff is lowest (the reachable outcomes its thesis excludes, and the thesis outcomes with the weakest payoff).
2. **Construct the hedging thesis** against that failure set: a claim over the same outcomes whose thesis set covers it. It is a full thesis: every exclusion is anchored to documented positions or bounds, and an unknown never eliminates an outcome.
3. **Then construct the hedging basket to fit that thesis:** choose instruments (equities first) whose documented downstream effects, per outcome, fit the hedging thesis. The search happens *inside* the constructed narrative, over baskets. It is not a search over narratives.
4. The pair is scored on its own declared objectives (D31 guards: objectives declared at lock, N capped, each basket scored on its own objective).

**What the depth and price tests did instead:** they took baskets as given (by depth, by sector) and asked afterwards whether any of them hedged. That is a search, so it could not test a procedure that constructs.

**The falsifiable claim, then:** for a primary basket and its failure set, the constructed hedge (thesis, then basket) gives a **lower worst case across realised outcomes, out of sample**, than (i) the primary alone, (ii) a de-risking control at the same cost, and (iii) a hedge built **without narrative guidance** (a purely statistical one: minimum correlation or minimum variance fitted to the same universe).
If the narrative-guided hedge does no better than the blind statistical one, the narrative is decoration. The generative freedom is the risk (a narrative can be built to fit anything), which is why the anchor rule, the declared objectives and the cap on N are conditions of the test and not extras.

### 7.2 The general form (Rob, 2026-09-30: designing specific scenarios where it can work means it is not yet understood)

The mechanism must not need a scenario. Stated with no domain in it:

- A position has a payoff vector **p** over an outcome space **Omega** (typed outcomes, as an ACK's vocabulary). Its **failure set** is A, the outcomes where p is lowest.
- The universe supplies instruments with payoff vectors s_j over Omega (with gaps where unknown). All are long-only.
- **A hedge exists (at the margin) exactly when some non-negative combination of instruments pays on every outcome in A** (Ville's theorem): either such a combination exists, or there is a distribution q over A under which every instrument has non-positive expected payoff. That second case is the whole content of "no hedge in this universe". It depends only on the payoff matrix, never on the domain.
- **Cost is the price of the hedge**, not a special case: a fairly priced instrument that pays on A must pay less elsewhere, so a hedge always gives up upside (the trade the maximin makes).
- **The narrative's general role is a prior over the payoff matrix's sign structure**: which instruments pay in which outcomes, supplied from anchored mechanism chains. It is worth most where the matrix cannot be estimated from data (rare or new event classes, regime breaks) and least where it can (a stable single factor with long history, as the FOMC test showed). So the narrative's advantage over a blind statistical hedge is a function of estimation difficulty, not of the domain.

**What follows for implementation and for testing generality.**
1. The engine takes an outcome space, a position payoff vector, an instrument payoff matrix (with typed gaps) and constraints. It contains no event class. Domains enter only through adapters that supply exposures and outcomes.
2. Do not pick the events. Run the same procedure on **every** round the intake yields, with the shadow comparator (a blind statistical pair) always on, and let the record decide.
3. Generality is shown when success and the narrative's advantage are **predicted by two domain-free quantities** across all classes: whether instruments pay on the failure set (the condition above), and how much data the blind fit had (the number of trailing observations). A test that only works in chosen scenarios is a test of the scenarios.
