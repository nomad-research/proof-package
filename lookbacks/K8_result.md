# K8 — result

*Run 2026-09-29 against the v15 ledger (chain verified), per `K8_prereg.md`.*

## Verdict: **unreadable** under the pre-registered guards

| | qualifying nodes | passing | share |
|---|---|---|---|
| K8-proxy, all rounds | 2 | 1 | 0.5 |
| K8-proxy, clean | 1 | 1 | — |
| K8-strict | 0 | 0 | — |

Two nodes can't carry a kill test. Nothing clears the guards, for two reasons that belong to the v15 record,
not to the world:

1. **141 of 200 v15 positions have no `knowable_from`.** The spec counts a missing `knowable_from` as
   unknown (§14), so those rows can't pass the time-wall guard.
2. **Rounds 1–6 have no `touched_set` rows and no node on their event.** The table was introduced later,
   so under the pre-registered node definition those rounds have no nodes at all.

v15's stake term is blank on almost every leg, so K8-strict has no denominator.

## Post-hoc sensitivity (NOT a verdict)

Written after the result above came back, and labelled accordingly (`k8_sensitivity.py`): the
`knowable_from` guard is dropped (positions only need to be recorded before the original lock), each
round's own `events.node` is used, and rounds 1–6 get a stated manual node map. Listed status is as
recorded in September 2026.

- Nodes with any sided holder: **11**.
- Listed holders on both sides, **or** a listed holder with options: **9 / 11 (0.82)**.
- Listed holders on both sides only: **6 / 11 (0.55)**.
- Nodes that fail: the Antwerp access node (only one side listed, no options), Sasolburg (only the
  losers listed), and three nodes with no sided holder recorded before lock (Singhitarai, Gelsenkirchen,
  Deurganck). The cloud-region node has none either.

**Read with care.** Unguarded, the record points the way K8 hopes: most nodes carry a listed hedge, mostly
through options. But this is exactly what the guards exist to stop us concluding, because positions with
no `knowable_from` may have been authored from later documents.

## What would make K8 readable

A backfill of `knowable_from` on the v15 positions from their `source` and `source_time` fields, done by
someone who can't see outcomes, as a dated migration row per position. Then re-run `k8.py` unchanged.
