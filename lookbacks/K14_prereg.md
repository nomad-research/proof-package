# K14 — open-entity reading: pre-registration (values frozen, no reading run)

Status: **FROZEN on its values (§5) but not yet read; no reading has been run.** The two blanks are set (provisional_unratified). The template-authorship guard is unverified (§5).

**§8 (amendments of 2026-09-30) supersedes §2 to §6 wherever they differ.**

## 1. What K14 asks (spec §9.2, restated exactly)

On the source entities each qualifying round had at its lock, does an open-entity reading find, in at least **X14 = 25% of the
readable qualifying rounds** (rounded up; 3 of 11 if all are readable), an entity of a kind v16 could not hold that
(i) is **within reach** of the round's node (documented, reviewed, transmitting relations at or above SUPPORT_THRESHOLD,
seeds of spec §6.6), and (ii) fills a role in a forced or switch derivation, or is `expressible`, or is one documented
relation from an entity that is? Dies if fewer rounds show one; then V3–V5 stop and the schema stays open.

The unit of count is an **entity found**, per round. A document is itself an entity (a kind such as `filing`, `report`, `notice`);
the **source entities** are the ones the reader reads from, and they enter the test through the readability gate (§3) and nowhere else.

## 2. Qualifying rounds (fixed before counting)

**Primary count: v15 harness rounds seq 5, 6, 7, 8, 9, 10, 11, 15, 16, 17 = 10 rounds.** R16-001 is **excluded from the
primary count** and reported as a labelled sensitivity (11 rounds), because its template guard is uncleared (§8). Voided
rounds 12 and 14 and the 2025 re-run (13) are excluded from both; they are the pilot pool.

## 3. Readability condition (spec; "documents" in the spec's wording are source entities of kind document)

K14 is readable only if at least 6 of the 11 rounds have lock-time source entities that can still be retrieved. Below that it is
reported **unreadable**, not passed and not killed.

## 4. Readability census (run 2026-09-30, before any reading)

Source: v15 `evidence` table, rows with an http URL and `knowable_from[:10] <= event_date` (operator-typed dates;
the back-fill found these unreliable for positions, so this is an upper bound). Liveness: one plain GET per URL.

| v15 seq | pre-event dated URLs | still 200 |
|---|---|---|
| 5 | 4 | 3 |
| 6 | 1 | 1 |
| 7 | 0 | 0 |
| 8 | 1 | 0 |
| 9 | 1 | 0 (timeout) |
| 10 | 3 | 3 |
| 11 | 2 | 2 |
| 15 | 4 | 3 |
| 16 | 1 | 1 |
| 17 | 0 | 0 |
| R16-001 | 131 evidence rows stored with full text in the ledger | n/a (text held locally) |

v15 stores only excerpts, not full text, so v15 source entities must be re-fetched. Two rounds (7, 17) have none.

Readable rounds by threshold on "usable lock-time source entities per round" (the count is the number of pre-event dated URLs still returning 200, plus R16-001):

| threshold SOURCE_MIN | rounds meeting it |
|---|---|
| ≥ 1 | 7 of 11 (5, 6, 10, 11, 15, 16, R16-001) |
| ≥ 2 | 5 of 11 (5, 10, 11, 15, R16-001) |
| ≥ 3 | 4 of 11 (5, 10, 15, R16-001) |

## 5. Values set (Rob, 2026-09-30, relayed by the requester; before any reading)

- **SOURCE_MIN = 1**: a round is readable if at least one lock-time source entity, dated at or before the event and still
  retrievable, exists. Status provisional_unratified (appetite key `K14_SOURCE_MIN`).
  **Disclosure (kept):** the §4 counts were seen before this value was set, so it is not a blind choice. It is the
  only setting at which K14 is readable on the census (7 of 11 at SOURCE_MIN 1; 5 of 11 at SOURCE_MIN 2, which is below the 6 the spec requires).
- **Sensitivity, SOURCE_MIN = 2**, reported beside the main result. On the census it is **unreadable** (5 of 11 < 6), so it
  gets no pass or dead verdict. The count of rounds with a qualifying entity among the 5 is still reported, as information only.
- **Reader:** the declared operator model, `claude-opus-5-5` (declared trained-through 2026-06-30, from the R16-001
  operator manifest), in fresh cold sessions. Every qualifying event is dated 2026-07-14 or later, so each is after that cutoff.
- **Census re-run 2026-09-30 before freezing:** unchanged (7 of 11 and 5 of 11; per-round counts as in §4).

**Freeze.** Kinds, capabilities, relation seeds and templates are those in `config/seed.json`
(sha256 `dfa404d0…b948b`) and `config/seed_v17.json` (sha256 `e5c702f9…7af2e`) at the commit that adds this section.
**Not verified:** that the templates in those files were authored from rounds 1–4 only (for rounds 5–7) and from
rounds 1–7 only (for the rest), as the spec's guard requires. The seed files carry no authorship record of that. Until
someone can show it, K14 is read as *provisional on the template guard*, and the result says so.

## 6. Procedure once frozen

1. Freeze kinds, capabilities, relation seeds and templates (`config/seed_v17.json`) at the freeze commit. Templates for
   rounds 5–7 come from rounds 1–4 only; for later rounds, from rounds 1–7 only.
2. Each readable round is read twice by a cold reader, closed then open, alternating which comes first by round parity.
3. Per round, record whether the open reading found at least one entity meeting (i) and (ii). Persons are counted as
   roles from source entities; none is stored (PERSON_INGEST is off).
4. The closed reading finds zero entities of a kind v16 cannot hold by construction, so it is not a baseline. It controls
   for reader effort: report its finds of kinds v16 could hold beside the open run's. If a second look alone finds as much
   as the open look, effort and not vocabulary is the variable and the result is read that way.
5. Verdict: unreadable if readable rounds < 6; else dead if rounds with a qualifying entity < ceil(0.25 × readable rounds);
   else not dead.

## 7. Notes

- Fetching v15 URLs now returns present-day pages; a page edited after the event is not lock-time evidence. Rounds
  where the page's own date cannot be verified as ≤ event date use the Wayback snapshot or are dropped.
- The census can only fall from here as links rot; re-run before freeze.

## 8. Amendments of 2026-09-30 (Rob, relayed by the requester), before any qualifying reading

**Template provenance, as disclosed.**
- **v16 seeds** (`config/seed.json`: attributes, obligation templates, transforms, carriers): recorded in `STATE.md`
  2026-09-29. Authored by the builder from general knowledge and statute text, before enumeration, with no v15 record present.
- **v17 kinds, capabilities and relation seeds** (`config/seed_v17.json` and spec §6.6): authored by Claude in the spec session
  **after reading R16-001's stored round and the K8, K10, K11 and back-fill result files**. **R16-001 is guard-uncleared.**
- **Unresolved, raised by the builder, not decided:** the K8, K10, K11 and back-fill result files are about v15 rounds 5 to 15
  as well as R16-001. If the same reading is judged to leave rounds 5 to 15 uncleared too, no cleared round remains in the
  primary count. Rob has said only that R16-001 is uncleared; this file treats rounds 5 to 15 as cleared on that instruction
  and says so here.

**Counts under the primary/sensitivity split** (census of 2026-09-30; needs at least 6 readable rounds):

| Reading | SOURCE_MIN 1 | SOURCE_MIN 2 |
|---|---|---|
| **Primary** (10 rounds, no R16-001) | 6 of 10 readable (5, 6, 10, 11, 15, 16): **at the floor, so one lost link makes it unreadable**; X14 needs `ceil(0.25 × 6)` = 2 rounds | 4 of 10: unreadable |
| Sensitivity, with R16-001 (11) | 7 of 11 readable; X14 needs 2 | 5 of 11: unreadable |

**Procedure added.**
1. **Pilot first.** One reading on a non-qualifying round (rounds 12 and 14 hold no documents; the 2025 re-run, 13, is the pilot),
   with cost reported before any qualifying round. Nothing from the pilot counts toward K14. The pilot corpus is not lock-time:
   the round's one dated document (an encyclopaedia entry) has no revision before 2025-12-21, so the pilot reads four
   early-August-2025 news pages instead. It measures procedure and cost only.
2. **Cost cap.** The full run is capped at **$100**. If the pilot projects higher, stop and report.
3. **Each find lists its chain hop by hop** with registry relation types, an effect-kind pair, a document id and an exact
   quoted span. `lookbacks/k14/support.py` recomputes support (transform value × hop discount, multiplied along the chain)
   against `SUPPORT_THRESHOLD` 0.3, verifies every quote literally against the stored document, and checks the kind's review
   status. Reach is decided by the script, not the reader.
4. **A blind second session judges (ii)** (role, expressible, or one documented relation from something expressible). It sees
   the find's entity, chain and expression leg but not the reader's claimed class, the script's result or the round's outcome.
   A round shows a find only if the script passes (i) and the judge accepts (ii).

**Operationalisations chosen by the builder, open to Rob's amendment before the first qualifying reading:**
- *Transmitting* means a transform entry for the hop's effect pair with value above 0 and a hop discount above 0. Non-transmitting
  relations (`references`, `member_of`, provenance, classificatory, analogical) can be the documented last relation of a one-hop
  find and never a hop of the reach chain.
- *A kind v16 could hold* = the `LEGACY_KIND` values in `nomad16/entities.py` (company, facility, sovereign, agency, central_bank,
  fund, index, commodity_grade, currency, contract) and composite, plus every descendant of those in `seed_v17.json`. Listed by
  `support.v16_holdable`. Unreviewed kinds propose and never support, so an unreviewed kind is not a find.
- *Order:* the reader reads the open reading first on odd round numbers and the closed reading first on even ones.
- A reader lists at most 8 finds per reading; persons are named by office and organisation only.
- Relation registry: `lookbacks/k14/registry.json` (sha256 `1038032f…35f3d`), extracted mechanically by `lookbacks/k14/registry.py` from
  `seed.json`, the appetite hop discounts and spec §6.6. The scripts (`registry.py`, `support.py`, `package.py`) are frozen at the
  commit that carries this section.
- Document sizes of the qualifying rounds' pre-event pages were measured (characters only, 13 pages, median 7,821) to project cost;
  no content was read.
