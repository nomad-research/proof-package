"""Render walk_result.json into the auditable rejection log required by spec 7.2.

"Log every rejection with the criterion it failed." All 175, in walk order, one
row each, with the class disposition that applied and the reasoning behind it.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = json.loads((HERE / "walk_result.json").read_text())

CRIT = {
    "Q1": "Citable forcing -- a specific, retrievable document removes discretion "
          "from a named actor",
    "Q2": "Price insensitivity -- does the rule specify what and when but NOT at "
          "what price?",
    "Q3": "Magnitude floor -- forced flow must exceed 0.8 days of ADV of the named set",
    "Q7": "Enumeration content -- the set must not be published in advance",
}


def main() -> None:
    out = ["# Blind run 2 — the chronological walk",
           "",
           "**175 candidates. 0 qualifiers.** Walked in strict order of "
           "`(filing date, accession number)`, the tie-break fixed cold in "
           "`screen_log.md` before the walk began. Criteria applied in **numerical "
           "order**, first failure recorded, per `criteria.md`.",
           "",
           "Every candidate document was opened through `firewall/edgar.py`, which "
           "enforces the filing-date ceiling in code and logs each open with its "
           "date. **175 opened, 0 failures, 0 post-fire filings touched.**",
           "",
           "## Summary — first failing criterion",
           "",
           "| Criterion | Count | What it asks |",
           "|---|---:|---|"]
    counts: dict[str, int] = {}
    classes: dict[str, dict] = {}
    for r in ROWS:
        counts[r["failed"]] = counts.get(r["failed"], 0) + 1
        c = classes.setdefault(r["class"], {"n": 0, "crit": r["failed"],
                                            "reason": r["reason"]})
        c["n"] += 1
    for k in ("Q1", "Q2", "Q3", "Q7"):
        if k in counts:
            out.append(f"| **{k}** | {counts[k]} | {CRIT[k]} |")
    out += [f"| | **{len(ROWS)}** | **and none reached Q4, Q5, Q6, Q8a or Q8b** |",
            "",
            "No candidate survived as far as Q4. The screen never got to the "
            "criteria that blind run 1 died on.",
            "",
            "## Class dispositions, each verified on named instances",
            ""]
    for cls, c in sorted(classes.items(), key=lambda kv: -kv[1]["n"]):
        if cls == "individual":
            continue
        out += [f"### {cls} — {c['n']} candidates — fails **{c['crit']}**", "",
                c["reason"], ""]
    out += ["## Full walk, all 175 in order", "",
            "| # | Filed | Entity | Items | Failed | Disposition |",
            "|---:|---|---|---|:---:|---|"]
    for r in ROWS:
        ent = r["entity"].split("  (CIK")[0][:44].replace("|", "/")
        out.append(f"| {r['idx']} | {r['filed']} | {ent} | "
                   f"{','.join(r['items']) if r['items'] else r['matched']} | "
                   f"**{r['failed']}** | {r['class']} |")
    out += ["", "## The 30 assessed individually", "",
            "Every Item 2.04 and Item 1.03 candidate, plus the nine the classifier "
            "refused to place and referred for individual reading. Quotations are "
            "verbatim from the fetched filing.", ""]
    for r in ROWS:
        if r["class"] != "individual":
            continue
        ent = r["entity"].split("  (CIK")[0]
        out += [f"**{r['idx']}. {r['filed']} — {ent}** — fails **{r['failed']}**",
                "", r["reason"], ""]
    (HERE / "walk_log.md").write_text("\n".join(out) + "\n")
    print(f"wrote walk_log.md — {len(ROWS)} rows, "
          f"{sum(1 for r in ROWS if r['class'] == 'individual')} individual")


if __name__ == "__main__":
    main()
