"""Foundation checks on the frozen V1 pool (2026-09-30): do the exactness assumptions hold on real resolved data, and does the draw have prices at its locks?
Reads outcomes only to test the structure claims (partition has one winner; ladder is nested), never for selection. Output: v1_foundation_checks_output.txt"""
import collections, datetime as dt, json, re, sys, urllib.request
H = {"User-Agent": "Mozilla/5.0"}
pool = json.load(open("v1_pool.json")); draw = json.load(open("v1_draw.json"))
YES = lambda m: json.loads(m["final"])[0] == "1"       # outcomes are [Yes, No]; final prices decisive by pool construction


def strike(q):
    q = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(,?\s*20\d\d)?", "", q, flags=re.I)
    m = re.search(r"\$\s?([\d,]*\.?\d+)\s?(k|m|b|million|billion|t|trillion)?", q, re.I) or re.search(r"\b(\d[\d,]*\.?\d*)\s?(k|m|b|%)?\b", q)
    if not m:
        return None
    v = float(m.group(1).replace(",", "")); u = (m.group(2) or "").lower()
    return v * {"k": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9, "t": 1e12, "trillion": 1e12}.get(u, 1)


print("A. partitions: exactly one winner?")
res = collections.Counter()
for e in pool:
    if e["class"].startswith("partition"):
        n = sum(YES(m) for m in e["markets"])
        res[(e["class"], n)] += 1
print("  ", dict(res))

print("B. terminal ladders: is the resolved YES set nested (at most one switch along the strikes)?")
ok = bad = skipped = 0; badlist = []
for e in pool:
    if e["class"] == "ladder" and e["ladder_kind"] == "terminal":
        pts = [(strike(m["q"]), YES(m)) for m in e["markets"]]
        if any(s is None for s, _ in pts) or len({s for s, _ in pts}) < 3:
            skipped += 1; continue
        pts.sort(key=lambda x: x[0]); seq = [y for _, y in pts]
        sw = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
        if sw <= 1: ok += 1
        else: bad += 1; badlist.append((e["id"], e["title"][:50], "".join("Y" if y else "n" for y in seq)))
print(f"   nested {ok}, not nested {bad}, skipped (unparseable) {skipped}"); [print("   NOT NESTED:", b) for b in badlist[:8]]

print("B2. date ladders: ordered by each market's own end date, is 'by <date>' nested in time (once YES, every later date YES; 'through/until' runs the other way)?")
sup = json.load(open("v1_pool_market_dates.json"))
okd = badd = skd = 0; badl = []
for e in pool:
    if e["class"] == "date_ladder":
        pts = [(sup.get(m["cid"], {}).get("end"), YES(m)) for m in e["markets"]]
        if any(w is None for w, _ in pts) or len({w for w, _ in pts}) < 3: skd += 1; continue
        pts.sort(key=lambda x: x[0]); seq = [y for _, y in pts]
        rev = bool(re.search(r"\b(through|until|continues)\b", e["markets"][0]["q"], re.I))
        if rev: seq = seq[::-1]
        if all(not (a and not b) for a, b in zip(seq, seq[1:])): okd += 1
        else: badd += 1; badl.append((e["id"], e["title"][:50], "".join("Y" if y else "n" for y in seq)))
print(f"   nested {okd}, not nested {badd}, unparseable {skd}"); [print("   NOT NESTED:", b) for b in badl[:8]]

print("C. resolution timing: closedTime against the scheduled end (days early; negative = late)")
early = []
for e in pool:
    if e["end"] and e["closed_time"]:
        end = dt.datetime.fromisoformat(e["end"].replace("Z", "+00:00")); ct = dt.datetime.fromisoformat(e["closed_time"].replace("Z", "+00:00").replace(" ", "T") if "T" in e["closed_time"] else e["closed_time"].replace("+00", "+00:00").replace(" ", "T"))
        early.append((end - ct).days)
early.sort(); q = lambda p: early[int(p * (len(early) - 1))]
print(f"   n {len(early)}  q10 {q(.1)}  median {q(.5)}  q90 {q(.9)}  resolved >30 days before scheduled end: {sum(d > 30 for d in early)}")

print("D. the draw: is there an eligible price (a point within 48 h before the lock) for each contract?")
def g(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read())
    except Exception: return None
def parse(t): return dt.datetime.fromisoformat(t.replace("Z", "+00:00").replace(" ", "T").replace("+00", "+00:00") if not t.endswith("+00:00") and t.endswith("+00") else t.replace("Z", "+00:00").replace(" ", "T"))
byid = {e["id"]: e for e in pool}; tot = collections.Counter(); ok = collections.Counter(); ev_ok = []
for d in draw:
    e = byid[d["id"]]
    lock = int((parse(e["start"]).timestamp() + parse(e["closed_time"]).timestamp()) / 2)
    got = 0
    for m in e["markets"]:
        tok = m["tokens"][0] if m["tokens"] else None
        tot[e["class"]] += 1
        if not tok: continue
        found = False
        for fid in (60, 720):
            h = g(f"https://clob.polymarket.com/prices-history?market={tok}&startTs={lock - 5 * 86400}&endTs={lock}&fidelity={fid}")
            pts = [x for x in (h or {}).get("history", []) if x["t"] <= lock and lock - x["t"] <= 48 * 3600]
            if pts: found = True; break
        if found: ok[e["class"]] += 1; got += 1
    ev_ok.append((got, len(e["markets"])))
for c in tot: print(f"   {c}: {ok[c]}/{tot[c]} contracts have an eligible lock price ({ok[c] / tot[c]:.0%})")
full = sum(1 for a, b in ev_ok if a == b); half = sum(1 for a, b in ev_ok if a >= b / 2)
print(f"   events with every contract priced: {full}/{len(ev_ok)}; with at least half priced: {half}/{len(ev_ok)}; with none: {sum(1 for a, b in ev_ok if a == 0)}")
