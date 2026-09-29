# Nomad — The System As It Stands

*One file: the ideas, the theory, the amendments waiting on ratification, the v16 specification, the intake requirements and the data-product spec. Written 2026-09-29. Load all of it, or the Sections your job needs (table below).*

**What Nomad is.** An AI-operated research system that looks for relationships between economic and financial entities that are *inferable* from public facts but not yet in relative prices. It plays real events against reality, scores every call, and records which channels actually carried an effect. The bet is that reading widely and cheaply, at finer resolution than the market prices, finds links no single participant's book is organised around. The open question is whether any of it can be held as a position.

---

## A1. How to use this file

### Sections

| Section | What it holds | Status | ≈ Words |
|---|---|---|---|
| **A** | This orientation and the state of play | Current | 1,900 |
| **B** | The ideas in plain terms, with diagrams and two invented worked examples | Explanatory; not normative | 4,400 |
| **C** | The theory record (`T1`–`T12`): what Nomad claims and what fifteen rounds established | **Ratified** (theory v2, plus the 2026-09-29 entity-scope amendment) | 3,800 |
| **D** | Register of the **proposed** amendments to C from the 29 Sep gate redesign | **Proposed**; each waits on Rob | 1,700 |
| **E** | The v16 specification (`§0`–`§35`): conceptual model, system, technical | The build reference; v16 is **not built** | 30,100 |
| **F** | Event Requirements v3: the intake rules | Ratified. §15 applies it in full, adds a `tags_only` mode beside `strict_v3`, and proposes two changes (D9 absence expiry, D15 domain preference) | 1,000 |
| **G** | Data-product isolation spec (`G0`–`G12`) | To build | 4,700 |

### What to load for which job

| Job | Load |
|---|---|
| Get a fresh session up to speed, or a refresher for you | A, B |
| Decide or ratify a claim | C, D (D9 also needs F and E §15) |
| Build or change the harness (Claude Code, Hermes, API loop) | A, E, F; add G for the data-product track |
| Run a round as the operator | C, E (esp. §9, §14–§16), F |
| Build the data product | G, plus `§23` and `§26` of E |
| Everything | The whole file, about 47,700 words |

### Conventions

- **References.** Bare `§n` means Section E (the specification). `Tn` means a numbered part of Section C (the theory), e.g. `T5`. `Gn` means Section G. `Dn` means a row of Section D's register. `Q1a`–`Q9` are Section F's intake questions.
- **Provenance tags** in E (`[carried]`, `[v16]`, `[fold]`, `[gate]`, `[new]`, and `[ratified]` once Rob ratifies a `[gate]` item) say where an item came from. `[gate]` is the 29 Sep redesign. In E §§3–8 and §12 a `[gate]` item is a **proposed amendment** (Section D lists them); elsewhere it is a build decision that carries the proposals into the harness. Tags like `[v16 A1]` and ids like `C1`, `C6`, `A2` inside E refer to the v16 brief's own numbering, not to Sections of this file.
- **Names marked *(v15)*** exist today in the harness on Rob's machine (`C:\Users\bato2\Documents\nomad`, v15, last modified 2026-09-10; 146 MCP tools). Everything else is new.
- **Two kinds of authority.** Where C and E disagree about what Nomad *claims*, C governs. Where they disagree about what to *build*, E governs. Sections A, B and D explain or index C and E, and yield to them if they ever conflict. E's `[gate]` material changes statements C makes today, so until Rob ratifies D it is a proposal that E builds in order to test it.
- **Never rewrite a spec to match the code.** Gaps between E and the build go in `STATE.md` beside it, dated. Rewriting a spec to describe what got built quietly lowers the bar.
- **No verdict-governing number has a default.** Section E §33 lists the ones Rob must set.

### Where each idea is decided

Some ideas appear in more than one Section because they serve different readers. One place owns each.

| Idea | Explained in | Governing text |
|---|---|---|
| Premise, claims, the bet | B1 | T1 |
| Library, positions, effects, ACKs, anchors | B2–B5 | T2–T6, restated for the build in §3–§6 |
| The wall (why nothing passes) | B6 | T9, §11 |
| The gate redesign (derived ACKs, reachable sets, baskets, stories, S⊥, junctions) | B7 | D (proposals), §4, §7, §8, §20–§22 |
| Risk terms and typed gaps | B6 | T8, §8, §20 |
| Data model, tools, phases, kill tests, appetite values | — | E only |
| Intake (which events may be played) | — | F, restated in §15 |
| Data layer | — | G, and §26 |

---

## A2. State of play

### What is established

- **The instrument works for reading.** Consistent edge over a naive baseline in 14 of 15 rounds (theory v2), surviving a second scorer. Absence calls 15/16, occurrence 8/14, map 1/5, magnitude systematically timid. **Caveat:** the 15/16 counts absence calls that expired unanswered as hits, as v15 does. D9 proposes recomputing it under a stricter rule, and P1 reports both numbers.
- **Ruling things out works.** The elimination edge is demonstrated: before retrieval, the system can say which legs are non-positions.
- **The record is small.** Rounds 1–4 learning, 5–10 clean, 11 learning, 12 voided then re-run as learning, 13 clean, 14 and 15 learning and partially scored. **Seven clean rounds.**
- **Expressible edge has no evidence.** No leg in the programme's history has cleared appetite on every term. One attributed re-encode, at latency zero.
- **The wall map, corrected.** Over 251 legs: unassessable 53.8%, `expression` 43.8%, `stake` 1.6%, `pricedness` 0.8%, `structural` 0%. Where all five terms can be computed (nine legs ever), `stake` binds on seven and `pricedness` on two. `stake` is blank on 96% of legs and `operator` on 90%.
- **The same wall, found from the other side.** The Ohmni repository's report 005 (2026-09-18) found that every directional mechanism reaching its gate had zero aligned corroboration. Two systems built separately can rule things out and can't support a direction from invariance alone.

### Why nothing got through

Arming required an AND over risk terms, and two pairs of those terms move against each other. Being listed means being big, which means diversified, so **the more of it you can hold, the less any one event matters to it** (stake against expression). A high-stake event on a listed entity is material and watched, so **the more that's at stake, the more likely it is already in the price** (stake against pricedness). An AND over anti-correlated terms is empty by construction. Six earlier fixes each kept the AND.

### What the 29 Sep redesign does (proposed)

1. **Anchors veto, risk builds.** Only structural impossibility and the time wall kill a hypothesis. The risk engine builds capped-loss positions instead of vetoing legs.
2. **Positions trigger ACKs.** A documented combination of positions that forces a notice is a *derived ACK*.
3. **Narrow the world.** For each ACK, list what its document can say, cut that to what is still reachable, and let the thesis narrow it further.
4. **Baskets respond; they don't predict.** Choose weights that do best in the worst outcome the thesis keeps, with the loss capped in the outcomes it rules out.
5. **Hedge the stories, hold the structure.** Hedge out the stories the market is telling; hold what no active story explains (S⊥); exit when that is gone.
6. **Score in money.** A paper book, split into narrowing, timing and residual gains, minus costs and leaks.

### What is built, designed and pending

| Item | State |
|---|---|
| Nomad harness | **v15 built** and used for 15 rounds. **v16 not built.** The spec evolves v15 in place (`§30`) rather than rebuilding |
| Data product | Isolation spec written (Section G). Rob is separating the data layer from Ohmni's harness in a Claude Code session |
| Decision model | **Laya** (a published model) is the chosen reader. Fine-tuning, the `decider` runtime and shadow mode are **designed, not built** (`§23`–`§24`, track DM). **Jev held**, to be added modularly through the `crowd_mirror` slot |
| Operator runtime | Claude Code today. Hermes Agent with the `claude-subscription-directsdk` plugin is under consideration (`§28`; subscription use through a third-party harness is policy-sensitive, an API key is the stable path) |
| Prediction markets | An adjacent idea (B8). Not specified beyond `§34` |
| Data spend | Free sources only. Spend follows a measured block, never an anticipated one |

### Decisions waiting on Rob

1. **Ratify or reject the amendments in Section D.** Three conflict with statements C makes today: building on switch-derived ACKs (D3; T4's arm/disarm asymmetry), exiting on S⊥ before delivery (D5; T4's exit rule) and building baskets rather than filtering (D7; T7).
2. **Set the P0 values:** `NOMAD_OPERATOR_MODEL` (P0 removes the silent fallback default), and a ratified `DEFAULT_HOP_DISCOUNT`. `§33` lists every other value by the phase that needs it.
3. **Settle the open calls in `§34`:** whether stress-capped instruments (stocks and pairs under stops) stay; which of `absorbed_by_slack` and `no_sink` applies to which effect kind; where `decider` lives.
4. **Author the first obligation templates and outcome vocabularies** from rounds 1–7 only (`§33.3`). They are inputs the machine can't invent, and K10 measures whether they suffice.

### What happens next, and what would stop it

The build runs P0 to P4 (`§32`), with cheap look-backs on the v15 record before the expensive code:

| When | Test | If it dies |
|---|---|---|
| End of P1 | **K8**: do nodes carry listed holders on both sides? | Structural hedges are rare; build on options and event contracts |
| End of P2 | **K10**: were the forced notices derivable from the positions and templates on file? | Emergence is limited by the stores; invest in positions before construction |
| End of P3 | **K11, K12**: does S⊥ separate later-priced from never-priced effects? Do junction flags predict correlation jumps? | Drop the priced test; stop treating junctions |
| Decision point | If **K8 and K10 both die**, stop and choose the programme's shape (`§11`) before building construction | Choose among shapes A, B and C (`§11`); nothing pre-decides C |
| P4 | **K9** rebuild of rounds 5–15; **K13** paper book over live rounds | K9: if the block is in the world (`no_edge`, `no_opposite`, `rho_too_small`) move toward shape C; if it is data (`no_instrument`, `timing_unexpressible`, `modelled_prices`) fix sources first. K13: Claim 1 isn't expressible in capped instruments at this scale, shape C |

Two tracks run in parallel with P0–P4 and never block them: **DP** (the data product, Section G) and **DM** (Laya and the decision-model runtime). K1–K7 (the Laya reader, wiring, the census, procedural chains, notice watch) run inside those tracks (`§31`, `§32`).

### Housekeeping

- The Moni Moni project's copy of the theory doc (`nomad_theory_as_it_stands_v1.md`) is **v1** with the 29 Sep entity-scope amendment. Section C is theory **v2** from the repository with the same amendment applied, and supersedes it.
- A count harmonised on assembly: the descriptive-edge record reads "14 of 15 rounds" everywhere (theory v2). The 22 September spec draft said "13 of 14".

---

# SECTION B — The ideas, in plain terms

*Explanatory, not normative. Each part ends with where the rule is decided. The diagrams and the two worked examples (B7) are invented for explanation and are not recorded rounds. Numbers quoted from the record come from rounds 1–15.*

---

## B1. The premise: a price is a compression

Companies, sovereigns, funds, commodities, currencies and contracts are tied together by facts anyone could look up: who supplies whom, who owns which plant, who is obliged to send which notice. Nomad bets that some of those ties are not in prices yet, and that an AI reading widely and cheaply can find them first.

A price is a lossy summary of the world, kept at the resolution the market's instruments work at. When the world holds something the summary dropped, there is a **residual**. Nomad doesn't argue with prices. It looks for what they left out, and a position closes when the market takes that fact in.

Two questions separate a priced link from an unpriced one, and they are different axes. *Is it written down anywhere?* is a property of documents. *Has anyone worked it out?* is a property of people.

```
                            HAS ANYONE WORKED IT OUT?
                       someone has                nobody has
                 ┌───────────────────────┬───────────────────────┐
   IS IT         │ IN THE PRICE          │ WRITTEN, NOT          │
   WRITTEN  yes  │ written and           │ CONNECTED             │
   DOWN?         │ understood            │ cheap reading closes  │
                 │ nothing left to find  │ this for everyone     │
                 ├───────────────────────┼───────────────────────┤
             no  │ PRICED, INVISIBLE     │ THE CLAIMED EDGE      │
                 │ everyone knows it,    │ not written down, not │
                 │ nobody wrote it       │ worked out: posited   │
                 │                       │ first, then tested    │
                 └───────────────────────┴───────────────────────┘
```

An edge decays as it moves toward the top-left: someone writes it down or works it out. That movement is also the exit. (The grid is an explanatory device; E §7.6 alludes to its bottom-right corner.)

**Two claims.** *Claim 2:* you can capture such relationships (the mechanisms below). *Claim 1:* they stay unpriced long enough to matter. Claim 1 is empirical and still open. What is established is that the lag exists and is large in contract, notice, freight and insurance space: force-majeure letters, allocation notices, contract resets, war-risk premia, incident reports. What is not established is that it can be held in any traded instrument. Fifteen rounds looked only at equities and found one attributed re-encode, at latency zero (K2 tests whether it lies outside the noise).

**The bet** is breadth and cheapness over depth and capital. Two popular answers to "why would anything stay unpriced?" are dead. *Coverage* fails because AI makes reading cheap for everyone at once. *A proprietary schema* fails because a schema is a document, and extraction is the fastest-falling cost there is. Nomad doesn't need a story for why the gap exists, only a way to measure whether it does. What can't be copied quickly is an accumulated, scored record of which channels actually carried an effect, under which conditions, with which lag. It is built by playing against reality, one second per second.

*Decided in: T1, §1.*

---

## B2. The machine: library proposes, predicates condition, shocks resolve

```
 SHOCK ───► POSITIONS ───► LIBRARY ───► GENERATE ───► ANCHORS ───► PREDICATES ───► BASKET
 dated      who holds      how things    permissive:   remove what   may it fire,    each leg has
 event      what, per      connect       every effect  cannot        and when does   its own clock
            asset          (verbs)       the rules     happen        it stop?        and dies alone
                                         allow
   ▲                                                                                     │
   └──── every call is scored; resolved calls re-weight the rules ◄──────────────────────┘
```

- The **library** stores mechanisms as verbs: *constraint prices reprice before commodity prices*, never *Hormuz insurance went up*. No company name ever goes in a rule.
- **Positions** hold the nouns the verbs act on: who holds what, asset by asset. **Library ∘ Positions ← Shock** gives every effect the rules allow.
- **Predicates (ACKs)** are standing conditions that decide which survivors may fire and when.
- **Shocks** are dated events, selected mechanically. Each call is scored against what happened.

Two rules keep this honest. **Every rule must forbid something**, because a rule compatible with every outcome is a slogan. And **weight only comes from contact with the world**. It flows forward one inference at a time, and every step away from a real outcome can only lose weight. Validating a validation never adds weight on top.

A rule also has a **domain**. Round 15 found the first limit: the transmission half of the library was built on events that destroy or withhold a consumable. A cloud outage consumes nothing and leaves nobody short, so no constraint price reprices. That limit is now a rule that forbids, so it can be tested.

*Decided in: T2, T3, §2, §3.*

---

## B3. Anchors, not priors

Cascades don't repeat. The same outage lands differently in a tight market and in a glutted one, so predicting a point from past patterns is close to worthless. Read the other way, the same rules are strong: nothing transmits without a path, a cut into a glut is silent, below the noise band nothing is observable. **A rule that forbids is an anchor. A rule that predicts is a prior.**

So the procedure inverts. Generate the space permissively, run the anchors over all of it, and look at what is left standing. A remembered pattern may *propose* into the space and may never *support* anything, so a wrong analogy costs an eliminated leg, not a scored miss. **A prior is a placeholder for a fact you haven't fetched.** The one exception is bureaucracy: regulators and courts follow rules and do repeat, so base rates are allowed for them and nowhere else.

*Decided in: T5, §5.*

---

## B4. One event, many effects

Two firms sharing a supplier can be hit in opposite directions, so belonging to the same group can't carry a sign. What matters is each holder's **position** on the shared thing: allocation tier, contractual priority, substitutability, share, how long it's committed. Sign and size come from the *difference* between positions. Positions are per asset, not per owner, so an owner with several assets on one node is partly hedged against itself.

A single holder rarely has one sign either. The owner of a failed smelter loses volume, owes deliveries it can't make, and may be forced to send a notice; a rival smelter gains pricing power from the same event. So **the unit is the effect**, and holders are where effects land. Effects form a DAG, and **degree is depth in it**.

```
 EVENT              FIRST EFFECTS                        SECOND EFFECTS (fainter)
                    ┌ smelter owner: volume shortfall (−)
 Smelter            ├ smelter owner: delivery obligation (−) ──► notice owed  (FORCED)
 outage  ───────────┼ concentrate mine: offtake stranded (−) ──► spot discount (−)
                    ├ rival smelter: better pricing (+)
                    └ cathode buyers: input cost up (−)

 Passing an effect through a relation is a table lookup, and most entries say
 "does not transmit": a stranded offtake creates no delivery obligation at the mine.
```

Relations are sorted by how they transmit. Physical and contractual links carry effects slowly and lose some at each hop. Accounting links carry them instantly. Attention and classification move fast and feed back on themselves. Analogy carries nothing. **Only physical, contractual and accounting links may support a claim.** Price may confirm a relation and may never propose one. Support decays with each hop, and that decay is the depth limit.

*Decided in: T6, §6.*

---

## B5. The clock: ACKs

An **ACK** is a standing condition: a named source, a threshold and a date, set in advance so a wrong idea never fires instead of firing and then piling up risk. The event is the thesis, the ACK is the clock, the positions are the footprint.

Two kinds carry the whole strategy:

- A **scheduled** ACK sits on a calendar: a results date, a regulatory deadline.
- A **forced** ACK is an obligation whose *timing is not public*. A producer that can't deliver must send a force-majeure letter. A regulator must answer inside a statutory window. A restart statement must come.

A system that only moves on calendared facts only moves where the market is already looking, and so inherits pricedness by construction.

What gets forced is **information and goods**, not capital: the letter must be sent, the cargo rerouted, the allocation made. Whether the market reprices is still a choice other people make. Nomad claims the fact arrives and **measures whether the price changes**. A fired ACK must deliver a fact; "the date passed and nothing was said" prunes a branch rather than advancing it.

```
 day 0 · lock        day 7 · forced notice      day 21 · results date    day 60 · calls due
    │                       │                          │                       │
    ├─ segment 0 ───────────┤                          │                       │
    │  locked on what       ├─ segment 1 ──────────────┤                       │
    │  was knowable         │  effects named when the  │                       │
    │                       │  notice fired: stake from│                       │
    │                       │  a fact that did not     │                       │
    │                       │  exist at lock           │                       │
```

That last box is the **walk**, and it is the only known escape from a bind described next: stake created by a firing ACK cannot have been priced in advance, because there was nothing to price.

*Decided in: T4, §4, §22.*

---

## B6. The wall: why nothing got through

Fifteen rounds gave a clear shape. Effects with a path land on holders that can't be held, and the holders that can be held have nothing at stake.

```
                        CAN IT BE HELD?  (expression)
                        no                         yes
              ┌─────────────────────────┬──────────────────────────┐
   high       │ private operators,      │ empty after 15 rounds    │
   IS         │ single assets           │                          │
   ANYTHING   │ lots at stake,          │  (open questions: effect │
   AT STAKE?  │ nothing to buy          │   paths; bonds; parents) │
   (stake)    ├─────────────────────────┼──────────────────────────┤
   low        │                         │ big listed parents:      │
              │                         │ tradeable, but the event │
              │                         │ is a rounding error      │
              └─────────────────────────┴──────────────────────────┘
```

Two mechanisms drive it, and both have a reason. **Stake ↔ expression, through size:** being listed means being big enough to list, which means diversified enough that one asset is a fraction of the band. **Stake ↔ pricedness, through materiality:** a high-stake event on a listed entity is material, disclosable and watched, so it is in the price before Nomad can know it.

**Risk is kept as five separate terms and never multiplied:** is anything at stake, is the structure right, is it already priced, how often is the operator wrong on this kind of call, can it be held. A product hides walls. Five terms at 0.6 multiply to about 0.08, and one term at 0.03 with four at 0.95 to about 0.02: both look poor, and they describe opposite situations.

**Unknown is a value, not a verdict.** A check with no data neither passes a leg nor fails it, and every gap says why: it can't be computed honestly, it wasn't published, it's outside our reach, or it doesn't apply. That rule exists because the first wall map was wrong. It took the minimum over only the terms it could compute, so an unknown term could never bind, and walls were credited to whichever computable term happened to be lowest. Once corrected, the map said: `expression` is the one wall we've measured, and over half the map had never been read.

**Why the old gate emptied itself.** Arming required an AND over eight predicates and the risk terms. Two pairs of those terms move against each other (stake and expression, stake and pricedness), so an AND over them is empty by construction. Six earlier fixes each kept the AND. *A filter never violated is a filter never tested.*

*Decided in: T8, T9, §8, §11.*

---

## B7. The gate redesign (proposed 29 Sep)

Every idea here is a **proposal** until Rob ratifies it (Section D). All of it is specified in §4, §7, §8 and §20–§22.

### 1. Anchors veto; risk builds

Only two things kill a hypothesis: an **anchor** says it structurally can't happen or can't be seen, or the **time wall** says it couldn't have been known. Everything else that used to veto a leg (a small position share, a channel already traversed, a recurring "weather" event, no listed instrument on this holder) becomes an *input to construction*. The risk engine's job is to build a position with a capped loss, not to say no.

### 2. Positions trigger ACKs

The old AND ran over each leg's risk terms. The new one runs over the **set of positions**, cross-referenced. When a documented combination makes a notice unavoidable, that is a **derived ACK**: forced, obligatory, and found by the machine rather than by the operator's imagination (the operator ratifies each one, and may decline any basket it builds). Unknown conditions don't kill it. They make it a **switch**: an ACK candidate with a list of facts to fetch. Obligation templates live in the library.

### 3. Narrow the world

Given an ACK, very little can happen. Close the world (only what the library, transform table and procedural chains can produce; anything else is a *piano falling from the sky*, logged as a leak and never modelled). List what the ACK's document can say. Cut that to what is still reachable. Let the thesis narrow it again.

```
 Ω   every outcome the notice could contain        <2 wk │ 2–6 wk │ >6 wk │ FM declared │ other
     │  cut by what is impossible: anchors, parts lead times, statutes, inventory
     ▼
 R   reachable      (unknown keeps an outcome IN)          2–6 wk │ >6 wk │ FM declared
     │  narrowed by the thesis, each exclusion citing the positions or rules behind it
     ▼
 Ωₜ  thesis set                                                    >6 wk │ FM declared

 'other' sits outside the closed world: never covered, booked as a piano if it happens.
```

The edge, stated once: **what the market pays for outcomes outside the thesis set, minus costs.** We never claim to know which outcome inside the set happens. We claim to know what's outside it.

### 4. Baskets respond; they don't predict

A trader with one stock can predict a direction or pay for options on both sides. A basket built from positions has a third choice: **the structure supplies the hedge**. Holders on a shared node sit on opposite sides of it, so the building blocks already respond in opposite directions to the same event. The basket doesn't follow the market's reading of the event; it is built so that no reading matters.

```
 payoff by scenario         tide down    tide flat    tide up
 outcome the thesis keeps      ≥ z          ≥ z          ≥ z        z is as high as it can be
 outcome the thesis drops    −small       −small       −small      loss capped in advance
```

Weights are chosen to make the worst kept cell as high as possible (**maximin**), with the whole loss budget committed so that "worst case" is a real number rather than zero. If the worst case clears an edge margin, build. If it falls just short, build anyway when every instrument is hard-capped and enough thesis scenarios pay (flagged `capped_tolerance`). Otherwise the basket is **unbuildable, and the reason is recorded** (no opposite holder, bands too wide, costs, no instrument, no edge). The histogram of those reasons is the new wall map.

### 5. Hedge the stories, hold the structure

This is *narrative* hedging, not position hedging. The basket keeps the structural view and hedges the **stories the market is telling**. Every story is a direction across instruments (its *loading*), classed by its angle to the thesis:

| Story | What it is | What to do |
|---|---|---|
| **Orthogonal** | Unrelated to the event but moves the same names: rate cuts, an index flow | **Hedge it out.** It's tide |
| **Parallel** | Already says part of what the structure says, through the obvious channel | **Hedge it out.** What it explains is priced |
| **Adjacent** | A neighbouring reading the market isn't telling yet, one step toward the thesis | **Hold it.** It's the route by which the market reaches the structure |
| **Synthetic** | A composite built from other stories | **Break it into parts** and class each |

### 6. S⊥, and the exit

```
   S  (the thesis) ──┬── the part the active stories already explain   → hedged; it is priced
                     └── S⊥: the part no active story explains         → what the basket holds
```

**S⊥ is "unpriced" written as a number.** If the thesis sits inside the span of the stories already running, it's priced and there is nothing to build. If a large part points where no story goes, that part is the unpriced relationship. As adjacent stories take hold, the span of active stories grows until it covers the thesis and S⊥ shrinks to zero. **That is the exit**, and it is measured rather than guessed. Because the hedge cancels whatever the market already knew, the basket makes money only if a relationship was unpriced and then got priced when the fact arrived: *its P&L is Claim 1 turned into money.*

### 7. Junctions

Unrelated stories start moving together when their paths meet at a **shared, constrained node**, usually because an ACK lands there.

```
 story A: gulf gas ─────► LNG offline ─────┐
                                           ├──► [ electricity price ]  ← constrained node
 story B: data-centre power demand ────────┘
 Before the notice lands, A and B move independently. After, they move together.
 A hedge that treated them as independent breaks. Hedge them as one story.
```

Junctions are predictable from structure, so they are flagged at lock. A correlation with no shared node behind it is noise (a piano), never a junction. Loadings are re-estimated at every ACK.

### 8. Book rules

**One basket per ACK, never netted against another** (netting across baskets nets away divergence). Cover only the reachable set: buying protection against outcomes the anchors ruled out pays for the thing we're supposed to be paid for. **Every held position has a maximum loss known at entry.** The loss budget is per *tide*, not per basket: ten baskets on one conflict are one bet.

### 9. Scored in money

Every built basket is entered in a **paper book** at lock. Nothing is traded. Each result splits into `narrowing + timing + residual − costs − leaks`, so "made money" and "was right" can't be confused, and a basket that wins only because its leaks went its way counts as a loss.

### Two worked examples (invented)

**A derived ACK.** A furnace fails at an unlisted smelter. The positions on file show: the smelter owes contracted deliveries to several buyers; a concentrate mine is tied to it by an offtake; no other smelter is reachable inside the window. An obligation template in the library says *an operator that can't deliver under contract, with no substitute inside the window, must notify its counterparties*. Every condition is documented except one: whether inventory at the buyers covers the gap. So the ACK is derived as a **switch**, and "buyers' inventory days" goes on the fetch list. The notice's vocabulary is *restart under 2 weeks / 2–6 weeks / over 6 weeks / force majeure declared / other*. The furnace rebuild lead time on file cuts "under 2 weeks". The thesis, resting on the mine's stranded offtake, also drops "2–6 weeks". What remains can be compared with a market only where one quotes the outcomes (an option surface, an event contract). Because the ACK is still a switch, only hard-capped instruments are allowed, at a reduced budget. The unlisted holders supply the conditions and the clock; the listed instruments carry the trade.

**The stories.** A strait closes and oil rises. The thesis: a fuel-hedged airline outperforms an unhedged one. *"Oil up, airlines down"* is **parallel**: the market is already telling it, so it's hedged out. *"Rate cuts"* is **orthogonal**: tide, hedged out. *"Fuel hedges are what matter this time"* isn't on the tape yet and points toward the thesis: **adjacent**, held. *"Middle East risk premium"* loads on oil, defence, shipping and airlines together: **synthetic**, decomposed into its parts. S⊥ is what's left of "hedged beats unhedged" once the running stories are subtracted. When the market starts telling the fuel-hedge story, S⊥ shrinks, and the basket exits.

---

## B8. Adjacent idea: prediction markets

A prediction-market contract is an ACK with a price. Nomad's wall disappears there, because the instrument is the event and the loss is capped at the price paid. That makes event contracts a natural building block (§20.6) and a natural place to test the gate. A separate project (a Polymarket agent forked from PredictionProphet) would wire in a decision model and use Nomad as the risk engine, replacing the fork's twenty generated subqueries with the set of relevant first principles gathered by a recursive search chain. The idea: decompose a contract into its **necessary conditions**, bound the probability above by the weakest of them (Fréchet bound, summed over alternative routes), keep the market price out of the reasoning until the gate. **This is not specified in this file**; `§34` records it as a separate spec.

---

## B9. Reading the reader (the decision-model fold)

The operator is expensive per judgment and good at proposing. A small decision model (Laya, to be fine-tuned; §24) is nearly free per judgment and can only choose among options it is given. So **the operator lists the pieces** (effects at holders) and **the model checks every link between them**. The operator's habit is to draw famous names, first-order links and connections that make good sentences; checking every pair removes that selection by construction.

The model's scores decide **the order** things get looked at and fetched. They never become weight, support, a veto or a construction input. Attention is the scarce resource. A prior may spend attention but never evidence.

**Spread probes.** Ask the same link question twice, once without the document that would settle it and once with it, and read how the *shape* of the answer changes:

| Shape after the document | Reading | What to do |
|---|---|---|
| Collapses from wide to narrow | **Ignorance**: the reader lacked the fact | Fetch it; not a gradient |
| Stays tight and high | **Mechanical**: transmits by construction | A structural link |
| Stays centred | **Graded**: loses some on the way | Real attenuation |
| Splits into "none" and "full" | **Switch**: hinges on an unknown fact | **An ACK belongs here** |

The model finds where an ACK belongs; the operator decides whether to arm it. A related idea is held: a commoditised model's confidence may measure how *obvious* a link is, and obvious links are probably already priced. That needs a model everyone uses, the slot Jev would fill, and can only run on live rounds where the model can't already know the outcome.

*Decided in: §10, §23–§25.*

---

## B10. Integrity: nothing from after the event

Every input obeys one rule: **nothing may be used at time T that couldn't have been known at T.**

- **Documents:** anything knowable on or before the event date is fair game. It's a time wall, not a retrieval wall, so a round tests the system rather than the operator's memory.
- **Prices:** a segment's loadings, volatilities and bands use only sessions before that segment's clock. Every price comes from a frozen, hashed vintage.
- **The library:** when playing a round dated D, the operator sees rule weights computed only from outcomes knowable by D.
- **Models:** a model may answer about T only if it trained on nothing after T. An unknown cutoff counts as the release date.
- **The operator:** a fresh session each round with no memory. Only the ledger, the library as of the event date and the documents cross between rounds.

*Decided in: §9, §14.*

---

## B11. What decides it, and what would kill it

The **ownership census** (K7) can close the equity version: take every high-stake unlisted holder from the record and ask whether any listed parent, bond or partner carries concentrated exposure to it. If almost never, that is a result in its own right. K8 and K10 gate whether construction is worth building, and K13 is the verdict. The programme then takes one of three shapes:

| Shape | Idea |
|---|---|
| **A** | A thin equity universe of listed pure-plays |
| **B** | Different instruments: credit, options around notice dates, event contracts, closer to where the lag shows up |
| **C** | Sell the map. Procurement and supply-chain desks already live in the contract space where the lag is visible. Reading events and ruling things out is what they would buy |

v16 points at **B, with equities as building blocks.** Headline and geopolitical events fit best, because they come with forced notices, priced options and event contracts. Each idea above with an empirical claim has a kill test written before it runs (§31):

| Test | Plain question |
|---|---|
| K7 | Does any listed instrument carry concentrated exposure to the high-stake unlisted holders? |
| K8 | Do real nodes carry listed holders on both sides, or is there nothing to hedge with? |
| K9 | Rebuilt under v16, does any past round produce a basket? |
| K10 | Were the forced notices that actually arrived derivable from what we had on file? |
| K11 | Is S⊥ larger on effects that later got priced? |
| K12 | Do flagged junctions show bigger correlation jumps than unflagged pairs? |
| K13 | Over enough independent tides, does the paper book beat costs plus leaks? |

If K8 and K10 both die, stop before building construction and choose the shape.

*Decided in: §11, §31, §32.*

---

## B12. The rules that don't move

- Library proposes, predicates condition, shocks resolve.
- Generate permissively, validate strictly.
- Price is an outcome, never a proposer.
- Every rule forbids something. No proper nouns in rules.
- A prior is a placeholder for a fact you haven't fetched.
- Weight flows forward and never accumulates.
- Unknown is a value, not a verdict. Could-not-compare is never read as compared-and-differed.
- Anchors veto; risk builds. Every held position has a maximum loss known at entry. *(proposed)*
- Thresholds are appetite: set once, never moved because they weren't met.
- Spend follows a measured block, never an anticipated one.
- An idea is scrapped for a stated cost, never for its label.
- One falsifiable sentence, then the cheapest thing that could kill it.

The full lists are T11 and §12.

---

# SECTION C — Theory as it stands

**Theory v2** (fifteen rounds), **with the 2026-09-29 entity-scope amendment (D0).** Supersedes v1, including the copy in the Moni Moni project. The theory of the system, separate from the harness that tests it. Parts are cited as `T1`–`T12`.

This Section holds what Nomad *claims* and what fifteen rounds have established or killed. It changes when a claim changes, not when the build does.

**What changed from v1, and only this:** T9's wall map was resting on a number v1 flagged as generated wrong. It has been recomputed. The finding's *shape* survives; its *ranking* does not, and one of the two walls v1 named turns out not to be a wall at all. T10's first open question is therefore answered, and everything v1 said was downstream of it moves. T3, T5, T6 and T7 gain the effect DAG as their unit. Everything else stands as written.

---

## T1. Premise

> Economic and financial entities are linked by relationships **inferable** from verified facts. Some are not reflected in relative prices. An agent that reads all of them, at a finer resolution than the market prices, and assembles across kinds of fact that no single participant's book is organised around, sees relationships that are unpriced.

**What counts as an entity.** Any economic or financial entity: companies and their individual assets, sovereigns and state agencies, central banks, funds and indices, commodities by grade and location, currencies, and contracts — bonds, derivatives, offtakes, event contracts. Entities relate through a node they both hold a position on, and the same thing can be a holder in one relation and a node in another: a sovereign holds a position on a strait and is itself the node its bondholders hold positions on. Companies were the first case studied, never the scope.

Two claims:

- **Claim 2 — you can capture it.** The mechanisms in T3–T6.
- **Claim 1 — they are unpriced for long enough to matter.** Empirical, and after fifteen rounds still the open question. What is established: the lag **exists and is large in contract, notice, freight and insurance space** — force-majeure letters, allocation notices, contract resets, war-risk premia, and now incident reports and service-credit claims. What is not established at all: that it is expressible in any traded instrument. Fifteen rounds looked only at equities: one attributed re-encode, latency zero.

**The bet:** breadth × cheapness × a differentiated hypothesis space beats depth × capital. Real, with a real prior against it, and with a specific complication: the place the edge is *visible* may not be the place it is *tradeable*.

Two candidate answers to Claim 1 are dead. *Coverage* — cheap reading commoditises it. *Ontology as moat* — a schema is a document, and extraction cost is the fastest-collapsing cost there is.

---

## T2. The three layers

> **Library proposes · Predicates condition · Shocks resolve.**

| Layer | What it is | Plain question |
|---|---|---|
| **Library** | A store of *mechanisms* — ways things connect. Verbs, not nouns. | "How could this event reach anyone?" |
| **Predicates (ACKs)** | Standing, machine-checkable conditions: named source + threshold + date. | "Is this idea allowed to fire, and when does it stop?" |
| **Shocks** | Dated events, mechanically selected. | "What happened, and did the predicted propagation occur?" |

A fourth store sits under the library and is easy to lose: **positions**. The library holds the verbs; positions hold the nouns the verbs act on; a shock is the argument. Library ∘ Positions ← Shock.

---

## T3. Library — the hypothesis space

**It stores verbs.** **No proper nouns in a rule, ever**; one worked example lives in a provenance field, exempt.

**Every rule must forbid something.** *A rule that forbids is an anchor; a rule that predicts is a prior* (T5).

**Rules declare what they carry** — `occurrence | absence | ordering | magnitude | duration | map` — and a citation outside a rule's carriage is refused.

**Weight propagates forward and never accumulates.** The only source of weight is contact with the world. **The fitting risk is not the discount factors — it is narrowing (validating, arming, promoting) on state that was not propagated.**

**A rule has a domain, and the domain is discoverable.** Round 15 found the first one: the whole transmission half of the library — constraint prices lead, the toll booth learns before the cargo, a cut into a glut is silent, allocation dates the move — was built on events that destroy or withhold a **consumable**. An availability failure has none: nothing is consumed, nobody is short afterwards, there is nothing to allocate and no constraint price to reprice. That limit is now a rule that forbids, so it can be tested rather than rediscovered.

### Current entries, grouped

*Sequence and state:* novelty belongs to channels, not events · recurring disruption is priced as weather · late in a crisis the neglected side is resolution · the headline names what reopened, not what stayed shut · a repeat filer gets the base-rate procedure.

*Transmission:* a cut into a glut is silent · the move is largest where substitution is hardest · the toll booth learns before the cargo · constraint prices de-escalate slowest · a tide sets the price of everything it touches · a catalyst that does not concern the node is a tide · a toxic release closes the shared space · **an availability failure consumes nothing and leaves nothing short, so no constraint price reprices** · **an operator of shared infrastructure under an availability commitment must publish an account of a multi-tenant failure, and the account precedes the money.**

*Ownership and visibility:* the wounded owner of the substitutes collects its own scarcity premium · equity visibility = event size ÷ ambient tide · a lag without a listed pure-play is a spectacle, not an edge.

*Operator distortions:* my freshness is not the market's · specialists already hold my map · overweights famous names and first-order links · underweights boring intermediaries and second-order plumbing · knowing a rule is not applying it · substitutes a remembered generic pattern for a fetchable specific fact (map calls 1-for-5, with a sixth flagged for dispute).

---

## T4. Predicates — ACKs

An **ACK** is a standing predicate: named source + threshold + date, prepositioned so a wrong idea *does not fire*.

**Arm/disarm asymmetry.** A false disarm costs a missed trade; a false arm costs money.

**`scheduled` vs `forced`.** Scheduled ACKs are calendared. Forced ACKs are obligations whose *timing is not public*. This is load-bearing, because **a system advancing only on calendared facts advances only where the market is already looking** — it inherits pricedness by construction.

**The ACK graph is a second space, and it is a DAG.** Knowability is not a field on an effect; it is its own graph, because *a field cannot branch*. One fact advances several effects at once, and **a shared ACK is structural correlation on the time axis** — known before any price exists.

**A fired ACK must deliver a fact.** "The date passed and nothing was said" is an absence fact: it prunes, it does not advance. Without this, "advance the walk" becomes "keep the round alive", and a walk that cannot terminate is a thesis that cannot be killed.

**Forced flow, relocated.** What is forced here is not capital but **information and goods**. The ACK forces a *re-encode*: at a known moment the market's projection is obliged to take in a fact it did not have. **We claim the information arrives; we measure whether the compression changes.**

**Exit is derivable**, and it is a date rather than a number measured afterwards: the **first attention ACK after the structural ACK**. A fact delivered to a channel nobody who marks the security reads changes nothing.

---

## T5. Anchors, not priors

Cascades do not repeat. **Priors over outcomes are close to worthless here.**

An anchor says what **cannot** happen. So the procedure inverts: **generate the hypothesis space permissively, run the anchors as eliminators over the whole space, and see what is left standing.** Analogies may *propose* and may never support.

**A prior is a placeholder for a fact you have not fetched.** **Base rates are permitted only for procedural actors** and are forbidden for cascades.

---

## T6. Effects, positions, and the shape of a claim

**The effect is the unit, not the leg.** A leg carries one sign and the world does not. A concentrate buyer facing an outage has higher input cost **and** volume shortfall **and** a delivery obligation **and**, if diversified, better pricing on competing output — four effects, different magnitudes, timings and carriers, some opposed. An effect **is** a claim, with its own carrier and falsifier, so a holder with five effects has five chances to be wrong, not five chances to be right.

**No sign at generation time.** Sign is a projection applied at the worst possible moment: it forces the answer before the work and discards everything that does not fit. **Net direction is derived late**, over a stated holding window. A holder whose effects net to zero over one window and to something over another is exactly what the leg model could not see.

**Effects are degrees, and the structure is a DAG.** The chain is not holder→holder with effects attached; the chain *is* effects, and holders are where each effect lands. `d1 → d3` need not route through the same `d2` as `d1 → d2`, so depth is depth in the DAG rather than hops between holders, and two effects on one holder can sit at different depths.

**Position, not sharing.** Set membership cannot carry sign. Two holders relate through a node when both hold a *position* on it, and sign and magnitude are properties of the **difference in positions**. Positions are per asset, not per owner.

**Relation modes, cut by transmission.** Physical/contractual (slow, lossy per hop) · accounting/identity (instant, symmetric) · attentional/classificatory (fast, reflexive) · positional/analogical (does not transmit). **Only physical, contractual and accounting relations may support.** Price may confirm a relation and may never propose one. **`transmits` is a property of the edge**, so the admissibility rule lives in the data structure rather than in a reviewer's memory — which stops the graph treating its own silence as evidence.

**Composition through a relation is a mapping, not a sign flip**, and **most entries in the transform table are "does not transmit"**. Naming the relation correctly is what decides which effects exist: round 15's compositions were unreachable under `offtake` and correct under `input_supply`, which is the same relation read from the other side.

**Attenuation is the depth limit.** Decay is a limit the world imposes rather than one we pick. **Re-rooting resets attenuation only where the effect is independently carried** by its own document. Re-rooting on inference is inference laundering and is refused, not discouraged.

---

## T7. The basket, and what is held

**The event is the thesis, the ACK is the clock, the positions are the footprint.** There is no basket-construction step, only a filtering one. Each leg has its own falsifier and dies alone.

**Three levels, three questions.** *Effect* — was the claim right. *Basket* — did the construction work. *Set* — which effects are implied across interpretations. Consistency across the three is the diagnostic, and it is detectable **because all three numbers exist**.

**Balancing within a basket is not balancing across baskets, and across is forbidden.** **Netting across baskets nets away divergence.**

**A basket carries exposures nobody wrote down**, and this *sharpens* as construction improves. It must be **declared at construction and typed as a floor**. If it cannot be named, the construction is not understood well enough to hold. `basket_stake = intended residual ÷ declared exposure`; below 1.0 the basket is a position on something nobody chose. Round 15's would have read **0.0093**.

**Cross-membership is convergent implication** — weight as a count of surviving independent derivations, discounted by the depth of the most recent common ancestor, walking transmitting edges only. **Compute it both ways and write both rankings: if they agree, the discount is doing nothing and the paths were never independent.**

**The most cross-supported effect may be robust because it is inert.** If nothing touches a holder, every path trivially implies "nothing happens here." Support says how *conditional* an effect is; stake says whether it is worth being unconditional about. Both, always.

**A bridge is not an object.** An effect path **is** a position when some node in it clears expression and some ancestor has stake. No new mechanism, no hop limit, and not a loosening: the path stays admissible at every hop and attenuation still applies. What changes is only that stake and expression need not be properties of the same node.

---

## T8. Risk

**The five terms, kept as a vector.** `stake`, `structural`, `pricedness`, `operator`, `expression`. **Never multiplied.** Five terms at 0.6 and one term at 0.03 with four at 0.95 collapse to the same product and are opposite situations: uniformly mediocre, versus one **wall**. *(Assembly note: 0.6⁵ ≈ 0.08 and 0.03 × 0.95⁴ ≈ 0.02. The products are close in kind, both low, not equal; the point that the situations are opposite stands.)*

**Unevaluable is a value, not a verdict** — and it is not a pass, not a fail, and **not a synonym for anything else**. An anchor with no data discounts confidence. A term with no value makes the binding term **unassessable**, because an unknown term can bind below every computable one. A frontier with nothing readable has not converged to price; it has never been compared to price. Every one of those was, at some point, silently reported as its opposite.

**No load-bearing computation swallows a failure.** Five such failures were found in the v14 code by audit and a sixth by running v15. One of them produced a published finding (T9).

**The operator is a risk term.** Absence 15/16, occurrence 8/14, map 1/5, magnitude systematically timid. Computed from clean resolutions, never self-reported.

**Permissible risk has a shape.** We are paid for being wrong about structure. Not for tide risk, timing beyond the ACK, or liquidity on thin names.

**Arming as built was an AND over eight predicates.** Zero armed legs did not discover that arming is hard — it specified arming to be near-impossible and then measured that it was. **A filter never violated is a filter never tested.**

---

## T9. What fifteen rounds established

**The instrument works.** Consistent edge over a naive baseline in fourteen of fifteen rounds, surviving a second scorer. The map skill is real for structure and poor for causes.

**Three kinds of edge, and only two are demonstrated.**
- **Descriptive edge** — we read an event's structure better than a crude reader. Demonstrated. The baseline is a naive *reader*, not a competitor, and it holds nothing either.
- **Elimination edge** — we can say before retrieval which legs are non-positions. Demonstrated, four rounds running, and underrated: it is what makes searching for a live leg cheap.
- **Expressible edge** — no evidence.

**The composition of the score matters.** Most of the edge is absence calls and orderings against a baseline that predicts movement. **A scorecard weighted toward nulls flatters a null detector.**

**Institutional occurrence is callable; market occurrence is untested.** Stoppage statements, regulator investigations, restart dates, incident reports — all hit, several off base rates. "Will a price move" has never had a fair test, because every event sampled was too small for anything to transmit to.

### The wall map, corrected

**v1 of this document flagged its own T9 as resting on a number generated wrong. It was, and the correction removes a wall.**

`binding_term` was `min()` over the terms that happened to have a value. Ranking that way today reproduces v14's published table to within a point — structural 49.0%, expression 44.6%, pricedness 2.8%, stake 2.4%, operator 1.2% — which confirms the defect as its cause. Ranking honestly, over the same 251 legs:

| binding term | legs | |
|---|---|---|
| **unassessable** | 135 | 53.8% |
| expression | 110 | 43.8% |
| stake | 4 | 1.6% |
| pricedness | 2 | 0.8% |
| **structural** | **0** | **0%** |

**`structural` binds on nothing.** Of the 135 unassessable legs, 123 are ones the old method attributed to `structural`.

What survives:

- **`expression` is the one demonstrated wall**, on 44% of legs, and that attribution is honest by construction: `expression` reads 0.0 on an unlisted holder, and no unknown term can bind below zero.
- **On the other 54% we do not know what binds**, because `stake` has no value on 96% of legs and `operator` on 90%.
- Where all five terms can be computed — nine legs in the programme's history — `stake` binds on seven and `pricedness` on two, at 0.005 to 0.4 against an appetite of 1.0.
- **No leg in the programme's history has ever cleared appetite on every term.**

**The two anti-correlations behind it stand, and both have a mechanism.** **Stake ↔ expression through size**: being listed means being big enough to list, which means diversified enough that one asset is a fraction of the band. **Stake ↔ pricedness through materiality**: a high-stake event on a listed entity is material, disclosable and watched, so it is in the price before it is knowable to us.

Round 15 is the sharpest instance yet, in a domain the programme had never touched: the operator of a flagship cloud region carries `stake` 0.026 of its own band against `expression` 0.75; the region itself carries the whole event and `expression` 0.0. **Being large enough to own the node is why the node cannot matter to you.**

**"Selection is the only lever" does not survive as stated.** It was read off the table the defect produced. What replaces it: *expression is the one wall we have measured, and over half the map has never been read.* **Fixing computability is prior to fixing selection.**

---

## T10. Open questions, in the order they decide things

1. ~~Does the corrected wall map still say selection is the only lever?~~ **Answered: no.** It says expression is the one demonstrated wall and half the map is unread. Everything below is now downstream of *making the map readable*.
2. **Can a walk reach stake that did not exist at lock?** The facts that generate direction mostly do not exist at lock. Stake created by a firing ACK **cannot have been pre-priced, because the fact did not exist to price**. This is the only known escape from the stake↔pricedness bind, and it is now the first question rather than the second. Round 15 walked one generation on a forced ACK that delivered; whether the fact it delivered *created* stake anywhere is what the next rounds test.
3. **Do effect paths bridge the two walls?** A path is a position when a descendant clears expression and an ancestor has stake. Reported per round; empty so far, and empty is a reportable answer.
4. **Do credit instruments concentrate what equity dilutes?** Same event, same entity: stake 19.02 on the bond against 7.12 on the equity.
5. **Is there a listed pure-play universe at all?** An empty census closes the equity thesis.
6. **Structure vs narrative on divergent legs** — pre-registered, untested for want of divergent legs.
7. **Do synthetics pass where naturals fail?** Two of three attempts failed on component quality rather than structure.

**The three shapes the programme could take**, unchanged: **A** a thin equity universe of listed pure-plays; **B** different instruments — credit, freight, options calendars around ACK dates; **C** an information product, selling the map rather than the trade, to the procurement and supply-chain desks who live in the contract space where our lag is visible. Descriptive plus elimination edge is exactly what C sells and exactly what a fund cannot.

---

## T11. Standing principles

- Library proposes, predicates condition, shocks resolve
- Permissive generation, strict validation
- The effect is the unit; a holder with five effects has five chances to be wrong
- Sign is derived late and never recorded at generation time
- Proposal rights, support rights and arming rights differ by mode, source class and instrument noise
- Price is an outcome, never a proposer — banned on the trigger side, required on the scoring side
- Every rule forbids something; no proper nouns in rules; and a rule has a domain
- A rule that forbids is an anchor; a rule that predicts is a prior. Anchors constrain a space; priors predict a point
- A prior is a placeholder for a fact you have not fetched
- Weight propagates forward and never accumulates; narrowing on unpropagated state is the fitting risk
- **Unevaluable is a value, not a verdict — and never a synonym for its opposite.** An anchor that cannot be evaluated is absent; a term that cannot be computed makes the binding term unassessable; a frontier that cannot be read has not converged
- No load-bearing computation swallows a failure silently
- A null call is scored, weighted low, and never counted as edge
- The calendar chooses the branch; choosing one is selection at generation two
- A fired ACK must deliver a fact, or the branch terminates
- Read at the finest resolution available; act at the coarsest the evidence identifies
- Hierarchy is ledger; exposure is flat
- Granularity is declared before the hypothesis forms, and locked
- Literature is for targeted claim verification at the moment of commitment. Never a design gate
- One falsifiable sentence, then the cheapest thing that could kill it
- An idea gets scrapped for a stated cost, never for its label
- Load-bearing vocabulary lives in a document, not in session memory
- Amendments to validity are learning; amendments to thresholds are fitting
- Thresholds are appetite: stated once, reviewed on a schedule, never moved because they have not been met
- Novelty is post-hoc and only needed to distinguish alpha from repackaged premium

---

## T12. Where the rest lives

Harness briefs `cc_brief_for_v7.md` … `cc_brief_for_v15.md` and `RECONCILIATION.md` (what the briefs claimed vs what the code does) live in the repository; round recaps 1–15 live in `docs/rounds`. The build reference that supersedes the briefs is Section E; the intake rules are Section F (`event_requirements_v3.md`); the data layer is Section G. The harness is at `harness/`; the ledger holds the round record.

**Vocabulary lost once and rebuilt worse:** ACKs were reinvented as "trigger" across a context reset. That is why this document exists separately from the build.

---

**Proposed changes to this Section are in Section D.** They are not applied here until Rob ratifies them.

---

# SECTION D — Proposed amendments to the theory (29 Sep gate redesign)

*Status of every row: **proposed**. Section C (the theory) is unchanged except for the entity-scope amendment Rob requested on 2026-09-29, which is applied and listed at the end. Section E builds each proposal so it can be tested, and tags it `[gate]`.*

**How to ratify.** For each row, Rob marks it *ratified*, *rejected* or *amended*, with a date. Ratified: edit the cited part of C (of F, for D9 and D15), and change the `[gate]` tag in E to `[ratified]`. Rejected: remove or revert the E text, and note why in `§34`. A row with no kill test (D14) is a judgment call; D9 is settled by the recomputed absence record. A row with a kill test can be left proposed until the test has run.

**Three rows contradict text in C today: D3 (the arming standard), D5 (the exit rule) and D7 (filtering rather than construction). D9 contradicts text in F.** They are marked **conflict**.

| ID | What C says today | Proposed change | Specified in | What measures it |
|---|---|---|---|---|
| **D1** | T3: the library stores mechanisms as verbs; rules declare what they carry | A new rule kind, **obligation templates** (`kind = obligation`, carries `occurrence`): the conjunction of positions that makes a notice unavoidable, forbidding *"no notice of this kind without this conjunction"* | §3, §22.2 | K10 |
| **D2** | — | A candidate library rule: *unrelated stories correlate only where they share a constrained node* (forbids a junction with no node behind it) | §3, §7.5, §20.3 | K12 |
| **D3** **conflict** | T4: *"A false disarm costs a missed trade; a false arm costs money"*, so arming is held to a higher standard than disarming. (An earlier version of the theory spelled this out: arming predicates must be precise and low-noise.) | Precision **scales with possible loss**, because a false arm on a capped position costs a bounded amount. A hard-capped position (bought option, spread, event contract, protection) may be built on a switch-derived ACK with unknown conditions, at a reduced budget. A stress-capped position (stock or pair under a stop) needs every condition documented. An uncapped position is never held | §4, §20.6, §20.7 | K9, K13 |
| **D4** | T4: an ACK is a named source + threshold + date; scheduled ACKs are calendared, and forced ACKs are obligations whose timing isn't public | **ACKs can be derived**: the AND runs over the set of positions, and a documented conjunction that forces an obligation is a forced ACK, ratified by the operator. Unknown conditions make a *switch* with a fetch list. The v15 locator complements derivation | §4, §22.2, §10.4 | K10 |
| **D5** **conflict** | T4: *"Exit is derivable, and it is a date rather than a number measured afterwards: the first attention ACK after the structural ACK. A fact delivered to a channel nobody who marks the security reads changes nothing."* | A basket closes at the first of: **S⊥ recovered** (the span of active stories covers the thesis, or the price reaches the structure without a story), the first attention ACK after the structural ACK, the end of the ACK window, or a stop. S⊥ recovery can come **before delivery** | §4, §20.4, §22.5 | K11, K13 (the paper book records which rule closed each basket) |
| **D6** | T5: run the anchors as eliminators over the whole space. (The v15 harness also runs further eliminators per leg) | **Anchors are the only structural veto**, with the time wall. Five vetoes, per effect: `no_path`, `signs_held`, `absorbed_by_slack`, `no_sink`, `below_band` (on the tide-only hedged residual). The v15 eliminators `traversed`, `weather` and `immaterial_position`, the tradability gate, and the 22 Sep draft's `already_priced` become **construction inputs** | §5, §21 | K9 |
| **D7** **conflict** | T7: *"There is no basket-construction step, only a filtering one"* | Baskets are **built**: one per ratified ACK, weights chosen to maximise the worst payoff over the thesis scenarios, loss capped in the reachable outcomes the thesis excludes, the whole budget committed, capped-loss instruments only. Balancing *across* baskets stays forbidden (one basket per ACK, never netted). Instruments deeper than degree 1 enter only while their response bands stay tight (a construction limit beside T6's attenuation, not a replacement) | §7.1, §7.3, §20.5 | K9, K13 |
| **D8** | T8: five risk terms as a vector, never multiplied; *"Arming as built was an AND over eight predicates"* | The vector stays as a **diagnostic** and the wall map stays a report. Each term gets a construction role: `stake` sets payoff size; `structural` says which side each holder sits on; `pricedness` becomes **ρ**, the share of the thesis no active story explains (higher is better); `operator` shrinks size and never vetoes; `expression` becomes *which capped instrument exists*. The arming statuses (`armed_dated`, `gate_pass_undated`, `gate_fail`) retire; baskets are `built`, `unbuildable` (with a reason), `vetoed`, `declined`, `held`, `closed` | §8, §20.1 | K9 (the unbuildable-reason histogram) |
| **D9** **conflict** | Section F (Event Requirements v3), live rounds: *an absence claim whose carrier has not spoken by `due_at` resolves `hit`* | An absence call resolves `hit` **only if its carrier was read in full through `due_at` and said nothing** (`carrier_state = silent`). Otherwise `unverified`. v15 expires them as hits, so the 15-of-16 absence record is **recomputed and both numbers reported** | §8, §15, §19.1 | The recomputed record |
| **D10** | — (nothing in C) | **A closed world.** Only transitions the library, transform table and procedural chains can produce; anything else is a *piano*, logged as a leak. For each ACK: an outcome vocabulary Ω (always with `other`, outside the world), cut to a reachable set R (unknown keeps an outcome in), narrowed to a thesis set Ωₜ. **Edge = what the market pays for outcomes outside Ωₜ, minus costs** | §7.2, §22.3 | K9, K13 |
| **D11** | T8: *"Permissible risk has a shape"*; T7: a basket carries exposures nobody wrote down, declared and typed as a floor | **Narrative hedging.** Hedge the stories the market is telling; hold the structure. Stories are classed by angle to the thesis (orthogonal, parallel: hedge; adjacent: hold; synthetic: decompose). **S⊥** is the part of the thesis no active story explains, and is what the basket holds. Declared exposures (T7) become computed story loadings, and `basket_stake` (T7) stays as a report. The T3 entry *equity visibility = event size ÷ ambient tide* generalises to any instrument's hedged residual (the equity form stays, because it is true within equities) | §7.4, §7.6, §20.2, §20.4 | K11 |
| **D12** | — | **Junctions.** Unrelated stories that share a constrained node, usually one an ACK lands on, correlate; flagged at lock, treated as *merge* or *hold*, confirmed after the trigger ACK; loadings re-estimated at every ACK | §7.5, §20.3 | K12 |
| **D13** | T7: three levels of scoring; T9: the record | **Scored in money.** A paper book (entries at lock, marks, exits), each basket's result split into `narrowing + timing + residual − costs − leaks`, aggregated per disjoint tide. Only live, clean, non-modelled baskets count toward K13 | §19.2 | K13 |
| **D14** | T11: the standing principles | Twelve principles added (§12): anchors veto and risk builds; a documented position conjunction is an ACK; emergent at generation and frozen at lock; close the world and log the pianos; cover only the reachable set; baskets respond and don't predict; hedge the stories and hold the structure; no shared node, no junction; price enters construction and never generation; every held position has a known maximum loss; one basket per ACK and the budget is per tide; a construction that never builds is reported with its reasons. (One exception to "price never enters generation": the `below_band` veto reads a pre-event band.) | §12 | — |
| **D15** | F, selection procedure: the harness presents *the first passing item* in date order | A **domain-preference tie-break** inside the harness-run procedure: among candidates that pass v3, prefer events whose node carries an obligation template that could fire and a priced distribution listed before the event date (options on a holder, or an event contract on a holder or node). It never removes an item or reorders the human's first pass, and is recorded per round | §15 | The population it creates is reported per round |
| **D16** | T10: seven open questions in a stated order | The open-question list is **reordered and extended**: opposite holders (K8), whether anything builds (K9), whether the stores contain what the forced notices needed (K10), whether S⊥ is real (K11), whether junctions are predictable (K12), whether the book makes money (K13), then T10's walk, credit and pure-play questions. T10's structure-versus-narrative question is now measured by S⊥ and the narrative rows, and its synthetics question becomes part of construction (a synthetic is one more building block) | §11 | — |

## Applied, and not proposed

| ID | Change | Where |
|---|---|---|
| **D0** | **Entity scope** (Rob, 2026-09-29): the premise reads "economic and financial entities", with an explicit definition (companies and their assets, sovereigns and agencies, central banks, funds and indices, commodities by grade and location, currencies, contracts). T6 says "holders", "per asset, not per owner" and "hops between holders". Claim 1 reads "expressible in any traded instrument. Fifteen rounds looked only at equities" | T1, T6 |

## What the proposals do not change

T2 (three layers, and positions as the fourth store), T5's inversion (generate permissively, veto by anchor, base rates only for procedural actors), T6 (effects as the unit, DAG, transform table, attenuation, no re-rooting on inference), the rule that netting across baskets is forbidden, T4's forced-flow argument (information and goods are forced; whether the price changes is measured), the five-term vector never being multiplied, and every principle in T11.

## Build decisions that are not amendments

Items tagged `[v16]` and `[fold]` in E, and `[gate]` items outside §§3–8 and §12 (T_seg clocks, the lock manifest, the price vintage store, the phases), (typed gaps and stake bases, the operator fallback, the model time wall, `library_as_of`, the cold operator, tide-counted support, the decision-model runtime, the Ohmni salvage, the data-product boundary) are build decisions taken earlier and do not restate any claim in C.

---

# SECTION E — System Specification v16 (final)

*2026-09-29. The build reference for v16: conceptual model, system and technical, with the Ohmni salvage, the decision-model fold and the new gate folded in. **v16 is not built**; §30 evolves the v15 harness in place.*

**In this file.** The theory record is Section C; the proposed amendments are Section D; Event Requirements v3 is Section F (applied in full by §15); the data-product isolation spec is Section G (Nomad consumes the data product only through its contract; §26).

**Supersedes, as the build reference:**
- the v16 draft of 2026-09-22 (`nomad_system_spec_v16.md`);
- `nomad-system-as-it-stands-v9.md`;
- `cc_brief_for_v7.md` … `cc_brief_for_v16.md`;
- `nomad_fold_ohmni_jev_v1.md`.

**Authority.** Where this Section and Section C disagree on a claim, C governs; where they disagree on the build, E governs. Every `[gate]` item in §§3–8 and §12 is a **proposed amendment** to C, listed row by row in Section D. `[gate]` items elsewhere (§§9, 14, 15, 19–22, 26, 30–32) are build decisions that carry the proposals into the harness; the exception is the absence-expiry override (§15, §19.1), which contradicts ratified text in Section F (D9). Three change statements C makes today: building on switch-derived ACKs (D3, against T4's arm/disarm asymmetry), exiting on S⊥ before delivery (D5, against T4's exit rule) and building baskets rather than filtering (D7, against T7). Until Rob ratifies them, C's versions govern claims, and E builds the proposals so they can be tested.

**Grounded in what exists.** This Section was written against:
- the v15 harness on Rob's machine (`Documents/nomad`, last modified 2026-09-10): 146 MCP tools, 15 rounds of exports and recaps. **Every existing module, table, tool and config key named here was read from that code**;
- theory v2 (Section C), with the 2026-09-29 amendment that widens the premise to any economic or financial entity (D0);
- the Ohmni repository through report 005 (2026-09-18, branch `claude/model-mechanisms-experiment-u6wq5y`).

**Contents of E.** §0 How to read this document · §1 Premise, claims, bet · §2 Architecture of the idea · §3 Library · §4 Predicates — ACKs · §5 Anchors, not priors · §6 Positions, effects, degrees · §7 The basket · §8 Risk · §9 Time · §10 The fold's mechanisms · §11 What the record shows, and open questions · §12 Standing principles · §13 Components and boundaries · §14 Round lifecycle — the firewall state machine · §15 Intake · §16 Operator procedure per round · §17 Stack and conventions · §18 Data model · §19 Scoring · §20 The risk engine: measure, then build · §21 The veto set, per effect · §22 ACKs: representation, derivation, reach, walk, exit · §23 Decision-model runtime (`decider`) · §24 Laya fine-tuning pipeline · §25 Fold mechanisms — technical · §26 Data-product integration · §27 MCP tool surface · §28 Operator runtime · §29 Reports · §30 Build path: evolve the v15 harness in place · §31 Kill tests (pre-registered) · §32 Build order and acceptance · §33 Appetite register · §34 Not decided · §35 Glossary

### What's new against the 22 September draft

**The gate.** No leg has passed in fifteen rounds because every leg had to clear an AND over risk terms that move against each other: stake against expression, and stake against pricedness. That AND is empty by construction. v16-final replaces it:

1. **Anchors veto, risk builds** (§8, §21). Only structural impossibility and the time wall kill anything. The risk engine's job is to *build* a position with a capped loss, not to veto legs.
2. **Positions trigger ACKs** (§4, §22.2). The AND runs over the set of positions, cross-referenced. When a documented conjunction makes an obligation unavoidable, that's a derived ACK.
3. **Emergent when generated, frozen at lock** (§2, §14). Hypotheses, ACKs, baskets and the walk are computed from authored stores, and every computed object is hashed at lock.
4. **Closed world, narrow set** (§7.2, §22.3). Given an ACK, list what its document can say, cut the list to what's still reachable, and let the thesis narrow it further. "Pianos" (anything outside the grammar) are logged as leaks, never modelled.
5. **Baskets respond, they don't predict** (§7.3, §20.5). Holders on a node sit on opposite sides of it, so the structure supplies the hedge. Weights are chosen to do best in the worst scenario the thesis keeps, with the loss capped in the reachable outcomes it excludes, and the whole loss budget committed so the worst case is a real number.
6. **Hedge the stories, hold the structure** (§7.4–§7.6, §20.2–§20.4). Every story the market is telling is classed by its angle to the thesis: orthogonal, parallel, adjacent or synthetic. Junctions are where unrelated stories start moving together. The basket holds **S⊥**, the part of the thesis no active story explains, and exits when S⊥ is gone.
7. **Book rules** (§7.7, §20.7). One basket per ACK, never netted against another. Only the reachable set is covered. The loss budget is set per tide.
8. **Scored in money** (§19.2). A paper ledger records entry prices, maximum loss and exit rules at lock, and every basket's result is split into narrowing, timing and residual gains, minus costs and leaks.

The Ohmni salvage, the data-product boundary, Laya, the held Jev slot and the fold mechanisms from the draft are carried over.

**Build path: evolve the v15 harness in place** (§30), not a fresh build. The survey found that most of the machinery the new gate needs already exists: the effect DAG, the transform table, the ACK graph and the walk, the pair form of the tradability gate, declared synthetic exposures on attribute nodes, narrative rows, `edge.executability`, and bands. A fresh build would re-implement 146 tools to reach the same starting point.

---

### 0. How to read this document

**Keywords.**
- **MUST** is a requirement of the build.
- **SHOULD** is the default unless there is a stated reason not to.
- **Appetite** marks a threshold Rob sets once, reviews on schedule (at twenty clean rounds unless stated), and never moves because it has not been met.

**Provenance tags on headings and items:**

| Tag | Meaning |
|---|---|
| `[carried]` | From v7–v15 and already built |
| `[v16]` | From the v16 brief (make the terms computable, anchors per effect, round-15 fixes) |
| `[fold]` | From the Ohmni salvage or the decision-model fold (22 September draft) |
| `[gate]` | From the 29 September gate redesign. In §§3–8 and §12 a proposed amendment to Section C (Section D lists them); elsewhere a build decision that carries the proposal into the harness |
| `[ratified]` | A former `[gate]` item that Rob has ratified into Section C (or, for the absence-expiry override, Section F). None yet |
| `[new]` | Introduced in the 22 September draft |

**Existing names.** Tool, module, table and config names marked *(v15)* exist in the harness today. Everything else is new and may be renamed, provided the glossary (§35) changes in the same commit.

**Discipline carried from Ohmni.** Never rewrite this spec to describe what got built. Gaps between spec and build go in `STATE.md` beside it, dated. Rewriting a spec to match the code quietly lowers the bar.

---

## PART I OF E — CONCEPTUAL MODEL (§1–§12)

### 1. Premise, claims, bet

> Economic and financial entities are linked by relationships **inferable** from verified facts. Some are not reflected in relative prices. An agent that reads all of them, at a finer resolution than the market prices, and assembles across kinds of fact that no single participant's book is organised around, sees relationships that are unpriced.

**What counts as an entity** (amended 2026-09-29). Any economic or financial entity: companies and their individual assets, sovereigns and state agencies, central banks, funds and indices, commodities by grade and location, currencies, and contracts (bonds, derivatives, offtakes, event contracts). Entities relate through a node they both hold a position on. The same thing can be a holder in one relation and a node in another: a sovereign holds a position on a strait, and is itself the node its bondholders hold positions on. Companies were the first case studied, never the scope.

**Claim 2 — you can capture it.** The mechanisms in §§2–10.

**Claim 1 — they are unpriced for long enough to matter.** Empirical, and still open.
- **Established:** the lag exists and is large in contract, notice, freight and insurance space: force-majeure letters, allocation notices, contract resets, war-risk premia, incident reports, service-credit claims.
- **Not established:** that it is expressible in any traded instrument. Fifteen rounds looked only at equities, and found one attributed re-encode, at latency zero.

**The bet.** Breadth × cheapness × a differentiated hypothesis space beats depth × capital. The complication: the place the edge is *visible* may not be the place it is *tradeable*. The v16 gate is the answer to that complication. Stake lives in positions, which supply the conditions and the clock; the trade lives wherever a capped-loss instrument can hold the unexplained part of the structure (§7).

**Dead answers to Claim 1:**
- **Coverage.** Cheap reading commoditises it, and AI collapses the cost of reading for everyone. The decision models make reading cheaper for Nomad and for everyone else.
- **Ontology as moat.** A schema is a document, and extraction cost is the fastest-collapsing cost there is.

You don't need to know why a wedge exists to measure whether it does. S⊥ (§7.6) is that measurement.

### 2. Architecture of the idea

> **Library proposes · Predicates condition · Shocks resolve.**

| Layer | What it is | Plain question |
|---|---|---|
| **Library** | Mechanisms: ways things connect. Verbs, not nouns | "How could this event reach anyone?" |
| **Predicates (ACKs)** | Standing, machine-checkable conditions: named source + threshold + date | "Is this idea allowed to fire, and when does it stop?" |
| **Shocks** | Dated events, mechanically selected | "What happened, and did the predicted propagation occur?" |

**Positions** are the fourth store. The library holds the verbs, positions hold the nouns, and a shock is the argument: **Library ∘ Positions ← Shock.** It was always meant to be generative. v16-final lets everything downstream of the event emerge from it:

```
shock ─→ effects (library ∘ positions) ─→ anchors veto the impossible
                    │
                    ├─→ conjunctions over positions ─→ derived ACKs (forced)      §4, §22.2
                    │                                     │
                    │                         outcome set ─→ reachable set ─→ thesis set   §7.2, §22.3
                    │                                                   │
   stories on the tape ─→ loadings ─→ classed by angle; junctions flagged   §7.4–7.5
                    │                                                   │
                    └──────────── scenario grid ─→ constructed basket (maximin, capped loss)   §7.3
                                                          │
                                                   paper ledger at lock ─→ walk ─→ exit when S⊥ is gone
```

**What's authored and what emerges:**

| Authored by people | Emerges by computation |
|---|---|
| Positions: who holds what, per asset | Effects and their DAG |
| The library, including obligation templates (§22.2) | Derived ACKs, fired when a conjunction of positions forces an obligation |
| Outcome vocabularies per notice kind; procedural chains; bounds (lead times, statutory durations, inventory norms) | Reachable sets and timing windows |
| Story proxies and adjacent-story candidates | Loadings, angle classes, junction flags, S⊥ |
| Instruments, cost model, appetite numbers | Scenario grids, basket weights, ledger entries, the walk |

The operator's authorship moves upstream: curating positions, enumerating pieces, naming candidate stories. The machine computes the conjunctions the operator would never think to cross-reference. **Nothing emerges that the stores don't contain.** Emergence moves the enumeration problem into the stores; it doesn't remove it. That's why recall is measured (K10).

**The decision-model runtime (`decider`)** `[fold]` is an instrument, not a layer. It sits wholly in the "proposes" column. It never supports, weights, arms, sizes or scores (§23).

### 3. Library `[carried]` + `[gate]`

- **It stores verbs.** No proper nouns in a rule, ever. One worked example lives in a provenance field, which is exempt.
- **Every rule must forbid something.** A rule that forbids is an **anchor**; a rule that predicts is a **prior** (§5).
- **Rules declare what they carry:** `occurrence | absence | ordering | magnitude | duration | map`. A citation outside a rule's carriage is refused at lock.
  - Meta rows carry `ordering` and `magnitude` as a general rule.
  - After five map calls no rule carried `map`. The harvest owed from rounds 10 and 14 is §32 item C4.
- **Weight propagates forward and never accumulates.**
  - The only source of weight is contact with the world.
  - Every derived object — a hit, a rule the hit supports, a composition, an armed hypothesis — is one more inference from the ground and can only *lose* weight.
  - Validating a validation reduces a discount; it never adds weight on top.
  - The fitting risk is narrowing (validating, arming, promoting) on state that was not propagated.
- **Weight state is shown everywhere a weight is shown:** `weight_state ∈ {untested_as_carried, netted_to_zero, tested}`, with `trials_as_carried` beside it. Untested-at-0.0 must be visibly distinct from tested-and-cancelled-at-0.0.
- **Validation requires a qualifying positive hit:** mechanism right, adequate coverage, clean round. An absence hit under thin coverage cannot validate a rule alone.
- **Support is counted per disjoint tide, not per round** `[fold]`. Two hits under the same ambient condition are one observation with wide coverage, not two. Firings are not replications (Ohmni §17).

**Library entries by group, as of v16:**

| Group | Entries |
|---|---|
| Sequence and state | Novelty belongs to channels, not events · recurring disruption is priced as weather · late in a crisis the neglected side is resolution · the headline names what reopened, not what stayed shut · a repeat filer gets the base-rate procedure, not the form of its last filing |
| Transmission | A cut into a glut is silent · the move is largest where substitution is hardest · the toll booth learns before the cargo · constraint prices de-escalate slowest · a tide sets the price of everything it touches, and events under it are visible only in what the tide does not price · a catalyst that does not concern the node is a tide · a toxic release closes the shared space, not the failed asset · **an availability failure consumes nothing and leaves nothing short; it has no constraint price** `[v16 0.4]`, which carries `[absence]`, sits in layer `transmission`, and forbids citing constraint-price, toll-booth or allocation rules on events that withhold no consumable |
| Ownership and visibility | The wounded owner of the substitutes collects its own scarcity premium · equity visibility = event size ÷ ambient tide · a lag without a listed pure-play is a spectacle, not an edge |
| Operator distortions | My freshness is not the market's · specialists already hold my map · overweights famous names, first-order links and connections that make good sentences · underweights boring intermediaries, logistics, insurance and second-order plumbing · knowing a rule is not applying it · substitutes a remembered generic pattern for a fetchable specific fact (map calls 1 in 5, every miss on a document that existed) |
| Candidate | `lib.account_precedes_the_rebate` (kept as candidate, v16 brief §0.4) |

**What the library is for.** It answers "where does differentiated generation come from if everyone has the same model?" Not from the model and not from a schema. It comes from an accumulated, scored record of which channels transmit, under which state conditions and with which lag, built by playing against reality and not copyable faster than one second per second. The fold extends this: a decision model fine-tuned on that record is the record compiled into a component (§24).
**Additions in v16-final** `[gate]`:
- **A rule has a domain, and the domain is discoverable** (theory v2). The availability-failure rule is the first stated domain limit: the transmission half of the library was built on events that withhold a consumable.
- **`lib.account_precedes_the_rebate`** (theory v2 lists it as an entry): an operator of shared infrastructure under an availability commitment must publish an account of a multi-tenant failure, and the account precedes the money.
- **Obligation templates are a new rule kind** (`kind = obligation`), carrying `occurrence`. Each names the conjunction of positions that makes a notice unavoidable, and what it forbids: *no notice of this kind without this conjunction*. Derived ACKs (§22.2) are computed from them, and are always forced.
- **Candidate rule:** *unrelated stories correlate only where they share a constrained node.* It forbids a junction with no shared node behind it (§7.5). Carries `ordering` (the node fact precedes the correlation). K12 is its first test.
- **"Equity visibility = event size ÷ ambient tide" generalises.** For any instrument, visibility is the event's residual over the noise of its hedged residual (§7.6). The equity form stays as written, because it's true within equities.

### 4. Predicates — ACKs `[carried]` + `[gate]`

**An ACK** is a standing predicate: a named source, a threshold and a date, set in advance so a wrong idea *does not fire* rather than accumulating risk. It has three ordered levels: **support** (which branches exist) → **conditioning** (which are live) → **direction** (which realises).

**Arm/disarm asymmetry, restated for capped loss** `[gate]`. The asymmetry exists because a false arm costs money and a false disarm costs a missed trade. It now scales with what a mistake can cost:
- A **hard-capped** position (a bought option, a debit or credit spread, a bought event contract, bought credit protection: maximum loss fixed by the contract at entry) may be built on a derived ACK that still has unknown conditions (a *switch*), inside the loss budget.
- A **stress-capped** position (a stock or ETF held long or short under a stop, a stock pair, a futures spread: maximum loss estimated at a stress quantile and enforced by the stop) needs every condition of its derived ACK documented true. A gap through the stop is booked as a leak.
- An **uncapped** position (a short with no stop, a naked sold option) is never held. It is converted to a capped form or dropped (§20.6).

Building on a switch relaxes the standard T4's arm/disarm asymmetry sets for arming (a false arm costs money, so arming is held to more than disarming). It is a proposed amendment (D3), bounded by the hard cap and a reduced budget (§20.7).
- Disarming stays noise-tolerant.

**Three timing classes:**
- **`scheduled`** — calendared: results dates, regulatory deadlines, index events.
- **`forced`** — obligations whose timing is not public: an FM letter must come when a producer can't serve contracted offtake; a restart statement must come; a regulator must answer inside a statutory window.
- **`discretionary`** `[fold]` — no obligation and no clock. It is recorded as conditioning, never as an ACK.

A system that advances only on calendared facts advances only where the market is already looking, and inherits pricedness by construction.

**The ACK graph is a DAG** `[carried, theory v2]`. Knowability is its own graph, because a field cannot branch. One fact advances several effects at once, and **a shared ACK is structural correlation on the time axis**, known before any price exists.

**A fired ACK must deliver a fact** `[carried, theory v2]`. "The date passed and nothing was said" is an absence fact: it prunes, it doesn't advance. Without this rule, advancing the walk becomes keeping the round alive.

**Derived ACKs: the AND runs over positions** `[gate]`. The old gate ran an AND over each leg's risk terms. The new one runs it over the set of positions, cross-referenced. For example: the supplier is short, the buyer holds a contracted offtake, no substitute exists inside the window, and inventory is below N days. When every condition in an obligation template is documented true, the notice is an obligation, not a guess, and a forced ACK is derived. If some conditions are unknown and none is false, the result is a **switch**: an ACK candidate whose missing facts become a fetch list. If any condition is false, there is no ACK. The operator ratifies every derived ACK (§22.2).

**Forced flow, relocated.** What is forced is not capital but **information and goods**: the letter must be sent, the filing made, the allocation carried out, the cargo rerouted. The ACK forces a *re-encode*, a moment when the market's projection must take in a fact it did not have. **We claim the information arrives; we measure whether the compression changes.** v16-final adds how we measure it: the hedged residual on the instruments the structure points at (§7.6).

**Exit is derivable, and it is a date** `[carried]` + `[gate]`. A position closes when the residual is recovered. Theory v2 dates this as the first attention ACK after the structural ACK: the fact delivered, and the price-setting class looking. v16-final proposes adding a measurement: the basket closes at the first of (a) S⊥ recovered, by the span test or the price test (§20.4), (b) the first attention ACK after the structural ACK, (c) the end of the ACK window, or (d) a stop (§22.5). Exit (a) can come before delivery, which T4's exit rule doesn't allow; it's a proposed amendment (D5), and the paper book records which rule closed each basket so the two can be compared.

**The walk** `[carried, round 15]`. A forced ACK that fires can deliver a cause that didn't exist at lock. Its successors are named at firing, and a new segment locks. When an ACK fires, the positions update, new conjunctions can become true, and the next derived ACKs follow. Stake created by a firing ACK cannot have been pre-priced, because the fact did not exist to price. This is the only known escape from the stake↔pricedness bind.

### 5. Anchors, not priors `[carried]` + attention `[fold]` + `[gate]`

**Cascades do not repeat.** Propagation is contingent on slack, positions, traversal state and the running tide, so priors over outcomes are close to worthless.

**Anchors are the only structural veto** `[gate]`. With the time wall, they are the only things that kill a hypothesis (§8). Everything that survives them is handed to construction (§7), where risk decides *how* to hold it, never *whether* it exists.

**Anchors say what cannot happen:**
- no admissible path, so nothing transmits (`no_path`);
- the receiving market absorbs it, so nothing shows (`absorbed_by_slack`);
- nowhere for it to land, so nothing transmits (`no_sink`);
- both signs held, so no net direction (`signs_held`);
- below the band, so nothing observable (`below_band`). From v16-final the band is the noise band of the instrument's **hedged residual**, not its raw price band (§21).

**`absorbed_by_slack` and `no_sink` point opposite ways and both are in the record.** The library rule *a cut into a glut is silent* says slack in the receiving market kills the effect; theory v1's anchor list (*no slack, nothing to transmit into*; T5 in v2 abbreviates it) says the absence of slack does. They are separate anchors here rather than one anchor with a contested sign, and **which applies to which effect kind is an open call (§34)** — until it is settled, an effect is vetoed only by the one whose condition the operator can state for that effect kind, and the other reads `unevaluable`.

**The procedure:** generate the hypothesis space permissively, run the anchors as vetoes over the whole space, and see what is left standing. What's left standing is built into baskets, not filtered again (§7.1). The anchors also do the cutting from the outcome set to the reachable set (§7.2). Analogies and remembered patterns may *propose* into the space and may never support. A wrong analogy costs an eliminated leg, not a scored miss.

**A prior is a placeholder for a fact you have not fetched.** Where the document exists, fetch it. Base rates are permitted only for **procedural actors** (bureaucracies repeat) and are forbidden for cascades.

**Attention is the scarce resource; priors may order attention and never weight** `[fold]`. A model's score for a link or chain may decide *which* chain gets examined first and *which* document gets fetched first. It may never decide what is true, what survives, or how much anything weighs. It dissolves when the fetch lands. Chains ranked out of attention are `unexamined`, never `vetoed`.

### 6. Positions, effects, degrees `[carried]` + `[gate]`

**Position, not sharing.** Two holders relate through a node when both hold a *position* on it: allocation tier, contractual priority, substitutability, share, duration. Sign and magnitude are properties of the **difference in positions**. Positions are **per asset, not per owner** (a plant, a field, a vessel, a bond issue, a contract), so an owner holding several positions on one node is partially self-hedged. Holders can be any economic or financial entity (§1).

**Positions do three jobs in v16-final** `[gate]`:
1. **They carry the effects,** as before.
2. **Their conjunctions trigger ACKs.** A documented set of positions can make a notice unavoidable (§4, §22.2).
3. **They supply the hedge.** Holders on one node sit on opposite sides of it, so the structure offers building blocks that respond in opposite directions to the same event (§7.3). Whether listed opposite holders exist on real nodes is the first thing to check (K8).

**Relation modes, and what each may do:**

| Mode | Speed | May propose | May support |
|---|---|---|---|
| Physical / contractual | Slow, lossy per hop | Yes | Yes |
| Accounting / identity | Instant, symmetric | Yes | Yes |
| Attentional / classificatory | Fast, reflexive | Yes | No |
| Positional / analogical | Does not transmit | Yes | No |

Price may confirm a relation and may never propose one. Decision-model output is analogical in this sense: it may propose, never support `[fold]`.

**Effects are the unit, not legs.** A holder does not have *a* sign. A concentrate buyer facing an outage has higher input cost **and** a volume shortfall **and** a delivery obligation **and**, if diversified, better pricing on competing output. Sign is derived late, over the holding window.

**Effects are degrees.**
- The chain *is* effects, and holders are where each effect lands. The structure is a **DAG over effects**.
- Degree is depth in that DAG. `d1 → d3` need not route through the same `d2` as `d1 → d2`.
- **Attenuation is the depth limit.** Support decays per effect hop.
- **Re-rooting resets attenuation only where the effect is independently carried by its own document.** Re-rooting on inference is inference laundering.

**Composition through a relation is a mapping, not a sign flip.** The **transform table** maps `(parent effect kind, relation) → child effect kinds with a transmission value`, and most entries are "does not transmit". Round 15: `volume → obligation` transmits at 0.0 under `offtake` and at 0.6 under `input_supply`.

**Graph structure** `[carried, v15]`.
- `node_kind ∈ {event, attribute}`. Venue, currency, index and sector are positions on attribute nodes.
- Edges carry `transmits: bool`. Traversal walks only transmitting edges; basket construction sums over both kinds.
- "Orthogonal" is known only for modelled factors. The correlations that hurt live in edges we never drew.
- **A bridge is not an object** (theory v2). An effect path is a position when some node on it can be held and some ancestor has stake. The v15 tool `nomad_bridge_paths` *(v15)* finds these, and in v16-final they are candidate building blocks for construction, not legs to be gated.

### 7. The basket `[carried]` + `[gate]`

#### 7.1 Built, not filtered

**The event is the thesis, the ACK is the clock, the positions are the footprint** `[carried]`. What changes is the last step. Until v15 the basket was whatever survived a per-leg filter, and nothing survived. From v16 the basket is **built**: for each ACK, the risk engine chooses capped-loss positions on the instruments the structure touches, weighted so the basket does best in the worst scenario the thesis keeps, with its loss capped in the reachable outcomes the thesis excludes (§7.3).

**What stays from v15:**
- **Three levels, three questions.** *Effect*: was the claim right (epistemic; feeds the library). *Basket*: did the construction work (outcome; money). *Set*: which effects are implied across interpretations. Consistency across the three is the diagnostic.
- **Balancing within a basket is construction; balancing across baskets is forbidden.** Across, baskets are different interpretations; netting them nets away divergence and leaves nothing held.
- **A basket carries exposures nobody wrote down.** They're declared at construction and typed as a floor. v16-final makes most of them computed rather than declared: they are the story loadings (§7.4).
- **Cross-membership is convergent implication**, and the most cross-supported effect may be robust because it's inert.
- **A bridge is not an object** (theory v2). An effect path is a position when some node on it can be held and some ancestor has stake.

**Why "built" fixes the wall.** The wall existed because stake and tradeability had to sit in the same leg. In a built basket, they don't:
- **Stake lives in the positions.** The private smelter, the mine and the offtake contract don't have to be tradeable. They supply the conditions and the clock.
- **The trade lives wherever a capped instrument responds to the structure.** Opposite holders on the node, a listed parent, a bond, an option, an event contract.

#### 7.2 A closed world and a narrow set

Given an ACK, the set of things that can happen is small. The rules:

- **Close the world.** Only transitions the library, the transform table and the procedural chains can produce are allowed. Anything else is a **piano**: logged as a leak and measured, never modelled. Capped-loss instruments are what make closure survivable: if a piano falls, the loss is the premium.
- **List what the ACK's document can say.** Each notice kind has a small, typed outcome vocabulary, **Ω**. A restart statement: under 2 weeks, 2–6 weeks, over 6 weeks, force majeure declared. A regulator's decision: approve, reject, extend, nothing by the deadline. Every vocabulary also names `other`, which sits outside the closed world: it is never in the reachable set, the basket never covers it, and if it happens it is booked as a piano.
- **Cut to what's reachable.** An outcome stays in **R** if every condition it needs is true, still reachable before the deadline, or **unknown**. Unknown keeps an outcome in; it never eliminates it. Structural anchors, bounds (parts and rebuild lead times, statutory minimum durations), inventory positions and ratified procedural states do the cutting. A price never cuts an outcome.
- **Apply the thesis.** The thesis is our cross-referenced claim over positions, and it narrows R to **Ωₜ**. A thesis resting on unknowns doesn't narrow anything; it becomes a switch to go and fetch.
- **Pick the shape from the thesis set** (instrument forms in §20.6). The shape is computed from the structure's response S(ω) in each thesis outcome (§20.4), before anything about stories or prices except the quoted implied move:

| Across Ωₜ, the structure's response is… | Test | Shape |
|---|---|---|
| The same direction wherever it moves | Every non-flat outcome points the same way along S̄, and at least one is non-flat | Directional, capped: a debit spread, a bought option, a stock or pair, an event contract |
| Large, in either direction | Non-flat outcomes point both ways, and none is flat | Long volatility: a bought straddle or strangle, event contracts on several outcomes |
| Flat, while the market prices a move | Every outcome is flat, and the quoted implied move exceeds the noise band by `PREMIUM_MIN` | Sell premium, inside a spread (credit spread, condor) |
| Mixed | Anything else: both directions with some flat outcomes, or all flat with no quote showing a priced move | No trade on this ACK. Wait for the next one to narrow the set |

- **Match the timing.** Every dated instrument must outlive the ACK window: expiry after the ACK's due date, or, for a forced ACK with no public date, after the window its ratified procedural chain gives at the appetite quantile. A forced ACK with `unknown_forced` timing gets a window capped at `DUE_AT_MAX_DAYS`. Dated instruments must outlive the cap, or the basket is held in undated form (stock, ETF), or not built.
- **Walk.** When the ACK fires, the delivered outcome replaces the set. Positions update, the next derived ACKs are computed, and the next basket is built on the successor (§22.4).

The edge, stated once:

```
edge = what the market pays for outcomes outside Ωₜ − costs
```

We never claim to know which outcome inside the set happens. We claim to know what's outside it, and we're paid for whatever the market wrongly puts there. The sharpest case: if a price sits outside the range of payoffs the reachable set allows, the trade is right in every outcome we can reach.

The narrowing edge is only computable where the market quotes a distribution over outcomes: an option surface or an event contract. On a plain stock there's no quoted distribution to compare against, and the basket relies on the timing and residual edges (§19.2).

#### 7.3 Baskets respond, they don't predict

We don't predict the direction of anything. We build a basket that comes out ahead whichever way things go inside the thesis set, and loses only a capped amount in the rest of the reachable set.

**Positions are what make this possible.** A trader with one stock can predict the direction or pay for options on both sides. A basket built from positions has a third choice: the hedge comes from the structure. Holders on a shared node sit on opposite sides of it (the supplier's gain is the buyer's cost; the hedged airline is the unhedged one's mirror), so the building blocks already respond in opposite directions to the same event.

**The construction** (technical form in §20.5):

```
scenarios  = every outcome in the thesis set Ωₜ × tide down / flat / up
payoff(s)  = Σ weight_i × response_i(s) − costs      (each response is a band, not a point;
                                                      the worse end is used)

choose weights to maximise  the minimum payoff over the thesis scenarios
subject to   the stories the market is telling are hedged out (§7.4)
             adjacent readings may only help (their loading is held ≥ 0)
             in every reachable outcome the thesis excludes, the loss is at most a set fraction of the budget
             the whole loss budget is committed, so the worst case is a real number, not zero
             position sizes ≤ liquidity caps
```

- **Worst case above the edge margin:** the basket wins in every outcome the thesis keeps, and loses a bounded amount in the reachable outcomes it excludes. Build it.
- **Worst case slightly below, every instrument hard-capped, and positive in enough scenarios:** build it under the capped-loss gate (the thresholds are appetite).
- **Otherwise:** don't build. Record why (no opposite holder, bands too wide, costs, too few instruments for the stories that need hedging) and wait for the next ACK to narrow the set.

**Readings don't need their own dimension.** The stories the market is telling are hedged to zero, so their moves don't reach the payoff, and adjacent readings are constrained to help, never hurt. That's what "market reading doesn't matter" means in the arithmetic: the basket is built to survive every reading, not to ignore them. The payoff if an adjacent reading is adopted is reported as upside, never counted toward the worst case.

#### 7.4 Hedge the stories, hold the structure

Every event has stories the market trades: "copper up", "airlines down", "risk off". A story moves a set of vehicles: a sector, a commodity, famous names. Treat each story as a direction across instruments (its **loading**) and the thesis as a direction too, set by the positions. How each story sits relative to the thesis decides what to do with it:

| Relation | What it is | Hormuz example (thesis: long the fuel-hedged airline, short the unhedged one) | What to do |
|---|---|---|---|
| **Orthogonal** | A story unrelated to the event that moves the same names | Rate cuts, the AI trade, index flows | **Hedge it out completely.** It's tide |
| **Parallel** | A story already saying part of what the structure says, through the obvious channel | "Oil up, airlines down" | **Hedge it out.** Whatever it explains is already priced |
| **Adjacent** | A neighbouring reading, one step from the thesis | "Fuel hedges are what matter this time" | **Keep the exposure,** pointed toward the thesis. It's the route by which the market reaches the structure |
| **Synthetic** | A composite theme built from other stories | "Middle East risk premium", loading on oil, defence, shipping and airlines together | **Break it into its parts** and apply the rules above. Where the market has built a story that doesn't hold, it can also be traded as a synthetic thesis |

Two things set the class: the story's angle to the thesis, and whether the market is already telling it. A story the market is telling is hedged either way: orthogonal if it sits near right angles to the thesis (tide), parallel otherwise (priced). A story the market isn't telling yet, pointing toward the thesis, is adjacent. A story that lies in the span of other stories is synthetic. The cut-off angle is appetite (§20.2).

#### 7.5 Junctions

A **junction** is where two stories that were running independently start moving together.

- **Why it happens.** A story is a path through the graph (oil → jet fuel → airline margins). Two unrelated stories correlate when their paths meet at a shared node, usually because a fact lands there. Qatari LNG going offline puts "Middle East gas" and "AI data-centre power demand" through the same node, electricity prices.
- **What it does to a basket.** It breaks hedges: an orthogonal story hedged out as independent suddenly carries the event. It can also recover S⊥ through a route nobody was watching.
- **What it is.** Two stories linked through public facts that nobody's book connects: the premise again, one level up.

**Rules:**
- **Junctions are predictable from structure.** Flag a pair of stories when both paths pass through the same node of the event's effect DAG, and that node is constrained inside the ACK window: a forced ACK or a derived ACK's outcome lands there, or a no-slack fact is stated for it (§20.3).
- **No shared node, no junction.** A correlation with no node behind it is a piano: noise, logged.
- **Derived ACKs often trigger them.** Positions trigger ACKs, and ACKs trigger junctions.
- **Each flagged junction gets one treatment, recorded at lock:** hedge the two stories as one combined story, or, if S⊥ points at the junction itself, hold it as its own leg.
- **Loadings are re-estimated at every ACK firing.** Loadings measured before a junction are wrong after it.

#### 7.6 S⊥, and the exit

**S⊥ is the part of the thesis no active story explains:** the thesis direction minus its projection onto the stories currently running. It is "unpriced" written as a number, measured at lock. It's the grid's "nobody has worked it out" corner in arithmetic.

- If the thesis sits inside the span of the stories already running, it's priced. Don't build.
- If a large part of it points where no story goes, that's the unpriced relationship, and the basket is built to hold exactly that part.

**The exit becomes a rule.** As adjacent stories take hold, or a junction merges stories, the span of active stories grows until it covers the thesis and S⊥ shrinks toward zero. When S⊥ falls below its exit threshold, or the price reaches the structure before any story does, the residual has been recovered: close the basket (§4, §20.4, §22.5).

**Narrative hedging, not position hedging.** The basket hedges the market's stories, never the structural view. A narrative-hedged basket makes money only if a relationship was unpriced and then got priced when the fact arrived, so **its P&L is Claim 1 turned into money.** If the market read it right all along, the hedge cancels the gain and the basket makes nothing. Structural sign still matters: it tells us which side each holder sits on, and it keeps feeding the library.

#### 7.7 Book rules

- **One basket per ACK**, robust within its own reachable set, **never netted against another basket.** Baskets on the same event hold different views of what's excluded; sizing them to cancel would net away divergence.
- **Cover only the reachable set.** Buying protection against outcomes the anchors ruled out pays for the thing we're supposed to be paid for. Eliminated outcomes are left uncovered, or sold with capped risk.
- **Capped loss everywhere.** Every held position has a maximum loss known at entry.
- **Budget per tide, not per basket.** Ten baskets on one conflict are one bet and share one loss cap.
- **Degrees go deeper only while the response bands stay tight.** Further out, attenuation widens the bands, the worst case becomes noise, and covering it adds cost.
- **What pays, and nothing else:** the market paying for outcomes we've eliminated (narrowing); forced notices that option prices don't contain (timing); S⊥ being priced when the fact lands (residual); cheap hedges from opposite holders; junctions seen before the market links the stories. If none of these exists, a fully hedged book slowly bleeds costs, and the four-part split (§19.2) shows it.

#### 7.8 Carried detail `[carried]`

- **Independence.** Weight counts surviving independent derivations. Independence is judged by shared ancestry in the effect DAG, walking transmitting edges only: the independence discount runs from 1.0 for paths that split at the root to 0.15 for paths that split at the last node (appetite). Support and stake are always reported together, and the inert-stake ceiling is appetite.
- **Synthetic legs.** Basket subsets giving equal but differently shaped factor exposure, built only from shared-factor edges, from pre-registered construction rules (`syn.tradability_opposing`, `syn.time_toll_cargo`, `syn.cross_node_event_pair` *(v15)*). Weight = min(component weights) × 0.85 per extra component. **Built before lock only.** In v16-final a synthetic is one more candidate building block for construction.
- **`basket_stake`** *(v15)* = intended residual ÷ declared synthetic exposure. It was never enforced in v15; construction supersedes it, and it stays as a report.
- **Narrative rows.** One per leg where a bounded channel can be named.
  - `narrative_sign` is scored on whether the channel *said* it, not on whether it was right.
  - `divergence` is computed from the sign **at lock**. Revisions are shown separately as `revised_sign`.
  - The narrative row is scored first (the channel speaks early) and is never re-scored after structural resolution.
  - `divergence_held` reads `unreadable` where no implied reading exists, and fails only on branches that could be read `[v16 C6]`.

### 8. Risk `[carried]` + `[v16]` + `[gate]`

**Anchors veto, risk builds** `[gate]`. Only two things kill anything:
1. **An anchor** says it structurally can't happen or can't be seen (§21);
2. **the time wall** (§9).

Every other risk term stops being a veto and becomes an input to construction.

**The five terms stay, as a vector, never multiplied** `[carried]`. A product hides walls: five terms at 0.6, and one at 0.03 with four at 0.95, give the same number and describe opposite situations. The vector stays the diagnostic, and the wall map stays a report. What changes is each term's job:

| Term | v15 job | v16-final job |
|---|---|---|
| `stake` | Measured, vetoes nothing (the vector never gated); fed the "surviving but small" label | **Payoff size** in the scenario grid; sets the response band's centre |
| `structural` | Measured | **Which side each holder sits on**, and support for the thesis set |
| `pricedness` | Measured; some of its inputs (`traversed`, `weather`) also ran as eliminators | **ρ, the share of the thesis no active story explains** (§7.6, §20.4). Higher is better, as for every v15 term |
| `operator` | Measured | **Shrinks size** for the call shapes the operator gets wrong |
| `expression` | The one demonstrated wall; the tradability gate enforced it | **Which capped instrument exists** for each holder (§20.6). No instrument means no building block, not a dead leg |

**Unevaluable is a value, not a verdict** `[carried]`. Every missing value carries exactly one typed reason, and each reason has a different fix:

| Reason | Meaning | Fix |
|---|---|---|
| `not_representable` | No honest computation exists, e.g. price-band stake on an unlisted holder | Change the model (the stake basis, below) |
| `not_disclosed` | The input exists but wasn't published | Read the document; fetch |
| `not_covered` | Outside our reach: no carrier, no fetch path, no instrument | The data product: add a source |
| `not_applicable` | The term doesn't apply, e.g. stake on an authority holder | Nothing to fix; report it |

In construction, an unknown term widens the response band (and so worsens the worst case) or shrinks the size. It never passes and never fails silently. **Carrier silence is typed too:** only `silent` (a carrier read in full said nothing by `due_at`) resolves an absence claim as a hit; `unread` and `not_covered` never do. Could-not-compare is never collapsed into compared-and-differed.

**Stake basis per holder class** `[v16 A1]`:

| Holder class | Denominator | `stake_basis` |
|---|---|---|
| Listed instrument | The pre-event band of its **hedged residual**, resolved at lock as a rule over its own history | `price_band` |
| Unlisted operating asset | The asset's own operating scale (output, capacity, revenue, throughput) over the same window | `operating_scale` |
| Aggregate / class holder | The class's stated scale where one exists, else a typed gap | `class_scale` |
| Authority / non-commercial | — (`not_applicable`) | — |

Stake values are never compared across bases without the basis shown.

**Operator fallback** `[v16 A2]`. Fall back up the hierarchy `(call_type, modifiers)` → `(call_type)` → `(all clean calls)`, taking the first level with at least `OPERATOR_MIN_N` resolutions (appetite). Record `operator_basis` and `n`. The fallback is computed per operator model, never pooled across models.

**Binding term** `[carried, v15 fix]`. The term furthest below its appetite ratio, chosen over all five terms. It is `unassessable` whenever an unknown term could bind below the lowest computable one. It's a diagnostic now, not a gate.

**Permissible risk has a shape** `[carried]` + `[gate]`. We're paid for being wrong about structure. We're not paid for tide, for timing beyond the ACK, or for liquidity on thin names. The constructed basket enforces this: tide and story loadings are hedged, timing is bounded by the ACK window, and sizes are capped by liquidity.

**What arming used to be.** v15 armed a leg only if every arming predicate held and the tradability gate held: zero armed legs in fifteen rounds. The statuses `armed_dated`, `gate_pass_undated` and `gate_fail` *(v15)* are replaced by basket states: `built`, `unbuildable` (with a typed reason) and `vetoed` (by an anchor). A filter never violated is a filter never tested; a construction that never builds is reported with its reasons, so it can be tested.

**The same wall, found twice.** Ohmni report 005 (2026-09-18) found that every directional mechanism reaching its gate had zero aligned corroboration: Ohmni promotes only no-move claims. Nomad got there from the other direction: 15 of 16 absence calls right, no expressible edge. Two systems built separately can rule things out and can't support a direction from invariance alone. v16 stops asking for direction to be supported. It asks for structure to be held and stories to be hedged.

### 9. Time `[carried]` + `[fold]` + `[gate]`

Nomad's integrity rests on one idea, applied to every input: **nothing may be used at time T that could not have been known at T.**

| Input | Rule |
|---|---|
| Documents | **The time wall** `[carried]`. Anything knowable at or before `event_date` is pre-lock legal. **Two names, one meaning:** the data-product contract calls this `knowable_at`, and the v15 harness calls it `knowable_from` *(v15)* on positions, evidence and scheduled facts. Because v16 evolves the harness in place (§30), the harness keeps `knowable_from`, and the data-product adapter maps `knowable_at → knowable_from` on the way in. Nothing is renamed and no row is dropped. It is a time wall, not a retrieval wall: it scores the system, not the operator's recall |
| Timestamps | **`knowable_from` separate from `event_time`, to the minute where the source allows** `[fold]`. Gating uses `knowable_from`. Latency is measured in the finest unit available, and the side of the market close is recorded |
| The library | **`library_as_of(D)`** `[new]`. When playing a round with `event_date = D`, the operator sees library rules and weights computed **only from resolutions whose `knowable_from ≤ D`**. For live rounds this is the current library. For backfilled rounds walked forward through a window, it stops round N's post-lock outcomes from leaking into round N+1 through rule weights |
| Models | **The model time wall** `[fold]`. A model may answer a question about time T only if `trained_through ≤ T`, where `trained_through` covers everything the model learned from, base pretraining included. Unknown means the model's public release date |
| The operator | The operator is a model, so the model time wall applies to it: **Q2 is the model time wall** `[new]`. `operator_cutoff` is per operator model, recorded per round. Changing the operator's model changes the cutoff and re-classifies rounds; that is never done silently |
| Prices `[gate]` | **A segment's computations read only prices dated before its clock** (T_seg, §14: `event_date` for segment 0). Loadings, volatilities, bands and S⊥ use sessions strictly before T_seg. **Execution prices** (a stock's price, an option's premium, a contract's price) are what the basket would actually pay: on a live round, the last quote before lock; on a backfilled round, the entry-rule price (§19.2). The market's reaction between the event and our entry is in that price, never booked as our slippage. Fills, marks and exits use prices after lock. Every price read comes from the **price vintage store**: a frozen, hashed copy with its retrieval time. A later refetch that disagrees (adjustments, splits, metadata drift, all seen in Ohmni) is recorded as drift, never silently substituted (§26) |
| Sessions | **The cold operator** `[new]`. Each round runs in a fresh operator session with no persistent agent memory, no self-written skills carried from other rounds, and no chat memory or past-chat search. The only things that cross rounds are the ledger, `library_as_of(D)` and the documents (this file) |

### 10. The fold's mechanisms `[fold]`

These five mechanisms sit entirely in the "proposes" column. Each is on probation until its kill test passes (§31).

**10.1 The operator enumerates, the decision model wires.**
- The operator is expensive per judgment and good at proposing. A decision model is nearly free per judgment and cannot propose; it can only choose among options it is given.
- Pieces (effects at holders) grow linearly; links grow with the square.
- So the operator enumerates the pieces and the decision model asks about every link, which removes by construction the operator's bias in *which* links it bothers to draw.
- The output is an ordering of chains for attention and fetching. It is never weight (§5).

**10.2 Obviousness as a pricedness meter (candidate).**
- A commoditised reader's confidence in a link approximates what every cheap reader sees, and so what is most likely priced.
- A model in the `crowd_mirror` role is read as *obviousness*, not truth.
- The target region is links with low obviousness that survive anchors against documents.
- It also supplies the narrative side of divergent legs, which serves open question 6.
- **The `crowd_mirror` slot is empty in v16** (Jev held; §23.6).

**10.3 Spread probes.**
- A wide answer spread mixes "transmits weakly" with "can't tell". So the same link question is asked without and with the settling document, and the change in the *shape* of the answer is read (§25.2).
- A distribution that stays split between "none" and "full" after the document is a **switch**: transmission depends on a fact not yet known.

**10.4 The ACK locator.**
- Switch links → the settling document type → whether publication is obliged → a source from the carrier registry → timing from the calendar (`scheduled`) or from procedural chains (`forced`) → operator ratification.
- It locates **where** predicates belong. It never arms, and it never builds.
- **It complements derived ACKs** `[gate]`. Derivation (§22.2) finds ACKs that documented positions force, by checking obligation templates. The locator finds ACKs the templates don't cover yet, from the model's reading of links. A locator candidate that the operator ratifies more than once for the same kind of conjunction is a candidate obligation template for the library.

**10.5 Procedural-actor chains.**
- Regulators, courts, trade-remedy cases and FM processes are genuine state machines. Their transition odds and timing are counted from public dockets **in code**; the decision model only classifies which state a new document puts the process in.
- This is the one place base rates are legitimate (§5), and it strengthens the one call type Nomad already wins: institutional occurrence.

### 11. What the record shows, and open questions

**Record, rounds 1–15:**
- Rounds 1–4 are `learning`; 5–10 clean; 11 learning; 12 voided, then re-run as learning; 13 clean; 14 and 15 learning, partially scored. **Seven clean rounds** (5–10, 13). Every look-back below reports clean and learning rounds separately.
- Descriptive edge: 14 of 15 rounds over a naive reader, surviving a second scorer (theory v2; the 22 September draft said 13 of 14).
- Elimination edge: demonstrated.
- Expressible edge: no evidence.
- Absence calls 15/16, occurrence 8/14, map 1/5, magnitude systematically timid.
- Zero armed legs. One attributed re-encode, at latency zero.
- **The corrected wall map:** `structural` binds on 0 legs, `expression` on about 44%, and about 54% are `unassessable`. `stake` is blank on 96% and `operator` on 90%. Nine legs in the programme's history have had all five terms computed. "Selection is the only lever" is retired; computability comes first.
- **Round 15:** the walk's first step, and the availability-failure domain bound.

**Ohmni, report 005 (2026-09-18)** `[gate]`. Every directional mechanism that reached Ohmni's gate had zero aligned corroboration, and every promotion was a no-move claim. Two systems built separately reach the same place: they can rule things out and can't support a direction from invariance alone. The report also found two data defects that v16 inherits as rules: freeze hashes must be taken over decompressed payloads, and Yahoo price metadata drifts between fetches (§26).

**Why no leg passed** `[gate]`. Arming required an AND over risk terms, and two pairs of those terms move against each other: stake against expression (the stake sits with unlisted holders), and stake against pricedness (the big, visible effects are the priced ones). An AND over anti-correlated terms is empty by construction. Six earlier attempts at a fix all kept that AND: the eight-predicate arming check, `gate_pass_undated`, synthetic legs, the "negative space" mirror of the risk layer, basket totality, and computability. v16-final removes it (§7, §8).

**Open questions, in the order they decide things:**
1. **Are there opposite holders?** On the nodes of rounds 1–15, how often does a node carry listed holders on both sides (K8)? If almost never, structural hedges don't exist and construction falls back to options and event contracts.
2. **Does anything build?** Rebuilt under v16-final, do rounds 5–15 produce any `built` basket, and what's the distribution of worst cases and `unbuildable` reasons (K9)?
3. **Do the stores contain what the forced notices needed?** For each forced notice that actually arrived in rounds 8–15, were the positions that would have derived it in the stores at lock, under templates authored from rounds 1–7 only (K10)? Emergence can't produce what the stores lack.
4. **Is S⊥ real?** At lock, was S⊥ larger on relationships that were later priced than on those that weren't (K11)?
5. **Are junctions predictable?** Did story pairs flagged by a shared node show a larger jump in correlation than unflagged pairs (K12)?
6. **Does the book make money?** Across enough disjoint tides, does the paper book beat costs plus leaks (K13)?
7. **Carried from v16:** does a walk reach stake that didn't exist at lock? Do credit instruments concentrate what equity dilutes (stake 19.02 on the bond against 7.12 on the equity, same event)? Is there a listed pure-play universe at all (K7)?

Question 6 in the 22 September draft (structure against narrative on divergent legs) is now measured directly by S⊥ and the narrative rows. Question 7 (synthetics) becomes part of construction: a synthetic is one more candidate building block.

**The three shapes the programme could take, and where v16-final points:**
- **A:** a thin equity universe of listed pure-plays.
- **B:** different instruments: credit, options around ACK dates, event contracts.
- **C:** an information product, selling the map to procurement and supply-chain desks.

v16-final is **B, with equities as building blocks**. Headline and geopolitical events fit best, because they come with forced notices, priced options and event contracts. A and C stay open, and K7, K8 and K13 decide between them.

### 12. Standing principles

**Carried:**
- Library proposes, predicates condition, shocks resolve.
- Permissive generation, strict validation.
- Proposal rights, support rights and arming rights differ by mode, source class and instrument noise.
- Price is an outcome, never a proposer: banned on the trigger side, required on the scoring side.
- Every rule forbids something; no proper nouns in rules.
- A rule that forbids is an anchor; a rule that predicts is a prior.
- A prior is a placeholder for a fact you have not fetched.
- Weight propagates forward and never accumulates; narrowing on unpropagated state is the fitting risk.
- Unevaluable is a value, not a verdict.
- No load-bearing computation swallows a failure silently.
- A null call is scored, weighted low, and never counted as edge.
- Read at the finest resolution available; act at the coarsest the evidence identifies.
- Hierarchy is ledger; exposure is flat.
- Granularity is declared before the hypothesis forms, and locked.
- Literature is for targeted claim verification at the moment of commitment. Never a design gate.
- One falsifiable sentence, then the cheapest thing that could kill it.
- An idea gets scrapped for a stated cost, never for its label.
- Load-bearing vocabulary lives in a document, not in session memory.
- Amendments to validity are learning; amendments to thresholds are fitting.
- Thresholds are appetite.
- Spend follows a measured block, never an anticipated one.
- Pre-lock retrieval is a time wall, not a retrieval wall.
- Every data source gets a discriminating probe before it is trusted; never trust a filter's promise, verify the payload against its own metadata.
- Novelty is post-hoc.

**Added by the fold:**
- Could-not-compare is never collapsed into compared-and-differed.
- A declared form carries rules, not numbers: parameters resolve against the window they are applied in.
- Firings are not replications; support counts per disjoint tide.
- Attention is scarce; priors may order attention and never weight.
- Models obey the time wall; unknown training cutoff means release date.
- The operator runs cold; only the ledger, the library as of the event date, and the documents cross rounds.
- Never rewrite the spec to match the code; gaps live in `STATE.md`.
- No number that governs a verdict gets a default.

**Added by the gate** `[gate]` (proposed theory amendments until ratified):
- Anchors veto; risk builds. Only structural impossibility and the time wall kill anything.
- A documented conjunction of positions that forces an obligation is an ACK.
- Emergent at generation, frozen and hashed at lock.
- Close the world, and log the pianos. Unknown keeps an outcome in.
- Cover only the reachable set.
- Baskets respond; they don't predict.
- Hedge the stories, hold the structure.
- No shared node, no junction.
- Price enters construction, never generation. Loadings, bands and costs are read from prices; effects, derived ACKs, reachable sets and theses never are. The one exception is the `below_band` veto, which reads a pre-event band to decide whether anything could be seen at all (§21).
- Every held position has a maximum loss known at entry.
- One basket per ACK, never netted against another; the loss budget is per tide.
- A construction that never builds is reported with its reasons, so it can be tested.

---

## PART II OF E — SYSTEM (§13–§16)

### 13. Components and boundaries

```
                    ┌──────────────────────────── contract (pinned >=0.2,<0.3) ─────────────────────────────┐
  dataprod ─────────┤  Records (knowable_at, typed status, lineage, revisions) · search · attachments       ├──→ adapter (knowable_at → knowable_from)
  (separate repo;   └───────────────────────────────────────────────────────────────────────────────────────┘        │
   Section G)                                                                                                         ▼
  decider (shared runtime) ── DecisionModel protocol ── LayaAdapter (shadow; per-job gates) · [crowd_mirror slot: empty]
        ▲
        │ recorded calls (input_hash, question_set_hash, checkpoint)
        │
  NOMAD HARNESS — the v15 harness, evolved in place (Python, FastMCP, SQLite WAL, hash-chained ledger)
    kept from v15 (module names as in the code)
      rounds ─ firewall state machine, lock, PIT fetch, reveal, live windows, due_at
      positions · effects · synthetic · exposure ─ names book, effect DAG, transform table, declared exposures
      acks · walk · scheduled ─ ACK graph, firings, segments, calendar, catalyst check
      surviving · vector · predicates ─ anchors (becomes the veto set, §21), five-term vector (diagnostic)
      edge · prices · basket ─ executability, bands, the event-basket view
      scoring, library, narrative, second scorer ─ as in v15
    new in v16-final
      derive      ─ obligation templates × positions → forced ACKs, switches, fetch lists      §22.2
      reach       ─ outcome vocabularies, bounds, reachable sets, thesis sets, pianos          §22.3
      stories     ─ story registry, loadings, angle classes, junctions, S⊥                     §20.2–20.4
      instruments ─ instrument map, cap classes, cost model, price vintages                    §20.6, §26
      construct   ─ scenario grid, maximin solve, budgets, basket states                       §20.5, §20.7
      paper       ─ paper book: entries at lock, marks, exits, the four-part split              §19.2
      (plus the fold modules from the 22 September draft: library_as_of, tides, wiring,
       probes, locator, procedural chains, notice watch)
        │
        ▼ MCP tools (§27)
  OPERATOR RUNTIME (Claude via Claude Code, Hermes Agent, or API) — cold per round (§28)
```

**Naming.** The paper book is called `paper`, never "ledger". The ledger is the hash-chained event record (§14), and two things called "ledger" is how a spec rots.

**Import rules** (from the isolation spec, G1):
- Nomad library code imports `contract` and `decider` only.
- Tests use `testkit`.
- Only integration code (the MCP server wiring and run scripts) imports `dataprod`.
- The v15 modules that fetch prices directly (`prices` *(v15)*, via the Yahoo v8 chart API) keep working until the data product serves prices; from then on, they read through the vintage store (§26).

**One-way dependencies inside the harness.** `derive` and `reach` read positions, bounds, the library, ratified procedural states and the ACK graph, and never read prices or unratified model output. `stories`, `instruments` and `construct` read prices, and never write effects, ACKs, reachable sets or theses. The veto module (`surviving` *(v15)*) reads prices for one purpose, the pre-event band behind `below_band`. This is the principle "price enters construction, never generation" (§12), enforced by the import linter.

### 14. Round lifecycle — the firewall state machine `[carried]` + `[fold]` + `[gate]`

**v15's round states are kept** (`rounds.state` *(v15)*: `created`, `locked`, `open`, `partially_scored`, `scored`, `void`). The phases below are how the spec talks about a round; each maps onto a v15 state.

```
candidate ─→ admitted ─→ pre_lock ─→ locked ─→ post_lock ─→ live ─→ scored ─→ adjudicated
   │            │            │           │                     │
   │            │            │           └─ calls and emergent  └─ calls resolve at due_at;
   │            │            │              objects hash-sealed    baskets marked and exited
   │            │            └─ PIT only; dp as_of pinned = T_seg; web tools denied by hook
   │            └─ tags + class + Q7 computed; rejections written
   └─ enumeration_candidates (v15)
```

| Phase | v15 state | Entry condition | What is allowed | Rows written |
|---|---|---|---|---|
| `candidate` | — (`enumeration_candidates` *(v15)*) | Enumerated by `nomad_enumerate` | Intake dry-run | Candidate row |
| `admitted` | `created` | Human confirms Q3, Q4, Q6, Q8 (or, in `tags_only` mode, Q3 and Q8; §15) | — | `rounds`, `round_tags`, `round_classifications` *(v15)*; the operator manifest |
| `pre_lock` | `created` | Reveal issued | `nomad_pit_fetch`; `dp_*` pinned to `as_of = T_seg`; `library_as_of(T_seg)`; decider calls with models passing the model time wall; derivation, reachability, stories and construction (§16) on prices dated before T_seg. **Live WebSearch and WebFetch are denied by a hook** | `evidence` *(v15)* with `knowable_from` and `retrieved_pre_lock = true`; `pit_fetches` with the operator's stated reason |
| `locked` | `locked` | `nomad_lock_predictions` *(v15)* for segment 0; `nomad_segment_lock` *(v15)*, extended, for later segments | Nothing may change a call, an ACK, a set or a basket. **A further lock is refused, with one exception:** v15's further lock that names a fallback carrier for a flagged call (Q7) stays, as a supersession that changes nothing else | The lock manifest (below); one `paper_positions` row per instrument of each built basket, with the fill pending |
| `post_lock` / `live` | `open`, `partially_scored` | Immediately after lock | Live retrieval opens on live rounds (on backfilled walks, see below). Paper fills are written at the first quote after lock. Calls resolve as they fall due. At each ACK firing, the walk recomputes and locks the next segment (§22.4) | `resolutions`, `ack_firings`, `segments` *(v15)*; `paper_marks`, `paper_exits` |
| `scored` | `scored` | Every call resolved or expired, and every basket closed | — | Round score (three levels) and the paper result, split four ways (§19.2) |
| `adjudicated` | `scored` | Second scorer returns | Disputed resolutions are excluded from library stats | `second_scores` *(v15)* |
| — | `void` | `nomad_void_round` *(v15)* | Nothing | Kept, never scored; its baskets are closed at the void date and reported, never counted |

**T_seg, the clock of a segment** `[gate]`. Segment 0's clock is `event_date`, the time wall of §9. A later segment's clock is the `knowable_from` of the firing that opened it (a column v16 adds to `ack_firings`). **Every read for a segment is bounded by its clock:** positions and bounds with `knowable_from ≤ T_seg` (a NULL `knowable_from` counts as unknown), price vintages dated before T_seg for loadings, volatilities and bands, `library_as_of(T_seg)`, the data-product pin, point-in-time fetches, and procedural counts. Execution prices are the exception, and are set by the entry rules (§19.2). v15's `lock_segment` stamps `locked_at` with today's date unless told otherwise; v16 always passes the segment's clock, and records the wall-clock time separately. This is what keeps a backfilled walk from seeing its own future.

**Later segments lock like segment 0.** v15's `nomad_segment_lock` writes only a `segments` row. v16 gives it the full lock behaviour for the segment (calls with `segment_id`, derived ACKs, sets, stories, baskets, manifest, paper rows, lock hash), legal while the round is `open` or `partially_scored`.

**Backfilled rounds:** `event_date` is in the past, and walking forward through a window is allowed, one segment clock at a time. **On a backfilled walk the pre-lock regime moves with the clock.** The hook stays closed and the data product and the point-in-time fetcher stay pinned, first to T₀, then to each new T_seg as ACKs fire. The operator finds a firing by reading the ACK's carriers forward from the current clock; the first delivered fact sets the next clock, and nothing dated after it is readable until that segment locks. Live retrieval for scoring opens only when the walk's last segment has locked. **Live rounds:** submitted from the day of the event (Event Requirements v3, Section F), with `due_at ≤ DUE_AT_MAX_DAYS` (90) per call.

**Lock runs once, and on one pass** `[gate, v15 fix]`. `rounds.lock_predictions` *(v15)* calls `assess_round` twice with `write=True`, so the second pass writes superseding `surviving_risk` rows. v16 calls it once. A test asserts one `surviving_risk` row per leg (P0), then per effect (P1), per lock.

**The lock manifest** `[gate]`. Several inputs to the emergent objects live in mutable stores (library rules, holders, ACK nodes, transforms, and the new templates, vocabularies, bounds, stories, instruments and cost models), which are corrected in place. So lock records a manifest: the **canonical content** of every mutable-store row read (content-addressed, so a row used by many locks is stored once), every vintage id (vintages keep their payloads), the `library_history` version, the config hash, and the round and tide budget used before this lock. The lock hash covers the calls, branches, pieces, links and vetoes, every emergent object (derived ACKs with their condition states, outcome, reachable and thesis sets, story classes and loadings, junction flags and treatments, S⊥, scenario grids, basket weights and states) and the manifest. **Replay reads the manifest, not the live stores.** An emergent object recomputed from the manifest must reproduce the lock hash; if it doesn't, the round is flagged `nondeterministic`, and its baskets are excluded from K13 until the cause is found.

**The ledger, as v15 built it** `[carried]`:
- Ledger tables (`LEDGER_TABLES` in `db.py` *(v15)*) are append-only. Each row carries `prev_row_hash` and `row_hash`, chaining the rows of its table, and `recorded_at` is set by the database layer only.
- Mutable stores (`MUTABLE_TABLES` *(v15)*) are corrected in place. What they date goes on the ledger elsewhere, and v16's lock manifest pins the versions a round used.
- `nomad_verify_chain` *(v15)* verifies the chains. v16 also runs it at start-up, and a break stops the harness.
- Every new table in §18.3 is declared ledger or mutable there.
- Widening a v15 CHECK constraint goes through `db._rebuild_table` *(v15)*, which preserves the hash chain. No other schema edit to a v15 table is allowed.
### 15. Intake `[carried]` (Event Requirements v3) + `[fold]` + `[gate]`

**Event Requirements v3 (Section F) applies in full as the `strict_v3` mode, with one proposed override** (absence expiry, below; D9) **and one proposed addition** (the domain-preference tie-break, D15):
- Tags: `lag_test`, `headline`, `weather`, `late_headline`, `learning`.
- The cap: at most one `weather` or `late_headline` in any two consecutive admitted rounds.
- The required mix over the next seven admitted rounds: ≥4 `headline` and ≥3 `lag_test`.
- Questions Q1a–Q9, with Q8 never relaxing.
- Live rounds.
- The harness-run selection procedure.

**Q2 and Q9 sit outside the mode table, in both modes.** Q2 is not a gate and not a tag: it is computed at admission and sets `class` (`clean` or `learning`; §9, §14). Q9 gates **clean** rounds only, as v15 enforces it (v11 §C; `rounds.py`): a Q9 fail on a clean round is refused, and the round may be re-submitted as `learning`. An `enumeration_manual` round (fold change 1 below) passes Q9 only through v15's logged-skip route (`nomad_selection_window` and `nomad_reject_event` for every skip); otherwise it is admitted as `learning`.

**Intake mode is a config value, recorded per round:**

| Mode | What gates | What becomes a tag |
|---|---|---|
| `strict_v3` | As written in v3 | As written in v3 |
| `tags_only` | Q3 and Q8 only | Q1a, Q1b, Q4, Q5, Q6 and Q7. Mid-sequence (Q1a-fail) candidates are admitted and tagged. **Formal handling of that class is still an open call (§34)** |

**Fold changes:**
1. **Enumeration source.** `nomad_enumerate(feed_set, from, to)` *(existing)* reads from the data product (`dp_search` / `dp_stream` over recorded feeds) wherever `Capability.RECORDING` covers the window. Where it doesn't, it falls back to web enumeration with the round tagged `enumeration_manual`, which Q9 cannot pass mechanically.
2. **Q1a window search** uses `dp_search(as_of = event_date)` where recorded. It is point-in-time, and it **raises on truncation**. A truncated search is never read as "nothing related".
3. **Q1b** reads the ledger and the incident registries per node type, as before.
4. **Laya pre-sort** (§24, job `intake_reader`) reads each enumerated item before the human does:
   - It answers Q3 and proposes Q4–Q6 tags and a size-band hint.
   - It **never reorders**, so first-pass stays in date order.
   - **In shadow (the default, until K1 passes) it removes nothing.** It flags and annotates; the human reads the whole pile.
   - **Removal is the gated exception.** Only after K1 passes may a model reading keep an item from the human, and then every removal is a logged rejection row with the full distribution and the checkpoint, and a random sample (appetite; suggest 10%) is re-read by the human each batch so recall is measured rather than assumed.
   - **Removal changes the population every finding generalises to**, so a round enumerated under model removal records `presort_active` with the checkpoint, next to `feed_set`. This is an intake filter, never an anchor: it never eliminates an effect, a link or a leg (§5).
5. **Feed vocabulary per stratum** `[v16 C5]`. Each stratum (industrial, energy, metals, shipping, chemicals, digital infrastructure, …) has its own query set and feeds. Digital infrastructure includes status pages and cloud-provider incident feeds. The feed set defines the population every finding generalises to, so it is recorded per round.
6. **`node_type` is a registry, not an enum** `[v16 C3]`. Unseen types (strait, smelter, pipeline, sovereign debt, a cloud region, …) are accepted and registered, and carrier density is computed per type from what exists. It is a new field: v15's `nodes.node_kind` *(v15)* keeps its meaning (`event` or `attribute`), and the `node_kinds` lists on v15's carrier seeds (`refinery`, `power`, `port`, …) are read as node types.
7. **Entity scope** `[gate]`. An event's node can be any economic or financial entity (§1): a strait, a sovereign's debt, a central bank's facility, a commodity grade at a location, a contract. `node_type` registration (item 6) covers these.

**Domain preference** `[gate]` (D15). Selection is unchanged: Event Requirements v3's tags, cap and required mix still govern. Within the candidates that pass, the selector prefers events whose node carries (a) at least one obligation template that could fire and (b) a priced distribution **listed before the event date**: options on a holder, or an event contract on a holder or on the node. (A contract listed on the event itself exists only after the event, so it can't inform selection of a backfilled round.) Headline and geopolitical events usually qualify. The preference is a tie-break inside the harness-run selection procedure (`nomad_select_next` *(v15)*), applied after v3's rules: it decides which candidate is admitted when v3 leaves a tie. It never removes an item, the human's first pass still reads in date order, and the preference is recorded per round so the population it creates is known.

**The selector suspension is cleared** (v16 brief §0.2), logged with its reason through `nomad_selector_clear` *(v15)*.

**The override: absence claims don't expire into hits** `[gate]` (D9; proposed, and it contradicts Section F). v15's `scorer.close_round` *(v15)* expires every unresolved absence call (a `null` call, or a `sign` call of `0`) as `hit` at thin coverage, following v3. v16 replaces that rule with typed silence (§8): an absence call resolves `hit` only when its carrier was read in full through `due_at` and said nothing (`carrier_state = silent`). An expired absence call whose carrier was not read in full resolves `unverified`, with `carrier_state = unread` or `not_covered`. The absence record (15 of 16) is recomputed under the new rule, and both numbers are reported, in P1.
### 16. Operator procedure per round `[carried]` + `[fold]` + `[gate]`

Decision-model steps are in *italics*; each runs in shadow until its promotion gate passes (§24.6). **The operator authors inputs and ratifies; the harness computes.** The operator never edits a derived ACK's conditions, a reachable set, a loading or a basket weight by hand. A disagreement with a computed object is recorded as a note with its reason, and fixed in the stores (a position, a template, a vocabulary, a story), which the next computation reads.

1. **Reveal** `[carried]`. The operator receives:
   - the event line (bare, Q8);
   - holders and positions on the node and its neighbours, per asset;
   - node facts;
   - scheduled facts within the round's maximum `due_at` for degree ≤1 holders;
   - applicable rules with weights and `weight_state`, from `library_as_of(event_date)`, **including the obligation templates** for the node type;
   - the Q1a window-search result;
   - the carrier registry for the node type;
   - `[gate]` the **instrument map** for every holder within reach (§20.6), the **story registry** as of the event date, and the **tide registry**;
   - the point-in-time fetcher.
2. **Blind pass** `[carried]`. The operator's first reading before any fetch, recorded.
3. **Enumerate pieces.** Effects at holders, per asset where positions differ, with equal depth of analysis across degrees. An empty touched set needs a stated `no-touched-set:` reason. Generation is permissive.
4. ***Wire*** `[fold]`. `nomad_wire` asks the decision model about every candidate link (§25.1) and returns chains ranked for attention, plus a bottom slice.
5. **Fetch in attention order** via `nomad_pit_fetch` and `dp_*` (pinned). Fetch lists from step 8's switches join the queue.
6. ***Probe*** `[fold]`. `nomad_probe` runs spread probes on ranked links once their settling documents are fetched (§25.2).
7. **Anchors per effect** `[v16 B]` + `[gate]`. `nomad_anchors` runs the veto set per effect (§21). Vetoed effects leave; everything else goes forward.
8. **Derive ACKs** `[gate]`. `nomad_derive_acks` checks every obligation template against the positions (§22.2). For each template instance it returns `forced` (all conditions documented true), `switch` (some unknown, none false, with the fetch list) or `none`. *`nomad_ack_candidates` adds the locator's candidates (§25.3).* The operator ratifies or drops each. Scheduled ACKs come from the calendar as in v15 (`nomad_ack_build_standing` *(v15)*).
9. **Outcomes, reach, thesis** `[gate]`. For each ratified ACK, `nomad_outcomes` loads the outcome vocabulary for its notice kind. `nomad_reachable` cuts it to the reachable set, recording the anchor and evidence behind each cut. The operator states the thesis set Ωₜ, citing the positions and rules that remove each excluded outcome. Each ACK's vocabulary is registered as a `map` call whose branches are the outcomes, `other` included, so the ACK is scored like any other map call.
10. **Calls** `[carried]`. Each call has:
    - a call type *(v15)* (`sign`, `magnitude_order`, `lag_band`, `predicate`, `null`, `meta`, `map`, `narrative`), and the claim kind it makes (`occurrence | absence | ordering | magnitude | duration | map`), which every cited rule must carry;
    - a carrier with a working fetch path and a `due_at`;
    - a falsifier;
    - cited rules;
    - factors.

    `map` calls take named branches that **cover the space or include an `other` branch with its own falsifier** `[v16 C1]`. `lag_band` includes `minutes` and `hours` `[v16 C2]`, which widens the v15 CHECK (§14).
11. **Stories** `[gate]`. The operator names the stories running on the tape and the candidate adjacent readings, each with a path through the graph and either a proxy series or a construction rule (`nomad_stories`). The harness then:
    - estimates or constructs loadings (`nomad_loadings`);
    - classes each story by its angle to the thesis;
    - flags junctions (`nomad_junctions`);
    - computes S⊥ (`nomad_s_perp`).

    The operator records a treatment for each flagged junction: merge or hold.
12. **Narrative rows, then synthetics** `[carried]`. Narrative rows are pre-registered and scored first, as before. The stories they name are candidates for the story registry; a narrative row's resolution is post-lock and is never evidence that a story was active. Synthetics are built before lock and become candidate building blocks.
13. **Construct** `[gate]`. `nomad_construct` builds one basket per ratified ACK (§20.5) and returns `built`, `unbuildable` with its reason, or `vetoed`. The operator may not change weights. The operator may decline to hold a built basket, with a reason; the basket is still entered in the paper book as `declined`, so declining is scored too.
14. **Lock** `[carried]`. `nomad_lock_predictions` *(v15)* freezes and hashes everything from steps 3–13 (§14) and writes the paper entries.
15. **Post-lock.**
    - Live retrieval opens.
    - The notice watch (§25.4) runs against open calls.
    - Resolutions land as calls fall due.
    - At each ACK firing, the walk recomputes and locks the next segment (§22.4).
    - Marks and exits go to the paper book.

---

## PART III OF E — TECHNICAL (§17–§35)

### 17. Stack and conventions

- **Language and runtime:** Python ≥3.11, FastMCP for the MCP server, SQLite in WAL mode. Ledger tables are append-only, each with its own row hash chain (`prev_row_hash`, `row_hash` *(v15)*); mutable stores sit beside them (§14).
- **Tests:** `pytest`. Fixture-only by default; a test needing real data is marked and excluded from the default run.
- **Versions are content hashes** `[fold]`. `harness_version` is the hash of the harness source; `config_hash` is the hash of the appetite and config files. Both are recorded on every round and every report.
- **No defaults on verdict-governing numbers.** A test asserts that the config loader refuses a missing appetite value.
- **Every tool response that feeds a decision** carries `harness_version`, `logic_version`, `config_hash`, the chain heads (`db.chain_heads` *(v15)*) and, where relevant, the checkpoint ids and the data-product receipt.

### 18. Data model `[carried]` + `[fold]` + `[gate]`

The harness is evolved in place, so **v15 tables keep their names and columns** (as in `db.py` *(v15)*). v16 adds columns and tables. Adding a column is a plain migration; widening a v15 CHECK constraint goes through `db._rebuild_table` *(v15)* (§14). Field lists are the minimum, and builds may add fields. Every new table is declared **ledger** (append-only, hash-chained, `recorded_at` set by the database layer) or **mutable** (a store corrected in place, pinned per round by the lock manifest).

#### 18.1 v15 tables kept, with v16 additions

| Table *(v15)* | Relevant v15 columns | v16 adds |
|---|---|---|
| `rounds` (ledger) | `operator`, `operator_cutoff`, `state`, `round_class`, `contamination` | Written at admission: `intake_mode`, `feed_set`, `stratum`, `operator_runtime`, `harness_version`, `logic_version` (`v15`/`v16`), `config_hash`, `live`, `presort_active`, `domain_pref`. Fields known only later (`hook_verified`, `tide_id`, declared at lock) go to a new ledger table `round_meta` (`round_id`, `field`, `value`, `supersedes`), because `rounds` rows can't be updated. Tags stay in `round_tags` *(v15)* |
| `holders` | `kind`, `listed`, `ticker`, `exchange`, `parent_id`, `options_listed`, `price_symbol`, `cik` | `holder_class` (`listed_instrument`/`unlisted_operating_asset`/`aggregate`/`authority`), `entity_kind` (`company_asset`/`sovereign`/`agency`/`central_bank`/`fund`/`index`/`commodity`/`currency`/`contract`), `entity_ref` (data-product entity id) |
| `positions` | Append-only; `holder_id`, `node`, `attribute`, `value` (text), `unit`, `source`, `source_time`, `knowable_from`, `confidence` (`stated`/`inferred`/`implicit`), `supersedes`, `recorded_at` | `asset_ref` (per asset, not per owner), `source_document`, `value_num` (numeric value where the attribute is numeric). **The `attribute` enum CHECK is dropped** in one `_rebuild_table`, and `positions.add` (plus a BEFORE INSERT trigger) validates the attribute against `position_attributes` (§18.3), so registering an attribute never rebuilds the table |
| `nodes` | `node`, `node_kind` (`event`/`attribute`), `attribute_kind` | `node_type` (§15) |
| `effects` | `effect_kind`, `magnitude`, `parent_effect_id`, `depth`, `attenuated_support`, `root_effect_id`, `ack_id`, `segment_id`, `eliminated`, `elimination_basis`, `carried_by` | `vetoed_by` (veto id), `outcome_id` (when an effect is conditional on an ACK outcome). v15's `eliminated` is kept as history |
| `transforms` | Keys `tf.{rel}.{from}.{to}`, seeded from `TRANSFORM_SEED` | — |
| `ack_nodes` (mutable) | `ack_kind` (`scheduled`/`forced`), `fact`, `source`, `due_at`, `obligation`, `parent_ack_id`, `round_id`, `holder_id`, `participant_class`, `attention`, `standing` | `origin` (`operator`/`calendar`/`derived`/`locator`), `derivation_id`, `notice_kind`, `status` (`candidate`/`ratified`/`dropped`), `is_switch`, `window_to`, `window_basis` (`statute`/`procedural_chain`/`operator`/`cap`), `window_ratified` |
| `ack_firings` | `fired_at`, `delivered`, `delivered_fact`, `implied`, `gap`, `opens_effect_ids`, `kills_effect_ids`, `successor_ack_ids`, `segment_id` | `outcome_id` (required when `delivered`), `knowable_from` (when the delivered fact became public: the next segment's clock) |
| `segments` | `idx`, `parent_segment_id`, `opened_by_ack_id`, `opened_by_firing_id`, `effect_ids`, `next_ack_ids`, `locked_at` | `clock` (T_seg, §14), `lock_hash`, `manifest_id` |
| `predictions` (calls) | `call_type`, `claim`, `lag_band`, `due_at`, `branches`, `conditional_on`, `narrative_sign`, `implied_method`, `implied_value`, `effect_id` | `segment_id`, `claim_kind` (the carriage kind). **`lag_band` CHECK widened** to add `minutes` and `hours` |
| `resolutions` | `outcome` (`hit`/`miss`/`unverified`/`untestable`), `source_coverage`, `expired`, `quality` | `carrier_state` (`silent`/`spoke`/`unread`/`not_covered`) (§15). Disputes stay in v15's dispute and second-scorer tables |
| `evidence` | `url`, `source_time`, `knowable_from`, `carrier` | `retrieved_pre_lock` |
| `surviving_risk` | Per leg (`position_id`, NOT NULL), `eliminators_fired`, `eliminators_unevaluable`, `survives`, `effect_id` (never written in v15) | `position_id` made nullable (one `_rebuild_table`), since an effect may have no leg. Written **per effect**, once per lock; `status` (`vetoed`/`forward`); per-term `gap_reason`; `stake_basis`, `operator_basis`, `n` |
| `library_rules` (mutable) | `rule_text`, `forbids`, `layer`, `status`, `carries`, `weight`, `clean_hit_rounds` | `kind` (`mechanism`/`obligation`/…) |
| `synthetic_legs`, `synthetic_exposures` | As is | `instrument_id` on components; declared attribute exposures seed constructed loadings (§20.2) |
| `price_observations` | `date`, `value`, `band_low`, `band_high`, `attributed` | `vintage_id` |
| `pit_fetches`, `leg_claims`, `risk_rules`, `second_scores`, `round_tags` | As is | — |

Narrative rows are `predictions` rows with `call_type = narrative` *(v15)*.

#### 18.2 New tables from the fold (22 September draft)

| Table | Kind | Key fields |
|---|---|---|
| `intake_candidates` | ledger | `cand_id`, `source_record_ids[]`, `enumeration_run_id`, `q_results{Q1a..Q9}`, `model_reading{dist, checkpoint}`, `decision`, `reason`, `failing_q` |
| `enumeration_runs` | ledger | `run_id`, `feed_set`, `from`, `to`, `source_mode` (`recorded`/`manual`), `complete`, `truncation_reason` |
| `node_types` | mutable | `node_type`, `description`, `first_seen_round`, `carrier_density` (computed) |
| `tides` | mutable | `tide_id`, `label`, `declared_by`, `from`, `to`, `retro_declared` |
| `library_history` | ledger | `rule_id`, `weight`, `weight_state`, `computed_from_resolutions[]`, `valid_from` (the latest `knowable_from` of its inputs) |
| `wiring_runs` | ledger | `run_id`, `round_id`, `checkpoint`, `question_set_hash`, `k`, `bottom_slice`, `mode` |
| `link_readings` | ledger | `link_id`, `parent_effect`, `candidate_child`, `dist_without_doc`, `dist_with_doc`, `settling_doc_type`, `obliged`, `reading` (`ignorance`/`mechanical`/`graded`/`switch`/`unread`), `paraphrase_stable`, `checkpoint` |
| `chains` | ledger | `chain_id`, `round_id`, `effects[]`, `attention_rank`, `status` (`examined`/`unexamined`/`vetoed`) |
| `procedural_models` | mutable | `process_type`, `states[]`, `transitions{from, to, n, time_dist}`, `docket_sources[]`, `counted_through` |
| `procedural_states` | ledger | `ack_id`, `document_ref`, `state`, `proposed_by` (checkpoint), `ratified` |
| `decision_calls` | ledger | `call_hash`, `input_hash`, `question_set_hash`, `checkpoint`, `outputs{full distributions}`, `latency_ms`, `job`, `mode` |
| `model_registry` | mutable | `checkpoint`, `base`, `task_heads[]`, `trained_through`, `trained_through_basis`, `label_snapshot_hash`, `temperatures{}`, `metrics{}`, `status` |
| `labels` | ledger | `label_id`, `task`, `input_ref`, `answer`, `label_source`, `label_knowable_at` |

#### 18.3 New tables from the gate

| Table | Kind | Key fields |
|---|---|---|
| `position_attributes` | mutable | `attribute`, `type` (`numeric`/`enum`/`bool`/`text`), `unit`, `allowed[]`. Seeded with v15's six, plus the ones templates test: `inventory_days`, `contract_type`, `hedge_ratio`, `input_share`, `capacity`, `substitute_lead_days`, … |
| `bounds` | mutable | `bound_id`, `subject` (asset class, process type or statute), `quantity` (`lead_time_days`/`rebuild_days`/`statutory_min_days`/`inventory_norm_days`/…), `value`, `source_document`, `knowable_from` |
| `obligation_templates` | mutable | `template_id` (also a library rule id, `kind = obligation`), `node_types[]`, `roles[]`, `conditions[]{role, attribute or bound, op, value}`, `forces` (the `notice_kind`), `carrier_kinds[]`, `window_rule` (statute, procedural chain or none), `forbids`, `authored_from_rounds[]` |
| `ack_derivations` | ledger | `derivation_id`, `round_id`, `segment_id`, `clock`, `template_id`, `bindings{role: holder/asset}`, `conditions[]{position_ids[], state (true/false/unknown), evidence_ids[]}`, `result` (`forced`/`switch`/`none`), `fetch_list[]`, `ack_id` |
| `outcome_vocabs` | mutable | `vocab_id`, `notice_kind`, `outcomes[]{outcome_id, label, needs[]{role, attribute or bound, op, value}}`; always includes `other` |
| `ack_outcomes` | ledger | `ack_id`, `segment_id`, `outcome_id`, `reach` (`reachable`/`cut`/`kept_unknown`), `cut_by` (veto, bound, statute, ratified procedural state), `evidence_ids[]`, `in_thesis`, `thesis_basis` |
| `stories` | mutable | `story_id`, `label`, `path_nodes[]`, `loading_kind` (`estimated`/`constructed`), `proxy[]`, `construction_rule`, `origin` (`operator`/`decider_proposed`/`junction`) |
| `story_classes` | ledger | `story_id`, `round_id`, `segment_id`, `active`, `active_basis`, `angle`, `class` (`orthogonal`/`parallel`/`adjacent`/`synthetic`/`unrelated`), `decomposition[]`, `s_ref_hash` |
| `story_loadings` | ledger | `story_id`, `instrument_id`, `segment_id`, `loading`, `se`, `window_from`, `window_to`, `vintage_ids[]` |
| `junctions` | ledger | `junction_id`, `segment_id`, `story_a`, `story_b`, `shared_node`, `trigger_ack_id`, `corr_before`, `corr_after`, `status` (`flagged`/`confirmed`/`piano`), `treatment` (`merged`/`held`), `node_story_id` |
| `s_perp` | ledger | `round_id`, `segment_id`, `ack_id`, `outcome_id`, `s_norm`, `s_perp_norm`, `rho`, `residual_noise_band`, `hedged_set[]` |
| `instruments` | mutable | `instrument_id`, `holder_id` or `ack_id` (event contracts), `yes_outcomes[]` (event contracts: which vocabulary outcomes pay), `kind`, `symbol`, `venue`, `listed_from`, `cap_class` (`hard`/`stress`/`uncapped`), `expiry`, `strikes[]`, `multiplier`, `liquidity`, `cost_model_id`, `quote_source` |
| `cost_models` | mutable | `cost_model_id`, `kind`, `spread_rule`, `fee`, `borrow`, `slippage_rule`, `pricing_rule` (for options) |
| `price_vintages` | ledger | `vintage_id`, `symbol`, `source`, `retrieved_at`, `from`, `to`, `payload` (or a content-addressed blob reference), `payload_hash` (over the decompressed payload), `metadata{}`, `drift_of` |
| `lock_manifests` | ledger | `manifest_id`, `round_id`, `segment_id`, `store_rows{table: {row_id: content_hash}}`, `vintage_ids[]`, `library_history_version`, `config_hash`, `round_budget_used`, `tide_budget_used` |
| `store_snapshots` | ledger | `content_hash`, `table`, `row_id`, `canonical_json`. Content-addressed: one copy per distinct row version |
| `constructed_baskets` | ledger | `basket_id`, `round_id`, `segment_id`, `ack_id`, `status` (`built`/`unbuildable`/`vetoed`/`declined`/`held`/`closed`), `reason`, `shape`, `z_star`, `b_basket`, `max_loss`, `tide_id`, `weights_hash`, `lock_hash` |
| `basket_weights` | ledger | `basket_id`, `instrument_id`, `w_long`, `w_short`, `max_loss_contribution` |
| `scenarios` | ledger | `basket_id`, `scenario_id`, `outcome_id`, `in_thesis`, `tide_state`, `payoffs{instrument_id: [lo, hi]}`, `payoff_worst`, `upside_if_adopted` |
| `paper_positions` | ledger | `paper_id`, `basket_id`, `instrument_id`, `side`, `qty`, `entry_rule` (`live_first_quote`/`backfill_first_close`/`modelled`), `max_loss`, `exit_rules{}` |
| `paper_fills` | ledger | `paper_id`, `at`, `price`, `vintage_id` |
| `paper_marks` | ledger | `paper_id`, `at`, `price`, `vintage_id`, `trigger` (`ack_fired`/`scheduled`/`exit_check`) |
| `paper_exits` | ledger | `paper_id`, `at`, `price`, `reason` (`s_perp_recovered`/`attention_ack`/`window_end`/`stop`/`void`), `pnl`, `split{narrowing, timing, residual, costs, leaks}` |
| `pianos` | ledger | `piano_id`, `round_id`, `basket_id`, `description`, `outside` (`vocabulary`/`closure`/`stop_gap`/`junction_without_node`), `cost` |

**Three names that must not be confused.** `basket.py` *(v15)* and `nomad_event_basket` *(v15)* are the v15 view of legs per round; `constructed_baskets` is the v16 table of built baskets. `risk.exposure` *(v15)* and `nomad_exposure` *(v15)* sum signed support per node, and have nothing to do with `synthetic_exposures` or story loadings. `nodes.node_kind` *(v15)* is event-or-attribute; `node_type` is what kind of thing the node is.
### 19. Scoring `[carried]` + `[fold]` + `[gate]`

#### 19.1 Resolutions and weight propagation `[carried]` + `[fold]`

- **Resolution outcomes:**
  - `hit` / `miss` — the carrier spoke and decided the call.
  - `unverified` — the carrier had not spoken by `due_at`, on a non-absence claim.
  - `untestable` — a dead branch, at weight 0.
  - Disputes — second-scorer disagreements, recorded through v15's dispute tools (`nomad_score_disputes`, `nomad_disputes` *(v15)*) rather than as an outcome value, and excluded from library stats until settled.
  - `[gate]` Absence claims resolve `hit` only on `carrier_state = silent`, with quality discounted by coverage. This overrides v15's expiry rule and Event Requirements v3 (§15, D9; proposed).
- **Carriage is enforced at lock.** Retroactive carriage backfills exclude citations the rule does not carry and recompute weights. Those weights become `untested_as_carried`; they are not demoted.
- **Weight propagation.**
  - Rule weight derives from qualifying resolutions.
  - Each derived object applies its hop discount (values carried from the current config; re-ratify on migration). A relation with no hop discount of its own uses `DEFAULT_HOP_DISCOUNT`, which is now a ratified appetite value (§33), and the effect records that it did.
  - Cross-membership applies the independence discount (appetite: 1.0 at root split → 0.15 at last-node split).
  - The support threshold is appetite (0.30).
  - Nothing ever sums weight down a chain.
- **Scoring at three levels** (§7.1). All three numbers are written per round. The basket level is now scored in money (§19.2).
- **Scorer bias** is a standing statistic in three classes. Only `lenient` counts toward a self-scoring discount, reviewed at twenty clean rounds.
- **Narrative rows** are scored first and never re-scored after structural resolution.
- **Tide-counted support** `[fold]`.
  - Each resolution records its ambient tide (declared by the operator at lock, from a registry of tides).
  - Library support counts the number of **distinct tides** with qualifying hits, alongside the raw count.
  - Validation requires support across ≥2 tides (appetite) or is marked `single_tide`.
  - v15 validates on distinct `clean_hit_rounds` ≥ 2; v16 keeps that count and adds the tide count beside it.

#### 19.2 The paper book `[gate]`

Every built basket is entered in a **paper book** at lock. Nothing is traded. The book exists so Claim 1 is answered in money, per basket, with the losses counted.

**Entry.** Lock writes one `paper_positions` row per instrument: instrument, side, size, maximum loss and exit rules. The fill price is written separately (`paper_fills`), because on a live round it doesn't exist yet at lock:
- **Live rounds:** the fill is the first executable quote after lock, at the cost model's fill (mid plus half the spread plus slippage), `entry_rule = live_first_quote`. Construction priced at the last quote before lock; only the drift from that quote to the fill is booked as slippage.
- **Backfilled rounds:** the first close after the event's `knowable_from`, `entry_rule = backfill_first_close`. Construction prices at that same close, so there is no slippage term beyond the cost model. No backfilled entry may use a price from before the fact was public.
- **Instruments with no quote history** (options and most event contracts on backfilled rounds, since free sources keep current chains only): priced by a stated model from the underlying's vintage prices, `entry_rule = modelled`. Modelled entries are reported separately and **never count toward K13**.

Each row records its maximum loss, known at entry, and its exit rules: S⊥ threshold, attention ACK, window end, and a stop for stress-capped instruments.

**Marks and exits.** Marks are taken at every ACK firing and on a fixed schedule (appetite). A basket exits at the first of:
- S⊥ below its exit threshold;
- the first attention ACK after the structural ACK;
- the end of the ACK window;
- a stop, for stress-capped positions.

The exit reason is recorded, because each one says something different about Claim 1.

**The four-part split.** Every closed basket's result is split, in a fixed order, so that "made money" and "was right" can't be confused:

```
result = narrowing + timing + residual − costs − leaks
```

| Part | What it is | How it's attributed |
|---|---|---|
| **Costs** | Spreads, fees, borrow, slippage | From the cost model; attributed first |
| **Leaks** | Pianos, stop gaps, and hedge slippage (P&L from stories the basket was meant to have hedged) | Hedge slippage = weights × loadings × realised story and tide moves, for orthogonal and parallel stories; pianos and gaps logged individually |
| **Narrowing** | The market paying for outcomes outside Ωₜ | Change in value of the basket's claim on excluded outcomes, priced from the quoted distribution (option surface or event contract) at entry and at exit. Zero where no distribution is quoted |
| **Timing** | Forced notices landing inside a window the options didn't price | Option and contract P&L around the ACK date not explained by moves in the underlying or by narrowing |
| **Residual** | S⊥ being priced when the fact lands | What remains: the hedged residual's P&L, plus P&L on deliberately held adjacent exposure |

The attribution order and formulas are fixed before the first lock (appetite, §33) and never changed to flatter a result. A basket whose result is positive only through leaks going its way counts as a loss for K13.

**Counting.** P&L is aggregated per disjoint tide, not per basket or per round: ten baskets on one conflict are one observation (§7.7, §19.1). Declined baskets are booked and reported beside held ones. Clean and learning rounds, and live and backfilled rounds, are reported separately; only live, clean, non-modelled baskets count toward K13.

### 20. The risk engine: measure, then build `[v16]` + `[fold]` + `[gate]`

The risk engine has two jobs. It **measures** the five terms per effect, which is diagnostic and feeds the wall map. And it **builds** one basket per ratified ACK, which is where the terms now do their work. Nothing in this section vetoes an effect; vetoes are §21's. Every computation for a segment is bounded by that segment's clock, T_seg (§14).

**Two units, kept apart.** Angles, projections and ρ are computed in **residual-volatility units**: each instrument's coordinate is scaled by its pre-T_seg volatility after regressing on the tide, so a volatile small cap doesn't dominate every angle.

**The hedged residual**, wherever this spec uses it (stake bands, `below_band`, visibility), is the residual after regressing on the **tide only**. It can be computed at the veto step, before any story exists. Payoffs, costs, maximum losses and budgets are in **currency**, and weights are in **instrument units** (shares, contracts). §20.4 is in the first unit; §20.5 converts to the second.

#### 20.1 Terms and typed gaps

| Term | Inputs | Computation | Typed gaps |
|---|---|---|---|
| `stake` | Effect magnitude: `leg_claims.impact_pct` *(v15)*, else the % in an occurrence claim. **`implied_value` is not a stake input in v16**: it is what the market prices, and its v15 method `realised_since_event` is post-event | `impact ÷ denominator`, with `stake_basis` as in §8. For `price_band`, the denominator is a **rule resolved at lock over the instrument's own pre-T_seg hedged residual** (a block-bootstrap quantile of residual moves over the call's horizon, block length `BOOTSTRAP_BLOCK`). The rule is appetite; the resolved number is recorded | `not_representable` (no denominator for the class), `not_disclosed` (no impact stated, or operating scale unpublished), `not_covered`, `not_applicable` (authority) |
| `structural` | Surviving support of the effect path after vetoes, attenuation and independence | As in v15 (`vector.leg_vector` *(v15)*) | Rare; `not_covered` if the path has no document |
| `pricedness` | At lock: **ρ** (§20.4). Higher is better, as for every v15 term. Post-lock: the **noise baseline** and **peer control** decide whether a re-encode happened | Noise baseline: is the post-`knowable_from` move outside the instrument's own block-bootstrap distribution of hedged residuals? Peer control: did the holder move while declared peers held? Record which side of the close `knowable_from` fell on. Where ρ can't be computed at lock, the v15 heuristic stands **without its re-encode terms** (they read post-event observations), with `basis = v15_heuristic_pre_event` | `not_covered` (no price series), `not_representable` (unlisted) |
| `operator` | Clean resolutions by call shape, per operator model | Fallback hierarchy (§8); `operator_basis` and `n` recorded | `not_covered` if even the top level is below `OPERATOR_MIN_N` |
| `expression` | The instrument map (§20.6), the turnover floor | The best cap class available on the holder before T_seg (`listed_from` < T_seg): 1.0 hard-capped instrument, 0.5 stress-capped only, 0.0 none | — (0.0 is a value, not a gap) |

**The obviousness meter never enters the risk engine.** A model reading that reached pricedness, loadings, S⊥ or construction would weight and size positions, exactly what §5 and §23 forbid. The meter's only uses are attention order (§25.1) and its own measurement in K3. If K3 passes, admitting it anywhere in this section is a **separate theory amendment**, argued and ratified on its own, never a consequence of K3.

#### 20.2 Stories and loadings

A **story** is a named reading on the tape with a path through the graph (the nodes it runs through) and a loading on each instrument in reach. There are two kinds:

| Kind | When | Loading |
|---|---|---|
| **Estimated** | The story has a proxy series: a commodity price, a sector ETF, an index, a spread | Regress each instrument's daily returns on the proxies and the tide over the `LOADING_SESSIONS` sessions before T_seg: rᵢ = αᵢ + βᵢ·tide + Σₖ Lᵢₖ·fₖ + εᵢ. Record Lᵢₖ with its standard error and the vintages it was read from |
| **Constructed** | The story has no series yet, which is usual for adjacent readings (they're not on the tape until the market reaches them), and for junction node stories | Lᵢ is a position attribute of the holder behind instrument i, standardised across instruments: fuel-hedge ratio, input share from the node, exposure to the attribute node. Declared `synthetic_exposures` *(v15)* rows are read here |

**Active or candidate, per segment.** A story is `active` for a segment if its proxy moved outside its own noise band in the `ACTIVE_WINDOW` before T_seg, or if the operator names it as running and cites a source knowable before T_seg. A narrative row's *resolution* is never evidence of activity; it is post-lock. Every other named story is a `candidate`. Activity is recorded per segment in `story_classes`, never on the story itself.

**The reference direction.** Stories are classed against S̄, the mean of S(ω) over the non-flat outcomes of the thesis set (§20.4), whose hash is recorded. The shape (§7.2) is computed from S(ω) first, because classing depends on it.

**Classing.** Let cₖ = |cos θₖ| between Lₖ and S̄. The test order is fixed:
1. **Synthetic**, if Lₖ lies within `SYNTH_EPS` of the span of the loadings of stories registered before it (lower `story_id`). Replace it with its components and class those. **If the synthetic story is active, its components inherit that activity**, so its direction can't leave the hedged set. Testing only against earlier stories stops both members of a collinear pair being marked synthetic.
2. **Orthogonal**, if active and cₖ ≤ cos(`ANGLE_ORTH`). Tide for this basket; hedged.
3. **Parallel**, if active and cₖ > cos(`ANGLE_ORTH`), whatever its sign. What it explains is priced; hedged. (An anti-parallel active story is parallel in this sense.)
4. **Adjacent**, if a candidate with cos θₖ > cos(`ANGLE_ORTH`) (pointing toward S̄), **and the basket's shape is directional**. Held. For volatility and premium shapes, S̄ doesn't define a direction, so no candidate is adjacent.
5. Otherwise **unrelated**: not constrained, watched for junctions.

Orthogonal and parallel are both hedged. The labels differ only in what they report: tide, or already priced.

**Re-estimation.** At every ACK firing, loadings and classes are recomputed for the new segment, from prices before its clock. At every scheduled mark, they are recomputed only for the exit tests (§20.4), from prices before the mark, and keyed by the mark; a mark doesn't open a segment. Recomputed values never rewrite the lock record.

#### 20.3 Junctions

**Flag at lock (structural).** For every pair of stories (a, b), flag a junction when both paths pass through the same node of the event's effect DAG, and that node is **constrained** inside the ACK window: a forced ACK or a derived ACK's outcome lands on it, or a no-slack fact is stated for it. Record the shared node and the triggering ACK. This is the only definition of a junction flag; §7.5 states the same rule.

**Treat at lock.** A flagged junction adds a **constructed story on the shared node** (`origin = junction`), with loadings from each instrument's position on that node. The operator records one treatment:
- **Merge:** the node story joins the hedged set H (§20.4). Use this when the thesis doesn't run through the node.
- **Hold:** the node story is held like an adjacent story (w · L ≥ 0), for directional shapes. Use this when S⊥ points at the node, so the junction is itself a recovery route.

**Confirm after lock (empirical).** After the trigger ACK, compare the rolling correlation of the two stories' factor residuals over `JUNCTION_WINDOW` sessions before and after. A rise of at least `JUNCTION_DELTA` confirms a flagged junction. A rise of that size between stories with no shared node is logged as a **piano**. It is never modelled after the fact.

#### 20.4 S⊥

For each named outcome ω in the reachable set R (the thesis set Ωₜ is part of it), S(ω) is the vector of the structure's expected responses across the instruments in reach, in residual-vol units: the sign from the effect DAG, the size from stake, both conditional on ω. Outcomes where |S(ω)| is below the residual noise band are **flat outcomes**.

```
H        = span of: the tide; every active story (orthogonal or parallel); every merged junction story
S⊥(ω)    = S(ω) − P_H S(ω)            (projection residual, residual-vol metric)
ρ(ω)     = |S⊥(ω)| / |S(ω)|          (non-flat ω only)
```

**Why this is what the basket holds.** Construction requires w · L ≈ 0 for every loading that spans H (§20.5). For any such w, w · S(ω) = w · S⊥(ω), up to `HEDGE_EPS`. So the hedged basket's structural payoff is its payoff on S⊥ and nothing else: the stories in H can't pay it and can't cost it. **The identity is first-order.** It is exact for linear instruments; for options it holds through their deltas, and is re-checked at every mark; event contracts don't load on stories at all (below).

**Pre-solve gates** (directional shapes only; flat and volatility shapes are judged by the programme itself, through the premiums in their payoffs, §20.5):
- **Priced:** min over non-flat ω of ρ(ω) ≥ `RHO_MIN`, else `unbuildable: rho_too_small`.
- **Visible:** min over non-flat ω of |S⊥(ω)| ≥ `VIS_K` × the hedged residual noise band, else `unbuildable: below_visibility`. This is "visibility = event size ÷ ambient tide" generalised to any instrument (§3).

**Exit tests,** run at every ACK firing and mark (each new segment recomputes H from the stories now active, and S from the delivered outcome if the ACK has fired):
- **Span test:** ρ ≤ `RHO_EXIT`. The market's stories have reached the structure.
- **Price test:** the basket's cumulative residual P&L reaches `RECOVERY_FRACTION` of its expected residual. The price has reached the structure without a story.

Either closes the basket with `reason = s_perp_recovered` (§19.2). Both are proposed amendments to T4's exit rule (D5).

#### 20.5 Construction

One programme per ratified ACK that has an outcome vocabulary, solved deterministically (HiGHS through `scipy.optimize.linprog`).

**Pre-solve gates**, in this order. The first that fails names the basket `unbuildable`:
1. `no_vocabulary`: the ACK's notice kind has no outcome vocabulary.
2. `shape_mixed`: the shape rule (§7.2) returns "mixed".
3. `no_instrument`: no instrument allowed by the shape, listed before T_seg, is in reach. The shape restricts instruments: directional → linear instruments, debit spreads, bought options, event contracts; long volatility → straddles, strangles, event contracts on several outcomes; sell premium → credit spreads, condors, event-contract NO sides.
4. `rho_too_small`, then `below_visibility` (§20.4; directional shapes only).
5. `timing_unexpressible`: no dated instrument outlives the ACK window, and the shape has no undated instrument.
6. `budget_exhausted`: B_basket (§20.7) is zero.

**Variables.** For each instrument i in reach, allowed by the shape: wᵢ⁺ ≥ 0 and wᵢ⁻ ≥ 0, in instrument units. wᵢ⁻ is fixed at 0 unless the instrument's short side is capped: a stock or ETF short under a stop, on a fully documented ACK, or a spread's short leg inside its package (§20.6).

**Payoff per unit**, in currency, for scenario s = (ω, τ) with τ ∈ {tide down, flat, up} at ±`TIDE_SHOCK`, evaluated at the ACK window's end:

| Instrument kind | Payoff per unit, band [lo, hi] |
|---|---|
| Linear (stock, ETF, future) | (Sᵢ(ω)·σᵢ + βᵢ·τ) · Pᵢ · multᵢ, ∓ the residual band × Pᵢ · multᵢ. σᵢ converts residual-vol units back to returns |
| Option or spread | The package's value at the band ends of its underlying, from the cost model's pricing rule (intrinsic value if expiry falls inside the window), minus the premium paid. The worse end is lo |
| Event contract | 1 if ω is in the contract's YES set, else 0, minus the price paid (for NO, the reverse). Exact: no band |

An unknown risk term widens the band of every instrument it touches by `UNKNOWN_WIDEN` (§8). Adjacent-story moves are not in the payoff: the adjacency constraint below makes them help or do nothing, and the upside if adopted is reported separately.

**Programme.** With rᵢ(s) = [loᵢ(s), hiᵢ(s)]:

```
maximise  z
subject to
  Σᵢ (wᵢ⁺·loᵢ(s) − wᵢ⁻·hiᵢ(s)) − cost(w) ≥ z                          every s with ω ∈ Ωₜ
  Σᵢ (wᵢ⁺·loᵢ(s) − wᵢ⁻·hiᵢ(s)) − cost(w) ≥ −EXCLUDED_LOSS_FRAC·B_basket every s with ω ∈ R \ Ωₜ
  |w · Lₖ| ≤ HEDGE_EPS · Σᵢ(wᵢ⁺ + wᵢ⁻)·Pᵢ                              every loading spanning H (tide, active, merged)
  w · Lₖ ≥ 0                                                          every adjacent and held-junction story (directional shapes)
  Σᵢ (wᵢ⁺ + wᵢ⁻) · maxlossᵢ = B_basket                                 the whole budget is committed
  wᵢ⁺ + wᵢ⁻ ≤ LIQ_CAP · liquidityᵢ
```

- Loadings enter the hedge constraints in currency per unit: Lᵢₖ · σᵢ · Pᵢ · multᵢ for a linear instrument; Δᵢ · L_uₖ · σ_u · P_u · mult_u for an option or spread on underlying u (its delta at entry, re-checked at marks); zero for an event contract, whose story loading is a typed gap (`not_applicable`), so event contracts enter only through their payoffs.
- `cost(w)` is linear: half-spread, fees, borrow and slippage per unit, from the cost model.
- **The budget is an equality.** Otherwise w = 0 is always feasible, z* is never negative, and any positive z* scales with the budget. With the equality, z* is the worst-case result of committing B_basket, and it can be negative.
- **What the programme is paid for.** Premiums and contract prices sit inside the payoffs. An instrument that pays in every outcome of Ωₜ, and costs the market's price for outcomes outside it, is exactly "what the market pays for outcomes outside Ωₜ" (§7.2).
- Summing maximum losses is conservative on purpose.

**Decision.** `EDGE_MARGIN` and `TOLERANCE` are fractions of B_basket:

| Result | State |
|---|---|
| z* ≥ `EDGE_MARGIN` · B_basket | `built` |
| −`TOLERANCE` · B_basket ≤ z* < `EDGE_MARGIN` · B_basket, every instrument hard-capped, and at least `POS_SHARE_MIN` of the thesis scenarios have positive payoff | `built`, flagged `capped_tolerance` |
| Otherwise | `unbuildable`, with the first reason the post-solve ladder finds |

**Post-solve ladder**, run in a fixed order so the reason is reproducible. An infeasible programme is diagnosed by adding the constraint families back one at a time, in this order, and naming the first that makes it infeasible:
1. `liquidity`: the liquidity caps can't absorb the committed budget.
2. `excluded_loss`: no weights keep the loss in excluded reachable outcomes inside its floor.
3. `story_rank_deficient`: the hedge constraints can't be met with the instruments available.

A feasible programme below the decision thresholds is diagnosed in turn:
4. `no_opposite`: no two instruments have payoffs that move in opposite directions across the thesis scenarios or the tide, so nothing can hedge anything.
5. `costs`: re-solved at zero cost, it would be built.
6. `bands_too_wide`: re-solved at band centres, it would be built.
7. `no_edge`: none of the above. The reachable set simply doesn't pay at these prices.

On a backfilled round where the deciding instruments are `modelled` (§19.2), `no_edge` and `costs` are reported as `modelled_prices`: a model's prices can't tell us what the market would have charged.

The reason histogram across rounds is the new wall map. If it says `no_opposite` everywhere, K8 already said so and structural hedging is dead.

#### 20.6 Instruments and costs

| Instrument | Cap class | Maximum loss per unit | Free source today |
|---|---|---|---|
| Bought call or put, debit spread | hard | Premium | Yahoo current chains; history `modelled` (§19.2) |
| Credit spread, condor | hard | Width − credit | Same |
| Bought straddle or strangle | hard | Premium | Same |
| Bought event contract (YES or NO) | hard | Price paid | Prediction-market quotes via the data product (`quote`) |
| Bought credit protection | hard | Premium over the life | `not_covered` (no free source) |
| Stock or ETF, long or short, under a stop | stress | Stress quantile over the window (`STRESS_QUANTILE`), enforced by the stop | Yahoo, via the vintage store |
| Stock pair, futures spread, under a stop | stress | Same | Same |
| Bond, long | stress | Same | `instrument_map` identifies it; quotes are mostly `not_covered` |
| Short with no stop, naked sold option | uncapped | — | **Never held.** Converted to a capped form (a bought put for a short, a spread for a sold option) or dropped |

- **Stress-capped instruments need a fully documented ACK.** On a switch-derived ACK, only hard-capped instruments are allowed (§4).
- **Every instrument records `listed_from`.** One not listed before T_seg isn't in reach for that segment.
- **Costs:** half the quoted spread (or `SPREAD_FALLBACK` by instrument kind when no quote exists), venue fees, borrow at `BORROW_RATE` unless quoted, and slippage proportional to size over average daily volume.
- **The turnover floor** `TURNOVER_FLOOR_USD` *(v15)* still applies to stock and ETF instruments.

#### 20.7 Budgets and sizing

- **Per round:** `LOSS_BUDGET_PER_ROUND`. **Per tide:** `LOSS_CAP_PER_TIDE`, shared by every basket and every walk segment under that tide, whatever round it belongs to.
- **Share per basket:** B_basket = min(the round's **remaining** budget ÷ the number of the segment's ACKs that pass the pre-solve gates, the tide's remaining cap). Both remainders are read at lock, from baskets already locked (in lock order), and recorded in the lock manifest, so sizing is reproducible and a walk of k segments can't spend the round budget k times.
- **Release:** a basket's committed maximum loss stays committed until it closes. On close, it is released, less any realised loss.
- **Switch-derived ACKs** get `SWITCH_BUDGET_FRACTION` of that share.
- **Operator term:** below its appetite, B_basket is multiplied by operator ÷ appetite for the call shapes the basket depends on. The operator's known weaknesses shrink size; they never veto.
- **Degrees:** instruments at depth > 1 enter only while their response bands stay inside `BAND_WIDTH_MAX` × their centre. Beyond that, attenuation has made them noise.
### 21. The veto set, per effect `[v16 B]` + `[gate]`

**Vetoes run per effect**, reading the transform table. In v15 the eliminators run per leg (`surviving.evaluate_leg` *(v15)*), `surviving_risk.effect_id` is never written, and per-effect elimination is manual (RECONCILIATION #32). v16 moves them to effects and **splits the v15 eliminator list in two**: the structural vetoes stay; everything that was really a risk judgment becomes a construction input.

**Stay as vetoes** (anchors: the structure says it can't happen or can't be seen):

| Veto | v15 source | Fires when |
|---|---|---|
| `no_path` | `no_path`, and `effects.compose`'s refusal | Either condition: (a) no transmitting entry exists for `(effect kind, relation)`. v15's `effects.compose` raises an error on a zero transform; v16 writes the refused child as an effect with `vetoed_by = no_path`, so the veto is recorded and counted. `no_path` on a `cost` effect is a different question from `no_path` on an `obligation` effect through the same relation. (b) v15's admissibility test, kept: an effect at degree ≥ 2 with no cited mechanism and no stated position |
| `signs_held` | `self_hedged` | Both signs held across the holder's positions on the node, so no net direction for that effect |
| `absorbed_by_slack` | `slack` (`SLACK_WORDS` in node facts) | The receiving market has slack **for that effect**, so it is absorbed (*a cut into a glut is silent*). The v15 word match is replaced by a stated slack fact with evidence |
| `no_sink` | — (new) | The effect has nowhere to land, for that effect kind (theory v1's *nothing to transmit into*). The opposite condition to `absorbed_by_slack`; see §5 and the open call in §34 |
| `below_band` | `tide` (move/band < `TIDE_RATIO_MIN`) | The expected move is below the pre-T_seg noise band of the instrument's **hedged residual** (tide-only; §20). v15 compared against the raw price band, which counted tide as noise the basket would now hedge away. This is the only veto that reads prices (§12) |

**Move to construction inputs** (they change *how* to hold, not *whether* the effect exists):

| v15 eliminator | Why it isn't a veto | Where it goes now |
|---|---|---|
| `traversed` (Q1a fail, prior traversal) | A traversed channel is priced, not impossible | Pricedness: the story set and S⊥ (§20.2, §20.4) |
| `weather` (Q1b fail, leg on the event node) | Weather is a priced recurring story | An active parallel story; hedged |
| `immaterial_position` (share < `POSITION_SHARE_FLOOR`) | Small stake is small payoff, not no payoff | Stake, which sets the response band's centre; the degree rule in §20.7 drops noise |
| `already_priced` (22 Sep draft) | Priced is a matter of degree | ρ and the priced test (§20.4) |
| The tradability gate (`TRADABILITY_GATE_KEYS`, `computed_gate`) | No instrument on this holder isn't no trade on this structure | Instrument availability in construction (§20.6); `no_opposite` in the diagnostic ladder |

- A veto that can't be evaluated is **absent**: the effect goes forward, and the unknown widens its response band (§8).
- A veto records the anchor, its inputs and the evidence ids.
- Report `veto_rate` per depth and per effect kind. A rate of 0.0 on a fanned-out DAG is a defect signal, not a finding.
- **Effect states** after the veto set: `vetoed` or `forward`. **Basket states** after construction: `built`, `unbuildable` (with reason), `vetoed` (every effect the ACK's basket would hold was vetoed), `declined`, `held`, `closed`. The v15 statuses `eliminated`, `unchecked`, `gate_fail`, `armed_dated` and `gate_pass_undated` are kept on v15 rows as history and are no longer written.

### 22. ACKs: representation, derivation, reach, walk, exit `[carried]` + `[fold]` + `[gate]`

#### 22.1 What exists `[carried, v15]`

- **`ack_nodes`** *(v15)*: `ack_kind` is `scheduled` (must have `due_at`) or `forced` (must have `obligation` and must not have a date). Also `attention`, `standing`, `parent_ack_id`, `participant_class`.
- **`ack_firings`** *(v15)*: `delivered`, `delivered_fact`, `implied`, `gap`, `opens_effect_ids`, `kills_effect_ids`, and `successor_ack_ids`, which must be named at firing. A non-delivering firing prunes its branch and forbids successors.
- **Scheduled ACKs** are built from the calendar for holders with positions on the node (`nomad_ack_build_standing` *(v15)*). **The catalyst-class predicate requires the statement to concern the node**: a listed holder's results date is a catalyst only if the node is material to it; otherwise it's a tide (v3).
- **The walk** (`walk.py` *(v15)*): `lock_segment`, `advance` (refuses unfired ACKs), `convergence` (`CONVERGENCE_THRESHOLD` 0.5), `prune`.
- **Forced ACKs carry no date.** `acks.add` *(v15)* refuses a `due_at` on a forced ACK, because a public date is what makes a fact scheduled. v16 keeps that and adds a **window** (`window_to`, `window_basis`, `window_ratified`): the latest date by which the obligation must be met, from a statute, a ratified procedural chain, or the operator, and capped at `DUE_AT_MAX_DAYS` after `event_date` (v15's cap on every call's `due_at`) when nothing else sets it. A window is not a date the fact is expected; it bounds exits and instrument expiries.
- **Forced-ACK timing** comes from procedural chains (§25.5) where a process type matches; otherwise it's `unknown_forced`, and no date is invented.

#### 22.2 Derivation `[gate]`

**Obligation templates** are library rules of `kind = obligation` (§3). Each one names:
- the roles in the conjunction (supplier, buyer, carrier, regulator, …);
- the condition on each role, as a test on a registered position attribute (`share ≥ x`, `substitutability = low`, `inventory_days < n`, `contract_type = offtake`) or a bound (`substitute_lead_days > window`);
- the notice kind it forces, its carrier kinds, and its window rule (statute, procedural chain, or none). Derived ACKs are always forced;
- what it forbids: *no notice of this kind without this conjunction*.

**Algorithm** (`derive.py`), run at reveal and again at every ACK firing, each time for the current segment's clock T_seg:

```
for each template T applicable to the node type:
  for each binding of T's roles to holders/assets with positions on the node or its neighbours:
    for each condition c in T:
      state(c) = true      if a position or bound row with knowable_from ≤ T_seg documents it
               = false     if such a row documents its negation
               = unknown   otherwise
    result = forced  if every condition is true
           = switch  if none is false and some are unknown   → fetch_list = the unknown conditions
           = none    if any is false
    write ack_derivations row; if forced or switch, write an ack_nodes candidate (origin = derived)
```

- **Bound conditions** read the `bounds` store as of T_seg, the same way.
- **Only documented positions count.** A position with `confidence = inferred` or `implicit` *(v15)*, or with a NULL `knowable_from`, is `unknown` for derivation, never `true`. After an ACK fires, the delivered fact counts from the next segment on, because its `knowable_from` is that segment's clock.
- **Bindings are bounded** by `DERIVATION_BINDINGS_MAX` (appetite, its own constant; the effect frontier bound is a different limit). A template whose bindings exceed it is reported as `bindings_exceeded`, never silently truncated.
- **The operator ratifies** every candidate: `ratified` or `dropped`, with a reason. A switch is ratified with `is_switch = true`; its fetch list joins the fetch queue, and it stops being a switch if the fetches turn every unknown true.
- **Derived ACKs are forced ACKs.** They carry `obligation`, no date, and a window. A switch is stored the same way with `is_switch = true`: it is the one kind of forced ACK whose conditions are not all documented, and while the flag is set its baskets may use hard-capped instruments only, at the switch budget (§20.6, §20.7).

#### 22.3 Outcome vocabularies and reach `[gate]`

**Vocabularies are authored per notice kind** (restart statement, force-majeure declaration, regulatory decision, allocation notice, incident report, …), not per `ack_kind`, which only says scheduled or forced. They are stored in `outcome_vocabs`. Each has a small number of typed outcomes, and each outcome lists the conditions it `needs`. Every vocabulary also names `other`, whose falsifier is "none of the named outcomes". **`other` is outside the closed world:** it is never in R, it needs no exclusion citation, the basket never covers it, and if it happens it is booked as a piano.

**Reach** (`reach.py`), per named outcome ω, reading positions, bounds and ratified procedural states as of T_seg:
- `cut` if a need of ω is documented false before the window closes: by a structural anchor (`no_path`, `signs_held`, `absorbed_by_slack`, `no_sink`; never the price-reading `below_band`), a bound (a parts or rebuild lead time longer than the window, a statutory minimum duration), an inventory figure in a position, or a zero-count transition from an **operator-ratified** procedural state. A model's unratified reading of a process state never cuts. The cutting fact and evidence are recorded.
- `kept_unknown` if some need is unknown. **Unknown keeps an outcome in.**
- `reachable` otherwise.

**Thesis.** The operator marks `in_thesis` for the outcomes the thesis keeps, and each outcome it excludes must cite the positions or rules that exclude it. An exclusion resting on an unknown is refused at lock and becomes a switch.

**Registered as a map call.** Each ratified ACK's vocabulary is also a `map` call with covering branches (`other` included), so each ACK's outcome is scored like any other call, and the library learns from it. Its `due_at` is the ACK's `due_at` (scheduled) or `window_to` (forced).

#### 22.4 The walk, recomputed at each firing `[carried]` + `[gate]`

When an ACK fires:
1. Record `ack_fired` with the delivered fact and its **`outcome_id`** from the vocabulary.
2. Name successors at firing, as v15 requires (`successor_acks` on `nomad_ack_fire` *(v15)*; a non-delivering firing may not name any).
3. **Update positions** that the delivered fact changes: new append-only rows, `supersedes` set.
4. **Re-derive** (§22.2). New conjunctions can become true now; their ACKs are the next step of the walk.
5. **Re-estimate** loadings, re-class stories, re-check junctions, recompute S⊥ (§20.2–20.4).
6. **Test exits** for every open basket (§22.5).
7. **Lock the next segment** with its clock (the firing's `knowable_from`), its own calls (`predictions.segment_id`), `due_at`s, derived ACKs, baskets, lock manifest and lock hash. Segments inherit the round's tags and tide.

Stake created by a firing ACK can't have been priced before the firing, because the fact didn't exist to price.

#### 22.5 Exit `[carried]` + `[gate]`

A basket closes at the first of:
- **S⊥ recovered:** the span test or the price test (§20.4);
- **the first attention ACK after the structural ACK** (theory v2; `nomad_exit_ack` *(v15)*);
- **the end of the ACK window** (for a forced ACK, `window_to`; so every basket has an exit date, and every round can reach `scored`);
- **a stop,** for stress-capped positions (a gap through it is a leak).

The exit reason is written to `paper_exits` (§19.2).

### 23. Decision-model runtime (`decider`) `[fold]`

#### 23.1 Protocol

Both Laya and Jev use the same three primitives, so adapters are thin:
- **`noul`** — a yes/no probability.
- **`choice`** — one of a fixed set, with a full distribution.
- **`score`** — ordered, situation-described levels, with a full distribution.

```python
class DecisionModel(Protocol):
    model_id: str
    checkpoint: str                     # content hash of weights, or pinned remote version id
    trained_through: datetime           # REQUIRED here; see 23.3.
    # The contract's ModelIdentity allows None (unknown). `decider` does not:
    # an adapter resolves None to the model's public release date at registration,
    # so no job ever runs against an unknown cutoff.
    trained_through_basis: str          # written justification
    max_state_tokens: int
    max_options: int
    languages: frozenset[str] | None    # None = multilingual

    def predict(self, state: dict | str, questions: dict) -> Answers: ...
    # Answers carry the FULL distribution per question, raw (pre-temperature)
    # and calibrated (post-temperature), plus the model's confidence field if any.
```

#### 23.2 Recording and replay

- Every call is written to `decision_calls`, keyed by `(input_hash, question_set_hash, checkpoint)`, before its result is used.
- A replay reads the table and never calls the model.
- A call whose key already exists returns the recorded answer. Reproduction is not a new test.

#### 23.3 The model time wall

- `trained_through` is the latest `knowable_at` of **anything** the checkpoint learned from, including base pretraining.
- **For base checkpoints** it is declared from the model card with a written `trained_through_basis`, e.g. "backbone pretraining cutoff X; head trained on synthetic workflows with no dated world content". If it can't be justified, the model's public release date stands in.
- **For fine-tuned checkpoints** it is the max of the base value and every training label's `label_knowable_at` and input `knowable_at`.
- **`decider` refuses** a call tagged with `about_time = T` when `trained_through > T`, unless the job is flagged `live_only` and the round is live.
- Every job states its `about_time`, which for round work is the `event_date`.

#### 23.4 Roles and jobs

| Role | Model | Jobs | Status in v16 |
|---|---|---|---|
| `reader` | Laya, fine-tuned (§24) | `intake_reader`, `notice_watch`, `procedural_state`, `settling_doc`, `link_transmission` (wiring and probes) | Active in shadow; each job promotes on its own gate |
| `reader_base` | Laya base (`laya`, `laya-multilingual`) | Baseline for every promotion gate; fallback | Active as baseline |
| `crowd_mirror` | **Empty.** Reserved for a commoditised frontier-class decision model (Jev) | `obviousness` | **Held**; K3 deferred |
| `attachment` (in `dataprod`) | Laya | `entity_link`, `event_cluster`, `category`, `extraction` | Per Section G |

**What decider output may never enter** `[gate]`: derivation conditions (§22.2), reachable and thesis sets (§22.3), loadings, angle classes, junction treatments, S⊥ (§20.2–20.4), or construction weights (§20.5). It may propose candidate stories, candidate adjacent readings and candidate obligation templates, each of which the operator authors or drops.

**Job registry fields:** `job`, `role`, `question_set` (versioned), `about_time_rule`, `live_only`, `mode` (`shadow`/`active`), `promotion_gate`.

#### 23.5 Laya specifics

These are from the model card, confirmed on 2026-09-22; re-check them when the package updates.

| Checkpoint | Backbone | Params | Context | Notes |
|---|---|---|---|---|
| `convaiinnovations/laya` (root) | ModernBERT-large | 421M | 512 tokens (option budget 192, about 320 for state) | English only. **Confidently wrong on non-Latin scripts** (card: 0.000 accuracy at 0.952 confidence on Khmer) |
| `laya` subfolder `multilingual` | mmBERT-base | 322M | 1024 by default (option budget 256, about 768 for state); the encoder supports up to 8,192 | 100+ languages; faster |
| `laya` subfolder `typed-decisions` | ModernBERT-large | 421M | 1024 | Fine-tuned on four synthetic workflows |

**Usage rules:**
- **Install and load.** `pip install laya`; `laya.load(repo, subfolder=...)`, or `Router(preload=True)` for language routing. Set `USE_TF=0` if loading hangs.
- **Routing is mandatory** for mixed-language feeds.
- **Long documents are filtered first.** Split into chunks, ask a relevance `noul` per chunk, and send only relevant chunks to the real questions. Combine across chunks in code (e.g. max for notice detection).
- **More than 20 options:** use a coarse-to-fine two-step choice, or raise `head_max_len` and `max_len` and re-validate.
- **Ordinal `score` is the weakest primitive.** Read shapes, never means (§25.2).
- **Ships overconfident.** Temperature is refit per `(question type, option count)` on our own calibration split before any probability is read (§24.4).
- **Inference runs on CPU.** Preloaded, the card reports about 193–464 ms per call; fan out all questions for one state in a single call.

#### 23.6 The Jev slot (held)

When added, Jev is a `DecisionModel` adapter with:
- `checkpoint` = the pinned version id (e.g. `jev-1.13.0`), never an alias;
- `trained_through` = its release date unless TypeSafe publishes a cutoff, so every clean-window backfilled use is refused automatically;
- `max_state_tokens` of about 32k and `max_options` of 255.

**Its only role is `crowd_mirror`.** It never settles an absence claim, never does dates or counts, and never feeds weight.

Before any Jev output is used as a training label for Laya (`label_source = teacher`), check TypeSafe's terms on training with outputs. Teacher labels may train proposal-tier jobs only and never enter an evaluation set.

### 24. Laya fine-tuning pipeline `[fold]`

#### 24.1 Tasks

| Task | Primitive(s) | State | Label sources |
|---|---|---|---|
| `intake_reader` | `noul` Q3 (world event, not a price move); `choice` event category; `noul` Q6 (single event); `choice` size-band hint | Title, lede, outlet class | `human` (intake confirmations and rejections with reasons); `structured` (EDGAR 8-K `items` as free category labels) |
| `notice_watch` | `choice` notice type (FM / restart / allocation / regulator answer / none); `noul` "concerns node X" given a node description | Item title and lede, or the relevant chunk | `resolved` (carriers that spoke, from the ledger); `human` |
| `procedural_state` | `choice` over the process type's states | Document title, lede or chunk | `structured` (docket metadata: Federal Register document types, trade-remedy case stages) |
| `settling_doc` | `choice` document type; `noul` publication obliged | Link description plus node context | `human` (operator-ratified ACKs); `resolved` |
| `link_transmission` | `score` over situation-described levels | Parent piece, relation, candidate child, path so far, optionally the settling-document chunk | `resolved` (effects that transmitted or not); `human` (second scorer). Few labels: expect it to promote last |
| `relevance_chunk` | `noul` "relevant to question Q" | Chunk | `structured` (derived from which chunk held the answer); `human` |

#### 24.2 Labels

- **Every label** carries `label_source` and `label_knowable_at` — when the label itself became knowable, e.g. the human decision date or the resolution date, **not** the event date.
- **Evaluation sets use only `human`, `resolved` and `structured` labels.**
- `operator` and `teacher` labels may train proposal-tier jobs and never evaluate.
- **Label snapshots are frozen by content hash.** The hash goes into the checkpoint's registry row.

#### 24.3 Splits and training

- **Split by time, never at random.** Train on `label_knowable_at < t1`, calibrate on `[t1, t2)`, test on `[t2, t3)`.
- **Base model:** multilingual for any task that sees non-English feeds; English root where inputs are English-only and length fits.
- **Starting point:** the published fine-tuning notebook (`laya_finetune_typed_decisions_2xT4_kaggle.ipynb`). Confirm its objective before adapting; the model family was trained against strictly proper scoring rules, and that property should survive fine-tuning.
- **Compute:** free Kaggle GPUs or a short rented GPU. Inference stays on CPU.
- **Cadence:** a new checkpoint per `retrain_interval` or per `retrain_min_new_labels` (both appetite).
- **Old checkpoints are never deleted.** Backfilled rounds need the checkpoint that was clean for their date.

#### 24.4 Calibration

Fit one temperature per `(question type, option count)` on the calibration split. Report ECE and Brier before and after, per task. Temperatures are stored in the registry row and applied by `decider`, never by the caller.

#### 24.5 Evaluation

Per task, on the test split:
- accuracy per primitive;
- Brier;
- ECE;
- **recall at the operating threshold** (for filters, missing a true item is the expensive error);
- the confusion on typed-gap-like cases ("can't tell" answers).

Compare against `reader_base` (zero-shot base Laya) and against the rule baseline where one exists.

#### 24.6 Promotion gate (per job)

A checkpoint moves `candidate → shadow → active` for a job only if all three hold:
1. It beats `reader_base` and the incumbent on the time-held-out test split on the job's primary metric, by the margin set as appetite.
2. Its calibration after temperature is within the ECE ceiling (appetite).
3. In shadow on live traffic for `shadow_min_items` (appetite), its decisions match the human's on the sample at or above the job's recall floor.

Until then its output is logged and never used. `intake_reader` is gated by K1.

### 25. Fold mechanisms — technical `[fold]`

#### 25.1 Wiring (`nomad_wire`)

- **Input:** the round's pieces. For each parent piece, the candidate children are all pieces at the next depth whose `(parent kind, relation)` has a transmitting entry in the transform table.
- **One decider call per parent**, fanned out: one `link_transmission` question per candidate child. The state holds the parent piece, the path so far and the node context (short and structured, to fit Laya's budget).
- **Chain building:** depth by depth, keep the top `k` children per parent plus a `bottom_slice` drawn from the lowest-ranked (both appetite). The depth limit is attenuation.
- **Output:** `chains` with `attention_rank`. Chains outside `k` and the bottom slice are `unexamined`.
- **Never used** as support, weight, veto or construction input.

#### 25.2 Spread probes (`nomad_probe`)

- For each ranked link whose settling document has been fetched pre-lock: ask `link_transmission` without the document, then with it.
- Store both distributions, then classify:

| Reading | Without the document | With the document |
|---|---|---|
| `ignorance` | Wide | Collapses |
| `mechanical` | Tight and high | Tight and high |
| `graded` | Any | One peak in the middle |
| `switch` | Any | Mass at both ends |

- **Bimodality thresholds** (end mass and middle mass) are appetite.
- **Paraphrase stability:** every `switch` is re-asked with a second, independently worded question set. It passes only if both read `switch`.
- **Rules:**
  - Graded scale levels describe situations, never degrees.
  - Read shape, never the mean. Levels aren't numerically calibrated against each other, and magnitudes come from documents.
  - The gradient along a chain is **where the shape changes**, never a product.
  - The with/without comparison is the load-bearing signal, because it compares the model with itself.

#### 25.3 ACK locator (`nomad_ack_candidates`)

1. Take paraphrase-stable switches.
2. Run `settling_doc` on each: the document type, and `noul` obliged.
3. Look up the carrier in the registry. If there is no fetch path, record `not_covered`; the switch is **kept**, never dropped.
4. Assign timing:
   - `scheduled` → the calendar;
   - `forced` → the procedural chain (§25.5), or `unknown_forced`;
   - `discretionary` → no ACK, recorded as conditioning.
5. Return candidates with `origin = locator`. **The operator ratifies each one**, through the same path as derived ACKs (§22.2). A locator candidate is never ratified as a documented forced ACK on the model's reading: it needs the obligation documented, or it is ratified as a switch (`is_switch`, §22.2).

#### 25.4 Notice watch

- **Post-lock**, every new recorded item from the relevant carriers is run through `notice_watch` against the open calls' nodes.
- **A flag creates an operator task.** The fetched document, read by the operator, is what fires an ACK or resolves a call.
- **Never resolves an absence claim.** Silence is established only by reading the carrier in full.
- **Flag budget per day** is appetite.
- **Metrics:** flags raised, flags confirmed, and recall measured against carriers read in full (K6).

#### 25.5 Procedural-actor chains

- **Per process type:** states, allowed transitions, and statutory windows.
- **Counted from bulk dockets in code:** transition counts, and a time-to-next-state distribution. Use an empirical CDF with right-censoring for open cases, and record `counted_through`.
- **Laya's `procedural_state`** proposes a state for each new document, written to `procedural_states` unratified. The operator ratifies it. Only a ratified state sets a timing window or cuts an outcome in `reach` (§22.3).
- **Output:** proposed `due_at` anchors and forced-ACK timing windows. **Every model-derived or docket-derived date is a proposal the operator ratifies before it becomes a call's `due_at`**, on the same footing as §25.3 — `due_at` decides whether an absence claim resolves `hit`, so an unratified date reaches scoring.
- **The model time wall applies to the counts too.** When used for a round, only cases whose transitions were knowable by `event_date` count.
- **Ratified windows also set instrument expiries** `[gate]`. A dated instrument must outlive the window at the `EXPIRY_QUANTILE` of the chain's time distribution (§7.2). An unratified window sets nothing.

### 26. Data-product integration `[fold]` + `[gate]`

- Nomad consumes `dataprod` through `contract>=0.2,<0.3`.
- **The adapter maps the contract's `knowable_at` to the harness's `knowable_from`** (§9). Inside the harness `knowable_from` is the only name; `decider` and the data product use `knowable_at`; the adapter is where the two meet.
- **Pre-lock**, the MCP session pins `as_of = event_date`, so the product refuses later reads. Nomad's harness separately refuses any read past its own clock. **Both guards run.**

**Nomad's degradation table** (its own, keyed by `contract.Capability`):

| Capability missing | Consequence in Nomad |
|---|---|
| `KNOWABLE_AT` | **Refuse** to run |
| `TYPED_STATUS` | Run; gap reasons collapse to `not_covered`; the round is flagged `gaps_untyped` |
| `REVISION_CHAINS` | Run; the round is marked contaminated for any term reading restatable values |
| `SURVIVORSHIP` | Run; the noise baseline and peer control are marked contaminated |
| `RECORDING` | Enumeration falls back to manual (`enumeration_manual`); Q9 cannot pass mechanically; point-in-time search is unavailable |
| `ATTACHMENTS` | Entity links are done in-harness; the event spine is unavailable, so Q1a uses window search only |
| `CROSS_REFERENCE` | No `/relate`; no event spine |
| `LINEAGE_COUPLING` | Independence across carriers is over-estimated; the round is flagged |

**What Nomad reads from the product:**
- recorded feeds (enumeration, notice watch);
- `filing_item`, `announcement` and `regulatory_notice` records;
- `ownership_edge` and `instrument_map` (the census, K7; `expression` for bonds);
- `customer_disclosure` (positions candidates for the names book, confirmed by the operator);
- prices (noise baseline and peer control);
- `scheduled_fact`;
- `quote` (the prediction-market benchmark);
- the event spine and `first_knowable_at` (Q1a, and latency).

**The point-in-time fetcher is kept.** `nomad_pit_fetch(source, target, as_of, reason)` *(v15)* resolves a named target through Wayback or Wikipedia revisions (`source` ∈ `wayback`, `wikipedia`, `auto`), and refuses anything without a resolvable as-of date. Filings by date come through the data product, not the fetcher. The product's recorded search covers what the fetcher can't — search — for windows after recording began.

**The price vintage store** `[gate]`. Every price the harness reads for a loading, a band, S⊥, an entry, a mark or an exit comes from a stored vintage (`price_vintages`, §18.3), never from a live read used directly. Two rules come from Ohmni's report 005:
- **Hash the decompressed payload,** not the compressed transfer. The freeze broke on compression differences, not content.
- **Verify the payload against its own metadata** on every fetch. Yahoo's price metadata drifts between fetches. A disagreement with an earlier vintage is stored as a new vintage with `drift_of` set, and reported. The harness never substitutes silently.

Until the data product serves prices, `prices.py` *(v15)* fetches from Yahoo and writes each response into the vintage store before any computation reads it. Static `FX_TO_USD` *(v15)* holds rates dated 2026-09-01, so every round with an earlier event date reads FX from after its own event. It is replaced by FX vintages dated before each segment's clock.

**Instrument data, honestly** `[gate]`:

| Instrument | History available free | Consequence |
|---|---|---|
| Stocks, ETFs, indices | Yes (Yahoo daily) | Live and backfilled rounds |
| Listed options | Current chains only | Live rounds record chains into the vintage store from lock onward. Backfilled option legs are `modelled` and excluded from K13 |
| Event contracts | Yes, from venue APIs where the data product records them (`quote`) | Live and backfilled rounds where recorded |
| Bonds, credit protection | Mostly no | `not_covered`; the census (K7) still identifies them, and they are reported as instruments nobody could price |
| Commodity futures | Front-month daily for some (Yahoo), no curve | Stress-capped spreads on live rounds only |

A paid source is added only when a measured block names it (§12: spend follows a measured block).

### 27. MCP tool surface `[carried]` + `[fold]` + `[gate]`

All tools carry the `nomad_` prefix. The 146 v15 tools stay under their current names; v16 changes the behaviour of a few and adds the rest.

#### 27.1 Kept from v15 *(v15)*

| Group | Tools |
|---|---|
| Intake | `event_window`, `submit_event`, `feeds`, `feed_add`, `enumerate`, `select_next`, `decide`, `strata`, `intake_dry_run`, `intake_check`, `reject_event`, `selection_window`, `selector_clear`, `round_tags`, `node_history`, `confirm_event_date`, `reveal_event`, `node_context`, `t0_submit_candidate`, `t0_count` |
| Lifecycle | `touched_set`, `lock_predictions`, `open_retrieval`, `open_scoring`, `close_scoring`, `firewall_violation`, `close_round`, `void_round`, `round_status`, `round_note`, `export_round`, `criteria_supersede`, `calls_due`, `settings`, `model_cutoffs`, `verify_chain` |
| Evidence | `add_evidence(_batch)`, `pit_fetch(es)`, `snapshot`, `snapshot_targets`, `snapshot_target_add`, `snapshot_run` |
| Scoring | `score_call`, `score_batch`, `score_round`, `resolution_supersede`, `second_scorer_view`, `second_score`, `second_scorer_batch`, `score_disputes`, `disputes`, `calibration`, `scorer_bias`, `replay`, `replay_stats`, `programme_stats` |
| Library | `library_query`, `library_propose`, `library_set_carries`, `library_retire`, `base_rates`, `base_rate_add`, `precedent` |
| Names and positions | `holder_upsert`, `resolve`, `orphans`, `position_add`, `positions_on_node`, `hypothesis_open`, `hypothesis_check`, `hypothesis_schedule`, `hypotheses_due`, `node_fact_add`, `node_facts`, `ingest_target_add`, `ingest_targets`, `ingest_target_close` |
| Carriers and schedule | `carrier_check`, `carrier_upsert`, `carriers`, `carrier_path_set`, `carrier_probe`, `scheduled_add`, `ingest_scheduled`, `catalyst_check`, `catalyst_link`, `mechanical_add`, `scheduled_backfill` |
| Gate and risk | `predicate_list`, `predicate_check`, `risk_rules`, `risk_rule_add`, `set_preconditions`, `practice_date_rules`, `grid`, `surviving_risk`, `operator_risk`, `null_breakdown`, `annotate_leg`, `generate_legs`, `generate_space`, `adjacent`, `glossary`, `index`, `log_move` |
| Prices and basket | `price_observe`, `price_backfill`, `exposure`, `event_basket`, `shared_factors`, `synthetic_rules`, `synthetic_build`, `synthetic_exposure_declare`, `attribute_coverage` |
| Effects | `effect_root`, `effect_compose`, `effect_reroot`, `effect_eliminate`, `effects`, `effect_width`, `net_direction`, `effect_migrate`, `relation_add`, `transforms`, `transform_propose`, `node_kind`, `edge_traversal`, `effect_support`, `implicit_position`, `bridge_paths` |
| ACKs and walk | `ack_add`, `ack_graph`, `ack_build_standing`, `ack_calendar`, `ack_fire`, `segment_lock`, `walk_advance`, `convergence`, `prune`, `walk_report`, `contradictions`, `contradiction_record`, `common_set_anchors`, `exit_ack` |

**Behaviour changes in v16:**

| Tool | Change |
|---|---|
| `nomad_lock_predictions` | Runs `assess_round` once; refuses a round or segment that is already locked; writes the lock manifest; freezes and hashes every emergent object; writes paper entries (§14) |
| `nomad_surviving_risk` | Per effect; runs the veto set of §21; writes typed gaps and bases |
| `nomad_ack_fire` | Requires `outcome_id` and the fact's `knowable_from` when delivered; triggers the recompute of §22.4 |
| `nomad_segment_lock` | Full lock behaviour for later segments (§14), legal in `open` and `partially_scored` |
| `nomad_ack_add` | Accepts `origin`, `derivation_id`, `notice_kind` and a window; still refuses a `due_at` on a forced ACK; derived candidates arrive through `nomad_derive_acks` |
| `nomad_effect_compose` | A child refused for a zero transform is written as an effect vetoed `no_path` instead of only raising (§21). Refusals for a non-transmitting relation or the frontier bound still raise |
| `nomad_position_add` | Accepts any attribute registered in `position_attributes`, with a numeric value where the attribute is numeric |
| `nomad_score_batch`, `nomad_close_round` (scoring) | Resolutions carry `carrier_state`; an expired absence call resolves `unverified` unless its carrier was read in full (§15) |
| `nomad_library_propose` | Accepts `kind = obligation` with a template body (§3, §22.2) |
| `nomad_price_observe`, `nomad_price_backfill` | Read and write through the vintage store (§26) |
| `nomad_event_basket` | Unchanged as the v15 leg view; adds a link to the round's constructed baskets |
| `nomad_predicate_check`, `nomad_grid` | Arming and tradability keys are read-only history |
| `nomad_programme_stats` | Adds tide counts, the unbuildable-reason histogram and paper results |

#### 27.2 New from the fold

| Tool | Purpose |
|---|---|
| `nomad_library_as_of(date)` | Rules and weights valid at a date (§9) |
| `nomad_tides` / `nomad_tide_declare` | The tide registry (§19.1) |
| `nomad_operator_manifest(round_id)` | Model, runtime, cutoff, hook verification (§28); a round without one can't lock |
| `nomad_wire(round_id)` | Wiring, shadow or active per job mode (§25.1) |
| `nomad_probe(round_id, link_ids)` | Spread probes (§25.2) |
| `nomad_ack_candidates(round_id)` | Locator output (§25.3) |
| `nomad_notice_flags()` | Notice-watch queue (§25.4) |
| `nomad_census(holder_id)` | Ownership and instrument census (K7) |
| `nomad_wall_map(scope)`, `nomad_computability(scope)`, `nomad_decider_report(job)` | Reports (§29) |

#### 27.3 New from the gate

| Tool | Purpose |
|---|---|
| `nomad_templates(node_type)` | Obligation templates applicable to a node type |
| `nomad_position_attribute_add(...)` / `nomad_bound_add(...)` | Register a position attribute; author a bound (§18.3) |
| `nomad_procedural_ratify(state_id, decision)` | Ratify a proposed procedural state (§25.5) |
| `nomad_ack_window(ack_id, window_to, basis)` | Set or ratify a forced ACK's window (§22.1) |
| `nomad_derive_acks(round_id)` | Run derivation (§22.2); returns forced, switch and none results with fetch lists |
| `nomad_ack_ratify(ack_id, decision, reason)` | Ratify or drop a derived or locator candidate |
| `nomad_outcome_vocab_add(notice_kind, outcomes)` | Author a vocabulary (`other` is added automatically) |
| `nomad_outcomes(ack_id)` / `nomad_reachable(ack_id)` | The vocabulary, and the cut to the reachable set with evidence (§22.3) |
| `nomad_thesis_set(ack_id, outcomes, basis)` | The operator's thesis set; refused if an exclusion rests on an unknown |
| `nomad_story_add(label, path, proxy or rule)` / `nomad_stories(round_id)` | Story registry (§20.2) |
| `nomad_loadings(round_id)` | Estimate or construct loadings; class by angle |
| `nomad_junctions(round_id)` / `nomad_junction_treat(junction_id, treatment)` | Flag and treat junctions (§20.3) |
| `nomad_s_perp(round_id)` | S⊥, ρ, visibility (§20.4) |
| `nomad_instruments(holder_id)` / `nomad_instrument_add(...)` | Instrument map with cap classes (§20.6) |
| `nomad_opposite_census(scope)` | Listed holders on both sides of each node (K8) |
| `nomad_construct(round_id)` | Build one basket per ratified ACK (§20.5) |
| `nomad_basket_decline(basket_id, reason)` | Operator declines a built basket; still booked |
| `nomad_paper_book(scope)`, `nomad_paper_mark(...)`, `nomad_paper_exit(...)` | The paper book (§19.2) |
| `nomad_pianos(scope)` | The leak log |
| `nomad_rebuild(round_id)` | Re-run a past round under v16 without changing its v15 record (K9) |

**Hooks** (operator runtime):
- **Pre-lock:** deny live web search and fetch tools; allow `nomad_*` and `dp_*` (pinned).
- **Post-lock:** allow live web.

The hook, not the operator's discipline, is the control. Verify it is live at session start **by attempting a denied call and checking that it is refused**. Earlier sessions found that a network control that looked in force wasn't the one actually enforcing anything; the hook was.

### 28. Operator runtime `[new]`

**Runtimes supported** (the harness is operator-agnostic because it is an MCP server):
- Claude Code;
- Hermes Agent (`claude-subscription-directsdk` provider, or an API provider);
- a direct API loop.

**Recorded per round:** `operator_runtime`, `operator_model`, `operator_cutoff`, session id, and whether the hook was verified live.

**The cold operator** (§9) is required:
- a fresh session per round;
- no agent memory;
- no persisted self-written skills (Hermes: an isolated profile per round, with the learning loop and memory off);
- no chat memory or past-chat search.

The operator's context is this file (at least Sections C, E and F), the reveal and the tools.

**On runtime choice.** It is operational (always-on, scheduling, cost), not a quality lever: the model is the same. Subscription use through a third-party harness is policy-sensitive and has changed several times this year, so if Nomad comes to depend on unattended runs, an API key is the stable path.

### 29. Reports `[carried]` + `[gate]`

**Per round:**
- tags, class and mode;
- call counts by type;
- resolutions by outcome and `carrier_state`;
- the three-level score;
- divergence rows;
- synthetics;
- `veto_rate` per depth and kind;
- derived ACKs: forced, switch and none counts, ratified and dropped, fetch lists outstanding;
- per ACK: outcome, reachable and thesis sets, with the cuts and their evidence;
- stories by class, junction flags and treatments, S⊥ and ρ;
- baskets by state, with unbuildable reasons, worst case z*, maximum loss, and budget used per tide;
- the paper result per basket, split four ways, with entry rules shown (`modelled` separated);
- pianos;
- risk computability;
- the wall-map slice;
- the decider jobs run, with their modes and flags.

**Per programme:**
- edge by call type against the baseline;
- operator error by call shape, with basis;
- the wall map and **the count of fully computable legs**, with the per-effect count beside it;
- **the unbuildable-reason histogram**, the new wall map (§20.5);
- the opposite-holder census (K8);
- recall: forced notices that arrived against those derivable from the stores at lock (K10);
- S⊥ and junction look-backs (K11, K12);
- paper P&L per disjoint tide, split four ways, live and backfilled reported separately (K13);
- computability per term;
- library support per rule, counted per tide;
- `weight_state` distribution;
- scorer bias;
- scheduled-facts coverage;
- fetch-path health;
- recorder coverage (from the product);
- decider metrics per job (§24.5) and promotion states;
- kill-test status.

**Computability** `[v16 A4]`: per round and per programme, for each term, the fraction of effects with a value, the basis distribution and the gap-reason distribution. A conclusion drawn over effects where the deciding term was a gap is refused by the report generator.

**The unbuildable histogram is read like the wall map was.** A reason that dominates names the next thing to fix: `no_vocabulary` is authoring; `no_instrument`, `timing_unexpressible` and `modelled_prices` are data; `liquidity` and `story_rank_deficient` are instruments; `excluded_loss` and `shape_mixed` say the thesis is too wide; `no_opposite`, `rho_too_small`, `below_visibility` and `no_edge` are the world.

### 30. Build path: evolve the v15 harness in place `[gate]`

The 22 September draft planned a fresh build that imports the record. The survey of the v15 code changes that: the effect DAG, the transform table, the ACK graph and walk, positions, synthetic legs and exposures, narrative rows, bands and `edge.executability` already exist, behind 146 working tools. v16 evolves that code.

#### 30.1 Rules for evolving in place

- **Schema changes are additive, with one sanctioned exception.** New columns and tables arrive through migration scripts, each hashed and recorded in `STATE.md` and on a ledger row. Widening a v15 CHECK constraint goes through `db._rebuild_table` *(v15)*, which preserves the hash chain. No existing ledger row is modified. Where a v16 computation disagrees with a stored v15 value, a new row supersedes it and the old one stays.
- **v15 behaviour stays reachable.** Every rewired function keeps its v15 path, selected by the round's `logic_version` (`v15` or `v16`), so a v15 round replays exactly as it was scored. (`harness_version` is a source hash: it identifies the code, and can't be branched on.)
- **One migration report.** Every recomputed value (typed gaps, weights, `weight_state`, tide counts, the absence record, the wall map) is listed against its old value. Nothing is overwritten silently.

#### 30.2 Order of work

1. **Freeze v15.** Tag the repository, export each store with a hash, and run `nomad_verify_chain`. This is the rollback point.
2. **Fix what's broken.**
   - `lock_predictions` runs `assess_round` once, and refuses an already-locked round (§14).
   - `STATE.md` is created.
   - The config loader refuses a missing value for every verdict-governing key, including the ones v15 defaults silently: `DEFAULT_OPERATOR` is removed (a round without `NOMAD_OPERATOR_MODEL` set can't be admitted), and `DEFAULT_HOP_DISCOUNT` becomes a ratified appetite value (§33).
   - The operator manifest and the hook check.
3. **Typed gaps.** Replace `None` plus free-text bases with typed reasons (§8), and add `stake_basis`, `operator_basis` and `n`. Drop `implied_value` as a stake input and the re-encode terms from lock-time pricedness (§20.1).
4. **The absence rule.** Add `carrier_state` to resolutions, change `scorer.close_round` (§15), and recompute the absence record.
5. **The veto split.** Move vetoes to effects, write `compose` refusals as `no_path` vetoes, and retire the construction-input eliminators (§21).
6. **Calls.** Branch coverage with `other` (C1); `lag_band` widened to `minutes` and `hours` (C2).
7. **`library_as_of`.** `rebuild_library_stats` *(v15)* overwrites weights in place. It now writes `library_history` rows, and `library_as_of(D)` reads them. The v15 analogues `rule_covers(as_of)` and `base_rates(knowable_by)` are the pattern to follow.
8. **Tides.** The tide registry, per-tide counting, and tides declared retroactively for rounds 1–15, marked `retro_declared`.
9. **Cold operator** (§9, §28). v15 records `operator` and `operator_cutoff` but pools operator rates across models; v16 separates them.
10. **Price vintage store and FX vintages** (§26).
11. **The position-attribute registry and bounds store** (§18.3), and the instrument map with `listed_from`. **K8** runs here: it needs only holders, positions and instruments.
12. **`derive` and `reach`** (§22.2–22.3), templates authored from rounds 1–7 only. **K10** runs here.
13. **`stories`** (§20.2–20.4). **K11 and K12** run here.
14. **Decision point.** If K8 and K10 both die, stop and decide the programme's shape (§11) before building construction.
15. **`instruments`, `construct`, `paper`** (§20.5–20.7, §19.2).
16. **Rebuild rounds 5–15** under v16 with `nomad_rebuild` (K9), under the look-back guards of §31. Rebuilt objects live in a `rebuild` namespace; the v15 record is untouched.

#### 30.3 The fresh build, if evolving fails

If the in-place evolution hits a structural limit (a v15 invariant that v16 can't live with), the fresh build of the 22 September draft remains the fallback. Its migration applies unchanged:
- export the stores and hash each export;
- verify the old chain before import;
- import as ledger rows with original timestamps and `imported_from`, renaming `knowable_from → knowable_at`;
- recompute, and report every difference.

The decision to switch is recorded in `STATE.md` with the limit that forced it.
### 31. Kill tests (pre-registered) `[fold]` + `[gate]`

| # | Falsifiable sentence | Dies if | If it dies |
|---|---|---|---|
| K1 | Fine-tuned Laya `intake_reader`, at a threshold that keeps ≥98% of human-passed items, removes ≥60% of the pile on a time-held-out split (bounds are appetite) | Either bound missed | Keep the human reading everything; `intake_reader` stays in shadow; revisit after more labels |
| K2 | The one attributed re-encode lies outside the holder's own block-bootstrap noise at the lock-resolved band | It lies inside | Retire it as pricedness evidence |
| K3 | On scored legs, `crowd_mirror` obviousness separates effects already priced at `knowable_from` from those that weren't | No separation beyond noise | Drop the meter; keep wiring as fetch order. **Deferred until the slot is filled; live rounds only** |
| K4 | On live rounds, paraphrase-stable switch links resolve through a discrete notice more often than graded links | No difference | Drop the locator; keep probes as fetch triggers only |
| K5 | For forced-ACK process types, docket-counted timing beats the operator's timing calls on past institutional calls | The operator is as good or better | Keep procedural chains as documentation only |
| K6 | Notice watch flags at least X% of real forced notices in carriers read in full over a set period (X is appetite) | Below X | Notice watch stays advisory; the operator reads carriers directly |
| K7 | The ownership census finds listed instruments (equity or bond) with concentrated exposure for a meaningful share of the high-stake unlisted holders from rounds 1–15 (the share is appetite) | The census comes back near-empty | Close the equity thesis; move to shapes B and C |
| K8 | On the nodes of rounds 1–15 that carry a high-stake holder, at least a share X₈ carry listed instruments (listed before the event) on both sides of the node, or one listed holder with options (X₈ is appetite) | Below X₈ | Structural hedges are rare: construction relies on options and event contracts; stock pairs are dropped as building blocks. Runs at the end of P1 |
| K9 | Rebuilt under v16, rounds 5–15 produce at least one `built` basket, and every unbuilt one carries a reason. Clean rounds (5–10, 13) and learning rounds are reported separately | No clean round builds, and the dominant reason is `no_edge`, `no_opposite` or `rho_too_small` | The block is in the world, not the gate: the relationships found are priced or unhedgeable. Move toward shape C. (If the dominant reason is `no_instrument`, `timing_unexpressible` or `modelled_prices`, the block is data; fix sources before concluding.) Runs in P4 |
| K10 | Of the forced notices that actually arrived in rounds 8–15 (carriers read in full), at least a share X₁₀ were derivable at lock from the positions in the stores (`recorded_at` before the original lock) and from templates **authored using rounds 1–7 only** | Below X₁₀ | Emergence is limited by the stores. Invest in positions (census, disclosures, the names book) before construction. Runs at the end of P2 |
| K11 | Using the stories named in the narrative rows registered at lock in rounds 5–15, ρ at lock is higher on effects whose instrument's hedged residual later left its noise band than on effects whose instrument's residual didn't | No separation beyond noise | ρ doesn't measure unpricedness: drop the priced test and build on the visibility test alone. Runs at the end of P3 |
| K12 | Story pairs flagged by a shared constrained node show a larger rise in correlation after the trigger than matched unflagged pairs | No difference | Junction flags are noise: stop treating them (no merge or hold constraints), keep logging. Runs at the end of P3 |
| K13 | Across at least N₁₃ disjoint tides of live, clean, non-modelled baskets, the paper book's result after costs and leaks is positive | Zero or negative | Claim 1 is not expressible in capped instruments at this scale: shape C. Accumulates from P4, live rounds only |

**Guards on the look-backs.** K8–K12 and the K9 rebuild run on the v15 record, which was scored before any of these tests existed. For each round:
- **Positions:** only rows with `recorded_at` before that round's original lock, and `knowable_from` before its clock.
- **Instruments:** only those with `listed_from` before the event.
- **Stories:** only those named in the narrative rows registered at lock, with each story's proxy series fixed by a written mapping rule before any ρ is computed.
- **Templates, vocabularies and bounds:** authored from rounds 1–7 only, and frozen before any of rounds 8–15 is rebuilt. For K9 on rounds 5–7, they are authored from rounds 1–4 only.
- **Theses:** stated by an operator session that sees the round's reveal and nothing after its lock (the cold operator, §9), run on a model whose `trained_through` is before the round's event. A rebuild on a later model is a learning round, whatever the original class.

A look-back that uses anything chosen after seeing the outcome is void.

### 32. Build order and acceptance `[gate]`

Each phase ends with its acceptance checks passing. Nothing in a later phase starts on a failing earlier check. **The mainline (P0–P4) is the gate.** The data product and the decision models run as parallel tracks (DP, DM) that never block it.

| Phase | Build | Acceptance |
|---|---|---|
| **P0 — Freeze and hygiene** | §30.2 steps 1–2 | The v15 chain verifies; one `surviving_risk` row per leg per lock; a second lock is refused; the loader refuses a missing appetite value, including the operator model; fold smoke test 15; a pre-lock web call is refused by the hook |
| **P1 — Computability and time** | §30.2 steps 3–11: typed gaps, the absence rule, the veto split, calls, `library_as_of`, tides, the cold operator, the vintage store, the attribute registry, bounds and instrument map | v16 smoke tests 1–7; fold smoke test 10; one `surviving_risk` row per effect per lock; `library_as_of(D)` excludes a resolution knowable after D; the migration report lists every recomputed value, including the absence record under both rules; the wall map is re-run with bases, and **either shows more than nine fully computable legs (per-effect count beside it) or names, per missing leg, the gap and its reason**. **K8 runs** |
| **P2 — Derived ACKs and reach** | §30.2 step 12: templates, `derive`, vocabularies, `reach`, thesis sets, map-call registration, windows, the walk recompute with segment clocks | Gate smoke tests 16–19 and 29. **K10 runs** |
| **P3 — Stories and S⊥** | §30.2 step 13: story registry, estimated and constructed loadings, classes, junctions, S⊥, exit tests | Gate smoke tests 20–22. **K11 and K12 run.** Then the decision point: **if K8 and K10 both died, stop and decide the programme's shape (§11) before P4** |
| **P4 — Instruments, construction, paper** | §30.2 steps 15–16: cap classes, cost model, the construction programme with its gates and ladder, budgets, the paper book and the four-part split, `nomad_rebuild` | Gate smoke tests 23–28. **K9 runs**; live rounds begin accumulating toward K13 |

**Parallel tracks:**

| Track | Build | Acceptance |
|---|---|---|
| **DP — Data-product track** | Per Section G. Then, in Nomad: enumeration from recorded feeds; Q1a point-in-time search with the truncation raise; feed vocabulary per stratum; the `node_type` registry; the ownership census; the prediction-market benchmark; prices served through the contract into the vintage store | v16 smoke tests 8–9; a truncated search raises; K7 and K2 run |
| **DM — Decision-model track** | `decider` with the Laya adapter, router, chunking, recording and time wall; label store; first fine-tune of `intake_reader`; calibration; registry; shadow mode. Then procedural chains, `notice_watch` and the locator in shadow; then wiring and probes on live rounds; the `crowd_mirror` slot when Jev is un-held | Fold smoke tests 11–14; K1 runs; K5 runs on past institutional calls; K6 is set up; K4 (and K3 once the slot is filled) run |

**v16 smoke tests** (from the v16 brief §D, retained):

1. Stake on an unlisted operating asset with a stated output → value computed, `stake_basis = operating_scale`.
2. Stake on an authority holder → a typed gap (`not_applicable`) with its reason, not a fabricated denominator.
3. The wall-map re-run shows `stake_basis` and `operator_basis` broken out, and the count of fully computable legs, higher than nine, with the per-effect count beside it.
4. The operator term on a sparse bucket falls back a level, with `operator_basis` and `n` recorded.
5. The veto set on an effect DAG gives a non-zero `veto_rate`, and a `cost` effect and an `obligation` effect through the same relation are vetoed differently.
6. A `map` call whose branches don't cover the space is refused unless an `other` branch with a falsifier is present.
7. A duration call on a two-hour event has `lag_band = hours` available and scoreable.
8. A node of a previously unseen kind is accepted and registered, with carrier density computed from what exists.
9. Enumeration over a digital-infrastructure window runs the stratum's own query set, and status-page items appear as candidates.

**Fold smoke tests** (each runs in the phase named beside it):

10. An absence claim with `carrier_state = unread` cannot resolve `hit`. *(P1)*
11. A decider call with `trained_through` after `about_time` is refused, and a replay does not call the model. *(DM)*
12. Wiring output never changes a weight, a support value, a veto or a construction input. The test holds the **examined set** fixed — the same chains, fed to the vetoes in a shuffled order — and asserts every weight, support value, veto verdict and basket is identical. (Diffing wiring on against wiring off cannot work: wiring changes which chains get examined, which is its whole purpose.) *(DM)*
13. A switch that fails paraphrase stability is not passed to the locator. *(DM)*
14. A locator candidate with no fetch path is kept as `not_covered`, not dropped. *(DM)*
15. A round's operator manifest records model, runtime, cutoff and hook verification; a round without them can't lock. *(P0)*


**Gate smoke tests:**

16. A template whose conditions are all documented derives a forced ACK. With one condition resting on an `inferred` position, it derives a switch with that condition on the fetch list. With one documented false, it derives nothing. *(P2)*
17. An outcome whose need is unknown stays in the reachable set. One whose need is documented false before the deadline is cut, with its evidence recorded. *(P2)*
18. A thesis exclusion resting on an unknown is refused at lock. *(P2)*
19. An ACK firing with `delivered = true` and no `outcome_id` is refused. A valid firing re-derives ACKs and locks a new segment with its own hash. *(P2)*
20. A story whose loading lies in the span of two others is classed synthetic and decomposed. *(P3)*
21. A thesis vector equal to an active story's loading gives S⊥ = 0 and ρ = 0. *(P3)* In P4, that basket is `unbuildable: rho_too_small` before any solve.
22. A correlation rise between two stories with no shared node is logged as a piano, never as a junction. *(P3)*
23. No built basket contains an uncapped instrument. A short on a switch-derived ACK arrives as a bought put, or is dropped; a stock short on a documented ACK carries a stop. *(P4)*
24. A basket built on a switch-derived ACK contains hard-capped instruments only. *(P4)*
25. Replaying a lock from its manifest returns the same weights, and the lock hash reproduces, even after the mutable stores have changed. *(P4)*
26. A backfilled fill never uses a price dated before the event's `knowable_from`. A `modelled` entry is excluded from K13. With the budget committed in full, a basket with no edge returns a negative z*, never zero. *(P4)*
27. Baskets under one tide never together exceed `LOSS_CAP_PER_TIDE`, and no basket's weights are sized against another's. *(P4)*
28. The import linter refuses `derive` or `reach` importing a price module, and refuses `stories`, `instruments` or `construct` writing to effects, ACKs or thesis sets. *(P4)*
29. On a backfilled walk, a segment's derivation and reach (and, from P3, its loadings) read nothing dated after its clock: a position recorded with a later `knowable_from` is ignored, and so is a price. *(P2)*

**Owed from v16 brief §C:**
- **C4:** check whether the map-layer rules harvested in rounds 10 and 14 were loaded. If absent, harvest at least:
  - *when an event names a site with more than one operator, the larger operator is the prior*;
  - *a repeat filer gets the base-rate procedure, not the form of its last filing*;

  both carrying `map`.
- **C6:** confirm the `divergence_held` fix.
- **v16 brief §0.1:** the round-15 map call goes to the second scorer and is not banked either way; it earns no mechanism credit.
- **v16 brief §0.2:** the selector suspension is cleared, logged with its reason (§15).

### 33. Appetite register

Every value here is set by Rob once, reviewed at twenty clean rounds unless stated, and never moved because it hasn't been met. **No verdict-governing number has a default**: the config loader refuses a missing one.

#### 33.1 Ratified and carried

| Item | Value | Status |
|---|---|---|
| Frontier bound (`FRONTIER_BOUND`) | 120 | Ratified. Enforced in `effects.compose` *(v15)*. Derivation bindings have their own bound (`DERIVATION_BINDINGS_MAX`, §33.3) |
| Hop discounts and transform seed (`HOP_DISCOUNT`, `TRANSFORM_SEED`, 28 entries) | As in the v15 config | Ratified |
| `DEFAULT_HOP_DISCOUNT` | As in the v15 config | **To ratify** as an appetite value (P0). Until v16 it was a silent default |
| `DUE_AT_MAX_DAYS` | 90 | Carried from Event Requirements v3 (live rounds). v16 also uses it to cap unknown forced-ACK windows (§22.1) |
| Independence discount | 1.0 (root split) → 0.15 (last-node split) | Ratified |
| Support threshold | 0.30 | Ratified |
| Inert-stake ceiling | 0.25 | Ratified |
| Convergence threshold (`CONVERGENCE_THRESHOLD`) | 0.5 | Ratified. v15 compares \|magnitude − implied\| < 0.5 in `walk.convergence` |
| Synthetic component and cross-node discounts | 0.85, 0.85 | Carried |
| Band method (`BAND_METHOD`, `BAND_SESSIONS_EMPIRICAL`, `BAND_PCTILE`) | Empirical, 60 sessions, (5, 95) | Carried for `logic_version = v15` rounds. The v16 rule on the tide-only hedged residual is set in §33.2 |
| `TURNOVER_FLOOR_USD` | 2,000,000 | Carried; **re-ratify** now that it sets the floor for stock instruments rather than a leg's gate |
| `OPERATOR_PRIOR_N` | 4 | Carried |
| `NARRATIVE_DUE_DAYS` | 5 | Carried |
| `FADEABLE_IMPLIED_MIN` | 2.0 | Carried |
| Risk-vector `APPETITE` (stake 1.0, structural 0.60, pricedness 0.50, operator 0.40, expression 0.50) | As in v15 | Carried **as diagnostic only**: it sets the binding term and the operator size factor (§20.7), and never gates |
| `basket_stake` floor (`BASKET_STAKE_FLOOR`) | 1.0 | Carried as a report. It was never enforced in v15 and construction supersedes it |
| `POSITION_SHARE_FLOOR`, `TIDE_RATIO_MIN`, `SURVIVING_MAGNITUDE_MIN` | 0.05, 1.0, 1.0 | **Retired as vetoes** (§21); kept in reports for comparison with v15 |

#### 33.2 Unset, required before the dependent phase (fold)

| Item | Needed by |
|---|---|
| `OPERATOR_MIN_N` | P1 |
| The operator model per round (`NOMAD_OPERATOR_MODEL`; `DEFAULT_OPERATOR` is removed) | P0 |
| Attenuation depth rule: the per-hop decay and the support floor at which a chain stops (§6, §25.1). **State it as a rule, not a depth number** | P1 |
| Tide registry: who declares a tide, and the vocabulary | P1 |
| Tide-count validation minimum (suggested: 2) | P1 |
| Price-band rule on the hedged residual (form and quantile); `BOOTSTRAP_BLOCK` | P1 |
| Materiality band per holder class (reports only now) | P1 |
| Per-job recall floor for the promotion gate (§24.6 step 3) | DM |
| K1 bounds (suggested: 98% keep, 60% removed); rejection audit sample (suggested: 10%) | DM |
| Promotion-gate margin; ECE ceiling; `shadow_min_items`; `retrain_interval` / `retrain_min_new_labels` | DM |
| Wiring `k` and bottom slice (suggested: 10–20%); bimodality thresholds | DM |
| Daily flag budget; K6 X | DM |
| K7 meaningful share | DP |

#### 33.3 Unset, required before the dependent phase (gate)

| Item | What it sets | Needed by |
|---|---|---|
| X₈ | K8 threshold | P1 |
| X₁₀ | K10 threshold | P2 |
| K11 and K12 separation tests | The statistic and the significance level, fixed before the look-back runs | P3 |
| Outcome vocabularies per notice kind | The first set: restart statements, FM declarations, regulatory decisions, allocation notices, incident reports | P2 |
| Obligation templates, bounds, position attributes | The first set, authored from rounds 1–7 only (K10) | P2 |
| `DERIVATION_BINDINGS_MAX` | The bound on template bindings (§22.2) | P2 |
| `LOADING_SESSIONS`, `ACTIVE_WINDOW` | Loading estimation and the active-story rule (§20.2) | P3 |
| `ANGLE_ORTH`, `SYNTH_EPS` | Angle classes (§20.2) | P3 |
| `JUNCTION_WINDOW`, `JUNCTION_DELTA` | Junction confirmation (§20.3) | P3 |
| `RHO_MIN`, `VIS_K`, `RHO_EXIT`, `RECOVERY_FRACTION` | The priced and visibility tests, and the exit tests (§20.4) | P3 |
| `PREMIUM_MIN` | How far the quoted implied move must exceed the noise band for the sell-premium shape (§7.2) | P3 |
| `TIDE_SHOCK` | The tide dimension of the scenario grid (§20.5) | P4 |
| `ADOPT_MOVE` | The reported upside if an adjacent reading is adopted (§7.3) | P4 |
| `EXCLUDED_LOSS_FRAC` | The loss floor, as a fraction of B_basket, in reachable outcomes the thesis excludes (§20.5) | P4 |
| `UNKNOWN_WIDEN` | How far an unknown risk term widens a band (§20.5) | P4 |
| `HEDGE_EPS`, `LIQ_CAP` | Hedge tolerance and liquidity cap (§20.5) | P4 |
| `EDGE_MARGIN`, `TOLERANCE` (fractions of B_basket), `POS_SHARE_MIN` | Build, capped tolerance, unbuildable (§20.5) | P4 |
| `LOSS_BUDGET_PER_ROUND`, `LOSS_CAP_PER_TIDE`, `SWITCH_BUDGET_FRACTION` | Budgets (§20.7) | P4 |
| `BAND_WIDTH_MAX` | How deep in degrees construction goes (§20.7) | P4 |
| `EXPIRY_QUANTILE` | Instrument expiry against procedural windows (§7.2, §25.5) | P4 |
| `STRESS_QUANTILE` and the stop rule | Stress-capped maximum loss (§20.6) | P4 |
| Cost model: `SPREAD_FALLBACK` per kind, fees, `BORROW_RATE`, slippage rule | Costs (§20.6) | P4 |
| Option pricing model for `modelled` entries | Backfilled option legs (§19.2) | P4 |
| Mark schedule; attribution order and formulas for the four-part split | The paper book (§19.2) | P4 |
| N₁₃ | K13: the number of disjoint tides | P4 |

### 34. Not decided

**Carried:**
- **Formal handling of mid-sequence (Q1a-fail) events** under `tags_only`.
- **Which of `absorbed_by_slack` and `no_sink` applies to which effect kind** (§5, §21). The two vetoes point opposite ways, both are in the record, and settling it is a theory question, not a build one.
- **The `crowd_mirror` model** (Jev held), and whether the operator's blind pass could serve as an interim mirror. It is leak-free on clean rounds because Q2 guarantees it, but it is also the thing being scored, so its use needs a separate argument.
- **Whether `link_transmission` ever gets enough labels to promote.** If it doesn't, wiring stays in shadow permanently, and that is an acceptable outcome.
- **Whether `decider` lives in the product repository or its own.**
- **Storage and redistribution terms** per exchange feed and GLEIF/OpenFIGI data, before recording and before shape C.

**Added by the gate:**
- **Ratifying the gate amendments into Section C.** The `[gate]` items in §§3–8 and §12 are proposals until Rob ratifies them, and Section D lists each. Three conflict with statements C makes today: building on switches (D3; T4's arm/disarm asymmetry), exiting on S⊥ before delivery (D5; T4's exit rule) and building baskets rather than filtering (D7; T7). Until ratified, E builds them so they can be tested, and C doesn't claim them.
- **Whether stress-capped instruments belong at all.** "Bounded risk as a gate" argues for hard caps only. Admitting stocks, shorts and pairs under stops widens the instrument set, makes stock pairs possible (and with them most structural hedges), and makes gaps through stops a leak class. The spec admits them on documented ACKs only (§4); dropping them is one config change, and K8 says how much it would cost.
- **Options history for backfilled rounds.** Free sources keep current chains only, so backfilled option legs are `modelled` and excluded from K13. Either K13 accrues on live rounds only (slow), or a paid options history is bought once a measured block names it.
- **The attribution convention for the four-part split.** Narrowing and timing overlap on option legs around the ACK date. The order in §19.2 is a convention; it must be fixed before the first lock and never changed after.
- **The candidate rule on junctions** (§3) is a rule candidate, and K12 is its first test.
- **Prediction markets as a native domain.** An event contract is an ACK with a price, so the wall disappears there. The PredictionProphet fork (necessary-condition decomposition, a Fréchet upper bound over routes, Jev judging conditions narrowly, price kept out until the gate) is a separate spec, not part of v16.

### 35. Glossary

| Term | Meaning |
|---|---|
| **ACK** | Standing predicate: named source + threshold + date. Levels: support, conditioning, direction. Timing: `scheduled`, `forced`, `discretionary` (the last is never an ACK). Origin: operator, calendar, derived, locator |
| **Active story** | A story the market is telling, per segment: its proxy moved outside its noise band before the segment's clock, or the operator names it as running, citing a source knowable before that clock. A narrative row's resolution never counts |
| **Adjacent story** | A reading the market isn't telling yet that points toward the thesis, on a directional basket. Held: it's the route by which the market reaches the structure |
| **Anchor** | A rule that forbids. With the time wall, the only thing that vetoes (§21) |
| **Appetite** | A threshold set once, reviewed on schedule, never moved because it has not been met |
| **Attention rank** | The wiring's ordering of chains for examination and fetching. Never weight |
| **Attenuation** | The per-hop decay of support down the effect DAG, and the floor at which a chain stops. The rule is appetite (§33); "the depth limit is attenuation" is a statement about what sets the limit, never a number |
| **Basket** | One per ratified ACK, built to do best in the worst scenario the thesis keeps, with its loss capped in the reachable outcomes the thesis excludes (§7.3, §20.5). v15's `event_basket` is the older view of legs per round |
| **Binding term** | The risk term furthest below appetite, chosen over all five terms. Diagnostic only; it gates nothing |
| **Built / unbuildable** | Basket states. Unbuildable always carries the first reason the diagnostic ladder finds (§20.5) |
| **Cap class** | `hard` (maximum loss fixed by the contract), `stress` (maximum loss estimated, enforced by a stop: stocks long or short, pairs, futures spreads), `uncapped` (never held) |
| **Carriage** | The claim kinds a rule may be cited for |
| **Carrier** | A source that will speak about a call, with a fetch path |
| **Carrier state** | `silent`, `spoke`, `unread`, `not_covered` |
| **Checkpoint** | A specific set of model weights, identified by content hash (or a pinned remote version) |
| **Closure** | Allowing only transitions the library, the transform table and the procedural chains can produce. Anything else is a piano |
| **Cold operator** | An operator session with no memory across rounds |
| **Crowd mirror** | A commoditised decision model whose confidence is read as obviousness |
| **`decider`** | The shared decision-model runtime |
| **Derived ACK** | A forced ACK computed from an obligation template whose conditions are all documented true by positions and bounds (§22.2). A switch is stored the same way, flagged `is_switch` |
| **Diagnostic ladder** | The fixed order of tests that names why a basket is unbuildable |
| **Divergence** | Narrative sign ≠ structural sign at lock |
| **Effect** | A consequence at a holder; the unit of the DAG |
| **Expression** | Which capped instrument exists for a holder (§20.6). No instrument means no building block, not a dead effect |
| **Forced ACK** | An obligation whose timing is not public |
| **Hedged residual** | An instrument's return after regressing on the tide only. Its noise band sets stake bands, `below_band` and visibility |
| **Hedged set (H)** | The tide, every active story and every merged junction story. Construction holds weights orthogonal to it (§20.4) |
| **Junction** | Where two unrelated stories start moving together because their paths share a constrained node |
| **`knowable_from` / `knowable_at`** | When a fact became provably public. `knowable_from` is the harness's name *(v15)*, kept; `knowable_at` is the data-product contract's name. The adapter maps one to the other (§9) |
| **`library_as_of(D)`** | Library state computed only from resolutions knowable by D |
| **Loading** | How much a story moves an instrument. Estimated from a proxy series, or constructed from position attributes |
| **Lock manifest** | The row hashes of every mutable-store row, vintage and version a lock read. Replay reads the manifest, not the live stores (§14) |
| **Maximin** | Choosing weights to maximise the worst payoff across scenarios |
| **Model time wall** | A model may answer about T only if `trained_through ≤ T` |
| **Names book** | Holders and their dated pages; entity resolution by the operator from documents |
| **Narrative row** | What a bounded channel says an event implies, scored on whether it said it |
| **Node type** | What kind of thing a node is (strait, smelter, pipeline, sovereign debt, …): a registry (§15). Different from v15's `node_kind`, which says event or attribute |
| **Notice kind** | The kind of document a forced ACK delivers (restart statement, FM declaration, regulatory decision, …). Outcome vocabularies are keyed on it |
| **Obligation template** | A library rule of `kind = obligation`: the conjunction of positions that makes a notice unavoidable |
| **Orthogonal story** | An active story at near right angles to the thesis. Tide; hedged |
| **Outcome set (Ω)** | What an ACK's document can say: a small typed vocabulary per notice kind. It also names `other`, which lies outside the closed world |
| **Paper book** | The record of built baskets, entered at lock and marked to exit, split four ways (§19.2). Code name `paper`, never "ledger" |
| **Parallel story** | An active story within the cut-off angle of the thesis, whichever its sign. Priced; hedged |
| **Piano** | Anything outside the closed world: logged as a leak, never modelled |
| **Piece** | An effect at a holder, as enumerated by the operator |
| **Position** | A holder's stake in a node, per asset: tier, priority, substitutability, share, duration |
| **Procedural chain** | A state model of a rule-following actor, counted from dockets |
| **Reachable set (R)** | The named outcomes whose needs are true, still reachable, or unknown. Unknown keeps an outcome in; `other` is never in it |
| **Rho (ρ)** | \|S⊥\| ÷ \|S\|: the share of the thesis no hedged story explains. It is the `pricedness` term at lock; higher is better |
| **Scenario grid** | Thesis-set outcomes (for the objective) and excluded reachable outcomes (for the loss floor), each × tide down/flat/up, with a payoff band per instrument (§20.5) |
| **Spread probe** | A link question asked without and with the settling document |
| **Stake basis** | `price_band`, `operating_scale`, `class_scale` |
| **Story** | A named reading on the tape, with a path through the graph and a loading on each instrument |
| **Switch** | A derived-ACK candidate with some conditions unknown and none false; its unknowns become a fetch list. Also, from the fold, a link whose answer stays split after the settling document |
| **Synthetic story** | A story that lies in the span of others; decomposed into its components |
| **S⊥** | The part of the thesis vector outside the span of the hedged stories' loadings (tide, active stories, merged junction stories). "Unpriced" as a number, and exactly what the hedged basket holds (§20.4) |
| **T_seg** | A segment's clock: `event_date` for segment 0, the opening firing's `knowable_from` after that. Every read for the segment is bounded by it (§14) |
| **Thesis set (Ωₜ)** | The reachable outcomes the thesis keeps, each exclusion citing positions or rules |
| **Tide** | An ambient condition that prices everything it touches |
| **Time wall** | Pre-lock, only what was knowable by the event date |
| **Transform table** | `(parent effect kind, relation) → child kind, transmission value` |
| **Typed gap** | A missing value with its reason: `not_representable`, `not_disclosed`, `not_covered`, `not_applicable` |
| **Veto rate** | Share of effects removed by the veto set, per depth and kind |
| **Veto set** | `no_path`, `signs_held`, `absorbed_by_slack`, `no_sink`, `below_band` (§21). Only `below_band` reads prices |
| **Vintage** | A frozen, hashed copy of a price fetch with its retrieval time |
| **Walk** | A chain of segments created by forced ACKs firing |
| **Weight state** | `untested_as_carried`, `netted_to_zero`, `tested` |
| **Window (forced ACK)** | The latest date by which an obligation must be met: from a statute, a ratified procedural chain, or the operator, capped at `DUE_AT_MAX_DAYS`. Not an expected date (§22.1) |

---

# SECTION F — Event Requirements v3

*Ratified intake rules (`event_requirements_v3.md`), reproduced whole. Section E §15 applies them in full (as its `strict_v3` mode), adds a looser `tags_only` mode, the Laya pre-sort and feed vocabulary per stratum, and proposes two changes: the absence-expiry rule under "Live rounds" below (D9) and a domain-preference tie-break in selection (D15).*

Supersedes v2. Purpose of the revision: the small-event result is established (nine rounds; the visibility rule at 14/15). The criteria now admit the events the open questions need — events with a narrative, events still unfolding — and move selection enumeration into the harness. Q8 is the one guard that does not relax.

## Tags (set at intake, immutable)

| Tag | Set when | Bears on |
|---|---|---|
| `lag_test` | Q1a and Q1b pass, Q5 pass (underread) | the lag hypothesis |
| `headline` | Q5 fails as *too big* (global or national front page) | narrative/divergence (v9 item F3), arming under tides, sequence rules |
| `weather` | Q1b fails | recurring-disruption rule, coverage, scoring |
| `late_headline` | Q1a fails, Q1b passes | sequence rules |
| `learning` | Q2 fails | nothing clean; kept for calibration |

A round can carry `headline` together with `weather` or `late_headline`; stats filter on any combination.

**Cap:** at most one of `weather` / `late_headline` in any two consecutive admitted rounds. No cap on `headline`. Required mix over the next seven admitted rounds: ≥ 4 `headline`, ≥ 3 `lag_test`.

## Questions

| Q | Name | Definition | Answered by | On fail |
|---|---|---|---|---|
| Q1a | First traversal — event | No directly related market-moving news on the channel in the prior 30 days. Harness runs the window search from the enumeration feeds; human confirms. | Harness + human | tag `late_headline` |
| Q1b | First traversal — node | No recorded disruption on the node in 90 days, < 3 in 12 months, from ledger + registry readers. | Harness (override with basis) | tag `weather` |
| Q2 | Post-cutoff | `event_date > operator_cutoff`. | Harness | class `learning` |
| Q3 | World event | A thing happened; not a price move. | Human | **reject** |
| Q4 | Shared thing | Touches a facility, route, material, rule, port, standard or region with more than one holder. | Human | **reject** |
| Q5 | Size band | `underread` (trade press / regional) → `lag_test`-eligible; `headline` (front page) → tag `headline`; `trivia` (no plausible holder beyond degree 0) → reject. | Human | reject only for trivia |
| Q6 | One event, one date, one line | Not a trend. | Human | **reject** |
| Q7 | Scoreable per call | **Age is no longer a criterion.** Each call at lock names a carrier with a working fetch path and a `due_at` by which it resolves. Intake passes Q7 if the node kind has open carriers; lock enforces per call. | Harness | at intake reject; at lock, fallback carrier required |
| Q8 | Clean prompt | Bare event + date. No aftermath, parties, reaction, adjectives, duration. **Does not relax.** For a live event the prompt is what was knowable at `event_date + 0`: the first wire line, stripped. | Human | reject and rewrite |
| Q9 | Selection honesty | The harness enumerated a fixed feed over a fixed window and wrote every rejection; the human took the first pass. | Harness | `Q9 = fail`; three in a row suspends the selector |

## Live rounds

An event may be submitted from the day it happens. Consequences:

- Every call carries `due_at` (≤ 90 days). Calls score as they fall due; the round is `scored` when the last call resolves or expires. A call whose carrier has not spoken by `due_at` resolves `unverified` unless it was an absence claim, in which case it resolves `hit` with quality discounted by coverage as usual.
  - **Override, proposed (D9; §15, §19.1):** an absence call resolves `hit` only if its carrier was read in full through `due_at` and said nothing (`carrier_state = silent`); otherwise it resolves `unverified`. The rule as written above is what the v15 harness does today.
- Post-lock retrieval opens at lock as before; for a live round most of what it finds is the event itself, and the aftermath arrives with the calendar. That is the wall working.
- The narrative row must be scored **first** — the channel speaks early — and never re-scored after structural resolution.
- Scheduled facts within the window are the natural `due_at` anchors; the catalyst-class predicate requires the statement to **concern the node** (a listed holder's results date is a catalyst only if the node is material to it; otherwise it is a tide — round 9).

## Selection procedure (harness-run)

1. `nomad_enumerate(feed_set, from, to)` — enumerates dated items from the registered open feeds (incident registries, regulator RSS, trade-press RSS, GDELT slice), in date order, deduplicated.
2. For each item intake dry-runs Q1a, Q1b, Q2, Q5 size hint (by outlet class), Q7; writes a rejection row for every item that fails Q3–Q6 by the human's reading or Q7 by computation.
3. Presents the first passing item with its computed tag. The human confirms Q3, Q4, Q6, Q8 and picks the size band. Confirming submits. Skipping writes a rejection with reason.
4. Reveal as v9 plus: the window-search result behind Q1a, and the scheduled facts inside the round's maximum `due_at`.

## What a good round now looks like

- For `headline`: an event on the front page with at least three listed holders across degrees 0–2 on both sides of a node, so the synthetic rules have material and the narrative row has a channel that will speak. Divergence expected.
- For `lag_test`: as v2 — a mid-chain material or shared facility, listed holders both sides, a statement about the node inside the window.
- For either: submitted within a week of the event, so at least half the calls are forecasts.

---

# SECTION G — Data Product: Isolation Specification

*v1, 2026-09-22. Status: to build. Parts are cited as `G0`–`G12`. References to "spec v4" are to the Ohmni specification (`ohmni-specification-v4.md`), which is not in this file.*

*Grounded in the `standard-reference/ohmni` repository as of commit `cadfb95` (2026-09-15) and in `ohmni-specification-v4.md` Part II.*

*This document says how to lift the data layer out of Ohmni into a standalone product that Ohmni and Nomad both consume through the contract. It does not change what the data layer claims (spec v4 §4). It changes where the code lives, what the contract is allowed to contain, and what the product must do before a second consumer can trust it.*

**Working name:** `dataprod`. Rename freely; nothing here depends on the name.

---

## G0. Why isolate, and what "isolated" means

The seam already holds at the test level. No harness test imports `data_layer`, and the real layer passes the same conformance suite as the fixture. But the product still lives inside one consumer's repository, and three things in the current code leak across the seam:

1. **Harness policy lives in the contract.** `contract/capability.py` carries `DEGRADATION_TABLE`, which names Ohmni harness features (`correlation_cap`, `root_set_independence`, `mechanism_as_graph_path_bonus`, `corroboration_by_independence`, `cadence_commensurability`, `gap_reason_discrimination`). It also carries the consequences (`REFUSE`, `CONTAMINATED`, `DISABLE`) that one consumer chose. A second consumer has different features and may choose different consequences.
2. **The contract has defaults that assert properties.** In `contract/declaration.py`:
   - `historical_access` defaults to `BULK`.
   - `plugin_trust` defaults to `CERTIFIED`.
   - `measurement_type` defaults to `MEASURED`.
   - `Emission.records_of` defaults to `EDITORIAL_PUBLICATION`.
   - `Emission.role` defaults to `CONSTITUTIVE`.

   A plugin that forgets to declare any of these silently claims backfillability, full trust, or a phenomenon it isn't. This contradicts the project's own rule that nothing governing a verdict gets a default, and it contradicts spec v4 §11.1, where declaration completeness rejects a missing `historical_access`.
3. **Data-side infrastructure lives in the harness.** `harness/dataset.py` (corpus freeze and manifest) and `scripts/rebuild_dataset.py` prove which bytes the layer served, so they are data-product infrastructure. The `/relate`-shaped validity matrix in `harness/presentation.py` is field algebra (spec v4 §10.5), which also belongs to the product.

**Isolated means all of the following hold, each mechanically checked (G9):**

- `contract` imports nothing outside the standard library.
- `dataprod` imports `contract` and never any harness.
- Each harness imports `contract` (and `testkit` in tests) and never `dataprod` from library code.
- The contract carries no consumer vocabulary and no property-asserting defaults.
- The product runs, tests, rebuilds its corpus and serves queries with no harness installed.

---

## G1. Packages after the split

```
contract/        the shared port. Types, enums, the DataLayer protocol. Nothing else.
dataprod/        the product: adapters, recorders, store, entity spine, xref,
                 attachments, dataset freeze, API + MCP server
testkit/         fixtures (honest / adversarial / degraded) + conformance suite.
                 Depends on contract only. Any consumer tests against it.
decider/         decision-model runtime (Laya now, other models later).
                 Shared by dataprod (neutral attachments) and Nomad (its own questions).
                 Specified in Section E §23; referenced here, not duplicated.

ohmni-harness/   consumer 1 (the current harness/ minus what moves out)
nomad-harness/   consumer 2
```

**Repository layout.** Recommended: one repository for `contract`, `dataprod`, `testkit` and `decider` (a monorepo with four packages), and one repository per harness.

- The contract is versioned and published as its own package, even from inside the monorepo.
- A single repository for all four is acceptable if the import rules in G9 are enforced by test. The rule, not the folder, is what keeps the seam.

**Dependency rules.**

| Package | May import | Must never import |
|---|---|---|
| `contract` | stdlib | anything internal |
| `testkit` | `contract` | `dataprod`, any harness, `decider` |
| `decider` | stdlib, `laya` (optional extra), `contract` (for hashing helpers only) | `dataprod`, any harness |
| `dataprod` | `contract`, `decider` (optional extra) | any harness |
| each harness (library code) | `contract`, `decider` | `dataprod` |
| each harness (tests) | `contract`, `testkit`, `decider` | `dataprod` |
| integration code (demos, run scripts, the operator's MCP wiring) | anything | — |

The last row is deliberate. The seam is between libraries. A run script that wires a real layer into a harness is allowed to import both, because it is the one place the two are meant to meet.

---

## G2. What moves where

| Current path (ohmni @ `cadfb95`) | Destination | Change on the way |
|---|---|---|
| `contract/record.py` | `contract/` | None |
| `contract/protocol.py` | `contract/` | Add the attachment query (G4.3); bump `CONTRACT_VERSION` to `0.2.0` |
| `contract/declaration.py` | `contract/` | Remove the property-asserting defaults (G3.2). Move `Phenomenon` from a closed enum to a versioned vocabulary (G3.3) |
| `contract/capability.py` | `contract/` keeps `Capability` and `CapabilitySet` | **`DEGRADATION_TABLE`, `Degradation`, `Consequence` and `NON_NEGOTIABLE` move to each harness** (G3.1). Add `Capability.ATTACHMENTS` and `Capability.RECORDING` |
| `contract/__init__.py` | `contract/` | Re-export only what remains |
| `data_layer/` (layer, cache, entities, adapters) | `dataprod/` | `layer_version` becomes a content hash (G5.3). Entities move into the entity spine module |
| `fixtures/` | `testkit/fixtures/` | Imports rewritten to `contract` only |
| `conformance/` | `testkit/conformance/` | Add the two new checks in G8.2 |
| `harness/dataset.py` | `dataprod/dataset/` | Freeze, manifest and `verify_against_manifest` unchanged |
| `scripts/rebuild_dataset.py` | `dataprod/scripts/` | Unchanged |
| `.dataset/` (manifest) | `dataprod/.dataset/` | Unchanged; stays committed, source data stays out of git |
| `/relate`-shaped validity matrix in `harness/presentation.py` | `dataprod/xref/algebra.py` | Only the matrix. Presentation logic stays with the harness |
| `harness/obligations.py` | `ohmni-harness/` | Now imports its degradation table from its own package |
| `harness/potency.py` | `ohmni-harness/` | It is the harness's interpretation of `records_of` / `role` / `reports_on`. Nomad writes its own if it needs one |
| `harness/budget.py`, `.budget/ledger.json` | `ohmni-harness/` | The budget ledger is a consumer's snooping ledger; each consumer keeps its own |
| everything else in `harness/` | `ohmni-harness/` | None |
| `tests/` | split | Data-product tests (including `-m historical`) go to `dataprod/tests/`; harness tests (fixture-only) go to `ohmni-harness/tests/` |
| `demo/` | `ohmni-harness/demo/` | Integration code; may import `dataprod` |
| `docs/spec/ohmni-specification-v4.md` | both | Part II becomes `dataprod/docs/spec.md`; Parts I, III and IV stay with the harness. Cross-reference, don't duplicate |
| `docs/spec/STATE.md` | both | The data-layer rows move to `dataprod/docs/STATE.md`; the harness rows stay |

**Preserve history.** Use `git filter-repo` (or `git subtree split`) on the moved paths so blame and the reasoning in commit messages survive. The commit messages are part of the record here.

---

## G3. Contract changes

### G3.1 The degradation table leaves the contract

The contract keeps the **facts** and loses the **policy**:

- **Stays:** `Capability` (the list of things a layer can provide) and `CapabilitySet` (which of them this layer provides, plus `missing`).
- **Moves to each harness:** what a missing capability *means* to that harness — refuse, run contaminated, or disable a named feature.

Each harness ships its own table, keyed by `contract.Capability`, and asserts it against its own obligations matrix. Ohmni's table moves verbatim. Nomad's is specified in Section E §26.

`KNOWABLE_AT` stays non-negotiable in every consumer. That is a property of the contract's purpose, not one harness's choice, so the contract states it in its docstring. Each harness still enforces it itself.

### G3.2 No property-asserting defaults

These four fields become **required**, with no default:

- `SourceDeclaration.historical_access`
- `SourceDeclaration.measurement_type`
- `Emission.records_of`
- `Emission.role`

A declaration that omits one fails to construct. Conformance keeps its declaration-completeness check as a second line (G8.2 `no_property_defaults` checks exactly these four).

**`plugin_trust` is not in that set, because the plugin does not supply it at all: the loader assigns it.** A plugin can't certify itself, so the field is set on the declaration after loading rather than required from it.
- `certified` is set only for adapters in the `dataprod` package.
- `conformant` is set by the loader after the full suite passes.
- `declared` is the floor.

### G3.3 `Phenomenon` becomes a versioned vocabulary

The current closed enum has eight members chosen for Ohmni's basis, and Nomad's carriers need members that don't exist yet. Adding one is a contract change, which is too heavy for a vocabulary that grows with the graph (spec v4 §19.1).

- **Replace the enum with a registry.** `PhenomenonVocabulary(version, members: dict[str, description])` ships with the contract as a data file.
- **Extensions are additive and bump the vocabulary version.**
- **The version is recorded in every manifest**, the same way `concept_map_version` is.
- **Removing or renaming a member is a breaking change** and bumps the contract's major version.

Nomad's first additions are proposals, to be confirmed against real records:

| Member | Records of |
|---|---|
| `contractual_notice` | Force-majeure declarations, allocation notices, restart statements |
| `market_assessment` | Published price assessments and freight/insurance indices that are not exchange prints |
| `risk_listing` | War-risk listed areas and sanctions lists |

### G3.4 Version

`CONTRACT_VERSION = "0.2.0"`. The changes in 3.1 and 3.2 are breaking for any plugin relying on defaults, which is the point. Both harnesses pin `contract>=0.2,<0.3`.

---

## G4. New contract types

### G4.1 Neutral record kinds Nomad needs

These are `Record.kind` values, which are neutral by construction. None is meaningless to a stock screener.

| Kind | Value shape (keys) | Typical source |
|---|---|---|
| `announcement` | `title`, `lede`, `url`, `issuer`, `category`, `language`, `claimed_published_at` | Exchange announcement feeds, company IR |
| `filing_item` | `form`, `items`, `accession`, `url`, `claimed_published_at` | EDGAR 8-K items |
| `regulatory_notice` | `title`, `lede`, `url`, `authority`, `docket`, `category`, `claimed_published_at` | Federal Register, EU Official Journal, national regulators |
| `news_item` | `title`, `lede`, `url`, `outlet`, `outlet_class`, `claimed_published_at` | Wires, trade-press RSS, GDELT |
| `ownership_edge` | `parent`, `child`, `relation` (`direct_parent`, `ultimate_parent`, `subsidiary_listed`), `source_document` | GLEIF relationship data, Exhibit 21 |
| `instrument_map` | `entity`, `instrument`, `instrument_type` (`equity`, `bond`, …), `figi`, `venue` | OpenFIGI |
| `customer_disclosure` | `discloser`, `customer_name_as_filed`, `share_band`, `period` | 10-K segment notes (extraction is an attachment; see 4.2) |
| `scheduled_fact` | `subject`, `fact_type`, `scheduled_for`, `url` | IR calendars via Wayback, filings |
| `index_level` | `index`, `value`, `unit` | Free freight indices, published assessments |
| `listed_area` | `list`, `area`, `action` (`added`, `removed`) | Joint War Committee listed areas |
| `quote` | as spec v4 §9.4 | Prediction markets (recorded) |

**Text policy.**
- Store title, lede and URL. Store bodies only where the source's terms allow it; SEC and Federal Register are public domain.
- `claimed_published_at` is what the source says. `knowable_at` is what we can prove (G6.2).
- Raw text stays in the cache, never in git.

### G4.2 Attachments

Spec v4 §4 splits **substance** (deterministic, no model) from **attachment** (links, tags, matches, possibly from a model, pinned and cached). The current contract has no attachment type, so consumers can't receive them. Add:

```python
@dataclass(frozen=True)
class ModelIdentity:
    model_id: str                 # e.g. "laya-multilingual"
    checkpoint: str               # content hash of the weights actually used
    trained_through: datetime | None
    # latest knowable_at of ANY data the checkpoint learned from (base pretraining
    # included). None = unknown; consumers must treat unknown as the model's
    # release date, never as "old enough".

@dataclass(frozen=True)
class Attachment:
    id: str
    kind: str                     # "entity_link" | "event_cluster" | "category" | "extraction" | ...
    targets: tuple[str, ...]      # Record ids this attaches to
    value: dict                   # labels with FULL probability distributions, never a bare argmax
    provenance_class: str         # "linked" | "extracted" | "matched" | "labelled"
    method: str                   # "rule" | "model"
    model: ModelIdentity | None   # required iff method == "model"
    input_hash: str               # hash of exactly what the model or rule saw
    question_set_hash: str | None
    computed_at: datetime
```

**The model time wall is the rule that makes attachments point-in-time.** An attachment produced by a model is servable at `as_of = T` only if **all** of these hold:

1. Every target record has `knowable_at ≤ T`.
2. `model.trained_through ≤ T`. A model that learned from data after T can leak post-T knowledge into a label about T.
3. If `trained_through is None`, the model's public release date stands in for it.

Otherwise the attachment is withheld. With `include_anachronistic=True` it is returned flagged `anachronistic`, and a consumer must never use a flagged attachment in a clean evaluation.

`trained_through: None` is permitted on the contract type because a source may genuinely not know it, but **no caller ever runs against an unknown cutoff**: `decider` resolves `None` to the model's public release date at registration (Section E §23.1), and rule 3 above applies to anything that reaches the layer unresolved.

This is the same time wall Nomad applies to documents, applied to models. It is what lets Laya checkpoints trained per window serve backfilled rounds honestly, and it restricts any model with a recent or unknown cutoff to live use automatically — no special rule needed.

### G4.3 Protocol additions

```python
class DataLayer(Protocol):
    # existing: layer_id, layer_version, sources(), capabilities(), stream(), query()

    def attachments(self, targets: list[str], as_of: datetime,
                    kinds: list[str] | None = None,
                    include_anachronistic: bool = False) -> list[Attachment]: ...

    def search(self, text: str | None, kinds: list[str],
               window: tuple[datetime, datetime], as_of: datetime,
               subjects: list[str] | None = None,
               limit: int | None = None) -> SearchResult: ...
```

`SearchResult` carries `records`, `complete: bool` and `truncated_reason: str | None`.

**Search raises on truncation.** A truncated result is never returned as if complete, because a cut-off search reads exactly like "nothing related found" — the trap already met with Algolia at 1,000 results and with EDGAR's stale `items=` bodies.

**Point-in-time search is new.** Over recorded streams (G6), `search(..., as_of=T)` searches only what was captured by T. This gives Nomad a point-in-time search it has never had: the Q1a window search becomes as-of and truncation-safe for any window after recording began.

**Capability flags.**
- `Capability.ATTACHMENTS` is declared only when `attachments()` is implemented and obeys 4.2.
- `Capability.RECORDING` is declared when at least one stream is recorded (G6).

---

## G5. The product

### G5.1 Modules

```
dataprod/
  adapters/      one module per source: declaration(), fetch_raw(), normalize()
                 (normalize is pure, and never touches the network — conformance)
  recorders/     scheduler + capture + revision/withdrawal detection (G6)
  store/         persistent store (G5.2)
  spine/         entity spine: ids, aliases, PIT tickers, ownership, instruments
  xref/          field algebra, /relate, event spine (spec v4 §10)
  attach/        attachment engine: rules + decider models (G7)
  dataset/       freeze, manifest, verify, rebuild
  api/           Python client (in-process DataLayer) + MCP server
  docs/          spec.md (spec v4 Part II), STATE.md
  tests/         product tests; -m historical for real-source tests
```

### G5.2 Persistent store

The current layer is in-memory over a raw cache (`STATE.md` A1: partial). A second consumer, plus recorders that run continuously, needs a store.

- **Raw capture stays in the content-addressed cache** (as now): gzipped, keyed by source, identity and hash, and never in git.
- **Normalized records go to an append-only store.** Recommended: SQLite in WAL mode for the index, plus Parquet partitions per `(source, month)` read through DuckDB.
- **Records are never updated in place.** A revision is a new record with the chain fields set, and a withdrawal is a new observation record.
- **The store can be rebuilt from the raw cache by re-running `normalize`.** Rebuild equality is checked against the manifest (G5.4).

### G5.3 Versions are content hashes

`layer_version` today is the hand-set string `"0.1.0"`. Ohmni's own finding applies here: the changes that matter are the ones nobody remembers to bump. So:

- `layer_version` is the hash of `dataprod` source plus all adapter declarations.
- The attachment engine's version is the hash of its rules plus the question sets plus the model checkpoints in use.

Both go into every response's determinism receipt.

### G5.4 Dataset freeze

Unchanged from `harness/dataset.py`: freeze by content hash, write a portable per-file manifest (root name plus relative path), and have `verify_against_manifest` name what is missing, changed or extra.

**New:** recorded streams freeze by **capture log**, not by fetch. The manifest for a recorded source is the hash chain of its capture log up to the freeze point, so "the same recorded data" is provable too.

### G5.5 API and MCP server

**In-process:** a `DataLayer` implementation (`dataprod.api.Layer`) for Python consumers.

**MCP server tools:**

| Tool | Parameters |
|---|---|
| `dp_sources` | — |
| `dp_capabilities` | — |
| `dp_query` | `subject`, `kind`, `window`, `as_of` |
| `dp_stream` | `start`, `end`, `subjects` |
| `dp_search` | `text`, `kinds`, `window`, `as_of`, `subjects`, `limit` |
| `dp_attachments` | `targets`, `as_of`, `kinds`, `include_anachronistic` |
| `dp_relate` | `a`, `b`, `as_of` |
| `dp_session_pin` | `as_of` — pins the session's clock; a later `as_of` then raises |
| `dp_receipt` | — |

**MCP rules** (from spec v4 §12):
- `as_of` is required on every read, and the server can pin it per session (`dp_session_pin(as_of)`). After pinning, a read with a later `as_of` raises.
- Every response carries the determinism receipt: `response_hash`, `layer_version`, `contract_version`, `vocabulary_version`, `concept_map_version`, `attachment_engine_version` and `substance_only`.
- `substance_only=true` drops all attachments.

**The guard exists on both sides** (spec v4 §2.1). The product refuses reads without `as_of`, and each harness separately refuses any read past its own clock. Neither trusts the other.

---

## G6. Recorders

Spec v4 §9.8 and `STATE.md` A10: "the only item with a clock on it". For Nomad, recorders are also what makes Q9 enumeration honest, because RSS and announcement pages keep only recent items.

### G6.1 Behaviour

A recorder is an adapter in recording mode.

- **It polls on a declared schedule.** Every poll is logged, including empty ones and failures.
- **It captures the raw payload** with `captured_at` and a content hash, into the cache.
- **Item identity** is the source's own id (`guid`, accession, announcement id), falling back to a normalized URL.
- **An edit is a new revision.** Same identity with a different content hash becomes a new revision link, never an overwrite.
- **A withdrawal is detected and recorded.** If an identity that was present is absent from a later poll within the source's declared listing depth, it becomes a `withdrawn` observation with `observed_at`. Survivorship is preserved from recording start onwards.
- **Gaps are recorded, never smoothed.** A missed or failed poll produces a coverage gap. Queries touching the gap return `not_covered` for that interval, never an empty result that looks like silence.

### G6.2 Time fields

| Field | Meaning |
|---|---|
| `knowable_at` | `captured_at` of the first capture: what we can prove. Conservative by construction |
| `value.claimed_published_at` | What the source says. Kept, never used for gating |
| `event_time` | The event the item describes, when the item states it; otherwise `claimed_published_at` |

The gap between `claimed_published_at` and `knowable_at` is a declared per-source statistic (median and 95th percentile). It is reported, not hidden.

### G6.3 Declaration for a recorded stream

- `retrieval = AS_OF` for `[recorded_since, now]`.
- `historical_access = RECORD_ONLY`.
- `record_survivorship = COMPLETE` from `recorded_since` onwards. Before that point, queries return `not_covered` with the reason `before_recording`.
- `recorded_since` is part of the declaration and part of every manifest.

### G6.4 First recorders, in priority order

Priority is set by what is lost soonest if not recorded, then by what Nomad needs most.

| # | Stream | Why now |
|---|---|---|
| 1 | JPX TDnet timely disclosures | Short public viewing window (verify the length); Japanese holders appear on metal and chemical nodes |
| 2 | ASX company announcements | Australian miners and processors |
| 3 | HKEXnews announcements | Chinese and Hong Kong holders |
| 4 | LSE RNS | UK-listed holders |
| 5 | Regulator and ministry feeds per node class | Starting with the classes rounds have hit: mining safety, energy, trade remedy, EU competition |
| 6 | Trade-press RSS headlines per vertical | Metals, energy, shipping, chemicals. Headline and lede only |
| 7 | Prediction-market quotes (Polymarket, Kalshi) | For the external benchmark on `headline` rounds |
| 8 | Wayback save-page-now over every IR and notices page in the names book | Carried from Nomad v9 §D. The cheapest ingest, feeding scheduled facts and point-in-time fetches at once |
| 9 | Joint War Committee listed areas | Changes are rare but decisive |

**Language rule.** Non-Latin-script feeds (TDnet, HKEXnews) must never be read by an English-only model checkpoint (G7.2).

---

## G7. Attachments engine

### G7.1 What the product attaches (neutral only)

The product attaches only what any consumer could use.

| Attachment | Method | Notes |
|---|---|---|
| `entity_link` | rule first (exact identifier, exact versioned alias); model second (a choice over candidate entities from the spine) | Resolution confidence travels with the link |
| `event_cluster` | rule (identifier-exact, declared tier-2 window); model for tier 3 (does item B concern the same occurrence as item A) | Builds the event spine and `first_knowable_at` (spec v4 §10.3) |
| `category` | model, over a published neutral taxonomy (e.g. `closure`, `outage`, `strike`, `insolvency`, `rule_change`, `recall`, `force_majeure`, `price_move`, `other`) | Versioned taxonomy |
| `extraction` | regex finds candidates; a model picks among them | For customer disclosures and similar. The model only picks; it never generates |

**The product never runs a consumer's questions.** Nomad's Q3–Q6 reading, notice detection against open calls, link wiring and spread probes run in Nomad's harness, on the same `decider` runtime. The rule: if a question would be meaningless to someone building a stock screener, it doesn't belong in the product.

### G7.2 Model use

- **Models come from `decider`** (Section E §23), with pinned checkpoints and recorded calls.
- **Every model attachment carries `ModelIdentity`** and obeys the model time wall (G4.2).
- **Language routing is mandatory.** Laya's English checkpoint is confidently wrong on non-Latin scripts (the model card reports 0.000 accuracy at 0.952 confidence on Khmer), so non-Latin input goes to the multilingual checkpoint via Laya's router.
- **Nothing an attachment says ever enters a substance field.**

---

## G8. Conformance and tests

### G8.1 Existing suite, now in `testkit`

The existing conformance suite (15+ checks, including normalize determinism and `no_network_in_read`) moves unchanged. Nine adversarial and seven degraded fixtures move with it.

### G8.2 New checks

| Check | Rejects |
|---|---|
| `no_property_defaults` | A declaration that constructed without explicitly setting `historical_access`, `measurement_type`, `records_of` or `role` (checked by introspecting the source's declaration call, not only the resulting value) |
| `vocabulary_guard` | Any consumer word appearing as a **whole identifier** in `contract` or `dataprod` source: `root_set`, `frames`, `residue`, `spark`, `EffectClaim`, `ACK`, `holder`, `leg`, `basket`, `effect_dag`. Matching is identifier-exact (word-boundary, not substring), so a legitimate field is not banned by a substring of its name. The list is maintained in `testkit`. **`basis` is deliberately absent**: it is too common a word to ban on its own, and the harness meaning is carried by `root_set` and `frames`, which are banned |
| `truncation_raises` | A `search` returning fewer items than the source reports with `complete=True` |
| `anachronistic_attachment` | An attachment served at `as_of < model.trained_through` without the flag |
| `recorder_gap_typed` | A query over a recorded gap returning empty instead of `not_covered` |
| `capture_time_gating` | A recorded record whose `knowable_at` is earlier than its first `captured_at` |

### G8.3 Import rules as tests

An import-linter configuration (or an equivalent test walking the import graph) enforces the G1 table. It runs in every package's CI.

---

## G9. Acceptance criteria

Isolation is done when all of these pass.

1. `pip install contract` in a clean environment succeeds and `import contract` pulls nothing internal.
2. The Ohmni harness test suite passes with `contract`, `testkit` and `decider` installed and **`dataprod` absent**.
3. The Nomad harness test suite (once written) passes under the same condition.
4. `dataprod` passes the full `testkit` conformance suite, including G8.2, with no special cases.
5. `dataprod` rebuilds its corpus from the manifest and `verify_against_manifest` reports zero missing, changed or extra files.
6. The import-linter contract passes in all packages.
7. The MCP server refuses a read without `as_of` and, after `dp_session_pin`, refuses a read past the pin.
8. `dp_search` over a deliberately over-limit query raises (or returns `complete=False` with a reason); it never returns a silent partial.
9. An attachment from a checkpoint with `trained_through` after `as_of` is withheld, or returned flagged.
10. Ohmni's report 003 run reproduces bit-identically against the isolated product (same freeze hash, same results). **The isolation must not change a single number.**

---

## G10. Migration steps, in order

1. **Freeze first.** Record the current dataset freeze hash and re-run report 003's protocol to get a reference output.
2. **Split history.** Create the new repository (or packages), carrying history with `git filter-repo` on `contract/`, `data_layer/`, `fixtures/`, `conformance/`, `harness/dataset.py`, `scripts/rebuild_dataset.py` and `.dataset/`.
3. **Move the degradation table** into `ohmni-harness` and point `obligations.py` at it. Run the obligations matrix test.
4. **Remove the property-asserting defaults.** Fix every adapter declaration the change breaks. Each break is a place a property was being asserted by accident, so review each one rather than pasting the old default back in.
5. **Replace `Phenomenon` with the vocabulary registry.** Map the existing eight members one-to-one.
6. **Move `fixtures/` and `conformance/` into `testkit`,** rewrite imports and run both suites.
7. **Move the validity matrix** into `dataprod/xref/`.
8. **Switch to content-hash versioning** and add the receipts.
9. **Wire the import-linter.**
10. **Re-run the reference** from step 1. It must match bit for bit before anything new is added.
11. Only then add the new work: the store, recorders, `attachments()`, `search()`, and the new kinds and adapters.

Steps 1–10 change nothing a result depends on. Step 11 is new product work and can proceed in parallel with the Nomad build.

---

## G11. Adapters Nomad needs (after isolation)

All free, in rough order of value to Nomad. Each gets a full `SourceDeclaration` and passes conformance before use.

| Adapter | Kinds | Access | Notes |
|---|---|---|---|
| EDGAR filings index (8-K items by own metadata) | `filing_item` | bulk | Enumerate day by day and filter on each filing's own `items` array. **Never trust `items=`**: it served stale bodies in Nomad blind run 2 |
| Exhibit 21 | `ownership_edge` | bulk | Listed parent to subsidiaries, per filing date |
| GLEIF with relationship data | `ownership_edge`, entity ids | bulk | Direct and ultimate parents for non-US holders |
| OpenFIGI | `instrument_map` | metered (free tier) | Includes bonds (open question 4) |
| 10-K segment notes, major customers | `customer_disclosure` | bulk | Rule candidates plus a model pick, as an attachment |
| Exchange announcements (TDnet, ASX, HKEXnews, RNS) | `announcement` | record-only | G6.4 |
| Federal Register, EU Official Journal | `regulatory_notice` | bulk | Also the docket source for Nomad's procedural chains |
| National regulators and ministries | `regulatory_notice` | record-only | Per node class, added as rounds need them |
| Trade-press RSS | `news_item` | record-only | Headline and lede |
| GDELT GKG bulk | `news_item` volumetrics | bulk | Exists; `gkgcounts` is the tractable variant |
| Daily prices, US | `price` | metered / free tier | Massive's free tier gives end-of-day data with two years of history; survivorship absent, so declare it |
| Daily prices, non-US | `price` | varies | Source per venue; declare survivorship honestly |
| Free freight indices | `index_level` | varies | Where terms allow |
| JWC listed areas | `listed_area` | record-only | G6.4 |
| Wayback CDX | first-capture timestamps | metered | The timestamp arbiter for mutable pages |
| Prediction markets | `quote`, contract, resolution | record-only / bulk | Spec v4 §9.4 |

---

## G12. What this does not decide

- **The product's name**, and whether it is ever offered to anyone else. Isolation keeps that option free and costs nothing either way.
- **Whether GLEIF relationship data, OpenFIGI and each exchange feed's terms allow storage and redistribution** of what we derive. Check each before recording. For Nomad's shape C (selling the map), redistribution rights are the constraint that matters.
- **The event-spine tier-2 window.** It is declared, never tuned, and has to be set once (spec v4 §10.3).
- **Whether `decider` lives in the product's repository or its own.** Either works under the import rules.
