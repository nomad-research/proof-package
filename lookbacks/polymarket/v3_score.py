"""V3 scorer: wraps the frozen v1_score.py unchanged. Outcomes are fetched from Gamma at scoring time (they did not exist at authoring).
    python v3_score.py --fetch            # snapshot the resolution state of every primary and menu event -> v3/resolutions/YYYYMMDD_HHMMSS.json.gz
    python v3_score.py --round <id>       # score one round if every contract it uses has resolved cleanly; else report what is pending
    python v3_score.py --all              # try every current round; writes v3/results/R<id>.json for the scorable ones
    python v3_score.py --study            # frozen study() over v3/results -> v3_study_report.json
Rules (V3_prereg.md difference 5): a round is scored only when its primary contracts, its hedge legs and its tier-mapped rungs have all resolved decisively (1/0, UMA 'resolved',
not disputed). The random arm R draws only from menu contracts that have resolved; the number excluded is reported. Unresolved 45 days after the horizon -> unscored 'unresolved'."""
import argparse, datetime as dt, glob, gzip, json, os, sys, time
REAL = os.path.dirname(os.path.abspath(__file__)); V3 = os.path.join(REAL, "v3"); sys.path.insert(0, REAL); sys.path.insert(0, os.path.join(REAL, "..", ".."))
import v3_run as W                       # patches v1_packet (lock, horizon-cut index) exactly as at authoring
import v1_packet as K, v1_pool as P, v1_score as S
from concurrent.futures import ThreadPoolExecutor
RES_DIR = os.path.join(V3, "resolutions"); OUT = os.path.join(V3, "results"); GRACE_D = 45

def rounds(): return json.load(open(os.path.join(V3, "v1_rounds_live.json")))["rounds"]

def event_ids_of(rid):
    d = os.path.join(V3, "packets", f"R{rid}"); ids = {rid}
    priv = json.load(open(f"{d}/private_1b.json")) if os.path.exists(f"{d}/private_1b.json") else {}
    ids |= {v["event_id"] for k, v in priv.items() if "." not in k and "event_id" in v}
    return ids

def fetch():
    ids = sorted({i for r in rounds() for i in event_ids_of(r)})
    def one(eid):
        e = P.page(f"{P.GAMMA}/{eid}")
        if not e: return eid, None
        return eid, {m.get("conditionId"): {"final": m.get("outcomePrices"), "uma": m.get("umaResolutionStatus"), "uma_all": m.get("umaResolutionStatuses"), "closed": m.get("closed"),
                                            "closedTime": m.get("closedTime"), "feeSchedule": m.get("feeSchedule"), "tick": m.get("orderPriceMinTickSize"), "end": m.get("endDate")} for m in (e.get("markets") or [])}
    with ThreadPoolExecutor(8) as ex: got = dict(ex.map(one, ids))
    os.makedirs(RES_DIR, exist_ok=True); p = os.path.join(RES_DIR, time.strftime("%Y%m%d_%H%M%S") + ".json.gz")
    with gzip.open(p, "wt") as f: json.dump(got, f, sort_keys=True)
    print("snapshot", os.path.basename(p), "events", len(got), "missing", sum(v is None for v in got.values())); return p

def latest():
    ps = sorted(glob.glob(os.path.join(RES_DIR, "*.json.gz")))
    if not ps: sys.exit("no resolution snapshot; run --fetch")
    with gzip.open(ps[-1], "rt") as f: snap = json.load(f)
    return {cid: v for ev in snap.values() if ev for cid, v in ev.items()}, os.path.basename(ps[-1])

def clean(r):
    if not r or r.get("uma") != "resolved": return False
    try: f = sorted(float(x) for x in json.loads(r["final"] or "[]"))
    except Exception: return False
    return f == [0.0, 1.0] and "disputed" not in json.dumps(r.get("uma_all") or "").lower()

def load(rid, res):
    """v1_score.load_round, with finals from the snapshot. Unresolved contracts get yes_won None and are listed."""
    W.use(rid); e = W.POOL[rid]; d = os.path.join(V3, "packets", f"R{rid}"); lock = W.LOCK; pending = []
    def con(label, cid, tok, q, fallback_fee=None, fallback_tick=None):
        r = res.get(cid)
        if not clean(r): pending.append(label)
        yes = json.loads(r["final"])[0] == "1" if clean(r) else None
        return {"label": label, "cid": cid, "tok_yes": tok, "q": q, "fee": (r or {}).get("feeSchedule", fallback_fee), "tick": (r or {}).get("tick", fallback_tick), "end": (r or {}).get("end"), "yes_won": yes}
    mk = {m["cid"]: m for m in e["markets"]}
    priv1, priv2 = json.load(open(f"{d}/private_1a.json")), json.load(open(f"{d}/private_1b.json"))
    pk1, pk2 = json.load(open(f"{d}/stage1a.json")), json.load(open(f"{d}/stage1b.json"))
    idx = {r["id"]: r for r in K.load_index()}
    R = {"round_id": f"R{rid}", "ans1a": json.load(open(f"{d}/answer_1a.json")), "ans1b": json.load(open(f"{d}/answer_1b.json")), "lock": lock,
         "primary": {"kind": pk1["event"]["kind"], "total": len(e["markets"]), "shown": len(pk1["event"]["contracts"]),
                     "contracts": {lab: con(lab, v["cid"], v["token_yes"], v.get("q"), mk[v["cid"]]["feeSchedule"], mk[v["cid"]]["tick"]) for lab, v in priv1.items()}}, "menu": {}}
    for c in pk2["candidates"]:
        ev = priv2[c["label"]]["event_id"]; cs = []
        if c["kind"].endswith("ladder"):
            for k, m in enumerate(idx[ev]["markets"]):
                if m.get("tokens") and K.open_at(m, lock): cs.append(con(f"{c['label']}.r{k}", m["cid"], m["tokens"][0], m.get("q")))
        else:
            for k in c["contracts"]:
                v = priv2[k["label"]]; cs.append(con(k["label"], v["cid"], v["token_yes"], v.get("q")))
        R["menu"][c["label"]] = {"kind": c["kind"], "contracts": cs, "total": len(idx[ev]["markets"])}
    return R, d, set(pending)

def used_labels(R, price_of):
    """Labels of every contract the round's score depends on: all primary contracts, hedge legs, tier-mapped rungs (hedges and claim consequents)."""
    u = set(R["primary"]["contracts"])
    for h in R["ans1b"].get("hedges", []) + [c["then"] for c in R["ans1b"].get("claims", [])]:
        if "contract" in h: u.add(h["contract"])
        elif h.get("event") in R["menu"]:
            v = R["menu"][h["event"]]; m = S.map_tier(v["contracts"], v["kind"], h["direction"], h["tier"], price_of)
            if m: u.add(m[0]["label"])
    for ev in {h.get("event") or h.get("contract", "").split(".")[0] for h in R["ans1b"].get("hedges", [])}:       # every rung of a held ladder enters the state space
        if ev in R["menu"] and R["menu"][ev]["kind"].endswith("ladder"): u |= {c["label"] for c in R["menu"][ev]["contracts"]}
    return u

def score(rid, res, snapname):
    R, d, pending = load(rid, res)
    if R["ans1b"].get("no_instrument"): return {"round_id": f"R{rid}", "status": "unscored", "reason": "no_instrument"}
    price_of = S.live_price_of(R, d)
    need = used_labels(R, price_of); wait = sorted(need & pending)
    H = W.POOL[rid]["horizon"]
    if wait:
        late = time.time() > H + GRACE_D * 86400
        return {"round_id": f"R{rid}", "status": "unscored" if late else "pending", "reason": "unresolved" if late else None, "waiting_on": wait, "snapshot": snapname}
    n_excl = 0
    for v in R["menu"].values():                                 # arm R draws only from resolved menu contracts
        keep = [c for c in v["contracts"] if c["yes_won"] is not None]; n_excl += len(v["contracts"]) - len(keep); v["contracts"] = keep
    out = S.score_round(R, price_of); out["snapshot"] = snapname; out["menu_contracts_unresolved_excluded"] = n_excl
    os.makedirs(OUT, exist_ok=True); json.dump(out, open(os.path.join(OUT, f"R{rid}.json"), "w"), indent=1, default=str)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--fetch", action="store_true"); ap.add_argument("--round"); ap.add_argument("--all", action="store_true"); ap.add_argument("--study", action="store_true"); a = ap.parse_args()
    if a.fetch: fetch()
    if a.round or a.all:
        res, sn = latest(); tally = {}
        for rid in ([a.round] if a.round else rounds()):
            try: o = score(rid, res, sn)
            except Exception as ex: o = {"round_id": f"R{rid}", "status": "error", "error": repr(ex)[:300]}
            tally[rid] = o.get("status"); print(rid, o.get("status"), o.get("reason") or "", ("waiting on %d" % len(o["waiting_on"])) if o.get("waiting_on") else "", ("lift %.1f" % o["lift"]) if o.get("lift") is not None else "", o.get("error", ""))
        json.dump({"snapshot": sn, "status": tally}, open(os.path.join(V3, "v3_score_status.json"), "w"), indent=1)
    if a.study:
        rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(OUT, "R*.json")))]
        st = json.load(open(os.path.join(V3, "v3_score_status.json")))["status"] if os.path.exists(os.path.join(V3, "v3_score_status.json")) else {}
        rs += [{"round_id": f"R{k}", "status": "unscored", "reason": "no_instrument"} for k, v in st.items() if v == "unscored" and not os.path.exists(os.path.join(OUT, f"R{k}.json"))]
        rep = S.study(rs); rep["pending"] = [k for k, v in st.items() if v == "pending"]
        json.dump(rep, open(os.path.join(REAL, "v3_study_report.json"), "w"), indent=1); print(json.dumps(rep, indent=1)[:2500])
