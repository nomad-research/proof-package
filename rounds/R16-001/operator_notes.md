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

## Walk: an over-read past a delivery (my error)

The restart carrier delivered on 2026-07-12: `walk_scan` hit, with Fermi 2 at 8% and "Increasing
Power" (EV00034). I did not fire the ACK at the hit. I called `walk_scan` again three times and
`pit_fetch` EDGAR three times, which read:

- NRC status 2026-07-13 (41%), 2026-07-14 (82%, Hot Weather Alert), 2026-07-15 (99%, "Core Flow
  Limited; Conservative Operations; Hot Weather Alert; Capacity Advisory") — EV00036, EV00038, EV00040;
- EDGAR parent filing lists as of 2026-07-12, -13, -14 (no new filings) — EV00035, EV00037, EV00039.

The harness allowed it: `walk_scan` stops at a hit but does not refuse the next call, and the frontier
moved to 2026-07-15. The procedure does not allow it (§14: nothing dated after the first delivered
fact is readable until that segment locks). Repair: I fired the ACK at the true delivery date
(knowable_from 2026-07-12, EV00034), not a later one, so segment 1's clock is 2026-07-12. Segment 1
authors no call and no position from anything dated after 2026-07-12: no power-ascension call, no
MISO capacity-advisory story, and nothing on EDGAR after 07-12. Segment 1's calls should be read as
exposed to this leak. Suggested harness fix: `walk_scan` and `pit_fetch` refuse to read past a
`walk_scan` hit until an `ack_fire` or an explicit `walk_read` on that date is recorded.

## Walk end: a window that has not closed in real time

The replacement-procurement ACK's window runs to 2026-10-01 (the DUE_AT_MAX_DAYS cap). This session
runs on 2026-09-29. `walk_scan` read EDGAR "through 2026-10-01", but a filing list fetched on 09-29 for
as_of 09-30 or 10-01 only returns what exists on 09-29: the two future dates were not read. The frontier
note says 10-01; the true full read is through 2026-09-29 (walk_read recorded that). So I did not fire
the ACK as a non-delivery: its silence is not yet observable. I ended the walk (every carrier read to
the present), and its two map calls (C002, segment 0; C008, segment 1; the same claim) stay open for a
later session to score after 2026-10-01. Suggested harness fix: `pit_fetch` caps as_of at the real
current date and refuses to advance the frontier past it.

Also: `edgar_doc` saves every document of one accession to the same file (`edgar_<accession>.txt`), so
reading an 8-K, its index and its exhibits overwrites the earlier text on disk. The evidence rows keep
each content hash, but only the last document's text survives. Store: the `_save` name in `pit.py`.

## Scoring notes

- **C006 (price absence) hit narrowly:** the DTE residual hedged on XLU (beta 0.891, 250 pre-clock
  sessions) from the 07-02 close to the 07-17 close was −2.95%, against a 90% band of 3.40% over 10
  sessions. Raw DTE was −3.88%, XLU −1.30%. The residual after the restart news (07-13..07-17) was
  −1.03%. It is inside the band, but a reader should not treat it as a comfortable absence.
- **The pass-through premise has a documented crack:** the Q2 earnings release (EV00056) reconciles
  an "MPSC disallowance of power supply costs previously recorded" in the six-month numbers. PSCR
  recovery is not unconditional. It did not touch this outage inside the window, but P00010/P00019
  should carry that caveat in later rounds.
- **Junction confirmation, run twice:** the first `junction_confirm` for segment 0 ran on story-proxy
  vintages that stopped at 2026-07-10 (≈5 "after" sessions) and logged two pianos (AI×rates,
  nuclear×rates). I then fetched the proxies live and re-ran: segment 0 shows no rise, and segment 1
  logs two pianos (heat×AI, heat×nuclear). The first run's rows stay on the ledger; the second run
  is the one to read. The only flagged junction (st_nuclear × st_unit_exposure on fermi-2) involves a
  constructed story, which `junction_confirm` does not test (estimated proxies only).
- **Harness version:** the round row records harness `ad0779d5dd7bd979` (admission); every tool call in
  this session returned `ab6b3fde744f0e67`. The harness source changed between admission and play;
  this session made no edits under `nomad16/`.
- **C002 and C008** (the replacement-cost map call, segments 0 and 1, the same claim) stay open until
  2026-10-01. Read through 2026-09-29, the carrier is silent on the July outage's replacement cost; if it
  stays silent, both resolve on branch `not_disclosed`, inside the thesis. Score them as one observation.

## Harness friction

- The guard treats any URL inside a Bash command as egress, so the commit trailer
  `Claude-Session: https://…` could not be written in a commit message pre-lock (the guard also refuses
  writes outside `rounds/`, so a message file can't be used). The blind-pass commit carries only
  the Co-Authored-By trailer.
