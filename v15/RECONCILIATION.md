# Reconciliation: what the briefs claimed, what the code does

**v11 §F.** One pass, then maintained. Every number below was read out of `harness/` and the live ledger on 2026-09-08,
not copied from a brief. Where the build and the brief disagree, the disagreement is stated, not smoothed.

At the twelve-round read someone will ask whether the numbers mean what the documents say. This is that answer.

## Pre-registered constants (`harness/config.py`)

| Constant | Value | Brief | Agrees? |
|---|---|---|---|
| `NULL_CALL_WEIGHT` | 0.2 | v4 §6 invariant 6 | yes; stored on every resolution and scorecard |
| `VALIDATION_THRESHOLD` | 1.0 | tightening A5 | yes |
| `QUALITY_FACTORS` | round_class clean 1.0 / learning 1.0 (v12 §0.5: the learning discount was dead code once v11 excluded learning rounds entirely, and is now stated as 1.0 rather than left to mislead); scorer self 0.6, second 0.85, human 1.0; coverage adequate 1.0, thin 0.7, english_only 0.7, none 0.0; call_type positive 1.0, null 0.2; evidence stated_dated 1.0, inferred 0.7, none 0.7 | tightening A5/A12 | yes — but see the note below: the learning factor is now dead code for weights |
| `MISS_FACTORS` | coverage, evidence class, call type (never round class or scorer) | tightening A5 | yes |
| `COMPONENT_DISCOUNT` | 0.85 | v8 §E3 | yes |
| `CROSS_NODE_DISCOUNT` | 0.85 | v10 §D1 | yes |
| `SCORING_WINDOW_DAYS` | days 14, weeks 56, months 183, never none, default 28 | tightening A4 | yes |
| `DUE_AT_MAX_DAYS` | 90 | v10 §A2 | yes |
| `NARRATIVE_DUE_DAYS` | 5 | v10 §A4 | yes |
| `SCHEDULED_WINDOW_DAYS` | 7 (reveal look-back only; the forward window is the scoring window) | v8 §D3, widened by v9 §A3 | yes |
| `BAND_SESSIONS` / `BAND_SIGMA` | 20 / 2.0 | v10 §I1 ("20-session realised band") | yes, and **met on the live ledger since v12 §0.1**: every one of round 12's seven listed legs computes a full 20-session band. Mis-specified for illiquid names — see 15 below |
| `EFFECT_KINDS` | direction, volume, vol, timing | v10 §J | yes, frozen |
| `WINDOWS` | event_day, days, weeks, to_due | v10 §J | yes, frozen |
| `GRID_DEGREES` | 0, 1, 2, 3 | v10 §J | yes, frozen |
| `FACTOR_KINDS` | equity, private, physical, aggregate | not in any brief | **build-only**: the grid needs a factor axis for `risk_rules.covers`; declared with the grid and frozen with it |
| `WINDOW_DAYS` | event_day 2, days 14, weeks 56 | not in any brief | build-only: maps a call's `falsifier_window` onto the grid's window axis |
| `FREEZE_ROUNDS` / `REQUIRED_MIX` | 7 / headline ≥ 4, lag_test ≥ 3 | v10 §B3 | yes |
| `CAP_TAGS`, cap lookback | weather, late_headline; lookback 1 (one in any two consecutive) | v10 §B2 | value yes, **behaviour changed by v11 §C: the cap warns, it no longer refuses** |
| `STRATA` / `STRATUM_QUOTA` | chemical 2, ports_logistics 2, power_grid 1, corporate_distress 2, regulatory 2, other 1 per rolling 10 admitted rounds (retuned by v12 §0.5 so the quota sums to <= 10) | v11 §D ("pre-registered, reviewed at twenty") | **awaiting the human's ratification (§H1)**; the strata list is the build's, not the brief's |
| `INTAKE_GATES` | Q3, Q8, Q9 | v11 §C | yes; Q9 is the one that still accepts an unbacked assertion (see 21) |
| `ELIMINATORS` / `ELIMINATOR_PRECONDITION` | tide, traversed, weather, slack, self_hedged, immaterial_position, no_path, each with a declared precondition | v13 §A2/§A3 | yes, closed list; **awaiting ratification (§E1)** |
| `TIDE_RATIO_MIN` / `POSITION_SHARE_FLOOR` / `SURVIVING_MAGNITUDE_MIN` | 1.0 / 0.05 / 1.0 | v13 §A2, §A4 | **build-only numbers**: the brief names the tests, not the thresholds |
| `BAND_METHOD` / `BAND_SESSIONS_EMPIRICAL` / `BAND_PCTILE` | empirical / 60 / 5th-95th | v13 §B1 | yes |
| `TURNOVER_FLOOR_USD` / `FX_TO_USD` | $2,000,000 median daily / a static table dated 2026-09-01 | v13 §B1 ("add a turnover floor") | **build-only**: the brief gives no number and no way to compare currencies. Awaiting ratification (§E2) |
| `PARTICIPANT_CLASSES` / `CLASS_ADJACENCY` | contract, credit, equity_generalist, equity_specialist, options, compliance, physical_press, procurement; distance capped at 3 | v12 §E1 | yes, closed list; **awaiting the human's ratification (§J1)** |
| `CHANNELS` | sell_side_coverage, shared_data_vendor, index_event, rating_action, trade_press_pickup | v12 §E2 ("a pre-registered channel set") | the brief names three by example; the build adds rating actions and trade-press pickup |
| `FADEABLE_IMPLIED_MIN` | 2.0 (%) | v12 §D3 ("materially above zero") | **build-only threshold**: the brief does not give a number. Reviewed at twenty with the rest |

## Where the build differs from the brief

1. **Learning rounds and rule weights (v11 §A1).** The brief says this was "already true". It was not: before v11 a
   learning round's resolutions entered rule weights at a 0.5 quality factor. v11 excludes them entirely. The effect on
   the live ledger, measured at the change: `lib.route_closure` 0.3 → 0.0 (2 trials → 0), `lib.substitutes_gift`
   −1.0 → 0.0, `lib.liability_periphery` −0.4 → 0.0, and 42 citations across the seed rounds became non-trials.
   `lib.equity_visibility_ratio` stays validated on clean rounds alone. The `round_class` quality factor is now dead
   code for weights and survives only as documentation of the old behaviour.
2. **The cap (v11 §C).** The brief lists what becomes a tag and says "never a rejection", without naming the cap. The
   cap was a rejection driven by a first-traversal tag, so it had to stop refusing; it is now a warning note on the
   round plus a programme stat. **The human should confirm this reading** — it is the one place v11 §C was applied by
   inference rather than by instruction.
3. **Q9's gate (v11 §C).** The brief keeps Q9 as a gate. v10 had made "came through the enumeration tooling" the only
   pass; v11 relaxes it to *either* the enumeration path *or* a fixed window whose rejections are on the ledger,
   because a human sweep that logs its skips is exactly as verifiable. Q9 refuses on clean rounds only: on a learning
   round the calls never enter the lag stats, so selection honesty cannot bias them, and it is recorded as a tag.
4. **Q3 is detected as well as asked.** The brief calls Q3 structural. The build adds a price-move detector on the
   prompt (`rounds.looks_like_price_event`) which refuses unless the human answers Q3 `pass: <why>` explicitly. Not in
   the brief; it is the only gate a mis-typed prompt can slip through.
5. **`skip` as a selection outcome (v11 §0.4).** The brief says not to manufacture a failing question for the hGears
   candidate. `skip` was added to `FAILING_QS` and to `nomad_decide` so a pass-over can be recorded as itself. A skip
   may supersede an earlier reject; that is how round 10's manufactured Q9 rejection was ratified.
6. **Cell clocks (v10 §K, corrected under v11).** A grid cell's dating window runs to the event date + 90 days, not to
   the operator's chosen `due_at` on the leg, and a cell is dated only by facts belonging to its own holder (plus
   parent and children). Both were wrong when the OEM reporting dates were first entered: one holder's results date was
   dating another holder's cells. Not a brief item; found by running §0.3.
7. **The firewall under concurrent rounds (v11 §E).** `hook.py` previously allowed retrieval whenever some round was
   `open`. With rounds running concurrently the invariant is "nothing is pre-lock": retrieval is denied while any round
   sits in `created` or `locked`. **This does not protect a round that has not been submitted yet** — see round 11's
   contamination note. The enumeration path is what closes that hole, and it was not used for round 11.
8. **Round 10's mechanical dates (v11 §0.3).** The brief expects the OEM reporting dates to date "round 10's 24
   gate-pass vol cells". After the corrections in (6), 16 cells are dated (Volkswagen, BMW, Mercedes, Continental ×
   four windows each). Forvia's four and Voltabox's four are not: no reporting date could be read for Forvia, and
   Voltabox has no listed options, so its vol cells fail the gate before dating matters.
9. **Bands on the live ledger (v10 §I1).** `BAND_SESSIONS = 20` is the pre-registered method. Every price observation
   written for rounds 8–10 uses 6–10 sessions, taken from the closes recorded in each round's own evidence, and says so
   in its own `band_method` field. The bands are therefore wider than the method intends and the re-encode test is
   conservative. **Resolved by v12 §0.1** and worth stating as a correction rather than a fix: those
   bands were so wide that only a catastrophe could register, so the engine was detecting disasters, not re-encodes.
   The first cut of the corrected backfill was wrong in the opposite direction — a fixed level band applied across a
   90-day window measures drift — and was rebuilt as a one-day band, sigma from the pre-registered pre-event window
   applied to each prior close. The ledger was restored from backup and re-run rather than corrected in place.

10. **§E6's premise (v12).** The brief says "every round's evidence already names its carriers". It did not: `evidence`
   held a url, a headline and an excerpt, and of 91 rows across rounds 1-11 exactly six resolved to a registered
   carrier, because the registry holds descriptive names and evidence holds press headlines. `evidence.carrier` was
   added and is resolved at write time (host, then headline), with an explicit carrier accepted from the operator.
   The class-distance test therefore has 70 classed legs, 68 of them "divergent", and **zero re-encodes at any
   distance** — the test is not thin, it is empty, and stays empty until re-encodes exist.
11. **§G's materiality hint is a sentence, not a number (v12).** The brief asks for "estimated event impact over the
   largest listed holder's size, computed from whatever the store holds at intake". At intake the store holds a
   headline and no touched set, so the ratio is not computable: `materiality_hint` is always null and
   `materiality_basis` says whether any listed holder in the names book matches the headline at all. Reported, never a
   gate, as the brief requires — but less than the brief asked for.
12. **§D is unreadable on a backdated round (v12).** `implied_at_lock` is read at lock; on an event weeks or months old
   every reading available at lock is post-event and would import the outcome. Backdated rounds therefore record
   `method: none` with that reason and are `executable: no` by construction. §D measures something only on a live
   round, which makes it a downstream dependent of the enumeration path.
13. **Q2 is computed from the submitted date, not from the event (v12, found in round 12).** The cutoff test runs at
   intake, before any retrieval, so it can only test the date the submitter claims. Round 12 was handed over as
   2026-07-31 and is 2025-07-31; Q2 passed and the event predates the operator cutoff by eleven months. Recomputing Q2
   at `open_retrieval` and voiding on a fail is the fix and is **not yet built** — round 12 was voided by hand.
14. **Q1b answers about our reach in the language of the node (v12, same round).** It returned "0 disruptions in the
   prior 90 days, 0 in the prior 12 months; nothing recorded on the ledger or in reachable registries" for El Teniente,
   whose fatal collapse is the best-reported mining accident of the year. There is no mining incident registry in the
   fetch paths at all. Either register sources per node kind or have Q1b return `unknown` where it has no registry.
15. **The 2σ band is mis-specified for illiquid names (v12, measured).** On the Santiago small caps the pre-registered
   band is ±1.47% (SalfaCorp) and ±1.00% (Besalco), and the close falls outside it on 23 of 62 and 18 of 62 sessions.
   The liquid names sit at 1-6 of 64. Out-of-band carries no information on a thin listing until the band takes
   liquidity into account.

16. **The eliminators were round-level constants in their first cut (v13 A3, found by running §C).** `traversed` fired
   on all 28 legs of round 11 and `weather` on all 13 legs of rounds 6 and 8, because Q1a and Q1b are facts about the
   round. That is the mirror basket's error one layer down. Both were rewritten leg-level: `traversed` fires only where
   the ledger shows this holder already carried on this node before the event and returns **unevaluable** otherwise;
   `weather` fires only on the node Q1b was computed over. Firings fell 28 -> 14 and 13 -> 8.
17. **`eliminators_unevaluable` is a build addition (v13 A4).** The brief's schema has fired, checked, survives,
   magnitude and basis. An eliminator that cannot be evaluated is not an eliminator that did not fire, and without the
   distinction a leg surviving on no data is indistinguishable from a leg surviving on seven checks. Over rounds 1-12
   tide was unevaluable on 110 of 195 legs and slack on 58.
18. **`leg_claims.impact_pct` is a build addition, made after §C (v13).** §A4 says magnitude is expected move over the
   ambient band, and the ledger held no independent per-leg impact estimate: the only number was the call's own claim,
   and feeding an absence call's implicit zero back into tide would make A5's split a restatement of the call type. The
   operator now states the impact per leg at lock, with a basis. Round 13 is the first round carrying it.
19. **§C's check 2 failed (v13).** 39 absence calls across rounds 1-12: **0** on a leg where an eliminator fired, 10 on
   a surviving leg, 29 not attached to any leg at all because a `null` call carries `target = "none"`. The brief's
   instruction on this outcome is to say so plainly and stop building on §A, and that is what `docs/rounds/round13_recap.md`
   does. Check 1 passed, on 2 computable magnitudes out of 195 legs.
20. **Tide cannot be evaluated at lock (v13, open).** Its denominator is the leg's own band, which comes from the price
   carrier, which does not run until retrieval opens. The band uses pre-event closes only, so this is fixable by
   computing it at lock; until then a lock-time assessment records tide as unevaluable and a scoring-time pass supersedes it.
21. **Q9 still takes an unbacked assertion (v13, open).** `_compute_q9` returns the submitter's own verdict whenever no
   selection-window row exists. That is the same shape as the two gates §B fixed: Q2 tested the submitter's date until
   B2, Q1b reported our reach until B3. Round 13 carries an intake note saying its Q9 pass is an assertion the ledger
   cannot check.
22. **`carriers.fetch_paths` accepted a bare list (v12 bug, found in v13).** A host registration wrote a JSON list where
   a dict was expected, and every caller of `open_for_kind` -- enumeration included -- raised `AttributeError` until
   `fetch_paths` was made defensive and the four rows repaired. A convenience column took out the enumeration path for
   a version.
23. **`prices.SUFFIX` mapped `SSE` to Santiago (v12 bug, found in v13).** Shanghai and Santiago share the abbreviation.
   Round 13 would have priced a Chinese respondent off a Chilean ticker. Shanghai, Shenzhen, Tokyo, Hong Kong, Korea
   and Taiwan are now mapped explicitly.

24. **v11 §A3 is superseded (v14 A2).** Mechanical leg generation was refused on a clean round, because it was a
   substitute for the operator's decomposition where the outcome was known. Under v14 the decomposition is not the
   operator's job at all: generation is wide by construction and the operator's judgement moves to the elimination side
   and the vector, both recorded per leg. `generate_space` therefore runs on any round class.
25. **The appetite block and the term thresholds are build-only numbers (v14 A4/A7).** The brief names the five terms
   and says appetite is pre-registered; it gives no values. `APPETITE`, `TIDE_RATIO_MIN`, `POSITION_SHARE_FLOOR` and
   `SURVIVING_MAGNITUDE_MIN` are the build's, awaiting ratification, and must not be moved to make legs arm.
26. **`pricedness` was keyed to the wrong thing in its first cut (v14, found by §D2).** A re-encode was read per
   (holder, node) row, so round 10's filer read as unpriced on one node and priced on another, and one row cleared
   appetite on every term. A re-encode is a fact about the instrument. Both rows now read 0.05 and bind on pricedness,
   which is what §D2 says must happen.
27. **§B's stated prior was wrong (v14).** The brief expected `stake` to bind nearly everywhere. It binds on 6 of 225
   legs, because it **could not be computed on 217 of them**; `structural` and `expression` bind on 93% between them
   and are the two terms that can always be computed from the store. The ranking of binding terms is therefore mostly a
   fact about computability, and fixing that is prior to acting on the map.
28. **The enumeration query and the incident filter did not match (v14 C7, found in round 14).** `INCIDENT_WORDS`
   passes leak, outage, halt, shutdown and force majeure; no windowed query could return them, so a whole class of
   events was unreachable by construction while the filter screened for it. An outage feed was added. Declared: it was
   written while looking for round 14's event and checked against whether it surfaces it (it does not).
29. **C6 costs clean rounds, immediately (v14, first live consequence).** With Q9 returning `unknown` on an unbacked
   selection, a handed-over event cannot be a clean round. Six of the last nine events were handed over. Either the
   enumeration path reaches events like round 14's, or the freeze's seven clean rounds do not happen.

## The carriage table (`harness/library.py: CARRIES_BACKFILL`)

Still awaiting ratification in full (standing item since v8). 34 keyed rules plus 13 matched by text prefix. Two rules
were keyed during v9/v10 (`lib.toxic_release_shared_space`, `lib.single_supplier_hidden_node`) and two harvested since
(`lib.catalyst_not_about_node_is_tide` carries occurrence and absence; `lib.repeat_filer_base_rate` carries map).
`lib.force_majeure_fast_carrier` remains `[ordering]` at weight 0.0 (untested as carried), per the v8 ruling.

## The risk-rules seed (`harness/risk.py: RISK_SEED`)

Seven rules, each with a `knowable_from` taken from the round that made it explicit: tide/visibility (2026-04-03),
weather/recurring disruption (2026-04-09), recovered-before-entry (2026-04-03), catalyst-about-the-node (2026-09-08),
slack (2026-04-09), cut-into-glut (2026-03-12), self-hedged owner (2026-04-03). Six are linked to a library rule; the
self-hedged owner has no library rule behind it. **Awaiting the human's ratification (v10 §H3).**

**Superseded by v12 §0.2.** Six of the seven are ordinary practice long predating the programme, and dating them by
when they became explicit to us made the coverage curve measure our own learning: mirror share appeared to decay 0.92
(12 March) → 0.75 (3 April) → 0.5625 from 9 April. They are now dated to the `1900-01-01` sentinel with
`origin = practice`, and the curve is flat at 0.50-0.56 across all twelve rounds. `risk.catalyst_about_node`, harvested
from round 9, keeps its programme date (`origin = programme`). What the old curve showed was the harness, not the world.

## Programme numbers as of 2026-09-09 (after round 14)

Rounds 1-4 learning, 5-10 clean, 11 learning, 12 voided then re-run as learning, 13 clean and scored, 14 learning and
partially scored (two calls still inside their windows). Two void rounds. Validated rules:
`lib.equity_visibility_ratio` only.

**Arming: still zero, and now diagnosed rather than merely counted.** The wall map over 225 legs of rounds 1-13 puts
`structural` as the binding term on 114 legs and `expression` on 96, with `stake` binding on 6 and `pricedness` on 6.
That ranking is mostly a fact about what can be computed: **`stake` had no value on 217 of 225 legs and `operator` none
on 201**, while `structural`, `pricedness` and `expression` are computable everywhere. Not one leg in the programme's
history clears appetite on every computable term. The closest, round 10's two paragon rows, carry the highest stakes
recorded (7.12 and 19.02) and are killed on `pricedness` at 0.05: re-encoded at latency zero, in the price before it
was knowable to us.

Operator risk, computed from clean resolutions: absence 15 of 16, occurrence 8 of 14, **map 1 of 5**. Every map loss
turned on a primary document that existed and was not read, except round 14's, where the settling document did not
exist until day five and the attempt is on the ledger.

Round 14 generated 23 legs against round 13's hand-decomposed 10; the anchors cut 14, the operator restored five paths
and killed one more by hand. Every survivor bound on `expression` at 0.0 (all unlisted); every eliminated listed leg
bound on `stake` at 0.04-0.26. The things with a path to the event cannot be held, and the things that can be held have
nothing at issue.


## Programme numbers as of 2026-09-09 (after round 15)

Rounds 1-4 learning, 5-10 clean, 11 learning, 12 voided then re-run as learning, 13 clean and scored, 14 learning and
partially scored, 15 learning and partially scored (three calls still inside their windows). Two void rounds.
Validated rules: `lib.equity_visibility_ratio` only.

**28. The wall map's headline was a defect, and the correction removes a wall (v15 §0b.5).** v14 §B reported
`structural` binding on 51% of legs and `expression` on 43%. `binding_term` was `min()` over the terms that had a
value, so a leg whose `stake` was unknown reported as binding on whichever computable term ranked lowest -- and
`stake` was uncomputable on 217 of 225 legs. Ranking by lowest *computable* term today reproduces v14's table to
within a point (structural 49.0%, expression 44.6%, pricedness 2.8%, stake 2.4%, operator 1.2% over 251 legs), which
confirms the defect as its cause. The corrected distribution: **`unassessable` 53.8%, `expression` 43.8%, `stake`
1.6%, `pricedness` 0.8%, `structural` 0%.** Of the 135 unassessable legs, 123 are ones v14 attributed to
`structural`. **`structural` binds on nothing.** `expression`'s 44% is honest by construction, because it reads 0.0 on
an unlisted holder and no unknown term can bind below zero. **"Selection is the only lever" was read off the table the
defect produced and does not survive as stated**; what survives is that expression is the one demonstrated wall and
that over half the map is unread. Round 14's own §K1 said fixing computability is prior to fixing selection, and that
is now the finding rather than the caveat.

**29. Four more silent failures, same shape (v15 §0b.1-0b.4).** The re-encode lookup that fires the §D2 wall could
throw and leave `pricedness` at a passing value; an unresolvable rule citation dropped out of the structural
computation and cost the leg nothing; `second_scorer_batch` dropped rounds whose blind view failed while reporting
success, on a statistic C1 suspends disputed weights against; and the blind view silently omitted unresolvable rules,
reintroducing the mechanism-dispute class v7 §C2 closed. All four now record and report. Regression tests §J17-J20.

**30. A fifth found by running v15 (round 15).** `convergence()` returned `divergence_held: 0` with a note saying the
frontier had converged to price, on a round where no effect carried an implied reading and nothing had ever been
compared to price. It now returns a `state` of `divergence_held` / `converged_to_price` / `unreadable`, and the
failure verdict fires only on branches that could be read. Same disease as §0b, one layer along.

**31. §I1 caught the generator on contact (round 15).** With node kinds in the store, the v14 leg generator was
turning "both listed in the US" into a leg with a path. Attribute nodes are now skipped by `generate_space`, by
`assess_round` and by the claim template: nine such legs were excluded on round 15.

**32. Anchors do not yet run per effect.** §A5 specifies elimination at the effect; the eliminators still run per leg,
so round 15's `elimination_rate` over the effect DAG was 0.0. Named as owed rather than reported as done.

**33. The vocabulary does not reach a third domain.** `node_kind` has no entry for digital infrastructure (recorded
`other`); `lag_band` bottoms out at `days` against an outage of 2h22m; and no library rule carries `map`, so a fifth
map call was locked with `no-mechanism:`. All three recorded rather than widened mid-round.

**Arming: still zero.** Round 15 computed `stake` at lock on three of four legs -- the first round where impact
estimate and pre-event band both existed before retrieval. The leg with a path binds on `expression` at 0.0 (an
unlisted facility); the three listed legs bind on `stake` at 0.005-0.026. `bridge_paths` returned empty. The declared
synthetic exposure over the three listed names gives `basket_stake` 0.0093 against a floor of 1.0: about 107x more
exposure to mega-cap technology beta than to the thing the analysis was about.

Operator risk, computed from clean resolutions, is unchanged by round 15 because learning rounds never enter it:
absence 15 of 16, occurrence 8 of 14, map 1 of 5. Round 15's map call was scored a hit and is **flagged for dispute**
rather than banked, because it moves that statistic on a reading a strict scorer can reverse.
