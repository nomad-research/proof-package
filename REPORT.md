# Nomad — full record of every attempt

One file, everything. Written to be read start to finish without opening
anything else. Six attempts, **none of which produced a positive result** — but
the last one produced the project's first *readable* negative, which is a
different and more useful thing. Plus everything that went wrong along the way,
which is most of the value here.

Last updated 2026-08-18. Branch `claude/nomad-gate-test-spec-f2o5i1`.

## Contents

1. [Scoreboard](#1-scoreboard)
2. [Test A — LETF rebalancing, mega-cap indices](#2-test-a--letf-rebalancing-mega-cap-indices)
3. [Test B — Stale information](#3-test-b--stale-information)
4. [Test A-2 — LETF rebalancing, thin underlyings](#4-test-a-2--letf-rebalancing-thin-underlyings)
5. [Test B-2 — Stale information across the 2012 split](#5-test-b-2--stale-information-across-the-2012-split)
6. [Test B-3 — the rates re-run](#6-test-b-3--the-rates-re-run)
7. [Blind run — Situational Awareness LP](#7-blind-run--situational-awareness-lp)
8. [Everything that went wrong](#8-everything-that-went-wrong)
9. [Amendments made after seeing results](#9-amendments-made-after-seeing-results)
10. [What was built](#10-what-was-built)
11. [Where this leaves the project](#11-where-this-leaves-the-project)

---

## 1. Scoreboard

| # | Test | Question | Verdict |
|---|---|---|---|
| A | LETF rebalancing | Does perfectly enumerated forced flow pay in mega-cap indices? | **FAIL** |
| A-2 | LETF, thin underlyings | Does it pay where counterparty scarcity is high? | **FAIL — Test A closed permanently** |
| B | Stale information | Does "public but unconnected" survive post-2012? | **NOT REPLICATED** |
| B-2 | Extended across the split | Same, on a sample spanning 2012 | **UNREADABLE** (instrument failed) |
| **B-3** | **Rates re-run** | **Same blocks, measured against rates instead of SPY** | **VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES** |
| — | Blind run (SA LP) | Can the framework be operated on one real event? | **NOT OPERABLE** for that event |
| C | Gate 1 | Do enumerated destinations predict returns? | **never started** — gated, gate never opened |

**Cumulative evaluations logged: 204** (A 32, B 45, A-2 19, B-2 66, B-3 42), zero
failures, 181 distinct configurations. Every Deflated Sharpe Ratio is computed
against that cumulative count, read from `config_log.jsonl` rather than asserted.

**What changed with B-3.** Every earlier null was *unreadable* — the instrument
could not detect a reaction even to genuinely new information, so its silence on
stale information meant nothing. B-3 fixed the instrument, confirmed it works
against a positive control, and got a null anyway. That is the first result in
this project that can actually be interpreted, and it fires the pre-registered
stop trigger.

---

## 2. Test A — LETF rebalancing, mega-cap indices

**Verdict: FAIL.** Full detail: `tests_a/results.md`.

### What was tested

Leveraged and inverse ETFs must rebalance daily to hold constant leverage. After
an underlying return `r`, a fund with leverage `L` and assets `A` must trade
`A · L · (L−1) · r`. That is positive in `r` for both long and inverse funds —
both buy on up days — and it executes in the closing auction. It is the most
perfectly enumerable forced flow that exists: every input public, formula
closed-form, execution window known.

Sample: 16,560 underlying-days, 2010-03 to 2026-08, S&P 500 / Nasdaq-100 /
Russell 2000 / Dow, 16 ProShares leveraged and inverse ETFs.

### Result

| Quantity | Value | Hurdle |
|---|---|---|
| Primary β (overnight reversal) | 0.004567 | — |
| t, Newey–West 5 lags | **1.58** | 2.78 |
| t, clustered by date | 1.87 | 2.78 |
| Sign | **opposite to prediction** | negative predicted |
| Years individually significant | **0 of 17** | — |
| Strategy gross | +0.38 bps/day, **t = 0.44** | — |
| Strategy net | −3.91 bps/day, t = −4.53 | — |
| Deflated Sharpe (32 trials) | 4.8e-11 | — |

### Why the data is trustworthy

The rebalance multiplier is computed, not estimated — ProShares publish
full-life daily NAV, shares outstanding and AUM per fund. As a check, each fund's
daily NAV return was regressed on its index return: **all 16 recover their stated
leverage to within 0.004, R² > 0.998.** The AUM file, the leverage assumptions
and the index mapping are mutually consistent.

### The half-life the project wanted does not exist

The spec hoped Test A would replace an invented "12–36 month" decay figure with a
measured one, and called that potentially more valuable than the trade. The
exponential fit does return **6.27 years** — with a bootstrap 95% CI of
**[0.51, 64.91] years**, on 17 yearly coefficients of which **zero** are
individually distinguishable from zero.

It is flagged `NOT INTERPRETABLE` in code and in the report. Fitting decay to a
quantity that was never distinguishable from zero measures the decay of noise,
and a spurious half-life was the most dangerous artefact this test could emit.

---

## 3. Test B — Stale information

**Verdict: NOT REPLICATED.** Full detail: `tests_b/results.md`.

### What was tested

Do markets react to information that is not new? Gilbert, Kogan, Lochstoer &
Ozyildirim (2012), *Investor Inattention and the Market Impact of Summary
Statistics*, found the Leading Economic Index moves prices despite containing
only already-published components.

The LEI is proprietary and unobtainable, so two substitute blocks were run —
because no single free indicator has both properties the test needs.

### Result

| | B1 — Industrial Production | B2 — CFNAI |
|---|---|---|
| Period | 2003-07 to 2026-07, 275 announcements | 2017-10 to 2026-07, 104 |
| Prediction R² | 0.49 | **0.92** |
| Spans the pre/post-2012 split? | **yes** | no |
| **Detects genuine surprise? (validity)** | **no, t = −0.02** | yes, t = 4.51 |
| Predictable component, full sample | t = 0.14 | **t = 3.91** |
| …excluding Mar–Dec 2020 | t = −0.10 | t = 0.98 |
| …dropping 2 most influential obs | t = 0.74 | **t = 0.44** |

### The one significant number is two data points

B2's t = 3.91 collapses to **0.44** when the two most influential observations
are removed. They are April and May 2020, where the COVID collapse in the
pre-released components drove the standardised predictor to **−14 standard
deviations**. Two observations are not an effect.

### B1 is blind, and that is the important part

B1 was the only block spanning 2012, so the only one that could test the decay
claim. It fails the validity check that was registered in advance: it does not
detect a reaction even to genuine industrial-production *surprise*. Its
pre/post-2012 coefficients are unreadable in either direction. **The primary
comparison the test was designed around went unanswered — for a data reason, not
a market reason.**

### What did work

The point-in-time machinery is verified rather than assumed. Every macro input is
a first print pulled from the ALFRED vintage in which the reference month first
appeared. Release dates are measured from the archive rather than taken from a
schedule, and the resulting ordering check confirms the Employment Situation
preceded Industrial Production in **364 of 364 months**, median gap 11 days.

---

## 4. Test A-2 — LETF rebalancing, thin underlyings

**Verdict: FAIL — Test A closed permanently.** Full detail: `tests_a2/results.md`.

### Why this test exists

Test A read its null as a ceiling: *if perfectly enumerated flow pays nothing,
imperfect enumeration cannot pay more.* That collapses two independent variables.
The premium from forced flow comes from **scarcity of the other side**, not from
difficulty of enumeration, and Test A's universe was maximally liquid and
minimally idiosyncratic — the regime McLean & Pontiff (2016) identify as where
alpha does not survive. This ran the identical mechanic where counterparty
scarcity is high.

The correction was right and was accepted without reservation.

### The premise checks out

| Underlying | median M/ADV |
|---|---|
| Semiconductors | **82.9** |
| Technology | 14.7 |
| Internet | 12.8 |
| Home construction | 9.9 |
| Financials | 9.6 |
| *S&P 500 (control)* | *2.0* |
| Industrials | 0.19 |

> **`M/ADV` is a multiplier, not flow.** Realised forced flow is `M · r / ADV` —
> the multiplier times the day's return. At a 1% move, a multiplier of 82.9 is
> **0.83 days of ADV**, and A-2's top decile averaged **0.80 days of ADV** of
> realised flow across its whole range of 0.001–0.80. So A-2 established that
> **~0.8 days of ADV produces no measurable effect**, and says nothing about 5x,
> 10x or 20x ADV — the regime fire sales and forced liquidations occupy. Any
> screen inheriting the multiplier as though it were flow sets a magnitude bar
> roughly 100x too high and rejects events A-2 never tested.


A 400× span. 33,284 underlying-days, 23 underlyings (19 thin + 4 index controls),
2020-07 to 2026-08.

### Result — null on every pre-registered statistic

| Statistic | Result | Hurdle |
|---|---|---|
| H1 — top-decile β | 0.000175, **t = 0.647**, wrong sign | t < −2.78 |
| H2 — decile-rank interaction | β_g = −1.1e-05, **t = −0.013** | \|t\| > 2.78 |
| H2 — Spearman ρ (decile vs β) | −0.067, permutation p = 0.875 | — |
| H2 — Spearman on scaled effect | −0.127, p = 0.734 | — |
| Thin underlyings only | t = −0.15 | — |
| Index controls only | t = 0.83 | — |
| Excluding 2020 | t = −0.10 | — |
| Deciles clearing the hurdle | **0 of 10** | — |
| Strategy gross | 0.142 bps/day, **t = 0.048** | — |
| Strategy net | −76.9 bps/day, t = −25.1 (cost 76.2 bps) | — |

### The stopping condition fired

Pre-registration §8, written before the test ran: *if the top-decile coefficient
is not significant AND there is no monotone gradient, the LETF mechanic is dead
in both regimes and Test A is closed permanently. No third regime will be
proposed.* Both conditions met. **Test A is closed.** The value of writing that
sentence in advance is that it removes the option of proposing a fourth universe.

### Two build notes

**Direxion AUM had to be reconstructed.** They publish no historical NAV or
shares-outstanding feed, and their 3x sector funds *are* the high-imbalance
regime — SOXL alone carries a $145bn rebalance multiplier against semiconductor
ETF ADV of order $1bn. Quarterly SEC N-PORT `netAssets` anchors were interpolated
to daily via each fund's own return path, and the method was **validated against
ProShares funds where true daily AUM is published: 2.7% median absolute error,
10% at p90.**

**Leverage was estimated, not assumed.** Direxion cut several funds from 3x to 2x
during 2020 (ERX, ERY, NUGT, DUST, JNUG, JDST, GUSH, DRIP). A fixed table would
have mis-stated `L·(L−1)` for those fund-days — the entire signal. A rolling
120-day regression of fund return on underlying return, snapped to the nearest
half-integer with an R² floor, handles the changes and doubles as the
fund-to-underlying mapping check.

---

## 5. Test B-2 — Stale information across the 2012 split

**Verdict: UNREADABLE.** Full detail: `tests_b2/results.md`.

### CFNAI could not be extended

The plan was to extend CFNAI back to ~2001 using release dates archived by the
Chicago Fed. Four routes were tried, all failed:

| Attempt | Result |
|---|---|
| ALFRED CFNAI vintages | first vintage **2011-05-23**, nothing earlier |
| Chicago Fed `cfnai/past-releases` page | list rendered client-side, no data endpoint in source (confirmed twice) |
| Chicago Fed `cfnai/archive` | 404 |
| FRED release-date API | requires a key unobtainable in this environment |

Reconstructing release dates from a schedule was forbidden, so it was not done.
**If a working archive URL exists, extending to CFNAI is a small delta on the
committed code.**

### The substitute delivered the sample and then failed

Core PCE price index (`PCEPILFE`), predicted from CPI first prints.

| Guard check | Value |
|---|---|
| Sample | 2005-02-28 to 2026-07-30 |
| Observations | 253 |
| Pre-2012 | **83** |
| Post-2012 | **170** |
| Guard passed | yes |

Then the validity check failed:

| Event window | validity t (surprise) | b1 t (predictable) |
|---|---|---|
| Close-to-close (pre-registered) | **0.32** | 0.49 |
| Overnight, prior close to release open | **1.26** | 0.02 |

Neither clears 2.78. The overnight window was added on noticing the release lands
at **08:30 ET, before the open**, so close-to-close brackets the announcement
plus six and a half hours of unrelated news. It improved validity and still did
not pass.

**This is a gap, not a negative result.** A blind instrument's null says nothing.

### Two honest admissions

- Core PCE was justified as near-deterministic from CPI. Its measured prediction
  R² is **0.28**, against CFNAI's 0.92. A much weaker analogue than claimed
  before running.
- The sample guard fired on its own mis-calibrated tripwire (a fixed 2004 start
  date standing in for "enough pre-2012 data") and was **relaxed after firing** —
  the pattern that should always attract suspicion. The arithmetic showing the
  start date was warm-up rather than truncation is in the amendment.

---

## 6. Test B-3 — the rates re-run

**Verdict: VALIDITY PASSES + NO ROBUST EFFECT — STOP TRIGGER FIRES.**
Full detail: `tests_b3/results.md`.

### Why this ran

All four earlier macro blocks used SPY, and three of four failed the validity
check. An equity index's daily return is dominated by everything other than a
macro release; the front end of the Treasury curve reprices sharply on inflation
and activity data. Gilbert et al. used Treasury futures alongside the S&P for
exactly this reason, and the original spec never questioned the SPY choice.

**Only the outcome variable changed.** Vintage assembly, first prints,
archive-measured release dates, ordering verification, the expanding-window
prediction and the hurdle are byte-identical to the runs that produced the SPY
results. Three outcomes: `DGS2` yield change (primary), `TLT` and `IEF` returns.
The overnight window was registered **in advance** this time, removing the fence
that was needed when it was added mid-run.

### Step 1 — validity, reported before any other coefficient

| Block | Best t (surprise) across outcomes | Pass? |
|---|---|---|
| B1 — Industrial Production | 2.22 | **no** |
| **B2 — CFNAI** (positive control) | **4.68** | **yes** — 3 of 5 outcomes |
| B-2 — core PCE | 0.96, and **wrong sign** on 3 of 5 | **no** |

**3 of 15** block-outcome combinations pass.

**The positive control did its job.** CFNAI passed validity on SPY at 4.51 and
passes on rates at 4.68. The rates instrument demonstrably detects macro news, so
a null from it is readable rather than blind — which is the entire point of the
exercise.

A coherence check that SPY could never have provided also holds for all three
blocks: yields and bond prices move in **opposite** directions on the same
surprise, confirming the instrument measures what it is meant to.

### Step 2 — the predictable component, on the readable block

| Combination | raw t | after dropping 1 | 2 | 3 | 5 |
|---|---|---|---|---|---|
| CFNAI / TLT close-to-close | **−2.98** | −1.00 | 0.92 | −0.58 | −0.44 |
| CFNAI / IEF close-to-close | **−3.55** | −1.39 | −1.36 | −4.67 | −4.68 |
| CFNAI / IEF overnight | −1.83 | −3.89 | −0.37 | 0.32 | 0.36 |

Two of three clear the hurdle in raw form. **This is not a flat zero and is not
described as one.** But none survives the pre-registered influence diagnostic:
dropping a **single** observation takes the strongest from −2.98 to −1.00, and
the three most influential releases are the same COVID dates that drove the SPY
result — March, April and May 2020.

The second row is the more instructive one. It swings −3.55 → −1.39 → −1.36 →
−4.67 → −4.68 depending on which points are removed. A coefficient with a real
effect behind it does not behave like that; a small sample steered by its
extremes does.

### The prize was not won

**B1 still fails validity**, on all five outcomes, best t = 2.22. The
pre/post-2012 split — the primary output the whole B-line was built to deliver —
**remains unanswered**.

But the *reason* changed, and that is worth recording. Previously B1's failure
was ambiguous: a blind instrument and a silent announcement look identical from
the outside. Now the instrument is demonstrably not blind, because the control
clears the hurdle on the same data. So the failure is attributable to the
announcement: **industrial production surprises do not measurably move the front
end.** The split is now unanswerable *demonstrably* rather than presumptively.

Core PCE's failure is also better diagnosed: it fails validity with the **wrong
sign** on three of five outcomes, which is further evidence it was a weak
analogue all along rather than a good one poorly measured.

### The stop trigger

Pre-registered before running: *validity passes + null → the stop trigger fires;
state it plainly, do not soften it, do not propose a fourth instrument.*

Validity passes. No robust effect. **The trigger fires.** On the one indicator a
working instrument can read, there is no robust market response to the
already-public component of a composite announcement.

This is **the first clean stop in the project.** Every previous null was
unreadable. This one is not.

---

## 7. Blind run — Situational Awareness LP

**Verdict: NOT OPERABLE for this event.** Full detail: `blindrun/verdict.md`.

This was the only test of the *framework* rather than of an assumption underneath
it. Operator knowledge cutoff end of May 2026; event fire date 2026-07-30, so the
outcome was structurally unknown.

### The firewall

Structural, verified: 44 search / aggregator / financial-media domains blackholed
in `/etc/hosts` on both A and AAAA records; a market-data wrapper that truncates
every series to the fire date before anything reaches disk; an EDGAR wrapper
enforcing a filing-date ceiling in code.

Procedural, declared as such: `WebSearch` is not blockable by DNS (it runs
server-side, established with an inert test query), so it was a commitment made
auditable by the transcript. **WebSearch calls during the run: 0.**

Guard decisions logged: **23 — 13 allowed, 10 denied.** The denials include
WebSearch, a search-shaped MCP tool, three media domains, one unlisted host, two
fail-closed on unverifiable network commands, one fail-closed on malformed input,
and **one of my own commit commands**, when a message embedded a non-allowlisted
URL. That last is the only unplanned denial and the only real evidence the
firewall governs the operator rather than just the test cases.

### The mapping

Seven pre-fire filings opened. Three refused as post-fire, including the **13F-HR
filed 2026-08-14** for period 2026-06-30 — the single document that would have
revealed the answer.

Established: $13.68bn across 42 line items at 2026-03-31, top-10 = 72.7%,
concentrated in semis / AI datacentre / miner-to-AI names. Two large stakes exist
only in ownership filings and are invisible in the 13F — **Nebius 5.63%** and
**SharonAI ~19.99% capped**. A Form 4 filed 2026-07-02 shows the fund still
*exercising warrants to acquire* on 06/30, so the forcing happened in July.

### Every edge quarantined

| Edge | Failed field | Why |
|---|---|---|
| 1 — the forcing itself | `trigger_document`, `binding_rule`, `rule_document`, `window_basis` | A 13F is a holdings disclosure. It contains no clause removing discretion from anyone. |
| 2 — SMH in-kind redemption | `binding_rule` at the third link | An authorised participant is not *forced* to sell what it receives. |
| 3 — Rule 144(e) on SharonAI | constrains the seller, creates no destination set | The only retrievable rule found. Bears on timing, not destination. |

**3 attempted, 0 verified, 100% quarantined.** Two §7 stop conditions met.

### Primary finding — a framework constraint, not an event failure

**The verification standard structurally excludes private-contract forcing.**
Margin agreements, LPAs, ISDA CSAs and bilateral covenants are where the largest
and most price-insensitive forced flows live, and none is public. Forcing that
lives in a private contract is unmappable by construction, however certain it is.

What survives is the publicly-documented subset — which is also the subset most
likely to be pre-enumerated for everyone, the defect Q7 exists to exclude:

```
Q7 excludes: destinations published in advance  (index recon, scheduled flows)
Q8 excludes: forcing documented only privately  (margin, LPA, CSA, covenants)
                            |
              what remains is narrower than assumed
```

---

## 8. Everything that went wrong

The most useful section. Every error, bug and dead end, including mine.

### Errors in my own analysis

| # | What | Consequence | Caught by |
|---|---|---|---|
| 1 | **Magnitude conflation.** Compared SA's forced flow to A-2's "82.9× ADV". 82.9 is the *multiplier* `M/ADV`; realised flow is `M·r/ADV` — at r=1%, 0.83 days of ADV. A-2's top decile averages **0.80 days**. SA's largest positions are **3.07 and 2.80** — about 3.5× A-2's most extreme decile. | The comparison **inverts**. Q3 is arguably passed, not failed. My secondary argument for stopping was withdrawn; only Q1 binds. Verdict unchanged, but resting on one leg rather than two. | **The analyst.** I had it wrong and was corrected. |
| 2 | **The A-2 β column reads backwards.** β is a slope whose regressor spans 1,200× across deciles, so it shrinks mechanically as imbalance rises — decile 1 shows the largest raw β. | A reader scanning that column would draw the opposite conclusion from the correct one. Fixed by adding an economically-scaled effect column and a warning. | Me, before publishing |
| 3 | **Corwin–Schultz gave 47bp round-trip on SPY/QQQ/IWM/DIA**, wrong by two orders of magnitude. Its identifying assumption fails for instruments trading millions of times a session. | Test A's net figures were badly overstated. Replaced with a tick-based estimator for liquid names; CS retained for illiquid ones. | Me — the number was implausible on its face |
| 4 | **The spec's own Q3 carries the same conflation as #1**: *"82.9× ADV … produced no measurable effect."* | Left uncorrected, every future screen inherits a magnitude bar **about 100× too high** and rejects events A-2 never tested. Should read *~0.8 days of ADV*. | Flagged for correction |

### Bugs

| # | What | Consequence |
|---|---|---|
| 5 | **Price cache keyed on symbol alone** — returned a file built for a later start date regardless of the start requested. | Silently truncated Test B's sample by **five years** and suppressed the pre/post-2012 split entirely, because the split needed at least 40 observations either side and there were 36. A cache keyed on symbol alone is a correctness bug, not a performance detail. |
| 6 | **IPv4-only DNS blackhole** — the first firewall attempt blocked only A records. | reuters.com and google.com resolved over IPv6 and stayed **fully reachable**. A firewall believed to work but not working is exactly the failure the protocol exists to catch. Fixed with `::` entries before the run began. |
| 7 | **PreToolUse hook not live mid-session** — project settings are read at session start. | Verified empirically (a fetch to a non-allowlisted host succeeded) rather than assumed. Primary enforcement fell to DNS plus wrappers. The hook did go live later. |
| 8 | **B-2 sample guard fired on its own mis-calibrated tripwire** — a fixed 2004 start date proxying for "enough pre-2012 data". | Relaxed **after firing**. The substantive condition it proxied for passes by a factor of two (83 against 40 required), and the arithmetic ruling out truncation is recorded. |
| 9 | **The DNS blackhole did not survive the session.** Checked at the start of the rates re-run: `/etc/hosts` was back to 4 lines with every blackhole entry gone — the container regenerates it. | The sealed blind run is unaffected: the blackhole was verified live *during* that run, by resolution checks and an actually-blocked fetch, and the guard log records the denials as they happened. But the control is structural **only within a session**, and spec v2 §7.1 presents it as a proven configuration without that qualifier. A future run must re-apply and re-verify at the start rather than assume persistence. Recorded rather than quietly re-applied — a control believed to be in force when it is not is the exact failure the protocol exists to catch, and that has now happened **twice**: first the IPv6 leak, now non-persistence. |
| 10 | **The guard blocked me four times, all false positives.** (a) A commit message embedding a session URL. (b) Writing this very report, whose prose names a network tool. (c) A commit message using an ordinary English word that also happens to be the name of a text-mode browser. (d) The follow-up commit describing (b) and (c), which therefore contained both trigger words. The rule is fail-closed on any network-tool mention with no extractable URL. | Every time the fix was to route around it — a message file, then a non-network write tool, then a reword — **never** to widen the allowlist. This is the real cost of fail-closed and it is worth paying: the same rule that trips on ordinary prose is the rule that would stop an actual unchecked fetch. It is most annoying exactly when it is working. Note (d) especially: writing *about* the firewall's trigger words is enough to trip it, which is a genuine ergonomic flaw rather than a virtue. |

### Data dead ends

| # | Source | Outcome |
|---|---|---|
| 11 | Direxion historical NAV / shares outstanding | 403 to automated access; only a current-day holdings snapshot. Worked around via SEC N-PORT quarterly anchors. |
| 12 | Chicago Fed CFNAI release archive | Client-side rendered, no data endpoint; archive path 404s. Killed the CFNAI extension outright. |
| 13 | Stooq | JavaScript proof-of-work challenge |
| 14 | `yfinance` package | SSL failures through the outbound proxy; replaced with direct requests |
| 15 | ALFRED multi-vintage request | Silently returns only the first vintage — needed **about 1,100 individual requests** instead |
| 16 | Wayback Machine | Blocked by egress policy |
| 17 | Free intraday history | About 60 days at 30m, 730 days at 1h. Killed Test A's 2010–present impact leg; only the overnight leg survived. |
| 18 | N-PORT for ERY, NUGT, YANG, NAIL, TMV | Zero observations returned — excluded from A-2 |

### Things that worked and are worth keeping

- **Structural beats procedural.** The EDGAR date ceiling refused the Q2 13F by
  construction. A human promising to check dates has to be right every time.
- **Truncate before writing to disk.** A domain allowlist cannot enforce a date
  ceiling; the wrapper can. 12 post-fire bars dropped per symbol, logged.
- **Commit the reasoning before the prediction exists.** The quarantine standard
  is timestamped independently of any map, so it cannot have been
  reverse-engineered. **This should be the default ordering for every run.**
- **Check resolution, do not trust the write** — how the IPv6 leak was found.
- **The guard blocked its own operator.** A firewall that only ever blocks other
  people is not evidence it works.

---

## 9. Amendments made after seeing results

Eight across the project. Each dated and disclosed in the relevant
`preregistration.md`, never edited in silently.

| # | Test | Change | Direction |
|---|---|---|---|
| 1 | A | Intraday window moved to 15:30→16:00 (toward the original spec) | before results |
| 2 | A | Threshold warm-up fixed at 252 days | before results |
| 3 | A | Cost model: tick-based spread for liquid names | **after** — can only *lower* costs, cannot rescue a result |
| 4 | B | Citation correction (paper title) | after — factual only |
| 5 | B | Influence diagnostic (Cook's distance) | **after** — can only *remove* significance |
| 6 | A-2 | Economically-scaled effect column | **after** — *could* have strengthened a finding, so fenced |
| 7 | B-2 | Sample guard tripwire replaced with an arithmetic check | after — no result threshold touched |
| 8 | B-2 | Dual event window, selected on the *validity* statistic | **after** — could have manufactured readability, so fenced |

**B-3 added none.** The overnight window and the validity-first ordering were
both registered *in advance* this time, precisely because they had to be fenced
when introduced mid-run. That is the amendment rule working: the fix for a
post-hoc amendment is to pre-register it next time, not to keep fencing it.

The two that could have strengthened a finding (6, 8) are fenced explicitly:
neither forms part of a pass condition, both are applied to all rows rather than
selectively, and **neither changed a verdict**.

Separately, the blind run added two screen criteria post-hoc — **Q7**
(destinations must not be pre-published) and **Q8** (the forcing document must be
publicly retrievable). Both exclude-only, so neither can manufacture a positive.
**Two post-hoc amendments in a single run is on the record as a warning: a third
would mean the screen is being fitted to the candidates rather than derived.**

---

## 10. What was built

Shared infrastructure, unit tested (**25/25 passing**), used across all tests:

| Component | Purpose |
|---|---|
| `config_logger.py` | Append-only evaluation log — the multiple-testing denominator. Counts failed and abandoned runs, so the denominator cannot be understated. |
| `deflated_sharpe.py` | Bailey & López de Prado DSR and PSR, plus CSCV probability of backtest overfitting. Trial count read from the log, not asserted. |
| `pit_corpus.py` | Bitemporal document store — `valid_from` / `known_from` / `retrieved_at`, as-of queries, verbatim clause location (refuses to store an unlocatable clause), recognition-lag tracking. |
| `cost_model.py` | Full-spread round trip plus two-sided square-root impact. Corwin–Schultz for illiquid names, tick-based for liquid ones. |
| `inference_family.py` | Link tagging, quarantine accounting, effective breadth via `N_eff = N²/(1'C1)`. |

Blind-run infrastructure: `firewall/guard.py` (fail-closed PreToolUse hook,
13/13 unit cases), `firewall/fetch.py`, `firewall/market_data.py`,
`firewall/edgar.py`.

Test C infrastructure exists and is tested but was **never used** — the gate
never opened.

---

## 11. Where this leaves the project

### Settled

- **Test A is closed permanently**, in both the liquid and illiquid regimes, by
  its own pre-registered stopping rule.
- **The stale-information line is closed.** B-3 fired the pre-registered stop
  trigger: a working instrument, verified against a positive control, returns no
  robust response to the already-public component of a composite announcement.
  Per the pre-registration, **no fourth instrument will be proposed.**
- **Test C never started.** The gate required a positive result upstream. It
  never came.

### The one thing B-3 changed, and it matters

Every earlier null in this project was **unreadable**. Three of four SPY blocks
could not detect a reaction even to genuinely new information, and a blind
instrument's silence carries no information. The honest position after five
attempts was *"we do not know"* — not *"there is nothing there."*

B-3 closes that gap. The rates instrument sees macro news (control at t = 4.68,
correct sign, coherent yield/price relationship) and still finds nothing in the
predictable component. **That is a real negative result, not an absence of
evidence.** It is the only interpretable finding the project has produced about
the mechanism underneath the enumeration thesis.

### What remains genuinely open

- **The pre/post-2012 decay question is still unanswered.** B1 was the only block
  spanning 2012 and it fails validity even on rates. The difference now is that
  the failure is *diagnosed*: industrial production surprises do not move the
  front end, so the silence is the announcement's, not the instrument's.
- **No decay half-life was ever measured.** The invented "12–36 month" clock is
  unsupported, not refuted — and demonstrably untested.
- **The LEI test itself was never run.** Gilbert et al.'s actual indicator is
  proprietary. Everything here used substitutes.
- **Nothing here is statistical evidence about enumeration.** Five of six tests
  measured assumptions *underneath* the framework. The one that measured the
  framework directly stalled on document class, not on prediction quality.

### The framework constraint that outlives all of it

From the blind run, and independent of every result above: **the verification
standard structurally excludes private-contract forcing.** Margin agreements,
LPAs, ISDA CSAs and bilateral covenants are where the largest and most
price-insensitive forced flows live, and none is public. Combined with Q7's
exclusion of pre-published destinations, the addressable universe is materially
smaller than the thesis assumed.

That conclusion does not depend on any prediction being right or wrong, and it is
the finding most worth carrying forward.

### If anything continues

Not a recommendation to continue — the stop conditions fired and the honest
reading is that they should be respected. But if work does continue, the order
that follows from what was actually learned:

1. **Settle the Q8 relaxation cold**, against no candidate, as spec v2 §3.1
   requires. The blind run showed Q7 and Q8 together may leave the universe
   nearly empty. That question is decidable on paper and costs nothing.
2. **Buy LEI vintage data** and run the real Gilbert et al. replication. B-3
   established the instrument; it did not establish the indicator. This is the
   only remaining way to test the actual published claim rather than a substitute.
3. **Intraday index data to 2010** for Test A's untested impact leg — the one leg
   the LETF work never reached.

What should *not* happen: a fourth macro instrument, a third LETF regime, or
Test C on the strength of anything above.
