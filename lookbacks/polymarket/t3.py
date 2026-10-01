"""T3: cluster sessions, forward, with live retrieval (v18 §6.4 and §5.3; session format: docs/DECISIONS_2026-10.md decisions 4 and 6).

    python lookbacks/polymarket/t3.py snapshot                 # network: open events now (Gamma), scoped; writes t3/open_<stamp>.json.gz and t3/snapshot.json
    python lookbacks/polymarket/t3.py clusters                 # V3's authored events still open, each with candidates from the open-set graph; writes t3/clusters.json
    python lookbacks/polymarket/t3.py sessions                 # one cluster per session; writes t3/sessions/C##.json (private labels) and C##.txt
    python lookbacks/polymarket/t3.py publish C01
    python lookbacks/polymarket/t3.py ingest C01 <agent_id>     # retrieval audit, validation, then the lock prices read at once (book asks), hashed
    python lookbacks/polymarket/t3.py freeze                   # answers and lock prices into t3/manifest.json, committed before any outcome exists
    python lookbacks/polymarket/t3.py score                    # forward: scores what has resolved (Gamma re-read), reports the rest pending

A session may search and fetch live public pages while it authors (D42). Prediction-market and odds sites are blocked: every search must pass the blocked list,
no fetch may reach a blocked domain, and an answer that speaks of a market's view is invalid (R6). Pages that quote odds are counted per session.
"""
import argparse, collections, datetime as dt, gzip, hashlib, json, math, os, random, re, shutil, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import numpy as np
import bt_audit as A
import bt_crawl as BC
import bt_t2 as T
import v1_packet as K
import v1_run as V
import v1_score as S
from nomad16 import pmgraph as G

D = os.path.join(HERE, "t3")
SEED = 20261003
HORIZON_MAX_D = 150                                   # V3 A2
CLUSTER_MAX_EVENTS, P_EDGE_MIN = 8, 4.0               # v18 §7 builder-set values, used as stand-ins until C4 is settled (see T3_prereg.md)
BLOCKED = ["polymarket.com", "kalshi.com", "predictit.org", "manifold.markets", "metaculus.com", "betfair.com", "smarkets.com", "oddschecker.com",
           "electionbettingodds.com", "polymarketanalytics.com", "gjopen.com", "goodjudgment.com", "insightprediction.com", "limitless.exchange",
           "myriad.markets", "betmgm.com", "draftkings.com", "fanduel.com", "williamhill.com", "paddypower.com", "bet365.com", "ladbrokes.com", "polymarket.co"]
ODDS = re.compile(r"\b(polymarket|kalshi|predictit|manifold markets|metaculus|betting odds|bookmakers?|the odds (are|of|on)|implied probabilit(y|ies)|priced in|"
                  r"the market (implies|thinks|expects|prices|gives)|markets? (give|put|price)s?\b|traders (give|put|see|price)|prediction markets?)\b", re.I)
ALLOWED_TOOLS = {"Read", "WebSearch", "WebFetch", "ToolSearch"}


def now_ts():
    return int(time.time())


# ---------------------------------------------------------------- the open set now
def cmd_snapshot(a):
    t0 = now_ts(); BC.VOLUME_MIN, BC.SCOPE = 10000.0, True
    out, log = {}, []
    a_ = dt.datetime.fromtimestamp(t0, dt.timezone.utc); b_ = a_ + dt.timedelta(days=HORIZON_MAX_D)
    BC.GAMMA_CLOSED = "false"
    t = a_
    while t < b_:
        u = min(t + dt.timedelta(days=3), b_)
        crawl_open(t, u, out, log); t = u
        print(BC.iso(u), "open events so far", len(out), file=sys.stderr, flush=True)
    os.makedirs(D, exist_ok=True)
    rows = sorted(out.values(), key=lambda e: e["id"]); blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    name = f"open_{a_.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.GzipFile(os.path.join(D, name), "wb", mtime=0) as fh:
        fh.write(blob)
    snap = {"taken_at": t0, "as_of": a_.strftime("%Y-%m-%d"), "file": name, "events": len(rows), "sha256_of_json": hashlib.sha256(blob).hexdigest(), "dropped": BC.DROPPED}
    A.jdump(snap, os.path.join(D, "snapshot.json")); print(json.dumps(snap))


def crawl_open(a, b, out, log):
    off = 0
    while True:
        p = BC.get(f"{BC.GAMMA}?closed=false&end_date_min={BC.iso(a)}&end_date_max={BC.iso(b)}&order=endDate&ascending=true&limit={BC.PAGE}&offset={off}&volume_min=10000")
        for e in p:
            if str(e["id"]) not in out and BC.in_scope(e):
                c = BC.compact(e)
                for m, raw in zip(c["markets"], e.get("markets") or []):
                    m["closed"] = bool(raw.get("closed"))
                out[str(e["id"])] = c
        if len(p) < BC.PAGE:
            log.append({"from": BC.iso(a), "to": BC.iso(b), "events": off + len(p)}); return
        off += BC.PAGE
        if off >= BC.CAP:
            mid = a + (b - a) / 2; crawl_open(a, mid, out, log); crawl_open(mid, b, out, log); return
        time.sleep(0.2)


# ---------------------------------------------------------------- clusters (graph proposes, the session decides)
def open_markets(e, t):
    return [m for m in e["markets"] if m.get("tokens") and not m.get("closed") and m.get("end") and A.ts(m["end"]) > t]


def v3_seeds():
    rounds = json.load(open(os.path.join(HERE, "v3", "v1_rounds.json"), encoding="utf-8"))["rounds"]
    return [str(r if isinstance(r, (str, int)) else (r.get("id") or r.get("event_id"))) for r in rounds]


def cmd_clusters(a):
    snap = A.jload(os.path.join(D, "snapshot.json")); evs = A.jload(os.path.join(D, snap["file"])); t0 = snap["taken_at"]
    byid = {e["id"]: e for e in evs}
    usable = {e["id"]: e for e in evs if open_markets(e, t0) and max(A.ts(m["end"]) for m in open_markets(e, t0)) <= t0 + HORIZON_MAX_D * 86400
              and not A.MAKER.search(A.text_of(e))}
    g = G.Graph([dict(e, markets=e["markets"]) for e in usable.values()])
    out, tally = [], collections.Counter()
    for sid in v3_seeds():
        if sid not in usable:
            tally["seed_not_open_or_out_of_horizon"] += 1; continue
        nb = sorted(((j, d) for j, d in g.edges_from(sid).items() if d["score"] >= P_EDGE_MIN and j in usable), key=lambda x: (-x[1]["score"], x[0]))
        cands = [{"id": j, "score": round(d["score"], 3), "tags": d["tags"], "entities": d["entities"]} for j, d in nb[:CLUSTER_MAX_EVENTS - 1]]
        out.append({"seed": sid, "seed_title": usable[sid]["title"], "candidates": cands})
        tally["clusters"] += 1; tally["with_no_candidate"] += int(not cands)
    A.jdump({"snapshot": snap["file"], "rule": {"CLUSTER_MAX_EVENTS": CLUSTER_MAX_EVENTS, "P_EDGE_MIN": P_EDGE_MIN, "horizon_max_days": HORIZON_MAX_D},
             "tally": dict(tally), "clusters": out}, os.path.join(D, "clusters.json"))
    print(json.dumps({"tally": dict(tally)}))
    for c in out:
        print(c["seed_title"][:60], "|", "; ".join(byid[x["id"]]["title"][:40] for x in c["candidates"]))


# ---------------------------------------------------------------- packets
CLAIMS = """CLAIMS. Where you believe one event's outcome changes the chances of another in this group, write a claim:
  {"if": {"contract": "E1.C2", "resolves": "YES"}, "then_event": "E3", "if_true": <what you would write for E3 if that happens>, "if_false": <what you would write for E3 if it does not>}
"if_true" and "if_false" use exactly the fields E3 asks for (the same "p", "levels", "high", "low" or "dates" object). Write as many claims as you believe in, including none."""

PROMPT = """You are reading a group of prediction-market questions that may affect each other. Your view is as of {as_of}.

You may search the web and fetch public pages to inform your view (load the WebSearch and WebFetch tools if needed). Rules for that:
- Every web search must pass blocked_domains = {blocked}.
- Never open a prediction-market, betting or odds site, and never use or mention what any market, bookmaker or trader thinks. Give your own view from the evidence.
- No other tools: only reading this file, searching and fetching.

First decide which questions belong together. For any you judge unrelated to the rest, put its label in "drop" with a one-line reason; write nothing else for it.

For every question you keep, write what it asks for. Whole percents run from 1 to 99. Levels are plain numbers in the units the contracts use. Dates are YYYY-MM-DD.

{claims}

{scale}

Also list the pages you relied on in "sources" (URLs).

Reply with one JSON object and nothing else:
{{"drop": {{"E5": "reason"}}, "events": [{{"label": "E1", ...the fields it asks for..., "scale": {{"class": "...", "percentile": 50}}}}], "claims": [...], "sources": ["https://..."]}}

{body}"""


SCALE = """SCALE. For every question you keep that measures a quantity, a count, a price, a size or a date, also write "scale": the kind of thing this is and where you expect this instance to land among instances of that kind.
  "scale": {"class": "<the reference class, e.g. monthly US core CPI prints since 2010>", "percentile": <0 to 100: where your middle view of this instance sits among instances of that class; 50 is an ordinary one>}
Write "scale": null for a question with no scale (a plain yes/no about whether something happens)."""

INSTRUCTION_T3 = "Your task is in the file {path}. Read that file (in parts if it is too long for one read), then do exactly what it instructs."   # T3 sessions may search; the backtests' wording forbids it


def event_record(e, t):
    ms = sorted(open_markets(e, t), key=K.order_key)
    cs = [{"cid": m["cid"], "token_yes": m["tokens"][0], "token_no": m["tokens"][1] if len(m["tokens"]) > 1 else None, "q": m.get("q"), "git": m.get("git"),
           "description": m.get("description"), "end": m.get("end"), "fee": m.get("feeSchedule"), "tick": m.get("tick")} for m in ms]
    k = T.kind_of(dict(e, markets=ms), len(ms)) if len(ms) != 2 else "percent"
    return {"id": e["id"], "title": e["title"], "description": e.get("description"), "tags": e["tags"], "kind": k or "percent", "contracts": cs}


def cmd_sessions(a):
    snap = A.jload(os.path.join(D, "snapshot.json")); evs = {e["id"]: e for e in A.jload(os.path.join(D, snap["file"]))}; t0 = snap["taken_at"]
    cl = A.jload(os.path.join(D, "clusters.json"))["clusters"]; os.makedirs(os.path.join(D, "sessions"), exist_ok=True)
    for n, c in enumerate(cl, 1):
        sid = f"C{n:02d}"; ids = [c["seed"]] + [x["id"] for x in c["candidates"]]
        order = list(ids); random.Random(f"{SEED}:{sid}").shuffle(order)       # the seed is not marked
        recs = [dict(event_record(evs[i], t0), as_of=snap["as_of"]) for i in order]
        labels = {f"E{i}": {"event_id": r["id"], "kind": r["kind"], "sides": T.sides(r) if r["kind"] == "touch" else None,
                            "contracts": {f"E{i}.C{j}": x["cid"] for j, x in enumerate(r["contracts"], 1)}} for i, r in enumerate(recs, 1)}
        body = "\n\n".join(T.block(i, r) for i, r in enumerate(recs, 1))
        text = PROMPT.format(as_of=snap["as_of"], blocked=json.dumps(BLOCKED), claims=CLAIMS, scale=SCALE, body=body)
        with open(os.path.join(D, "sessions", f"{sid}.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        A.jdump({"session": sid, "seed": c["seed"], "labels": labels, "events": recs, "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()},
                os.path.join(D, "sessions", f"{sid}.json"))
    print(json.dumps({"sessions": len(cl)}))


def cmd_publish(a):
    os.makedirs(A.PROMPT_DIR, exist_ok=True); dst = os.path.join(A.PROMPT_DIR, f"t3_{a.sid}.txt")
    shutil.copyfile(os.path.join(D, "sessions", f"{a.sid}.txt"), dst); print(INSTRUCTION_T3.format(path=dst))


# ---------------------------------------------------------------- the retrieval audit
def host(u):
    try:
        return (urllib.parse.urlparse(u).hostname or "").lower()
    except Exception:
        return ""


def blocked(u):
    h = host(u)
    return any(h == b or h.endswith("." + b) for b in BLOCKED)


def audit_retrieval(path, prompt_path, prompt):
    """Allowed: reading the prompt file, ToolSearch (to load the web tools), WebSearch with the blocked list, WebFetch of an unblocked page. Every assistant turn on the
    declared model. Returns the audit and the evidence record (every search and fetch with its returned text, hashed)."""
    tools, models, bad, evidence, odds_pages = collections.Counter(), collections.Counter(), [], [], 0
    calls, raw = {}, open(path, "rb").read()
    for line in raw.decode("utf-8").splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        if m.get("role") == "assistant" and m.get("model"):
            models[m["model"]] += 1
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                name, inp = b.get("name"), (b.get("input") or {})
                if name in V.IGNORED_TOOLS:
                    continue
                tools[name] += 1; calls[b["id"]] = (name, inp)
                if name not in ALLOWED_TOOLS:
                    bad.append(f"tool {name}")
                elif name == "Read" and inp.get("file_path") != prompt_path:
                    bad.append(f"read {inp.get('file_path')}")
                elif name == "WebFetch" and blocked(inp.get("url", "")):
                    bad.append(f"fetched blocked {host(inp.get('url', ''))}")
                elif name == "WebSearch" and not set(BLOCKED) <= set(inp.get("blocked_domains") or []):
                    bad.append("search without the blocked list")
                elif name == "ToolSearch" and not re.fullmatch(r"\s*(select:)?\s*(WebSearch|WebFetch)(\s*,\s*(WebSearch|WebFetch))*\s*", str(inp.get("query", ""))):
                    bad.append(f"tool search {inp.get('query')!r}")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                name, inp = calls[b["tool_use_id"]]
                if name in ("WebSearch", "WebFetch"):
                    t = b.get("content"); t = t if isinstance(t, str) else "".join(x.get("text", "") for x in t if isinstance(x, dict))
                    hit = bool(ODDS.search(t or "")); odds_pages += hit
                    evidence.append({"tool": name, "input": inp, "sha256": hashlib.sha256((t or "").encode("utf-8")).hexdigest(), "chars": len(t or ""), "quotes_odds": hit})
    ok = not bad and set(models) == {A.DECLARED_MODEL}
    return {"ok": ok, "violations": bad, "tool_calls": dict(tools), "models": dict(models), "pages_quoting_odds": odds_pages,
            "transcript_sha256": hashlib.sha256(raw).hexdigest()}, evidence


def validate(obj, labels):
    errs = []; drop = obj.get("drop") or {}
    if not isinstance(drop, dict):
        errs.append("drop is not an object"); drop = {}
    keep = {k: v for k, v in labels.items() if k not in drop}
    sub = {"events": [e for e in (obj.get("events") or []) if isinstance(e, dict) and e.get("label") in keep]}
    for e in sub["events"]:
        e.setdefault("recognised", False)
    views, er = T.validate(sub, keep); errs += er
    scale = {}
    for e in sub["events"]:
        s = e.get("scale")
        if s is None:
            scale[e["label"]] = None; continue
        try:
            pc = float(s["percentile"]); cl = str(s["class"]).strip()
            if not (0 <= pc <= 100) or not cl:
                raise ValueError
            scale[e["label"]] = {"class": cl, "percentile": pc}
        except (KeyError, TypeError, ValueError):
            errs.append(f"{e['label']}: scale must be null or {{class, percentile 0-100}}")
    claims = []
    for i, c in enumerate(obj.get("claims") or []):
        try:
            ifc, ev = c["if"]["contract"], c["then_event"]
            lab_if = ifc.split(".")[0]
            if lab_if not in keep or ifc not in keep[lab_if]["contracts"]:
                errs.append(f"claim {i}: unknown or dropped 'if' contract {ifc}"); continue
            if ev not in keep or ev == lab_if:
                errs.append(f"claim {i}: 'then' event {ev} unknown, dropped or the same event"); continue
            if c["if"].get("resolves") not in ("YES", "NO"):
                errs.append(f"claim {i}: 'resolves' must be YES or NO"); continue
            sides = {}
            for br in ("if_true", "if_false"):
                v, e2 = T.validate({"events": [dict(c[br], label=ev, recognised=False)]}, {ev: keep[ev]})
                errs += [f"claim {i} {br}: {x}" for x in e2]; sides[br] = v.get(ev)
            claims.append({"if": c["if"], "then_event": ev, **sides})
        except (KeyError, TypeError, AttributeError) as ex:
            errs.append(f"claim {i}: malformed ({ex!r})")
    text = json.dumps(obj)
    if ODDS.search(text):
        errs.append(f"the answer speaks of a market's view ({ODDS.search(text).group(0)!r}), R6")
    return {"drop": drop, "views": views, "scale": scale, "claims": claims, "sources": obj.get("sources") or []}, errs


def book_ask(tok):
    """Best ask for buying a token now, and the dollars on offer within 1 and 2 cents of it (decision 11: depth at every lock); None if the book is empty or unreachable."""
    try:
        b = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://clob.polymarket.com/book?token_id={tok}", headers=BC.H), timeout=30).read().decode("utf-8"))
        asks = sorted((float(x["price"]), float(x["size"])) for x in (b.get("asks") or []))
        if not asks:
            return None
        best = asks[0][0]
        return {"ask": best, "usd_1c": sum(p * s for p, s in asks if p <= best + 0.01 + 1e-9), "usd_2c": sum(p * s for p, s in asks if p <= best + 0.02 + 1e-9)}
    except Exception:
        return None


def cmd_ingest(a):
    meta = A.jload(os.path.join(D, "sessions", f"{a.sid}.json")); prompt = open(os.path.join(D, "sessions", f"{a.sid}.txt"), encoding="utf-8").read()
    dst = os.path.join(A.PROMPT_DIR, f"t3_{a.sid}.txt"); path = V.find_transcript(a.agent_id)
    au, evidence = audit_retrieval(path, dst, prompt)
    if au["ok"] and not A.reads_by_line(path, dst, prompt):          # the whole prompt must have been read, by line number (BT-A addendum A2)
        au["ok"] = False; au["violations"].append("prompt not read in full")
    errs, ans = [], None
    try:
        ans, errs = validate(V.extract_json(V.final_answer(a.agent_id)), meta["labels"])
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    lock = now_ts(); prices = {}
    if status == "ok":                                      # the lock is the hand-back: prices are read now, after the answer exists
        for r in meta["events"]:
            for c in r["contracts"]:
                prices[c["cid"]] = {"ask_yes": book_ask(c["token_yes"]), "ask_no": book_ask(c["token_no"]) if c.get("token_no") else None}
    # the fetch tool gives the session a summary, not the page: each fetched URL is re-read now and kept whole, hashed (v18 §5.3's evidence record)
    edir = os.path.join(D, "evidence", a.sid); os.makedirs(edir, exist_ok=True)
    for ev in evidence:
        if ev["tool"] != "WebFetch":
            continue
        u = ev["input"].get("url", "")
        try:
            body = urllib.request.urlopen(urllib.request.Request(u, headers=BC.H), timeout=60).read()
            h = hashlib.sha256(body).hexdigest()
            with gzip.GzipFile(os.path.join(edir, f"{h}.gz"), "wb", mtime=0) as fh:
                fh.write(body)
            ev["page_sha256"], ev["page_refetched_at"] = h, now_ts()
        except Exception as ex:
            ev["page_refetch_error"] = repr(ex)[:200]
    rec = {"session": a.sid, "agent_id": a.agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "evidence": evidence, "lock": lock,
           "lock_prices": prices, "prompt_sha256": meta["prompt_sha256"], "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    A.jdump(rec, os.path.join(D, "answers", f"{a.sid}.json"))
    print(json.dumps({"session": a.sid, "status": status, "errors": errs[:6], "violations": au["violations"], "tool_calls": au["tool_calls"],
                      "pages_quoting_odds": au["pages_quoting_odds"], "claims": len((ans or {}).get("claims") or []), "priced": len(prices)}))


def cmd_freeze(a):
    rows = {}
    for f in sorted(os.listdir(os.path.join(D, "answers"))):
        r = A.jload(os.path.join(D, "answers", f))
        rows[r["session"]] = {"status": r["status"], "answers_sha256": A.sha(r["answers"]), "lock": r["lock"], "lock_prices_sha256": A.sha(r["lock_prices"]),
                              "evidence_sha256": A.sha(r["evidence"]), "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "sessions": rows}; man["manifest_sha256"] = A.sha(man)
    A.jdump(man, os.path.join(D, "manifest.json")); print(json.dumps({"sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("snapshot", "clusters", "sessions", "freeze"):
        sp.add_parser(n)
    p = sp.add_parser("publish"); p.add_argument("sid")
    p = sp.add_parser("ingest"); p.add_argument("sid"); p.add_argument("agent_id")
    a = ap.parse_args()
    {"snapshot": cmd_snapshot, "clusters": cmd_clusters, "sessions": cmd_sessions, "publish": cmd_publish, "ingest": cmd_ingest, "freeze": cmd_freeze}[a.cmd](a)


if __name__ == "__main__":
    main()
