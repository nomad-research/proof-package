# Round 8 recap: July 27, 2026, a lightning-triggered process upset at a refinery in Sweeny, Texas

Round id `01a07c3d-f101-7627-b48a-ffd4eca12d7f`. Clean. First round under v8: carrier-density intake (refinery: EIA, TCEQ emissions event, company IR page, exchange filings all open), point-in-time fetches before lock, a map call with branches, a conditional row, a narrative row, a synthetic leg, and the one-trade statement. The selector did not pass a rejection list, so `rejections` is empty and Q9 stays unknown.

## Before lock
- Point-in-time fetches (logged): Wikipedia "Sweeny Refinery" has no article; Wikipedia "Phillips 66" as of 21 Jul 2026 confirms the CPChem JV; Wayback of the Phillips 66 Sweeny page (snapshot 11 Apr 2026) lists the refinery's units and location. The map layer (one refinery, owner Phillips 66) was a lookup, not a coin flip. The CPChem page had no snapshot.
- Touched set: eight rows, degrees 0 to 3 (refinery, Phillips 66, CPChem complex, CPChem, Chevron, Valero, Marathon Petroleum, the Gulf Coast gasoline market).
- Synthetic: `syn.tradability_opposing` built mechanically from Valero (+), Marathon Petroleum (+) and Phillips 66 (−). Support 0.52 = 0.72 (weakest component) × 0.85². The first build ran before lock and had no support because no rule was cited yet; the second, after lock, did. Build synthetics after lock.
- Carrier check at lock: nothing unreachable, Q7 computed pass.

## Calls and outcomes (operator / second scorer; zero disputes)

| # | Call | Claim | Outcome | Mechanism | Notes |
|---|------|-------|---------|-----------|-------|
| 0 | map, branches | confined to Phillips 66 refinery units | hit, branch `refinery_only` | n.a. | Reuters names the P66 TCEQ entity; no CPChem event found. Coverage thin: the TCEQ filing itself was unreachable to the fetcher. |
| 1 | sign 0, PSX vs XLE | no attributable move | hit | right | +0.4, −1.4, +1.3 pts over 28–30 Jul; UBS target raise the same day; nothing cites the upset. Baseline differs between scorers on its letter (dip on the day) but that is not a dispute. |
| 2 | sign +, TCEQ report within 7 days | filed | hit | n.a. | Established through the Reuters wire that quotes the filing. |
| 3 | sign 0, Gulf Coast crack | no attributable move | hit, quarantined | wrong | Silence came from event size under a tight market, not from slack; the cut-into-glut rule did not operate. No credit. |
| 4 | lag_band days, 3 factors | units back within days | unverified | n.a. | End time sits in the unread TCEQ filing. |
| 5 | sign +, ethylene, conditional on `complex_wide` | | untestable, weight 0 | | Branch did not arise; never touched a rule. |
| 6 | narrative, PSX leg | press says it weighs on PSX | miss | n.a. | Channel did not say it. Structural sign moved to 0 post-lock, so the basket shows one divergent leg. |
| 7 | meta one-trade | long VLO vs PSX, 5 sessions | hit | n.a. | +0.86% vs −0.78%, but the move was group-wide on 30 Jul. |

Scorecard: outcome 0.71, mechanism 0.60, baseline 0.43, edge +0.17, map 1.0, one quarantined hit, one dead-branch row. Second scorer agreed on every outcome and mechanism. Bias over clean rounds: lenient 2, under-informed 6, self-stricter 2 of 24 compared.

## Arming
Three legs checked plus the synthetic. Every natural leg fails the tradability gate's single form. The synthetic passes the pair form (two listed longs against one listed short on the same node), which is the E4 claim's first data point, but the catalyst-class predicate fails on every component, so nothing armed. A gate holding on one leg no longer counts as the round arming; the scorecard was corrected and re-appended after this round exposed that.

## Library
`equity_visibility_ratio` 2.86 → 3.46 (10 carried trials, 9 hits). `cut_into_glut_silent` unchanged at 0.72 candidate: its hit here is quarantined. Nothing else cited.

## Lessons
- **Carrier density passed at intake and failed in practice.** TCEQ and the Phillips 66 IR page are open to a browser and unreachable to this fetcher (connection resets, DNS timeout). The registry needs an `access` reading per fetch path, or the point-in-time fetcher needs a Wayback fallback for live pages. Three of eight calls were unverified or thin because of it.
- **Recurring node.** Sweeny filed upsets in January, on 13 July and on 27 July 2026; first traversal fails at both levels. The round is a weather-rule case, not a lag test, and criteria_pass should be read with that in mind.
- **Branches worked as designed.** The map call carried real uncertainty (shared utilities), the conditional ethylene row died with its branch at weight 0, and no rule was touched by it.
- **The narrative row measured something.** The press carried a bare TCEQ note and no framing against the stock; structure and narrative diverged only because the structural sign was revised to 0 after lock.
