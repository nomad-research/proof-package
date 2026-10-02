"""How much can be bought near the best price? (2026-10-01; describes the venue, declares nothing)

From the open-set snapshot T3 took today (t3/open_*.json.gz), a seeded sample of open markets. For each, the NO token's order book is read once from the
public CLOB endpoint, and the dollars on offer within 1 and 2 cents of the best ask are recorded. NO tokens whose best ask is between 0.50 and 0.95 are the
kind of position E1 takes. Output: bt/depth_sample.json.
"""
import json, os, random, sys, time, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import bt_audit as A
import bt_crawl as BC

snap = A.jload(os.path.join(HERE, "t3", "snapshot.json")); evs = A.jload(os.path.join(HERE, "t3", snap["file"]))
mk = []
for e in evs:
    for m in e["markets"]:
        if m.get("closed") or len(m.get("tokens") or []) < 2:
            continue
        outs = [o.lower() for o in json.loads(m.get("outcomes") or "[]")]
        if outs[:2] != ["yes", "no"]:
            continue
        mk.append({"event": e["title"], "q": m.get("q"), "no_token": m["tokens"][1], "event_volume": e.get("volume") or 0, "markets_in_event": len(e["markets"])})
random.Random(20261005).shuffle(mk)


def book(tok):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"https://clob.polymarket.com/book?token_id={tok}", headers=BC.H), timeout=30).read().decode("utf-8"))
    except Exception:
        return None


rows = []
for m in mk[:400]:
    b = book(m["no_token"]); time.sleep(0.1)
    if not b or not b.get("asks"):
        continue
    asks = sorted((float(x["price"]), float(x["size"])) for x in b["asks"])
    best = asks[0][0]
    d1 = sum(p * s for p, s in asks if p <= best + 0.01 + 1e-9); d2 = sum(p * s for p, s in asks if p <= best + 0.02 + 1e-9)
    rows.append(dict(m, best_ask=best, usd_within_1c=d1, usd_within_2c=d2))
    if len([r for r in rows if 0.5 <= r["best_ask"] <= 0.95]) >= 150:
        break
e1 = [r for r in rows if 0.5 <= r["best_ask"] <= 0.95]


def q(x, p):
    return float(np.quantile(x, p)) if x else None


out = {"taken_at": int(time.time()), "books_read": len(rows), "e1_type_books": len(e1),
       "e1_usd_within_1c": {f"p{int(p * 100)}": q([r["usd_within_1c"] for r in e1], p) for p in (0.25, 0.5, 0.75, 0.9)},
       "e1_usd_within_2c": {f"p{int(p * 100)}": q([r["usd_within_2c"] for r in e1], p) for p in (0.25, 0.5, 0.75, 0.9)},
       "by_event_volume": {}, "rows": rows}
for lo, hi in ((0, 1e5), (1e5, 1e6), (1e6, 1e12)):
    s = [r["usd_within_2c"] for r in e1 if lo <= r["event_volume"] < hi]
    out["by_event_volume"][f"{lo:g}-{hi:g}"] = {"n": len(s), "median_usd_within_2c": q(s, 0.5)}
json.dump(out, open(os.path.join(HERE, "bt", "depth_sample.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
