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

## Your expectation (fill in)

- **Expected verdict** (survives / dies / unreadable), and why:
- **Expected number of qualifying nodes** under the guards:
- **Node map for rounds 1–6** (use the manual map / leave rounds 1–6 out):
- **What result would change your mind about stock pairs** (the v17 row: survives → keep pairs as building
  blocks; dies → drop them; unreadable again → the v15 store is the limit, census-first):
