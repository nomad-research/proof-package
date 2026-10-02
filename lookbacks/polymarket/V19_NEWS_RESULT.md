# The reader with news (result)

**Process.**
- Registered in `V19_NEWS_prereg.md` (commit `5bced1d`; addenda A1 to A3) before any headline was kept or any session ran.
- Headlines from Google News, fetched on Rob's machine (commit `2faa9dc`):
  - 330 questions covered, with no request errors;
  - none published after its lock;
  - none naming a prediction market or odds;
  - a median of 25 headlines a question, and 14 questions with none.
- 55 cold sessions (N4: 25, N5: 30), all passing V1's audit, with no recognised outcomes.
  - 12 written 0% values were counted as 1%.
  - Frozen before any score (manifests `8179f76a…` and `8d25d603…`, commit `677b88d`).
- Scored at real prices (the last trade print within 48 hours before the lock) by `v19_news.py score` into `v19/news_result.json`.
- The comparison is the frozen cold readings of the same 330 questions.

## 1. The declared statistics (95%, resampled by occasion)

| | Positions | Events | Mean | 95% interval | Reading |
|---|---|---|---|---|---|
| **1. E1 with news:** every NO position | 624 | 250 | +2.5¢ | −2.8 to +7.3 | direction only |
| **2. A2 with news:** armed NOs | 89 | 60 | +2.3¢ | −9.6 to +13.4 | direction only |
| **3. What news adds to E1** (news minus cold, same questions) | 624 against 624 | 180 occasions | +1.7¢ | −0.8 to +4.5 | direction only |

## 2. Secondary (declaring nothing)

**News makes the reader more accurate.**

| | Cold | News | News minus cold |
|---|---|---|---|
| Log score against the real price (per contract; 0 means as good as the market) | −0.084 (−0.123 to −0.048) | −0.036 (−0.078 to +0.008) | **+0.048 (+0.025 to +0.074)** |
| Location (N1): ladders, touch and dates, the news median against the cold median | | | closer 81, farther 52, tied 103; **mean +0.12 (+0.03 to +0.21)** |

**But the betting edge barely moves.**

| | Cold | News |
|---|---|---|
| E1 skill | +0.7¢ (−3.9 to +5.0) | +2.5¢ (−2.8 to +7.3) |
| E1 money | +2.9¢ | +4.5¢ |
| A2 skill | +4.0¢ (−8.7 to +15.8) | +2.3¢ (−9.6 to +13.4) |
| A2 money | +12.9¢ (+0.2 to +25.0) | +11.8¢ (−0.8 to +23.1) |
| A2, news minus cold | | −1.7¢ (−10.5 to +6.8) |
| E1 strict window (from 1 June), news minus cold | | +2.2¢ (−1.5 to +6.2) |

**By kind (E1 with news):**
- percent questions +12.9¢ (+1.7 to +21.4), but on 7 events (cold: +12.1¢);
- pick-the-winner +2.5¢;
- ladders −1.0¢;
- touch +3.4¢.

**The P5 filter's conditions with news (A2):** no pattern.
- Conviction under 10%: +3.7¢; 10% or more: +0.9¢.
- At least 3 days: −4.1¢; under 3 days: +9.8¢.
- Not touch: +5.0¢; touch: −2.8¢.

**A3 on the news readings** blocks what does well: blocked +26.2¢ (18 positions), passed −3.7¢ (71 positions). It fails again.

## 3. Reading

- **News helps the reader know the present, as expected.**
  - Its probabilities move most of the way toward the market's: log score −0.084 cold, −0.036 with news.
  - Its location calls get closer to what happened.
  - The losing divergences in the ledger (N1, N6) come largely from being blind to the present, and news repairs much of that.
- **It does not create a betting edge on the backtests.** E1 and A2 stay direction only, and news adds +1.7¢ to E1 (direction only).
- **Accuracy is not edge.** News is what the market already knows. A reader that reads it agrees with the market more, so its disagreements are fewer and no sharper. That is the salience risk flagged when news was proposed: what news gives in accuracy, the crowd has already priced.
- **Limits of this test:**
  - headlines only (no article text, which could leak);
  - keyword-matched;
  - a 7-day window.
  A fuller news feed could do more. One step (news in a single reading) was tested, not the two-step design (habit anchor first, then facts).

## 4. What follows (registration §4)

- **Statistic 3 is direction only.** So the forward sweep decides, and news enters forward only as a registered variant. The backtests do not show that news earns its place in belief.
- **Neither E1 nor A2 returns to the design on backtest evidence.**
- **What stands on backtests at real prices** (decision 23): the mention edge (E3b), +8.1¢.
