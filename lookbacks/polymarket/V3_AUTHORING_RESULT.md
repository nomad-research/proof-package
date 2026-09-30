# V3: authoring results (pre-outcome; not a verdict)

Everything here was fixed before any V3 contract resolved. It describes what the sessions chose, not whether it worked. Data: `v3_authoring.json` (built from the frozen packets with the V0 domain list).

**Coverage.** 30 rounds: 26 hedged, 4 no instrument (13%; V1 was 7 of 24, 29%). The forward menu was richer (median about 80 candidates against 45 in V1), and it showed. Rounds that hedged had supply in 91% of the domains their search terms asked for; the four no-instrument rounds had 38%. Every no-instrument round asked for something the venue does not list: South African rand and bonds (Johannesburg mayor), Rhine and Danube freight and power (Danube level), Japanese defence stocks (Taiwan local elections), or had no hedge terms at all (White House press secretary).

**Claims.** 25 of the 26 hedged rounds made at least one causal claim (mean 1.8); one (956597, memecoin to $1B) hedged with BTC and ETH weekly ladders and made none, so its floor lift will be zero by construction. Claims are what V3's B1 will test against outcomes.

**Same-underlying (structural) hedges, flagged now so the flag cannot be fitted to results.** S = at least one leg is the same underlying or a direct necessary condition: 425728 and 81557 (Israeli election winner, PM and Likud seat counts: one election), 653446 (leaders leaving office vs Venezuela de facto leader: same office), 488234 (Gemini Pro Arena debut vs Gemini Pro release date: necessary condition). Everything else is cross-entity (X). That is 4 S rounds of 26, fewer than V1's 6 of 17.

**Within-domain hedging is still common** (11 of 26 by the V0 keyword domain), for example crypto launches hedged with HYPE, ETH, ENA or BNB ladders, central banks hedged with other central banks, US races hedged with House and Senate control. Several claims are market-wide beta claims ("a $1B launch needs a crypto rally, so HYPE touches its nearest upside rung"), which are plausible but not structural.

**Process.** 6 rounds were replaced from the reserve under the registered rules (details in V3_prereg.md A4). Two of those came from stage-1b prompts of about 1,200 lines that a session could not read in the permitted chunks, which is a harness limit to fix before any V4, not a model result.

**When outcomes arrive.** First horizon 15 October 2026, last 10 January 2027; `v3_score.py` scores each round when every contract it depends on has resolved. Today: 0 scored.
