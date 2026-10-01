# Nomad thesis-first hedging: evaluation of the evidence (2026-10-01)

## Question

The question is whether a session can write a thesis, say how it fails, and choose hedges on Polymarket that are tied to that failure by causal claims. Those hedges are sized by exact payoffs. They should give a better result than plainly holding less of the primary (D) and better than a random or blind statistical hedge.

## Evidence base

All V1 and V1b events resolved after the model's training cutoff. Every session used the same frozen prompts, scorer and transcript audit.

| Study | Status | Rounds authored | Scored | Primary lost |
|---|---|---|---|---|
| V1 | registered, frozen | 24 | 17 | 7 |
| V1b | registered before any session, the rest of the same pool | 33 | 24 | 8 |
| V1 + V1b pooled | post-hoc secondary | 57 | 41 | 15 |
| V3 | forward test, frozen | 30 | 0 | outcomes due 15 Oct 2026 to 10 Jan 2027 |

Supporting checks:
- Variance re-run: 7 rounds.
- Blind statistical hedge: the registered B arm.
- Structural split: hedges on the same underlying versus cross-entity hedges.
- Claim-informativeness test.
- Hedge-timing test.
- V0 market audit.

## Results

**1. The registered verdicts are inconclusive, and both studies miss the same gate.**

| | V1 | V1b |
|---|---|---|
| Scored rounds (gate ≥ 20) | 17, fail | 24, pass |
| Primary losses (gate ≥ 10) | 7, fail | 8, fail |
| B1, claims hold (≥ 0.90) | 0.88 | 0.92 |
| B2, mean C−D (90% CI) | +3.9 (−2.7, +10.7) | +1.8 (−4.8, +8.4) |
| B3, C beats random hedge (≥ 65%) | 71% | 64% |
| B4, retention (≥ 0.5) | 0.78 (4 rounds) | 0.33 (8 rounds) |

Neither study has a passing B2. V1b would not pass even if its gates were met, because B2's interval includes zero and B4 fails.

**2. Pooled, which is post-hoc but meets the gate sizes (41 scored, 15 losses), there is no advantage over de-risking.**
- C minus D is +2.7, with a 90% interval of −2.0 to +7.5.
- Mean payoff on $100: P (the primary alone) −2.9, C (hedged) 0.0, D (de-risked) −2.7.
- B1 sits exactly at 0.90 (37 of 41).

**3. The measured advantage comes from rounds where no hedge was needed.**
- Primary lost (15 rounds): C−D is −2.6 (−10.9 to +4.6). When it mattered, the hedge did not beat holding less.
- Primary held (26 rounds): C−D is +5.7 (+0.2 to +12.1). The hedge ate less of the upside than de-risking did.

**4. Cross-entity hedges, which are what the mechanism is supposed to deliver, show nothing.**
- Cross-entity (32 rounds): C−D is +0.9 (−4.4 to +6.0). B1 is 0.88. Retention is 0.40.
- Same-underlying (9 rounds): C−D is +9.1 (+0.4 to +21.8). B1 is 1.00.

The only interval clear of zero belongs to the hedges whose lift is arithmetic: the same Fed meeting, a by-date rung, a launch versus its FDV.

**5. Two signals are positive, and both are weak.**
- **Hedges tend to pay when needed.** The realised hedge payoff averaged +7.5 in rounds where the primary lost and −1.7 where it held. The difference is +9.1, with a one-sided permutation p of 0.063 over 41 rounds. The hedges point the right way, but not by enough to beat cutting position size.
- **Claims carry information beyond lock-time prices.** 16 claims had their "if" side happen. Their "then" side held 75% of the time, against a market-implied 47% at the lock. The excess is +28 percentage points (90% interval +10 to +45). For cross-entity claims alone it is +23 points on 10 claims.
- **Caveat on the claims signal.** The benchmark is the unconditional lock price, so any genuinely correlated pair would beat it. A random contract-side would score zero, because calibrated prices make its expected excess zero. My placebo returned zero for a mechanical reason, since it scored both sides of every contract. It is not evidence.

**6. The session hedge beats a blind statistical hedge.**
- On the 15 rounds where both exist, the session hedge did better in 12, with a mean of +14.9 (+4.1 to +24.3).
- The blind hedge did worse than de-risking (−13.5).
- The blind arm is formally infeasible: only 11 V1 rounds and 8 V1b rounds had 30 days of pre-lock price history, against the 12 the registration needs. These comparisons are therefore descriptive.

**7. Choosing the hedge is fairly stable; deciding whether to hedge is not.**
- When a fresh session re-ran a round that had hedged, its hedge events overlapped 0.67 to 1.00 with the original.
- Both no-instrument rounds that were re-run found a hedge the second time.

**8. The venue is the binding constraint.**
- No-instrument rates: V1 7 of 24, V1b 5 of 29, V3 4 of 30.
- The decliners mostly wanted rates, commodities, FX, freight or national-politics markets that Polymarket does not list.
- 11 of 17 hedged V1 rounds hedged inside the primary's own domain. Most of the hedges that worked were same-asset or same-event structures.

## What the registered controls could not show

**The mismatched-thesis control (M) is degenerate.** Shifting hedges round by round leaves their total unchanged, so mean(M−D) always equals mean(C−D). It cannot detect anything on the mean. Any future study should replace it with the hedge-timing permutation test from result 5.

## Verdict

**The mechanism is not supported as a way to beat plain de-risking.**
- The point estimate of C−D is small and positive, with an interval around zero.
- The rounds that should show the effect (the primary lost) and the hedges that should show it (cross-entity) show none.
- The hedges and claims are not empty: they are directionally right, they beat a blind statistical picker, and the claims beat lock-time prices. But the edge they find is too small, after fees and the cost of the hedge, to beat simply holding less.

**What would change this.**
- V3, the forward test, is the one confirmatory test left.
- If V3's cross-entity rounds show C−D clearly above zero with claims holding at 0.90 or more, this verdict should be revisited.
- If V3 repeats the pattern above (gains only in rounds where the primary held, cross-entity C−D near zero), the thesis-first hedge should be dropped as a source of edge. What remains useful is the exact-payoff solver and the claim-checking machinery.

**Spending.** Nothing here justifies paying for fine-tuning (Laya) or putting money at risk.

## Files

| Topic | Files |
|---|---|
| Registered studies | `V1_prereg.md`, `V1b_prereg.md`, `V3_prereg.md` |
| Study results | `v1_study_report.json`, `v1b_study_report.json` |
| Pooled, structural and lost/held splits | `v1_pooled_report.json` |
| Claim informativeness and hedge timing | `v1_evidence.py`, `v1_evidence_report.json` |
| Blind arm | `v1_blind.py`, `v1_blind_report.json`, `v1b_blind_report.json`, `v1_blind_pooled.json` |
| Variance re-run | `V1_VARIANCE_RESULT.md` |
| Structural split, V1 | `V1_STRUCTURAL.md` |
| Structural flags, V1b | `v1b/v1b_structural_flags.json` |
| Market audit | `V0_RESULT.md` |
| V3 authoring (outcomes pending) | `V3_AUTHORING_RESULT.md` |
