# Round 5 — 2026-07-15 — fire at a refinery complex in Gelsenkirchen, Germany

**Round id:** `01a078f5-565b-769c-8238-058fa471626e` · **Class:** **clean** (contamination none; Q2 computed pass, event inside the window 2026-07-01 to 2026-08-10) · **Operator:** claude-fable-5-1 (cutoff 2026-06-30, from `model_cutoffs`) · **Played:** 2026-09-07 through the harness API (the session's MCP server was still the pre-tightening build; same functions, same ledger) · **Scorer:** self (B2 second scorer starts at round 6)

**Firewall:** Claude Code rounds are hook-enforced (all MCP retrieval surfaces now covered; denials logged to `hook_denials`). Chat rounds remain soft: there the wall is a promise.

## What it was

BP's Gelsenkirchen refinery, Scholven site: a fire at ~17:00 in the **diesel desulphurisation unit**, a sulphur-gas line isolated and burned out, under control the same evening, **no injuries**, NINA/Katwarn warning for Marl, Gladbeck, Dorsten and Herten. Product loadings had already been halted since 13 July for pipeline maintenance, and fuel prices were being driven by the Hormuz blockade reinstated on 14 July. The consequential trace was elsewhere: **BP suspended all benzene deliveries**, and **INEOS Phenol declared force majeure on European phenol and acetone** with pro-rata allocation (benzene → Marl cumene → Gladbeck phenol), still in force on 27 July. The site's sale to Klesch Group, agreed in March, **completed on 3 August** on schedule.

## Scorecard

| | |
|---|---|
| outcome_score | 0.73 |
| mechanism_score | **0.32** (three hits quarantined by the operator) |
| baseline_score | 0.00 |
| edge_vs_baseline | +0.32 |
| tradability gate | claimed fails, observed fails → **not armed** |
| unverified | 1 of 9 (coverage thin: restart date and lifting notice behind paywalls) |

## Calls

| # | Call | Result | Note |
|---|---|---|---|
| 1 | Map: BP Scholven site under a sale process, integrated petchem, contained in a day, no fatalities | hit, **quarantined** | Right on all that, but the chemical offtaker that mattered was INEOS's benzene chain, not the polyolefin producer. The rule cited did not carry a map claim; credit withheld. |
| 2 | Affected unit out weeks not months; complex keeps running | unverified (thin) | Sources conflict (one unit vs several vs "full halt"); no restart date found; force majeure still in force 27 Jul, "temporarily shut" by 8 Aug. |
| 3 | No attributable step in Rhine-Ruhr fuel differentials | hit, **quarantined** | Argus: no additional market effect, because loadings were already halted and Hormuz set prices. Not the slack mechanism I rode. |
| 4 | Force majeure on petchem offtake within 14 days **if** the petchem side burned; none if only fuels | **miss** (mechanism right) | Fuels unit burned, and the notice came anyway: the whole site's deliveries stopped. Conditional was a misread. |
| 5 | Magnitude ordering: physical > offtake > fuel differentials > equity | **hit** | Held exactly. Offtake layer (force majeure, 15 rail cars cut to 10) was the visible one. |
| 6 | Null: no attributable equity move within 3 sessions | hit (0.2) | BP inside a +10% oil week; nothing attributed. |
| 7 | Null: fails tradability gate at event time | hit (0.2) | Supermajor owner, private buyer, private offtaker; every holder on the node is sign −. Time-bounded falsifier this time. |
| 8 | Sale/restructuring timetable unchanged by the fire (no-mechanism) | **hit** | Completed 3 Aug as announced. |
| 9 | Smoke warning on the day; no lasting regulatory constraint | hit, **quarantined** | Both true; the cited rules (fatal-accident inspection, liability periphery) did not operate. |

## Predicates (claimed → observed)

first traversal event unknown → holds · **node fails → holds** (my class-level prior was not an observation) · slack fails → fails (but for a different reason than slack) · tradability fails → fails · existence floor unknown → holds (the force majeure) · path composition unknown → fails (the benzene link was stated in trade press since 2024; I did not hold it) · bounded-channel fails → fails · catalyst class unknown → holds (dated sale completion, announced turnaround).

## Library (weights under A12)

- No rule validated. Several now sit above the threshold on weight but with only one clean round: `lib.cut_into_glut_silent`, `lib.toll_booth_learns_first`, `lib.equity_visibility_ratio`. A second clean round with a positive hit would validate them; a miss would not.
- `lib.force_majeure_fast_carrier` took a clean-round miss on call 4 and is now negative, which flagged the plant-outage composition for review and leaves the new hypothesis unable to arm.
- Harvested candidates: a fire in one unit stops deliveries of unrelated products · a pre-existing logistics stop masks an outage · map and identity calls carry no mechanism · a single-supplier feedstock link is a hidden node.

## Names book and positions

Added BP p.l.c., the Ruhr Oel / BP Gelsenkirchen site, Klesch Group, INEOS Group, INEOS Phenol Gladbeck (substitutability low), INEOS Marl cumene. Node `bp_gelsenkirchen_scholven_output`: all sign −, no listed pair.

## Hypothesis opened

Single-supplier feedstock links: a refinery-side stop produces a downstream force majeure within 14 days and a contract-price rise the month after. support_weight −0.7 (cannot arm until the force-majeure rule recovers weight). Arming: existence floor, slack; disarming: falsifier, staleness.

## Housekeeping

- Two evidence rows (Dorsten Online, Radio Vest) were written twice: the first evidence batch failed on a 503-character excerpt after two rows had gone in. Append-only, so both copies stay; the resolutions cite the second batch.
- BP.com pages return 403 to the fetcher; ICIS and ChemWeek are paywalled. The restart date and the force majeure lifting are the two facts B4's daily ingest would have caught.

## After the review (applied 2026-09-07)

- **A13**: call 4 is now a recorded misread (miss, mechanism right). `lib.force_majeure_fast_carrier` is back to +0.3 with no misses; the plant-outage composition is unflagged; the single-supplier hypothesis has support 0.3 (still below the 1.0 threshold, so still unarmed, but for the right reason).
- Round 5 stays as scored (mechanism 0.32; the three self-quarantines stand, since call 1 was locked as `meta` before `map` existed). Scorecard now reports `misreads = 1`.
- Tide note recorded on the round (`round_notes`, kind `tide`) and the tide rule proposed as a candidate.
- B4 targets opened: the desulphurisation unit restart date and the INEOS force majeure lifting. Three node facts recorded, including the single-supplier benzene dependency with `knowable_from = 2024-02-14`, which is the date the operator should have held it.

## Programme

Clean: 1 scored, arming rate 0/1, mechanism 0.32. All rounds: 5 scored, arming rate 0/5. Chain verified; chain heads in the export.
