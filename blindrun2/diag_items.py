"""Diagnostic: is the EDGAR FTS `items=` filter trustworthy?

Context. A first probe of `items=2.04` returned 17 filings, every one of which
carried 2.04 in its own `items` metadata -- correct. A later batch of five
probes, fired back to back straight after a ~160-request screen, returned
BYTE-IDENTICAL responses for 1.03, 2.04, 2.05, 3.01 and 5.02 -- all of them the
1.03 result set.

Two hypotheses, and they have opposite consequences:

  H1  The filter is broken / aliased. Then item-code screening by this channel
      is unusable and the whole screen must move to client-side filtering.
  H2  EDGAR throttled a burst and served one cached body for every request.
      Then the filter is fine and only the request rate was wrong.

This script separates them: one request at a time, spaced, each response
hashed, and every returned filing checked against its OWN items metadata rather
than trusted because the filter was asked for it. Never trust the filter; check
the payload.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "firewall"))
from guard import _decide, _load  # noqa: E402

_ALLOW, _DENY = _load("allowlist.txt"), _load("denylist.txt")
UA = "nomad-research bato2912@gmail.com"
BASE = "https://efts.sec.gov/LATEST/search-index"
D, END = "2026-06-01", "2026-07-15"
PAUSE = 1.5  # deliberately slow: EDGAR asks for <=10 req/s, we use well under


def get(url: str) -> tuple[dict, str]:
    ok, why = _decide(urlparse(url).hostname, _ALLOW, _DENY)
    if not ok:
        raise SystemExit(f"REFUSED by in-process guard check: {why}")
    p = subprocess.run(["curl", "-sS", "--max-time", "90", "-H", f"User-Agent: {UA}", url],
                       capture_output=True, text=True)
    body = p.stdout
    return (json.loads(body) if body.strip() else {},
            hashlib.md5(body.encode()).hexdigest()[:12])


if __name__ == "__main__":
    codes = ["1.03", "2.04", "2.05", "3.01", "5.02"]
    print(f"one request every {PAUSE}s, each response hashed and payload-checked\n")
    print(f"  {'code':<7} {'total':>6} {'ret':>5} {'carry_code':>11}  md5")
    seen: dict[str, list[str]] = {}
    for c in codes:
        time.sleep(PAUSE)
        d, h = get(f"{BASE}?q=&items={c}&startdt={D}&enddt={END}")
        hits = d.get("hits", {}).get("hits", [])
        tot = d.get("hits", {}).get("total", {}).get("value", -1)
        carry = sum(1 for x in hits if c in (x["_source"].get("items") or []))
        seen.setdefault(h, []).append(c)
        print(f"  {c:<7} {tot:>6} {len(hits):>5} {carry:>11}  {h}")

    print()
    if len(seen) == 1:
        print("  VERDICT: every response identical -> filter is NOT usable (H1), or")
        print("           throttling is still active. Re-run when idle before concluding.")
    else:
        print(f"  VERDICT: {len(seen)} distinct responses across {len(codes)} codes.")
        for h, cs in seen.items():
            flag = "  <-- COLLISION" if len(cs) > 1 else ""
            print(f"    {h}  {','.join(cs)}{flag}")
