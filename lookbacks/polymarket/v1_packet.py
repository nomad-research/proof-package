"""V1 packet builder (V1_prereg.md §3, A2, A5 to A8, A12, A13).

What a blind session may see, built by a script and hashed: rules text and contract questions **as of the lock**; never a price, volume, liquidity, order book, token or
condition id, resolution status, closing time or outcome. Contracts are shown only if they could be traded at the lock (an eligible price within 48 hours, and the market
not already closed); that reveals that a recent trade exists and nothing about its level (disclosed, A13). Sessions refer to contracts by opaque labels; the label map
stays in a private file the session never sees.

    python lookbacks/polymarket/v1_packet.py --build-index <universe.jsonl.gz>     # once; writes v1_live_index.json.gz (frozen by hash)
    python lookbacks/polymarket/v1_packet.py --stage1a <event_id>                   # writes packets/R<id>/stage1a.txt (+ private map)
    python lookbacks/polymarket/v1_packet.py --stage1b <event_id> <terms_json>      # retrieval from the stage-1a hedge terms; writes stage1b.txt
"""
import argparse, collections, datetime as dt, functools, gzip, hashlib, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE))); sys.path.insert(0, HERE)
import v1_pool as P
from nomad16 import pmgraph as G

SEED = 20260930
CLS = {"partition_exact", "partition_open", "ladder", "date_ladder"}
MAX_AGE_S = 48 * 3600
CAP_CANDIDATES, MAX_CONTRACTS_PER_EVENT, MIN_MENU_TEMPLATES = 60, 12, 10
RULES_CHARS = 1400
TIERS = ("mild", "moderate", "severe")
# past-tense resolution language and dated updates in rules text: a possible leak of the outcome. Forward-looking 'will resolve to' is normal and not flagged.
LEAK = re.compile(r"(\bresolved (to|as|yes|no)\b|\bhas (now |already )?resolved\b|\bwas resolved\b|\bhas been resolved\b|\bfinal(ly)? (result|outcome)\b|\bupdate[d]?\s*[:\-]|\bthe outcome (was|is)\b|\bnow resolved\b)", re.I)


def parse(t):
    t = t.replace("Z", "+00:00").replace(" ", "T")
    if re.search(r"[+-]\d\d$", t):
        t += ":00"
    return dt.datetime.fromisoformat(t)


def ts(t):
    return int(parse(t).timestamp())


def lock_of(e):
    """The lock: the midpoint between the event's start and its actual closing time (V1_prereg.md A9)."""
    return (ts(e["start"]) + ts(e["closed_time"])) // 2


def as_of(lock):
    return dt.datetime.fromtimestamp(lock, dt.timezone.utc).strftime("%Y-%m-%d")


def leak_flags(text):
    return sorted({m.group(0).lower() for m in LEAK.finditer(text or "")})


def price_fn_live(token, lock):
    """True if the token has a price point within 48 hours before the lock (60-minute fidelity, then 12-hour). Network."""
    for fid in (60, 720):
        h = P.page(f"https://clob.polymarket.com/prices-history?market={token}&startTs={lock - MAX_AGE_S}&endTs={lock}&fidelity={fid}")
        if any(x["t"] <= lock and lock - x["t"] <= MAX_AGE_S for x in (h or {}).get("history", [])):
            return True
    return False


def open_at(m, lock):
    """The market is not already closed at the lock. Unknown close time (an event still open) counts as open."""
    c = m.get("mclosed")
    return c is None or ts(c) > lock


def order_key(m):
    try:
        return (int(m.get("gthr")), m.get("q") or "")
    except (TypeError, ValueError):
        return (10 ** 6, m.get("q") or "")


def eligible(markets, lock, price_fn, limit=None):
    out = []
    for m in sorted(markets, key=order_key):
        if not m.get("tokens") or not open_at(m, lock):
            continue
        if price_fn(m["tokens"][0], lock):
            out.append(m)
            if limit and len(out) >= limit:
                break
    return out


def kind_label(cls, ladder_kind=None):
    """The structure as a session reads it, from the question wording: partition exact | partition open | price ladder | touch ladder | date ladder."""
    if cls == "ladder":
        return "touch ladder" if ladder_kind == "touch" else "price ladder"
    return cls.replace("_", " ")


_NORM = re.compile(r"\$\s?[\d,\.]+\s?(k|m|b|million|billion)?|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(,?\s*20\d\d)?|\b\d[\d,\.]*\b", re.I)


def norm(t):
    """Rules text with its dates and numbers blanked, so rungs that differ only by a date or a strike compare equal."""
    return re.sub(r"\s+", " ", _NORM.sub("#", t or "")).strip().lower()


def rules_of(m, event_desc):
    """A contract's own rules, only if they differ from the shared rules beyond dates and numbers (else the shared text stands for all of them)."""
    d = (m.get("description") or m.get("desc") or "").strip()
    return "" if not d or norm(d) == norm(event_desc) else d[:RULES_CHARS]


def shared_rules(e, keep):
    """The rules shown once: the first eligible contract's own text if it has one (so its dates are live ones), else the event's."""
    for m in keep:
        d = (m.get("description") or "").strip()
        if d:
            return d
    return (e.get("description") or "").strip()


# ---------------------------------------------------------------- stage 1a
def stage1a(e, lock, price_fn, mkt_info):
    """Primary event packet. ``mkt_info`` maps condition id to {'closed': ...} (the supplement). Returns (packet, private, flags)."""
    ms = [dict(m, mclosed=(mkt_info.get(m["cid"]) or {}).get("closed")) for m in e["markets"]]
    keep = eligible(ms, lock, price_fn)
    desc = shared_rules(e, keep)
    contracts, private = [], {}
    for i, m in enumerate(keep, 1):
        lab = f"C{i}"
        contracts.append({"label": lab, "question": m.get("q"), "group_item": m.get("git"), "extra_rules": rules_of(m, desc) or None})
        private[lab] = {"cid": m["cid"], "token_yes": m["tokens"][0], "token_no": m["tokens"][1] if len(m["tokens"]) > 1 else None, "q": m.get("q")}
    flags = leak_flags(desc) + [f for m in keep for f in leak_flags(rules_of(m, desc))]
    packet = {"round_id": f"R{e['id']}", "as_of": as_of(lock), "event": {"title": e["title"], "kind": kind_label(e["class"], e.get("ladder_kind")), "rules": desc[:6000], "contracts": contracts}}
    return packet, private, sorted(set(flags))


PROMPT_1A = """You are one of several independent analysts. Work only from what is written below. Do not use any tool, do not look anything up, and do not use anything you
know that happened after {as_of}: reason as of that date. You are shown no market prices, and you are not asked for any probability.

EVENT: {title}   (structure: {kind})
RULES (as of {as_of}):
{rules}

CONTRACTS (each pays $1 if its statement is true when the event resolves, $0 otherwise; you may name YES or NO on any contract):
{contracts}

Task. Write your own view as documents-and-mechanism reasoning, not as odds.
1. primary: a thesis about how this event resolves and a basket of at most 4 contracts from the list that expresses it (long only: a contract with YES or NO).
2. failure_narrative: the specific way the thesis is wrong (what would have to happen for the basket to lose).
3. hedge_thesis: a second narrative, about a DIFFERENT part of the world, that would tend to be true in exactly the worlds where the primary fails. Say why, in mechanism terms.
4. search_terms: 3 to 8 words or names (entities, assets, places, institutions) that instruments for the hedge thesis would carry. Lower-case single words or short names.

Answer with one JSON object and nothing else:
{{"primary": {{"thesis": "...", "basket": [{{"contract": "C1", "side": "YES", "reason": "..."}}]}}, "failure_narrative": "...", "hedge_thesis": "...", "search_terms": ["..."]}}
"""


def prompt_1a(packet):
    ev = packet["event"]
    cs = "\n".join(f"  {c['label']}: {c['question']}" + (f"  [{c['group_item']}]" if c["group_item"] else "") + (f"\n      extra rules: {c['extra_rules']}" if c["extra_rules"] else "") for c in ev["contracts"])
    return PROMPT_1A.format(as_of=packet["as_of"], title=ev["title"], kind=ev["kind"], rules=ev["rules"], contracts=cs)


def validate_1a(obj, packet):
    labels = {c["label"] for c in packet["event"]["contracts"]}
    errs = []
    for k in ("primary", "failure_narrative", "hedge_thesis", "search_terms"):
        if k not in obj:
            errs.append(f"missing {k}")
    if errs:
        return errs
    b = (obj["primary"] or {}).get("basket") or []
    if not 1 <= len(b) <= 4:
        errs.append("primary.basket must hold 1 to 4 contracts")
    for x in b:
        if x.get("contract") not in labels or x.get("side") not in ("YES", "NO"):
            errs.append(f"bad basket entry {x}")
    terms = obj["search_terms"]
    if not isinstance(terms, list) or not 3 <= len(terms) <= 8 or not all(isinstance(t, str) and t.strip() for t in terms):
        errs.append("search_terms must be 3 to 8 non-empty strings")
    txt = json.dumps(obj)
    if re.search(r"\b\d{1,3}\s?%|\bprobabilit|\bodds\b|\bpriced?\b|\$\s?\d", txt, re.I):
        errs.append("the answer contains a probability, a price or a percentage: not asked for, and it would anchor stage 2")
    return errs


# ---------------------------------------------------------------- stage 1b (retrieval)
def live_rows(index, lock):
    out = []
    for r in index:
        end = ts(r["closed_time"]) if r.get("closed_time") else 4102444800
        if ts(r["start"]) <= lock <= end:
            out.append(dict(r, end=None))       # liveness is applied here; Graph.search is called without ``at``
    return out


def stage1b(index, terms, lock, exclude_template, round_id, price_fn, exclude_id=None):
    """Retrieval for the hedge thesis: search the events open at the lock, exact structures only, one candidate per template, contracts that could be traded at the lock,
    at most 60, in a seeded shuffle (rank carries no information). Returns (packet, private, stats)."""
    rows = [r for r in live_rows(index, lock) if r["id"] != exclude_id]
    g = G.Graph(rows, generic_share=0.05)
    hits = [h for h in g.search(terms, cap=400, classes=CLS) if g.template[h["event_id"]] != exclude_template]
    cands, tried = [], 0
    for h in hits:
        if len(cands) >= CAP_CANDIDATES * 2:
            break
        r = g.events[h["event_id"]]; tried += 1
        keep = eligible(r["markets"], lock, price_fn, limit=MAX_CONTRACTS_PER_EVENT)
        if len(keep) >= 2:
            cands.append((h, r, keep))
    cands = cands[:CAP_CANDIDATES]
    random.Random(f"{SEED}:{round_id}").shuffle(cands)
    entries, private = [], {}
    for i, (h, r, keep) in enumerate(cands, 1):
        lab = f"E{i}"; desc = shared_rules(r, keep)[:RULES_CHARS]
        cs = []
        for j, m in enumerate(keep, 1):
            cl = f"{lab}.{j}"
            cs.append({"label": cl, "question": m.get("q"), "group_item": m.get("git")})
            private[cl] = {"cid": m["cid"], "token_yes": m["tokens"][0], "token_no": m["tokens"][1] if len(m["tokens"]) > 1 else None, "event_id": r["id"], "q": m.get("q")}
        entries.append({"label": lab, "title": r["title"], "kind": kind_label(r["class"], g.struct[r["id"]].get("kind")), "similar_events": h["n_in_template"], "rules": desc[:RULES_CHARS], "contracts": cs})
        private[lab] = {"event_id": r["id"], "class": r["class"]}
    stats = {"terms": terms, "templates_found": len(hits), "candidates_with_priced_contracts": len(cands), "checked": tried, "empty_menu": len(entries) < MIN_MENU_TEMPLATES}
    return {"round_id": round_id, "as_of": as_of(lock), "candidates": entries}, private, stats


PROMPT_1B = """Continue as the same analyst, under the same rules (no tools, nothing after {as_of}, no prices, no probabilities).

YOUR HEDGE THESIS: {hedge_thesis}
YOUR PRIMARY BASKET: {basket}
YOUR FAILURE NARRATIVE: {failure}

Below are the instruments open at {as_of} that match the words you gave. Each candidate is a group of contracts on one question; 'similar events' says how many near-identical
events were folded into it. The list is in random order and its order means nothing.

{cands}

Task. From the candidates only:
1. hedges: at most 4 contracts to hold alongside the primary (long only: a contract with YES or NO). For a candidate whose structure is a price ladder, touch ladder or date ladder, do not name a rung: name the
   event, a direction (above|below for a price ladder, reach|dip for a touch ladder, by_date for a date ladder; each candidate's structure is named) and a tier (mild, moderate or severe: how far from the ordinary the move must be).
   For any other structure name the contract.
2. claims: for each way your hedge thesis says the worlds are linked, one claim of the form "if this primary contract resolves NO (or YES), then this hedge condition holds", each with a reason
   in mechanism terms. A claim says which combinations cannot both happen; it is tested against what actually happened, so make only the claims you would stand behind.
3. If nothing in the list can express your hedge thesis, say so: return no hedges (that is an acceptable answer and is recorded as 'no instrument').

Answer with one JSON object and nothing else:
{{"hedges": [{{"contract": "E3.2", "side": "YES", "reason": "..."}}, {{"event": "E5", "direction": "below", "tier": "moderate", "reason": "..."}}],
  "claims": [{{"if": {{"contract": "C2", "resolves": "NO"}}, "then": {{"contract": "E3.2", "resolves": "YES"}}, "reason": "..."}}], "no_instrument": false}}
"""


def prompt_1b(packet_1a, answer_1a, packet_1b):
    basket = "; ".join(f"{x['contract']} {x['side']}" for x in answer_1a["primary"]["basket"])
    cands = "\n\n".join(f"{c['label']}  {c['title']}  (structure: {c['kind']}; similar events: {c['similar_events']})\n  rules: {c['rules']}\n" + "\n".join(f"    {k['label']}: {k['question']}" + (f"  [{k['group_item']}]" if k['group_item'] else "") for k in c["contracts"]) for c in packet_1b["candidates"])
    return PROMPT_1B.format(as_of=packet_1b["as_of"], hedge_thesis=answer_1a["hedge_thesis"], basket=basket, failure=answer_1a["failure_narrative"], cands=cands)


def validate_1b(obj, packet_1a, packet_1b):
    c_labels = {c["label"] for c in packet_1a["event"]["contracts"]}
    cand = {c["label"]: c for c in packet_1b["candidates"]}
    k_labels = {k["label"] for c in packet_1b["candidates"] for k in c["contracts"]}
    ladder_labels = {k["label"] for c in packet_1b["candidates"] if c["kind"].endswith("ladder") for k in c["contracts"]}       # a rung is chosen by tier at expression (A5, A6), never named
    errs = []
    if obj.get("no_instrument"):
        return errs if not obj.get("hedges") else ["no_instrument is true but hedges are listed"]
    hs = obj.get("hedges") or []
    if not 1 <= len(hs) <= 4:
        errs.append("hedges must hold 1 to 4 entries (or set no_instrument)")
    for h in hs:
        if "contract" in h:
            if h["contract"] not in k_labels or h.get("side") not in ("YES", "NO") or h["contract"] in ladder_labels:
                errs.append(f"bad hedge {h}" + (" (a ladder rung is not named: give the event, a direction and a tier)" if h["contract"] in ladder_labels else ""))
        elif "event" in h:
            kind = (cand.get(h["event"]) or {}).get("kind", "")
            ok_dir = {"price ladder": ("above", "below"), "touch ladder": ("reach", "dip"), "date ladder": ("by_date",)}.get(kind)
            if not ok_dir or h.get("direction") not in ok_dir or h.get("tier") not in TIERS:
                errs.append(f"bad ladder hedge {h}")
        else:
            errs.append(f"bad hedge {h}")
    for cl in obj.get("claims") or []:
        i, t = cl.get("if") or {}, cl.get("then") or {}
        if i.get("contract") not in c_labels or i.get("resolves") not in ("YES", "NO"):
            errs.append(f"bad claim antecedent {i}")
        if t.get("contract") in ladder_labels or not (t.get("contract") in k_labels or t.get("event") in cand) or (t.get("resolves") not in ("YES", "NO") and "tier" not in t):
            errs.append(f"bad claim consequent {t}")
    if re.search(r"\b\d{1,3}\s?%|\bprobabilit|\bodds\b|\bpriced?\b|\$\s?\d", json.dumps(obj), re.I):
        errs.append("the answer contains a probability, a price or a percentage")
    return errs


# ---------------------------------------------------------------- index
def build_index(universe_path, out_path):
    rows = []
    for eid, e in P.crawl_closed().items():
        if {t.get("slug") for t in (e.get("tags") or [])} & P.EXCL or not e.get("startDate") or not e.get("closedTime"):
            continue
        c = P.compact(e); cls = G.structure(c)["class"]
        if cls not in CLS or c["volume"] < 100_000:
            continue
        rows.append(_row(c, cls, {m.get("conditionId"): m.get("closedTime") for m in (e.get("markets") or [])}))
    for u in G.load_universe(universe_path):
        if u.get("header_only") or not u.get("start") or float(u.get("volume") or 0) < 100_000 or set(u.get("tags") or []) & P.EXCL:
            continue
        cls = G.structure(u)["class"]
        if cls not in CLS:
            continue
        full = P.page(f"{P.GAMMA}/{u['id']}")
        if not full:
            continue
        c = P.compact(full); c["closed_time"] = None
        rows.append(_row(c, cls, {}))
    rows.sort(key=lambda r: r["id"])
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    with gzip.open(out_path, "wb") as f:
        f.write(blob)
    print(len(rows), "events in the live index; sha256 of the uncompressed json:", hashlib.sha256(blob).hexdigest())


def _row(c, cls, mclosed):
    d = (c.get("description") or "").strip()
    ms = [{"cid": m["cid"], "tokens": m["tokens"], "q": m["q"], "git": m["git"], "gthr": m["gthr"], "nro": m["nro"], "mclosed": mclosed.get(m["cid"]),
           "description": None if (m.get("description") or "").strip() == d else (m.get("description") or "")[:RULES_CHARS]} for m in c["markets"]]
    return {"id": c["id"], "title": c["title"], "tags": c["tags"], "start": c["start"], "closed_time": c.get("closed_time"), "negRisk": c["negRisk"], "class": cls,
            "description": d[:6000], "markets": ms}


def load_index(path=os.path.join(HERE, "v1_live_index.json.gz")):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--build-index"); ap.add_argument("--stage1a"); ap.add_argument("--stage1b", nargs=2)
    a = ap.parse_args()
    if a.build_index:
        build_index(a.build_index, os.path.join(HERE, "v1_live_index.json.gz"))
    pool = {e["id"]: e for e in json.load(open(os.path.join(HERE, "v1_pool.json")))}
    mkt = json.load(open(os.path.join(HERE, "v1_pool_market_dates.json")))
    if a.stage1a:
        e = pool[a.stage1a]; lock = lock_of(e)
        pk, pv, flags = stage1a(e, lock, price_fn_live, mkt)
        d = os.path.join(HERE, "packets", f"R{e['id']}"); os.makedirs(d, exist_ok=True)
        open(f"{d}/stage1a.txt", "w").write(prompt_1a(pk)); json.dump(pk, open(f"{d}/stage1a.json", "w"), indent=1); json.dump(pv, open(f"{d}/private_1a.json", "w"), indent=1)
        json.dump({"packet_sha256": sha(pk), "lock": lock, "as_of": pk["as_of"], "contracts_shown": len(pk["event"]["contracts"]), "of": len(e["markets"]), "leak_flags": flags}, open(f"{d}/meta_1a.json", "w"), indent=1)
        print(f"R{e['id']}: {len(pk['event']['contracts'])}/{len(e['markets'])} contracts shown, leak flags {flags}, packet sha256 {sha(pk)[:16]}")
    if a.stage1b:
        eid, terms_file = a.stage1b; e = pool[eid]; lock = lock_of(e); d = os.path.join(HERE, "packets", f"R{eid}")
        ans = json.load(open(terms_file)); pk1 = json.load(open(f"{d}/stage1a.json"))
        pk, pv, st = stage1b(load_index(), [t.lower() for t in ans["search_terms"]], lock, G.template(e["title"]), f"R{eid}", price_fn_live, exclude_id=eid)
        open(f"{d}/stage1b.txt", "w").write(prompt_1b(pk1, ans, pk)); json.dump(pk, open(f"{d}/stage1b.json", "w"), indent=1); json.dump(pv, open(f"{d}/private_1b.json", "w"), indent=1)
        json.dump(dict(st, packet_sha256=sha(pk)), open(f"{d}/meta_1b.json", "w"), indent=1)
        print(f"R{eid}: {st}")
