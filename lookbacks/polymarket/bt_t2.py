"""BT-T2: single events backtested in the graded format, no-evidence arm (registration BT_T2_prereg.md and its addendum A1).

    python lookbacks/polymarket/bt_t2.py frame --start 2026-07-01 [--strict-start 2026-07-01]   # network (price history); writes bt/t2/frame.json
    python lookbacks/polymarket/bt_t2.py sessions
    python lookbacks/polymarket/bt_t2.py publish S01
    python lookbacks/polymarket/bt_t2.py ingest S01 <agent_id>
    python lookbacks/polymarket/bt_t2.py freeze
    python lookbacks/polymarket/bt_t2.py score

Shares BT-A's helpers (crawl reading, clean resolution, price at a time from a 7-day window) and V1's run tooling (audit, hand-back, leak scan, orientation and
strike parsing, all-in cost). Nothing in V1, V1b, V3 or T0 is edited.
"""
import argparse, collections, datetime as dt, json, math, os, random, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import numpy as np
import bt_audit as A
import v1_packet as K
import v1_run as V
import v1_score as S
from nomad16 import exact as X
from nomad16 import pmgraph as G

D = os.path.join(HERE, "bt", "t2")
CRAWL = "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"
SEED = 20261002
DATA_DATE = A.ts("2026-09-30T23:59:59Z")
LOCK_HOUR = 12
STEP_D, HORIZON_D, MIN_OPEN = 7, 75, 3                      # BT_LOCK_STEP, T2_HORIZON_DAYS, T2_MIN_OPEN_MARKETS
PER_STRATUM, PER_SESSION = 90, 6                            # addendum A1; SWEEP_BATCH
SLIP, MATCH_BAND = 0.01, 0.05
CHANCES = (10, 25, 50, 75, 90)
DEADLINE = re.compile(rf"\b(by|before)\s+(the\s+end\s+of\s+)?({S.MON}|\d)", re.I)
INSTRUCTION = A.INSTRUCTION


def iso_day(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")


def lock_grid(start):
    t = A.ts(f"{start}T{LOCK_HOUR:02d}:00:00Z"); out = []
    while t <= DATA_DATE:
        out.append(t); t += STEP_D * 86400
    return out


def kind_of(e, n_open):
    """Session format for an event (BT_T2_prereg.md §3)."""
    if len(e["markets"]) == 1:
        return "dates1" if DEADLINE.search(e["markets"][0].get("q") or "") else "percent"
    st = G.structure({"markets": e["markets"], "negRisk": e.get("negRisk")})
    c = st["class"]
    if c in ("partition_exact", "partition_open"):
        return "partition"
    if c == "ladder":
        return "touch" if st.get("kind") == "touch" else "terminal"
    if c == "date_ladder":
        return "dates"
    if c == "other":
        return "percent"
    return None                                               # 'single' with two markets: neither stratum


def schedule_locks(e, grid):
    """Locks at which the event passes the schedule rules (§2), each with the markets open at it."""
    out = []
    for L in grid:
        if A.ts(e.get("created")) and A.ts(e["created"]) > L:
            continue
        ms = [m for m in e["markets"] if m.get("tokens") and not (m.get("created") and A.ts(m["created"]) > L)
              and not (m.get("closed_time") and A.ts(m["closed_time"]) <= L) and m.get("end") and A.ts(m["end"]) > L]   # a deadline already past at the lock is not open
        if not ms:
            continue
        H = max(A.ts(m["end"]) for m in ms)
        if H > L + HORIZON_D * 86400 or H > DATA_DATE:
            continue
        out.append((L, ms))
    return out


def priced(ms, L):
    out = []
    for m in sorted(ms, key=K.order_key):
        p, n = A.price_at(m["tokens"][0], L)
        if p is not None and n >= A.MIN_POINTS:
            out.append({"cid": m["cid"], "token_yes": m["tokens"][0], "q": m.get("q"), "git": m.get("git"), "description": m.get("description"),
                        "end": m.get("end"), "price_yes": p, "fee": m.get("feeSchedule"), "tick": m.get("tick")})
    return out


def cmd_frame(a):
    crawl = A.jload(os.path.join(HERE, "bt", CRAWL)); grid = lock_grid(a.start)
    tally = collections.Counter(); cands = collections.defaultdict(list)
    for e in crawl:
        if A.MAKER.search(A.text_of(e) + " " + " ".join(e["tags"])):
            tally["maker_excluded"] += 1; continue
        r = A.clean(e)
        if r:
            tally[r] += 1; continue
        if K.leak_flags(A.text_of(e)):
            tally["leak_flag"] += 1; continue
        k = kind_of(e, len(e["markets"]))
        if k is None:
            tally["two_market"] += 1; continue
        locks = schedule_locks(e, grid)
        if not locks:
            tally["no_schedule_lock"] += 1; continue
        cands["binary" if len(e["markets"]) == 1 else "multi"].append((e, k, locks))
    frame = []
    for stratum, evs in sorted(cands.items()):
        rng = random.Random(f"{SEED}:{stratum}"); evs = sorted(evs, key=lambda x: x[0]["id"]); rng.shuffle(evs)
        got = 0
        for e, k, locks in evs:
            if got == PER_STRATUM:
                break
            order = list(locks); random.Random(f"{SEED}:{e['id']}").shuffle(order)
            pick = None
            for L, ms in order:
                cs = priced(ms, L)
                if (stratum == "multi" and len(cs) >= MIN_OPEN) or (stratum == "binary" and len(cs) == 1):
                    pick = (L, cs); break
            if pick is None:
                tally[f"no_priced_lock_{stratum}"] += 1; continue
            L, cs = pick
            frame.append({"id": e["id"], "title": e["title"], "description": e.get("description"), "tags": e["tags"], "stratum": stratum, "kind": k,
                          "lock": L, "as_of": iso_day(L), "n_schedule_locks": len(locks), "volume": e.get("volume"),
                          "strict": bool(a.strict_start and L >= A.ts(f"{a.strict_start}T00:00:00Z")), "contracts": cs})
            got += 1
        tally[f"pool_{stratum}"] = len(evs); tally[f"drawn_{stratum}"] = got
        print(stratum, f"drew {got} from a pool of {len(evs)}", file=sys.stderr, flush=True)
    os.makedirs(D, exist_ok=True)
    with A.gzip.GzipFile(os.path.join(D, "price_cache.json.gz"), "wb", mtime=0) as fh:
        fh.write(json.dumps(A.CACHE, sort_keys=True).encode("utf-8"))
    out = {"crawl": CRAWL, "crawl_sha256": A.hashlib.sha256(open(os.path.join(HERE, "bt", CRAWL), "rb").read()).hexdigest(), "start": a.start,
           "strict_start": a.strict_start, "tally": dict(tally), "events": frame}
    A.jdump(out, os.path.join(D, "frame.json")); print(json.dumps({"events": len(frame), "frame_sha256": A.sha(frame), "tally": dict(tally)}))


# ---------------------------------------------------------------- packets
PROMPT = """You will be shown {n} questions from a prediction market. Each has one or more contracts that resolve YES or NO under the rules shown. Each question gives the date your view is "as of": answer as you would on that date.

Use only what you already know. Do not search for or look up anything: reading this file is the only tool call you may make. There are no prices in this file and you should not try to estimate what any market thinks; give your own view.

Each question says what to write for it. Whole percents run from 1 to 99. Levels are plain numbers in the units the contracts use (for example 95000 for $95,000, 3.25 for 3.25%). Dates are YYYY-MM-DD.

For each question also say whether you recognise how it actually turned out ("recognised": true only if you believe you remember the real outcome; otherwise false).

Reply with one JSON object and nothing else:
{{"events": [{{"label": "E1", "recognised": false, ...the fields that question asks for...}}]}}

{body}"""

ASK = {
    "partition": 'Write "p": a whole percent for every contract label, your chance that it is the one that resolves YES. They should add up to about 100 (less if outcomes not listed could win).',
    "percent": 'Write "p": a whole percent for every contract label, your chance that it resolves YES.',
    "terminal": 'Write "levels": for each chance 10, 25, 50, 75 and 90, the level you give that chance of the measured quantity being at or above when it resolves. The 10 level is the highest and the 90 level the lowest. Example: {"10": 120, "25": 110, "50": 100, "75": 92, "90": 85}.',
    "touch_high": 'Write "high": for each chance 10, 25, 50, 75 and 90, the level you give that chance of being reached (at or above) within the period. The 10 level is the highest.',
    "touch_low": 'Write "low": for each chance 10, 25, 50, 75 and 90, the level you give that chance of being reached (at or below) within the period. The 10 level is the lowest.',
    "dates": 'Write "dates": for each chance 10, 25, 50, 75 and 90, the date by which you give it that chance of having happened, or null if you do not give it that chance by the last date the contracts cover. Dates must not go earlier as the chance rises.',
}


def sides(ev):
    s = {S.orient(c["q"]) for c in ev["contracts"]}
    return [x for x in ("up", "down") if x in s]


def asks(ev):
    k = ev["kind"]
    if k == "touch":
        return [ASK["touch_high" if s == "up" else "touch_low"] for s in sides(ev)]
    return [ASK["dates" if k == "dates1" else k]]


def block(i, ev):
    shared = (ev.get("description") or "").strip() or ((ev["contracts"][0].get("description") or "").strip())
    lines = [f"=== E{i} (as of {ev['as_of']}): {ev['title']}", "Rules:", shared, "Contracts:"]
    for j, c in enumerate(ev["contracts"], 1):
        lines.append(f"  E{i}.C{j}: {c['q']}")
        d = (c.get("description") or "").strip()
        if d and A._norm(d) != A._norm(shared):
            lines.append(f"    Contract rules: {d}")
    lines += ["What to write for E%d:" % i] + ["  " + x for x in asks(ev)]
    return "\n".join(lines)


def cmd_sessions(a):
    fr = A.jload(os.path.join(D, "frame.json"))["events"]
    evs = sorted(fr, key=lambda e: e["id"]); random.Random(f"{SEED}:sessions").shuffle(evs)
    os.makedirs(os.path.join(D, "sessions"), exist_ok=True)
    for s in range(0, len(evs), PER_SESSION):
        chunk = evs[s:s + PER_SESSION]; sid = f"S{s // PER_SESSION + 1:02d}"
        labels = {f"E{i}": {"event_id": ev["id"], "kind": ev["kind"], "sides": sides(ev) if ev["kind"] == "touch" else None,
                            "contracts": {f"E{i}.C{j}": c["cid"] for j, c in enumerate(ev["contracts"], 1)}} for i, ev in enumerate(chunk, 1)}
        text = PROMPT.format(n=len(chunk), body="\n\n".join(block(i, ev) for i, ev in enumerate(chunk, 1)))
        if K.leak_flags(text):
            raise SystemExit(f"{sid}: leak flags {K.leak_flags(text)}")
        with open(os.path.join(D, "sessions", f"{sid}.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        A.jdump({"session": sid, "labels": labels, "prompt_sha256": A.hashlib.sha256(text.encode("utf-8")).hexdigest()}, os.path.join(D, "sessions", f"{sid}.json"))
    print(json.dumps({"sessions": (len(evs) + PER_SESSION - 1) // PER_SESSION, "events": len(evs)}))


def cmd_publish(a):
    os.makedirs(A.PROMPT_DIR, exist_ok=True); dst = os.path.join(A.PROMPT_DIR, f"bt2_{a.sid}.txt")
    shutil.copyfile(os.path.join(D, "sessions", f"{a.sid}.txt"), dst); print(INSTRUCTION.format(path=dst))


def _pct(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 1 <= v <= 99


def _five(d, kind):
    """Validate a five-chance object; returns (clean dict {chance: value or None}, errors)."""
    if not isinstance(d, dict):
        return None, ["not an object"]
    out, errs = {}, []
    for c in CHANCES:
        v = d.get(str(c), d.get(c))
        if kind == "dates":
            if v is None:
                out[c] = None; continue
            try:
                out[c] = A.ts(str(v)[:10] + "T23:59:59Z")
            except Exception:
                errs.append(f"{c}: {v!r} is not a date"); continue
        else:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                errs.append(f"{c}: {v!r} is not a number"); continue
            out[c] = float(v)
    if errs:
        return None, errs
    vals = [out[c] for c in CHANCES]
    if kind == "dates":
        seen_null = False
        for c in CHANCES:
            if out[c] is None:
                seen_null = True
            elif seen_null:
                errs.append("a date follows a null")
        nn = [v for v in vals if v is not None]
        if any(b < a for a, b in zip(nn, nn[1:])):
            errs.append("dates go earlier as the chance rises")
    elif kind == "desc":                                      # 10 highest ... 90 lowest
        if any(b > a for a, b in zip(vals, vals[1:])):
            errs.append("levels must not rise from 10 to 90")
    elif kind == "asc":                                       # 10 lowest ... 90 highest
        if any(b < a for a, b in zip(vals, vals[1:])):
            errs.append("levels must not fall from 10 to 90")
    return out, errs


def validate(obj, labels):
    errs, out = [], {}
    evs = {e.get("label"): e for e in (obj.get("events") or []) if isinstance(e, dict)}
    for lab, L in labels.items():
        e = evs.get(lab)
        if e is None:
            errs.append(f"{lab} missing"); continue
        rec = {"recognised": bool(e.get("recognised"))}; k = L["kind"]
        if k in ("partition", "percent"):
            p = e.get("p") or {}
            bad = [cl for cl in L["contracts"] if not _pct(p.get(cl))]
            if bad:
                errs.append(f"{lab}: no whole percent for {bad}")
            rec["p"] = {cl: float(p[cl]) for cl in L["contracts"] if _pct(p.get(cl))}
        elif k == "terminal":
            v, er = _five(e.get("levels"), "desc"); errs += [f"{lab} levels: {x}" for x in er]; rec["levels"] = v
        elif k == "touch":
            for sd in L["sides"]:
                key = "high" if sd == "up" else "low"
                v, er = _five(e.get(key), "desc" if sd == "up" else "asc"); errs += [f"{lab} {key}: {x}" for x in er]; rec[key] = v
        elif k in ("dates", "dates1"):
            v, er = _five(e.get("dates"), "dates"); errs += [f"{lab} dates: {x}" for x in er]; rec["dates"] = v
        out[lab] = rec
    return out, errs


def cmd_ingest(a):
    meta = A.jload(os.path.join(D, "sessions", f"{a.sid}.json")); prompt = open(os.path.join(D, "sessions", f"{a.sid}.txt"), encoding="utf-8").read()
    path = V.find_transcript(a.agent_id); dst = os.path.join(A.PROMPT_DIR, f"bt2_{a.sid}.txt")
    au = V.audit_transcript(path, declared=A.DECLARED_MODEL, allowed_reads={dst: prompt}, expect_instructions=[INSTRUCTION.format(path=dst)])
    errs, ans = [], None
    try:
        ans, errs = validate(V.extract_json(V.final_answer(a.agent_id)), meta["labels"])
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    rec = {"session": a.sid, "agent_id": a.agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "prompt_sha256": meta["prompt_sha256"],
           "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    A.jdump(rec, os.path.join(D, "answers", f"{a.sid}.json"))
    print(json.dumps({"session": a.sid, "status": status, "errors": errs[:6], "audit_ok": au["ok"], "tool_calls": au["tool_calls"], "models": au["models"]}))


def cmd_freeze(a):
    rows = {}
    for f in sorted(os.listdir(os.path.join(D, "answers"))):
        r = A.jload(os.path.join(D, "answers", f)); rows[r["session"]] = {"status": r["status"], "answers_sha256": A.sha(r["answers"]), "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "frame_sha256": A.sha(A.jload(os.path.join(D, "frame.json"))["events"]), "sessions": rows}
    man["manifest_sha256"] = A.sha(man); A.jdump(man, os.path.join(D, "manifest.json")); print(json.dumps({"sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


# ---------------------------------------------------------------- scoring helpers (§4, §5)
AFTER = 1                                                     # dates are whole seconds: 'after d' starts one second past d (addendum A3)


def intkeys(answers):
    """Answers come back from JSON with the five chances as string keys ('10' ...); the scorer reads them as integers (addendum A3)."""
    out = {}
    for lab, rec in (answers or {}).items():
        r = dict(rec)
        for k in ("levels", "high", "low", "dates"):
            if isinstance(r.get(k), dict):
                r[k] = {int(c): v for c, v in r[k].items()}
        out[lab] = r
    return out


def chance_from_five(five, x, rising):
    """(lo, hi) chance that the variable is at or beyond x, from five (value at chance c) points.
    rising=False: P(V >= x) falls as x rises (levels written 10 highest); rising=True: P(event by x) rises with x (dates, low-side levels)."""
    pts = [(five[c], c / 100.0) for c in CHANCES if five.get(c) is not None]
    if not pts:
        return (0.0, CHANCES[0] / 100.0) if rising else (0.0, 1.0)
    if rising:
        pts.sort()
        if x < pts[0][0]:
            return (0.0, pts[0][1])
        for (v1, c1), (v2, c2) in zip(pts, pts[1:]):
            if v1 <= x <= v2:
                c = c1 if v2 == v1 else c1 + (c2 - c1) * (x - v1) / (v2 - v1); return (c, c)
        top_c = pts[-1][1]
        higher = [c / 100.0 for c in CHANCES if c / 100.0 > top_c]       # chances written as "not within the horizon"
        return (top_c, higher[0] if higher else 1.0)
    pts.sort()                                                # ascending value, falling chance
    if x > pts[-1][0]:
        return (0.0, pts[-1][1])
    if x < pts[0][0]:
        return (pts[0][1], 1.0)
    for (v1, c1), (v2, c2) in zip(pts, pts[1:]):
        if v1 <= x <= v2:
            c = c1 if v2 == v1 else c1 + (c2 - c1) * (x - v1) / (v2 - v1); return (c, c)
    return (0.0, 1.0)


def rung_value(c, kind):
    if kind in ("dates", "dates1"):
        return A.ts(c["end"])
    return S.strike(c["q"])


def contract_chance(ev, ans, lab, cl, c):
    """(lo, hi) of the session's chance that contract c resolves YES (§4); None if the view does not reach it."""
    k = ev["kind"]
    if k in ("partition", "percent"):
        p = ans[lab]["p"].get(cl)
        return None if p is None else (p / 100.0, p / 100.0)
    x = rung_value(c, k)
    if x is None:
        return None
    if k in ("dates", "dates1"):
        return chance_from_five(ans[lab]["dates"], x, rising=True)
    up = S.orient(c["q"]) == "up"
    if k == "terminal":
        lo, hi = chance_from_five(ans[lab]["levels"], x, rising=False)          # P(V >= x)
        return (lo, hi) if up else (1 - hi, 1 - lo)
    if k == "touch":
        if up:
            return chance_from_five(ans[lab]["high"], x, rising=False)
        return chance_from_five(ans[lab]["low"], x, rising=True)                # P(min <= x)
    return None


def cost(c, yes):
    q = c["price_yes"] if yes else 1 - c["price_yes"]
    return X.share_cost(q, c.get("fee"), SLIP, float(c["tick"]) if c.get("tick") else None)


def isotonic(xs, ys, increasing):
    """Pool-adjacent violators on ys ordered by xs."""
    order = sorted(range(len(xs)), key=lambda i: xs[i]); y = [ys[i] for i in order]; w = [1.0] * len(y)
    if not increasing:
        y = [-v for v in y]
    blocks = [[y[0], w[0], 1]]
    for v in y[1:]:
        blocks.append([v, 1.0, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            a, b = blocks.pop(), blocks.pop(); n = a[1] + b[1]; blocks.append([(a[0] * a[1] + b[0] * b[1]) / n, n, a[2] + b[2]])
    out = []
    for v, _, k in blocks:
        out += [(-v if not increasing else v)] * k
    return [xs[i] for i in order], out


def median_set(points, increasing):
    """Where the chance curve crosses 0.5, as an interval (lo, hi): a point gives lo == hi; beyond the outermost value gives an open side."""
    if not points:
        return (-math.inf, math.inf)
    xs, ys = isotonic([p[0] for p in points], [p[1] for p in points], increasing)
    for (x1, y1), (x2, y2) in zip(zip(xs, ys), list(zip(xs, ys))[1:]):
        if (y1 - 0.5) * (y2 - 0.5) <= 0 and y1 != y2:
            x = x1 + (0.5 - y1) * (x2 - x1) / (y2 - y1); return (x, x)
        if y1 == 0.5:
            return (x1, x1)
    if (ys[0] > 0.5) == (not increasing):                    # chance still above 0.5 at the top (falling curve) or below 0.5 at the top (rising curve)
        return (xs[-1] + (AFTER if increasing else 0), math.inf)   # dates: past the last rung means after it
    return (-math.inf, xs[0])


def gap(a, b):
    """Distance between two intervals (0 if they overlap)."""
    if a[1] < b[0]:
        return b[0] - a[1]
    if b[1] < a[0]:
        return a[0] - b[1]
    return 0.0


def outcome_interval(ev, kind, side=None):
    """The interval the realised variable fell in, from which rungs resolved YES."""
    cs = [c for c in ev["contracts"] if rung_value(c, kind) is not None and (side is None or S.orient(c["q"]) == side)]
    if not cs:
        return None
    if kind in ("dates", "dates1"):
        yes = [rung_value(c, kind) for c in cs if c["yes"]]; no = [rung_value(c, kind) for c in cs if not c["yes"]]
        return ((max(no) + AFTER) if no else ev["lock"], min(yes) if yes else math.inf)   # NO on a 'by d' rung means after d
    if kind == "terminal" or side == "up":                    # V >= k for YES on up rungs; V < k for YES on down rungs (terminal)
        ge = [rung_value(c, kind) for c in cs if (c["yes"] if S.orient(c["q"]) == "up" else not c["yes"])]
        lt = [rung_value(c, kind) for c in cs if (not c["yes"] if S.orient(c["q"]) == "up" else c["yes"])]
        return (max(ge) if ge else -math.inf, min(lt) if lt else math.inf)
    yes = [rung_value(c, kind) for c in cs if c["yes"]]; no = [rung_value(c, kind) for c in cs if not c["yes"]]   # low side: min <= k for YES
    return (max(no) if no else -math.inf, min(yes) if yes else math.inf)


def scaled_vars(ev):
    k = ev["kind"]
    if k in ("dates", "dates1"):
        return [("dates", None, True)]
    if k == "terminal":
        return [("levels", None, False)]
    if k == "touch":
        return [("high" if s == "up" else "low", s, s == "down") for s in sides(ev)]
    return []


def market_points(ev, side):
    k = ev["kind"]; pts = []
    for c in ev["contracts"]:
        x = rung_value(c, k)
        if x is None or (side and S.orient(c["q"]) != side):
            continue
        p = c["price_yes"]
        if k == "terminal" and S.orient(c["q"]) == "down":
            p = 1 - p                                         # P(V >= k) from a "below k" rung
        pts.append((x, p))
    return pts


def session_median(five, ev):
    v = five.get(50)
    if v is None:                                             # dates: the 50% chance is not reached by the last date the contracts cover
        last = max((A.ts(c["end"]) for c in ev["contracts"] if c.get("end")), default=ev["lock"])
        return (last + AFTER, math.inf)
    return (v, v)


def boot(x, rng, n=4000, by=None):
    x = np.asarray(x, float)
    if by is None:
        m = x[rng.integers(0, len(x), (n, len(x)))].mean(axis=1)
    else:
        groups = collections.defaultdict(list)
        for v, g in zip(x, by):
            groups[g].append(v)
        keys = list(groups); m = np.array([np.mean([v for i in rng.integers(0, len(keys), len(keys)) for v in groups[keys[i]]]) for _ in range(n)])
    return {"n": int(len(x)), "mean": float(x.mean()), "ci95": [float(np.quantile(m, .025)), float(np.quantile(m, .975))],
            "ci90": [float(np.quantile(m, .05)), float(np.quantile(m, .95))], "p_positive": float(np.mean(m > 0)),
            "declares": "edge shown" if np.quantile(m, .025) > 0 else ("edge shown absent" if np.quantile(m, .975) < 0 else "direction only")}


def cmd_score(a):
    man = A.jload(os.path.join(D, "manifest.json")); fdoc = A.jload(os.path.join(D, "frame.json")); frame = {e["id"]: e for e in fdoc["events"]}
    for sid, row in man["sessions"].items():
        if A.sha(A.jload(os.path.join(D, "answers", f"{sid}.json"))["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{sid} changed after the freeze")
    crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}
    for ev in frame.values():                                  # outcomes are read only here, after the freeze
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
    # the matched base: every drawn contract, both sides, by event class (addendum A1)
    base = [(ev["id"], ev["kind"], cost(c, yes), float(c["yes"] == yes)) for ev in frame.values() for c in ev["contracts"] for yes in (True, False)]
    rng = np.random.default_rng(SEED); pos, mags, calib, logs, base_t0, voided = [], [], collections.defaultdict(list), [], [], collections.Counter()
    for sid, row in man["sessions"].items():
        if row["status"] != "ok":
            voided[row["status"]] += 1; continue
        ans = intkeys(A.jload(os.path.join(D, "answers", f"{sid}.json"))["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"]:
                voided["recall_flag"] += 1; continue
            byc = {c["cid"]: c for c in ev["contracts"]}
            for cl, cid in L["contracts"].items():
                c = byc[cid]; ch = contract_chance(ev, ans, lab, cl, c)
                if ch is None:
                    continue
                lo, hi = ch
                for yes, want in ((True, lo), (False, 1 - hi)):
                    cc = cost(c, yes)
                    if want > cc:
                        hit = float(c["yes"] == yes)
                        bm = [h - k for (eid, kd, k, h) in base if eid != ev["id"] and kd == ev["kind"] and abs(k - cc) <= MATCH_BAND]
                        pos.append({"event": ev["id"], "stratum": ev["stratum"], "kind": ev["kind"], "strict": ev["strict"], "money": hit - cc,
                                    "skill": (hit - cc) - (float(np.mean(bm)) if bm else 0.0), "n_base": len(bm), "cost": cc})
                mid = (lo + hi) / 2; p_side = mid if c["yes"] else 1 - mid; q_side = c["price_yes"] if c["yes"] else 1 - c["price_yes"]
                logs.append({"event": ev["id"], "v": math.log(max(p_side, 1e-9) / max(q_side, A.Q_FLOOR)), "bounded": lo != hi})
                if ev["kind"] in ("partition", "percent"):
                    calib[f"pct_{int(lo * 10) * 10}"].append(float(c["yes"]))
            for key, side, rising in scaled_vars(ev):
                five = ans[lab][key]; oi = outcome_interval(ev, ev["kind"], side)
                if oi is None or five is None:
                    continue
                mm = median_set(market_points(ev, side), increasing=rising); sm = session_median(five, ev)
                gs, gm = gap(sm, oi), gap(mm, oi)
                mags.append({"event": ev["id"], "stratum": ev["stratum"], "kind": ev["kind"], "strict": ev["strict"], "v": float(np.sign(gm - gs))})
                for c_ in CHANCES:                              # calibration: was the stated value reached?
                    v = five.get(c_)
                    if v is None:
                        continue
                    if rising:                                   # dates and low levels: P(at or before v) = c
                        if oi[1] <= v: calib[f"{key}_{c_}"].append(1.0)
                        elif oi[0] >= v: calib[f"{key}_{c_}"].append(0.0)
                    else:                                        # high levels: P(at or above v) = c
                        if oi[0] >= v: calib[f"{key}_{c_}"].append(1.0)
                        elif oi[1] <= v: calib[f"{key}_{c_}"].append(0.0)
                # the T0 baseline: on the session's side of the market's central value, the rungs nearest 0.50, 0.25, 0.10
                sess_hi = sm[0] > mm[1]; sess_lo = sm[1] < mm[0]
                if sess_hi or sess_lo:
                    cand = []
                    for c in ev["contracts"]:
                        x = rung_value(c, ev["kind"])
                        if x is None or (side and S.orient(c["q"]) != side):
                            continue
                        if rising:
                            yes = sess_lo                         # an earlier (or lower) view buys YES on 'by d' / 'dip to k'
                        else:
                            yes = (S.orient(c["q"]) == "up") == sess_hi
                        cand.append((c, yes, c["price_yes"] if yes else 1 - c["price_yes"]))
                    for tgt in (0.50, 0.25, 0.10):
                        if cand:
                            c, yes, q = min(cand, key=lambda z: (abs(z[2] - tgt), z[0]["cid"]))
                            cc = cost(c, yes); hit = float(c["yes"] == yes)
                            bm = [h - k for (eid, kd, k, h) in base if eid != ev["id"] and kd == ev["kind"] and abs(k - cc) <= MATCH_BAND]
                            base_t0.append({"event": ev["id"], "money": hit - cc, "skill": (hit - cc) - (float(np.mean(bm)) if bm else 0.0)})
    def read(rows, key, filt=lambda r: True):
        rs = [r for r in rows if filt(r)]
        return boot([r[key] for r in rs], rng, by=[r["event"] for r in rs]) if rs else None
    out = {"voided": dict(voided), "positions": len(pos), "events_with_positions": len({p["event"] for p in pos}),
           "S1_skill": read(pos, "skill"), "S1_money": read(pos, "money"),
           "S1_skill_strict_window": read(pos, "skill", lambda r: r["strict"]),
           "S2_magnitude": read(mags, "v"), "S2_magnitude_strict_window": read(mags, "v", lambda r: r["strict"]),
           "log_score": read(logs, "v"), "t0_baseline_skill": read(base_t0, "skill"), "t0_baseline_money": read(base_t0, "money"),
           "calibration": {k: {"n": len(v), "share": float(np.mean(v))} for k, v in sorted(calib.items())},
           "by_stratum": {s: {"S1_skill": read(pos, "skill", lambda r, s=s: r["stratum"] == s), "S2": read(mags, "v", lambda r, s=s: r["stratum"] == s)} for s in ("multi", "binary")},
           "by_kind": {k: {"S1_skill": read(pos, "skill", lambda r, k=k: r["kind"] == k), "S2": read(mags, "v", lambda r, k=k: r["kind"] == k)}
                       for k in sorted({p["kind"] for p in pos} | {m["kind"] for m in mags})},
           "magnitude_counts": dict(collections.Counter({1.0: "session closer", -1.0: "market closer", 0.0: "tie"}[m["v"]] for m in mags))}
    A.jdump(dict(out, rows={"positions": pos, "magnitude": mags}), os.path.join(D, "result.json"))
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("frame"); p.add_argument("--start", required=True); p.add_argument("--strict-start")
    sp.add_parser("sessions")
    p = sp.add_parser("publish"); p.add_argument("sid")
    p = sp.add_parser("ingest"); p.add_argument("sid"); p.add_argument("agent_id")
    sp.add_parser("freeze"); sp.add_parser("score")
    a = ap.parse_args()
    {"frame": cmd_frame, "sessions": cmd_sessions, "publish": cmd_publish, "ingest": cmd_ingest, "freeze": cmd_freeze, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
