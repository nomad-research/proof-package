# Round 12 recap: the El Teniente tunnel collapse — submitted at the wrong year, voided, replayed at the right one

Two round ids. `01a081ae-0483-7770-a92f-e91103ecb012` was submitted at **31 July 2026**, locked eleven calls blind, and was **voided as contaminated** an hour later when retrieval opened and established that the collapse is **31 July 2025**. `01a081b4-f08f-72ec-bdef-4719ac5f04bf` is the same event re-submitted at the true date, classified `learning` / `q2_fail` by the harness itself, carrying the same eleven calls transcribed from the pre-retrieval lock with every date moved back a year. It is scored: outcome **0.766**, mechanism **0.838**, baseline **0.128**, map **0.0**, 11 of 11 resolved.

First, the thing you asked to be told about.

---

## The enumeration problem, measured

You said enumeration is core, and that if it is not being done we have a problem in the build. We do, and it is worse than "not being done": it has been quietly unable to run for a while, and nothing in the harness said so.

**What was there, before this round.** Twelve feeds. Ten are rolling RSS: they serve the last N items and have no window parameter at all. One is a registry scraper (TCEQ, which returns nothing at present). The twelfth, GDELT DOC, was the only date-windowed source in the registry.

**What that means, measured on 8 September 2026:**

| feed set | feeds | items pulled | oldest item | reach |
|---|---|---|---|---|
| trade_press | 6 | 82 | 2026-09-03 | **5 days** |
| wires | 1 | 20 | 2026-09-03 | 5 days |
| registries | 3 | 20 | 2026-05-12 | one feed reaches back, ten items deep |
| gdelt | 1 | 0 | — | **HTTP 429 on every attempt today, on two user agents, and the same in the previous version** |

(The German ad-hoc feed set is a single filing feed and is not a general enumerator; it is what found round 10.)

So the enumeration path could see roughly the last five days, and the one source that could see further was refusing us. An event five weeks old could not be enumerated **at all**. That is not a gap in coverage, it is a gap in the instrument's only Q9-passing path, and it explains a pattern the last four rounds have shown without anyone naming it: rounds 9, 11 and 12 were handed over by the human because the harness could not have found them. Q9 fails on a handed-over event, a Q9 fail forces `learning`, and a learning round's calls never enter rule weights. **The enumeration hole is what has been starving the clean-round count**, which is the same count the freeze needs seven of.

**What was built this round.** A second date-windowed feed, `feed.news_windowed`, on a dated news-search endpoint that actually answers. Three things had to be right, and two of them were only found by measuring:

1. **The query has to stay short.** A twenty-two-term boolean returned 10 of 100 items inside the window and spanned five months; a nine-term one returned 83 of 100 inside it. Past some length the date operators stop binding, and an unbound window is worse than no window because it looks like it worked.
2. **The window has to be walked, not asked for.** A single week-wide request is truncated by the result cap to its last few days. `pull_window_daily` walks a day at a time and collects the per-day errors so a gap in the enumeration is said out loud rather than silently absorbed.
3. **The lookback has to be pulled separately** from the window, or thirty days of prior items crowd the window itself out of the cap.

**Result:** the same window that returned nothing now returns **345 dated, deduplicated candidates over 2026-07-27 to 2026-08-03** — 34, 55, 53, 50, 58, 48, 21, 26 by day — each with a bare prompt, node and kind guess, computed Q1a/Q1b/Q2/Q7 and a size hint. The path works.

**And it did not surface El Teniente.** Nor should it have: there was no El Teniente collapse in that window. But it is worth writing down that the enumeration is honest in both directions — it produced a full week of candidates and did not manufacture the one it was implicitly being asked for.

**What is still wrong.** The endpoint is non-deterministic: the same day pulled twice returned 65 and then 39 items. An enumerated universe that changes between requests cannot support a strict Q1a denominator, only an indicative one. That is a v13 item, and the fix is to snapshot the candidate list (we already have `enumeration_candidates`, so the ledger side is done) and treat the *stored* list as the universe rather than re-pulling.

---

## The misdating, and what caught it (and what did not)

The event was handed over as 31 July **2026**. It is 31 July **2025**: a magnitude 4.2 seismic event at 17:34 local, a rock burst in the Andesita sector of El Teniente, six workers dead, national mourning on 3 August. The 2026 El Teniente item is a different thing entirely — the August 2026 suspension of Andes Norte development over seismic risk, which is not a collapse.

That puts the true event **eleven months before the operator cutoff of 2026-06-30**. The operator has read the aftermath in training. The round was a forecast of nothing.

Three gates should have had a chance at this, and here is how each did:

- **Q2 passed, and was wrong.** Q2 is computed — that was the v9 upgrade, and it is right that it is computed — but it is computed **from the date the submitter supplies**, not from the event. A misdated event passes it by construction. This is the sharpest instrument finding of the round: *the cutoff test cannot be run before retrieval, because before retrieval we only have a claim about a date.* The fix is not to move Q2 earlier; it is to **re-compute Q2 at `open_retrieval` and void on a fail**, which is what was done here by hand.
- **Q1b passed, and was wrong.** It returned "0 disruptions in the prior 90 days, 0 in the prior 12 months; nothing recorded on the ledger or in reachable registries" — for a node that had the best-reported mining fatality of the year in its history and a public suspension of its expansion six weeks before intake. The registries the computation can reach hold **no mining incidents at all**. Q1b's pass was a statement about our reach, not about the node, and it was phrased as though it were about the node.
- **The firewall worked.** Nothing was retrieved before the lock. The eleven calls on the voided round stand on the ledger as locked, unscored.

Both criteria were superseded on the ledger with those reasons (`event_criteria`, superseding the intake row), a contamination note was written, and the round was voided. A reader bug turned up while checking the effect: `coverage_decay` counted the voided round's 224 grid cells. Voided rounds are now filtered out of both of its queries.

---

## The re-dated round

Re-submitted at 2025-07-31. The harness classified it itself: `contamination = q2_fail`, `round_class = learning`, tag `learning`, size band `headline`. **Its calls are recorded and scored and never enter rule weights, validation or calibration; its measurements do count.** That is the whole point of the class, and it is the right home for a round like this. The score below is a test of the machinery, not a forecasting record — a model that has read the aftermath is not predicting it.

**The footprint.** Fourteen legs, all `leg_source = mechanical`, across two nodes: `el_teniente_copper_supply` (operator, state owner, union, three listed copper peers, the Chinese smelter class, the copper aggregate) and `codelco_capex_programme` (the sponsor, two listed Chilean contractors, two listed equipment names, the regulator). Signs: 4 long, 9 short, 1 flat.

**The opposition is only cross-node.** `syn.tradability_opposing` refused on both nodes and said why — three listed longs and no listed shorts on the supply node, four listed shorts and no listed longs on the capex node. `syn.cross_node_event_pair` built with **seven listed components, support 1.94**: the peers long against the contractors and equipment short. This is the structure v10 added the cross-node rule for, and it is the first round where the single-node rule refuses on both nodes while the cross-node rule builds.

Grid at lock: 14 legs × 16 cells = 224, 98 positive and 126 mirror, 8 cells stamped. Q7 computed pass, 11 of 11 calls on open carriers.

### Calls

| # | Call | Due | Outcome |
|---|---|---|---|
| 4 | narrative, Codelco leg (−): the press frames it as ground failure/seismicity, not a tunnelling defect | 5 Aug | **hit** — every first-week account calls it a rock burst from a M4.2 event; the open question was induced vs tectonic. Scored first, as required. |
| 0 | map, branches sector_only / whole_mine: the stop is confined to one sector, loss in tens of thousands of tonnes | 21 Aug | **miss**, branch `whole_mine` — Sernageomin suspended the whole underground operation on the evening of 31 July; 8 of 12 sectors restarted 9 August, nine days, against a falsifier set at seven. The tonnage limb was exactly right (33,000 t). Baseline had it. |
| 1 | sign +, Codelco publicly states a stoppage within 3 days (base rate `br.mine_fatal_collapse_suspension`, 17/20) | 7 Aug | **hit** — stated the same evening. |
| 2 | sign +, Sernageomin opens an investigation naming the site within 14 days (base rate `br.fatal_accident_inspection_order`, 4/20, departed from upward and said so) | 14 Aug | **hit** — formal suspension plus four required reports (cause, recovery plan, fortification, structural), and it was the regulator that authorised the partial restart. |
| 3 | null: no Chilean order reaching beyond El Teniente within 30 days | 30 Aug | **hit**, coverage **thin** — no such order in any carrier read; the only claim of a wider inspection programme comes from a content aggregator, unsupported by the regulator's own notices or by any wire. |
| 5 | sign 0, Antofagasta inside its band on the event day and two sessions after, nothing attributed | 7 Aug | **hit**, mechanism right — **and this is the round's most important row, see below**. |
| 6 | magnitude_order, ANTO against FCX and SCCO | 7 Aug | **miss** — ANTO did close outside its band; the ranking limb held for the wrong cause. |
| 7 | sign 0, Epiroc inside its band across five sessions | 10 Aug | **hit**, mechanism right — −1.94, −1.70, 0.00, +0.20, −0.36% against a 4.73% band; Sandvik the same. |
| 8 | null: no English-language carrier names SalfaCorp or Besalco within 14 days | 14 Aug | **miss**, mechanism **wrong** — Salfa Montajes, a SalfaCorp subsidiary carried as an alias in the names book, is named on **day ten** as the employer of one of the six dead. |
| 9 | sign 0, copper does not close 3% above its 31 July level within three sessions on this | 6 Aug | **hit** — max +1.96%. Confound stated and it is enormous: copper fell 22.25% on 31 July on the US tariff proclamation. |
| 10 | sign +, Codelco restates or revises guidance within 45 days (`no-base-rate:` reason given) | 14 Sep | **hit** — 21 August, 2025 guidance cut to 1.34–1.37 Mt, El Teniente put at 316 kt, 33 kt and ~$340m named. |

Second scorer took the three arguable rows (5, 6, 8) from the blind view and agreed on all three, with a procedural objection to row 6 recorded: it conjoins an absence claim with a ranking claim, so one limb can hold while the other fails, and B4's decomposition check did not catch it because the conjunction is between a claim and its own conditional. Programme scorer-bias table now compares 37 pairs, 2 lenient.

---

## What the corrected bands did, on their first live window

This is the first round where the v12 §0.1 carrier ran over a complete 90-day window at scoring time: **446 observations across 7 listed legs, every one with a full 20-session band**. Under v11 this round would have had six or ten hand-scraped closes.

**The near-miss that matters.** Antofagasta closed **5.89% down on 31 July against its own 3.33% band** — out of band, on the event day, on the leg nearest the event. That is the exact shape the programme has been hunting for eleven rounds, and it is not a re-encode. The London close is at 15:30 UTC; the collapse was at 21:34 UTC, six hours later. The day's cause is on the tape: the US copper tariff proclamation of 30 July, which took COMEX copper down 22.25% that session. Under the definition (out of band **and** attributed) the leg is out-of-band-unattributed, and the absence call stands.

Write this down, because it is the answer to §H4's question. **The corrected bands did not produce a flood of re-encodes on legs we called silent. They produced their first genuine false positive, and attribution caught it.** A scorer reading only the band would have written the programme's second re-encode into the ledger this round, on a leg where nothing happened. The 17-of-18 null record was not an artifact of undetectable bands — at least not here.

**The bands are still mis-specified for thin names.** SalfaCorp's 20-session band is ±1.47% and it closed outside it on **23 of 62 sessions**; Besalco ±1.00%, out on 18 of 62. A two-sigma band that is breached 30% of the time is not a two-sigma band: on illiquid Santiago listings the daily return distribution is nothing like the normal the band assumes, and "out of band" carries no information there. The liquid names behave: ANTO 6/64, SCCO 4/64, FCX 3/64, Epiroc 1/65, Sandvik 1/65. **A band needs a liquidity qualification before out-of-band counts as evidence on a small cap** — v13 item.

**The class gap held even where the naming test failed.** Call 8 lost: the contractor was named in the press on day ten. But SalfaCorp closed 717 on 31 July and 771 on 8 August, *up* 7.5% with the market, and its two out-of-band days in the window are 1.9% and 2.7% moves against a 1.47% band — noise on a thin listing, not a re-encode. Named in the physical press, unpriced in the equity. That is exactly the §E divergence claim, arriving from the direction we did not predict: the fact travelled to the name and stopped there.

---

## §H: the corrected stack against the v11 baseline

Baseline frozen in `baselines/v11.json` before any §0 change landed; both stacks are re-runnable with `--stack v11|v12`.

| | v11 baseline | v12 corrected |
|---|---|---|
| price observations | 12 | **1,017** |
| legs with a computable band | 12 | **40** |
| observations out of band | 1 (a −54% collapse) | 87 |
| K5 positive | 84 cells, 7 re-encoded, 0.083 | 365 cells, 8 re-encoded, **0.022** |
| K5 mirror | 108 cells, 9 re-encoded, 0.083 | 419 cells, 8 re-encoded, **0.019** |
| latency distribution | n=1, median 0 | n=1, median 0 |
| mirror share by round | 0.92 → 0.75 → 0.5625 (a "decay curve") | **flat 0.50–0.56 across all twelve** |
| rule weight changes | — | **none** (as H3 requires) |
| validated set | `[lib.equity_visibility_ratio]` | unchanged |

**H4's verdict.** The corrected stack is better on the test the brief set: it produces far more measurements — 85× the price observations, 3.3× the legs with a computable band — without touching a single rule weight. Two of the numbers it produces are worse-looking and more honest:

- **The K5 rates fell by a factor of four** because the denominator finally has cells in it. Seven "re-encodes" in the v11 positive space were an artifact of a tiny denominator; the corrected count is 8 in 365. K5's claim (mirror re-encodes at a higher rate than positive) is now numerically *false* in the ledger — 0.019 against 0.022 — on 16 re-encoded cells that all come from a single leg — round 10's filer, one leg, eight positive cells and eight mirror. One leg cannot separate two spaces. It stays open.
- **The coverage-decay curve was our own learning and is gone.** Practice-dating the seeded risk rules (§0.2) flattened mirror share to 0.50–0.56 everywhere. There was never a decay; there was a record of when the rules became explicit to us.

The latency distribution still has exactly one point. That is the finding under §E6.

---

## §E6: the class-distance test cannot run yet, and the reason is instructive

The brief said the ledger already holds both sides — "every round's evidence already names its carriers." It does not.

**Evidence rows held a URL and a headline and nothing else.** Of 91 evidence rows over rounds 1–11, **6 resolved to a registered carrier**, because the registry holds descriptive names ("Chilean and international mining trade press") and evidence holds press headlines. So `fact_holder_class` could not be derived for most legs, and the test had no left-hand side.

Fixed this round: `evidence.carrier` is a column, resolved at write time from the host first and the headline second, and `add_evidence` accepts an explicit carrier from the operator. Hosts were registered for the new carriers. Round 12's eleven rows predate the host registration and resolved 1 of 11; the next round's will do better.

**What the test says with what we have.** 70 legs classed across twelve rounds — 6 of them from real v12 annotations on this round, the rest derived. Distances: 48 legs at 1, 20 at 2, 2 at 3. Measurable: 28. **Re-encoded: zero, at every distance.** The programme's one attributed re-encode (round 10's filer, latency 0, same class) sits on the single leg whose fact-holder class cannot be derived, because round 10's evidence carriers do not resolve.

So E5's claim — latency scales with class distance — has one data point and it is not classed. The test is not thin, it is empty, and it will stay empty until re-encodes exist. **Nothing about §E can be tested until the programme detects more than one re-encode, and that is now the binding constraint on the whole measurement layer.**

The other half of §E did produce something. On this round, annotated by hand at lock: Codelco compliance→credit (distance 1, divergent), SalfaCorp and Besalco compliance→equity_specialist (2, divergent), Epiroc physical_press→equity_generalist (2, **not** divergent — a shared data vendor joins them), ANTO compliance→equity_generalist (3, divergent), FCX the same pair but **not** divergent because copper sell-side coverage spans both. That is the first round with any spread in the measure. On the derived legs from rounds 1–11 the picture is degenerate: **68 of 70 legs are "divergent"**, because almost every fact arrives through physical_press and almost nothing has a named channel. §E4's warning is right — divergence alone is the 17-of-18 null record wearing a new label, and the conjunction with visibility is the part that has to carry the weight.

---

## §D and §G, briefly

**§D is unreadable on a backdated round, and three of the last four rounds were backdated.** `implied_at_lock` requires an option-implied or realised-since-event reading at lock. On an event 39 days old (as submitted) or thirteen months old (as re-dated), every reading available at lock is post-event: it *is* the answer. All four listed-leg calls this round recorded `method: none` with that reason, so all four are `executable: no`. This is not a flaw in §D — the reading is right on a live round, and round 10 proved it — it is another downstream cost of the enumeration hole. **Live rounds are what makes §D measurable, and enumeration is what makes rounds live.**

**§G's materiality hint is a sentence, not a number.** `materiality_hint` is implemented and `select_next` reports it, but the numeric ratio is always null: at intake the store has a headline and no touched set, so event impact over the largest listed holder's size is not computable. What it returns is the basis — whether any listed holder in the names book matches the headline at all. That is honest and it is less than the brief asked for. The number becomes computable once a candidate has a touched set, which is after selection, which is too late for selection. A cheaper proxy (does the headline name a listed holder we already hold, and what is its market cap band) is the v13 shape.

---

## Build changes this round

- `feed.news_windowed` — a working date-windowed feed, with the query-length and cap constraints documented in the code where the next person will hit them; `pull_window_daily` walks a window a day at a time.
- `evidence.carrier` column, resolved at write time (host, then headline), explicit carrier accepted from the operator; hosts registered for four new carriers.
- `coverage_decay` no longer counts voided rounds.
- `prices.SUFFIX` extended: Santiago (`.SN`), Toronto, ASX.
- Four carriers registered with participant classes: Codelco IR, Sernageomin, Chilean/international mining trade press, Santiago close.
- Two base rates exercised for the first time (`br.mine_fatal_collapse_suspension`, `br.fatal_accident_inspection_order`), one call declining to cite one with a stated reason.
- 127 tests pass; the hash chain verifies on every ledger table.

A cosmetic blemish, recorded rather than hidden: call 10's `target` still reads "Codelco: 2026 production guidance" because the re-dating rewrote claims and falsifiers but not target strings. The claim, falsifier and due date are all 2025.

---

## For the human

1. **Ratify or reject the enumeration fix.** `feed.news_windowed` is seeded but `confirmed = 0`. The feed set is the selector's universe and the brief says you confirm it once. It is a national/aggregator source, so it will bias towards headline events — which §G says we need, and which the required mix (headline ≥ 4 of seven) needs too.
2. **The next round should come through the enumeration path.** 345 candidates are on the ledger for 2026-07-27..08-03 and the path is now demonstrably able to enumerate any window you name. Three of the last four rounds were learning rounds for want of it; the freeze needs seven admitted rounds and has four left.
3. **Decide on the Q2 re-computation.** Recomputing Q2 at `open_retrieval` and voiding on a fail would have caught this round's misdating automatically instead of by hand. It is a small change and it makes the cutoff test real rather than declarative.
4. **Q1b needs mining, or it needs to stop claiming.** "Nothing in reachable registries" reads as "nothing happened" and it means "we can reach nothing". Either register incident sources per node kind, or have Q1b return `unknown` where it has no registry for the kind.
5. **The band needs a liquidity qualification** before out-of-band means anything on a small cap: 23 of 62 sessions outside a 2σ band is a mis-specified band, not a series of events.
6. Standing: the carriage table in full, the risk-rules seed, `STRATUM_QUOTA`, the participant-class matrix (§E1) — still awaiting ratification, now with a round's worth of real annotations to look at.
