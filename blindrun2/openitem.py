"""Open a candidate filing through the date-ceilinged wrapper and print its item text.

Every document reaching the operator goes through firewall/edgar.py, which
refuses anything filed on or after the fire date in code rather than by
discipline, and logs what it opened with its date.

This adds nothing to that check. It strips markup so the item text can be read
and quoted verbatim, which V3 of the quarantine standard requires: a clause is
located only if its exact text is copied from the fetched file, never recalled
or paraphrased.

usage:  openitem.py <index-in-walk_pool> [item ...]
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
POOL = json.loads((HERE / "walk_pool.json").read_text())


def text_of(path: Path) -> str:
    t = path.read_text(errors="ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def fetch(i: int) -> tuple[dict, Path]:
    r = POOL[i - 1]
    doc = r["doc_id"].split(":", 1)[1] if ":" in r["doc_id"] else None
    out = ROOT / "firewall" / "fetched" / f"{r['accession']}_{(doc or '').replace('/', '_')}"
    if not out.exists():
        cmd = ["python3", str(ROOT / "firewall" / "edgar.py"), "open",
               r["ciks"][0], r["accession"]]
        if doc:
            cmd.append(doc)
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        sys.stderr.write(p.stdout + p.stderr)
        if not out.exists():
            raise SystemExit(f"could not open candidate {i}")
    return r, out


def main() -> None:
    i = int(sys.argv[1])
    items = sys.argv[2:] or ["Item"]
    r, path = fetch(i)
    t = text_of(path)
    print(f"### candidate {i}  {r['filed']}  {r['form']}  {r['accession']}")
    print(f"### {r['entity']}   items={r['items']}   matched={r['matched']}")
    print(f"### {len(t)} chars of text\n")
    for it in items:
        for m in re.finditer(re.escape(it), t):
            seg = t[m.start(): m.start() + 2000]
            print(f"--- at offset {m.start()} ---")
            print(seg)
            print()
            break


if __name__ == "__main__":
    main()
