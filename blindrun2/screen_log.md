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
