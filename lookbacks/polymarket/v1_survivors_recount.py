"""Recount of survivors under the packet's actual eligibility (V1_prereg.md A13): a contract is shown only if its market was not already closed at the lock AND it has a price
within 48 hours before the lock. A11 counted the price condition only. Reads prices for availability, never outcomes.  python lookbacks/polymarket/v1_survivors_recount.py"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v1_packet as K
pool = json.load(open(f"{HERE}/v1_pool.json")); mkt = json.load(open(f"{HERE}/v1_pool_market_dates.json"))
draw = {d["id"] for d in json.load(open(f"{HERE}/v1_draw.json"))}; res = json.load(open(f"{HERE}/v1_reserve.json"))
reserve = [r["id"] for r in res["reserve_in_order"]]
rows = []
for e in pool:
    lock = K.lock_of(e)
    ms = [dict(m, mclosed=(mkt.get(m["cid"]) or {}).get("closed")) for m in e["markets"]]
    shown = K.eligible(ms, lock, K.price_fn_live)
    rows.append({"id": e["id"], "title": e["title"], "class": e["class"], "group": e["group"], "markets": len(ms), "shown": len(shown), "drawn": e["id"] in draw, "reserve": e["id"] in reserve})
    print(e["id"], e["class"], f"shown {len(shown)}/{len(ms)}", flush=True)
json.dump(rows, open(f"{HERE}/v1_survivors_recount.json", "w"), indent=1)
def s(R, k): return sum(r["shown"] >= k for r in R)
print("\nevents with at least k contracts shown (k=1,2,3):")
for label, R in (("all 73", rows), ("drawn 24", [r for r in rows if r["drawn"]]), ("reserve 12", [r for r in rows if r["reserve"]])):
    print(f"  {label}: {s(R,1)}, {s(R,2)}, {s(R,3)} of {len(R)}")
print("drawn events with fewer than 3 shown:", [(r["id"], r["shown"]) for r in rows if r["drawn"] and r["shown"] < 3])
print("reserve events with fewer than 3 shown:", [(r["id"], r["shown"]) for r in rows if r["reserve"] and r["shown"] < 3])
