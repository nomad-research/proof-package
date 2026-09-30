# V1 variance check (declared before any second session ran)

Question: if the same round is authored again by a fresh, independent session from the same prompts, how much of the result survives? This bounds how much of V1 is the mechanism and how much is session noise. It does not change V1's verdict, gates or frozen answers.

Rounds (fixed by rule, not picked): every third of the 17 scored rounds sorted by id from index 0 -> 155674, 287395, 606437, 655630, 680764, 850741; plus the first and fourth of the 7 no-instrument rounds sorted by id -> 125877, 624242. Eight rounds, each two stages, same model (`claude-opus-5-5`), same one-line instruction, same audit. Nothing from the first session is shown to the second. A failed audit voids that round's second run; no replacements.

Compared per round: is stage 1a's prompt byte-identical to the first run's, is the primary basket the same, did `no_instrument` agree, overlap of the hedge events chosen (Jaccard), and floor lift and realised C-D of the second run scored with the frozen scorer. Reported as counts; no test or gate.

Tooling: `v1_variance.py` (wraps the frozen `v1_run.py` and `v1_score.py` without editing them; writes only to `variance/`, never to `packets/` or `results/`). Prompts live in `/tmp/claude-0/v1_prompts_var/`.
