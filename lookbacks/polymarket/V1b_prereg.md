# V1b: V1 on the rest of the frozen pool (registration, written before any V1b session)

**Why.** V1 was inconclusive on its gates (17 scored rounds of 20; 7 primary losses of 10). V1b authors the remaining eligible events of the same frozen pool so the question can get an answer. It is written after V1's results were seen, so it is registered as its own study with its own verdict. It is not merged into V1, and V1's verdict stays inconclusive.

**Rounds (fixed by rule, no choice).** Every event in `v1_pool.json` (frozen, sha256 `069ed732...`) that shows at least 3 tradable contracts at its lock (`v1_survivors_recount.json`) and was not a V1 round, a V1 replacement or a replaced V1 draw: **33 events**, listed in `v1b/v1_rounds.json`, in ascending id. They include the 8 events left in V1's reserve. All resolved after 2026-06-30. There is no reserve: a round voided for a data or harness reason is reported as void, not replaced.

**Method (unchanged).** The frozen `v1_packet.py`, `v1_run.py` and `v1_score.py`, reached through `v1b_run.py`, which only points them at `v1b/` and a separate prompt directory. Same model (`claude-opus-5-5`), same one-line instruction, same two stages, same audit, same one registered return of an invalid answer, same recall and leak rules, same replacement-free treatment of `no_instrument` (unscored).

**Bar (V1's, restated).** Gates: at least 20 scored rounds and at least 10 where the primary lost more than $10. B1 in-set share at least 0.90; B2 mean C minus D positive with the 90% bootstrap lower bound above zero; B3 M shows no effect and C beats R's median in at least 65% of rounds; B4 retention at least 0.5. Verdict: inconclusive below the gates; dead if B1 fails or B2's mean is not positive; pass only if all hold. Structural (same-underlying) hedges are flagged by the V1_STRUCTURAL.md rule **before scoring** and reported as a separate row.

**Secondary (declared now, gates nothing).** A pooled V1 plus V1b figure, labelled pooled and post-hoc.

**Order.** All 33 rounds are authored and their answers frozen by hash (`v1b/v1_answers_manifest.json`) before any V1b round is scored.
