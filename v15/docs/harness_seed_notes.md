# Harness seed — notes outside the JSON

Companion to `seed_v4.json`, `nomad_system_as_it_stands_v4.md`, `nomad_harness_spec_v1.md`, `nomad_session_record_rounds_1-3.md`.

## 1. Q1–Q9 — event qualifying criteria (definitions)

Applied by the human selector at intake; recorded in `events.criteria_json` as `pass | fail | unknown` with an optional note. These decide whether an event is *playable*; the arming predicates decide whether it is *armable*. Different questions.

| Q | Name | Definition | Guards against |
|---|---|---|---|
| Q1 | First traversal | The event is the opening shock of its own story, at **both** event and node level. Event: no directly related market-moving news in the prior ~30 days. Node: the shared thing is not a recurring-disruption node (repeat failures in recent months). | Round 1 (event), round 3 (node): channels already priced |
| Q2 | Post-cutoff | Event date is after the operator's knowledge cutoff (`config.operator_cutoff`, currently 2026-01-31). | Training-set contamination |
| Q3 | World event, not price event | Something happened in reality — closure, ban, fire, strike, rule change, insolvency, recall. Not "X fell 20%". | Circularity; price never proposes |
| Q4 | Touches a shared thing | Hits something multiple holders depend on or compete over: facility, route, material, rule, port, standard, region. Not a single-company internal event. | Nothing to join up |
| Q5 | Underread but material | Trade-press or regional-news sized. A normal person hasn't heard of it; someone inside the industry cares a lot. | Global headlines (instantly read) and trivia (nothing propagates) |
| Q6 | One event, one date, one line | Not a trend. | No before/after to score |
| Q7 | Scoreable aftermath | ≥4 weeks old; at least one plausibly touched party has a checkable carrier (price, filing, notice, index). | Unscoreable rounds |
| Q8 | Clean prompt | Bare event + date. No aftermath, affected parties, market reaction, or loaded adjectives. Paraphrase down if needed. | Leakage (round 3's duration leak) |
| Q9 | Selection honesty | Chosen by a fixed source + start date + first-qualifier rule, not by remembered outcome. Rejections logged in `events.rejected_before`. | Selector cherry-picking manufacturing fake lags |

Known tension: Q5 and Q7 pull apart. Sacrifice obscurity before scoreability.

## 2. Which predicate is the tradability gate

`pred.arm.tradability_gate` — arming predicate 6 in v4 §4.3. Two forms, **both logged every round** (`t0_candidates.arming_pass_single` and `arming_pass_pair`):

- **Single-name form:** a listed holder whose expected earnings impact from the event clears the micro/macro ratio (event impact ÷ concurrent macro variance on that name). Threshold unmeasured; log the ratio, don't gate on a number yet.
- **Pair form:** two *listed* holders with opposite `sign_of_exposure` on the shocked node and a position difference above threshold (day one: any difference). A holder with `sign_of_exposure = both` on the node (owner of substitutes, round 2) is **self-hedged** and does not form a pair.

If neither form holds, the round is **scored but not armed**. `pred_arm_tradability_gate` is the only predicate whose failure changes the round's status semantics; every other arming predicate failing just records a miss.

The library rule `lib.lag_without_pureplay_spectacle` is the same idea as a *rule* (scoreable when cited); the predicate is the *gate*. Keep both.

## 3. Things from v4 §11 the build should know

- **Build the harness, not the system.** Baskets are a projection of `positions` under a shock; nothing stores a basket. Netting, walks, sizing, promotion, mark-to-market: out.
- **Knowable-time from day one.** `recorded_at` is set by the harness, never by a caller. `source_time` and `knowable_from` are nullable and caller-supplied. The seed's `knowable_from` values are best-effort reconstructions and should be flagged `retro` (see §5).
- **Firewall honesty.** In chat the wall is soft; the harness refuses out-of-order evidence/scores and stamps everything. In Claude Code, a `PreToolUse` hook denying `WebSearch`/`WebFetch` unless the active round is `open` makes it real. Ship the hook if time allows.
- **Library stats are a view.** `rebuild_library_stats()` recomputes hits/misses/false_alarms/trials from `resolutions` × `predictions.mechanism_ids`. The seed sets every rule to `candidate` and supplies **no counters**; run the rebuild after loading and let status transitions fall out (candidate → validated at ≥2 hits in ≥2 distinct rounds with 0 misses). Expect few or none to validate from three retro rounds — that's correct.
- **Compositions.** Two are seeded (`lib.comp.*`). Their stats do not flow to parts; a part's miss sets `review_flag` on the composition. Neither composition is cited by any seeded prediction, so both start at zero trials.
- **Null weighting.** `config.NULL_CALL_WEIGHT = 0.2`, pre-registered, reviewed once at 20 rounds. Three null calls are seeded (all round 3), weights already set in the seed's resolutions.
- **Quarantine.** `resolutions.quarantined` is derived (`outcome == hit AND mechanism_outcome == wrong`); the seed pre-computes it (one case: `call.r1.oil_fade`). The loader may recompute and should get the same answer.
- **Programme stats to expose when cheap:** arming rate = rounds where the tradability gate was observed `holds` ÷ rounds scored (seed: 0/3); mechanism-score distribution across rounds.

## 4. Enums used in the seed (from spec v1 — check against the build)

- `predicates.kind`: `arming | disarming | exit | catalyst`
- `library_rules.status`: `candidate | validated | retired`; `layer`: `sequence | transmission | ownership | operator | other`; `obscurity`: 1–5
- `holders.kind`: `company | plant | facility | authority | fund | other`
- `aliases.alias_kind`: `name | former_name | subsidiary | plant_name | ticker | abbreviation`
- `positions.attribute`: `tier | priority | substitutability | share | duration | sign_of_exposure`; `confidence`: `stated | inferred | implicit`. `sign_of_exposure` values used: `+ | - | both`
- `rounds.state`: `created | locked | open | scored | void` (seed rounds are `scored`)
- `predictions.call_type`: `sign | magnitude_order | lag_band | predicate | null | meta`; `sign`: `+ | - | 0 | null`; `lag_band`: `days | weeks | months | never | null`
- `resolutions.outcome`: `hit | miss | unverified | untestable`; `mechanism_outcome`: `right | wrong | unknown`; `baseline_outcome`: `hit | miss | unverified`
- `predicate_checks.claimed/observed`: `holds | fails | unknown`
- `hypotheses.status`: `open | armed | fired | falsified | expired | resolved`

Validation rules the seed already satisfies: every `sign`/`magnitude_order` call has a `falsifier`; every `null` call has `target = "none"`; every call has non-empty `mechanism_ids` **or** a `claim` beginning `no-mechanism:` (one case, the round-1 defense baseline leg); every rule's `rule_text` and `forbids` are lowercase with no capitalised tokens; all cross-references resolve.

## 5. Assumptions and things to hand-check

1. **Field names follow spec v1 verbatim.** If the build renamed anything, the seed needs a one-pass rename; the enum list above is the diff surface.
2. **IDs are human-readable strings** (`lib.cut_into_glut_silent`, `holder.lyb`, `call.r2.fm`), not UUIDv7. If the build requires UUIDs, map on load and keep the strings as an `external_id` — the strings are what the operator will cite in `mechanism_ids` during play.
3. **Evidence URLs are placeholders** (`search:<query>`). The originals were lost in a context compaction. `scorer_note` carries the fact. If the loader validates URL shape, relax it for rows where `rounds.retro = true`.
4. **`rounds.retro = true`** is an extra field on the three seeded rounds (spec put it in `scorer_note`; a boolean is cleaner). Treat all seeded `recorded_at`/`knowable_from` as reconstructed.
5. **Holders' tickers/exchanges** are from operator training knowledge, not verified at seed time. Spot-check before anything depends on them.
6. **Positions are thin and mostly `inferred`.** That thinness is the first measurement of v4 hole 7 (position disclosure rate), not a defect of the seed.
7. **Two rules were used at lock but got scored as wrong** (`lib.supply_fear_fade`, `lib.substitutes_gift` in round 2 context). They remain `candidate` with a miss on record — do not retire by hand; let the ledger decide.
8. The spec's rule-text noun heuristic allows sentence-initial capitals; the seed avoids even those. If the build's heuristic is stricter or looser, nothing here should trip it.

## 6. First live round — suggested smoke test

Play one round through the harness deliberately badly: try `nomad_add_evidence` before lock; try `nomad_lock_predictions` with empty `mechanism_ids` and no `no-mechanism:` prefix; try `nomad_library_propose` with a company name in `rule_text`; try `nomad_resolve("Acme Foam LLC")` and confirm it lands in orphans. All four should refuse or divert. Then play the round properly.
