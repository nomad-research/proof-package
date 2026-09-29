# K11 and K12 — results

*Run 2026-09-29 exactly as pre-registered (`K11_K12_prereg.md`, commit 6110244, pushed before any price was
fetched). Script `k11.py`; full output `k11_result.json`. Every price is from the nomad16 vintage store.*

## K11 — **dies**: no separation beyond noise

| | units whose residual left its band | units that stayed | median ρ, left | median ρ, stayed | one-sided MWU p | verdict |
|---|---|---|---|---|---|---|
| **Pooled, rounds 5–15** | 8 | 79 | 0.920 | 0.954 | **0.65** | **no separation: K11 dies** |
| Clean | 2 | 43 | — | — | — | unreadable (fewer than 5 left) |
| Learning | 6 | 36 | 0.897 | 0.932 | 0.73 | no separation |

The sign is the wrong way: units that later moved had slightly *lower* ρ. Per the spec, ρ doesn't measure
unpricedness on this record, so **drop the priced test (`RHO_MIN`) and build on the visibility test alone**
(§31, "If it dies").

**Read with these beside it.**
- **Base rate.** 8 of 87 units (9%) left a 90% band. That is about the rate noise alone produces.
  The v15 events rarely moved a listed instrument beyond its own noise, which is the wall map again. With
  so little signal there is little for ρ to separate. K11's death says ρ didn't find signal here, not that
  signal exists and ρ missed it.
- **Narrow hedged set.** H is the tide plus at most one narrative story per round, so ρ sits near 0.9
  almost everywhere. A richer story set (v16 rounds name several) is where ρ could still earn its keep.
  That would be a new test, never a re-run of this one.
- **Degenerate rounds.** Rounds 5 and 15 had one instrument, so ρ ≡ 0; they were excluded from the test and
  reported, as pre-registered.
- **Exclusions.** No series: `SAA1V.HE` (rounds 10, 11) and `VBX.DE` (round 10). Home index unavailable, so
  the ACWI tide was used, per the rule: `WIG20.WA` and `OBX.OL` returned empty series, and `^IPSA` was
  rate-limited on both attempts. That affects `ATC.WA`, `NSKOG.OL`, `BESALCO.SN` and `SALFACORP.SN`. A rate
  limit is not an absent series, so rerunning when `^IPSA` fetches would change those units' tides.
  The rule is fixed, so that rerun is legitimate; the verdict above stands until it is done.
- **Independence.** Units within a round share an event, so p overstates the evidence. The per-round medians
  in `k11_result.json` show no round where left units clearly carry higher ρ.

## K12 — **unreadable on the v15 record**, as pre-registered

v15 registered at most one narrative story per round and no story paths, so there are no within-round pairs
and nothing to flag. K12 accumulates from v16 rounds. R16-001 logged one flagged junction on a constructed
story, which `junction_confirm` doesn't test yet, and four unflagged correlation rises, logged as pianos.
