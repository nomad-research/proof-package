# K7 — pre-registration (DRAFT: the pass share is unset)

*Written 2026-09-29 by the build session, before the candidate list was generated and before any holder was
looked up. Spec v16 §31 K7: "The ownership census finds listed instruments (equity or bond) with concentrated
exposure for a meaningful share of the high-stake unlisted holders from rounds 1–15 (the share is
appetite). Dies if the census comes back near-empty. Consequence: close the equity thesis; move to shapes B
and C."*

**The pass share, `K7_SHARE`, is not in `config/appetite.json` on purpose.** Rob sets it in a dated commit
*before the census starts* (the v17 checkpoint requires it). Until that commit exists, `python -m nomad16
census` reports counts and refuses to state a verdict.

## Which holders (mechanical, fixed here)

From the frozen v15 ledger (`v15/nomad_harness.db`, opened immutable):

1. **Population:** holders with `listed = 0` and `kind` in {company, plant, facility, other} that appear in
   `touched_set` in any un-voided round (rounds 1–15, including the round 12 re-run; the voided originals
   excluded). Authorities are excluded: they have no equity or bond to find.
2. **Rank:** by (a) the largest `|impact_pct|` on any `leg_claims` row for the holder, descending, where one
   exists; then (b) the lowest degree at which the holder appears in `touched_set`, ascending; then (c) the
   number of distinct rounds it appears in, descending; then (d) name, ascending. v15 recorded stake on
   only 4 unlisted legs, so (b) and (c) decide most of the order, and that is disclosed rather than hidden.
3. **Take the top 15.** `k7_candidates.py` writes `k7_candidates.json`. The list is not edited by hand.

## What counts as a find

For each candidate, look for a **listed equity or bond** such that the candidate is a **concentrated share of
that instrument's exposure**, through one of: a listed parent, a majority owner, a sole (or >50%) customer, a
lender or bond issuer whose credit rests on it. Each find records the instrument, the relation, the
concentration figure where one is published (else `null`), the source document and its `knowable_from`.
`concentrated` is the census-taker's judgment against this rule: **the candidate accounts for at least 25%
of the instrument's revenue, earnings, capacity, or collateral value** (the inert-stake ceiling in §33.1).
**Control alone is not enough.** A listed parent or majority owner whose share of the candidate is high but
for which the candidate is a small part of the parent's own exposure is exactly the dilution R16-001 hit
(a 1.1 GW unit was about 0.01% of its listed owner's value). Such rows are recorded as `unquantified_control`
and reported separately; they are not finds. Only a published or computable concentration figure at or
above the threshold makes a row a find.

A holder is **found** if it has at least one such row, **not found** otherwise. A holder the census-taker
couldn't research in reasonable effort is `unresolved`, and stays in the denominator as not found.

## Verdict rule

Share found = found ÷ candidates. K7 **dies** if the share is below `K7_SHARE` (Rob's, unset), and the
spec's consequence follows: close the equity thesis and build on shapes B and C. Report beside it, and
never blended: how many finds are parent/majority-owner (control) versus customer/lender (credit), and
how many carry a published concentration figure.

## Decisions left to Rob before the census starts

The candidate list is mechanical, and two of its features are worth a look before it is used:

1. **Sister and aggregate entries.** Rank 3 and 4 are one group and its yard; 5 and 15 share a parent; rank 13
   is an aggregate ("Chinese trichlor exporters") that has no single listed parent, so it can only be
   `not found`. Rob may amend the population rule (for example, collapse an asset into its operator, drop
   aggregates) **before** the census starts; after that it is fixed.
2. **The 25% threshold.** It reuses the inert-stake ceiling. A different figure is a legitimate choice if
   set before the census, together with `K7_SHARE`.

## Guards

- **Time:** a find counts only if its source's `knowable_from` is on or before the earliest event date among
  the rounds the holder appears in. (A parent that IPO'd later is not a find.)
- **Listing:** "listed before the event" is checked from the instrument's first-trade date where the
  price source gives it; otherwise stated as unenforced, as in K8.
- **The census-taker sees the candidate's name and its rounds' event lines, never the outcomes** of those
  rounds. The build session has seen outcomes, so it prepares the worksheet and doesn't run the census.
