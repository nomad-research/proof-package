# BT-T2 pass 2 result: the NO edge (E1), registered test (2026-10-01)

Registration `BT_T2_pass2_prereg.md` (addenda A1, A2). Result `bt/t2_pass2/result.json`.

**The run.**
- 150 fresh multi-market events (none from pass 1), locks on the 7-day grid from 2026-07-01, no evidence.
- 25 cold `claude-opus-5-5` sessions, every transcript audited.
- Four re-authorings: S01, S04 and S23 hit the Read tool's 25,000-token cap and read once (addendum A2); S04's second session wrote a 0 where 1 to 99 is required.
- No recall flags.
- Answers frozen by hash (manifest `86754b30…`, commit `8d050b4`) before any outcome was read.

## The registered statistic

| | n | Mean | 95% interval | P(positive) | Reading |
|---|---|---|---|---|---|
| **E1: NO positions against same-side, same-class, same-cost contracts** | 375 positions | **+2.6¢** | −2.7 to +8.0 | 0.82 | **direction only: not confirmed, not killed. E1 carries to the next pass** |

## Secondary (declaring nothing)

| | n | Mean | 95% interval |
|---|---|---|---|
| NO money (hit − all-in cost) | 375 | +5.2¢ | −0.0 to +10.3 |
| YES positions, same-side skill | 613 | +1.6¢ | −1.6 to +5.1 |
| NO, "surer than the market" (pass 1's sharpest subset) | 231 | +2.5¢ | −4.0 to +8.0 |
| NO, mention markets ("What will … say") | 20 | +15.6¢ | +10.8 to +22.8 |
| NO, bucket or count markets | 160 | +1.4¢ | −8.3 to +12.3 |
| NO, by size of disagreement: 0–0.1 / 0.1–0.2 / 0.2–0.4 / 0.4+ | | +1.0 / −2.3 / +5.5 / +8.0¢ | each spans zero |
| All positions (pass 1's S1) | 988 | +2.7¢ | −0.2 to +5.6 |
| Magnitude (S2: central value closer than the market's) | 117 | −0.13 | −0.26 to 0.00 (market closer 44, session 29, ties 44) |
| Log score against price | 1,553 | −0.074 | −0.109 to −0.039 (market better calibrated) |

## Where the money comes from: the model's choosing, not a market habit (post-hoc, both passes)

| NO bets | Pass 1 | Pass 2 |
|---|---|---|
| **Every NO in the frame** (a blind "always buy NO" rule) | −0.4¢ per share (1,037) | −0.1¢ (1,553) |
| **The model's NO picks** | **+4.4¢** (305) | **+5.2¢** (375) |
| Every NO priced 50¢ or more (blind) | +0.3¢ (807) | +0.1¢ (1,290) |
| **The model's NO picks priced 50¢ or more** | **+8.5¢** (177), about +11.6% per dollar | **+8.6¢** (234), about +11.8% per dollar |

Blind NO earns nothing; the model's NO picks earn +4 to +5¢ a share, and +8.5¢ where they bet against an outcome the market favours. That held on two independent sets of events.

The registered E1 comparison is stricter: it matches the event class as well as the price, and some of the model's picks fell in classes and prices where NO did well in this window. Both readings are honest. The registered one decides, and it says direction only.

## Pooled with pass 1 (pass 1's E1 is post-hoc, so this declares nothing)

| | Mean | 95% interval | Events |
|---|---|---|---|
| E1, NO against same-side, same-class, same-cost | +3.4¢ | −0.3 to +7.2 | 242 |
| NO money | **+4.9¢** | **+1.3 to +8.4** | 242 |
| All positions (S1, both sides) | **+3.3¢** | **+1.1 to +5.5** | 298 |
| Mention markets, NO | +15.9¢ | +5.8 to +29.4 | **4** |
| All other NO | +2.6¢ | −1.2 to +6.3 | 238 |

## Reading

1. **The NO edge is smaller than pass 1 suggested, and still pointing the same way.**
   - Four positive reads on four samples:
     - BT-A NO +3.7¢ skill (significant);
     - pass 1 +4.4¢;
     - pass 2 +2.6¢;
     - pooled +3.4¢.
   - Only the first clears 5%. The forward sweep is the next test.
2. **Pass 1's sharpest subset ("surer than the market") shrank on fresh data**, from +7.6¢ to +2.5¢. That is the usual fate of a subset found after looking. It stays a secondary.
3. **The money is the model's choosing.** A blind NO rule earns nothing in either pass. The model's NO picks earn about 5¢ a share, about 8.5¢ on NOs priced above 50¢.
4. **Mention markets are a new candidate (E3),** strong in both passes (+16¢) but resting on four events. A targeted backtest of every mention market in the window is cheap and settles it.
5. **Magnitude as scored here (location) shows the market closer, again.** This is the strongest sign yet that "where it lands" is the wrong magnitude without evidence. Decision 10's scale of scale is the replacement under test.
