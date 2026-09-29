# Nomad Harness

Firewalled, scored, append-only event-prediction instrument, exposed as an MCP server.
Built to `nomad_harness_spec_v1.md`. Python 3.11+, `mcp` (FastMCP, pinned `<2`), `pydantic` v2, stdlib `sqlite3`.

## Install and run

```bash
uv sync
uv run pytest
uv run nomad-harness init            # creates nomad_harness.db, loads harness/seed/seed_v1.json, verifies the chain
uv run nomad-harness serve           # stdio MCP server (what .mcp.json launches)
uv run nomad-harness serve --http    # streamable HTTP on 127.0.0.1:8765 (for claude.ai later)
uv run nomad-harness verify          # walk the hash chains
uv run nomad-harness status          # row counts, round states, programme stats
```

DB path: `$NOMAD_HARNESS_DB`, else `./nomad_harness.db`. `init` is idempotent; `init --seed <file>` loads another seed file.

## Claude Code wiring

- `.mcp.json` registers the server as `nomad` (project scope; approve it the first time Claude Code asks).
- `.claude/settings.json` installs a `PreToolUse` hook that denies `WebSearch`/`WebFetch` unless some round is `open`.
  It allows silently when the DB does not exist, and `NOMAD_HARNESS_HOOK_OFF=1` switches it off for non-round work.
- Both run `uv` from PATH with the project directory as cwd (Claude Code launches MCP servers and hooks there),
  so the same files work on Windows, Linux and macOS. The DB defaults to `./nomad_harness.db`.

## Round protocol (the firewall)

```
nomad_submit_event   (human; returns round_id + event_hash, never event_text)
nomad_reveal_event   (operator sees event_text + event_date only)
nomad_lock_predictions   created -> locked   (append-only, stamped; may be called again until open)
nomad_open_retrieval     locked  -> open     (only now may the operator search; returns the frozen list)
nomad_add_evidence       (open only; excerpt <= 500 chars; source_time / knowable_from)
nomad_predicate_check    (claims at lock time, observations at scoring time)
nomad_score_round        open -> scored      (one resolution per prediction; scorecard; library stats rebuilt)
nomad_export_round
nomad_void_round         any -> void (reason logged; 'contaminated' if the operator peeked)
```

Other surfaces: `nomad_library_*` (rules and compositions; proper-noun heuristic on rule text), `nomad_predicate_list`,
`nomad_t0_*`, `nomad_holder_upsert` / `nomad_resolve` / `nomad_orphans` (names book), `nomad_position_add` /
`nomad_positions_on_node` (pair gate), `nomad_hypothesis_*` / `nomad_hypotheses_due` (standing-hypothesis notebook),
`nomad_verify_chain`, `nomad_programme_stats`.

## Invariants, and how they are enforced

1. **Append-only.** `BEFORE UPDATE` / `BEFORE DELETE` triggers abort on every ledger table
   (events, rounds, round_transitions, predictions, evidence, resolutions, scorecards, predicate_checks,
   t0_candidates, aliases, orphans, positions, hypothesis_checks). Corrections are new rows with `supersedes`.
2. **Hash chain.** Per table, `row_hash = sha256(prev_row_hash || canonical_json(row))` in rowid order.
   `verify_chain` reports the first break with table and rowid.
3. **Firewall order.** A round cannot be opened without a locked prediction; evidence and scores are refused
   outside `open`; predictions are refused after `open`. Errors name the missing step.
4. **Bitemporal.** `recorded_at` is stamped by the harness and rejected from callers; evidence, aliases and
   positions carry `source_time` / `knowable_from`.
5. **No proper nouns in rules.** Capitalised tokens outside a function-word sentence start, minus an allowlist,
   reject the rule. Writing a rule in lower case always passes; nouns go in `provenance`.
6. **NULL_CALL_WEIGHT = 0.2** in `harness/config.py`, stored on every resolution and scorecard.

Design notes that go beyond the spec text:

- `rounds.state` holds only the initial state; the `round_state` view (latest `round_transitions` row) is truth.
  This keeps `rounds` append-only while the transitions table stays the source of record.
- `library_rules` status is derived on every rebuild: `validated` iff >= 2 clean hits in >= 2 distinct rounds with
  zero misses; retired stays retired. A part's miss sets `review_flag` on any composition containing it.
- Scorecard denominator excludes `untestable`; `unverified` stays in the denominator as a non-hit.
- `arming_claimed` / `arming_observed` and the programme arming rate refer to the tradability gate only
  (`config.TRADABILITY_GATE_KEYS`); `any_arming_*` report the other arming predicates.
- Hypothesis status is derived from the latest observation per predicate; falsified/expired/resolved are terminal,
  and a resolved hypothesis is continued by opening a successor with `supersedes`.

## Tightening pass (after round 4)

- **A1** `round_class` (learning|clean) and `contamination` (none|q2_fail|q2_unknown|peeked) live in the append-only
  `round_classifications` ledger; programme stats and rule validation run on clean rounds by default
  (`include_learning` for the second view). Rounds 1-4 are learning.
- **A2** The operator model comes from `NOMAD_OPERATOR_MODEL` (set in `.mcp.json`) and its cutoff from the
  human-maintained `model_cutoffs` table (`nomad-harness model-cutoff set <model> <date>`). Q2 is computed at intake.
- **A3** `nomad_event_window` returns `[cutoff + 1 day, today - 28 days]`; intake refuses events outside it unless
  `round_class='learning'` is passed.
- **A4** `falsifier_window` (scoring_window | days:N | until:date), required on null and predicate calls; the open-retrieval
  output carries each window's end date; late facts are recorded as `late_falsifier`, they do not fire.
- **A5/A12** `resolutions.quality` = round-class x scorer x coverage x call-type x evidence-class factors
  (`config.QUALITY_FACTORS`); rule `weight` = sum of hit quality minus sum of miss quality (misses carry coverage,
  evidence and call-type factors only); compositions are capped at their weakest part; hypotheses carry
  `support_weight = min(cited rule weights)` and arm only at or above `VALIDATION_THRESHOLD` (1.0). Validation needs
  weight >= threshold, hits in >= 2 distinct clean rounds, no undiscounted miss, >= 1 positive hit. Every narrowing
  decision is logged to `narrowing_log` with the weight it read.
- **A6** `source_coverage` (adequate|thin|english_only|none) required on miss/unverified; a hit cannot rest on `none`.
- **A7** First traversal takes two checks per round (`scope` event and node); intake takes `node_recent_incidents`.
- **A8** The hook denies WebSearch, WebFetch and every `mcp__*` tool except the servers in
  `config.HOOK_ALLOWED_MCP_SERVERS` unless a round is open, and logs denials to `hook_denials`.
- **A9** `nomad_criteria_supersede` corrects Q1-Q9 by a new `event_criteria` row.
- **A10** `nomad_hypothesis_schedule` sets `next_check_at`, `hard_stop_at`, cadence; `nomad_hypotheses_due` reports what is due.
- **A11** `nomad_export_round` carries the chain head of every ledger.
- Hash form v2 drops NULL columns so nullable columns can be added later; rows written before the pass verify under
  the original form. `nomad-harness migrate` applies the schema additions to an existing DB.

## Round-5 review (before round 6)

- **A13** A miss with `mechanism_outcome = right` is an operator misread: counted on the scorecard (`misreads`,
  `misread_frac`, programme `misreads_total`) and never debited to the rule, nor does it flag a composition. Mirror of
  quarantine (hit with mechanism wrong: no credit).
- **`call_type = map`** for identity claims: no mechanism, scored in the outcome ledger and `map_score`, excluded from
  `mechanism_score` and from rule weights. (SQLite cannot alter CHECK constraints; `init_schema` rebuilds the
  predictions table in rowid order when it finds the old constraint; the chain is unchanged.)
- **`basis`** is required on a predicate check whenever `claimed` is not `unknown`: a class prior is not an observation.
- **`nomad_add_evidence_batch`** validates every item then writes in one transaction; a bad item writes nothing.
- **`nomad_round_note`** appends free-text notes (kind `tide` for a macro backdrop that made legs unscoreable).
- **B2** `nomad_second_scorer_view` (calls and evidence only), `nomad_second_score` (own ledger `second_scores`),
  `nomad_score_disputes`; the human breaks ties with `nomad_resolution_supersede` (scorer `human`).
- **B4** `node_facts` ledger (`nomad_node_fact_add`, `nomad_node_facts`), `ingest_targets`
  (`nomad_ingest_target_add/targets/target_close`), and `nomad-harness ingest` which pulls the RSS/Atom feeds in
  `harness/ingest_sources.json` into `node_facts` (dedupe by url + node) and flags items that mention an open target.
  Run it daily; it never closes a target by itself. `nomad-harness facts` shows open targets and recent facts.

## v7 (before round 7): decomposition, reveal context, dispute-aware library, baskets

- **B1/B2 decompose or don't claim.** `lag_band` calls and any duration or extent claim need `factors[]` (factor, holder_id?, node?, estimate, carrier, falsifier, binding, against) with at least one `binding` and one `against`. Factors land in `prediction_factors`; at scoring each factor is resolved in `factor_outcomes` (`factor_resolutions` ledger) and the composite is **derived** (`max`/`min` over observed lag bands, `all` for extents; a binding factor left unverified makes the composite unverified). The operator's supplied outcome on a decomposed call is overridden and the note says so.
- **B3 touched set.** `nomad_touched_set` records holder x degree (0 site, 1 counterparties, 2 theirs, 3 sector) with node, position summary, substitutability, duration factor, carrier. Lock refuses without it unless `lock_note` starts `no-touched-set: <why>`.
- **B4 one claim per row.** Sign, map and null claims joining two falsifiable clauses (`;` or ` and `) are refused with "split it".
- **B5 reveal context.** `nomad_reveal_event` returns and logs (`reveal_context`) what the store already holds on the event's node: holders, parent/child neighbours with positions, node facts, rules matching node or kind. `nomad_node_context` reads the same before lock. Intake takes `node` and `event_kind`; a criteria fail is admitted but logged as an `intake` note.
- **C1 disputes suspend credit.** A resolution whose latest second score differs on outcome or mechanism, and that no human has ruled, is excluded from the library rebuild; `disputes_pending` shows on the scorecard, the rebuild, and programme stats. `criteria_pass` is a view filter (`nomad_programme_stats criteria_pass_only`).
- **C2/C3 blind view.** The second scorer sees cited rules' `rule_text` and `forbids`, the factors, and the reveal context; `mechanism_outcome` is defined as "did the cited rule operate". **C4** `nomad_scorer_bias` counts disagreement directions over clean rounds.
- **D1** hypotheses can be `spawned_from` a factor and inherit its evidence quality as support; factor holders and nodes unknown to the store go to the orphan queue. **D2** `nomad_shared_factors`, **D3** `position_id` on predicate checks with per-leg arming, **D4** `nomad_event_basket` (legs, signs, support, arming, correlation; never scored as a whole), **D5** armed legs in `nomad_t0_count`, **D6** the per-leg vs one-trade hypothesis is open in the notebook; each round records a `meta` one-trade call that is never armed.
- Not in v7: netting, sizing, promotion, mark-to-market, price feeds, alias matching, hypothesis scheduler, basket-as-a-whole scoring.

Round 7 (Sasolburg polyethylene fire) was the first round under this protocol: `docs/rounds/round7_recap.md`.

## v8 (before round 8): carriage, branches, carriers, synthetics, narrative

- **A1/A2 rules declare what they carry.** `library_rules.carries` is one or more of `occurrence | absence | ordering | magnitude | duration | map` (operator-layer rules carry nothing and cannot be cited). Lock derives each call's claim kind (`sign +/-` occurrence, `sign 0`/`null` absence, `magnitude_order` ordering or magnitude, `lag_band` duration, `map` map) and refuses a citation the rule does not carry. The rebuild applies the same test to old rows, so a citation outside carriage is not a trial of the rule; `meta` and `narrative` rows never are. The backfill table sits in `harness/library.py` for the human to ratify (`nomad_library_set_carries`).
- **B1 branches.** A map call with real uncertainty lists `branches[]`; downstream rows carry `conditional_on {prediction_ref, branch}` (`#i` inside the batch). At scoring the map call takes `branch_arose`; rows on other branches resolve untestable at weight 0 and never touch a rule. **B2** reveal returns `map_candidates` and `map_prior` (largest share) when several operators sit on the node.
- **C1** validation needs a qualifying positive hit: non-null call, mechanism right, adequate coverage, clean round. **C2** `nomad_scorer_bias` reports `lenient`, `under_informed`, `self_stricter`; only lenient counts toward the self-scoring discount.
- **D1/D2 carriers registry.** `carriers(name, kind, access)` seeded from seven rounds; `nomad_carrier_check` before lock, `carrier_status` on every locked call, `carrier_unreachable` flags in the lock result, Q7 computed and written as a criteria supersede when a majority of calls are unreachable or open. **D3** `node_facts` kind `scheduled`; reveal surfaces scheduled statements within seven days for the node, its holders and their neighbours.
- **E synthetic legs.** `synthetic_rules` (two pre-registered: opposing listed holders at degree <= 2; toll-booth and cargo legs) and `synthetic_legs`; `nomad_synthetic_build(round, node, rule)` constructs mechanically or says why not; support = min(component support) x `COMPONENT_DISCOUNT`^(n-1); the basket lists synthetics, per-leg predicate checks accept a synthetic id, the gate reads its listed components.
- **F narrative rows.** `call_type narrative` with `narrative_sign`, `position_id` and a channel carrier (never a price series); scored on whether the channel said it. Divergence from the leg's structural sign is derived in the basket and reported as a programme stat. Two notebook claims (E4 synthetics, F3 divergence) are open.

- **Rulings after v8 (human):** meta rows are ordering/magnitude claims (a "largest move is physical" row cannot credit an absence-only rule); the force-majeure rule stays at `[ordering]` and reads 0.0 untested, with the A3 sibling taking the occurrence evidence; every rule reports `trials_as_carried` and `weight_state` (untested as carried | netted to zero | tested) next to its weight.
- **B0 point-in-time fetcher.** `nomad_pit_fetch(source wayback|wikipedia, target, as_of, reason)` returns a page as it stood on a date; before lock the snapshot must predate the live round's event; every call is logged to `pit_fetches` and the snapshot date is the `knowable_from` for anything derived. **Carrier density at intake:** `node_kind` on submit runs `nomad_intake_check` (an event qualifies only if its node kind has open carriers), `rejections` are written into intake, and company IR pages, TCEQ emissions events, EIA, grid operators, USDA and delayed exchange prices are seeded as open carriers.

Round 8 (Sweeny refinery upset) was the first round under this protocol: `docs/rounds/round8_recap.md`.

## v9 (before round 9): scheduled facts, computed first traversal, tags and cap, fetch paths, arming categories

- **§0 ledger work.** The tide rule (`lib.tide_hides_event`, transmission, carries `absence`) got its key and its round 2/5/8 provenance; rounds 1-8 carry tags (1-4 `learning`, 5 `lag_test`, 6 `weather`, 7 `lag_test` with Q1b computed pass, 8 `weather` with Q1b computed fail from the January and 13 July Sweeny upsets, now `node_facts`); round 8's synthetic is the first `gate_pass_undated` row and its basket recomputes to zero divergent legs with the PSX revision shown as `revised_sign`.
- **§A scheduled facts get a feed.** `node_facts` kind `scheduled` gains `sched_kind` and `supersedes` (a moved date is a new row). Sources: EDGAR 8-K item 2.02 dates by filing date (needs `cik` on the holder, verified against EDGAR's own ticker list at load), the IR events page via the Wayback snapshot on or before `as_of` (needs `ir_url`), and `nomad_scheduled_add` as the manual fallback. `nomad_ingest_scheduled` appends new (holder, kind, date) triples with `knowable_from` = filing or snapshot date, never live pre-lock, and bounds EDGAR by `as_of` (the time wall). **A3** `nomad_catalyst_check` reads the store per leg (the leg's holder plus one hop in the names book; `event_date < date <= event_date + 28`), reports `holds_claimable` (knowable by the event date) against `holds_observed`, writes `predicate_checks` on a live round and only a dry-run report (`arming_status_if_dated`) on a scored one. Reveal now surfaces scheduled facts across the full scoring window with `knowable_by_event`. **A4** `nomad_scheduled_backfill` over rounds 5-8: 8 legs (all round 8) would have carried a date in hindsight, 0 knowable by the event date; forward coverage of the names book is 0% because the US IR event pages render their calendars with scripts and EDGAR dates results only at filing. Round 9 then showed the missing piece exactly: the results-date press release a week before the event.
- **§B node-level first traversal is computed.** `nomad_node_history(node, as_of)` reads prior rounds and disruption-kind `node_facts` on the node (token and alias match) plus open incident registries per node kind (TCEQ STEERS reader, live then Wayback, reporting `path_served`; port notices and grid logs arrive through the daily ingest). **Q1b** fails on any disruption in 90 days or three in twelve months; a human override needs a `basis`. **Q1a** is the human's, `pass|fail: <basis>` (a bare verdict is refused). **Tags** `lag_test | weather | late_headline | learning` are written to the append-only `round_tags` ledger at intake (`nomad-harness retag` for a human re-tag with `supersedes`). **Cap:** a `weather`/`late_headline` submission is refused with reason `cap` (and written to `event_rejections`) when the last three admitted rounds include one, unless `cap_override='<reason>'` (logged as a note). **Q9:** `nomad_selection_window` fixes source and start date, `nomad_reject_event` writes every skip with its failing question, and intake computes Q9 fail when a fixed window had more than one event and no rejection; three consecutive fails set `selector.suspended` until `nomad_selector_clear`. `nomad_intake_dry_run` shows all of it without writing.
- **§C synthetics and divergence.** `nomad_synthetic_build` is refused after lock and requires every component's touched-set row to cite `mechanism_ids` (basket support reads those first). The basket's structural sign is the **sign at lock** (positions recorded up to the first `locked` transition); later rows show as `revised_sign` with their `recorded_at`; divergence never reads a revision. A synthetic built after lock is flagged `built_after_lock`.
- **§D fetch paths and snapshots.** `carriers.fetch_paths` per path `live | wayback | pit_api` with `status` and `last_checked`; `nomad_carrier_path_set`, `nomad_carrier_probe` (tries both), reachability reads the best path before the nominal access (TCEQ: live blocked, Wayback ok; the P66 IR page probed live ok on 7 Sep). `nomad_pit_fetch(source='auto')` goes live only when the round is open and the registry does not mark the host blocked, else the nearest Wayback snapshot, and logs `path_served`. `nomad_snapshot` submits save-page-now and records a `node_facts` row of kind `snapshot`; `snapshot_targets` is seeded from every `ir_url` and every live-blocked carrier url; `nomad_snapshot_run` / `nomad-harness snapshot-run` paces requests (archive.org throttles bursts with 429).
- **§E arming categories.** Every leg carries `arming_status` in `armed_dated | gate_pass_undated | gate_fail | unchecked`, on the basket, the scorecard (`arming_status_counts`), `nomad_t0_count` and programme stats. `gate_pass_undated` is support-branch only; the branch is not built.
- **§F programme stats.** `tag` filter (the lag hypothesis reads `lag_test` only), `arming_by_tag` as three counts, `scheduled_facts_coverage`, `fetch_path_health`, and the E4/F3 notebook rows written per round to `notebook_rows` at scoring.
- Also: the basket's "positions recorded while the round was live" window is now bounded at scoring, so an old round never shows a later round's holders; `nomad-harness reclassify` is the human's append-only path to change a round's class.

Round 9 (Sauget trichlor fire) was the first round under this protocol: `docs/rounds/round9_recap.md`.

## v10 (before round 10): live rounds, enumeration, the risk engine, the effect grid and the mirror basket

The last protocol change before the freeze: after v10 the schema and round protocol are fixed for seven admitted rounds (`nomad-harness freeze` writes `freeze_started_at`, sets `clean_lag_days = 0` and `cap_lookback = 1`; store-side work continues).

- **§0.** Round 9 reclassified clean (both rows on the ledger); the Coast Guard dispute ruled unverified / thin by the human; harvested `lib.catalyst_not_about_node_is_tide` (sequence, carries occurrence and absence); the third scheduled-facts source backfilled on round 9's holders (report only).
- **§A live rounds.** The age rule leaves Q7: `nomad_event_window` is `[cutoff + 1, today]`. Every call carries `due_at` (required, at most 90 days after the event; narrative rows default to event + 5 and are scored first: a structural call on a leg is refused while the leg's narrative row is due and unscored). `nomad_score_call` scores one call once due (or `early=true` with a reason); `nomad_score_round` is the bulk form over the due batch; the round moves `open -> partially_scored -> scored`; `nomad_calls_due` lists what waits; `nomad_close_round` expires what is past due (unverified, or hit at thin coverage for absence claims). The blind view is per scoring session and holds only final resolutions; the second scorer scores the same batch. The meta one-trade row is retired.
- **§B.** Q5 is a size band (`underread | headline | trivia`; trivia is refused and written as a rejection; headline is a second tag next to the first-traversal tag). Cap: at most one weather/late_headline in any two consecutive admitted rounds. Required mix over the freeze (headline >= 4, lag_test >= 3 of seven) is a programme stat and intake warns when the remaining rounds cannot meet it.
- **§C enumeration (Q9).** A `feeds` registry (trade-press RSS, registries, GDELT DOC slice, the GlobeNewswire earnings wire; the human confirms the set once). `nomad_enumerate(feed_set, from, to)` writes dated, deduplicated candidates with an auto-drafted bare prompt, node and kind guess, computed Q1b/Q2/Q7, an outlet-class size hint and a Q1a basis from the same feeds over the prior 30 days. `nomad_select_next` presents the first undecided candidate; `nomad_decide` accepts (submits with the selection window recorded, Q9 pass) or rejects (`'Qn: why'`, written). A hand-supplied event fails Q9 under v10, and three consecutive fails still suspend the selector.
- **§D.** Third synthetic rule `syn.cross_node_event_pair` (listed + on one node against listed − on another; one extra `CROSS_NODE_DISCOUNT` step; `cross_node` on the leg and in E4's rows). `dry_run=true` computes a build on a scored round without writing.
- **§E.** Forward scheduled sources in order: results-date announcements (EDGAR full-text search over 8-K 7.01/8.01 with the document parsed for the announced date; wire RSS; manual), IR events pages via Wayback, EDGAR 2.02 flagged `hindsight` and never used to date a leg. **Catalyst-about-the-node:** the wide read is back (every degree-0/1 holder on the leg) and `nomad_catalyst_link(concerns_node, basis)` decides per fact whether it dates the leg or is a `tide_candidate`; mechanical dates (`nomad_mechanical_add`, kind `mechanical`) date a leg as ACKs do and the check records which.
- **§F.** Readers for Illinois EPA news and the NRC quarterly spreadsheet (openpyxl); live-then-Wayback helper for the 403 set; fetch-path health in programme stats.
- **§I risk engine v0.** `price_observations` (post-lock, after the leg's due date or while scoring; pre-registered 20-session two-sigma band from the closes passed; attributed observations need the citing evidence row). Re-encode per leg = first attributed out-of-band observation after the event within the leg's due date; residual state `recovered | unrecovered | no_residual` on every basket leg and in the notebook row; `nomad_exposure` sums sign × support over unrecovered legs per shared factor with the earliest forcing date. `risk_rules` registry seeded from nine rounds (tide, weather, recovered-before-entry, catalyst-about-node, slack, cut-into-glut, self-hedged owner); a rule is added only between rounds.
- **§J.** The grid: `EFFECT_KINDS = direction, volume, vol, timing`, degrees 0–3, `WINDOWS = event_day, days, weeks, to_due`, factor kinds equity, private, physical, aggregate. Frozen.
- **§K mirror basket.** At the first lock every natural leg × effect kind × window becomes a `grid_cells` row: covered by an active rule → `positive` with the rule id, else `mirror`; each operator call is stamped with its cell's `space` and `covering_rule_id` (frozen). `nomad_event_basket(space=positive|mirror|both)` lists cells with per-cell arming (gate from the recorded checks, listed options for vol cells, `uncovered` computed against the registry, `now_covered` disarming, dated by any scheduled or mechanical fact). A rule added later writes `coverage_migrations` and never rewrites the locked row. K5's per-round rows (re-encode rate per space) are written to the notebook; `nomad_mirror_dry_run` is the K6 worked check on a pre-v10 round.
- Tests: 13 new (112 total), covering §G 1–12.

Round 10 is the first round under this protocol and the first under the freeze.

## v11 (before round 11): one round type, replay, gates become tags, stratified enumeration, batch scoring

The round protocol stays frozen. What changes is who runs the measurement, what intake refuses, and how scoring is batched.

- **§0.** Round 10's slack predicate recorded `observed = fails` per leg (the filer states ~94% sole-supplier revenue); harvested `lib.repeat_filer_base_rate` (sequence, carries `map`); the OEM Q3 reporting dates entered as `mechanical` facts, which date 16 of round 10's mirror `vol` cells; the hGears candidate ratified as a `skip` rather than a manufactured Q9 failure.
- **§A one round type.** No separate measurement pipeline and no separate operator role: what differs between rounds is only what was knowable, and the ledger records that. **A1** a learning round's resolutions never enter rule weights, validation or calibration (this was *not* already true — see `RECONCILIATION.md`); its measurements do count. **A2** coverage is assigned point-in-time, from `risk_rules` knowable by the event date. **A3** on a learning round or a replay, legs are generated from the positions store (`nomad_generate_legs`, `leg_source = mechanical`), never operator-selected; refused on a clean round. **A4** a historical event is an ordinary learning round.
- **§B replay.** `nomad_replay` applies the measurement layer to already-locked legs — point-in-time cells, re-encode detection against dated observations, latency, residual state — writing `replay_measurements` (`replay = true`) and never a `resolutions` row. `nomad_replay_stats` returns the coverage-decay curve (mirror share by round), the latency distribution and K5's rates. All ten prior rounds are replayed on the live ledger.
- **§C gates become tags.** Only three gates refuse: **Q3** (not a price event; asked *and* detected from the prompt), **Q8** (clean prompt), **Q9** (a verifiable selection: the enumeration path, or a fixed window whose rejections are on the ledger; clean rounds only). First traversal, size band, shared-thing, carrier density and the weather/late-headline cap all become tags and warnings, filtered at analysis time. A round with one holder and no listed party is a legitimate null generator.
- **§D stratified enumeration.** `feeds.stratum` plus a pre-registered `STRATUM_QUOTA` per rolling ten admitted rounds; `nomad_select_next` draws by largest quota shortfall first, then by date inside the stratum, so extra volume does not inherit one feed's bias. `nomad_strata` shows counts, quota and draw order.
- **§E batch scoring.** `nomad_calls_due` is the primary loop; `nomad_score_batch` scores across every open round in one call, `nomad_second_scorer_batch` regenerates one blind view over every call awaiting a second score, and `nomad_disputes` attaches disputes to calls rather than rounds. `nomad_calibration` reports the operator's hit rate by call type, absence vs occurrence, and by space, over clean rounds only.
- **§F** `RECONCILIATION.md`: every pre-registered constant, the carriage table, the risk-rules seed and the effect grid, with the nine places the build and the briefs disagree.
- Also: the firewall now denies retrieval while **any** round is pre-lock (`created` or `locked`) rather than requiring one to be `open`, which is what concurrent rounds need. Tests: 7 new (119 total).

Round 11 (UPM/Sappi Statement of Objections) is the first round under this protocol: `docs/rounds/round11_recap.md`.

## v12 (before round 12): real bands, practice dating, implied at lock, participant classes, base rates

The round protocol stays frozen. v12 is mostly a correction pass: three of the programme's headline numbers were measuring the harness rather than the world.

- **§0 corrections.** **0.1** `harness/prices.py` is a real daily-close carrier (chart API, exchange-suffix map), so the pre-registered 20-session band can actually be computed: price observations went 12 -> 1,017 and legs with a computable band 12 -> 40. **0.2** the seeded risk rules are ordinary practice long predating the programme, so they are dated to a `1900-01-01` sentinel with `origin in {practice, programme}`; the coverage-decay curve flattens to 0.50-0.56 across every round, because the "decay" was a record of when the rules became explicit to us. **0.3** the tradability gate is computed per leg when no check exists (`predicates.computed_gate`, `gate_source: checked|computed`), so no leg is silently `unchecked`. **0.4** `nomad_open_scoring` / `nomad_close_scoring` / `nomad_firewall_violation`: retrieval on a partially scored round is permitted only inside a scoring session naming its calls. **0.5** `STRATUM_QUOTA` retuned to sum <= 10; the `round_class` quality factor removed as dead code.
- **§D implied at lock.** `implied_at_lock {method: option_implied|realised_since_event|none, value, source, as_of, basis}` is required on `sign` and `magnitude_order` calls on a listed leg; executability is derived (`fadeable_null` where an absence call faces implied materially above zero, `exceeds_implied` where an occurrence call's stated move beats it, else `no`).
- **§E participant classes.** Eight classes with a pre-registered adjacency matrix; `carriers.participant_class`; `nomad_annotate_leg` records `fact_holder_class`, `price_setter_class` and an optional named `channel_between`, and derives `class_distance` and `class_divergence`.
- **§F institutional base rates.** `base_rates(class, condition, n, k, rate, source, knowable_from)`, seven seeded; a `sign +` call about institutional behaviour must cite a `base_rate_id` or write `no-base-rate: <why>` in the claim.
- **§G materiality in selection.** `enumeration_candidates.materiality_hint` and `materiality_basis`, reported by `nomad_select_next`, never a gate.
- **§H A/B.** `baselines/v11.json` freezes every programme number as of v11; `nomad_replay --stack v11|v12` keeps both comparable. Diff in `docs/rounds/round12_recap.md`.
- **Enumeration, made able to reach a window.** Every RSS feed is rolling (the six trade-press feeds together reached five days) and GDELT answers HTTP 429 from here, so the enumeration path could not see any event older than about a week. `feed.news_windowed` is a date-windowed search feed; `pull_window_daily` walks a window a day at a time, because the endpoint truncates a week-wide request to its last days and drops its date operators on a long query. The window that returned nothing now returns 345 dated candidates.
- Also: `evidence.carrier`, resolved at write time from the host then the headline (of 91 evidence rows on rounds 1-11, six resolved to a registered carrier, which is why §E6's class test had no left-hand side); voided rounds no longer counted in `coverage_decay`. Tests: 8 new (127 total).

Round 12 (Codelco's El Teniente collapse) was submitted a year out, voided as contaminated when retrieval showed the true date, and replayed at it: `docs/rounds/round12_recap.md`.

## v13 (before round 13): surviving risk replaces the mirror basket

This version breaks the freeze deliberately. K5 was unscorable: mirror share turned out to be a geometric constant (0.50-0.56 on every round regardless of the event) and one side of the comparison was mostly empty cells. The freeze restarts at v13 with four admitted rounds still owed.

- **A1 the mirror is retired as a generator.** Cell enumeration no longer produces legs; `predictions.space` stays on old rows for history and is not written again. What is kept: `pred.arm.uncovered` as a filter on structurally generated legs, and the effect kinds as a **template** over legs that already exist -- every leg carries a direction claim and a vol/volume/timing claim, or a stated `no-claim:` reason for the slot it leaves empty, with the touched set's equal-analysis discipline.
- **A2 the test that replaces it: does any risk survive this leg?** The silence rules run as **eliminators** rather than as predictions (`harness/surviving.py`): tide, traversed, weather, slack, self-hedged, immaterial-position, no-path. A leg no risk survives is a non-position, not a safe position, and the two were indistinguishable in the ledger.
- **A3 preconditions are declared with the rule** (`risk_rules.precondition`) and evaluated per leg. A rule does not cover every leg; it covers the legs its precondition is true on.
- **A4 surviving risk is a magnitude**, recorded per leg with the eliminators fired, the eliminators checked, **the eliminators that could not be evaluated at all**, and the basis. A leg that survives only because nothing could be checked says so.
- **A5 nulls are re-read.** `null_breakdown ∈ {eliminated, surviving, unassessed}`: an absence call on a leg where an eliminator fired is a non-position, not a win. **A6** `arming_status` gains `eliminated`, reported separately from `gate_fail`; `uncovered` becomes an independent field.
- **B1 empirical bands.** The 2-sigma parametric band was breached on 23 of 62 sessions on a thin listing: mis-specified, not mis-calibrated. The band is now the 5th-95th percentile of 60 trailing daily returns, plus a turnover floor (median daily turnover under $2m USD) below which observations are written `band_reliable = false` and excluded from re-encode counts, never deleted.
- **B2 Q2 is re-computed at `open_retrieval`** against the date retrieval established, with an automatic void on a fail; scoring is refused until it has happened. **B3** Q1b returns `unknown` where no registry covers the node kind. **B4** the conjunction check catches an absence claim carrying its own conditional. **B5** `feeds.reach_days` measured at enumeration, with a warning when the set cannot span the window. **B6** Q1a's denominator comes from the stored candidate list.
- **C the retrospective**, run over all 195 legs of rounds 1-12: check 1 passed (the programme's one re-encode carries surviving risk), **check 2 failed** (no absence call in the programme sits on an eliminated leg, and 29 of 39 are not attached to a leg at all). Read `docs/rounds/round13_recap.md` before building further on §A.
- Added after §C: `leg_claims.impact_pct`, the operator's own estimate of what the event is worth on a leg, stated at lock. Without it the tide eliminator had no numerator on 110 of 195 legs. Tests: 11 new (138 total).

Round 13 (the ITC's exclusion order against IRICO glass) is the first round under this protocol: `docs/rounds/round13_recap.md`.

## v14 (before round 14): generate wide, eliminate with anchors, diagnose what survives

The arming conjunction is retired. Thirteen rounds and zero armed legs did not discover that arming is hard: an AND over eight predicates specified it to be near-impossible and then measured that it was. And because arming commits no capital, every predicate cost information and bought nothing -- a filter never violated is a filter never tested.

- **A1/A2 permissive generation** (`harness/generate.py`): at lock, every holder with a position on the event's nodes at every degree the store reaches, plus everything one hop out (parent, child, same-node counterparty, chain-adjacent), plus anything a hunch proposes. An analogy may **propose** a leg and may never support one; only anchors and fetched facts keep it there, so a wrong analogy costs an eliminated leg rather than a scored miss. `generation_width` is reported per round.
- **A3 anchors as eliminators** over the whole space, with the v13 leg-level preconditions. **Unevaluable is a value, not a verdict**: an anchor with no data neither passes nor fails the leg, it discounts confidence, and the unevaluable rate is reported per anchor. The whole generated space is stored with its elimination reasons, because a leg killed by a constraint and a leg never generated look identical in a ledger that keeps only survivors.
- **A4 the risk vector** (`harness/vector.py`), kept as a vector and never multiplied: `stake` (impact over the leg's own band), `structural` (path, evidence class, rule weight), `pricedness` (first traversal, traversal state, slack, re-encode latency, class identity), `operator`, `expression` (instrument, band reliability, turnover, dating). `binding_term` is the output, with the distance from a pre-registered appetite block. Five terms at 0.6 and one at 0.03 with four at 0.95 have the same product and are opposite situations.
- **A5 operator risk is computed** from clean resolutions and never asserted, with modifiers the ledger has shown to matter (settling document fetched, base rate cited, claim is a conjunction, degree).
- **A6 a glossary and an index, not a map** (`harness/glossary.py`): the callable surface stated plainly, an index over the store, `nomad_precedent` (precedent, never endorsement), and `nomad_adjacent` returning neighbours and hop costs with **no ranking and no recommendation**. Every move is logged with the operator's stated reason. **A7** nothing is gated on the vector.
- **§C round-13 fixes.** Materiality is a number at selection; bands are computed at lock from pre-event closes (which is what makes `stake` evaluable at lock); map calls name and attempt their settling document; a call on a leg with no admissible path is refused; an ordering call over unattributed noise resolves `untestable`; Q9 returns `unknown` without a window on the ledger; a regulatory and an outage feed join the enumeration; short feed reach and malformed registry writes raise at the point of use.
- **§B the wall map**, over all 225 legs of rounds 1-13: `structural` binds on 114 and `expression` on 96, while **`stake` could not be computed on 217 of 225 legs** and `operator` on 201. Not one leg in the programme's history clears appetite on every computable term. Read `docs/rounds/round14_recap.md` before starting v15. Tests: 9 new (147 total).

Round 14 (PT Smelting's Gresik outage) is the first round under this protocol: `docs/rounds/round14_recap.md`.

# v15 -- the effect, not the leg, is the unit

A leg carries one sign and the world does not. A concentrate buyer facing an outage has higher input cost **and** volume
shortfall **and** a delivery obligation **and**, if diversified, better pricing on its own competing output -- four
effects, different magnitudes, different timings, different carriers, some opposed. And a round is a snapshot when it
should be a walk: the facts that generate *direction* do not exist at lock, which is 0/14 in one sentence. Those are
the same object, because an effect is what makes the next holder reachable.

- **§0b five silent-failure defects, fixed first.** The re-encode lookup could throw and leave `pricedness` at a
  passing value, which is the one wall the vector exists to fire; an unresolvable rule citation dropped out of the
  structural computation for free; `second_scorer_batch` dropped rounds in silence while reporting success; the blind
  view omitted unresolvable rules, reintroducing the dispute class v7 §C2 closed; and **`binding_term` ranked over the
  terms that happened to be computable**, which is what produced v14 §B's headline. All five now record rather than
  swallow. **Re-running the wall map: `structural` binds on 0 legs, `unassessable` on 53.8%, `expression` on 43.8%.**
  Of the unassessable, 123 of 135 are legs v14 attributed to `structural`. See `docs/rounds/round15_recap.md` §0b.
- **§A the effect DAG** (`harness/effects.py`). `effects` replaces the leg as the unit: an effect **is** a claim, with
  its own carrier, falsifier, due date and magnitude, so a holder with five effects has five chances to be wrong.
  **No sign field anywhere** -- net direction is derived late, over a stated holding window. Composition through a
  relation is a mapping and not a sign flip, and **most entries in the transform table are "does not transmit"**;
  attenuation is per hop with no depth limit; re-rooting is **refused** without an independently carried document, and
  `root_depth` is reported so a machine for justifying distance would show immediately. Rounds 1-14 migrate to
  depth-1 `direction` effects (274 of them) and the old columns stay for history.
- **§B the ACK graph** (`harness/acks.py`), built standing per node **before any event**. `scheduled` carries a date;
  **`forced` carries the obligation that generates it and is refused a date**, because a walk advancing only on
  calendared facts advances only where the market is already looking. A fired ACK **must deliver a fact**: "the date
  passed and nothing was said" is an absence fact that prunes.
- **§C the walk** (`harness/walk.py`). The operator walks and the harness records; **the calendar chooses the branch**,
  and advancing on an unfired ACK is refused by name. Successors are named **at firing**. Segments lock with lineage
  and nothing is rewritten.
- **§D contradictions are edge hypotheses** (`harness/contradiction.py`): computable from the DAG, dated by the ACK
  they sit on, with the common set returned to the eliminators as anchor-grade. Exit is the first **attention** ACK
  after the structural one.
- **§E convergence** measured, not scheduled, and pruning refuses divergent branches by name. `divergence_held`
  distinguishes `converged_to_price` from `unreadable`: an unmeasured frontier is not a converged one.
- **§F support** with and without the independence discount, **both rankings written every round**; the implicit
  position needs support **and** stake, and support without stake returns `inert`.
- **§G bridges fall out of the DAG** -- an effect path is a position when a descendant clears expression and an
  ancestor has stake. No bridge object, no hop limit, no loosening. **Empty is a valid answer and is reported.**
- **§H basket totality**: the synthetic exposure is declared at construction, typed as a floor, and
  `basket_stake = intended residual / declared exposure`.
- **§I the factor graph**: `node_kind` and `transmits` on the edge. Attribute nodes never propose an effect and are
  **always summed**, never traversed -- which caught the v14 generator turning a shared listing venue into a leg.

Tests: 22 new (169 total). Round 15 (a Google Cloud us-west1 region outage) is the first round under this protocol:
`docs/rounds/round15_recap.md`.

## Seed data

`harness/seed/seed_v4.json` (the default) is the v4 content: 14 predicates (7 arming, 5 disarming, exit, catalyst),
the 32-entry §3.4 library including two compositions, 25 holders with 61 aliases, 26 position rows, rounds 1-3
played through the live API as `retro=true` (19 calls, 10 evidence rows, 8 predicate checks), three standing
hypotheses and three T0 candidates. Its string ids (`lib.*`, `pred.*`, `holder.*`) are stored as `key` and can be
cited anywhere an id is accepted: `mechanism_ids`, `predicate_id`, `holder_id`, `composed_of`.
The reference documents are in `docs/`.

Loading notes: `sign_of_exposure = "both"` becomes two rows and reads as self-hedged; criteria values that do not
start with pass/fail/unknown are stored as `unknown: <text>`; the harness re-derives quarantine and weights and
the load warns if they disagree with the seed (they do not). After the load `lib.route_closure` is `validated`
under the pre-registered rule (clean hits in rounds 1 and 3, no misses); everything else is `candidate`.

`seed_v1.json` is the earlier spec-only seed and `seed_v4_template.json` the nested layout; both still load with
`nomad-harness init --seed <file>`.
