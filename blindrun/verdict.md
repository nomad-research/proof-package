# Blind run — verdict: **NOT OPERABLE for this event**

Event: Situational Awareness LP, forced liquidation of the public equity book.
Fire date 2026-07-30. Operating procedure v1 §7.

**No prediction was sealed. `prediction.md` does not exist. Steps 5–8 never
happened, and per §8 that is the answer.**

---

## 1. Why §7 fires

Two of the three stop conditions, independently:

| §7 condition | Status |
|---|---|
| "the first qualifying event cannot be mapped to at least one fully-verified edge" | **met** — 0 verified edges |
| "the quarantine rate exceeds the verified rate" | **met** — 3 quarantined, 0 verified, **100%** |

Edges attempted, and the field that failed in each:

| Edge | Failed field | Why |
|---|---|---|
| **1 — the forcing itself** | `trigger_document`, `binding_rule`, `rule_document`, `window_basis` | A 13F-HR is a holdings disclosure. It reports what was held on a date; it contains no clause removing discretion from anyone. |
| **2 — SMH in-kind redemption** | `binding_rule` (third link) | The redemption mechanic and daily basket are documentable, but an authorised participant is not *forced* to sell what it receives. §3.1: correlation is not membership. |
| **3 — Rule 144(e) on SharonAI** | constrains the seller, creates no destination set | The only retrievable rule in the whole event. It bears on timing, not on where capital lands. |

Second-order names — the part of the brief framed as "the harder and more
interesting enumeration task" — were **not** enumerated. §3.1 forbids them
outright, and the candidate count is unbounded, which is precisely why the rule
exists. They are logged as unverified candidates in `edges.md`.

## 2. Primary finding — a framework constraint, not an event failure

**The verification standard structurally excludes private-contract forcing.**

§3.3 requires the document naming the forcing rule to be fetched and the clause
located. That standard is right — it is what stops a plausible-sounding citation
to a rule that does not exist. But it has a consequence that had not been
stated:

> Margin agreements, LPAs, ISDA CSAs and bilateral covenants are where the
> largest and most price-insensitive forced flows live, and **none of them is
> public**. Forcing that lives in a private contract is unmappable by
> construction, no matter how certain the forcing is or how large the flow.

What survives the standard is the publicly-documented subset: index methodology
changes, regulatory deadlines, prospectus mechanics, rating-trigger covenants in
registered debt, corporate-action proration. That subset is real, but it is
**also the subset most likely to be pre-enumerated for everyone** — which is
exactly the defect Q7 was written to exclude.

So the framework is squeezed from both sides:

```
Q7 excludes:  destinations published in advance   (index recon, scheduled flows)
Q8 excludes:  forcing documented only privately   (margin, LPA, CSA, covenants)
                              |
                what remains is narrower than the framework assumed
```

**The addressable universe is smaller than the thesis has been treating it.**
That is the finding worth carrying forward, and it is independent of whether any
prediction would have been right.

## 3. Magnitude — correction to the record

An earlier draft argued Q3 also failed. **That was wrong and is withdrawn.**

A-2's `82.9` is the *multiplier* `M/ADV`, not flow. Realised flow is `M·r/ADV`;
at r = 1% a multiplier of 82.9 becomes **0.83 days of ADV**. A-2's top decile
averages **0.80 days of ADV** and its full range is 0.001–0.80.

| | days of ADV |
|---|---|
| A-2 decile 10, mean realised flow | 0.80 |
| A-2 decile 1 | 0.001 |
| **SA — Core Scientific** | **3.07** |
| **SA — SharonAI (incl. warrants)** | **2.80** |
| SA — Power Solutions / Riot / Nebius | 0.90 / 0.80 / 0.62 |

SA's two largest positions are roughly **3.5× A-2's most extreme decile**. On the
flow measure Q3 is not failed — it is arguably passed. My secondary argument for
stopping collapses; **only Q1 binds**, and the verdict is unchanged because Q1
alone is sufficient. It now rests on one leg rather than two, and that should be
visible.

**The operating procedure's own Q3 needs the same correction.** §2.2 reads
*"82.9× ADV in a liquid sector index produced no measurable effect."* Left as
written, every future screen inherits a magnitude bar roughly 100× too high and
rejects events A-2 never tested. It should read: *no measurable effect at
realised flows up to ~0.8 days of ADV.*

## 4. Process findings — what worked

Recorded as prominently as the failure, because operability is what is under
test and these are the parts that were operable.

1. **The date ceiling was structural, not manual.** `firewall/edgar.py` refused
   three post-fire filings — including the **13F-HR filed 2026-08-14** for period
   2026-06-30, the single document that would have handed over the answer. A
   human promising to check dates has to be right every time; the code is right
   by construction.
2. **Market data was truncated before it reached disk.** 12 post-fire bars
   dropped per symbol across 29 symbols, with counts logged. A domain allowlist
   cannot enforce a date ceiling; the wrapper can.
3. **The quarantine reasoning was committed before any prediction existed.** The
   standard is therefore timestamped independently of any map, so it cannot have
   been reverse-engineered from a destination set someone wanted to write.
   **This should be the default ordering for every future run.**
4. **IPv4-only blocking failed and was caught.** The first blackhole left reuters
   and google reachable over IPv6 — found by checking resolution rather than
   trusting the write.
5. **The guard caught the operator.** Late in the run the PreToolUse hook became
   live and blocked one of my own commands, because the commit message embedded a
   `claude.ai` session URL and the rule is fail-closed on any non-allowlisted
   host in a Bash command. A false positive, but the right kind: the fix was to
   route the message through a file, **not** to widen the allowlist.
6. **Refusing to search was correct**, and the analyst confirmed why: the missing
   document is a document-class fact, not a search failure. No amount of looking
   would have produced it.
7. **Going with the measurement over the framing was correct** — with a caveat
   worth keeping. The measurement I went with was itself mis-scaled, and the
   framing turned out closer to right on magnitude than my arithmetic was. The
   lesson is not "trust the framing"; it is *check the units on your own
   calibration before using it to overrule someone.*

## 5. Run statistics

| | |
|---|---|
| Edges attempted / verified / quarantined | 3 / **0** / **3** (100%) |
| Filings opened (all pre-fire) | 7 |
| Filings refused as post-fire | 3 |
| Leak-refusals ("cannot answer without leaking") | **0** |
| Tone-reading self-checks logged | 2 |
| `WebSearch` calls during the run | **0** (1 inert pre-run verification, logged) |
| Post-hoc screen amendments | **2** — Q7, Q8, both exclude-only, both disclosed |
| Wall clock, event to verdict | ~1 session, inside §0's "a day rather than three weeks" |

## 6. What this establishes, and what it does not

**Does not:** anything statistical. n = 1. This says nothing about whether the
enumeration edge exists.

**Does:** the framework could not be operated on this event, and the reason is
structural rather than incidental. §0 anticipated exactly this — *"a framework
that cannot produce a clean prediction on one event will not produce one on
fifty, and finding that out costs a day rather than three weeks."* It cost a day.

**Next run** starts fresh with **Q1–Q8 applied from the outset** rather than
discovered mid-map. A third post-hoc amendment in a single run would mean the
screen is being fitted to the candidates, and that is now on the record as a
tripwire.
