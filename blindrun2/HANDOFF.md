# Blind run 2 — handoff for a fresh session

You are the **operator** in a blind prediction test. Read this file, then
`methodology/pre_event_review.md`, then start at §3 below. Everything here is
methodology and state — **no outcome information appears in this document**, and
none may be added to it.

---

## 1. What you are doing, in one paragraph

Given a real forcing event that postdates your training cutoff, map which
specific instruments the forced capital must move through, commit that map, and
only then look at what happened. The point is **not** to find an edge. It is to
find out whether this system can be operated at all. Five prior tests measured
assumptions underneath the framework; one measured the framework and stalled.
A negative result is a success. A cheap kill is the intended outcome.

## 2. Authoritative documents, in precedence order

| Document | Status |
|---|---|
| `methodology/pre_event_review.md` | **Highest.** Four defect decisions taken cold on 2026-08-21. Supersedes Q8 and the edge format in spec v2 |
| `nomad_spec_v2.md` (uploaded) | Authoritative except where the review above overrides it |
| `blindrun2/screen_log.md` | State of the screen so far, including one approach that failed |
| `REPORT.md` | Full record of all six prior attempts. Read §8 "everything that went wrong" before starting |
| Earlier gate spec, amendment 1, operating procedure v1 | **Archived. Not authoritative.** |

## 3. FIRST — re-apply and verify the firewall. Do not skip, do not assume.

**The DNS blackhole does not persist across sessions.** It was found gone at the
start of the last session. Verify by **resolution**, never by checking that the
file was written.

```bash
cd /home/user/proof-package
python3 - <<'PY'
from pathlib import Path
deny=[l.split('#')[0].strip() for l in Path('firewall/denylist.txt').read_text().splitlines()]
deny=[d for d in deny if d]
lines=["","# ===== nomad blind run 2 ====="]
for d in deny:
    for h in (d, f"www.{d}"):
        lines += [f"0.0.0.0 {h}", f":: {h}"]
Path('/etc/hosts').open('a').write("\n".join(lines)+"\n")
print(f"blackholed {len(deny)} domains, A and AAAA")
PY
for h in www.reuters.com www.google.com seekingalpha.com; do
  echo "DENIED?  $h -> $(getent hosts $h | head -1 | awk '{print $1}')"; done
for h in www.sec.gov efts.sec.gov data.sec.gov; do
  echo "allowed  $h -> $(getent hosts $h | head -1 | awk '{print $1}')"; done
```

Both record types matter: an IPv4-only blackhole leaks over IPv6, which happened
and was caught only by checking resolution.

**`WebSearch` is banned for the whole run and is not blockable by DNS** — it runs
server-side. It is therefore a commitment made auditable by the transcript. **Any
`WebSearch` call invalidates the run.** Fetching a known URL is fine; searching
is not, including to find a document you know exists. If you need a document and
lack its URL, ask the analyst.

EDGAR is carved out — `firewall/edgar.py` enforces a filing-date ceiling **in
code** and refuses anything filed on or after the fire date.

## 4. State — what is already fixed and must not be re-litigated

- **D = 2026-06-01**, trigger window to **2026-07-15**. Fixed before screening.
  Do not move it.
- **Operator self-screens.** The analyst is not involved in selection. This
  closes the selection-contamination channel rather than merely disclosing it.
- **Q8 is replaced by Q8a + Q8b.** Q8a: a document someone was *obliged to file*
  must assert compulsion **as fact**, not the operator reconstructing it. Q8b:
  every destination traceable to a located clause or disclosed holding.
- **The edge format is direction-aware.** For a forced sale use
  `forced_supply_set` + `supply_basis` + `absorption_set`, not
  `eligible_destinations`.
- **Q3 magnitude floor is 0.8 days of destination ADV**, not 82.9. The old figure
  was a multiplier `M/ADV`; realised flow is `M·r/ADV`. A screen carrying the old
  number sets a bar ~100× too high.

## 5. Remaining steps, in order

1. **Extend the item-code screen.** Item 2.04 gave 51 candidates. Add **1.03**
   (bankruptcy/receivership), **2.05** (exit or disposal costs), **3.01**
   (delisting / listing-rule non-compliance), and **N-8F / 497** for fund
   wind-ups. Each is a filing a party is *obliged* to make and asserts an event
   rather than a contingency.
2. **Walk the combined set in strict chronological order.** Apply
   Q1–Q7 + Q8a + Q8b. **Take the first qualifier — not the most interesting
   one.** Log every rejection with the criterion it failed, in
   `blindrun2/screen_log.md`.
3. **Map edges** in the direction-aware format. Every `_document` field fetched
   and the clause located verbatim. Assertion that a rule exists is not evidence
   it exists.
4. **Commit the quarantine reasoning BEFORE `prediction.md` exists.** This
   timestamps the standard independently of any map, so it cannot have been
   reverse-engineered. This ordering is not optional.
5. **Write `prediction.md`, commit, print the hash. That is the seal.** Include
   the `falsifier` field — a prediction without one is a description. Nothing may
   edit it afterwards; corrections go in a dated appendix.
6. **Only then** touch outcome data. Score **S1–S4 separately, never blended.**
   Watch the high-recall/zero-spread cell: map right, already priced — a
   different result from a wrong map and the one the decay literature predicts.

## 6. Traps already paid for. Do not pay again.

| Trap | What happened | What to do |
|---|---|---|
| **Full-text search finds contracts, not events** | 238 candidates, dominated by credit-agreement exhibits dense with forcing vocabulary. A regex meant to spot asserted compulsion returned 8 hits, **all false positives** — definitions and conditions inside exhibits | Screen by **8-K item code**, not by phrase |
| **The blackhole does not persist** | Found gone at session start; IPv4-only version leaked over IPv6 | Re-apply and verify by resolution, both record types |
| **Hooks are not live mid-session** | Project settings load at session start, confirmed empirically | Treat `firewall/guard.py` as defence in depth; wrappers are primary |
| **The guard blocks its own operator** | Four false positives, including on prose naming a network tool and on a commit message containing an ordinary word that is also a text-mode browser | Route around it — message file, non-network write tool, reword. **Never widen the allowlist to get past it** |
| **A 13F is not a forcing document** | It reports holdings; it asserts no compulsion. This is what killed blind run 1 | Q8a exists for exactly this |
| **Most publicly-documented forcing is forced *selling*** | Q7 kills mandatory conversion, proration and exchange because they name their own destination | Expect an empty `absorption_set`. That is a finding, not a gap |

## 7. Stop conditions — pre-registered, per spec v2 §7.4

- **Not operable** if no event satisfies Q1–Q8b; **or** the first qualifier maps
  to zero verified edges; **or** the quarantine rate exceeds the verified rate.
- **Operable, edge absent** if recall is high and spread is zero.
- **A failure of an event is recorded as a failure of that event — never as a
  licence to shop for a better one.**

Report the quarantine rate. High is informative, not embarrassing.

## 8. Expectation recorded in advance

Nearly every Item 2.04 event is a forced sale, so the honest output for most will
be a derivable `forced_supply_set` and an **empty `absorption_set`** — no rule
compels anyone to buy. If that is what the screen yields, it is not a failure of
the run. It is the structural point the methodology review reached from the other
direction: **publicly-documented forcing is overwhelmingly forced selling, and
enumeration has far more to say about forced buying.**

This is written down now so it cannot later be presented as something the run
discovered.

## 9. Housekeeping

- Branch `claude/nomad-gate-test-spec-f2o5i1`; `main` is kept in sync and carries
  the same tree.
- Log **every** evaluation to `config_log.jsonl`, including abandoned ones. It
  stands at **204**. That count is the multiple-testing denominator.
- Amendments appended and dated, never edited in place. **Validity amendments are
  learning; threshold amendments are fitting.** Threshold amendments are not
  acceptable at any count.
- Do **not** start Test C. Do **not** propose a third LETF regime — Test A is
  closed permanently. Do **not** run a fourth macro instrument — B-3 fired the
  stop trigger.
