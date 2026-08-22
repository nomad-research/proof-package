"""Assign every Item 3.01 candidate to an instance-verified subtype.

Two subtypes were verified by opening actual filings and quoting them, per the
class-rejection standard in criteria.md. A class rejection that has not been
instance-verified is not permitted, and neither is one applied to a candidate
that does not demonstrably belong to the verified subtype.

  A  MERGER-COMPLETION DELISTING. The registrant has been acquired and asks the
     exchange to file Form 25. Verified on Thermon Group Holdings (candidate 1):
     discretion IS removed -- each share "ceased to have any rights ... except
     the right to receive" the merger consideration -- so Q1 passes. But the
     consideration is fixed by the merger agreement, so the rule specifies the
     price. **Q2 fails.**

  B  DEFICIENCY NOTICE WITH A CURE PERIOD. The registrant has received notice it
     is out of compliance and has time to regain it. Verified on Gencor
     Industries (candidate 3, late 10-Q, six-month cure) and HCW Biologics
     (candidate 11, bid-price rule, extension to 2026-07-29). Nothing is
     compelled; the filing reports a contingency. **Q1 fails.**

Anything matching neither, or matching both, is reported as UNCLASSIFIED and
must be read individually. The classifier may only route a candidate to a
disposition already verified on instances -- it may never create one.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from openitem import POOL, text_of  # noqa: E402

HERE = Path(__file__).resolve().parent
FETCHED = HERE.parent / "firewall" / "fetched"

# Markers are drawn from the verified instances, not invented.
A_MARKERS = [
    r"form\s*25", r"notification of removal from listing",
    r"consummation of the merger", r"certificates? of merger",
    r"completion of the merger", r"effective time of the merger",
    r"in connection with the (?:closing|consummation)",
    r"merger agreement", r"acquisition of the company",
]
B_MARKERS = [
    r"regain compliance", r"continued listing", r"not in compliance",
    r"compliance period", r"listing rule", r"deficiency", r"minimum bid price",
    r"received (?:a )?(?:written )?(?:notice|letter)", r"cure period",
    r"listing qualifications", r"hearings panel", r"company guide",
]


def item_text(r: dict) -> str:
    doc = r["doc_id"].split(":", 1)[1] if ":" in r["doc_id"] else ""
    p = FETCHED / f"{r['accession']}_{doc.replace('/', '_')}"
    if not p.exists():
        return ""
    t = text_of(p)
    m = re.search(r"item\s*3\.01", t, re.I)
    if not m:
        return t[:4000]
    return t[m.start(): m.start() + 4000]


def main() -> None:
    rows = [(i, r) for i, r in enumerate(POOL, 1) if r["matched"] == "3.01"
            or "3.01" in r["matched"].split(",")]
    out, counts = [], {"A": 0, "B": 0, "AB": 0, "NONE": 0}
    for i, r in rows:
        seg = item_text(r).lower()
        a = any(re.search(p, seg) for p in A_MARKERS)
        b = any(re.search(p, seg) for p in B_MARKERS)
        kind = "A" if a and not b else "B" if b and not a else "AB" if a and b else "NONE"
        counts[kind] += 1
        out.append({"idx": i, "filed": r["filed"], "entity": r["entity"][:46],
                    "accession": r["accession"], "kind": kind,
                    "head": re.sub(r"\s+", " ", item_text(r))[:230]})
    (HERE / "classify_301.json").write_text(json.dumps(out, indent=1))
    print(f"Item 3.01 candidates: {len(rows)}")
    print(f"  A  merger-completion delisting (Q2 fail): {counts['A']}")
    print(f"  B  deficiency notice, cure period (Q1 fail): {counts['B']}")
    print(f"  AB ambiguous, needs reading:               {counts['AB']}")
    print(f"  NONE no verified subtype, needs reading:   {counts['NONE']}")
    if len(sys.argv) > 1:
        want = sys.argv[1].upper()
        print(f"\n--- {want} ---")
        for r in out:
            if r["kind"] == want:
                print(f"\n{r['idx']:>4}. {r['filed']} {r['entity']}\n     {r['head']}")


if __name__ == "__main__":
    main()
