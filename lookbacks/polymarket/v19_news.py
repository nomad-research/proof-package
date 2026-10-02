"""The reader with news (V19_NEWS_prereg.md): BT-T2 passes 4 and 5 re-read with headlines from the 7 days before each lock.

    python lookbacks/polymarket/v19_news_fetch.py t2_pass5 t2_pass4   # network (GDELT, 5.5 s a request), on a machine with its own address
    python lookbacks/polymarket/v19_news.py sessions t2_pass4      # bt/news/t2_pass4_N/ (each prompt first rebuilt and checked against the frozen pass)
    python lookbacks/polymarket/v19_news.py publish t2_pass4 S01
    python lookbacks/polymarket/v19_news.py ingest t2_pass4 S01 <agent_id>
    python lookbacks/polymarket/v19_news.py freeze t2_pass4
    python lookbacks/polymarket/v19_news.py score                  # no network: v19/news_result.json
"""
import collections, datetime as dt, json, math, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T
import v1_packet as K
import v1_run as V1
import v19_a2 as V
import v19_real_prices as R
import v19_design_sim as DS
import v19_news_fetch as NF
from v19_news_fetch import NEWS, hpath, terms_of
assert NF.LEAK.pattern == K.LEAK.pattern, "the fetch's leak check must be the pipeline's"

PASSES = ("t2_pass4", "t2_pass5"); SEED = 20261016
HEADER_COLD = ("Use only what you already know. Do not search for or look up anything: reading this file is the only tool call you may make. "
               "There are no prices in this file and you should not try to estimate what any market thinks; give your own view.")
HEADER_NEWS = ("Use what you already know and the news headlines listed under each question, all published in the 7 days before its as-of date. "
               "Do not search for or look up anything else: reading this file is the only tool call you may make. "
               "There are no prices from any prediction market in this file and you should not try to estimate what any market thinks; give your own view.")


def ndir(d):
    return os.path.join(NEWS, f"{d}_N")


def prefix(d):
    return "bt2n" + d.replace("t2_pass", "")


def news_block(i, hs):
    if not hs:
        return f"News before E{i}'s as-of date: none found."
    return "\n".join([f"News before E{i}'s as-of date (date seen, source, headline):"] + [f"  - {h['seen']} | {h['source']} | {h['title']}" for h in hs])


def block(i, ev, hs):
    text = T.block(i, ev); anchor = "What to write for E%d:" % i
    assert text.count(anchor) == 1, (i, ev["id"])
    return text.replace(anchor, news_block(i, hs) + "\n" + anchor)


def cmd_sessions(d):
    src = os.path.join(HERE, "bt", d); D = ndir(d); fr = {e["id"]: e for e in A.jload(os.path.join(src, "frame.json"))["events"]}; heads = A.jload(hpath(d))
    assert T.PROMPT.count(HEADER_COLD) == 1
    os.makedirs(os.path.join(D, "sessions"), exist_ok=True); os.makedirs(os.path.join(D, "answers"), exist_ok=True)
    shutil.copyfile(os.path.join(src, "frame.json"), os.path.join(D, "frame.json")); n = 0
    for f in sorted(x for x in os.listdir(os.path.join(src, "sessions")) if x.endswith(".json")):
        sid = f[:-5]; meta = A.jload(os.path.join(src, "sessions", f)); evs = [fr[L["event_id"]] for L in meta["labels"].values()]
        plain = T.PROMPT.format(n=len(evs), body="\n\n".join(T.block(i, ev) for i, ev in enumerate(evs, 1)))
        if plain != open(os.path.join(src, "sessions", f"{sid}.txt"), encoding="utf-8").read():
            raise SystemExit(f"{d}/{sid}: rebuilt prompt differs from the frozen pass")
        body = "\n\n".join(block(i, ev, heads["events"][str(ev["id"])]["headlines"]) for i, ev in enumerate(evs, 1))
        text = T.PROMPT.replace(HEADER_COLD, HEADER_NEWS).format(n=len(evs), body=body)
        if K.leak_flags(text):
            raise SystemExit(f"{d}/{sid}: leak flags {K.leak_flags(text)}")
        open(os.path.join(D, "sessions", f"{sid}.txt"), "w", encoding="utf-8").write(text); n += 1
        A.jdump({"session": sid, "labels": meta["labels"], "prompt_sha256": A.hashlib.sha256(text.encode("utf-8")).hexdigest()}, os.path.join(D, "sessions", f"{sid}.json"))
    print(json.dumps({"pass": d, "sessions": n}))


def cmd_publish(d, sid):
    os.makedirs(A.PROMPT_DIR, exist_ok=True); dst = os.path.join(A.PROMPT_DIR, f"{prefix(d)}_{sid}.txt")
    shutil.copyfile(os.path.join(ndir(d), "sessions", f"{sid}.txt"), dst); print(T.INSTRUCTION_PAGED.format(path=dst))


def zero_to_one(obj):
    """Decision 23: a written 0% counts as 1%; the original answer is kept in 'raw'."""
    n = 0
    for e in (obj.get("events") or []):
        if isinstance(e, dict) and isinstance(e.get("p"), dict):
            for k, v in e["p"].items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0:
                    e["p"][k] = 1; n += 1
    return obj, n


def cmd_ingest(d, sid, agent_id):
    D = ndir(d); meta = A.jload(os.path.join(D, "sessions", f"{sid}.json")); prompt = open(os.path.join(D, "sessions", f"{sid}.txt"), encoding="utf-8").read()
    path = V1.find_transcript(agent_id); dst = os.path.join(A.PROMPT_DIR, f"{prefix(d)}_{sid}.txt")
    au = V1.audit_transcript(path, declared=A.DECLARED_MODEL, allowed_reads={dst: prompt}, expect_instructions=[T.INSTRUCTION_PAGED.format(path=dst)])
    if not au["ok"] and not au["read_content_matches"] and au["prompt_matches_file"] and au["instructions_match"] and not au["tool_calls"] \
            and set(au["models"]) == {A.DECLARED_MODEL} and A.reads_by_line(path, dst, prompt):
        au["ok"], au["read_content_matches"], au["read_check"] = True, True, "line-number reconstruction (BT-A addendum A2; BT-T2 pass 2 addendum A1)"
    errs, ans, raw, zeros = [], None, None, 0
    try:
        raw = V1.extract_json(V1.final_answer(agent_id)); obj, zeros = zero_to_one(json.loads(json.dumps(raw)))
        ans, errs = T.validate(obj, meta["labels"])
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    rec = {"session": sid, "agent_id": agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "raw": raw, "zeros_counted_as_1": zeros,
           "prompt_sha256": meta["prompt_sha256"], "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    A.jdump(rec, os.path.join(D, "answers", f"{sid}.json"))
    print(json.dumps({"pass": d, "session": sid, "status": status, "errors": errs[:4], "zeros": zeros, "audit_ok": au["ok"], "models": au["models"]}))


def cmd_freeze(d):
    D = ndir(d); rows = {}
    for f in sorted(os.listdir(os.path.join(D, "answers"))):
        r = A.jload(os.path.join(D, "answers", f)); rows[r["session"]] = {"status": r["status"], "answers_sha256": A.sha(r["answers"]), "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "frame_sha256": A.sha(A.jload(os.path.join(D, "frame.json"))["events"]), "sessions": rows}
    man["manifest_sha256"] = A.sha(man); A.jdump(man, os.path.join(D, "manifest.json")); print(json.dumps({"pass": d, "sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


# ---------------------------------------------------------------- scoring
def readings(d, news):
    """{(event id, label): answer} from a frozen reading, with each answer's hash checked."""
    D = ndir(d) if news else os.path.join(HERE, "bt", d); man = A.jload(os.path.join(D, "manifest.json")); out = {}
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(D, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{D}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            out[L["event_id"]] = ans[lab]
    return out


def diff(a, b, key, rng):
    """Mean of a minus mean of b, resampling occasions jointly."""
    occ = sorted({r["occ"] for r in a + b}); ga, gb = collections.defaultdict(list), collections.defaultdict(list)
    for r in a:
        ga[r["occ"]].append(r[key])
    for r in b:
        gb[r["occ"]].append(r[key])
    ds = []
    for _ in range(4000):
        s = [occ[i] for i in rng.integers(0, len(occ), len(occ))]; x = [v for o in s for v in ga[o]]; y = [v for o in s for v in gb[o]]
        if x and y:
            ds.append(np.mean(x) - np.mean(y))
    if not a or not b:
        return None
    return {"point": float(np.mean([r[key] for r in a]) - np.mean([r[key] for r in b])), "ci95": [float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))],
            "n_news": len(a), "n_cold": len(b), "occasions": len(occ)}


def verdict(ci, up="edge shown with news", down="shown absent with news"):
    return up if ci[0] > 0 else down if ci[1] < 0 else "direction only"


def logs(d, news):
    """Per contract with a real price: log(reader's chance of what happened / real price of what happened), as bt_t2's log score."""
    D = ndir(d) if news else os.path.join(HERE, "bt", d); fdoc = A.jload(os.path.join(HERE, "bt", d, "frame.json"))
    crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}; got = R.load(d); frame = {e["id"]: e for e in fdoc["events"]}
    man = A.jload(os.path.join(D, "manifest.json")); out = []
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(D, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{D}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"]:
                continue
            mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}; byc = {c["cid"]: c for c in ev["contracts"]}
            for cl, cid in L["contracts"].items():
                c = byc[cid]; q = R.real_yes(got.get(f"{cid}|{ev['lock']}"), ev["lock"]); ch = T.contract_chance(ev, ans, lab, cl, c)
                if q is None or ch is None:
                    continue
                y = A.yes_won(mk[cid]); mid = sum(ch) / 2; p_side = mid if y else 1 - mid; q_side = q if y else 1 - q
                out.append({"event": f"{d}/{ev['id']}", "v": math.log(max(p_side, 1e-9) / max(q_side, A.Q_FLOOR)), "hit": 0.0,
                            "subject": V.subject_of(ev), "end": V.scheduled_end(ev)})
    return out


def location(d, rng_unused=None):
    """Per ladder, touch and date side: +1 if the news reading's median lands closer to what happened than the cold reading's, -1 if farther, 0 if tied."""
    fdoc = A.jload(os.path.join(HERE, "bt", d, "frame.json")); crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}
    cold, news = readings(d, False), readings(d, True); out = []
    for ev in fdoc["events"]:
        if ev["id"] not in cold or ev["id"] not in news or cold[ev["id"]]["recognised"] or news[ev["id"]]["recognised"]:
            continue
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
        for key, side, rising in T.scaled_vars(ev):
            fc, fn = cold[ev["id"]].get(key), news[ev["id"]].get(key); oi = T.outcome_interval(ev, ev["kind"], side)
            if fc is None or fn is None or oi is None:
                continue
            gc, gn = T.gap(T.session_median(fc, ev), oi), T.gap(T.session_median(fn, ev), oi)
            out.append({"event": f"{d}/{ev['id']}", "v": float(np.sign(gc - gn)), "subject": V.subject_of(ev), "end": V.scheduled_end(ev), "hit": 0.0})
    return out


def cmd_score():
    rng = np.random.default_rng(SEED); cold, news = [], []
    for d in PASSES:
        rs, _ = R.t2_rows(d, "last", 0.0); cold += [dict(r, reading="cold") for r in rs if "event" in r]
        rs, _ = R.t2_rows(os.path.relpath(ndir(d), os.path.join(HERE, "bt")), "last", 0.0, src=d)
        news += [dict(r, reading="news", event=f"{d}/{r['event'].rsplit('/', 1)[1]}", pass_=d) for r in rs if "event" in r]   # the source pass's event key
    V.assign_occasions(cold + news)                           # one occasion map across both readings and both passes
    nE1 = [r for r in news if r["side"] == "NO"]; cE1 = [r for r in cold if r["side"] == "NO"]
    nA2 = [r for r in news if r["armed"]]; cA2 = [r for r in cold if r["armed"]]
    s1, s2, s3 = R.read(nE1, "skill_side", rng), R.read(nA2, "skill_side", rng), diff(nE1, cE1, "skill_side", rng)
    loc = [x for d in PASSES for x in location(d)]; V.assign_occasions(loc)
    heads = {d: A.jload(hpath(d)) for d in PASSES}
    lc, ln = [x for d in PASSES for x in logs(d, False)], [x for d in PASSES for x in logs(d, True)]; V.assign_occasions(lc + ln)
    a3 = lambda rs: {"any_prior": DS.a3([dict(kind=r["mtype"], lock=r["lock"], event=r["event"], skill=r["skill_side"]) for r in rs], 1),
                     "at_least_5_prior_events": DS.a3([dict(kind=r["mtype"], lock=r["lock"], event=r["event"], skill=r["skill_side"]) for r in rs], 5)}
    out = {"declared_1_E1_with_news": dict(s1, reading=verdict(s1["ci95"])) if s1 else None,
           "declared_2_A2_with_news": dict(s2, reading=verdict(s2["ci95"])) if s2 else None,
           "declared_3_news_minus_cold_E1": dict(s3, reading=verdict(s3["ci95"], "news helps", "news hurts")) if s3 else None,
           "secondary": {
               "E1_cold_same_events": R.read(cE1, "skill_side", rng), "A2_cold_same_events": R.read(cA2, "skill_side", rng),
               "news_minus_cold_A2": diff(nA2, cA2, "skill_side", rng),
               "log_score": {"news": R.read(ln, "v", rng), "cold": R.read(lc, "v", rng), "news_minus_cold": diff(ln, lc, "v", rng)},
               "A3_on_news_readings": a3(nA2),
               "E1_money_news": R.read(nE1, "money", rng), "E1_money_cold": R.read(cE1, "money", rng),
               "A2_money_news": R.read(nA2, "money", rng), "A2_money_cold": R.read(cA2, "money", rng),
               "location_news_closer_share": {"n": len(loc), "mean_sign": R.read(loc, "v", rng) if loc else None,
                                              "closer": sum(1 for x in loc if x["v"] > 0), "farther": sum(1 for x in loc if x["v"] < 0), "tied": sum(1 for x in loc if x["v"] == 0)},
               "E1_news_by_kind": {k: R.read([r for r in nE1 if r["kind"] == k], "skill_side", rng) for k in sorted({r["kind"] for r in nE1})},
               "E1_cold_by_kind": {k: R.read([r for r in cE1 if r["kind"] == k], "skill_side", rng) for k in sorted({r["kind"] for r in cE1})},
               "A2_news_pick_the_winner_vs_rest": {"partition": R.read([r for r in nA2 if r["kind"] == "partition"], "skill_side", rng),
                                                   "rest": R.read([r for r in nA2 if r["kind"] != "partition"], "skill_side", rng)},
               "A2_news_p5_conditions": {
                   "conviction_under_10": R.read([r for r in nA2 if r["mid"] < 0.10], "skill_side", rng),
                   "conviction_10_up": R.read([r for r in nA2 if r["mid"] >= 0.10], "skill_side", rng),
                   "timing_3_days_up": R.read([r for r in nA2 if (r["end"] - r["lock"]) / 86400 >= 3], "skill_side", rng),
                   "timing_under_3_days": R.read([r for r in nA2 if (r["end"] - r["lock"]) / 86400 < 3], "skill_side", rng),
                   "shape_not_touch": R.read([r for r in nA2 if r["kind"] != "touch"], "skill_side", rng),
                   "touch": R.read([r for r in nA2 if r["kind"] == "touch"], "skill_side", rng)},
               "strict_window_from_1_june": {"E1_news": R.read([r for r in nE1 if r["lock"] >= 1780272000], "skill_side", rng),
                                             "E1_cold": R.read([r for r in cE1 if r["lock"] >= 1780272000], "skill_side", rng),
                                             "news_minus_cold_E1": diff([r for r in nE1 if r["lock"] >= 1780272000], [r for r in cE1 if r["lock"] >= 1780272000], "skill_side", rng)},
               "headline_coverage": {d: {"events": len(h["events"]), "requests": len(h["requests"]), "none_found": sum(1 for v in h["events"].values() if not v["headlines"]),
                                         "median_headlines": float(np.median([len(v["headlines"]) for v in h["events"].values()]))} for d, h in heads.items()},
               "recognised": {"news": sum(1 for d in PASSES for a in readings(d, True).values() if a["recognised"]),
                              "cold": sum(1 for d in PASSES for a in readings(d, False).values() if a["recognised"])}}}
    A.jdump(out, os.path.join(HERE, "v19", "news_result.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"sessions": lambda: cmd_sessions(a[1]), "publish": lambda: cmd_publish(a[1], a[2]),
     "ingest": lambda: cmd_ingest(a[1], a[2], a[3]), "freeze": lambda: cmd_freeze(a[1]), "score": lambda: cmd_score()}[a[0]]()
