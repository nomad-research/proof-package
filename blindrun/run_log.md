# Run log — Nomad blind prediction test

Recorded as the run proceeds, not reconstructed afterwards (§6).

## Clock

| Milestone | Timestamp (UTC) |
|---|---|
| Firewall configured and verified | 2026-08-18 |
| Event received | — |
| Prediction sealed | — |

## Clarifying questions and refusals

Count of "cannot answer without leaking": **0** so far.

| # | Question asked | Answer | Leak-refusal? |
|---|---|---|---|

## Tone-reading self-checks

| # | Note |
|---|---|
| 1 | None yet. The analyst has not described the event. |

## Firewall events

| # | Event |
|---|---|
| 1 | IPv4-only DNS blackhole tried first and **failed** — reuters.com and google.com resolved over IPv6 and remained reachable. Fixed by adding `::` entries before the run began. Recorded because a firewall that was believed to work and did not is the exact failure this protocol exists to catch. |
| 2 | PreToolUse hook written and unit-tested 13/13, but confirmed **not live** mid-session (a WebFetch to a non-allowlisted host succeeded). Primary enforcement is therefore the DNS blackhole plus the logged fetch wrapper. |
| 3 | One `WebSearch` call made **before** the run, deliberately, to establish whether search is structurally blockable. Query: *"boiling point of water at sea level in celsius"* — inert, zero market content. Result: search is **not** blockable by DNS; it executes server-side. This is the only WebSearch call of the run; any further one invalidates it. |
