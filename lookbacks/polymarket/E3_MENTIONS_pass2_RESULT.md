# E3 pass 2 result: mention markets, April to June (2026-10-01)

Registration `E3_MENTIONS_pass2_prereg.md` (commit `09b1ef1`), written before BT-A pass 2 was frozen. BT-A pass 2 opened the window at 2026-04-01 under the loose gate (`BT_A_pass2_RESULT.md`), so this pass ran.
- Frame: 36 events, 729 contracts, locks daily from 2026-04-01 to 2026-06-30 (commit `a9f7155`).
- Answers frozen by hash (manifest `746e1884…`, commit `e5da2a3`) before any outcome was read.
- 6 cold sessions, all audited, no re-authorings, no recall flags.

## The registered statistic

| | n | Mean | 95% interval | Reading |
|---|---|---|---|---|
| **E3: the model's NO picks against other mention NOs at the same price** | 469 positions, 36 events | **+5.1¢** | −2.4 to +12.4 | **direction only** |

As registered (§4), E3 is **carried to the forward sweep**. It is neither confirmed nor killed on backtests.

## Secondary (declaring nothing)

| | Pass 2 | Pass 1 |
|---|---|---|
| NO money on the picks | +12.7¢ (+5.4 to +20.0) | +10.1¢ (+4.7 to +15.6) |
| **Blind NO** (every contract's NO side) | **+7.8¢ (+1.3 to +14.2)** | +3.1¢ (−1.4 to +7.5) |
| NO picks priced 50¢ or more: against same-price NOs | +7.5¢ (+0.4 to +13.6) | +11.5¢ (+6.6 to +16.2) |
| YES picks against same-price YESes | +11.0¢ (+2.2 to +19.7) | +14.3¢ (+8.5 to +19.9) |
| **All picks, both sides (S1)** | **+10.9¢ (+6.0 to +15.7)** | **+11.1¢ (+7.4 to +15.0)** |
| Log score against price | +0.014 (−0.036 to +0.068) | −0.007 (−0.057 to +0.042) |
| NO by size of disagreement, 0.4 and above | +19.5¢ (+3.6 to +32.9) | +13.9¢ (−0.5 to +26.2) |

- **Concentration (NO statistic).** 22 events add and 14 subtract. Three Trump events carry most of it:
  - the WHCA dinner;
  - bilateral events with Brazil's president;
  - bilateral events with Mark Rutte.

  Without them it is +0.7¢ (−5.7 to +7.3).
- **By lock month,** for May's borderline BT-A reading: April +5.0¢, May +4.8¢, June +5.8¢. They are alike, so nothing suggests May carries knowledge.

## Pooled over both passes (82 events; post-hoc, declaring nothing)

| | Pooled | Without the top 3 events | Without the top 5 |
|---|---|---|---|
| E3 (NO against same-price NOs) | +6.2¢ (+1.6 to +10.7) | +4.0¢ (−0.1 to +8.1) | +2.8¢ (−0.9 to +6.7) |
| YES against same-price YESes | +12.8¢ (+7.6 to +17.9) | +10.9¢ (+5.6 to +16.3) | |
| **All picks, both sides (S1)** | **+11.0¢ (+7.9 to +14.3)** | | **+8.7¢ (+6.1 to +11.4)** |
| NO money | +11.4¢ (+6.8 to +15.9) | | |

## Reading

1. **The NO-only claim (E3 as registered) is real but thin.** It points the same way in both passes (+7.3¢, +5.1¢). In both it leans on a few large Trump events, and it carries to the forward sweep.
2. **The sturdier finding is both-sided.**
   - On mention markets the model's picks beat same-price contracts on both sides, by +11¢ in each of two independent passes.
   - That survives removing the biggest events (+8.7¢ pooled without the top five).
   - Its log score ties or beats the market's here. In every other class tested, the market was clearly better calibrated.
   - Mention markets are where the model's probabilities, not only its NO picks, are as good as the crowd's or better.
   - The both-sides statistic was not the registered main statistic of either pass. It was reported by both and replicated almost exactly, so it is registered for the forward sweep (addendum A3) rather than declared here.
3. **A market habit appeared in April to June.** Blind NO earned +7.8¢. Some of the NO money in that window belongs to the market, not to Nomad. The registered statistic subtracts it.
4. **Forward relevance.** The backtest's Trump speech events (rallies, G7 events, bilateral meetings) carried "politics" and not "pop-culture". The same kind of event open now carries "pop-culture", so the forward sweep's scope list was dropping them. Addendum A3 keeps political mention markets from W02.
