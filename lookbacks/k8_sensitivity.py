"""K8 post-hoc sensitivity (NOT the verdict): unguarded on knowable_from, nodes from events.node,
and a stated manual map for rounds 1-6, whose events carry no node. Written after the pre-registered
run came back unreadable; see K8_result.md."""
import json, sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); c.row_factory = sqlite3.Row
MANUAL = {1: "strait_of_hormuz_tanker_transit", 2: "us_propylene_oxide_supply", 3: "port_of_antwerp_seagoing_access",
          4: "vlctpp_singhitarai_generation", 5: "bp_gelsenkirchen_scholven_output", 6: "deurganck_dock_container_handling"}
holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
pos = [dict(p) for p in c.execute("SELECT * FROM positions ORDER BY rowid")]
rows = []
for n, r in enumerate(c.execute("SELECT r.id, r.round_class, e.event_date, e.node FROM rounds r JOIN events e ON e.id=r.event_id ORDER BY r.rowid"), 1):
    tr = [x["to_state"] for x in c.execute("SELECT to_state FROM round_transitions WHERE round_id=? ORDER BY rowid", (r["id"],))]
    if "void" in tr:
        continue
    lock = c.execute("SELECT min(recorded_at) FROM round_transitions WHERE round_id=? AND to_state='locked'", (r["id"],)).fetchone()[0]
    node = r["node"] or MANUAL.get(n)
    side = {}
    for p in pos:
        if p["node"] == node and p["attribute"] == "sign_of_exposure" and (lock is None or p["recorded_at"] < lock):
            side[p["holder_id"]] = p["value"]
    L = lambda h: holders.get(h, {}).get("listed") == 1 and holders.get(h, {}).get("ticker")
    plus = sorted(holders[h]["ticker"] for h, s in side.items() if s == "+" and L(h))
    minus = sorted(holders[h]["ticker"] for h, s in side.items() if s == "-" and L(h))
    opts = sorted(holders[h]["ticker"] for h, s in side.items() if s in "+-" and L(h) and holders[h].get("options_listed") == 1)
    rows.append({"seq": n, "class": r["round_class"], "node": node, "sided": len(side), "plus": plus, "minus": minus,
                 "options": opts, "both_sides": bool(plus and minus), "pass": bool((plus and minus) or opts),
                 "lock_guard": lock is not None})
q = [x for x in rows if x["sided"]]
print(json.dumps({"rows": rows, "share_pass": round(sum(x["pass"] for x in q) / len(q), 3),
                  "share_both_sides_only": round(sum(x["both_sides"] for x in q) / len(q), 3), "n": len(q)}, indent=1))
