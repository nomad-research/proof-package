"""Build the blind back-fill package (lookbacks/backfill/package.json). Reads v15 read-only and writes only
{id, source, source_time}. Also writes package_map.json (id -> position ids), which the dater is not given."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(f"file:{ROOT / 'v15' / 'nomad_harness.db'}?mode=ro&immutable=1", uri=True)
c.row_factory = sqlite3.Row
groups = {}
for p in c.execute("SELECT id, source, source_time FROM positions WHERE knowable_from IS NULL OR knowable_from='' "
                   "ORDER BY rowid"):
    groups.setdefault((p["source"] or "", p["source_time"] or ""), []).append(p["id"])
pkg, mp = [], {}
for i, ((src, st), ids) in enumerate(sorted(groups.items()), 1):
    key = f"B{i:03d}"
    pkg.append({"id": key, "source": src, "source_time": st or None})
    mp[key] = ids
d = ROOT / "lookbacks" / "backfill"
(d / "package.json").write_text(json.dumps(pkg, indent=1, ensure_ascii=False) + "\n")
(d / "package_map.json").write_text(json.dumps(mp, indent=1) + "\n")
print(len(pkg), "distinct sources covering", sum(len(v) for v in mp.values()), "undated positions")
