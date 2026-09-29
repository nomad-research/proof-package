# Round 7 recap: July 21, 2026, a fire at a polyethylene plant in Sasolburg, South Africa

Round id `01a07b19-69fb-75dc-9802-fac853e0f859`. Clean (event after the operator cutoff, 48 days old at intake). First-qualifier selection; the selector's rejection list was not passed to intake, so `rejected_before` is 0 with that noted under Q9. Criteria pass (Q1 unknown, nothing on the node in our ledger). Node `sasolburg_polyethylene_output`, kind `fire`. First round played under the v7 protocol: reveal context, touched set, one claim per row, decomposed duration call, per-leg predicate checks, `meta` one-trade statement, second scorer with rule text.

## What the harness showed at reveal
Nothing. No holders, no node facts, no neighbours on the node. Eleven rules matched the kind tokens, led by `lib.equity_visibility_ratio` (validated, 2.26 going in). The touched set was built from the operator's own prior: seven rows, degrees 0 to 3, two candidate operators at degree 0 (Safripol HDPE; Sasol Polymers LDPE at Sasol One).

## Calls and outcomes (operator / second scorer)

| # | Call | Claim | Operator | Second | Notes |
|---|------|-------|----------|--------|-------|
| 0 | map | plant is Safripol's HDPE, not Sasol's | miss / n.a. | miss / n.a. | It was Sasol's Poly 3 (LDPE/LLDPE, Midland site). Baseline (the larger operator on site) was right. |
| 1 | sign 0, Sasol equity | no attributable move vs Top40, 3 sessions | hit / right | hit / right | SOL −2.4, +11.9, −3.9 pts vs Top40 on 22–24 Jul, all attributed to oil, the FY26 metrics released the morning of the fire, and the PIC stake. Nobody mentions the fire. Baseline "dips on the day" also hit on its letter. |
| 2 | sign −, KAP | KAP underperforms after Safripol is named | untestable / unknown | untestable / right | **Dispute (mechanism)**: condition never arose. Second scorer credits the victim-overweight rule for operating on Sasol instead. |
| 3 | lag_band weeks, decomposed (5 factors) | plant back within weeks | unverified (derived) / unknown | unverified (derived) / unknown | Binding factor (damage extent) unobserved; only the ethylene-feed factor scored (days). Sasol's 1 Sep results are silent on Poly 3. Coverage thin. |
| 4 | sign +, force majeure within 14 days | FM declared | miss / unknown | miss / wrong | **Dispute (mechanism)**: no FM found anywhere (ICIS paywalled). Operator: the rule does not predict FM occurrence, so it neither operated nor failed. Second: the first carrier was a newspaper, so the fast-carrier rule did not operate. |
| 5 | sign 0, local PE prices | no attributable rise above import parity in 4 weeks | hit / unknown | hit / unknown | Claim of absence under thin coverage, both scorers flag it. Baseline differs (miss vs unverified), not a dispute. |
| 6 | meta, one-trade | short KAP from naming day | untestable / unknown | untestable / unknown | Naming day never came. Baseline "no trade" hit. D6 comparison: legs 0 armed, trade untestable. |

Scorecard (operator, before the human rules the disputes): outcome 0.40, mechanism 0.50, baseline 0.60, edge −0.10, map 0.0, misreads 0, untestable 2/7, unverified 1/7. Zero legs armed of four checked; tradability gate fails on every listed leg (Poly 3 is one line of a 250 kt/y site inside R61bn of group EBITDA).

## What moved in the library
- `lib.equity_visibility_ratio` 2.26 → 2.86, still validated (8 hits, 0 misses).
- `lib.cut_into_glut_silent` 1.2 → 1.62 and **crossed to validated** on call 5. Flag: that hit is a claim of absence under thin coverage with mechanism unknown, quality 0.42. Worth a human look before the rule is treated as validated.
- `lib.force_majeure_fast_carrier` took a 0.7 debit on call 4 (1.2 → −0.4 in the operator view); the pending dispute suspends it (C1), so the rebuilt weight is back at 0.3 until you rule. The operator's own view is that the debit belongs to the citation, which is the existing operator rule "the operator attaches a rule to a call the rule does not carry".
- `lib.visible_victim_overweight` 0.18 → 0.78.
- Two disputes pending on this round; the human breaks each with `nomad_resolution_supersede` scorer `human`. Scorer bias over clean rounds now: self more lenient 8, more strict 2, of 16 compared. Most of the "lenient" count is second-scorer `unknown` where the operator said `right`.

## Basket
Seven legs on one node, three sign −, four sign 0 after the post-lock corrections (Safripol and KAP flipped to 0 once the plant was named as Sasol's). Twenty-one shared-node pairs, none opposing. No leg armed, none dated. The one-trade statement was never live.

## Lessons
- The map call was a coin flip dressed as a lean. The bare event wording carried no operator signal and the baseline (bigger operator on site) was the better prior. Two downstream rows (KAP, one-trade) died with it. Next time: make conditional calls on both branches or make none.
- Coverage on a single-line polymer outage in South Africa is one newspaper article. Restart, force majeure and local pricing all sit behind ICIS. Three of seven calls are unscoreable on the carriers named, which is a Q7 (checkable carrier) failure that intake marked unknown and should have marked fail for those carriers.
- The FY26 metrics release landing the same morning as the fire is a tide the operator could not have known at lock; the tide note records it.
- v7 mechanics all held under live use: touched set enforced, single-claim rows accepted, factors required and derived, per-leg predicate checks written, blind view carried rule text and reveal context, C1 suspended the disputed debit.
