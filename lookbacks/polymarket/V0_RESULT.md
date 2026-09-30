# V0: market-structure audit (result, descriptive, no gate)

Spec: `V0_SPEC.md`. Script `v0_audit.py`, output `v0_result.json`. The domain taxonomy is a keyword list I wrote after reading the menu titles, so it is tuned to this sample. No prices, outcomes or scores are used.

**1. What is open now (census, 5,297 active events; 457 usable).** Usable multi-market structures by domain: crypto token launches 58, US politics 55, Middle East 52, Russia/Ukraine 48, AI models 42, crypto price 30, Fed and rates 14, UK politics 14, equities and FX 12, Europe politics 12, commodities 11, weather, climate and shipping 1; 108 fall in "other" (mostly my keyword list missing them). By trading volume, US politics is 61% of active volume, Middle East 11%, UK politics 6%; Fed and rates 1.7%, commodities 0.4%, equities and FX 0.6%, weather and shipping 0.1%. Usable structures are 319 threshold ladders, 85 open-slot partitions, 51 exact partitions.

**2. What the V1 menus held.** 24 menus drew on only 181 distinct events (179 distinct titles). One event ("GPT-6 released by...?") sat on all 24 menus; the same handful of crypto-launch, Fed, Russia, Israel and primary events recur. A menu's size (median 45) therefore overstates how many different instruments were available across the study.

**3. Supply versus demand (by search terms the sessions wrote).**

| asked for | rounds asking | menu held something in that domain |
|---|---|---|
| equities and FX (vol, Nasdaq, yen, sterling) | 12 | 8 |
| commodities (gold, crude, LNG) | 7 | 2 |
| Fed and rates (yields, dollar) | 7 | 7 |
| weather, climate, shipping (freight, Rhine, tanker) | 5 | 1 |
| crypto price | 5 | 5 |
| Middle East, UK politics, Europe politics, AI, Russia, US politics | 1 to 4 each | all |

Rounds that ended hedged had supply for 84% of the domains they asked for; rounds that ended no-instrument, 64%. Eleven of 17 hedged rounds hedged entirely inside the primary's own domain (crypto with crypto, Fed with Fed), which is the structural pattern already flagged in V1_STRUCTURAL.md. The things the sessions most wanted as independent hedges (commodities, equities and FX, shipping and weather) are what Polymarket offers least of, in usable volume terms.

**4. Liquidity at event level only.** Median event volume is about $4M for both the menu sample (150 events) and the 30 events the sessions hedged with; none under $100k. That says the events are real markets, not that the contracts have depth at a given price: order books, spreads and fee-adjusted cost need recorder data, which is not in this container.

**What V0 means for the product.** The mechanism's premise is hedges in a different part of the world from the primary. The open Polymarket catalogue is thick in politics, crypto and Middle East conflict and thin in the macro, commodity and shipping contracts such a hedge most wants. So expect most hedges to be within-domain (crypto-with-crypto, UK-politics-with-UK-politics) and judge the mechanism on those, not on an idealised cross-asset hedge. This is a property of the venue, not the model.
