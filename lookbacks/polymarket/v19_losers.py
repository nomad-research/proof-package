"""What separates the armed NOs that held from the ones that flipped to YES (exploratory, after the fact; declares nothing). BT-T2 passes 1 to 4, non-mention, A2-armed.

    python lookbacks/polymarket/v19_losers.py      # run from lookbacks/polymarket; no network
"""
import sys, os, json, collections, math
sys.path.insert(0, ".")
import numpy as np, bt_audit as A, bt_t2 as T, v19_a2 as V
rows = []
for d in ("t2", "t2_pass2", "t2_pass3", "t2_pass4"):
    D = os.path.join("bt", d); fdoc = A.jload(os.path.join(D, "frame.json")); frame = {e["id"]: e for e in fdoc["events"]}
    crawl = {e["id"]: e for e in A.jload(os.path.join("bt", fdoc["crawl"]))}
    for ev in frame.values():
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]]); c["closed"] = A.ts(mk[c["cid"]].get("closed_time")) if mk[c["cid"]].get("closed_time") else None
    base_side = [(e["id"], e["kind"], yes, T.cost(c, yes), float(c["yes"] == yes)) for e in frame.values() for c in e["contracts"] for yes in (True, False)]
    man = A.jload(os.path.join(D, "manifest.json"))
    for sid, row in man["sessions"].items():
        if row["status"] != "ok": continue
        ans = T.intkeys(A.jload(os.path.join(D, "answers", f"{sid}.json"))["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"] or V.market_type(ev) == "mention": continue
            byc = {c["cid"]: c for c in ev["contracts"]}; evrows = []
            for cl, cid in L["contracts"].items():
                c = byc[cid]; ch = T.contract_chance(ev, ans, lab, cl, c)
                if ch is None: continue
                lo, hi = ch; mid = (lo + hi) / 2; cc = T.cost(c, False)
                if 1 - hi > cc:
                    hit = float(not c["yes"])
                    bs = [h - k for (eid, kd, s, k, h) in base_side if eid != ev["id"] and kd == ev["kind"] and not s and abs(k - cc) <= 0.05]
                    evrows.append({"pass": d, "event": f"{d}/{ev['id']}", "skind": ev["kind"], "mtype": V.market_type(ev), "q": c["price_yes"], "mid": mid, "lo": lo, "hi": hi,
                                   "cost": cc, "gap": abs(mid - c["price_yes"]), "hit": hit, "money": hit - cc, "skill": (hit - cc) - (float(np.mean(bs)) if bs else 0.0),
                                   "days": (V.scheduled_end(ev) - ev["lock"]) / 86400, "n_contracts": len(ev["contracts"]),
                                   "subject": V.subject_of(ev), "end": V.scheduled_end(ev)})
            arm = [r for r in evrows if r["cost"] >= 0.5 and r["gap"] >= 0.2]
            for r in arm:
                r["n_armed_event"] = len(arm); r["mkt_mass_armed"] = sum(x["q"] for x in arm); r["reader_mass_armed"] = sum(x["mid"] for x in arm)
            rows += arm
V.assign_occasions(rows)
occ_n = collections.Counter(r["occ"] for r in rows)
for r in rows: r["n_armed_occasion"] = occ_n[r["occ"]]
json.dump(rows, open("v19/armed_rows.json", "w"))
L = [r for r in rows if r["hit"] == 0]; W = [r for r in rows if r["hit"] == 1]
print("armed", len(rows), "events", len({r['event'] for r in rows}), "losers", len(L), "loss rate %.2f" % (len(L)/len(rows)))
def band(name, key, edges):
    out = []
    for lo, hi in zip(edges, edges[1:]):
        rs = [r for r in rows if lo <= r[key] < hi]
        if rs: out.append("%s[%g,%g): n=%d loss %.0f%% skill %+.1fc" % (name, lo, hi, len(rs), 100*np.mean([1-r['hit'] for r in rs]), 100*np.mean([r['skill'] for r in rs])))
    print("\n".join(out)); print()
band("market YES mass of armed NOs in the event ", "mkt_mass_armed", [0, 0.4, 0.6, 0.8, 1.0, 9])
band("armed NOs in the event ", "n_armed_event", [1, 2, 3, 5, 99])
band("armed positions in the occasion ", "n_armed_occasion", [1, 2, 4, 8, 99])
band("days to scheduled end ", "days", [0, 3, 7, 14, 30, 999])
band("market YES price ", "q", [0, 0.25, 0.35, 0.45, 1])
band("reader's own YES (mid) ", "mid", [0, 0.02, 0.05, 0.10, 0.2, 1])
for k in sorted({r["skind"] for r in rows}):
    rs = [r for r in rows if r["skind"] == k]; print("session kind %-10s n=%3d loss %.0f%% skill %+.1fc" % (k, len(rs), 100*np.mean([1-r['hit'] for r in rs]), 100*np.mean([r['skill'] for r in rs])))
