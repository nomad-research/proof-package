# V1: structural versus cross-entity hedges (post-hoc, descriptive)

Written after the scores were seen, so it is not part of the registered bar and changes no verdict. Labels are in `v1_structural.py` with a reason per round; the numbers are `v1_structural_report.json`.

S = a hedge leg is the same underlying as the primary (same Fed meeting in a multi-meeting ladder, same election, a necessary condition). Its floor lift is arithmetic.
X = every hedge leg is a different underlying; the lift exists only if the session's causal claim holds.

| subset | rounds | primary lost | mean floor lift | claims in set (B1) | mean C-D (90% CI) |
|---|---|---|---|---|---|
| all | 17 | 7 | 34.9 (median 19.9) | 0.88 | +3.9 (-2.7, +10.7) |
| S only | 6 | 4 | 5.5 (median 1.3) | 1.00 | +2.6 (0.0, +7.6) |
| X only | 11 | 3 | 50.9 (median 38.7) | 0.82 | +4.6 (-5.6, +14.8) |

What it says:
1. The structural rounds are a minority and carry little lift (three of six are exactly 0), so they do not inflate the headline. My earlier worry that they did was overstated.
2. The lift lives in the cross-entity rounds, and those are exactly where the claims can fail. Both rounds whose realised outcome fell outside the declared reachable set are X rounds (624096 and 674379, UK ministerial-office partitions: the claim "if the Foreign/Defence Secretary changes, the Home Secretary changes too" did not hold). 674379 is also the +205 outlier, so its floor lift was never real.
3. On X rounds only, C-D is not distinguishable from zero and the primary lost in just 3 of 11, so there is almost no loss-case evidence.
4. The BTC/ETH pair (655630, 655631) shows the price of a hedge that is never needed: large floor lift, realised C-D of -11 and -16.
