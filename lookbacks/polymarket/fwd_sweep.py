"""Forward sweep (FORWARD_SWEEP_prereg.md): E1 and E3 forward, cold and price-blind, one batch a week.

    python lookbacks/polymarket/fwd_sweep.py snapshot W01            # network: open events ending within 14 days, scoped; writes sweep/W01/open_<stamp>.json.gz
    python lookbacks/polymarket/fwd_sweep.py frame W01               # eligibility and the draw: every mention event, then others at random to 102
    python lookbacks/polymarket/fwd_sweep.py sessions W01            # 6 events a session, BT-T2's cold prompt
    python lookbacks/polymarket/fwd_sweep.py publish W01 S01
    python lookbacks/polymarket/fwd_sweep.py ingest W01 S01 <agent_id>   # BT-T2's audit, validation, then the lock asks read at once (with depth)
    python lookbacks/polymarket/fwd_sweep.py freeze W01              # answers and lock asks into sweep/W01/manifest.json, committed at once
    python lookbacks/polymarket/fwd_sweep.py score                   # every frozen batch: what has resolved (Gamma re-read), E1 and E3 at their looks
"""
import argparse, collections, concurrent.futures, datetime as dt, gzip, hashlib, json, math, os, random, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import numpy as np
import bt_audit as A
import bt_crawl as BC
import bt_t2 as T
import t3
import v1_run as V
from nomad16 import exact as X

D = os.path.join(HERE, "sweep")
HORIZON_D, N_EVENTS, PER_SESSION = 14, 102, 6
MENTION = re.compile(r"\bsay\b|\bmention", re.I)                # E3's rule, word for word
LOOKS = {"E1": (400, 800), "E3": (50, 130)}                     # resolved events with a NO position (§2)
MATCH_BAND, SEED = 0.05, 20261006


def bdir(b):
    return os.path.join(D, b)


def cmd_snapshot(a):
    t0 = t3.now_ts(); BC.VOLUME_MIN, BC.SCOPE = 10000.0, True; out, log = {}, []
    a_ = dt.datetime.fromtimestamp(t0, dt.timezone.utc); b_ = a_ + dt.timedelta(days=HORIZON_D); t = a_
    while t < b_:
        u = min(t + dt.timedelta(days=3), b_); t3.crawl_open(t, u, out, log); t = u
    low, t = {}, a_                                              # addendum A1: mention events at any volume so far
    while t < b_:
        u = min(t + dt.timedelta(days=3), b_); crawl_mentions(t, u, low); t = u
    for k, e in low.items():
        if k not in out:
            out[k] = dict(e, low_volume_at_snapshot=True)
    os.makedirs(bdir(a.batch), exist_ok=True)
    rows = sorted(out.values(), key=lambda e: e["id"]); blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    name = f"open_{a_.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.GzipFile(os.path.join(bdir(a.batch), name), "wb", mtime=0) as fh:
        fh.write(blob)
    snap = {"batch": a.batch, "taken_at": t0, "as_of": a_.strftime("%Y-%m-%d"), "file": name, "events": len(rows), "sha256_of_json": hashlib.sha256(blob).hexdigest(),
            "dropped": BC.DROPPED, "windows": log}
    A.jdump(snap, os.path.join(bdir(a.batch), "snapshot.json")); print(json.dumps({k: v for k, v in snap.items() if k != "windows"}))


def mention_in_scope(e):
    """Addendum A3: a mention event whose only out-of-scope tag is 'pop-culture' is kept when it carries 'politics'."""
    tags = {t.get("slug") for t in (e.get("tags") or [])}
    if (tags & BC.EXCL) == {"pop-culture"} and "politics" in tags:
        return True
    return BC.in_scope(e)


def crawl_mentions(a, b, out):
    off = 0
    while True:
        p = BC.get(f"{BC.GAMMA}?closed=false&tag_slug=mention-markets&end_date_min={BC.iso(a)}&end_date_max={BC.iso(b)}&order=endDate&ascending=true"
                   f"&limit={BC.PAGE}&offset={off}")                      # addendum A2: found by Gamma's tag, since a date-window crawl stops at the cap
        for e in p:
            if MENTION.search(e.get("title") or "") and mention_in_scope(e) and str(e["id"]) not in out:
                c = BC.compact(e)
                for m, raw in zip(c["markets"], e.get("markets") or []):
                    m["closed"] = bool(raw.get("closed"))
                out[str(e["id"])] = c
        if len(p) < BC.PAGE or off + BC.PAGE >= BC.CAP:
            return
        off += BC.PAGE; time.sleep(0.2)


def taken_elsewhere(batch):
    """Events in T3's sessions (dependent, scored there) and in earlier sweep batches."""
    ids = set()
    sd = os.path.join(HERE, "t3", "sessions")
    for f in os.listdir(sd):
        if f.endswith(".json"):
            ids |= {r["id"] for r in A.jload(os.path.join(sd, f))["events"]}
    t3_ids = set(ids)
    for b in sorted(os.listdir(D)) if os.path.isdir(D) else []:
        p = os.path.join(bdir(b), "frame.json")
        if b != batch and os.path.exists(p):
            ids |= {e["id"] for e in A.jload(p)["events"]}
    return ids, t3_ids


def cmd_frame(a):
    snap = A.jload(os.path.join(bdir(a.batch), "snapshot.json")); evs = A.jload(os.path.join(bdir(a.batch), snap["file"])); t0 = snap["taken_at"]
    taken, t3_ids = taken_elsewhere(a.batch); tally = collections.Counter(); mention, other = [], []
    for e in evs:
        if e["id"] in taken:
            tally["t3" if e["id"] in t3_ids else "earlier_batch"] += 1; continue
        if A.MAKER.search(A.text_of(e) + " " + " ".join(e["tags"])):
            tally["maker_excluded"] += 1; continue
        ms = t3.open_markets(e, t0)
        if not ms:
            tally["no_open_market"] += 1; continue
        if max(A.ts(m["end"]) for m in ms) > t0 + HORIZON_D * 86400:
            tally["ends_after_horizon"] += 1; continue
        r = t3.event_record(e, t0); r["as_of"] = snap["as_of"]; r["mention"] = bool(MENTION.search(e.get("title") or ""))
        r["volume_at_snapshot"], r["low_volume_at_snapshot"] = e.get("volume"), bool(e.get("low_volume_at_snapshot"))
        (mention if r["mention"] else other).append(r)
    rng = random.Random(f"{SEED}:{a.batch}"); other = sorted(other, key=lambda r: r["id"]); rng.shuffle(other)
    draw = sorted(mention, key=lambda r: r["id"]) + other[:max(0, N_EVENTS - len(mention))]
    tally.update({"eligible_mention": len(mention), "eligible_other": len(other), "drawn": len(draw)})
    A.jdump({"batch": a.batch, "snapshot": snap["file"], "snapshot_sha256": snap["sha256_of_json"], "tally": dict(tally), "events": draw},
            os.path.join(bdir(a.batch), "frame.json"))
    print(json.dumps({"events": len(draw), "frame_sha256": A.sha(draw), "tally": dict(tally)}))


def cmd_sessions(a):
    fr = A.jload(os.path.join(bdir(a.batch), "frame.json"))["events"]
    evs = sorted(fr, key=lambda e: e["id"]); random.Random(f"{SEED}:{a.batch}:sessions").shuffle(evs)
    sd = os.path.join(bdir(a.batch), "sessions"); os.makedirs(sd, exist_ok=True)
    for s in range(0, len(evs), PER_SESSION):
        chunk = evs[s:s + PER_SESSION]; sid = f"S{s // PER_SESSION + 1:02d}"
        labels = {f"E{i}": {"event_id": ev["id"], "kind": ev["kind"], "sides": T.sides(ev) if ev["kind"] == "touch" else None,
                            "contracts": {f"E{i}.C{j}": c["cid"] for j, c in enumerate(ev["contracts"], 1)}} for i, ev in enumerate(chunk, 1)}
        text = T.PROMPT.format(n=len(chunk), body="\n\n".join(T.block(i, ev) for i, ev in enumerate(chunk, 1)))
        with open(os.path.join(sd, f"{sid}.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        A.jdump({"session": sid, "labels": labels, "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}, os.path.join(sd, f"{sid}.json"))
    print(json.dumps({"sessions": (len(evs) + PER_SESSION - 1) // PER_SESSION, "events": len(evs)}))


def prompt_path(batch, sid):
    return os.path.join(A.PROMPT_DIR, f"fw{batch}_{sid}.txt")


def cmd_publish(a):
    os.makedirs(A.PROMPT_DIR, exist_ok=True); dst = prompt_path(a.batch, a.sid)
    shutil.copyfile(os.path.join(bdir(a.batch), "sessions", f"{a.sid}.txt"), dst); print(T.INSTRUCTION_PAGED.format(path=dst))


def cmd_ingest(a):
    sd = os.path.join(bdir(a.batch), "sessions"); meta = A.jload(os.path.join(sd, f"{a.sid}.json"))
    prompt = open(os.path.join(sd, f"{a.sid}.txt"), encoding="utf-8").read(); dst = prompt_path(a.batch, a.sid); path = V.find_transcript(a.agent_id)
    au = V.audit_transcript(path, declared=A.DECLARED_MODEL, allowed_reads={dst: prompt}, expect_instructions=[T.INSTRUCTION_PAGED.format(path=dst)])
    if not au["ok"] and not au["read_content_matches"] and au["prompt_matches_file"] and au["instructions_match"] and not au["tool_calls"] \
            and set(au["models"]) == {A.DECLARED_MODEL} and A.reads_by_line(path, dst, prompt):
        au["ok"], au["read_content_matches"], au["read_check"] = True, True, "line-number reconstruction (BT-A addendum A2)"
    errs, ans = [], None
    try:
        ans, errs = T.validate(V.extract_json(V.final_answer(a.agent_id)), meta["labels"])
    except Exception as ex:
        errs = [repr(ex)]
    status = "void_audit" if not au["ok"] else ("invalid" if errs else "ok")
    lock = t3.now_ts(); prices = {}
    if status == "ok":                                          # the lock is the hand-back: asks are read now, after the answer exists
        fr = {e["id"]: e for e in A.jload(os.path.join(bdir(a.batch), "frame.json"))["events"]}
        cs = [c for L in meta["labels"].values() for c in fr[L["event_id"]]["contracts"]]
        toks = [t for c in cs for t in (c["token_yes"], c.get("token_no")) if t]
        with concurrent.futures.ThreadPoolExecutor(16) as ex:     # read every book at once, so the lock price sits close to the hand-back
            got = dict(zip(toks, ex.map(t3.book_ask, toks)))
        for c in cs:
            prices[c["cid"]] = {"ask_yes": got.get(c["token_yes"]), "ask_no": got.get(c["token_no"]) if c.get("token_no") else None}
    rec = {"session": a.sid, "agent_id": a.agent_id, "status": status, "errors": errs, "audit": au, "answers": ans, "lock": lock, "lock_prices": prices,
           "prompt_sha256": meta["prompt_sha256"], "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    os.makedirs(os.path.join(bdir(a.batch), "answers"), exist_ok=True); A.jdump(rec, os.path.join(bdir(a.batch), "answers", f"{a.sid}.json"))
    print(json.dumps({"session": a.sid, "status": status, "errors": errs[:6], "audit_ok": au["ok"], "tool_calls": au["tool_calls"], "priced": len(prices)}))


def cmd_freeze(a):
    rows = {}
    ad = os.path.join(bdir(a.batch), "answers")
    for f in sorted(os.listdir(ad)):
        r = A.jload(os.path.join(ad, f))
        rows[r["session"]] = {"status": r["status"], "answers_sha256": A.sha(r["answers"]), "lock": r["lock"], "lock_prices_sha256": A.sha(r["lock_prices"]),
                              "transcript_sha256": r["audit"]["transcript_sha256"]}
    man = {"batch": a.batch, "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(), "frame_sha256": A.sha(A.jload(os.path.join(bdir(a.batch), "frame.json"))["events"]),
           "sessions": rows}
    man["manifest_sha256"] = A.sha(man); A.jdump(man, os.path.join(bdir(a.batch), "manifest.json"))
    print(json.dumps({"batch": a.batch, "sessions": len(rows), "manifest_sha256": man["manifest_sha256"]}))


# ---------------------------------------------------------------- scoring (§2, §3)
def outcomes(eid):
    """({cid: (yes_won, closed_ts)} for the event's markets that have resolved cleanly, lifetime volume), re-read from Gamma now."""
    try:
        e = BC.compact(BC.get(f"{BC.GAMMA}/{eid}"))
    except Exception:
        return {}, None
    out = {}
    for m in e["markets"]:
        w = A.yes_won(m)
        if m.get("uma") == "resolved" and w is not None and "disputed" not in json.dumps(m.get("uma_all") or "").lower():
            out[m["cid"]] = (w, A.ts(m.get("closed_time")))
    return out, e.get("volume")


def ask_cost(c, side_ask):
    return X.share_cost(side_ask["ask"], c.get("fee"), 0.0, float(c["tick"]) if c.get("tick") else None)


def cmd_score(a):
    rows, contracts, logs = [], [], []
    for b in sorted(os.listdir(D)):
        mp = os.path.join(bdir(b), "manifest.json")
        if not os.path.exists(mp):
            continue
        man = A.jload(mp); fr = {e["id"]: e for e in A.jload(os.path.join(bdir(b), "frame.json"))["events"]}
        for sid, row in man["sessions"].items():
            rec = A.jload(os.path.join(bdir(b), "answers", f"{sid}.json"))
            if A.sha(rec["answers"]) != row["answers_sha256"] or A.sha(rec["lock_prices"]) != row["lock_prices_sha256"]:
                raise SystemExit(f"{b}/{sid} changed after the freeze")
            if row["status"] != "ok":
                continue
            ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(bdir(b), "sessions", f"{sid}.json"))["labels"]
            for lab, L in labels.items():
                ev = fr[L["event_id"]]; res, vol = outcomes(ev["id"]); byc = {c["cid"]: c for c in ev["contracts"]}
                counts = not ev.get("low_volume_at_snapshot") or (vol or 0) >= 10000          # addendum A1
                for cl, cid in L["contracts"].items():
                    c = byc[cid]; lp = rec["lock_prices"].get(cid) or {}
                    if cid not in res or (res[cid][1] and res[cid][1] <= rec["lock"]):
                        continue                                 # unresolved, or closed before the lock
                    won = res[cid][0]
                    for yes in (True, False):
                        sa = lp.get("ask_yes" if yes else "ask_no")
                        if sa:
                            contracts.append({"batch": b, "event": ev["id"], "kind": ev["kind"], "mention": ev["mention"], "yes": yes, "counts": counts,
                                              "cost": ask_cost(c, sa), "hit": float(won == yes)})
                    ch = T.contract_chance(ev, ans, lab, cl, c)            # the session's view needs no price
                    if ch is None:
                        continue
                    lo, hi = ch
                    if lp.get("ask_yes") and lp.get("ask_no"):           # the log score against the midpoint of the two asks (§3)
                        q = (lp["ask_yes"]["ask"] + 1 - lp["ask_no"]["ask"]) / 2; m = (lo + hi) / 2
                        logs.append({"event": ev["id"], "v": math.log(max(m if won else 1 - m, 1e-9) / max(q if won else 1 - q, A.Q_FLOOR))})
                    for yes, want in ((True, lo), (False, 1 - hi)):
                        sa = lp.get("ask_yes" if yes else "ask_no")
                        if not sa:
                            continue
                        k = ask_cost(c, sa)
                        if want > k:
                            t = (ev.get("title") or "").lower()
                            rows.append({"batch": b, "event": ev["id"], "kind": ev["kind"], "mention": ev["mention"], "side": "YES" if yes else "NO", "counts": counts,
                                         "cost": k, "hit": float(won == yes), "money": float(won == yes) - k, "usd_2c": sa.get("usd_2c"),
                                         "speaker": "Trump" if "trump" in t else "earnings call" if "earnings call" in t else "other"})
    for r in rows:
        same = lambda x: x["counts"] and x["event"] != r["event"] and x["kind"] == r["kind"] and x["yes"] == (r["side"] == "YES") and abs(x["cost"] - r["cost"]) <= MATCH_BAND
        bs = [x["hit"] - x["cost"] for x in contracts if same(x)]
        bm = [x["hit"] - x["cost"] for x in contracts if same(x) and x["mention"]]
        r["skill"] = r["money"] - (float(np.mean(bs)) if bs else 0.0); r["skill_mention"] = r["money"] - (float(np.mean(bm)) if bm else 0.0)
        both = [x["hit"] - x["cost"] for x in contracts if x["counts"] and x["mention"] and x["event"] != r["event"] and x["kind"] == r["kind"]
                and abs(x["cost"] - r["cost"]) <= MATCH_BAND]                                    # addendum A3: E3b, both sides
        r["skill_mention_both"] = r["money"] - (float(np.mean(both)) if both else 0.0)
        r["money_150"] = (min(150.0, r["usd_2c"]) / r["cost"]) * r["money"] if r.get("usd_2c") else None
    rng = np.random.default_rng(SEED)

    def read(rs, key, level):
        rs = [r for r in rs if r.get(key) is not None]
        if not rs:
            return None
        x = np.array([r[key] for r in rs]); ev = [r["event"] for r in rs]; byev = collections.defaultdict(list)
        for v, e in zip(x, ev):
            byev[e].append(v)
        keys = list(byev); ms = []
        for _ in range(4000):
            s = rng.choice(len(keys), len(keys)); ms.append(np.mean(np.concatenate([byev[keys[i]] for i in s])))
        lo, hi = np.percentile(ms, [(100 - level) / 2, 100 - (100 - level) / 2])
        return {"n": len(rs), "events": len(keys), "mean": float(x.mean()), f"ci{level}": [float(lo), float(hi)]}

    no = [r for r in rows if r["side"] == "NO" and r["counts"]]; nom = [r for r in no if r["mention"]]
    nom_all = [r for r in rows if r["side"] == "NO" and r["mention"]]
    out = {"batches": sorted({r["batch"] for r in rows}), "positions": len(rows), "resolved_contract_sides": len(contracts)}
    allm = [r for r in rows if r["mention"] and r["counts"]]
    LOOKS["E3b"] = LOOKS["E3"]
    for name, rs, key in (("E1", no, "skill"), ("E3", nom, "skill_mention"), ("E3b", allm, "skill_mention_both")):
        n_ev = len({r["event"] for r in rs}); first, second = LOOKS[name]
        look = 2 if n_ev >= second else 1 if n_ev >= first else 0
        res = read(rs, key, 97.5)
        verdict = None
        if look and res:
            verdict = "confirmed" if res["ci97.5"][0] > 0 else "killed" if res["ci97.5"][1] < 0 else "carried"
        out[name] = {"events_resolved": n_ev, "look_reached": look, "looks_at": [first, second], "statistic": res, "reading": verdict or "not yet at a look"}
    blind_no = [{"event": x["event"], "money": x["hit"] - x["cost"]} for x in contracts if not x["yes"] and x["counts"]]
    out["secondary"] = {"no_money": read(no, "money", 95), "no_money_cost_50_up": read([r for r in no if r["cost"] >= 0.5], "money", 95),
                        "blind_no_money": read(blind_no, "money", 95), "yes_skill": read([r for r in rows if r["side"] == "YES"], "skill", 95),
                        "no_money_at_150_capped_by_depth": read(no, "money_150", 95),
                        "log_score": read(logs, "v", 95), "e3_no_money": read(nom, "money", 95),
                        "e3_all_mention_events_skill": read(nom_all, "skill_mention", 95), "e3_all_mention_events_money": read(nom_all, "money", 95), "e3_no_by_speaker": {g: read([r for r in nom if r["speaker"] == g], "skill_mention", 95) for g in ("Trump", "earnings call", "other")}}
    A.jdump(dict(out, rows=rows), os.path.join(D, "result.json")); print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("snapshot", "frame", "sessions", "freeze"):
        sp.add_parser(n).add_argument("batch")
    p = sp.add_parser("publish"); p.add_argument("batch"); p.add_argument("sid")
    p = sp.add_parser("ingest"); p.add_argument("batch"); p.add_argument("sid"); p.add_argument("agent_id")
    sp.add_parser("score")
    a = ap.parse_args()
    {"snapshot": cmd_snapshot, "frame": cmd_frame, "sessions": cmd_sessions, "publish": cmd_publish, "ingest": cmd_ingest, "freeze": cmd_freeze, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
