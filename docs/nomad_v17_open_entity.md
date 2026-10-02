# Nomad v17 — the open entity

*2026-09-29. A delta against v16-final (Sections C–G of `nomad_the_system_as_it_stands.md`). One change, taken as far as it goes: **an entity is anything with a state that can change, that can be observed, and that can be related to other entities.** Nothing here is built. The premise change (D0′) is applied on Rob's instruction of 2026-09-29; every mechanism below is proposed, tagged `[v17]`, and has a test or an acceptance check. v16 stays the build reference until items are ratified.*

*Evidence read for this document:* the v16 spec and theory (Sections C, D, E, F, G); the repo at `be893a6` (`nomad16/*.py`, `config/seed.json`, `state/nomad16.db`), including the R16-001 store: 7 holders, 2 nodes, 25 positions, 9 effects, 131 evidence rows. Every statement about the code or the store below was read from those, not recalled.

---

## 0. The change in plain English

**What v16 gets wrong.** D0 widened the premise to "any economic or financial entity" and then wrote the widening as a list: companies and their assets, sovereigns and agencies, central banks, funds and indices, commodities, currencies, contracts. The harness enforces the list. `positions.py` accepts four holder classes and ten entity kinds and refuses everything else. The one document-like kind, `contract`, is a label on a holder: it has no parties, version or lifecycle. There is no kind for a person, a supply chain, a place or a market narrative. Three deeper things are closed as well:

1. **Two tables for "things".** `holders` (a fixed list) holds whatever can carry an effect. `nodes` (an open registry) holds whatever a position is held *on*. The same real thing has to be entered twice under different keys, and effects can only land on a holder.
2. **Documents are receipts.** The `evidence` table stores 131 documents for R16-001, and 22 of the 25 positions cite them, but a document can never have a state, never be the thing an event happens to (a licence revoked, a contract terminated), and never be a party's relation to another party.
3. **Relations are labels, not rows.** v15 had a `relations` table (mode, `transmits`, hop discount). The v16 fresh build did not carry it, so the code holds no edge rows. `effects.relation` is a free-text label checked only against the transform table. Adjacency is a `neighbours` list on nodes. Ownership is a `holders.parent_id` column with one parent, no share and no date; joint ownership exists only as per-asset `share` positions.

**What v17 does.** One table of entities. Kinds and relation types are open registries, with the same register-on-first-use behaviour `node_type` already has. Documents, people (in public capacity only), places, instruments, and composite or abstract things such as a supply chain, a corridor or a market are all entities. Relations become dated, sourced rows. A document is an entity first and evidence second.

**What stays closed.** Openness applies to what can *exist* in the graph. It does not touch what can *support* a claim. Only physical, contractual and accounting relations with a documented instance in force at the clock may support; a new kind or relation type starts as proposal-only until a document-backed instance and a transform entry exist. The time wall, the veto set, the five-term risk vector (never multiplied), the ledger discipline and every kill test are unchanged. Openness on what exists, strictness on what counts.

**Why it might matter, and what it will not do.** The v16 look-backs say the old record was too thin to answer K8 and K10, and the reason is deeper than dating: the back-fill found that the 127 positions still undated are the operator's own priors, not documents, and K10 found that every one of its 16 templates tests an attribute no v15 row ever held. v17 cannot repair that record and does not try. What it does is make the *forward* record addressable: every new fact cites a document entity, its date is derived from that document, and obligations name the document that governs them. Separately, the events v16 has played sit at unlisted reactors, where stake is high and instruments do not exist (the wall map: expression 43.8%, unassessable 53.8%). Documents, contracts and officers attach to *listed* entities more directly, so events that touch them may land nearer to something that can be held. That is a hypothesis, and K14 is its test. **v17 does not by itself make anything tradeable, does not change a threshold, and does not include thesis stacking, the decay-curve measurement or the pooled-basket idea** (§11).

**Where things are.** §1 the rule; §2 documents; §3 persons; §4 composites; §5 instruments, places, stories; §6 relations and the transform seeds; **§7 the register: every part of the system this touches, and how far**; §8 examples; §9 tests; §10 phases; §11 what v17 leaves out; §12 risks; §13 amendments and the two decisions that are Rob's; §14 numbers; §15 glossary.

**How much it costs to find out.** Three kill tests (K14–K16, §9). Phases V0–V2 are additive and change no verdict on v16 rounds (check A1); V3–V5 do not start until K14 has been read (§10).

---

## 1. The rule `[v17]` (D0′)

### 1.1 Definition

> **An entity is anything that has a state that can change, that can be observed through some carrier, and that can stand in typed relations to other entities.**

Everything v16 calls a holder, a node, an asset, a counterparty, an authority, an aggregate, an instrument or a carrier's subject is an entity **playing a role** (§1.5). "Company" is a kind of entity, not the scope. Round 15 and R16-001 studied one kind first.

Three tests decide whether something is an entity, and all three are checked when it is registered:

| Test | Question | If it fails |
|---|---|---|
| **State** | Is there at least one attribute whose value can differ at different times? | It is a label (a sector name, a category). Registered as a classificatory tag, never as an entity |
| **Observable** | Could some carrier, in principle, read that state? | Registered as `unobservable`. It may **propose** and never support (T5's rule for analogy) |
| **Relational** | Does it stand in at least one typed relation to another entity? | It is registered and held as an orphan; `orphans` reports it |

Registration is permissive and valuation is strict, which is T5's rule applied to what exists.

### 1.2 What an entity has

| Part | Content |
|---|---|
| **Identity** | `entity_id`; canonical name; dated aliases; external identifiers (LEI, CIK, ISIN, vessel IMO number, registry number, docket number) held as `entity_ref`s. Identity is a claim with evidence (§3.4) |
| **Kind** | A node in the kind tree (§1.3). A kind gives an entity its capabilities and the attributes registered for it |
| **Lifecycle** | `exists_from`, `exists_to`, each with its own `knowable_from`. A company is delisted, an officer resigns, a contract is terminated. As-of reads honour both dates |
| **State** | Dated statements about the entity: the existing `positions` table, generalised (§6.4). Apart from lifecycle dates, no state is held on the entity row itself |
| **Observables** | `reports_on` edges from document series (§2.6). No observable means `not_covered` for every term that needs one |
| **Relations** | Typed, dated, sourced rows (§6) |

### 1.3 Kinds are a tree and a registry

`entity_kinds` is a mutable registry, like `node_types`. An unseen kind registers on first use as `unreviewed`. An unreviewed kind can propose and never support (§1.6). The operator ratifies a kind (`reviewed`) when it has a scale attribute or an explicit "none", a capability list, and at least one attribute registered for it.

Kinds form a tree, so capabilities inherit (`organisation` → `company` → `listed_company`). Seed kinds:

| Kind (children) | Examples | Scale attribute (§5.3) | Typical carriers |
|---|---|---|---|
| `organisation` (company, agency, central_bank, fund, sovereign, cooperative, exchange, court) | a utility, a regulator, a sovereign issuer | revenue / capacity / assets under management / none | filings, dockets, announcements |
| `facility` (plant, reactor_unit, mine, field, vessel, pipeline, port, data_centre, warehouse) | Fermi 2, a smelter, a tanker | capacity or throughput | status reports, AIS, satellite |
| `person` **(public capacity only, §3)** | an officer, a director, a controlling owner, a governor | none | filings, appointments, registers |
| `instrument` (share, bond, option, future, etf, event_contract, cds) | a bond, an event contract | price band of the hedged residual | prices, quotes |
| `commodity_grade` | a grade at a location | volume / price | indices, exchanges |
| `currency` | | none | prices |
| `index` | | none | index levels |
| `place` (region, zone, strait, port_area, hazard_area) | MISO zone 7's footprint, a strait | none | hazard catalogues, satellite |
| `document` (filing, contract, statute, regulation, licence, tariff, notice, ruling, report, release, dataset) | a licence, an offtake, a docket entry | notional / obligation amount where it has one | itself, its issuer's register |
| `document_series` | the NRC daily status reports; EDGAR filings by one issuer | none | its own fetch path (§2.6) |
| `composite` (supply_chain, corridor, market, ownership_group, cluster, regime, class) | the payers under one cost-recovery clause; a market zone | derived from members (§4) | members, or its own carrier |
| `story`, `factor` | a market narrative; a tide | none | price loadings |

The seed list is a starting registry, not a boundary. Adding a kind is a data change, not a code change.

### 1.4 Capabilities replace the closed lists

v16 filters role fillers by `holder_classes` and `entity_kinds` in `derive.py`. v17 filters by **capability**. A kind declares capabilities; roles in obligation templates require them.

| Capability | Meaning | Declared or derived |
|---|---|---|
| `party_to_contract` | Can be bound by a document | declared on the kind |
| `files_reports` | Files periodic or event reports with a regulator or exchange | declared per entity, evidenced by a document |
| `issues_debt` | Has or can have coupons and maturities | declared on the kind |
| `operates_assets` | Operates facilities | declared on the kind |
| `holds_office` | Can hold an office | declared on `person` |
| `controls` | Can be the controlling party in a control relation | declared on `person`, `organisation` |
| `has_operating_scale` | Has a scale attribute (§5.3) | declared on the kind |
| `expressible` | At least one instrument references it directly | **derived** from `references` edges at the clock. Used by expression, intake preference and reports; **never** by derivation, reach or conditions |
| `expressible_by_proxy` | An instrument references an entity it is documented to be exposed to | **derived** from documented exposure edges (§5.2). Same restriction |
| `observable_by(kind)` | A `reports_on` edge from a series of that carrier kind exists | **derived** |

`holder_class` retires. Its four values map to a kind plus capabilities: `listed_instrument` becomes an organisation with `files_reports` (that is what the seed template `obl.material_event_current_report` means by it: a listed filer, a legal status, not the existence of an instrument); `unlisted_operating_asset` becomes `operates_assets` or a `facility` with `has_operating_scale`; `aggregate` becomes a `composite` (§4); `authority` becomes an `organisation` of kind `agency` with no scale. The derived capabilities `expressible` and `expressible_by_proxy` read instruments, so they stay out of derivation, reach and conditions, exactly as the existing import-linter test (`test_28`) keeps prices, stories, construction, instruments, paper and vetoes out of the generation modules.

### 1.5 Roles are relational, not kinds

| Role | Meaning | Where it lives |
|---|---|---|
| **Holder** | The subject of a position | `positions.holder_id` |
| **Node** | The object a position is held on; the locus of a round's event | `positions.node`, `rounds.node` |
| **Obligor** | The entity a template says must produce a document | `ack_nodes.holder_id`, `bindings{role: entity}` |
| **Party** | An entity bound by a document | `binds` relation rows |
| **Authority** | An entity whose documents govern others | `governs` relation rows |
| **Junction node** | A shared constrained node behind a story pair | `junctions.shared_node` |
| **Sink / source** | Where an effect lands or starts | `effects.holder_id` |

The same entity fills several roles. A sovereign holds a position on a strait and is the node its bondholders hold positions on. That sentence was true in D0 and was not representable in the schema; it is representable once `holders` and `nodes` are one table. `nodes.node_kind` (`event` or `attribute`) keeps its meaning as a property of the *round's use* of an entity, recorded on the round, not on the entity: a currency is an entity, and it is an "attribute node" in the rounds that put positions on it.

### 1.6 What stays closed

| Closed | Why |
|---|---|
| **What may support** | Only physical, contractual and accounting relations, backed by a document-evidenced relation row in force at the clock, may support an effect or an ACK condition. Unreviewed kinds, unreviewed relation types (which cannot even be composed through, §6.2), classificatory memberships, `inferred` and `implicit` statements, price, satellite, GDELT and decision-model output propose and never support (T6, §6) |
| **The time wall** | An entity, relation or statement exists for derivation only if its `knowable_from` ≤ the segment clock |
| **The veto set** | Five vetoes, unchanged. No entity kind gets an exemption. An undocumented relation is *unknown*, and unknown keeps an outcome in (§6.5) |
| **The five-term vector** | Never multiplied, never gated. New kinds get typed gaps, never fabricated denominators |
| **The ledger** | Append-only, hash-chained. Merges, splits, kind changes and document state changes are appended events, never edits |
| **Construction and scoring** | Capped instruments only; one basket per ACK; no netting across baskets; the paper book. Not touched |

---

## 2. Documents are entities `[v17]` (D19, D20)

### 2.1 Two jobs, kept apart

| Job | What the document is | Off the path or on it |
|---|---|---|
| **Evidence** | Something that *states* a fact or is a *component* of a derived fact (a filing, a status report) | Off the effect path: provenance. This is all the `evidence` table does today |
| **Reification** | Something that *is* a relation or a rule: a contract, a licence, a tariff, a statute, an indenture | On the path: it is the edge between parties, and it can be the thing an event happens to |

One document can do both: a contract evidences its own terms and reifies the relation between its parties.

### 2.2 The record

A document entity carries `content_hash`, `url`, `published_at` (its `knowable_at` in the data product's terms), `issuer`, `version_of` (a contract has versions; each version is immutable by content hash), and a lifecycle state:

`draft → executed → in_force → (amended | suspended) → (terminated | expired | revoked | superseded)`

Each transition is itself a dated statement, evidenced by another document (a termination notice, a revocation order). `amends` and `supersedes` are relations between documents. Each `evidence` row that is actually cited is linked to a document entity keyed by content hash through a side table; nothing is rewritten (§7.6). Of R16-001's 131 evidence rows, 94 are EDGAR filing-list fetches: reads of a series, not documents.

### 2.3 Knowability derives from the cited documents `[v17]` (D19)

**What v16 does.** `position_add` refuses a row without a `knowable_from`, defined as "the date its source became public", and refuses a `stated` row with no source document or evidence id. The operator types the date. That is a typed input to the time wall, and it was introduced after v15 left 141 of 200 rows undated.

**What R16-001 shows.** 22 of its 25 positions cite evidence, and **20** carry a date equal to the earliest cited document's date. So the operator's stamps are mostly right, and derivation does not repair a defect visible in this record. What it changes is that the date stops being typed, and that the two disagreements become auditable. They are:
- `prior_outage_restart_days = 4`, stamped 2026-05-22, against documents dated 05-20, 05-20, 05-22 and 05-26. A duration needs the start and the end, so the right derived date is the latest *component* (05-26), or 05-22 if the document dated 05-22 states the four days by itself. The stamp is not obviously an embargo; which is right depends on how each link is tagged.
- `listed_domestic_filer`, stamped 07-02, against documents dated 06-05 and 07-03.
- **3** positions cite nothing: `unit_status = offline` (from the event line: its `source_document` names the reveal), and two `inferred` operator estimates whose own source note says no filing states them.

A naive "earliest cited document" would date the restart duration too early, and a mis-tagged early document would leak the future into the past. That is the risk of derivation, so the rule below makes the judgment explicit and checkable.

**The rule.**
1. A `stated` statement must cite at least one document entity through its links (v16: a `source_document` or evidence id). `inferred` and `implicit` statements are admitted without one, as in v16, and stay unknown for derivation and reach. **The time wall still needs a date for them, and it is `recorded_at`**: the append time the ledger stamps itself. An operator's own estimate is knowable from when it was made, and a later migration or back-fill can therefore never make a row visible to an earlier clock.
2. **The admission record is a document.** At admission the event line and its date are written as a document entity (`published_at` = when the line was knowable, per Q8). Without this, every round's first `stated` position (R16-001's `unit_status = offline`) would have no document and its derived ACK would degrade to a switch.
3. Each link is tagged **`states`** or **`component`**. **`component` is the default.** A `states` tag must carry the **quoted span** of the document that states the value, and the harness checks that the span occurs in the document's stored text and, for numeric and enumerated attributes, contains the value. A link that fails the check is stored as `component`.
4. `knowable_from` = the **earliest** `published_at` among the `states` links; if there are none, the **latest** among the `component` links; if the statement has no links, its `recorded_at`. It is derived, never typed.
5. An operator may set `embargo_until` later than the derived date, with a reason. It may never set an earlier one.
6. **Scope.** Positions and relations. `bounds` and `node_facts` cite a document and derive the same way. `ack_firings.knowable_from` is the delivered document's `published_at`. `census_rows` keeps its own time guard.
7. `published_at` is the data product's capture-gated `knowable_at`, so a document captured late is dated by when it could first have been seen (G8.2, `capture_time_gating`).

v16 rows are not rewritten. For them the derived date is computed beside the typed one and disagreements are reported.

**What the old record cannot get from this.** The blind back-fill already asked whether the old positions' sources resolve to dated documents: 14 of 141 did, and the rest were not documents. v17 does not claim to rescue the v15 record. It makes the forward record's dating rest on documents rather than on a typed field.

### 2.4 Reified relations: one hop, two ways to land `[v17]` (D20)

A contract, licence or tariff between parties creates a relation row between them (§6). Two things follow.

- **Traversal is one hop.** An effect moving from party A to party B through the document pays the hop discount of the relation type once. Passing through the document must not cost a second hop, or legal chains would be penalised for being documented.
- **An effect can land on the document itself.** A `state` effect (terminated, breached, force-majeure declared, revoked) lands on the document entity, and transmits to the parties through `binds` (§6.5).

A document that is not `in_force` at the clock, or is outside its term, supplies no relation for support. This is the same rule as the time wall, applied to validity: `valid_from ≤ clock < valid_to` and `knowable_from ≤ clock`.

R16-001 already contains this structure without naming it. `cost_recovery_passthrough = true` on DTE Electric (knowable 2026-04-30) and the position `role = pay fuel and purchased power through the PSCR clause` on the retail customers are one cost-recovery clause between two parties. E005 (`dte_retail_customers` cost, relation `counterparty`) is the effect that clause carries.

### 2.5 Documents are what obligations run through `[v17]`

An ACK is an obligation on an entity to produce a document of some kind by a window. In v16 the obligation's source is a bare number in `bounds` (`statutory_min_days`, …) with a text `source_document`. In v17 a template names its **governing document** (the statute, regulation, licence condition or contract clause) as a role filler. Its version, amendment history and `knowable_from` are graph facts, so "which rule was in force on that date" is a query. `bounds.source_document` becomes an entity reference.

### 2.6 Carriers are document series

A `carrier` in v16 is a row with a `fetch_path` and a `read_in_full_rule`, matched to nodes by `node_types`. In v17 a carrier is a `document_series` entity (a composite of documents by issuer, class and cadence: the NRC daily status reports, an issuer's filing list, a docket) with:

- `reports_on` edges to the entities and attributes it covers (this replaces the `node_types` list, which is a kind-level guess);
- its fetch path, read-in-full rule, cadence and latency as attributes.

Q7 (scoreable per call) becomes a graph query: does a series with a working fetch path `report_on` this entity's state attribute? "No carrier" is then a typed, countable gap (`not_covered`) per entity and attribute, not a per-node-type judgement. Silence resolves an absence claim only when the series was read in full through `due_at` (D9, unchanged).

---

## 3. Persons, in public capacity only `[v17]` (D21)

### 3.1 Scope: capacity, not biography

A person is an entity of kind `person`, and the schema treats it like any other. What the system records about a person is limited to what they are **in an economic role, from a public document**:

| Allowed (each with a document) | Not recorded, ever |
|---|---|
| Offices held and dates (`holds_office_at`) | Health, family, residence, private finances |
| Disclosed control or ownership stakes and the share | Anything not in a public document of the person's capacity |
| Signatory or authorised-representative status on a document | Inferences about personality, motive or intent |
| Insider status and disclosed transactions | Location or movement |
| | Any attribute not in the registered public-capacity list |
| | **Designation on a sanctions or debarment list, and anything that touches offences or proceedings against an individual.** This borders on offence data, which several jurisdictions treat as a special category. It is not recorded, for any person, until a separate legal review says how |

The attribute registry (`position_attributes`) gets an `applies_to_kinds` column. A statement about a person whose attribute is not registered for `person` is refused, so the limit lives in the data structure rather than in a reviewer's memory. The data product gets a matching conformance check (`person_scope_guard`, §7.4).

### 3.2 What persons add to the graph

- **Relations:** `holds_office_at`, `controls` (with a `share` attribute), `signatory_for`, `appointed_by`. All are contractual or accounting relations when a document evidences them.
- **Effects:** an office vacated or a control change is a `state` or `control` effect that lands on the person and transmits to the organisations they hold office at or control (§6.6). Some events that land directly on a listed company (an officer leaves, a controlling owner changes) are person events.
- **Obligations:** persons are obligors. Officer-change notices, insider-transaction reports and beneficial-ownership filings are documents a person or an issuer must produce inside a statutory window. Each is a candidate obligation template with a person, or an organisation bound to a person, as the obligor. The windows are statutory and live in `bounds` with their governing document (§2.5); this spec does not restate any jurisdiction's deadline, because each is a value to be read from the regulation and dated, not remembered.

### 3.3 Where persons attach to something holdable

This is the reason persons are in v17 and not an afterthought. A reactor scram has stake at an unlisted unit and a fraction of a percent at the listed parent (R16-001: 9.19% at DTE Electric, 0.01–0.4% at DTE Energy). An officer change or a control change lands **on the listed entity or its immediate control chain**, so `expressible` is true at the first hop more often. Whether it is true often enough is K14.

### 3.4 Identity is a claim with evidence `[v17]`

Persons are the hardest kind to resolve, so the rule is strictest here and applies to every kind:

- A merge (two records are one entity) or a split is an **appended event** with its evidence, never an edit. An as-of read before the merge sees two entities.
- **Exact identifiers first** (a filer identifier, a registry number, a LEI, a vessel IMO number). A name alone never merges two persons. An unresolved match stays `unresolved` and does not carry support.
- Alias merges for organisations or places need operator ratification with a reason.
- Every wrong merge found is reversible by an appended split, and the graph as of any earlier clock is recomputable (K15).
- **As-of time for identity events.** A merge or split is visible to a read when its evidence's `knowable_from` ≤ the segment clock **and** its `recorded_at` ≤ the lock manifest's `ledger_cutoff` (the same two conditions every ledger row already faces).
- **Expect a low resolution rate for persons.** With no date of birth or address, a name alone never merges. Unresolved persons carry no support. That is the safe direction, and it is a stated cost.

### 3.5 Ingestion is a separate switch from schema, with preconditions

The schema can describe persons at no risk. **Storing person data is different, and it is off by default.** `PERSON_INGEST = off` is enforced in the harness tools as well as in the data product: `entity_upsert` refuses a `person` row while it is off (A9), so a session cannot enable persons by accident.

Turning it on has two preconditions this spec does not satisfy:
1. **A legal review** by someone qualified. Data about identifiable individuals, even in public capacity, is regulated in some jurisdictions (purpose limitation, minimisation, and rights to rectification and erasure).
2. **A place for erasable data.** The ledger is append-only and hash-chained, and `store_snapshots` keeps every row version, so **a person's data cannot be erased from it**. Ingestion therefore needs a design in which the ledger holds only an opaque person key and non-identifying state, while names, identifiers and anything else that identifies live in a separate erasable `person_vault` store, referenced by the key. Whether even the non-identifying state is linkable enough to count as personal data is part of the review.

Until both exist, persons stay in the schema and the templates and no person is stored. K14 counts person *roles* (an officer of the issuer, a controlling owner) from the documents; it stores counts, not people.

---

## 4. Composite and abstract entities `[v17]` (D22)

### 4.1 What a composite is

A composite is an entity whose identity is a **membership plus a rule**. A supply chain, a corridor, a market zone, an ownership group, a set of payers under one clause, a regime (a body of statutes and the agencies applying them), a cluster. Two `aggregate` holders exist in the R16-001 store: `dte_retail_customers` (payers under one cost-recovery clause; effect E005 lands on it, with a stake of `None`) and `miso_lrz7_energy` (the price at a market zone; no position or effect in the round refers to it). v17 makes them what they are.

### 4.2 Membership is a relation, with two grades

Membership rows are dated, sourced and moded like any relation, and the two grades are two relation types: `member_of` (documented) and `classified_as` (classificatory).

| Grade | Backed by | May support |
|---|---|---|
| **Documented** (`member_of`) | A contract chain, a tariff or order defining the population, a registry, bills of lading, a customs or filing record | **Yes** (accounting/identity mode) |
| **Classificatory** (`classified_as`) | An analyst grouping, a thematic label, a sector code | **No.** May propose. It is the sector or theme lens and nothing more |

This is the guard against the obvious failure. A supply chain the operator draws by inference is a story, not a structure, and T6's rule ("only physical, contractual and accounting relations may support") already says what to do with it.

### 4.3 Aggregation rules: how a composite's state is computed

A composite registers one rule **per attribute** (a supply chain can be a bottleneck for throughput and a weighted mean for cost). The rule is operator-ratified and pinned in the lock manifest, like a template.

| Rule | Composite state = | Use |
|---|---|---|
| `bottleneck` | The minimum over the members on the documented critical path | Serial chains, corridors |
| `sum` | The sum of member capacity or volume | Pooled capacity, a market zone's supply |
| `redundant` | The maximum, or the top-k, over parallel members | Where any of several suffices |
| `weighted_mean` | Σ weight × member value | Baskets of prices, cost indices |
| `share_of_total` | Member ÷ sum | Concentration attributes |
| `all` / `any` | Logical over member statuses | "Regime in force", "corridor open" |

**Transmission by recomputation.** Member → composite transmission is found by re-evaluating the rule with the member's state moved by the effect's magnitude and reading the relative change in the composite's state, capped at 1. A `bottleneck` member that is the binding minimum transmits at factor 1.0: the composite falls by the same relative amount, capped at 1. A member that is not binding transmits nothing until the effect drives it below the current minimum, and then only the part below it. A `sum` member transmits its share. A `redundant` member transmits nothing unless it is the maximum and its loss drops the composite to the next member. A `weighted_mean` member transmits its weight. `all` and `any` transmit only when the effect flips the logical result. Both evaluations and every input are recorded.

A rule needs documented inputs for every member it reads. **A member with an unknown input makes the composite state unknown**, never a guess. Unknown keeps an outcome in (D10), so an unknown composite widens the response band and does not cut a branch.

### 4.4 Derived state and observed state

| | Derived | Observed |
|---|---|---|
| Comes from | The rule over member statements | The composite's own carrier (a freight index for a lane; an operator's published market-zone figure) |
| Evidence | The members' evidence, inherited | Its own documents |
| May count as corroboration of its members | **Never** | Yes, as one independent source |

A derived state is arithmetic on facts already counted. If it could corroborate its members the graph would count each fact twice. The convergence measure in T7 (independent derivations, discounted by the depth of the most recent common ancestor) treats a derived composite as a **descendant** of its members' statements, never a second source.

### 4.5 Traversal through a composite: compress, do not exempt

1. **Member to composite** is accounting/identity and instant. The transmission is **computed by recomputation (§4.3) from documented inputs and recorded with them**. It is never assigned.
2. **Composite to dependents** goes through an ordinary typed relation (`input_supply`, `offtake`, `logistics`, `regulatory_scope`) that has a document behind it, and pays that relation's hop discount once.
3. **No sibling spread.** An effect on one member reaches another member only through a documented relation *between them*. A strike at one supplier does not move every other member of its supply chain, and a sector's membership spreads nothing.
4. **Attenuation still binds.** A composite hop's support is parent transmission × computed transmission × the dependent relation's discount, and must clear `SUPPORT_THRESHOLD`. A bottleneck's throughput is set by its **binding member**, not by a product of hop factors down the chain, so recomputation gives the binding member's own change and not a multiplied-down one. That is a stronger claim than chaining makes, and it is exactly what K16 tests: composite-level prediction against the same effects predicted along the members' separate chained paths. The composite does not launder reach that the documents would not carry, because the dependent relation's hop discount is still paid once and `SUPPORT_THRESHOLD` still binds, and because an undocumented member makes the state unknown (§4.3).
5. **Cycles are refused** at add time, and nesting is bounded by `COMPOSITE_DEPTH_MAX` (§14).

### 4.6 What composites buy

- **Reach without free hops.** A long documented chain is one node with a computed transmission. That is the honest version of "the butterfly effect applies to markets": distant effects propagate when the documents say the structure carries them, and are cut when it does not.
- **Exposures nobody wrote down become computable.** T7 says a basket carries exposures nobody wrote down, and that this sharpens as construction improves. An instrument's exposure to a composite is the sum of its documented exposure to the members. Declared exposure is a graph query.
- **Junction nodes are explicit.** K12's premise ("no shared node, no junction") gets a shared node that can be a corridor or a chain, not only a facility.
- **Pooled reading.** Members with `expressible` are the instruments a composite can be held through (§5.2). This is the entity-level ground under any later idea of merging theses (§11).

---

## 5. Instruments, places and stories `[v17]` (D23)

### 5.1 Instruments are entities

An instrument has a state (quoted, halted, expired, in default), observables (prices, quotes) and relations. The link that matters is `references`: instrument → the entity it prices (issuer, commodity grade, index, or the outcome of an event contract's ACK). A bond's indenture, an option's contract specification and a fund's prospectus are document entities that `govern` it, so covenants, coupon dates and settlement rules are graph facts and obligation candidates.

v16's `instruments.KINDS` (stock, etf, call, put, event_contract, each mapped to a cap class) is a closed set for a safety reason: an uncapped form is never held. v17 opens it as an `instrument` kind tree with a **mandatory registered cap class**; a kind with none is refused at construction. Opening the entity set does not touch the capped-loss rule.

v16's `instruments` table keeps its columns (`cap_class`, `listed_from`, `expiry`, `strikes`, `multiplier`, `cost_model_id`, `quote_source`, `underlying`). Its `holder_id` becomes a `references` row, so a share that references a company and an option that references its underlying are the same shape. **`ack_id` stays a column**: an ACK is a predicate row and not an entity, so no edge can point at it. An event contract's `references` row points at the entity its ACK is about, and its `ack_id` and `yes_outcomes` columns keep the link to the predicate. `stories.py` selects instruments by `holder_id` in five places (reach, loadings, construction inputs); each moves to the `references` lookup.

### 5.2 Expression by the graph

v16's `expression_term(view, holder_id, clock)` finds the best capped instrument linked to a holder through `holder_id` or the underlying's holder. v17 keeps the term and its values (1.0 hard-capped, 0.5 stress-capped only, 0.0 none) and computes it on the graph:

| Term | Definition | Reported |
|---|---|---|
| `expression` (direct) | Best cap class among instruments that `reference` the entity, `listed_from` < T_seg | as today |
| `expression_proxied` | Best cap class among instruments on entities the effect's entity is **documented** to be exposed to (ownership, offtake, debt, membership), with the **exposure share** | beside `expression`, never merged with it |

A proxied instrument carries the documented exposure as its stake link. In R16-001 that is the ownership share (1.0) and the cost-recovery clause that passes cost to customers, which together leave the shareholder a small residual. The operator's 0.01–0.4% estimates would then be checked against a documented chain instead of standing alone. For a composite, proxied expression is the set of members' instruments weighted by documented exposure.

### 5.3 Stake basis by kind, not by holder class

In v16 a stake is the effect's magnitude (a fraction of the entity's own scale) divided by a **materiality band constant** for its basis: for an unlisted operating asset `MATERIALITY_BAND` is 0.05, so R16-001's 100% availability reads 20.0 and 9.19% reads 1.838; for a listed instrument the denominator is the pre-event band of its hedged residual. The basis is chosen by `holder_class`. v17 chooses it by the **scale attribute registered for the kind**. `MATERIALITY_BAND` keeps its v16 keys (`listed_instrument`, `unlisted_operating_asset`, `aggregate`), so the appetite file pinned in an old round's lock manifest still loads and reproduces (A1); a fixed map reads the key for each basis. Values are never compared across bases without the basis shown (unchanged).

| Kind (or state of the world) | What the magnitude is a fraction of | `stake_basis` | If there is none |
|---|---|---|---|
| Entity with an instrument | The pre-event band of the hedged residual | `price_band` | `not_covered` |
| Facility, or organisation with a scale | Its operating scale over the same window | `operating_scale` | `not_disclosed` |
| Document with an amount | The document's notional or obligation amount | `notional` | `not_disclosed` |
| Composite | Derived from members per the rule (§4.3) | `derived_from_members` | `not_representable` until members are documented |
| Person | — | — | `not_applicable` (stake is read on the organisation they hold office at) |
| Agency, regime | — | — | `not_applicable`, as today |

| Basis | Reads `MATERIALITY_BAND` key | Status |
|---|---|---|
| `operating_scale` | `unlisted_operating_asset` (0.05) | v16 value, unchanged |
| `derived_from_members` | `aggregate` (0.05) | **Not a new basis.** It is v16's `class_scale` renamed, reading the same entry |
| `notional` | `notional` (new) | New provisional key; no v16 round reads it |
| `price_band` | none | The denominator is the computed pre-event band of the instrument. The `listed_instrument` entry (0.01) is unused today and stays so |

A basis with no entry yields `not_representable`, never a default. The rename touches new rows only; stored `surviving_risk` rows keep the label they were written with. **No R16-001 effect used `class_scale`**: its `surviving_risk` rows carry only `operating_scale`, `price_band` and `None`.

### 5.4 Places

Regions, zones, straits and port areas are entities of kind `place`. Facilities are `located_at` places, and hazard occurrences (a quake, a storm, a fire detection) are events at places. USGS, FIRMS, IODA and Portwatch are already registered carriers; in v17 they `report_on` places, and `located_at` is the physical relation through which a hazard reaches a facility.

### 5.5 Stories and tides

Stories and tides are already stored things with state (active or not) and observables (price loadings). v17 gives them entity ids so that `stories.path_nodes` and `junctions.shared_node` are foreign keys into the same graph. **No change to the S⊥, ρ, junction or construction mathematics.**

---

## 6. Relations, effects and the transform table `[v17]` (D18, D25)

### 6.1 Relations become rows

v16 has no edge table. v17 adds `relations` (ledger, append-only, `supersedes` for change):

`relation_id`, `from_entity`, `to_entity`, `relation_type`, `attributes` (share, term, priority, …), `evidence_ids` (each tagged `states` or `component`), `knowable_from` (derived, §2.3), `valid_from`, `valid_to`, `confidence` (`stated`/`inferred`/`implicit`), `reified_by` (a document entity, optional), `supersedes`.

**Two grains, kept apart.** v16 stores no pairwise relation. Two holders relate *through a node* when both hold positions on it (T6), and that through-node relation stays **derived**, a view over positions. v17 stores **direct** relations (ownership, contract, licence, tariff, membership, office, control) as rows.

**There is no automatic conversion of v16 data.** `holders.parent_id` carries no evidence or date, and positions name no counterparty. For R16-001 a one-time migration session writes the relation rows that the seven relation-labelled effects assume, citing the same positions and evidence. A row is `documented` where the cited evidence supports it and `inferred` where it does not. The count of each is the first reading of `edge_basis` (§6.5).

### 6.2 The relation-type registry

`relation_types` (mutable) replaces the free-text label: `type`, `mode` (physical/contractual, accounting/identity, attentional/classificatory, positional/analogical), `from_kinds`, `to_kinds` (at capability level), `symmetric`, `computed` (true for `member_of`), `default_hop_discount`, `review` (`unreviewed`/`reviewed`), `transmits` (which effect-kind pairs have transform entries).

- **No untyped relation.** `related_to` and its synonyms are refused. A new type registers as `unreviewed`, mode classificatory, which cannot support.
- **Mode is data on the type**, so T6's admissibility rule is enforced by the structure. It was previously enforced by whoever composed the effect.
- **A type becomes supporting** when it is reviewed, its mode is physical, contractual or accounting, and the transform table has an entry for the effect kind in question. `transform_add` on an unreviewed type is refused, and `effect_compose` refuses to compose through an unreviewed type or an attentional or analogical one, in the way v16 already refuses a relation with no transform entries. Whether a **documented instance** exists for a particular effect is recorded separately, as `edge_basis` (§6.5).

### 6.3 New effect kinds

`EFFECT_KINDS` (v16: volume, cost, price, revenue, obligation, availability, credit, margin, demand, timing, direction) gains two:

| Kind | Meaning | Lands on |
|---|---|---|
| `state` | A discrete status change: in force → terminated, in office → vacated, open → closed | documents, persons, composites |
| `control` | Who has decision rights over an entity changes | organisations, facilities |

### 6.4 Positions, generalised

`positions` keeps its name, columns and append-only rule. Changes:

- `holder_id` is an entity id (any kind); `node` is an entity id and is **nullable**: a null node means the statement is about the subject's own state (a reactor's `unit_status`, a licence's `state`).
- `asset_ref` (free text) is replaced by an entity reference to the asset, with the text kept when it does not resolve.
- `source_document` (free text; set on 1 of 25 R16-001 positions) is retired in favour of `evidence_ids`, which are document entities.
- `attribute` is validated against `position_attributes`, which gains `applies_to_kinds`.
- **`visible_positions` must include null-node statements for the subject.** It currently filters on `node`, so a statement about an entity's own state would be invisible to derivation and conditions.

### 6.5 Edge basis, not a new veto

Today `effect_compose` validates the relation only against the transform table, so an operator can compose through a relation that was never documented. T6 and E §6 both say `transmits` is a property of the **edge**; the v16 build has no edge to carry it. v17 supplies the edge, and then must decide what an *undocumented* relation means.

It means **unknown**, not false. An anchor that cannot be evaluated is absent, and unknown keeps an outcome in (T5, D10). So v17 adds **no veto**. Each effect instead carries `edge_basis`, in a side table (`effect_flags`, ledger):

| `edge_basis` | When |
|---|---|
| `root` | The effect has no parent |
| `documented` | A relation row of the composing type exists between the parent's entity and the child's entity, documented, in force and knowable at the clock, and the type is reviewed with a supporting mode |
| `proposed` | Anything else |

**What changes is what counts as support, not what exists.** Only `documented` effects count in (a) the convergence measure, (b) reach cuts (only a documented fact cuts an outcome), and (c) thesis exclusions. T7's rule applies: **the convergence measure is computed both ways and both are written**, with and without `proposed` derivations, so the difference is visible. The share of effects that are `documented` is reported per round, per depth and per kind.

**On v16 rounds the flag is computed and reported and never used** (A1 must hold). On rounds played under v17 it is used. Nobody can say today what R16-001's share is, and that number is the first thing v17 produces.

### 6.6 New relation types, provisional seeds

These are **my choices, set under Rob's instruction to choose rather than ask**, marked `provisional_unratified`, and any round that reads them is `learning`. Each is replaced by a measured value as resolved calls accumulate.

| Relation | Mode | From → to | Reified by | Hop discount | Transform seeds (from kind → to kind = value) |
|---|---|---|---|---|---|
| `binds` | contractual | document → party | contract, indenture, tariff | 0.8 | state→obligation 0.9; state→availability 0.6; state→cost 0.5; state→revenue 0.5 |
| `governs` | contractual (legal) | statute, regulation, licence, order → subject | itself | 0.6 | state→availability 0.8; state→obligation 0.7; state→cost 0.5; state→timing 0.5 |
| `amends`, `supersedes` | accounting/identity | document → document | itself | 0.9 | state→state 0.9 |
| `controls` | accounting | person or organisation → organisation | ownership or control filing | 0.75 | control→direction 0.6; control→obligation 0.5; state→control 0.7 |
| `holds_office_at` | contractual | person → organisation | appointment, filing | 0.6 | state→control 0.7 |
| `located_at` | physical | facility → place | registry | 0.6 | availability→availability 0.6; timing→timing 0.4 |
| `member_of` | accounting (documented) | member → composite | tariff, order, registry | 1.0 (computed) | computed by recomputation (§4.3); no table entry |
| `classified_as` | classificatory | member → composite | none | 0 | none. Proposes only |
| `references` | accounting/identity | instrument → underlying | prospectus, contract specification | 0 | none: an expression edge, not a transmitting one |
| `evidences`, `issued_by`, `reports_on` | provenance | document → claim, issuer, entity | — | 0 | none. Provenance edges do not transmit |
| `adjacent_to` | classificatory | any → any | none | 0 | none. The v16 `neighbours` lists, migrated (§7.6). Scope only, never support |

The registry is seeded with the **sixteen relations that have transform entries** (offtake, input_supply, input_cost, ownership, shared_facility, shared_infrastructure, logistics, regulatory_scope, customer, competitor, substitute, grid_neighbour, lender, insurer, regulator, counterparty) and the **seven that exist only as hop discounts** (`coverage` at 0.4, attentional; `analogy`, `index_membership`, `listing_venue`, `reporting_currency`, `sector`, `size_bucket` at 0, analogical or classificatory). All keep their v15 (ratified) and v16 builder values unchanged. **Checked against the support floor:** `binds` state→obligation is 0.9 × 0.8 = 0.72; a second hop through `ownership` obligation→obligation (0.5 × 0.85 = 0.425) gives 0.306, just above `SUPPORT_THRESHOLD` (0.3), and a third hop fails. **One rule keeps the shared table safe:** derivation and reach read only relation types whose `transmits` set is non-empty, so `references`, `adjacent_to` and the provenance edges never enter a derivation neighbourhood (`adjacent_to` is read for scope alone). An instrument therefore cannot become reachable through its own `references` row, which is what keeps `test_28` true. Chains through documents still reach about two to three steps. Anything deeper still comes only through the time walk, when an independently documented fact fires an ACK and opens a new segment.

---

## 7. Everywhere it applies: the register `[v17]`

*How to read the last column.* **Full** = the change applies as written. **Partial** = only some of the part changes. **None** = the part is deliberately untouched, and §7.9 says why.

### 7.1 Theory (Section C)

| Part | Today | v17 | Reach |
|---|---|---|---|
| **T1 Premise** | "What counts as an entity" is a list (D0) | Replaced by the §1.1 definition; the list is deleted. "Companies were the first case studied, never the scope" stays | Full |
| **T2 Three layers** | Library ∘ Positions ← Shock; positions are the fourth store | Positions are dated statements about entities. The **entity graph** (entities, relations, registries) is the store under positions: it holds the nouns, their identity, kind and edges | Full |
| **T3 Library** | Mechanisms as verbs; every rule forbids something | Rule form unchanged; rules are stated over kinds and capabilities, never proper nouns. Four candidate anchors added (§7.2) | Partial |
| **T4 ACKs** | Named source + threshold + date; derived from position conjunctions | The obligor is any entity with the capability; the governing document is a role; carriers are document series | Full |
| **T5 Anchors, not priors** | Anchors veto; base rates only for procedural actors | Permissive registration, strict valuation extends to what exists. **The veto set is unchanged**; an undocumented relation is unknown, and `edge_basis` records it (§6.5) | Full |
| **T6 Effects, positions** | "Holders", "per asset, not per owner", relation modes | Effects land on entities. The asset is an entity. Relation modes are data on relation types. A document that reifies a relation is one hop | Full |
| **T7 The basket** | Exposures nobody wrote down; cross-membership by independent derivations | Exposures are graph queries. A derived composite counts once | Partial |
| **T8 Risk** | Five-term vector; stake by holder class | Stake by the kind's scale attribute; typed gaps for new kinds | Full |
| **T9 The record** | Fifteen rounds; wall map | A per-kind wall map, reported as soon as more than one kind has been played | Partial |
| **T10 Open questions** | Ordered list | One added: does the open set reach something held (K14)? | Partial |
| **T11 Principles** | Standing list | Six added (§13) | Full |

### 7.2 Specification (Section E)

| § | Today | v17 | Reach |
|---|---|---|---|
| **1** Premise | Entity list | §1.1 definition | Full |
| **2** Architecture | Three layers; component diagram | Entity graph and entity spine added to the diagram | Full |
| **3** Library | Rules and obligation templates | Templates bind by capability. New candidate anchors: `lib.undocumented_edge_is_not_support` (forbids counting as support an effect whose relation has no documented in-force instance), `lib.document_in_force` (forbids support through a relation whose reifying document is not in force at the clock), `lib.composite_counts_once` (forbids a derived composite corroborating its members), `lib.capacity_not_biography` (forbids a person statement outside public capacity) | Partial |
| **4** ACKs | Derived from position conjunctions | Conditions may test the state of any entity, including a document (`in_force`, `terminated`) | Full |
| **5** Anchors | Structural anchors | Unchanged; `edge_basis` recorded (§6.5) | Full |
| **6** Positions, effects | Holders, node, asset_ref | §6.4 | Full |
| **7** Basket | Instruments per holder; hedge from opposite holders | Instruments reference entities; opposite holders generalise to instruments on entities on both sides of a node; composite exposure | Full |
| **8** Risk | Stake basis by holder class | §5.3 | Full |
| **9** Time | `knowable_from` stamped | Derived from evidence (§2.3); validity intervals on entities and relations | Full |
| **10** Fold mechanisms | Decision-model jobs | Candidate sets drawn from the spine; no new task | Partial |
| **11** Record and open questions | K7, K8 | Both unchanged (§9.3); one open question added (K14) | Partial |
| **12** Principles | 12 gate principles | Six added (§13) | Full |
| **13** Components | `harness`, `dataprod`, `decider` | Entity spine module in `dataprod` (G1) | Full |
| **14** Lifecycle | Lock manifest pins mutable stores | Pins `entities`, `entity_kinds`, `capabilities`, `relation_types`, `composite_rules` too; `relations` and `entity_events` are ledger | Full |
| **15** Intake | `node_type` registry; entity scope item 7 | §7.3 | Full |
| **16** Operator procedure | Enumerate effects at holders | Effects at entities; cite documents; propose kinds, relation types, composites (unreviewed by default); ratify. The operator never edits a derived composite state by hand | Full |
| **18** Data model | `holders`, `nodes`, `positions`… | §7.6. `procedural_models` (mutable) keeps its shape; its `states[]` and `transitions` seed the lifecycle of a document class where the process is a document's (§2.2), and its `docket_sources` become `document_series` entities | Full |
| **19** Scoring | Calls on effects; carrier states | Claims about the state of any entity, resolved from its series; per-kind hit and coverage reports | Full |
| **20** Risk engine | Stories, S⊥, construction, expression | Expression direct and proxied; path nodes are entities. **S⊥, ρ, junction and construction mathematics unchanged** | Partial |
| **21** Vetoes | Five | Unchanged. `edge_basis` decides what counts as support (§6.5) | Partial |
| **22** ACKs | Derivation, reach, walk, exit | Role binding by capability; windows cite governing documents; a firing appends statements about any entity | Full |
| **23–25** Decision models | `decider`, Laya pipeline | Label sets extended per kind, all in shadow until their gates. No new task | Partial |
| **26** Data-product integration | Reads filings, ownership edges, instrument map… | Reads entity, relation and document-version records; the degradation table adds `ENTITY_SPINE` | Full |
| **27** MCP tools | `holder_upsert`, `position_add`… | §7.7 | Full |
| **29** Reports | Wall map, veto rates | §7.8 | Full |
| **30–32** Build path, kill tests, build order | v16 phases P0–P4 | K14–K16; phases V0–V5 (§10), named apart from v16's | Full |
| **33** Appetite | 71 values (5 ratified, 15 carried, 51 provisional at last count) | §14 adds provisional values, all `learning` | Full |
| **34** Not decided | | Adds person ingestion and the ratification path | Full |
| **35** Glossary | | §15 | Full |

### 7.2b Other parts of the merged document

| Part | Change |
|---|---|
| **Section A** (orientation) | A2's record and decisions refreshed; the entity definition in the orientation text replaced |
| **Section B** (ideas) | About 15 plain-language uses of "holder", mostly in the effect and position passages, reworded to "entity" or "the party holding the position". No schema content |
| **Section D** (amendments) | D0 replaced by D0′; D17–D28 added (§13.1) |
| **E §35 glossary** | Effect ("a consequence at a holder"), Expression ("for a holder"), Names book ("holders and their dated pages"), Piece ("an effect at a holder"), Position ("a holder's stake in a node"): reworded to entity; new terms in §15 |
| **Section F, Section G** | §7.3 and §7.4 |

### 7.3 Intake (Section F and E §15)

| Item | Today | v17 |
|---|---|---|
| **Q1a** Window search | Directly related market-moving news in 30 days | Searched by entity (D26), so a person's, a licence's or a corridor's prior news is found, not only a node's |
| **Q1b** Recorded disruption | No recorded disruption on the node in 90 days, fewer than 3 in 12 months, from ledger and registry readers | Both thresholds kept. The unit becomes an adverse state change of the entity, read from the ledger and the entity's series (D26) |
| **Q3** World event | A thing happened; not a price move | Kept as written, with a clause added (D26): **and it is a dated state change of an entity**. The event line names the entity and the change |
| **Q4** Shared thing | Touches a facility, route, material, rule, port, standard or region with more than one holder | Kept, plus (D26): or an entity with more than one dependent through documented relations. "Rule" and "standard" are documents and now say so |
| **Q5** Size band | Trivia: no plausible holder beyond degree 0 | Trivia: no plausible holder or documented dependent beyond degree 0 (D26) |
| **Q7** Scoreable per call | The node kind has open carriers | A series `reports_on` the entity's state attribute (§2.6). v16's match is a literal string test against `node_types`, and 6 of its 10 carriers are wildcards, so the graph result is stricter and A17 lists every difference |
| **Q8, Q9, tags, cap, mix** | | **None.** Q8 never relaxes |
| **Enumeration** | Reads registered feeds | Each enumerated item is a **document entity**; the event is the state change it reports. Feed sets are recorded per document class (court dockets, regulator decisions, filings, notices) as well as per stratum |
| **Domain preference (D15)** | Prefer nodes with a firing-capable template and a priced distribution listed before the event. **D15 is not yet implemented**: the enumerator reads only the NRC power-reactor feed | (a) some template binds an obligor of any kind; (b) `expressible` or `expressible_by_proxy` at first hop. Still a tie-break, recorded per round |

### 7.4 Data product (Section G)

| Part | v16 | v17 |
|---|---|---|
| **Record kinds** | `filing_item`, `ownership_edge`, `instrument_map`, `customer_disclosure`, `regulatory_notice`, `announcement`, `price`… | Adds `entity`, `relation`, `document_version` as neutral kinds (no consumer words; `entity`, `relation`, `document` and `person` are neutral) |
| **Entity spine** | Named in G7.1 as where `entity_link` resolves | The central module: entities, dated aliases, external identifiers, lifecycle, and the append-only merge and split events (§3.4) |
| **`entity_link`** | Rule first (exact identifier, exact versioned alias), model second | Same rule order; candidate sets include persons, documents, composites. The model chooses among given candidates and never generates |
| **`extraction`** | Regex finds candidates, model picks | Adds parties, dates, amounts, term, governing law and termination or force-majeure clauses from contract and licence text. Same rule: the model only picks |
| **Conformance** | G8.2 checks | Adds `person_scope_guard` (rejects attributes outside the public-capacity list), `identity_reversible` (every merge undone by a split reproduces the earlier graph), `relation_typed` (no untyped edge in a record) |
| **`vocabulary_guard`** | Bans `holder`, `effect_dag`, `ACK`, `leg`, `basket`… | Unchanged. `holder` stays banned in `dataprod`, which is one more reason the harness's own word should retire |
| **Adapters (G11)** | EDGAR index, Exhibit 21, GLEIF, OpenFIGI, 10-K notes, exchange announcements, Federal Register, prices | **Candidates, each needing a discriminating probe and a full `SourceDeclaration` before use:** material-contract exhibits; officer, director and insider filings (person ingestion off until the §3.5 preconditions are met); control and beneficial-ownership filings; court dockets (regulatory and civil, organisations as parties; no criminal dockets); vessel and facility registries; statute and regulation version histories; index constituents. Sanctions, designation and offence lists are excluded pending the legal review of §3.5. Each adapter also needs its terms and redistribution rights checked (E §34, G12) |

### 7.5 Code, by module (81 lines mention "holder" across 11 modules)

| Module | Today | v17 |
|---|---|---|
| `positions.py` | `HOLDER_CLASSES` (4) and `ENTITY_KINDS` (10); `holder_upsert` refuses anything else | `entity_upsert`; kinds from the registry; an unseen kind registers `unreviewed`. `holder_upsert` stays as an alias for one release. `position_add` keeps v16's rule (a `stated` row needs a document; `inferred` and `implicit` are admitted without one), **derives** `knowable_from` from the links, and falls back to `recorded_at` for a row with none (§2.3) |
| `db.py` | `holders`, `nodes`, `node_types`, `carriers` (mutable); no relation table | Adds `entities`, `entity_kinds`, `capabilities`, `relation_types`, `composite_rules` (mutable); `relations`, `entity_events`, `evidence_entities`, `statement_links`, `effect_flags` (ledger side tables); `key_map`. **No existing ledger table gains a column** (§7.6). Ledger columns named `holder_id` keep their names |
| `effects.py` | `_check_common` looks up `holders`; `relation` is free text; 11 effect kinds | Entity lookup; relation validated against the registry, and composing through an unreviewed or non-supporting type refused; `state`, `control`; composite transmission by recomputation; `edge_basis` written to `effect_flags` |
| `derive.py` | Role filter by `holder_classes` and `entity_kinds`; `scope_nodes` reads `nodes.neighbours` | Capability filter; scope is the documented-relation neighbourhood bounded by `ENTITY_MATERIALISE_MAX`; `neighbours` links become `adjacent_to` rows (classificatory, scope only, never support) |
| `conditions.py` | Attribute tests on holders; `visible_positions` filters on `node` | Attribute tests on any entity, including document state; `visible_positions` includes null-node statements for the subject |
| `instruments.py` | `KINDS` closed (stock, etf, call, put, event_contract); instrument belongs to a holder; `expression_term(view, holder_id, clock)` | Instrument kind tree with a mandatory cap class; `references` rows; `expression` and `expression_proxied` |
| `vetoes.py` | Stake basis by `holder_class`; `MATERIALITY_BAND` keyed by class | Basis by the kind's scale, through a fixed basis-to-key map into the unchanged v16 `MATERIALITY_BAND` (`class_scale` renamed `derived_from_members`; one new key, `notional`); no new veto |
| `stories.py` | `path_nodes`, `shared_node`; instrument selection by `holder_id` in five places | Entity references; `references` lookup; a junction node may be a composite |
| `census.py` | The K7 census; relations already include listed parent, majority owner, sole and major customer, lender, bond issuer | No change required. A new relation joins its vocabulary only if a round needs it |
| `intake.py` | `node_type`; NRC power-reactor feed only | Entity kind and state change; enumeration by document class |
| `reach.py`, `walk.py`, `lock.py` | Reach, walk, lock manifest | Reach unchanged; the walk's firings append statements about any entity; the manifest pins the new stores |
| `calls.py`, `report.py`, `view.py` | Claims, reports | Claims about entity states; per-kind reports; as-of views over entities and relations |
| `seed.py`, `config/seed.json`, `config/appetite.json` | 37 attributes, 9 templates, 61 transforms, 10 carriers | Seeds kinds, capabilities, relation types, composite rules; transform and hop-discount seeds (§6.6); appetite (§14) |
| `tests/` | 57 of 58 pass; the one failure is a hard-coded path | Acceptance checks A1–A19 (§9.2); the path fix is independent of v17 |

### 7.6 Data model and migration

**No column is added to any ledger table.** `DB.append` hashes every column (`row_hash` covers the whole row), so a new column would change what `verify_chain` computes for every existing row and break the chain. Spec E §14 already notes that widening a v15 table needs a chain-preserving rebuild, and the v16 fresh build has none. So new ledger facts go in **new ledger tables that point at existing rows by id**. Mutable stores can take columns (`ALTER`); old rounds' snapshots are content-addressed, so they are unaffected.

| v16 | v17 | Migration |
|---|---|---|
| `holders` (mutable) | `entities` (mutable), key preserved | Renamed; `holder_class` and `entity_kind` map to a kind plus capabilities. Ledger columns still say `holder_id` and are read as an entity id |
| `nodes` (mutable) | Merged into `entities` | A `key_map` row per key; a collision policy suffixes the node's key. Where a node and a holder are one real thing (`fermi-2` and `fermi2_unit` in R16-001) the merge is a **proposed `entity_merge` event**, operator-ratified, never automatic. `neighbours` links become `adjacent_to` rows (classificatory: scope only, never support) |
| `node_types` | `entity_kinds` (tree) | Each type becomes a kind, `unreviewed` or placed in the seed tree |
| `evidence` (ledger, unchanged) | **New** `evidence_entities` (ledger): `evidence_id` → document entity | Written for every evidence row that is cited |
| `positions` (ledger, unchanged) | **New** `statement_links` (ledger): `statement_id`, `evidence_entity`, `role` (`states`/`component`), `span`; derived `knowable_from` computed beside the typed one | `holder_id`, `node`, `asset_ref` are already strings and read as entity ids; `node` may be null on new rows; `source_document` stays and is no longer written on new rows |
| `effects` (ledger, unchanged) | **New** `effect_flags` (ledger): `effect_id`, `edge_basis` | `relation` is validated against the registry on new rows |
| — | **New** `relations`, `entity_events` (ledger) | Relation rows for R16-001 are written once by a migration session (§6.1) |
| `instruments` (mutable) | Adds `references` relation rows and an `instrument_kinds` registry with cap class | Written from `holder_id` and `ack_id` |
| `carriers` (mutable) | `document_series` entities with `reports_on` relations | The table stays readable as a view for one release |
| `bounds`, `node_facts` | Cite document entities through `statement_links` | Additive |
| `ack_nodes` (mutable) | `holder_id` reads as the obligor entity | None |
| `rounds` (ledger) | `logic_version` gains the value `v17` (a value in an existing column) | v16 rounds keep `v16` |
| — | **New mutable:** `capabilities`, `relation_types`, `composite_rules`, `key_map` | Seeded from `config/seed.json` |

**Principles of the migration.** Additive. Ledger rows are never rewritten and no ledger column is added. R16-001 stays a v16 round; it is read through the compatibility map and must reproduce identically (A1), **using the appetite file pinned in its lock manifest**, not today's (its ownership hop discount was 0.9 when it was played and the file now carries v15's 0.85). A round played under v17 records `logic_version = v17`, so the two populations are never pooled without a flag.

### 7.7 MCP tool surface

**Built today in `nomad16/tools.py`:** `holder_upsert`, `node_upsert`, `position_add`, `position_attribute_add`, `bound_add`, `node_fact_add`, `effect_root`, `effect_compose`, `transform_add`, `surviving_risk`, `derive_acks`, `ack_ratify`, `ack_add`, `ack_window`, the reach and thesis tools, calls, stories and the round tools.
**In the v16 spec (E §27) but not in the fresh build:** `resolve`, `orphans`, `nomad_opposite_census`, `relation_add`, `edge_traversal`. (v15 had `relation_add` and a `relations` table.) The census and instrument tools **do exist** in the build, under short names: `census_add`, `census`, `instrument_add`.

| Tool | v17 |
|---|---|
| `holder_upsert`, `node_upsert` | Become one `entity_upsert`; the old names stay as aliases for one release. A `person` row is refused while `PERSON_INGEST` is off |
| `resolve`, `orphans`, `nomad_opposite_census` | Built for the first time, over every kind. The opposite census counts instruments on entities on both sides of a node, direct and proxied, reported separately |
| `relation_add` | Built, over the relation registry |
| **New** | `entity_kind_add`, `relation_type_add`, `entity_merge`, `entity_split`, `composite_define`, `composite_member_add`, `composite_rule_set`, `document_state_set` (appends a state statement; evidence required), `capability_grant`, `nomad_reach(entity)` (the documented neighbourhood, bounded) |

### 7.8 Reports

Per-kind wall map (stake, structural, pricedness, operator, expression, and unassessable share by kind); per-kind effect counts, hit rates and coverage; the share of effects that are `documented` by `edge_basis`, per round, depth and kind; unreviewed kinds and relation types, listed until ratified; identity events (merges, splits, unresolved); document-dating coverage (share of statements with a derived date, and the disagreements with stamped dates); composite derivations with their inputs.

### 7.9 Where it does not apply

| Untouched | Reason |
|---|---|
| The hash-chained ledger, the lock and its manifest discipline | New stores join it; nothing about how it works changes |
| The price vintage store and every rule about reading prices | Prices are observations of instrument entities, and they still enter construction and never generation |
| S⊥, ρ, story classes, junction mathematics, maximin construction, loss caps, the paper book, the four-part split | None reads an entity kind |
| The five-term vector, never multiplied; typed gaps | New kinds get gaps, not denominators |
| The time wall and the model time wall | Strengthened by derived dating, not changed |
| K1–K13 definitions, including K7 and K8 | Unchanged (§9.3) |
| The threshold discipline | Every new number is provisional and `learning` until ratified |

---

## 8. Worked examples

The first is read from the store. The other two are **illustrations, not evidence**: nothing in the 16 rounds played contained a person or a composite, so no result can be drawn from them.

### 8.1 R16-001, read as entities (from the store)

| v16 record | v17 entity | What changes |
|---|---|---|
| Node `fermi-2` (`power_reactor`) and holder `fermi2_unit` (`unlisted_operating_asset`, `company_asset`) | One `reactor_unit` entity, a proposed operator-ratified merge | Two rows for one thing become one. The unit's statements (status, capacity, market region) and its role as the round's node are the same entity |
| `dte_electric` (unlisted, `company`, `parent_id` `dte_energy`) | `organisation`, with `controls` from its parent | The single-parent column becomes a relation row with a share |
| `dte_energy` (`listed_instrument`, ticker `DTE`) and `cms_energy` (`CMS`) | Listed organisations, `expressible` because a share `references` each | The 0.01/0.05/0.4% estimates gain a documented chain to be checked against: the ownership edge and the cost-recovery clause that passes cost to customers |
| `dte_retail_customers` (`aggregate`) | `composite` of the payers under one cost-recovery clause | Membership is documented by the clause. The clause is a document entity that `binds` DTE Electric and the composite |
| `nrc` (`authority`, `agency`) | `agency` organisation | Its licence and event-notification documents are entities; the licence `governs` the unit. This is the structure behind the `licensed_facility` position |
| `miso_lrz7_energy` (`aggregate`, `commodity`; no position or effect in the round refers to it) and node `miso-lrz7` (`power_market_zone`) | A `composite` market with an observed price, and a `place` for its footprint | Two rows and a class collapse into a market and its footprint |
| 131 `evidence` rows: 94 EDGAR filing-list fetches, 17 NRC status reports, 16 EDGAR documents, 3 NRC event notifications, 1 GDELT export | Four `document_series` (EDGAR, NRC status, NRC event notifications, GDELT). A document entity for each document actually read or cited (the 94 list fetches are reads of the EDGAR series, not 94 documents) | The carrier registry entries become the series; `reports_on` replaces `node_types` |
| Two carriers the operator recorded as not covered: the NRC licensee event reports in ADAMS, and the state commission's cost-recovery docket | Two `document_series` with no working fetch path | The gap becomes a typed, countable `not_covered` per entity and attribute. It is exactly why the derived `obl.written_event_report` ACK was dropped |
| 25 positions; 22 cite evidence; 3 do not | 22 with derived dating; the event-line row cites the admission record; 2 `inferred` rows stay undocumented | 20 stamps equal the earliest cited document; 2 differ (§2.3) |

**What the round would have shown differently.** Nothing about its numbers: the replay identity check (A1) requires the 9 effects, the band near 8%, the unbuildable baskets and the 6 of 6 resolved calls to reproduce. What becomes visible is which of the 7 effects that carry a relation label (ownership 5, counterparty 1, regulator 1) have a documented relation row behind them. That is the `edge_basis` reading (§6.5), and nobody can say today what it will find.

**What the record cannot say.** It has no person, no contract as such, and no composite other than the two aggregates. Of its 4 derived ACKs, 3 were ratified (one a switch) and 2 of those fired, one delivered and one not; the fourth was dropped because its carrier is not covered. It cannot tell us whether v17 helps. That is K14's job, on more documents than one round holds.

### 8.2 An officer change (illustration)

A listed issuer discloses in a current report that its chief financial officer is resigning.

- **Entities:** the person (`holds_office_at` the issuer, evidenced by an appointment filing); the issuer (`expressible`: a share references it); the current report (a document that `states` the vacancy); the officer's service agreement (a document that reifies the office).
- **Effects:** `state` (office vacated) lands on the person; it composes to a `control` effect at the issuer through `holds_office_at` at 0.7 × 0.6 = 0.42, above the 0.3 floor. The issuer's share is `expressible` at the first hop. In v16 none of this is representable: there is no kind for the person, the office, the report as a thing whose publication is the event, or the agreement.
- **Obligation:** a governing regulation may require a further filing inside a window. It is a template with the issuer or the person as obligor and the regulation as governing document. Its window is a dated `bound`, not a remembered number.
- **What K14 asks:** how often a chain like this exists in the record, and whether it lands on something holdable when it does.

### 8.3 A supply chain (illustration)

Three concentrate mines sell under offtake contracts to one smelter; the smelter sells to two refiners; every shipment passes one port.

- **Composite:** `supply_chain`, members documented by the offtake contracts and a port-services agreement. Rule for throughput: `bottleneck` over the documented critical path.
- **An outage at the smelter:** the effect lands on the smelter (`availability`). The smelter is the **binding minimum** on the critical path (its documented capacity is the lowest), so recomputation (§4.3) gives member → composite transmission of **1.0**: the composite's throughput falls by the smelter's own relative loss, capped at 1. Had a mine been the binding member instead, the smelter's outage would have transmitted only the part below that minimum. Inputs are recorded. The composite's throughput effect reaches the refiners through `input_supply` (availability → volume 0.6 × hop discount 0.7 = 0.42), once. Support at the refiners is parent transmission 1.0 × composite transmission 1.0 × 0.42 = 0.42, above the 0.3 floor.
- **The mines** are affected through their own documented `offtake` relations (availability → volume 0.5 × 0.7 = 0.35, just above the 0.3 floor), **not** through composite membership. A strike at one mine would not move the other two: no sibling spread.
- **If a member's capacity were undocumented,** the composite's throughput is unknown, the response band widens, and no branch is cut.
- **The composite counts once.** The chain's derived throughput is not a second source of evidence for the smelter's status.

---

## 9. Tests and acceptance

### 9.1 Kill tests, pre-registered `[v17]`

**Numbers here are provisional and set by me under Rob's instruction to choose rather than ask.** They are fixed before anything is read and never moved because they were not met. Each round that reads them is `learning`.

| # | Falsifiable sentence | Dies if | If it dies |
|---|---|---|---|
| **K14** | On the documents each qualifying round had at its lock, an open-entity reading finds, in at least **X₁₄ = 25% of the readable qualifying rounds** (rounded up; 3 of 11 if all are readable), an entity of a kind v16 could not hold that (i) is **within reach** of the round's node, and (ii) either fills a role in a `forced` or `switch` derivation, or is `expressible`, or is one documented relation from an entity that is | Fewer rounds than that show one | **Keep the schema open (it costs nothing), and stop V3–V5.** The v16 wall is not a vocabulary problem. Persons, composites and the spine adapters are not built for the equity thesis; they stay candidates for shape C |
| **K15** | Merge precision is at least **X₁₅ = 0.98** on a hand-labelled sample of 200 candidate pairs drawn across kinds, and every wrong merge is undone by an appended split that reproduces the earlier as-of graph | Precision below 0.98, or a split that does not restore the graph | Alias merging is switched off for the failing kind; exact identifiers only; unresolved stays unresolved |
| **K16** | For composites with a `bottleneck` or `sum` rule, composite-level effects predicted from documented member states are right at least as often as the same effects predicted from the members' separate chained paths, over at least **N₁₆ = 20** resolved calls | Composite-level is worse | Composites stay as reporting entities; their computed transmission is not used for support. **Unreadable until 20 resolved calls involve a composite, likely months away** |

**How K14's terms are fixed.**
- **Qualifying rounds** are those whose event falls after the operator's declared cutoff (2026-06-30), so a cold reader has not seen them: rounds 5–15 except the one re-run dated 2025-07-31, plus R16-001. **11 at last count.** Rounds 1–4 and that re-run pre-date the cutoff.
- **Within reach:** connected to the round's node by documented, reviewed, transmitting relations whose support stays at or above `SUPPORT_THRESHOLD`, using the seeds of §6.6.
- **Fills a role:** in a derivation result under capability-based role filtering.
- **One documented relation from an entity that is `expressible`:** this is what lets a person or a document count, since neither is itself referenced by an instrument.
- **What the closed run is for.** By construction the closed run finds **zero** entities of a kind v16 cannot hold, so it is not a baseline for the count and the count is the open run's. Its job is to control for **reader effort**: each round is read twice on the same documents in one session, and the closed run's finds of kinds v16 *could* hold are reported beside the open run's. If a second look alone finds as much as the open look, effort and not vocabulary is the variable, and the result is read that way. The order alternates by round, so the second reading does not always benefit from the first. K10's 0 of 6 is context only.
- **Freeze.** Kinds, capabilities, relation seeds and templates are fixed before the reading. Templates are authored from **rounds 1–4 only for rounds 5–7, and from rounds 1–7 for the rest** (E §31, the same guard as the K9 rebuild).
- **Persons** are counted as roles from documents (an officer of the issuer); no person record is stored (§3.5).
- **Readable only if** at least 6 of the 11 qualifying rounds have retrievable lock-time documents. The reader is a cold session on a model whose `trained_through` is before the event, and it runs before the K14 result is seen.

**Other guards.** K14 is a reading, not a round: no theses, baskets or prices, so it costs less than a K9 rebuild round (R16-001 took about $13; K14's cost is not measured). K15 needs a hand-labelled sample, a day of labelling and no build. A look-back that uses anything chosen after seeing the outcome is void (E §31).

**What was dropped.** An earlier draft had a fourth test, "documents date the old record". It is not needed: the blind back-fill already asked it (14 of 141 dated; the remaining 127 rows are operator priors, not documents). The forward dating rule is checked mechanically (A3).

### 9.2 Acceptance checks (mechanical)

| # | Phase | Check |
|---|---|---|
| **A1** | V0 | **Replay identity.** v17 code on the R16-001 store, using the appetite file pinned in its lock manifest, reproduces the same `surviving_risk` statuses, `constructed_baskets` rows and report figures as v16. G9.10 puts the same rule as "The isolation must not change a single number" |
| **A2** | V0 | **No closed lists.** `entity_upsert` accepts any registered kind; an unseen kind registers `unreviewed`; an unreviewed kind or relation type can propose and never support |
| **A3** | V1 | **Derived dating.** A statement's `knowable_from` is the earliest `states` link, else the latest `component` link; a `states` link without a span that occurs in the document text is stored as `component`; a typed `knowable_from` is refused on new rows; an `embargo_until` later than the derived date is accepted with a reason and an earlier one is refused; the admission record is a document, so a round's first `stated` position has one |
| **A4** | V2 | **No untyped relation.** `related_to` and synonyms are refused; a new type registers `unreviewed`, classificatory, and cannot be composed through |
| **A5** | V3 | **Composite structure.** A cycle is refused; nesting beyond `COMPOSITE_DEPTH_MAX` is refused |
| **A6** | V3 | **Counts once.** A derived composite state and its members count as one derivation in the convergence measure |
| **A7** | V3 | **No sibling spread.** An effect on one member reaches another only through a documented relation between them |
| **A8** | V0 | **Identity events.** Merge and split are appended; a read whose clock or `ledger_cutoff` precedes a merge sees two entities; a split restores the earlier graph |
| **A9** | V0, V4 | **Persons.** With `PERSON_INGEST` off, `entity_upsert` refuses a `person` row (V0). With it on, a statement with an attribute not registered for `person` is refused (V4) |
| **A10** | V2 | **Capability roles.** The nine seed templates bind on the R16-001 store to the same bindings as under the closed lists, and the import-linter test (`test_28`) still passes: derivation, reach and conditions import nothing that reads instruments |
| **A11** | V2 | **Reified hop.** Traversal through a contract between two parties pays the hop discount once |
| **A12** | V0, V2 | **As-of validity.** Entities honour `exists_from` and `knowable_from` (V0). Relations and documents also honour `valid_from` ≤ clock < `valid_to`, and a document not in force supplies no relation (V2) |
| **A13** | V4 | **Stake basis.** The basis comes from the kind's registered scale and is read through a fixed basis-to-key map into the unchanged `MATERIALITY_BAND` (so the v16 appetite file still loads); a kind without a scale yields a typed gap; a basis without a band entry yields `not_representable`; R16-001's stakes (20.0 and 1.838) reproduce |
| **A14** | V2 | **Materialisation budget.** Exceeding `ENTITY_MATERIALISE_MAX` or `DOCUMENT_MATERIALISE_MAX` yields a typed `materialise_exceeded` report, never silent truncation |
| **A15** | V5 | **Data product.** `person_scope_guard`, `identity_reversible` and `relation_typed` pass; `vocabulary_guard` still passes |
| **A16** | V2 | **`edge_basis` is recorded** on every effect. On the R16-001 replay it is computed and reported and changes no status |
| **A17** | V2 | **Carriers as series.** Q7 computed from the graph is compared with v16's match on every recorded round, and every difference is listed with its cause (v16's wildcard carriers cover every node type) |
| **A18** | V0 | **Ledger integrity.** No column is added to any ledger table, and `verify_chain` passes on the migrated store |
| **A19** | V4 | **Instrument kinds.** An instrument kind without a registered cap class is refused; an uncapped form is never built |

### 9.3 K7 and K8

- **K8** (opposite holders) keeps its pre-registration, and v17 does not amend it. More entities can raise its numerator, but they can raise its denominator too, so a widened reading is reported as a **separate figure on the same 11 nodes**, never a replacement. Running K8 now on the existing overlay, as the checkpoint says, wastes nothing. The back-fill's own reading is that it will mostly stay unreadable.
- **K7** (the census) is unchanged. The drafted census already records listed parent, majority owner, sole and major customer, lender and bond issuer, and none of the 15 rounds' holders needs a new relation. Its pre-registration is still an unlocked draft (`K7_SHARE` unset).

---

## 10. Phasing and migration

Named **V0–V5** so they cannot be confused with v16's phases P0–P4 (E §32). Each phase can be stopped without loss. Spend follows a measured block (E §12), so the phases after the gate wait for K14.

| Phase | Content | Exit | Risk |
|---|---|---|---|
| **V0 Schema and compatibility** | Side tables and registries, `key_map`, the `holders` alias, identity events, the person switch, `logic_version = v17` | A1, A2, A8, A9 (switch), A12 (entities), A18 | Low. Any replay difference stops it |
| **V1 Documents as evidence** | Document entities for cited evidence; the admission record; `statement_links` with spans; derived dating beside typed dating | A3 | Low |
| **V2 Relations as rows, capabilities** | `relations`, the type registry and seeds (§6.6), capability roles, carriers as series, `edge_basis`, budgets | A4, A10, A11, A12 (relations), A14, A16, A17 | Medium: changes how templates bind on new rounds |
| **Gate** | K14 read (it can run once V0 and V1 make kinds and documents addressable; it does not need V2) | K14 does not die | |
| **V3 Composites** | Membership, aggregation rules, derived and observed state | A5, A6, A7; K16 accrues | Medium |
| **V4 Persons (schema and templates), instruments as entities, expression by graph, stake bases** | `references`; direct and proxied expression; instrument kind tree | A9 (scope), A13, A19 | Medium. No person is stored |
| **V5 Data-product spine, adapters, intake by document class** | Spine module, record kinds, adapters, enumeration by document class | A15; K15 | Highest: external data, terms and the legal review |

**Order of the first steps** (each small): (1) K8 on the existing overlay, as pre-registered; (2) ratify D17–D20, D24 and D25 (§13.3) and ask the builder for V0 and V1; (3) K14 once V1 has made documents addressable; (4) V2 in parallel.

---

## 11. What v17 does not do

**Not in v17, deliberately.** v17 is one change.
- **Merging or stacking theses, parallel theses and convergence nodes.** Composites are the entity-level ground such an idea would stand on; the idea itself is separate and still parked.
- **The decay curve by graph distance** (measuring hop discounts instead of carrying them). Composites and reified documents change what a hop is, so that measurement is better taken after v17 than before.
- **The pooled-basket look-back pre-registration**, **the K9 rebuild** and **threshold ratification** (they stay `learning`; I write the rationales before the first counting round).
- **New decision-model tasks.**

**What it does not fix.**
- **The old record.** The v15 positions were mostly priors, not documented facts, and every K10 template tests attributes no v15 row held. v17 cannot change that; the forward record is where it matters.
- **Expression is still the wall.** Opening the entity set adds entities without instruments as well as with them. K14 measures which dominate.
- **Most v15 events did not move a listed instrument beyond its noise** (8 of 87 units, about 9%, left a 90% band: K11). A wider entity set changes what can be known, not how often prices move.
- **Round cost and the model time wall** are unchanged.

---

## 12. Risks

| Risk | How it shows | Guard |
|---|---|---|
| **The graph becomes a machine for connecting anything** | Every story has a path | Only documented, in-force, reviewed physical, contractual or accounting relations count as support. Classificatory and unreviewed proposals never do, and an unreviewed type cannot be composed through (§1.6, §6.2, §6.5) |
| **A wrong merge poisons the graph** | Two people or two contracts become one | Exact identifiers first; merges and splits are events; K15 |
| **Ontology drift** | Hundreds of kinds and relation types | `unreviewed` status; a report of unreviewed kinds and types; the materialisation budgets |
| **A composite counts a fact twice** | Convergence rises with no new evidence | Derived composites are descendants (A6) |
| **A mis-tagged early `states` link leaks the future into the past** | A fact is dated before it was public | `component` is the default; `states` needs a checkable span (A3); tags are part of the statement and reviewed at ratification |
| **More entities, still nothing to hold** | K14 dies | The design already stops at V2 (§10) |
| **Person data** | Legal exposure; erasure impossible in an append-only ledger | Off by default and enforced by the tool; public capacity only; no offence data; a legal review and an erasable `person_vault` before any person is stored (§3.5) |
| **Spec and code diverge** | The spec says open, the code says closed | A2 is the check; gaps live in `STATE.md`, and the spec is never rewritten to match the code |
| **`edge_basis` changes support counts on v17 rounds** | Convergence rankings move | Both rankings are written (T7's rule); on v16 rounds the flag is never used (A16) |
| **A ledger column breaks the hash chain** | `verify_chain` fails at row 1 | No column is added to any ledger table; side tables only (A18) |
| **Row growth** | 131 evidence rows for one round | Content-hash de-duplication; documents are materialised only when cited or reifying; budgets |
| **The existing test suite** | 57 of 58 pass today | The migration is additive, and A1 is a replay identity check |

---

## 13. Amendments, principles and the decisions for Rob

### 13.1 Amendments

| ID | What v16 says today | Change | Specified in | What measures it |
|---|---|---|---|---|
| **D0′** *(applied, 2026-09-29, on Rob's instruction)* | D0: entity scope written as a list of kinds | The open definition (§1.1); the list is deleted | §1 | A2, K14 |
| **D17** | Two tables, `holders` (four classes, ten kinds) and `nodes`; effects land on holders only | One `entities` table; kinds as a tree and a registry; capabilities; roles are relational | §1.3–§1.5 | A1, A2, A10 |
| **D18** | `relation` is a free label checked only against the transform table | Relation rows and a type registry with mode as data; no untyped relation; an unreviewed type cannot be composed through; `edge_basis` decides what counts as support (no new veto) | §6.1–§6.2, §6.5 | A4, A16 |
| **D19** | `position_add` takes an operator-typed `knowable_from` (the date the source became public); evidence is provenance | Evidence is document entities; `knowable_from` derived from `states`/`component` links with a checkable span; a typed date refused on new rows; the admission record is a document | §2.3 | A3 |
| **D20** | A document can only be evidence; the `contract` kind labels a holder and has no parties, version or lifecycle | Documents are entities with a lifecycle; a reifying document is one hop; validity intervals; carriers are series | §2.2, §2.4–§2.6 | A11, A12, A17 |
| **D21** | No persons | Persons in public capacity; identity events; ingestion off by default with two preconditions | §3 | A8, A9, K15 |
| **D22** | `aggregate` class; no composites | Composites: two membership grades, aggregation rules, transmission by recomputation, derived versus observed state, compress not exempt | §4 | A5–A7, K16 |
| **D23** | Instruments hang off holders; stake basis by holder class; `instruments.KINDS` closed | Instruments are entities; direct and proxied expression; stake basis and `MATERIALITY_BAND` by kind scale; instrument kinds open with a mandatory cap class | §5 | A13, A19, K14 |
| **D24** | Template roles filter by `holder_classes` and `entity_kinds` | Roles require capabilities; the governing document is a role filler; bounds cite documents | §1.4, §2.5 | A10 |
| **D25** | 11 effect kinds, 16 relation types with transform entries | Adds `state` and `control`, the relation seeds of §6.6 and `edge_basis`. **No new veto** | §6.3–§6.6 | A16 |
| **D26** | Intake by `node_type`; an event is at a node | An event is a dated state change of an entity; enumeration by document class; Q1a, Q1b, Q3, Q4, Q5 and Q7 restated with their v3 thresholds kept | §7.3 | K14 |
| **D27** | Neutral record kinds | Entity spine, relation records, person guard | §7.4 | A15, K15 |
| **D28** | Wall map by stake class | Per-kind wall map. K7 and K8 unchanged | §7.8, §9.3 | K14 |

Ratification follows the existing rule: Rob marks each *ratified*, *rejected* or *amended* with a date; a row with a kill test can stay proposed until the test has run.

### 13.2 Principles added

1. **An entity is anything with a state that can change, be observed and be related.**
2. **Open in what exists; closed in what supports.**
3. **A document is an entity before it is evidence.**
4. **A composite compresses documented structure; it never exempts it, and it never corroborates its own members.**
5. **Persons only in public capacity, from public documents, and none stored until erasure is possible.**
6. **Identity is a claim with evidence, and every merge can be undone.**

### 13.3 The decisions that are Rob's

Only two. Everything else I have chosen, marked provisional, and can be overruled.

1. **Persons.** Are they in the schema and the templates now, with **ingestion off** (enforced by the tool) until a legal review and an erasable person store exist? I recommend yes. It costs nothing and keeps the option.
2. **Ratification path.** D0′ is applied on Rob's instruction. I recommend ratifying **D17, D18, D19, D20, D21, D24 and D25** now, which is what V0–V2 need (D21 because V0 exits on A8, identity events, and A9, the person refusal), and leaving D22, D23 and D26–D28 proposed until K14 has been read.

---

## 14. Appetite additions

All are `provisional_unratified`, every round that reads them is `learning`, and the loader refuses to run if one is missing (the v16 rule: no number that governs a verdict gets a default). **One v16 fallback exists and is named here:** `DEFAULT_HOP_DISCOUNT` (0.5, provisional) applies to a relation with no registered discount. v17's `relation_type_add` requires a discount, so a new type never reaches it.

| Name | Value | Rationale |
|---|---|---|
| `ENTITY_MATERIALISE_MAX` | 400 | Non-document entities expanded per round. The effect frontier is 120, and an effect touches a subject and usually a relation counterparty |
| `DOCUMENT_MATERIALISE_MAX` | 2,000 | Documents are leaves. R16-001 alone holds 131 evidence rows |
| `COMPOSITE_DEPTH_MAX` | 2 | A chain inside a market is two levels. A third is a classification |
| Hop discounts and transform seeds, new relations | As §6.6 | Carried from the nearest existing relation (`binds` near `ownership`; `governs` equals `regulatory_scope`); high where the document makes the consequence mechanical. Replaced by measurement |
| `MATERIALITY_BAND`, one new key | `notional` 0.05 | Carried from the nearest existing basis (`aggregate` is 0.05). `derived_from_members` is `aggregate` renamed and needs no new value |
| `X₁₄`, `X₁₅`, `N₁₆` | 25% of readable rounds (3 of 11), 0.98, 20 | About one round in four is the lowest rate that shows within the first tens of rounds. A wrong merge is worse than a missed one, so precision is set high. 20 calls is the least that separates two hit rates |
| `RELATION_UNREVIEWED_MODE` | classificatory | A fixed rule, not a threshold |
| `PERSON_INGEST` | off | A switch, not a number |

---

## 15. Glossary changes

| Term | v16 | v17 |
|---|---|---|
| **Entity** | Anything from a fixed list | Anything with a state that can change, be observed and be related |
| **Holder** | A row in `holders`, from four classes | A **role**: the subject of a position. Any entity can hold |
| **Node** | A row in `nodes`; event or attribute | A role: the object of a position, or a round's locus. Any entity can be one |
| **Asset** | `asset_ref` text on a position | An entity of a facility kind |
| **Document** | Evidence | An entity with a state; evidence, or a reified relation, or both |
| **Carrier** | A registry row with a fetch path | A `document_series` entity that `reports_on` entities |
| **Composite** | — (`aggregate`, a holder class) | An entity whose identity is a membership plus an aggregation rule |
| **Relation** | A label on an effect | A typed, dated, sourced row with a mode |
| **Capability** | — | What a kind can do; roles require capabilities |
| **Unreviewed** | — | A kind or relation type registered on first use; can propose, cannot support, and cannot be composed through |
| **Edge basis** | — | Per effect: `root`, `documented` or `proposed`. Only `documented` effects count as support; no effect is vetoed for being `proposed` |
