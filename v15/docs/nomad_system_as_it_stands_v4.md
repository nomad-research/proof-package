# Nomad — System As It Stands (v4)

**Supersedes `nomad_system_as_it_stands_v3.md` (2026-08-23) and everything before it.**

Last revised 2026-09-06. Written to be portable — a fresh session or a fresh model should be able to work from this alone. Plain English first; formal terms are named once and then used.

---

## 0. Status

**Coherent architecture. First empirical contact made — three scored rounds. Zero capital deployed.**

Since v3, three things happened and they reorganise the document.

**First, a working-mode change.** Ideas are stated as one falsifiable plain-English sentence, then the cheapest possible test tries to kill them. Literature is consulted only when real money is about to be committed to a claim. Vagueness is the enemy, not jargon; code is the precision layer. This replaced prior-art-as-design-gate, which v3 had already condemned and which had cost roughly half a session.

**Second, the system made contact with reality** through a blind event-prediction game: an operator with a fixed knowledge cutoff is given a post-cutoff event and must say who it touches, in which direction, how hard, and how fast — before searching. Three rounds are scored in §8. They produced the first evidence bearing on Claim 1 (§1) and a new, uncomfortable finding about where the edge is expressible (§10).

**Third, a vocabulary loss was detected and repaired.** Across a context reset the ACK concept (§4) fell out of the working vocabulary and was partly reinvented, worse, as the "trigger" problem in v3 §5. This document restores it. The lesson generalises: names for load-bearing organs must live in this document, not in session memory.

**The re-seating.** v3 was organised around a chain of arrows. v4 is organised around three layers that the game forced into view:

> **Library** proposes · **Predicates** condition · **Shocks** resolve.

The mechanism library is the hypothesis space. Predicates (ACKs) are the conditioning layer that stops wrong ideas from firing. Shocks are the dated events that test both. v3 had the third layer, half the second, and had lost the first.

---

## 1. Premise

> Entities are linked by relationships **inferable** from verified facts. Some are not reflected in relative prices. An agent that reads all of them, at a finer resolution than the market prices, and assembles across kinds of fact that no single participant's book is organised around, sees relationships that are unpriced.

Two claims:

- **Claim 2 — you can capture it.** Addressed by the mechanisms in §6 and the predicate layer in §4.
- **Claim 1 — they are unpriced for long enough to matter.** Previously open with zero evidence. Now three rounds of evidence, summarised here and detailed in §8:

  The repricing lag **exists**, is **large**, and is **observable** — but so far only in **contract and commodity space**: force-majeure letters, allocation notices, contract-price resets, freight rates, war-risk premia. In **equity space** the same events left no attributable trace in any of three rounds, for three different reasons (everything already priced; micro swamped by macro; no listed pure-play). This is the finding that reshapes the programme (§10).

**The bet, plainly:** breadth × cheapness × a differentiated hypothesis space beats their depth × capital. Real, with a real prior against it, and now with one real complication: the place the edge is *visible* may not be the place it is *tradeable*.

---

## 2. The three layers

| Layer | What it is | Plain question it answers | v3 name(s) |
|---|---|---|---|
| **Library** | A store of *mechanisms* — ways things connect — not facts | "How could this event reach anyone?" | hypothesis space, generation, relation modes |
| **Predicates** | Standing, machine-checkable conditions with named source + threshold + date | "Is this idea allowed to fire, and when does it stop?" | trigger, entry, falsifier, exit, promotion, ACK |
| **Shocks** | Dated node events, mechanically selected | "What happened, and did the predicted propagation occur?" | event, T0, propagation replay |

The chain from v3 still holds — `event → facts → relational hypothesis → event hypothesis → trigger → basket → entry → position → exit` — but it reads as a walk through these three layers, and the three arrows v3 left undefined (trigger, basket, entry) are all predicates.

---

## 3. Library — the hypothesis space

### 3.1 What it stores

**Verbs, not nouns.** A mechanism is a way one thing reaches another: "constraint prices reprice before commodity prices," not "Hormuz insurance went up." The library stores the verb; the provenance field stores the noun.

**Hard rule: no proper nouns in a rule, ever.** Abstract each learning to the highest layer that still *forbids* something, then come one rung down. One worked example lives in a provenance field, exempt from the noun ban. The same event may teach at several layers; each rule is scored separately.

**Every rule must forbid something.** A rule that is compatible with every outcome is a slogan.

### 3.2 Rule format

```
rule:        one plain sentence
forbids:     what this rule says will NOT happen
obscurity:   would a journalist name this channel within a day? (1–5)
status:      candidate | validated (called a future event blind) | retired
false_alarms: n / trials
provenance:  round, event, what happened (nouns allowed here)
```

Mechanisms harvested from misses are **candidates** until they call a future event blind. Misses are classified as *missing mechanism*, *misread*, or *misweight*.

### 3.3 Edge hypothesis the library carries

> Mechanisms a journalist would name reprice in days. Mechanisms nobody names take weeks — **in the price space where they are expressed.**

The qualifier is new, from §8.

### 3.4 Current entries (after three rounds)

Sequence and state:
- **Novelty belongs to channels, not events.** A channel already traversed by a crisis is priced for every later headline in that crisis. Locate the headline in its sequence before predicting.
- **Recurring disruption is priced as weather.** A node whose failures recur has its variance in everyone's plan. First-traversal must hold at the *node*, not just the event.
- **Late in a crisis the neglected side is resolution.** When every channel is priced for continuation, the unpriced asymmetry is de-escalation.
- **The headline names what reopened, not what stayed shut.** Duration lives one node smaller than the choke that made the news.

Transmission:
- **A cut into a glut is silent.** Supply loss transmits only where the receiving market has no slack. Check destination-market slack before predicting any co-product or substitute repricing.
- **The move is largest where substitution is hardest.** Response concentrates at the chain position with least optionality — requalification lags, formulation lock-in, route dependence.
- **The toll booth learns before the cargo.** Constraint prices (insurance, freight, allocation) reprice before the commodity they gate.
- **Constraint prices de-escalate slowest.** Fear enters through the commodity and leaves through the insurance bill.

Ownership and visibility:
- **The wounded owner of the substitutes collects its own scarcity premium.** When the victim also owns the remaining capacity, the competitor's gift self-cancels. Forbids long-rival/short-owner where the owner holds sister plants.
- **Equity visibility = event size ÷ ambient tide.** Compare the event's earnings impact to what the macro is doing to the same name in the same window. Below a ratio to be measured, there is no trace to trade.
- **A lag without a listed pure-play is a spectacle, not an edge.** (Promoted to a predicate — §4.3.)

Operator distortions (specific to an AI operator):
- **My freshness is not the market's.** The operator wakes new to every event; the market has been living in it. Operator surprise is a bias toward assuming un-inferredness.
- **Specialists already hold my map.** Obscurity must be measured against the people at the terminal, not the public. A sell-side analyst named the co-product channel in five days.
- Prior list retained: overweights famous companies, first-order links, connections that make good sentences; underweights boring intermediaries, logistics, insurance, second-order plumbing.

### 3.5 What the library is for

It is the answer to v3's dead question "where does differentiated generation come from if everyone has the same model?" Not from the model, not from a schema document — from an accumulated, scored record of *which channels transmit, under which state conditions, with which lag*, built by playing against reality and never copyable faster than one second per second. This is the durable version of the hypothesis-space claim, and it is testable: does the library's forbid-rate improve with rounds?

---

## 4. Predicates — the conditioning layer (ACKs restored)

### 4.1 Definition

An **ACK** is a standing predicate: **named source + threshold + date**, machine-checkable, prepositioned so that a wrong idea *does not fire* rather than accumulating risk. Chains of ACKs stop error compounding: each one is a conditioning event. This was the strongest single element of the pre-Nomad system and it survives intact; v3 used it in four places without naming it (forward-dated facts, the falsifier field, the promotion rule, the exit rule).

Three ordered levels, unchanged: **support** (which branches exist) → **conditioning** (which are live after ACKs eliminate some) → **direction** (which realises). A direction claim implies a support claim; a support claim can stand alone.

Because ACKs are dated, they price into calendars: buy vol spanning the ACK window, not vol in general. Predicates *not* firing is short vol. Dates the market has not recognised as resolution points are a calendar trade.

**Round 2 was an ACK firing in the wild.** Force majeure on the derivative the day after the fire; on the parent chemical on day five. Named source (the producer), threshold (declared), date (stamped). Every contract reset that followed was downstream of that predicate.

### 4.2 Arm / disarm asymmetry

Instruments are assigned rights by their noise structure:

- **Arming predicates** must be properties of things you hold or can check over a bounded, named set. Precise, low-noise.
- **Disarming predicates** may be noisy. A false disarm costs a missed trade; a false arm costs money.

This extends v3's "proposal rights and support rights differ by mode and source class" into the trigger layer as a third rights class.

### 4.3 Arming predicates (the v3 "trigger," resolved)

All must hold. Each is checkable without a claim about the whole population's beliefs.

1. **Path composition.** The supporting path contains at least one non-stated edge (§6.4). Property of your own graph.
2. **Existence floor.** At least one independent, non-price trace from a source class *not used at generation* confirms the relation is real. Guards the adverse-selection case (zero pricing = nobody cares).
3. **First traversal — event and node.** No related market-moving news in the prior ~30 days for the *channel*, and the *node* is not a recurring-disruption node. (Rounds 1 and 3.)
4. **Bounded-channel absence.** Over a pre-named set of fast channels — analyst Q&A co-mention, sell-side note coverage, independent-outlet co-mention, optionally 13F shifts — the relation is below calibrated thresholds. A checkable negative over a defined set, not a universal one.
5. **Slack check.** The receiving market for the predicted repricing has no spare capacity or inventory glut. (Round 2, MTBE.)
6. **Tradability gate.** Some listed party's exposure to the touched channel clears the micro/macro ratio: expected earnings impact of the event ÷ concurrent macro variance on that name. If no listed party clears it, the shock is **scored but not armed.** (All three rounds would have failed this gate; two correctly.)
7. **Catalyst class.** A forward-dated fact supplies a known statement window → armed *dated*, directional expression permitted. No date → armed *undated*, **support-branch expression only** (dispersion, never directional). Hard restriction carried from v3.

### 4.4 Disarming predicates

Any one fires → position closes or arming is withdrawn.

- **Falsifier.** A pre-registered fact that, appearing before resolution, kills the hypothesis. Every hypothesis carries one at creation.
- **Channel fill.** Any bounded channel crosses its threshold.
- **Rate-of-change.** The adoption curve has visibly inflected. Too noisy to arm; fine to disarm.
- **Date passed.** The forward-dated statement date has arrived.
- **Staleness.** A load-bearing fact has exceeded its class half-life without re-verification.

### 4.5 Exit predicate

> A position closes when the **decompression residual is recovered** — when the market's projection has absorbed the fine-grained state you inferred. Not at a price target. Not at a P&L.

Observable through the epistemic-class ladder: an implicit edge going stated *is* recovery. Exits are evaluated against the **net book**, never leg by leg, because closing one leg un-hedges others; replacement hedge cost is charged to the exit.

### 4.6 Portfolio-level ACK: promotion

The shadow book is the predicate library; promotion is the fire. Promote when shadow-measured edge × deployable capacity clears round-trip cost plus a rotation reserve, with a stated error band. Rotate only when expected improvement exceeds round-trip cost — you will knowingly hold the second-best basket.

---

## 5. Shocks — the resolving layer

### 5.1 Two words, not one

- **Event.** Anything dated that happened in the world. Cheap. Most of them.
- **Armable shock.** An event that passes the arming predicates. Rare. The programme's real unit of supply, and its arming rate is now a first-class measurement (§9, hole 2).

Round 3 was an event and a correct non-shock. The system must be scored for calling that right *and* must not count it as a win of any size.

### 5.2 Selection rule

Shocks are selected by a pre-registered mechanical rule from a fixed source and date range — first qualifier, rejections logged — never by memory. Qualifying criteria (from the game, carried into the harness):

1. First traversal (channel and node) · 2. Post-operator-cutoff · 3. World event, not price event · 4. Touches a shared thing (facility, route, material, rule, port, standard, region) · 5. Underread but material — trade-press sized · 6. One event, one date, one line · 7. Scoreable aftermath: ≥4 weeks old, some touched party has a checkable carrier · 8. Clean prompt: bare event + date; no aftermath, affected parties, market reaction, or loaded adjectives · 9. Selection honesty logged.

Known tension: 5 and 7 pull apart; sacrifice obscurity before scoreability.

### 5.3 What is scored per shock

- **Propagation calls:** for each named entity or carrier — sign, magnitude ordering (not level), lag ordering by mode.
- **Predicate calls:** which arming predicates the operator said would hold; which did.
- **Null calls:** an explicit "no armable position" is a scoreable call, weighted low (§9, hole 5).
- **Baseline comparison:** every call is paired with the dumb baseline (sector + size; "owner down, nothing else").
- **Attribution:** every event hypothesis records which relations it rode. Right-call-wrong-relation is **quarantined** from calibration (round 1, oil).

### 5.4 T0, redefined

v3's T0 was "count 40–80 mechanically selectable shocks." Redefined:

> **T0: count (shock × listed party × carrier) triples that pass the arming predicates including the tradability gate, from a fixed source over a fixed window.**

The unit is the pair, not the shock, because each shock yields 5–20 scored pairs and the relational ledger fills 5–10× faster than any basket ledger. The tradability gate will cut the count hard. Better to know the number before building anything downstream of it. If the number is single digits per quarter, §10 decides the programme's shape.

---

## 6. Retained mechanisms (compressed from v3 §3; unchanged unless noted)

### 6.1 Facts, four kinds
Entity facts (filings, fundamentals — slow, ticker-keyed) · **Node facts** (commodity/regulatory/geopolitical/logistics state — not ticker-keyed, hence in no entity database, hence the important omission) · Forward-dated facts (roadmaps, guidance, scheduled announcements — a free settlement calendar; these are ACKs) · Adoption facts (news, social, analyst output — fast). Fine facts are readouts of coarse states; edge lives in the slow layer; carrying cost is dominated by the fast one.

### 6.2 Statedness × inferredness
Two axes. Statedness is a property of documents; inferredness of actors. The claimed edge is unstated-and-un-inferred; the invisible cell is unstated-but-everyone-inferred. Every document-derived null is ambiguous because of it. **New:** the game's operator distortion "my freshness is not the market's" is a bias toward misreading the invisible cell as the claimed cell. The bounded-channel predicate (§4.3.4) is the operational defence.

### 6.3 Position, not sharing
Two entities relate through a node when both hold a *position* on it (allocation tier, contractual priority, substitutability, share, duration); sign and magnitude are properties of the *difference*. Paired generation is intra-node and satisfies the intra-factor legality guard automatically. **New from round 2:** when one entity holds several positions on the same node, its own outage is partially self-hedged — position maps must be per-plant, not per-company.

### 6.4 Relation modes by transmission
Physical/contractual (cash flows, slow, lossy per hop) · accounting/identity (instant, symmetric) · attentional (fast, reflexive) · analogical (does not transmit — may propose, never support). **Price may confirm a relation; it may never propose one.** Implicit relations are abduced from non-price co-occurrence. Epistemic ordering: stated < inferred < implicit in both edge and scarcity. Irreducible exhaustion is the signature of an implicit relation — a candidate to test by prediction, not an extraction target.

### 6.5 Three processes that look identical under monthly sorts
Statement (step) · contagion (S-curve, random inflection) · independent discovery (linear drift). Any test aggregating across pairs in calendar windows cannot distinguish them; tests align on each pair's own transition event.

### 6.6 Price as compression
Price is a lossy projection at the market's operating resolution. A world/price gap is a decompression residual, not a conflict. Read at the finest resolution available; act at the coarsest the evidence identifies. Implied vol reinterpreted (provisionally) as a stated measure of unresolved residual.

### 6.7 Graph
One store; edges typed by epistemic class; "separate graphs" are views. Hypergraph with fact-set nodes preserves hop structure. Path composition is a free crowding gauge; class migration is decay observed directly — **requires knowable-time on every fact, which is a build-order commitment, not a footnote (§11).**

### 6.8 Netting, validation, shadow book
Direction is the residual after opposing evidence; weight is a count of surviving validations terminating at ground truth or exhaustion; necessity via marginal contribution over subsets, reported continuously. Shadow book is full-information online learning with promotion (§4.6). Factor-selective not neutral; hierarchy is ledger, exposure is flat. Symmetric competitor assigned the opposite side, not a critic — and its shadow baskets are a standing live null.

---

## 7. Standing principles

- **Library proposes, predicates condition, shocks resolve**
- **Permissive generation, strict validation**
- **Proposal rights, support rights, and arming rights differ by mode, source class, and instrument noise**
- **Price is an outcome, never a proposer** — banned on the trigger side, required on the scoring side
- **Every rule in the library forbids something; no proper nouns in rules**
- **A null call is scored, weighted low, and never counted as edge**
- **Granularity declared before the hypothesis forms, and locked**
- **Read at the finest resolution available; act at the coarsest the evidence identifies**
- **Hierarchy is ledger; exposure is flat**
- **Literature is for targeted claim verification at the moment of commitment. Never a design gate**
- **One falsifiable sentence, then the cheapest code that could kill it**
- **Load-bearing vocabulary lives in this document, not in session memory**
- **Amendments to validity are learning; amendments to thresholds are fitting**
- **Novelty is post-hoc, from returns, and only needed to distinguish alpha from repackaged premium**

---

## 8. Evidence — three scored rounds

Operator: Claude, knowledge cutoff end-January 2026. Predictions committed before any search; scoring by web search afterward with contamination noted. Chat-round firewall is a promise, not a wall; §11 replaces it with code.

| Round | Event | Frame | What repriced, where | Equity trace | Verdict |
|---|---|---|---|---|---|
| 1 | Apr 3 2026, US strikes on Iranian infrastructure | Read as fresh shock; was day ~34 of a war, Hormuz already closed | Freight 4× pre-war and sticky; war-risk premia 0.25% → 3–10% of hull into July; methanol +72%, urea to ~$780/t — all by March 20–25 | Everything priced weeks earlier; real trade was short the war basket into ceasefire talks | Tie vs baseline; frame miss dominated |
| 2 | Mar 12 2026, fire at world's largest PO/TBA plant, Pasadena TX | First traversal; operator and technology called correctly from training | FM on derivative day 1, on PO day 5; PO contract +13%; polyol +28%, MPG +34% within weeks; foam costs +15–20% in days; allocation | Owner *upgraded* same day on war-driven sector trade; $250M outage inside a quarter where EBITDA tripled; owner self-hedged via sister plants; co-product cut into a glut → silent | Mechanisms 5/6; prices called; equities null as half-hedged; one clean kill (slack) |
| 3 | Apr 9 2026, bunker spill closes Scheldt / Deurganck Dock | First traversal at event; **not** at node (strike in March, pilots in June, leak in July) | River reopened in half a day; dock ~4 days; ~85,000 TEU lost; port omissions and backlog for a week | None, correctly predicted | Correct null; scored low |

**What the three rounds say together.**

1. The relational layer works at the *map* level: operator, technology, chain, co-products, FM timing were derived cold from training in round 2. "Who does it touch" is a real skill.
2. The lag exists and is large **in contract/commodity/insurance space.** FM letters, allocation, contract resets, freight and premia repriced in days-to-weeks and stayed repriced for months.
3. **In equity space, three events, zero attributable traces**, for three different reasons: pre-priced (1), micro swamped by macro plus private downstream plus owner self-hedge (2), no listed pure-play (3). The game reproduced v3's *recovered-before-entry*, *contamination quarantine*, and *bounded-channel check* organs independently — decent evidence they were real and not jargon.
4. Obscurity window in a hot crisis ≈ 2–3 weeks. Specialist audiences hold the map within days.
5. Nulls are cheap. Three rounds, zero profitable trades armed. The arming rate is the number.

---

## 9. Open holes (revised)

### Critical

| # | Hole |
|---|---|
| 1 | **Scoring harness.** Two ledgers (relational, event), attribution of which relations each hypothesis rode, null calls weighted low, baseline pairing per call, contamination quarantine. Now specified well enough to build (§11). |
| 2 | **Arming rate.** Fraction of mechanically selected events that pass §4.3. Three rounds: 0/3. Unknown at scale. T0 measures it. |
| 3 | **The instrument question.** §10. Premise-level. |
| 4 | **Inferredness instrument.** Bounded-channel set needs calibration against stated-transition ground truth (per-channel lead-time distributions). All candidates right-shifted and confounded with link strength. |
| 5 | **Null weighting.** A system that only wins by not trading has a cost base, not an edge. Weight to be set so that nulls cannot rescue a calibration score. |

### Structural

| # | Hole |
|---|---|
| 6 | **Micro/macro ratio threshold.** The tradability gate needs a number. Measure on rounds as they accrue. |
| 7 | **Position disclosure rate** — per-plant now, not per-company. Determines whether §6.3 is operable. |
| 8 | **Partition problem.** Scored coarser than generated. Pair-unit scoring relieves the relational ledger; the basket ledger still starves. |
| 9 | **Invisible cell.** Bounded ex post by the leaked-fraction of price-path decomposition per relation class. |
| 10 | **Granularity lock enforcement** — by schema field at registration; harness rejects off-granularity resolution claims. |
| 11 | **Assembly is where fitting lives.** Symmetric competitor is the fix; not yet architected. |

### Known costs (carried)

No commercial point-in-time data — hard constraint on retrospective work, and the reason ingestion-time recording must start now. Entity resolution size-biased toward large caps. Paid data reintroduces the wedge. Shadow validates inference, not execution. Capacity single-digit $M per expression.

---

## 10. The instrument question

Stated once, so it is attacked rather than dodged.

The repricing cascades the system can see and predict live in **contract, commodity, freight and insurance** markets — spaces with no tickers in the universe the venture was designed around. The equity shadow of those cascades is diluted by diversified owners, private downstream victims, self-hedging, and macro tides. Three rounds, three different dilution mechanisms, same result.

Three shapes the programme could take. Each is a bet; the pass does not choose.

- **A. Thin equity universe.** Accept that the tradability gate leaves only small-cap listed pure-plays with concentrated exposure to a touched channel. Arming rate falls; capacity is already single-digit $M so this may be tolerable. T0 tells you whether the rate is non-zero.
- **B. Different instruments.** Express in the markets where the lag is visible: commodity futures, freight derivatives (FFAs), listed chemical/fertiliser producers as *sector* proxies where the ambient tide is the trade, options calendars around ACK dates. Operational access dominates; some of these are plumbing-heavy. The old scope decision was "equities and options" for exactly that reason.
- **C. Information product.** Sell the map, not the trade. The library plus the predicate layer is a forecasting product for procurement and supply-chain desks who *do* live in contract space. Not a fund. Changes what "edge" means entirely.

The game can inform this cheaply before any decision: a **listed pure-play census** over the three rounds — which listed names anywhere had exposure to the touched channels above a threshold, and what their equity did. If A has a non-empty universe, the equity thesis survives narrowed. If empty, B or C.

---

## 11. Build path — Claude Code and MCP

Principle: build the **harness**, not the system. The game is T0 in miniature; the harness is the scoring harness (hole 1) with a firewall. Everything downstream is downstream of a number the harness produces.

### 11.1 Components, in build order

1. **Event intake.** One-line event + date; hashed and stored before the operator sees it. Selection rule and rejections logged.
2. **Prediction lock.** Operator's commitments (propagation calls, predicate calls, null call, baseline) written to an append-only, timestamped store *before* any retrieval tool is available. Firewall enforced by tool gating, not promise.
3. **Knowable-time recording.** Every fact and every retrieved document stamped with ingestion time and, where available, source publication time. Starts the bitemporal layer from day one — the one asset that cannot be backfilled.
4. **Scorer.** Two ledgers, attribution, contamination quarantine, baseline pairing, null weighting. Outputs per-mechanism false-alarm rates back into the library.
5. **Library store.** Rules in the §3.2 format; status transitions (candidate → validated) driven by the scorer, not by hand.
6. **Predicate registry.** ACKs as first-class records: source, threshold, date, arm/disarm role, last check. The bounded-channel set lives here.
7. **Shock selector.** Mechanical rule over a fixed source; produces the T0 count.

### 11.2 Exposure

Wrap 1–7 as an MCP server so the same harness serves chat rounds and Claude Code test runs. Tools: `submit_event`, `lock_predictions`, `open_retrieval` (only after lock), `score_round`, `library_query`, `library_propose`, `predicate_check`, `t0_count`. Chat rounds then run under the same firewall as code rounds, and the promise-not-wall problem disappears.

### 11.3 What is deliberately not built yet

Baskets, positions, walks, netting, promotion, capital. All downstream of the arming rate and the instrument question.

---

## 12. Dissolved and superseded

| Was | Dissolved by |
|---|---|
| Trigger as an unverifiable negative | Arming predicates over bounded sets and held properties (§4.3); ACK vocabulary restored |
| "Where does differentiated generation come from" | The scored library, accumulated at one second per second (§3.5) |
| Shock = any dated event | Event vs armable shock (§5.1) |
| T0 counts shocks | T0 counts (shock × listed party × carrier) triples passing the tradability gate (§5.4) |
| Obscurity as a global property | Obscurity relative to the specialist audience, consumed by first traversal, node-level (§3.4) |
| Null as free win | Null scored, weighted low (§9.5) |

---

## 13. Session record — the pattern, continued

v3 recorded that every dead test was scaffolding built inside published methodology. This revision's failures are of a different and better kind: they came from contact with events, not with papers.

- **Frame miss** (round 1): predicted a fresh shock into a mature crisis. Produced four library entries.
- **Sizing timidity** (round 2): derivatives moved 2–3× what was predicted. Right mechanism, wrong magnitude.
- **Obscurity overestimate** (round 2): specialists named the channel in five days.
- **Duration misplacement** (round 3): read the headline's node, not the smaller one that stayed shut.
- **Vocabulary loss across reset:** ACKs reinvented as "trigger." Repaired here; principle added to §7.

The posture toward every mechanism in §6 remains: a claim about how to organise the work, not a result. The library in §3.4 is the newest material and therefore the least tested, not the most. Rounds continue until the arming rate has a number.
