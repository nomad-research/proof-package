# Test C — Gate 1: do enumerated destinations predict returns?

## Status: NOT STARTED — gated

Specification §4 opens with: *"This is the actual gate. Tests A and B are cheap
proxies; this tests the framework directly. **Do not start it before A and B
return.**"*

A, A-2, B and B-2 have all returned. Gate Spec Amendment 1 §3 narrows the gate
further: **Test C may begin only on a positive B-2 result or a positive A-2
gradient result.** Neither occurred — A-2 was decisively null on every
pre-registered statistic and closed Test A permanently, and B-2 failed its
validity check and is unreadable.

One distinction matters more than the verdicts themselves. The
**stop-permanently trigger did not fire**: it requires a clean null *with
validity passing*, and validity did not pass. The "public but unconnected"
mechanism has therefore not been shown to lack empirical support — it has not yet
been tested with a working instrument. Treating B-2's unreadable result as a
negative is the easiest available mistake, and the one the pre-registrations were
written to prevent.

See [`../SUMMARY.md`](../SUMMARY.md) for the cross-test position and for the
one-day fix that would make every block already run readable.

Test C costs roughly three weeks. Ordering the tests by cost-per-bit was done
precisely so that the decision to spend it could be taken for the price of a few
days. That decision belongs to the operator, not to this code, and the two
results files state plainly what each test implies for it.

## What already exists

The shared infrastructure Test C would need is built, unit-tested, and in use —
it was built once for all three tests rather than deferred:

| Component | What it does for Test C | Where |
|---|---|---|
| `pit_corpus.py` | Freezes the corpus at t₀. As-of queries return only documents with `known_from <= as_of`, so a mapping run cannot read post-dated text. Clauses must be located **verbatim** in the retrieved body or the write is refused — an assertion that cannot be found is rejected at the storage layer rather than trusted. Stores `recognised_from − known_from`, the recognition-lag gap the specification calls a research object in its own right | `nomad/infra/` |
| `inference_family.py` | Tags every link with an inference family at enumeration time, maintains the quarantine (unverified edges are recorded, never silently dropped) and reports the quarantine rate, and computes effective breadth as `N_eff = N²/(1'C1)` — which is what tells you whether you have N independent bets or only as many as you have families | `nomad/infra/` |
| `cost_model.py` | Corwin–Schultz spread estimation for the illiquid names Test C would actually trade. Note Test A's finding that Corwin–Schultz is badly upward-biased for *liquid* instruments — for Test C's universe it is the right tool, which is why it was kept | `nomad/infra/` |
| `config_logger.py` | The multiple-testing denominator, counting abandoned and failed evaluations too | `nomad/infra/` |
| `deflated_sharpe.py` | DSR and CSCV probability of backtest overfitting | `nomad/infra/` |

## What would still have to be built

Nothing below has been started, because building it now would be scope creep
against an unvalidated core (specification §6).

1. **Event list construction from a news or filing source** — not from memory.
   Memory selects for cascades that resolved dramatically, which is exactly the
   bias that would make the result look better than it is.
2. **The forcing-chain extractor**: root event → condition Y → rule Z binds for
   actor A → eligible destination set D, with every edge resolving to a retrieved
   document and a located clause.
3. **Verification consensus across ≥3 model families** for factual extraction
   only — does this document exist and say this. Explicitly **not** for judgment
   calls; §4.4 notes correlated errors make panels underperform the best single
   model on judgment, and §6 lists multi-agent judgment ensembles as a non-goal.
4. **Matched control sampling** on observables available at t₀ only.
5. **Contamination split** at the mapping model's training cutoff, with both
   subsamples reported separately. §4.5 names this the primary validity threat —
   a model trained through the outcome period will "discover" connections that
   were only obvious afterwards, and a point-in-time corpus stops it reading
   post-dated text but does not stop it knowing how things turned out.

## Two numbers that must never be blended

Specification §4.1, restated here because it is the distinction most likely to be
lost in a summary:

- **Destination recall** — did realised flow land in the enumerated set? A
  property of the *map*. Binary and unambiguous.
- **Return spread** — enumerated set versus matched control. A property of the
  *market*.

High recall with zero spread means the map is right and already priced. That is a
completely different failure from a wrong map, and the correct response to each is
different. Reported as one blended number, they are indistinguishable.

Related, from §4.6: **source recall and destination recall are also separate
numbers.** Sources — mandates, covenants, filings — are well documented.
Destinations, where money actually lands, are often opaque. Enumeration is
expected to be structurally stronger on the source side, and positions depend on
the destination side. Destination recall is the number that predicts losses.
