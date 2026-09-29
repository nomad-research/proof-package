# R16-001 — blind pass (before any fetch)

*Operator: claude-opus-5-5, cold session session_01E4zNsm1p4SLeh6t7vePZFZ. Written from the reveal
and training memory only (cutoff 2026-06-30). Nothing below is a fetched fact; every noun here is a
thing to fetch and document before it may count. Memory may propose and never support (§5, §6).*

## Event line

Fermi 2 automatic reactor scram, 2026-07-03. Node `fermi-2`, a power reactor. Tagged `weather`
(a manual scram on 2026-05-19 is in the NRC registry, Q1b fail). Round class `learning`.

## What I think the node is (to verify)

- A single-unit boiling-water reactor in southeast Michigan, roughly 1.1–1.2 GWe, on the western
  shore of Lake Erie. Licensee and, I believe, sole owner: the regulated electric subsidiary of a
  listed Detroit-area utility holding company (DTE Electric / DTE Energy, ticker DTE). Operates in
  the MISO market.
- The owner is a vertically integrated, rate-regulated utility with an obligation to serve its
  retail load. Fuel and purchased-power costs pass to customers through a state cost-recovery
  mechanism (PSCR in Michigan), so replacement power for an unplanned outage is largely a
  customer cost, not a shareholder cost, subject to prudence review.
- The unit is one asset among a fleet of roughly 11 GW owned generation. Its share of the parent's
  earnings is small; I don't expect the scram to be material under the current-report test
  (impact share ≥ 5%).

## Pieces I expect (effects at holders), all degrees

- d0 `fermi-2` (the asset): availability loss; restart status published daily by NRC; a written
  licensee event report (60-day window under the reporting regulation) that attributes a cause.
- d1 DTE Electric (owner/licensee, unlisted subsidiary, SEC filer through its parent and in its own
  right for debt): replacement energy purchased or self-supplied from other units; cost passed
  through the recovery clause; possible prudence exposure only if the outage runs long.
- d1 DTE Energy (listed parent): earnings effect small; visibility below the tide (utilities beta,
  rates) by `lib.equity_visibility`; recurring scrams priced as weather (`lib.recurring_weather`).
- d1 MISO / the Michigan zone (market): a ~1.1 GW baseload hole; I expect slack in July to absorb it
  unless it coincides with a heat event. `lib.cut_into_glut_silent` and
  `lib.availability_no_constraint_price` both lean toward silence in any constraint price.
- d2 retail customers (aggregate): pay the replacement cost through the clause, later.
- d2 regulator (state commission): prudence review only for a long outage (authority, no stake).
- d2 other MISO generators in the zone: marginally better dispatch while the unit is down; below band.
- Fuel supplier / vendors: nothing forced by a short scram.

## Forced notices I expect

1. Unit status in the NRC daily status report every day (restart or still down) — forced, carrier
   `nrc_status`.
2. Written event report within the statutory window (≈ 60 days → about 2026-09-01) — forced,
   carrier: LER in ADAMS (`not_covered` here; only the event notification feed and Wayback).
3. Replacement procurement — an obligation to serve plus a large unit offline forces buying or
   self-supplying replacement energy; the disclosure of its cost is not forced on any clock I
   know of, and may appear only in a quarterly filing.
4. A current report (8-K) — I expect **no** current report, since the event should fall below the
   materiality threshold.

## First reading of outcomes

- Restart: a scram on a unit with a recent prior scram. My memory prior (a placeholder, not a fact):
  most automatic scrams without major equipment damage restart within days to two weeks; a
  turbine/generator or main transformer failure pushes it to weeks or months. Unknown until the
  event notification text is readable (it is public only on 2026-07-06, after the clock).
- Cause in the written report: equipment is the most common attribution for automatic scrams.
- Price: I expect nothing visible in DTE against the utilities tide. The edge, if any, is not in
  the equity; this is likely a spectacle in the sense of `lib.no_pure_play_spectacle` (no listed
  pure-play on the unit).

## What would kill this reading

- The owner not being sole owner (co-owners would add holders and an allocation question).
- A heat wave in MISO in early July (no slack → a constraint price could move).
- A long outage (major component) making the event material to the parent.
