# Cold dater report

**Knowledge cutoff.** June 2026, as stated in my system prompt. I cannot verify it independently, and my recall of the last few months before it is thin. It falls before the dates of every dated source in the package.

**Files opened (exactly two).**
1. `/home/user/Nomad-Research/lookbacks/backfill/package.json` (read in full)
2. `/home/user/Nomad-Research/lookbacks/backfill/PROCEDURE.md` (read in full)

Other file activity:
- I wrote `dating.json` and this report in `lookbacks/backfill/`.
- I wrote a small generator script in my session scratchpad, outside the repo.
- After writing, I re-parsed `package.json` (already opened) only to check that the ids in `dating.json` match it exactly. They do: 115 ids, same order, no extras, no duplicates.

I opened, listed or grepped nothing else in `/home/user/Nomad-Research`. I ran no git command and did not use the web.

**Information beyond the two files and my own knowledge.** None. My own knowledge was not used to date any row. No row is `upper_bound`, because none is a period-only or scheduled periodic document that I could bound from pre-cutoff knowledge.

**Counts (115 ids).**
- exact: 14 (B005, B006, B007, B008, B009, B014, B015, B107, B108, B109, B110, B111, B112, B113)
- upper_bound: 0
- null: 101

**Rows worth a second look.**
- **B008.** `source_time` is 2026-07-28 (the Reuters piece), but the text also says "no restart statement found by 7 Sep". That claim cannot be public before 7 Sep. I used 2026-09-07 (the conservative, later date) and marked it `looks_inferred`. If you want the Reuters date instead, use 2026-07-28.
- **B107 and B108-B113.** The date comes only from `source_time`. The text has no absolute date, except B109, which cites "13 Aug", earlier than `source_time`. The text does not conflict with `source_time`.

**How I read `confidence_note`.** The procedure does not define the values.
- `consistent`: the text contains a date anchor compatible with the row's date.
- `looks_inferred`: the date rests on `source_time` alone, or the text conflicts with it (B008).
- `n/a`: null rows.

**Unclear in the procedure.**
1. **Timeless statements and operator priors.** Rule 2 covers "period-only or scheduled periodic documents". Many entries are neither: generic structural statements (B001-B004, B010-B013, B114, B115) and "operator prior" entries (B016-B106) that are not source documents at all. I read them literally as "no date, so null". You could argue for upper bounds from general public knowledge, such as "the country's first copper smelter" (B104), but that would invent a date for something that is not a dated document.
2. **`source_time` versus a date in the text.** Rule 1 does not say which wins when they differ (B008). I took the later one.
3. **Mixed sources.** B008 combines a dated article with an as-of note about a later search. The procedure does not say whether such a source dates to the article or to the note.
4. **`confidence_note` semantics.** See above. The procedure says "stated / inferred" in rule 5, but the output schema uses `consistent / looks_inferred / n/a`. I mapped between them as described.
5. **"Post-lock reading" rows (B108-B113).** They read as the operator's own after-the-fact analysis, not public documents, so 2026-08-21 is when the reading was written and not when a document was public. I followed `source_time` per rule 1.
