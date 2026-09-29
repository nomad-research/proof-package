# Nomad

An AI-operated research system that looks for relationships between economic and financial entities that
are *inferable* from public facts but not yet in relative prices. It plays real events against reality,
scores every call, and records which channels actually carried an effect. The open question is whether any
of it can be held as a position.

The system is specified in [`docs/nomad_system_spec_v16_final.md`](docs/nomad_system_spec_v16_final.md) and
built here as `nomad16/`. [`docs/nomad_the_system_as_it_stands.md`](docs/nomad_the_system_as_it_stands.md)
holds the theory, the ideas in plain terms, the intake rules and the data-product spec in one file.

**Read [`STATE.md`](STATE.md) first.** It records, dated, every gap between the spec and the build, the
round played so far, and every kill-test result. The spec is never rewritten to match the code.

## Status, 2026-09-29

- **Built:** the v16 harness (a fresh build, spec §30.3, because the v15 code it evolves wasn't available at
  the time), with a firewall hook, point-in-time fetchers and alternative data (satellite scenes, ship
  counts, event feeds). 53 tests.
- **Played:** round R16-001 (Fermi 2 reactor scram), by a cold operator session. Two segments locked and
  replayed; no basket could be built, because every priced effect sat below its noise band.
- **Kill tests on the v15 record:** K10 and K11 die, K8 and K12 are unreadable there. See `lookbacks/`.
- **v17 (open entity):** V0 (entities, kinds, identity events, person switch) and V1 (documents as evidence, derived
  dating) are built; V2 onward is not. See `docs/nomad_v17_open_entity.md`, `docs/RATIFICATIONS.md` and `STATE.md`.
- **Every round is `learning`** until Rob ratifies the provisional appetite values in
  `config/appetite.json`.

## Layout

```
docs/                   the v16 spec, the theory and system document, OPERATOR.md (how to play a round)
nomad16/                the harness (ledger, derive, reach, stories, construct, paper, walk, lock, fetchers)
nomad16/tests/          smoke tests, including the pre-lock guard
config/                 appetite.json (every value with its status) and seed.json (library, templates, bounds)
firewall/               guard16.py, the PreToolUse hook; guard.py and the allow/deny lists it defers to when idle
rounds/<id>/            one directory per round: reveal, blind pass, operator notes, fetched documents, report
state/nomad16.db        the hash-chained ledger; state/phase.json switches the hook between closed and open
lookbacks/              pre-registered look-backs on the v15 record (K8, K10, K11, K12) and their results
v15/                    the v15 harness and its record, frozen untouched, with a sha256 manifest
STATE.md                what is built, what isn't, and what every result does and doesn't show
```

## Running

```bash
pip install -r requirements.txt
python3 -m pytest nomad16/tests -q       # smoke tests
python3 -m nomad16 help                  # the tool surface (one JSON call per command)
```

Operators read [`docs/OPERATOR.md`](docs/OPERATOR.md). The pre-lock hook (`.claude/settings.json` →
`firewall/guard16.py`) denies web access and quarantined reads while a round is closed.

## Standing rules

- **Pre-registration.** A look-back or test is written down and committed before any number is computed.
- **A negative result is a success.** The purpose is to kill the thesis cheaply if it is wrong.
- **No verdict-governing number has a default.** The config loader refuses a missing value.
- **Point-in-time.** Nothing may be used at time T that couldn't have been known at T.
- **Never rewrite the spec to describe what got built.** Gaps go in `STATE.md`, dated.

## History

The earlier gate tests (LETF rebalancing, stale information and its rates re-run, and two blind runs) all
returned nulls or "not operable", and were retired on 2026-09-29 in favour of the v16 line. Their code,
pre-registrations, data and the consolidated record are in git history: `main` at commit `ca4edf1`.
