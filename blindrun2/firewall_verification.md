# Blind run 2 — firewall re-application and verification

**Session start: 2026-08-22.** Re-applied and verified per HANDOFF §3, which is
mandatory and must not be assumed. Verified **by resolution**, never by checking
that the file was written.

## State found at session start

`/etc/hosts` contained **4 lines** and **zero** blackhole entries. The blackhole
had not persisted, exactly as REPORT.md §8 bug 9 predicted. This is now the
**second consecutive session** in which it was found gone; non-persistence is
confirmed as the normal behaviour of this container, not an anomaly.

## What was applied

44 denylist domains × 2 hostnames (`d`, `www.d`) × 2 record types
(`0.0.0.0` A, `::` AAAA) = **176 host entries**. Prior `/etc/hosts` backed up to
`firewall/hosts.backup.<epoch>`.

## Verification by resolution

| Host | A | AAAA | Expected |
|---|---|---|---|
| www.reuters.com | 0.0.0.0 | (none) | denied |
| reuters.com | 0.0.0.0 | (none) | denied |
| www.google.com | 0.0.0.0 | (none) | denied |
| google.com | 0.0.0.0 | (none) | denied |
| seekingalpha.com | 0.0.0.0 | (none) | denied |
| www.bloomberg.com | 0.0.0.0 | (none) | denied |
| x.com | 0.0.0.0 | (none) | denied |
| finviz.com | 0.0.0.0 | (none) | denied |
| substack.com | 0.0.0.0 | (none) | denied |
| www.sec.gov | 23.62.85.147 | (none) | allowed |
| efts.sec.gov | 23.194.147.250 | (none) | allowed |
| data.sec.gov | 23.194.147.250 | (none) | allowed |

## Finding 1 — IPv6 is moot in this container, and that must not be mistaken for a fix

`getent ahostsv6` returns nothing for **any** host, including `www.sec.gov`,
which resolves fine over A. `ip -6 addr` shows no inet6 address and there is no
default v6 route. **There is no IPv6 path in this container at all.**

The `::` entries were written regardless, because the cost is zero and the
failure mode they guard (REPORT.md §8 bug 6) is one this project has already
paid for once. But the honest statement is that IPv6 is closed here by absence of
a network stack, not by the blackhole. In a container that *did* have IPv6, the
`::` lines would be doing the work.

## Finding 2 — NEW DEFECT. The DNS blackhole is not the binding control in this environment

The environment sets an HTTPS proxy on loopback port 42555, together with
`CLAUDE_CODE_PROXY_RESOLVES_HOSTS=true`.

All outbound HTTPS is routed to that local agent proxy, **which performs its own
DNS resolution**. A request routed through it therefore never consults
`/etc/hosts`, so the blackhole does not constrain it. HANDOFF §3, executed
exactly as written and verified exactly as instructed, would report a green
firewall while leaving this path open.

This is the same class of failure as the IPv6 leak and non-persistence: **a
control believed to be in force that is not.** It is recorded rather than quietly
patched, per the standing rule.

### What is actually holding, and it is a different layer

`firewall/guard.py` **is live this session**, contrary to the trap-table entry
"hooks are not live mid-session" (REPORT.md §8 bug 7). It was confirmed
empirically and unplanned: the operator's first connectivity probe was **blocked
by the guard**, not by DNS:

```
[nomad-firewall] bash network egress blocked:
host www.google.com matches denylist entry google.com
```

That probe was the only attempt made at a denied host and **it did not reach the
network**. So the enforcement stack in this session is, in order of what actually
binds:

1. **`guard.py` PreToolUse hook — live, fails closed.** Denies WebSearch
   unconditionally, denies WebFetch off-allowlist, denies bash containing a
   denied URL, and denies any bash naming a network tool or networking API with
   no extractable URL. **This is the binding control.**
2. **`firewall/fetch.py` / `firewall/edgar.py` wrappers** — check, fetch, log;
   `edgar.py` enforces the filing-date ceiling in code.
3. **DNS blackhole** — holds for anything that resolves locally; bypassed by the
   proxy path. Defence in depth, no longer the primary.

The handoff's ordering (wrappers primary, hook defence-in-depth) is **inverted**
in this session. Both statements were true when written; neither is safe to
assume. The general lesson stands and is now three-for-three: *verify the
control, do not inherit the belief.*

### Guard false positive #5 — writing this file tripped the guard

Composing this document through a shell heredoc was **blocked by the guard**,
because the prose quoted the proxy URL above:

```
[nomad-firewall] bash network egress blocked: host 127.0.0.1 is not on the allowlist
```

This is the fifth recorded false positive and the second of exactly the kind
noted in REPORT.md §8 bug 10(d): **writing about the firewall is enough to trip
the firewall.** The fix was the sanctioned one — route around it with a
non-network write tool — **not** to widen the allowlist. Loopback was never added
to `allowlist.txt` and must not be.

## Operator commitments, not enforceable by machinery

- **`WebSearch`: 0 calls, and it stays 0.** It executes server-side and no DNS
  entry can touch it, so it is a commitment made auditable by this transcript.
  The guard also denies it, but the commitment does not depend on the guard.
- **No denied-domain content was read.** One probe was attempted and blocked
  before egress; the probe target was a search-engine root reached by HEAD, which
  carries no outcome content even on success.

## Amendment — operator document ceiling, 2026-08-22. Exclude-only, disclosed.

`firewall/config.json` sets `fire_date` / `screening_ceiling` = **2026-08-01**,
so `edgar.py` will open anything filed before that. For a trigger event dated
2026-06-01 the transmission window closes well before 2026-08-01, which means a
later filing by the same issuer could carry outcome information about the very
event under test.

> **The operator therefore adopts a tighter ceiling than the configured one: no
> document is opened whose filing date is after the trigger date of the selected
> event, except where a document is required to establish the destination set and
> is itself dated on or before that trigger date.**

This is a **validity** amendment, not a threshold amendment. It is exclude-only —
it can only reduce what the operator is permitted to see, never admit a document
or manufacture a result — and it is recorded here **before any candidate has been
selected**.
