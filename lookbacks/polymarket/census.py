"""Polymarket catalogue census. Definitions in CENSUS_SPEC.md, written before this ran.   python lookbacks/polymarket/census.py"""
import collections
import json
import re
import urllib.error
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (research nomad)"}
G = "https://gamma-api.polymarket.com/events"
EXCL = set("sports,games,esports,soccer,tennis,nfl,nba,nhl,mlb,hockey,ufc,boxing,golf,f1,cricket,rugby,league-of-legends,dota-2,counter-strike-2,valorant,pop-culture,entertainment,music,movies,celebrities,daily-temperature,highest-temperature,uefa-nations-league,unl-matchday".split(","))
GROUPS = [("geopolitics", "geopolitics world war iran israel russia ukraine china taiwan middle-east ceasefire nato strait-of-hormuz"),
          ("politics and elections", "politics elections global-elections us-presidential-election midterms trump congress"),
          ("economy and finance", "fed fed-rates economy finance stocks equities oil commodities inflation earnings earn-4 ipo tariffs trade"),
          ("crypto", "crypto bitcoin ethereum crypto-prices"), ("technology and science", "tech ai big-tech openai ai-releases science space health climate energy spacex"),
          ("business and manufacturing", "business manufacturing companies ipo")]
GROUPS = [(n, set(s.split())) for n, s in GROUPS]


def page(url):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read())
    except urllib.error.HTTPError:
        return []
    except Exception:
        return None


def crawl(query):
    out, off = [], 0
    while off < 6000:
        p = page(f"{G}?{query}&limit=100&offset={off}")
        if not p:
            break
        out += p; off += 100
    return out


def vol(m):
    return float(m.get("volumeNum") or m.get("volume") or 0)


MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
DATE_TOK = re.compile(rf"\b{MON}\s+\d{{1,2}}(,?\s*20\d\d)?\b|\b{MON}\s+20\d\d\b|\bq[1-4]\b|\b20\d\d\b|\b{MON}\b", re.I)
NUM_TOK = re.compile(r"\$\s?[\d,\.]+\s?(k|m|b|million|billion)?|\b\d[\d,\.]*\s?(%|k|m|b)\b|\b\d[\d,\.]*\b", re.I)
COND = re.compile(r"\b(if|conditional on|given that|assuming)\b", re.I)


def toks(q):
    d = [m.group(0).lower() for m in DATE_TOK.finditer(q)]
    rest = DATE_TOK.sub("@", q)
    n = [m.group(0).lower() for m in NUM_TOK.finditer(rest)]
    stem = re.sub(r"\s+", " ", NUM_TOK.sub("#", rest)).strip().lower()
    return tuple(d), tuple(n), stem


def classify(e):
    ms = e.get("markets") or []
    n = len(ms)
    if n <= 2:
        return "single or pair"
    slots = any(m.get("negRiskOther") or (m.get("groupItemTitle") or "").strip().lower() in ("other", "someone else") or re.match(r"person [a-z]$", (m.get("groupItemTitle") or "").strip().lower()) for m in ms)
    if e.get("negRisk"):
        return "partition with an open slot" if slots else "partition, exact"
    T = [toks(m.get("question") or "") for m in ms]
    common = collections.Counter(t[2] for t in T).most_common(1)
    same = [t for t in T if common and t[2] == common[0][0]]
    thr = len({m.get("groupItemThreshold") for m in ms if m.get("groupItemThreshold") not in (None, "")}) >= 3
    if thr or (len(same) >= 3 and len({t[1] for t in same}) >= 3):
        return "threshold ladder"
    if len(same) >= 3 and len({t[0] for t in same}) >= 3:
        return "date ladder"
    if any(COND.search(m.get("question") or "") for m in ms):
        return "conditional chain (low confidence)"
    return "other multi-market"


def group(e):
    slugs = {(t.get("slug") or "") for t in (e.get("tags") or [])}
    for name, s in GROUPS:
        if slugs & s:
            return name
    return "other"


def usable(e, mv=10000, ev=100000):
    ms = e.get("markets") or []
    return float(e.get("volume") or 0) >= ev and sum(vol(m) >= mv for m in ms) >= 3


print("crawling ...")
active = {}
for order in ("volume24hr", "volume", "liquidity", "endDate", "startDate"):
    for asc in ("false", "true"):
        for e in crawl(f"active=true&closed=false&order={order}&ascending={asc}"):
            active[e["id"]] = e
active = list(active.values())
closed = {}
for order in ("volume", "endDate", "liquidity", "startDate"):
    for asc in ("false", "true"):
        for e in crawl(f"closed=true&order={order}&ascending={asc}"):
            closed[e["id"]] = e
print(f"active events {len(active)}; closed events {len(closed)}")
rows = []
dropped = 0
for status, evs in (("active", active), ("closed", list(closed.values()))):
    for e in evs:
        if {(t.get("slug") or "") for t in (e.get("tags") or [])} & EXCL:
            dropped += 1; continue
        rows.append(dict(status=status, cls=classify(e), grp=group(e), usable=usable(e), u1k=usable(e, 1000, 100000), u100k=usable(e, 100000, 100000), vol=float(e.get("volume") or 0),
                         n=len(e.get("markets") or []), end=(e.get("endDate") or "")[:10], title=e.get("title") or "", id=e["id"]))
print(f"in scope {len(rows)}; dropped as sport, gaming, entertainment or temperature: {dropped}")
CLS = ["partition, exact", "partition with an open slot", "threshold ladder", "date ladder", "conditional chain (low confidence)", "other multi-market", "single or pair"]
for status in ("active", "closed"):
    R = [r for r in rows if r["status"] == status]
    print(f"\n== {status}: events by class (usable structures in brackets), total volume $M")
    for c in CLS:
        X = [r for r in R if r["cls"] == c]
        print(f"  {c:<38}{len(X):>6}  ({sum(r['usable'] for r in X):>4} usable)   ${sum(r['vol'] for r in X) / 1e6:>10,.1f}M")
    print("  usable multi-market structures by group and class:")
    T = collections.defaultdict(collections.Counter)
    for r in R:
        if r["usable"] and r["cls"] != "single or pair":
            T[r["grp"]][r["cls"]] += 1
    for g, cn in sorted(T.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"    {g:<28}{sum(cn.values()):>5}   " + ", ".join(f"{k.split(',')[0].split(' (')[0]} {v}" for k, v in cn.most_common()))
C = [r for r in rows if r["status"] == "closed" and r["end"] > "2026-06-30"]
print(f"\nclosed events ending after 2026-06-30 (clean for a round): {len(C)}; usable multi-market: {sum(r['usable'] and r['cls'] != 'single or pair' for r in C)}")
for c in CLS[:-1]:
    print(f"  {c:<38}{sum(r['cls'] == c and r['usable'] for r in C):>4} usable of {sum(r['cls'] == c for r in C)}")
print("\nsensitivity of the usable count to the liquidity floor (multi-market, all statuses): market floor $1k:", sum(r['u1k'] and r['cls'] != 'single or pair' for r in rows),
      "| $10k:", sum(r['usable'] and r['cls'] != 'single or pair' for r in rows), "| $100k:", sum(r['u100k'] and r['cls'] != 'single or pair' for r in rows))
words = lambda t: {w for w in re.findall(r"[a-z]{4,}", t.lower())}
byg = collections.defaultdict(list)
for r in rows:
    if r["usable"]:
        byg[r["grp"]].append(words(r["title"]))
pairs = sum(1 for g, L in byg.items() for i in range(len(L)) for j in range(i + 1, len(L)) if len(L[i] & L[j]) >= 2)
print("cross-event candidate pairs among usable events (same group, two shared title words; unmeasured beyond this):", pairs)
json.dump(rows, open("census_rows.json", "w"))
print("NOTE: each ordering is capped near 2,100 events by the API; coverage is the union of orderings, not the whole catalogue.")
