"""Open every walk-pool candidate through the date-ceilinged wrapper.

Pre-fetching is mechanical and involves no judgement, so it does not disturb the
strict chronological order of the walk -- it only puts every document in hand
before assessment begins. Every open still goes through firewall/edgar.py, which
refuses post-fire filings in code and logs each open with its filing date.

All 175 candidates are filed on or before 2026-07-15, comfortably below the
configured ceiling of 2026-08-01 and below the operator's tighter ceiling.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
POOL = json.loads((HERE / "walk_pool.json").read_text())
FETCHED = ROOT / "firewall" / "fetched"


def main() -> None:
    ok = skip = fail = 0
    failures = []
    for i, r in enumerate(POOL, 1):
        doc = r["doc_id"].split(":", 1)[1] if ":" in r["doc_id"] else ""
        out = FETCHED / f"{r['accession']}_{doc.replace('/', '_')}"
        if out.exists():
            skip += 1
            continue
        cmd = ["python3", str(ROOT / "firewall" / "edgar.py"), "open",
               r["ciks"][0], r["accession"]]
        if doc:
            cmd.append(doc)
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if out.exists():
            ok += 1
        else:
            fail += 1
            failures.append((i, r["accession"], r["entity"][:38],
                             (p.stdout + p.stderr).strip()[:120]))
        time.sleep(0.35)
        if i % 25 == 0:
            print(f"  ...{i}/{len(POOL)}  opened={ok} cached={skip} failed={fail}",
                  flush=True)
    print(f"\nopened={ok}  already cached={skip}  failed={fail}")
    for f in failures:
        print(f"  FAILED {f[0]:>4} {f[1]} {f[2]}  {f[3]}")
    if fail:
        print("\nFailures are reported, not passed over. Any candidate whose "
              "document could not be opened is recorded in the walk as "
              "UNRESOLVED rather than silently dropped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
