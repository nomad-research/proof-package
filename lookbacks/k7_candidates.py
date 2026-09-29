"""K7 candidate list, per K7_prereg.md: the top 15 unlisted holders from v15 rounds 1-15. Read-only."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(f"file:{ROOT / 'v15' / 'nomad_harness.db'}?mode=ro&immutable=1", uri=True)
c.row_factory = sqlite3.Row
H = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
rounds = {}
for n, r in enumerate(c.execute("SELECT r.id, e.event_date, e.event_text FROM rounds r JOIN events e ON e.id=r.event_id "
                                "ORDER BY r.rowid"), 1):
    st = [x["to_state"] for x in c.execute("SELECT to_state FROM round_transitions WHERE round_id=?", (r["id"],))]
    if "void" not in st:
        rounds[r["id"]] = {"seq": n, "event_date": r["event_date"], "event_line": r["event_text"]}
impact = {}
for x in c.execute("SELECT holder_id, impact_pct FROM leg_claims WHERE impact_pct IS NOT NULL"):
    impact[x["holder_id"]] = max(impact.get(x["holder_id"], 0.0), abs(float(x["impact_pct"])))
cand = {}
for t in c.execute("SELECT round_id, holder_id, degree FROM touched_set"):
    h = H.get(t["holder_id"])
    if not h or h["listed"] != 0 or h["kind"] not in {"company", "plant", "facility", "other"} or t["round_id"] not in rounds:
        continue
    d = cand.setdefault(t["holder_id"], {"holder_id": t["holder_id"], "name": h["canonical_name"], "kind": h["kind"],
                                         "min_degree": 99, "rounds": set()})
    d["min_degree"] = min(d["min_degree"], t["degree"] if t["degree"] is not None else 99)
    d["rounds"].add(rounds[t["round_id"]]["seq"])
rows = sorted(cand.values(), key=lambda d: (-impact.get(d["holder_id"], -1), d["min_degree"], -len(d["rounds"]), d["name"]))
out = []
for i, d in enumerate(rows[:15], 1):
    seqs = sorted(d["rounds"])
    out.append({"rank": i, "name": d["name"], "kind": d["kind"], "max_abs_impact_pct": impact.get(d["holder_id"]),
                "min_degree": d["min_degree"], "round_seqs": seqs,
                "event_lines": [next(r["event_line"] for r in rounds.values() if r["seq"] == s)[:120] for s in seqs],
                "earliest_event_date": min(r["event_date"] for r in rounds.values() if r["seq"] in seqs)})
(ROOT / "lookbacks" / "k7_candidates.json").write_text(json.dumps({"rule": "K7_prereg.md", "population": len(rows),
                                                                    "candidates": out}, indent=1) + "\n")
print(len(rows), "in the population;", len(out), "candidates")
for o in out:
    print(o["rank"], o["name"], o["kind"], o["max_abs_impact_pct"], "deg", o["min_degree"], "rounds", o["round_seqs"])
