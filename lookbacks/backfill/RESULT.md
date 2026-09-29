# Blind back-fill of `knowable_from` — result

*Run 2026-09-29 per `PROCEDURE.md` (written before any date was assigned). Overlay:
`v15_overlay/knowable_from_backfill.json`. Dater: a fresh subagent; its self-report is `dater_report.md`.*

| | positions |
|---|---|
| Undated in v15 | 141 (115 distinct sources) |
| **Dated by the back-fill, exact** | **14** (7 anchored in the source text or date, 7 resting on `source_time` alone) |
| Dated by upper bound | 0 |
| **Left undated (`null`)** | **127** |
| With a `knowable_from` after the overlay | **73 of 200** (was 59) |

**Why so few.** The dater's report explains it: the 101 null sources are not documents. About 90 are the
operator's own priors ("the country's first and long its only copper smelter") and the rest are generic
structural statements. Neither has a publication date to find, and inventing one from general knowledge would
be exactly the guess this exercise exists to avoid. That matches v15's own labels: 131 of its 200 positions
are `inferred`. **The v15 positions were mostly never documented facts**, so K8's unreadability wasn't
only a missing-stamp problem, and a better back-fill would not have fixed it.

**Rows to check.** B008: the source has a `source_time` of 2026-07-28 but the text says "no restart statement
found by 7 Sep"; the dater took the later date (conservative) and marked it inferred. B108–B113 are the
operator's own post-lock readings, dated by `source_time` (when written); the `recorded_at < lock` guard
excludes them from any round they post-date, so they don't leak into K8.

**Procedure notes from the dater** (unclear in the procedure): rule 2 covers only periodic documents, so
priors were nulled rather than bounded; the rule for conflicting dates and the meaning of `confidence_note`
values were interpreted literally. None changes a result.

**What this means for the checkpoint.** The K8 re-run can now count 14 more positions, and the honest
expectation is that it stays mostly unreadable. If it does, the row in the checkpoint table is the third one:
*treat the v15 store as the limit; census-first for everything after.* The forward rounds, which stamp every
position at write (enforced since this commit), are how K8 and K10 become readable.
