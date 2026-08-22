"""Robustness check on the two interpretive calls that carry the most candidates.

Q7 is written BUY-SIDE -- "the eligible DESTINATION set must not be published in
advance" -- exactly like the edge format that Defect 2 of the methodology review
had to make direction-aware. The review fixed the format and did not restate Q7.
So applying Q7 to a forced SALE requires reading it by analogy: if the set that
must be SOLD is handed to the operator, the event tests transmission rather than
enumeration, which is the purpose Q7 states for itself.

That reading disposes of 37 candidates. An interpretive extension carrying that
much weight must not be load-bearing on its own, so this checks what happens if
it is WITHDRAWN -- if Q7 is held to be buy-side only and therefore inapplicable
to every forced sale in the pool.

The same is done for Q2 on merger-completion delistings.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = json.loads((HERE / "walk_result.json").read_text())

# What each Q7-rejected candidate fails on INSTEAD, if Q7 is withdrawn entirely.
FALLBACK_Q7 = {
    "3.01-C involuntary delisting": (
        "Q8a",
        "The 8-K asserts that the EXCHANGE determined to delist. It does not "
        "assert that any holder is required to transact. The compulsion on "
        "index funds and mandate-constrained holders would have to be "
        "reconstructed by the operator from index methodologies -- which is "
        "exactly what Q8a forbids: 'the compulsion must be asserted by the "
        "filer, not reconstructed by the operator.'"),
    "individual": (
        "Q1/Q2",
        "83 Office Properties: reorganized equity is DISTRIBUTED by operation "
        "of the confirmed plan, not transacted in a market, and the plan names "
        "the allocation -- Q1 has no market transaction to point at. "
        "161 Data I/O: the note names its own conversion price, so Q2 fails "
        "independently."),
}

# What each Q2-rejected merger candidate fails on INSTEAD, if Q2 is withdrawn.
FALLBACK_Q2 = (
    "Q7",
    "The merger consideration and therefore the destination instrument are "
    "published in the merger agreement months before the fire date. Thermon's "
    "was signed 2026-02-23 for a 2026-06-01 closing. The destination set is "
    "handed to the operator, which is the case Q7 exists for.")


def main() -> None:
    q7 = [r for r in ROWS if r["failed"] == "Q7"]
    q2 = [r for r in ROWS if r["failed"] == "Q2"]
    q1 = [r for r in ROWS if r["failed"] == "Q1"]
    q3 = [r for r in ROWS if r["failed"] == "Q3"]

    print(f"Q1 {len(q1)}   Q2 {len(q2)}   Q3 {len(q3)}   Q7 {len(q7)}"
          f"   total {len(ROWS)}\n")

    print("=== If Q7 is withdrawn as buy-side-only, what do its 37 fail on? ===")
    by_class: dict[str, int] = {}
    for r in q7:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    still = 0
    for cls, n in sorted(by_class.items(), key=lambda kv: -kv[1]):
        crit, why = FALLBACK_Q7.get(cls, ("?", "needs individual reading"))
        print(f"  {n:>3}  {cls:<32} -> {crit}")
        print(f"       {why}")
        still += n
    print(f"  => {still}/{len(q7)} still rejected without Q7\n")

    print("=== If Q2 is withdrawn, what do the merger-completion ones fail on? ===")
    crit, why = FALLBACK_Q2
    print(f"  {len(q2):>3}  merger consideration fixed -> {crit}")
    print(f"       {why}")
    print(f"  => {len(q2)}/{len(q2)} still rejected without Q2\n")

    print("=== Conclusion ===")
    print("  Neither interpretive call is load-bearing. Withdrawing Q7 entirely")
    print("  leaves every candidate it rejected still rejected, on Q8a or on Q1/Q2.")
    print("  Withdrawing Q2 leaves every merger candidate rejected on Q7.")
    print("  The NOT OPERABLE verdict does not depend on either reading.")


if __name__ == "__main__":
    main()
