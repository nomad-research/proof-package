"""V1b runner: the frozen v1_run / v1_score, unchanged, pointed at v1b/ (see V1b_prereg.md). Data files are symlinks to the V1 frozen files.
    python v1b_run.py prepare1a|prepare1b <id> | ingest-agent <id> <1a|1b> <agent> | audit <id> <stage> <agent> | score <id> | study | manifest | batch <n>"""
import glob, json, os, sys
REAL = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(REAL, "v1b"); sys.path.insert(0, REAL); sys.path.insert(0, os.path.join(REAL, "..", ".."))
for f in ("v1_pool.json", "v1_pool_market_dates.json", "v1_resolutions.json.gz"):
    if not os.path.lexists(os.path.join(B, f)): os.symlink(os.path.join(REAL, f), os.path.join(B, f))
import v1_run as V, v1_score as S
V.HERE = B; S.HERE = B; V.LIVE = os.path.join(B, "v1_rounds_live.json"); V.PROMPT_DIR = "/tmp/claude-0/v1b_prompts"
_ut = V.user_texts
V.user_texts = lambda path: [t for t in _ut(path) if not t.startswith(("Your answer was rejected by the validator", "[handback-send-enforce]"))]   # the one registered return and the harness's nudge
if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == "prepare1a": print(json.dumps(V.prepare1a(a[0]), indent=1))
    elif cmd == "prepare1b": print(json.dumps(V.prepare1b(a[0]), indent=1))
    elif cmd == "ingest-agent":
        eid, st, ag = a; txt = V.final_answer(ag); open(os.path.join(V.rdir(eid), f"reply_{st}.txt"), "w").write(txt); print(json.dumps(V.ingest(eid, st, txt), indent=1))
    elif cmd == "audit": print(json.dumps(V.audit(a[0], a[1], a[2]), indent=1))
    elif cmd == "batch": print(json.dumps(V.next_batch(int(a[0]))))
    elif cmd == "manifest": print(json.dumps(V.manifest(False, False), indent=1))
    elif cmd == "score":
        R, d = S.load_round(a[0]); out = S.score_round(R, S.live_price_of(R, d)); os.makedirs(os.path.join(B, "results"), exist_ok=True)
        json.dump(out, open(os.path.join(B, "results", f"R{a[0]}.json"), "w"), indent=1, default=str); print(out.get("status"), out.get("reason", ""), out.get("lift"))
    elif cmd == "study":
        rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(B, "results", "R*.json")))]
        rep = S.study(rs); json.dump(rep, open(os.path.join(REAL, "v1b_study_report.json"), "w"), indent=1); print(json.dumps(rep, indent=1)[:2500])
