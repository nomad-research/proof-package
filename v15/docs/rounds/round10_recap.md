# Round 10 lock report: September 7, 2026, paragon GmbH & Co. KGaA filed for insolvency

Round id `01a0801b-19c3-757a-b01f-5e7339e5f5fa`. **Clean**, tag `lag_test`, size band `underread`. First round under v10 and the first under the freeze: a live round (event one day old at intake), the first round through the enumeration path (Q9 pass), per-call due dates, the grid assigned at lock, two early resolutions. This is a lock report, not a scorecard: eleven of thirteen calls wait on due dates between 11 September and 6 December. `nomad_calls_due` lists them; `nomad_close_round` expires whatever is left past due.

## Intake (v10)
- **Enumeration.** The German ad-hoc feed (finanznachrichten.de, real XML where the EQS pages serve HTML shells) enumerated 1–8 September: two candidates on 7 September, an hGears subsidiary item first by write order and the paragon filing second. The human had fixed paragon before enumeration; the hGears skip is written as a Q9 rejection saying exactly that. paragon accepted with the human's Q3/Q4/Q6/Q8 confirmations, prompt overridden to the bare line. Q9 pass, the first since round 5.
- Q1a pass on the feed's own 30-day read (a weak basis: the feed holds six days of items; the post-lock search found the last paragon ad-hoc on 19 June). Q1b computed pass (one distress event in twelve months, the end-2025 bond prolongation vote; none in ninety days; the 2009 filing is seventeen years back). Cap clear; mix after one round: still needs four `headline` and two `lag_test` of the remaining six.
- Q7 computed pass at lock, 12 of 12 calls on open carriers. Seven German carriers registered (XETRA close, EQS ad-hoc, court notices, Bundesanzeiger, Automobilwoche paywalled, East Westphalia regional press, Nordic bond prices).

## Before lock
- Point-in-time reads (as of 6 September): German Wikipedia (revision 4 March 2026): Delbrück, 779 staff and EUR 162m sales in 2023, sites in Suhl, Landsberg, Nürnberg, Markgröningen, St. Georgen, Limbach, Croatia, China, India; the 2009 self-administered plan insolvency; Voltabox spun off 2014, sold 2021; the 2022 liquidity crisis. paragon.ag via Wayback (7 June): the April 2026 decision to move from Prime Standard to Scale. No English article; no archived financial calendar for paragon or any OEM.
- Names book: 12 holders on two nodes, `paragon_automotive_electronics_supply` and `paragon_2027_bond`. Signs at lock: paragon and its site and the notes −, the OEM customers (Volkswagen, BMW, Mercedes) and Voltabox 0, Forvia, Continental and Preh +, the tier-2 class −.
- Synthetics, built before lock with every component cited: `syn.tradability_opposing` (paragon short against Forvia and Continental long, support −0.72 because the short leg's rule, liability periphery, is a net miss) and the new `syn.cross_node_event_pair` (the issuer's equity on the bond node against the competitors on the supply node, support −0.61 with the cross-node discount). The bond node alone is one-sided.
- Scheduled facts: none reachable (no Wayback snapshot of any listed holder's calendar). Catalyst claimed fails on every leg.
- Grid at lock: 13 legs × 4 effect kinds × 4 windows = 208 cells, 100 positive (covered), 108 mirror; 8 calls stamped to their cells. Mirror cells that pass the gate: 24, all `vol` cells on names with listed options, none dated.

## Calls (due dates; two resolved early on stated facts)

| # | Call | Claim | Due | Status |
|---|------|-------|-----|--------|
| 0 | map, branches | self-administration with a plan, as in 2009 | 14 Sep | **miss** (early): regular proceedings, provisional administrator Martin Mucha appointed the same afternoon in all three cases (97 IN 318–320/26). Baseline had it. |
| 1 | sign −, PGN | 8 Sep close ≥ 30% below 4 Sep | 10 Sep | **hit** (early): 1.48 → 0.678, −54%; the ad-hoc landed at 11:51 inside the session. Baseline had it too. |
| 2 | magnitude_order | the notes were already below 60 on 4 Sep (toll booth learned first) | 14 Sep | waiting: today's Frankfurt quote 5.00/5.45, −23% on the day, and an undated pre-filing read near 18; no dated 4 Sep print reachable yet. |
| 3–6 | sign 0 | VW, BMW, Voltabox, Continental: no attributable move vs the DAX | 11 Sep | waiting; day-one prints intraday. |
| 7 | null | no OEM names paragon as a supply risk in 60 days | 6 Nov | waiting. |
| 8 | sign + | continuation and insolvency money stated within 14 days | 21 Sep | waiting; the company expects continuation, the administrator has not spoken, Insolvenzgeld unaddressed. |
| 9 | sign + | notes below 30 by 30 Sep | 30 Sep | waiting; already there on the day-one quote. |
| 10 | lag_band months | resolution in months, production continuing | 6 Dec | waiting. |
| 11 | narrative, VW leg (−) | press says supply to a named OEM is threatened | 12 Sep | waiting; no customer named anywhere on day one. |
| 12 | meta ordering | largest move is the filer's own shares and notes | 21 Sep | waiting. |

Interim scorecard (2 of 13): outcome 0.5, mechanism n/a, baseline 1.0, map 0.0.

## What day one changed
- **The slack claim was wrong.** The company says about 94% of its revenue comes from customers for which it is the sole supplier. The pre-lock basis (dual sourcing) is superseded; the observed slack check fails. Whether an OEM feels it now depends on continuation under the administrator, which is what the null call and the lag call measure.
- **The notes are 2017/2031, not 2017/2027**, extended again at the end of 2025 (EUR 43.65m outstanding), and were already distressed before the filing. The toll-booth reading survives; the label on the node does not, and stays as locked.
- **Regular proceedings, not self-administration.** The one map call went the other way from the 2009 precedent, and the baseline (base rate for a second filing) was right.
- **First zero-latency re-encode on the ledger.** The filer's own equity re-encoded by the close of the event day (attributed, out of band); its leg reads `recovered`. Every other leg is `unrecovered` with a forcing date; `nomad_exposure` sums them per node until their calls fall due.

## Fetcher reach on day one
Read: EQS ad-hoc and corporate releases, the court orders with case numbers, BondGuide, Anleihen-Finder, regional coverage, XETRA closes, an intraday bond quote. Not read: finanzen.net (403), comdirect (401), insolvenzbekanntmachungen.de (TLS failure), Automobilwoche (paywall), the OEM IR calendars (no Wayback snapshot; now on the snapshot list).

## For the human
- Score the 11 September batch (VW, BMW, Voltabox, Continental, then the VW narrative row on the 12th, which gates nothing here since the structural VW call is due a day earlier) with `nomad_calls_due` and `nomad_score_call`; the blind view for the second scorer regenerates per batch.
- Ratify the hGears skip as a selection note or supersede it with a real failing question.
- The mirror's 24 gate-pass `vol` cells need dates: the OEMs' Q3 reporting dates are knowable from their IR calendars, which the fetcher cannot snapshot; a manual `nomad_mechanical_add` from the calendar pages would date them within the freeze without a protocol change.
