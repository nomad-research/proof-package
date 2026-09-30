# K14 — open-entity reading: pre-registration (DRAFT, not frozen)

Status: **DRAFT. No reading has been run.** Frozen only when the two blanks in §5 are ratified by the user and the freeze commit is recorded.

## 1. What K14 asks (spec §9.2, restated exactly)

On the documents each qualifying round had at its lock, does an open-entity reading find, in at least **X14 = 25% of the
readable qualifying rounds** (rounded up; 3 of 11 if all are readable), an entity of a kind v16 could not hold that
(i) is **within reach** of the round's node (documented, reviewed, transmitting relations at or above SUPPORT_THRESHOLD,
seeds of spec §6.6), and (ii) fills a role in a forced or switch derivation, or is `expressible`, or is one documented
relation from an entity that is? Dies if fewer rounds show one; then V3–V5 stop and the schema stays open.

The unit of count is an **entity found**, per round. Documents are only the material the reader reads; they enter the
test through the readability gate (§3) and nowhere else.

## 2. Qualifying rounds (fixed before counting)

v15 harness rounds seq 5, 6, 7, 8, 9, 10, 11, 15, 16, 17, plus R16-001 = **11**. Voided rounds 12 and 14 and the
2025 re-run (13) are excluded.

## 3. Readability condition (spec)

K14 is readable only if at least 6 of the 11 rounds have lock-time documents that can still be retrieved. Below that it is
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

v15 stores only excerpts, not full text, so v15 documents must be re-fetched. Two rounds (7, 17) have none.

Readable rounds by threshold on "usable lock-time documents per round" (the count is the number of pre-event dated URLs still returning 200, plus R16-001):

| threshold DOC_MIN | rounds meeting it |
|---|---|
| ≥ 1 | 7 of 11 (5, 6, 10, 11, 15, 16, R16-001) |
| ≥ 2 | 5 of 11 (5, 10, 11, 15, R16-001) |
| ≥ 3 | 4 of 11 (5, 10, 15, R16-001) |

## 5. Blanks (no default; K14 cannot freeze until set)

- **DOC_MIN** — how many retrievable lock-time documents make a round readable. **Unset.** Disclosure: these counts were
  seen before this rule was written, so any value chosen after seeing §4 is not a blind choice. On the table above, K14
  is readable only at DOC_MIN = 1 (7 of 11 ≥ 6); at DOC_MIN ≥ 2 it is unreadable (5 or 4 of 11). The user decides, with that on the record.
- **Reader model** — a model whose training cutoff precedes the earliest qualifying event (2026-07-14). Unset.

## 6. Procedure once frozen

1. Freeze kinds, capabilities, relation seeds and templates (`config/seed_v17.json`) at the freeze commit. Templates for
   rounds 5–7 come from rounds 1–4 only; for later rounds, from rounds 1–7 only.
2. Each readable round is read twice by a cold reader, closed then open, alternating which comes first by round parity.
3. Per round, record whether the open reading found at least one entity meeting (i) and (ii). Persons are counted as
   roles from documents; none is stored (PERSON_INGEST is off).
4. The closed reading finds zero entities of a kind v16 cannot hold by construction, so it is not a baseline. It controls
   for reader effort: report its finds of kinds v16 could hold beside the open run's. If a second look alone finds as much
   as the open look, effort and not vocabulary is the variable and the result is read that way.
5. Verdict: unreadable if readable rounds < 6; else dead if rounds with a qualifying entity < ceil(0.25 × readable rounds);
   else not dead.

## 7. Notes

- Fetching v15 URLs now returns present-day pages; a page edited after the event is not lock-time evidence. Rounds
  where the page's own date cannot be verified as ≤ event date use the Wayback snapshot or are dropped.
- The census can only fall from here as links rot; re-run before freeze.
