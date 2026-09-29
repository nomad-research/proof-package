# K10 — result

*Run 2026-09-29 against the v15 ledger (chain verified, file hash equals `v15/MANIFEST.json`), per
`K10_prereg.md` and its Addendum 1. Engine: `k10.py`. Machine output: `k10_result.json`,
`k10_coverage.json`. Order of freezing, by commit: pre-registration `73fc53c`; authoring package `e3bf47c`;
engine and addendum `4e6ad20`; **forced-notice list `04dbcb4`**; **templates `9d2c2b2`** (opened only after
the notice list was committed).*

## Verdict: **dies** (0 of 6 derivable, under the guards and under the upper bound)

| | primary denominator (`clear`, read in full) | forced | switch, ≤1 unknown | switch, any |
|---|---|---|---|---|
| **guarded (the verdict)** | 6 | **0** (0.0) | 0 | 1 |
| S1 drop `knowable_from` | 6 | 0 | 3 | 6 |
| S2 accept inferred rows | 6 | 0 | 0 | 1 |
| S3 add `touched_set` rows | 6 | 0 | 0 | 6 |
| **upper bound (S1+S2+S3)** | 6 | **0** (0.0) | 3 | 6 |

X₁₀ = 0.5. The primary denominator (6) clears the floor of 5, the guarded share is below X₁₀, and so is the
upper bound, so the death does not depend on the v15 stamping gaps. The other two denominators give the same
zero: all `clear` notices (6, the same six) and `clear` plus `doubtful` (13; the one notice with no template
kind is `other:development_suspension_disclosure`). The "switch, any" column is vacuous, as the
pre-registration said: a template whose conditions are unknown yields a switch for any binding.

## Why it is zero, and why no other run could have been anything else

**Every one of the 16 templates tests at least one attribute that no v15 position row ever holds.**
`k10_coverage.json`: 15 attributes are tested and never stored (`operating_status` in 11 templates,
`contract_type` 6, `shared_access` 3, `input_share` 2, `inventory_days` 2, `listed` 2, then `fm_status`,
`fatalities`, `regulatory_hold`, `emissions_event_regime`, `emissions_release`, `casualties`, `capacity`,
`generation_outage_reporting_regime`, `war_risk_listed_area`). The whole v15 positions table holds six
attributes, 169 of its 200 rows are `sign_of_exposure`, and **only 22 rows are both `stated` and stamped
with a `knowable_from`** (18 signs, 2 shares, 2 durations). So `forced` (every condition true) is
unreachable from the v15 store under any guard setting, and the verdict would be `dies` for any
denominator. No condition was ever documented `false`; every best result is a switch.

The audit of the six primary notices (`k10_result.json`, `variants.*.audit`) shows what each missed:

| notice | best template | unknown conditions (upper bound) |
|---|---|---|
| R08-N1 incident report (an emissions-event filing) | generation-unit outage publication | `generator.operating_status`, `.capacity`, `.generation_outage_reporting_regime` |
| R13-N1..N3 regulatory decisions | fatality inquiry | `site.fatalities` (one unknown; the other two conditions are true) |
| R16-N1 restart statement | listed-owner outage guidance | `asset.operating_status`, `owner.listed`, `owner.share` |
| R17-N1 incident report | generation-unit outage publication | the same three as R08-N1 |

The guarded reading fails earlier for two of them: R16-N1 and R17-N1's issuers (a smelter owner and a cloud
operator) have no counted position rows on their node, so no template binds. Row 13 has **zero** counted
rows under the guard, because its clock is the re-run's event date (2025-07-31) and the earliest
`knowable_from` anywhere in the v15 store is 2025-11-06, so no position can pass that clock.

## What this does and doesn't show

- **It shows** the v15 stores could not have derived any of the forced notices that arrived: they recorded
  who is exposed and in which direction, and none of the standing facts (contract type, inventory, shared
  access, operating status, listing) that an obligation needs. That is §31's consequence exactly:
  *emergence is limited by the stores; invest in positions before construction.* The attribute list above,
  in order of how many templates need it, is the fetch list.
- **It does not show** that a census could not reach those facts. v15 never tried to record them. This is a
  floor for the stores as they were, not a measurement of what the world lets you document. The v16 build
  (`state/nomad16.db`) holds 25 position rows, all from R16-001, under a richer 39-entry attribute registry
  (`unit_status`, `capacity`, `reportable_event_notified`, `listed_domestic_filer`, and others). It has no
  bearing on this result, which is about rounds 8–15 of v15; K10 can be re-run on v16 rounds as they
  accumulate.
- **One relaxation was considered and cannot rescue it.** The pre-registration had no slot for trigger facts
  ("the plant is down", "a fatality occurred"), so the author had to encode them as position attributes. The
  only place a trigger is the sole unknown is R13-N1..N3 (`site.fatalities`), and that round's reveal text
  reads "an underground tunnel collapsed at a copper mine": it states no death. Everywhere else the unknowns
  are standing facts (listed, share, capacity, regime, contract type).

## Limits of this look-back (read before using the number)

1. **The denominator is small and lopsided.** Six notices: one each from rows 8, 16 and 17, and three from
   row 13. Rows 9, 10, 11 and 15 have no `clear` notice, mostly because their notice-like documents are
   dated on the event date, which the pre-registration excludes as `before_clock` (the same-day items
   are recorded in `k10_enum/`'s `excluded` lists; a same-day variant was not run and cannot change the
   verdict). The enumeration is only what the v15 operator found; the record's carrier coverage was often
   thin, so "none seen" is not "none arrived".
2. **"Read in full" is v15's own coverage field, and it is generous.** R08-N1 counts because a linked
   resolution is `adequate`, although the scorer's note says the filing itself was unreachable and it is
   known only through a wire report. R13's three notices reach the record through press, not from a primary
   document.
3. **Matching is by notice kind, which is also generous.** Two of the three row-13 notices are approvals to
   restart; the template that best fits them forces an inquiry or stop-work decision. Neither reading gets
   near a forced result.
4. **Dates the record leaves open** (row 13's suspension, R16-N2's issuer and date) were set by the
   enumerators and are marked in their notes. No verdict turns on them.
5. **One author.** The 16 templates are one cold session's reading of rounds 1–7. The author records that
   it could ground few kinds (seven gaps, including no insolvency template and no statutory-window
   regulatory-decision template) and that several thresholds (`share ≥ 5%`, `inventory_days < 14`,
   `input_share ≥ 50`) were its own choices. A template written only over the six stored attributes could
   fire, but would not make a notice unavoidable, and no such template was written. Not tested.
6. **The kind list is a pre-registration choice.** It adds three kinds to §33.3's five
   (`insolvency_or_restructuring_notice`, `corporate_disclosure_of_event_impact`, `counterparty_notice`).

## Process disclosures

- **The orchestrating session did not author.** It had read `K8_prereg.md`, `K8_result.md`,
  `K11_K12_prereg.md`, `STATE.md` and the round 8 recap, which name the stories of rounds 8–14, so it could
  not satisfy "rounds 1–7 only". It assembled the package by a timestamp filter (`k10_package.py`, which
  fails on any named entity of rounds 8–17 and redacts operator model names) and froze artefacts in the
  order above.
- **The cold author** is a fresh subagent that reports it opened only the package, declared a knowledge
  cutoff of June 2026 (before every round 8–15 event), and used no event-specific knowledge. That is its
  self-report and a procedure, not a wall. The templates are committed verbatim (sha256
  `e4389855c6f6c5b36c091ed0b975ee8c0e69c41ba993a7aee8723943adedb7fc`).
- **The enumerators** are four fresh subagents that never saw the templates (which did not yet exist).
  One (rows 8–9) read `K10_prereg.md` lines 48–107, a few lines past the section it was allowed; the
  excess is the start of the derivability rules and holds no template content.
- **Residual leakage, as pre-registered:** the spec extracts in the package were written after round 15.
  A reader who thinks they leak should discount a survival, not this death.
- **Engine.** `python lookbacks/k10.py --selftest` passes; `engine_stats` is empty (no unit mismatches, no
  bindings over the bound). The audit above was read for artefacts before the verdict was accepted: none.

## The decision point

§30.2 step 14 stops construction only if **K8 and K10 both die**. K10 dies here. K8 came back `unreadable`
(`K8_result.md`), not dead, so the joint condition is not met on the record as it stands. K8 and K10 fail
for the same reason (the v15 store is unstamped and thin), so the programme owner decides whether K8's
unguarded sensitivity, which pointed the other way, is enough to proceed. This file doesn't choose the
shape (§11).

## What would make K10 informative

Record the fetch list on real nodes at lock (a census of `operating_status`, `contract_type`,
`shared_access`, `listed`, `inventory_days`, `input_share` first), stamp every row with `knowable_from`
and `confidence`, and re-run `k10.py` unchanged on later rounds with the frozen templates. For the v15
record, a blind back-fill of `knowable_from` and `confidence` (the K8 remedy) would move only the
guarded reading toward the upper bound; the upper bound is already zero.
