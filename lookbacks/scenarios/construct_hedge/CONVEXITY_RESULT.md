# Convexity check — result (run 2026-09-30, after the pre-registration commit b8536eb)

```
events 67; x in bp: mean |x| 5.8; buckets: <5bp 36, 5-10bp 19, >=10bp 12

series            b (slope)  c (convexity)  c 10th pct     <5bp   5-10bp   >=10bp    worst
A banks             0.00041        0.00030    -0.00069  +0.0006  -0.0123  +0.0028  -0.0967
H hedge basket     -0.00107       -0.00012    -0.00080  -0.0032  -0.0028  +0.0052  -0.0542
S blind pick       -0.00117        0.00049    -0.00036  +0.0003  +0.0015  +0.0132  -0.0408
pair A+H           -0.00033        0.00009    -0.00060  -0.0013  -0.0075  +0.0040  -0.0523
pair A+S           -0.00038        0.00040    -0.00035  +0.0005  -0.0054  +0.0080  -0.0442
control 0.5A        0.00021        0.00015    -0.00035  +0.0003  -0.0061  +0.0014  -0.0483

verdict (pre-registered): c(pair) +0.00009 > 0 with a 10th percentile above 0 and above max(c(A), c(H)) = +0.00030  ->  NOT SUPPORTED HERE
```

## Verdict under the pre-registered rule: **not supported here**
The pair A+H has c = +0.00009 (10th percentile of the bootstrap -0.0006), below A's own c of +0.0003. The shape (a floor with open upside in either direction) is not present in this pair. Builder's expectation (about 25%): consistent.

## What it says
- Both legs are roughly **linear** in the yield move (A slope +0.0004, H slope -0.0011; convexity near zero for each), and of opposite sign. Two linear legs of opposite slope sum to a near-linear leg with a small slope. The complement hedge from the earlier test lowers the worst case (beats cash on dovish days) but is not convex.
- The by-size table is noisy and not monotone (the pair: -0.13% under 5 bp, -0.75% at 5 to 10 bp, +0.40% at 10 bp or more; only 12 events at 10 bp or more).
- What the shape needs, then, is not two opposite-sloped longs but **two one-sided (kinked) legs**: each responds to the state in one direction and is flat, or capped in loss, in the other. Their sum is the straddle-like profile.

## Limits
67 events, one underlying; exploratory; the legs were chosen as complements, not as one-sided; a 2-day window; convexity estimated with a single |x| term.
