# R1: does averaging independent readings sharpen the reader? (registration, written before any R1 session runs)

Decision 17 named making the system as strong as possible the focus, and Rob chose this test first ("1 and 4 look good"). Its basis is `docs/EDGE_LEDGER.md`'s calibration notes:
- the reader is overconfident when it says "likely";
- the edge grows with the size of the reader's disagreement with the market (the starting point, §6).

If one reading carries noise, a second independent reading of the same question should cancel some of it. More of the armed positions would then be real disagreements. Scorer: `r1.py`.

## 1. Data

- **Questions:** BT-T2 pass 3's 150 events (April to June locks), its 25 prompts as frozen, and its outcomes and lock prices (frame commit `044e4cf`).
  - Pass 3 is used because it holds the most armed events of the three passes (43).
  - Every R1 session reads a prompt whose outcome the builder can see. That is why only cold, audited sessions author anything.
- **Reading A:** pass 3's frozen answers (manifest `1dc03fd2…`), unchanged.
- **Readings B and C:** fresh, independent cold sessions on the same 25 prompts.
  - Each uses the same paged instruction pass 3 used, from a copy of the prompt outside the repository (`NOMAD_PROMPT_DIR`, this session's scratch folder).
  - They are run and ingested with `bt_t2.py`'s own tooling: V1's transcript audit and the line-number read check. Each reading is frozen by hash before any R1 score is computed.
  - 50 sessions in all. Sessions are cold `claude-opus-5-5` subagents of this cloud session. The runtime shows them the date and model name, as before.

## 2. What is compared

- **The reader's view per contract,** in each reading, is the range bt_t2.py derives (`contract_chance`).
- **Averaging:** each contract's lower and upper bounds are averaged in log-odds across the readings that give it, clipped at 0.5% and 99.5%.
- **An event any reading flags as recalled** is left out of every comparison.
- **Positions and skill** are exactly as BT-T2: the session's chance beats the all-in cost. Skill is against same-side, same-class contracts on other events with cost within 0.05.
- **Armed** is A2 as in the backtest: NO, cost 50¢ or more, and the reader's midpoint at least 20 points from the lock price.

## 3. The registered statistic

**The armed skill of avg(B, C), minus the mean of the armed skill of B alone and of C alone.** It is resampled by event, paired (one resampling of events for all three), with 4,000 draws, seed 20261003, and a 95% interval (decision 7):
- **Edge shown (averaging sharpens)** if the interval is above zero.
- **Shown absent (averaging blunts)** if it is below zero.
- **Direction only** otherwise.

**Why A is left out of the registered comparison.** A2's thresholds were chosen on reading A's answers across the three passes, so any comparison containing A is flattered by that fit. B and C are fresh to the rule.

## 4. Secondary (declaring nothing)

- **Each reading alone, and avg(A, B, C):**
  - armed positions, events, skill and money;
  - every NO position's skill;
  - the log score against the lock price.
- **B alone and C alone are a replication of A2.** They show whether the rule, fixed beforehand, keeps its edge on fresh readings of the same questions. They are not new events: outcomes and prices are shared.
- **Agreement:** how far the armed sets of A, B and C overlap.

## 5. What follows

- **If averaging sharpens (edge shown),** the v19 reader reads each question more than once. That change is registered forward in the shadow book before it is used.
- **If direction only,** R1 is repeated on pass 2 (July to September) for power before any change.
- **If it blunts,** the reader stays single.
- **The "will this not happen" framing** (`EDGE_LEDGER.md`, calibration fix 4b) needs new question wording. It is a separate test, R2, registered on its own.

## 6. Cost

About 50 sessions at roughly 75,000 to 115,000 tokens each (BT-T2's measured range).
