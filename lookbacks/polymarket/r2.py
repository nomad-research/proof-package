"""R2: asking "will this not happen" (V19_DESIGN_TESTS_prereg.md §5). Reading D of BT-T2 pass 3's 25 prompts, with half of the percent and
partition events asked in reverse (key p_not, converted to YES = 100 - p_not). Everything else is pass 3's prompt word for word.

    python lookbacks/polymarket/r2.py sessions                 # writes bt/r2/t2_pass3_D/sessions (checks that unreversed blocks match pass 3)
    python lookbacks/polymarket/r2.py publish S01
    python lookbacks/polymarket/r2.py ingest S01 <agent_id>
    python lookbacks/polymarket/r2.py freeze
    python lookbacks/polymarket/r2.py score                    # no network
"""
import collections, datetime as dt, json, math, os, random, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T
import v1_packet as K
import v1_run as V
import r1

SRC = os.path.join(HERE, "bt", "t2_pass3"); D = os.path.join(HERE, "bt", "r2", "t2_pass3_D"); PREFIX = "bt2r2p3D"; SEED = 20261013
ASK_NOT = {"percent": 'Write "p_not": a whole percent for every contract label, your chance that it does NOT resolve YES.',
           "partition": 'Write "p_not": a whole percent for every contract label, your chance that it is NOT the one that resolves YES. These need not add to any total.'}


def reversed_events(frame):
    elig = sorted(e["id"] for e in frame if e["kind"] in ASK_NOT)
    random.Random(SEED).shuffle(elig)
    return set(elig[: len(elig) // 2])


def block(i, ev, rev):
    text = T.block(i, ev)
    if rev:
        old = "What to write for E%d:\n  %s" % (i, T.ASK[ev["kind"]])
        assert old in text, (i, ev["id"])
        text = text.replace(old, "What to write for E%d:\n  %s" % (i, ASK_NOT[ev["kind"]]))
    return text


def cmd_sessions():
    fr = {e["id"]: e for e in A.jload(os.path.join(SRC, "frame.json"))["events"]}; rev = reversed_events(fr.values())
    os.makedirs(os.path.join(D, "sessions"), exist_ok=True); os.makedirs(os.path.join(D, "answers"), exist_ok=True)
    shutil.copyfile(os.path.join(SRC, "frame.json"), os.path.join(D, "frame.json")); n_rev = 0
    for f in sorted(x for x in os.listdir(os.path.join(SRC, "sessions")) if x.endswith(".json")):
        sid = f[:-5]; meta = A.jload(os.path.join(SRC, "sessions", f)); evs = [fr[L["event_id"]] for L in meta["labels"].values()]
        plain = T.PROMPT.format(n=len(evs), body="\n\n".join(block(i, ev, False) for i, ev in enumerate(evs, 1)))
        if plain != open(os.path.join(SRC, "sessions", f"{sid}.txt"), encoding="utf-8").read():
            raise SystemExit(f"{sid}: rebuilt prompt differs from pass 3's")
        text = T.PROMPT.format(n=len(evs), body="\n\n".join(block(i, ev, ev["id"] in rev) for i, ev in enumerate(evs, 1)))
        if K.leak_flags(text):
            raise SystemExit(f"{sid}: leak flags {K.leak_flags(text)}")
        r = [lab for lab, L in meta["labels"].items() if L["event_id"] in rev]; n_rev += len(r)
        open(os.path.join(D, "sessions", f"{sid}.txt"), "w", encoding="utf-8").write(text)
        A.jdump({"session": sid, "labels": meta["labels"], "reversed": r, "prompt_sha256": A.hashlib.sha256(text.encode("utf-8")).hexdigest()},
                os.path.join(D, "sessions", f"{sid}.json"))
    print(json.dumps({"sessions": 25, "reversed_events": n_rev, "eligible": len([e for e in fr.values() if e["kind"] in ASK_NOT])}))


def cmd_publish(sid):
    os.makedirs(A.PROMPT_DIR, exist_ok=True); dst = os.path.join(A.PROMPT_DIR, f"{PREFIX}_{sid}.txt")
    shutil.copyfile(os.path.join(D, "sessions", f"{sid}.txt"), dst); print(T.INSTRUCTION_PAGED.format(path=dst))


def convert(obj, reversed_labels):
    """p_not -> p (100 - p_not) on reversed events; a reversed event answered with p, or an unreversed one with p_not, is an error."""
    errs = []
    for e in (obj.get("events") or []):
        if not isinstance(e, dict):
            continue
        if e.get("label") in reversed_labels:
            pn = e.pop("p_not", None)
            if not isinstance(pn, dict):
                errs.append(f"{e.get('label')}: no p_not"); continue
            e["p"] = {cl: (100 - v if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for cl, v in pn.items()}
        elif "p_not" in e:
            errs.append(f"{e.get('label')}: p_not where p was asked")
    return obj, errs


def cmd_ingest(sid, agent_id):
    meta = A.jload(os.path.join(D, "sessions", f"{sid}.json")); prompt = open(os.path.join(D, "sessions", f"{sid}.txt"), encoding="utf-8").read()
    path = V.find_transcript(agent_id); dst = os.path.join(A.PROMPT_DIR, f"{PREFIX}_{sid}.txt")
    au = V.audit_transcript(path, declared=A.DECLARED_MODEL, allowed_reads={dst: prompt}, expect_instructions=[T.INSTRUCTION_PAGED.format(path=dst)])
    if not au["ok"] and not au["read_content_matches"] and au["prompt_matches_file"] and au["instructions_match"] and not au["tool_calls"] \
            and set(au["models"]) == {A.DECLARED_MODEL} and A.reads_by_line(path, dst, prompt):
        au["ok"], au["read_content_matches"], au["read_check"] = True, True, "line-number reconstruction (BT-A addendum A2; BT-T2 pass 2 addendum A1)"
    errs, ans, raw = [], None, None
    try:
        raw = V.extract_json(V.final_answer(agent_id)); obj, errs = convert(json.loads(json.dumps(raw)), set(meta["reversed"]))
        ans, e2 = T.validate(obj, meta["labels"]); errs += e2
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    rec = {"session": sid, "agent_id": agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "raw": raw, "reversed": meta["reversed"],
           "prompt_sha256": meta["prompt_sha256"], "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    A.jdump(rec, os.path.join(D, "answers", f"{sid}.json"))
    print(json.dumps({"session": sid, "status": status, "errors": errs[:6], "audit_ok": au["ok"], "tool_calls": au["tool_calls"], "models": au["models"]}))


def cmd_freeze():
    rows = {}
    for f in sorted(os.listdir(os.path.join(D, "answers"))):
        r = A.jload(os.path.join(D, "answers", f)); rows[r["session"]] = {"status": r["status"], "answers_sha256": A.sha(r["answers"]), "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "frame_sha256": A.sha(A.jload(os.path.join(D, "frame.json"))["events"]), "sessions": rows}
    man["manifest_sha256"] = A.sha(man); A.jdump(man, os.path.join(D, "manifest.json")); print(json.dumps({"sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


def cmd_score():
    fdoc = A.jload(os.path.join(SRC, "frame.json")); crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}; frame = fdoc["events"]
    for ev in frame:
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
    rev = reversed_events(frame)
    base_side = [(ev["id"], ev["kind"], yes, T.cost(c, yes), float(c["yes"] == yes)) for ev in frame for c in ev["contracts"] for yes in (True, False)]
    loaded = {"B": r1.load_reading(r1.READINGS["B"]), "C": r1.load_reading(r1.READINGS["C"]), "D": r1.load_reading(D)}
    skip = set().union(*[r for _, r in loaded.values()]); views = {k: v for k, (v, _) in loaded.items()}
    out = {"reversed_events": len(rev)}
    for part, keep in (("reversed", rev), ("control (not reversed)", {e["id"] for e in frame} - rev)):
        sub = [e for e in frame if e["id"] in keep]
        arm = {k: r1.armed(r1.positions(views[k], sub, base_side, skip)) for k in views}
        rng = np.random.default_rng(SEED)
        md, mb, mc = r1.boot_mean([r1.byev(arm["D"], "skill_side"), r1.byev(arm["B"], "skill_side"), r1.byev(arm["C"], "skill_side")], rng)
        diff = md - (mb + mc) / 2; s = r1.summary(diff)
        mean = lambda rs: float(np.mean([r["skill_side"] for r in rs])) if rs else float("nan")
        logs = {k: r1.log_score(views[k], sub, skip) for k in views}
        ml = r1.boot_mean([r1.byev(logs["D"], "v"), r1.byev(logs["B"], "v"), r1.byev(logs["C"], "v")], rng)
        hi = {}
        for k in views:
            xs = [float(c["yes"]) for ev in sub if ev["id"] not in skip for c in ev["contracts"]
                  if (ev["id"], c["cid"]) in views[k] and 0.85 <= sum(views[k][(ev["id"], c["cid"])]) / 2 < 0.95]
            hi[k] = {"n": len(xs), "happened": float(np.mean(xs)) if xs else None}
        out[part] = {"armed_skill_D_minus_mean_BC": {"point": mean(arm["D"]) - (mean(arm["B"]) + mean(arm["C"])) / 2, **s,
                                                   "reading": ("edge shown (framing sharpens)" if s["ci95"][0] > 0 else "shown absent (framing blunts)" if s["ci95"][1] < 0 else "direction only")},
                     "armed": {k: {"positions": len(a), "events": len({r["event"] for r in a}), "skill": mean(a)} for k, a in arm.items()},
                     "log_score_D_minus_mean_BC": r1.summary(ml[0] - (ml[1] + ml[2]) / 2),
                     "log_score": {k: float(np.mean([x["v"] for x in logs[k]])) for k in views},
                     "said_85_to_95_happened": hi}
    A.jdump(out, os.path.join(HERE, "bt", "r2", "result.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"sessions": lambda: cmd_sessions(), "publish": lambda: cmd_publish(a[1]), "ingest": lambda: cmd_ingest(a[1], a[2]),
     "freeze": lambda: cmd_freeze(), "score": lambda: cmd_score()}[a[0]]()
