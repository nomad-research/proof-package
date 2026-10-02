"""Were the backtest's lock prices tradeable? Exploratory, declares nothing (V19_FRAMEWORK_P5_RESULT.md §3). Run after P5 was scored.

A BT-T2 lock price is the last prices-history point within 48 hours before the lock. On a book with no real quotes that point is the
midpoint of an empty book, about 50c. A position is flagged "suspect" when its event shows this:
  - a partition (exclusive outcomes, so YES prices should sum to about 1) whose YES prices sum to more than 1.3; or
  - an event whose every contract is priced between 40c and 55c.

    python lookbacks/polymarket/v19_price_check.py read t2 t2_pass2 t2_pass3 t2_pass4 t2_pass5     # no network; writes v19/price_check.json
    python lookbacks/polymarket/v19_price_check.py trades                                          # network: trade prints near the lock, 12 + 12 sampled
"""
import json, os, random, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T
import v19_a2 as V
import v19_p5 as P

SUM_MAX, FLAT = 1.3, (0.40, 0.55)
OUT = os.path.join(HERE, "v19", "price_check.json")


def positions(d):
    """v19_p5.positions, plus the contract id and the event's price shape."""
    D = os.path.join(HERE, "bt", d); fdoc = A.jload(os.path.join(D, "frame.json")); frame = {e["id"]: e for e in fdoc["events"]}
    crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", fdoc["crawl"]))}
    for ev in frame.values():
        mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
        for c in ev["contracts"]:
            c["yes"] = A.yes_won(mk[c["cid"]])
    base_side = [(e["id"], e["kind"], yes, T.cost(c, yes), float(c["yes"] == yes)) for e in frame.values() for c in e["contracts"] for yes in (True, False)]
    man = A.jload(os.path.join(D, "manifest.json")); rows = []
    for sid, row in man["sessions"].items():
        rec = A.jload(os.path.join(D, "answers", f"{sid}.json"))
        if A.sha(rec["answers"]) != row["answers_sha256"]:
            raise SystemExit(f"{d}/{sid} changed after the freeze")
        if row["status"] != "ok":
            continue
        ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(D, "sessions", f"{sid}.json"))["labels"]
        for lab, L in labels.items():
            ev = frame[L["event_id"]]
            if ans[lab]["recognised"] or V.market_type(ev) == "mention":
                continue
            byc = {c["cid"]: c for c in ev["contracts"]}; ps = [c["price_yes"] for c in ev["contracts"]]
            suspect = (ev["kind"] == "partition" and sum(ps) > SUM_MAX) or (len(ps) >= 2 and all(FLAT[0] <= p <= FLAT[1] for p in ps))
            for cl, cid in L["contracts"].items():
                c = byc[cid]; ch = T.contract_chance(ev, ans, lab, cl, c)
                if ch is None:
                    continue
                lo, hi = ch; mid = (lo + hi) / 2; cc = T.cost(c, False)
                if not (1 - hi > cc and cc >= 0.50 and abs(mid - c["price_yes"]) >= 0.20):
                    continue
                hit = float(not c["yes"])
                bs = [h - k for (eid, kd, s, k, h) in base_side if eid != ev["id"] and kd == ev["kind"] and not s and abs(k - cc) <= T.MATCH_BAND]
                rows.append({"pass": d, "cid": cid, "event": f"{d}/{ev['id']}", "skind": ev["kind"], "mid": mid, "cost": cc, "hit": hit, "money": hit - cc,
                             "skill": (hit - cc) - (float(np.mean(bs)) if bs else 0.0), "lock": ev["lock"], "days": (V.scheduled_end(ev) - ev["lock"]) / P.DAY,
                             "subject": V.subject_of(ev), "end": V.scheduled_end(ev), "mtype": V.market_type(ev), "price_sum": sum(ps), "suspect": suspect})
    V.assign_occasions(rows)
    for r in rows:
        r["occ"] = f"{d}|{r['occ']}"
        r["framework"] = r["mid"] < 0.10 and r["days"] >= 3 and r["skind"] != "touch"; r["tier"] = 1 if r["mid"] < 0.05 else 2 if r["mid"] < 0.10 else None
    return rows


def read(passes):
    rows = [r for d in passes for r in positions(d)]; rng = np.random.default_rng(P.SEED)
    rd = lambda rs: {"skill": P.read(rs, "skill", rng), "money": P.read(rs, "money", rng)} if rs else None
    S, C = [r for r in rows if r["suspect"]], [r for r in rows if not r["suspect"]]; last = passes[-1]
    out = {"passes": passes, "rule": f"suspect: partition YES prices sum > {SUM_MAX}, or every contract priced {FLAT[0]}-{FLAT[1]}",
           "a2_all": rd(rows), "a2_suspect": rd(S), "a2_clean": rd(C),
           "a2_clean_by_kind": {k: rd([r for r in C if r["skind"] == k]) for k in sorted({r["skind"] for r in C})},
           "a2_suspect_by_kind": {k: rd([r for r in S if r["skind"] == k]) for k in sorted({r["skind"] for r in S})},
           "a2_clean_by_pass": {d: rd([r for r in C if r["pass"] == d]) for d in passes},
           "framework_clean_earlier_passes": rd([r for r in C if r["framework"] and r["pass"] != last]),
           f"framework_clean_{last}": rd([r for r in C if r["framework"] and r["pass"] == last]),
           f"blocked_clean_{last}": rd([r for r in C if not r["framework"] and r["pass"] == last]),
           f"framework_suspect_{last}": rd([r for r in S if r["framework"] and r["pass"] == last]),
           "share_suspect_by_pass": {d: float(np.mean([r["suspect"] for r in rows if r["pass"] == d])) for d in passes}}
    A.jdump(out, OUT); A.jdump(rows, os.path.join(HERE, "v19", "price_check_rows.json")); print(json.dumps(out, indent=1))


def trades(cid, pages=6):
    got = []
    for off in range(0, 500 * pages, 500):
        req = urllib.request.Request(f"https://data-api.polymarket.com/trades?market={cid}&limit=500&offset={off}", headers={"User-Agent": "curl/8.5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=30)); got += d
        if len(d) < 500:
            break
    return got


def sample_trades():
    """Trade prints from 48 hours before to 24 hours after the lock, as a NO-equivalent price, for 12 suspect and 12 clean positions."""
    rows = A.jload(os.path.join(HERE, "v19", "price_check_rows.json")); random.seed(1); out = {}
    for name, pool in (("suspect", [r for r in rows if r["suspect"]]), ("clean", [r for r in rows if not r["suspect"]])):
        out[name] = []
        for r in random.sample(pool, 12):
            t = trades(r["cid"]); near = [x for x in t if r["lock"] - 48 * 3600 <= x["timestamp"] <= r["lock"] + 24 * 3600]
            no = [x["price"] if x["outcome"] == "No" else 1 - x["price"] for x in near]
            out[name].append({"event": r["event"], "cid": r["cid"], "backtest_cost": r["cost"], "trades_near_lock": len(near),
                              "no_price_median": float(np.median(no)) if no else None, "no_price_min": min(no) if no else None})
    A.jdump(out, os.path.join(HERE, "v19", "price_check_trades.json")); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    read(sys.argv[2:]) if sys.argv[1] == "read" else sample_trades()
