"""Post-hoc anatomy of BT-T2's disagreements: what kind of disagreement each position was, and which kinds paid."""
import sys, json, glob, math, collections
import numpy as np
import os; HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); sys.path.insert(0, REPO)
import bt_t2 as T, bt_audit as A, v1_score as S

fr = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "t2", "frame.json"))["events"]}
crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"))}
for ev in fr.values():
    mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
    for c in ev["contracts"]:
        c["yes"] = A.yes_won(mk[c["cid"]])
base = [(ev["id"], ev["kind"], T.cost(c, y), float(c["yes"] == y)) for ev in fr.values() for c in ev["contracts"] for y in (True, False)]

rows, ladders = [], []
for f in sorted(glob.glob(os.path.join(HERE, "bt", "t2", "sessions", "S*.json"))):
    L = A.jload(f)["labels"]; ans = T.intkeys(A.jload(f.replace("sessions", "answers"))["answers"])
    for lab, l in L.items():
        ev = fr[l["event_id"]]; byc = {c["cid"]: c for c in ev["contracts"]}
        for cl, cid in l["contracts"].items():
            c = byc[cid]; ch = T.contract_chance(ev, ans, lab, cl, c)
            if ch is None:
                continue
            lo, hi = ch; mid = (lo + hi) / 2; q = c["price_yes"]
            for yes, want in ((True, lo), (False, 1 - hi)):
                cc = T.cost(c, yes)
                if want <= cc:
                    continue
                hit = float(c["yes"] == yes)
                bm = [h - k for (eid, kd, k, h) in base if eid != ev["id"] and kd == ev["kind"] and abs(k - cc) <= 0.05]
                # what kind of disagreement: does the session pull the price toward 50% (less sure than the market) or away from it (surer)?
                toward = abs(mid - 0.5) < abs(q - 0.5)
                flip = (mid - 0.5) * (q - 0.5) < 0
                rows.append({"event": ev["id"], "kind": ev["kind"], "title": ev["title"], "q": c["q"], "price_yes": q, "session": mid, "bounded": lo != hi,
                             "side": "YES" if yes else "NO", "cost": cc, "hit": hit, "money": hit - cc, "skill": (hit - cc) - (np.mean(bm) if bm else 0),
                             "type": "opposite side of 50%" if flip else ("less sure than market" if toward else "surer than market"),
                             "gap": mid - q})
        # ladder shape: where the session centres its view and how wide it draws it, against the market's own ladder
        for key, side, rising in T.scaled_vars(ev):
            five = ans[lab].get(key)
            if not five or ev["kind"] in ("dates", "dates1"):
                continue
            pts = T.market_points(ev, side); oi = T.outcome_interval(ev, ev["kind"], side)
            if len(pts) < 3 or oi is None:
                continue
            xs, ys = T.isotonic([p[0] for p in pts], [p[1] for p in pts], increasing=rising)
            def mq(level):                                   # market's value where its chance curve crosses `level`
                for (x1, y1), (x2, y2) in zip(zip(xs, ys), list(zip(xs, ys))[1:]):
                    if (y1 - level) * (y2 - level) <= 0 and y1 != y2:
                        return x1 + (level - y1) * (x2 - x1) / (y2 - y1)
                return None
            m25, m50, m75 = mq(0.25), mq(0.5), mq(0.75)
            s25, s50, s75 = five[25], five[50], five[75]
            out = (oi[0] + oi[1]) / 2 if math.isfinite(oi[0]) and math.isfinite(oi[1]) else None
            ladders.append({"title": ev["title"], "kind": ev["kind"], "side": side, "as_of": ev["as_of"], "s50": s50, "m50": m50,
                            "s_width": abs(s25 - s75), "m_width": abs(m25 - m75) if (m25 is not None and m75 is not None) else None, "outcome_mid": out, "oi": oi})

def boot(sub, key="skill"):
    g = collections.defaultdict(list)
    for r in sub: g[r["event"]].append(r[key])
    ks = list(g); rng = np.random.default_rng(7)
    m = [np.mean([x for i in rng.integers(0, len(ks), len(ks)) for x in g[ks[i]]]) for _ in range(3000)]
    return f"n={len(sub):3d} ev={len(ks):3d} skill={np.mean([r[key] for r in sub]):+.3f} (95% {np.quantile(m,.025):+.3f} to {np.quantile(m,.975):+.3f}) hit={np.mean([r['hit'] for r in sub]):.2f} cost={np.mean([r['cost'] for r in sub]):.2f}"

print("ALL", boot(rows))
print("\nBY TYPE OF DISAGREEMENT")
for t in ("less sure than market", "surer than market", "opposite side of 50%"):
    print(f"  {t:24s}", boot([r for r in rows if r["type"] == t]))
print("\nBY SIDE")
for s in ("YES", "NO"):
    print(f"  {s:24s}", boot([r for r in rows if r["side"] == s]))
print("\nBY TYPE x SIDE")
for t in ("less sure than market", "surer than market", "opposite side of 50%"):
    for s in ("YES", "NO"):
        sub = [r for r in rows if r["type"] == t and r["side"] == s]
        if sub: print(f"  {t:24s} {s:3s}", boot(sub))
print("\nBY SIZE OF GAP (session minus price, in chance points)")
for lo, hi in ((0, .1), (.1, .2), (.2, .4), (.4, 1.01)):
    sub = [r for r in rows if lo <= abs(r["gap"]) < hi]
    if sub: print(f"  |gap| {lo:.1f}-{hi:.1f}       ", boot(sub))
print("\nBY KIND x TYPE")
for k in sorted({r["kind"] for r in rows}):
    for t in ("less sure than market", "surer than market", "opposite side of 50%"):
        sub = [r for r in rows if r["kind"] == k and r["type"] == t]
        if sub: print(f"  {k:9s} {t:24s}", boot(sub))
print("\nMENTION MARKETS (What will Trump say)")
for r in sorted([r for r in rows if "say" in r["title"].lower()], key=lambda r: -r["skill"])[:12]:
    print(f"   {r['side']} at {r['cost']:.2f}  session {r['session']:.2f} price {r['price_yes']:.2f} hit {int(r['hit'])}  {r['q'][:70]}")
print("\nLADDERS: centre and width against the market")
for d in ladders:
    if d["m50"] is None or d["m_width"] in (None, 0):
        continue
    d["centre_gap"] = (d["s50"] - d["m50"]) / d["m_width"]; d["width_ratio"] = d["s_width"] / d["m_width"]
    d["outcome_vs_market"] = None if d["outcome_mid"] is None else (d["outcome_mid"] - d["m50"]) / d["m_width"]
ok = [d for d in ladders if "centre_gap" in d]
print(f"  variables {len(ok)}; session width / market width: median {np.median([d['width_ratio'] for d in ok]):.2f}, "
      f"share wider {np.mean([d['width_ratio'] > 1 for d in ok]):.2f}")
cg = [d["centre_gap"] for d in ok]; print(f"  session centre minus market centre, in market widths: median {np.median(cg):+.2f}, share below market {np.mean([x < 0 for x in cg]):.2f}")
ov = [d for d in ok if d["outcome_vs_market"] is not None]
print(f"  outcome minus market centre, in market widths: median {np.median([d['outcome_vs_market'] for d in ov]):+.2f}; "
      f"outcome outside the market's 25-75 range: {np.mean([abs(d['outcome_vs_market']) > 0.5 for d in ov]):.2f} (a calibrated market: 0.50)")
same = [d for d in ov if np.sign(d["centre_gap"]) == np.sign(d["outcome_vs_market"])]
print(f"  outcome landed on the session's side of the market centre: {len(same)} of {len(ov)}")
for d in sorted(ok, key=lambda d: d["centre_gap"])[:5] + sorted(ok, key=lambda d: d["centre_gap"])[-5:]:
    print(f"   {d['as_of']} {d['title'][:48]:48s} side={d['side']} session50={d['s50']:.4g} market50={d['m50']:.4g} gap={d['centre_gap']:+.2f}w width x{d['width_ratio']:.2f} outcome={d['outcome_vs_market'] if d['outcome_vs_market'] is None else round(d['outcome_vs_market'],2)}")
json.dump({"rows": rows, "ladders": ladders}, open(os.path.join(HERE, "bt", "t2", "anatomy.json"), "w", encoding="utf-8"), default=str)
