"""Variance check: a SECOND independent session on a pre-declared subset of V1 rounds. Uses the frozen v1_run / v1_score unchanged
by pointing their HERE at variance/ (packets and results live there; data files are symlinks) and their prompt dir at a separate one.
Never touches packets/ or results/ (the frozen study).
    python v1_variance.py prepare1a|prepare1b <id>
    python v1_variance.py ingest-agent <id> <1a|1b> <agent_id>
    python v1_variance.py audit <id> <stage> <agent_id>
    python v1_variance.py score <id>
    python v1_variance.py compare"""
import json, os, sys
REAL = os.path.dirname(os.path.abspath(__file__)); VAR = os.path.join(REAL, "variance"); os.makedirs(VAR, exist_ok=True)
for f in ("v1_pool.json", "v1_pool_market_dates.json", "v1_resolutions.json.gz", "v1_rounds.json"):
    if not os.path.lexists(os.path.join(VAR, f)): os.symlink(os.path.join(REAL, f), os.path.join(VAR, f))
sys.path.insert(0, REAL)
import v1_run as V, v1_score as S
V.HERE = VAR; S.HERE = VAR; V.PROMPT_DIR = "/tmp/claude-0/v1_prompts_var"
_user_texts = V.user_texts
CORRECTION_PREFIX = "Your answer was rejected by the validator"                   # the one registered return of an invalid answer; the frozen audit's instruction list has no slot for it
def _user_texts_ex_correction(path):
    return [t for t in _user_texts(path) if not t.startswith((CORRECTION_PREFIX, "[handback-send-enforce]"))]   # the second is the harness's own nudge to hand back
V.user_texts = _user_texts_ex_correction
SUBSET_HEDGED = ["155674", "287395", "606437", "655630", "680764", "850741"]     # every third of the 17 scored rounds, sorted by id, from index 0
SUBSET_NOINSTR = ["125877", "624242"]                                            # first and fourth of the 7 no_instrument rounds, sorted by id
SUBSET = SUBSET_HEDGED + SUBSET_NOINSTR


def basket(a): return sorted(f"{b['contract']}:{b['side']}" for b in a.get("primary", {}).get("basket", []))
def legs(a): return sorted(h.get("event") and f"{h['event']}" or h["contract"].split(".")[0] for h in a.get("hedges", []))


def compare():
    rows = []
    for i in SUBSET:
        o, n = f"{REAL}/packets/R{i}", f"{VAR}/packets/R{i}"
        if not os.path.exists(f"{n}/answer_1b.json"): rows.append({"round": i, "status": "not run"}); continue
        a1, b1 = json.load(open(f"{o}/answer_1a.json")), json.load(open(f"{n}/answer_1a.json"))
        a2, b2 = json.load(open(f"{o}/answer_1b.json")), json.load(open(f"{n}/answer_1b.json"))
        ev = lambda ans, pv: sorted({pv[h["contract"].split(".")[0]]["event_id"] if "contract" in h and "." in h["contract"] else pv[h["event"]]["event_id"] for h in ans["hedges"]}) if ans["hedges"] else []
        pa, pb = json.load(open(f"{o}/private_1b.json")), json.load(open(f"{n}/private_1b.json"))
        ea, eb = set(ev(a2, pa)), set(ev(b2, pb)); jac = len(ea & eb) / len(ea | eb) if (ea | eb) else None
        r = {"round": i, "primary_basket_same": basket(a1) == basket(b1), "basket_1": basket(a1), "basket_2": basket(b1),
             "no_instrument": [bool(a2.get("no_instrument")), bool(b2.get("no_instrument"))], "recalls": [bool(a1.get("recalls_outcome") or a2.get("recalls_outcome")), bool(b1.get("recalls_outcome") or b2.get("recalls_outcome"))],
             "hedge_event_jaccard": jac, "menu_same": json.load(open(f"{o}/stage1b.json")).get("candidates") is not None and json.load(open(f"{o}/meta_1b.json"))["candidates_with_priced_contracts"] == json.load(open(f"{n}/meta_1b.json"))["candidates_with_priced_contracts"],
             "stage1a_packet_same": json.load(open(f"{o}/meta_1a.json"))["packet_sha256"] == json.load(open(f"{n}/meta_1a.json"))["packet_sha256"]}
        for tag, d in (("first", f"{REAL}/results"), ("second", f"{VAR}/results")):
            p = f"{d}/R{i}.json"
            if os.path.exists(p):
                x = json.load(open(p)); r[f"lift_{tag}"] = x.get("lift"); r[f"in_set_{tag}"] = x.get("in_reachable_set"); r[f"C_minus_D_{tag}"] = (x["realised"]["C"] - x["realised"]["D"]) if x.get("realised") else None
        rows.append(r)
    json.dump(rows, open(f"{REAL}/v1_variance_report.json", "w"), indent=1)
    return rows


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "prepare1a": print(json.dumps(V.prepare1a(args[0]), indent=1))
    elif cmd == "prepare1b": print(json.dumps(V.prepare1b(args[0]), indent=1))
    elif cmd == "ingest-agent":
        eid, st, ag = args; txt = V.final_answer(ag); open(os.path.join(V.rdir(eid), f"reply_{st}.txt"), "w").write(txt); print(json.dumps(V.ingest(eid, st, txt), indent=1))
    elif cmd == "audit": print(json.dumps(V.audit(args[0], args[1], args[2]), indent=1))
    elif cmd == "score":
        R, d = S.load_round(args[0]); out = S.score_round(R, S.live_price_of(R, d)); os.makedirs(f"{VAR}/results", exist_ok=True)
        json.dump(out, open(f"{VAR}/results/R{args[0]}.json", "w"), indent=1, default=str); print(json.dumps(out, indent=1, default=str)[:900])
    elif cmd == "compare": print(json.dumps(compare(), indent=1))
