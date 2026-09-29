# K8 — pre-registration (written before any K8 number was computed)

*2026-09-29, the v16 build session. Spec v16 §31 K8: "On the nodes of rounds 1–15 that carry a
high-stake holder, at least a share X₈ carry listed instruments (listed before the event) on both
sides of the node, or one listed holder with options." X₈ = 0.5 (provisional_unratified).*

## Data and guards
- Source: the v15 ledger (`nomad_harness.db`), chain verified by v15's own `verify_chain` (ok, no break).
- Nodes of a round: the distinct `touched_set.node` values for that round.
- Positions: a `positions` row counts for a round only if its `recorded_at` precedes the round's
  first transition into `locked` (`round_transitions`), and its `knowable_from` is on or before the
  round's `event_date` (§31 guards). Superseded rows are dropped among the counted ones.
- "Listed before the event": v15 records `holders.listed` with no listing date. Listed status is taken as
  recorded (September 2026). **This guard is unenforceable here and flagged.**
- Voided rounds, and the round 12 re-run's contaminated original, are excluded. Clean and learning rounds
  are reported separately.

## Definitions
- **Side of a holder on a node:** its counted `sign_of_exposure` position (`+`, `-`, `0`).
- **Both sides:** at least one listed holder (`listed = 1` with a ticker) at `+`, and at least one at `-`,
  on the same node. **Or options:** at least one listed holder with `options_listed = 1` and a non-zero side.
- **High-stake holder, K8-strict:** a holder whose v15 risk vector on that round and node carries
  `stake ≥ 1.0` (the v15 appetite). Expected to qualify almost no nodes (stake is blank on ~96% of legs);
  reported for completeness.
- **High-stake holder, K8-proxy:** a holder at degree ≤ 1 in `touched_set` with a counted non-zero side.
  This is a proxy for "high stake", because stake itself is almost never computable in v15. It is
  reported as a proxy and **K8's verdict is read from the proxy only with that caveat**.

## Verdict rule
Share = qualifying nodes that have both sides or options ÷ qualifying nodes. K8 **dies** if share < X₈
(0.5), under the proxy. K8-strict is reported with its denominator; with fewer than 5 qualifying nodes it
is `unreadable`.
