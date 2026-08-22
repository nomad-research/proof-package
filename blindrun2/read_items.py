"""Print the item text for a set of walk-pool candidates, for individual assessment.

usage:  read_items.py <item-heading-regex> <chars> <idx> [idx ...]
"""

from __future__ import annotations

import re
import sys

from openitem import POOL, text_of  # noqa: E402
from classify_301 import FETCHED  # noqa: E402


def main() -> None:
    pat, n = sys.argv[1], int(sys.argv[2])
    for i in (int(x) for x in sys.argv[3:]):
        r = POOL[i - 1]
        doc = r["doc_id"].split(":", 1)[1] if ":" in r["doc_id"] else ""
        p = FETCHED / f"{r['accession']}_{doc.replace('/', '_')}"
        if not p.exists():
            print(f"{i:>4}. UNRESOLVED -- document not on disk")
            continue
        t = text_of(p)
        m = re.search(pat, t, re.I)
        seg = t[m.start(): m.start() + n] if m else t[1500: 1500 + n]
        seg = re.sub(r"\s+", " ", seg)
        print(f"\n{'='*4} {i:>4}. {r['filed']}  {r['entity'][:50]}  items={r['items']}")
        print(seg)


if __name__ == "__main__":
    main()
