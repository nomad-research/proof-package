# Operator guide — playing one v16 round

*For the cold operator session (spec v16 §9, §28). Your context is the spec
(`docs/nomad_system_spec_v16_final.md`), the theory (Section C of
`docs/nomad_the_system_as_it_stands.md`), your round's reveal (`rounds/<id>/reveal.json`), this guide
and the tools. Nothing else crosses rounds.*

**The operator authors inputs and ratifies; the harness computes (§16).** You never edit a derived
ACK's conditions, a reachable set, a loading or a basket weight. If you disagree with a computed object,
record a note with your reason and fix the store it read (a position, a bound, a story), then recompute.

Every tool: `python3 -m nomad16 <tool> '<json args>'` (one call per Bash command; chaining is refused
by the hook). `python3 -m nomad16 help` lists them. A refusal prints `{"refused": …}`: read it, it
names the rule.

## 0. Before anything

1. `python3 -m pip install -q numpy scipy pandas pillow pytest` if they're missing.
2. **Verify the hook by attempting a denied call.** Issue a WebSearch for anything. It must be refused.
   That refusal is logged, and the manifest reads it.
3. `operator_manifest {"round_id", "operator_model", "operator_runtime": "claude_code",
   "operator_cutoff", "cutoff_basis", "session_id", "cold": true}`. It must return `hook_verified: true`,
   or the round can't lock. Your cutoff is your training cutoff; if you don't know it, use your model's
   public release date (§9).
4. Read `rounds/<id>/reveal.json`.

Don't open anything outside `docs/`, `nomad16/`, `config/`, `rounds/<id>/`, `STATE.md` and `README.md`.
The hook quarantines the rest; don't go looking for ways around it.

## 1. Pre-lock, segment 0 (§16 steps 2–14)

| Step | What you do | Tools |
|---|---|---|
| 2 Blind pass | Write your first reading before any fetch, and commit it before your first fetch | the file `rounds/<id>/blind_pass.md` |
| 3 Pieces | Author the names book: holders (per asset, any economic entity), positions from documents knowable by the clock, per asset where positions differ. Register attributes you need. Then the effects at holders, with equal depth across degrees | `pit_fetch` (sources `nrc_en`, `nrc_status`, `edgar_filings`, `edgar_doc`, `wayback`: pass targets without `https://`), `alt_fetch` (satellite, AIS, GDELT, outages; run `alt_probe` first if a source has none), `holder_upsert`, `node_upsert`, `position_attribute_add`, `position_add`, `bound_add`, `node_fact_add`, `effect_root`, `effect_compose` |
| 5 Fetch | In your attention order; switch fetch lists join the queue | same |
| 7 Vetoes | Inspect per-effect vetoes and typed gaps | `surviving_risk` |
| 8 Derive ACKs | Run derivation; ratify or drop each candidate with a reason. Calendar ACKs by hand | `derive_acks`, `ack_ratify`, `ack_add`, `ack_window` |
| 9 Outcomes, reach, thesis | Per ratified ACK: vocabulary, the cut to R, then your thesis set Ωₜ. Every excluded reachable outcome cites documented positions or bounds (an exclusion resting on an unknown is refused). This registers the ACK as a `map` call | `outcomes`, `reachable`, `thesis_set` |
| 10 Calls | Each with a claim kind, a carrier with a working fetch path, `due_at` ≤ 90 days, a falsifier, and cited rules that carry the claim kind | `call_add` |
| 11 Stories | Name the stories on the tape (proxy tickers) and candidate adjacent readings (construction rule on a position attribute). Name a story active only with a source knowable before the clock. Treat each flagged junction | `story_add`, `story_active`, `junction_treat`, `preview` |
| 12 Narrative rows | `call_add` with `call_type: narrative` and `narrative_sign` | `call_add` |
| 13 Instruments, construct | Instruments for holders in reach, listed before the clock; fetch their prices (truncated at the clock automatically); declare the tide; preview the baskets. You may not change weights | `instrument_add`, `price_fetch`, `tide_declare`, `preview` |
| 14 Lock | Freezes and hashes everything, writes the manifest and the paper entries | `lock_predictions` |

Commit and push after the lock (`git add rounds/<id> state/nomad16.db && git commit && git push`).

## 2. The walk (backfilled rounds, §14, §22.4)

After lock the round is `walking`. Read each ratified ACK's carriers **forward from the clock, one date
at a time**. `pit_fetch` refuses anything more than one day past the frontier, and each read advances it.

- `walk_scan` reads one carrier forward date by date and stops at the first date matching a predicate you
  declare before it runs: a unit's power in `nrc_status`, an event for a facility in `nrc_en`, or a filing
  form in `edgar_filings`. It's mechanical. You still read the matching document and decide what it
  delivered.
- When a carrier **delivers**, fire the ACK with the outcome from its vocabulary, the fact's
  `knowable_from`, and the evidence id: `ack_fire`. The round goes back to `pre_lock` at the new clock.
  Add the positions the fact changes (`knowable_from` = the new clock), re-run `derive_acks`,
  `reachable` and `thesis_set` for the new segment, add the segment's calls, `preview`, then
  `segment_lock`.
- A carrier read silent through a date is recorded by the read itself. A forced ACK that doesn't deliver
  by its window's end is fired with `delivered: false` (it prunes and names no successors).
- Paper: `paper_fill` after each lock; `paper_mark` at firings (automatic) and every 5 sessions;
  `exit_check` at each mark (window end and the price test).
- When no ratified ACK remains open, or every window has closed: `walk_end`. Live retrieval opens.

## 3. Scoring (post-walk)

- Score each call against its carrier: `score_call` with `carrier_state` (`spoke`, or `silent` for a
  carrier read in full through `due_at`). Narrative rows first. Absence claims hit only on `silent`.
- `close_round {"round_id", "as_of"}` expires what's left (unread carriers resolve `unverified`, never `hit`).
- `junction_confirm` for each segment's trigger date; `paper_book`; `report`.
- Commit and push: `rounds/<id>/`, `state/nomad16.db`.

## Rules that bite

- Only `stated` positions with `knowable_from ≤ clock` count for derivation and reach. `inferred` and
  `implicit` are unknown: they make switches, never forced ACKs.
- No proper nouns in a rule. Positions, holders and bounds carry the nouns.
- Satellite counts, GDELT tallies and any model reading are attentional or analogical. They may
  **propose**, and never **support** (§6).
- The round is `learning` (provisional appetite values). Play it exactly as if it were clean.
