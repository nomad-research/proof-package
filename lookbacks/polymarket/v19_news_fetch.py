#!/usr/bin/env python3
"""Headlines from the 7 days before each lock, from GDELT (V19_NEWS_prereg.md §1). Standard library only, so it runs on any machine with the repo.

Google News search by default (addendum A3; add --gdelt for GDELT, which throttles hard). A cloud container is refused by both, so run this on your own machine:

    git pull
    python3 lookbacks/polymarket/v19_news_fetch.py t2_pass5 t2_pass4

It writes lookbacks/polymarket/bt/news/<pass>_news.json, saving every 10 requests; if stopped, run it again and it carries on.
It reads only each event's title and lock time from the frozen frame. It never reads prices, outcomes or answers.
"""
import datetime as dt, email.utils, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__)); NEWS = os.path.join(HERE, "bt", "news")
WINDOW_D, KEEP, MIN_HITS, MAX_TERMS, SPACING, RECORDS = 7, 25, 5, 3, 12.0, 250
SOURCE, G_SPACING = "google", 2.5           # addendum A3: Google News search by default; "gdelt" stays available
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


CONNECT = {"of", "el", "de", "la", "del", "da", "do", "dos", "das", "al", "bin", "van", "von", "der", "le", "du", "and", "&"}


def terms_of(title):
    """Up to 3 query terms from the title, names first: runs of capitalised words in title order, joined across connectors such as "of"
    or "el-" ("Strait of Hormuz", "Bab el-Mandeb Strait", "Augusto Cury"); a name joined by a connector also gives its last word as a term.
    A title with no name asks for its longest non-generic words together ("&jobs added"). The first term is the one requested."""
    toks = [t.strip(".'-_") for t in re.findall(r"[^\W\d_][\w&'\.-]*|[^\w\s]", (title or "").replace("_", " "))]
    capw = lambda w: (w[:1].isupper() and w.lower() not in STOP and len(w) >= 2) or ("-" in w and w.split("-")[0].lower() in CONNECT and w.split("-")[1][:1].isupper())
    runs, cur = [], []
    for i, w in enumerate(toks):
        link = w.lower() in CONNECT and cur and i + 1 < len(toks) and capw(toks[i + 1])
        if capw(w) or link:
            cur.append(w)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    runs = [r for r in runs if len(" ".join(r)) >= 3]
    names = [" ".join(r) for r in runs if len(r) > 1] + [" ".join(r) for r in runs if len(r) == 1]
    names = sorted(names, key=lambda n: (" " not in n, [" ".join(r) for r in runs].index(n)))      # multi-word names first, each in title order
    tails = [r[-1] for r in runs if len(r) > 2 and any(x.lower() in CONNECT for x in r)]
    words = [t for t in toks if re.match(r"[^\W\d_]", t or "")]
    rest = [w for w in dict.fromkeys(words) if w.lower() not in STOP and w.lower() not in CONNECT and len(w) >= 4 and not any(w.lower() in n.lower() for n in names)]
    if not names:
        top = sorted(rest, key=lambda w: (-len(w), w))[:2]
        return (["&" + " ".join(w for w in rest if w in top)] if top else []) + sorted(rest, key=lambda w: (-len(w), w))[:2]
    seen, out = set(), []
    for t in names + tails + sorted(rest, key=lambda w: (-len(w), w)):
        if t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return out[:MAX_TERMS]


def has(title, term):
    if term.startswith("&"):                                  # several words, all required
        return all(w.lower() in title.lower() for w in term[1:].split())
    return term.lower() in title.lower()


def gdelt(term, lock):
    fmt = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    q = (term[1:] if term.startswith("&") else f'"{term}"' if " " in term else term) + " sourcelang:english"
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": q, "mode": "ArtList", "maxrecords": RECORDS, "format": "json", "sort": "DateDesc",
         "startdatetime": fmt(lock - WINDOW_D * 86400), "enddatetime": fmt(lock)}))
    for i in range(6):
        time.sleep(SPACING)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    GDELT asked us to slow down (429); waiting {60 * 2 ** i}s", flush=True); time.sleep(60 * 2 ** i); continue
            return {"query": q, "error": f"HTTP {e.code}", "articles": []}
        except Exception as e:
            print(f"    request failed ({type(e).__name__}); waiting {10 * (i + 1)}s", flush=True); time.sleep(10 * (i + 1)); continue
        if not raw.strip().startswith("{"):                  # GDELT answers a rate limit or a bad query with plain text
            if "limit requests" in raw:
                print(f"    GDELT asked us to slow down; waiting {60 * 2 ** i}s", flush=True); time.sleep(60 * 2 ** i); continue
            return {"query": q, "error": raw.strip()[:160], "articles": []}
        try:
            return {"query": q, "articles": json.loads(raw).get("articles", [])}
        except json.JSONDecodeError:
            return {"query": q, "error": "bad json", "articles": []}
    return {"query": q, "error": "gave up after retries", "articles": []}


def google(term, lock):
    """Google News RSS search for the term, published from 7 days before the lock to the lock's day (the exact cut is made in keep()).
    Returned in GDELT's article shape: title, seendate (the publication time), domain, language."""
    day = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")
    q = (term[1:] if term.startswith("&") else f'"{term}"' if " " in term else term)
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{q} after:{day(lock - WINDOW_D * 86400)} before:{day(lock + 86400)}", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    for i in range(6):
        time.sleep(G_SPACING)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) NomadResearch/0.1"}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"    Google asked us to slow down ({e.code}); waiting {30 * 2 ** i}s", flush=True); time.sleep(30 * 2 ** i); continue
            return {"query": q, "error": f"HTTP {e.code}", "articles": []}
        except Exception as e:
            print(f"    request failed ({type(e).__name__}); waiting {10 * (i + 1)}s", flush=True); time.sleep(10 * (i + 1)); continue
        try:
            return {"query": q, "articles": rss_articles(raw)}
        except ET.ParseError:
            return {"query": q, "error": "not an RSS feed (a captcha page?)", "articles": []}
    return {"query": q, "error": "gave up after retries", "articles": []}


def rss_articles(raw):
    out = []
    for it in ET.fromstring(raw).iter("item"):
        title, src, pub = it.findtext("title") or "", it.find("source"), it.findtext("pubDate")
        name = (src.text or "").strip() if src is not None else ""
        if name and title.endswith(" - " + name):
            title = title[: -len(" - " + name)]
        try:
            ts = email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        except (TypeError, ValueError):
            continue
        host = urllib.parse.urlparse(src.get("url", "")).netloc if src is not None else ""
        out.append({"title": title, "seendate": ts.strftime("%Y%m%dT%H%M%SZ"), "domain": host or name, "language": "English"})
    return out


def keep(arts, lock, cap=KEEP):
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
    out = sorted(out, key=lambda x: -x["ts"])
    return out[:cap] if cap else out


def hpath(d):
    return os.path.join(NEWS, f"{d}_news.json")


def save(got, d):
    tmp = hpath(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(got, f, indent=1, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, hpath(d))


def fetch(d):
    """One request per distinct (term, lock): the event's first term, and its second only if the first leaves fewer than 5 headlines.
    Each event then keeps the headlines containing all its terms, dropping the last term until at least 5 remain (down to one term)."""
    os.makedirs(NEWS, exist_ok=True)
    fr = json.load(open(os.path.join(HERE, "bt", d, "frame.json"), encoding="utf-8"))["events"]
    got = json.load(open(hpath(d), encoding="utf-8")) if os.path.exists(hpath(d)) else {"source": SOURCE, "requests": {}, "events": {}}
    if got.get("source", "gdelt") != SOURCE:                  # never mix sources in one file
        os.replace(hpath(d), hpath(d) + f".{got.get('source', 'gdelt')}_partial"); got = {"source": SOURCE, "requests": {}, "events": {}}
    req = got["requests"]; n_req = len({(t, ev["lock"]) for ev in fr for t in terms_of(ev["title"])[:1]})
    print(f"{d}: {len(fr)} events, about {n_req} requests, {len(req)} already held; source {SOURCE}, one request every {SPACING if SOURCE == 'gdelt' else G_SPACING:.1f}s", flush=True)

    def ask(term, lock):
        k = f"{term}|{lock}"
        if k not in req or req[k].get("error"):
            r = (gdelt if SOURCE == "gdelt" else google)(term, lock); req[k] = {"query": r["query"], "error": r.get("error"), "articles": keep_all(r["articles"], lock)}
            print(f"  {term} @ {dt.datetime.fromtimestamp(lock, dt.timezone.utc):%Y-%m-%d}: {len(req[k]['articles'])} headlines" + (f" ({r['error']})" if r.get("error") else ""), flush=True)
            if len(req) % 10 == 0:
                save(got, d)
        return req[k]

    for i, ev in enumerate(fr):
        terms = terms_of(ev["title"]); pool, used = [], []
        for t in terms[:2]:
            r = ask(t, ev["lock"]); used.append(f"{t}|{ev['lock']}"); pool += r["articles"]
            if len(pick(pool, terms[:1])) >= MIN_HITS:
                break
        hs, k = [], len(terms)
        while k >= 1:
            hs = pick(pool, terms[:k])
            if len(hs) >= MIN_HITS or k == 1:
                break
            k -= 1
        if not any(has(h["title"], terms[0]) for h in hs) and len(terms) > 1:
            hs = pick(pool, terms[1:2])                       # the first term found nothing: fall back to the second term's request
        got["events"][str(ev["id"])] = {"title": ev["title"], "lock": ev["lock"], "terms": terms, "requests": used, "terms_matched": k, "headlines": hs[:KEEP]}
    save(got, d)
    errs = sum(1 for v in req.values() if v.get("error"))
    print(f"{d}: done, {len(got['events'])} events, {len(req)} requests, {errs} ended on an error (run again to retry them)", flush=True)


def keep_all(arts, lock):
    """keep() without the cap: every English headline seen before the lock that passes the R6 and leak filters."""
    return keep(arts, lock, cap=None)


def pick(pool, terms):
    seen, out = set(), []
    for h in sorted(pool, key=lambda x: -x["ts"]):
        if h["title"].lower() not in seen and all(has(h["title"], t) for t in terms):
            seen.add(h["title"].lower()); out.append(h)
    return out[:KEEP]


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--gdelt" in args:
        SOURCE = "gdelt"; args.remove("--gdelt")
    for d in args or ["t2_pass5", "t2_pass4"]:
        fetch(d)
