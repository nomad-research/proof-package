# Edge ledger (started 2026-10-01)

Rob, 2026-10-01: "if we can take all the edges we learn through running the system and start fresh in design with edge in our back pocket we may have more success."

This file keeps every candidate edge in one place. For each one:
- what it is, in plain English;
- the **divergence mechanism**: what in the world makes our view differ from the market's;
- the **framework mechanism**: what in our setup produced that divergence;
- the evidence, marked **registered** or **post-hoc**;
- its status, and what would confirm or kill it.

It also keeps the things that turned out **not** to be edges, because a fresh design needs those too. Nothing here is a decision. An edge earns a place in the design only once a registered pass confirms it (decisions 5 and 7).

---

## E1. Ruling things out: Nomad as a NO predictor

**In plain English.** When the model is confident that something specific will **not** happen (a word won't be said, a price won't land in a bucket, a count won't reach a level, a deadline won't be met) and the market gives it a real chance, the model is right more often than the price implies. Its confident NOs are sharp. Its confident YESes are not.

**Divergence mechanism (the world).** Base rates against salience.
- The model, frozen at its training cutoff and given no news, falls back on how such things usually go:
  - how often a person uses a phrase;
  - how much an asset moves in a week;
  - how often a count clears a level;
  - how often announced deadlines are met;
  - and the exact wording of the resolution rules.
- The market prices short-window, attention-driven questions partly from what is salient right now. That puts a "maybe" premium on specific outcomes the base rate says rarely happen.
- Where the two disagree on a specific outcome, the base rate wins more often than the price allows.
- It is **not** a market-wide bias the model is riding:
  - across 231 multi-outcome markets the market's favourite came in exactly as often as priced (0.597 against 0.595);
  - NO contracts as a whole sit close to fair;
  - the edge survives subtracting same-side, same-price contracts.

  The model is choosing *which* maybes are overpriced.

**Framework mechanism (our setup).**
- **R6.** The session reads only the rules and never sees the price, so it cannot be pulled toward the crowd's salience.
- **No evidence after its cutoff.** That pushes it onto base rates.
- **The format asks for a number on every outcome,** so its "won't happen"s surface as confident low numbers on outcomes the crowd likes.
- **The bet rule** (only where the view beats the all-in cost) turns those into NO positions. On mid-priced NOs costs are small next to the gap.
- **The same handicaps** (no current information) produce the losing divergences below (N1, N2). The framework makes two kinds of disagreement, and only one carries edge.

**Evidence.**

| Source | What | Kind |
|---|---|---|
| BT-T2 (`BT_T2_RESULT.md`, `bt_t2_anatomy.py`) | Positions where the session was *surer than the market*: +7.6¢ skill against same-side, same-cost contracts (95% +1.6 to +13.8, 206 positions, 74 events). Positions where it was *less sure* (mostly cheap YES longshots): +2.3¢, spans zero. The whole registered S1 skill was +4.1¢ (edge shown) | post-hoc split of a registered result |
| BT-A answers, April to September (`edge_no_check.py`) | NO bets where the model was surer than the price: **+7.4¢ money** (+4.3 to +10.7), +3.7¢ against same-side, same-cost (+0.6 to +6.9), 559 positions on 221 events. YES bets: −1.4¢ money (−3.2 to +0.6) | post-hoc; BT-A was built as a knowledge audit, not an edge test |
| BT-A calibration | Model says under 5% → happened 1% (market said 4%), n 660. Model says 85–95% → happened 68% (market said 57%), n 41. Accurate low, overconfident high | post-hoc |
| T0 / V1 | Exclusions ("this joint state will not happen") failed in 4 of 69 claims; reality landed inside the declared sets in 37 of 41 rounds | registered (V1); unpriced, a reliability figure |
| Equity era | Absence calls held 15 of 16, counting expired, unanswered calls as hits | as reported in `docs/nomad_the_system_as_it_stands.md` |

**Status (updated after BT-T2 pass 2, 2026-10-01).** Its registered test, pass 2, gave +2.6¢ (95% −2.7 to +8.0): **direction only: not confirmed, not killed**. Four positive reads in four samples; pooled across the two BT-T2 passes +3.4¢ (−0.3 to +7.2).

The money is the model's choosing: a blind always-NO rule earns about 0 in both passes; the model's NO picks earn +4.4¢ and +5.2¢ a share, and +8.5¢ and +8.6¢ on NOs priced above 50¢ (`BT_T2_pass2_RESULT.md`). Pass 1's "surer than market" subset shrank from +7.6¢ to +2.5¢ on fresh events. Next test: the forward E1 sweep.

**To confirm.** Register it as the main statistic of the next pass: BT-T2 pass 2, on fresh events in the same window. The claim: NO positions where the session is surer than the market beat same-side, same-cost contracts, read at 5%.

**To kill.** That statistic's 95% interval falls below zero on the registered pass.

**Risks a design must carry if it holds.**
- A NO book wins small and often and loses big and rarely: buy NO at 0.74, and a miss costs 0.74.
- One shock can turn many NOs into YESes at once (v18 §13, correlated tails).
- So global risk (C1) and position risk (C2) matter more here than in a balanced book.

## E2. Linked events: "if A then B"

**In plain English.** When the session says two events move together and A happens, B holds more often than other contracts of the same kind and price.

**Divergence mechanism.** The market prices each event alone (no conditional contracts exist). A reader who sees the link can know more about B once A is known.

**Framework mechanism.** Claims written price-blind across events in one packet.

**Evidence.**
- T0 against a kind-and-price matched base: +30 points on the 9 tier claims whose "if" happened (+13 to +48).
- Bought at the lock either way: +4 points, spanning zero (`T0_BASE_RATE.md`).
- Post-hoc throughout.

**Status.** Hypothesis. The value is conditional: betting it needs a view on A as well.

**To confirm.** T3 (forward, claims with both branches, S3 registered).

## E3. Mention markets: "What will … say" (two registered passes: edge shown, then direction only; both-sided reading replicates)

**In plain English.** On markets that pay if a person says a given word or phrase in a window (weekly Trump remarks, an earnings call), the model's NO bets (it won't be said) beat the price by a wide margin.

**Divergence mechanism (hypothesis).** The crowd prices words by salience: what is in the news, what the person said recently. The model prices them by the person's long-run vocabulary and the rules' exact wording (an exact phrase, said by that person, in that window). Exact-phrase rules are easy to over-price when the topic is hot.

**Framework mechanism.** Price-blind, rules-literal reading with a number on every word. Mention markets list many words at once, so the format makes the model rule many of them out.

**Evidence.** BT-T2 pass 1 +16.2¢ (21 positions, 2 events); pass 2 +15.6¢ (20 positions, 2 events); pooled +15.9¢ (95% +5.8 to +29.4) on **4 events**. Post-hoc in both passes.

**Registered test (`E3_MENTIONS_RESULT.md`).**
- Every eligible mention event in the clean window, minus the four above: 46 events, 494 NO positions.
- **The model's NO picks against other mention NOs at the same price: +7.3¢ (95% +1.8 to +13.0). Edge shown.**
- NO money +10.1¢. NO picks priced 50¢ or more: +19.5¢ a share, about +29% per dollar, hit rate 88%.
- Blind NO +3.1¢, spanning zero: the market leans slightly towards NO, and the picks beat that lean.
- It is not only NO. YES picks beat same-price YESes by +14.3¢. The log score ties the market's (−0.007), where every other class lost (−0.074).
- It holds with stale or decided prices removed.
- **Fragile:** 23 events add and 23 subtract. Without the top three events it is +3.8¢ (−0.4 to +8.4).

**Second registered pass (`E3_MENTIONS_pass2_RESULT.md`).** April to June, 36 fresh events, opened by BT-A pass 2.
- The NO statistic: **+5.1¢ (−2.4 to +12.4), direction only.** Three Trump events carry most of it again.
- Pooled over both passes: +6.2¢ (+1.6 to +10.7), +2.8¢ without the top five events.
- Blind NO earned +7.8¢ in April to June, a market habit in that window that the statistic subtracts.

**What replicated: both sides.**
- All picks against same-price contracts: **+11.1¢ and +10.9¢** in the two passes; pooled +11.0¢ (+7.9 to +14.3), **+8.7¢ (+6.1 to +11.4) without the top five events**.
- YES picks: +12.8¢ pooled.
- Log score: ties or beats the market (−0.007, +0.014). It loses in every other class.
- Mention markets are the one class tested where the model's probabilities are as good as the crowd's. Its disagreements pay on both sides, not only on NO.
- This was a reported, not a registered, statistic in both passes. It is registered forward as E3b (`FORWARD_SWEEP_prereg.md` addendum A3).

**Status.**
- E3 (NO only): carried to the forward sweep.
- E3b (both sides): the strongest candidate in the ledger. It replicated across two independent backtest passes and survives removing the biggest events. It is registered forward.
- Neither earns a design slot until the forward sweep confirms it.

**To confirm.** Mention markets open now, read cold and price-blind, scored as they resolve: the same statistic, registered before the first batch.

**To kill.** The forward statistic's 95% interval falls below zero.

## A framework observation: the ladder-structure hint (2026-10-01)

One pass-2 session placed price levels "from where the strike ladders are centred and which nearby strikes are missing (I assumed those were already hit)". Rungs already resolved before the lock are left out of a packet, and the rungs a market lists sit around where the market expects the price.

So the structure of a ladder tells a price-blind session roughly where the market thinks the level is. It is knowable at the lock and is not a price, but it comes from the market's own design. That makes it a channel through which the market's view of location reaches the session.

It may help explain why location (S2) never beats the market: the session's best location clue is the market's own. Decision 10's scale of scale sidesteps it.

---

## Not edges (what the runs showed does not work, or was an artefact)

| | What | Why it is not an edge | Source |
|---|---|---|---|
| N1 | Location and timing without evidence: where a price ends up, when something happens | The session's centre is stale (its knowledge stops in June): it sat below the market's centre on 74% of ladders and landed on the right side 11 of 23. On deadline questions the market's timing was closer (−0.18). S2 overall −0.08, direction only | BT-T2 |
| N2 | YES longshots from ignorance | Without current information the session spreads its view wider (1.46× the market's width on ladders) and buys cheap far rungs. +2.3¢, spans zero; small-gap YES bets in BT-A lose 3.5¢ | BT-T2, BT-A |
| N3 | "Sooner than the market thinks" (T0's timing reading) | Mostly the V1 pool's selection: date-ladder YES rungs beat their price by +13 points with no claim at all | `T0_BASE_RATE.md` |
| N4 | Hedging as a source of edge | Changes risk, not expected value, with single-event contracts. V1 and V1b inconclusive, pooled +2.7 (−2.0 to +7.5) | `EVALUATION.md` |
| N5 | The sessions' own "what will happen" picks | −2.3 points against matched contracts; 72% were favourites | T0 |
| N6 | The model's probabilities as a whole | Log score loses to the market in BT-A (from July on) and in BT-T2 (−0.09). The edge is where it disagrees, not in its overall accuracy | BT-A, BT-T2 |

## Market facts learned on the way (useful in any design)

- **A pool chosen by actual close time over-represents "it happened early".** Choose by schedule (`T0_BASE_RATE.md`).
- **The market's favourite in multi-outcome markets is fairly priced** (231 markets).
- **YES contracts run slightly rich next to NO at the same cost:** −2.1¢ against −0.4¢ hit minus cost (BT-T2's contracts).
- **The no-evidence model knows January to March outcomes and not July to September ones** (BT-A).

---

## Notes for the fresh design

### Magnitude, defined

Magnitude is **the size of the departure from the status quo** (how much changes between the lock and resolution), kept separate from **direction** (which way).
- "Nothing happens" is magnitude zero.
- E1 is a magnitude edge: the session expects *less to happen* than the market prices.
- BT-T2's S2 scored *location* (where the middle lands). That mixes direction with the model's stale starting point, which is why it showed nothing.

To score magnitude as magnitude:
- the session needs the status quo at the lock (the current level, the last count), so its spread means "expected change" and not "I don't know where we are";
- the score compares the departure the session expects with the departure the market implies, against the departure that happened, separately from its sign.

**Open for Rob:** for price questions the status quo is itself a market price (the underlying's spot, not the contract's price). Whether R6 allows it as world data is a question for him.

### Magnitude as "scale of scale" (decision 10, reading to confirm)

Rob: "scale of scale not shift delta". Read as: how big this instance is within the range of sizes its kind takes, an order of magnitude or a percentile of its reference class, not how far something moves.

What changes if so:
- **Units.** Every outcome is placed on its own reference scale (its percentile among past instances of its kind, or its order of magnitude). Magnitudes then compare across crude, seats and casualties, so they can drive sizing on one scale.
- **What the session writes.** The reference class and where this instance sits in it. That is base-rate reasoning, the thing E1 shows the model is good at.
- **The status-quo problem mostly goes away.** The instance's place in its class does not need today's level, except for price questions, where the class is "moves of this size".
- **Scoring is by rank:** the instance's realised place in its class against the place the session and the market implied. That is calibration-free, as decision 6 asks.
- **E1 reads as a scale call.** "This will be an ordinary-sized instance, not the large one the market is pricing." Most instances of anything are ordinary.

### Calibration methodology (from `calibration_methods.py`, 2026-10-01)

Measured, walk-forward on BT-A (fit on earlier months, score the next):

| | log loss | calibration error |
|---|---|---|
| raw | 0.316 | 0.038 |
| bin-by-bin (isotonic) | 0.317 | 0.020 |
| **Platt: one slope, one shift** | **0.309** | **0.015** |
| beta: separate low and high ends | 0.311 | 0.023 |

Carried from BT-A to BT-T2, a different pipeline, every method made things *worse* than raw: log loss 0.337 raw against about 0.35 for each map.

The method that follows:
1. **Calibrate within a pipeline only. Never carry a map between pipelines.** Miscalibration depends on how the question is asked: an as-of date or none, priced at the lock or 14 days out, evidence or none.
2. **Platt scaling as the default,** starting at "no correction" and refitted walk-forward as resolved answers accumulate. Applied only once its walk-forward score beats raw on that pipeline's own history.
3. **Shrink toward the pipeline's own overall fit by context** (event class, horizon, evidence or none) rather than fitting each small group alone. Two parameters per group, partially pooled.
4. **Test two elicitation fixes in a dedicated calibration pass:**
   - several independent sessions per event, averaged in log-odds;
   - asking half the contracts as "the chance it does *not* happen".

   The YES overconfidence may be partly how the question is framed.
5. **Calibration never touches E1's selection or magnitude's ranks.** It only rescales chances for the money score and for sizing (decision 6).

### Calibration, the pattern

The model is asymmetric: accurate when it says "unlikely", overconfident when it says "likely".

Proper calibration is learned within the same pipeline and conditions, from earlier resolved answers only. Moving BT-A's map onto BT-T2's answers made the log score worse (−0.078 to −0.090), because the conditions differ:
- BT-A gave no as-of date and priced 14 days out;
- BT-T2 gave an as-of date and priced at the lock.

So calibration runs per format and per pipeline, as standing passes accumulate history. Until then, the working rule is: trust low numbers, shrink high ones.
