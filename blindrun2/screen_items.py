"""Blind run 2 -- item-code screen. Complete enumeration, client-side filtering.

## Why this is not a filter query

Attempt 1 (`screen.py`) searched for forcing LANGUAGE and found contracts rather
than events: 238 candidates dominated by credit-agreement exhibits.

Attempt 2 screened by 8-K item code but did it by full-text searching the
literal string "Item 2.04", which over-counts -- any document mentioning the
item number is a hit, including exhibits and amendments. It reported 51.

Attempt 3 (this file, first version) used EDGAR's `items=` query parameter,
which looked correct: a first probe of `items=2.04` returned 17 filings, every
one carrying 2.04 in its own metadata.

**That filter is not reliable and must not be used.** Diagnostics
(`diag_items.py`, `diag_items2.py`, both kept) establish it:

  - Five spaced probes for 1.03 / 2.04 / 2.05 / 3.01 / 5.02 returned four
    BYTE-IDENTICAL bodies -- all of them the 1.03 result set -- while 3.01
    correctly returned its own.
  - A second run returned eight byte-identical bodies across four codes, that
    time all the 2.05 set.
  - `Cache-Control: no-cache` and a unique cache-busting parameter did not
    change the response, so this is not an edge cache the client can defeat.

The endpoint intermittently serves a stale body computed for a *different*
`items` value. A screen built on it silently mixes result sets, and would look
like it was working. That is the same failure class as the phrase-search screen
and as a firewall believed to be in force -- which this project has now paid for
four times.

## What this screen does instead

It enumerates **every 8-K filed in the window**, day by day, and filters on each
filing's OWN `items` metadata, which travels in the response body next to the
filing it describes and therefore cannot be transposed between result sets.

Every page is validated before it is accepted: each returned hit must actually
be an 8-K, and pages are re-requested if a stale body is detected. Completeness
is checked against EDGAR's own reported total per day, and any shortfall is
reported rather than passed over.

## Item codes, per HANDOFF section 5.1

Each is a filing a party is OBLIGED to make and each asserts an event HAS
OCCURRED rather than describing a contingency -- the Q8a predicate.

  1.03  Bankruptcy or Receivership
  2.04  Triggering Events That Accelerate or Increase a Direct Financial
        Obligation or an Obligation under an Off-Balance Sheet Arrangement
  2.05  Costs Associated with Exit or Disposal Activities
  3.01  Notice of Delisting or Failure to Satisfy a Continued Listing Rule

Fund wind-ups are screened by FORM, since they are not 8-Ks: N-8F (application
for deregistration) and 497 (definitive materials). Their treatment, including
the recall problem 497 creates, is recorded in screen_log.md.

Dates are bounded to [D, TRIGGER_END] before display and the whole range sits
below the configured screening ceiling, so a post-fire hit is never surfaced.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

D = "2026-06-01"            # fixed before screening. Do not move.
TRIGGER_END = "2026-07-15"  # fixed before screening. Do not move.

TARGET_ITEMS = {"1.03", "2.04", "2.05", "3.01"}

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE.parent / "firewall" / "config.json").read_text())
CEILING = CFG["screening_ceiling"]

UA = "nomad-research bato2912@gmail.com"
BASE = "https://efts.sec.gov/LATEST/search-index"
PAGE = 100          # EDGAR returns at most 100 hits per request
PAUSE = 0.9         # well under EDGAR's 10 req/s ceiling
MAX_RETRY = 4

# The PreToolUse guard inspects the BASH COMMAND STRING, so a URL assembled
# inside this process is never seen by it -- a blind spot allowlist.txt already
# records. Rather than rely on that blind spot, apply the guard's own decision
# to every URL before fetching, and fail closed.
sys.path.insert(0, str(HERE.parent / "firewall"))
from guard import _decide, _load  # noqa: E402

_ALLOW, _DENY = _load("allowlist.txt"), _load("denylist.txt")
AUDIT: list[dict] = []


def _fetch(url: str) -> tuple[dict, str]:
    ok, why = _decide(urlparse(url).hostname, _ALLOW, _DENY)
    if not ok:
        raise SystemExit(f"REFUSED by in-process guard check: {why}")
    p = subprocess.run(["curl", "-sS", "--max-time", "90", "-H", f"User-Agent: {UA}", url],
                       capture_output=True, text=True)
    body = p.stdout
    if p.returncode != 0 or not body.strip():
        return {}, ""
    try:
        return json.loads(body), hashlib.md5(body.encode()).hexdigest()[:12]
    except Exception:
        return {}, ""


def _page(form: str, day: str, frm: int) -> tuple[int, list[dict], str]:
    """One validated page. Retries on a stale or malformed body."""
    for attempt in range(MAX_RETRY):
        time.sleep(PAUSE)
        url = (f"{BASE}?q=&forms={form}&startdt={day}&enddt={day}"
               f"&from={frm}&_n={attempt}")
        d, h = _fetch(url)
        hits = d.get("hits", {}).get("hits", [])
        total = d.get("hits", {}).get("total", {}).get("value", -1)
        if total < 0:
            continue
        # VALIDATION. Every hit must be the form we asked for and fall on the
        # day we asked for. A stale body from another query fails this.
        bad = [x for x in hits
               if form not in (x["_source"].get("root_forms") or [])
               or x["_source"].get("file_date") != day]
        if bad:
            AUDIT.append({"event": "stale_page_rejected", "form": form, "day": day,
                          "from": frm, "attempt": attempt, "bad": len(bad),
                          "returned": len(hits), "md5": h})
            continue
        return total, hits, h
    AUDIT.append({"event": "page_FAILED", "form": form, "day": day, "from": frm})
    return -1, [], ""


def _day(form: str, day: str) -> tuple[list[dict], int, int]:
    """All filings of one form on one day. Returns (rows, reported, collected)."""
    rows: list[dict] = []
    total, frm = None, 0
    while True:
        t, hits, _ = _page(form, day, frm)
        if t < 0:
            break
        if total is None:
            total = t
        if not hits:
            break
        for x in hits:
            s = x["_source"]
            filed = s.get("file_date", "")
            if not (D <= filed <= TRIGGER_END) or filed >= CEILING:
                continue  # bound before display; never surface a post-ceiling hit
            rows.append({
                "accession": s.get("adsh", ""),
                "filed": filed,
                "form": s.get("form", ""),
                "items": s.get("items") or [],
                "entity": (s.get("display_names") or [""])[0],
                "ciks": s.get("ciks") or [],
                "doc_id": x.get("_id", ""),
            })
        frm += len(hits)
        if total is not None and frm >= total:
            break
        if frm > 9000:
            AUDIT.append({"event": "deep_page_cap", "form": form, "day": day})
            break
    return rows, (total or 0), frm


def sweep(form: str) -> list[dict]:
    start = date.fromisoformat(D)
    end = date.fromisoformat(TRIGGER_END)
    seen: dict[str, dict] = {}
    reported_sum = collected_sum = 0
    n_days = (end - start).days + 1
    for i in range(n_days):
        day = (start + timedelta(days=i)).isoformat()
        rows, reported, collected = _day(form, day)
        reported_sum += reported
        collected_sum += collected
        for r in rows:
            seen.setdefault(r["accession"], r)
        print(f"    {day}  reported={reported:>4}  collected={collected:>4}"
              f"  {'OK' if collected >= reported else '*** SHORTFALL ***'}")
    print(f"  {form}: {reported_sum} reported, {collected_sum} collected, "
          f"{len(seen)} distinct accessions")
    AUDIT.append({"event": "sweep_done", "form": form, "reported": reported_sum,
                  "collected": collected_sum, "distinct": len(seen)})
    return sorted(seen.values(), key=lambda r: (r["filed"], r["accession"]))


if __name__ == "__main__":
    print(f"D = {D}   trigger window to {TRIGGER_END}   ceiling {CEILING}")
    print(f"target items: {sorted(TARGET_ITEMS)}\n")

    print("sweeping every 8-K in the window (complete enumeration):")
    all_8k = sweep("8-K")
    hits_8k = [r for r in all_8k if TARGET_ITEMS & set(r["items"])]
    for r in hits_8k:
        r["matched"] = ",".join(sorted(TARGET_ITEMS & set(r["items"])))

    print("\nsweeping fund wind-up forms:")
    n8f = sweep("N-8F")
    for r in n8f:
        r["matched"] = "form:N-8F"
    f497 = sweep("497")
    for r in f497:
        r["matched"] = "form:497"

    (HERE / "screen_all_8k.json").write_text(json.dumps(all_8k, indent=1))
    combined = sorted(hits_8k + n8f + f497, key=lambda r: (r["filed"], r["accession"]))
    (HERE / "screen_items.json").write_text(json.dumps(combined, indent=1))
    (HERE / "screen_audit.json").write_text(json.dumps(AUDIT, indent=1))

    per_item = {c: sum(1 for r in all_8k if c in r["items"]) for c in sorted(TARGET_ITEMS)}
    print("\nitem census, derived client-side from each filing's own metadata:")
    for c, n in per_item.items():
        print(f"  item {c}: {n:>4} filings")
    print(f"  8-K filings matching at least one target item: {len(hits_8k)}")
    print(f"  N-8F: {len(n8f)}   497: {len(f497)}")
    print(f"  total 8-K filings enumerated in window: {len(all_8k)}")
    print(f"\ncombined candidate pool: {len(combined)}")
    print("wrote screen_items.json, screen_all_8k.json, screen_audit.json")
