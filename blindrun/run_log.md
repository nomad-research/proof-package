# Run log — Nomad blind prediction test

Recorded as the run proceeds, not reconstructed afterwards (§6).

## Clock

| Milestone | Timestamp (UTC) |
|---|---|
| Firewall configured and verified | 2026-08-18 |
| Event received | 2026-08-18 |
| Prediction sealed | **never — §7 fired, see verdict.md** |

## Clarifying questions and refusals

Count of "cannot answer without leaking": **0** so far. One question is
outstanding and is blocking — see Q1 below.

| # | Question asked | Answer | Leak-refusal? |
|---|---|---|---|
| Q1 | **BLOCKING, ANSWERED NO.** What document, dated before 2026-07-30, evidences that the liquidation was *forced* rather than voluntary — and what rule in it removes discretion? A 13F reports holdings; it contains no forcing clause. If such a document exists, I need its URL (I will not search). | Analyst: no such document exists and none can — LPAs, prime brokerage margin agreements and ISDA CSAs are private contracts. A document-class fact, not a search failure. | no |

## Tone-reading self-checks

| # | Note |
|---|---|
| 1 | The analyst's framing — "the forced sale is COMPLETE at the fire date", "the harder and more interesting enumeration task" — could be read as implying the flow was large enough to matter. I am explicitly **not** treating it that way. The liquidity measurement below says the opposite, and I am going with the measurement. |
| 2 | The phrase "second-order names ... exposed to the same forced flow without appearing in the filing at all" describes the thing §3.1 forbids. I am not inferring from its prominence in the brief that it must be answerable. |

## Firewall events

| # | Event |
|---|---|
| 1 | IPv4-only DNS blackhole tried first and **failed** — reuters.com and google.com resolved over IPv6 and remained reachable. Fixed by adding `::` entries before the run began. Recorded because a firewall that was believed to work and did not is the exact failure this protocol exists to catch. |
| 2 | PreToolUse hook written and unit-tested 13/13, but confirmed **not live** mid-session (a WebFetch to a non-allowlisted host succeeded). Primary enforcement is therefore the DNS blackhole plus the logged fetch wrapper. |
| 3 | One `WebSearch` call made **before** the run, deliberately, to establish whether search is structurally blockable. Query: *"boiling point of water at sea level in celsius"* — inert, zero market content. Result: search is **not** blockable by DNS; it executes server-side. This is the only WebSearch call of the run; any further one invalidates it. |

## Documents opened (§6)

All pre-fire; the date ceiling is enforced in `firewall/edgar.py`, not by hand.
Full detail in `firewall/fetch_log.jsonl`.

| Form | Filed | Clause located? |
|---|---|---|
| 13F-HR (period 2026-03-31) | 2026-05-18 | yes — information table parsed, 42 rows, $13.68bn |
| SCHEDULE 13D (Core Scientific) | 2025-08-19 | yes — 5.8% |
| SCHEDULE 13D/A (Core Scientific) | 2025-10-14 | yes — 9.4%, 28,756,478 sh |
| SCHEDULE 13G (Nebius) | 2026-05-27 | yes — 5.63%, 12,410,060 sh |
| SCHEDULE 13G (SharonAI) | 2026-06-29 | yes — 19.99% cap clause quoted |
| Form 3 (SharonAI) | 2026-06-29 | yes — insider status |
| Form 4 (SharonAI) | 2026-07-02 | yes — warrant exercise, acquiring on 06/30 |

**Refused by the wrapper, never opened:** 13F-HR filed 2026-08-14, SCHEDULE 13D/A
filed 2026-08-04, SCHEDULE 13G/A filed 2026-08-14.

## Market data

29 tickers fetched through `firewall/market_data.py`, every series truncated at
2026-07-30 before reaching disk (12 post-fire bars dropped per symbol, logged).

## Wall clock

Event received to blocking question raised: same session, roughly one hour of
operator time. Well inside the "costs a day rather than three weeks" test in §0.

## Firewall events (continued)

| # | Event |
|---|---|
| 4 | The PreToolUse guard became **live** partway through the run and blocked one of my own Bash commands: the commit message embedded a `claude.ai` session URL, and the rule is fail-closed on any non-allowlisted host appearing in a command. A false positive on intent, but the correct response was to route the message through a file rather than widen the allowlist. Recorded because a firewall that only ever blocks other people is not evidence it works. |

## Corrections to the record

| # | Correction |
|---|---|
| 1 | I compared SA's forced flow against A-2's "82.9x ADV" and concluded Q3 also failed. **Wrong.** 82.9 is the multiplier `M/ADV`; realised flow is `M*r/ADV`, which at r=1% is 0.83 days of ADV. A-2's top decile averages 0.80. SA's largest positions are 3.07 and 2.80 — about 3.5x A-2's most extreme decile. The comparison inverts; Q3 is arguably passed. Withdrawn in `edges.md` and `verdict.md`. Only Q1 binds. |
| 2 | The operating procedure's own §2.2 Q3 carries the same conflation and would hand every future screen a magnitude bar ~100x too high. Flagged for correction before the next run. |
