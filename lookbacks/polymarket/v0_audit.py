"""V0 market-structure audit (descriptive). Output: v0_result.json. See V0_SPEC.md."""
import json, os, re, collections, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
DOMAINS = [  # first match wins; order matters
 ("crypto_launch", r"\btoken\b|\bfdv\b|airdrop|ticker|\blaunch"),
 ("crypto_price", r"bitcoin|ethereum|\bbtc\b|\beth\b|solana|\bxrp\b|crypto|what price will"),
 ("ai_models", r"\bgpt|claude|gemini|openai|anthropic|\bmodel\b|arena|deepseek|\bllm\b|\bgrok\b|best ai"),
 ("fed_rates", r"\bfed\b|fomc|rate hike|rate cut|interest rate|powell|treasury|gilt|yield"),
 ("commodities", r"\bgold\b|crude|\boil\b|\bwti\b|silver|natural gas|brent|copper|\blng\b|\bttf\b|\bjkm\b"),
 ("equities_fx", r"nasdaq|s&p|\bvix\b|stock|\bipo\b|market cap|spacex|microstrategy|coinbase|dollar|\byen\b|sterling|\beuro\b|\bdxy\b|tesla|nvidia|\bspx\b"),
 ("middle_east", r"iran|israel|hezbollah|gaza|houthi|hormuz|airspace|lebanon|syria|saudi|yemen"),
 ("war_ukraine_russia", r"russia|ukraine|capture|\benter\b|kostyant|dobropil|toretsk|putin|zelensk|donbas|kyiv"),
 ("uk_politics", r"\buk\b|starmer|prime minister|clacton|farage|reform uk|secretary|badenoch|labour|tory|conservative|\bmp\b|by-election|gb\b"),
 ("us_politics", r"primary|senate|governor|\bhouse\b|president|trump|republican|democrat|congress|supreme court|\bgop\b|nominee|midterm|\bdoge\b|shutdown"),
 ("europe_politics", r"german|\bafd\b|\bfrance|\bfrench|serbia|orban|hungar|poland|\bitaly|election winner|parliament|chancellor|macron|le pen|\beu\b"),
 ("weather_climate_shipping", r"hurricane|temperature|flood|\brain|rhine|freight|tanker|climate|wildfire|earthquake|shipping|water level"),
 ("sports_entertainment", r"\bnba\b|\bnfl\b|\bmlb\b|world cup|champions|oscars|grammy|super bowl|\bufc\b|wimbledon|f1\b|formula|eurovision|box office|album|movie"),
]
def domain(text):
    t = (text or "").lower()
    for name, rx in DOMAINS:
        if re.search(rx, t): return name
    return "other"
def run():
    out = {}
    # 1 open universe
    rows = json.load(open(os.path.join(HERE, "census_rows.json")))
    act = [r for r in rows if r["status"] == "active"]
    u = [r for r in act if str(r["usable"]) == "True"]
    by = collections.Counter(); byv = collections.Counter()
    for r in act:
        d = domain(r["title"]); by[d] += 1; byv[d] += float(r["vol"] or 0)
    out["open_universe"] = {"active_events": len(act), "usable_active_events": len(u),
        "usable_by_domain": dict(collections.Counter(domain(r["title"]) for r in u).most_common()),
        "active_by_domain": dict(by.most_common()), "volume_share_by_domain": {k: round(v / sum(byv.values()), 3) for k, v in byv.most_common()},
        "usable_by_class": dict(collections.Counter(r["cls"] for r in u).most_common())}
    # 2 menus, 3 demand vs supply
    rounds = sorted(d[1:] for d in os.listdir(os.path.join(HERE, "packets")) if d.startswith("R") and os.path.exists(os.path.join(HERE, "packets", d, "stage1b.json")))
    appear = collections.Counter(); rec = []
    for i in rounds:
        d = os.path.join(HERE, "packets", "R" + i)
        cands = json.load(open(f"{d}/stage1b.json"))["candidates"]; a1 = json.load(open(f"{d}/answer_1a.json")); a2 = json.load(open(f"{d}/answer_1b.json"))
        for c in cands: appear[c["title"]] += 1
        menu_dom = collections.Counter(domain(c["title"]) for c in cands)
        want = collections.Counter(domain(t) for t in a1["search_terms"]); want.pop("other", None)
        prim = domain(re.search(r"THE PRIMARY EVENT: (.*)", open(f"{d}/stage1b.txt").read()).group(1))
        private = json.load(open(f"{d}/private_1b.json"))
        chosen = []
        for h in a2.get("hedges", []):
            k = h.get("event") or h["contract"].split(".")[0]
            title = next((c["title"] for c in cands if c["label"] == k), ""); chosen.append(domain(title))
        rec.append({"round": i, "primary_domain": prim, "menu_size": len(cands), "wanted": dict(want), "wanted_available": {w: menu_dom.get(w, 0) for w in want},
                    "share_wanted_domains_with_supply": (sum(1 for w in want if menu_dom.get(w, 0) > 0) / len(want)) if want else None,
                    "outcome": "no_instrument" if a2.get("no_instrument") else "hedged", "hedge_domains": chosen,
                    "hedge_same_domain_as_primary": bool(chosen) and all(c == prim for c in chosen)})
    out["menus"] = {"rounds": len(rounds), "distinct_events": len(appear), "appear_in_all_24": [t for t, n in appear.items() if n == len(rounds)], "top": appear.most_common(12),
                    "menu_domain_totals": dict(collections.Counter(domain(t) for t in appear).most_common())}
    demand = collections.Counter(); supplied = collections.Counter()
    for r in rec:
        for w in r["wanted"]: demand[w] += 1; supplied[w] += 1 if r["wanted_available"][w] > 0 else 0
    out["demand_vs_supply"] = {w: {"rounds_asking": demand[w], "rounds_with_supply_in_menu": supplied[w]} for w in demand}
    hed = [r for r in rec if r["outcome"] == "hedged"]; ni = [r for r in rec if r["outcome"] == "no_instrument"]
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    out["by_outcome"] = {"hedged": {"n": len(hed), "mean_share_wanted_with_supply": mean([r["share_wanted_domains_with_supply"] for r in hed if r["share_wanted_domains_with_supply"] is not None]), "hedge_same_domain_as_primary": sum(r["hedge_same_domain_as_primary"] for r in hed)},
                         "no_instrument": {"n": len(ni), "mean_share_wanted_with_supply": mean([r["share_wanted_domains_with_supply"] for r in ni if r["share_wanted_domains_with_supply"] is not None])}}
    out["rounds"] = rec
    # 4 volume: event-level USD volume fetched from Gamma for every event a session hedged with and a seeded sample of menu events
    import random, sys as _s; _s.path.insert(0, os.path.join(HERE, "..", "..")); import v1_pool as P
    from concurrent.futures import ThreadPoolExecutor
    menu_ids, hedge_ids = set(), set()
    for i in rounds:
        d = os.path.join(HERE, "packets", "R" + i); priv = json.load(open(f"{d}/private_1b.json")); a2 = json.load(open(f"{d}/answer_1b.json"))
        menu_ids |= {v["event_id"] for k, v in priv.items() if "." not in k and "event_id" in v}
        for h in a2.get("hedges", []):
            k = h.get("event") or h["contract"].split(".")[0]
            if k in priv and "event_id" in priv[k]: hedge_ids.add(priv[k]["event_id"])
    sample = sorted(menu_ids); random.Random(7).shuffle(sample); sample = sample[:150]
    def vol(eid):
        try: return float(P.page(f"{P.GAMMA}/{eid}").get("volume") or 0)
        except Exception: return None
    with ThreadPoolExecutor(8) as ex: hv = list(ex.map(vol, sorted(hedge_ids))); mv = list(ex.map(vol, sample))
    hv = [x for x in hv if x is not None]; mv = [x for x in mv if x is not None]
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))] if xs else None
    out["volume_usd"] = {"menu_events_sample": {"n": len(mv), "of_distinct_menu_events": len(menu_ids), "p25": q(mv, .25), "median": q(mv, .5), "p75": q(mv, .75), "share_under_100k": sum(x < 1e5 for x in mv) / len(mv)},
                         "hedge_events": {"n": len(hv), "p25": q(hv, .25), "median": q(hv, .5), "p75": q(hv, .75), "share_under_100k": sum(x < 1e5 for x in hv) / len(hv)}}
    json.dump(out, open(os.path.join(HERE, "v0_result.json"), "w"), indent=1)
    return out
if __name__ == "__main__":
    o = run()
    print(json.dumps({k: o[k] for k in ("open_universe", "menus", "demand_vs_supply", "by_outcome", "volume_usd")}, indent=1)[:6000])
