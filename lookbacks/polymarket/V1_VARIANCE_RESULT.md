# V1 variance check: result (8 rounds planned, 7 valid)

Declared in `V1_VARIANCE.md` before any second session ran. Raw: `v1_variance_report.json`; second-run packets and scores in `variance/`. Descriptive only; V1's verdict, gates and frozen answers are unchanged.

**Run record.** Seven of eight second runs are valid. 287395 is void: its stage-1b answer failed the probability-language check twice ("would be priced in through June"), which under the registered rules voids the round (no replacement in this check). Two other answers needed the one registered return (606437 at 1a for probability language, 655630 at 1b for malformed JSON) and passed. The frozen audit has no slot for that returned message, so `v1_variance.py` drops it (and the harness's own hand-back nudge) from the expected-instructions comparison; in every other respect the audit is unchanged and all seven pass it (declared model on every turn, no tool call beyond the one prompt read).
Every second run got a byte-identical stage-1a prompt and the same menu size as the first.

| round | first run | second run | same basket | hedge-event overlap | floor lift first to second | realised C-D first to second |
|---|---|---|---|---|---|---|
| 155674 | hedged (3 events) | hedged (4) | yes | 0.75 | 28.1 to 28.1 | +16.4 to +16.4 |
| 606437 | hedged | hedged | no | 0.67 | 0.0 to 0.0 | 0.0 to 0.0 |
| 655630 | hedged (ETH ladder) | hedged (ETH ladder) | no | 1.00 | 49.7 to 47.4 | -10.9 to -12.8 |
| 680764 | hedged (Clacton winner) | hedged (Clacton winner) | no | 1.00 | 1.3 to 1.3 | +0.5 to +1.1 |
| 850741 | hedged | hedged | yes | 1.00 | 57.7 to 35.0 | +19.6 to +11.9 |
| 125877 | **no instrument** | hedged (gold) | no | 0.00 | none to 27.7 | none to -6.1 |
| 624242 | **no instrument** | hedged (Israel airspace) | no | 0.00 | none to 0.0 | none to 0.0 |
| 287395 | hedged | void | | | | |

What it says:
1. **Where a hedge was found, the second session mostly found the same one.** In five of five rounds that hedged both times, the chosen events overlap 0.67 to 1.00, and the floor lift and realised C-D are equal or close, because the menu is narrow and the tier mapping lands on the same rungs. So the scored results are not mostly noise on those rounds. The one visible swing is 850741 (57.7 to 35.0): same events, different tier.
2. **Whether a session hedges at all is not stable.** Both re-run no-instrument rounds came back hedged, each with a different proxy (gold for an oil-price thesis; Israeli airspace for a US-Iran diplomacy thesis). That is 2 of 2, so the 7 no-instrument rounds should not be read as "nothing on the menu could express the thesis"; it is partly a willingness threshold. On the second pass they picked a weak proxy (the 624242 session said so explicitly and made no claims; its lift is 0.0).
3. **Primary baskets differ in four of seven** (same thesis domain, different contracts), which the lift figures mostly ignore because lift depends on the hedge.
4. **Sample is seven rounds.** Treat as an indication of how stable the authoring step is, not an estimate.
