"""K8 look-back over the v15 ledger, per K8_prereg.md. Read-only."""
import json, sqlite3, sys, collections
DB = sys.argv[1]  # optional: --overlay v15_overlay/knowable_from_backfill.json
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); c.row_factory = sqlite3.Row
rounds = []
for n, r in enumerate(c.execute("SELECT r.id, r.round_class, e.event_date, e.node, substr(e.event_text,1,70) t "
                                "FROM rounds r JOIN events e ON e.id=r.event_id ORDER BY r.rowid"), 1):
    tr = [dict(x) for x in c.execute("SELECT to_state, recorded_at FROM round_transitions WHERE round_id=? ORDER BY rowid", (r["id"],))]
    lock = next((x["recorded_at"] for x in tr if x["to_state"] == "locked"), None)
    void = any(x["to_state"] == "void" for x in tr)
    rounds.append(dict(r) | {"seq": n, "lock": lock, "void": void, "states": [x["to_state"] for x in tr]})
holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
pos = [dict(p) for p in c.execute("SELECT * FROM positions ORDER BY rowid")]
if "--overlay" in sys.argv:  # v15/ stays frozen: dates come from the overlay, never written to the database
    ov = {r["position_id"]: r["knowable_from"] for r in json.load(open(sys.argv[sys.argv.index("--overlay") + 1]))["rows"]}
    for p in pos:
        if not p["knowable_from"] and ov.get(p["id"]):
            p["knowable_from"] = ov[p["id"]]
vec = collections.defaultdict(list)
for s in c.execute("SELECT round_id, holder_id, node, vector FROM surviving_risk WHERE vector IS NOT NULL"):
    try:
        v = json.loads(s["vector"])
    except ValueError:
        continue
    vec[(s["round_id"], s["holder_id"], s["node"])].append((v.get("terms") or {}).get("stake"))
out = []
for r in rounds:
    if r["void"] or not r["lock"]:
        out.append({"seq": r["seq"], "event": r["t"], "excluded": "void" if r["void"] else "never locked"})
        continue
    ts = [dict(t) for t in c.execute("SELECT * FROM touched_set WHERE round_id=?", (r["id"],))]
    nodes = sorted({t["node"] for t in ts if t["node"]})
    counted = [p for p in pos if p["recorded_at"] < r["lock"] and p["knowable_from"] and p["knowable_from"][:10] <= r["event_date"]]
    sup = {p["supersedes"] for p in counted if p["supersedes"]}
    counted = [p for p in counted if p["id"] not in sup]
    per_node = []
    for nd in nodes:
        side = {}
        for p in counted:
            if p["node"] == nd and p["attribute"] == "sign_of_exposure":
                side[p["holder_id"]] = p["value"]
        deg = {t["holder_id"]: t["degree"] for t in ts if t["node"] == nd}
        listed = lambda h: holders.get(h, {}).get("listed") == 1 and holders.get(h, {}).get("ticker")
        plus = [h for h, s in side.items() if s == "+" and listed(h)]
        minus = [h for h, s in side.items() if s == "-" and listed(h)]
        opts = [h for h, s in side.items() if s in "+-" and listed(h) and holders[h].get("options_listed") == 1]
        proxy = [h for h, s in side.items() if s in "+-" and deg.get(h) is not None and deg[h] <= 1]
        strict = [h for h in side if any(x is not None and x >= 1.0 for x in vec.get((r["id"], h, nd), []))]
        per_node.append({"node": nd, "n_holders_sided": len(side), "listed_plus": len(plus), "listed_minus": len(minus),
                         "listed_with_options": len(opts), "proxy_high_stake": len(proxy), "strict_high_stake": len(strict),
                         "pass": bool((plus and minus) or opts)})
    out.append({"seq": r["seq"], "event": r["t"], "event_date": r["event_date"], "class": r["round_class"], "nodes": per_node})
def share(sel, cls=None):
    q = [n for o in out if "nodes" in o and (cls is None or o["class"] == cls) for n in o["nodes"] if sel(n)]
    return {"qualifying_nodes": len(q), "passing": sum(n["pass"] for n in q),
            "share": round(sum(n["pass"] for n in q) / len(q), 3) if q else None}
res = {"rounds": out,
       "proxy": {"all": share(lambda n: n["proxy_high_stake"] > 0), "clean": share(lambda n: n["proxy_high_stake"] > 0, "clean"),
                 "learning": share(lambda n: n["proxy_high_stake"] > 0, "learning")},
       "strict": {"all": share(lambda n: n["strict_high_stake"] > 0)}}
print(json.dumps(res, indent=1))
