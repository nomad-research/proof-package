# What separates the armed NOs that held from the ones that flipped (2026-10-02; exploratory, after the fact; declares nothing)

Every NO loss is a YES that happened. Rob: betting NO across the board fails "because there's no framework around the edge or strong risk management that leans to excluding YESes".

This note asks which features of an armed NO predict the flip.
- **Data:** A2-armed, non-mention NOs on BT-T2 passes 1 to 4: 337 positions, 140 events, 58 losses. Script: `v19_losers.py`.
- **Two separate checks:** the levers were read on passes 1 to 3 and on P4, and the strongest was checked on BT-A's armed NOs (`v19_bta.py`'s positions).

| Lever | Passes 1 to 3 | P4 (fresh events) | BT-A (fresh events, other pipeline) |
|---|---|---|---|
| **Reader's YES under 5%** | **1% lost, +20.3¢ (69 positions)** | **0% lost, +22.0¢ (28)** | **7% lost, +19.5¢ (27)** |
| Reader's YES 5% to 10% | 10% lost, +20.0¢ | 35% lost, −2.4¢ | 22% lost, +6.4¢ |
| Reader's YES 10% or more | 30% lost, −0.6¢ | 26% lost, +12.3¢ | 23% lost, +11.1¢ |
| Ends in under 3 days | 27% lost, +4.4¢ | 35% lost, −1.1¢ | |
| **Ends in 3 to 7 days** | **9% lost, +15.3¢** | **4% lost, +25.7¢** | |
| Ends in 7 days or more | 19% lost, +12.5¢ | 38% lost, −4.5¢ | |
| Touch questions ("will it reach X") | 30% lost, +15.2¢ | 59% lost, −15.1¢ | |
| **5 or more armed NOs in one event (ruling out a ladder's tails)** | **4% lost, +21.1¢** | **8% lost, +23.9¢** | |
| A single armed NO in its event | 30% lost, −3.0¢ | 22% lost, +12.6¢ | |

## Reading

- **Only the first lever has a reason given in advance.**
  - BT-A's calibration (`EDGE_LEDGER.md`): when the model says under 5%, it happened 1% of the time.
  - It holds on all three samples, with about 0% to 7% lost and about +20¢.
- **The others were found by looking at several cuts,** so some will be noise.
  - Horizon (3 to 7 days) and ladder-tail exclusions point the same way on both BT-T2 samples.
  - Touch questions lost heavily in P4.
- **Each is a candidate rule.** It is registered before data and tested on fresh events or forward, never adopted from this table.
