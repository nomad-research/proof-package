# The scale of the edges: an initial reading of capital and timelines (2026-10-01)

For Rob, on request: "explain the scale of the edges we have right now so I have an initial reading of capital requirements and timelines".

**This is a planning estimate built on unconfirmed, post-hoc numbers. It is not investment advice, and the builder is not a licensed financial adviser.**
- Nothing here has been traded or filled.
- Real money still needs Rob's word, D33 and the terms check (v18 §6.7), and the global risk numbers of C1, which are Rob's.

## The edge that has a size: E1, betting NO where the model is surer than the market

| Measure | Value | Source and status |
|---|---|---|
| Profit per share, all NO positions | +4.4¢ at a mean cost of 50¢ | BT-T2 pass 1, post-hoc, 305 positions on 122 events |
| Profit per share, NO where the model is *surer than the market* | **+8.9¢** at a mean cost of 74¢, hit rate 82% | BT-T2 pass 1, post-hoc, 176 positions on 64 events |
| Return per dollar staked, that subset | **about +12.5%** per bet, standard deviation about 57% per bet | same |
| Profit per share, NO bets, a second dataset | +7.4¢ (95% +4.3 to +10.7) | BT-A, post-hoc, 559 positions on 221 events |
| Holding time, lock to scheduled end | **median 4.5 days** (quarter under 2.2, quarter over 7.4) | BT-T2 pass 1 |
| How often | about 600 eligible events a month in scope; about 1.2 "surer NO" positions per event read, so roughly **700 a month** if every eligible event is read | the backtest crawl, July to September |
| **Depth: dollars on offer near the best price, NO books priced 50–95¢** | **median $120 within 1¢, $200 within 2¢**; a quarter above $530 / $740; a tenth above $1,100 / $2,500 | live order books, 70 books, 2026-10-01 |

**Caution on "all NO positions" against the subset.** The registered E1 counts every NO position. Cheap NOs (bought under 50¢) are mostly the "less sure" kind and lose on an equal-stake basis: −10.8% per dollar across all NO positions. The money is in the "surer than market" NOs. Pass 2 reports both, and the registered one decides.

## What that implies for capital (illustration; every assumption labelled)

Assumptions:
- $150 per position, about median depth within 1–2¢, so the bet does not move the price much;
- 700 positions a month;
- a 4.5-day median hold;
- +5% to +12% per dollar staked, a band from the low end of BT-A to the "surer NO" subset.

| Quantity | Estimate |
|---|---|
| Dollars staked per month | about $105,000 (700 × $150), turned over weekly |
| **Working capital tied up at once** | **about $15,000–$30,000** (a week's positions, plus the slower quarter that runs past 7 days) |
| **Expected gross profit per month, if the edge holds at this size** | **about $5,000–$13,000** |
| Spread of a month's result | Independent bets would give a standard deviation near $2,300. Bets inside an event, and across events driven by one shock (a crypto move, a news week), are not independent, so plan on **$3,000–$6,000**, with occasional bad weeks when many NOs fail together |
| Token cost of the reading | about 100 sessions a month to read 600 events (about 9 million subagent tokens) |

**Capacity is the binding limit, not capital.**
- Larger bets per position move the price: the median book has about $200 within 2¢.
- Scaling past roughly $30,000–$50,000 working capital means fewer, deeper markets (the $1M+ events have about $1,300 within 2¢) or accepting worse fills.
- v18 §13 said it already: the viable open set is small, which bounds the business, not the test.

**What would change these numbers.**
- **Fills.** Slippage is assumed at 1¢ and has never been measured (C7). Paper fills against live books are the check.
- **The payoff shape.** A NO book wins small and often and loses big and rarely. A single regime change can turn many NOs at once, so the drawdown stop (C1 number 4) has to allow for clustered losses.
- **The edge itself.** Every figure above is post-hoc. Pass 2 is the first registered test.

## Timeline

| Step | When | What it settles |
|---|---|---|
| BT-T2 pass 2 (registered E1, fresh events in the July–September window) | **Tonight**: frame building now, about 25 sessions, scored on freeze | Whether E1 holds out of sample on backtest. Confirm, kill, or carry |
| T3 (forward, live evidence, claims) | Authored by 14 October; contracts resolve over weeks to months | E2 (linked events) and E1 forward |
| A forward E1 sweep: about 100 open events read a week, NO positions scored as they resolve (median 4.5 days) | First read about 2 weeks after it starts; enough positions to read at 5% in roughly **3–5 weeks** | E1 on events nobody knew the outcome of |
| Paper fills against live books | In parallel with the forward sweep, 2–4 weeks | Real slippage and how much fills (C7) |
| BT-A pass 2 (months by actual resolution) | Any time, about 25 sessions | Whether backtests can lock from April, doubling the window |
| **Earliest point E1 could be "confirmed forward, with execution measured"** | **about mid-November 2026** | The prerequisite for any real-money discussion |

## Update after BT-T2 pass 2 (same day)

- **What replicated.** The money on the model's NO picks: +4.4¢ and +5.2¢ a share in the two passes, and **+8.5¢ and +8.6¢ on NOs priced 50¢ or more** (about +11.7% per dollar). A blind always-NO rule earned about 0 in both. The +5% to +12% per dollar band above stands. Its upper end now rests on two independent samples rather than one subset.
- **What did not.** The registered, stricter test (against NO contracts of the same class and price) gave +2.6¢ with an interval spanning zero. The "surer than market" subset shrank on fresh events.
- **So read the illustration's lower end as the planning case,** about +5% per dollar or $5,000 a month at the illustrated scale, until the forward sweep confirms more.
- **Opportunity count, revised from pass 2:** about 2.5 NO positions per event read, of which about 1.6 are priced 50¢ or more. At 600 events a month that is about 950 of the latter, before depth limits.

## Update after three E1 passes and two E3 passes (night of 2026-10-01)

**Still not investment advice.** Every figure is a backtest priced at the last trade plus 1¢, not at real fills. The forward sweep, which prices at the actual ask, is the check.

### What each edge is worth per dollar (the lean-free part is the planning number)

| Edge | Bets | Per bet (mean cost) | **Skill per dollar** (versus same-price contracts) | Money per dollar (includes any market lean) | Basis |
|---|---|---|---|---|---|
| E1, NO picks priced 50¢ or more | 690 on 231 events | 72¢, wins 83% | **+6.5% (+2.0 to +11.1)** | +14.3% (+9.3 to +18.7) | BT-T2 passes 1–3 pooled, post-hoc pooling |
| E1, all NO picks | 1,093 on 367 events | 54¢ | +7.4% (+2.1 to +12.9) | +13.6% | same |
| E3b, mention markets, both sides | 1,412 on 82 events | 46¢ | **+23.8% (+17.4 to +30.0)** | +19.1% (+12.8 to +25.6) | E3 passes 1–2 pooled, post-hoc |

- **Why skill and money differ.** Money counts what NO bets earned in that window, and in April to June every NO earned something (blind NO +3.3¢). Skill subtracts what same-price contracts earned, so it is the part that should survive any window. Plan on skill.
- **E3b's spread risk is larger.** Mention books are thin (below), so the 1¢ slippage assumed in the backtest is optimistic there. Each extra cent of spread costs about 2% per dollar at a 46¢ mean cost. Planning case: about +15% per dollar after spread, until forward fills say otherwise.

### Capacity: how much each edge can take

| | E1 (short-dated NOs) | E3b (mention markets) |
|---|---|---|
| Eligible events a month | About 500 (W01 snapshot: 242 events in scope ending within 14 days) | About 20–40 (Gamma lists 18 open mention events; about 5–10 a week are in scope from W02) |
| Bets per event | About 1.6–1.9 (NO priced 50¢ or more; passes 2–3) | About 17 (both sides) |
| Dollars on offer near the best price | Median $120 within 1¢, $200 within 2¢ (`depth_sample.py`). Longer-dated T3 books: median $416 and $777 | **Median $50 within 1¢, $60 within 2¢; a quarter above $170–180** (live, 2026-10-01, 250 books priced 30–95¢) |
| Size per bet | $150 | About $60 |
| Staked a month | About 850 bets × $150 ≈ **$127k** | About 30 events × 17 × $60 ≈ **$30k** |
| Expected gross a month | 6.5% → **about $8k** (range $2.5k–14k on the interval) | 15% → **about $4.5k** (range $2k–7k) |
| Holding time | Median 4.5 days | Mostly hours to a week |
| Working capital tied up | About $20–35k | About $5–10k |

**Together: about $12k a month gross at about $25–45k working capital, capacity-bound, before execution costs are measured.** The previous planning case was about $5k a month on E1 alone at +5% per dollar. The rise comes from a firmer E1 skill estimate (three passes), more bets per event, and E3b.

### Risk shape (unchanged, and larger for E1)
- An E1 NO bought at 72¢ makes 28¢ when it wins (83%) and loses 72¢ when it doesn't.
- Losses cluster: one shock can flip many NOs together.
- C1 (global risk) and C2 (position risk) are Rob's numbers and are still blank. Nothing here sizes a real position.

### Timeline to a real-money decision

| Step | Earliest | What it settles |
|---|---|---|
| Sweep W01 resolves | By 15 October | First forward E1 and E3 rows, priced at the real ask |
| Weekly batches W02 onward | Each week (needs a session open, or a scheduled run) | Builds the forward sample |
| **E1 forward, first look** (400 resolved events with a NO pick) | **About mid-November**, at about 80 such events a week plus two weeks to resolve | Confirms or kills E1 at 97.5% |
| E1 forward, second look (800) | About mid-December | The same, with more power |
| E3 and E3b forward, first look (50 mention events) | About early to mid December | Confirms or kills the mention edge |
| **Execution (C7): paper fills against recorded books** | Can start now: the recorder logs books every 15 minutes and the live stream since 2026-10-01 18:24 | Real spread and slippage, above all on mention books |
| T3 (claims, live evidence) | October to December as contracts resolve | E2, and E1 with retrieval |
| **Earliest real-money discussion** | **Late November** (E1 first look plus measured fills) | Needs Rob's C1 numbers and the terms check (v18 §6.7) |
