# V1 pilot — one closed pair, builder-authored (nothing here counts toward V1)

*2026-09-30. Script `pilot_v1.py`, output `pilot_v1_output.txt`. Purpose: test the arithmetic and the data path and find gaps in `V1_prereg.md` before any round exists.*

**Setup.** Primary: Fed April 2026 decision (event 75478, exact partition of 4), long YES "25 bps decrease". Hedge menu: the April Bitcoin "hit" ladder (event 334550, 23 markets: 11 reach, 12 dip, touch contracts). Lock 2026-04-08 12:00 UTC. Thesis, written before prices or outcomes were fetched: the primary fails if the Fed does not cut; if it does not cut, Bitcoin touches a level below its lock-time median dip level; a 50+ bp cut is not reachable. **Disclosure:** the builder had seen the ladder's final outcomes before writing the script, and the median dip strike is price-derived. A demonstration, not evidence.

**What ran.** 624 joint states (4 Fed outcomes × 12 reach-touched × 13 dip-touched counts), 396 in the declared reachable set. Weights from a linear program (maximin floor over reachable states, $60 on the primary, $40 on hedges, at most 6 contracts). Fees from each market's `feeSchedule`; slippage 0.01.

| Arm | Floor over reachable states | Realised |
|---|---|---|
| P: primary alone ($100) | −100 | −100 |
| C: $60 primary + $40 hedge (88.5 shares of "dip to $65,000" YES) | −11.54 | **−100** |
| D: primary scaled to the same floor | −11.54 | **−11.54** |
| R: random 6-contract hedges (200 draws) | — | median −60 (−100 to −60) |

**The mechanism works as arithmetic, and the narrative failed.** The Fed held (so the primary lost, as the thesis expected as a failure case) but Bitcoin touched only $75,000, not $65,000. The realised state (No change, 2 reach, 1 dip) is **outside the declared reachable set**. The −11.54 floor was conditional on the claim "no cut ⇒ Bitcoin touches $65k", the claim was false, so C lost everything and did worse than plain de-risking. This is exactly what B1 and B2 in the pre-registration are built to catch.

**Data path.**
- Fed YES prices summed to 1.001: the partition identity holds at lock.
- Ladder monotonicity: one adjacent break (0.0035 against 0.0045 in the deep tail), inside one 0.001 tick; not exploitable after fees.
- 6 of 46 hedge contracts (both sides of dip 75k, dip 70k, reach 82.5k) had **no price history** before the lock, and one price was **48 hours stale**. The missing ones are the strikes nearest spot.
- History for closed markets came back at 60-minute fidelity for most tokens within a few days of the lock, and at 720 otherwise; the Fed tokens returned 4 points at 12-hour fidelity.

**Gaps this exposed in `V1_prereg.md`** (amended in §11 before any round):
1. The linear program would shrink the primary to nothing (a floor of ≈ 0 by holding nothing). The primary's weight must be fixed.
2. Choosing a strike needs the underlying's level. A session that sees no price cannot translate "Bitcoin falls" into a strike. This is **Rob's decision** (D-V1-1).
3. Eligibility needs a price-age rule, and thin history removes exactly the near-the-money contracts.
4. The midpoint lock leaves menus with few live events for long-lived primaries; needs a menu-size rule.
