"""BT-A, the cutoff audit (v18 §6.7; registration BT_A_prereg.md). Does the operator model know how events turned out, month by month?

    python lookbacks/polymarket/bt_audit.py draw --crawl <bt/closed_*.json.gz>   # eligibility, seeded draw, prices at the price time; writes bt/audit/draw.json
    python lookbacks/polymarket/bt_audit.py sessions                              # writes bt/audit/sessions/S##.json (private label map) and S##.txt (the prompt)
    python lookbacks/polymarket/bt_audit.py publish S01                           # copies the prompt outside the repository, prints the one-line instruction
    python lookbacks/polymarket/bt_audit.py ingest S01 <agent_id>                 # audits the transcript, validates, stores bt/audit/answers/S01.json
    python lookbacks/polymarket/bt_audit.py freeze                                # hashes every answer into bt/audit/manifest.json (before any score)
    python lookbacks/polymarket/bt_audit.py score                                 # needs the manifest; writes bt/audit/result.json (both gates, addendum A1)

Sessions are cold subagents sent one instruction: read the prompt file and answer. They see each event's rules and contract questions only, under opaque
labels: no price, volume, date of resolution, outcome or id. The V1 run tooling is imported unchanged (audit, hand-back extraction, leak scan).
"""
import argparse, collections, datetime as dt, gzip, hashlib, json, math, os, random, re, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import numpy as np
import v1_packet as K
import v1_run as V

D = os.path.join(HERE, "bt", "audit")
PROMPT_DIR = os.environ.get("NOMAD_PROMPT_DIR", os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "nomad_prompts") if os.name == "nt" else "/tmp/nomad_prompts")
DECLARED_MODEL = "claude-opus-5-5"

# ---- registered design values (BT_A_prereg.md §3); none is read from data
SEED = 20261001
MONTHS = [f"2026-{m:02d}" for m in range(1, 10)]          # by scheduled end
CONTROL = {"2026-01", "2026-02", "2026-03"}                # positive control: well before the declared cutoff (v18 §6.7)
N_NEWS, N_PRICE = 40, 10                                   # per month: BT_AUDIT_N for the gated stratum; a smaller price-level stratum, reported only
LEAD_DAYS = 14                                             # price time = 14 days before the earlier of scheduled end and actual close (v18 §6.7)
MAX_AGE_H = 48                                             # a price point within 48 hours before the price time (V1 A2)
MIN_POINTS, POINTS_WINDOW_D = 10, 7                        # BT_MIN_POINTS: price points in the 7 days before the price time, on each scored contract
MAX_CONTRACTS = 12                                         # contracts scored per event, in display order (V1's menu cap)
PER_SESSION = 10                                           # events per session (v18 §6.7)
Q_FLOOR = 0.001                                            # a price side is floored at Polymarket's smallest tick
GATES = {"loose": 0.5, "strict": 0.2}                      # BT_AUDIT_GATE (Rob, 2026-10-01; BT_A_prereg.md addendum A1): loose first pass, v18's 0.2 as the confirming pass
PRICE_TAGS = {"crypto-prices", "hit-price", "stock-prices", "finance-updown", "pyth-finance", "multi-strikes", "equities", "stocks", "commodities",
              "forex", "crypto", "bitcoin", "ethereum", "solana", "xrp", "ripple", "dogecoin", "token-prices", "pre-market", "fdv"}
MAKER = re.compile(r"\b(anthropic|claude)\b", re.I)        # v18 §6.7 rule 6: events about the operator model's maker are excluded


def ts(s):
    if not s:
        return None
    s = s.strip().replace(" ", "T")
    if s.endswith("+00"):
        s += ":00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T00:00:00"
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return int((t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).timestamp())


def month_of(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def jload(p):
    with (gzip.open(p, "rt", encoding="utf-8") if p.endswith(".gz") else open(p, encoding="utf-8")) as fh:
        return json.load(fh)


def jdump(o, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(o, fh, indent=1, sort_keys=True)


def yes_won(m):
    """True/False from the final outcome prices; None if not decisive."""
    try:
        outs = [o.lower() for o in json.loads(m.get("outcomes") or "[]")]; fin = [float(x) for x in json.loads(m.get("final") or "[]")]
    except Exception:
        return None
    if "yes" not in outs or sorted(fin) != [0.0, 1.0]:
        return None
    return fin[outs.index("yes")] == 1.0


def clean(e):
    """None if every market resolved decisively and undisputed (V1's rule), else the reason."""
    for m in e["markets"]:
        if m.get("uma") != "resolved":
            return "not_resolved"
        if yes_won(m) is None:
            return "not_decisive"
        if "disputed" in json.dumps(m.get("uma_all") or "").lower():
            return "disputed"
    return None


def stratum(e):
    return "price" if set(e["tags"]) & PRICE_TAGS else "news"


def text_of(e):
    return " ".join([e.get("title") or "", e.get("description") or ""] + [(m.get("q") or "") + " " + (m.get("description") or "") for m in e["markets"]])


# ---- prices: one fetch per token, the 7 days before the price time, kept in a cache that is hashed into the draw
CACHE = {}


def history(tok, t):
    key = f"{tok}@{t}"
    if key not in CACHE:
        pts = []
        for fid in (60, 720):
            h = K._history(f"https://clob.polymarket.com/prices-history?market={tok}&startTs={t - POINTS_WINDOW_D * 86400}&endTs={t}&fidelity={fid}")
            pts = sorted(((int(x["t"]), float(x["p"])) for x in (h or {}).get("history", []) if int(x["t"]) <= t), key=lambda x: x[0])
            if pts and t - pts[-1][0] <= MAX_AGE_H * 3600:
                break
        CACHE[key] = pts
    return CACHE[key]


def price_at(tok, t):
    """(price, points in the window) or (None, n): the last point at or before t no older than 48 hours."""
    pts = history(tok, t)
    if not pts or t - pts[-1][0] > MAX_AGE_H * 3600:
        return None, len(pts)
    return pts[-1][1], len(pts)


def eligible_event(e):
    """(record, None) for an event that can be scored at its price time, or (None, reason). Reads no outcome except 'resolved cleanly'."""
    end, closed = ts(e.get("end")), ts(e.get("closed_time"))
    if end is None:
        return None, "no_end"
    t = min(end, closed) - LEAD_DAYS * 86400 if closed else end - LEAD_DAYS * 86400
    if ts(e.get("created")) and ts(e["created"]) > t:
        return None, "created_after_price_time"
    ms = []
    for m in sorted(e["markets"], key=K.order_key):
        if not m.get("tokens") or (m.get("created") and ts(m["created"]) > t) or (m.get("closed_time") and ts(m["closed_time"]) <= t):
            continue
        p, n = price_at(m["tokens"][0], t)
        if p is None or n < MIN_POINTS:
            continue
        ms.append({"cid": m["cid"], "token_yes": m["tokens"][0], "q": m.get("q"), "git": m.get("git"), "description": m.get("description"), "price_yes": p, "points": n})
        if len(ms) == MAX_CONTRACTS:
            break
    if not ms:
        return None, "no_priced_contract"
    return {"id": e["id"], "title": e["title"], "description": e.get("description"), "tags": e["tags"], "month": month_of(end), "stratum": stratum(e),
            "price_time": t, "end": e.get("end"), "closed_time": e.get("closed_time"), "contracts": ms}, None


def cmd_draw(a):
    crawl = jload(a.crawl)
    tally = collections.Counter(); pools = collections.defaultdict(list)
    for e in crawl:
        end = ts(e.get("end"))
        if end is None or month_of(end) not in MONTHS:
            tally["outside_months"] += 1; continue
        if MAKER.search(text_of(e) + " " + " ".join(e["tags"])):
            tally["maker_excluded"] += 1; continue
        r = clean(e)
        if r:
            tally[r] += 1; continue
        if K.leak_flags(text_of(e)):
            tally["leak_flag"] += 1; continue
        pools[(month_of(end), stratum(e))].append(e)
    draw, reasons = [], collections.Counter()
    for (mo, st), evs in sorted(pools.items()):
        rng = random.Random(f"{SEED}:{mo}:{st}"); evs = sorted(evs, key=lambda e: e["id"]); rng.shuffle(evs)
        need, got = (N_NEWS if st == "news" else N_PRICE), 0
        for e in evs:
            if got == need:
                break
            rec, why = eligible_event(e)
            if rec is None:
                reasons[why] += 1; continue
            draw.append(rec); got += 1
        tally[f"drawn_{mo}_{st}"] = got; tally[f"pool_{mo}_{st}"] = len(evs)
        print(mo, st, f"drew {got} of {need} from a pool of {len(evs)}", file=sys.stderr, flush=True)
    os.makedirs(D, exist_ok=True)
    with gzip.GzipFile(os.path.join(D, "price_cache.json.gz"), "wb", mtime=0) as fh:
        fh.write(json.dumps(CACHE, sort_keys=True).encode("utf-8"))
    out = {"crawl": os.path.basename(a.crawl), "crawl_sha256": hashlib.sha256(open(a.crawl, "rb").read()).hexdigest(), "tally": dict(tally),
           "ineligible_after_draw": dict(reasons), "events": draw}
    jdump(out, os.path.join(D, "draw.json")); print(json.dumps({"events": len(draw), "draw_sha256": sha(draw)}))


PROMPT = """You will be shown {n} questions from a prediction market. Each question has one or more contracts, and each contract resolves YES or NO under the rules shown.

For every contract, give your probability, as a whole percent from 1 to 99, that it resolves YES. Use only what you already know. Do not search for or look up anything: reading this file is the only tool call you may make.

For each question, also say whether you recognise how it actually turned out ("recognised": true only if you believe you remember the real outcome; otherwise false).

Where a question's contracts are mutually exclusive (exactly one can resolve YES), your numbers for it should add up to about 100. Where they are nested thresholds or dates, keep them consistent with each other.

Reply with one JSON object and nothing else, in this form:
{{"events": [{{"label": "E1", "recognised": false, "p": {{"E1.C1": 35, "E1.C2": 60}}}}]}}

Every contract label below must appear exactly once in your reply.

{body}"""


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"\d[\d,.:]*", "#", t or "")).strip().lower()


def event_block(i, ev):
    """The event's shared rules once; a contract's own rules only where they differ beyond dates and numbers (V1's shared-rules rule)."""
    shared = (ev.get("description") or "").strip()
    first = next((c.get("description") for c in ev["contracts"] if c.get("description")), "") or ""
    rules = shared or first.strip()
    lines = [f"=== E{i}: {ev['title']}", "Rules:", rules, "Contracts:"]
    for j, c in enumerate(ev["contracts"], 1):
        lines.append(f"  E{i}.C{j}: {c['q']}")
        d = (c.get("description") or "").strip()
        if d and _norm(d) != _norm(rules):
            lines.append(f"    Contract rules: {d}")
    return "\n".join(lines)


def cmd_sessions(a):
    draw = jload(os.path.join(D, "draw.json"))["events"]
    evs = sorted(draw, key=lambda e: e["id"]); random.Random(f"{SEED}:sessions").shuffle(evs)
    os.makedirs(os.path.join(D, "sessions"), exist_ok=True)
    for s in range(0, len(evs), PER_SESSION):
        chunk = evs[s:s + PER_SESSION]; sid = f"S{s // PER_SESSION + 1:02d}"
        labels = {f"E{i}": {"event_id": ev["id"], "contracts": {f"E{i}.C{j}": c["cid"] for j, c in enumerate(ev["contracts"], 1)}} for i, ev in enumerate(chunk, 1)}
        text = PROMPT.format(n=len(chunk), body="\n\n".join(event_block(i, ev) for i, ev in enumerate(chunk, 1)))
        flags = K.leak_flags(text)
        if flags:
            raise SystemExit(f"{sid}: leak flags in the prompt {flags}")
        with open(os.path.join(D, "sessions", f"{sid}.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        jdump({"session": sid, "labels": labels, "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}, os.path.join(D, "sessions", f"{sid}.json"))
    print(json.dumps({"sessions": (len(evs) + PER_SESSION - 1) // PER_SESSION, "events": len(evs)}))


INSTRUCTION = "Your task is in the file {path}. Read that file (it is the only tool call you may make), then answer exactly as it instructs."


def cmd_publish(a):
    src = os.path.join(D, "sessions", f"{a.sid}.txt"); os.makedirs(PROMPT_DIR, exist_ok=True)
    dst = os.path.join(PROMPT_DIR, f"bta_{a.sid}.txt"); shutil.copyfile(src, dst)
    print(INSTRUCTION.format(path=dst))


def validate(obj, labels):
    errs, out = [], {}
    evs = {e.get("label"): e for e in (obj.get("events") or []) if isinstance(e, dict)}
    for lab, L in labels.items():
        e = evs.get(lab)
        if e is None:
            errs.append(f"{lab} missing"); continue
        p = e.get("p") or {}
        for cl in L["contracts"]:
            v = p.get(cl)
            if not isinstance(v, (int, float)) or not 1 <= v <= 99:
                errs.append(f"{cl}: {v!r} is not a percent from 1 to 99")
        extra = set(p) - set(L["contracts"])
        if extra:
            errs.append(f"{lab}: unknown labels {sorted(extra)}")
        out[lab] = {"recognised": bool(e.get("recognised")), "p": {k: float(p[k]) for k in L["contracts"] if k in p}}
    return out, errs


def cmd_ingest(a):
    meta = jload(os.path.join(D, "sessions", f"{a.sid}.json")); prompt = open(os.path.join(D, "sessions", f"{a.sid}.txt"), encoding="utf-8").read()
    path = V.find_transcript(a.agent_id); dst = os.path.join(PROMPT_DIR, f"bta_{a.sid}.txt")
    au = V.audit_transcript(path, declared=DECLARED_MODEL, allowed_reads={dst: prompt}, expect_instructions=[INSTRUCTION.format(path=dst)])
    status, errs, ans = "invalid", [], None
    try:
        obj = V.extract_json(V.final_answer(a.agent_id))
        ans, errs = validate(obj, meta["labels"])
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    rec = {"session": a.sid, "agent_id": a.agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "prompt_sha256": meta["prompt_sha256"],
           "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    jdump(rec, os.path.join(D, "answers", f"{a.sid}.json"))
    print(json.dumps({k: rec[k] for k in ("session", "status", "errors")} | {"audit_ok": au["ok"], "tool_calls": au["tool_calls"], "models": au["models"]}))


def cmd_freeze(a):
    rows = {}
    for f in sorted(os.listdir(os.path.join(D, "answers"))):
        r = jload(os.path.join(D, "answers", f)); rows[r["session"]] = {"status": r["status"], "answers_sha256": sha(r["answers"]), "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "draw_sha256": sha(jload(os.path.join(D, "draw.json"))["events"]), "sessions": rows}
    man["manifest_sha256"] = sha(man); jdump(man, os.path.join(D, "manifest.json")); print(json.dumps({"sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


def boot_mean(x, rng, n=4000):
    x = np.asarray(x, float); idx = rng.integers(0, len(x), (n, len(x)))
    return x[idx].mean(axis=1)


def cmd_score(a):
    man = jload(os.path.join(D, "manifest.json")); draw = {e["id"]: e for e in jload(os.path.join(D, "draw.json"))["events"]}
    for sid, row in man["sessions"].items():                       # the answers scored are the ones frozen
        if sha(jload(os.path.join(D, "answers", f"{sid}.json"))["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{sid} changed after the freeze")
    crawl = {e["id"]: e for e in jload(os.path.join(HERE, "bt", jload(os.path.join(D, "draw.json"))["crawl"]))}
    res = {}
    for sid, row in man["sessions"].items():
        if row["status"] != "ok":
            continue
        r = jload(os.path.join(D, "answers", f"{sid}.json")); labels = jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = draw[L["event_id"]]; mk = {m["cid"]: m for m in crawl[L["event_id"]]["markets"]}; pr = {c["cid"]: c["price_yes"] for c in ev["contracts"]}
            terms = []
            for cl, cid in L["contracts"].items():
                y = yes_won(mk[cid]); p = r["answers"][lab]["p"][cl] / 100.0; q = pr[cid]
                ps, qs = (p, q) if y else (1 - p, 1 - q)
                terms.append(math.log(ps / max(qs, Q_FLOOR)))
            res[L["event_id"]] = {"month": ev["month"], "stratum": ev["stratum"], "excess": float(np.mean(terms)), "recognised": r["answers"][lab]["recognised"], "session": sid}
    rng = np.random.default_rng(SEED); out = {"gates": GATES, "by_month": {}}
    ctrl = [v["excess"] for v in res.values() if v["stratum"] == "news" and v["month"] in CONTROL]
    cb = boot_mean(ctrl, rng); out["control"] = {"n": len(ctrl), "mean": float(np.mean(ctrl)), "ci90": [float(np.quantile(cb, .05)), float(np.quantile(cb, .95))],
                                                 "p_positive": float(np.mean(cb > 0))}
    informative = out["control"]["mean"] > 0
    for mo in MONTHS:
        for st in ("news", "price"):
            x = [v["excess"] for v in res.values() if v["month"] == mo and v["stratum"] == st]
            if not x:
                continue
            b = boot_mean(x, rng); row = {"n": len(x), "mean": float(np.mean(x)), "ci90": [float(np.quantile(b, .05)), float(np.quantile(b, .95))],
                                         "recognised": sum(v["recognised"] for v in res.values() if v["month"] == mo and v["stratum"] == st)}
            if st == "news" and mo not in CONTROL and informative:
                row["p_reaches_half_control"] = float(np.mean(b >= 0.5 * cb))
                row["clean"] = {name: row["p_reaches_half_control"] <= g for name, g in GATES.items()}
            out["by_month"][f"{mo}_{st}"] = row
    out["bt_window_start"] = {}
    for name in GATES:
        start = None
        if informative:
            test = [mo for mo in MONTHS if mo not in CONTROL]
            for i, mo in enumerate(test):
                if all(out["by_month"].get(f"{m}_news", {}).get("clean", {}).get(name) for m in test[i:]):
                    start = mo; break
        out["bt_window_start"][name] = f"{start}-01" if start else None
    if not informative:
        out["note"] = "the positive control shows no recall (mean excess not above zero), so the gate cannot be calibrated; the declared cutoff stands, unaudited"
    out["events"] = res; jdump(out, os.path.join(D, "result.json"))
    print(json.dumps({k: v for k, v in out.items() if k != "events"}, indent=1))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("draw"); p.add_argument("--crawl", required=True)
    sp.add_parser("sessions")
    p = sp.add_parser("publish"); p.add_argument("sid")
    p = sp.add_parser("ingest"); p.add_argument("sid"); p.add_argument("agent_id")
    sp.add_parser("freeze")
    sp.add_parser("score")
    a = ap.parse_args()
    {"draw": cmd_draw, "sessions": cmd_sessions, "publish": cmd_publish, "ingest": cmd_ingest, "freeze": cmd_freeze, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
