# Refiners against producers — result (run 2026-09-30, after the pre-registration commit aa423aa)

Script: `refiners.py`; rule, baskets and thresholds unchanged.

## Main window, 2019-01-02 to 2025-12-30 (35 events)
```
dropped: none | basket sizes {'A': 4, 'T1b': 4, 'REF': 4}
events: 35

trailing crude beta (controlling SPY): producers-B 0.40, refiners 0.33  (lambda for the loading-matched control 0.64)
refiners: mean R +0.039, mean F +0.026, F in the producers' worst quarter -0.080, corr(F) with producers +0.72
baseline A+T1b: CVaR25(F) -0.085, mean R +0.045
A+REF:          CVaR25(F) -0.090, gain -5% (P better 0.29), mean R +0.044 (100% of baseline)
loading-matched control (T1b scaled by lambda, rest cash): gain +22%   ->  gain beyond de-risking -27 points
channel: corr(REF F, change in crack over F) +0.55; corr(change in crack, change in crude over F) +0.37; mean crack change over F +1.30 $/bbl

verdict for this window (needs both windows): (1) downside [fail]  (2) beyond de-risking [fail]  (3) channel [fail]  (4) reaction kept [ok]  -> NOT SUPPORTED
```
## Holdout, 2026-01-02 to 2026-09-29 (9 events)
```
dropped: none | basket sizes {'A': 4, 'T1b': 4, 'REF': 4}
events: 9

trailing crude beta (controlling SPY): producers-B 0.43, refiners 0.38  (lambda for the loading-matched control 0.90)
refiners: mean R +0.030, mean F +0.083, F in the producers' worst quarter -0.026, corr(F) with producers +0.88
baseline A+T1b: CVaR25(F) -0.070, mean R +0.031
A+REF:          CVaR25(F) -0.047, gain +33% (P better 0.87), mean R +0.031 (101% of baseline)
loading-matched control (T1b scaled by lambda, rest cash): gain +7%   ->  gain beyond de-risking +26 points
channel: corr(REF F, change in crack over F) +0.14; corr(change in crack, change in crude over F) +0.18; mean crack change over F +3.50 $/bbl

verdict for this window (needs both windows): (1) downside [ok]  (2) beyond de-risking [ok]  (3) channel [fail]  (4) reaction kept [ok]  -> PARTIAL
```

## Verdict under the pre-registered rule (needs both windows): **not supported**
- **Main window:** no hedge at all. Refiners followed the producers through the fade (correlation +0.72; -8.0% in the producers' worst-quarter fades); the pair's worst-quarter loss was 5% worse than the baseline's; the loading-matched control (just holding less of T1b) did
  better (+22%). Refiners' crude beta (0.33) was not much lower than the producers' (0.40). The channel did not behave as hypothesised: the crack **fell with crude** over the fade (correlation +0.37), it did not widen.
- **Holdout (9 events):** gain +33%, beating the loading-matched control by 26 points, so more than de-risking; but the crack channel test failed (corr with refiners' fade +0.14; crack vs crude +0.18), and 3 events is what the worst quarter is there.
- Builder's expectation (55% / 40% / 50% / about 20% all): the main window came in below it on (1) and (3).

## Where the pooled price tests stand (all of them on oil-spike days, five in a row, all pre-registered; disclosure: several designs were tried on the same claim)
Depth by causal chain (ETFs, then equities), a long at depth as a synthetic short, a synthetic leg at the same loading, and refiners: none found a hedge that beats holding less risk in both windows. The correlation gradient with depth is real; the gains came from lower crude loading, not from decorrelation at a fixed loading.

## What this suggests
A pooled crude-spike study averages over events with different causes and chains (supply, demand, geopolitics), and the mechanism is stated per thesis, conditional on the ACK outcome. The instrument may be the problem: it cannot see a hedge that exists only for a specific outcome
of a specific chain. The next test would need a homogeneous event class where the outcome is observed (a restart duration, an outage length) and the company sets differ by documented positions, and a check first that listed owners respond beyond noise in it at all (K11 found 8 of 87 v15 units did).

## Limits
35 and 9 events; equal weights; a futures crack proxy for four refiners with different slates; long-only equities cannot express a payoff that differs in kind on a fade (convexity needs derivatives, which are for later).
