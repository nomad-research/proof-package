"""V3 tracker: for each current round, which of its events (primary and every hedge event the session chose) have resolved, and how many days to the horizon.
Read-only (Gamma). Scoring is not run until every leg has resolved (V3_prereg.md difference 5). Output: v3_status.json"""
import datetime as dt, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); V3 = os.path.join(HERE, "v3"); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import v1_pool as P
from concurrent.futures import ThreadPoolExecutor
pool = {e["id"]: e for e in json.load(open(os.path.join(V3, "v3_pool.json")))}
lock = json.load(open(os.path.join(V3, "v3_lock.json")))["lock"]; now = int(time.time())
rounds = json.load(open(os.path.join(V3, "v1_rounds_live.json")))["rounds"]
def event_ids(rid):
    a = json.load(open(os.path.join(V3, "packets", f"R{rid}", "answer_1b.json"))); priv = json.load(open(os.path.join(V3, "packets", f"R{rid}", "private_1b.json")))
    ids = set()
    for h in a.get("hedges", []):
        k = h.get("event") or h["contract"].split(".")[0]
        if k in priv and "event_id" in priv[k]: ids.add(priv[k]["event_id"])
    return ids
want = {}
for r in rounds:
    want[r] = (set(), event_ids(r)); want[r][0].add(r)
allids = sorted({i for p, h in want.values() for i in p | h})
def state(eid):
    e = P.page(f"{P.GAMMA}/{eid}")
    if not e: return None
    ms = e.get("markets") or []
    return {"closed": bool(e.get("closed")), "markets": len(ms), "markets_closed": sum(1 for m in ms if m.get("closed")), "markets_resolved": sum(1 for m in ms if m.get("umaResolutionStatus") == "resolved")}
with ThreadPoolExecutor(8) as ex: st = dict(zip(allids, ex.map(state, allids)))
out = []
for r in rounds:
    p, h = want[r]; H = pool[r]["horizon"]
    legs = {i: st.get(i) for i in sorted(p | h)}
    done = all(v and v["markets"] and v["markets_resolved"] == v["markets"] for v in legs.values())
    out.append({"round": r, "title": pool[r]["title"], "horizon": dt.datetime.fromtimestamp(H, dt.timezone.utc).strftime("%Y-%m-%d"), "days_to_horizon": round((H - now) / 86400), "hedge_events": len(h), "all_events_fully_resolved": done, "events": legs})
json.dump({"at": now, "rounds": out}, open(os.path.join(HERE, "v3_status.json"), "w"), indent=1)
print("rounds", len(out), "| fully resolved:", sum(o["all_events_fully_resolved"] for o in out), "| horizons", min(o["horizon"] for o in out), "to", max(o["horizon"] for o in out))
for o in sorted(out, key=lambda o: o["horizon"])[:6]: print(o["round"], o["horizon"], o["title"][:50], "hedge events", o["hedge_events"])
