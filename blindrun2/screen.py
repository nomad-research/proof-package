"""Operator self-screen for blind run 2. Queries declared before results are seen.

Spec v2 §7.2: fix D, screen forward by Q1-Q8, take the FIRST qualifier -- not the
most interesting one. Log every rejection with the criterion it failed.

The query set below is fixed in this file before it is run. It targets documents
capable of satisfying Q8a: a filing someone was OBLIGED to make, asserting as
fact that a named actor is required to transact. Holdings disclosures are
deliberately absent -- they report what is held, never that anything must move.

Screening uses EDGAR full-text search only. It returns filing metadata and filing
text, with no narrative or commentary, so it cannot leak an outcome narrative
because it does not contain one. Results are date-bounded before display.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

D = "2026-06-01"          # fixed before screening
TRIGGER_END = "2026-07-15"  # leaves 5+ weeks for a transmission window to close by 2026-08-21
UA = "nomad-research bato2912@gmail.com"
FTS = "https://efts.sec.gov/LATEST/search-index"

# Declared before any result was seen. Ordered by forcing class, not by expected yield.
QUERIES = [
    # --- forced BUYING classes: where enumeration has the most to say ---
    ("mandatory conversion",      "8-K",  "issuer compels conversion; holders must take stock"),
    ("subject to proration",      "8-K",  "oversubscribed corporate action, pro-rata forced"),
    ("mandatory exchange",        "8-K",  "forced exchange into a named instrument"),
    # --- forced SELLING classes ---
    ("notice of acceleration",    "8-K",  "debt accelerated; assets must be realised"),
    ("mandatory redemption",      "8-K",  "instrument must be redeemed"),
    ("required to divest",        "8-K",  "regulatory or contractual divestiture"),
    ("liquidating distribution",  "8-K",  "entity winding up, holdings must be sold"),
]


def _fts(q: str, forms: str, start: str, end: str) -> list[dict]:
    url = (f"{FTS}?q=%22{q.replace(' ', '+')}%22&forms={forms}"
           f"&startdt={start}&enddt={end}")
    for _ in range(4):
        p = subprocess.run(["curl", "-sS", "--max-time", "60", "-H", f"User-Agent: {UA}", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout).get("hits", {}).get("hits", [])
            except Exception:
                pass
        time.sleep(2)
    return []


def run() -> list[dict]:
    seen, rows = set(), []
    for q, forms, why in QUERIES:
        hits = _fts(q, forms, D, TRIGGER_END)
        print(f"  {q:26} -> {len(hits):>3} hits   ({why})")
        for h in hits:
            s = h.get("_source", {})
            filed = s.get("file_date", "")
            if not (D <= filed <= TRIGGER_END):      # bound before display
                continue
            name = (s.get("display_names") or [""])[0]
            key = (name, filed, q)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"query": q, "form": s.get("form"), "filed": filed,
                         "entity": name, "id": h.get("_id", "")})
    rows.sort(key=lambda r: (r["filed"], r["entity"]))
    return rows


if __name__ == "__main__":
    print(f"D = {D}, trigger window to {TRIGGER_END}\n")
    rows = run()
    out = Path(__file__).resolve().parent / "screen_hits.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"\n{len(rows)} candidates, chronological:\n")
    for i, r in enumerate(rows[:60], 1):
        print(f"{i:>3}. {r['filed']}  {r['form']:<6} {r['entity'][:58]:<58} [{r['query']}]")
    print(f"\nwrote {out}")
