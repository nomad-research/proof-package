# K11 and K12 — pre-registration (written before any price was fetched or any ρ computed)

*2026-09-29, the v16 build session. Spec v16 §31. Test statistic and level from appetite
`K11_K12_TEST`: one-sided Mann–Whitney U, α = 0.05 (provisional_unratified).*

## K11

> Using the stories named in the narrative rows registered at lock in rounds 5–15, ρ at lock is higher on
> effects whose instrument's hedged residual later left its noise band than on effects whose instrument's
> residual didn't. **Dies if** there is no separation beyond noise.

**Rounds.** v15 rounds 5–15, i.e. ledger sequence 5–17, excluding the two voided rows. Round 12 is the
re-run (event 2025-07-31); the voided original is excluded. Clean and learning rounds are reported
separately and pooled. Rounds 1–4 are outside K11's range.

**Units.** A unit is (round, listed instrument) such that the round has an un-eliminated effect on that
instrument's holder. Several effects on one holder in one round are one unit: they share one ρ and one
outcome, so counting them separately would inflate n.

**Instruments.** Holders with `listed = 1`. The symbol is `holders.price_symbol` where set. Otherwise the
ticker, with the Yahoo suffix for `holders.exchange` (XETRA/Frankfurt → `.DE`, LSE → `.L`, Paris → `.PA`),
and as-is for US exchanges. "Listed before the event" is enforced with Yahoo's own `firstTradeDate`; a
unit whose instrument's first trade is after the event date, or that has no price series, is excluded and
counted.

**Tide per instrument.** The instrument's home-market index: US `SPY`; Germany `^GDAXI`; UK `^FTSE`;
France `^FCHI`; Finland `^OMXH25`; Sweden `^OMX`; Norway `OBX.OL`; Denmark `^OMXC25`; Italy `FTSEMIB.MI`;
Poland `WIG20.WA`; South Africa `^J203.JO`; Japan `^N225`; Shanghai `000001.SS`; Shenzhen `399001.SZ`;
Chile `^IPSA`; Indonesia `^JKSE`. The global `ACWI` is used where the home index has no series.

**Stories and their proxies. The mapping rule, fixed here.** Each round's story is the one its narrative
row names. The proxy is the narrowest liquid ETF or front-month future on Yahoo for the commodity or
industry the narrative says the event moves. Where none exists, it is the S&P sector SPDR of the leg the
narrative names. Applied:

| round (seq) | narrative row (channel says…) | proxy |
|---|---|---|
| 8 (8) | the upset weighs on a refiner | `CRAK` (oil refiners) |
| 9 (9) | the fire tightens trichlor supply / lifts pool-chlorine prices | no industry ETF → leg is POOL (consumer discretionary) → `XLY` |
| 10 (10) | the insolvency threatens supply to a named OEM | `EXV5.DE` (European autos and parts) |
| 11 (11) | the joint venture is likely blocked | `WOOD` (timber, forest and paper) |
| 12 (13) | ground failure at a block-cave copper mine | `HG=F` (copper) |
| 13 (15) | patent enforcement about display-substrate supply | no industry ETF → leg is IRICO (information technology) → `XLK` |
| 14 (16) | a smelter repair vs a copper supply disruption | `HG=F` (copper) |
| 5, 6, 7, 15 (5, 6, 7, 17) | no narrative row registered | none: H is the tide only |

Only narrative rows whose `recorded_at` precedes the round's first lock count. A row recorded later is
dropped and the round is treated as having no story.

**ρ at lock, per unit.** Over the round's units I (instruments in reach), with daily returns strictly
before the event date: for each instrument, regress its returns on its tide and the round's story proxy
over the last 120 common sessions (`LOADING_SESSIONS`). Its tide-only residual σ sets the unit. The vol-unit
loadings are τ_i = b_tide·sd(tide)/σ_i and ℓ_i = b_story·sd(story)/σ_i. H is the columns [τ, ℓ], or [τ] when
there's no story. The unit's own thesis vector is e_i (ρ of a single effect doesn't depend on its sign or
size), so ρ_i = sqrt(max(0, 1 − P_ii)), with P the projection onto the column space of H.
**Degenerate rounds:** when |I| ≤ the number of columns of H, the span covers everything and ρ ≡ 0. Those
rounds are reported and excluded from the test.

Because tides differ across instruments, H stacks each instrument's own tide loading in one column; the
column is still "the tide".

**Outcome.** Did the instrument's tide-hedged residual leave its noise band after the event? The tide-only
residual, with coefficients from the pre-event window, is summed over the first 10 sessions strictly after
the event date. The band is the 90% block-bootstrap quantile of |10-session sums| of the pre-event
residual over the last 250 sessions (block 5, 2,000 draws, seed 16), as in `BAND_RULE`. **Left** if
|sum| > band.

**Test.** One-sided Mann–Whitney U: ρ of the left units > ρ of the stayed units. K11 **dies** if p ≥ 0.05 on
the pooled non-degenerate units. Clean-only and learning-only are reported beside it. If either group has
fewer than 5 units, the verdict is `unreadable`. Units within a round share an event, so the p-value
overstates independence; the per-round medians are reported beside it.

## K12

> Story pairs flagged by a shared constrained node show a larger rise in correlation after the trigger than
> matched unflagged pairs.

**On the v15 record K12 is unreadable by construction, recorded here before looking further.** v15
registered at most one narrative row per round (rounds 8–14), and stories carried no path through the
graph. There are no story pairs within a round, and there are no paths from which to flag a shared
constrained node. Pairing stories across rounds would compare unrelated events on unrelated clocks, which
the test doesn't mean. **K12 accumulates from v16 rounds only.** R16-001 flagged one junction, on a
constructed story, which `junction_confirm` doesn't yet test; that is recorded as a gap.
