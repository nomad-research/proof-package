# Nomad Harness — Build Spec v1

**Target:** one working day (blocks 1–6, 8); block 7 may slip to day two. Companion to `nomad_system_as_it_stands_v4.md` §11.
**Purpose:** turn the event-prediction game into a firewalled, scored, append-only instrument — the scoring harness (v4 hole 1) with a wall, producing the arming rate (hole 2) and starting the bitemporal record.

Everything not listed under Scope is out. Resist adding baskets.

---

## 1. Scope

**In:**
1. Event intake with hash-before-reveal and selection logging
2. Round state machine that gates retrieval behind prediction lock
3. Prediction lock — append-only, hash-chained, timestamped
4. Scorer — two ledgers, attribution, quarantine, baseline pairing, null weighting
5. Library store — rules, compositions, status transitions driven by scores
6. Predicate registry — ACKs as records with arm/disarm role
7. T0 counter — criteria checklist + arming predicates per candidate, count over a window
8. Knowable-time stamping on every stored row
9. **Positions store** — holders' positions on nodes (the nouns the library's verbs act on); baskets are a *projection* of this store under a shock, not a store of their own
10. **Names book** — holders and their aliases, grown by play; the minimum entity resolution that lets a predicate be machine-checked
11. **Standing-hypothesis notebook** — bets the system would make that are waiting on a predicate; the plain-English core of the shadow book (§4.13)
12. MCP exposure (stdio for Claude Code; streamable HTTP later for claude.ai)

**Out (deliberately):** basket *sizing*, execution, netting, capital, promotion-to-live, mark-to-market of open hypotheses, price data feeds, automated web retrieval, automated alias matching beyond exact/normalised string match. The operator (Claude) does retrieval with its own tools *after* the harness opens the round; the harness records what was retrieved as evidence.

---

## 2. Stack

- Python 3.11+, `mcp` (FastMCP), `pydantic` v2, `sqlite3` (stdlib). One file DB: `nomad_harness.db`.
- Transport: **stdio** for Claude Code (day one). Add streamable-HTTP entry point behind a flag for later remote use.
- Repo: `standard-reference/Nomad-Research`, new package `harness/`. Reuse existing `config_logger` pattern if it fits; don't refactor it.
- Tests: `pytest`, in-memory SQLite.

---

## 3. Invariants (write these as tests first)

1. **Append-only.** No `UPDATE` or `DELETE` on `rounds`, `predictions`, `resolutions`, `evidence`, `events`. Corrections are new rows with `supersedes` pointing at the old one.
2. **Hash chain.** Every row in the append-only tables carries `row_hash = sha256(prev_row_hash || canonical_json(row))`. `verify_chain()` walks the table and fails loudly on any break.
3. **Firewall order.** A round cannot enter `open` until at least one `predictions` row exists for it with `locked_at` set. `open_retrieval` on an unlocked round is an error, not a warning.
4. **Bitemporal columns.** Every table has `recorded_at` (UTC, set by the harness, never by caller). `evidence` additionally has `source_time` (nullable, from the document) and `knowable_from` (nullable, when it became publicly discoverable). Callers may not set `recorded_at`.
5. **No proper nouns in rules.** `library_propose` rejects rule text matching a capitalised-token heuristic (regex for `\b[A-Z][a-z]+` outside sentence-start plus an allowlist: month names, "AI", "US", "EU"). Nouns go in `provenance`. Heuristic, not perfect — that's fine; the point is friction.
6. **Null weighting is a pre-registered constant.** `NULL_CALL_WEIGHT = 0.2` in config, logged with every score. Changing it is a config commit, not a runtime parameter.

---

## 4. Data model

SQLite; `id` = UUIDv7 text; all times ISO-8601 UTC strings.

### 4.1 `events`
```
id, event_text (one line), event_date, source (where it was found),
selection_rule (text), rejected_before (int — how many candidates were rejected before this one),
criteria_json (Q1–Q9 pass/fail/unknown, filled at intake by the human selector),
event_hash (sha256 of event_text||event_date — set at intake, revealed to operator only via reveal_event),
recorded_at, prev_row_hash, row_hash
```

### 4.2 `rounds`
```
id, event_id, operator (model id string), operator_cutoff (date),
state ∈ {created, locked, open, scored, void}, state_changed_at,
recorded_at, prev_row_hash, row_hash
```
State transitions are rows in `round_transitions(id, round_id, from_state, to_state, reason, recorded_at, …hash)`. `rounds.state` is a cache; the transitions table is truth.

### 4.3 `predictions`
One row per **call**. A round has many.
```
id, round_id, call_type ∈ {sign, magnitude_order, lag_band, predicate, null, meta},
target (entity, carrier, predicate name, or a (holder_id, node) position), claim (text),
hypothesis_id (nullable — set when this call resolves a standing hypothesis from §4.13),
sign ∈ {+, -, 0, null}, magnitude_rank (int, nullable), lag_band ∈ {days, weeks, months, never, null},
carrier (what will be checked to score this — required for all but meta),
falsifier (text — what appearing first kills this call; required for sign/magnitude),
mechanism_ids (json list — library rule/composition ids the call rides; required, may be empty with reason),
baseline_claim (text — what the dumb baseline says for this target),
confidence_band (text, optional), locked_at,
recorded_at, prev_row_hash, row_hash
```

### 4.4 `evidence`
```
id, round_id, url, title, source_time, knowable_from, excerpt (≤ 500 chars), note,
recorded_at, prev_row_hash, row_hash
```
Written only while round is `open`.

### 4.5 `resolutions`
One per prediction.
```
id, prediction_id, outcome ∈ {hit, miss, unverified, untestable},
mechanism_outcome ∈ {right, wrong, unknown},
quarantined (bool — true iff outcome=hit AND mechanism_outcome=wrong),
baseline_outcome ∈ {hit, miss, unverified},
evidence_ids (json list), scorer_note, weight (float — 1.0, or NULL_CALL_WEIGHT for null calls),
recorded_at, prev_row_hash, row_hash
```

### 4.6 `library_rules`
```
id, rule_text, forbids (text), obscurity (1–5), layer (text: sequence|transmission|ownership|operator|other),
status ∈ {candidate, validated, retired}, composed_of (json list of rule ids; empty for atomic),
provenance (text — nouns allowed), proposed_in_round (nullable),
hits (int), misses (int), false_alarms (int), trials (int),
created_at, superseded_by (nullable)
```
Mutable counters are acceptable here (this table is a *view* over resolutions; `rebuild_library_stats()` recomputes it from the ledgers, so it is never the source of truth).

**Compositions** are rows with non-empty `composed_of`. They are proposed and scored exactly like atomic rules. A composition's hit does *not* propagate to its parts; a part's miss *does* flag the composition for review (`review_flag`).

### 4.7 `predicates`
```
id, name, kind ∈ {arming, disarming, exit, catalyst}, source (named), threshold (text), date (nullable),
role_note, active (bool), created_at
```
Seed with the seven arming predicates from v4 §4.3 and the disarming set from §4.4. Day one they are records, not executors; `predicate_check` records the operator's *claim* about each.

### 4.8 `predicate_checks`
```
id, round_id, predicate_id, claimed ∈ {holds, fails, unknown}, observed ∈ {holds, fails, unknown, null},
note, recorded_at, …hash
```

### 4.9 `t0_candidates`
```
id, event_id, window_label, criteria_pass (bool), arming_pass_single (bool nullable),
arming_pass_pair (bool nullable), listed_party (text nullable), pair_holders (json nullable),
carrier (text nullable), micro_macro_note,
recorded_at, …hash
```
Both gate versions logged so we can see which arms more often (§4.12 pair gate).

### 4.10 `holders` — the names book
A holder is anything that can hold a position: a company, a plant, a terminal, a port authority, a fund. Plants are holders in their own right (round 2: per-plant, not per-company), with `parent_id` pointing at the owning company.
```
id, canonical_name, kind ∈ {company, plant, facility, authority, fund, other},
parent_id (nullable), listed (bool), ticker (nullable), exchange (nullable),
first_seen_round (nullable), created_at
```

### 4.11 `aliases`
```
id, holder_id, alias (text), alias_kind ∈ {name, former_name, subsidiary, plant_name, ticker, abbreviation},
source, knowable_from (nullable), recorded_at, …hash
```
Resolution day one is **exact and normalised string match** (casefold, strip punctuation and corporate suffixes) against `aliases`. Anything that doesn't match goes to `orphans(id, raw_string, context, round_id, recorded_at)` — a queue the human clears by either linking to a holder or creating one. The orphan rate by holder size *is* the size-bias measurement (v4 known cost). No fuzzy matching, no external entity API, day one.

### 4.12 `positions`
The nouns the library's verbs act on. A basket is what you get by shocking this table; it is not stored.
```
id, holder_id, node (text — the shared thing: material, route, facility, rule, region),
attribute ∈ {tier, priority, substitutability, share, duration, sign_of_exposure},
value (text or number), unit (nullable), source, source_time (nullable), knowable_from (nullable),
confidence ∈ {stated, inferred, implicit}, superseded_by (nullable),
recorded_at, …hash
```
`sign_of_exposure` is the coarsest attribute (does scarcity on this node help or hurt this holder) and is always populated first; finer attributes fill in as disclosed. `confidence` is the epistemic class of the fact, so the store carries the ladder (v4 §6.4) from day one.

**Pair gate (arming predicate 6, pair form):** on shocked node N, there exist two *listed* holders with opposite `sign_of_exposure` and a position difference above threshold (threshold to be measured; day one: any difference, logged). Pre-registered test carried in the seed: *for shocks where two listed holders held opposing positions on the node, the pair's relative move exceeded either leg's absolute attributable move.* If this fails across ten rounds, tide-cancellation is dead and positions are ontology only.

### 4.13 `hypotheses` — the standing-hypothesis notebook
The plain-English core of the shadow book: **every bet the system would make, whether or not it makes it, with the condition that would make it fire written next to it.** Predictions in §4.3 are event-first and round-bound; hypotheses are standing and predicate-bound. Nothing here is marked to market day one — status is resolved by predicates, not prices.
```
id, text (one falsifiable sentence), node (nullable), holder_ids (json), position_ids (json, nullable),
mechanism_ids (json), arming_predicate_ids (json), disarming_predicate_ids (json), falsifier (text),
granularity (text — declared and locked at creation), status ∈ {open, armed, fired, falsified, expired, resolved},
opened_in_round (nullable), created_at, superseded_by (nullable)
```
`hypothesis_checks(id, hypothesis_id, predicate_id, observed ∈ {holds, fails, unknown}, evidence_ids, note, recorded_at, …hash)` — the scheduled check record. Status transitions are derived: all arming predicates `holds` → `armed`; any disarming `holds` → `falsified`/`expired`; a later round's event resolves it → `resolved` with a `resolutions` row like any prediction.

What this gives without building the rest of the shadow book: a place to hold prepositioned predicates so ACKs have something to condition; the full population of unacted hypotheses in the calibration denominator; and lineage (`superseded_by`) so learned-later edges become new hypotheses rather than edits.

---

## 5. Firewall — state machine

```
created ──lock_predictions──▶ locked ──open_retrieval──▶ open ──score_round──▶ scored
   │                                                            
   └───────────────────────── void (with reason) ◀──────────────┘
```

- `created`: event exists; operator has been shown **only** `event_text` + `event_date` via `reveal_event`. No other fields.
- `locked`: ≥1 prediction row with `locked_at`. Further predictions may be added *until* `open_retrieval`, each individually stamped; none may be edited.
- `open`: retrieval permitted. Predictions frozen. Evidence rows accepted.
- `scored`: resolutions exist for every prediction. Round frozen entirely.
- `void`: abandoned; reason logged; nothing deleted.

**Enforcement, honestly stated.** The harness cannot stop a chat client from web-searching. It can (a) refuse to accept evidence or scores against an unlocked round, (b) stamp everything so out-of-order behaviour is visible in the chain, and (c) in **Claude Code**, be paired with a `PreToolUse` hook that denies `WebSearch`/`WebFetch` unless `harness_state(round_id) == open`. Ship (a) and (b) day one; (c) is a 20-line hook and turns the promise into a wall — do it if time allows.

---

## 6. MCP tools

Prefix `nomad_`. Return structured JSON plus a one-line text summary. Errors must say what to do next.

| Tool | Args | Effect | Annotations |
|---|---|---|---|
| `nomad_submit_event` | event_text, event_date, source, selection_rule, rejected_before, criteria_json | Creates `events` row + `rounds` row in `created`. Returns round_id and event_hash. **Does not return event_text** (the human already has it; this keeps the operator path clean). | destructive=false, idempotent=false |
| `nomad_reveal_event` | round_id | Returns event_text + event_date only. Logs a transition note `revealed`. | readOnly |
| `nomad_lock_predictions` | round_id, predictions: list[PredictionIn] | Validates (carrier required, falsifier required for sign/magnitude, mechanism_ids required), stamps, appends. Moves round to `locked` on first call. Error if round is `open`/`scored`. | destructive=false |
| `nomad_open_retrieval` | round_id | Requires `locked`. Moves to `open`. Returns the frozen prediction list for the scorer's reference. | destructive=false |
| `nomad_add_evidence` | round_id, url, title, excerpt, source_time?, knowable_from?, note? | Requires `open`. Appends evidence. | destructive=false |
| `nomad_score_round` | round_id, resolutions: list[ResolutionIn] | Requires `open`; requires one resolution per prediction (error lists missing ids). Computes `quarantined`, applies `weight`, appends, moves to `scored`, triggers `rebuild_library_stats()`. Returns scorecard (§7). | destructive=false |
| `nomad_void_round` | round_id, reason | Any state → void. | destructive=false |
| `nomad_library_query` | text?, layer?, status?, limit | Search rules/compositions. Returns rule + stats. | readOnly |
| `nomad_library_propose` | rule_text, forbids, obscurity, layer, composed_of?, provenance, round_id? | Applies noun heuristic; inserts as `candidate`. Returns id. | destructive=false |
| `nomad_library_retire` | rule_id, reason | Sets status retired; writes `superseded_by` if a replacement id given. | destructive=false |
| `nomad_predicate_check` | round_id, checks: list[{predicate_id, claimed, observed?, note}] | Appends `predicate_checks`. `observed` may be filled at scoring time via a second call. | destructive=false |
| `nomad_predicate_list` | kind? | Registry read. | readOnly |
| `nomad_t0_submit_candidate` | event_id, window_label, criteria_pass, arming_pass?, listed_party?, carrier?, micro_macro_note? | Appends. | destructive=false |
| `nomad_t0_count` | window_label | Returns counts: candidates, criteria_pass, arming_pass, distinct (event × listed_party × carrier) triples. | readOnly |
| `nomad_holder_upsert` | canonical_name, kind, parent_id?, listed, ticker?, aliases: list | Creates holder + aliases (append-only aliases). Returns id. | destructive=false |
| `nomad_resolve` | raw_string, context?, round_id? | Normalised match against aliases → holder_id, or writes an orphan and returns `unresolved` with the orphan id. | destructive=false |
| `nomad_orphans` | limit | Queue of unresolved names. | readOnly |
| `nomad_position_add` | holder_id, node, attribute, value, unit?, source, source_time?, knowable_from?, confidence | Appends a position fact. | destructive=false |
| `nomad_positions_on_node` | node, listed_only? | All current positions on a node (latest per holder×attribute); flags opposing-sign listed pairs — the pair gate's raw material. | readOnly |
| `nomad_hypothesis_open` | text, node?, holder_ids, mechanism_ids, arming_predicate_ids, disarming_predicate_ids, falsifier, granularity, round_id? | Opens a standing hypothesis. Rejects missing falsifier or granularity. | destructive=false |
| `nomad_hypothesis_check` | hypothesis_id, checks: list[{predicate_id, observed, evidence_ids?, note}] | Appends checks; recomputes derived status. | destructive=false |
| `nomad_hypotheses_due` | status?, limit | Open/armed hypotheses and their last check — the schedule surface. | readOnly |
| `nomad_verify_chain` | table? | Walks hash chains; returns first break or ok. | readOnly |
| `nomad_round_status` | round_id | State, counts of predictions/evidence/resolutions, transitions. | readOnly |
| `nomad_export_round` | round_id | Full round as JSON (for Notion/markdown recap). | readOnly |

**PredictionIn** (pydantic): `call_type, target, claim, sign?, magnitude_rank?, lag_band?, carrier, falsifier?, mechanism_ids: list[str], baseline_claim, confidence_band?`. Validation: `call_type=null` requires `target="none"` and `claim` non-empty; `mechanism_ids` may be `[]` only if `claim` contains `no-mechanism:` prefix explaining why (this is the operator-distortion trap; make them say it).

**ResolutionIn**: `prediction_id, outcome, mechanism_outcome, baseline_outcome, evidence_ids: list[str], scorer_note`.

---

## 7. Scorer

Computed at `score_round`, stored with the round, and recomputable from ledgers.

**Per call:** `hit ∈ {0,1}`, `weight`, `quarantined`.
- `weight = NULL_CALL_WEIGHT` if `call_type = null`, else `1.0`.
- `quarantined = (outcome == hit) and (mechanism_outcome == wrong)`. Quarantined calls **count as hits in the outcome ledger and are excluded from the mechanism ledger.**

**Round scorecard:**
```
outcome_score   = Σ hit·weight / Σ weight            (over resolved, non-untestable)
mechanism_score = Σ [hit and not quarantined]·weight / Σ weight   (same denominator)
baseline_score  = Σ baseline_hit·weight / Σ weight
edge_vs_baseline = mechanism_score − baseline_score
null_called      = bool
arming_claimed   = bool (any predicate_check claimed holds for the tradability gate)
unverified_frac, untestable_frac
```

**Library stats (rebuilt):** for each rule id appearing in `mechanism_ids` of a resolved prediction: `trials += 1`; `hits += 1` if hit and not quarantined; `misses += 1` if miss; `false_alarms += 1` if the rule was cited and the call was a miss on a `sign` or `magnitude_order` type. Status transition: `candidate → validated` when `hits ≥ 2` in ≥2 distinct rounds with `misses == 0`, **or** manually via `library_retire`'s inverse (leave manual promotion out day one — automatic only).

**Programme-level (read tool later):** arming rate = rounds where tradability gate claimed *and* observed `holds` / rounds scored. Mechanism score distribution over rounds. These are two SQL queries; expose as `nomad_programme_stats` if time allows.

---

## 8. Seed data

On first run (`nomad_harness init`):
- Insert the 7 arming + 5 disarming + 1 exit + 1 catalyst predicates from v4 §4.3–4.5.
- Insert the current library entries from v4 §3.4 as `candidate` (they were harvested from misses; none has yet called a future event blind). Provenance fields carry the round nouns.
- Insert rounds 1–3 retroactively as `scored` with a `retro=true` flag in `scorer_note`, so the ledgers start non-empty. Their predictions are already written down in the session record; enter them faithfully, including the misses.
- Seed the names book and positions from the three rounds: the PO producers (per plant where known), the freight/insurance holders, the port and terminal operators — with `confidence` set honestly (most will be `inferred`). This is the first position map and it will be thin; that thinness is data (v4 hole 7).
- Open two standing hypotheses from the session as the notebook's first entries, e.g. the tide-cancellation test (§4.12) and "constraint prices de-escalate slowest" expressed against the Hormuz premia ladder, each with falsifier and granularity.

---

## 9. Tests (minimum)

1. Append-only: attempt UPDATE/DELETE via the API surface → impossible (no such tool); direct SQL in test confirms triggers block it (add `BEFORE UPDATE`/`BEFORE DELETE` triggers that `RAISE(ABORT)` on ledger tables).
2. Hash chain: insert 3 rows, tamper one, `verify_chain` reports the break at the right row.
3. Firewall: `open_retrieval` on `created` → error; `add_evidence` on `locked` → error; `lock_predictions` after `open` → error.
4. Scorer: constructed round with 4 calls (hit, miss, quarantined hit, null-hit) → outcome_score, mechanism_score, weights match hand computation.
5. Noun heuristic: "The toll booth learns before the cargo" passes; "Hormuz insurance repriced first" fails; "AI operators wake fresh" passes (allowlist).
6. Composition: propose composition of two rules; score a round citing the composition; parts' stats unchanged; composition's stats change.
7. T0 count: three candidates, two criteria_pass, one arming_pass → counts correct; distinct triple count correct with duplicates.
8. Names book: `resolve("LyondellBasell Industries N.V.")` → holder; `resolve("Bayport Choate")` → plant holder with parent; `resolve("Acme Foam LLC")` → orphan written, returned unresolved.
9. Positions + pair gate: two listed holders with opposite `sign_of_exposure` on node X → `positions_on_node` flags the pair; one holder with both signs (owner-of-substitutes) → flagged as self-hedged, not a pair.
10. Hypothesis lifecycle: open → arming checks all `holds` → status `armed`; a disarming `holds` → `falsified`; a round resolution referencing it → `resolved`.

---

## 10. Acceptance (end of day)

- [ ] `nomad_harness init` creates DB, seeds predicates + library + retro rounds; `nomad_verify_chain` → ok
- [ ] A full round runs end-to-end from Claude Code over stdio: submit → reveal → lock → open → evidence → score → export
- [ ] `nomad_open_retrieval` before lock is rejected with a message naming the missing step
- [ ] Library stats rebuild from ledgers; deleting `library_rules` counters and rebuilding gives identical numbers
- [ ] All tests green
- [ ] Optional: `PreToolUse` hook denying `WebSearch`/`WebFetch` unless the active round is `open`

---

## 11. Day plan

| Block | Deliverable |
|---|---|
| 1 | Schema + triggers + hash chain + `verify_chain` + tests 1–2 |
| 2 | Rounds state machine + `submit/reveal/lock/open/add_evidence/void` + test 3 |
| 3 | Scorer + `score_round` + library stats rebuild + tests 4, 6 |
| 4 | Library propose/query/retire with noun heuristic + predicates registry + test 5 |
| 5 | T0 tools + test 7; seed script incl. retro rounds 1–3 |
| 6 | Names book + positions + `positions_on_node` pair flag; tests 8–9 |
| 7 | Hypotheses notebook + checks + derived status; test 10 |
| 8 | FastMCP wiring, stdio, Claude Code config, one live round; hook if time |

If the day runs short, block 7 slips to day two; blocks 6 and 8 do not.

---

## 12. Open decisions (decide in five minutes, don't design)

- **Operator identity:** store `operator` as the model string the round was played with; the cutoff date is per-operator config. Firewall is per-operator-model.
- **Who scores:** day one the operator self-scores (as in rounds 1–3) and the human ratifies via `scorer_note`. A separate scorer model is a flag for later, not a feature now.
- **Round-1-style contamination:** if the operator peeks before lock, the round is `void` with reason `contaminated`, not scored. No partial credit.
- **NULL_CALL_WEIGHT = 0.2** stands until 20 rounds exist; then it is reviewed once and locked again.
