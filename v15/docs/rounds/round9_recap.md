# Round 9 recap: August 12, 2026, a trichloroisocyanuric acid fire at a container storage facility in Sauget, Illinois

Round id `01a07e03-1a20-7445-a4de-634c281d09de`. **Learning class**, tag `lag_test`. First round under v9: computed Q1b and tag at intake, synthetic attempted before lock with cited components, scheduled-facts feed read pre-lock and post-lock, catalyst checks computed per leg, fetch paths on the carriers, arming status per leg, divergence from the sign at lock, notebook rows written at scoring.

**Why learning.** The event was submitted on 8 September, one day inside the 28-day lag (clean window ended 11 August), so intake refused it as clean and it was declared learning. Q2 is a computed pass (event after the 30 June cutoff), every falsifier window was set to close by 26 August, and nothing else about the round is learning-shaped. The human can move it to clean with `nomad-harness reclassify <round_id> clean --reason ...` on or after 9 September; the ledger keeps both rows.

## Intake (v9)
- Q1b computed: no disruption on the node on the ledger; the only registry reader for the kind (TCEQ STEERS) is Texas-only and reset the connection; Wayback had no snapshot of it. Pass.
- Q1a: the human supplied the event without a 30-day window search and the operator cannot run one pre-lock, so intake took `unknown`. Post-lock the search found nothing on the pool-chlorine channel between 12 July and 12 August; Q1a was superseded to pass with that basis. Tag `lag_test` stands.
- Cap: not applicable to a `lag_test` round (last three admitted: weather, lag_test, weather).
- Q9: no selection window was fixed and no rejections were written; the human handed over one event. Q9 stays unknown, and the selector's streak is unchanged.
- Q7: computed pass at lock, 11 of 11 non-meta calls on open carriers; ICIS (the only trichlor price series) is unreachable and was not cited.

## Before lock
- Point-in-time fetches (13 logged, two duplicated by a console-encoding failure): Wikipedia "Trichloroisocyanuric acid" (revision 4 Aug: reacts with a little water into chlorine gas and nitrogen trichloride; a containerised Chinese import), "Sauget, Illinois" (revision 6 Aug: incorporated for the Monsanto plants, the village runs the industrial wastewater plant, sits on the American Bottom), Pool Corporation and Leslie's (June revisions), and the ContainerPort Group site via Wayback (16 Jun: a drayage, depot, transloading and warehousing operator). No article for ContainerPort Group, Bio-Lab or KIK.
- Names book: 16 holders on two nodes. `us_trichlor_supply`: the yard and its private operator (−), Chinese exporters, BioLab/KIK, Clearon and Occidental (+), Pool Corp, Leslie's and Hayward (+), pool owners (−). `sauget_industrial_corridor_access`: the yard (−), Afton Chemical's and Eastman's Sauget plants and their listed owners (−), the corridor neighbours (−). CIKs and IR pages recorded for the six listed names.
- Touched set: 15 rows, every row citing a mechanism (C1). Synthetic under `syn.tradability_opposing`: **not built on either node**, four listed longs and no listed short on the material node, two listed shorts and no long on the corridor node. The refusal is the round's arming verdict in advance.
- Scheduled facts (A2, as of 11 Aug): EDGAR gave every listed name's past results dates; the IR pages had no usable snapshot (Hayward's and Eastman's archived pages carry no dates). Catalyst check written on 16 legs: claimed fails everywhere, no future fact knowable by the event date.
- Carrier check: 7 of 8 intended carriers open; six new open carriers registered for the kind (NASDAQ/NYSE close, NRC incident reports, Illinois EPA, USCG bulletins, St. Louis local press, Pool & Spa News).

## What happened
Fire at 12:45 a.m. on 12 August at ContainerPort Group's yard on Sauget Industrial Parkway, up to 15 pallets of trichlor, chlorine plume. Shelter-in-place over roughly four square miles and 3,400 homes and businesses in Sauget, Cahokia Heights and East St. Louis, extended north as the plume shifted, lifted at 8:53 a.m.; schools closed for the day; rail operations in the area shut; a sand berm for runoff; no injuries; EPA and Illinois EPA had no violations on file for the site. No report names the owner of the material. After the close the same day, Leslie's released fiscal Q3 results (sales −8.4%, outlook withdrawn, strategic alternatives) and fell 42% on 13 August.

## Calls and outcomes (operator / second scorer)

| # | Call | Claim | Outcome | Mechanism | Notes |
|---|------|-------|---------|-----------|-------|
| 0 | map, branches | closes shared space beyond the yard | hit, branch `corridor_closure` | right | Four square miles, 3,400 homes, schools, rail. `lib.toxic_release_shared_space` gets its first carried trial. |
| 1 | sign 0, POOL vs XRT | no attributable move | hit | right | +0.7, −2.5, −0.7 pt over 13–17 Aug; the 14 Aug slide is the Leslie's read-across, nothing cites the fire. |
| 2 | sign 0, LESL vs XRT | no attributable move | hit | right | −41.7% on results released after the close on the event date. No fire attribution anywhere. Both scorers flag it: the leg was swamped by its own tide; `lib.tide_hides_event` was the truer citation. |
| 3 | sign 0, OXY vs XLE | no attributable move | hit | right | −1.5 pt on 13 Aug, uncited. |
| 4 | sign 0, EMN vs XLB, conditional on `corridor_closure` | no attributable move | hit | right | Branch arose. +2.2 pt on 13 Aug, over the size line but nothing connects Eastman to Sauget; survives on the attribution clause alone (second scorer's words). |
| 5 | null, no FM or allocation notice in 14 days | | hit | right | Nothing from any producer, importer or distributor. Coverage thin (trade press via search only). |
| 6 | sign 0, no trichlor price move attributed | | hit | right | The only "chemical fire raises concerns" piece is Westlake 2020. Coverage thin. |
| 7 | sign +, Coast Guard bulletin, conditional | | **miss / unverified (dispute)** | n.a. | Ten local reports never mention the river; the sector's own page returned 403. Operator read the silence as a miss, second scorer as a coverage gap. Open for the human. |
| 8 | sign +, NRC report filed | | unverified | n.a. | No report number surfaced; the FOIA database was not searched directly. |
| 9 | lag_band days, 3 factors | out and lifted within days | hit | unknown | Factors 0 and 1 hit in hours; the cleanup factor (against, not binding) unverified: nothing reported on the yard after 12 Aug. |
| 10 | narrative, POOL leg (+) | trade or local press says it tightens supply | miss | n.a. | The channel did not say it: a hazmat and school-closure story only. |
| 11 | meta ordering | largest move is physical | hit | right | Baseline "the pool names move" was literally true for an unrelated reason; scored baseline hit, so this row carries no edge. |
| 12 | meta one-trade, long HAYW vs LESL | | hit | n.a. | +49 points over five sessions, all of it the retailer's results. A hit the event did not earn. |

Scorecard: outcome 0.75, mechanism 0.80, baseline 0.41, edge +0.39, map 1.0, unverified 1 of 13, zero quarantined, zero misreads, one dispute pending. Bias over clean rounds unchanged (24 compared: lenient 2, under-informed 6, self-stricter 2).

## Arming
Sixteen legs, none armed. Six listed legs checked and gate-fail (POOL, LESL, OXY, HAYW, EMN, NEU), ten unchecked (private operators, plants, aggregates). No synthetic, so no `gate_pass_undated` row this round. Post-lock every listed leg's structural sign was revised to 0 in a new row; the basket shows the six revisions as `revised_sign` and computes divergence from the signs at lock: zero divergent legs (the narrative row said + on a + leg, and the channel did not speak).

## The scheduled-fact the feed missed
Leslie's results landed on the event date. Their date was public from 5 August in a press release ("to report third quarter 2026 financial results on August 12, 2026"). The feed reads EDGAR item 2.02 filings (which exist only once results are out) and IR events pages through Wayback (Leslie's page had no snapshot; the US pages that do render their calendars with scripts). So the store held no future fact for any leg on 11 August, the catalyst predicate failed everywhere at claim time, and the one dated statement in the window was the one that made every pool-name leg unscoreable for the event. The cheap fix is a third source: the results-date press release itself (8-K item 7.01 or the wire), or manual entry from the announcement. This is the same gap A4 measured on round 8 (8 legs dated in hindsight, 0 in advance) and it says the forward feed, not the hindsight feed, is what dates a leg.

## Library
`lib.equity_visibility_ratio` 3.46 → 4.96 (15 carried trials, 14 hits; learning-class quality). `lib.cut_into_glut_silent` 0.72 → 0.97 (6 trials; still candidate: no clean positive hit). `lib.toxic_release_shared_space` first trial, 0.3. `lib.headline_names_what_reopened` unchanged (mechanism unknown on the lag call). Nothing validated or demoted. The disputed Coast Guard row cites no rule.

## Lessons
- **A yard is not a plant.** Fifteen pallets in a container depot is below every visibility ratio in the book; the only transmission was physical (eight hours of shelter-in-place, rail, schools) and the map call was the round's one real claim. Everything listed went silent, as called.
- **One-sided nodes cannot arm.** With no listed holder on the losing side of the material node and no listed holder on the winning side of the corridor node, the synthetic rule has nothing to build from. The E4 claim did not get a data point.
- **The tide was a results date.** Round 9's tide was not a macro move but the named retailer's own earnings on the event day. `lib.tide_hides_event` was cited on the touched set and nowhere on a call; the LESL row should have carried it.
- **Forward scheduled facts need the announcement, not the filing.** See above; §A's third source is the results-date press release.
- **Fetcher reach.** RiverBender, FOX 2, HazardEx and the Coast Guard sector page return 403; the NRC database is a quarterly spreadsheet. Two calls were unverifiable for that reason and one became the round's dispute. Registry readers for Illinois and for the NRC are the next carrier work.
- **Selector discipline** still has no data: the human supplied the event and no window was fixed. Q9 stays unknown for the fifth round running.
