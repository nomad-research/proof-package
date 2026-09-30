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
- A parallel is *correlated* (same event, same outcome space) and *divergent* (its response across the outcomes has a different sign
  pattern from the primary's, so the pair lifts the worst case). Both are properties of the payoff matrix, not of the holders, so they need the
  payoff-matrix estimator (per outcome, per instrument) before they can be checked.
- **N baskets** are built from the pool, each under an objective (maximin, minimum regret, a loss cap, a shape). The spec's rule stays: balancing
  *within* a basket is construction, balancing *across* baskets is forbidden, because it nets away the divergence.

**Guards I would attach, because the flexibility is the risk.** The number of parallel theses and of baskets multiplies the ways to fit the
outcomes after the fact. So: (1) the list of objectives is declared at lock, not chosen after the payoff matrix is seen; (2) N has a budget
(an unset appetite value, `BASKET_N_MAX`); (3) each basket is scored on its own declared objective, and the set is scored separately; (4) a parallel
thesis has to pass the same anchor checks as the primary. Without (1), "N baskets to fit whatever we need" can always be made to fit.

**Decision (Rob's).** D31: ratify, amend or reject, and set `BASKET_N_MAX` (or say to propose one).
