# Nomad — Spec v2

**Supersedes `nomad_gate_spec.md`, `nomad_gate_spec_amendment_1.md`, and `nomad_operating_procedure_v1.md`. Those are archived, not authoritative.**

Last revised 2026-08-18, after five tests.

---

## 0. What this system claims

Some actors are **forced to transact** by a rule that removes discretion — mandate, covenant, margin agreement, index methodology, regulatory deadline. Forced transactions are **price-insensitive**: the actor completes them at a materially worse price rather than not completing them.

The claimed edge is **enumeration**: identifying *where that forced capital must land* before others connect it. Not estimation — not predicting probabilities over a known outcome set, but specifying the set.

**Status: unproven.** Five tests, one interpretable result, and it was about LETFs.

---

## 1. WHAT IS CLOSED — do not re-open

**Test A (LETF rebalancing) is closed permanently**, in both liquid and illiquid regimes, by its own pre-registered stopping rule. Both conditions fired: top-decile coefficient insignificant with wrong sign, and no monotone gradient across deciles. No third regime.

**Scope of that closure:** LETF rebalancing at the magnitudes LETFs generate does not move prices. See §3 Q3 — this is a much narrower finding than it first appeared.

---

## 2. THE MAGNITUDE CORRECTION

Carried in every prior artefact and wrong in all of them.

`82.9× ADV` is the **multiplier** `M/ADV`. Realised flow is `M · r / ADV` — the multiplier times the day's return.

**A-2's top decile averaged 0.80 days of ADV of realised flow.**

So A-2 established that **~0.8 days of ADV produces no measurable effect.** It says nothing about 5×, 10×, or 20× ADV, which is the regime fire sales and forced liquidations occupy.

Any screen inheriting the old figure sets a bar roughly 100× too high and rejects events A-2 never tested.

---

## 3. EVENT QUALIFICATION — Q1 to Q8

All eight must hold. Q7 and Q8 were added mid-run in the blind run and are disclosed as post-hoc; both are exclude-only.

**Q1 — Citable forcing.** A specific, retrievable document removes discretion from a named actor.

**Q2 — Price insensitivity.** The actor would complete the transaction at a materially worse price. Test: does the rule specify *what* and *when* but not *at what price*?

**Q3 — Magnitude floor.** *(CORRECTED)* Forced flow must exceed **0.8 days of destination ADV**, which is the level A-2 showed produces nothing. A-2 gives no information about where above 0.8 the threshold sits, so this is a floor and not a target. Prefer events at multiples of ADV.

**Q4 — Coverage thinness.** Destination candidates have low analyst coverage or are off-benchmark. Liquid, well-covered destinations have an abundant other side and no premium.

**Q5 — Resolved window.** For retrospective runs, the transmission window has closed. For prospective runs, it has not opened — see §7.

**Q6 — Post-cutoff.** Fire date after the operator's training cutoff.

**Q7 — Enumeration content.** *(post-hoc, exclude-only)* The eligible destination set must **not** be published in advance by the forcing party, an index provider, or any public list dated before the fire date. If destinations are handed to you, the event tests transmission, not enumeration. This is why index reconstitution does not qualify.

**Q8 — Retrievable forcing document.** *(post-hoc, exclude-only)* The document naming the rule that removes discretion must be publicly retrievable at the fire date. Private contracts — prime brokerage margin agreements, LPAs, ISDA CSAs, bilateral covenants — do not qualify however certain the forcing is.

### 3.1 Q8 is under review — decide before the next candidate

Q7 and Q8 together may leave the addressable universe nearly empty. Candidate relaxation: require the forcing be **publicly evidenced with the rule class identifiable**, rather than the specific contract retrievable. An 8-K disclosing a covenant breach, a fund announcing liquidation, a downgrade against publicly documented mandate rules.

**Decide this against no candidate.** If Q8 relaxes because it is too strict, that is a standard. If it relaxes because it excluded an event you wanted, that is fitting. Only timing distinguishes them.

---

## 4. AMENDMENT RULE — replaces the raw amendment count

> **Amendments to VALIDITY are learning. Amendments to THRESHOLDS are fitting.**

A validity amendment changes *what counts as a valid test* (this event cannot test enumeration; this forcing cannot be documented). A threshold amendment changes *what counts as a passing result*.

**Validity amendments: acceptable, disclose and date. Threshold amendments: not acceptable, at any count.**

Every amendment must additionally be **exclude-only** — capable of removing a candidate or a result, never of manufacturing one.

---

## 5. THE FORCING EDGE — executable format

Every field filled or the edge is **quarantined**. Not softened, not widened, not approximated.

```
EDGE <id>
  trigger_event:         what happened, with date
  trigger_document:      URL + clause quoted verbatim
  constrained_actor:     named entity, or named class with membership rule
  binding_rule:          the rule that removes discretion, stated plainly
  rule_document:         URL + clause quoted verbatim
  forced_action:         buy | sell — what instrument or asset class
  magnitude:             estimate, in DAYS OF DESTINATION ADV
  magnitude_basis:       derivation, from which figures in which document
  eligible_destinations: the set capital may land in, per the rule
  destination_basis:     what constrains the set — eligibility rules, not inference
  expected_window:       dates
  window_basis:          deadline, settlement cycle, or reporting date — not a guess
```

**Membership:** a node belongs iff `trigger → condition → rule binds for named actor → eligible destination set` can be written with every link resolving to a retrieved document and a located clause. **Correlation is not membership.** "Also affected" is not an edge.

**Termination:** stop when the next edge cannot be written to this standard. Exhaustion, not a threshold.

**Verification:** every `_document` field fetched and the clause located. Assertion that a rule exists is not evidence it exists. Confidence is not verification.

**Report the quarantine rate.** High is informative. Quarantine exceeding verified fires a stop condition.

---

## 6. PREDICTION AND SCORING

Written to `prediction.md`, committed, hashed **before any outcome data is touched.**

```
PREDICTION <event_id>
  edges:              verified edge ids
  quarantined:        count + reasons
  destination_set:    ranked specific instruments
  direction:          per instrument
  window:             dates, per instrument
  magnitude_class:    order of magnitude of expected move
  control_set:        matched — same universe, size and liquidity band,
                      NOT enumerated, matched on fire-date observables only
  confidence:         a stated base rate, or the word "unknown". Not a score
  falsifier:          what observation makes this wrong. Written before scoring
```

**Scoring — four numbers, reported separately, never blended:**

- **S1 Destination recall** — did realised flow land in the set? Binary. Primary
- **S2 Return spread** — enumerated vs matched control, gross and net
- **S3 Direction accuracy** — per instrument
- **S4 Window accuracy** — did the move occur inside the stated window?

| Recall | Spread | Reading |
|---|---|---|
| High | Positive | Map right, market slow. Thesis working |
| **High** | **Zero** | **Map right, already priced. Enumeration works, edge does not** |
| Low | Positive | Luck. Do not update |
| Low | Zero | Map wrong. Framework did not operate |

The high-recall/zero-spread cell is what the decay literature predicts and must stay visible.

---

## 7. BLIND RUN PROTOCOL

**Retrospective:** fire date after the operator's training cutoff, window closed. Contamination is a capability constraint, not a promise.

**Prospective (stronger):** seal before the window opens. Nobody knows the outcome, including the analyst, which closes the selection channel entirely.

### 7.1 Firewall — proven configuration

Structural, not procedural:
- DNS blackhole on search engines, aggregators, and financial media — **both A and AAAA records.** IPv4-only leaks over IPv6
- Market-data wrapper truncating every series to the fire date **before anything reaches disk**
- Document wrapper enforcing a filing-date ceiling in code
- Fail-closed guard on any network tool without an extractable allowlisted URL

**Verify by checking resolution, not by trusting the write.** Where a tool cannot be blocked structurally (server-side search), declare the commitment as procedural and make it auditable in the transcript.

**A firewall that never blocks its own operator is not evidence it works.**

### 7.2 Selection

The analyst knows outcomes; the operator does not. This puts contamination on **selection**. Fix a date `D`, screen forward by Q1–Q8, take the **first qualifier**. Log every rejection with the criterion it failed.

If the selector has outcome exposure, disclose it and withhold specifics; apply at scoring as a coincidence flag.

### 7.3 Ordering

**Commit the quarantine reasoning before `prediction.md` exists.** This timestamps the standard independently of any map, so it cannot have been reverse-engineered. Default for every run.

### 7.4 Stop conditions

**Not operable:** no event satisfies Q1–Q8; or the first qualifier maps to zero verified edges; or quarantine rate exceeds verified rate.

**Operable, edge absent:** recall high and spread zero across events run.

**Failure of an event is recorded as a failure of that event — not a licence to shop for a better one.**

---

## 8. STANDING METHODOLOGY

- **Pre-registration** committed before analysis; amendments appended and dated, never edited in place
- **Every** configuration evaluated logged to `config_log.jsonl`, including abandoned ones. That is the multiple-testing denominator
- **t > 2.78** (Harvey-Liu-Zhu). Deflated Sharpe against the cumulative logged count
- **Point-in-time discipline**: first prints, archive-measured release dates, no restated data. Where survivorship-free data is unavailable, say so and treat results as upward-biased
- **Gross and net**, always. Correwin-Schultz for illiquid names only — it returns 47bp round-trip on SPY, wrong by two orders of magnitude
- **Validity check before interpretation.** If the instrument cannot detect a reaction to genuinely new information, its null on stale information carries none

---

## 9. OPEN WORK, IN ORDER

1. **Rates re-run.** Every macro block used SPY, whose day is dominated by everything except the release. Re-run existing machinery against TLT/IEF or 2-year yields. One day; converts four unreadable blocks to readable; the only path to a clean stop
2. **Propagate the Q3 correction** to every downstream artefact
3. **Intraday index data to 2010** for Test A's untested impact leg
4. **Q8 relaxation decision**, cold, against no candidate
5. **Next blind run** with Q1–Q8 applied from the outset

---

## 10. WHAT IS NOT ESTABLISHED

- **The stale-information question is unanswered, not answered negatively.** Three of four blocks failed validity. Treating an unreadable result as a negative is the easiest available mistake
- **No decay half-life was measured.** The 12–36 month clock is unsupported, not refuted, and demonstrably untested
- **Test C never ran.** Infrastructure exists and is tested
- **Nothing so far is statistical evidence against the thesis.** Four tests measured assumptions underneath the framework; one measured the framework and stalled on document class
