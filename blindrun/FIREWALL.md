# Contamination firewall — configured and verified before the event was requested

Operating procedure v1 §1. Configured 2026-08-18, before the analyst named the
event. Split honestly into what is **structural** (I cannot bypass it) and what
is **procedural** (I can, so it is auditable instead).

## Structural controls — verified

| # | Control | Verification |
|---|---|---|
| 1 | **Knowledge cutoff.** Operator cutoff is end of May 2026; the event postdates it. §1 calls this the strongest point-in-time control available, and it is a capability constraint rather than a promise. | Inherent |
| 2 | **DNS blackhole.** 44 search-engine, news-aggregator and financial-media domains resolved to `0.0.0.0` / `::` in `/etc/hosts`, both A and AAAA records. | `WebFetch https://www.reuters.com/markets/` → *"Claude Code is unable to fetch from www.reuters.com"*. IPv4-only blocking was tried first and **failed** — reuters and google resolved over IPv6 and would have been reachable. Caught and fixed before the run. |
| 3 | **Market-data date ceiling.** `firewall/market_data.py` refuses to run until the analyst supplies `fire_date`, and truncates every series to `<= fire_date` **before** anything is written to disk or printed. The untruncated response is never surfaced. A domain allowlist cannot do this — a price endpoint returns whatever range it likes. | Refuses with no `fire_date` set; logs `rows_returned`, `rows_kept`, `truncated` per call |
| 4 | **Logged fetch path.** `firewall/fetch.py` checks allowlist + denylist, fetches, hashes, and appends URL / doc date / outcome to `firewall/fetch_log.jsonl` (§6 requires this). | Fail-closed on unlisted hosts |

## Procedural controls — auditable, not preventable

| # | Control | Status |
|---|---|---|
| 5 | **`WebSearch` is banned for the entire run.** | **NOT structurally blockable.** Tested with a deliberately inert query (*"boiling point of water at sea level"*, zero market content): it returned results despite the DNS blackhole, because it executes server-side and never resolves a search domain in this container. So this is a commitment, not a wall. It is **auditable**: every tool call appears in the transcript. **Any `WebSearch` call after this document is written is a contamination event and invalidates the run.** The one inert verification call above is the only one, and it is logged in `run_log.md`. |
| 6 | **PreToolUse hook** (`firewall/guard.py`, wired in `.claude/settings.json`) denying WebSearch unconditionally, WebFetch off-allowlist, Bash egress to unlisted hosts, and search-shaped MCP tools. Fails closed on malformed input. | Written and unit-tested — **13/13 cases correct**. **Not live in this session**: project settings are read at session start, verified by a WebFetch to a non-allowlisted host succeeding. It would be live in a fresh session, which is the recommended way to run this protocol next time. |

## Allowlist (fetch permitted)

`sec.gov` and EDGAR endpoints (`data.sec.gov`, `efts.sec.gov`); index-provider
methodology (`spglobal.com`, `ftserussell.com`, `msci.com`, `solactive.com`,
`nasdaq.com`, `crsp.org`, `stoxx.com`, `ice.com`, `lseg.com`); exchange and SRO
notices (`nyse.com`, `cboe.com`, `finra.org`, `dtcc.com`, `federalreserve.gov`,
`ecb.europa.eu`). Issuer investor-relations hosts are added **per event, on
request**, with the reason recorded in `run_log.md`.

Everything else is denied by default. `query1.finance.yahoo.com` is reachable
but only through the truncating wrapper in control 3.

## Standing rules for this run

- **Fetch a known URL: yes. Search: never** — including to find a document I know
  exists. If I need a document and lack its URL, I ask the analyst for it.
- No reading tone. If I catch myself inferring outcome from how the analyst
  phrases something, I log it.
- Every "cannot answer without leaking" is logged and counted. A high count is
  itself a finding: it means the framework depends on information it will not
  have in live operation.


---

## Post-run note — 2026-08-18: the DNS blackhole is NOT durable

Checked at the start of the rates re-run: `/etc/hosts` is back to 4 lines and
**every blackhole entry is gone**. The container regenerated it between sessions.

What this does and does not affect:

- **The sealed blind run is unaffected.** The blackhole was verified live *during*
  that run — by resolution checks and by an actual blocked fetch of reuters.com —
  and `blindrun/guard_decisions.jsonl` records the denials as they happened. The
  verdict stands.
- **The claim needs a qualifier.** Spec v2 §7.1 presents the DNS blackhole as a
  proven structural control. It is structural **for the duration of a session**
  and does not survive a restart. Any future run must re-apply and re-verify it
  at the start rather than assume it persisted — and must verify by checking
  resolution, not by checking that the file was once written.

This is recorded rather than quietly re-applied, because a control believed to be
in force when it is not is the precise failure the protocol exists to catch, and
it has now happened twice in this project — first as the IPv6 leak, now as
non-persistence.
