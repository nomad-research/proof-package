"""Diagnostic 2: is the items= collision a CDN cache artifact?

Diagnostic 1 ruled out plain throttling: 3.01 returned its own correct 128-row
set inside the same spaced burst in which 1.03, 2.04, 2.05 and 5.02 all collided
on one 9-row body. And the very first probe of the session -- items=2.04, fired
before any other FTS traffic -- returned 17 filings, every one carrying 2.04.

That pattern is what an edge cache looks like: a body cached under a key that
several distinct URLs map to, with whichever request arrives first populating it.

Test: fire the same logical query twice, once plain and once with a harmless
unique parameter that no cache key can have seen before. If the cache-busted
response differs from the plain one, the collision is caching, the filter is
sound, and the screen just has to defeat the cache. If they agree, the filter
is genuinely broken and item screening must move client-side.

The buster parameter is inert -- EDGAR ignores unknown query parameters -- so it
changes the cache key without changing the query.
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


def get(url: str):
    ok, why = _decide(urlparse(url).hostname, _ALLOW, _DENY)
    if not ok:
        raise SystemExit(f"REFUSED by in-process guard check: {why}")
    p = subprocess.run(["curl", "-sS", "--max-time", "90",
                        "-H", f"User-Agent: {UA}", "-H", "Cache-Control: no-cache",
                        "-H", "Pragma: no-cache", url],
                       capture_output=True, text=True)
    body = p.stdout
    d = json.loads(body) if body.strip() else {}
    hits = d.get("hits", {}).get("hits", [])
    return (d.get("hits", {}).get("total", {}).get("value", -1),
            hits,
            hashlib.md5(body.encode()).hexdigest()[:12])


if __name__ == "__main__":
    print(f"  {'code':<7} {'variant':<14} {'total':>6} {'ret':>5} {'carry':>6}  md5")
    for i, c in enumerate(["1.03", "2.04", "2.05", "3.01"]):
        for variant, extra in (("plain", ""), ("cache-busted", f"&_cb=nomad{i}x")):
            time.sleep(1.5)
            tot, hits, h = get(f"{BASE}?q=&items={c}&startdt={D}&enddt={END}{extra}")
            carry = sum(1 for x in hits if c in (x["_source"].get("items") or []))
            print(f"  {c:<7} {variant:<14} {tot:>6} {len(hits):>5} {carry:>6}  {h}")
        print()
