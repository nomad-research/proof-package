# Blind back-fill of `knowable_from` on the v15 positions — procedure

*Written 2026-09-29 before any date was assigned. v17 checkpoint, group 2.*

**Purpose.** 141 of v15's 200 positions carry no `knowable_from`, so the time-wall guard can't count them
and K8 and K10 came back unreadable. This back-fill dates them, blind to outcomes, so K8 can be re-run.
`v15/` is frozen under a sha256 manifest and is **not touched**: every date goes in an overlay
(`v15_overlay/knowable_from_backfill.json`), one dated row per position, applied by the look-back
scripts and never written into the v15 database.

**What the cold dater sees.** Only `package.json`: a list of `{id, source, source_time}` for the distinct
sources of the undated positions. Not the holder, the node, the attribute, the value, the round, the event,
or anything after the source itself. It decides one thing per id: **the latest date by which the source
document could have been public** ("no later than"). An upper bound is the conservative direction: a later
`knowable_from` can only exclude a position from a round, never smuggle one in.

**Rules the dater follows.**
1. Use a date stated in `source_time` or in the `source` text. If the text gives an exact day for the
   document (a letter, a filing, a notice), that day is the bound (`bound_type: exact`).
2. If the text gives only a period or a scheduled periodic document (an annual report, a results deck),
   give the latest date it could plausibly have first been public, from what the dater knows from before its
   own knowledge cutoff, and mark `upper_bound`. If that can't be bounded, `null`.
3. Never use knowledge of what happened after the source, and never date from an event's outcome.
4. `null` is a normal answer. A position that stays undated stays out of the time-guarded counts.
5. Also report, per id, whether the text supports the row being `stated` (a document says it) or only
   `inferred`. v15's own `confidence` is kept unless the text plainly contradicts it; the dater notes that.

**Output.** `lookbacks/backfill/dating.json`: `[{"id", "knowable_from" (YYYY-MM-DD or null), "bound_type"
("exact"|"upper_bound"|null), "basis" (a short quote from the source that gives the date, or why null),
"confidence_note" ("consistent"|"looks_inferred"|"n/a")}]`, one entry for every id, no others.

**Disclosures fixed in advance.**
- "Cold" here is a procedure, not a wall: the dater is a fresh subagent that is told to open only the
  package. The container holds the v15 database. Its self-report is recorded with the result.
- The orchestrating session did not read the source strings in bulk and made no dating decisions.
- The dater's knowledge cutoff (June 2026) precedes most of these sources' dates, which is what makes
  "date it from the text" the only route; expect many `upper_bound` and `null` answers.
- **Result reported as:** the share of the 200 positions with a `knowable_from` (59 already had one),
  split exact / upper-bound, and the number left undated. K8 is **not** re-run by this step: the
  requester writes down what they expect first (`lookbacks/K8_rerun_expectations.md`).
