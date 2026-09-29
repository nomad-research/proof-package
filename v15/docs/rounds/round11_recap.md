# Round 11 recap: August 26, 2026, the Commission's Statement of Objections on the UPM/Sappi graphic-paper joint venture

Round id `01a0816a-0e1d-7619-b83d-2995e6bb75df`. **Learning class** (see the contamination note below), tag `late_headline`, size band `underread`. First round under v11: gates reduced to Q3/Q8/Q9, first traversal as a tag, legs generated mechanically from the positions store, the grid assigned point-in-time, six of nine calls resolved and three waiting on due dates.

## Why learning, and it is the operator's fault

Before this round was submitted I ran a web search on the event. Round 10 was sitting `partially_scored`, so the firewall allowed it: v11's rule is "nothing is pre-lock", and round 11 did not exist yet. The search returned aftermath — trade-press coverage dated 3 September and the Commission's own release — which is past the time wall. The round is therefore declared learning at intake, by the operator rather than by Q2: **its calls are recorded and scored but never enter rule weights, validation or calibration; its measurements do count** (v11 §A1). That is exactly the case §A1 was written for.

The design finding is worth more than the round: *"nothing is pre-lock" does not protect a round that has not been submitted yet.* The enumeration path is what closes the hole — candidates arrive as bare prompts from feeds and the round is submitted before anything is read. Round 11 did not come through it.

## Intake (v11)
- **Q9 passes** on the human's own sweep: the window was fixed on the ledger (source, start date 1 August) and three skips were written before the qualifier — mining licence revocations (Q8: no clean single date), the Indigo West/Central cable cuts (`skip`: passed over, not failed — a recurring-incident class that does not answer the lag question), and the UK/Shenzhen HYT block (Q2: 25 June is pre-cutoff). This is the v11 relaxation working: a logged human sweep is as verifiable as the tooling.
- **Q1a fails** and no longer refuses. LOI 4 Dec 2025 → definitive agreement 28 May 2026 → Phase II → this Statement of Objections: a further instalment, so the round is tagged `late_headline` and is filtered out of the lag question at analysis time rather than rejected at the door.
- **Q1b passes**: nothing on the ledger for this node, and EU merger control against these two is not a recurring-disruption category the way ports, refineries and recalls are.
- Q7 computed pass at lock, 8 of 8 calls on open carriers. Five carriers registered: EC press corner, MLex (paywalled), paper trade press, Nasdaq Helsinki close, JSE close.

## The footprint
Fourteen legs, all `leg_source = mechanical` — generated from the positions store rather than chosen (§A3), which on a learning round is the point. One market node (`eea_graphic_paper_supply`) and one deal node (`upm_sappi_jv_completion`).

Signs at lock: the producers negative (UPM, Sappi, Stora Enso, Norske Skog, Arctic Paper, Burgo — a blocked or remedied JV leaves the structural overcapacity in place), the customer side positive (Sanoma, Mondadori, Elanders, the publisher class — they keep the fragmented supply they buy from).

**The first natural opposing-listed pair in the programme.** `syn.tradability_opposing` built with eight listed components, five short against three long on the same node, support 1.94 — the highest support any synthetic has carried. `syn.cross_node_event_pair` also built (five components, support 2.68). The deal node alone is one-sided and refused, with the message saying so.

Grid at lock: 14 legs × 16 cells = 224, of which 98 positive and 126 mirror, four calls stamped to their cells. The Commission's own decision deadline (11 November) went in as a `mechanical` fact and dates eight mirror cells.

## Calls

| # | Call | Due | Outcome |
|---|------|-----|---------|
| 1 | narrative, UPM leg (−): the trade press says the JV is likely to be blocked or abandoned | 31 Aug | **miss** — PaperAge, Lesprom, Wood & Panel, Global Wood Markets and Pulp & Paper News all report the step and the parties' answer; none predicts the outcome. Scored first, as v11 requires, before the structural call on the same leg. |
| 2 | sign 0, UPM vs Nasdaq Helsinki | 2 Sep | **hit**, mechanism right — −0.13% on the day, +0.34% and +0.67% after; nothing attributes a move to the objection. |
| 3 | magnitude_order: Sappi's relative move is the larger | 2 Sep | **hit**, mechanism right — Sappi −1.50% and −2.08% against UPM −0.13% and +0.34%. Confound stated: Sappi was already falling (−4.31%, −3.11% on 24–25 Aug), so the level is not attributable; the ordering is what was called. |
| 4 | sign 0, Sanoma (customer side) | 2 Sep | **unverified**, coverage none — the series returned 404 and no other free dated feed was reached. |
| 5 | sign +, both parties confirm within five days | 31 Aug | **unverified**, thin — UPM confirmed on the day and spoke for both ("Together with Sappi, UPM is reviewing the SO carefully"); no statement in Sappi's own name was found and SENS was not searched. |
| 0 | map, branches: horizontal only, not vertical | 14 Sep | **hit** (scored early on a stated, final fact) — the concern named is market power to raise prices and cut quality for customers of coated mechanical and coated woodfree paper. No vertical theory anywhere. Baseline had it too. |
| 6 | null: no remedy, abandonment or withdrawal within 30 days | 25 Sep | waiting |
| 7 | lag_band months: the review resolves in months, not weeks | 24 Nov | waiting — the Commission's deadline is 11 November, which is inside the window and consistent with the call |
| 8 | meta ordering: the largest attributable move is the smaller party's | 14 Sep | waiting |

Interim scorecard (6 of 9): outcome 0.50, mechanism 0.50, baseline 0.33, map 1.0. Nothing armed; the tradability gate was not checked per leg this round.

## What this round adds
- **The pair gate can hold.** Ten rounds of single-sided nodes, and the first event with a genuine customer class on the other side produced an eight-component opposing pair at the highest support yet. Whether it arms is a different question — no leg here was gate-checked — but the construction finally has raw material.
- **The calibration signature is now visible.** Across the clean rounds only: absence calls hit 17 of 18 (94%), occurrence calls 2 of 7 (29%), mechanism right on 20 of 24. The operator can call silence and cannot call moves. That is the programme's real result so far, and it is what the mirror basket exists to attack.
- **The replay gave K5 a denominator**: 84 positive cells against 108 mirror cells over ten rounds, with exactly one attributed re-encode (round 10's filer, latency 0 days). The rates tie at 0.083 because one leg cannot separate two spaces. The coverage-decay curve is real but short — mirror share 0.92 (12 March) → 0.75 (3 April) → 0.5625 from 9 April, flat to round 10's 0.52 — because six of the seven seeded risk rules were knowable by April.

## For the human
- Score the remaining three calls as they fall due (14 Sep, 25 Sep, 24 Nov) with `nomad_calls_due` and `nomad_score_batch`, which now runs across rounds 10 and 11 together.
- Round 12 should come through `nomad_enumerate` → `nomad_select_next` → `nomad_decide`, submitted before anything about the event is read. That is the only way the next round is clean.
- Ratify `STRATUM_QUOTA` and the stratum list (§H1), and the risk-rules seed and grid (v10 §H3). `RECONCILIATION.md` lists the nine places the build and the briefs disagree, including the cap reading that was applied by inference.
