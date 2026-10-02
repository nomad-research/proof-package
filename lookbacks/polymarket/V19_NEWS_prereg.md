# The reader with news (registration, written before any headline is fetched or any session runs)

Rob, 2026-10-02: "Bro of course we can use the news", then "Let's test everything we've done since yesterday ruled things as failed but with news access".

**Why.**
- Every BT-T2 reading so far was cold: no news, knowledge frozen at the model's cutoff. That was a backtest condition: a reader cannot be handed the news as of a past date without leaking what came after. It was never a design rule.
- The ledger's losing divergences (N1 location and timing, N2 longshots) come from not knowing the present.
- **What failed since yesterday, and is re-tested here with news:**
  - E1 at real prices: +1.1¢, direction only (decision 23);
  - A2 at real prices: +4.0¢ on passes 4 and 5, direction only (decision 23);
  - the P5 filter, set aside (decisions 21 and 22).
- **What is not re-run, and why:**
  - **A3** blocks a kind by its own past record. It is a rule on results, not on reading. It is reported on the news readings as a secondary.
  - **R1 (averaging) and R2 (wording)** changed how the reader is asked, not what it knows. They are left for later; this test isolates information.

## 1. The design: the same questions, plus headlines

**Readings N4 and N5:** BT-T2 passes 4 and 5, event for event and session for session (55 sessions, 330 events), with one change.
- **Each question carries the headlines published in the 7 days before its lock.**
- Each session's prompt is first rebuilt from the frozen pass and checked word for word against the original; it stops on any difference.
- The cold readings already frozen for passes 4 and 5 are the comparison. Nothing in them is changed.

**The prompt change** is in the header, and nothing else:
- **Cold:** "Use only what you already know. Do not search for or look up anything: reading this file is the only tool call you may make. There are no prices in this file…"
- **News:** "Use what you already know and the news headlines listed under each question, all published in the 7 days before its as-of date. Do not search for or look up anything else: reading this file is the only tool call you may make. There are no prices from any prediction market in this file…"
- Under each question, before "What to write": "News before E*i*'s as-of date (date seen, source, headline):", one line per headline, or "none found".

**The headlines** (`v19_news.py fetch`; fixed here, before any is fetched):
- **Source:** GDELT's article search (`api.gdeltproject.org/api/v2/doc/doc`, mode ArtList, English sources). It is the one dated news archive reachable from this container. Wikipedia and the Wayback Machine refuse it, and Google News asks for a captcha.
  - GDELT's "seen" date is when it found the article, so nothing seen after the lock can enter.
  - Paced at one request every 5.5 seconds, as GDELT asks.
- **The window:** from 7 days before the lock to the lock.
- **The query, built mechanically from the event title:**
  - the title's capitalised words, minus a fixed list of question words, months, weekdays and generic market words;
  - otherwise its longest non-generic words;
  - up to 3 terms, all required.
  - If fewer than 5 articles come back, the last term is dropped and the search is repeated, down to 1 term.
- **Kept:**
  - English headlines seen before the lock, de-duplicated, newest first, at most 25 per question.
  - Dropped: any headline naming Polymarket, Kalshi, a prediction market, betting, odds or a sportsbook (R6: a market's price never reaches the reader).
  - Dropped: any headline tripping the pipeline's leak check (`v1_packet.leak_flags`).
- **R6, as read here.** A headline may carry a world figure, such as a coin's spot price, a poll or a count. These are world data, not this market's price. If Rob reads R6 as excluding underlying prices too, that is a reason to re-run with them stripped.
- Headlines only. Article pages are not fetched: a page can be updated after the lock, and that would leak.

**Sessions.**
- 55 cold `claude-opus-5-5` subagents with the paged instruction.
- V1's transcript audit with the line-number read check.
- Frozen by hash before any score.
- **A written 0% counts as 1%** (decision 23), and the original answer is kept. No re-authoring for that alone.

## 2. Scoring

Scoring is at real prices: each contract's last trade print within 48 hours before the lock (`V19_REAL_PRICES_prereg.md`, `bt/real_prices/`). Contracts with no print are dropped.

**The declared statistics** (95%, 4,000 resamples by occasion; occasions assigned across passes 4 and 5 together):

| | Statistic | Reading |
|---|---|---|
| **1. E1 with news** | Every NO position in N4 and N5: same-side skill, as `V19_REAL_PRICES_prereg.md` §2 | above zero: edge shown with news; below zero: shown absent; otherwise direction only |
| **2. A2 with news** | A2-armed non-mention NOs in N4 and N5, at real prices, same-side skill | the same |
| **3. What news adds to E1** | Mean E1 skill with news minus mean E1 skill cold (passes 4 and 5's frozen readings at real prices), resampling occasions jointly | above zero: news helps; below zero: news hurts; otherwise direction only |

Three declared statistics, so the chance of at least one false positive is about 14%.

## 3. Secondary (declaring nothing)

- **What news adds to A2:** armed skill with news minus cold, resampled jointly.
- **Location (N1), news against cold on the same questions.** For ladders, touch and date questions: the share of question sides where the news reading's median lands closer to what happened than the cold reading's (`bt_t2.gap`, `outcome_interval`, `session_median`).
- **Log score** against the real price, news against cold.
- **The P5 filter's conditions with news:** conviction (tiers 1 and 2), timing and shape, each with and without.
- **Pick-the-winner against the rest.**
- **A3** on the news readings.
- **The strict window** (locks from 1 June, after most of the model's knowledge ends), apart.
- **Headline coverage:** questions with none found, and the median count.
- **Recognition:** how often each reading says it recognises the outcome.

## 4. What follows

- **If news helps (statistic 3 above zero),** the v19 reader reads news. Its exact shape (one step, or the habit anchor first and then facts) is designed next and tested forward.
- **If E1 or A2 is shown with news,** that edge is back in the design on backtest evidence. It is still confirmed only forward.
- **If news hurts,** the reader stays cold, and the habit-reader design keeps news out of belief.
- **Otherwise,** direction only. The forward sweep decides, and news enters forward only as a registered variant.

## 5. Cost

- About 55 sessions at roughly 70,000 to 100,000 tokens each.
- About 330 to 1,000 GDELT requests, at 5.5 seconds each.

## Addendum A1 (2026-10-02, before any headline was kept)

**The fetch runs on Rob's machine.**
- GDELT allows one request every 5 seconds per address. This container shares its address, and GDELT refused most requests even 20 seconds apart.
- The fetch is moved to `v19_news_fetch.py`: standard library only, and it reads each frame's titles and lock times and nothing else. Rob runs it on his own machine.
- `v19_news.py` imports its query, filter and file functions, so there is one implementation. It checks that the fetch's leak pattern is the pipeline's own.
- Nothing in §1 changes. The first attempt here was stopped before it saved anything.
- Feasibility probes made before this registration returned a few headlines for test queries. None was kept, and no session saw any.

## Addendum A2 (2026-10-02, before any headline was kept)

**Fewer, larger requests.** GDELT throttled Rob's machine too, at one request every 5.5 seconds. GDELT's article search has no batch endpoint; its bulk routes are BigQuery (a paid Google Cloud account) and raw files of tens of GB. So the requests themselves are batched.

**One request per distinct (term, lock date)** instead of one or more per question: 255 requests across both passes, against 330 to 1,000 before.
- The request asks for the question's first term, with up to 250 headlines.
- Questions sharing a term and a lock date share the request (the coin ladders, for instance).
- A question's second term is requested only if its first leaves fewer than 5 headlines.

**Each question's headlines are then picked locally:**
- those containing all its terms, dropping the last term until at least 5 remain, down to the first term;
- at most 25, newest first.
- This is §1's rule applied to a wider fetch, rather than separate narrower searches.

**Query terms keep names whole:**
- runs of capitalised words, in title order, joined across connectors ("Strait of Hormuz", "Bab el-Mandeb Strait", "Augusto Cury", "Palo Alto Networks");
- a name joined by "of" also gives its last word as a later term ("Malta", "Hormuz");
- a title with no name asks for its longest words together ("jobs added").

**Pace:** one request every 12 seconds. A 429 or "slow down" waits 60, 120, 240 seconds and so on.

**Unchanged:**
- the 7-day window, English only, seen before the lock;
- the R6 and leak filters, at most 25 headlines, and the prompt;
- the scoring and the declared statistics.

**The output is `bt/news/<pass>_news.json`.** Any earlier partial file from the first version is not used.

## Addendum A3 (2026-10-02, before any headline was kept)

**The source changes to Google News search.**
- GDELT refused Rob's machine at one request every 12 seconds, backing off 60, 120 and 240 seconds, so the fetch would have taken hours.
- Google News's RSS search takes date bounds (`after:` and `before:`) and needs no account. It is paced at one request every 2.5 seconds, and waits from 30 seconds, doubling, when refused.
- **"Seen" is now the publication time** Google gives. A headline is kept only if it was published before the lock, to the second.
- **Everything else in §1 and addendum A2 is unchanged:**
  - the batching by term and lock date, and local picking;
  - the terms;
  - the 7-day window, English;
  - the R6 and leak filters;
  - at most 25 headlines, and the prompt.
- GDELT stays available (`--gdelt`). A file is never filled from both sources.
