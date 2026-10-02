# Ideas Nomad adopts from Ohmni (A2 addendum, 2026-09-30)

*Source read: `standard-reference/ohmni` at commit `cadfb95` (contract 0.1.0), cloned into the session; nothing there was changed. **Ohmni is a separate project, a more ambitious one that is meant to generate Nomad-like frameworks over time. Nomad stays Nomad and has no dependency on it; ideas are adopted, not integrated** (Rob, 2026-09-30). Rob: "we landed on kinds previously."*

## 1. The same pattern
Ohmni's spec §18 is titled **"Core pattern: artifact + kind registry"**: a small frozen core (`id`, `kind`, `schema_version`, `attributes`) and an open, registered kind that declares the shape and behaviour of everything else,
each kind validated on registration, each with its own typed registry. That is the entity-and-kind view of `docs/nomad_v17_entity_model.md`, arrived at separately. Two things it adds that the Nomad model should adopt, and one it deliberately keeps separate:
- **Kind registration validates on registration** (the model's registry does this for relation roles; it should for dataset kinds too).
- **Versioned spaces are never compared across versions** (Ohmni's embeddings; Nomad's concept maps and bucket partitions carry the same rule).
- **Separate typed registries** for interfaces that differ (Ohmni keeps effect-claim, evidence, corroboration and so on apart). Nomad keeps one registry mechanism with a `domain` column (D29); the constraint that matters is the same: a wrong-kind lookup must fail, not succeed syntactically.

## 2. Field by field
| Ohmni contract | Nomad entity model |
|---|---|
| `Record.id`, `kind`, `subject` | an entity (or a statement about the subject) of a dataset kind; the subject is an entity key |
| `Record.event_time` | the statement's validity start |
| `Record.knowable_at` (required, no default) | `knowable_from`; the adapter is where the two names meet (spec §26), and Nomad's own derivation from evidence still applies to statements |
| `Record.value` | the statement's value, shaped by the kind |
| `Record.status` (reported, derived, not_representable, not_disclosed, not_applicable, not_covered) | a typed gap: `not_disclosed` (applies, entity did not report it) is exactly Nomad's "no documented exposure"; `not_covered` is outside the source; `not_applicable` and `not_representable` are refusals to guess. None is a zero |
| `Lineage.documents` | `states` / `component` links to a document entity |
| `Lineage.derived_from` | the `derived_from` relation (record to input records) |
| `Lineage.reports_on` | the `reports_on` relation (forty-three articles about one 8-K collapse to one observation) |
| `Revision` (a chain: index, chain_length, superseded_at) | a `supersedes` chain; an as-of read takes the latest `filed <= T` per period |
| `SourceDeclaration` (measurement process, retrieval, survivorship, historical access, backfilled, measurement type, known biases, couples_to) | a dataset kind's registration |
| `Phenomenon`, `TruthRole`, `MeasurementType` | the kind's evidence classification (`config/system_model.json`); Nomad's evidence modes are derived from them (rule R13) |
| `Capability` and the degradation table | Nomad's degradation table (spec §26); same shape, the consequence is data |

**Evidence follows what a source measures.** Ohmni's declarations say what each record is a record *of*: `corporate_disclosure` (EDGAR, a filing IS the disclosure, constitutive), `off_exchange_routing` (FINRA, attested), `information_seeking` (Wikimedia pageviews, observed), `editorial_publication` (GDELT, observed),
`retail_discourse` (Hacker News, constitutive), `exchange_activity` (prices, constitutive). Rule R13 in the model says a dataset supports a statement about X only if its phenomenon is the one X consists of; attention, belief and trading activity about a company propose and never support a statement about the company.
Nomad's additions for the physical world and schedules, `physical_state` (a reactor's recorded power level, a port count, an earthquake catalogue) and `schedule` (an agency calendar), are proposals for Ohmni's registry, not declared there yet.

## 3. What Nomad adopted, and where it lives in Nomad
- **Source self-declaration** (Ohmni §7): `nomad16/declarations.py`. Every adapter Nomad has, and every source the look-backs used, declares what it measures (phenomenon), the truth role of its records, measured or modeled, `as_of` or `snapshot`, survivorship, historical access, backfill,
  needs and known biases. An undeclared source is refused. The declarations are the builder's and are marked unverified until checked against each source's own documentation.
- **Evidence follows what a source measures** (Ohmni's phenomenon and truth role): rule R13, implemented as `may_support`. A price supports a claim about exchange activity and only proposes about a company's exposure; a recorded reactor power level supports a claim about state; a modeled image reading is analogical until validated.
- **A snapshot with unrecoverable deletions has no honest history** (Ohmni §7): `check_historical` refuses it.
- **Typed statuses, never null** (Ohmni's Status): Nomad already had typed gaps; `not_disclosed`, `not_covered`, `not_applicable` and `not_representable` are the vocabulary the exposure work needs, since an undisclosed sensitivity is the case that kept recurring.
- **The discipline:** declare the bar before the run; no default on a verdict-governing number; report negative results; and **run a null control** (Ohmni's report 004: one epoch promoted 0 and another 39 on null data). The convexity map used a permutation null; the earlier oil and Fed-day tests did not, and each look-back from now on carries one.

## 4. What Nomad does not take
The contract, the `Record` class, the plugin loader, the harness and the six-entity universe. Nomad's spec §26 describes a data-product boundary of its own; in this repository Nomad's data layer is its own adapters (`pit.py`, `altdata.py`, `prices.py`) plus what the look-backs read directly (structured filing facts, the Fed statements, HURDAT2),
declared in `nomad16/declarations.py`. Where Nomad needs a source it lacks (filing text and items, ownership edges, scheduled facts, prediction-market quotes, an event spine), it builds or connects it itself.
