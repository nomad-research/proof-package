# T3 scale of scale: how it is scored (registration, written before any T3 outcome is read)

T3 sessions wrote `scale` for every kept question that measures a quantity, count, price, size or date:
- a reference class ("basis-point change in the fed funds target at scheduled FOMC meetings since 1994");
- the percentile (0–100) where their middle view of this instance sits in that class.

Decision 10 reads magnitude as this "scale of scale". `T3_prereg.md` §9 says the score gets its own registration before any T3 outcome is read, and that **it declares nothing in T3**. This is that registration. `t3.py score`, which reads outcomes, is not run before this file is committed.

## 1. The realised percentile

- **Who computes it.** A grader session runs once the event has resolved. It is a cold `claude-opus-5-5` subagent with retrieval, the same blocked list and the same audit as T3. It is given:
  - the class, word for word as the session wrote it;
  - the event's rules and how it resolved, as Gamma reports it;
  - the market's central value at the lock: the median of the lock-ask midpoints, as S2 computes it.
- **What it does not see:** the session's percentile, any other part of the session's answer, or which session wrote the class.
- **What it returns:**
  - the realised instance's percentile in the class, with sources;
  - the market central value's percentile in the same class;
  - or "not determinable" with a reason, for a class too vague to rank against or an outcome too coarse to place.
- **Grading cadence.** One grader session per resolved event, batched. Every transcript is audited as T3's are.

## 2. What is reported (declaring nothing)

| | Measure | Unit of resampling |
|---|---|---|
| **Scale S2** | +1 if the session's percentile is closer to the realised percentile than the market's is, −1 if farther, 0 if tied. The mean is the share of wins minus the share of losses. It is BT-T2's S2, re-expressed in the class's own scale | clusters |
| Rank agreement | Spearman correlation between the session's percentile and the realised percentile across graded events, with a permutation test | events |
| Not determinable | Count and reasons | — |

## 3. What would make it a declared statistic later

It becomes a declared statistic only if Rob confirms decision 10's reading, and only in a test registered after that. Results here inform that registration; they decide nothing.
