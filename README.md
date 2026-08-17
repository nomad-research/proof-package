# Nomad — Gate Tests

Three tests, ordered by cost-per-bit, of a single claim: that **enumerating which
entities are forced to transact, and where that forced capital must land, predicts
returns better than chance — and that this survives even though the underlying
mechanism is well documented.**

Each test can kill the ones below it. **A negative result is a success.** The
purpose is to kill the thesis cheaply if it is wrong, not to confirm it.

| Test | Question | Kills what if it fails | Result |
|---|---|---|---|
| **A** — LETF rebalancing | Does perfectly enumerated forced flow still pay? | Sets the ceiling: if perfect enumeration pays nothing, imperfect enumeration pays less | **FAIL** — [`tests_a/results.md`](tests_a/results.md) |
| **B** — Stale information | Does "public but unconnected" survive post-2012? | The bitemporal / backward-reading thesis | **NOT REPLICATED** — [`tests_b/results.md`](tests_b/results.md) |
| **C** — Gate 1 | Do enumerated destinations predict returns? | The whole framework | **not started, gated** — [`tests_c/README.md`](tests_c/README.md) |

**Start here: [`SUMMARY.md`](SUMMARY.md)** — the cross-test verdict, the
recommendation on Test C, and the qualifications that matter.

## Layout

```
nomad/infra/            shared infrastructure, built once, used by all three tests
  config_logger.py        append-only evaluation log — the multiple-testing denominator
  deflated_sharpe.py      Bailey & López de Prado DSR + CSCV probability of overfitting
  pit_corpus.py           point-in-time document store (valid_from / known_from / retrieved_at)
  cost_model.py           half-spread + square-root impact; Corwin-Schultz spread estimation
  inference_family.py     link tagging and effective-breadth measurement
nomad/tests_common/     unit tests for the above
tests_a/                Test A: preregistration, pipeline, analysis, results, decay curve
tests_b/                Test B: preregistration, pipeline, analysis, results
tests_c/                Test C: gated — not started unless A or B leaves the thesis alive
config_log.jsonl        every evaluation ever run, including abandoned ones
```

## Non-negotiable methodology

These are not stylistic. Each guards a failure mode identified in advance.

1. **Pre-registration.** `preregistration.md` is committed before any analysis code
   is written. Changes are dated amendments appended at the bottom, never edits.
2. **Configuration logging.** Every parameter combination, universe filter, window
   and threshold *ever evaluated* — not only those reported — is appended to
   `config_log.jsonl`. That count is the denominator for multiple-testing
   correction. Without it the results are uninterpretable.
3. **Significance hurdle.** `t > 2.78` (Harvey, Liu & Zhu), plus the Deflated
   Sharpe Ratio computed against the trial count in `config_log.jsonl`.
4. **Point-in-time discipline.** No data that was not available at the decision
   timestamp. Where a survivorship-free source is unavailable, that is stated in
   the output and the result is labelled upward-biased.
5. **Costs.** Every return figure is reported gross *and* net. A gross-only number
   is not a result.

## Reproducing

```bash
pip install pandas numpy scipy statsmodels requests pytest
python -m pytest nomad/tests_common -q          # infrastructure tests
python -m tests_a.pipeline                      # fetch and cache Test A data
python -m tests_a.analysis                      # run Test A, write results + decay curve
python -m tests_b.pipeline                      # fetch and cache Test B data
python -m tests_b.analysis                      # run Test B, write results
```

Data is fetched from public sources and cached under `data/cache/`. Sources and
their limitations are documented in each test's `preregistration.md` §7.

## Explicit non-goals

Not built here, deliberately: live trading or broker integration; options
strategies; position sizing, portfolio construction or risk systems; a
general-purpose event detection pipeline; any signal that cannot be traced to a
retrieved document with a located clause; multi-agent judgment ensembles.
