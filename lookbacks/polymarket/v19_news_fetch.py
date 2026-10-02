#!/usr/bin/env python3
"""Headlines from the 7 days before each lock, from GDELT (V19_NEWS_prereg.md §1). Standard library only, so it runs on any machine with the repo.

GDELT allows one request every 5 seconds per address. A cloud container shares its address and is refused, so run this on your own machine:

    git pull
    python3 lookbacks/polymarket/v19_news_fetch.py t2_pass5 t2_pass4

It writes lookbacks/polymarket/bt/news/<pass>_headlines.json, saving every 10 events; if stopped, run it again and it carries on.
It reads only each event's title and lock time from the frozen frame. It never reads prices, outcomes or answers.
"""
import datetime as dt, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); NEWS = os.path.join(HERE, "bt", "news")
WINDOW_D, KEEP, MIN_HITS, MAX_TERMS, SPACING = 7, 25, 5, 3, 5.5
STOP = set("""will what who which when where how why whose the a an and or of in on at by for to from with without into over under after before
during between above below up down than vs versus is are be been was were do does did has have had this that these those it its next
first second third last highest lowest most least more less any each every other others another price prices close closes closing
end ends ending finish finishes reach reaches hit hits dip dips win wins winner winners election elections vote votes seats seat party
how many much number share percent percentage range bucket buckets market markets yes no announce announced announcement say said says
mention mentions january february march april may june july august september october november december jan feb mar apr jun jul aug sep
sept oct nov dec monday tuesday wednesday thursday friday saturday sunday week weekly month monthly year yearly today tomorrow q1 q2 q3 q4
day days daily presidential parliamentary legislative congressional gubernatorial mayoral municipal regional general national
assembly senate governor round runoff primary primaries place""".split())
R6 = re.compile(r"polymarket|kalshi|prediction market|betting|\bbets?\b|\bodds\b|sportsbook|bookmaker|manifold", re.I)
LEAK = re.compile(r"(\bresolved (to|as|yes|no)\b|\bhas (now |already )?resolved\b|\bwas resolved\b|\bhas been resolved\b|\bfinal(ly)? (result|outcome)\b|\bupdate[d]?\s*[:\-]|\bthe outcome (was|is)\b|\bnow resolved\b)", re.I)   # = v1_packet.LEAK
UA = {"User-Agent": "NomadResearch/0.1 (backtest; headlines before a date only)"}


def terms_of(title):
    """Up to 3 query terms from the title: capitalised words first, else the longest non-generic words."""
    clean = [w.strip(".'-") for w in re.findall(r"[^\W\d_][\w&'\.-]*", title or "")]
    caps = [w for w in clean if w[:1].isupper() and w.lower() not in STOP and len(w) >= 3]
    rest = sorted({w for w in clean if w.lower() not in STOP and len(w) >= 4 and w not in caps}, key=lambda w: (-len(w), w))
    seen, out = set(), []
    for w in caps + rest:
        if w.lower() not in seen:
            seen.add(w.lower()); out.append(w)
    return out[:MAX_TERMS]


def gdelt(terms, lock):
    fmt = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    q = " ".join(f'"{t}"' if " " in t else t for t in terms) + " sourcelang:english"
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": q, "mode": "ArtList", "maxrecords": 75, "format": "json", "sort": "DateDesc",
         "startdatetime": fmt(lock - WINDOW_D * 86400), "enddatetime": fmt(lock)}))
    for i in range(8):
        time.sleep(SPACING)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (i + 1)); continue
            return {"query": q, "error": f"HTTP {e.code}", "articles": []}
        except Exception:
            time.sleep(10 * (i + 1)); continue
        if not raw.strip().startswith("{"):                  # GDELT answers a rate limit or a bad query with plain text
            if "limit requests" in raw:
                time.sleep(15 * (i + 1)); continue
            return {"query": q, "error": raw.strip()[:160], "articles": []}
        try:
            return {"query": q, "articles": json.loads(raw).get("articles", [])}
        except json.JSONDecodeError:
            return {"query": q, "error": "bad json", "articles": []}
    return {"query": q, "error": "gave up after retries", "articles": []}


def keep(arts, lock):
    """English headlines seen before the lock, without prediction-market or odds headlines (R6) or leak-check hits, newest first, at most 25."""
    out, seen = [], set()
    for a in arts:
        t = " ".join((a.get("title") or "").split())
        try:
            seen_at = dt.datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            continue
        if not t or seen_at >= lock or (a.get("language") or "English") != "English" or R6.search(t) or LEAK.search(t) or t.lower() in seen:
            continue
        seen.add(t.lower()); out.append({"seen": dt.datetime.fromtimestamp(seen_at, dt.timezone.utc).strftime("%Y-%m-%d"), "source": a.get("domain"), "title": t, "ts": seen_at})
    return sorted(out, key=lambda x: -x["ts"])[:KEEP]


def hpath(d):
    return os.path.join(NEWS, f"{d}_headlines.json")


def save(got, d):
    tmp = hpath(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(got, f, indent=1, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, hpath(d))


def fetch(d):
    os.makedirs(NEWS, exist_ok=True)
    fr = json.load(open(os.path.join(HERE, "bt", d, "frame.json"), encoding="utf-8"))["events"]
    got = json.load(open(hpath(d), encoding="utf-8")) if os.path.exists(hpath(d)) else {}
    for i, ev in enumerate(fr):
        if str(ev["id"]) in got and not any(t.get("error") for t in got[str(ev["id"])]["tries"]):
            continue                                          # done; an event that ended on an error is tried again
        terms = terms_of(ev["title"]); tries, hs = [], []
        while terms:
            r = gdelt(terms, ev["lock"]); hs = keep(r["articles"], ev["lock"])
            tries.append({"query": r["query"], "error": r.get("error"), "returned": len(r["articles"]), "kept": len(hs)})
            if len(hs) >= MIN_HITS or len(terms) == 1:
                break
            terms = terms[:-1]
        got[str(ev["id"])] = {"title": ev["title"], "lock": ev["lock"], "tries": tries, "headlines": hs}
        if (i + 1) % 10 == 0:
            save(got, d); print(f"{d}: {i + 1}/{len(fr)}", flush=True)
    save(got, d)
    errs = sum(1 for v in got.values() if any(t.get("error") for t in v["tries"]))
    print(f"{d}: done, {len(got)} events, {errs} ended on an error (run again to retry them)", flush=True)


if __name__ == "__main__":
    for d in sys.argv[1:] or ["t2_pass5", "t2_pass4"]:
        fetch(d)
