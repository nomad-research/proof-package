# Edge attempt log (§3, §6) — every edge attempted, including quarantined

Fire date 2026-07-30. Every `_document` field below was fetched, not recalled.
Filings opened are in `firewall/fetch_log.jsonl`; all have filing dates before
the fire date, enforced in code by `firewall/edgar.py`.

## Filings opened (all pre-fire, verified by the wrapper)

| Form | Filed | Period | What it establishes |
|---|---|---|---|
| 13F-HR | 2026-05-18 | 2026-03-31 | 42 line items, **$13.68bn**, top-10 = 72.7% |
| SCHEDULE 13D | 2025-08-19 | — | Core Scientific **5.8%** |
| SCHEDULE 13D/A | 2025-10-14 | — | Core Scientific **9.4%**, 28,756,478 sh |
| SCHEDULE 13G | 2026-05-27 | event 05/19 | **Nebius (NBIS) 5.63%**, 12,410,060 sh — *not in the 13F* |
| SCHEDULE 13G | 2026-06-29 | event 06/22 | **SharonAI (SHAZ)**, 19.99%-capped |
| Form 3 | 2026-06-29 | 2026-06-22 | SA becomes a Section 16 insider of SHAZ |
| Form 4 | 2026-07-02 | 2026-06-30 | SA **exercises** 3.7m warrants — still *acquiring* on 06/30 |

**Blocked and never opened** (post-fire, refused by `edgar.py`): 13F-HR filed
2026-08-14 (period 2026-06-30); SCHEDULE 13D/A filed 2026-08-04; SCHEDULE 13G/A
filed 2026-08-14. The first of these is precisely the document that would reveal
the answer.

---

## EDGE-1 — the forcing itself — **QUARANTINED**

```
EDGE 1
  trigger_event:        Situational Awareness LP forced to liquidate its entire
                        public equity book; complete at 2026-07-30
  trigger_document:     *** CANNOT BE FILLED ***
  constrained_actor:    Situational Awareness LP / Situational Awareness Partners
                        LP (the Fund) / SAF AI GP LP  [named, verified: Form 4
                        explanatory note 1, filed 2026-07-02]
  binding_rule:         *** CANNOT BE FILLED ***
  rule_document:        *** CANNOT BE FILLED ***
  forced_action:        sell — US-listed equities and one ETF
  magnitude:            ~$13.7bn at 2026-03-31 marks; larger by 2026-07-30
  magnitude_basis:      13F-HR 2026-03-31 information table, summed
  eligible_destinations: n/a — a liquidation returns capital to LPs as cash
  expected_window:      *** cannot be derived without a deadline document ***
  window_basis:         *** CANNOT BE FILLED ***
```

**Field that failed: `trigger_document`, `binding_rule`, `rule_document`,
`window_basis`.**

The 13F-HR is a **holdings disclosure**. It contains no clause that removes
discretion from anyone; it reports what was held on a date. It is an inventory,
not a forcing document. §3.3 is explicit — assertion that a rule exists is not
evidence a rule exists.

For a private fund the forcing document would be one of: the limited partnership
agreement (redemption terms, key-man, gates), a redemption notice, a prime
brokerage margin agreement, or a regulatory order. **None of the first three is
public.** No regulatory order appears in the filer's EDGAR history. The forced
liquidation may well be real — it is simply **not documentable from public
sources**, which is the condition §3.3 quarantines on regardless of operator
confidence.

## EDGE-2 — SMH in-kind redemption chain — **QUARANTINED**

The largest single position is $2.05bn of VanEck Semiconductor ETF (SMH), 14.9%
of the book. Chain attempted: SA sells SMH → net redemption → authorised
participant redeems in kind per the ETF's prospectus → AP receives the
semiconductor basket → AP sells the components.

**Field that failed: `binding_rule` at the third link.** The in-kind redemption
mechanic is documentable, and the basket is published daily. But an authorised
participant is **not forced** to sell what it receives — it may hold, hedge, or
warehouse. There is no rule removing its discretion. Per §3.1 that link is
correlation, not membership, and the edge cannot be written to standard. It is
also downstream of EDGE-1, which is itself quarantined.

## EDGE-3 — Rule 144 volume limit on SHAZ — **PARTIAL, quarantined as an edge**

This is the one genuinely citable rule in the whole event. SA is a >10% holder
and Section 16 insider of SharonAI (Form 3, 2026-06-29; Form 4, 2026-07-02), and
therefore an affiliate. Rule 144(e) caps an affiliate's sales in any three-month
period at the greater of 1% of shares outstanding or average weekly volume over
the preceding four weeks.

**Field that failed: it constrains the seller, it does not create a destination
set.** It bears on `window_basis` — it means the SHAZ stake *cannot* be
liquidated quickly through open-market sales — but it forces no one to transact
in any instrument. It is logged because it is the only retrievable rule found,
and because it is evidence *against* a fast-transmission window on that name.

---

## Unverified candidates — intuition that ran ahead of documentation

Per the operator's pre-resolved judgement call: destinations I am confident about
but cannot tie to an eligibility rule are **not in the set** and are logged here
so the gap between intuition and documentation is visible.

- Second-order AI-infrastructure names not in any SA filing (power, cooling,
  interconnect, HBM supply chain). §3.1 forbids these outright: "This company is
  also affected" is not an edge. I can name no rule forcing anyone to transact in
  them. **Count: unbounded — which is exactly why the rule exists.**
- Peers of the miner-to-AI-datacentre cohort (the sector SA is concentrated in)
  not held by SA. Same failure.

## Quarantine rate

**Edges attempted: 3. Verified: 0. Quarantined: 3. Quarantine rate: 100%.**

§7: *"the quarantine rate exceeds the verified rate, meaning most claimed rules
cannot be retrieved"* → **stop condition met**, and separately §7's *"the first
qualifying event cannot be mapped to at least one fully-verified edge."*
