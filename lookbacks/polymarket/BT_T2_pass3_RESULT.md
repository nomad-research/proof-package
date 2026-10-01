# BT-T2 pass 3 result: the NO edge (E1), April to June (2026-10-01)

Registration `BT_T2_pass3_prereg.md` (commit `7cb450d`). Frame: commit `044e4cf`, 150 multi-market events with locks on the 7-day grid from 2026-04-01 to 2026-06-30 (April 53, May 35, June 62). Answers frozen by hash (manifest `1dc03fd2…`, commit `da6afd3`) before any outcome was read.
- 25 cold sessions, all audited, with the paged instruction.
- S18 was re-authored once after writing a 0 where 1 to 99 is required; the original is kept.
- No recall flags.

## The registered statistic

| | n | Mean | 95% interval | Reading |
|---|---|---|---|---|
| **E1: NO positions against same-side, same-class, same-cost contracts** | 413 positions, 149 events | **+4.9¢** | −0.1 to +9.7 | **direction only** (misses by 0.1¢) |

## Secondary (declaring nothing)

| | Mean | 95% interval |
|---|---|---|
| NO money on the model's picks | **+11.3¢** | +6.8 to +15.5 |
| NO picks priced 50¢ or more: money | +12.9¢ | |
| Blind NO (every contract's NO side) | +3.3¢ | +1.7 to +4.8 |
| "Surer than the market" NO | +5.1¢ | −0.5 to +10.2 |
| NO by size of disagreement, 0.4 and above | +15.5¢ | +1.4 to +28.5 |
| YES against same-side | +1.6¢ | −1.3 to +4.8 |
| All positions, both sides (S1) | +4.6¢ | +1.5 to +7.6 |
| Log score against price | −0.064 | −0.100 to −0.029 (market better calibrated) |
| Location (S2) | −0.29 | −0.43 to −0.14 (market closer) |
| NO by lock month: April / May / June | +6.1 / +6.4 / +2.4¢ | n 176 / 92 / 145 |

May reads like April and June. Nothing suggests May carries knowledge (BT-A pass 2's borderline month).

## Pooled over the three BT-T2 passes (367 events; post-hoc, declaring nothing)

| | Mean | 95% interval |
|---|---|---|
| E1 | **+4.0¢** | **+1.2 to +7.0** |
| E1 without the top five events | +2.0¢ | −0.5 to +4.5 |
| NO money | +7.3¢ | +4.5 to +10.1 |
| NO money, picks priced 50¢ or more | **+10.3¢** | **+7.0 to +13.5** |
| S1, both sides | +3.8¢ | +2.1 to +5.5 |

## Reading

1. **E1 has now read positive on three independent registered passes:** +4.4¢ (pass 1, post-hoc on that pass), +2.6¢ and +4.9¢.
   - None cleared 5% on its own.
   - Pooled, the interval sits above zero (+4.0¢, +1.2 to +7.0). Pooling was not registered, so it declares nothing.
   - The forward sweep is the registered confirmation.
2. **The money on NO picks is the most stable number in the programme.** It was +4.4¢, +5.2¢ and +11.3¢ a share. On NOs priced 50¢ or more it was +8.5¢, +8.6¢ and +12.9¢, pooled +10.3¢ (+7.0 to +13.5), about +14% per dollar.
3. **Part of that money belonged to the market in April to June.** Blind NO earned +3.3¢ in this window, as it did on mention markets (+7.8¢). The registered statistic subtracts same-price NOs, which is why it reads +4.9¢ against +11.3¢ of money. The two earlier windows showed no blind-NO lean (−0.4¢ and −0.1¢).
4. **The model is still worse calibrated than the market overall and worse at location.** The edge stays where the ledger says it is: confident NOs against outcomes the market favours, not overall accuracy.
