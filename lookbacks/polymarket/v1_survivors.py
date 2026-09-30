"""V1 survivor count (V1_prereg.md A11). Prices are read only to test availability at the lock; outcomes are not read.  python lookbacks/polymarket/v1_survivors.py <universe.jsonl.gz>"""
import collections, datetime as dt, json, sys
sys.path.insert(0, __file__.rsplit("/lookbacks/", 1)[0])
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import v1_pool as P
from nomad16 import pmgraph as G

here = __file__.rsplit("/", 1)[0]
pool = json.load(open(f"{here}/v1_pool.json")); draw = {d["id"] for d in json.load(open(f"{here}/v1_draw.json"))}
def parse(t):
    t = t.replace("Z", "+00:00").replace(" ", "T")
    if t.endswith("+00"): t += ":00"
    return dt.datetime.fromisoformat(t)
def ts(t): return int(parse(t).timestamp())

# live set: closed events (crawl) and the recorder's open set
CLS = {"partition_exact", "partition_open", "ladder", "date_ladder"}
live = []
for eid, e in P.crawl_closed().items():
    if {t.get("slug") for t in (e.get("tags") or [])} & P.EXCL or not e.get("startDate") or not e.get("closedTime"): continue
    c = P.compact(e); c["class"] = G.structure(c)["class"]
    if c["class"] in CLS and c["volume"] >= 100_000: live.append((ts(c["start"]), ts(c["closed_time"]), eid, G.template(c["title"])))
for e in G.load_universe(sys.argv[1]):
    if e.get("header_only") or not e.get("start"): continue
    if G.structure(e)["class"] in CLS and float(e.get("volume") or 0) >= 100_000: live.append((ts(e["start"]), 4102444800, str(e["id"]), G.template(e["title"])))
print("live-set candidates (usable exact-structure events, closed crawl + open now):", len(live))

def priced(tok, lock):
    for fid in (60, 720):
        h = P.page(f"https://clob.polymarket.com/prices-history?market={tok}&startTs={lock - 5 * 86400}&endTs={lock}&fidelity={fid}")
        pts = [x for x in (h or {}).get("history", []) if x["t"] <= lock and lock - x["t"] <= 48 * 3600]
        if pts: return True
    return False

rows = []
for e in pool:
    lock = (ts(e["start"]) + ts(e["closed_time"])) // 2
    n_priced = sum(1 for m in e["markets"] if m["tokens"] and priced(m["tokens"][0], lock))
    tpl = G.template(e["title"])
    menu = {t for (s, c, i, t) in live if s <= lock <= c and i != e["id"] and t != tpl}
    rows.append({"id": e["id"], "title": e["title"], "class": e["class"], "group": e["group"], "drawn": e["id"] in draw, "lock": lock, "markets": len(e["markets"]), "priced": n_priced, "menu_templates": len(menu)})
    print(e["id"], e["class"], f"priced {n_priced}/{len(e['markets'])} menu {len(menu)}", flush=True)
json.dump(rows, open(f"{here}/v1_survivors.json", "w"), indent=1)

def summarize(R, label):
    out = {"events": len(R)}
    for k in (1, 2, 3):
        out[f"S1>={k}"] = sum(r["priced"] >= k for r in R)
    out["S2 (menu>=10)"] = sum(r["menu_templates"] >= 10 for r in R)
    out["survivors (S1>=3 and S2)"] = sum(r["priced"] >= 3 and r["menu_templates"] >= 10 for r in R)
    out["by class"] = dict(collections.Counter(r["class"] for r in R if r["priced"] >= 3 and r["menu_templates"] >= 10))
    out["by group"] = dict(collections.Counter(r["group"] for r in R if r["priced"] >= 3 and r["menu_templates"] >= 10))
    print(f"\n== {label}\n" + json.dumps(out, indent=1))
summarize(rows, "all 73 pool events"); summarize([r for r in rows if r["drawn"]], "the 24 drawn")
mt = sorted(r["menu_templates"] for r in rows); print("\nmenu templates live at lock: min", mt[0], "median", mt[len(mt) // 2], "max", mt[-1])
