# Round 14 recap: PT Smelting's Gresik outage — and §B, the wall map

Round id `01a0857b-b404-711e-8de9-e2e6f4ec17ec`. **Learning class** (see Q9 below), tag `lag_test`, size band `underread`. First round under v14: generation is wide and mechanical, the anchors cut it, and what survives carries a five-term vector instead of passing an eight-predicate AND. Nine calls, seven resolved, two still inside their windows: outcome **0.677**, mechanism **1.0**, baseline **0.323**, map **0.0**.

§E1 says read §B before v15 is started. It comes first, and it answers the question that was put before the brief arrived — *is there open edge here, or are we still just a null detector.*

---

## §B. The wall map, over 225 legs

The vector, computed point-in-time for every leg of rounds 1–13.

**B2. What binds:**

| binding term | legs | |
|---|---|---|
| structural | 114 | 51% |
| expression | 96 | 43% |
| stake | 6 | 2.7% |
| pricedness | 6 | 2.7% |
| operator | 3 | 1.3% |

**The brief's stated prior was wrong, and the way it is wrong matters more than the fact.** The prior was "stake binds nearly everywhere; pricedness binds on the one leg where stake did not". Stake binds on 2.7% of legs. But:

| term | legs where it could not be computed at all |
|---|---|
| **stake** | **217 of 225** |
| **operator** | **201 of 225** |
| structural | 0 |
| pricedness | 0 |
| expression | 0 |

So the ranking is mostly an artefact of computability. The two terms that bind everywhere are the two that can always be computed from the store; the term the brief expected to bind is the one the ledger almost never has a number for. That is the same disease v13's §C found, one layer along: **the measure that matters is the one we cannot take.**

Where stake *can* be computed — round 13's six legs and round 14's four — it binds every time, at 0.04 to 0.26 against an appetite of 1.0.

**Not one leg in the programme's history clears appetite on every computable term.** The closest are round 10's two paragon rows, and they are killed by the term the brief said should kill them.

**B4. The pathology tail, which is the point.** Three legs show two terms out of whack in opposite directions, and all three are the degree-0 signature the brief predicted:

- round 10, paragon equity: `stake` **7.12**, `pricedness` **0.05** — the most at issue in the programme, and re-encoded at latency 0. It was in the price before it was knowable to us.
- round 10, paragon's 2027 bond: `stake` **19.02**, `pricedness` **0.05** — the same wall, larger.

A conjunction would have armed both and been wrong. The vector kills them on `pricedness`, which is §D2's test, and it took a real correction to get there: pricedness was keyed to a (holder, node) row, so the same equity read as unpriced on one node and priced on another, and one row cleared appetite. A re-encode is a fact about the instrument. Fixed, and the leg now reads 0.05 rather than 0.5.

**B3. What a hop would clear.** Almost nothing. Of 225 legs, the binding term is one no one-hop adjacency can reach on 12 — but that understates it, because the two dominant binding terms are structural and expression, and a hop *degrades* structural by construction (a further step from the event is a further link to be admissible about) while only sometimes helping expression (the neighbour has to be listed). **Going to degree 2 for stake buys structural risk faster than it buys stake.** Round 14 is the clean demonstration, below.

---

## Round 14, and what the wide generation did

**Intake, and C6's first live consequence.** Q9 now returns `unknown` where no selection window sits on the ledger, so a handed-over event can no longer be a clean round. This one was handed over, so it is learning class. That is the rule working as specified and it hands the clean-round count entirely to the enumeration path.

The path was run first, over the event's own window: **272 dated candidates across four windowed feeds** (GDELT answered for once, at 35 days of reach; the news feed at 58; the new regulatory feed at 64) and **not one of them touched an Indonesian smelter**. A real defect was found doing it and fixed: the query vocabulary and the `INCIDENT_WORDS` filter did not match, so leaks, outages, halts and shutdowns were *unreachable by construction* while the filter was busy screening for them. A fourth feed now carries the outage vocabulary. It still did not surface this event, which is a fact about English-language search coverage rather than about the query — and it is recorded as such, along with the declaration that the fix was written while looking for this event.

**Generation width 23, against round 13's 10.** Every holder with a position on either node, at every degree the store reaches, plus one hop out. The hops did real work: they pulled in Codelco, Antofagasta and Southern Copper from round 12's Chilean node, because Freeport holds a position on both.

**The anchors cut 14 of 23.** `no_path` took 10 — every chain hop into the Chilean node, which shares a holder with this event and nothing else. `tide` took 4 once impact estimates existed. `immaterial_position` took 2.

Then the operator did the thing v14 moves onto the elimination side: **five of the killed legs got a path stated** (the two export-licence competitors, the minority owner and trading arm, the concentrate buyers of last resort, the acid offtaker), and the other ten stayed dead. Both moves are in `move_log` with their reasons. One leg the anchors could not kill — Codelco, which has a *stated* position on the Chilean node — was killed by the operator in a `no-claim:` reason instead: *a shared holder is not a path from an Indonesian boiler to a Chilean mine.*

**And here is the round's finding, which is §B4 in one event:**

| | legs | binding term |
|---|---|---|
| survivors | 9 | **`expression` at 0.0 on every one** — all unlisted |
| eliminated listed legs | 4 | **`stake`**, at 0.04–0.26 |

The things with a path to the event cannot be held. The things that can be held have nothing at issue. PT Smelting itself has `impact_pct` 100 — the outage is the whole of that asset's output — and no `stake` value at all, because an unlisted plant has no band to divide by.

**Every path trades one wall for another, and this round is the demonstration.** That is a finding, not a tuning problem, and it is the answer to the question that prompted the brief.

### Calls

| # | Call | Due | Outcome |
|---|---|---|---|
| 4 | narrative, PT Smelting leg (−): the press reports a routine utility repair, not a supply disruption | 13 Aug | **miss** — TechTimes ran it as extending a record copper rally, SMM as a regional tightening, Reuters as delayed shipments. Baseline had it. |
| 0 | map, branches utility_repair / structural_damage | 22 Sep | **miss** (early), branch `structural_damage` — see below |
| 1 | sign 0, Mitsubishi Materials (5711) inside its band | 15 Aug | **hit**, mechanism right — −0.77, +3.59, +0.48% against 4.84% |
| 2 | sign 0, Freeport (FCX) inside its band, five sessions | 18 Aug | **hit**, mechanism right — inside 4.90% throughout |
| 3 | sign 0, Amman (AMMN) inside its band, five sessions | 18 Aug | **hit**, mechanism right — inside 7.1% throughout |
| 7 | sign +, an owner names a restart date within 14 days (base rate 18/20) | 22 Aug | **hit** — day five: PTFI's president director confirmed the halt and named Q3 |
| 5 | null: no force majeure on offtake or delivery within 30 days | 7 Sep | **hit**, thin — with the confound named |
| 6 | lag_band weeks: back in production in weeks, not months | 22 Oct | waiting — Q3 completion is a projection, not a restart |
| 8 | null: no export-licence relaxation naming the outage within 45 days | 22 Sep | waiting |

**The map call lost, and it is the fourth in a row lost the same way.** The claim was a repairable *utility* failure rather than damage to the furnace line — reasoned from the word "boiler" in the prompt. The operator's own announcement on 13 August calls it "operational issues requiring urgent furnace repairs". C3 worked exactly as designed here: the call named its settling document, the fetch was attempted as of the day before the event, the attempt returned nothing, and that is on the ledger. What it could not do is conjure a document that did not exist until day five. **The operator's map record is now 1 of 5, and `operator` risk reads it directly.**

**The confound worth keeping.** The whole copper complex fell together on 13 August, the announcement day: FCX −4.30%, SCCO −3.49%, Antofagasta −6.83%, Amman −3.95%. There was a real move, and every band was wide enough to swallow it. The only leg that closed outside its band was Antofagasta — a chain hop on another node, eliminated by `no_path` before any of this. An absence call on a name that moves 5–7% on ordinary days is cheap, and the round says so against itself.

**A second confound, recorded rather than left in the search results:** a Grasberg force majeure exists in the record from the mud rush of 8 September **2025**, and a careless search returns it inside this round's thirty-day window. It is a prior-year declaration on the mine, not on this stoppage.

**The null breakdown, third round running:** 3 absence calls on eliminated legs, all three hit; 0 on surviving legs; 2 unassessed. §A5's premise keeps holding on every round where it can be computed.

---

## Build

- **§A** `harness/generate.py` (permissive generation, one-hop adjacency, proposals that may put a leg on the board and never support one) and `harness/vector.py` (the five terms, never multiplied; operator risk computed from clean resolutions). `harness/glossary.py` gives the move glossary, the store index and `nomad_precedent` — precedent, never endorsement. Every move is logged with the operator's stated reason (`move_log`).
- **§C** materiality is a number at selection (C1); bands computed at lock from pre-event closes, which is what made `stake` and `tide` evaluable at lock for the first time (C2); map calls name and attempt their settling document (C3); a call on a leg with no admissible path is refused (C4); an ordering call over unattributed noise resolves `untestable` (C5); Q9 returns `unknown` without a window on the ledger (C6); a regulatory feed and then an outage feed (C7); short feed reach and malformed registry writes now raise at the point of use (C8).
- 147 tests pass (9 new); the chain verifies on all 42 ledger tables.

**Not built, and deliberately:** no route-finder. `nomad_adjacent` returns neighbours and hop costs with no ranking and no recommendation, because a path-finder trained on thirteen contingent propagations would encode cascade priors that are limiting and wrong on the world's own terms, and would only ever surface paths already walked.

---

## For the human

1. **Read §B before v15.** The wall map says selection is the only lever with real leverage — but it says it through two terms that are always computable while the term that should decide is missing on 96% of legs. **Fixing computability is prior to fixing selection.** `impact_pct` at lock and bands at lock are now in; a run of rounds carrying both is what turns the wall map into a measurement.
2. **The honest answer on edge.** No leg in fourteen rounds has cleared appetite on every computable term. On the two rounds where `stake` could be computed it binds every time, and the legs with real stake are unlisted. This programme has become very good at identifying non-positions, which is worth something, and has not yet produced a position.
3. **Ratify the appetite block** (§A7) — as appetite, not as a target. It has never been met and must not be moved because of that.
4. **Ratify the term structure and the operator-risk inputs.** Current values, computed: absence 15/16, occurrence 8/14, **map 1/5**.
5. **Q9 now costs clean rounds.** Six of the last nine events were handed over; under C6 every one of those is a learning round. Either the enumeration path gets good enough to find events like this one, or the freeze's seven clean rounds will not happen.
6. Standing: carriage table, risk-rules seed, `STRATUM_QUOTA`, participant-class matrix, eliminator preconditions, turnover floor and FX table.
