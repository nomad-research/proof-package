# Criteria in force for blind run 2

Assembled 2026-08-22 **before the candidate walk**, from the two authoritative
sources, so that the screen being applied is written down in one place and is
reproducible. Nothing here is new. Q1–Q7 are quoted verbatim from
`nomad_spec_v2.md` §3; Q8a and Q8b are quoted verbatim from
`methodology/pre_event_review.md`, which supersedes spec Q8.

`nomad_spec_v2.md` had never been committed to this repository — it existed only
as an uploaded artefact in a prior session, which meant **Q2, Q4, Q5 and Q6 were
unavailable to this session and the screen could not be applied faithfully.** The
operator raised this as a blocker rather than reconstructing the four missing
criteria, since inventing qualification criteria is precisely the fitting failure
the cold-decision rule exists to prevent. The analyst supplied the document and
it is now committed at the repository root.

---

## Q1 — Citable forcing

> A specific, retrievable document removes discretion from a named actor.

## Q2 — Price insensitivity

> The actor would complete the transaction at a materially worse price. Test:
> does the rule specify *what* and *when* but not *at what price*?

## Q3 — Magnitude floor *(corrected)*

> Forced flow must exceed **0.8 days of destination ADV**, which is the level
> A-2 showed produces nothing. A-2 gives no information about where above 0.8
> the threshold sits, so this is a floor and not a target. Prefer events at
> multiples of ADV.

**Direction-aware reading.** `methodology/pre_event_review.md` Defect 2 replaces
the destination fields for a forced sale and defines magnitude as *"in DAYS OF
ADV of the named set below"*. For `forced_action == sell` the named set is
`forced_supply_set`, so Q3 is applied against the ADV of the instruments that
must be sold. This is not a relaxation — the floor is unchanged at 0.8 days.

**The old figure was 82.9 and it was a multiplier, not a flow.** A screen
carrying it sets a bar about 100× too high. It is not used here.

## Q4 — Coverage thinness

> Destination candidates have low analyst coverage or are off-benchmark. Liquid,
> well-covered destinations have an abundant other side and no premium.

## Q5 — Resolved window

> For retrospective runs, the transmission window has closed. For prospective
> runs, it has not opened — see §7.

**This run is retrospective.** D = 2026-06-01, trigger window to 2026-07-15,
assessed 2026-08-22, so a five-week transmission window has closed for every
candidate in the pool.

## Q6 — Post-cutoff

> Fire date after the operator's training cutoff.

**Operator training cutoff: May 2026.** Every candidate in the pool is filed
2026-06-01 or later, so Q6 is satisfied pool-wide by construction. It is still
checked per candidate rather than waved through.

## Q7 — Enumeration content *(post-hoc, exclude-only)*

> The eligible destination set must **not** be published in advance by the
> forcing party, an index provider, or any public list dated before the fire
> date. If destinations are handed to you, the event tests transmission, not
> enumeration. This is why index reconstitution does not qualify.

## Q8a — Forcing evidence *(supersedes spec Q8)*

> A document that a party was *obliged to file or publish* must state, as fact
> rather than as operator inference, that a named actor is required to transact.
> The specific private instrument need not be retrievable, but **the compulsion
> must be asserted by the filer, not reconstructed by the operator.** An 8-K
> reporting a covenant default and acceleration qualifies. A holdings disclosure
> does not — it reports what is held, not that anything must be sold.

## Q8b — Destination derivation *(supersedes spec Q8)*

> Every member of the eligible set must be derivable from publicly retrievable
> rules or disclosures, each traceable to a located clause or a disclosed
> holding. Where the forcing instrument itself is retrievable it is used; where
> it is not, the destination set must be independently derivable, and if it is
> not, the edge is quarantined as before.

---

## How the walk applies them

**All of Q1–Q7 plus Q8a and Q8b must hold.** Spec §3: *"All eight must hold."*

**Order of application: numerical.** Q1, then Q2, … then Q8a, then Q8b. The
**first** criterion that fails is the one recorded, so every rejection has a
single unambiguous cause and the log is reproducible by anyone re-walking the
pool. Applying the cheapest criterion first would produce a different and
inconsistent set of recorded reasons for the same pool.

**Class-level dispositions are permitted, and must be verified on instances.**
Where an entire form or item code fails a criterion by construction, the class
may be rejected once and applied to its members — but only after the disposition
has been **checked against actual filings**, not asserted. This is the method the
prior session used for `mandatory conversion` and `mandatory exchange` under Q7,
where two instances were opened and quoted before the class was disposed of. A
class rejection that has not been instance-verified is not permitted.

**Order is strict and is not re-sorted around findings.** Candidates are walked
by `(filing date, accession number)` — the tie-break fixed cold in
`screen_log.md` before the walk. When a candidate belongs to a class already
dispositioned, the class rejection is recorded against it and the walk continues.
The first candidate that passes all criteria is the event. **Not the most
interesting one, not the largest, the first.**
