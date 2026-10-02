# T0 result: the sessions' own picks and claims, priced (2026-10-01)

Registration: `T0_prereg.md`, committed before the script ran. Script: `t0_picks_and_claims.py`. Data: `t0_report.json`.

One correction, made after the first run. The script de-duplicated "then" contracts across all claims instead of among triggered claims only, which dropped one failed claim (329566). The figures below use the corrected count. Both versions point the same way.

## Claims

| Test | Count | Result | P(positive) |
|---|---|---|---|
| c3: triggered claims, de-duplicated | 14 | "then" held 71% against a lock price of 48%: excess +24 points (90% CI +5 to +42) | 0.98 |
| c2: against a matched placebo (other contracts shown to the session, priced within ±0.05, same "if") | 14 | claim beats placebo by +22 points (+1 to +42); placebo's own excess +2 points | 0.96 |
| c1: trigger lag (buy the "then" at least 1 hour after the "if" closed) | 6 tradable | hit minus all-in cost +3 points (−28 to +34) | 0.65 |

Why the trigger-lag test has only 6 tradable claims:
- In 7 of the 14 claims, the "then" closed at or before the "if", so there was no trigger to trade on.
- In 1, there was no price within 48 hours.

In the 6 tradable claims, the "then" price had already moved from 0.44 at the lock to 0.63 within about 1.3 hours of the "if" closing (+18 points, probability 0.96).

**Reading.**
- The claims pick the right linked contract: they beat both the lock price and contracts of the same cost under the same "if". That is the strongest result Nomad has.
- The trigger trade does not capture it. The market moves within about an hour, and half the time the "then" resolves first anyway.
- So the claims' value has to be taken before resolution. That needs a belief about whether the "if" will happen.

## Picks (each primary leg as a bet at its lock all-in cost)

| | n | Money: hit − cost | Skill: minus matched-cost contracts of the same event |
|---|---|---|---|
| All | 143 (100 with a matched null) | −0.3 points (−4.3 to +3.5) | −2.3 points (−6.9 to +1.9), P(positive) 0.19 |
| Priced above 0.8 | 103 | +2.0 points (−0.8 to +4.4), P 0.89 | +2.3 points (−0.9 to +5.3), P 0.89 |
| Below 0.8 | 40 | negative in every band | negative |

**Reading.**
- The sessions' "what will happen" picks have no edge over price overall.
- 72% of them are favourites priced above 0.8. There they show a small positive direction, consistent with the known favourite/longshot bias.
- Under R20 a breakdown that points up is a hypothesis for the next batch, not a result.

## Post-mortems (v18 §6.0 classes)

| Round | Claim | Class |
|---|---|---|
| 624096 | Foreign Secretary changes, so Home Secretary changes | Wrong direction: offices moved separately, so the reshuffle link does not exist as claimed. The market had already priced "then" at 0.001 an hour after "if" |
| 674379 | Defence Secretary changes, so Home Secretary changes | Wrong direction (the same link as 624096) |
| 329566 | Fed hike by October, so crude reaches its rung by end of June | Timing: "then" closed in June, months before "if"; the claim linked a later cause to an earlier effect |
| 871083 | US strike on Iran, so no senior US–Iran talks | Right direction, wrong strength: talks went ahead despite the strike. The same round's other claim (Israeli airspace closure) held, bought at 0.085 after the trigger |

## Consequence for the build (taken into addendum B1 as §5)

18.0c changes from a trigger trade to a **pre-resolution claim bet**: belief(B) = P(A)·P(B | A) + (1 − P(A))·P(B | not A).
- P(B | A) and P(B | not A) are authored as graded C edges and recalibrated from the claims' track record.
- P(A) is an authored, graded node belief.
- All of it is price-free (R6). Price enters only at sizing.
- This needs graded beliefs, which v18 packets now allow. T2 and T3 must collect P(A) and both branches of every C edge, and their calibration is measured before 18.0c bets.

## Post-hoc breakdown (2026-10-01, after the result): magnitude claims against named-contract claims

Not registered; under R20 a hypothesis for the next batch, not a result. Triggered claims, de-duplicated among triggered claims (14), split by how the "then" was stated:

| "Then" stated as | Triggered | Held | Mean lock price |
|---|---|---|---|
| A magnitude: a ladder direction and severity tier (mild, moderate, severe) | 9 | 8 | 0.43 |
| A named contract | 5 | 2 | 0.55 |

When the "if" did not happen, magnitude claims held 19% against 24% priced (36 claims, not de-duplicated). The single magnitude miss is 329566, the timing error.

- **Reading.** The claims' edge sits in the magnitude claims. The named-contract claims include both wrong-direction failures.
- **Caveat.** The tier was mapped to a rung by lock price with the builder's provisional values (0.50, 0.25, 0.10). So "magnitude" here is partly defined through price, and the sessions gave only one of three words.

## Post-hoc (2026-10-01): every claim's "then" bet at the lock, under three price-only weightings

Not registered; R20 hypothesis only. Script `t0_weightings.py`, data `t0_weightings.json`. Each claim's "then" is bought at the lock whether or not its "if" later happened. Figures are return on total money staked, 90% interval resampled by round. Claims carry no fees or slippage; picks use the all-in cost.

| Set | n (rounds) | Equal shares | Equal variance | Equal stake |
|---|---|---|---|---|
| Magnitude (tier) claims | 47 (26) | +27% (−16 to +76), P 0.83 | +37% (−13 to +100), P 0.88 | +69% (−19 to +183), P 0.88 |
| Named-contract claims | 22 (15) | −6%, P 0.28 | −2%, P 0.26 | −36% (−65 to −11), P 0.01 |
| Picks | 143 (41) | 0%, P 0.47 | +1%, P 0.71 | −4%, P 0.28 |

**Reading.**
- The tier claims are positive under every weighting, so the direction does not depend on the weighting.
- Equal stake is carried by three long shots priced 0.08 to 0.09 (two of them are the same contract in round 871083). Without those three it is −1%.
- All intervals for the tier claims span zero.
