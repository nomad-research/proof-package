# Components register (2026-10-01)

**Rob's framing:** an unratified value means "the system is missing a defined component that needs discussion". It is not a threshold to be assumed so that a test can run.

**What this register covers:**
- the 85 values in `config/appetite.json`;
- the 22 values in `docs/nomad_v18_updates.md` §7;
- the constants inside the Polymarket studies.

**How it sorts them:**

| Part | What it holds | What to do |
|---|---|---|
| 1 | The missing components of the event-contract system | Discuss |
| 2 | Test design values | Set in each pre-registration before data |
| 3 | Values frozen inside finished studies | None (historical) |
| 4 | Values that do not apply to this system | Removed from discussion |

Nothing in Part 4 has been deleted from the code. `config/appetite.json` is read by the parked equity harness (`nomad16/`) and its tests, so deleting values would break code that is parked rather than retired.

---

## Part 1. Missing components (for discussion)

The system as it now stands (`docs/nomad_v18_addendum_B1.md` §6–8):
- A thesis is a subgraph of events.
- Each subgraph is one basket, meaning which positions it holds, not how much of each.
- Links are never traded on their own.
- A basket's stake = position weight × global scale.

### C1. Global risk: how much of the bankroll is at risk at once

- **Missing.**
  - Four numbers (blank, Rob's):
    - the most deployed at once;
    - the most on one basket;
    - the most on a group sharing a driver;
    - the drawdown stop.
  - A definition of "shares a driver".
- **Stood in for it.**
  - `MAX_EVENT_SHARE` 0.05 and `MAX_CLUSTER_SHARE` 0.15 (v18).
  - The scale part of `KELLY_FRACTION`.
  - The equity-era `LOSS_BUDGET_PER_ROUND`, `LOSS_CAP_PER_TIDE` and `STOP_RULE`.
- **What we know.** Under far-rung weighting most baskets lose, so a drawdown stop set without allowing for that would stop the book while it is working as designed.
- **Questions.**
  - Is "shares a driver" authored by the session, taken from the world graph (D edges), or both?
  - Is the drawdown counted per month, or from the peak?

### C2. Position risk: one basket's size relative to the others

- **Missing.**
  - The weighting rule.
  - What a basket's "risk" means: its worst case across its own scenarios, or the money spent.
- **Stood in for it.** Kelly sizing and `KELLY_FRACTION` 0.25 (v18 §5.5, suspended).
- **What we know.** T0, post-hoc: the tier claims bet at the lock are positive under all three price-only weightings:

  | Weighting | Return on stake |
  |---|---|
  | Equal shares | +27% |
  | Equal variance | +37% |
  | Equal stake | +69% |

  But equal stake rests on three long shots, and every interval spans zero. Named-contract claims and the sessions' picks show nothing.
- **Questions.**
  - How lumpy a return is acceptable?
  - Should size ever depend on something the session says (magnitude, confidence), and if so, what evidence would earn that?

### C3. Magnitude: how far, how many, how soon

- **Missing.** How magnitude is stated, how it is mapped to contracts, how it is scored, and how it enters sizing. Rob: "sizing should most directly be related to magnitude"; and "what if magnitude is just a factor derived from risk?"
- **Stood in for it.** V1's three tier words (mild, moderate, severe), mapped to the rung whose lock price is nearest 0.50, 0.25 or 0.10. These are builder values, so magnitude has been defined partly through price. The scorer never measured magnitude as magnitude.
- **What we know.**
  - Claims whose "if" happened, by type:

    | Claims stated as | Held | Mean lock price |
    |---|---|---|
    | Magnitude (tier) | 8 of 9 | 0.43 |
    | Named contract | 2 of 5 | 0.55 |

  - The only magnitude miss was a timing error.
  - The equity-era system carried magnitude as `magnitude_pct` and stake = move ÷ band (`nomad16/vetoes.py`), the same idea in instrument terms.
- **Questions.**
  - Is magnitude authored (in world units: "crude above $95", "at least 12 seats", "by March"), or derived (the multiple a basket returns on its risk)?
  - What about yes/no events with no scale?
  - Does a bigger magnitude mean a bigger position, or a position further out at the same stake?

### C4. The thesis subgraph and its basket

- **Missing.** What bounds a subgraph. How two subgraphs are shown to be independent. Whether two baskets may hold the same contract.
- **Stood in for it.** `P_EDGE_MIN` 4.0, `CLUSTER_MAX_EVENTS` 8, `NARR_MAX` 5, `SWEEP_BATCH` 6 (v18).
- **What we know.**
  - Same-underlying hedges, which sit inside one subgraph, added +9.1.
  - Cross-entity hedges, which bridge what should be separate theses, added +0.9.
  - The automatic world graph merges unrelated events (one component of 181 events) unless it is cut.
- **Questions.**
  - Does the session draw the subgraph, the world graph, or both?
  - On overlap: the 2026-09-30 idea of a hedge as its own parallel thesis says baskets may share contracts; "independent subgraphs" says they may not. Which holds?

### C5. Belief: does the system need authored probabilities?

- **Missing.** The role of probability, now that sizing does not need it.
- **Stood in for it.**
  - The graded-belief floors: `EXCLUSION_FLOOR` 0.05, `OUTCOME_FLOOR_SHARE` 0.1, `PROB_SUM_TOL` 0.01.
  - The learning store: `COVERAGE_MIN_OBS` 30, `COVERAGE_SHRINK_K` 20.
  - The 18.1 scenario solver: `SCENARIO_CAP` 200,000.
- **What we know.**
  - V1 and V1b asked for no probabilities.
  - The 18.0c claim bet (addendum §5) needed P(if) and both branches; §6 folded claims into subgraphs.
  - The sessions' picks on primary contracts showed no edge over price.
- **Question.** Should T3's packet ask sessions for probabilities (so their calibration can be measured), for magnitudes only, or for both? This has a deadline: T3 must be authored by 14 October.

### C6. Reading evidence: when does a line count as working?

- **Missing.** One rule for pushing a line further, keeping it running, or dropping it, and for when money may follow.
- **Stood in for it.**
  - `DIRECTION_PUSH` 0.80 (v18, R20).
  - V1's bar: at least 20 scored rounds and at least 10 primary losses, B1 0.90.
- **What we know.** Every study so far has been inconclusive under its bar; most results are direction reads with wide intervals.
- **Question.** What would Rob need to see before any money is placed, and on how many independent baskets?

### C7. Execution and costs

- **Missing.** An execution model. Nothing has ever been filled, so slippage and the lock-time price are assumptions.
- **Stood in for it.** Slippage 0.01, rounded up to the tick; the market's own fee schedule; the lock price from the 48-hour history (retrospective) or the recorder's book (forward).
- **Question.** Should we paper-fill against the recorder's books for a period before anything else, to measure real costs?

### C8. Exit

- **Missing.** Every position is held to resolution. The kill-and-rotate monitor of v18 §5.7 is phase 2 and unbuilt.
- **What we know.** T0: once an "if" resolved, prices moved within about an hour, so exiting on news would need to be fast.
- **Question.** Is hold-to-resolution the rule for now, or is a thesis dying (a necessary condition failing) a reason to close its basket?

---

## Part 2. Test design (set in each pre-registration, before data)

These shape a test, not the system. Each is fixed in the test's pre-registration before any data is seen, with its reason stated there:
- `T2_HORIZON_DAYS` 75
- `T2_MIN_OPEN_MARKETS` 3
- `BT_WINDOW_START` 2026-07-01
- `BT_AUDIT_FROM` 2026-01
- `BT_LOCK_STEP` 7 days
- `BT_MIN_POINTS` 10
- `BT_AUDIT_N` 40
- bootstrap draws and seeds

One exception goes to Rob: `BT_AUDIT_GATE` 0.2. It decides whether a backtest month counts as clean of the model having already seen the outcome. That is an integrity rule, not a design choice.

## Part 3. Frozen in finished or running studies (historical; no action)

These apply only to the studies they were registered in, and changing them would invalidate those studies:
- **V1 and V1b:**
  - the bar (at least 20 scored rounds, at least 10 primary losses, B1 0.90, B2 to B4);
  - the tier mapping 0.50, 0.25, 0.10;
  - slippage 0.01;
  - the 48-hour history rule;
  - the horizon cap.
- **V3:** horizon 150 days, reserve 20, at least 3 open markets (addenda A2 and A3), 45 days' grace at scoring.

V3 is still to be scored, from 15 October, under its frozen values.

## Part 4. Do not apply to this system (removed from discussion)

The values of `config/appetite.json` belong to the v16 and v17 equity harness, which is parked. Grouped by what they did:

| Group | Values |
|---|---|
| Effect propagation and support | `FRONTIER_BOUND`, `INDEPENDENCE_DISCOUNT`, `SUPPORT_THRESHOLD`, `CONVERGENCE_THRESHOLD`, `HOP_DISCOUNT`, `DEFAULT_HOP_DISCOUNT`, `HOP_DISCOUNT_BUILDER`, `ATTENUATION_RULE`, `TRANSFORM_SEED_STATUS`, `SYNTH_COMPONENT_DISCOUNT`, `SYNTH_CROSS_NODE_DISCOUNT`, `SYNTH_EPS`, `ANGLE_ORTH` |
| Equity vetoes and appetite | `INERT_STAKE_CEILING`, `RISK_APPETITE`, `BASKET_STAKE_FLOOR`, `POSITION_SHARE_FLOOR`, `TIDE_RATIO_MIN`, `SURVIVING_MAGNITUDE_MIN`, `MATERIALITY_BAND`, `FADEABLE_IMPLIED_MIN`, `TURNOVER_FLOOR_USD`, `POS_SHARE_MIN`, `EDGE_MARGIN`, `TOLERANCE` |
| Tides, stories and bands | `TIDE_REGISTRY_RULE`, `TIDE_COUNT_MIN`, `TIDE_SHOCK`, `ADOPT_MOVE`, `BAND_RULE`, `BAND_WIDTH_MAX`, `BOOTSTRAP_BLOCK`, `BOOTSTRAP_DRAWS`, `UNKNOWN_WIDEN`, `RHO_MIN`, `RHO_EXIT`, `VIS_K`, `JUNCTION_WINDOW`, `JUNCTION_DELTA`, `ACTIVE_WINDOW`, `LOADING_SESSIONS`, `RECOVERY_FRACTION`, `PREMIUM_MIN`, `NARRATIVE_DUE_DAYS` |
| Equity execution | `HEDGE_EPS`, `LIQ_CAP`, `SPREAD_FALLBACK`, `FEE_PER_UNIT`, `BORROW_RATE`, `SLIPPAGE_COEF`, `OPTION_PRICING_MODEL`, `MARK_SCHEDULE`, `EXPIRY_QUANTILE`, `STRESS_QUANTILE`, `STOP_RULE`, `LOSS_BUDGET_PER_ROUND`, `LOSS_CAP_PER_TIDE`, `SWITCH_BUDGET_FRACTION`, `EXCLUDED_LOSS_FRAC`, `ATTRIBUTION` |
| Old K tests and operator records | `X8`, `X10`, `K11_K12_TEST`, `N13`, `X14`, `X15`, `N16`, `K14_SOURCE_MIN`, `CENSUS_CONCENTRATION_PCT`, `OPERATOR_PRIOR_N`, `OPERATOR_MIN_N`, `DUE_AT_MAX_DAYS`, `DERIVATION_BINDINGS_MAX` |
| Open-entity graph | `ENTITY_MATERIALISE_MAX`, `DOCUMENT_MATERIALISE_MAX`, `COMPOSITE_DEPTH_MAX`, `RELATION_UNREVIEWED_MODE`, `BUCKET_MIN_OBS`, `BUCKET_SHRINK_K`, `BEND_TOL`, `BEND_MIN_NODES`, `PROFILE_DEPTH_MAX` |
| Alternative data | `ALT_LATENCY` |

Three ideas from the equity system come back in Part 1:
- the loss budgets, loss caps and stop rule, as C1;
- magnitude and stake = move ÷ band, as C3;
- execution costs, as C7.

**Kept as policies, not discussed:**
- `PERSON_INGEST` stays off: evidence bundles store no personal records.
- `OPERATOR_CUTOFF_DEFAULT_RULE` is replaced for backtests by the BT-A cutoff audit.
