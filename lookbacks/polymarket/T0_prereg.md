# T0: the sessions' own picks and claims, priced (registration, written before the T0 script ran)

Retrospective and descriptive; it gates nothing. Data: the 41 scored rounds of V1 and V1b and their 69 claims. All answers were already frozen by hash. Nothing new is authored. Per `docs/nomad_v18_updates.md` §6.1 and `docs/nomad_v18_addendum_B1.md` §3.

**Statistics, all reported with a 90% bootstrap interval (resampled by round) and the probability that the effect is positive:**

1. **Claims, de-duplicated (T0-c3).** Among claims whose "if" happened, each "then" contract is counted once per round. Reported as hit rate minus lock price.

2. **Trigger lag (T0-c1), the 18.0c money test.** A claim is triggered when its "if" contract closed as stated before its "then" contract closed.
   - The post-trigger price is the first price point of the "then" side at least 1 hour after the "if" closed, from the public price history.
   - Statistic: hit − post-trigger price, and hit − post-trigger all-in cost (`exact.share_cost`, slippage 0.01, the market's fee and tick).
   - Also reported: how far the "then" price moved between the lock and the trigger.
   - Excluded and counted: claims where the "then" closed at or before the "if", or where no price point exists within 48 hours after the trigger.

3. **Matched placebo (T0-c2).** For each claim whose "if" happened, take every other contract shown to that session (the menu as displayed), on whichever side has a lock price within ±0.05 of the claim's "then" lock price. Statistic: claim (hit − price) minus the mean placebo (hit − price), under the same "if".

4. **Picks as bets (T0-p).** Each leg of each primary basket is a binary bet at its lock all-in cost.
   - Money statistic: mean(hit − cost).
   - Skill statistic: money minus the same quantity for the other contracts of the same primary event, on whichever side has a lock price within ±0.05 (matched cost).
   - Breakdown by price band: below 0.2, 0.2 to 0.5, 0.5 to 0.8, above 0.8.

5. **Post-mortems.** Every failed triggered claim, and every primary-loss round where C did worse than D, is classified with the v18 §6.0 classes.

**Reading.** Direction only (R20). If T0-c1 is positive with probability ≥ 0.80, 18.0c is pushed into the BT and forward tests as a co-primary statistic. If it is at or below zero, the market already propagates by the trigger, and 18.0c is dropped from the build order in favour of coverage alone. Small counts are expected (16 triggered claims), so this is a direction read, not a verdict.
