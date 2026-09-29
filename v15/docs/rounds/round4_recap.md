# Round 4 — 2026-04-14 — boiler explosion at a thermal power plant, Sakti district, Chhattisgarh

**Round id:** `01a078cb-69c8-7075-ac27-7d6c2424193c` · **Operator:** claude-fable-5-1 (cutoff 2026-06-30) · **Played:** 2026-09-06/07 over stdio from Claude Code

**Contamination flag:** Q2 (post-operator-cutoff) FAILS for this operator; the event sits inside its training window. Operator reports no specific recall; latent exposure cannot be excluded. Recorded in the event criteria and the first scorer note. Human decides whether the round stands or is voided.

**Firewall checks before lock (all refused, no ledger rows written):** evidence before lock · empty mechanism list without a reason · company name in rule text · unknown name diverted to orphans. **After scoring:** WebSearch with no open round → denied by the PreToolUse hook.

## What it was

Vedanta Ltd's Chhattisgarh Thermal Power Plant (ex-Athena) at Singhitarai, Dabhra tehsil: 2×600 MW supercritical, Unit 1 at COD since mid-2025, **Unit 2 still under construction**. Steam tube from Boiler 1 ruptured at 14:30; death toll 24 by 19 Apr; victims were staff of NGSL (NTPC-GE JV), the O&M contractor. Cause per probes: unburnt fuel accumulation and continued load ramp despite PA-fan faults. FIR names the group chairman. Unit 1 shut from 14 Apr; restart guided for end Q2 FY27 (30 Sep 2026). Vedanta Power (demerged, listed 15 Jun 2026) reported Q1 FY27 segment EBITDA −30% YoY because of it.

## Scorecard

| | |
|---|---|
| outcome_score | 0.43 |
| mechanism_score | 0.43 |
| baseline_score | 0.00 |
| edge_vs_baseline | +0.43 |
| null_called | yes (2 nulls at 0.2) |
| tradability gate | claimed fails, observed fails → **not armed** |
| unverified | 2 of 9 |

## Calls

| # | Call | Result | Note |
|---|---|---|---|
| 1 | Map: private IPP in Dabhra cluster, 300–600 MW unit, plant keeps running on other units, contract-worker casualties | **miss** | Owner, cluster, unit size, casualties right; Unit 2 not built so the whole site stopped. Falsifier fired. |
| 2 | Unit offline for months (≥3) | **hit** | Shut 14 Apr; restart guided end Sep. Baseline "weeks" wrong. |
| 3 | No attributable step in IEX day-ahead prices | **hit** | April DAM ₹5.26, +1% YoY, weather-driven; no source mentions the outage. |
| 4 | State orders inspection/audit of peer plants within 14 days | **miss** | Probes of the plant itself only; no peer-plant order found (English sources). New rule takes its first miss. |
| 5 | Owner notifies offtaker of shortfall / force majeure within 30 days | unverified | 200 MW TNPDCL PPA exists; no public notice found. |
| 6 | Magnitude ordering: physical > owner cash flow > coal > grid > equity | **hit** | Held exactly. |
| 7 | Null: no attributable equity move anywhere | **hit** (0.2) | Vedanta +1.79% / +2.19% day-after (demerger, metals); −1.39% on FIR day, under threshold. Baseline "owner down" wrong. |
| 8 | Null: fails tradability gate, no listed pure-play | **miss** (0.2) | Scored strictly: the falsifier "a listed holder with concentrated exposure emerges" fired when Vedanta Power listed by demerger on 15 Jun. Gate was right at event time; the falsifier lacked a time bound. Human may supersede. |
| 9 | No attributable move in boiler OEM equity | unverified | OEM not identifiable from retrieved sources. |

## Predicates (claimed → observed)

first traversal fails → fails (node-level: recurring fatal accidents at Chhattisgarh plants) · slack fails → fails · tradability gate fails → fails · existence floor unknown → holds · path composition unknown → fails (only a stated edge) · bounded-channel absence unknown → fails (global headline day one) · catalyst class unknown → holds (dated restart guidance).

## Library

- Validated by the ledger this round: `lib.equity_visibility_ratio` (clean hits in rounds 3 and 4, no misses). `lib.route_closure` was validated at seed.
- Misses recorded on: the new inspection-order rule (proposed at lock).
- Four candidates harvested: tradability can arrive by corporate action (time-bound your falsifiers) · a revived stranded asset runs fewer units than nameplate · the attributable equity move comes with the criminal complaint, not the accident · for contracted power plants the first public carrier is the owner's quarterly, not a force majeure letter.

## Names book and positions

Added: Vedanta Limited (VEDL), Vedanta Power Limited (VEDPOWER, listed 15 Jun 2026), the plant (parent Vedanta Power), NTPC GE Power Services, TNPDCL. Node `vlctpp_singhitarai_generation`: every holder is sign −; **no opposing listed pair**; pair gate fails for the right reason.

## Standing hypothesis opened

A listed power pure-play created by demerger while a plant is shut trades at a discount to thermal-IPP peers until the guided restart and re-rates within four weeks of confirmed restart. Arming: catalyst class (restart by 30 Sep 2026), existence floor. Disarming: date passed, falsifier. Granularity locked: weekly relative move vs a pre-named peer set.

## Programme after four rounds

4 scored · arming rate 0/4 · mechanism scores 0.40, 0.57, 1.00, 0.43 (mean 0.60) · chain verified.

## For the human to decide

1. Keep or void this round given the Q2 failure for the current operator.
2. Whether to supersede call 8 (the time-bound falsifier point) or let the strict score stand.
3. Q7 in round 3 ("thin on listed parties by design") is stored as unknown; may be a pass.
