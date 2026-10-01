# E3 result: mention markets (2026-10-01)

Registration: `E3_MENTIONS_prereg.md` (commit `a84a834`, before the frame). Frame: commit `a816f1e`. Answers frozen by hash: manifest `280e21e4…`, commit `43ccfa3`, before any outcome was read. Result: `bt/e3_mentions/result.json`.

**The run.**
- 46 mention events: every eligible one in the clean window, minus the four that produced the hypothesis. That is 816 contracts.
- Locks were daily at 12:00 UTC from 2026-07-01.
- 8 cold `claude-opus-5-5` sessions, price-blind and with no evidence.
- Every transcript passed the audit. No re-authorings and no recall flags.

## The registered statistic

| | n | Mean | 95% interval | P(positive) | Reading |
|---|---|---|---|---|---|
| **E3: the model's NO picks against other mention NOs of the same price** | 494 positions, 46 events | **+7.3¢** | **+1.8 to +13.0** | 0.997 | **edge shown** (decision 7) |

## Secondary (declaring nothing)

| | n | Mean | 95% interval |
|---|---|---|---|
| NO money on the model's picks (hit − all-in cost) | 494 | **+10.1¢** | +4.7 to +15.6 |
| NO picks priced 50¢ or more: money | 227 | **+19.5¢** | +14.7 to +24.2 |
| NO picks priced 50¢ or more: against same-price NOs | 227 | +11.5¢ | +6.6 to +16.2 |
| NO picks priced under 50¢: against same-price NOs | 267 | +3.7¢ | −3.5 to +10.9 |
| **Blind NO** (every contract's NO side) | 816 | +3.1¢ | −1.4 to +7.5 |
| YES picks against same-price YESes | 243 | **+14.3¢** | +8.5 to +19.9 |
| All picks, both sides (S1) | 737 | +11.1¢ | +7.4 to +15.0 |
| Log score against price | 816 | −0.007 | −0.057 to +0.042 |
| NO picks by speaker: Trump / earnings calls / other | 147 / 270 / 77 | +10.0 / +3.4 / +15.7¢ | −2.1 to +22.2 / −1.4 to +8.5 / +2.9 to +32.0 |

## Checks run after scoring (post-hoc)

**Stale or decided prices.** The registered statistic was re-scored with the following contracts removed:
- those whose price did not move in the 24 hours before the lock (a thin or stale book);
- those already priced under 3¢ or over 97¢.

| Removed | E3 statistic | NO money |
|---|---|---|
| No movement in 24 hours (79 contracts) | +6.7¢ (+0.8 to +12.8) | +8.6¢ (+3.1 to +14.3) |
| That, and priced under 3¢ or over 97¢ (132) | +6.9¢ (+0.9 to +13.2) | +8.9¢ (+3.2 to +14.8) |
| Priced under 5¢ or over 95¢ (112) | +8.0¢ (+2.1 to +14.2) | +11.4¢ (+5.7 to +17.6) |

It holds under each.

**Concentration.**
- Of the 46 events, 23 add and 23 subtract.
- Three events carry about half the total: a White House press briefing, "Trump-named things" in August, and "What will Trump say in August?".
- Without them the statistic is +3.8¢ (−0.4 to +8.4); without the top five, +2.4¢ (−1.5 to +6.6).
- The result is real on the registered test but leans on a few events, as BT-T2's first pass did.

## Reading

1. **E3 passes its registered test.** Against other mention NOs at the same price, the model's NO picks earn +7.3¢ a share, and the interval clears zero. It holds with stale and decided prices removed.
2. **It is the model's choosing, mostly.** Blind NO on mention markets earns +3.1¢ with an interval spanning zero, so there is a lean towards NO in the market itself. The picks beat it.
3. **It is not only NO.**
   - The model's YES picks also beat same-price YESes (+14.3¢).
   - Its log score ties the market's. In every other class tested, the market was clearly better calibrated (pass 2: −0.074).
   - Mention markets are where the model's prior is as good as the crowd's, and its disagreements pay on both sides.
4. **Where the money is.** NO picks priced 50¢ or more earn +19.5¢ a share: about +29% per dollar, at a mean cost of 68¢ and a hit rate of 88%. That matches E1's pattern: betting against an outcome the market favours.
5. **Fragile.** Removing the three biggest events takes the interval across zero. The next pass is forward: mention markets open now, read cold, scored as they resolve. That is the confirmation decision 7 asks for before any design leans on it.
6. **Mechanism (divergence).**
   - The market prices "will they say X" from what is in the news.
   - The model prices it from how the speaker talks and how long the format runs:
     - a briefing's length and its Q&A;
     - an earnings call's script;
     - a person's stock phrases.
   - Many words that feel topical are not in the speaker's habit, and many that feel dull are.
7. **Mechanism (framework).** The model is cold and price-blind and writes a number for every word. The bet rule turns its confident disagreements into positions.

**Note on the crawl hash.** The registration gives the crawl's hash as `929ddee7…`, the hash of its uncompressed JSON. Every frame records `a99059aa…`, the hash of the `.gz` file. Both are the same crawl, checked on 2026-10-01.
