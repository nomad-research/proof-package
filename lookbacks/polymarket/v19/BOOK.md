# v19 paper book (version 0), 2026-10-02 06:56 UTC

The new system run on paper over the forward sweep's frozen batches. Nothing is traded. The book declares nothing: the rule's test is read only at its looks (`V19_A2_prereg.md`).

Paper fills are at the lock ask plus the fee, each sized at the lesser of $150 and the dollars on offer within 2c of the ask. The 2c-worse column shows the same fills 2c dearer, until real fills are measured.

## The books

| Book | Positions | Events | Staked | Settled | Paper P&L | 2c worse | Return on settled | Still open ($) |
|---|---|---|---|---|---|---|---|---|
| **Armed** | 24 | 20 | $2,388 | 0 | – | – | – | 24 ($2,388) |
| Armed, non-mention (the E1 book) | 24 | 20 | $2,388 | 0 | – | – | – | 24 ($2,388) |
| Armed, mention (the mention book) | 0 | 0 | $0 | 0 | – | – | – | 0 ($0) |
| Shadow only: NO | 114 | 82 | $9,304 | 13 (0 won) | -$319 | -$319 | -100.0% | 101 ($8,985) |
| Shadow only: YES | 786 | 98 | $15,468 | 42 (2 won) | -$449 | -$473 | -49.6% | 744 ($14,564) |

**Reading the ledger early.** A NO bet that loses usually settles early (the thing happens), while one that wins settles only at its deadline. Settled results lean towards losses until a batch's deadlines pass.

**Already decided at the lock.** 315 shadow positions sit on contracts the market priced at 3% or less, or 97% or more, at the lock; 10 have settled, 0 won. These are mostly outcomes that had already happened (a day's rain, a closing price) that the news-blind reader bet against. A2's 50c floor keeps them out of the armed book; D1's narrowed rule ("the outcome already happened") would flag them.

**Fill bound from the lock books.** 19 of 24 armed stakes fit within 1c of the ask, the rest within 2c (each stake is capped at the dollars on offer within 2c).

## Armed book by kind of market

| Kind | Positions | Settled (won) | Paper P&L | Open stake |
|---|---|---|---|---|
| elections and votes | 22 | 0 (0) | $0 | $2,187 |
| macro and commodities | 1 | 0 (0) | $0 | $51 |
| other | 1 | 0 (0) | $0 | $150 |

## Armed exposure by occasion: what is lost if every open bet in it goes wrong

Occasions are addendum A3's: the same kind of market, the same place or asset, settling within 7 days. Shown largest first; this is the group a cap would act on.

| Occasion | Open positions | Events | Worst case |
|---|---|---|---|
| elections and votes | brazil | from 2026-10-04 | 15 | 13 | $1,507 |
| elections and votes | peru | from 2026-10-05 | 6 | 4 | $663 |
| event 1083675 | 1 | 1 | $150 |
| macro and commodities | jobs | from 2026-10-03 | 1 | 1 | $51 |
| elections and votes | canada | from 2026-10-05 | 1 | 1 | $17 |
| **All open armed** | 24 | | **$2,388** |

## Armed positions

| Batch | Event | Contract | Side | Cost | Reader | Market | Stake | Depth 2c | Status | P&L |
|---|---|---|---|---|---|---|---|---|---|---|
| W01 | Brazil Presidential Election First Round: August | Will Augusto Cury win between 4% and 6% of the v | NO | 0.66 | 0.94 | 0.38 | $150 | $294 | open | – |
| W01 | Brazil Presidential Election First Round: 3rd Pl | Will Augusto Cury finish in third place in the f | NO | 0.61 | 0.99 | 0.40 | $150 | $2,653 | open | – |
| W01 | Brazil Presidential Election First Round: 3rd Pl | Will Renan Santos finish in third place in the f | NO | 0.57 | 0.88 | 0.45 | $150 | $1,470 | open | – |
| W01 | Pará Governor Election Winner | Will Dr. Daniel Santos win the Governor of Pará  | NO | 0.60 | 0.93 | 0.43 | $150 | $170 | open | – |
| W01 | Rio de Janeiro Governor Election Winner | Will Douglas Ruas win the Governor of Rio de Jan | NO | 0.72 | 0.93 | 0.30 | $150 | $873 | open | – |
| W01 | Acre Senate Election: 1st Place | Will Mara Rocha win the most votes in the 2026 A | NO | 0.75 | 0.97 | 0.32 | $104 | $104 | open | – |
| W01 | Acre Senate Election: 1st Place | Will Marcio Bittar win the most votes in the 202 | NO | 0.70 | 0.92 | 0.37 | $150 | $836 | open | – |
| W01 | Amapá Senate Election: 2nd Place | Will Lucas Barreto win the second-most votes in  | NO | 0.57 | 0.85 | 0.46 | $38 | $38 | open | – |
| W01 | Maranhão Senate Election: 1st Place | Will Roseana Sarney win the most votes in the 20 | NO | 0.61 | 0.75 | 0.52 | $6 | $6 | open | – |
| W01 | Minas Gerais Senate Election: 1st Place | Will Domingos Sávio win the most votes in the 20 | NO | 0.78 | 0.86 | 0.44 | $64 | $64 | open | – |
| W01 | Mato Grosso do Sul Senate Election: 1st Place | Will Capitão Contar win the most votes in the 20 | NO | 0.82 | 0.86 | 0.36 | $16 | $16 | open | – |
| W01 | Paraná Senate Election: 1st Place | Will Deltan Dallagnol win the most votes in the  | NO | 0.65 | 0.72 | 0.53 | $67 | $67 | open | – |
| W01 | Rio de Janeiro Senate Election: 1st Place | Will Benedita da Silva win the most votes in the | NO | 0.66 | 0.83 | 0.40 | $11 | $11 | open | – |
| W01 | Paraíba Senate Election: 2nd Place | Will Veneziano win the second-most votes in the  | NO | 0.51 | 0.73 | 0.56 | $150 | $178 | open | – |
| W01 | Tocantins Senate Election: 2nd Place | Will Alexandre Guimarães win the second-most vot | NO | 0.70 | 0.92 | 0.33 | $150 | $287 | open | – |
| W01 | Quebec General Election: PLQ # Seats? | Will the PLQ win 36-39 seats in the National Ass | NO | 0.71 | 0.88 | 0.35 | $17 | $17 | open | – |
| W01 | Maynas Mayoral Election Winner | Will Roger Cristóbal Gronerth Pinedo win the nex | NO | 0.62 | 0.96 | 0.40 | $150 | $505 | open | – |
| W01 | Maynas Mayoral Election Winner | Will Boris Guido Morey Sifuentes win the next Ma | NO | 0.86 | 0.93 | 0.33 | $108 | $108 | open | – |
| W01 | Chiclayo Mayoral Election Winner | Will Edwin Gonzalo Vásquez Sánchez win the next  | NO | 0.71 | 0.90 | 0.32 | $150 | $496 | open | – |
| W01 | Piura Mayoral Election Winner | Will Jorge Hilton Flores Bazán win the next Piur | NO | 0.70 | 0.92 | 0.36 | $72 | $72 | open | – |
| W01 | Trujillo Mayoral Election Winner | Will Víctor Robert De La Cruz Rosas win the next | NO | 0.60 | 0.96 | 0.42 | $150 | $281 | open | – |
| W01 | Trujillo Mayoral Election Winner | Will Mario Colberth Reyna Rodríguez win the next | NO | 0.68 | 0.84 | 0.40 | $34 | $34 | open | – |
| W01 | Donald Trump # Truth Social posts September 29 - | Will Donald Trump post 200+ Truth Social posts f | NO | 0.68 | 0.92 | 0.36 | $150 | $195 | open | – |
| W01 | How many jobs added in September? | Will the US add between 100k and 150k jobs in Se | NO | 0.68 | 0.86 | 0.38 | $51 | $51 | open | – |

## Gaps this run shows

- **No falsifier on any position (D2).** The sweep's reader is not asked for one, and its prompt is frozen. A falsifier needs a v19 reader pass or a separate step.
- **Not yet available on any position:** A3 (record by kind), A4 (statistical baseline), A6 (fills measured), D1 (news check), D3 (staleness).
- **Positions with no depth recorded at the lock (A5 unassessable, stake $0):** 0 armed.
