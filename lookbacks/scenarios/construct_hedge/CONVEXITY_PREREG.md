# Convexity check — pre-registration (written before any number was computed)

*2026-09-30. Rob: combining two long but different narratives over the same underlying, however constructed, equates to a downside-capped, upside-uncapped "hedge". Stated as a payoff shape: the pair is **convex in the underlying's move**
(a floor, open upside in either direction), although each leg alone is roughly linear. This is a direct, exploratory check of the shape on data already in hand; no new design; **no verdict on the mechanism**.*

**Data:** the 67 FOMC statement days and the baskets already fixed: A (JPM BAC WFC C), H (DHI O AMT NEE), the blind pick S and the half-cash control, all as in `PREREG.md`. x = the day's change in the 5-year yield in bp; y = the window return (t0-1 to t0+1, excess over SPY).
**Model, per basket and per pair:** y = a + b x + c |x|. c > 0 is convexity (a straddle-like profile), c < 0 concavity.
**The shape claim is supported by this check only if:** the pair A+H has c > 0 with the 10th percentile of a bootstrap over events (5,000) above 0, and c(pair) exceeds the larger of c(A) and c(H). Also reported: the mean pair return by |x| bucket (under 5 bp, 5 to 10, over 10) and the worst pair return.
**Disclosure:** the events and the basket returns were seen in the construct-then-hedge run. **Expectation (builder's):** about 25% that c(pair) > 0 reliably: the two legs are both close to linear in the yield, opposite in sign, so their sum should be close to linear, with a small slope.
