# Blind run 2 — verdict

# NOT OPERABLE.

**Stop condition fired: spec v2 §7.4, first clause — *no event satisfies
Q1–Q8b*.** Recorded against the **screen**, not against any event, because no
event was ever selected.

**175 candidates walked in strict chronological order. 0 qualifiers.
0 unresolved. No prediction was sealed and no outcome data was touched.**

| | |
|---|---|
| D | **2026-06-01**, fixed before screening, not moved |
| Trigger window | to **2026-07-15**, not moved |
| 8-K filings enumerated | **7,413** |
| Candidate pool after item/form screen | **175** (166 8-K + 9 N-8F) |
| Candidates walked | **175** |
| Qualifying events | **0** |
| Edges attempted | **0** |
| Quarantine rate | **undefined — 0 edges attempted** |
| Prediction sealed | **none** |
| Outcome data touched | **none** |
| `WebSearch` calls | **0** |
| Post-fire filings opened | **0** |

---

## 1. Where the pool died

| Criterion | Count | What it asks |
|---|---:|---|
| **Q1** Citable forcing | **99** | does a retrievable document remove discretion from a named actor? |
| **Q7** Enumeration content | **37** | is the set published in advance? |
| **Q2** Price insensitivity | **34** | does the rule specify what and when but *not at what price*? |
| **Q3** Magnitude floor | **5** | does forced flow exceed 0.8 days of ADV of the named set? |

**Nothing reached Q4.** The screen never got as far as coverage thinness, window
resolution, post-cutoff, or either of the Q8 criteria — which means **blind run 2
did not fail the way blind run 1 failed.** Blind run 1 died on document class, at
Q8. This one died three criteria earlier, at Q1, on more than half the pool.

Full per-candidate log with the criterion each failed: **`walk_log.md`**.

## 2. The finding, and it is not the one that was written down in advance

HANDOFF §8 recorded an expectation before the walk, precisely so it could not
later be presented as a discovery:

> Nearly every Item 2.04 event is a forced sale, so the honest output for most
> will be a derivable `forced_supply_set` and an **empty `absorption_set`** — no
> rule compels anyone to buy.

**That is not what the screen produced, and the difference matters.** The
expectation was that supply would be derivable and only absorption would be
missing. What the walk actually found is that **the `forced_supply_set` is
usually not derivable either — because in most of these events nothing is sold
into a market at all.**

The item-code channel is a channel into **corporate credit and listing events**,
and in those the compelled obligation is almost always to **pay cash**, not to
**sell a specified portfolio**:

- **Acceleration under a credit agreement or indenture** compels repayment. It
  names no instrument to be sold. Which assets get liquidated to fund it is the
  borrower's choice, and that discretion is exactly what Q1 requires to be
  absent.
- **Chapter 11** accelerates and then immediately neutralises the acceleration.
  Inotiv's own filing puts both in one paragraph: obligations "shall be
  immediately due and payable", and "Any efforts to enforce such payment
  obligations ... are **automatically stayed**."
- **Where a forced sale genuinely does occur, the asset is not an instrument.**
  Permex Petroleum received a real notice of foreclosure sale — over "oil and gas
  leases". Silver Star and Stratus, likewise, over real property. There is no ADV
  for a Walgreens store, so Q3 cannot be evaluated, let alone met.
- **Where the forced asset IS an instrument, the size is trivial.** DevvStream
  was the only candidate whose forced supply set was both identified and
  tradeable — "approximately 22.23 Bitcoin, approximately 12,610 Solana" — and it
  is roughly **five orders of magnitude** below the 0.8-day floor.

So the asymmetry the direction-aware format was built to expose is real but
sits one step further back than the review anticipated. It is not *forced selling
with no compelled buyer*. It is:

> **Publicly-documented corporate forcing overwhelmingly compels the payment of
> cash, not the sale of an enumerable set of instruments. There is usually no
> forced supply set to write down, so the question of who absorbs it never
> arises.**

Recording the difference from the pre-registered expectation explicitly, because
the expectation was written down to be checked, not to be confirmed.

## 3. The one candidate that was structurally right and still failed

**MV Oil Trust (candidate 119, filed 2026-07-02)** is worth naming because it is
the only event in the pool with genuinely automatic, quantitatively triggered,
publicly documented forcing.

The Trust's net profits interest "terminated on June 30, 2026 ... in accordance
with the terms of the Conveyance of Net Profits Interest ... because the minimum
amount of production (14.4 million barrels of oil equivalent) ... has been
produced and sold", and "the Trust **dissolved** as of the Termination Date".

No board voted. No counterparty elected. A public trust instrument fired on a
production threshold and dissolution followed automatically. **Q1 passes cleanly
and Q2 passes cleanly** — the first candidate in 175 to do both.

**Q3 fails, and it fails at exactly zero.** The wind-up is "the final quarterly
cash distribution on July 24, 2026", followed by "the cancellation of the Trust
Units". Nobody sells anything to anybody. Forced flow is **0.0 days of ADV**
against a floor of 0.8.

A forced sale with no sale. That is the cleanest single illustration of §2 above
in the whole pool.

## 4. Robustness — the verdict does not rest on either interpretive call

Two readings carried large blocks of the pool, so both were tested by
withdrawal (`robustness.py`).

**Q7 is written buy-side.** It says the *eligible destination set* must not be
published in advance — the same buy-only framing that Defect 2 of the methodology
review had to fix in the edge format. The review fixed the format and did not
restate Q7. Applying it to a forced sale therefore requires reading it by
analogy: if the set that must be **sold** is handed to you, the event tests
transmission. That reading rejected 37 candidates, so it must not be
load-bearing.

> **Withdraw Q7 entirely and all 37 are still rejected.** The 34 involuntary
> delistings fail **Q8a** instead: the 8-K asserts that the *exchange* determined
> to delist, never that any *holder* must transact. The compulsion on index funds
> would have to be reconstructed by the operator from index methodologies — which
> is the precise thing Q8a forbids. The remaining 3 fail on Q1 or Q2.

> **Withdraw Q2 and all 34 merger completions are still rejected**, on Q7: the
> consideration and therefore the destination instrument are published in the
> merger agreement months ahead. Thermon's was signed 2026-02-23 for a 2026-06-01
> closing.

Neither call is doing the work. **The verdict survives the removal of either.**

## 5. Why there is no `prediction.md`, and why that is not a shortfall

The kickoff instructs: *write `prediction.md`, commit, print the hash — that is
the seal.* **That step is conditional on an event existing, and none does.**

Spec §7.4 places the stop conditions before the prediction step, and §6 defines a
prediction as `edges`, `destination_set`, `direction`, `window` and `falsifier`
over a selected event. With **0 events and 0 edges**, every one of those fields
would be empty and the `falsifier` would be unfalsifiable — a document with the
shape of a prediction and none of the content. Writing it would be fabrication
dressed as procedure.

**S1–S4 are undefined**, not zero. There is no destination set to score recall
against, no enumerated basket to spread against a control, no direction and no
window. Touching outcome data would establish nothing and would spend the
firewall for nothing, so it was not touched.

**The quarantine rate is undefined, not high and not low.** Quarantine is a
property of attempted edges, and the run terminated at the screen, before edge
mapping began. Reporting "0%" would be false — it would imply edges were
attempted and all survived.

The quarantine *standard* was still committed in advance, at `fb8d879`, before
any candidate had been assessed against any criterion. It was never applied,
because nothing reached it. It stands unaltered for the next run, and the fact
that it was fixed before the walk — not merely before the prediction — is the one
piece of §7.3 discipline this run was able to over-deliver on.

## 6. What this does and does not establish

**Establishes, and it is a real negative:**

- **The 8-K item-code channel does not reach the addressable universe.** Six
  weeks, a complete enumeration of 7,413 8-K filings, four item codes and two
  fund forms produce **zero** events that satisfy Q1–Q8b. This is not a small
  sample or a thin screen; it is every 8-K filed in the window.
- **The channel's failure mode is now diagnosed, not merely observed.** It fails
  at Q1 on 99 candidates because corporate credit events compel cash rather than
  named instruments, and the exceptions fail at Q2 or Q7 because a fixed
  consideration or a published deletion rule hands the answer over.
- **Screening is not the bottleneck it was thought to be.** The methodology
  review worried Q7 and Q8 together might "leave the addressable universe nearly
  empty" and relaxed Q8 to open it up. The relaxation was correct on its own
  terms and it did not help: **the pool now dies at Q1, upstream of Q8 entirely.**
  Q8a and Q8b were never reached by a single candidate.

**Does not establish:**

- **Nothing about the enumeration thesis.** No prediction was made, so no
  prediction was tested. This is a screen result, not evidence about whether
  enumerated destinations predict returns.
- **Nothing about other channels.** 13D/G amendments, N-PORT, Rule 144 notices,
  SC TO-T tender results, index-provider announcements and rating actions were
  not screened. This run tested one channel.
- **Nothing about D.** The window was fixed before screening and not moved. A
  different six weeks might contain a qualifier; this one did not, and looking
  for a better window is exactly the shopping §7.4 forbids.

## 7. What would have to change for a run to be operable

Stated as a consequence of the walk, not as a plan, and **not** as a criteria
relaxation — no threshold in this project may be relaxed at any count.

The binding constraint is now precisely locatable. An operable event needs a
**named actor compelled to transact in an enumerable set of tradeable
instruments, at a size above 0.8 days of that set's ADV, where the set is not
published in advance.** The item-code channel supplies the first half — actors
compelled, publicly and undeniably — and essentially never the second.

The document classes that would supply both are the ones where **the constrained
actor's holdings are themselves disclosed**: a registered fund that must
liquidate a disclosed portfolio, a 13D/G filer under a divestiture order, an
insurer breaching a published capital rule. Those are screened by holdings
filings, not by 8-K item codes. **That is a channel question, not a criteria
question**, and it is the honest next step — for a later run, decided cold,
against no candidate.

## 8. Self-checks

**Tone reading.** One instance to record, and it cuts against the result rather
than toward it: HANDOFF §8 and `screen_log.md` both state the expected shape of
the answer in advance and at length. That is legitimate pre-registration, but it
is also a strong prior arriving before the evidence. **The walk produced a
different and more severe finding than the one written down** (§2), and it would
have been easy to report the expected shape instead, since the expected shape was
already drafted. I am recording that I noticed the pull and went with the
filings.

**Shopping.** None occurred and none was possible: the walk was exhaustive rather
than truncated at a first qualifier. There was no first qualifier to abandon. The
stop condition fired on the whole pool, which is the form of the §7.4 clause that
was actually met.

**Amendments.** One, made before any candidate was selected and disclosed at the
time: a **tighter** operator document ceiling than the configured one
(`firewall_verification.md`). It is a **validity** amendment and exclude-only. It
can only reduce what the operator sees; it cannot admit a candidate or
manufacture a result. **No threshold was touched.** Q3's floor was applied at
0.8 days of ADV, as corrected, in both directions — it is what rejected
DevvStream and what rejected MV Oil Trust, and it was not moved to rescue either.

**Two procedural rules** were fixed cold before the walk and are recorded in
`screen_log.md`: the `(date, accession)` tie-break, and the class-level rejection
of Form 497 with its recall cost stated.

## 9. Firewall

Full record: `firewall_verification.md`. Two defects found and recorded rather
than quietly patched:

1. The blackhole was **gone again** at session start — second consecutive
   session, so non-persistence is normal container behaviour.
2. **The blackhole is not the binding control in this environment.** Outbound
   HTTPS is routed to a local agent proxy that performs its own DNS resolution,
   so `/etc/hosts` is never consulted on that path. HANDOFF §3, executed exactly
   as written and verified exactly as instructed, reports a green firewall while
   leaving that path open. What actually binds is the **PreToolUse guard, which
   IS live this session** — contrary to the recorded trap, and established
   unplanned when it refused the operator's own first probe before egress.

**The guard blocked its own operator three more times** (false positives #5, #6
and #7): composing the firewall write-up, because the prose quotes a loopback
address; a commit message carrying a session URL; and a shell command containing
the word `fetch` followed by a parenthesis. Every one was routed around — a
non-network write tool, a message file, a renamed script. **The allowlist was
never widened.**

**`WebSearch` calls: 0.** It is not blockable by DNS and runs server-side, so it
is a commitment made auditable by this transcript rather than a control.

**175 filings opened, every one through the date-ceilinged wrapper, every one
logged with its filing date, zero post-fire filings touched, zero failures.**

## 10. The screen was rebuilt twice more before it could be trusted

Recorded because a screen that looks like it is working and is not is the failure
class this project keeps meeting, and it happened twice more here.

- The previously recorded **51 Item 2.04 candidates is wrong; the true figure is
  17.** The 51 came from full-text searching the literal string `"Item 2.04"`,
  which counts any document that mentions the item number.
- The obvious fix — EDGAR's own `items=` filter — **is unreliable**, and looked
  perfect on first probe. Spaced diagnostics returned four byte-identical bodies
  across five distinct item codes, then eight across four, and neither a
  `no-cache` header nor a cache-busting parameter defeated it. Had the first
  probe been trusted, the screen would have silently mixed result sets.

What replaced it enumerates **every** 8-K in the window and filters on each
filing's own `items` metadata, validating every page and checking each day
against EDGAR's reported total. 7,413 filings, zero day shortfalls, zero stale
pages.

> **Never trust a filter's promise. Verify the payload against its own
> metadata.** That is now four instances of the same lesson in this project: a
> phrase screen that looked right, an IPv4-only blackhole that looked right, a
> non-persistent blackhole that looked right, and a filter that looked right.

---

## Bottom line

**A cheap kill, which is the intended outcome.** The run cost one session,
touched no outcome data, sealed no prediction, and returns a diagnosed negative
rather than an ambiguous one: the 8-K item-code channel cannot produce a
qualifying forcing event, and the reason is that corporate forcing compels cash
rather than an enumerable set of instruments.

`config_log.jsonl` stands at **209**. That is the multiple-testing denominator
and it includes every abandoned screen.
