# Blind run 2 — screening log

**D = 2026-06-01.** Trigger window to 2026-07-15, leaving five-plus weeks for a
transmission window to close before 2026-08-21. Operator self-screened: the
analyst was not involved in selection, which closes the selection-contamination
channel entirely rather than merely disclosing it.

Methodology: `methodology/pre_event_review.md`, decided cold before any candidate
was in view.

## Firewall — re-applied and re-verified

The blackhole does **not** persist across sessions, which was recorded as a
finding after the last run. It was therefore re-applied and **verified by
resolution, not by trusting the write**: 44 media, search and aggregator domains
resolve to `0.0.0.0` / `::` on both record types; `sec.gov`, `efts.sec.gov`,
`data.sec.gov` and `fred.stlouisfed.org` resolve normally.

## Attempt 1 — full-text search on forcing language. **Wrong, and abandoned.**

Seven queries were declared in `screen.py` before any result was seen, targeting
documents capable of satisfying Q8a. They returned **238 candidates**:

| Forcing class | Hits |
|---|---|
| mandatory redemption | 77 |
| notice of acceleration | 76 |
| mandatory conversion | 29 |
| mandatory exchange | 21 |
| subject to proration | 20 |
| liquidating distribution | 13 |
| required to divest | 2 |

### Q7 eliminates four classes by construction, verified on instances

Rather than assert this, two were checked against the actual filings:

- **CECO / Thermon, "subject to proration"** — the destination is *"cash and/or
  shares of CECO common stock, at their election and subject to proration"*. A
  single named instrument, published in the merger terms. **Q7 fail: the
  destination set is handed to you, so the event tests transmission rather than
  enumeration.**
- **Casella Waste, "mandatory redemption"** — the clause is conditional
  boilerplate: *"If the Bonds are declared to be taxable … the Bonds are subject
  to mandatory redemption."* Nothing is being redeemed. **Q8a fail: no compulsion
  is asserted as fact.**

The same reasoning disposes of mandatory conversion and mandatory exchange — both
name their destination instrument in the notice itself.

### Then the screen itself turned out to be broken

A regex was written to separate filings that *assert* compulsion from those that
merely *describe* it, and applied to the 22 chronologically-first forced-selling
candidates. It reported "COMPULSION ASSERTED" for eight of them.

**Every one of those eight was a false positive.** The matched text came from
credit-agreement exhibits attached to the 8-K, not from the body reporting an
event:

- *"Plan of Reorganization **means** any plan of reorganization…"* — a definition
- *"**if** amounts outstanding … shall have become due and payable"* — a condition
- *"at any time **after** all or any portion of the Obligations have been declared
  due and payable **pursuant to Section 9.2(b)**"* — a cross-reference

The underlying error is not the regex. It is the channel:

> **Full-text search for forcing language finds contracts, not events.** Credit
> agreements are filed as exhibits and are dense with exactly the vocabulary a
> forcing event would use, so the corpus is dominated by instruments that
> *describe* compulsion rather than filings that *report* it.

Recorded rather than quietly fixed, because a screen that looks like it is
working and is not is the same class of failure as a firewall that looks like it
is working and is not — and that has now happened three times in this project.

## Attempt 2 — screen by 8-K item code. **Correct channel.**

Item 2.04 is *"Triggering Events That Accelerate or Increase a Direct Financial
Obligation"*. A filer uses it only when such an event **has occurred**, which is
precisely the Q8a predicate: a document someone was obliged to file, asserting
compulsion as fact.

**51 candidates** in the window. Sample of the chronological set:

| Filed | Entity |
|---|---|
| 2026-06-01 | EchoStar Corp (SATS) |
| 2026-06-03 | DevvStream Corp (DEVS) |
| 2026-06-04 | American Shared Hospital Services (AMS) |
| 2026-06-08 | Silver Star Properties REIT |
| 2026-06-12 | Sleep Number Corp (SNBR) |
| 2026-06-16 | Assertio Holdings (ASRT) |
| 2026-06-25 | Permex Petroleum, Clearwater Analytics, AMC Entertainment |
| 2026-06-26 | VSee Health (VSEE) |
| 2026-07-06 | Fortress Net Lease REIT |
| 2026-07-08 | AXT Inc (AXTI) |
| 2026-07-13 | Data I/O Corp (DAIO) |
| 2026-07-15 | Creative Media & Community Trust (CMCT) |

Item 2.04 should be complemented by the parallel item codes before the screen is
called complete: **1.03** (bankruptcy or receivership), **2.05** (costs
associated with exit or disposal), **3.01** (delisting or listing-rule
non-compliance) and **N-8F** / **497** for fund wind-ups. Each is a filing a
party is obliged to make and each asserts an event rather than describing a
contingency.

## Status

**The run is set up but not complete.** What remains, in order:

1. Extend the item-code screen to 1.03, 2.05, 3.01 and fund wind-up forms.
2. Walk the combined set **in strict chronological order**, applying
   Q1–Q7 + Q8a + Q8b, and **take the first qualifier** — not the most
   interesting one. Log every rejection with the criterion it failed.
3. Map edges in the direction-aware format, expecting most of these to be forced
   **sales** with an empty `absorption_set`.
4. Write `prediction.md`, commit, seal — **committing the quarantine reasoning
   before the prediction exists**, per §7.3.
5. Score S1–S4 separately against the closed window.

### One expectation worth stating before step 2 rather than after

Nearly every Item 2.04 event is a forced **sale**. Under the direction-aware edge
format the honest output for most will be a derivable `forced_supply_set` and an
**empty `absorption_set`** — because no rule compels anyone to buy.

If that is what the screen produces, the finding is not "the framework failed on
this event". It is the structural point the methodology review already reached
from the other direction: **publicly-documented forcing is overwhelmingly forced
selling, and enumeration has much more to say about forced buying.** Stating it
now means it cannot later be presented as a discovery the run made.

---

# Session 2 — 2026-08-22. Screen rebuilt; the item-code channel was also broken.

## Firewall re-applied and re-verified, with two new defects

Full record: `blindrun2/firewall_verification.md`. In short: the blackhole was
found **gone again** at session start (second consecutive session, so
non-persistence is normal container behaviour, not an anomaly); it was re-applied
and verified by resolution on both record types. Two findings that change what
the firewall claim means:

1. **IPv6 is closed here by absence of a network stack, not by the blackhole.**
   No inet6 address, no default v6 route, no AAAA for any host including the
   permitted ones.
2. **The blackhole is NOT the binding control in this environment.** Outbound
   HTTPS is routed to a local agent proxy that performs its own resolution, so
   `/etc/hosts` is never consulted on that path. HANDOFF section 3, executed
   exactly as written, reports a green firewall while leaving that path open.
   What actually binds is the **PreToolUse guard, which IS live this session** —
   established unplanned, when it refused the operator's own first probe before
   egress. The handoff's ordering of primary and defence-in-depth is inverted
   here.

Guard false positives **#5 and #6** were recorded and routed around — never by
widening the allowlist.

## Attempt 3 — EDGAR's `items=` filter. **Also wrong, and abandoned.**

The obvious fix for the phrase-matching problem in attempt 2 is EDGAR's own
`items=` query parameter, since 8-K item membership is structured metadata
rather than prose. A first probe looked perfect: `items=2.04` returned 17
filings, **every one of which carried 2.04 in its own metadata.**

**That filter is not reliable and must not be used.** Two diagnostics, both kept
in the repo (`diag_items.py`, `diag_items2.py`):

| Probe | Result |
|---|---|
| Five spaced requests, codes 1.03 / 2.04 / 2.05 / 3.01 / 5.02 | **Four byte-identical bodies** — all of them the 1.03 result set. 3.01 alone returned its own. |
| Four codes × {plain, cache-busted}, `Cache-Control: no-cache` | **All eight byte-identical** — that time all the 2.05 set |

The endpoint intermittently serves a **stale body computed for a different
`items` value**, and neither a no-cache header nor a unique cache-busting
parameter defeats it, so it is not an edge cache the client can wash out.

The danger is precise: had the first probe been trusted, the screen would have
silently mixed result sets while appearing to work. That is the **fourth** time
this project has hit the same failure class — a phrase screen that looked right,
an IPv4-only blackhole that looked right, a non-persistent blackhole that looked
right, and now a filter that looked right. The lesson is now explicit:

> **Never trust a filter's promise. Verify the payload against its own
> metadata.**

## Attempt 4 — complete enumeration, client-side filtering. **The screen that holds.**

Rather than ask EDGAR to filter, **every 8-K filed in the window is enumerated**,
day by day, and filtered on each filing's OWN `items` array — which travels in
the response body beside the filing it describes and therefore cannot be
transposed between result sets.

Each page is validated before acceptance (every hit must actually be an 8-K and
must fall on the requested day) and re-requested on failure. Completeness is
checked against EDGAR's reported total for each day.

**7,413 8-K filings enumerated across 2026-06-01 to 2026-07-15. Zero shortfalls
on any day. Zero stale pages during the sweep** — the validator was armed and
never had to fire.

### Item census, derived client-side

| Item | Filings | What it is |
|---|---|---|
| 1.03 | **7** | Bankruptcy or Receivership |
| 2.04 | **17** | Triggering Events That Accelerate a Direct Financial Obligation |
| 2.05 | **24** | Costs Associated with Exit or Disposal Activities |
| 3.01 | **125** | Notice of Delisting / Failure to Satisfy a Continued Listing Rule |
| — | **166** | distinct 8-Ks carrying at least one target item |
| N-8F | **9** | Application for deregistration of an investment company |
| 497 | **1,492** | Definitive materials (fund wind-up supplements, among much else) |

### Correction to the recorded Item 2.04 count

The previous session recorded **51** Item 2.04 candidates. The true figure is
**17**. The 51 came from full-text searching the literal string `"Item 2.04"`,
which counts any document that *mentions* the item number — exhibits and
amendments included. The structural count is cross-validated: enumeration and
the (unreliable) filter agree at 17 for 2.04, 24 for 2.05, and agree for 1.03
once the two non-8-K `ABS-15G` filings the filter mixed in are removed.

This is a **downward** correction to the candidate pool and is recorded rather
than quietly adopted.

## Two procedural rules, fixed now — before the walk, before any candidate is assessed

Both are recorded cold. Neither was chosen with knowledge of which candidate it
favours, because the walk has not been performed.

### Rule 1 — intra-day ordering

"Strict chronological order" does not resolve ties, and 2026-06-01 alone carries
multiple candidates. Ordering is therefore **(filing date, then accession
number)**. The accession number encodes EDGAR's own submission sequence, so it
is the closest available proxy for actual filing time and is deterministic.

### Rule 2 — Form 497 is rejected as a class, at the form level, on Q8a

Form 497 is a **container**: "definitive materials" filed under Rule 497. The
*filing* is obliged, but the form asserts nothing about the world — it is a
delivery mechanism for prospectus text, most of it routine.

> Q8a requires a document that **states, as fact, that a named actor is required
> to transact.** A 497 does not. The form is a wrapper; whether any given one
> announces a liquidation is a fact about its contents, not about the form.

Narrowing 1,492 of them to the liquidating subset requires searching for
liquidation language **inside** the documents — which is the phrase-matching
channel already established as broken in attempt 1, and which fails for the same
reason: a prospectus *describes* liquidation procedure as a contingency without
any liquidation having occurred.

**N-8F carries the same information and satisfies Q8a properly**: an application
for deregistration is filed only when a fund has actually wound up, so it asserts
a completed event rather than describing a possibility. All 9 are retained.

**The recall cost is stated rather than hidden:** any fund wind-up announced in a
497 whose sponsor had not yet filed an N-8F within the window is invisible to
this screen. That is a real gap in coverage. It is accepted because the
alternative is a channel already known to produce false positives, and because
the direction of the error is conservative — it can only *remove* candidates,
never manufacture one.

**Pool carried into the walk: 166 8-K filings + 9 N-8F = 175 candidates.**

---

## Walk complete — 175 candidates, 0 qualifiers. See `verdict.md`.

The chronological walk was performed over the full 175-candidate pool in strict
`(filing date, accession)` order, with criteria applied in numerical order and
the first failure recorded. **No candidate qualified.**

| Criterion | First failures |
|---|---:|
| **Q1** citable forcing | 99 |
| **Q7** enumeration content | 37 |
| **Q2** price insensitivity | 34 |
| **Q3** magnitude floor | 5 |
| | **175** |

**Nothing reached Q4**, so Q8a and Q8b — the criteria this whole methodology
review was built around, and the ones that ended blind run 1 — were never
exercised by a single candidate.

Per-candidate log: `walk_log.md`. Verdict and reasoning: `verdict.md`.
Robustness of the two interpretive calls that carried the largest blocks:
`robustness.py` — withdrawing either leaves every affected candidate rejected.

**Stop condition fired (spec v2 §7.4, first clause): no event satisfies Q1–Q8b.**
Recorded against the screen, not against any event, because no event was ever
selected. No prediction was sealed and no outcome data was touched.
