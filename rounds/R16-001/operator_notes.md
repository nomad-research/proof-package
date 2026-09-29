# R16-001 — operator notes (segment 0, pre-lock)

Notes on inputs I authored and on computed objects I disagree with. Per §16 I did not edit any
computed object; where I disagree, the store it reads is named.

## Encodings I authored that a reader should know about

- **P00009 `uncommitted_capacity_share = 0.0` (stated).** The 10-K (EV00010) says DTE Electric "is a
  net purchaser of power that supplements its generation capability to meet customer demand during
  peak cycles or during major plant outages". That documents the template's inequality (uncommitted
  capacity does not cover the lost unit, so < 1) but publishes no figure. 0.0 encodes only the
  documented bound. If a reviewer reads this as unstated, the replacement-procurement ACK becomes a
  switch; nothing else changes (its basket is `shape_mixed` either way).
- **P00016 `event_impact_share = 0.01` (inferred).** An operator estimate from operating scale, not a
  document. It makes the current-report ACK a switch, as it should be.
- **P00012 `reportable_event_notified` (inferred).** Statute and the event line imply the 4-hour
  notification; the notification itself is published 2026-07-06, after the clock.
- **P00001 `unit_status = offline` (stated), source = the reveal event line.** It is the only
  pre-clock document of the trip; the 2026-07-03 status report (EV00001) is a morning snapshot and
  still shows the unit at 83% under a Hot Weather Alert.

## Effect magnitudes on the listed parent (E007–E009)

Stake from operating scale: 1,141 MW × 24 h ≈ 27.4 GWh/day replaced from MISO at a spread over nuclear
fuel of order $40–50/MWh ≈ $1.1–1.4m/day. That is a customer cost through PSCR (P00010, P00019), so the
shareholder effect is unrecovered O&M and repair, plus prudence risk on a long outage. Against a market
capitalisation of order $28bn (208.0m shares, EV00009): restart < 2w ≈ −0.01%, 2–6w ≈ −0.05%,
> 6w ≈ −0.4%. Every one is below DTE's hedged-residual band (7.9% at the 63-session horizon), and the
harness vetoes all three `below_band`. The shape is `mixed` (all outcomes flat), so every basket is
`unbuildable: shape_mixed`. This is the structural answer, not a construction failure: no listed
holder sits on the node with stake above noise (`lib.no_pure_play_spectacle`).

## Disagreements with computed objects (stores named)

1. **E003 vetoed `no_path`:** the transform table has no `ownership: availability → obligation`
   entry, while the obligation template `obl.replacement_procurement` says exactly this conjunction
   forces a procurement obligation on the owner. The table and the template disagree. I did not add a
   transform mid-round (that is library authorship, and §31's guard wants templates and transforms
   authored before events). Instead I re-rooted the obligation on its own document (E004, EV00010),
   which §6 allows. Store to fix: `transforms`.
2. **Grid-neighbour and insurer chains stop at attenuation** (0.25 and 0.16 < 0.30). The zone-price
   effect of a 1.1 GW baseload trip during a heat alert is the one channel that could reach a
   merchant generator. Under the provisional hop discounts it is unexamined, not vetoed. Store:
   `HOP_DISCOUNT` (provisional).
3. **Story classing is rank-limited.** With two linear instruments in reach (DTE, CMS), every story
   after the first two spans nothing new, so `st_nuclear`, `st_rates` and `st_unit_exposure` are
   classed synthetic by arithmetic, not by content. Store: the instrument map. No other listed holder
   has a documented position on the node or its neighbour.
4. **The written-event-report ACK was dropped** only because its carrier (LERs in ADAMS) is
   `not_covered`. Store: the carrier registry.

## Harness friction

- The guard treats any URL inside a Bash command as egress, so the commit trailer
  `Claude-Session: https://…` could not be written in a commit message pre-lock (the guard also refuses
  writes outside `rounds/`, so a message file can't be used). The blind-pass commit carries only
  the Co-Authored-By trailer.
