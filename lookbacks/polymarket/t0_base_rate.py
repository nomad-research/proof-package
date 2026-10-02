"""Post-hoc (2026-10-01, after T0): the T0 claims against a kind-and-price matched base rate. Not registered; R20 hypothesis only.
Output: t0_base_rate.json. Write-up: T0_BASE_RATE.md.

Why: the V1 pool admitted events by their actual close time and locked each at the midpoint of start and close (V1_prereg.md A9). v18 §6.7 records that a
close-time rule over-selects date ladders that closed early on a Yes rung. So every priced contract shown in V1 and V1b (primary and menu) is scored at its
lock price with no claim at all, by event kind and price band, and each T0 claim is compared with contracts of the same kind within 0.05 of its lock price.

Read-only: each round's prices.db is copied to a temporary directory and the price fetch is disabled, so only cached points are read and no study file is
written. The frozen scorer (v1_score.load_round) is used unchanged."""
import builtins, collections, json, os, shutil, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import v1_score as S
from nomad16 import prices
from nomad16.db import DB

prices.fetch_polymarket = lambda *a, **k: None          # cached points only; nothing is fetched or written into a study's prices.db
CONTAINER = "/home/user/Nomad-Research/"                  # V1b's pool files are git symlinks to this path; where symlinks are not checked out they are text


def _resolve(p):
    p = str(p)
    try:
        if os.path.isfile(p) and os.path.getsize(p) < 300:
            with builtins.open(p, "rb") as fh:
                t = fh.read().decode("utf-8", "ignore").strip()
            if t.startswith(CONTAINER):
                return os.path.join(ROOT, *t[len(CONTAINER):].split("/"))
    except OSError:
        pass
    return p


S.open = lambda p, *a, **k: builtins.open(_resolve(p), *a, **k)
_res0 = S._res
S._res = lambda p: _res0(_resolve(p))
TMP = tempfile.mkdtemp(prefix="t0_base_rate_")
rng = np.random.default_rng(20261001)


def price_fn(R, d, tag):
    cp = os.path.join(TMP, f"{tag}.db"); shutil.copyfile(os.path.join(d, "prices.db"), cp); db = DB(cp)
    class V:
        manifest = None
        def led(self, t, w="", p=()): return db.rows(t, w, p)
    view, lock, done = V(), R["lock"], {}
    def price_of(tok):
        if tok not in done:
            done[tok] = prices.pm_price_at(view, tok, lock)
        return done[tok]
    return price_of


def boot(sub, key):
    """Mean of key with a 90% interval resampled by round, and P(mean > 0)."""
    by = collections.defaultdict(list)
    for x in sub:
        by[x["round"]].append(key(x))
    ks = list(by); m = [np.mean([y for i in rng.choice(len(ks), len(ks)) for y in by[ks[i]]]) for _ in range(4000)]
    return {"n": len(sub), "rounds": len(ks), "mean": float(np.mean([key(x) for x in sub])),
            "ci90": [float(np.quantile(m, .05)), float(np.quantile(m, .95))], "p_positive": float(np.mean(np.array(m) > 0))}


def main():
    rows = []
    for base, tag in ((HERE, "v1"), (os.path.join(HERE, "v1b"), "v1b")):
        for f in sorted(os.listdir(os.path.join(base, "results"))):
            r = json.load(open(os.path.join(base, "results", f)))
            if r.get("status") != "scored":
                continue
            eid = r["round_id"][1:]; S.HERE = base
            R, d = S.load_round(eid); pf = price_fn(R, d, f"{tag}_{eid}")
            evs = [("primary", R["primary"]["kind"], list(R["primary"]["contracts"].values()))] + [(lab, v["kind"], v["contracts"]) for lab, v in R["menu"].items()]
            for lab, kind, cs in evs:
                for c in cs:
                    p, _ = pf(c["tok_yes"])
                    if p is not None:
                        rows.append({"study": tag, "round": eid, "role": "primary" if lab == "primary" else "menu", "kind": kind, "cid": c["cid"],
                                     "p": float(p), "yes": float(bool(c["yes_won"]))})
    out = {"base": {}, "claims": {}}
    ex = lambda x: x["yes"] - x["p"]
    for kind in sorted({x["kind"] for x in rows}):
        sub = [x for x in rows if x["kind"] == kind]
        out["base"][kind] = {"all": dict(boot(sub, ex), cids=len({x["cid"] for x in sub}), mean_price=float(np.mean([x["p"] for x in sub])))}
        for lo, hi in ((0, .2), (.2, .5), (.5, .8), (.8, 1.01)):
            b = [x for x in sub if lo <= x["p"] < hi]
            if b:
                out["base"][kind][f"band_{lo}_{hi}"] = dict(boot(b, ex), mean_price=float(np.mean([x["p"] for x in b])))
    dl = [x for x in rows if x["kind"] == "date ladder" and 0.05 <= x["p"] <= 0.6]
    out["base"]["date ladder"]["band_0.05_0.60_where_tiers_land"] = dict(boot(dl, ex), mean_price=float(np.mean([x["p"] for x in dl])))

    t0 = json.load(open(os.path.join(HERE, "t0_report.json")))
    kind_of = {(x["round"], x["cid"]): x["kind"] for x in rows}
    cl = []
    for c in t0["claims"]:
        k = kind_of.get((c["round"], c["then_cid"]))
        if k is None:
            continue
        v = [ex(x) for x in rows if x["kind"] == k and abs(x["p"] - c["q_lock"]) <= 0.05 and x["cid"] != c["then_cid"]]
        if v:
            cl.append(dict(c, then_kind=k, base=float(np.mean(v)), excess=c["hit"] - c["q_lock"], vs_base=(c["hit"] - c["q_lock"]) - float(np.mean(v))))
    seen, trig = set(), []
    for x in cl:                                           # de-duplicated among triggered claims, as T0's corrected count
        if x["antecedent_happened"] and (x["round"], x["then_cid"]) not in seen:
            seen.add((x["round"], x["then_cid"])); trig.append(x)
    sets = {"tier_at_lock": [x for x in cl if x["kind"] == "tier"], "contract_at_lock": [x for x in cl if x["kind"] == "contract"],
            "tier_if_happened_dedup": [x for x in trig if x["kind"] == "tier"], "contract_if_happened_dedup": [x for x in trig if x["kind"] == "contract"],
            "all_if_happened_dedup": trig, "tier_if_not_happened": [x for x in cl if x["kind"] == "tier" and not x["antecedent_happened"]]}
    for name, s in sets.items():
        out["claims"][name] = {"claim_excess": boot(s, lambda x: x["excess"])["mean"], "matched_base": float(np.mean([x["base"] for x in s])),
                               "claim_minus_base": boot(s, lambda x: x["vs_base"]), "then_kinds": dict(collections.Counter(x["then_kind"] for x in s))}
    json.dump(out, open(os.path.join(HERE, "t0_base_rate.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


main()
