# Round 13 recap: the ITC's exclusion order against IRICO glass — and §C, which says read it first

Round id `01a082b4-918a-75d9-9132-637c692e2aec`. **Clean class**, tag `weather`, size band `underread`. First round under v13: the mirror basket is retired as a generator, every leg carries a claim or a stated reason for having none, and the surviving-risk assessment runs at lock. Nine calls, all nine resolved: outcome **0.512**, mechanism **0.516**, baseline **0.244**, map **0.0**.

§E3 says read §C before this round is played. §C ran first, so it comes first.

---

## §C. Does surviving risk have content? One check passes, one fails

Both checks were pre-registered in the brief. They ran over all 195 legs of rounds 1–12, point-in-time, no new data.

**C2 check 1 — PASS.** The programme's one attributed re-encode is round 10's filer (paragon, latency 0). Under the eliminators it **survives**: nothing fires on it, and its surviving magnitude is 7.12, the second-highest of the only two magnitudes computable in the whole programme. The pre-registered reasoning holds exactly — no tide rule can fire on a company whose own insolvency is the event, because the leg is at degree 0.

The check passes on almost no data, and that is the honest qualification: with magnitude computable on **2 of 195 legs**, "among the legs with the highest surviving risk" is nearly vacuous.

**C2 check 2 — FAIL, and worse than the brief's falsifier anticipated.**

| absence calls across rounds 1–12 | 39 |
|---|---|
| on a leg where an eliminator fired (`eliminated`) | **0** |
| on a leg where risk survives (`surviving`) | 10 |
| not attached to any leg at all (`unassessed`) | **29** |

The brief expected "nearly all of the 17-of-18 record to land in `eliminated`". None of it does. And three quarters of the absence calls cannot be assigned to a leg in the first place, because a `null` call is required to carry `target = "none"` and most were written without a `position_id`.

**Why it fails, precisely.** The eliminator the whole absence story depends on — tide, "the event is too small to see against this name's own variance" — could not be evaluated on **110 of 195 legs**. It has no numerator. The only per-leg number the ledger held was the call's own claim, and using that would make the split a restatement of the call type rather than a fact about the leg:

> An absence call's own expected move is zero by construction. Feed it back into tide and every null eliminates its own leg, and A5's finding is a tautology.

So the verdict to write down, per §C3: **surviving risk as specified is not shown to have content, and §A should not be built on further until it does.** The failure is not "the measure was tested and the world disagreed"; it is "the measure could not be computed, and where it could, it pointed the other way".

**One correction the retrospective produced on its own.** The first pass fired `traversed` on all 28 legs of round 11 and `weather` on all 13 legs of rounds 6 and 8 — because Q1a and Q1b are facts about the *round*, so using them as leg-level tests made the eliminators round-level constants. That is the mirror basket's error one layer down, which is exactly what §A3's preconditions exist to prevent. Both were rewritten leg-level: `traversed` fires only where the ledger shows this holder already carried on this node before the event (and reports **unevaluable** where Q1a says the episode had an earlier instalment we never played), and `weather` fires only on the node Q1b was computed over. Firings fell from 28 to 14 and from 13 to 8.

**What the eliminators actually did, over 195 legs:** 105 eliminated, 90 surviving.

| eliminator | fired | unevaluable |
|---|---|---|
| no_path | **94** | 0 |
| traversed | 14 | 14 |
| weather | 8 | 0 |
| immaterial_position | 5 | 0 |
| self_hedged | 3 | 0 |
| tide | 0 | **110** |
| slack | 0 | 58 |

`no_path` does 90% of the elimination, and it is the bluntest of the seven: it fires on a degree-2-or-worse leg with no cited mechanism and no stated position. **Half the programme's legs have no declared path from the event to the holder.** That is a finding about the footprints, not about the risk engine, and it is probably the most useful thing §C produced.

---

## What was built for it, after §C

§C named the missing piece, so it was built rather than argued about: `leg_claims.impact_pct` and `impact_basis` — the operator's own estimate of what the event is worth on this leg, in per cent, stated at lock, independent of any call's direction. Round 13 is the first round to carry them, and it is therefore the first round where tide can be evaluated at all.

One limit found immediately: **tide is still unevaluable at lock**, because the denominator (the leg's own ambient band) comes from the price carrier, which does not run until retrieval opens. At lock, round 13 recorded tide as unevaluable on four legs. After the backfill it was evaluable on all six equity legs and fired on four. The band is computed from *pre-event* closes only, so this is fixable — compute it at lock — and it is a v14 item.

---

## Round 13

**Intake.** The human's sweep picked it; Q1a fails (the 7 April ALJ determination was the episode's first mover) and Q1b fails (an active parallel dispute, a second determination weeks away). Both were accepted as tags, not gates — v11 §C working.

Two intake findings worth recording:

- **B3 fired on its first live round.** Q1b computed `unknown`, not `pass`: no registry in the reader set covers node kind `listed_company`, so the harness declined to report its own reach as the node's history. The human holds the fact the registries cannot, so it went in as a `q1b_override` with a basis — which is what the override is for. The first submission (before the override) was voided and re-submitted, because the tag drives the `weather` eliminator and a tag derived from `unknown` would have been derived from nothing.
- **Q9 is the last gate of this shape.** The harness takes the submitter's Q9 verdict whenever no selection-window row exists. The sweep behind this round is real and was logged in chat, but the ledger cannot check it, so the round carries an intake note saying exactly that. Q2 tested the submitter's date until B2; Q1b reported our reach until B3; **Q9 still takes an unbacked assertion**, and it is now the only one left.

**The footprint.** Ten legs the operator decomposed by hand (a clean round's legs are not mechanical): the respondent, the complainant and the Commission at degree 0; CBP and the two substitute glass makers at degree 1; two panel makers, an unlisted panel maker and the downstream importer class at degree 2.

**The strongest synthetics the programme has built.** `syn.tradability_opposing` built on *both* nodes for the first time — Corning, AGC and NEG long against IRICO short on the glass node (4 components, support **3.71**), LG Display long against BOE short downstream (2 components, support **5.13**) — plus a cross-node pair at 3.15. The previous best was 1.94.

**The template.** 20 rows over 10 legs: 5 slots filled by calls, **15 by a stated `no-claim:` reason**. That ratio is the point of A1. Writing fifteen reasons is uncomfortable in a way that letting a grid enumerate 160 cells never was, and three of them are real findings — CSOT is unlisted so no direction claim can be scored on it, LG Display's competitive read is already tested on BOE with the sign reversed, and the two authorities have no instrument at all.

### Calls

| # | Call | Due | Outcome |
|---|---|---|---|
| 4 | narrative, IRICO leg (−): the trade press frames it as IP enforcement, not a China trade measure | 11 Aug | **hit** — DigiTimes frames it as trade-secret and patent enforcement over fusion-draw technology throughout; Corning is quoted on innovation. Scored first, as required. |
| 0 | map, branches limited_only / reaches_downstream | 6 Sep | **miss**, branch `reaches_downstream` — see below |
| 1 | sign +, Corning confirms the determination within 5 days (base rate 18/20) | 11 Aug | **unverified**, thin — counsel announced the July determination and Corning is quoted on *that* one; no statement in Corning's own name about 6 August was found, and its IR feed was not read directly |
| 2 | sign 0, Corning (GLW) inside its band on the event day and two sessions after | 13 Aug | **hit**, mechanism right — −0.06%, +5.02%, −5.13% against a band of 10.6% |
| 3 | magnitude_order, IRICO's move larger than Corning's | 13 Aug | **miss**, mechanism **wrong** — see below |
| 5 | null: no CBP instrument names finished displays within 45 days | 20 Sep | **hit** (early), thin — none found, but the order's own scope already reaches downstream, so this is a narrow technical pass |
| 6 | lag_band months: the Presidential review runs without disapproval | 20 Oct | **hit** (early), thin — the remedy carries a bond rate for the review period; the parallel case's orders are described as effective January 2027 |
| 7 | sign 0, AGC inside its band across five sessions | 18 Aug | **hit**, mechanism right — +0.01, +0.08, +0.71, +0.10, +0.79% against 4.8%; NEG the same inside 5.4% |
| 8 | sign 0, BOE inside its band across five sessions | 18 Aug | **hit**, mechanism right — −1.17, +0.82, −3.94, −0.67, −0.67% against 9.0% |

**The map call is the round's real loss, and it was avoidable.** The Limited Exclusion Order of 6 August prohibits importation of IRICO glass **and products containing such glass** — TVs, monitors and computers named explicitly — and a Cease and Desist Order issued against the remaining importer respondent. Both limbs of the call were wrong. The investigation has been captioned *"Certain Glass Substrates for Liquid Crystal Displays, **Products Containing the Same**, and Methods for Manufacturing the Same"* since institution in March 2025. The downstream reach was in the case name eighteen months before the order, and the operator reasoned from what a limited order usually does instead of reading the caption. The baseline — an exclusion order on a component stops the finished goods that contain it — had it.

**The ordering call is the round's most interesting loss.** IRICO closed **+3.03%, +3.27%, −1.80%** over the three sessions: the respondent *rose* after being barred from the US market, and its moves were smaller than the complainant's. The call cited the visibility ratio to argue the order was the whole of the respondent's exposure and a fraction of the complainant's. The ratio that decided it was the other one — ambient variance — and Corning's is enormous.

---

## The bands, on their first live round under B1

The empirical band replaces the 2σ parametric one, and the first thing it does is show how wrong the old one was about Corning.

**GLW's 60-session empirical band is ±10.6%**, because Corning's daily returns in the sixty sessions before the event include −13.6%, −12.1%, +13.4% and +15.7%. A two-sigma normal band would have been perhaps a third of that and would have called several ordinary sessions "out of band". The empirical band makes no distributional claim and cannot be wrong about the past.

It also makes the absence calls on this round very cheap, and the round says so against itself in the scorer notes: **an order worth a fraction of a per cent could not have shown up on a name that moves ±10% on ordinary days, whatever happened.** That is the surviving-risk finding arriving as a score.

The turnover floor worked where it was asked to. On the v12 data it marks SalfaCorp ($207k/day) and Besalco ($67k/day) unreliable while ANTO ($20m) and FCX ($479m) pass. On this round it passed GLW, AGC, NEG and LPL, and returned **null** for the two Chinese listings because the pre-registered FX table carried no CNY rate when the backfill ran. That is recorded on the rows rather than fixed after the fact; CNY, KRW, TWD, BRL and MXN have since been added for the next round.

---

## What round 13 says about §A, which §C could not

This is the one round where the null breakdown is computable, and it comes out as §A5 predicted:

| round 13 absence calls | 4 |
|---|---|
| on an eliminated leg | **3** (all three **hit**) |
| on a surviving leg | 0 |
| unassessed (the `null` row with no leg) | 1 |

**Eight of ten legs were eliminated**, six by `weather` (the node's Q1b failure), four by `tide` once the bands existed, one by `immaterial_position` (IRICO's share of US display glass imports is recorded as small). Every computed magnitude — 0.047 for Corning, 0.40 for IRICO, 0.056 for BOE, 0.062 for AGC, 0.070 for LG Display, 0.093 for NEG — is far below the pre-registered floor of 1.0. The two survivors are unlisted aggregates with no computable magnitude at all.

So v13's machinery said, before retrieval opened, that this round was a non-position from end to end. Then the prices agreed: **not one leg closed outside its own band on any session of the window.**

That is one round. It is a data point for §A, not a rescue of it: the honest position after §C is still that the measure is unproven, and the way to prove it is more rounds carrying `impact_pct` at lock, not more argument. The pre-registered claim to test next: *an absence call on an eliminated leg hits, and an absence call on a surviving leg is where the misses live.*

---

## Build changes

- **§A** `harness/surviving.py`: seven eliminators with pre-registered preconditions written onto the risk rules themselves; per-leg records of what fired, what was checked, **what could not be evaluated**, and the surviving magnitude. Cell enumeration deleted as a source of legs (`predictions.space` no longer written; four v10 tests rewritten to record the retirement). The effect kinds survive as a per-leg template. `arming_status` gains `eliminated`, reported separately from `gate_fail`; `uncovered` becomes an independent field.
- **§B** empirical bands with a turnover floor and a static dated FX table; Q2 re-computed at `open_retrieval` with an automatic void and a scoring gate behind it; Q1b returns `unknown` where no registry covers the node kind; the conjunction check extended to an absence claim carrying its own conditional; `feeds.reach_days` measured at enumeration; Q1a's denominator taken from stored candidates.
- Two bugs found in passing: `coverage_decay` counted voided rounds (fixed in v12, still worth noting), and a v12 host registration wrote a bare list into `carriers.fetch_paths`, which crashed every caller of `open_for_kind` — enumeration included — until `fetch_paths` was made defensive. **A convenience column took out the enumeration path for a version.**
- `prices.SUFFIX` had `SSE` pointing at Santiago; it now points at Shanghai, with Shenzhen, Tokyo, Hong Kong, Korea and Taiwan added. Round 13 would have priced a Chinese respondent off a Chilean ticker.
- 138 tests pass (11 new); the hash chain verifies on every ledger table.

**Feed reach, measured at enumeration (B5):** the windowed feed reaches **57 days**, the window needed 36, and GDELT still answers HTTP 429 on most days (reach 33). 193 dated candidates were written for 2026-08-03..08-06 and **none of them was a trade or legal action** — the enumeration query is industrial-incident vocabulary only, so the `regulatory` stratum has no windowed feed behind it. That is why this event had to be handed over.

---

## For the human

1. **§C failed check 2. The brief says stop building on §A, and that is the recommendation.** Keep the eliminators recording; do not let `survives` gate anything that matters until the null split has been reproduced on rounds that carry `impact_pct`. Round 13 is the first such round and it went §A's way; one round is not a result.
2. **Ratify or reject the eliminator list and preconditions (§A2, §A3)**, now with 195 legs of evidence about which of them can actually fire. `tide` and `slack` were unevaluable on 110 and 58 legs; `no_path` did 90% of the work.
3. **Ratify the turnover floor** ($2m median daily) and the static FX table behind it — build-only, no brief gives either.
4. **Q9 is the last unbacked gate.** Two of its three siblings were fixed this version. The fix is the same shape: the selection window and its rejections on the ledger, or Q9 returns `unknown`.
5. **The regulatory stratum needs a windowed feed.** The enumeration path can now reach any window you name and still cannot see an agency action.
6. Standing: carriage table, risk-rules seed, `STRATUM_QUOTA`, participant-class matrix.
