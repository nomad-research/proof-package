# K10 authoring package: rounds 1-7 only

Built from the frozen v15 ledger. Every ledger-derived item below was created before `2026-09-07T14:20:29.313933Z`, the creation time of the first round under test. Nothing later is in this file.

## A. What an obligation template is (format-defining extracts of the v16 spec)

### A1. From section 3

- **Obligation templates are a new rule kind** (`kind = obligation`), carrying `occurrence`. Each names the conjunction of positions that makes a notice unavoidable, and what it forbids: *no notice of this kind without this conjunction*. Derived ACKs (§22.2) are computed from them, and are always forced.

### A2. From section 4

**Three timing classes:**
- **`scheduled`** — calendared: results dates, regulatory deadlines, index events.
- **`forced`** — obligations whose timing is not public: an FM letter must come when a producer can't serve contracted offtake; a restart statement must come; a regulator must answer inside a statutory window.
- **`discretionary`** `[fold]` — no obligation and no clock. It is recorded as conditioning, never as an ACK.

A system that advances only on calendared facts advances only where the market is already looking, and inherits pricedness by construction.

**Derived ACKs: the AND runs over positions** `[gate]`. The old gate ran an AND over each leg's risk terms. The new one runs it over the set of positions, cross-referenced. For example: the supplier is short, the buyer holds a contracted offtake, no substitute exists inside the window, and inventory is below N days. When every condition in an obligation template is documented true, the notice is an obligation, not a guess, and a forced ACK is derived. If some conditions are unknown and none is false, the result is a **switch**: an ACK candidate whose missing facts become a fetch list. If any condition is false, there is no ACK. The operator ratifies every derived ACK (§22.2).

### A3. Section 22.2 in full

### 22.2 Derivation `[gate]`

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

### A4. From section 18.3: the four tables a template file feeds

| Table | Kind | Key fields |
|---|---|---|
| `position_attributes` | mutable | `attribute`, `type` (`numeric`/`enum`/`bool`/`text`), `unit`, `allowed[]`. Seeded with v15's six, plus the ones templates test: `inventory_days`, `contract_type`, `hedge_ratio`, `input_share`, `capacity`, `substitute_lead_days`, … |
| `bounds` | mutable | `bound_id`, `subject` (asset class, process type or statute), `quantity` (`lead_time_days`/`rebuild_days`/`statutory_min_days`/`inventory_norm_days`/…), `value`, `source_document`, `knowable_from` |
| `obligation_templates` | mutable | `template_id` (also a library rule id, `kind = obligation`), `node_types[]`, `roles[]`, `conditions[]{role, attribute or bound, op, value}`, `forces` (the `notice_kind`), `carrier_kinds[]`, `window_rule` (statute, procedural chain or none), `forbids`, `authored_from_rounds[]` |
| `ack_derivations` | ledger | `derivation_id`, `round_id`, `segment_id`, `clock`, `template_id`, `bindings{role: holder/asset}`, `conditions[]{position_ids[], state (true/false/unknown), evidence_ids[]}`, `result` (`forced`/`switch`/`none`), `fetch_list[]`, `ack_id` |

The spec asks for: templates, bounds and position attributes authored from rounds 1-7 only.

## B. The record of rounds 1-3 (played in chat, imported)

# Nomad — Session Record, Rounds 1–3

Operator: Claude (cutoff end-January 2026). All three rounds played in chat: commitments written before any search; self-scored by web search afterward; contamination status noted per round. The firewall in these rounds was a promise, not a wall — the harness replaces it.

Evidence URLs from the scoring searches were not retained across a context compaction. Each resolution below carries the fact and its source *type*; re-attach URLs at seed time only if the harness insists.

---

## Round 1 — 2026-04-03 — US strikes on Iranian civilian infrastructure

**Prompt as given:** "Trump Warns of 'Much More to Follow' as U.S. Bombs Civilian Infrastructure in Iran," April 3, 2026.

**Contamination:** none before lock. Peeking permitted after lock for learning.

**Frame at lock:** treated as a fresh escalation from a calm-ish baseline. *This was the round's dominant error* — the event was ~day 34 of a war begun February 28 with coordinated US–Israeli strikes; Hormuz was already effectively closed (~20% of world oil disrupted); Brent ~$109 after a +7.9% move on April 2.

**Mechanisms used at lock (pre-library, named in-round):** chokepoint premium; supply-fear-with-a-fade; substitute's gift; dark-factory chain (stalled-output propagation); route closure; escalation-words-are-cheap.

### Commitments and resolutions

| # | Call | Mechanism | Outcome | Mechanism outcome | Note |
|---|---|---|---|---|---|
| 1 | Crude up 5–12% immediately, round-trips within ~2 weeks unless Hormuz transit physically hit | supply-fear-with-a-fade | **hit** | **wrong → quarantined** | Brent fell below $100 within weeks — but on ceasefire talks (MoU signed June 17), not fear decay; and the "unless Hormuz hit" carve-out had *already fired* before the round. Right call, wrong relation. |
| 2 | Tanker rates up and stickier than crude | chokepoint premium + route closure | **hit** | right | VLCC ~$474k/day April 17 (4× pre-war ~$117k), ~$498k later; war-risk premia 3–10% of hull into July while crude round-tripped. Relative claim validated; absolute "up" was pre-priced. |
| 3 | Methanol/urea producers outside region up over 2–3 weeks; "no day-one journalist names methanol" | dark-factory chain + substitute's gift | **miss** (as a trade) | right (as mechanism) | Mechanism enormous (SE Asia methanol +72%; urea ~$780/t mid-April; 800kt stranded) but mainstream by March 20–25. April 3 entry ≈ top; urea then −36%. Obscurity had been consumed weeks earlier. |
| 4 | Defense up | baseline | hit | n/a (baseline) | Declared zero-edge. |
| 5 | Airlines down | route closure | **unverified** | unknown | Not checked. |
| 6 | Gold and vol up, then fade absent a second strike | escalation-words-are-cheap | gold hit; vol **untestable** | unknown | Strikes never stopped; antecedent never held. |

**Baseline comparison:** dumb baseline ("energy up, defense up, equities down"). Baseline missed the oil fade; matched defense. Net ≈ tie.

**Miss classification:** frame miss (misread of sequence position), not missing mechanism. Leg 3 = misweight (highest conviction on a five-week-old channel).

**Library entries produced:** novelty belongs to channels, not events · my freshness is not the market's · late in a crisis the neglected side is resolution · the toll booth learns before the cargo · constraint prices de-escalate slowest.

**Predicate checks (retro):** first-traversal (event) — claimed holds, observed **fails**. Tradability gate — not claimed; observed fails (everything priced).

---

## Round 2 — 2026-03-12 — fire at a propylene oxide plant, Pasadena, Texas

**Prompt as given:** "March 12, 2026: a fire at a propylene oxide plant in Pasadena, Texas."

**Contamination:** none. Clean prompt (no operator, no casualties, no adjectives).

**Checklist at lock:** Q1 pass with a flag — war backdrop contaminates absolute prices, so claims made relative/incremental; Q2–Q8 pass; Q5 leaned on ("passed the materiality screen, so central case is a real outage").

**Map derived from training at lock:** operator most likely LyondellBasell Bayport (PO/TBA technology); US PO capacity a handful of Gulf Coast plants across ~4 companies, one world-scale unit ≈ 15–20% of US supply; product region-locked (hazardous to ship); ~2/3 to polyols → PU foam, rest to propylene glycol and glycol ethers; co-product TBA → MTBE (or styrene if PO/SM; none if HPPO). **Map confirmed:** Bayport Choate, "world's largest PO/TBA facility."

### Commitments and resolutions

| # | Call | Mechanism | Outcome | Mechanism outcome | Note |
|---|---|---|---|---|---|
| 1 | Operator equity dips 1–4%, recovers ≤6 weeks; falsifier −10% sustained | visible-victim overweighting | **untestable** (swamped) | unknown | Owner *upgraded* by a bank the same day on a war-driven sector trade; stock ran ~+30% in weeks. Outage cost ~$250M EBITDA, restart June — inside a quarter where EBITDA tripled to $2.1B. Event ÷ tide ≈ invisible. Small day-after relative underperformance only. |
| 2 | Force majeure on PO and/or derivatives within 14 days if material | force-majeure-fast-carrier | **hit** | right | PG FM effective March 13 (day 1); PO FM March 17 (day 5); CFO confirmed constraint at a conference March 17. Faster than predicted. |
| 3 | US PO spot jumps within days; +10–40% over the month; demand slump may mute | cargo-learns-first + region-locked capacity concentration | **hit** | right | March contract +8¢ to 69.5¢/lb (+13%); early-April spot sharply firmer on FM; cautious downstream buying capped upside (mute confirmed). |
| 4 | Remaining US PO producers outperform owner by 2–6% over 6–8 weeks | substitute's gift | **miss / untestable** | wrong (self-hedge missed) | Sector moved together on the war tide; owner holds sister PO plants and collected its own scarcity premium; no evidence the spread paid. |
| 5 | Co-product (MTBE) firms 1–3 weeks after, incremental step; obscure | co-product collateral | **miss** | wrong | Global MTBE in Chinese-overcapacity glut, prices flat-to-down 2026; a sell-side analyst named the MTBE link within 5 days. Cut into a glut; not obscure to specialists. |
| 6 | Polyol/PG +5–20% over 4–6 weeks; foam-cost mentions on next earnings calls | chain lag | **hit** (direction/speed) | right, magnitude timid | April flexible slabstock polyol +20¢ (+28%); MPG +31.5¢ (+34%); foam costs +15–20% *within days*; allocation letters. Earnings-call mentions not verified. |
| 7 | Local propylene softens at margin | feedstock backwash | **unverified** | unknown | Logging leg; war noise dominates. |
| — | One-trade statement: long US PO competitors vs owner, 6 weeks | — | flat-to-loss | — | See 4. |

**Baseline comparison:** baseline ("owner down, nothing else") was wrong on both halves. Operator beat baseline decisively on chain legs (2, 3, 6); both failed equities.

**Miss classification:** leg 5 = missing mechanism (slack gates transmission) + misread of obscurity; leg 4 = missing mechanism (owner-of-substitutes self-hedge); leg 1 = misweight (macro vs micro); leg 6 = misweight (magnitude timid).

**Library entries produced:** a cut into a glut is silent · the wounded owner of the substitutes collects its own scarcity premium · equity visibility = event size ÷ ambient tide · the move is largest where substitution is hardest · a lag without a listed pure-play is a spectacle, not an edge · specialists already hold my map.

**Predicate checks (retro):** first-traversal (event) holds; slack check — not claimed at lock, observed fails for the co-product; tradability gate (single) — claimed weakly, observed fails; tradability gate (pair) — observed *fails for the right reason* (owner on both sides).

---

## Round 3 — 2026-04-09 — bunker spill closes the Scheldt / Deurganck Dock, Antwerp

**Prompt as given:** "April 9, 2026: a bunker spill at Deurganck Dock halted seagoing traffic at the Port of Antwerp-Bruges for much of the following day."

**Contamination:** none. Q8 mild leak: "much of the following day" gave duration — and duration was the load-bearing variable.

**Checklist at lock:** Q1 unknown at node level (flagged); Q5 materiality explicitly questioned; Q7 thin on listed parties by design.

**Map at lock:** left-bank container dock, two large private terminal operators; seagoing halt implies the river approach closed, i.e. the whole port; ~250–300 movements / ~35k TEU per day; backdrop of war-driven European port congestion.

### Commitments and resolutions

| # | Call | Mechanism | Outcome | Mechanism outcome | Note |
|---|---|---|---|---|---|
| 1 | No attributable equity move anywhere; falsifier: any listed party >2% day-after with press attribution | event ÷ tide; no listed pure-play | **hit** (null) | right | No attribution found. Weight 0.2. |
| 2 | No step in European container spot indices attributable to Antwerp within 2 weeks | schedule perturbation ≠ supply shock | **hit** (null) | right | No index commentary citing the closure. Weight 0.2. |
| 3 | Operational ripple 1–3 weeks: bunching, yard density, barge delays; longer if baseline congested | congestion has memory | **hit** | right | River reopened 13:30 April 10; dock shut ~4 days (berths from April 13); locks ~2 days; ~85,000 TEU lost per port H1 report; carrier advisories of omissions and backlog into the following week; trade press framed it as adding to congested European ports. |
| 4 | Liability lands on a small party; no rule change | liability-to-periphery | **partial** | partly wrong | Responsible vessel belonged to the world's largest container line (private). No rule change found. |
| 5 | Meta: do nothing; event fails tradability gate by construction | tradability gate | **hit** (null) | right | Correct non-shock. |

**Duration misplacement:** read the headline's node (river, half a day) not the smaller node that stayed shut (dock, four days). Estimate of TEU lost was >2× too low.

**Q1 wobble (node level):** four-day nautical-chain strike in March (~100,000 TEU), pilot action in June, toxic leak at the same dock in July — the node is a recurring-disruption node; first traversal held at the event, not the node.

**Baseline comparison:** baseline ("shipping stocks down") had no evidence; operator's null was right. Scored low: a null is cheap.

**Library entries produced:** recurring disruption is priced as weather · the headline names what reopened, not what stayed shut · tradability gate promoted from candidate to predicate.

**Predicate checks (retro):** first-traversal (event) holds; first-traversal (node) — not checked at lock, observed **fails**; tradability gate (single and pair) — claimed fails, observed fails.

---

## Across the three rounds

- Map skill is real (round 2 derived operator, technology, chain, co-product from training).
- The lag exists and is large in contract/commodity/insurance space; equity trace: 0/3, three different dilution mechanisms (pre-priced; micro ÷ macro plus self-hedge plus private downstream; no listed pure-play).
- Obscurity window in a hot crisis ≈ 2–3 weeks; specialists hold the map within days.
- Arming rate 0/3. Nulls: 3 calls at weight 0.2.
- Vocabulary loss across a context reset: ACKs reinvented as "trigger"; repaired in v4.

## B4. Round 4 recap

# Round 4 — 2026-04-14 — boiler explosion at a thermal power plant, Sakti district, Chhattisgarh

**Round id:** `01a078cb-69c8-7075-ac27-7d6c2424193c` · **Operator:** [operator model] (cutoff 2026-06-30) · **Played:** 2026-09-06/07 over stdio from Claude Code

**Contamination flag:** Q2 (post-operator-cutoff) FAILS for this operator; the event sits inside its training window. Operator reports no specific recall; latent exposure cannot be excluded. Recorded in the event criteria and the first scorer note. Human decides whether the round stands or is voided.

**Firewall checks before lock (all refused, no ledger rows written):** evidence before lock · empty mechanism list without a reason · company name in rule text · unknown name diverted to orphans. **After scoring:** WebSearch with no open round → denied by the PreToolUse hook.

## What it was

Vedanta Ltd's Chhattisgarh Thermal Power Plant (ex-Athena) at Singhitarai, Dabhra tehsil: 2×600 MW supercritical, Unit 1 at COD since mid-2025, **Unit 2 still under construction**. Steam tube from Boiler 1 ruptured at 14:30; death toll 24 by 19 Apr; victims were staff of NGSL (NTPC-GE JV), the O&M contractor. Cause per probes: unburnt fuel accumulation and continued load ramp despite PA-fan faults. FIR names the group chairman. Unit 1 shut from 14 Apr; restart guided for end Q2 FY27 (30 Sep 2026). Vedanta Power (demerged, listed 15 Jun 2026) reported Q1 FY27 segment EBITDA −30% YoY because of it.

## Scorecard

| | |
|---|---|
| outcome_score | 0.43 |
| mechanism_score | 0.43 |
| baseline_score | 0.00 |
| edge_vs_baseline | +0.43 |
| null_called | yes (2 nulls at 0.2) |
| tradability gate | claimed fails, observed fails → **not armed** |
| unverified | 2 of 9 |

## Calls

| # | Call | Result | Note |
|---|---|---|---|
| 1 | Map: private IPP in Dabhra cluster, 300–600 MW unit, plant keeps running on other units, contract-worker casualties | **miss** | Owner, cluster, unit size, casualties right; Unit 2 not built so the whole site stopped. Falsifier fired. |
| 2 | Unit offline for months (≥3) | **hit** | Shut 14 Apr; restart guided end Sep. Baseline "weeks" wrong. |
| 3 | No attributable step in IEX day-ahead prices | **hit** | April DAM ₹5.26, +1% YoY, weather-driven; no source mentions the outage. |
| 4 | State orders inspection/audit of peer plants within 14 days | **miss** | Probes of the plant itself only; no peer-plant order found (English sources). New rule takes its first miss. |
| 5 | Owner notifies offtaker of shortfall / force majeure within 30 days | unverified | 200 MW TNPDCL PPA exists; no public notice found. |
| 6 | Magnitude ordering: physical > owner cash flow > coal > grid > equity | **hit** | Held exactly. |
| 7 | Null: no attributable equity move anywhere | **hit** (0.2) | Vedanta +1.79% / +2.19% day-after (demerger, metals); −1.39% on FIR day, under threshold. Baseline "owner down" wrong. |
| 8 | Null: fails tradability gate, no listed pure-play | **miss** (0.2) | Scored strictly: the falsifier "a listed holder with concentrated exposure emerges" fired when Vedanta Power listed by demerger on 15 Jun. Gate was right at event time; the falsifier lacked a time bound. Human may supersede. |
| 9 | No attributable move in boiler OEM equity | unverified | OEM not identifiable from retrieved sources. |

## Predicates (claimed → observed)

first traversal fails → fails (node-level: recurring fatal accidents at Chhattisgarh plants) · slack fails → fails · tradability gate fails → fails · existence floor unknown → holds · path composition unknown → fails (only a stated edge) · bounded-channel absence unknown → fails (global headline day one) · catalyst class unknown → holds (dated restart guidance).

## Library

- Validated by the ledger this round: `lib.equity_visibility_ratio` (clean hits in rounds 3 and 4, no misses). `lib.route_closure` was validated at seed.
- Misses recorded on: the new inspection-order rule (proposed at lock).
- Four candidates harvested: tradability can arrive by corporate action (time-bound your falsifiers) · a revived stranded asset runs fewer units than nameplate · the attributable equity move comes with the criminal complaint, not the accident · for contracted power plants the first public carrier is the owner's quarterly, not a force majeure letter.

## Names book and positions

Added: Vedanta Limited (VEDL), Vedanta Power Limited (VEDPOWER, listed 15 Jun 2026), the plant (parent Vedanta Power), NTPC GE Power Services, TNPDCL. Node `vlctpp_singhitarai_generation`: every holder is sign −; **no opposing listed pair**; pair gate fails for the right reason.

## Standing hypothesis opened

A listed power pure-play created by demerger while a plant is shut trades at a discount to thermal-IPP peers until the guided restart and re-rates within four weeks of confirmed restart. Arming: catalyst class (restart by 30 Sep 2026), existence floor. Disarming: date passed, falsifier. Granularity locked: weekly relative move vs a pre-named peer set.

## Programme after four rounds

4 scored · arming rate 0/4 · mechanism scores 0.40, 0.57, 1.00, 0.43 (mean 0.60) · chain verified.

## For the human to decide

1. Keep or void this round given the Q2 failure for the current operator.
2. Whether to supersede call 8 (the time-bound falsifier point) or let the strict score stand.
3. Q7 in round 3 ("thin on listed parties by design") is stored as unknown; may be a pass.

## B5. Round 5 recap

# Round 5 — 2026-07-15 — fire at a refinery complex in Gelsenkirchen, Germany

**Round id:** `01a078f5-565b-769c-8238-058fa471626e` · **Class:** **clean** (contamination none; Q2 computed pass, event inside the window 2026-07-01 to 2026-08-10) · **Operator:** [operator model] (cutoff 2026-06-30, from `model_cutoffs`) · **Played:** 2026-09-07 through the harness API (the session's MCP server was still the pre-tightening build; same functions, same ledger) · **Scorer:** self (B2 second scorer starts at round 6)

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

## B6. Round 6 recap

# Round 6 — 2026-07-14 — hydrofluoric-acid container leak at Deurganck Dock, Port of Antwerp-Bruges

**Round id:** `01a07ae0-5349-775b-806d-e58237e1bea8` · **Class:** clean (Q2 computed pass; window 2026-07-01 to 2026-08-10) · **Operator:** [operator model] · **Played:** 2026-09-07 over stdio from Claude Code (new server) · **Scored:** self, then a blind second scorer (B2), 7 disputes over 9 calls awaiting the human.

**Same node as round 3.** The ledger already held the dock's 2026 history (March strike, April spill, June pilots, "a toxic leak in July"), so first traversal was claimed *fails* at the node from stored facts before lock. Hormuz blockade reinstated on the event day; tide note recorded.

## What it was

Evening of 14 July: a tank container of hydrogen fluoride developed a ~10 cm hole during loading aboard **MSC Mia Summer II** at MPET (possibly a twistlock). Toxic vapour cloud; **entire Deurganck Dock and the Kieldrecht lock closed**, waterway traffic in the area suspended, both terminals (MPET and DP World's Antwerp Gateway) shut. **186 assessed, 28 hospitalised, one in intensive care, no fatalities.** Antwerp Gateway resumed 15 July afternoon; MPET quay 1718 at 22:00 on 15 July; MPET declared safe 17 July 14:00; rail 20 July; **quay 1742 (north berth) still out ten days later with three damaged STS cranes and ~90 staff cars written off.** Ghent labour prosecutor opened a criminal investigation. WCI fell 2% on 16 July with no Antwerp mention; one trade headline said the leak "deepens congestion".

## Scorecard (operator, self)

| | |
|---|---|
| outcome_score | 0.73 |
| mechanism_score | 0.69 |
| baseline_score | 0.00 |
| map_score | 1.00 (falsifier terms) |
| misreads | 2 |
| tradability gate | claimed fails, observed fails → **not armed** |

## Calls and the two scorings

| # | Call | Operator | Second scorer | Dispute |
|---|---|---|---|---|
| 1 | Map: tank container on a vessel at MPET, part of terminal closed, contained in a day, no fatalities, other terminals open | **hit** (falsifier did not fire; scale badly under-called) | **miss** (claim as stated failed: whole dock, lock, waterways, other terminal closed) | outcome |
| 2 | Dock and terminal fully operational within 3 days | miss, mechanism right (misread) | miss, mechanism **wrong** | mechanism |
| 3 | No attributable step in indices or congestion commentary | miss, right (commentary clause fired) | miss, right | agree |
| 4 | No carrier omits Antwerp citing the leak within 7 days | **hit** | **unverified** (Hapag update unreachable, no Maersk advisory found) | outcome |
| 5 | Magnitude ordering physical > throughput > schedules > indices > equity | hit, right | hit, **unknown** | mechanism |
| 6 | Null: no attributable equity move in 3 sessions | hit | hit | agree |
| 7 | Null: fails tradability gate | **hit** | **unverified, coverage none** (positions store not in the evidence) | outcome |
| 8 | No regulatory order within 30 days; liability on shipper/packer | **hit** (order leg) | **unverified** (liability leg undecided; investigation points at employer) | outcome |
| 9 | No force majeure citing the leak | hit, unknown (no-mechanism) | hit, **right** | mechanism |

## My recommendation on each dispute (yours to decide)

1. **Map (1):** take the second scorer's **miss**. The falsifier did not fire, but the claim had three extent statements and two were false. The harvested rule below says why. If you take it, map_score goes to 0 and outcome to 0.59.
2. **Lag mechanism (2):** keep **right**. The cited rule (duration lives one node smaller) is precisely what happened; I failed to apply it. Under A13 that is a misread charged to me, not a debit to the rule. The second scorer read "mechanism" as the claim's implied mechanism, not the cited rule.
3. **Carriers (4):** take **unverified, thin**. I gave benefit of the doubt on a gap the evidence record itself flags.
4. **Magnitude mechanism (5):** keep **right** or accept **unknown**; low stakes. The ordering held and the equity-visibility rule operated. I lean keep.
5. **Tradability null (7):** keep **hit**, and fix the harness (done below): the positions store was read before lock and is in the ledger, but the blind view did not show it, so the second scorer could not see it. This is a view defect, not a scoring one.
6. **Regulatory (8):** take **unverified**. The liability half of my own claim is unsupported; the investigation's target is unknown.
7. **Chemical notices mechanism (9):** accept **right**; harmless either way since no rule was cited.

Breaking a dispute is one `nomad_resolution_supersede` with `scorer='human'` per call. If you take all six of my recommendations, the round lands at roughly outcome 0.46, mechanism 0.47.

## Predicates (claimed → observed)

first traversal event unknown → **fails** (June pilots inside 30 days) · node fails → fails (from the ledger) · slack fails → fails · tradability fails → fails · existence floor unknown → holds · path composition unknown → fails · bounded channel unknown → fails · catalyst unknown → holds (dated reopening statements).

## Library

- **Validated:** `lib.equity_visibility_ratio` (positive hits in both clean rounds, no misses, weight 1.86). First validation under the propagated weights.
- Harvested: a toxic release closes the whole shared space, not the failed asset · knowing the rule is not applying it (operator) · narrative and price diverge after a small shock; a price falsifier must name the price series only (operator).

## Names book, positions, node facts

DP World and Antwerp Gateway added. Node `deurganck_dock_container_handling`: seven holders, all sign −, no pair; MPET duration "3 days terminal; 10+ days north berth". Two node facts (the outage timeline; the port's H1 losses).

## Housekeeping

- Evidence batch was rejected once for three over-length excerpts and wrote nothing, as designed; resubmitted trimmed.
- Paywalled or blocked: Loadstar, Flows, Sourcing Journal body, Hapag-Lloyd updates, the port's crisis page. The north-berth reopening date is the natural B4 target for this node.

## Programme after six

Clean: 2 scored, arming 0/2, mechanism 0.32 and 0.69 (mean 0.51 before disputes). All: 6 scored, arming 0/6. Chain verified across 20 ledgers.

## B7. Round 7 recap

# Round 7 recap: July 21, 2026, a fire at a polyethylene plant in Sasolburg, South Africa

Round id `01a07b19-69fb-75dc-9802-fac853e0f859`. Clean (event after the operator cutoff, 48 days old at intake). First-qualifier selection; the selector's rejection list was not passed to intake, so `rejected_before` is 0 with that noted under Q9. Criteria pass (Q1 unknown, nothing on the node in our ledger). Node `sasolburg_polyethylene_output`, kind `fire`. First round played under the v7 protocol: reveal context, touched set, one claim per row, decomposed duration call, per-leg predicate checks, `meta` one-trade statement, second scorer with rule text.

## What the harness showed at reveal
Nothing. No holders, no node facts, no neighbours on the node. Eleven rules matched the kind tokens, led by `lib.equity_visibility_ratio` (validated, 2.26 going in). The touched set was built from the operator's own prior: seven rows, degrees 0 to 3, two candidate operators at degree 0 (Safripol HDPE; Sasol Polymers LDPE at Sasol One).

## Calls and outcomes (operator / second scorer)

| # | Call | Claim | Operator | Second | Notes |
|---|------|-------|----------|--------|-------|
| 0 | map | plant is Safripol's HDPE, not Sasol's | miss / n.a. | miss / n.a. | It was Sasol's Poly 3 (LDPE/LLDPE, Midland site). Baseline (the larger operator on site) was right. |
| 1 | sign 0, Sasol equity | no attributable move vs Top40, 3 sessions | hit / right | hit / right | SOL −2.4, +11.9, −3.9 pts vs Top40 on 22–24 Jul, all attributed to oil, the FY26 metrics released the morning of the fire, and the PIC stake. Nobody mentions the fire. Baseline "dips on the day" also hit on its letter. |
| 2 | sign −, KAP | KAP underperforms after Safripol is named | untestable / unknown | untestable / right | **Dispute (mechanism)**: condition never arose. Second scorer credits the victim-overweight rule for operating on Sasol instead. |
| 3 | lag_band weeks, decomposed (5 factors) | plant back within weeks | unverified (derived) / unknown | unverified (derived) / unknown | Binding factor (damage extent) unobserved; only the ethylene-feed factor scored (days). Sasol's 1 Sep results are silent on Poly 3. Coverage thin. |
| 4 | sign +, force majeure within 14 days | FM declared | miss / unknown | miss / wrong | **Dispute (mechanism)**: no FM found anywhere (ICIS paywalled). Operator: the rule does not predict FM occurrence, so it neither operated nor failed. Second: the first carrier was a newspaper, so the fast-carrier rule did not operate. |
| 5 | sign 0, local PE prices | no attributable rise above import parity in 4 weeks | hit / unknown | hit / unknown | Claim of absence under thin coverage, both scorers flag it. Baseline differs (miss vs unverified), not a dispute. |
| 6 | meta, one-trade | short KAP from naming day | untestable / unknown | untestable / unknown | Naming day never came. Baseline "no trade" hit. D6 comparison: legs 0 armed, trade untestable. |

Scorecard (operator, before the human rules the disputes): outcome 0.40, mechanism 0.50, baseline 0.60, edge −0.10, map 0.0, misreads 0, untestable 2/7, unverified 1/7. Zero legs armed of four checked; tradability gate fails on every listed leg (Poly 3 is one line of a 250 kt/y site inside R61bn of group EBITDA).

## What moved in the library
- `lib.equity_visibility_ratio` 2.26 → 2.86, still validated (8 hits, 0 misses).
- `lib.cut_into_glut_silent` 1.2 → 1.62 and **crossed to validated** on call 5. Flag: that hit is a claim of absence under thin coverage with mechanism unknown, quality 0.42. Worth a human look before the rule is treated as validated.
- `lib.force_majeure_fast_carrier` took a 0.7 debit on call 4 (1.2 → −0.4 in the operator view); the pending dispute suspends it (C1), so the rebuilt weight is back at 0.3 until you rule. The operator's own view is that the debit belongs to the citation, which is the existing operator rule "the operator attaches a rule to a call the rule does not carry".
- `lib.visible_victim_overweight` 0.18 → 0.78.
- Two disputes pending on this round; the human breaks each with `nomad_resolution_supersede` scorer `human`. Scorer bias over clean rounds now: self more lenient 8, more strict 2, of 16 compared. Most of the "lenient" count is second-scorer `unknown` where the operator said `right`.

## Basket
Seven legs on one node, three sign −, four sign 0 after the post-lock corrections (Safripol and KAP flipped to 0 once the plant was named as Sasol's). Twenty-one shared-node pairs, none opposing. No leg armed, none dated. The one-trade statement was never live.

## Lessons
- The map call was a coin flip dressed as a lean. The bare event wording carried no operator signal and the baseline (bigger operator on site) was the better prior. Two downstream rows (KAP, one-trade) died with it. Next time: make conditional calls on both branches or make none.
- Coverage on a single-line polymer outage in South Africa is one newspaper article. Restart, force majeure and local pricing all sit behind ICIS. Three of seven calls are unscoreable on the carriers named, which is a Q7 (checkable carrier) failure that intake marked unknown and should have marked fail for those carriers.
- The FY26 metrics release landing the same morning as the fire is a tide the operator could not have known at lock; the tide note records it.
- v7 mechanics all held under live use: touched set enforced, single-claim rows accepted, factors required and derived, per-leg predicate checks written, blind view carried rule text and reveal context, C1 suspended the disputed debit.

## C. Positions recorded in the names book before the cut

Columns are as stored. `knowable_from` blank means the row carries no stamp. `confidence` is `stated` (a document says it), `inferred` or `implicit`. `sign_of_exposure` is the sign of the holder's exposure to the event on that node.

| id | holder | holder kind | listed | node | attribute | value | unit | source | source_time | knowable_from | confidence | supersedes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01a076cc | LyondellBasell Bayport Choate | plant | no | us_propylene_oxide_supply | sign_of_exposure | - |  | operator force majeure letters, march 13 and 17 2026 | 2026-03-17 | 2026-03-17 | stated |  |
| 01a076cc | LyondellBasell Bayport Choate | plant | no | us_propylene_oxide_supply | share | 620 | kt/yr po capacity | cfo remarks at a bank conference, march 17 2026 | 2026-03-17 | 2026-03-17 | stated |  |
| 01a076cc | LyondellBasell Channelview | plant | no | us_propylene_oxide_supply | sign_of_exposure | + |  | training knowledge of site technology; sister plants sell into tightness |  | 2026-03-12 | inferred |  |
| 01a076cc | LyondellBasell Industries | company | yes | us_propylene_oxide_supply | sign_of_exposure | + |  | holds destroyed and scarcity-capturing positions on the same node (self-hedged) |  | 2026-03-12 | inferred |  |
| 01a076cc | LyondellBasell Industries | company | yes | us_propylene_oxide_supply | sign_of_exposure | - |  | holds destroyed and scarcity-capturing positions on the same node (self-hedged) |  | 2026-03-12 | inferred |  |
| 01a076cc | Dow Inc. | company | yes | us_propylene_oxide_supply | sign_of_exposure | + |  | training knowledge of us po producer set |  | 2026-03-12 | inferred |  |
| 01a076cc | Huntsman Corporation | company | yes | us_propylene_oxide_supply | sign_of_exposure | + |  | training knowledge of us po producer set |  | 2026-03-12 | inferred |  |
| 01a076cc | US flexible polyurethane foam producers (aggregate, mostly private) | other | no | us_propylene_oxide_supply | sign_of_exposure | - |  | mattress trade press: 15-20% foam input cost increases within days; allocation | 2026-03-20 | 2026-03-20 | stated |  |
| 01a076cc | US flexible polyurethane foam producers (aggregate, mostly private) | other | no | us_propylene_oxide_supply | substitutability | low | weeks | polyol grade requalification 8-12 weeks (sourcing guide) |  | 2026-04-01 | inferred |  |
| 01a076cc | Leggett & Platt | company | yes | us_propylene_oxide_supply | sign_of_exposure | - |  | foam is an input; share of cogs small |  | 2026-03-12 | inferred |  |
| 01a076cc | Tempur Sealy International | company | yes | us_propylene_oxide_supply | sign_of_exposure | - |  | foam is an input; share of cogs small |  | 2026-03-12 | inferred |  |
| 01a076cc | Lear Corporation | company | yes | us_propylene_oxide_supply | sign_of_exposure | - |  | foam is an input; share of cogs small |  | 2026-03-12 | inferred |  |
| 01a076cc | Adient | company | yes | us_propylene_oxide_supply | sign_of_exposure | - |  | foam is an input; share of cogs small |  | 2026-03-12 | inferred |  |
| 01a076cc | Frontline | company | yes | strait_of_hormuz_tanker_transit | sign_of_exposure | + |  | scarcity of willing transit raises rates for vessels that trade |  | 2026-02-28 | inferred |  |
| 01a076cc | DHT Holdings | company | yes | strait_of_hormuz_tanker_transit | sign_of_exposure | + |  | scarcity of willing transit raises rates for vessels that trade |  | 2026-02-28 | inferred |  |
| 01a076cc | International Seaways | company | yes | strait_of_hormuz_tanker_transit | sign_of_exposure | + |  | scarcity of willing transit raises rates for vessels that trade |  | 2026-02-28 | inferred |  |
| 01a076cc | Airlines with Gulf routings (aggregate) | other | no | strait_of_hormuz_tanker_transit | sign_of_exposure | - |  | airspace and fuel; unverified |  | 2026-02-28 | inferred |  |
| 01a076cc | Gulf-region methanol and urea exporters (aggregate, mostly state-owned) | other | no | gulf_methanol_urea_exports | sign_of_exposure | - |  | trade press: iranian plant outages and stranded cargoes, march 2026 | 2026-03-20 | 2026-03-20 | stated |  |
| 01a076cc | Methanex | company | yes | gulf_methanol_urea_exports | sign_of_exposure | + |  | non-gulf producers capture spread |  | 2026-02-28 | inferred |  |
| 01a076cc | CF Industries | company | yes | gulf_methanol_urea_exports | sign_of_exposure | + |  | non-gulf producers capture spread |  | 2026-02-28 | inferred |  |
| 01a076cc | Nutrien | company | yes | gulf_methanol_urea_exports | sign_of_exposure | + |  | non-gulf producers capture spread |  | 2026-02-28 | inferred |  |
| 01a076cc | Port of Antwerp-Bruges | authority | no | port_of_antwerp_seagoing_access | sign_of_exposure | - |  | port h1 report: ~85,000 teu lost to the spill | 2026-07-31 | 2026-07-31 | stated |  |
| 01a076cc | MSC PSA European Terminal | facility | no | port_of_antwerp_seagoing_access | sign_of_exposure | - |  | dock closed ~4 days per port notices | 2026-04-13 | 2026-04-10 | stated |  |
| 01a076cc | A.P. Moller-Maersk | company | yes | port_of_antwerp_seagoing_access | sign_of_exposure | - |  | carrier advisory: omissions and backlog into following week | 2026-04-10 | 2026-04-10 | stated |  |
| 01a076cc | A.P. Moller-Maersk | company | yes | port_of_antwerp_seagoing_access | share | small |  | one port among many; below noise floor |  | 2026-04-10 | inferred |  |
| 01a076cc | Hapag-Lloyd | company | yes | port_of_antwerp_seagoing_access | sign_of_exposure | - |  | uses the port; below noise floor |  | 2026-04-10 | inferred |  |
| 01a078d2 | Vedanta Limited | company | yes | vlctpp_singhitarai_generation | sign_of_exposure | - |  | owner at event time; Q1 FY27 segment EBITDA -30% YoY attributed to the Sakti outage | 2026-07-30 | 2026-04-14 | stated |  |
| 01a078d2 | Vedanta Limited | company | yes | vlctpp_singhitarai_generation | share | small | share of group EBITDA | one 600 MW unit inside a diversified metals and mining group guiding to ~$10bn FY27 EBITDA; below the noise floor at group level |  | 2026-04-14 | inferred |  |
| 01a078d2 | Vedanta Power Limited | company | yes | vlctpp_singhitarai_generation | sign_of_exposure | - |  | owner after the 15 Jun 2026 demerger; Q1 FY27 EBITDA -30% YoY due to the boiler incident | 2026-07-30 | 2026-06-15 | stated |  |
| 01a078d2 | Vedanta Power Limited | company | yes | vlctpp_singhitarai_generation | share | 14 | percent of operational capacity (600 of 4200 MW) | Vedanta Power 4.2 GW operational at listing; Sakti 600 MW |  | 2026-06-15 | inferred |  |
| 01a078d2 | Tamil Nadu Power Distribution Corporation Limited | authority | no | vlctpp_singhitarai_generation | sign_of_exposure | - |  | offtaker of 200 MW under a Feb 2026 to Jan 2031 PPA at Rs 5.38/kWh; loses contracted supply while the unit is down |  | 2025-11-06 | inferred |  |
| 01a078d2 | NTPC GE Power Services Limited | company | no | vlctpp_singhitarai_generation | sign_of_exposure | - |  | O&M subcontractor whose staff died; named in probe findings and FIR; liability exposure |  | 2026-04-14 | inferred |  |
| 01a078d3 | Vedanta Limited Chhattisgarh Thermal Power Plant | plant | no | vlctpp_singhitarai_generation | sign_of_exposure | - |  | the plant itself; Unit 1 shut since 14 Apr 2026, Unit 2 not yet built | 2026-07-30 | 2026-04-14 | stated |  |
| 01a078d3 | Vedanta Limited Chhattisgarh Thermal Power Plant | plant | no | vlctpp_singhitarai_generation | duration | 5.5 | months of outage (14 Apr 2026 to guided restart end Q2 FY27) | Vedanta Power Q1 FY27 earnings call guidance, 30 Jul 2026 | 2026-07-30 | 2026-07-30 | stated |  |
| 01a078fd | Ruhr Oel GmbH - BP Gelsenkirchen | plant | no | bp_gelsenkirchen_scholven_output | sign_of_exposure | - |  | the site itself: desulphurisation unit and several others shut; benzene deliveries suspended | 2026-07-29 | 2026-07-15 | stated |  |
| 01a078fd | BP p.l.c. | company | yes | bp_gelsenkirchen_scholven_output | sign_of_exposure | - |  | owner at event time (sale pending, completed 3 Aug 2026) |  | 2026-07-15 | inferred |  |
| 01a078fd | BP p.l.c. | company | yes | bp_gelsenkirchen_scholven_output | share | small | share of group earnings | one of six BP refineries, already agreed for sale; Q2 trading statement dominated by oil price and margins |  | 2026-07-14 | inferred |  |
| 01a078fd | Klesch Group | company | no | bp_gelsenkirchen_scholven_output | sign_of_exposure | - |  | buyer under a signed agreement at event time; owner from 3 Aug 2026 |  | 2026-03-01 | inferred |  |
| 01a078fd | INEOS Phenol GmbH Gladbeck | plant | no | bp_gelsenkirchen_scholven_output | sign_of_exposure | - |  | force majeure on phenol and acetone after BP suspended benzene deliveries (ChemNet 29 Jul 2026) | 2026-07-29 | 2026-07-20 | stated |  |
| 01a078fd | INEOS Phenol GmbH Gladbeck | plant | no | bp_gelsenkirchen_scholven_output | substitutability | low | single-supplier benzene link via Marl cumene | described as the core feedstock supplier for the European chain; no alternative benzene source named |  | 2026-07-29 | inferred |  |
| 01a078fd | INEOS cumene plant Marl | plant | no | bp_gelsenkirchen_scholven_output | sign_of_exposure | - |  | benzene feed from the site suspended | 2026-07-29 | 2026-07-20 | stated |  |
| 01a07ae7 | MSC PSA European Terminal | facility | no | deurganck_dock_container_handling | sign_of_exposure | - |  | terminal closed 14-17 Jul 2026; quay 1742 berth out with three damaged STS cranes as of 24 Jul | 2026-07-24 | 2026-07-14 | stated |  |
| 01a07ae7 | MSC PSA European Terminal | facility | no | deurganck_dock_container_handling | duration | 3 days terminal; 10+ days north berth | days out of operation (terminal declared safe 17 Jul; quay 1742 still out 24 Jul, no reopening date found) | WorldCargo News 16 and 24 Jul 2026 | 2026-07-24 | 2026-07-24 | stated |  |
| 01a07ae7 | Port of Antwerp-Bruges | authority | no | deurganck_dock_container_handling | sign_of_exposure | - |  | whole dock and Kieldrecht lock closed 14-15 Jul 2026 by the port's crisis plan | 2026-07-15 | 2026-07-14 | stated |  |
| 01a07ae7 | Mediterranean Shipping Company | company | no | deurganck_dock_container_handling | sign_of_exposure | - |  | vessel operator (MSC Mia Summer II) and terminal co-owner; advisory naming four affected quays; criminal investigation open | 2026-07-16 | 2026-07-14 | stated |  |
| 01a07ae7 | A.P. Moller-Maersk | company | yes | deurganck_dock_container_handling | sign_of_exposure | - |  | uses Antwerp; no July advisory found; share small (round 3) |  | 2026-07-14 | inferred |  |
| 01a07ae7 | Hapag-Lloyd | company | yes | deurganck_dock_container_handling | sign_of_exposure | - |  | uses Antwerp; week-29 operational update not retrievable; share small (round 3) |  | 2026-07-14 | inferred |  |
| 01a07ae8 | Antwerp Gateway | facility | no | deurganck_dock_container_handling | sign_of_exposure | - |  | closed with the whole dock 14 Jul evening; resumed 15 Jul afternoon | 2026-07-15 | 2026-07-14 | stated |  |
| 01a07b19 | Safripol | company | no | sasolburg_polyethylene_output | sign_of_exposure | - |  | operator prior, pre-lock, no retrieval: candidate owner of the plant: HDPE plant in Sasolburg on ethylene from Sasol |  |  | inferred |  |
| 01a07b19 | Safripol | company | no | sasolburg_polyethylene_output | substitutability | high |  | operator prior, pre-lock, no retrieval: HDPE is import-substitutable into South Africa at a freight and time cost |  |  | inferred |  |
| 01a07b19 | Sasol Polymers Sasolburg (Sasol One site) | plant | no | sasolburg_polyethylene_output | sign_of_exposure | - |  | operator prior, pre-lock, no retrieval: candidate owner: LDPE plant at Sasol One |  |  | inferred |  |
| 01a07b19 | Sasol Limited | company | yes | sasolburg_polyethylene_output | sign_of_exposure | 0 |  | operator prior, pre-lock, no retrieval: diversified owner; ethylene supplier to both candidate plants; a single polymer line is below the visibility ratio |  |  | inferred |  |
| 01a07b19 | KAP Industrial Holdings | company | yes | sasolburg_polyethylene_output | sign_of_exposure | - |  | operator prior, pre-lock, no retrieval: parent of Safripol; chemicals is one of its divisions; exposed only if the plant is Safripol's |  |  | inferred |  |
| 01a07b19 | Mpact Limited | company | yes | sasolburg_polyethylene_output | sign_of_exposure | - |  | operator prior, pre-lock, no retrieval: converter buying domestic PE; substitutes with imports at a cost |  |  | inferred |  |
| 01a07b19 | Nampak Limited | company | yes | sasolburg_polyethylene_output | sign_of_exposure | 0 |  | operator prior, pre-lock, no retrieval: packaging group; PE intake unknown; sign uncertain |  |  | inferred |  |
| 01a07b19 | South African plastics converters (sector, Plastics SA membership) | other | no | sasolburg_polyethylene_output | sign_of_exposure | - |  | operator prior, pre-lock, no retrieval: sector buying domestic PE |  |  | inferred |  |
| 01a07b1f | Sasol Polymers Sasolburg (Sasol One site) | plant | no | sasolburg_polyethylene_output | sign_of_exposure | - |  | M&G 24 Jul 2026: the burned unit is Sasol's Poly 3 at the Midland site | 2026-07-24 |  | stated |  |
| 01a07b1f | Sasol Polymers Sasolburg (Sasol One site) | plant | no | sasolburg_polyethylene_output | duration | unknown |  | Poly 3 shut pending investigation; DEL prohibition notice; no restart statement found by 7 Sep 2026 | 2026-09-07 |  | stated |  |
| 01a07b1f | Safripol | company | no | sasolburg_polyethylene_output | sign_of_exposure | 0 |  | not the burned plant (M&G 24 Jul 2026); Safripol HDPE unaffected | 2026-07-24 |  | stated |  |
| 01a07b1f | KAP Industrial Holdings | company | yes | sasolburg_polyethylene_output | sign_of_exposure | 0 |  | parent of Safripol; plant not Safripol's | 2026-07-24 |  | inferred |  |
| 01a07b1f | Sasol Limited | company | yes | sasolburg_polyethylene_output | sign_of_exposure | 0 |  | SOL moves 22-24 Jul attributed to oil, FY26 metrics and PIC stake, not the fire (FX Leaders 23 and 28 Jul); Sasol FY26 results silent on the fire | 2026-09-01 |  | stated |  |

## D. Library rules created before the cut

Text, what each forbids, its layer and its provenance only. Hit and miss counts are omitted on purpose (later rounds updated them).

- **[transmission]** when a transit chokepoint is threatened, the price of passage rises before and more durably than the price of what passes through it
  - forbids: freight and insurance being flat while the commodity spikes on a chokepoint threat
  - provenance: Round 1: Strait of Hormuz; VLCC rates 4x pre-war, war-risk premia 3-10% of hull.
- **[transmission]** a supply-fear spike with no physical interdiction mean-reverts within weeks
  - forbids: a sustained commodity premium without a physical constraint
  - provenance: Round 1: Brent fell below $100 within weeks — but on de-escalation, with Hormuz already closed. Outcome hit, mechanism wrong; quarantined.
- **[ownership]** when one supplier of a region-locked product is removed, the remaining suppliers capture the spread
  - forbids: remaining suppliers' spreads staying flat after a peer outage in a region-locked market
  - provenance: Round 1: non-Gulf methanol/urea producers. Round 2: US PO producers — but see lib.wounded_owner.
- **[transmission]** when a large producing region is shut, its exports vanish and the chain downstream reprices in the order of substitution difficulty
  - forbids: downstream derivative prices being unaffected by an upstream regional shutdown
  - provenance: Round 1: Iranian methanol/urea plants down; SE Asia methanol +72%, urea to ~$780/t. Round 2: PO -> polyols -> foam.
- **[transmission]** closing a route reprices everything that must use it, in proportion to how hard it is to reroute
  - forbids: route-dependent carriers being unaffected by closure
  - provenance: Round 1: Hormuz. Round 3: Scheldt (half a day) vs Deurganck Dock (four days).
- **[sequence]** statements of intent to escalate move prices on the day and fade unless followed by physical action
  - forbids: a durable premium built on rhetoric alone
  - provenance: Round 1: +7.9% crude on 'continue attacks' statement, then fade.
- **[ownership]** the named victim of an event is over-attended relative to its earnings impact; single-unit losses at diversified owners are equity noise
  - forbids: predicting a large sustained equity loss for a diversified owner from one unit outage absent casualties or liability
  - provenance: Round 2: LyondellBasell — untestable because macro swamped, but the premise held.
- **[transmission]** a producer's force majeure declaration is the fastest public carrier of a plant outage, preceding every price print
  - forbids: waiting for price prints to confirm a plant outage when a force majeure letter is available
  - provenance: Round 2: PG FM day 1, PO FM day 5.
- **[transmission]** a product that is hazardous to ship and made by few producers reprices locally and stays repriced until local capacity returns
  - forbids: expecting import relief to cap a regional price spike in a hard-to-ship product
  - provenance: Round 2: US propylene oxide.
- **[transmission]** cost travels down a chain with contract lag; derivatives reprice weeks after the parent chemical, downstream buyers at their next contract or earnings
  - forbids: downstream repricing on the same day as the upstream event
  - provenance: Round 2: polyol +28%, MPG +34% in April contracts; foam costs +15-20% within days (faster than predicted).
- **[transmission]** a plant that co-produces two products cuts both when it stops; the second product is named later than the first
  - forbids: ignoring the co-product when scoping a plant outage
  - provenance: Round 2: PO/TBA -> MTBE. Channel was real but specialists named it in five days and the destination market was in glut.
- **[transmission]** a large consumer of a feedstock going offline softens that feedstock at the margin
  - forbids: predicting feedstock tightening from a consumer outage
  - provenance: Round 2: propylene; unverified under war noise.
- **[transmission]** a supply shock landing in a demand slump produces a smaller price response than the same shock in a tight market
  - forbids: full-strength price predictions when downstream demand is contracting
  - provenance: Round 2: cautious downstream buying capped PO spot.
- **[transmission]** a short closure at an already-congested node produces a ripple that outlasts the closure by weeks
  - forbids: assuming the effect ends when the closure ends
  - provenance: Round 3: Antwerp; backlog into the following week; ~85,000 teu lost.
- **[ownership]** liability for an operational accident lands on a party too small or private to trade; no listed exposure is created
  - forbids: predicting a tradeable liability leg from an ordinary operational accident
  - provenance: Round 3: responsible vessel belonged to a large private carrier — partly wrong on size, right on tradeability.
- **[sequence]** novelty belongs to channels, not events; a channel already traversed by a crisis is priced for every later headline in that crisis
  - forbids: predicting a lag on a channel the current crisis has already repriced
  - provenance: Round 1: methanol/urea mainstream by march 20-25; april 3 entry bought the top.
- **[sequence]** recurring disruption at a node is priced as weather; single events there transmit nothing regardless of size
  - forbids: arming on an event at a node with recent recurring failures
  - provenance: Round 3: Antwerp — strike in march, spill in april, pilots in june, leak in july.
- **[sequence]** late in a crisis the neglected side is resolution; when every channel is priced for continuation the unpriced asymmetry is de-escalation
  - forbids: adding to the crisis basket when all its channels are already traversed
  - provenance: Round 1: real april 3 trade was short the war basket into ceasefire talks.
- **[sequence]** the headline names what reopened, not what stayed shut; duration lives one node smaller than the choke that made the news
  - forbids: using the headline node's closure time as the event duration
  - provenance: Round 3: river reopened in half a day, dock shut four days.
- **[transmission]** a cut into a glut is silent; supply loss transmits only where the receiving market has no slack
  - forbids: predicting repricing of a co-product or substitute without checking destination-market slack
  - provenance: Round 2: MTBE in chinese-overcapacity glut; no step.
- **[transmission]** the price move is largest at the chain position with least optionality — requalification lags, formulation lock-in, route dependence
  - forbids: expecting the largest move at the constrained input itself rather than at the least-substitutable consumer
  - provenance: Round 1: shippers who could not reroute. Round 2: foamers facing 8-12 week polyol requalification; derivatives moved 2-3x the parent chemical.
- **[transmission]** the toll booth learns before the cargo; constraint prices (insurance, freight, allocation) reprice before the commodity they gate
  - forbids: treating the commodity price as the earliest signal of a chokepoint or plant event
  - provenance: Round 1: 'the insurance market closed the strait before any attack did'. Round 2: FM letters before price prints.
- **[transmission]** constraint prices de-escalate slowest; fear enters through the commodity and leaves through the insurance bill
  - forbids: assuming freight and premia round-trip on the same timescale as spot
  - provenance: Round 1: premia 3-10% into july while crude round-tripped by early july.
- **[ownership]** the wounded owner of the substitutes collects its own scarcity premium; when the victim also owns remaining capacity the competitor's gift self-cancels
  - forbids: long-rival/short-owner where the owner holds sister plants on the same node
  - provenance: Round 2: owner's other po plants sold into the tightness its own outage created.
- **[ownership]** equity visibility equals event size divided by ambient tide; below a ratio to be measured there is no trace to trade
  - forbids: predicting a stock move without comparing event earnings impact to concurrent macro variance on the same name
  - provenance: Round 2: ~$250m outage inside a quarter where ebitda tripled; owner upgraded same day on a sector trade.
- **[ownership]** a lag without a listed pure-play is a spectacle, not an edge
  - forbids: arming a shock whose touched channel has no listed holder above the noise floor
  - provenance: Promoted to pred.arm.tradability_gate. Rounds 2 and 3.
- **[operator]** the operator wakes new to every event while the market has been living in it; operator surprise is a bias toward assuming un-inferredness
  - forbids: treating the operator's own surprise as evidence that a channel is unpriced
  - provenance: Round 1: predicted day 34 of a war as a fresh shock.
- **[operator]** specialists already hold the operator's map; obscurity must be measured against the people at the terminal, not the public
  - forbids: rating a channel obscure without checking specialist coverage
  - provenance: Round 2: sell-side analyst named the co-product channel in five days.
- **[operator]** the operator overweights famous names, first-order links, and connections that make good sentences
  - forbids: leading a prediction with the most quotable connection
  - provenance: Prior distortion list, carried.
- **[operator]** the operator underweights boring intermediaries, logistics, insurance, and second-order plumbing
  - forbids: omitting the intermediary layer from a touched-set
  - provenance: Prior distortion list, carried. Round 1 partially corrected by the toll-booth entry.
- **[transmission]** a plant outage in a region-locked concentrated product with an owner holding sister plants: force majeure arrives first, derivatives reprice larger than the parent, the co-product reprices only if its market is tight, and the owner's equity shows nothing
  - forbids: the round-2 pre-lock prediction set
  - provenance: Composition assembled from round 2.
- **[sequence]** a chokepoint crisis in its nth week: constraint prices lead and lag, all traversed channels are priced, the unpriced side is resolution
  - forbids: adding to the crisis basket late
  - provenance: Composition assembled from round 1.
- **[other]** a fatal industrial accident triggers a jurisdiction-wide inspection order within weeks that binds nothing durable on peers
  - forbids: a lasting operational or cost constraint on peer plants arising from a post-accident inspection order
  - provenance: Round 4 (Sakti district thermal plant boiler explosion, April 2026), proposed at lock from training priors on Indian state factories-department responses to plant fatalities; untested.
- **[ownership]** tradability can arrive by corporate action after the event; a claim that no listed pure-play exists must carry a time bound
  - forbids: an unbounded no-listed-exposure null; forbids assuming the ownership map at event time holds through the scoring window
  - provenance: Round 4: Vedanta demerger listed Vedanta Power on 15 Jun 2026, two months after the Sakti explosion, creating a listed holder with ~14% capacity exposure; the round's tradability null was killed by its own unbounded falsifier.
- **[ownership]** a plant revived from insolvency runs fewer units than its nameplate; an outage there takes the whole site, not one unit
  - forbids: assuming nameplate unit count, and therefore partial-site continuity, at an asset recently bought out of insolvency
  - provenance: Round 4: the Singhitarai plant (ex-Athena, bought by Vedanta in 2022 out of insolvency) had Unit 1 at COD since mid-2025 and Unit 2 still under construction; the map call assumed two running units and missed.
- **[sequence]** for a fatal accident at a diversified owner, the attributable equity move comes with the criminal complaint naming executives, not with the accident
  - forbids: expecting the day-after session to carry the attributable move; forbids scoring the equity trace before the legal response has landed
  - provenance: Round 4: Vedanta +1.79% on 15 Apr and +2.19% on 16 Apr (demerger, metal prices), then -1.39% on 17 Apr when an FIR named the group chairman. Observation, not yet a blind call.
- **[transmission]** where offtake is a bilateral utility contract, the outage's first public carrier is the owner's quarterly disclosure, not a force majeure notice
  - forbids: expecting a force majeure letter as the fast public carrier for a contracted power plant; the notice goes to one counterparty and is not published
  - provenance: Round 4: no PPA shortfall or force majeure notice to the Tamil Nadu offtaker surfaced; the outage became public in numbers only at the 30 Jul Q1 FY27 results. Contrast round 2, where chemical force majeure letters were public within days.
- **[transmission]** a fire in one unit of an integrated site stops deliveries of unrelated products; the offtaker's force majeure names the site, not the unit
  - forbids: conditioning an offtake or force majeure call on which unit burned; forbids assuming a fuels-unit fire leaves the chemical side supplying
  - provenance: Round 5: a diesel desulphurisation unit fire at the Gelsenkirchen Scholven site led BP to suspend all benzene deliveries and INEOS Phenol to declare force majeure on phenol and acetone within two weeks.
- **[transmission]** a pre-existing logistics stop masks an outage; when loadings are already halted the fuels market cannot see the unit go down
  - forbids: reading a null fuel-market response as evidence of slack when product loadings were already stopped for another reason
  - provenance: Round 5: loadings at the site had been halted since 13 July for pipeline maintenance; the 15 July unit outage had no additional market effect (Argus).
- **[operator]** the operator attaches a rule to a call the rule does not carry, buying the rule unearned credit; identity and map calls carry no mechanism
  - forbids: citing a library rule on a map, identity or corporate-timetable call; such calls declare no-mechanism
  - provenance: Round 5: the map call and the public-safety call cited rules that did not operate; both were quarantined at scoring by the operator to keep the credit out of the library.
- **[ownership]** a single-supplier feedstock link is a hidden node; the downstream plant's force majeure is the first public statement of the link
  - forbids: treating a chemical plant as unexposed to a refinery it is not co-located with; forbids assuming the link is priced before the notice
  - provenance: Round 5: the benzene link Gelsenkirchen -> Marl cumene -> Gladbeck phenol was stated in trade press since 2024 but not held by the operator at lock; the force majeure made it visible.
- **[transmission]** a tide sets the price of everything it touches; an event under it is visible only in what the tide does not price
  - forbids: scoring a commodity or equity leg as attributable when a larger concurrent driver set the price; forbids reading a null response under a tide as slack
  - provenance: Rounds 1, 4 and 5: Hormuz set oil, fuels and BP; the Sakti outage sat inside a demerger and metals rally; the Gelsenkirchen fuel legs sat on the 14 July blockade. Each time the event was visible only in the offtake layer (force majeure, allocation, contract resets). Extends lib.equity_visibility_ratio to commodity legs. | v9 §0.1: rounds 2, 5, 8 (crack spread silence under Hormuz pricing; equity silence under sector tides). Distinct from lib.cut_into_glut_silent, which requires a demonstrated surplus in the receiving market.
- **[transmission]** a toxic release closes the whole shared space, not the asset that failed; the closure boundary is the emergency plan's perimeter, not the unit's
  - forbids: sizing a closure by the failed container, tank or unit; forbids assuming neighbouring terminals or locks stay open when a vapour cloud is involved
  - provenance: Round 6: one tank container leaking hydrogen fluoride on a vessel at MPET closed the entire Deurganck Dock, both terminals and the Kieldrecht lock, and sent 186 people for assessment; the map call had sized it as 'part of the terminal'.
- **[operator]** knowing the rule is not applying it: the operator cites the smaller-node rule and still calls the headline node's duration
  - forbids: a duration call on the headline node when the cited rule says the duration lives one node smaller; the call must name the smaller node
  - provenance: Round 6: the lag call cited 'the headline names what reopened, not what stayed shut' and then called the terminal fully operational within 3 days; the north berth with three damaged cranes stayed out for weeks. Same shape as round 3's duration misplacement.
- **[operator]** narrative and price diverge after a small shock: trade press narrates congestion the indices do not show; a price call must name the price series and nothing else in its falsifier
  - forbids: a falsifier that fires on commentary for a claim about prices; forbids reading a 'deepens congestion' headline as a price move
  - provenance: Round 6: the WCI fell 2% with European congestion easing and no Antwerp mention while a trade headline said the leak deepened congestion; the indices call died on its own commentary clause.
- **[transmission]** a producer issues a public force majeure when it has contracted offtake it cannot serve and a channel that reports it; a single-line unit in a thin-coverage market stops without a notice
  - forbids: predicting a public force majeure notice from an outage alone; forbids reading the absence of a notice as the absence of an outage
  - provenance: Rounds 5 (Gelsenkirchen: INEOS notice came, contracted offtake and a reporting channel) and 7 (Sasolburg Poly 3: none found, thin coverage)
- **[ownership]** when an event names a site with more than one operator, the larger operator is the prior
  - forbids: a map call on the smaller operator without a stated basis beyond the wording of the headline
  - provenance: Round 7: the baseline (Sasol, the larger operator at Sasolburg) beat the operator's Safripol lean

## E. Carriers known before the cut

| name | kind | access | note | participant class |
|---|---|---|---|---|
| ICIS | price_assessment | paywalled | rounds 2, 5, 7: restart, FM and local pricing sit behind it | physical_press |
| ChemWeek | newspaper | paywalled | chemical trade press | physical_press |
| Loadstar | newspaper | paywalled | container logistics press | physical_press |
| Flows | newspaper | paywalled | Antwerp port and logistics press | physical_press |
| bp.com | filing | blocked | round 5: blocked to the fetcher | compliance |
| port notices | notice_feed | open | port authority and terminal advisories | procurement |
| terminal notices | notice_feed | open |  | procurement |
| Argus | price_assessment | open | headline tables only | physical_press |
| exchange filings | filing | open | SENS, RNS, EDGAR, company releases | compliance |
| SENS | filing | open |  | compliance |
| owner statements | filing | open | company media releases | contract |
| JSE close | index | open | daily closes | equity_generalist |
| war-risk premium quotes | price_assessment | unknown | round 1: quoted in press, no direct series | contract |
| trade press | newspaper | unknown | generic; name the outlet | physical_press |
| ChemOrbis | price_assessment | paywalled | free view carries headlines only | physical_press |
| Plastics SA | notice_feed | open | round 7: silent on the event | physical_press |
| company IR page | notice_feed | open | producers post force majeure and outage notices to their own sites; Wayback snapshots them (free dated notice feed) | compliance |
| TCEQ emissions event | notice_feed | open | Texas STEERS air emissions event reports: dated, unit-level, public | compliance |
| EIA | index | open | weekly petroleum status, refinery inputs, spot prices | physical_press |
| grid operator notices | notice_feed | open |  | compliance |
| energy regulator | notice_feed | open |  | compliance |
| USDA | notice_feed | open |  | compliance |
| LME/CME delayed prices | price_assessment | open |  | procurement |

## F. Holder kinds and authority holders in the names book before the cut

Holder kinds in use: `company`, `plant`, `facility`, `authority`, `other`.

- authority: Port of Antwerp-Bruges
- authority: Tamil Nadu Power Distribution Corporation Limited
