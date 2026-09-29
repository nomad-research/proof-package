"""Stories, loadings, angle classes, junctions and S⊥ (§7.4-§7.6, §20.2-§20.4).

Reads prices (through the vintage store, strictly before the segment clock), positions
and the stores. **Never writes effects, ACKs, reachable sets or theses** (smoke 28).

Units. Angles, projections and ρ are in residual-volatility units: an instrument's
coordinate is its expected move divided by its tide-hedged residual volatility at the
horizon. Loadings are the response to a one-standard-deviation daily story move, in the
same units.
"""
from __future__ import annotations

import math

import numpy as np

from . import config, prices
from .conditions import visible_positions
from .db import DB, Refused
from .derive import scope_nodes
from .instruments import LINEAR, OPTION, listed_before
from .util import day, le, ts

MIN_SESSIONS = 30


# ----------------------------------------------------------------------------- registry
def story_add(db: DB, story_id: str, label: str, path_nodes: list[str], proxy: list[str] | None = None,
              construction_rule: dict | None = None, origin: str = "operator",
              round_id: str | None = None) -> dict:
    if bool(proxy) == bool(construction_rule):
        raise Refused("a story has either a proxy series or a construction rule (§20.2)")
    if origin not in {"operator", "decider_proposed", "junction"}:
        raise Refused("origin is operator, decider_proposed or junction")
    if not path_nodes:
        raise Refused("a story is a path through the graph: name its nodes")
    return db.upsert("stories", story_id, label=label, path_nodes=path_nodes,
                     loading_kind="estimated" if proxy else "constructed", proxy=proxy or [],
                     construction_rule=construction_rule, origin=origin, round_id=round_id)


def story_active(db: DB, round_id: str, story_id: str, evidence_id: str, basis: str) -> dict:
    """The operator names a story as running, citing a source knowable before the clock."""
    from .rounds import current_segment, require_pre_lock
    require_pre_lock(db, round_id)
    seg = current_segment(db, round_id)
    ev = db.one("evidence", "evidence_id=?", (evidence_id,))
    if ev is None:
        raise Refused(f"no evidence {evidence_id}")
    if not le(ev["knowable_from"], seg["clock"]):
        raise Refused("the source naming a story as active must be knowable before the segment clock")
    if db.get("stories", story_id) is None:
        raise Refused(f"no story {story_id}")
    return db.append("notes", round_id=round_id, segment_idx=seg["idx"],
                     subject=f"story_active:{story_id}", text=f"{evidence_id} | {basis}")


# ----------------------------------------------------------------------------- stats
def _ols(y: np.ndarray, X: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    s2 = float(resid @ resid) / dof
    try:
        cov = s2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        se = np.full(X.shape[1], np.nan)
    return beta, se, resid


def _aligned(view, symbols: list[str], clock: str, n: int):
    import pandas as pd
    cols = {}
    for s in symbols:
        r = prices.returns(view, s, before=clock)
        if not r.empty:
            cols[s] = r
    if not cols:
        return pd.DataFrame()
    df = pd.DataFrame(cols).dropna()
    return df.iloc[-n:]


class Context:
    """Everything a segment's stories and construction read, computed once per view."""

    def __init__(self, view, round_row: dict, clock: str):
        self.view, self.round, self.clock = view, round_row, clock
        tide_id = _round_meta(view, round_row["round_id"], "tide_id")
        tide = view.mget("tides", tide_id) if tide_id else None
        if not tide or not tide.get("proxy"):
            raise Refused("declare the round's tide (tide_declare) with a proxy before loadings")
        self.tide_id, self.tide_symbol = tide_id, tide["proxy"]
        self.nodes = scope_nodes(view, round_row["node"])
        self.gaps: list[str] = []
        self.instruments = self._reach()
        self.linear = [i for i in self.instruments if i["kind"] in LINEAR]
        self.stats = {}
        n = int(config.get("LOADING_SESSIONS"))
        for i in self.linear:
            df = _aligned(view, [i["symbol"], self.tide_symbol], clock, max(n, int(config.get("BAND_RULE")["history_sessions"])))
            if len(df) < MIN_SESSIONS:
                self.gaps.append(f"{i['key']}: not_covered (fewer than {MIN_SESSIONS} sessions before {day(clock)})")
                continue
            hist = df
            est = df.iloc[-n:]
            X = np.column_stack([np.ones(len(est)), est[self.tide_symbol].values])
            b, se, e = _ols(est[i["symbol"]].values, X)
            Xh = np.column_stack([np.ones(len(hist)), hist[self.tide_symbol].values])
            _, _, eh = _ols(hist[i["symbol"]].values, Xh)
            fr = prices.frame(view, i["symbol"], before=clock)
            self.stats[i["key"]] = {
                "sigma": float(np.std(e, ddof=1)), "beta": float(b[1]), "beta_se": float(se[1]),
                "resid_hist": eh, "raw_hist": hist[i["symbol"]].values,
                "price": float(fr["close"].iloc[-1]), "price_date": fr.index[-1],
                "adv": float(np.nanmean(fr["volume"].astype(float).values[-20:])),
                "mult": float(i.get("multiplier") or 1.0), "n": len(est)}
        self.linear = [i for i in self.linear if i["key"] in self.stats]
        self.index = [i["key"] for i in self.linear]
        t = _aligned(view, [self.tide_symbol], clock, n)
        self.tide_sd = float(np.std(t[self.tide_symbol].values, ddof=1)) if len(t) > 2 else float("nan")
        self._band_cache = {}

    # instruments whose holder is in reach: a forward effect in this round, or a documented
    # position on a scope node (hedge instruments such as an index holder on an attribute node)
    def _reach(self):
        rid = self.round["round_id"]
        eff_holders = {e["holder_id"] for e in self.view.led("effects", "round_id=?", (rid,))
                       if not e.get("vetoed_by")}
        pos_holders = {p["holder_id"] for p in visible_positions(self.view, self.clock, nodes=self.nodes)
                       if p["confidence"] == "stated"}
        reach = eff_holders | pos_holders
        out = []
        for i in self.view.mut("instruments"):
            if not listed_before(i, self.clock):
                continue
            if i["kind"] in LINEAR and i.get("holder_id") in reach:
                out.append(i)
            elif i["kind"] in OPTION:
                u = self.view.mget("instruments", i.get("underlying") or "")
                if u and u.get("holder_id") in reach and (not i.get("expiry") or ts(i["expiry"]) > ts(self.clock)):
                    out.append(i)
        return sorted(out, key=lambda r: r["key"])

    def band(self, key: str, h: int) -> float:
        """Hedged-residual noise band (return units) at horizon h: BAND_RULE."""
        ck = (key, h)
        if ck not in self._band_cache:
            br = config.get("BAND_RULE")
            self._band_cache[ck] = prices.block_bootstrap_quantile(
                self.stats[key]["resid_hist"], h, float(br["quantile"]), int(config.get("BOOTSTRAP_BLOCK")),
                int(config.get("BOOTSTRAP_DRAWS")))
        return self._band_cache[ck]

    def stress(self, key: str, h: int, side: int) -> float:
        return prices.adverse_quantile(self.stats[key]["raw_hist"], h, float(config.get("STRESS_QUANTILE")),
                                       int(config.get("BOOTSTRAP_BLOCK")), int(config.get("BOOTSTRAP_DRAWS")), side)

    def tide_vec(self) -> np.ndarray:
        return np.array([self.stats[k]["beta"] * self.tide_sd / self.stats[k]["sigma"] for k in self.index])


def _round_meta(view, round_id, field):
    rows = view.led("round_meta", "round_id=? AND field=?", (round_id, field))
    return rows[-1]["value"] if rows else None


def horizon(ack: dict, clock: str) -> int:
    end = ack.get("window_to") or ack.get("due_at")
    cap = 63
    if not end:
        return cap
    h = prices.business_days_between(clock, end)
    return int(min(max(h, 1), cap))


# ----------------------------------------------------------------------------- loadings
def loadings(ctx: Context) -> dict:
    """Per story: {'vec': vol-unit loading over ctx.index, 'kind', 'se', 'active', 'basis', ...}."""
    view, clock = ctx.view, ctx.clock
    rid = ctx.round["round_id"]
    stories = [s for s in view.mut("stories") if s.get("round_id") in (None, rid)]
    named = {}
    for n in view.led("notes", "round_id=?", (rid,)):
        if str(n["subject"]).startswith("story_active:"):
            named[n["subject"].split(":", 1)[1]] = n["text"]
    out = {}
    n = int(config.get("LOADING_SESSIONS"))
    est = [s for s in stories if s["loading_kind"] == "estimated"]
    # joint regression r_i = a + b tide + sum_k L_ik f_k (§20.2)
    fac = {}
    for s in est:
        df = _aligned(view, s["proxy"], clock, n + 400)
        if df.empty:
            ctx.gaps.append(f"story {s['key']}: not_covered (no proxy prices)")
            continue
        fac[s["key"]] = df.mean(axis=1)
    import pandas as pd
    L = {k: np.zeros(len(ctx.index)) for k in fac}
    SE = {k: np.zeros(len(ctx.index)) for k in fac}
    if fac:
        F = pd.DataFrame(fac)
        for j, key in enumerate(ctx.index):
            inst = next(i for i in ctx.linear if i["key"] == key)
            df = _aligned(view, [inst["symbol"], ctx.tide_symbol], clock, n + 400).join(F, how="inner").dropna().iloc[-n:]
            if len(df) < MIN_SESSIONS:
                continue
            X = np.column_stack([np.ones(len(df)), df[ctx.tide_symbol].values] + [df[k].values for k in fac])
            b, se, _ = _ols(df[inst["symbol"]].values, X)
            sig = ctx.stats[key]["sigma"]
            for m, k in enumerate(fac):
                sdf = float(np.std(df[k].values, ddof=1))
                L[k][j] = b[2 + m] * sdf / sig
                SE[k][j] = se[2 + m] * sdf / sig
    for s in stories:
        k = s["key"]
        rec = {"story_id": k, "label": s["label"], "kind": s["loading_kind"], "path_nodes": s["path_nodes"],
               "origin": s["origin"]}
        if s["loading_kind"] == "estimated":
            if k not in fac:
                continue
            rec["vec"], rec["se"] = L[k], SE[k]
            f = fac[k]
            f = f[f.index < day(clock)]
            aw = int(config.get("ACTIVE_WINDOW"))
            cum = float(f.iloc[-aw:].sum()) if len(f) >= aw else float("nan")
            band = prices.block_bootstrap_quantile(f.values[:-aw] if len(f) > aw + 30 else f.values, aw,
                                                   float(config.get("BAND_RULE")["quantile"]),
                                                   int(config.get("BOOTSTRAP_BLOCK")),
                                                   int(config.get("BOOTSTRAP_DRAWS")))
            moved = bool(abs(cum) > band) if not math.isnan(cum) and not math.isnan(band) else False
            rec["active"] = moved or k in named
            rec["active_basis"] = ("proxy moved outside its noise band" if moved else "") + \
                                  ((" | named: " + named[k]) if k in named else "")
            rec["proxy_move"], rec["proxy_band"] = cum, band
            rec["window"] = (f.index[-n] if len(f) >= n else f.index[0], f.index[-1])
        else:
            rule = s["construction_rule"] or {}
            vals = []
            for key in ctx.index:
                inst = next(i for i in ctx.linear if i["key"] == key)
                nodes = [rule["node"]] if rule.get("node") else ctx.nodes
                rows = [p for p in visible_positions(view, clock, inst["holder_id"], nodes, rule.get("attribute"))
                        if p["confidence"] == "stated" and p["value_num"] is not None]
                vals.append(rows[-1]["value_num"] if rows else None)
            known = [v for v in vals if v is not None]
            vec = np.zeros(len(ctx.index))
            if known:
                mu = float(np.mean(known))
                sd = float(np.std(known)) if len(known) > 1 else 0.0
                for j, v in enumerate(vals):
                    if v is None:
                        continue
                    vec[j] = (v - mu) / sd if sd > 0 else (v / max(abs(x) for x in known) if max(abs(x) for x in known) > 0 else 0.0)
            rec["vec"], rec["se"] = vec, np.zeros(len(ctx.index))
            rec["active"] = k in named
            rec["active_basis"] = ("named: " + named[k]) if k in named else "constructed; candidate until named"
            rec["missing"] = [ctx.index[j] for j, v in enumerate(vals) if v is None]
        out[k] = rec
    return out


# ----------------------------------------------------------------------------- S(ω)
def s_vectors(ctx: Context, ack: dict, outcome_ids: list[str], h: int, vetoed: set | None = None) -> dict:
    """Per outcome: expected move per linear instrument (return units), S in vol units, flat flag."""
    rid = ctx.round["round_id"]
    effs = [e for e in ctx.view.led("effects", "round_id=?", (rid,)) if not e.get("vetoed_by")]
    vetoed_ids = set(vetoed or ())
    out = {}
    for w in outcome_ids:
        exp = np.zeros(len(ctx.index))
        unknown = np.zeros(len(ctx.index), dtype=int)
        for j, key in enumerate(ctx.index):
            inst = next(i for i in ctx.linear if i["key"] == key)
            for e in effs:
                if e["holder_id"] != inst["holder_id"] or e["effect_id"] in vetoed_ids:
                    continue
                if e.get("ack_id") not in (None, ack["key"]):
                    continue
                if e.get("outcome_id") not in (None, w):
                    continue
                if e.get("magnitude_pct") is None:
                    unknown[j] += 1
                    continue
                exp[j] += int(e["sign"]) * abs(float(e["magnitude_pct"])) / 100.0
        scale = np.array([ctx.stats[k]["sigma"] * math.sqrt(h) for k in ctx.index])
        S = exp / scale if len(scale) else exp
        bands = np.array([ctx.band(k, h) for k in ctx.index])
        flat = bool(np.all(np.abs(exp) < bands)) if len(bands) else True
        out[w] = {"exp": exp, "S": S, "unknown": unknown, "flat": flat, "bands": bands}
    return out


def shape(svecs: dict, thesis: list[str]) -> tuple[str, np.ndarray | None]:
    nonflat = [w for w in thesis if not svecs[w]["flat"]]
    if not nonflat:
        return "mixed", None  # all flat and no quoted distribution shows a priced move
    Sbar = np.mean([svecs[w]["S"] for w in nonflat], axis=0)
    dots = [float(svecs[w]["S"] @ Sbar) for w in nonflat]
    flats = [w for w in thesis if svecs[w]["flat"]]
    if np.linalg.norm(Sbar) > 0 and all(d > 0 for d in dots):
        return "directional", Sbar
    if any(d > 0 for d in dots) and any(d < 0 for d in dots) and not flats:
        return "long_volatility", Sbar
    return "mixed", Sbar


def _cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return float("nan")
    return float(a @ b / (na * nb))


def classify(L: dict, Sbar: np.ndarray | None, shp: str) -> dict:
    """§20.2 classing in fixed test order. Returns {story_id: {...class...}}."""
    order = sorted(L)
    cos_orth = math.cos(math.radians(float(config.get("ANGLE_ORTH"))))
    eps = float(config.get("SYNTH_EPS"))
    res = {k: {"class": None, "decomposition": [], "active": L[k]["active"]} for k in order}
    # pass 1: synthetic, and activity inherited by its components
    for m, k in enumerate(order):
        earlier = [o for o in order[:m] if res[o]["class"] != "synthetic"]
        v = L[k]["vec"]
        if earlier and np.linalg.norm(v) > 0:
            A = np.column_stack([L[o]["vec"] for o in earlier])
            c, *_ = np.linalg.lstsq(A, v, rcond=None)
            r = v - A @ c
            if np.linalg.norm(r) / np.linalg.norm(v) < eps:
                res[k]["class"] = "synthetic"
                res[k]["decomposition"] = [[o, float(x)] for o, x in zip(earlier, c) if abs(x) > 1e-6]
                if res[k]["active"]:
                    for o, _ in res[k]["decomposition"]:
                        res[o]["active"] = True
                        res[o]["inherited_from"] = k
    # pass 2: angle classes
    for k in order:
        if res[k]["class"] == "synthetic":
            continue
        v = L[k]["vec"]
        c = _cos(v, Sbar) if Sbar is not None else float("nan")
        res[k]["cos"] = c
        res[k]["angle"] = math.degrees(math.acos(max(-1, min(1, c)))) if not math.isnan(c) else None
        if res[k]["active"]:
            if math.isnan(c) or abs(c) <= cos_orth:
                res[k]["class"] = "orthogonal"
            else:
                res[k]["class"] = "parallel"
        elif shp == "directional" and not math.isnan(c) and c > cos_orth:
            res[k]["class"] = "adjacent"
        else:
            res[k]["class"] = "unrelated"
    return res


# ----------------------------------------------------------------------------- junctions
def constrained_nodes(view, round_row, clock) -> set:
    rid = round_row["round_id"]
    out = set()
    for a in view.mut("ack_nodes"):
        if a.get("round_id") == rid and a.get("status") == "ratified" and a.get("ack_kind") == "forced":
            out.add(round_row["node"])
    for f in view.led("node_facts"):
        if f["kind"] in {"no_slack", "constrained"} and le(f["knowable_from"], clock):
            out.add(f["node"])
    return out


def junction_flags(ctx: Context, L: dict) -> list[dict]:
    cn = constrained_nodes(ctx.view, ctx.round, ctx.clock)
    ids = sorted(L)
    out = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = sorted(set(L[a]["path_nodes"]) & set(L[b]["path_nodes"]) & cn)
            for node in shared:
                out.append({"junction_id": f"J:{a}:{b}:{node}", "story_a": a, "story_b": b,
                            "shared_node": node})
    return out


def junction_node_vec(ctx: Context, node: str) -> np.ndarray:
    vals = []
    for key in ctx.index:
        inst = next(i for i in ctx.linear if i["key"] == key)
        rows = [p for p in visible_positions(ctx.view, ctx.clock, inst["holder_id"], [node])
                if p["confidence"] == "stated" and p["value_num"] is not None
                and p["attribute"] in ("node_exposure", "share")]
        vals.append(rows[-1]["value_num"] if rows else 0.0)
    v = np.array(vals, dtype=float)
    sd = float(np.std(v))
    return (v - v.mean()) / sd if sd > 0 else v


def junction_treatments(view, round_id: str, seg_idx: int) -> dict:
    out = {}
    for j in view.led("junctions", "round_id=? AND segment_idx=?", (round_id, seg_idx)):
        if j.get("treatment"):
            out[j["junction_id"]] = j["treatment"]
    return out


def junction_treat(db: DB, round_id: str, junction_id: str, treatment: str, basis: str) -> dict:
    from .rounds import current_segment, require_pre_lock
    require_pre_lock(db, round_id)
    if treatment not in {"merged", "held"}:
        raise Refused("treatment is 'merged' or 'held'")
    seg = current_segment(db, round_id)
    parts = junction_id.split(":")
    if len(parts) != 4 or parts[0] != "J":
        raise Refused("junction ids look like J:<story_a>:<story_b>:<node>")
    return db.append("junctions", junction_id=junction_id, round_id=round_id, segment_idx=seg["idx"],
                     story_a=parts[1], story_b=parts[2], shared_node=parts[3], trigger_ack_id=None,
                     corr_before=None, corr_after=None, status="flagged", treatment=treatment,
                     node_story_id=f"node:{parts[3]}")


# ----------------------------------------------------------------------------- S⊥
def hedged_set(ctx: Context, L: dict, classes: dict, junctions: list[dict], treat: dict) -> tuple[list, np.ndarray]:
    names, cols = ["tide"], [ctx.tide_vec()]
    for k, c in classes.items():
        if c["class"] in {"orthogonal", "parallel"}:
            names.append(k)
            cols.append(L[k]["vec"])
    for j in junctions:
        if treat.get(j["junction_id"]) == "merged":
            names.append(f"node:{j['shared_node']}")
            cols.append(junction_node_vec(ctx, j["shared_node"]))
    return names, np.column_stack(cols) if cols and len(ctx.index) else np.zeros((len(ctx.index), 0))


def s_perp(S: np.ndarray, H: np.ndarray) -> np.ndarray:
    if H.size == 0 or np.linalg.norm(S) == 0:
        return S.copy()
    c, *_ = np.linalg.lstsq(H, S, rcond=None)
    return S - H @ c


# ----------------------------------------------------------------------------- after lock
def junction_confirm(db: DB, round_id: str, segment_idx: int, trigger_date: str) -> dict:
    """§20.3: compare rolling correlations of story factor residuals before and after the
    trigger. A flagged pair that rises by JUNCTION_DELTA is confirmed; an unflagged pair that
    rises as much is a piano, logged and never modelled (smoke 22)."""
    from .view import View
    from .rounds import state
    if state(db, round_id) not in {"walking", "live", "scored"}:
        raise Refused("junctions are confirmed after lock")
    view = View(db)
    rnd = db.one("rounds", "round_id=?", (round_id,))
    tide_id = _round_meta(view, round_id, "tide_id")
    tide = view.mget("tides", tide_id)
    win = int(config.get("JUNCTION_WINDOW"))
    delta = float(config.get("JUNCTION_DELTA"))
    flagged = {(j["story_a"], j["story_b"]) for j in view.led("junctions", "round_id=? AND segment_idx=?",
                                                              (round_id, segment_idx)) if j["status"] == "flagged"}
    import pandas as pd
    est = [s for s in view.mut("stories") if s["loading_kind"] == "estimated" and s.get("round_id") in (None, round_id)]
    fac = {}
    for s in est:
        cols = [prices.returns(view, p, before="2999-01-01") for p in s["proxy"]]
        cols = [c for c in cols if not c.empty]
        if cols:
            fac[s["key"]] = pd.concat(cols, axis=1).mean(axis=1)
    t = prices.returns(view, tide["proxy"], before="2999-01-01")
    F = pd.DataFrame(fac).join(t.rename("tide"), how="inner").dropna()
    for k in fac:  # factor residuals after the tide
        X = np.column_stack([np.ones(len(F)), F["tide"].values])
        b, *_ = np.linalg.lstsq(X, F[k].values, rcond=None)
        F[k] = F[k].values - X @ b
    before = F[F.index < day(trigger_date)].iloc[-win:]
    after = F[F.index >= day(trigger_date)].iloc[:win]
    out = []
    ks = sorted(fac)
    for i, a in enumerate(ks):
        for b_ in ks[i + 1:]:
            if len(before) < 5 or len(after) < 5:
                continue
            cb, ca = float(before[a].corr(before[b_])), float(after[a].corr(after[b_]))
            rise = ca - cb
            is_flag = (a, b_) in flagged or (b_, a) in flagged
            if is_flag:
                st = "confirmed" if rise >= delta else "flagged"
                db.append("junctions", junction_id=f"J:{a}:{b_}:confirm", round_id=round_id, segment_idx=segment_idx,
                          story_a=a, story_b=b_, shared_node=None, trigger_ack_id=None, corr_before=cb, corr_after=ca,
                          status=st, treatment=None, node_story_id=None)
            elif rise >= delta:
                st = "piano"
                n = len(db.rows("pianos")) + 1
                db.append("pianos", piano_id=f"PI{n:03d}", round_id=round_id, basket_id=None,
                          description=f"stories {a} and {b_} correlation rose {cb:.2f} -> {ca:.2f} with no shared "
                                      f"constrained node", outside="junction_without_node", cost=None)
                db.append("junctions", junction_id=f"J:{a}:{b_}:none", round_id=round_id, segment_idx=segment_idx,
                          story_a=a, story_b=b_, shared_node=None, trigger_ack_id=None, corr_before=cb,
                          corr_after=ca, status="piano", treatment=None, node_story_id=None)
            else:
                st = "none"
            out.append({"pair": [a, b_], "corr_before": cb, "corr_after": ca, "status": st})
    return {"pairs": out}
