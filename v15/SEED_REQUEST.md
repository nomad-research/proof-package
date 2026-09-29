I have built the Nomad Harness from `nomad_harness_spec_v1.md` (append-only SQLite ledger, hash chain, firewall state machine, scorer, library, predicate registry, names book, positions, hypothesis notebook, all exposed over MCP). It is running and tested. What it does not have is the seed data from spec §8, because that content lives in `nomad_system_as_it_stands_v4.md` and the session record, which the build session never saw.

I need two things from you.

## 1. The documents themselves

Give me `nomad_system_as_it_stands_v4.md` in full as a downloadable markdown file, plus the session record for rounds 1-3 (the predictions as written, the retrieval, the self-scoring). I will keep them next to the spec.

## 2. A filled seed file

Fill the attached `seed_v4_template.json` and return it as one JSON file named `seed_v4.json`. It loads straight into the ledger, so the fields have to be exact. Rules that will make the load fail:

**Predicates** (v4 §4.3 seven arming, §4.4 five disarming, §4.5 one exit and one catalyst)
- `name`: unique snake_case. `kind`: arming | disarming | exit | catalyst.
- `source` (a named source), `threshold` (the checkable condition, in words), `date` (ISO or null), `role_note`.
- Tell me which arming predicate is the tradability gate, and which is predicate 6 (single form), because the harness already seeds the pair form of 6 as `pair_gate_opposing_listed_positions`.

**Library rules** (every entry in v4 §3.4, all as candidates)
- `key`: short unique handle used by the other sections. `layer`: sequence | transmission | ownership | operator | other. `obscurity`: 1-5.
- `rule_text` may not contain proper nouns. The loader rejects any capitalised word that is not a sentence-start function word (allowed: AI, US, EU, UK, UN, month names, Q1-Q4). Safest is to write the rule entirely in lower case. Every noun goes in `provenance` (round, event, names).
- `forbids`: what the rule says cannot happen. `composed_of`: list of other keys for compositions, else [].

**Holders and positions** (v4 §8: PO producers per plant, freight and insurance holders, port and terminal operators)
- `holders[].key` unique; `kind`: company | plant | facility | authority | fund | other; `parent`: the key of the owning company for plants; `listed` true/false; `ticker`, `exchange` or null; `aliases[]` with `alias_kind`: name | former_name | subsidiary | plant_name | ticker | abbreviation.
- `positions[]`: `holder` is a holder key; `node` is the shared thing (material, route, facility, rule, region); `attribute`: tier | priority | substitutability | share | duration | sign_of_exposure; for sign_of_exposure the `value` is "+" (scarcity on the node helps this holder), "-" or "0". Populate sign_of_exposure for every holder first, finer attributes only where disclosed. `confidence`: stated | inferred | implicit, honestly; most will be inferred. `source_time` and `knowable_from` ISO or null.

**Retro rounds 1-3**, entered faithfully, misses included
- `operator`: the model string the round was played with (e.g. claude-opus-4-1), and `operator_cutoff` as an ISO date if you know it.
- `event.event_text` one line; `event_date` YYYY-MM-DD; `criteria_json` Q1-Q9 each pass | fail | unknown; `selection_rule`; `rejected_before` integer.
- `predictions[]`, one per call: `call_type`: sign | magnitude_order | lag_band | predicate | null | meta. `carrier` required for all but meta. `falsifier` required for sign and magnitude_order. `sign` ("+","-","0") required for sign calls; `magnitude_rank` integer for magnitude_order; `lag_band`: days | weeks | months | never for lag_band calls. A null call has `target` "none". `mechanism_keys`: library keys the call rode; if empty, `claim` must contain the text `no-mechanism:` followed by why. `baseline_claim`: what the dumb baseline said.
- `evidence[]`: what was retrieved after the lock. `excerpt` 500 characters max. If there is no URL, put `session-record:round-N` as the url and say so in `note`. `source_time` is the time in the document, `knowable_from` when it became public.
- `predicate_checks[]`: `predicate_id` is a predicate name from above; `claimed` and `observed`: holds | fails | unknown.
- `resolutions[]`, exactly one per prediction: `prediction_index` (0-based), `outcome`: hit | miss | unverified | untestable; `mechanism_outcome`: right | wrong | unknown; `baseline_outcome`: hit | miss | unverified; `evidence_indexes` into the evidence list; `scorer_note`. A hit with mechanism wrong is quarantined automatically. Do not soften misses.

**Standing hypotheses** (spec §8 names two: the tide-cancellation test and "constraint prices de-escalate slowest" against the Hormuz premia ladder). The harness already holds a version of each in its own words; give me your wording and any others from the session. `arming` and `disarming` are predicate names; `falsifier` and `granularity` are mandatory and granularity is locked at creation.

Also tell me, outside the JSON: the one-line definitions of Q1-Q9, and anything in v4 §11 that the spec v1 build should have known about and might not.

If something is genuinely unknown, write null or "unknown" rather than filling it in. Thin is fine; the thinness is data.
