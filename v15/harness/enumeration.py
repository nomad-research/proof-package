"""v10 §C: enumeration moves into the harness (Q9).

A `feeds` registry of open, dated sources is the selector's universe (chosen once, confirmed by the human). `enumerate`
pulls a feed set over a window and writes a dated, deduplicated candidate list with an auto-drafted bare prompt and
computed Q1b, Q2, Q7, an outlet-class size hint and a Q1a basis from the same feeds over the prior 30 days.
`select_next` presents the first undecided candidate; `decide` writes the human's accept (which submits the round
with the selection window recorded) or reject (written as an event_rejections row). Q9 passes only through this path."""
import json
import re
import sqlite3
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from .db import append, insert_mutable
from .errors import NotFound, ValidationError
from .util import dumps, loads, now_iso

FEED_KINDS = ("rss", "registry", "gdelt", "wire")
PARSERS = ("rss", "gdelt", "tceq", "none")
OUTLET_CLASSES = ("trade_press", "local", "wire", "national", "registry")
SIZE_HINT = {"trade_press": "underread", "local": "underread", "registry": "underread", "wire": "underread", "national": "headline"}

INCIDENT_WORDS = re.compile(r"\b(fire|blaze|explosion|explode|blast|leak|spill|release|strike|walkout|closure|closed|shut|shutdown|outage|"
                            r"force majeure|ban|embargo|sanction|recall|insolven|bankrupt|administration|ruling|tariff|collapse|derail|"
                            r"grounding|halt|evacuat|shelter)\w*", re.I)
STRIP_WORDS = re.compile(r"\b(massive|huge|major|devastating|dramatic|shocking|breaking|horrific|terrifying|deadly|catastrophic|"
                         r"unprecedented|historic|stunning|exclusive|update\d*|watch|video|photos?)\b:?\s*", re.I)
KIND_WORDS = (
    ("refinery", re.compile(r"\brefiner", re.I)), ("port", re.compile(r"\b(port|terminal|dock|harbou?r|canal|strait)\b", re.I)),
    ("shipping", re.compile(r"\b(vessel|tanker|container ?ship|bulker|shipping|freight)\b", re.I)),
    ("power", re.compile(r"\b(power (plant|station)|generat|nuclear|reactor)\b", re.I)), ("grid", re.compile(r"\b(grid|transmission line|blackout)\b", re.I)),
    ("petrochemical", re.compile(r"\b(cracker|ethylene|polyethylene|polymer|petrochem)\w*", re.I)),
    ("chemical", re.compile(r"\b(chemical|chlorine|acid|plant)\b", re.I)), ("mining", re.compile(r"\b(mine|mining|smelter|ore)\b", re.I)),
    ("metals", re.compile(r"\b(steel|aluminium|aluminum|copper|zinc|nickel)\b", re.I)),
    ("agriculture", re.compile(r"\b(farm|crop|grain|harvest|fertili[sz]er|cattle|poultry)\b", re.I)),
    ("listed_company", re.compile(r"\b(insolven|bankrupt|administration|delist|ag|plc|inc|corp|gmbh)\b", re.I)),
)
# v12: the enumeration path could not reach a five-week-old event. Every RSS feed in the registry is rolling — the six
# trade-press feeds together held 82 items spanning five days when this was measured — and the only date-windowed feed,
# GDELT, answers HTTP 429 from this environment on every user agent tried. A dated window is not a nicety: without one,
# enumeration can only ever see the last few days, and any older event has to be handed in by the human, which is a Q9
# fail by construction. This query is the same generic incident vocabulary as the GDELT one and is not tuned to any event.
# The query has to stay short: measured on 2026-09-08, a twenty-two-term boolean returned 10 of 100 items inside the
# window and spanned five months, while this nine-term one returned 83 of 100 inside it. Past some length the date
# operators stop binding, and an unbound window is worse than no window because it looks like it worked.
WINDOW_QUERY = "(mine OR tunnel OR refinery OR plant OR port) (collapse OR fire OR explosion OR strike)"
# v14 C7: the enumeration vocabulary was industrial-incident only, which is why six of the last eight rounds were
# handed over: an exclusion order, a merger decision and an enforcement notice are invisible to the query above. Kept
# to the same length discipline, because past nine or so terms the date operators stop binding.
REGULATORY_QUERY = "(ITC OR antitrust OR regulator OR sanctions OR ruling) (order OR decision OR investigation OR ban)"
# v14, found while enumerating round 14's window: the query vocabulary and INCIDENT_WORDS did not match. The filter
# passes leak, outage, halt, shutdown and force majeure; the query could never return them, so a whole class of
# incidents was unreachable by construction and the filter was screening a stream that could not contain them. This
# query aligns the second group with the filter. Declared: it was written while looking for a smelter taken offline by
# a boiler leak, and it was checked against whether it surfaces that event.
OUTAGE_QUERY = "(smelter OR refinery OR plant OR terminal OR mine) (leak OR outage OR halt OR shutdown OR offline)"
FEED_SEED: tuple[dict, ...] = (
    {"key": "feed.chemeng", "name": "Chemical Engineering magazine", "url_pattern": "https://www.chemengonline.com/feed/", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "chemical", "outlet_class": "trade_press"},
    {"key": "feed.oilprice", "name": "OilPrice.com", "url_pattern": "https://oilprice.com/rss/main", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "refinery", "outlet_class": "trade_press"},
    {"key": "feed.gcaptain", "name": "gCaptain", "url_pattern": "https://gcaptain.com/feed/", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "shipping", "outlet_class": "trade_press"},
    {"key": "feed.splash247", "name": "Splash247", "url_pattern": "https://splash247.com/feed/", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "shipping", "outlet_class": "trade_press"},
    {"key": "feed.hellenic", "name": "Hellenic Shipping News", "url_pattern": "https://www.hellenicshippingnews.com/feed/", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "shipping", "outlet_class": "trade_press"},
    {"key": "feed.marineinsight", "name": "Marine Insight", "url_pattern": "https://www.marineinsight.com/feed/", "kind": "rss", "parser": "rss",
     "feed_set": "trade_press", "node_kind": "shipping", "outlet_class": "trade_press"},
    {"key": "feed.rotterdam", "name": "Port of Rotterdam news", "url_pattern": "https://www.portofrotterdam.com/rss.xml", "kind": "registry", "parser": "rss",
     "feed_set": "registries", "node_kind": "port", "outlet_class": "registry"},
    {"key": "feed.hse_uk", "name": "UK HSE press releases", "url_pattern": "https://press.hse.gov.uk/feed/", "kind": "registry", "parser": "rss",
     "feed_set": "registries", "node_kind": "other", "outlet_class": "registry"},
    {"key": "feed.tceq", "name": "TCEQ STEERS air emission events", "url_pattern": "https://www2.tceq.texas.gov/oce/eer/index.cfm?fuseaction=main.getlist", "kind": "registry",
     "parser": "tceq", "feed_set": "registries", "node_kind": "refinery", "outlet_class": "registry"},
    {"key": "feed.gdelt_industrial", "name": "GDELT DOC industrial incidents",
     "url_pattern": "https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&format=json&maxrecords=250&sort=DateDesc&startdatetime={from}000000&enddatetime={to}235959",
     "kind": "gdelt", "parser": "gdelt", "feed_set": "gdelt", "node_kind": None, "outlet_class": "national"},
    {"key": "feed.outage_windowed", "name": "dated outage and stoppage search (windowed)",
     "url_pattern": ("https://news.google.com/rss/search?q=" + urllib.parse.quote(OUTAGE_QUERY) + "+after:{from}+before:{to}"
                     "&hl=en-US&gl=US&ceid=US:en"),
     "kind": "wire", "parser": "rss", "feed_set": "gdelt", "node_kind": None, "outlet_class": "national"},
    {"key": "feed.regulatory_windowed", "name": "dated agency and docket search (windowed)",
     "url_pattern": ("https://news.google.com/rss/search?q=" + urllib.parse.quote(REGULATORY_QUERY) + "+after:{from}+before:{to}"
                     "&hl=en-US&gl=US&ceid=US:en"),
     "kind": "wire", "parser": "rss", "feed_set": "gdelt", "node_kind": "listed_company", "outlet_class": "national"},
    {"key": "feed.news_windowed", "name": "dated news search (windowed)",
     "url_pattern": ("https://news.google.com/rss/search?q=" + urllib.parse.quote(WINDOW_QUERY) + "+after:{from}+before:{to}"
                     "&hl=en-US&gl=US&ceid=US:en"),
     "kind": "wire", "parser": "rss", "feed_set": "gdelt", "node_kind": None, "outlet_class": "national"},
    {"key": "feed.globenewswire_earnings", "name": "GlobeNewswire earnings releases and results announcements",
     "url_pattern": "https://www.globenewswire.com/RssFeed/subjectcode/13-Earnings%20Releases%20And%20Operating%20Results/feedTitle/GlobeNewswire%20-%20Earnings%20Releases%20And%20Operating%20Results",
     "kind": "wire", "parser": "rss", "feed_set": "wires", "node_kind": "listed_company", "outlet_class": "wire"},
)
GDELT_QUERY = '(fire OR explosion OR leak OR "force majeure" OR closure OR strike OR insolvency OR outage) (plant OR refinery OR port OR terminal OR mine OR smelter OR factory OR pipeline) sourcelang:english'


def _get(url: str, timeout: int = 30) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "nomad-harness/0.1 (enumeration; contact bato2912@gmail.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def seed_feeds(conn: sqlite3.Connection) -> int:
    n = 0
    for f in FEED_SEED:
        if conn.execute("SELECT 1 FROM feeds WHERE key = ?", (f["key"],)).fetchone():
            continue
        insert_mutable(conn, "feeds", {**f, "active": 1, "confirmed": 0})
        n += 1
    return n


def feed_add(conn: sqlite3.Connection, key: str, name: str, url_pattern: str, kind: str, parser: str, feed_set: str,
             node_kind: str | None = None, outlet_class: str | None = None, confirmed: bool = False,
             stratum: str | None = None) -> dict:
    from . import config
    if kind not in FEED_KINDS or parser not in PARSERS:
        raise ValidationError(f"kind in {FEED_KINDS}, parser in {PARSERS}")
    if stratum and stratum not in config.STRATA:
        raise ValidationError(f"stratum must be one of {config.STRATA}")
    if outlet_class and outlet_class not in OUTLET_CLASSES:
        raise ValidationError(f"outlet_class in {OUTLET_CLASSES}")
    ex = conn.execute("SELECT id FROM feeds WHERE key = ?", (key,)).fetchone()
    if ex:
        conn.execute("UPDATE feeds SET name = ?, url_pattern = ?, kind = ?, parser = ?, feed_set = ?, node_kind = ?, outlet_class = ?, confirmed = ?, stratum = COALESCE(?, stratum), active = 1 WHERE id = ?",
                     (name, url_pattern, kind, parser, feed_set, node_kind, outlet_class, int(confirmed), stratum, ex["id"]))
        return {"feed_id": ex["id"], "key": key, "created": False}
    row = insert_mutable(conn, "feeds", {"key": key, "name": name, "url_pattern": url_pattern, "kind": kind, "parser": parser, "feed_set": feed_set,
                                         "node_kind": node_kind, "outlet_class": outlet_class, "active": 1, "confirmed": int(confirmed),
                                         "stratum": stratum})
    return {"feed_id": row["id"], "key": key, "created": True}


def list_feeds(conn: sqlite3.Connection, feed_set: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM feeds WHERE active = 1", []
    if feed_set and feed_set != "all":
        sql += " AND feed_set = ?"
        args.append(feed_set)
    return [dict(r) for r in conn.execute(sql + " ORDER BY feed_set, rowid", args)]


# ---- pulling ---------------------------------------------------------------------------------------------------------

def _parse_gdelt(data: bytes) -> list[dict]:
    d = json.loads(data.decode("utf-8", "replace") or "{}")
    out = []
    for a in d.get("articles", []):
        seen = a.get("seendate") or ""
        pub = f"{seen[:4]}-{seen[4:6]}-{seen[6:8]}" if len(seen) >= 8 else None
        out.append({"title": a.get("title") or "", "link": a.get("url"), "published": pub, "summary": (a.get("domain") or ""), "outlet": a.get("domain")})
    return out


def pull_feed(feed: dict, from_: str, to: str, fetch=_get) -> tuple[list[dict], str | None]:
    """Items for one feed. RSS feeds are rolling (recent items only); GDELT and TCEQ take the window."""
    from .facts import parse_feed
    from .history import read_tceq
    try:
        if feed["parser"] == "rss":
            url = feed["url_pattern"]
            if "{from}" in url:      # a windowed search feed: dates go in the query, so the window is real
                url = url.format(**{"from": from_, "to": (date.fromisoformat(to) + timedelta(days=1)).isoformat()})
            items = parse_feed(fetch(url))
        elif feed["parser"] == "gdelt":
            url = feed["url_pattern"].format(query=urllib.parse.quote(GDELT_QUERY), **{"from": from_.replace("-", ""), "to": to.replace("-", "")})
            items = _parse_gdelt(fetch(url))
        elif feed["parser"] == "tceq":
            r = read_tceq("", fetch, to)
            items = [{"title": i["text"], "link": i["url"], "published": i["date"], "summary": ""} for i in r["incidents"]]
        else:
            items = []
        return items, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"[:160]


def pull_window_daily(feed: dict, from_: str, to: str, fetch=_get) -> tuple[list[dict], str | None]:
    """A windowed search feed one day at a time, so the per-request result cap does not truncate the window to its last
    few days. Errors are collected, not raised: a day that fails leaves a gap in the enumeration, and the gap is said."""
    out, errs = [], []
    d, end = date.fromisoformat(from_), date.fromisoformat(to)
    while d <= end:
        items, err = pull_feed(feed, d.isoformat(), d.isoformat(), fetch)
        out += items
        if err:
            errs.append(f"{d.isoformat()}: {err}")
        d += timedelta(days=1)
    return out, ("; ".join(errs)[:160] if errs else None)


# ---- drafting and computing -----------------------------------------------------------------------------------------------

def bare_prompt(title: str, event_date: str) -> str:
    t = re.split(r"\s+[|–—-]\s+(?=[A-Z][\w& .]{2,30}$)", title.strip())[0]
    t = STRIP_WORDS.sub("", t).strip(" :-–")
    t = re.sub(r"\s+", " ", t)
    if t and not t.endswith("."):
        t += "."
    d = date.fromisoformat(event_date)
    return f"{d.strftime('%B')} {d.day}, {d.year}: {t}"


def key_tokens(title: str) -> set[str]:
    stop = {"the", "a", "an", "and", "of", "in", "at", "on", "to", "for", "after", "as", "by", "with", "from", "its", "is", "are", "was",
            "were", "has", "have", "over", "into", "near", "amid", "says", "said", "new", "us", "uk"}
    return {w for w in re.findall(r"[a-z][a-z\-]{2,}", title.lower()) if w not in stop}


def default_impact_pct(node_kind: str | None) -> float:
    """v14 C1: the seed impact for a single-site event by node kind, before anything is known about scale.
    Pre-registered here so a selection number is never tuned per candidate; the operator restates it per leg at lock."""
    return {"refinery": 1.5, "chemical": 1.0, "petrochemical": 1.0, "mining": 2.0, "metals": 1.5, "power": 1.0,
            "port": 0.8, "shipping": 0.8, "grid": 0.8, "listed_company": 3.0}.get(node_kind or "", 1.0)


def materiality_hint(conn: sqlite3.Connection, title: str, node_kind: str | None, event_date: str | None = None,
                     fetch=None) -> dict:
    """v12 G: selection has been optimising for cleanliness, which reliably produces events too small to transmit, which
    is why occurrence has never had a fair test. Estimate the event's size against the largest listed holder the store
    can match, from whatever the store already holds. Reported, never a gate.

    v14 C1: and it is a number now. Impact on the matched listed holder over that holder's pre-event empirical band,
    from pre-event closes only. No leg in thirteen rounds has cleared magnitude 1.0, which is most of an answer about
    the event population, and it belongs at selection rather than being discovered at scoring."""
    toks = key_tokens(title)
    best = None
    for r in conn.execute("SELECT h.id, h.canonical_name, h.listed, h.ticker FROM holders h WHERE h.listed = 1"):
        name_toks = key_tokens(r["canonical_name"])
        if name_toks & toks:
            best = {"holder": r["canonical_name"], "ticker": r["ticker"], "holder_id": r["id"]}
            break
    if not best:
        return {"materiality_hint": None,
                "materiality_basis": "no listed holder in the names book matches the headline: the event's transmission has to run "
                                     "through a leg the store does not hold yet"}
    band, band_basis = None, "no pre-event band could be computed for the matched holder"
    if event_date and best.get("holder_id"):
        from .surviving import _preevent_band
        got = _preevent_band(conn, best["holder_id"], event_date, fetch)
        if got:
            band, band_basis = got
    impact = default_impact_pct(node_kind)
    hint = (round(impact / band, 4) if (band and impact) else None)
    from . import config as _cfg
    return {"materiality_hint": hint,
            "materiality_basis": (f"headline names {best['holder']} ({best['ticker']}); a single-site event of kind "
                                  f"{node_kind or 'unknown'} is taken as {impact}% of the holder, against {band_basis}"
                                  + (f"; magnitude {hint} against a stake appetite of {_cfg.APPETITE['stake']}"
                                     if hint is not None else "; magnitude not computable at selection"))}


def node_kind_guess(title: str, feed_kind: str | None) -> str | None:
    for kind, rx in KIND_WORDS:
        if rx.search(title):
            return kind
    return feed_kind


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = " ".join(sorted(key_tokens(it["title"]))[:8])
        if not it.get("link") or not it.get("published") or k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def enumerate_window(conn: sqlite3.Connection, feed_set: str, from_: str, to: str, fetch=_get, operator_model: str | None = None,
                     today: date | None = None, registries: bool = False) -> dict:
    """C2: dated, deduplicated candidates over [from, to] with bare prompts and computed Q1b/Q2/Q7, size hint, Q1a basis."""
    from .carriers import open_for_kind
    from .history import q1b as compute_q1b
    from .rounds import event_window
    date.fromisoformat(from_), date.fromisoformat(to)
    if from_ > to:
        raise ValidationError("from must be on or before to")
    feeds = list_feeds(conn, feed_set)
    if not feeds:
        raise ValidationError(f"no active feeds in set {feed_set!r}; see nomad_feeds")
    lookback = (date.fromisoformat(from_) - timedelta(days=30)).isoformat()
    win = event_window(conn, operator_model, today)
    all_items, report = [], []
    for f in feeds:
        items, err = pull_feed(f, lookback, to, fetch)
        if "{from}" in (f.get("url_pattern") or ""):
            # a windowed search feed caps how many results it returns, so a single pull over lookback+window lets thirty
            # days of prior items crowd the window itself out, and a week-wide pull is truncated to its last few days.
            # Walk the window a day at a time; dedupe handles the overlap.
            w_items, w_err = pull_window_daily(f, from_, to, fetch)
            items, err = w_items + items, err or w_err
        conn.execute("UPDATE feeds SET last_pulled = ?, last_status = ? WHERE id = ?", (now_iso(), err or f"ok:{len(items)}", f["id"]))
        for it in items:
            it["feed"] = f
        all_items += items
        report.append({"feed": f["key"], "items": len(items), "error": err})
    # v13 B5: what each feed could actually reach, measured at the moment it was pulled. A five-day reach went
    # unreported for four rounds and starved the clean-round count; a feed set that cannot span the window says so here.
    reach = measure_reach(conn, report, all_items, from_, to)
    # v13 B6: the windowed endpoint is not deterministic (65 items, then 39, on the same day), so the Q1a denominator
    # is the stored candidate list rather than whatever a second pull happens to return.
    prior = [it for it in all_items if it.get("published") and lookback <= it["published"] < from_]
    prior += stored_prior(conn, feed_set, lookback, from_)
    window = [it for it in all_items if it.get("published") and from_ <= it["published"] <= to and INCIDENT_WORDS.search(it["title"])]
    window = _dedupe(sorted(window, key=lambda x: x["published"]))
    existing = {r["url"] for r in conn.execute("SELECT url FROM enumeration_candidates WHERE feed_set = ? AND window_from = ? AND window_to = ?",
                                               (feed_set, from_, to))}
    written, cands = 0, []
    for it in window:
        f = it["feed"]
        toks = key_tokens(it["title"])
        kind = node_kind_guess(it["title"], f.get("node_kind"))
        node_guess = " ".join(sorted(toks)[:4])
        prev = [p for p in prior if len(key_tokens(p["title"]) & toks) >= 2]
        q1a = (f"fail: {len(prev)} prior item(s) on these tokens in the 30 days before {from_}: " + "; ".join(p["title"][:60] for p in prev[:3])
               if prev else f"pass: no item on these tokens across {len(feeds)} feed(s) in the 30 days before {from_}")
        try:
            q1b = compute_q1b(conn, it["title"], it["published"], kind, registries=registries)["text"]
        except Exception as e:
            q1b = f"unknown: {type(e).__name__}"
        evd = date.fromisoformat(it["published"])
        q2 = ("unknown: no cutoff" if not win["cutoff"] else ("fail: on or before cutoff" if evd <= date.fromisoformat(win["cutoff"]) else "pass: after cutoff"))
        q7 = "unknown: no node kind guessed"
        if kind:
            try:
                d = open_for_kind(conn, kind)
                q7 = f"{'pass' if d['qualifies'] else 'fail'}: {len(d['open_carriers'])} open carrier(s) for {kind}"
            except ValidationError:
                pass
        c = {"feed_set": feed_set, "window_from": from_, "window_to": to, "feed_key": f["key"], "event_date": it["published"], "title": it["title"][:300],
             "url": it["link"], "prompt": bare_prompt(it["title"], it["published"]), "node_guess": node_guess, "node_kind_guess": kind,
             "q1a_basis": q1a, "q1b": q1b, "q2": q2, "q7": q7, "size_hint": SIZE_HINT.get(f.get("outlet_class") or "", "underread"),
             **materiality_hint(conn, it["title"], kind, it["published"], (fetch if fetch is not _get else None))}
        if it["link"] not in existing:
            row = append(conn, "enumeration_candidates", c)
            c["candidate_id"] = row["id"]
            written += 1
        cands.append(c)
    return {"feed_set": feed_set, "window": [from_, to], "feeds": report, "items_pulled": len(all_items), "candidates": cands,
            "written": written, "prior_items_for_q1a": len(prior), "reach": reach,
            "warning": reach["warning"]}


class ShortReach(ValidationError):
    """v14 C8: raised where the feed set cannot span the window that was asked for."""


def measure_reach(conn: sqlite3.Connection, report: list[dict], items: list[dict], from_: str, to: str,
                  strict: bool = True) -> dict:
    """B5: per feed, how many days back its oldest item reaches, written to `feeds.reach_days` and reported."""
    today = date.today()
    per_feed: dict[str, list[str]] = {}
    for it in items:
        if it.get("published") and it.get("feed"):
            per_feed.setdefault(it["feed"]["key"], []).append(it["published"])
    rows = []
    for r in report:
        pubs = sorted(per_feed.get(r["feed"], []))
        days = (today - date.fromisoformat(pubs[0])).days if pubs else None
        conn.execute("UPDATE feeds SET reach_days = ?, reach_measured_at = ? WHERE key = ?",
                     (days, now_iso(), r["feed"]))
        rows.append({"feed": r["feed"], "items": r["items"], "oldest": (pubs[0] if pubs else None), "reach_days": days,
                     "error": r["error"]})
    needed = (today - date.fromisoformat(from_)).days
    spans = [x for x in rows if x["reach_days"] is not None and x["reach_days"] >= needed]
    warning = None
    if not spans:
        best = max([x["reach_days"] for x in rows if x["reach_days"] is not None], default=None)
        warning = (f"no feed in this set reaches {from_}: the window needs {needed} days of reach and the deepest feed "
                   f"managed {best if best is not None else 'nothing'}. Any candidate list for this window is short by "
                   "construction, and Q1a computed against it is not a denominator")
        # v14 C8: fail loudly. A five-day reach went unreported for four rounds and starved the clean-round count; a
        # warning nobody reads is the same as no warning, so this raises at the point of use.
        if strict:
            raise ShortReach(warning)
    return {"needed_days": needed, "feeds": rows, "spanning": [x["feed"] for x in spans], "warning": warning}


def stored_prior(conn: sqlite3.Connection, feed_set: str, lookback: str, from_: str) -> list[dict]:
    """B6: candidates already on the ledger inside the lookback, as the stable half of the Q1a denominator."""
    return [{"title": r["title"], "published": r["event_date"], "link": r["url"], "summary": "", "stored": True}
            for r in conn.execute("SELECT title, event_date, url FROM enumeration_candidates "
                                  "WHERE feed_set = ? AND event_date >= ? AND event_date < ? ORDER BY rowid",
                                  (feed_set, lookback, from_))]


def _latest_candidates(conn: sqlite3.Connection, feed_set: str, from_: str, to: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM enumeration_candidates WHERE feed_set = ? AND window_from = ? AND window_to = ? ORDER BY rowid",
                                          (feed_set, from_, to))]
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return sorted([r for r in rows if r["id"] not in superseded], key=lambda r: (r["event_date"], r["recorded_at"]))


def stratum_of(conn: sqlite3.Connection, feed_key: str) -> str:
    r = conn.execute("SELECT stratum FROM feeds WHERE key = ?", (feed_key,)).fetchone()
    return (r["stratum"] if r and r["stratum"] else "other")


def stratum_counts(conn: sqlite3.Connection, window: int | None = None) -> dict:
    """v11 D: admitted rounds by stratum over the rolling window, with the shortfall against the quota."""
    from . import config
    window = window or config.STRATUM_WINDOW_ROUNDS
    rows = [dict(r) for r in conn.execute(
        "SELECT e.candidate_id, e.node_kind, e.source FROM rounds r JOIN events e ON e.id = r.event_id "
        "JOIN round_state s ON s.round_id = r.id WHERE s.state != 'void' ORDER BY r.rowid DESC LIMIT ?", (window,))]
    counts = {k: 0 for k in config.STRATA}
    for r in rows:
        st = "other"
        if r["candidate_id"]:
            c = conn.execute("SELECT feed_key FROM enumeration_candidates WHERE id = ?", (r["candidate_id"],)).fetchone()
            if c:
                st = stratum_of(conn, c["feed_key"])
        counts[st] = counts.get(st, 0) + 1
    short = {k: max(0, v - counts.get(k, 0)) for k, v in config.STRATUM_QUOTA.items()}
    return {"window_rounds": window, "counts": counts, "quota": config.STRATUM_QUOTA, "shortfall": short,
            "order": sorted(config.STRATA, key=lambda k: (-short.get(k, 0), counts.get(k, 0), k))}


def select_next(conn: sqlite3.Connection, feed_set: str, from_: str, to: str, stratified: bool = True) -> dict:
    """C3/D: the next undecided candidate. Draws in stratum order (largest shortfall against the quota first), then by
    date inside the stratum, so extra volume does not inherit one feed's bias."""
    cands = _latest_candidates(conn, feed_set, from_, to)
    pending = [c for c in cands if not c["decision"]]
    if not pending:
        return {"candidate": None, "remaining": 0, "decided": len(cands), "note": "no undecided candidate in this window; enumerate or widen"}
    sc = stratum_counts(conn)
    for c in pending:
        c["stratum"] = stratum_of(conn, c["feed_key"])
    if stratified:
        rank = {s: i for i, s in enumerate(sc["order"])}
        pending.sort(key=lambda c: (rank.get(c["stratum"], len(rank)), c["event_date"], c["recorded_at"]))
    c = pending[0]
    return {"candidate": c, "remaining": len(pending), "decided": len(cands) - len(pending),
            "strata": sc, "stratified": stratified,
            "pending_by_stratum": {s: sum(1 for x in pending if x["stratum"] == s) for s in sorted({x["stratum"] for x in pending})},
            "next_step": "nomad_decide(candidate_id, 'accept', size_band=..., criteria={Q3,Q4,Q6,Q8}) or nomad_decide(candidate_id, 'reject', reason='Qn: why')"}


def decide(conn: sqlite3.Connection, candidate_id: str, decision: str, reason: str | None = None, size_band: str | None = None,
           criteria: dict | None = None, node: str | None = None, node_kind: str | None = None, event_kind: str | None = None,
           prompt: str | None = None, operator_model: str | None = None, today: date | None = None, cap_override: str | None = None,
           q1b_override: dict | None = None) -> dict:
    """accept -> submits the round through the enumeration path (Q9 pass); reject -> event_rejections row."""
    from .rounds import FAILING_QS, reject_event, selection_window_open, submit_event
    r = conn.execute("SELECT * FROM enumeration_candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not r:
        raise NotFound(f"no candidate {candidate_id!r}")
    c = dict(r)
    latest = _latest_candidates(conn, c["feed_set"], c["window_from"], c["window_to"])
    cur = next((x for x in latest if x["id"] == candidate_id or x.get("supersedes") == candidate_id), c)
    if cur["decision"] and not (decision == "skip" and cur["decision"] != "accept"):
        raise ValidationError(f"candidate already decided: {cur['decision']} ({cur['decision_reason']})")
    if decision == "skip":
        # v11 §0.4: a plain selection note, no manufactured failing question (the human had already fixed the pick).
        # A skip may supersede an earlier reject: that is the ratification path for a manufactured failing question.
        if not (reason or "").strip():
            raise ValidationError("a skip needs a reason: say why this candidate was passed over without assessing it")
        row = append(conn, "enumeration_candidates", {**{k: c[k] for k in ("feed_set", "window_from", "window_to", "feed_key", "event_date", "title", "url", "prompt",
                                                                            "node_guess", "node_kind_guess", "q1a_basis", "q1b", "q2", "q7", "size_hint")},
                                                      "decision": "skip", "decision_reason": reason.strip(), "supersedes": c["id"]})
        return {"candidate_id": row["id"], "decision": "skip", "reason": reason.strip()}
    if decision == "reject":
        reason = (reason or "").strip()
        fq = next((q for q in FAILING_QS if reason.lower().startswith(q.lower())), None)
        if not fq:
            raise ValidationError(f"reject reason must start with the failing question ({', '.join(FAILING_QS)}): 'Q5: trivia'")
        rej = reject_event(conn, c["feed_set"], c["event_date"], c["prompt"], fq, reason, start_date=c["window_from"])
        row = append(conn, "enumeration_candidates", {**{k: c[k] for k in ("feed_set", "window_from", "window_to", "feed_key", "event_date", "title", "url", "prompt",
                                                                            "node_guess", "node_kind_guess", "q1a_basis", "q1b", "q2", "q7", "size_hint")},
                                                      "decision": "reject", "decision_reason": reason, "supersedes": c["id"]})
        return {"candidate_id": row["id"], "decision": "reject", "rejection_id": rej["rejection_id"], "failing_q": fq}
    if decision != "accept":
        raise ValidationError("decision must be accept, reject or skip")
    if not size_band:
        raise ValidationError("accept needs size_band (underread | headline | trivia)")
    crit = {"Q1a": c["q1a_basis"], **{k: v for k, v in (criteria or {}).items()}}
    for q in ("Q3", "Q4", "Q6", "Q8"):
        if q not in crit:
            raise ValidationError(f"accept confirms Q3, Q4, Q6 and Q8 explicitly ('pass: <why>'); {q} missing")
    if not conn.execute("SELECT 1 FROM selection_windows WHERE source = ? AND start_date = ?", (c["feed_set"], c["window_from"])).fetchone():
        selection_window_open(conn, c["feed_set"], c["window_from"], f"enumeration window to {c['window_to']}")
    seen = len(latest)
    sub = submit_event(conn, prompt or c["prompt"], c["event_date"], c["feed_set"], f"enumeration: first accepted candidate in {c['feed_set']} from {c['window_from']}",
                       0, crit, node=node or c["node_guess"], event_kind=event_kind, node_kind=node_kind or c["node_kind_guess"],
                       selection_start_date=c["window_from"], window_events_seen=seen, operator_model=operator_model, today=today,
                       via_enumeration=True, size_band=size_band, candidate_id=c["id"], cap_override=cap_override, q1b_override=q1b_override)
    append(conn, "enumeration_candidates", {**{k: c[k] for k in ("feed_set", "window_from", "window_to", "feed_key", "event_date", "title", "url", "prompt",
                                                                  "node_guess", "node_kind_guess", "q1a_basis", "q1b", "q2", "q7", "size_hint")},
                                            "decision": "accept", "decision_reason": reason, "round_id": sub["round_id"], "supersedes": c["id"]})
    return {"candidate_id": c["id"], "decision": "accept", "round": sub}
