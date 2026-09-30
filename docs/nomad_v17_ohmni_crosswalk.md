# Ohmni's data layer and Nomad's entity model: a crosswalk (A2 addendum, 2026-09-30)

*Source read: `standard-reference/ohmni`, cloned into the session at commit `cadfb95` (contract 0.1.0). Nothing in that repository was changed. Rob: "you can also see that we landed on kinds previously."*

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

## 3. What Ohmni supplies, and what Nomad needs
| Nomad needs (spec §26) | In Ohmni today | Gap |
|---|---|---|
| Fundamentals with revision chains | EDGAR XBRL, point-in-time, multiple facts per period kept | 6 entities only (semiconductors, hardware, software, automotive) |
| Filing text and items (`filing_item`, `announcement`) | facts only | no filing text |
| Regulatory notices | none | the NRC records are read by Nomad's own adapters |
| `ownership_edge`, `instrument_map`, `customer_disclosure` | a small instrument map for the six names | not built |
| `scheduled_fact` | none | not built |
| Prices | Yahoo daily, **prototype grade**: currently-listed names only, so runs are marked contaminated | no survivorship |
| `quote` (prediction markets) | none | not built |
| Attention sources | Wikimedia, GDELT bulk, Hacker News, FINRA short volume | present |
| Physical-state sources | none | Nomad's adapters (NRC, PortWatch, IODA, USGS, FIRMS keyed) |
| Event spine / cross reference | absent (`cluster_version` is None; `CROSS_REFERENCE` is not declared) | not built |
| Contract version | **0.1.0** | Nomad's spec pins `contract >= 0.2, < 0.3`: a mismatch to resolve |

**Nomad's own oil and rate names are not in it** (its universe is six technology names), so the oil, bank and rate filings I read were fetched by Nomad's adapters, not served by this layer.

## 4. What I would change, on each side
- **Nomad:** a thin `ohmni` adapter that reads `Record`s and writes source entities and statements with `knowable_from` from `knowable_at`, typed gaps from `status`, relations from `lineage`, and the evidence mode from the declared phenomenon and truth role. Bring Nomad's own sources (NRC, PortWatch, IODA, USGS) into the same declaration shape so they are one layer to the model.
- **Ohmni:** register the physical-state and schedule phenomena and the missing sources through its plugin loader, so the conformance suite runs on them; widen the entity set beyond six; reconcile the contract version.
- **Both:** Ohmni's own discipline is stricter than Nomad's look-backs have been: declare the bar before the run, no default on a verdict-governing number, report negative results, **and run the whole protocol over null markets** (its report 004 found one epoch promoted 0 and another 39 on null data). The convexity map used a permutation null; the earlier oil and FOMC tests did not. Each look-back should carry a null control.

## 5. Decisions (Rob's)
1. Are Nomad's physical-state and schedule sources to become plugins in Ohmni's layer, or stay Nomad-side adapters that declare themselves in Ohmni's shape?
2. Which universe does the shared layer cover first (the oil, bank and rate names used so far, or another)?
3. Contract 0.1.0 against Nomad's `>= 0.2`: which side moves?
4. R13 as stated: evidence supports only claims about its own phenomenon.
