# Quarantine standard — blind run 2

**Written 2026-08-22, before any candidate has been assessed against any
criterion, before any edge has been attempted, and before `prediction.md`
exists.**

HANDOFF §5.4 requires the quarantine reasoning to be committed before
`prediction.md` exists, so that the standard is timestamped independently of any
map and cannot have been reverse-engineered from one. This document goes further
and fixes the standard before the **candidate walk** has been performed, so it
cannot have been shaped by knowing which event it would be applied to. At the
time of writing, the operator has a pool of 175 candidates and has assessed
**none** of them.

REPORT.md §8 lists "commit the reasoning before the prediction exists" among the
things that worked and says it *should be the default ordering for every run*.
This is that ordering, applied one step earlier than required.

---

## 1. The thing this standard exists to stop

Spec v2 §5, quoted in `methodology/pre_event_review.md`:

> **Assertion that a rule exists is not evidence a rule exists. Confidence is
> not verification.**

The failure mode is not obscurity and it is not laziness. It is **fabrication**:
a model producing a fluent, plausible citation to a rule that does not exist, or
that exists but does not say what is claimed. Documented hallucination rates on
legal and regulatory text are high enough that unverified extraction is unusable,
and an operator's own certainty carries no information about whether the clause
is really there.

Blind run 1 quarantined **3 of 3** edges and that was the correct outcome. A high
quarantine rate is not a failure of the run. It is the standard working.

## 2. What "verified" requires. All five, for every edge.

An edge is **VERIFIED** only if every one of the following holds. Failing any one
quarantines the edge. There is no partial credit and no aggregation across
criteria — four out of five is a quarantine.

| # | Requirement | What discharges it |
|---|---|---|
| **V1** | **The document was fetched.** | It exists on disk under `firewall/fetched/`, with a `fetch_log.jsonl` or `edgar.py` entry carrying its URL and filing date. A document I have not retrieved cannot support an edge, however confident I am about its contents. |
| **V2** | **The document was filed before the ceiling.** | Filing date is on or before the operator document ceiling (the selected event's trigger date, per the exclude-only amendment of 2026-08-22), and strictly before the configured `fire_date`. Enforced in code by `firewall/edgar.py`, not by operator discipline. |
| **V3** | **The clause is located verbatim.** | The exact text is quoted in `edges.md`, with its position in the document identified, copied from the fetched file rather than recalled. A paraphrase is not a location. A section number without the text is not a location. |
| **V4** | **The located clause actually says what the edge claims.** | The quoted text, read on its own without surrounding argument, compels the named actor to transact. This is the criterion that kills definitions and conditions — see §3. |
| **V5** | **The compulsion is asserted by the filer, not reconstructed by me.** | Q8a. The filer states as fact that a named actor is required to transact. If the chain from document to conclusion passes through an inference of mine, the edge is quarantined regardless of how sound the inference is. |

## 3. Three text patterns that look like forcing and are not

These are not hypothetical. All three were the actual false positives that broke
the attempt-1 screen, and each is quoted in `screen_log.md` from a real filing.

1. **A definition.** *"Plan of Reorganization **means** any plan of
   reorganization…"* — defines a term. Compels nobody.
2. **A condition.** *"**If** amounts outstanding … shall have become due and
   payable"* — describes a state of the world that may or may not obtain. Nothing
   has happened.
3. **A cross-reference.** *"at any time **after** all or any portion of the
   Obligations have been declared due and payable **pursuant to Section
   9.2(b)**"* — points at a mechanism elsewhere. It is not itself the trigger.

> **Operative test.** A clause qualifies only if, read alone, it establishes that
> a **named actor** must transact, that the obligation is **live rather than
> contingent**, and that the triggering event **has already occurred**. Present
> and perfect tenses qualify. Conditionals, subjunctives and definitional
> language do not.

Credit agreements are filed as material-contract exhibits and are dense with
exactly this vocabulary. **An exhibit is where forcing language lives; the 8-K
body is where forcing events are asserted.** A clause found only in an exhibit
satisfies V3 but must still satisfy V4 and V5 on its own terms, and usually will
not, because an exhibit describes a mechanism rather than reporting that it
fired.

## 4. Direction-aware requirements

Per `methodology/pre_event_review.md` Defect 2, the edge format is direction-aware
and the fields differ by direction.

### If `forced_action == sell`

- `forced_supply_set` — the instruments that must be sold. Verified from either
  the rule itself or the actor's **own disclosed holdings**, with the holding
  located in a filing, not inferred from a business description.
- `supply_basis` — the located clause or the disclosure, quoted.
- `absorption_set` — who is **compelled** to take the other side.

> **An empty `absorption_set` is a finding and must be recorded as `EMPTY`, never
> as absent, omitted, or "n/a".** In almost every case no rule compels anyone to
> buy. Writing `EMPTY` states that the operator looked and found no compelling
> rule. Leaving the field blank states nothing and hides the asymmetry the field
> was created to expose.

An empty absorption set means the price effect depends on voluntary buyers'
willingness. **That is a liquidity claim, not an enumeration claim**, and an edge
resting on it must say so in terms.

### If `forced_action == buy`

- `eligible_destinations` — the set capital may land in, per the rule.
- `destination_basis` — eligibility **rules**, with clauses located. Not
  inference, not plausibility, not "these are the obvious candidates".

## 5. Quarantine is recorded per edge, per field

Each quarantined edge records: the edge id, **which of V1–V5 failed**, the field
that could not be discharged, and what would have discharged it. This is what
makes the quarantine rate interpretable rather than a bare count — blind run 1's
table named the failed field for all three of its edges and that is the format to
follow.

## 6. Pre-registered consequences, so they cannot be renegotiated later

These follow from HANDOFF §7 and are restated here so that the arithmetic is
fixed before the numbers exist.

- **Zero verified edges on the first qualifier → NOT OPERABLE for that event.**
  Recorded as a failure of that event. **Not** a licence to shop for a better
  one.
- **Quarantine rate > verified rate → NOT OPERABLE.** With `q` quarantined and
  `v` verified out of `a` attempted, `q > v` fires the stop condition. Note that
  `a = 3, q = 2, v = 1` fires it.
- **High recall, zero spread → OPERABLE, EDGE ABSENT.** The map was right and the
  market had already priced it. This is a *different* result from a wrong map and
  is the one the decay literature predicts. It must not be reported as a failure
  of the map.
- **No event satisfies the criteria → NOT OPERABLE**, recorded against the
  screen rather than against any event.

## 7. What this standard may not do

It is **exclude-only**. It can remove an edge from the verified set; it can never
add one, and it can never turn a null into a hit. Per
`methodology/pre_event_review.md` Defect 3, that is the correct scoping: this
document touches *results*, so exclude-only governs it, and it may not be
relaxed after outcomes are visible for any reason.

**Tightening it after seeing outcomes would also be illegitimate**, because a
tightening that removes an inconvenient verified edge is fitting in the other
direction. The standard is fixed as of this commit. Any change is a dated
appendix that states what it changes and why, and changes made after outcome data
has been touched are recorded as such and their effect reported both ways.
