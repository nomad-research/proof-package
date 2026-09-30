"""V3 forward runner: wraps the frozen v1_packet / v1_run unchanged (see V3_prereg.md). Packets, rounds and manifest live in v3/.
    python v3_run.py prepare1a|prepare1b <id> | ingest-agent <id> <1a|1b> <agent> | audit <id> <stage> <agent> | replace <id> <reason...> | batch <n> | status | manifest"""
import datetime, gzip, json, os, sys
REAL = os.path.dirname(os.path.abspath(__file__)); V3 = os.path.join(REAL, "v3"); sys.path.insert(0, REAL); sys.path.insert(0, os.path.join(REAL, "..", ".."))
import v1_packet as K, v1_run as V
LOCK = json.load(open(os.path.join(V3, "v3_lock.json")))["lock"]
POOL = {e["id"]: e for e in json.load(open(os.path.join(V3, "v3_pool.json")))}; DATES = json.load(open(os.path.join(V3, "v3_market_dates.json")))
_INDEX = None
if not os.path.exists(os.path.join(V3, "v1_rounds.json")):
    json.dump({"rounds": json.load(open(os.path.join(V3, "v3_draw.json"))), "reserve_left": json.load(open(os.path.join(V3, "v3_reserve.json"))), "replacements": []}, open(os.path.join(V3, "v1_rounds.json"), "w"), indent=1)
CUR = {"H": None}
def _index():
    global _INDEX
    if _INDEX is None:
        with gzip.open(os.path.join(V3, "v3_index.json.gz"), "rt") as f: _INDEX = json.load(f)
    return _INDEX
def load_index_h(*a, **k):
    """The open-event menu index with each event's markets cut to those ending between the lock and the primary's horizon (V3_prereg.md difference 3)."""
    H = CUR["H"]; out = []
    for r in _index():
        ms = [m for m in r["markets"] if m.get("end") and LOCK < K.ts(m["end"]) <= H]
        if len(ms) >= 2: out.append(dict(r, markets=ms))
    return out
K.lock_of = lambda e: LOCK
K.load_index = load_index_h
V.HERE = V3; V.LIVE = os.path.join(V3, "v1_rounds_live.json"); V.PROMPT_DIR = "/tmp/claude-0/v3_prompts"
V.round_row = lambda eid, rehearsal=False: (POOL[eid], DATES)
_ut = V.user_texts
V.user_texts = lambda path: [t for t in _ut(path) if not t.startswith(("Your answer was rejected by the validator", "[handback-send-enforce]"))]   # the one registered return and the harness's nudge
def use(eid): CUR["H"] = POOL[eid]["horizon"]
if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd in ("prepare1a", "prepare1b", "ingest-agent", "audit"): use(a[0])
    if cmd == "prepare1a": print(json.dumps(V.prepare1a(a[0]), indent=1))
    elif cmd == "prepare1b": print(json.dumps(V.prepare1b(a[0]), indent=1))
    elif cmd == "ingest-agent":
        eid, st, ag = a; txt = V.final_answer(ag); open(os.path.join(V.rdir(eid), f"reply_{st}.txt"), "w").write(txt); print(json.dumps(V.ingest(eid, st, txt), indent=1))
    elif cmd == "audit": print(json.dumps(V.audit(a[0], a[1], a[2]), indent=1))
    elif cmd == "replace": print(V.replace(a[0], " ".join(a[1:])))
    elif cmd == "batch": print(json.dumps(V.next_batch(int(a[0]))))
    elif cmd == "status": st = V.live_state(); print(json.dumps({"rounds": len(st["rounds"]), "reserve_left": len(st["reserve"]), "replacements": st["log"]}, indent=1))
    elif cmd == "manifest": print(json.dumps(V.manifest(False, False), indent=1))
