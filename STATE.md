# STATE — Nomad v16, as built here

*Kept beside the spec, per spec v16 §0: gaps between spec and build are recorded here, dated,
and the spec is never rewritten to match the code. Spec: `docs/nomad_system_spec_v16_final.md`
(Section E of `docs/nomad_the_system_as_it_stands.md` is the same text).*

## 2026-09-29 — first build

### Build path: the §30.3 fallback, not evolution in place

Spec §30 evolves the v15 harness in place (`Documents/nomad` on Rob's machine, 146 MCP tools,
15 rounds of stores). **That harness is not in this repository and was not reachable from the
build session.** On the user's instruction, v16 was built fresh here as the package `nomad16/`
(spec §30.3). The limit that forced it: the code and stores to evolve were absent.

Consequences, stated so nobody reads more into this build than it holds:

| Spec item | Status here | Why |
|---|---|---|
| §30.2 step 1 (freeze v15, verify its chain) | not applicable | no v15 stores |
| Migration report (§30.1), absence record recomputed over rounds 1–15 | not run | no v15 record. `absence_record` computes both rules for v16 rounds |
| Wall-map re-run (smoke 3), K7, K8, K9 rebuild, K10, K11, K12 look-backs | **cannot run** | every one reads the v15 record |
| Templates, vocabularies, bounds "authored from rounds 1–7 only" (§31 guards) | not satisfiable | authored by the builder from general knowledge and statute text before any v16 event was enumerated (`config/seed.json`, committed before enumeration) |
| `library_as_of`, tide-counted support, `weight_state` | table and reader built; every rule reads `untested_as_carried` with 0 trials | no resolutions banked yet; `rebuild_library_stats` equivalent not written |
| Second scorer, disputes, scorer bias | not built | |
| Operator term (fallback hierarchy, §8) | always the typed gap `not_covered` | no clean resolutions for any operator model yet |

### The tool surface is a CLI, not an MCP server

`python -m nomad16 <tool> '<json>'` with the spec's tool names minus the `nomad_` prefix
(`python -m nomad16 help` lists them). The operator runtime is agnostic either way (§28); a
FastMCP wrapper is a thin later addition. Every response carries `harness_version`,
`logic_version`, `config_hash` and chain heads (§17).

### The hook

`firewall/guard16.py` replaces `firewall/guard.py` as the PreToolUse hook (`.claude/settings.json`).
It reads `state/phase.json`, which the harness rewrites on every round transition:

- **closed** (`admitted`, `pre_lock`, `walking`): WebSearch, WebFetch and MCP tools are denied. Bash may
  make a single `python -m nomad16 …` call (the harness bounds every read by the clock); any other egress
  is denied. Paths holding post-cutoff material from earlier work are quarantined (blind runs, fetched
  filings, the NRC page cache, record files, `.git`).
- **open** (`live`, `scored`): live retrieval allowed.
- **idle**: the old blind-run guard applies unchanged.

`operator_manifest` sets `hook_verified` from the guard's own log (a denied WebSearch/WebFetch after
reveal), never from the operator's say-so. **Known blind spot, stated rather than relied on:** a Python
*file* the operator writes and runs can reach the network without the guard seeing a URL. The harness's
own fetchers are bounded; a script that bypasses them is a firewall violation by procedure, not by
structure.

### Appetite: provisional, so every round is `learning`

`config/appetite.json` holds 69 values: 18 ratified or carried, and **51
`provisional_unratified`**, set by the builder on the user's instruction (2026-09-29) so a round can run
end to end. The loader still refuses any missing value. **Any round that reads a provisional value is
classed `learning`** (recorded per segment in `round_meta`) and never counts toward K9 or K13. Rob
ratifies by flipping a status to `ratified` in a dated commit. The decision-model and data-product
values of §33.2 are deliberately left unset.

### Tracks not built

- **T2, decision models:** no `decider`, no Laya, no wiring, spread probes, locator, notice watch or
  procedural chains. Attention order is the operator's. Forced-ACK windows come from a statute bound or
  the `DUE_AT_MAX_DAYS` cap, never from a docket count.
- **T1, data product:** in-harness adapters stand in for it and map `knowable_at → knowable_from`
  directly: NRC event notifications and daily reactor status, EDGAR (filing-date ceiling applied in memory
  before anything is saved or printed), Wayback (latest capture at or before `as_of`), Yahoo prices
  through the vintage store, and the alternative-data adapters below. `RECORDING` is missing, so
  enumeration is `source_mode = manual`. `REVISION_CHAINS` is missing, so PortWatch and USGS values are
  flagged as restatable.

### Alternative data (added 2026-09-29 at the user's request)

`nomad16/altdata.py`, via `alt_probe` and `alt_fetch`. Every source gets a stated `knowable_from` rule
(lags are appetite `ALT_LATENCY`), a discriminating probe that must pass before use, and an in-memory
re-check of every record against the bound. Server-side date filters are never trusted.

| Source | Probe 2026-09-29 | Notes |
|---|---|---|
| `s2_scenes`, `s2_image` (Sentinel-2 L2A via Planetary Computer) | PASS | knowable from the product's processing time + 6 h. Crops render server-side to PNG, which the operator reads as an image; a crude bright-object count (ships on water, flares) is attached and may **propose, never support** |
| `portwatch_chokepoint`, `portwatch_port` (IMF PortWatch, AIS-derived daily transits and port calls by vessel type) | PASS | record date + 9 days (weekly publication) |
| `gdelt_events` (GDELT 2.0 15-minute exports) | PASS | knowable at the export's timestamp; counts by CAMEO root and mean Goldstein |
| `ioda` (internet-outage signals by country) | PASS | sample time + 1 h |
| `usgs_quakes` | PASS | origin + 1 h; magnitudes revisable |
| `firms` (NASA active fires) | NOT_COVERED | adapter built; needs `FIRMS_MAP_KEY` (free) as an environment secret |
| `gfw` (vessel presence), `acled` (conflict events), `black_marble` (night lights) | NOT_COVERED | need `GFW_TOKEN` / `ACLED_KEY`+`ACLED_EMAIL` / `EARTHDATA_TOKEN`, and an adapter |

Not yet added: Sentinel-1 radar rendering (sees through cloud and at night; the obvious next source for
straits), OpenSky flight history (needs an account; its anonymous API is live-only, so it can't serve a
backfilled round).

### Interpretations the spec leaves open (each is a build choice, not a claim)

- **Segment 0's clock is `event_date`** (a date). Documents with `knowable_from` on or before it are legal;
  prices use sessions strictly before it; the backfilled fill is the first close after the event's
  public `knowable_from`, and the next session when only a date is known.
- **Units.** S(ω) is the expected move divided by the tide-hedged residual σ at the horizon (√h scaling).
  A loading is the response to a one-sd daily story move in σ units. The hedge constraint uses the
  spec's form with `HEDGE_EPS = 0.002` (story exposure at most 0.2% of gross notional per sd).
- **Flat outcome:** every instrument's expected move is inside its own hedged-residual band. **Visibility:**
  |S⊥| against `VIS_K` × the median per-instrument band in σ units.
- **Horizon:** business days from the clock to the ACK window's end, capped at 63.
- **Instruments:** stocks and ETFs (stress-capped under a stop at the stress quantile) and bought calls
  and puts (hard-capped, always `modelled` with Black-Scholes on realised vol). Not built: debit spreads as
  packages, condors, credit spreads, event contracts, credit protection, and the sell-premium shape (it
  needs a quoted distribution).
- **Paper split:** narrowing and timing are zero (no quoted distribution, no quoted options). Leaks are
  hedge slippage: Σ weights × loadings × realised factor moves.
- `absorbed_by_slack` and `no_sink` each fire only on a stated fact for the effect kind (open call §34).

### Test status

`python -m pytest nomad16/tests -q`: 40 passed. Covered: smoke 1, 2, 5, 6, 7, 8, 10, 15–29, chain
tamper, loader refusal, construction building a structural pair, the paper round trip, and the guard.
Not covered: 3, 4, 9, 11–14 (v15 record, decider, data product).

## 2026-09-29 — round R16-001 admitted

- **Selection.** Fixed feed `nrc_en_power_reactor` (the NRC daily Event Notification Reports, power
  reactors only), window 2026-07-01 → 2026-07-31, after the operator cutoff 2026-06-30, read in date order.
  The feed and window were fixed and the seed library committed (3219c25) before enumeration.
- **Two enumeration defects, both on the ledger (`notes`, subject `enumeration_defect`).** Run 1 parsed
  unit-table cells as event titles, so nothing read as disruptive and the whole month was enumerated.
  Run 2's title test stopped on a loss-of-communication report. Run 3 reads the unit table. The stop rule
  only decides where the harness stops presenting items; the human decided every item in date order.
- **Decisions (the user, in the build session):** item 1, South Texas loss of communication capability
  (2026-07-01), rejected as Q5 trivia. Item 2, Fermi 2 automatic reactor scram (2026-07-03), confirmed on
  Q3, Q4, Q6 and Q8, size band underread. Q1a pass; Q1b fail (a manual scram on 2026-05-19), so tagged
  `weather`; Q2 pass; Q9 pass. Class `learning` (provisional appetite).
- **Clock and knowable_from.** Segment 0's clock is the event date, 2026-07-03. The event became public
  in NRC's report dated 2026-07-06, which is after the clock, so the operator gets only the Q8 line
  pre-lock.
- **What the ledger carries that the operator must not read.** Enumeration run 1 wrote July items dated
  after the clock, and the candidate rows hold the Fermi report text. Ledger rows can't be removed. The
  guard quarantines direct reads of `state/nomad16.db` pre-lock, and no harness tool exposes
  `intake_candidates`. A script the operator writes could still open the database; that is a violation
  by procedure, not a structural block.
- **The builder is not the operator.** This build session has read the item text and saw July's item
  titles in enumeration run 1. It plays no part in the round; it writes the phase file outside its own
  working tree so its tools stay usable, and the operator's clone carries the closed phase from git.

## 2026-09-29 — R16-001 played; v15 record imported

### R16-001 (Fermi 2 automatic scram, 2026-07-03), cold operator session

- **Played end to end** by a fresh operator session (claude-opus-5-5, declared cutoff 2026-06-30, hook
  verified from the guard log). Blind pass committed before any fetch. Two segments locked:
  seg 0 (clock 2026-07-03) `fdbf68d4…`; seg 1 (clock 2026-07-12, opened by the restart ACK firing
  `restart_lt_2w`) `9c7359af…`. **Both replay to their lock hashes** (manifests pin stores, vintages
  and, back-filled from git, the appetite file each lock read, whose hash equals the recorded one).
- **Derived ACKs:** 5 forced, 3 switch. Ratified: restart status, current report (switch), replacement
  procurement. The written event report was dropped because its carrier (the regulator's document system)
  is `not_covered`.
- **Calls:** 8. Six resolved, all hit: 3 on carriers that spoke, 3 absence calls on carriers read
  silent in full. The absence record is 2/2 under both the v16 and v15 rules. Two map calls on the
  replacement-procurement ACK stay open until their cap window closes on 2026-10-01; `close_round` after
  that date scores the round.
- **Baskets: all four `unbuildable: shape_mixed`.** Every priced effect on the listed parents (DTE, CMS)
  was vetoed `below_band`: a restart inside two weeks costs the listed parent about 0.01% and a long
  outage about 0.4%, against a hedged-residual band near 8%. No listed holder on the node carries stake
  above noise. That is the structural answer, not a construction failure. No paper positions.
- **Pianos:** 4 story-correlation rises with no shared constrained node, logged and not modelled.
- **A disclosed leak in segment 1.** After `walk_scan` hit the delivery on 07-12, the operator made
  further reads through 07-15, which the harness then allowed. It fired at the true delivery date and
  authored nothing from the later reads. Segment 1's calls are flagged as exposed. **Fixed after the
  round:** an unresolved `walk_scan` hit now pins the frontier until the ACK fires or the date is recorded
  as not delivering (test `test_walk_hit_holds_the_frontier`).
- **Operator friction, and what changed:** the commit-trailer URL was refused by the guard (fixed: plain
  `git commit/add/push` parts pass). A transform gap (`ownership: availability → obligation`) is left
  unfilled: filling it is library authorship, owed from rounds 1–7 authoring (K10). Hop discounts that
  stop the grid-price and insurer chains: v15's ratified discounts are now carried (below). Story classes
  set by rank: with two listed instruments in reach, three stories were classed synthetic by arithmetic.
  That is a real limit of construction on thin nodes, recorded rather than patched.

### v15 imported (the user uploaded `nomad.zip`, Rob's `Documents/nomad`, v15 head 2dd1507)

- Frozen, untouched, under `v15/`: code, database, docs, tests, and the git history as a bundle, with
  `v15/MANIFEST.json` (sha256 per file and of the zip). **v15's chain verifies with v15's own
  `verify_chain`: ok on all 48 ledger tables, no break.** This is §30.2 step 1.
- The user chose to keep the v16 build and import v15 into it, not to evolve v15 in place. The fresh build
  stands; v15 is the reference and the look-back source.
- **Carried config (§33.1):** `HOP_DISCOUNT` (15 relations) and the 28-entry `TRANSFORM_SEED` are now
  `carried`. The builder's entries for relations and kinds v15 lacks stay provisional
  (`HOP_DISCOUNT_BUILDER`, the per-row `transforms.basis`). v15's `timing` and `direction` effect kinds were
  added. `DEFAULT_HOP_DISCOUNT` 0.5 is confirmed as v15's value and is still "to ratify".
- **Quarantine:** `v15/` and `lookbacks/` hold material dated after July 2026, and are quarantined from
  operators pre-lock.

### K8 — unreadable under its guards (`lookbacks/K8_result.md`)

Pre-registered before any number was computed (`lookbacks/K8_prereg.md`). Under the guards, 2 nodes
qualify, which is unreadable. The v15 record can't carry K8: **141 of 200 positions have no
`knowable_from`**, rounds 1–6 carry no node link, and v15's stake term is blank on almost every leg. A
labelled post-hoc sensitivity with the time-wall guard dropped reads 9/11 nodes with a listed hedge (both
sides or options), 6/11 with both sides. That is indicative only, and exactly what the guard exists to
prevent concluding. Making K8 readable needs a blind back-fill of `knowable_from` on v15 positions.

### Still owed on the v15 record

- **K10:** templates, vocabularies and bounds authored **from rounds 1–7 only**, by an author who hasn't
  seen rounds 8–15. This build session has seen the titles of rounds 8–15, so the authoring should be a
  cold session given only the rounds 1–7 materials.
- **K11, K12:** mechanical on v15 narrative rows plus prices, once the story-to-proxy mapping rule is
  written down before any ρ is computed.
- **K9:** a rebuild of rounds 5–15 by cold operator sessions, one per round. Their events (2026-07-14 →
  2026-09-07) are after this environment's declared cutoff (2026-06-30), so the time-wall guard is
  satisfiable. The cost is one operator session per round (R16-001 used about $13).

### From the operator's closing notes (fixed after the round)

- **Junction confirmation on short data.** The first `junction_confirm` ran on story proxies whose vintages
  stopped five sessions after the trigger, and logged two pianos. The operator re-ran it on refreshed
  vintages, and both runs stay on the ledger; read the second. `junction_confirm` now refuses unless
  `JUNCTION_WINDOW` sessions exist on both sides of the trigger. Constructed stories are still not tested
  by it (estimated proxies only).
- **One map call per ACK.** The replacement-cost ACK's vocabulary was registered as a map call in both
  segments (C002, C008: the same claim). `thesis_set` now registers one per ACK across the walk. Score
  R16-001's C002 and C008 as one observation.
- **Harness version drift, disclosed.** R16-001's round row records harness `ad0779d5…` (at admission);
  the operator's calls ran on `ab6b3fde…`. The builder changed the harness between admission and the
  push that the operator cloned (it added `walk_scan` and hardened the guard). Nothing changed while the
  operator was playing, and the operator made no edits under `nomad16/`. Future rounds should be admitted
  on the exact commit the operator will clone.
- **A domain caveat worth carrying:** DTE's Q2 release records a regulator's disallowance of previously
  recorded power-supply costs. The pass-through premise (positions P00010, P00019) isn't unconditional.

### K11 and K12 (`lookbacks/K11_K12_result.md`)

Pre-registered and pushed (6110244) before any price was fetched. **K11 dies:** units whose tide-hedged
residual later left its band did not carry higher ρ at lock (pooled MWU p = 0.65, 8 left vs 79 stayed,
medians 0.92 vs 0.95). Per §31, the priced test (`RHO_MIN`) is dropped from construction in favour of the
visibility test. That is a construction change for Rob to ratify, and it hasn't been applied. Caveats:
only 9% of units left a 90% band (about the noise rate), and H held at most one story per round. **K12 is
unreadable on v15:** one narrative story per round, no paths. It accumulates from v16 rounds.
`prices.frame` no longer crashes on an empty vintage.

### K10 — dies (`lookbacks/K10_result.md`)

Pre-registered (`73fc53c`) before any template was authored or notice enumerated. **0 of 6 forced notices
that arrived in rounds 8–15 were derivable at lock, under the guards and under the all-relaxations upper
bound** (X₁₀ = 0.5). The zero is structural: **all 16 templates test at least one attribute no v15 position
row ever holds** (15 such attributes; `operating_status` in 11 templates, `contract_type` in 6), and only 22
of v15's 200 positions are both `stated` and stamped with a `knowable_from`. So `forced` was unreachable
from the v15 store for any denominator. Per §31: emergence is limited by the stores; invest in positions
before construction. The attribute list in `k10_coverage.json` is the fetch list, in order.

- **Not a claim about what a census could reach.** v15 never recorded these attributes. It's a floor for
  the stores as they were.
- **The decision point is not formally met.** It needs K8 and K10 both dead; K8 is `unreadable`. They fail
  for the same reason, and the call is Rob's (§11 shapes). Nothing here changes construction.
- **Small denominator:** 6 notices (rows 8, 16, 17 one each; row 13 three); rows 9, 10, 11, 15 have none,
  because their notice-like documents are dated on the event date (pre-registered `before_clock`). "Read in
  full" is v15's `source_coverage = adequate`, which counts a wire-only filing (R08-N1).
- **Process.** The orchestrating session had read the round 8–14 story summaries, so it did not author. A
  fresh subagent authored the 16 templates from a rounds-1–7-only package (`k10_package.py`, entity-scanned),
  four others enumerated the notices without seeing templates, and the notice list was committed
  (`04dbcb4`) before the template file was opened (`9d2c2b2`). "Cold" is procedure, not a wall.
- **Owed:** outcome vocabularies (the cold author wasn't asked for them; K9 needs them, authored from
  rounds 1–4 for rounds 5–7). `lookbacks/k10.py` re-runs unchanged on v16 rounds with the frozen templates.
- The v15 database is opened `immutable=1` in all K10 code so no `-shm`/`-wal` is created in the tracked
  directory.

## 2026-09-29 — repository cleaned

On the user's instruction, the earlier gate-test line was removed from the tree: `tests_a`, `tests_a2`,
`tests_b`, `tests_b2`, `tests_b3`, `tests_c`, both blind runs (`blindrun`, `blindrun2`), `methodology/`, the
`nomad/` infrastructure package, `data/`, `REPORT.md`, `SUMMARY.md`, `nomad_spec_v2.md`, `config_log.jsonl`,
and the old firewall's fetchers, logs and hosts backups. It all remains in git history (`main` at
`ca4edf1`, and the `claude/nomad-gate-test-spec-f2o5i1` and `claude/blindrun2-operator-handoff-g0xpfs`
branches, which were left alone). A tag marking that commit was refused by the remote (HTTP 403), so
the commit hash is cited in the README instead. Kept: `firewall/guard.py` and its allow/deny lists, which
`guard16.py` defers to when no round is in play. `nomad16/pit.py` no longer reads its SEC user agent out of
the deleted `firewall/edgar.py`.

## 2026-09-29 — v17 checkpoint prep: harness gaps, K7 tooling, blind back-fill

Against `v17_Checkpoint_Actionables.md` (groups 1–3 need a person; this is the part that didn't).

### Harness gaps closed (tests: 58 pass; R16-001's two locks still replay to their hashes)

- **Positions are stamped at write.** `position_add` refuses a row with no `knowable_from` and no longer
  defaults `confidence`. (v15 left 141 of 200 rows undated.)
- **Admit on the exact commit the operator will clone.** `submit_event` refuses to admit while `nomad16/`,
  `config/`, `firewall/` or `.claude/` has uncommitted changes, and records `admitted_commit`.
  `operator_manifest` compares the operator's own harness hash and config hash with the admitted ones, records
  `harness_match`, and `lock` refuses on a mismatch. Rounds admitted before this (R16-001) carry no
  `harness_match` and are unaffected. Caveat: the hash is over source bytes, so a checkout that rewrites line
  endings would mismatch.
- **The fetch list is recorded at lock.** For every holder in reach, `operating_status`, `contract_type`,
  `shared_access`, `listed`, `inventory_days` and `input_share` are classed documented / inferred / missing
  and written to `round_meta` as `fetch_list_seg<n>`. It is deliberately **not** part of the lock hash, so
  R16-001's locks still replay; it is ledger-chained and dated. The registry now carries the frozen K10
  templates' exact attribute vocabulary, so `lookbacks/k10.py` can re-run unchanged on new rounds.
- **The GDELT probe now requires matched events**, not just files read (the earlier probe couldn't tell a
  broken parser from an empty area). Verified separately: 53 events over Tehran, 103 over Washington, 0 over
  rural Monroe County (the world, not the code).

### Not done here, on purpose

- **D15 (domain-preference tie-break) is still not implemented**, and the enumerator reads only the NRC
  power-reactor feed. Group 3 needs a selection path for other feeds and for K7-derived nodes.
- **Nothing in group 1 was applied.** No threshold was ratified, `RHO_MIN` is still in place, and no D-register
  row was marked. Those are the requester's dated commits.

### K7 (`lookbacks/K7_prereg.md`, DRAFT, share unset)

`nomad16/census.py` (`census_add`, `census`) and a ledger table `census_rows`. A find needs a **concentration**
figure at or above `CENSUS_CONCENTRATION_PCT` (25, provisional); control alone (a listed parent or majority
owner) is recorded as `unquantified_control` and is not a find, because a diluted parent is exactly what
R16-001 hit. A source that became public after the earliest event the holder appears in is refused.
`K7_SHARE` is deliberately absent from the appetite file: the census reports counts and refuses a verdict until
it is set, in a dated commit before the census starts. `lookbacks/k7_candidates.py` produced the mechanical
top-15 unlisted holders from v15 (`k7_candidates.json`). Two features of that list are flagged for a decision
before use: sister entries (ranks 3/4, 5/15) and an aggregate with no single listed parent (rank 13).

### Blind back-fill of `knowable_from` (`lookbacks/backfill/RESULT.md`, overlay `v15_overlay/`)

Procedure written first; a fresh subagent dated 115 distinct sources from source text and `source_time` only.
**14 of 141 undated positions got an exact date; 127 stay null.** Positions with a `knowable_from`: 59 → 73
of 200. The 127 are operator priors and generic statements with no document to date, which matches v15's own
labels (131 of 200 `inferred`). So K8's unreadability was not only missing stamps. `k8.py --overlay` applies
the overlay (default behaviour unchanged, checked); **K8 has not been re-run**: `K8_rerun_expectations.md` is a
blank template for the requester to fill in first. "Cold" is a procedure, not a wall (the container holds the
v15 database); the dater's self-report is committed.

## 2026-09-29 — v17 V0 and V1 built (`docs/nomad_v17_open_entity.md`; ratifications in `docs/RATIFICATIONS.md`)

D17, D18, D19, D20, D21, D24 and D25 were ratified and persons put in the schema with ingestion off, on the
requester's instruction in this session. **Built: V0 (schema and compatibility) and V1 (documents as evidence).
Not built: V2 onward** (relations as rows, capability role binding in derivation, `edge_basis`, carriers as
series, `nomad_reach`), V3 composites, V4 instruments as entities and stake by kind, V5 the data-product spine.
K14, K15 and K16 have not been run.

### V0

- **`entities`** (mutable) with a kind tree (`entity_kinds`, 60 seed kinds, 32 reviewed), `capabilities`,
  `key_map`, `attribute_scope`. **`holders`, `nodes` and `node_types` are kept as they are**: v16 code paths and
  every old lock manifest read them, so nothing was renamed (the document says "renamed"; that would have broken
  replay of any manifest that pins `holders`). `holder_upsert` and `node_upsert` write the v16 table and mirror
  into `entities` once `seed_v17` has run; `migrate_v17` mirrored R16-001's 7 holders and 2 nodes (9 entities).
- **An unseen kind registers `unreviewed`** and can propose and never support; ratifying a kind needs a scale
  attribute (or an explicit none), a capability list, and an attribute registered *for that kind or an
  ancestor* (the generic `*` attributes don't count; the first version let them, and a test caught it).
- **Identity is a claim with evidence.** Merge, split, ratify and decline are appended events in
  `entity_events`; an as-of read honours the evidence's `knowable_from` and the view's `ledger_cutoff`, and a split
  restores the earlier graph. Merges need compatible kinds (the same, or one refining the other). A name alone never
  merges two persons. `migrate_v17` proposed two merges by a name-stem heuristic; **one was wrong** (`miso_lrz7_energy`,
  a market, and `miso-lrz7`, the place that is its footprint) because the heuristic ignored kinds. Fixed, and the
  wrong proposal is closed by an appended `decline` event (`EV00002`); it stays on the ledger. The other
  (`fermi2_unit` with `fermi-2`) is a proposal awaiting an operator's ratification, never applied automatically.
- **Persons.** `PERSON_INGEST` is `off` and read fail-closed (a missing value is off); `entity_upsert` refuses a
  person or any descendant kind; only five public-capacity attributes are scoped to `person`, and an attribute
  whose name suggests health, family, residence, location, sanctions, offences or motive can't be registered for one.
- **A18:** no existing ledger table gained a column (a frozen column fixture is compared); the three new ledger
  tables are `entity_events`, `evidence_entities`, `statement_links`. `position_attributes` did **not** gain
  `applies_to_kinds` (the document allows it): a side table `attribute_scope` does the job, so the v16 table stays
  byte-identical.
- **A1:** the R16-001 record is unchanged (every v16 ledger table's row count still sits at its pre-V0 head hash),
  the chain verifies, and both locks replay to their hashes on the migrated store.
- **Lifecycle (A12, entities):** `exists_from`/`exists_to` each honour their own `knowable_from`.

### V1

- **Documents are entities**, keyed by content hash and linked from an evidence row through `evidence_entities`
  when cited; a list fetch of a series is not a document. Lifecycle statements follow the document's state chain
  (draft → executed → in_force → …), each evidenced by another document.
- **`knowable_from` is derived** (`statement_add`): earliest verified `states` link, else latest `component` link,
  else the statement's own time. A `states` link needs its quoted span in the stored text (and, for numeric and
  enumerated attributes, the value in the span), otherwise it is stored as `component`. The check is literal: "1,141"
  in a span does not verify 1141. A typed date is refused; an embargo may only move a date later, with a reason.
  A v17 round writes its admission record (the Q8 line) as a document, so its first stated statement can cite it.
  `position_add` refuses while the active round is v17, and `statement_add` refuses on a v16 round.
- **Null-node statements** (about a subject's own state) are visible to a read that names the subject.
- **`dating_report` on R16-001 confirms the document's figures exactly:** 22 of 25 positions cite evidence; 20
  typed stamps equal the earliest cited document; 2 differ (`prior_outage_restart_days`, typed 05-22 against
  documents dated 05-20 to 05-26; `listed_domestic_filer`, typed 07-02 against 06-05 and 07-03); 3 cite nothing.

### Not done, and worth knowing

- V0 changes nothing about how a v16 round is played or scored; V1's derived dating applies only to rounds admitted
  with `logic_version: "v17"`. None exists yet.
- The relational test of §1.1 (an entity with no relation is an orphan) has nothing to check until V2 adds relation
  rows; `observable` records only whether the caller named a carrier.
- `resolve`, `orphans`, `nomad_opposite_census` and `relation_add` (the document's §7.7) are not built.
- `MATERIALITY_BAND`'s new `notional` key (V4) and the V2/V3 appetite values are added to the appetite file (all
  provisional) but nothing reads them yet.
- K14 needs a cold reader over 11 rounds' lock-time documents; it hasn't been started.
