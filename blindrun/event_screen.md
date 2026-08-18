# Event screen (§2) — recorded as the analyst reported it, not as it should have gone

**D = 2026-06-15.** Screened classes: index reconstitution, fund liquidation.

## §2.1 was NOT satisfied. The analyst disclosed this rather than papering over it.

| # | Event | Date | Q1–Q6 | Outcome |
|---|---|---|---|---|
| 1 | **FTSE Russell annual reconstitution** | effective after close 2026-06-26 | **PASSES as written** | **First chronological qualifier. OVERRIDDEN — not rejected on a Q1–Q6 failure.** Ground: FTSE publishes preliminary add/delete lists from 22 May with lockdown from 8 June, so the destination set is handed to the operator a month in advance. The event tests transmission, not enumeration. |
| 2 | Situational Awareness LP — forced liquidation of public equity book | fire 2026-07-30 | selected | **Tested.** Selected on the structural ground above, not because it was first. |

**Situational Awareness was not the first qualifier.** §2.1 says test the first
qualifier, "not the most interesting one, not the largest, the first." That rule
was overridden, and the override was made before the screen was amended rather
than after.

## Amendment — Q7, added 2026-08-17, post-hoc and disclosed

> **Q7 — ENUMERATION CONTENT.** The eligible destination set must not be
> published in advance by the forcing party, an index provider, or any public
> list dated before the fire date. If the destinations are already enumerated for
> you, the event tests transmission, not enumeration.

**Fence:** Q7 can only *exclude* events, never include one, so it cannot
manufacture a positive result. It is derived from a prior finding in this
project — an earlier test was invalidated for exactly this defect and the screen
failed to encode the lesson.

**Operator's assessment of the override.** The substance is right: an event whose
destination set is published a month ahead genuinely cannot test enumeration, and
Test A-2 in this repo failed for a related reason. But the *procedure* is what
§2.1 exists to protect, and it was not followed. The correct order was to amend
the screen, then re-run it, then take whatever came first. Overriding first and
amending afterwards leaves the selection dependent on the selector's judgement at
the moment of choosing — and the selector has disclosed outcome exposure on this
event. So:

- Operator-side blindness is **intact** — I do not know the outcome.
- Selection-side blindness is **not** — the event was chosen by someone who did.
- Therefore **a positive result on this event is weakened and must not be read as
  a clean hit.** A negative result is unaffected, because outcome knowledge on the
  selector's side cannot manufacture a miss.

## Contamination flag — declared by the analyst, contents withheld

The selector has outcome exposure from the search that surfaced this event:
sector-direction commentary, and a small number of specific tickers named as
peers trading alongside the book. The ticker list is withheld from the operator
and held by the human analyst for scoring.

**Agreed handling:** if the sealed destination set is predominantly composed of
the withheld tickers, that is recorded as a **coincidence flag** in the results.
It does not invalidate the map — it was built blind — but it must be visible
rather than buried.
