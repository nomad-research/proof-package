# Round 6 — 2026-07-14 — hydrofluoric-acid container leak at Deurganck Dock, Port of Antwerp-Bruges

**Round id:** `01a07ae0-5349-775b-806d-e58237e1bea8` · **Class:** clean (Q2 computed pass; window 2026-07-01 to 2026-08-10) · **Operator:** claude-fable-5-1 · **Played:** 2026-09-07 over stdio from Claude Code (new server) · **Scored:** self, then a blind second scorer (B2), 7 disputes over 9 calls awaiting the human.

**Same node as round 3.** The ledger already held the dock's 2026 history (March strike, April spill, June pilots, "a toxic leak in July"), so first traversal was claimed *fails* at the node from stored facts before lock. Hormuz blockade reinstated on the event day; tide note recorded.

## What it was

Evening of 14 July: a tank container of hydrogen fluoride developed a ~10 cm hole during loading aboard **MSC Mia Summer II** at MPET (possibly a twistlock). Toxic vapour cloud; **entire Deurganck Dock and the Kieldrecht lock closed**, waterway traffic in the area suspended, both terminals (MPET and DP World's Antwerp Gateway) shut. **186 assessed, 28 hospitalised, one in intensive care, no fatalities.** Antwerp Gateway resumed 15 July afternoon; MPET quay 1718 at 22:00 on 15 July; MPET declared safe 17 July 14:00; rail 20 July; **quay 1742 (north berth) still out ten days later with three damaged STS cranes and ~90 staff cars written off.** Ghent labour prosecutor opened a criminal investigation. WCI fell 2% on 16 July with no Antwerp mention; one trade headline said the leak "deepens congestion".

## Scorecard (operator, self)

| | |
|---|---|
| outcome_score | 0.73 |
| mechanism_score | 0.69 |
| baseline_score | 0.00 |
| map_score | 1.00 (falsifier terms) |
| misreads | 2 |
| tradability gate | claimed fails, observed fails → **not armed** |

## Calls and the two scorings

| # | Call | Operator | Second scorer | Dispute |
|---|---|---|---|---|
| 1 | Map: tank container on a vessel at MPET, part of terminal closed, contained in a day, no fatalities, other terminals open | **hit** (falsifier did not fire; scale badly under-called) | **miss** (claim as stated failed: whole dock, lock, waterways, other terminal closed) | outcome |
| 2 | Dock and terminal fully operational within 3 days | miss, mechanism right (misread) | miss, mechanism **wrong** | mechanism |
| 3 | No attributable step in indices or congestion commentary | miss, right (commentary clause fired) | miss, right | agree |
| 4 | No carrier omits Antwerp citing the leak within 7 days | **hit** | **unverified** (Hapag update unreachable, no Maersk advisory found) | outcome |
| 5 | Magnitude ordering physical > throughput > schedules > indices > equity | hit, right | hit, **unknown** | mechanism |
| 6 | Null: no attributable equity move in 3 sessions | hit | hit | agree |
| 7 | Null: fails tradability gate | **hit** | **unverified, coverage none** (positions store not in the evidence) | outcome |
| 8 | No regulatory order within 30 days; liability on shipper/packer | **hit** (order leg) | **unverified** (liability leg undecided; investigation points at employer) | outcome |
| 9 | No force majeure citing the leak | hit, unknown (no-mechanism) | hit, **right** | mechanism |

## My recommendation on each dispute (yours to decide)

1. **Map (1):** take the second scorer's **miss**. The falsifier did not fire, but the claim had three extent statements and two were false. The harvested rule below says why. If you take it, map_score goes to 0 and outcome to 0.59.
2. **Lag mechanism (2):** keep **right**. The cited rule (duration lives one node smaller) is precisely what happened; I failed to apply it. Under A13 that is a misread charged to me, not a debit to the rule. The second scorer read "mechanism" as the claim's implied mechanism, not the cited rule.
3. **Carriers (4):** take **unverified, thin**. I gave benefit of the doubt on a gap the evidence record itself flags.
4. **Magnitude mechanism (5):** keep **right** or accept **unknown**; low stakes. The ordering held and the equity-visibility rule operated. I lean keep.
5. **Tradability null (7):** keep **hit**, and fix the harness (done below): the positions store was read before lock and is in the ledger, but the blind view did not show it, so the second scorer could not see it. This is a view defect, not a scoring one.
6. **Regulatory (8):** take **unverified**. The liability half of my own claim is unsupported; the investigation's target is unknown.
7. **Chemical notices mechanism (9):** accept **right**; harmless either way since no rule was cited.

Breaking a dispute is one `nomad_resolution_supersede` with `scorer='human'` per call. If you take all six of my recommendations, the round lands at roughly outcome 0.46, mechanism 0.47.

## Predicates (claimed → observed)

first traversal event unknown → **fails** (June pilots inside 30 days) · node fails → fails (from the ledger) · slack fails → fails · tradability fails → fails · existence floor unknown → holds · path composition unknown → fails · bounded channel unknown → fails · catalyst unknown → holds (dated reopening statements).

## Library

- **Validated:** `lib.equity_visibility_ratio` (positive hits in both clean rounds, no misses, weight 1.86). First validation under the propagated weights.
- Harvested: a toxic release closes the whole shared space, not the failed asset · knowing the rule is not applying it (operator) · narrative and price diverge after a small shock; a price falsifier must name the price series only (operator).

## Names book, positions, node facts

DP World and Antwerp Gateway added. Node `deurganck_dock_container_handling`: seven holders, all sign −, no pair; MPET duration "3 days terminal; 10+ days north berth". Two node facts (the outage timeline; the port's H1 losses).

## Housekeeping

- Evidence batch was rejected once for three over-length excerpts and wrote nothing, as designed; resubmitted trimmed.
- Paywalled or blocked: Loadstar, Flows, Sourcing Journal body, Hapag-Lloyd updates, the port's crisis page. The north-berth reopening date is the natural B4 target for this node.

## Programme after six

Clean: 2 scored, arming 0/2, mechanism 0.32 and 0.69 (mean 0.51 before disputes). All: 6 scored, arming 0/6. Chain verified across 20 ledgers.
