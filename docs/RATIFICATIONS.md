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
