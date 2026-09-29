# K10 — pre-registration (written before any template was authored, before any notice was enumerated, before any derivation was run)

*2026-09-29, the v16 build repository, a second orchestrating session. Spec v16 §31 K10:
"Of the forced notices that actually arrived in rounds 8–15 (carriers read in full), at least a share X₁₀
were derivable at lock from the positions in the stores (`recorded_at` before the original lock) and from
templates **authored using rounds 1–7 only**." Dies if below X₁₀. X₁₀ = 0.5 (`provisional_unratified`,
`config/appetite.json`). If it dies: emergence is limited by the stores; invest in positions before
construction.*

## Who did what, and what each party was allowed to see

The spec's guard is that templates, attributes and bounds are authored from rounds 1–7 only, by an author
who has not seen rounds 8–15, and frozen before any of rounds 8–15 is read against them.

- **The orchestrator (this session) does not author.** It has read `lookbacks/K8_prereg.md`,
  `K8_result.md`, `K11_K12_prereg.md` and `STATE.md`, which name the round 8–14 stories in one line each,
  and the round 8 recap. It therefore cannot be the cold author. Its job is mechanical: assemble the
  rounds 1–7 package by a filter on the ledger, launch the author, launch the enumerators, freeze,
  run.
- **The cold author** is a fresh subagent session. It is given one file, the rounds 1–7 package
  (`lookbacks/K10_authoring_package.md`, built by `lookbacks/k10_package.py`), and is instructed to read
  nothing else and use no network. That instruction is a procedure, not a wall (the same limit STATE.md
  records for operators). Its knowledge cutoff (June 2026) precedes every round 8–15 event (2026-07-14
  onwards), which is the §31 time-wall condition for a look-back author. It states its own declared cutoff
  in its output.
- **The enumerators** are separate fresh subagent sessions that read rounds 8–15 in the v15 record and
  list the forced notices that arrived. They are given this file's definitions and **never see the
  templates**. The notice list is committed before the template file is opened by the orchestrator.
- **Residual leakage, disclosed.** The spec extracts in the package (§3, §4, §18.3, §22.2) were written
  after round 15; their examples and the attribute names they list (`inventory_days`, `contract_type`,
  `hedge_ratio`, `input_share`, `capacity`, `substitute_lead_days`) may reflect what rounds 8–15
  taught. They are format-defining and unavoidable; a reader who thinks they leak should discount a
  survival, not a death.

## Rounds

- **Authoring rounds (1–7):** ledger rows 1–7. The package holds only rows created before the creation
  time of ledger row 8 (`2026-09-07T14:20:29Z`): the rounds 1–3 session record, the round 4–7 recaps,
  positions recorded before that time, library rules created before it (text, forbids, layer and
  provenance only, no hit/miss statistics, which later rounds updated), and holder and carrier kinds
  created before it.
- **Test rounds (8–15):** programme rounds 8–15 are ledger rows **8, 9, 10, 11, 13, 15, 16, 17** (rows 12
  and 14 are voided; row 13 is programme round 12, the re-run; row 15 is programme round 13). The same
  mapping as `K11_K12_prereg.md`. Clean and learning rounds are reported separately and pooled.
- **Lock:** each row's first transition to `locked` in `round_transitions`. **Clock:** the row's
  `event_date` (segment 0). Row 17 has a v15 `segments` table entry; only its first lock is tested.

## The forced-notice list (the denominator)

A **forced notice** is a dated statement or document, issued by a named party, concerning the round's
event or node, that satisfies both:

1. **Obligation.** The issuer was obliged to make it, by (a) statute, regulation, court process or
   exchange rule, (b) contract (a force-majeure or allocation notice, a contractual service notice), or (c)
   operating necessity to state a status after an outage (a restart statement). And
2. **Timing not public.** Its date was not calendared in advance. Excluded: results dates and other
   scheduled disclosures, index events, discretionary commentary (interviews, analyst notes, opinion),
   price prints, and third-party press reports *about* the event that are not themselves the
   notice.

**It arrived** if a document in the v15 record for that round (an `evidence` row, or a resolution's
`scorer_note`, or the exported round record) shows it, dated after the round's clock.

**Closed list of notice kinds.** Both the enumerators and the author use exactly this list, so that no
matching judgement is needed afterwards. The first five are §33.3's first set; the next three are added
here, and are disclosed as an addition of this pre-registration.

| kind | meaning |
|---|---|
| `force_majeure_declaration` | a party's notice that it cannot perform contracted supply or service because of the event |
| `restart_statement` | a statement of whether or when an outage-hit facility restarts, returns to service or runs partly |
| `regulatory_decision` | a regulator's, court's or commission's decision, order, prohibition, permit action or determination on a party or asset, including a decision inside a statutory window |
| `allocation_notice` | a supplier's notice apportioning scarce supply among customers (allocation, prorationing, supply limitation) |
| `incident_report` | a mandatory or customary report of the event itself, filed with or by an authority or operator of shared infrastructure (an emissions-event report, an event notification, an accident notification, an incident page or post-incident account) |
| `insolvency_or_restructuring_notice` | a court or filing notice inside an insolvency or restructuring |
| `corporate_disclosure_of_event_impact` | an unscheduled statement or filing by a listed party on the event's operational or financial impact |
| `counterparty_notice` | a notice from a party to its own counterparties or customers that is neither force majeure nor allocation (a surcharge, a service-credit or supplier-switch notice) |
| `other:<slug>` | anything else; no template exists for `other`, so it is never derivable |

**Read in full** is taken from the v15 record, not judged: a notice is `read_in_full` if it is linked
(by the enumerator, citing ids) to a resolution whose `source_coverage = 'adequate'`. A notice found only
in evidence or in a recap, with no such resolution, is not `read_in_full`. This is the spec's "carriers
read in full", operationalised with v15's own coverage field.

**Doubtful.** An enumerator that cannot tell whether an item was obliged and unscheduled marks it
`doubtful`. Doubtful items are reported, and are excluded from the primary denominator.

**Primary denominator:** forced notices that are `clear` and `read_in_full`. **Secondary denominators**,
reported, never a verdict: all `clear` notices; and all `clear` plus `doubtful`.
The enumeration is only as complete as the v15 record. A forced notice that arrived and was never found by
the round's operator is not in the denominator. That is a limit of the look-back, and it can only flatter K10.

## When is a notice derivable

A template file gives, per notice kind: roles with holder-kind filters, conditions on registered position
attributes or on bounds, an issuer role, carrier kinds and a window rule (format fixed in the author's
instruction). For a notice N in round R with lock L_R and clock T_R:

- **Store (guarded reading, the primary).** A position row counts if all hold: `recorded_at < L_R`;
  `knowable_from` is non-null and its date is on or before `T_R`; `confidence = 'stated'`; and it is not
  superseded by another counted row. This is §22.2 (inferred, implicit or NULL `knowable_from` is `unknown`
  for derivation, never `true`) applied to the v15 schema. **Bounds** are the author's bounds file, frozen
  before the run, and count as documented from the freeze.
- **Nodes.** The event's `node` and the round's `touched_set` nodes. Position rows are looked up by
  (holder, node).
- **Bindings.** A role binds to a holder of a permitted kind that has at least one counted position row on
  a round node, or, for a role the author marks `binds_without_position` (a regulator with no position
  rows), to any holder of that kind named in the round's `touched_set` or events. Bindings are bounded by
  `DERIVATION_BINDINGS_MAX` (500); an excess is reported, never silently truncated.
- **Conditions.** Each is `true` if a counted row (or a bound) satisfies it, `false` if a counted row
  (or bound) documents its negation, `unknown` otherwise. Several counted rows for one (holder, node,
  attribute) that disagree make it `unknown`.
- **Result.** `forced` if every condition is true; `switch` if none is false and some are unknown;
  `none` if any is false.
- **Match.** N is derived in a tier if some template T and binding b satisfy: T.notice_kind equals N.kind;
  T's issuer role binds to N's issuer holder (or, when N's issuer is not a holder in the names book, to a
  role whose holder-kind filter includes N's issuer class and which `binds_without_position`); the binding's
  roles are on N's node; the result is in the tier; and N's arrival date is on or before the derived ACK's
  window end (event date plus the window rule's days, else `DUE_AT_MAX_DAYS` = 90).
- **Tiers.** *forced*; *switch with at most one unknown condition*; *switch with any number of unknown
  conditions*. A template whose conditions are all unknown yields a `switch` for any binding, so the
  any-switch tier is vacuous and is reported only for completeness. **The verdict is read from the forced
  tier.** `node_types` in a template is not evaluated (v15 has no node-type field); a template applies to
  every node.

## Verdict rule

Share = derived (forced tier) ÷ primary denominator, pooled over rounds 8–15, with per-round counts.
- **`unreadable`** if the primary denominator has fewer than 5 notices.
- **`survives`** if share ≥ X₁₀ (0.5) under the guarded reading.
- **`dies`** if share < X₁₀ under the guarded reading **and** also under the *upper bound* below. The death
  does not depend on the v15 stamping gaps.
- **`dies_under_guards_only`** if share < X₁₀ guarded but ≥ X₁₀ on the upper bound. Then the store is thin
  on paper, because v15 did not stamp or grade its rows the way §22.2 needs. That is a real result about
  the v15 record, and it is **not** a finding that the world limits emergence. It carries the same remedy
  as the K10 kill (invest in positions: here, a blind back-fill of `knowable_from` and `confidence`).

**Upper bound (labelled, never a verdict on its own).** Three relaxations applied together, and each also
reported alone: **S1** drop the `knowable_from` requirement (`recorded_at` before lock is enough); **S2**
also accept `inferred` and `implicit` rows as documented; **S3** also treat each round's at-lock
`touched_set` fields (`substitutability`, `duration_factor`) as documented position rows on that holder and
node. If even the upper bound is below X₁₀, the death is robust.

## What will be reported

Per notice: its kind, issuer, node, date, linked resolutions, and per template the derivation state
(each condition `true`/`false`/`unknown`, with the position ids). Per round and pooled: the shares
above under the guarded reading and S1, S2, S3, and all three; the tiers; notices with no template for their
kind; notices whose issuer could not be bound; and the **fetch list**: which attributes were `unknown` most
often. That list is the "invest in positions" instruction, in order. No threshold, tier, guard or
template is changed after the first number is computed. If a defect in the look-back is found, the fix is
a dated addendum, both runs stay in the record, and the first run is reported beside the second.

## The decision point

§30.2 step 14 stops construction only if **K8 and K10 both die**. K8 came back `unreadable`
(`K8_result.md`), not dead. Whatever K10 returns, this file records that the joint condition is
evaluated by the operator of the programme, not here.

## Addendum 1 — 2026-09-29, before any template was opened or any number computed

Written while the author and enumerators were still working, so it decides nothing about what they return.
It fixes how `lookbacks/k10.py` reads the pre-registration where the text left a choice.

- **Units.** v15 position rows carry free-text units (`share` is stored as a capacity such as `620`
  with unit `kt/yr po capacity`, not as a fraction). A numeric condition is tested on a row only if the
  row's unit is empty or compatible (either string contains the other, case-insensitive) with the unit the
  author's registry gives the attribute. An incompatible row makes the condition `unknown`, and is counted in
  `engine_stats.unit_mismatch`. No unit conversion is attempted.
- **The relaxations alone.** The five variants are: `guarded` (the primary); `S1_no_knowable_from` (drop
  the `knowable_from` requirement only); `S2_inferred_accepted` (accept `inferred` and `implicit` rows only,
  which still need a `knowable_from`); `S3_touched_set_rows` (add `touched_set` rows only); and
  `upper_bound` (all three together, which is the bound the verdict rule uses).
- **S3 rows.** For each `touched_set` row of the round: `substitutability` becomes a position row on that
  holder and node, and `duration_factor` (free text) becomes a row for attribute `duration_factor`. A
  numeric `duration` condition is not helped by S3.
- **Issuer with no holder.** A notice whose issuer is not in the names book binds only to an issuer role
  marked `binds_without_position` whose holder kinds include the notice's issuer class. Its conditions can
  then only be bounds; a condition on a position attribute of that role is `unknown`.
- **Bound conditions** compare the bound's value with the condition's value by the condition's op, so a
  bound-only template is `forced` or `none` and never `switch`.
- **Window.** The derived window is the template's `window_rule.days` when it is an integer, else
  `DUE_AT_MAX_DAYS` (90), counted from the event date. A notice that arrives after it does not match.
- **Engine check.** `python lookbacks/k10.py --selftest` runs the engine on a synthetic in-memory ledger
  (guards, tiers, units, windows, unbound issuers, coverage lookup). It contains no v15 data.
