# Nomad, new system: the starting point

*2026-10-01. Agreed as the starting point for designing a new system from the edges found, before any build. Rob asked for the choices to be made ("You choose and we'll take that as our new starting point"); every choice below is the builder's under that instruction and stays open to Rob's change. Evidence comes from branch `claude/v18-run`, head `e9ce901` (`docs/EDGE_LEDGER.md`, the BT-T2 and E3 results, and a new check run for this file, §6). All money figures are backtests priced at the last trade plus 1¢. Nothing has been filled, and nothing places an order.*

*Kept as Rob gave it. What was settled about it, and what is open, is in `docs/DECISIONS_2026-10.md` decisions 12 and 13. §6 is reproduced by `lookbacks/polymarket/v19_a2.py backtest`. **Amended by decision 13:** only A2 binds; A3, A4 and A6 are labels; A1, A5 and the group caps bind when real money starts; D2 is recorded on every position; D1 is narrowed and label-only; principle 2 carries a caveat.*

---

## 1. The problem, in one line

**Find the "maybes" the market overprices and the reader can rule out, take only the cleanest of them, and survive the rare day when many of them come true at once.**

Everything else in the old system (graph-first theses, hedging, narrative coverage, live news in the core) is out of the core. Each may come back only by beating this in a shadow book (§5).

## 2. The edges

### E1. Ruling out: the maybe premium (the core)

- **What it is.** On short-dated, attention-driven questions, the market gives specific vivid outcomes a real chance: a count clears a level, a bracket is hit, a deadline is met, a word is said. A cold reader that prices from how such things usually go is confidently right that many of them won't happen.
- **Correction to earlier wording.** The best positions are not bets *against* the market's favourite. They are NOs the market already leans towards, but not far enough:
  - the YES side is priced as a live maybe (roughly 20% to 50%);
  - the reader puts it at least 20 points lower.

  "NO priced 50¢ or more" means the market already gives YES under half.
- **Why the world produces it.** Salience. The crowd prices what is in the news; most instances of anything are ordinary.
- **Why we catch it.** The reader:
  - never sees the price;
  - has no news after its training cutoff, so it falls back on base rates;
  - writes a number for every outcome;
  - is accurate when it says "unlikely" (under 5% happened 1%, the market said 4%);
  - is overconfident when it says "likely".

  Only its confident "won't happen"s are traded.
- **Its risk.** Small wins often, rare large losses, and losses that cluster when one shock flips many NOs.

### E3. Mention markets: habit beats headlines (core, both sides)

- **What it is.** The question is whether a person says a word in a window. The crowd prices words by topicality; the reader prices by the speaker's habitual vocabulary, the format and the exact wording of the rules.
- **Both sides win.** This is the one market type where the reader is as well calibrated as the crowd, and it beats same-price contracts on both sides: +11¢ in each of two independent passes, and +8.7¢ without the five biggest events.
- **The registered NO statistic:**
  - +7.3¢ (edge shown) in the first pass;
  - +5.1¢ (direction only) in the second.
- **Its limits.**
  - Thin books: about $50 within 1¢ of the best price.
  - About 5 to 10 in-scope events a week.
  - A few big Trump events carry a lot of it.

### E2. Linked events (not in the core yet)

- **What it is.** When a session says "if A then B" and A happens, B beats contracts of the same kind and price by +30 points (+13 to +48, 9 claims). The links are real.
  - The earlier "71% against 48%" partly reflected how the pool was chosen (`T0_BASE_RATE.md`).
- **Why it is not in the core.** It earns nothing at the lock (+4 points, spanning zero). After A resolves, the market reprices B within about an hour, and in half the claims B had already resolved.
- **Status.** Held as information, until it can be bet with a view on A or with speed.

### What we learned does not work (kept so we don't rebuild it)

- Where a level ends up, and when something happens: the reader's sense of the present is stale.
- Cheap long shots: they come from ignorance, not insight.
- The reader's probabilities as a whole: the market is better calibrated.
- The sessions' "what will happen" picks.
- Hedging as a source of edge.
- A ladder's listed rungs leak where the market thinks the level is.

## 3. Principles carried forward

From v15 (theory v2, system doc v4), salvaged because they fit these edges better than they ever fitted equities:

1. **Base rates for procedural actors only.** v15 allowed base rates for scheduled processes and habitual behaviour, and forbade them for cascades. Both edges live there:
   - deadlines slip;
   - counts stay ordinary;
   - speakers repeat themselves.

   One-off cascades, such as whether a war escalates or a regime falls, are out of scope even when the reader is confident.
2. **Arm strictly, disarm freely.** "A false disarm costs a missed trade; a false arm costs money."
3. **Every position carries its own falsifier and dies alone.** No netting across positions.
4. **The reader's own record is a risk term,** computed from clean resolutions per market type, never self-reported.
5. **Risk terms are a vector, never multiplied.** A term that cannot be computed is "unassessable", not a pass.
6. **Permissible risk has a shape.** We are paid for base rate against salience. We are not paid for:
   - the tide (shared shocks);
   - timing;
   - thin books.
7. **Thresholds are appetite.** They are stated once and never loosened because nothing passed. Changing what counts as valid is learning; changing a threshold is fitting.
8. **A filter never violated is a filter never tested.** v15 armed nothing in 15 rounds because its AND over eight untested rules made arming near-impossible. So every rule here earns its place in a shadow book (§5).

From this week:

9. **Price never forms the reader's view** (R6). It enters only to decide whether, and how much, to trade.
10. **Read results for direction first;** strict bars only for money.
11. **Calibrate within one pipeline only:**
    - never carry a correction from one way of asking to another;
    - trust the reader's low numbers, shrink its high ones.

## 4. The stack

| Layer | What it does | Rule |
|---|---|---|
| 1. Market map | Every open market: structure, end dates, rules text, order-book depth | No beliefs |
| 2. Selector | Short-dated (resolving within about 14 days), procedural, attention-driven, specific-outcome markets: counts, brackets, deadlines, mentions | Cascades out (§3.1) |
| 3. Cold reader | Price-blind and news-blind on purpose. Writes a number for every outcome from base rates, the rules' exact wording, and the speaker's or process's habits | Cold sessions, transcript-audited |
| 4. Second derivation | A simple statistical base rate per market type, plus later two independent sessions | Arms only if it agrees (§5) |
| 5. Arming | Turns a disagreement into a candidate position only when every arming rule holds | §5 |
| 6. Disarm check | A cheap news check that may only *stop* a position, never start one | §5 |
| 7. Risk | The per-position vector, loss caps per shared driver, a drawdown stop | §5; the numbers are Rob's |
| 8. Execution | Priced at the ask, sized to the depth on offer; paper fills first | |
| 9. Ledger | Shadow book and armed book, weekly passes, a post-mortem on every miss, each edge with its own kill condition | §5 |

## 5. The risk layer

### Arming: all must hold

| # | Rule | Status |
|---|---|---|
| A1 | The question is procedural, not a cascade | Starting rule. Untested until events are labelled (§8) |
| A2 | **The reader's NO beats the price by at least 20 points, on a contract whose YES is priced as a live maybe** (NO priced 50¢ or more) | **Tested, §6.** This is the arming rule |
| A3 | The reader's record in this market type is positive | A walk-forward version, gating by market type, removed nothing in the backtests. So the rule exists but binds nothing yet |
| A4 | A second, independent derivation agrees | Starting rule. Untested until the statistical baseline exists |
| A5 | The book has at least the position's size within 2¢ of the ask | Sampled once (2026-10-01: median $200 within 2¢). To be recorded at every forward lock |
| A6 | The edge after all-in cost clears a margin | Implied by A2 at today's costs. Becomes binding once fills are measured |

On mention markets, A2's side condition is relaxed to "either side", because E3 earns on both.

### Disarming: any one fires

- **D1. News.** A dated, sourced fact since the reader's knowledge bears directly on the outcome (an official date set, a topic announced as the subject).
  - The news check has disarm rights only. That keeps the reader cold, since arming comes from base rates, while cutting the case that hurts a NO book most: a maybe priced high because something really did change.
- **D2. Falsifier.** Each position names the fact that would kill it. If that fact appears, close.
- **D3. Staleness.** A fact the position rests on has outlived its usual life without being re-checked.

### Exit

- **Armed book:** held to resolution until fills are measured.
- **Shadow book:** exits when the market's price reaches the reader's view, since at that point the edge is gone and only the tail remains. It is promoted to the armed book once real fills show it pays after the spread.

### Shape and budgets

- **Group positions by shared driver.** Examples: all brackets on one asset in one week; all words in one speech; all deadlines of one agency.
- **Cap each group's worst case:** the sum of its NO costs if every one flips. This is v15's per-tide loss cap and global number 3.
- **Also set:** the most deployed at once, the most on one position, and a drawdown stop that allows for clustered losses.
- **These four numbers are Rob's and are blank.** Nothing goes beyond paper until they exist.

### Shadow book and promotion (v15 §4.6)

- **What is recorded.** Every candidate position the reader produces is recorded and scored on paper: the shadow book. The armed book is the strict subset.
- **When a rule stays.** A rule stays only while the positions it lets through beat the ones it blocks.
- **When an edge goes live.** It is promoted to real money only when its measured edge × capacity clears costs plus a reserve, and Rob has set the four numbers.

## 6. The first check of the strict rules (backtests, run for this file)

**Data.** The three BT-T2 passes:
- 1,093 NO positions on 367 events;
- July to September locks, plus April to June;
- the cold, price-blind reader.

**Measure.** "Skill" is a position's hit minus cost, minus the same for NO contracts of the same type and price on other events. It is resampled by event, and the interval is 95%.

| | Positions (events) | Skill | Money (hit − cost) |
|---|---|---|---|
| All NO positions | 1,093 (367) | +4.0¢ (+1.2 to +7.0) | +7.3¢ |
| **Armed by A2** (NO priced 50¢ or more, reader at least 20 points surer) | **245 (107)** | **+13.5¢ (+8.0 to +18.5)** | **+23.1¢** (+17.4 to +28.0); hit 85% at a mean cost of 62¢ |
| Not armed | 848 (355) | +1.2¢ (−2.0 to +4.6) | +2.7¢ |

The armed rule's edge holds up under every cut:

| Check | Armed skill |
|---|---|
| **Each pass alone** | +13.9¢ (+0.1 to +25.6); +11.2¢ (−0.4 to +19.5); +15.1¢ (+7.5 to +21.2) |
| **Rises with the disagreement** (reader surer by at least…) | 10 points +7.1¢ · 15 points +8.2¢ · 20 points +13.5¢ · 25 points +16.0¢ · 30 points +22.3¢ · 40 points +29.0¢ (47 positions) |
| **Without the top 5 events** | +10.3¢ (+4.4 to +15.7) |
| **Without the top 10 events** | +7.0¢ (+1.1 to +12.5) |
| **Without mention markets** | +12.3¢ (+6.7 to +17.5) |
| **July to September locks only** (the cleanest window) | +12.3¢ (+3.8 to +19.4) |

**Reading.**
- The strict rule does what v15 said strictness should do: it concentrates the edge.
- What it drops is close to zero.
- It is consistent across three independent samples, rises steadily with the size of the disagreement, and survives losing its biggest events.

**Caveats.**
- The combination was chosen after looking. Its two parts were each reported earlier (the 50¢ band in pass 1, the disagreement bands in pass 2), but together they are post-hoc.
- The money assumes fills at the last trade plus 1¢. The armed positions cost 62¢ on average, and the books near the best price hold about $120 to $200.
- So this is a hypothesis to confirm forward, not a result.

## 7. What is out of the core

- Graph-first thesis construction.
- Hedging.
- Narrative coverage sets.
- Location and timing calls.
- Cheap long shots.
- Live news as an arming input.
- The equity harness.

They stay in the repository and may return only by beating the armed book in the shadow book.

## 8. Open items

- **Rob's four numbers (global risk):** the most deployed at once, the most on one position, the most on one shared-driver group, and the drawdown stop.
- **R6 and an underlying's current price.** Bracket markets on prices need the underlying's current level as world data. Does R6 allow it?
- **Procedural against cascade.**
  - A written rule.
  - A labelling of the 367 backtest events.
  - A test of A1 in the shadow book.
- **The statistical baseline per market type,** for A4 (for example, past volatility for price brackets, past frequency for counts and words).
- **Fills.** Paper fills against the recorder's books, for the ask, the spread on exit, and how much fills. This prices A6 and the exit rule.
- **E2's way to money:** a view on A, or speed.

## 9. Next steps (design first; nothing is built until the design is agreed)

1. **Register A2 as a forward statistic now, on sweep W01 onwards, before any W01 outcome is read.** W01's answers are frozen and resolve by about 15 October, so this is the fastest clean confirmation available.
2. **Label the backtest events** procedural or cascade with a written rule, and test A1 in the shadow book on existing data.
3. **Build the statistical baseline** for the two largest market types and test A4 on existing data.
4. **Start paper fills** against the recorder's books.
5. **Rob sets the four numbers** before anything leaves paper.
