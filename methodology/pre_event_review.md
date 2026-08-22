# Methodology review before the next real-events run

**Date: 2026-08-21. Decided cold — no candidate event is in view, and none has
been proposed.** That timing is the whole point: spec v2 §3.1 says *"If Q8
relaxes because it is too strict, that is a standard. If it relaxes because it
excluded an event you wanted, that is fitting. Only timing distinguishes them."*

**Status: the methodology was NOT ready. Four defects, all now resolved below.**

| # | Defect | Source | Blocks a run? |
|---|---|---|---|
| 1 | **Q8 excludes nearly the whole addressable universe** | flagged by spec v2 §3.1 itself | **yes** |
| 2 | **The edge format is buy-only.** A forced *sale* cannot be written in it | found in the blind run, never fixed | **yes** |
| 3 | **§4 contradicts §3.1.** "Every amendment must be exclude-only" forbids the Q8 relaxation §3.1 proposes | internal inconsistency | **yes** — you cannot follow both |
| 4 | **No sanctioned way to screen events** under the search ban | gap between §7.1 and §7.2 | **yes** |

---

## Defect 1 — Q8. **Decision: replace with Q8a + Q8b.**

### What Q8 says now

> The document naming the rule that removes discretion must be publicly
> retrievable at the fire date. Private contracts — prime brokerage margin
> agreements, LPAs, ISDA CSAs, bilateral covenants — do not qualify however
> certain the forcing is.

### What Q8 is actually protecting against

Not obscurity. **Fabrication.** Spec §5: *"Assertion that a rule exists is not
evidence a rule exists. Confidence is not verification."* The failure mode is a
model producing a plausible citation to a rule that does not say what is claimed,
and documented hallucination rates on legal and regulatory text are high enough
that unverified extraction is unusable.

Q8 is a blunt instrument aimed at a real target.

### Why it over-shoots

Q8 conflates two different requirements that the edge format keeps separate:

1. **Is the actor genuinely compelled?** (`binding_rule`)
2. **Is the destination set derivable rather than guessed?** (`destination_basis`)

The blind run failed on (1) and never got to (2) — even though (2) was
comfortably satisfiable: the destination set was fully derivable from 13F, 13D,
13G and Form 4, all public, all retrieved, all with located clauses.

There is also a factual error embedded in Q8's list. **Credit agreements and
indentures are frequently public**, filed as material-contract exhibits under
Item 601. The genuinely unretrievable set is narrower than Q8 implies: it is
contracts where the constrained actor has **no disclosure obligation** — prime
brokerage margin terms, private-fund LPAs, bilateral CSAs, private repo.

The right axis is not *public contract vs private contract*. It is **whether the
constrained actor is subject to a disclosure obligation.**

### Decision

**Q8 is replaced by two criteria.**

> **Q8a — Forcing evidence.** A document that a party was *obliged to file or
> publish* must state, as fact rather than as operator inference, that a named
> actor is required to transact. The specific private instrument need not be
> retrievable, but **the compulsion must be asserted by the filer, not
> reconstructed by the operator.** An 8-K reporting a covenant default and
> acceleration qualifies. A holdings disclosure does not — it reports what is
> held, not that anything must be sold.
>
> **Q8b — Destination derivation.** Every member of the eligible set must be
> derivable from publicly retrievable rules or disclosures, each traceable to a
> located clause or a disclosed holding. Where the forcing instrument itself is
> retrievable it is used; where it is not, the destination set must be
> independently derivable, and if it is not, the edge is quarantined as before.

### The test that this is a standard and not fitting

**Q8a still excludes the event that exposed the problem.**

Situational Awareness failed the old Q8 because no public document named the
forcing clause. It fails Q8a too, for a different and more precise reason: no
document *obliged to be filed* asserted that the fund was required to transact.
The analyst confirmed as much — *"No such document exists and none can."* A 13F
reports holdings; it asserts no compulsion, which is exactly what Q8a demands and
does not get.

So the relaxation does not retro-admit the event that motivated the review. That
is the strongest available evidence it is a standard rather than a rescue, and it
is the reason to record the decision now rather than when a candidate is in hand.

### What the change actually admits

| Event class | Old Q8 | Q8a + Q8b |
|---|---|---|
| Covenant default disclosed in an 8-K, credit agreement filed as an exhibit | excluded | **admitted** |
| Rating downgrade forcing mandate ineligibility, index rules public | ambiguous | **admitted** |
| Regulatory deadline, deadline document public | admitted | admitted |
| Corporate action proration, terms in the offer document | admitted | admitted |
| Fund liquidation with no filed assertion of compulsion | excluded | **still excluded** |
| Margin call on a private fund | excluded | **still excluded** |
| Index reconstitution | excluded by Q7 | excluded by Q7 |

The universe goes from *almost empty* to *small but non-empty*, and the two
classes most prone to fabricated forcing stay out.

---

## Defect 2 — the edge format cannot express a forced sale. **Decision: make it direction-aware.**

The blind run hit this and flagged it; it was never fixed. Spec v2 §5 still reads:

```
eligible_destinations: the set capital may land in, per the rule
```

A liquidation is forced **selling**. The capital lands in cash and then with
limited partners. There is no destination set in that sense, so the format cannot
be completed — not because the analysis failed but because the form asks the
wrong question. Any liquidation, redemption cascade, margin call or
covenant-triggered disposal hits this.

### Decision — replace the two destination fields with a direction-aware pair

```
EDGE <id>
  ...
  forced_action:        buy | sell
  magnitude:            in DAYS OF ADV of the named set below
  magnitude_basis:      derivation, from which figures in which document

  # if forced_action == buy
  eligible_destinations: the set capital may land in, per the rule
  destination_basis:     eligibility rules, not inference

  # if forced_action == sell
  forced_supply_set:     the instruments that must be sold, per the rule or
                         per the actor's own disclosed holdings
  supply_basis:          holdings disclosure or rule, with the clause located
  absorption_set:        who must take the other side, IF a rule compels anyone.
                         Usually EMPTY — and an empty absorption set is a
                         finding, not a gap
  ...
```

**`absorption_set` is the field that earns its place.** For forced buying, the
enumeration edge is *where must this land*. For forced selling, the equivalent
question is *who must absorb it* — and the answer is usually **nobody**, because
no rule compels anyone to buy. That asymmetry is a real property of forced flow
and the old format hid it by having no slot for it.

It also sharpens the thesis. If the absorption set is empty, the price effect
depends on voluntary buyers' willingness, which is a liquidity claim rather than
an enumeration claim. **Enumeration has more to say about forced buying than
forced selling**, and the format should make that visible rather than obscure it.

---

## Defect 3 — §4 and §3.1 contradict each other. **Decision: scope the exclude-only rule.**

- §3.1 proposes relaxing Q8.
- §4 says *"Every amendment must additionally be exclude-only — capable of
  removing a candidate or a result, never of manufacturing one."*

A relaxation of Q8 **admits** candidates. It is not exclude-only. As literally
written the two sections cannot both be obeyed, and the Q8 decision above would
be prohibited by §4.

### Decision

The exclude-only rule is doing real work, but not on qualification criteria. Its
purpose is to stop a *result* being manufactured. Scope it accordingly:

> **Exclude-only applies to amendments that touch results** — thresholds, test
> statistics, estimators, scoring rules, sample filters applied after outcomes
> are visible. These may only ever remove a finding.
>
> **Qualification criteria (Q1–Q8) are governed by the cold-decision rule
> instead**: they may be tightened at any time, and relaxed only against no
> candidate, with the reasoning recorded before any candidate is proposed.

This is not a loophole. It is the recognition that "which events are eligible"
and "what counts as a passing result" are different objects with different
failure modes. Widening eligibility changes the sample; it cannot turn a null
into a hit. Widening a threshold can.

Both remain disclosed and dated.

---

## Defect 4 — no sanctioned screening channel. **Decision: EDGAR full-text search, date-ceilinged.**

§7.2 requires screening events forward from a fixed date `D` by Q1–Q8. §7.1 bans
search. The spec never says how to satisfy both, and in the last run the analyst
did the screening — which is what put contamination on selection and forced the
coincidence flag.

### Decision

**EDGAR full-text search is the sanctioned screening channel**, under the same
carve-out reasoning already used and proven: it returns filing metadata and
filing text only. No narrative, no commentary, no market reaction, so it cannot
leak an outcome narrative because it does not contain one.

Conditions, all already implemented in `firewall/edgar.py`:

1. Results **filtered to filings dated before the fire date** before they are
   displayed, so a post-dated snippet is never surfaced.
2. Every filing opened is logged with its date.
3. Post-fire filings are refused in code, not by operator discipline.

**Consequence, and it is an improvement:** the operator can now screen without
the analyst, which **closes the selection-contamination channel entirely** rather
than merely disclosing it. Spec §7 already notes a prospective run is stronger
because it closes that channel; operator self-screening closes it for
retrospective runs too.

Screening queries are recorded in the run log with the criterion each rejected
candidate failed, per §7.2.

---

## Readiness

| Requirement | Status |
|---|---|
| Q1–Q7 | unchanged, usable |
| Q8 | **replaced by Q8a + Q8b**, decided cold above |
| Edge format | **direction-aware**, forced sales now expressible |
| Amendment rule | **scoped**, contradiction resolved |
| Screening channel | **EDGAR FTS**, date-ceilinged, operator self-screens |
| Firewall | proven, but **must be re-applied and re-verified at session start** — the DNS blackhole does not persist |
| Q3 magnitude floor | corrected: **0.8 days of ADV** is the floor, not 82.9 |

**The methodology is now ready for a real-events run.** Nothing above was decided
with a candidate in view, and the one decision that loosens a criterion has been
shown not to admit the event that prompted it.

### What a run needs next

Per §7.2, fix a date `D` after the operator's training cutoff, screen forward by
Q1–Q7 + Q8a + Q8b, and **take the first qualifier** — not the most interesting
one. Log every rejection with the criterion it failed.

Two open choices for the operator to confirm before starting, because they change
what the run can claim:

1. **Retrospective** (window closed, scorable this session) **or prospective**
   (sealed before the window opens, scored later — stronger, because nobody knows
   the outcome including the analyst).
2. **Operator self-screens** via EDGAR, closing the selection channel — or the
   analyst supplies the event, as last time, which reopens it and requires a
   coincidence flag.
