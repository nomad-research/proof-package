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
