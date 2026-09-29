# STATE — Nomad v16, as built here

*Kept beside the spec, per spec v16 §0: gaps between spec and build are recorded here, dated,
and the spec is never rewritten to match the code. Spec: `docs/nomad_system_spec_v16_final.md`
(Section E of `docs/nomad_the_system_as_it_stands.md` is the same text).*

## 2026-09-29 — first build

### Build path: the §30.3 fallback, not evolution in place

Spec §30 evolves the v15 harness in place (`Documents/nomad` on Rob's machine, 146 MCP tools,
15 rounds of stores). **That harness is not in this repository and was not reachable from the
build session.** On the user's instruction, v16 was built fresh here as the package `nomad16/`
(spec §30.3). The limit that forced it: the code and stores to evolve were absent.

Consequences, stated so nobody reads more into this build than it holds:

| Spec item | Status here | Why |
|---|---|---|
| §30.2 step 1 (freeze v15, verify its chain) | not applicable | no v15 stores |
| Migration report (§30.1), absence record recomputed over rounds 1–15 | not run | no v15 record. `absence_record` computes both rules for v16 rounds |
| Wall-map re-run (smoke 3), K7, K8, K9 rebuild, K10, K11, K12 look-backs | **cannot run** | every one reads the v15 record |
| Templates, vocabularies, bounds "authored from rounds 1–7 only" (§31 guards) | not satisfiable | authored by the builder from general knowledge and statute text before any v16 event was enumerated (`config/seed.json`, committed before enumeration) |
| `library_as_of`, tide-counted support, `weight_state` | table and reader built; every rule reads `untested_as_carried` with 0 trials | no resolutions banked yet; `rebuild_library_stats` equivalent not written |
| Second scorer, disputes, scorer bias | not built | |
| Operator term (fallback hierarchy, §8) | always the typed gap `not_covered` | no clean resolutions for any operator model yet |

### The tool surface is a CLI, not an MCP server

`python -m nomad16 <tool> '<json>'` with the spec's tool names minus the `nomad_` prefix
(`python -m nomad16 help` lists them). The operator runtime is agnostic either way (§28); a
FastMCP wrapper is a thin later addition. Every response carries `harness_version`,
`logic_version`, `config_hash` and chain heads (§17).

### The hook

`firewall/guard16.py` replaces `firewall/guard.py` as the PreToolUse hook (`.claude/settings.json`).
It reads `state/phase.json`, which the harness rewrites on every round transition:

- **closed** (`admitted`, `pre_lock`, `walking`): WebSearch, WebFetch and MCP tools are denied. Bash may
  make a single `python -m nomad16 …` call (the harness bounds every read by the clock); any other egress
  is denied. Paths holding post-cutoff material from earlier work are quarantined (blind runs, fetched
  filings, the NRC page cache, record files, `.git`).
- **open** (`live`, `scored`): live retrieval allowed.
- **idle**: the old blind-run guard applies unchanged.

`operator_manifest` sets `hook_verified` from the guard's own log (a denied WebSearch/WebFetch after
reveal), never from the operator's say-so. **Known blind spot, stated rather than relied on:** a Python
*file* the operator writes and runs can reach the network without the guard seeing a URL. The harness's
own fetchers are bounded; a script that bypasses them is a firewall violation by procedure, not by
structure.

### Appetite: provisional, so every round is `learning`

`config/appetite.json` holds 69 values: 17 ratified or carried from §33.1, and **52
`provisional_unratified`**, set by the builder on the user's instruction (2026-09-29) so a round can run
end to end. The loader still refuses any missing value. **Any round that reads a provisional value is
classed `learning`** (recorded per segment in `round_meta`) and never counts toward K9 or K13. Rob
ratifies by flipping a status to `ratified` in a dated commit. The decision-model and data-product
values of §33.2 are deliberately left unset.

### Tracks not built

- **T2, decision models:** no `decider`, no Laya, no wiring, spread probes, locator, notice watch or
  procedural chains. Attention order is the operator's. Forced-ACK windows come from a statute bound or
  the `DUE_AT_MAX_DAYS` cap, never from a docket count.
- **T1, data product:** in-harness adapters stand in for it and map `knowable_at → knowable_from`
  directly: NRC event notifications and daily reactor status, EDGAR (filing-date ceiling applied in memory
  before anything is saved or printed), Wayback (latest capture at or before `as_of`), Yahoo prices
  through the vintage store, and the alternative-data adapters below. `RECORDING` is missing, so
  enumeration is `source_mode = manual`. `REVISION_CHAINS` is missing, so PortWatch and USGS values are
  flagged as restatable.

### Alternative data (added 2026-09-29 at the user's request)

`nomad16/altdata.py`, via `alt_probe` and `alt_fetch`. Every source gets a stated `knowable_from` rule
(lags are appetite `ALT_LATENCY`), a discriminating probe that must pass before use, and an in-memory
re-check of every record against the bound. Server-side date filters are never trusted.

| Source | Probe 2026-09-29 | Notes |
|---|---|---|
| `s2_scenes`, `s2_image` (Sentinel-2 L2A via Planetary Computer) | PASS | knowable from the product's processing time + 6 h. Crops render server-side to PNG, which the operator reads as an image; a crude bright-object count (ships on water, flares) is attached and may **propose, never support** |
| `portwatch_chokepoint`, `portwatch_port` (IMF PortWatch, AIS-derived daily transits and port calls by vessel type) | PASS | record date + 9 days (weekly publication) |
| `gdelt_events` (GDELT 2.0 15-minute exports) | PASS | knowable at the export's timestamp; counts by CAMEO root and mean Goldstein |
| `ioda` (internet-outage signals by country) | PASS | sample time + 1 h |
| `usgs_quakes` | PASS | origin + 1 h; magnitudes revisable |
| `firms` (NASA active fires) | NOT_COVERED | adapter built; needs `FIRMS_MAP_KEY` (free) as an environment secret |
| `gfw` (vessel presence), `acled` (conflict events), `black_marble` (night lights) | NOT_COVERED | need `GFW_TOKEN` / `ACLED_KEY`+`ACLED_EMAIL` / `EARTHDATA_TOKEN`, and an adapter |

Not yet added: Sentinel-1 radar rendering (sees through cloud and at night; the obvious next source for
straits), OpenSky flight history (needs an account; its anonymous API is live-only, so it can't serve a
backfilled round).

### Interpretations the spec leaves open (each is a build choice, not a claim)

- **Segment 0's clock is `event_date`** (a date). Documents with `knowable_from` on or before it are legal;
  prices use sessions strictly before it; the backfilled fill is the first close after the event's
  public `knowable_from`, and the next session when only a date is known.
- **Units.** S(ω) is the expected move divided by the tide-hedged residual σ at the horizon (√h scaling).
  A loading is the response to a one-sd daily story move in σ units. The hedge constraint uses the
  spec's form with `HEDGE_EPS = 0.002` (story exposure at most 0.2% of gross notional per sd).
- **Flat outcome:** every instrument's expected move is inside its own hedged-residual band. **Visibility:**
  |S⊥| against `VIS_K` × the median per-instrument band in σ units.
- **Horizon:** business days from the clock to the ACK window's end, capped at 63.
- **Instruments:** stocks and ETFs (stress-capped under a stop at the stress quantile) and bought calls
  and puts (hard-capped, always `modelled` with Black-Scholes on realised vol). Not built: debit spreads as
  packages, condors, credit spreads, event contracts, credit protection, and the sell-premium shape (it
  needs a quoted distribution).
- **Paper split:** narrowing and timing are zero (no quoted distribution, no quoted options). Leaks are
  hedge slippage: Σ weights × loadings × realised factor moves.
- `absorbed_by_slack` and `no_sink` each fire only on a stated fact for the effect kind (open call §34).

### Test status

`python -m pytest nomad16/tests -q`: 40 passed. Covered: smoke 1, 2, 5, 6, 7, 8, 10, 15–29, chain
tamper, loader refusal, construction building a structural pair, the paper round trip, and the guard.
Not covered: 3, 4, 9, 11–14 (v15 record, decider, data product).
