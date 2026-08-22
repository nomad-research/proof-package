# Test B-3 — Rates re-run: pre-registration

**Status:** committed before any B-3 analysis was run.
**Date:** 2026-08-18
**Spec:** `nomad_spec_v2.md` §9 item 1, §8 standing methodology.

Amendments appended and dated, never edited in place. Per spec v2 §4:
**validity amendments are learning, threshold amendments are fitting.** No
threshold in this document may be amended at any count.

---

## 1. What changes, and what does not

**Changes: the outcome variable only.** Every macro block so far used SPY, and
three of four failed the pre-registered validity check — the instrument could not
detect a reaction even to genuinely *new* information. A blind instrument's null
on stale information carries no information at all.

An equity index's daily return is dominated by everything other than a macro
release. The front end of the curve reprices sharply on inflation and activity
data. Gilbert et al. used Treasury futures alongside the S&P for exactly this
reason.

**Unchanged:** the vintage assembly, first-print discipline, archive-measured
release dates, the ordering verification, the influence diagnostic, the expanding
-window prediction, the t > 2.78 hurdle, and the config log.

## 2. Outcome variables — all three run, disagreement reported not resolved

| Role | Series | Units | Source |
|---|---|---|---|
| **Primary** | 2-year Treasury yield, `DGS2` | **change in yield, basis points** | FRED |
| Secondary | `TLT` | daily return | Yahoo |
| Secondary | `IEF` | daily return | Yahoo |

If the three disagree materially, that disagreement is **reported as the
finding** rather than resolved by picking one.

## 3. Event windows — registered in advance, not mid-run

Macro releases land **08:30 ET, before the equity open**. A close-to-close window
brackets the release plus six and a half hours of unrelated news.

- **Primary: overnight** — prior close to release-day open.
- **Secondary: close-to-close.**

This was added mid-run last time (amendment 8) and had to be fenced because it
could have manufactured readability. Registering it here removes that concern
entirely.

### 3.1 A constraint on `DGS2` that must be stated now

`DGS2` is the H.15 constant-maturity series: **one observation per business day**,
with no open and no close. **The overnight window does not exist for it.** The
only window available is the day-over-day change.

That change spans roughly 15:30 ET on `t−1` to 15:30 ET on `t`, so it does
bracket the 08:30 release — but it also carries a full session of other news, and
it is therefore the *close-to-close* analogue rather than the overnight one.

Consequence, fixed here: **the primary outcome cannot use the primary window.**
`DGS2` is primary on *instrument* grounds (it is the cleanest read on the front
end); `TLT` and `IEF` are the only series that can carry the overnight window.
Both facts are reported side by side and neither is quietly dropped.

## 4. Sign conventions and the built-in coherence check

Stronger activity or higher inflation raises yields. So for a positive surprise:

| Outcome | Predicted sign of the surprise coefficient |
|---|---|
| `DGS2` change | **positive** (yields rise) |
| `TLT` return | **negative** (bond prices fall) |
| `IEF` return | **negative** |

This gives a free coherence check. If `DGS2` and `TLT`/`IEF` produce coefficients
with the *same* sign, the instrument is not measuring what it is supposed to
measure, and that invalidates the block regardless of significance. Reported
explicitly.

Note `DGS2` is in **basis points** and `TLT`/`IEF` in fractional returns, so
coefficient magnitudes are not comparable across them. Only signs and
t-statistics are.

## 5. Order of operations — not to be skipped

### Step 1 — VALIDITY, for every block, before anything else

```
outcome(m) = a + b1·predicted_z(m) + b2·surprise_z(m) + e(m)
```

Newey–West HAC, 3 lags. **`b2` is examined first.**

- **Pass:** |t(b2)| > 2.78 **and** the sign matches §4.
- **Fail:** the block is **UNREADABLE**. Its `b1` is not interpreted, not
  reported as a null, and not used in any conclusion.

Validity results for all blocks are reported **before** any `b1` result is
computed or shown.

### Step 2 — predictable component, only for blocks passing validity

Statistic: t on `b1`. Hurdle: |t| > 2.78. Null: `b1 = 0` — the predictable part
was already public when the announcement landed.

### Step 3 — the pre/post-2012 split, only for B1 and only if it passes validity

Single pooled interaction so the *difference* carries a standard error:

```
outcome = a + b1·predicted_z + b1p·(predicted_z × post2012)
            + b2·surprise_z + b2p·(surprise_z × post2012) + c·post2012 + e
```

Decay statistic: t on `b1p`. **This is the primary output of the whole
exercise** — B1 is the only block spanning 2012, so if it passes validity on
rates, its split becomes readable for the first time in the project.

### Step 4 — influence diagnostic on every reported coefficient

Refit dropping the 1, 2, 3 and 5 observations with the largest Cook's distance.
A coefficient that survives the full sample but collapses on removal of two
points is leverage, not an effect.

## 6. Blocks

| Block | Indicator | Sample | R² | Role |
|---|---|---|---|---|
| **B1** | Industrial Production | 2003-07 to 2026-07, 275 | 0.49 | **the prize** — only block spanning 2012 |
| **B2** | CFNAI | 2017-10 to 2026-07, 104 | 0.92 | **positive control** — already passed validity on SPY |
| **B-2** | Core PCE | 2005-02 to 2026-07, 253 (83 pre / 170 post) | 0.28 | weak analogue, but it has the sample |

**B2 is the control and it does real work.** It passed validity on SPY at
t = 4.51. If CFNAI does **not** also pass on rates, the rates instrument itself
is suspect, and that is reported as a finding about the instrument rather than
about any block.

## 7. Stop conditions — pre-registered, per spec v2

| Outcome | Consequence |
|---|---|
| **Validity passes + predictable-component effect present** | The mechanism underneath the enumeration thesis has support. |
| **Validity passes + null** | **THE STOP TRIGGER FIRES.** The first clean stop in this project. To be stated plainly, not softened, and **no fourth instrument will be proposed.** |
| **Validity fails on rates too** | The instrument class is not the problem. The stale-information line closes as **unanswerable with free data.** Also a legitimate stop. |

In every branch the outcome is a stop. This test is designed to end the line,
not to extend it.

## 8. Multiple testing

Every configuration evaluated — including abandoned ones — is appended to the
existing `config_log.jsonl`, which stands at **162** entries. Any Deflated Sharpe
is computed against the **cumulative** count, not against B-3's trials alone.

Three outcomes × two windows (where available) × three blocks is a deliberate
expansion of the trial count, and it is logged as such. It is justified because
the alternative — picking one outcome in advance and reporting only that — would
hide exactly the disagreement §2 requires to be surfaced.

## 9. Known limitations, stated in advance

1. **`DGS2` cannot use the overnight window** (§3.1). The primary instrument and
   the primary window cannot be combined.
2. **`TLT` and `IEF` are duration proxies, not the front end.** TLT is 20y+ and
   IEF is 7–10y; neither is the 2-year point. They are the only free instruments
   with an intraday open, so they carry the overnight window despite being the
   wrong maturity for maximum macro sensitivity.
3. **B-2's core PCE remains a weak analogue** at R² = 0.28. Changing the outcome
   variable does not fix a weak predictable component.
4. **A rates outcome does not make the LEI available.** This tests the same
   substitutes as before, better measured. It is not a replication of Gilbert
   et al.
5. **Positive validity would not retroactively make the SPY blocks readable.**
   It would establish that the rates instrument can see macro news, and any
   conclusion would rest on the rates runs alone.

---

## Amendments

*(none)*
