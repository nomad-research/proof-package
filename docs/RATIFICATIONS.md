# Ratifications

*A dated register of amendment decisions. The rule (Section D of `nomad_the_system_as_it_stands.md`): each
row is marked ratified, rejected, amended or held, with a date. A row with a kill test may stay proposed
until the test has run. This file records decisions; it changes no code.*

## 2026-09-29 — v17 open entity (`docs/nomad_v17_open_entity.md`, §13)

**How it was decided.** In the build session, asked whether to ratify D17, D18, D19, D20, D21, D24 and D25 "now
(what V0 to V2 need)" and to put persons in the schema with ingestion off and enforced by the tool, with D22, D23
and D26 to D28 left proposed until K14 is read, the requester answered **"Yes, both as recommended"**. The
document assigns these two decisions to Rob; this entry stands as Rob's if the requester is Rob, and needs his
countersign (a dated commit editing this file) if not.

| ID | Change | Decision | Built |
|---|---|---|---|
| **D0′** | Open entity definition replaces the list | applied (per the document, on Rob's instruction of 2026-09-29) | definition in `docs/`; the closed lists are retired by V0 |
| **D17** | One `entities` table; kinds as a tree and registry; capabilities; roles relational | **ratified** | V0: `entities`, `entity_kinds`, `capabilities`, `key_map`, `entity_upsert`, migration. Capability *role binding* in derivation is V2, not built |
| **D18** | Relation rows and a type registry; no untyped relation; `edge_basis` (no new veto) | **ratified** | **not built** (V2) |
| **D19** | `knowable_from` derived from `states`/`component` links with a checkable span; a typed date refused | **ratified** | V1: `statement_add`, `statement_links`, the admission record. A typed date is refused on v17 rounds |
| **D20** | Documents are entities with a lifecycle; a reifying document is one hop; validity intervals; carriers are series | **ratified** | V1 has document entities and lifecycle statements. The reified hop, validity intervals and carriers-as-series are V2, not built |
| **D21** | Persons in public capacity; identity events; ingestion off by default | **ratified**, with persons in the schema and templates and **ingestion off, enforced by the tool** | V0: `PERSON_INGEST` (fail-closed), the public-capacity attribute list, identity events. **No person is stored** |
| **D24** | Template roles require capabilities; the governing document is a role filler | **ratified** | **not built** (V2) |
| **D25** | `state` and `control` effect kinds, relation seeds, `edge_basis` | **ratified** | **not built** (V2) |
| **D22** | Composites | proposed, held until K14 is read | not built (V3) |
| **D23** | Instruments as entities; expression by graph; stake basis by kind | proposed, held until K14 is read | not built (V4) |
| **D26** | Intake by entity state change | proposed, held until K14 is read | not built |
| **D27** | Entity spine in the data product | proposed, held until K14 is read | not built (V5) |
| **D28** | Per-kind wall map | proposed, held until K14 is read | not built |

**What ratifying does and doesn't do.** Ratified rows are the specification of record for V0 to V2. Five of the
seven ratified rows have mechanisms that V0 and V1 don't reach (D18, D20's hop and validity, D24, D25); they are
the next phase (V2), not a claim that they exist. Persons: the tool refuses to store one. Turning ingestion on
needs a legal review and an erasable person store (§3.5); this record does not satisfy either.

**Earlier rows (D1–D16) are not touched here.** They are issue #9.

## 2026-09-30 — the dilution and bucket mechanism (V2 slice, `nomad16/dilution.py`)

**Who and when.** Rob, on 2026-09-30, before any data. The requester in the build session relayed the instruction
and stated it as Rob's; this entry stands as Rob's on that statement. A dated commit by Rob editing this file
countersigns it if a countersignature is wanted.

**What is set.**

| Item | Value | Status |
|---|---|---|
| The mechanism: node impact in band units, same-root paths not summed, `t · n_out^-alpha` per edge, post-hoc buckets as a versioned partition, retention r, the bend | as built | **provisional and report-only** |
| `BUCKET_MIN_OBS` | 8 | provisional_unratified |
| `BUCKET_SHRINK_K` | 10 | provisional_unratified |
| `BEND_TOL` | 0.5 | provisional_unratified |
| `BEND_MIN_NODES` | 10 | provisional_unratified |
| `PROFILE_DEPTH_MAX` | 5 | provisional_unratified (added by the requester with the profile mode; not in the four above) |

**Report-only means** the profile expands past `SUPPORT_THRESHOLD` to depth 5, bounded by `ENTITY_MATERIALISE_MAX`,
and its output is never used for support, for an ACK, a call, a basket, a veto or a lock. It writes nothing to any
ledger table. The trigram grouping stays as the proposal step until the first real edge texts exist.

**Rule for ratifying, set before any data.** The mechanism and the four values are ratified only if **at least one
bucket reaches 8 real observations** and **its alpha holds on a later block of rounds**. Real means an edge observed in a
round with its fan-out and its impact measured in band units; a planted or simulated observation does not count.

**Rule for removing it.** If no bucket has 8 real observations by **2027-03-31**, the code path is removed:
`nomad16/dilution.py`, its tests, its tools and the three `bucket_*` tables' use. The ledger rows already written stay,
because the ledger is append-only.

**Order.** V3 to V5 follow K14 as pre-registered (`lookbacks/K14_prereg.md`). This entry changes nothing about that
gate. D18, D20, D24 and D25 remain V2 work that is not built beyond this slice.

## 2026-09-30 — K14 values (`lookbacks/K14_prereg.md`)

Rob, relayed by the requester, before any reading: `K14_DOC_MIN` = 1 (provisional_unratified), with the disclosure that the
census counts were seen first, and a DOC_MIN = 2 sensitivity (unreadable on the census, 5 of 11). The reader is the
declared operator model `claude-opus-5-5` in fresh cold sessions. V3 to V5 follow K14 as pre-registered. One guard is
unverified and the file says so: that the frozen templates were authored from rounds 1–4 (for rounds 5–7) and 1–7 (for the rest).

## 2026-09-30 — what "holds" means for an alpha (`nomad16/dilution.py: holds`)

Rob, relayed by the requester, before any data. A bucket's alpha **holds** if the later block of rounds has **at least 8
observations of its own** (at fan-out above 1; `BUCKET_MIN_OBS`) **and its raw, unshrunk alpha is within 2 standard errors of
the first block's raw alpha**. Read the rule literally: the standard error used is the **first block's**. That reading is
the builder's, because the sentence does not say whose. It is strict: with a precisely measured first block, a later block
of 8 to 12 noisy observations will often miss by chance even when the alpha has not changed. `holds` therefore also reports,
for information only, the same gap against the two blocks' combined standard error (`would_hold_on_combined_se`). The decision
uses the first block's standard error unless Rob amends this entry.

## 2026-09-30 — PR #20: do not squash-merge

Rob's instruction: do not squash-merge PR #20; tag or preserve `3090edf`. Tag pushes are refused in this environment (HTTP 403,
issue #19), so the commit is preserved as a branch (see STATE.md). A merge commit or a rebase merge keeps the history.

**Rename, 2026-09-30 (Rob: "I'm still seeing the word document instead of entity").** `K14_DOC_MIN` is now `K14_SOURCE_MIN`
(value 1, unchanged); "DOC_MIN" in `lookbacks/K14_prereg.md` reads `SOURCE_MIN`, and the prereg says *source entities* where it said
documents. A document is an entity (a kind: filing, report, notice, and so on), so the readability gate counts source entities. Dated entries above
keep the old name, as written at the time.

## 2026-09-30 — K8 (Rob: "No structural count at all, caps gains and isn't necessary")

Recorded on the requester's statement: **no structural count**, so K8 as pre-registered (listed holders on both sides of a node, or options)
is **retired as a gate**. Nothing waits on it. The unguarded figure already in `lookbacks/K8_result.md` (9 of 11 nodes with a listed hedge, mostly options)
stays as a labelled note. The overlay run is not made. **Not yet set:** the replacement narrative-hedge measure, which is proposed
(two or more listed instruments with the same exposure sign and different story loadings, giving a lower maximum loss across the thesis
outcomes than either alone) and waits on Rob's definition. The stock-pair decision moves to that forward measure.

## 2026-09-30 — the narrative-hedge measure (Rob: "Candidate is good, leaning on 2 where it's outcome based")

Set on the requester's statement, before any data. A node **counts** as narrative-hedged if **two or more** listed instruments with the same
exposure sign to the event have different story loadings, so that a basket holding them has a **lower maximum loss than any one of them alone,
measured across the thesis outcomes** (outcome-based, not by side of the node). Status: provisional, forward-only (the v15 record has no thesis
sets or loadings). The builder read "leaning on 2" as the two-or-more-instruments threshold and the outcome basis; that reading is not confirmed.
It replaces K8 as the stock-pair decision (K8 retired as a gate, above). The scenario that motivated it is illustrative
(`lookbacks/scenarios/narrative_hedge.py`), not evidence.

**Design intent, stated by Rob (proposed, not built):** the hedge is itself a correlated parallel thesis. As a thesis is constructed, its
narrative hedges are constructed as parallel theses over the same event, and N baskets are then constructed from that pool to fit whatever
objective is needed. See `docs/nomad_v17_amendment_A1.md` §7 (proposed D31).
