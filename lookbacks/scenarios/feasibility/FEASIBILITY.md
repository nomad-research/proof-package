# Event-class feasibility for the construct-then-hedge test (2026-09-30)

Criteria: about 20 or more events; an observable, structured outcome; the information arrives at the event date; listed owners respond beyond noise.

| Class | Events | Outcome observable | Response beyond noise | Status |
|---|---|---|---|---|
| NRC power reactor events (v15 record) | many | yes (restart time) | **no**: K11 found 8 of 87 units left their 90% band (about the chance rate); R16-001's baskets were below band | **fails** |
| US Gulf hurricane landfalls, 2010 to 2025 | 45 storms (23 hurricanes) | yes (HURDAT2 landfall wind) | **no**: exceedance of the noise band is 8% (refiners), 8% (chemicals), 10% (utilities), 6% (insurers), against 5%, 14%, 8%, 11% on random dates; the storms are forecast days ahead, so the landfall date is not the information date | **fails** (`hurricane_response.py`) |
| Oil-spike days (used in the five pooled tests) | 35 + 9 | yes (the fade) | yes (by construction) | too heterogeneous: mixed causes and chains |
| Scheduled decisions with a categorical outcome that arrives on the notice date (OPEC+ ministerial decisions, FOMC, FDA, regulator and court rulings) | to be counted | to be sourced | expected yes for the owners with the stake | **candidates, not yet checked** |

## Reading
The two physical-event classes fail for the same reason K11 found: markets either forecast the event (hurricanes) or the listed owner's stake is too small to move it (reactors). The classes that fit the ACK design, a scheduled notice with a typed outcome vocabulary, are the ones with a decision date. Of those, OPEC+ ministerial decisions are the oil-native one:
outcomes (cut, hold, raise) are categorical, the date is the information date, and the narratives complement each other (a cut helps producers; a raise helps refiners and airlines).
The blocker is a source: a structured list of meeting dates and decisions that is not written from memory.
