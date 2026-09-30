# The whole system as entities and kinds (amendment A2, proposed)

*Status: **proposed**; nothing migrated and no ledger column changed. Written 2026-09-30 on Rob's instruction: the atom is an entity and its base type is a kind; a quarterly fundamental, a filing, a decision, a company and a thesis are all entities of some kind, which is why the model is broad. "Model the entire system under this view." Machine-readable form: `config/system_model.json`; the test `nomad16/tests/test_system_model.py` checks that every table below is covered and the constraints are consistent.*

## 1. The view

There are **four primitives**: an **entity** (a key, a kind, a lifecycle, an existence interval), a **relation** (one fact with unordered participants that fill roles), a **statement** (a dated claim about an entity with evidence links) and an **event** (a dated change, appended to the ledger). Everything the system has ever called a table, a store, an object or a procedure is one of these, of some kind. Kinds live in one registry, a tree with review states and capabilities. That is what makes the model broad and domain-free: nothing in it names an oil company, a reactor or a decision date.

The twelve rules that follow from the view (also in the JSON):

- **R1 ** he atom is an entity; its base type is a kind. Kinds live in one registry (a tree, with review state and capabilities). There are four primitives and no others: entity, relation, statement, event.
- **R2 **  relation is one fact with unordered participants that fill roles. The type says what may fill each role. Direction is a perspective, chosen by a traversal. A relation with an open slot is valid and the slot is a typed gap.
- **R3 **  statement is a dated claim about an entity with evidence links. Its knowable_from is derived from the evidence, never typed. Evidence is an entity of kind document or dataset, and a structured quarterly figure is one.
- **R4 ** nknown never eliminates and never supports. A missing exposure is a typed gap; an inferred one is implicit and makes any result a switch to check.
- **R5 **  kind, relation type or capability that is unreviewed proposes and never supports.
- **R6 ** rice is a dataset of kind price_series with the capability attentional: it may confirm and may never propose. It is not evidence for an exposure, an outcome or an effect. It enters only at expression (construction sizing, paper marks, costs).
- **R7 ** he ledger is append-only. Every change is an event. A correction supersedes and never overwrites. Mutable stores are current-state views, pinned by a snapshot at each lock.
- **R8 ** rocedures are parameterised by kinds and capabilities, never by an event class or a domain. Domains enter through adapters that supply source entities.
- **R9 **  hedge is constructed thesis-first: a primary thesis, its failure set (computed from pays_under, never authored), a hedge thesis that covers it, then a basket constructed for that thesis. The hedge relation is one-way, acyclic and single-sink; hedge baskets are long-only; a shadow basket is never traded.
- **R10** Objectives and the number of baskets are declared at lock. Each basket is scored on its own objective and the set is scored separately.
- **R11** A parameter is an entity with a status and provenance; a ratification is a decision entity by a person with a date.
- **R12** A test is an entity: its pre-registration entity carries a knowable_from that precedes every result entity it produces.

## 2. Kinds the system adds (over the entity kinds of `seed_v17.json`)

| Kind | Parent | Capabilities | What it is |
|---|---|---|---|
| `session` |  | authors | a cold operator, reader or judge: model, trained_through, cold, hook_verified |
| `run` | event |  | an enumeration or fetch run |
| `event` |  |  | a dated state change of an entity (spec v17 D26) |
| `decision` | event |  | an agency or a person deciding: a Fed statement, a ratification |
| `firing` | event |  | an ACK delivering an outcome |
| `snapshot` | dataset |  | content-addressed copy of a mutable store |
| `price_series` | dataset | attentional | prices: may confirm, never propose; expression layer only |
| `fundamental` | dataset |  | a quarterly figure from a filing, structured or stated |
| `outcome_vocab` |  |  | a typed set of outcomes for a notice kind |
| `outcome` |  |  | one member of a vocabulary; other is outside the closed world |
| `piano` | outcome |  | an outcome outside the closed world, booked when it happens |
| `obligation_template` |  | requires_capability_roles | library object: roles by capability, conditions, forces, window rule |
| `obligation` |  |  | a template instantiated on entities |
| `ack` |  |  | a named source, threshold and date: forced, switch or calendar |
| `thesis` |  |  | a claim over an outcome space: thesis set, anchored exclusions; role primary or hedge |
| `effect` |  |  | a documented consequence of an outcome on an entity, by channel, with degree and transmission |
| `call` |  |  | a falsifiable prediction about a carrier, with a due date |
| `resolution` |  |  | what the carrier said, scored against a call |
| `basket` |  | expressible | a composite of instruments constructed for a thesis |
| `paper_position` |  |  | a booked position of a basket's leg |
| `story` |  |  | a factor the market tells; a proxy series names it (attentional) |
| `junction` |  |  | two stories that move together, flagged for treatment |
| `segment` |  |  | a period of a round between clocks |
| `round` |  |  | a play of the procedure on one event, with lifecycle states |
| `manifest` |  |  | the frozen list of what a lock read |
| `lock` |  |  | the act of freezing a segment: hash of its objects |
| `tide` |  |  | the market factor a round declares |
| `cost_model` |  |  | spread, slippage and fee rules for an instrument kind |
| `library_rule` |  |  | a mechanism stated as a verb that forbids something |
| `procedural_model` |  |  | a chain of procedural actors and their windows |
| `attribute` |  |  | a registered position attribute: type, unit, allowed values |
| `transform` |  |  | a relation type by effect pair by value |
| `partition` |  |  | a versioned post-hoc grouping of relation instances (buckets) |
| `bucket` |  |  | one group in a partition, with a fitted dilution exponent or a gap |
| `parameter` |  |  | an appetite value: ratified, carried, provisional or unset, with provenance |
| `note` |  |  | operator commentary on any entity |
| `test` |  |  | a pre-registered look-back or kill test: its prereg entity precedes its result |

The v17 kinds (organisation, company, facility, person, instrument, document, filing, composite, and so on) are unchanged. A fundamental is a `dataset`; a Fed statement is a `notice` (a `document`); a price series is a `dataset` with the capability `attentional`.

## 3. Relation types (roles, not directions)

| Type | Roles (what may fill them) | Mode | Constraints and notes |
|---|---|---|---|
| `states` | source: document|dataset; claim: statement | provenance | excludes_source_kinds=['price_series']. span verified; a numeric claim's span carries the value |
| `component` | source: document|dataset; claim: statement | provenance | excludes_source_kinds=['price_series']. the default link; the later of the components dates the claim |
| `exposed_to` | holder: organisation|facility|composite; channel: story|commodity_grade|index|currency|market|factor | documented | excludes_source_kinds=['price_series']. attributes: sensitivity, unit, metric, basis; an undisclosed channel is a gap, an inferred one is implicit |
| `lands_on` | effect: effect; subject: * | structural |  |
| `under` | effect: effect; outcome: outcome | structural |  |
| `derived_from` | child: effect|ack|thesis|obligation; parent: effect|ack|obligation_template|statement | structural | acyclic. carries transmission; support is the product along the chain |
| `outcome_of` | outcome: outcome; vocabulary: outcome_vocab|ack | structural |  |
| `covers` | thesis: thesis; outcome: outcome | structural |  |
| `hedges` | hedge: thesis; primary: thesis | structural | acyclic, single_sink, no_cross_thesis, long_only. one-way: a thesis is hedged by others and does not hedge them back; the DAG's sink is the primary thesis |
| `constructed_for` | basket: basket; thesis: thesis | structural |  |
| `member_of` | member: *; whole: composite|basket | accounting | attributes: weight, side; a derived composite counts once |
| `references` | instrument: instrument; underlying: * | expression | an expression edge, not a transmitting one |
| `pays_under` | subject: basket|instrument; outcome: outcome | estimate | attribute payoff with basis documented, estimated or gap; the payoff matrix |
| `fails_under` | subject: basket|thesis; outcome: outcome | computed | computed from pays_under against FAILURE_LOSS_PCT; never authored |
| `shadows` | shadow: basket; shadowed: basket | structural | never_traded. a blind statistical comparator paper-filled beside a constructed basket |
| `fires` | firing: firing; ack: ack | structural |  |
| `delivers` | firing: firing; outcome: outcome | structural |  |
| `forces` | template: obligation_template; ack: ack | structural |  |
| `reports_on` | carrier: document_series; subject: * | provenance |  |
| `carried_by` | claim: call|ack; carrier: document_series | structural |  |
| `resolves` | resolution: resolution; call: call | structural |  |
| `observed_in` | resolution|observation: resolution|fundamental; source: document|dataset | provenance | excludes_source_kinds=['price_series'].  |
| `authored_by` | work: *; author: session|person | provenance |  |
| `supersedes` | new: *; old: * | identity |  |
| `pins` | manifest: manifest; snapshot: snapshot | structural |  |
| `part_of` | part: segment|paper_position|firing; whole: round|basket | structural |  |
| `loads_on` | subject: instrument|basket; story: story | estimate | attribute loading; attentional: proposes and never supports |
| `joins` | junction: junction; story: story | structural |  |
| `assigned_to` | instance: *; bucket: bucket | estimate | post hoc; a partition version records who assigned and on what text |

The v17 §6.6 types (`binds`, `governs`, `controls`, `holds_office_at`, `located_at`, `amends`, `supersedes`) and the sixteen v16 relations carry over with roles as A1 §3 describes.

## 4. Every table, read in the model

The tables stay as projections during migration (views first; a ledger table never gains a column, A18).

| Table | Read in the model as |
|---|---|
| `rounds` | entity kind round; its fields are statements |
| `round_meta` | statements on the round (supersedes chain) |
| `round_tags` | statements on the round |
| `round_state` | lifecycle events of the round (entity_events) |
| `operator_manifests` | entity kind manifest, authored_by a session; cold and hook_verified are statements |
| `notes` | entity kind note about any entity |
| `enumeration_runs` | entity kind run |
| `intake_candidates` | entities kind event (candidates) with decision statements |
| `evidence` | source entities of kind document or dataset (projection of evidence_entities) |
| `pit_fetches` | events on source entities (a fetch), with status statements |
| `positions` | statements on entities, evidence-linked (V1) |
| `node_facts` | statements with evidence links |
| `effects` | entities kind effect; relations lands_on, under, derived_from |
| `surviving_risk` | statements on effect (terms, vetoes, typed gaps) |
| `ack_status` | lifecycle events of the ack |
| `ack_derivations` | relations derived_from (ack from template and positions) with the trace as statements |
| `ack_outcomes` | entities kind outcome; relation outcome_of |
| `thesis_sets` | entity kind thesis; relations covers; anchored exclusions as statements |
| `ack_firings` | entity kind firing; relations fires and delivers |
| `segments` | entity kind segment; part_of round; clock as statement |
| `predictions` | entity kind call; carried_by a carrier |
| `resolutions` | entity kind resolution; resolves a call; observed_in a source |
| `story_classes` | statements on story per segment |
| `story_loadings` | relation loads_on with a loading attribute |
| `junctions` | entity kind junction; relation joins |
| `s_perp` | statements on thesis and story (rho, s_perp_norm) |
| `price_vintages` | entity kind price_series (a vintage) |
| `store_snapshots` | entity kind snapshot |
| `lock_manifests` | entity kind manifest; relation pins to snapshots |
| `locks` | entity kind lock; hash as statement |
| `constructed_baskets` | entity kind basket; relation constructed_for a thesis |
| `basket_weights` | relation member_of with weight and side |
| `scenarios` | relation pays_under (the payoff matrix) |
| `basket_status` | lifecycle events of the basket (built, unbuildable, why) |
| `paper_positions` | entity kind paper_position; part_of a basket |
| `paper_fills` | events on paper_position |
| `paper_marks` | statements on paper_position, from price_series (expression layer) |
| `paper_exits` | events on paper_position |
| `pianos` | entity kind piano (an outcome outside the closed world) |
| `census_rows` | statements and relations on company entities (owns, references, concentration) |
| `entity_events` | the event log itself: every change to an entity, relation or statement |
| `evidence_entities` | the link from an evidence row to its document entity (merged into entities) |
| `statement_links` | relations states and component |
| `bucket_versions` | entity kind partition, authored_by a session |
| `bucket_assignments` | relation assigned_to |
| `bucket_fits` | statements on bucket (alpha, se, n_obs, gap) |
| `library_history` | statements on library_rule (weight history) |
| `store_changes` | events (audit of changes to mutable stores) |
| `holders` | entities (kinds company, agency, and so on): legacy view |
| `nodes` | entities (facility, place, and so on): legacy view |
| `node_types` | registry kinds |
| `position_attributes` | registry entries of kind attribute |
| `bounds` | statements with an attribute bound, evidence-linked and dated |
| `library_rules` | entities kind library_rule |
| `obligation_templates` | entities kind obligation_template with role relations to capabilities |
| `outcome_vocabs` | entities kind outcome_vocab with outcome_of members |
| `ack_nodes` | entities kind ack |
| `transforms` | registry entries kind transform (relation type by effect pair) |
| `stories` | entities kind story |
| `instruments` | entities kind instrument (V4); references an underlying |
| `cost_models` | entities kind cost_model |
| `tides` | entities kind tide (a story with a proxy) |
| `carriers` | entities kind document_series; reports_on |
| `procedural_models` | entities kind procedural_model |
| `entities` | the entity table (canonical) |
| `entity_kinds` | the kind registry (canonical) |
| `capabilities` | the capability registry (canonical) |
| `key_map` | identity mapping (identity events) |
| `attribute_scope` | registry constraint: which attributes a kind may carry |

## 5. The hedge mechanism, in the model (A1 §7, restated with no scenario)

1. A **primary thesis** entity carries a `covers` relation to the outcomes in its thesis set, and a **basket** is `constructed_for` it.
2. The harness reads the basket's `pays_under` relations (the payoff matrix, with basis documented, estimated or gap) and **computes** `fails_under` for the outcomes below `FAILURE_LOSS_PCT`. It is never authored.
3. A **hedge thesis** (a thesis with role hedge) is authored by a session, `authored_by` it; it `covers` the failure set, each exclusion anchored by statements with evidence links; the `hedges` relation ties it to the primary. The set of `hedges` relations for one primary is the DAG: one-way, single-sink, acyclic, no cross-reference between theses.
4. A hedge **basket** is `constructed_for` the hedge thesis, from instruments whose documented `exposed_to` relations fit its outcomes; long-only.
5. A **shadow** basket (`shadows`), a blind statistical pair, is paper-filled beside it and never traded; the record scores both.
6. Objectives and the cap on baskets are `parameter` entities declared at lock.
7. **Price** appears only in step 2's payoff estimates and in paper marks, as `price_series` datasets: attentional, confirming and never proposing. Exposures, outcomes and effects are evidenced by documents and datasets of other kinds.

## 6. The data layer, as entities (added after Rob: "fundamentals are just one aspect")

Under the view every source is a **dataset or document entity of some kind**, and each kind has an **evidence mode** that says what it may do (R13). The mode follows what the source *measures*, not how it arrived. This replaces the older blanket rule that all
alternative data may only propose: a recorded reactor power level or an earthquake catalogue is a measurement of the state of a thing by a recording authority; a tally of news events is attention; a model's reading of an image is an analogy until it is validated.

| Dataset kind | Evidence mode | Evidences | What is wired in the repo today | Note |
|---|---|---|---|---|
| `price_series` | attentional | prices | prices.py (Yahoo) into the vintage store | |
| `regulatory_record` | regulatory | a notice, docket or event report from an agency (NRC event notificatio | pit_fetch: nrc_en; enumeration feed (NRC); Fed pages read in the look-backs | |
| `legal_filing` | accounting | a filing on the public record (10-K, 10-Q, 8-K, ownership forms), text | pit_fetch: edgar_filings, edgar_doc | |
| `fundamental` | accounting | a structured or stated figure from a filing (a quarterly line item, a  | SEC structured facts (used in the look-backs); no harness adapter yet | |
| `state_observation` | physical | a measurement of the state of a thing by a recording authority (reacto | pit_fetch: nrc_status; alt_fetch: portwatch_chokepoint, portwatch_port, ioda, usgs, firms (key needed) | |
| `remote_sensing` | analogical | a model reading of an image (scene brightness counts) | alt_fetch: s2_scenes, s2_image | |
| `media_event` | attentional | coded news events and tallies | alt_fetch: gdelt_events; acled needs a key | |
| `calendar_fact` | scheduled | an agency or exchange calendar entry | not in the harness; read from the data product's scheduled_fact | |
| `ownership_edge` | accounting | an ownership or control edge with a share and a source filing | data product: ownership_edge; the K7 census by hand | |
| `instrument_map` | accounting | which listed instrument references which entity | data product: instrument_map; the K7 census by hand | |
| `quote` | attentional | a prediction-market or event-contract quote | data product: quote | |

**So no, it is not only fundamentals.** Wired in this repo: the NRC event notifications and reactor status, the SEC filing index and documents, the Wayback snapshots, Sentinel-2 scenes, the IMF PortWatch port and chokepoint counts, the GDELT event exports, IODA internet-outage signals, the USGS earthquake catalogue, Yahoo prices (into the vintage store), and the hand-run K7 census.
Keyed and not yet usable: NASA FIRMS fire detections (needs a map key), Global Fishing Watch vessel presence, ACLED conflict events, NASA Black Marble night lights (issue #15).
**Nomad's own data layer.** The spec's data-product boundary (recorded feeds, `filing_item`, `announcement`, `regulatory_notice`, `ownership_edge`, `instrument_map`, `customer_disclosure`, `scheduled_fact`, `quote`, the event spine) is not built in this repository; where a source is missing Nomad builds or connects it itself. Every source it does read declares itself in `nomad16/declarations.py` (phenomenon, truth role, measured or modeled, as-of or snapshot, survivorship, access, needs), an idea adopted from Ohmni, a separate project with which Nomad has no dependency (`docs/nomad_v17_adopted_from_ohmni.md`).
The look-backs used prices, filings, structured share counts, HURDAT2 and the Fed pages because that is what could be reached.

**Why diversity matters for the mechanism.** Exposures, outcomes and effects can each be evidenced by different kinds, and independent lineages triangulate one another (the spec's rule that cross-membership needs independent derivations). An effect confirmed by a filing, a state observation and a regulator's record is stronger than any one of them, and a channel undisclosed in filings may still be documented by a physical observation or an ownership edge.

## 7. What this changes, and the order

- **Views first.** `entities`, `entity_kinds`, `capabilities`, `key_map`, `entity_events`, `statement_links` exist (V0, V1). Each table above becomes a view over entities, relations and statements with no ledger column added, one family at a time (positions and evidence are done; effects, ACKs and theses next).
- **The registry carries the constraints.** Roles, acyclicity, single-sink and the price exclusion are checked from `config/system_model.json`, not from private lists in the code. Extending the system means adding a kind or a relation type as data.
- **Nothing here is event-specific.** A test or a live round supplies documents and datasets through an adapter; the procedures read kinds and capabilities only.
- **Decision (Rob's): D32.** Adopt this as the model of the whole system, and migrate by views in the order above: ratify, amend or reject. It depends on D17, D19, D20 (ratified), and on D29, the amended D18, D30 and D31 (proposed).

