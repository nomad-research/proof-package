# Round 15 recap: a Google Cloud us-west1 region outage — and the corrected wall map

Round id `01a085ea-d88c-70bf-92dd-85f3e44db228`. **Learning class** (Q9, below), tag `lag_test`, size band `headline`. First round under v15: the unit is the **effect**, not the leg. Nine calls, six resolved, three still inside their windows: outcome **1.0**, mechanism **1.0**, baseline **0.0**, edge **1.0**, map **1.0**.

Read §0b first. It changes a number the last version led with.

---

## §0b. The corrected wall map

v14 §B reported, over rounds 1–13: `structural` binds on 51% of legs, `expression` on 43%, `stake` on 2.7%. It also reported that `stake` could not be computed on 217 of 225 legs. The brief's §0b.5 identified the cause: `binding_term` was `min()` over the terms that happened to have a value, so a leg with unknown `stake` reported as binding on whichever computable term ranked lowest.

**Fixed, and re-run.** `binding_term` now reads `unassessable` whenever an unknown term could bind below the lowest computable one — which is whenever the lowest computable ratio is above zero, since an unknown term's ratio could be anything from zero up. `summarise()` buckets those separately and reports, per term, how often the ledger had no value at all.

**First, the defect reproduces v14's headline exactly.** Ranking by lowest *computable* term over the same cut (251 legs today, against v14's stated 225 — the store has grown):

| binding term (v14 method) | legs | |
|---|---|---|
| structural | 123 | 49.0% |
| expression | 112 | 44.6% |
| pricedness | 7 | 2.8% |
| stake | 6 | 2.4% |
| operator | 3 | 1.2% |

That is v14 §B2 to within a point. The defect is confirmed as the cause of that table.

**The corrected distribution, same cut:**

| binding term | legs | |
|---|---|---|
| **unassessable** | **135** | **53.8%** |
| expression | 110 | 43.8% |
| stake | 4 | 1.6% |
| pricedness | 2 | 0.8% |
| **structural** | **0** | **0%** |

**Structural binds on nothing.** Of the 135 unassessable legs, 123 are ones v14 attributed to `structural`. The term v14 named as the programme's dominant wall never binds once the unknowns are honest; it was only ever the lowest term that happened to have a number.

What survives the correction:

- **`expression` is the one demonstrated wall**, on 44% of legs. Those readings are honest by construction: `expression` reads 0.0 on an unlisted holder, and no unknown term can bind below zero, so the attribution stands without assuming anything.
- **On the other 54% we do not know what binds**, because `stake` has no value on 96% of legs and `operator` none on 90%.
- Where all five terms *can* be computed — nine legs in the programme's history — the binding term is `stake` on seven and `pricedness` on two. **No leg has ever cleared appetite on every term.**

**So "selection is the only lever" does not survive as stated.** v14 read it off structural + expression = 94%. The corrected map says one wall is expression, which selection *can* address by choosing a listed universe, and the rest of the map is unread. Round 14's own §K1 suspected this — *fixing computability is prior to fixing selection* — and it is now the finding rather than the caveat.

The other four defects are fixed with regression tests: the re-encode lookup can no longer fail silently and leave `pricedness` passing (§J17), an unresolvable rule citation now costs the leg and appears in the blind view (§J18), `second_scorer_batch` returns its failures and the note carries a warning (§J19), and `binding_term`/`summarise` are covered by §J20. **Housekeeping:** the 147 tests shipped in the archive do run and do pass; `nomad_mirror_dry_run` is retired from the tool surface (the function stays so old rounds replay); `nomad_generate_legs` is marked SUPERSEDED in its own docstring and summary line.

---

## The round

**Intake, and three vocabulary gaps.** The enumeration path was run first over the event's own window — 2026-08-18 to 2026-08-21, all three windowed feeds spanning at 42–64 days of reach, **381 dated candidates** — and did not reach this event. The only data-centre items were two construction disputes. So Q9 fails and this is a learning round, as round 14 was.

Three places the programme's own vocabulary does not reach this domain, all recorded rather than widened to fit:

1. **`node_kind`** has no entry for digital infrastructure. Recorded as `other`; carrier density does not qualify.
2. **`lag_band`** bottoms out at `days`. The outage lasted 2h22m. The finest band the harness has understates the call by two orders of magnitude.
3. **No library rule carries `map`.** The map call was locked with `no-mechanism:` and its `mechanism_outcome` is `unknown` — a fifth map call and still nothing covering it.

**Generation.** Four legs after the region was modelled as a facility under its parent; **nine attribute-node legs excluded** by §I1, which found a real defect on contact: the v14 generator was turning "both listed in the US" into a leg with a path. Attribute nodes are now skipped by the generator, by the assessor and by the claim template.

**The effect DAG.** Seven effects over two depths — five roots and two compositions:

| depth | kind | holder | support | via |
|---|---|---|---|---|
| 1 | timing | Alphabet | 1.0 | — |
| 1 | obligation | Alphabet | 1.0 | — |
| 1 | cost | Alphabet | 1.0 | — |
| 1 | direction | Alphabet | 1.0 | — |
| 1 | volume | *(unnamed at lock)* | 1.0 | — |
| 2 | cost | *(unnamed at lock)* | 0.595 | `input_supply` |
| 2 | obligation | *(unnamed at lock)* | 0.42 | `input_supply` |

Four kinds on one holder, each with its own carrier, falsifier and due date, and no sign anywhere. The two depth-2 effects have **no holder named at lock** — deliberately: the store has no cloud tenants, and naming one would have been a prior standing in for a fact not yet fetched.

**The transform table did real work at the point of modelling.** The first draft called the relation `offtake` (the operator's view). Under `offtake`, `volume → obligation` is 0.0 and the tenant's own service obligation would have been unreachable. The correct type from the tenant's side is `input_supply`, where it transmits at 0.6. Naming the relation correctly is what decided which effects existed, which is what §A4 is for.

**The ACK graph, and the forced/scheduled distinction earning its keep.** Three forced ACKs (an incident report, SLA credits, a tenant service notice) and one certain calendar date (month end, 31 August). The incident report **fired on 2026-08-27** and delivered: fibre maintenance compromised inter-datacentre capacity, automated rerouting failed, congestion cascaded through Spanner Paxos consensus and the Unified Metadata Server. Two successor ACKs were named **at firing** and segment 1 locked with lineage. This is the first time in the programme that a round advanced a generation on a fact that did not exist at lock.

### Calls

| # | Call | Due | Outcome |
|---|---|---|---|
| 1 | sign 0, GOOGL inside its band, five sessions | 27 Aug | **hit** — inside on all 13 sessions of the window |
| 2 | sign 0, AMZN inside its band | 27 Aug | **hit** — inside on all five; out of band on 28 Aug, the seventh session, recorded against the call |
| 3 | sign 0, MSFT inside its band | 27 Aug | **hit** — inside on all 13 |
| 4 | predicate: a public incident report naming a cause within 30 days | 19 Sep | **hit** (early) — published 27 Aug, day seven |
| 6 | map, branches shared_logical_dependency / facility | 19 Sep | **hit** (early), branch `shared_logical_dependency` — **flagged for dispute, see below** |
| 7 | lag_band days, all services restored | 3 Sep | **hit** — 2h22m; three factors all hit |
| 0 | null: no constraint price reprices within 30 days | 19 Sep | waiting |
| 5 | magnitude_order: the account precedes the money | 5 Oct | waiting — the account is public, no credit stated by anyone |
| 8 | null: no listed company attributes a material impact within 45 days | 4 Oct | waiting |

**The map call is flagged, not banked.** The falsifier was "the incident report names a power, cooling or physical facility cause", and it did not fire; the report names exactly the shared logical dependencies the claim named. But the *originating* cause was scheduled fibre optic maintenance — a physical operation on physical plant — and the claim said "rather than a physical facility failure". A strict reader can call this a miss on the first clause. The counter-argument is in the scorer note in full, because this call moves a standing statistic (the operator's map record) from 1-of-5 to 2-of-6, and a statistic that moves on a contested reading should be contested first.

**Six of six is not six of six.** Three of the resolved calls are band nulls, and a fourth (duration) is an absence claim in a different costume. Two are real occurrence results. **A scorecard weighted toward nulls flatters a null detector**, and the baseline here is a naive reader that had no chance: it does not hold anything either.

---

## What v15 reported, and what each number says

| stat | value | reading |
|---|---|---|
| `generation_width` | 7 | five roots, two compositions |
| `elimination_rate` | 0.0 | **no effect was eliminated.** The anchors ran per leg, not per effect, on this round |
| `root_depth` | 7 at zero | nothing is being justified by distance — the honest reading of a round with one hop |
| `bridge_paths` | **0** | no path has a stake-clearing ancestor and an expression-clearing descendant |
| `contradictions` | 0 | no two paths point at one ACK with opposite implications |
| `support_rankings_agree` | **true** | §F7's warning fires: every effect group has one path, so cross-membership measures nothing here |
| `divergence_held` | 0, state **`unreadable`** | see below |
| `basket_stake` | **0.0093** | against a floor of 1.0 |
| `attribute_coverage` | 0.6 | on the three listed names |

**A defect found by running it.** `divergence_held` returned 0 and the note said the frontier had converged to price. It had never been compared to price: all seven effects carried no implied reading, because no option or realised reading existed at lock. Reporting an unmeasured frontier as a converged one is the same disease §0b was written about, one layer along. `convergence()` now returns a `state` of `divergence_held` / `converged_to_price` / `unreadable`, and the failure verdict fires only on branches that could actually be read. Regression test added.

**The declared synthetic exposure is the round's sharpest number.** Any basket over these three names is long the same venue, the same currency and the same size bucket, and those loadings do not cancel between an operator and its substitutes because all three are mega-cap US technology. Declared exposure 2.8 against an intended residual of 0.026: **`basket_stake` 0.0093**, about 107× more exposure to mega-cap tech beta than to the thing the analysis was about. Below the floor by two orders of magnitude, and named at construction rather than found in a P&L.

---

## The wall, in a third domain

Stake was computable **at lock** on three of four legs — the first round where the impact estimate and the pre-event band both existed before retrieval.

| leg | survives | binding | stake | expression |
|---|---|---|---|---|
| the region itself (unlisted facility) | yes | **expression** | uncomputable | **0.0** |
| Alphabet | no | **stake** | **0.0257** | 0.75 |
| Amazon | no | **stake** | 0.0060 | 0.75 |
| Microsoft | no | **stake** | 0.0049 | 0.75 |

**The thing with a path cannot be held. The things that can be held have nothing at issue.** Round 14 found this among Indonesian smelters; round 15 finds it among mega-cap cloud operators, where the anti-correlation is if anything sharper: being the operator of a flagship cloud region means being large enough to own one, which means one region's worst day is 2.6% of a single session's ordinary noise.

And the mechanism is visible rather than inferred. **An availability failure consumes nothing and leaves nothing short.** There is no cargo to reroute, no allocation to make, no premium to pay, no queue. The library's entire transmission machinery — constraint prices lead, the toll booth learns before the cargo, a cut into a glut is silent — was built on events that withhold a *consumable*. This event has none. Two rules were proposed for it (`lib.availability_has_no_constraint_price`, `lib.account_precedes_the_rebate`), and the first is the domain limit stated so it can be tested rather than rediscovered.

---

## For the human

1. **The wall map correction is the headline, and it costs a conclusion.** `structural` binds on zero legs. Over half the ledger is `unassessable`. "Selection is the only lever" was read off a table the defect produced.
2. **Ratify or reject the v15 appetite block**, as appetite and not as targets: frontier bound 120, hop discounts and the transform seed, independence discount (1.0 at root → 0.15 at leaf), support threshold 0.30, inert-stake ceiling 0.25, convergence threshold 0.5, `basket_stake` floor 1.0.
3. **The map call needs a second scorer before its result is banked.** It moves the operator's map record and the reading is genuinely contestable.
4. **The selector is suspended.** Three consecutive Q9 fails; two of them are this event, which was refused twice while the right intake call was found. It needs `nomad_selector_clear` before any further intake, and the underlying problem is unchanged: the feed set is industrial vocabulary and reaches neither Indonesian smelters nor cloud regions.
5. **Anchors do not yet run per effect.** §A5 specifies elimination at the effect; the eliminators still run per leg, and `elimination_rate` was 0.0 on the effect DAG. That is the largest piece of §A still owed.
6. **`divergence_held` needs implied readings to mean anything.** Until a round carries option or realised readings per effect, §E returns `unreadable` and the frontier statistic is not a measurement.
7. Three calls are still inside their windows (19 Sep, 4 Oct, 5 Oct), and two forced ACKs are open with no date, which is the point of them.
