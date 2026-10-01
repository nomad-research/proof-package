"""T0 (T0_prereg.md): the sessions' own picks and claims from V1 and V1b, priced. Retrospective, descriptive. Output: t0_report.json.
Reads the frozen scorer (v1_score.load_round, map_tier, live_price_of) without editing it; post-trigger prices come from the public price history."""
import datetime as dt, gzip, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import numpy as np, v1_score as S, v1_packet as K
from nomad16 import exact as X

RES = json.load(gzip.open(os.path.join(HERE, "v1_resolutions.json.gz"), "rt"))
DATES = json.load(open(os.path.join(HERE, "v1_pool_market_dates.json")))
LAG_S, WINDOW_S = 3600, 48 * 3600
rng = np.random.default_rng(20261001)

def t(s):
    if not s: return None
    s = s.strip().replace(" ", "T")
    if s.endswith("+00"): s += ":00"
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())

def closed_at(cid):
    for src in (DATES.get(cid), RES.get(cid)):
        if src and src.get("closed"): return t(src["closed"])
    return None

def first_price_after(tok, ts):
    h = K._history(f"https://clob.polymarket.com/prices-history?market={tok}&startTs={ts + LAG_S}&endTs={ts + WINDOW_S}&fidelity=60").get("history", [])
    h = sorted((x for x in h if x["t"] >= ts + LAG_S), key=lambda x: x["t"])
    return (float(h[0]["p"]), h[0]["t"]) if h else (None, None)

def boot(x, n=5000):
    x = np.asarray(x, float)
    if len(x) == 0: return None
    m = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return {"n": int(len(x)), "mean": float(x.mean()), "ci90": [float(np.quantile(m, .05)), float(np.quantile(m, .95))], "p_positive": float(np.mean(np.array(m) > 0))}

def one_round(base, eid):
    S.HERE = base; R, d = S.load_round(eid); price_of = S.live_price_of(R, d)
    shown = {v["cid"] for k, v in json.load(open(os.path.join(d, "private_1b.json"))).items() if "." in k}
    menu_by_label = {c["label"]: (ev, c) for ev, v in R["menu"].items() for c in v["contracts"]}
    claims, picks = [], []
    def side_price(c, yes):
        p, _ = price_of(c["tok_yes"]); return None if p is None else (p if yes else 1 - p)
    def matched(cands, q):
        out = []
        for c in cands:
            p, _ = price_of(c["tok_yes"])
            if p is None: continue
            for yes in (True, False):
                qq = p if yes else 1 - p
                if abs(qq - q) <= 0.05: out.append((c["yes_won"] == yes) - qq)
        return out
    # picks: each primary leg as a binary bet; matched-cost null from the other contracts of the primary event
    prim = list(R["primary"]["contracts"].values())
    for b in R["ans1a"]["primary"]["basket"]:
        c = R["primary"]["contracts"][b["contract"]]; yes = b["side"] == "YES"; q = side_price(c, yes)
        if q is None: continue
        cost = X.share_cost(q, c["fee"], S.SLIP, c["tick"]); hit = float(c["yes_won"] == yes)
        null = matched([x for x in prim if x["cid"] != c["cid"]], q)
        picks.append({"round": eid, "q": q, "cost": cost, "hit": hit, "null_mean": float(np.mean(null)) if null else None})
    # claims
    seen = set()
    for cl in R["ans1b"].get("claims") or []:
        i, th = cl["if"], cl["then"]; ca = R["primary"]["contracts"].get(i["contract"])
        if ca is None: continue
        ya = i["resolves"] == "YES"
        if "contract" in th:
            if th["contract"] not in menu_by_label: continue
            _, cb = menu_by_label[th["contract"]]; yb = th.get("resolves", "YES") == "YES"; kind = "contract"
        else:
            if th.get("event") not in R["menu"]: continue
            m = S.map_tier(R["menu"][th["event"]]["contracts"], R["menu"][th["event"]]["kind"], th["direction"], th["tier"], price_of)
            if m is None: continue
            cb, side, _ = m; yb = side == "YES"; kind = "tier"
        q_lock = side_price(cb, yb)
        if q_lock is None: continue
        ante = ca["yes_won"] == ya; hit = float(cb["yes_won"] == yb)
        row = {"round": eid, "if_cid": ca["cid"], "then_cid": cb["cid"], "kind": kind, "antecedent_happened": ante, "hit": hit, "q_lock": q_lock,
               "dup": (cb["cid"], yb) in seen}
        seen.add((cb["cid"], yb))
        if ante:
            ta, tb = closed_at(ca["cid"]), closed_at(cb["cid"])
            row.update(if_closed=ta, then_closed=tb)
            if ta and tb and ta < tb:
                p, pt = first_price_after(cb["tok_yes"], ta)
                if p is not None:
                    qt = p if yb else 1 - p
                    row.update(triggered=True, q_trigger=qt, trigger_price_ts=pt, cost_trigger=X.share_cost(qt, cb["fee"], S.SLIP, cb["tick"]), hours_after_if=(pt - ta) / 3600)
                else: row.update(triggered=False, why="no price within 48h of the trigger")
            else: row.update(triggered=False, why="then closed at or before if" if ta and tb else "close time missing")
            pl = matched([c for v in R["menu"].values() for c in v["contracts"] if c["cid"] in shown and c["cid"] != cb["cid"]], q_lock)
            row["placebo_mean"] = float(np.mean(pl)) if pl else None; row["placebo_n"] = len(pl)
        claims.append(row)
    return picks, claims

def main():
    picks, claims = [], []
    for base in (HERE, os.path.join(HERE, "v1b")):
        for p in sorted(os.listdir(os.path.join(base, "results"))):
            r = json.load(open(os.path.join(base, "results", p)))
            if r.get("status") != "scored": continue
            try:
                a, b = one_round(base, r["round_id"][1:]); picks += a; claims += b
            except Exception as ex: print("round failed", r["round_id"], repr(ex)[:160], flush=True)
    rep = {}
    trig = [c for c in claims if c["antecedent_happened"]]
    dd = [c for c in trig if not c["dup"]]
    rep["c3_dedup"] = {"triggered_all": len(trig), "dedup": len(dd), "hit_rate": float(np.mean([c["hit"] for c in dd])), "mean_lock_price": float(np.mean([c["q_lock"] for c in dd])),
                       "excess": boot([c["hit"] - c["q_lock"] for c in dd])}
    tg = [c for c in dd if c.get("triggered")]
    rep["c1_trigger_lag"] = {"n_triggered_with_price": len(tg), "excluded": {k: sum(1 for c in dd if c.get("why") == k) for k in ("then closed at or before if", "no price within 48h of the trigger", "close time missing")},
                             "hit_rate": float(np.mean([c["hit"] for c in tg])) if tg else None, "mean_q_lock": float(np.mean([c["q_lock"] for c in tg])) if tg else None,
                             "mean_q_trigger": float(np.mean([c["q_trigger"] for c in tg])) if tg else None,
                             "hit_minus_trigger_price": boot([c["hit"] - c["q_trigger"] for c in tg]), "hit_minus_trigger_cost": boot([c["hit"] - c["cost_trigger"] for c in tg]),
                             "price_move_lock_to_trigger": boot([c["q_trigger"] - c["q_lock"] for c in tg])}
    pl = [c for c in dd if c.get("placebo_mean") is not None]
    rep["c2_matched_placebo"] = {"n": len(pl), "claim_minus_placebo": boot([(c["hit"] - c["q_lock"]) - c["placebo_mean"] for c in pl]),
                                 "mean_placebo_excess": float(np.mean([c["placebo_mean"] for c in pl])) if pl else None}
    rep["p_picks"] = {"money": boot([x["hit"] - x["cost"] for x in picks]), "skill": boot([(x["hit"] - x["cost"]) - x["null_mean"] for x in picks if x["null_mean"] is not None])}
    for lo, hi in ((0, .2), (.2, .5), (.5, .8), (.8, 1.01)):
        b = [x for x in picks if lo <= x["q"] < hi]
        rep["p_picks"][f"band_{lo}_{hi}"] = {"n": len(b), "money": boot([x["hit"] - x["cost"] for x in b]),
                                             "skill": boot([(x["hit"] - x["cost"]) - x["null_mean"] for x in b if x["null_mean"] is not None])}
    json.dump({"report": rep, "claims": claims, "picks": picks}, open(os.path.join(HERE, "t0_report.json"), "w"), indent=1, default=str)
    print(json.dumps(rep, indent=1))

main()
