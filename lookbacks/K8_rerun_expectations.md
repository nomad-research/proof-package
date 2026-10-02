# K8 re-run on the back-filled record — expectations (TO BE FILLED IN BEFORE THE RE-RUN)

*The v17 checkpoint says to write down what you expect first. Fill this in and commit it; only then run
`python lookbacks/k8.py v15/nomad_harness.db --overlay v15_overlay/knowable_from_backfill.json`.
Nothing here has been run on the overlay.*

## What the back-fill changed (known before you write anything)

- Positions with a `knowable_from`: 59 → **73** of 200. Only 14 of the 141 undated positions could be dated
  (`lookbacks/backfill/RESULT.md`); 127 are operator priors or generic statements with no source document.
- Rounds 1–6 still have no node rows (the `touched_set` table starts later), so K8 reads on rounds 7–17 only
  unless you pre-register a manual node map for 1–6 (the sensitivity script has one; using it in the
  verdict is your call, and it must be decided here).
- "Listed before the event" is still unenforceable: v15 stores listed status as of September 2026.

## Rob's statement, recorded verbatim (2026-09-30, in the build session, before any re-run)

> "The answer is yes but there's a twist, they don't hedge in the typical sense of the word. They narrative hedge not
> structurally hedge. Two long narratives could hedge each other in this case over different correlated theses."

This is the requester's own wording. The four fields below are **not yet filled**: the statement says "yes", and it says the hedge
is narrative and not structural, but it does not say what verdict K8 as pre-registered (which counts structural opposite holders and
options) should return, how many nodes qualify, or what to do about rounds 1–6. The builder has not filled them in on Rob's behalf.
**K8 has not been re-run.** (Rob wrote earlier that he had written expectations elsewhere; they were not found in the repo, in
issue #11 or in the session transcript.)

## Your expectation (fill in)

- **Expected verdict** (survives / dies / unreadable), and why:
- **Expected number of qualifying nodes** under the guards:
- **Node map for rounds 1–6** (use the manual map / leave rounds 1–6 out):
- **What result would change your mind about stock pairs** (the v17 row: survives → keep pairs as building
  blocks; dies → drop them; unreadable again → the v15 store is the limit, census-first):
