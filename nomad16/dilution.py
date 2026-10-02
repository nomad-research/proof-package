"""Chain impact, count-dilution buckets and the depth profile (v17 V2 slice; see STATE.md, 2026-09-30).

The model, in the user's words: an effect fans out from a hub like an amplifier and does *not* dilute by nature of
quantity, except where the edge is of a kind whose impact is shared out. Which edges are which is not known in advance and is
not pre-assigned. So:

* Impact is a **node** quantity in noise-band units, not a path count. The impact of a node is built from the
  contributions of the roots behind it. **Paths from the same root are one signal by several routes: the strongest counts,
  they don't add.** Independent roots add (signed).
* An edge passes ``t * n_out(parent) ** -alpha`` of its parent's contribution. ``alpha = 0`` is the amplifier and ``alpha = 1`` is a
  fixed pot shared out; anything between is allowed. ``alpha`` belongs to a *bucket* of edges, and buckets are a
  versioned, post-hoc partition (ledger): proposed from text knowable at lock (an embedding or an LLM does the
  grouping), supported only by a behavioural fit of ``alpha``.
* A bucket with too few observations has **no** alpha: a typed gap. The impact of anything downstream is then an
  interval between the amplifier run (alpha = 0 on the gap edges) and the pot run (alpha = 1). Nothing is defaulted.
* The retention ``r`` of a node is its impact over the impact of the parent that supplies most of it. ``r`` above 1 is a
  convergence concentrating; the next fan-out projects out again. The **bend** is the first depth at which the median
  retention falls by more than ``BEND_TOL`` against the depth before it (the dilution accelerating).

Verdict-governing numbers (``BUCKET_MIN_OBS``, ``BUCKET_SHRINK_K``, ``BEND_TOL``, ``BEND_MIN_NODES``) are appetite values
that are not set: every function that needs one refuses until it is.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from typing import Callable

import numpy as np

from . import config
from .db import DB, Refused
from .util import ts


# ---------------------------------------------------------------- propagation

def _topo(nodes: set[str], edges: list[dict]) -> list[str]:
    indeg = {n: 0 for n in nodes}
    out = defaultdict(list)
    for e in edges:
        indeg[e["to"]] += 1
        out[e["from"]].append(e["to"])
    order, ready = [], sorted(n for n, d in indeg.items() if d == 0)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in sorted(out[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    if len(order) != len(nodes):
        raise Refused("the edge set has a cycle; impact is propagated on a DAG")
    return order


def propagate(roots: dict[str, float], edges: list[dict], alpha: Callable[[dict], float]) -> dict:
    """Node impacts (signed, band units). ``roots`` maps a node to the impact it starts with; each edge is
    ``{from, to, t}`` with ``t`` in [0, 1] (the edge's own transmission)."""
    for e in edges:
        if not (0 <= e["t"] <= 1):
            raise Refused(f"edge {e['from']}->{e['to']}: transmission is in [0, 1]; a gain above 1 is not an edge")
    nodes = set(roots) | {e["from"] for e in edges} | {e["to"] for e in edges}
    fan = defaultdict(int)
    for e in edges:
        fan[e["from"]] += 1
    incoming = defaultdict(list)
    for e in edges:
        incoming[e["to"]].append(e)
    contrib: dict[str, dict[str, float]] = {}
    hops: dict[str, dict[str, int]] = {}
    via: dict[str, dict[str, str]] = {}
    for n in _topo(nodes, edges):
        c: dict[str, float] = {}
        h: dict[str, int] = {}
        v: dict[str, str] = {}
        for e in incoming[n]:
            f = e["t"] * fan[e["from"]] ** (-alpha(e))
            for r, val in contrib[e["from"]].items():
                cand = val * f
                if r not in c or abs(cand) > abs(c[r]):        # same root: the strongest route, never the sum
                    c[r], h[r], v[r] = cand, hops[e["from"]][r] + 1, e["from"]
        if n in roots:
            c[n], h[n] = roots[n], 0
        contrib[n], hops[n], via[n] = c, h, v
    out = {}
    for n in nodes:
        c = contrib[n]
        imp = sum(c.values())
        dom = max(c, key=lambda r: abs(c[r])) if c else None
        out[n] = {"impact": imp, "by_root": c, "dominant_root": dom,
                  "depth": hops[n].get(dom) if dom else None, "dominant_parent": via[n].get(dom) if dom else None,
                  "fan_out": fan[n]}
    for n, d in out.items():
        p = d["dominant_parent"]
        d["retention"] = (abs(d["impact"]) / abs(out[p]["impact"])) if p and out[p]["impact"] else None
    return out


def profile(result: dict) -> list[dict]:
    """Per depth: how many nodes and the median retention. Depth 0 (the roots) has none."""
    by = defaultdict(list)
    for d in result.values():
        if d["depth"] and d["retention"] is not None:
            by[d["depth"]].append(d["retention"])
    return [{"depth": k, "n": len(v), "median_r": float(np.median(v)), "min_r": min(v), "max_r": max(v)}
            for k, v in sorted(by.items())]


def bend(prof: list[dict], tol: float | None = None, min_nodes: int | None = None) -> dict:
    """First depth whose median retention falls by more than ``tol`` (a fraction) against the depth before.
    Depths with fewer than ``min_nodes`` nodes are not used. Fewer than three usable depths: insufficient."""
    tol = config.get("BEND_TOL") if tol is None else tol
    min_nodes = config.get("BEND_MIN_NODES") if min_nodes is None else min_nodes
    use = [p for p in prof if p["n"] >= min_nodes]
    if len(use) < 3:
        return {"status": "insufficient", "usable_depths": len(use), "bend_at": None}
    for a, b in zip(use, use[1:]):
        if b["median_r"] < a["median_r"] * (1 - tol):
            return {"status": "bend", "bend_at": b["depth"], "from_r": a["median_r"], "to_r": b["median_r"],
                    "usable_depths": len(use)}
    return {"status": "no_bend", "bend_at": None, "usable_depths": len(use)}


# ---------------------------------------------------------------------- alpha

def fit_alpha(obs: list[dict], min_obs: int | None = None, shrink_k: float | None = None) -> dict:
    """``obs``: ``{bucket, n, ratio}`` where ``n`` is the parent's fan-out and ``ratio`` the child's observed impact over
    (parent impact x edge transmission). ``ln ratio = -alpha ln n``: fitted through the origin per bucket, then shrunk
    toward the pooled fit with weight ``shrink_k`` in information units. A bucket with fewer than ``min_obs``
    observations at n > 1 is a gap: no alpha."""
    min_obs = config.get("BUCKET_MIN_OBS") if min_obs is None else min_obs
    shrink_k = config.get("BUCKET_SHRINK_K") if shrink_k is None else shrink_k
    for o in obs:
        if o["n"] < 1 or o["ratio"] <= 0:
            raise Refused(f"observation {o}: n >= 1 and ratio > 0 are required")
    by = defaultdict(list)
    for o in obs:
        if o["n"] > 1:
            by[o["bucket"]].append((math.log(o["n"]), math.log(o["ratio"])))

    def raw(pairs):
        s = sum(x * x for x, _ in pairs)
        a = -sum(x * y for x, y in pairs) / s
        res = [y + a * x for x, y in pairs]
        se = math.sqrt(sum(r * r for r in res) / (len(pairs) - 1) / s) if len(pairs) > 1 else None
        return a, s, se

    allpairs = [p for v in by.values() for p in v]
    glob = raw(allpairs) if len(allpairs) >= min_obs else None
    fits = {}
    for b, pairs in sorted(by.items()):
        if len(pairs) < min_obs:
            fits[b] = {"status": "gap", "alpha": None, "alpha_raw": None, "se": None, "n_obs": len(pairs),
                       "information": sum(x * x for x, _ in pairs), "reason": f"fewer than {min_obs} observations at n > 1"}
            continue
        a, s, se = raw(pairs)
        alpha = (s * a + shrink_k * glob[0]) / (s + shrink_k) if glob else a
        fits[b] = {"status": "measured", "alpha": alpha, "alpha_raw": a, "se": se, "n_obs": len(pairs), "information": s}
    return {"fits": fits, "pooled_alpha": glob[0] if glob else None, "min_obs": min_obs, "shrink_k": shrink_k}


def propagate_interval(roots: dict[str, float], edges: list[dict], alphas: dict[str, float | None]) -> dict:
    """``alphas`` maps a bucket to its measured alpha, or None (a gap). An edge with no measured alpha and a parent
    that fans out makes the result an interval: the amplifier run (alpha 0 on gaps) and the pot run (alpha 1)."""
    fan = defaultdict(int)
    for e in edges:
        fan[e["from"]] += 1

    def make(default):
        return lambda e: alphas.get(e.get("bucket")) if alphas.get(e.get("bucket")) is not None else default

    gaps = [f"{e['from']}->{e['to']}" for e in edges if fan[e["from"]] > 1 and alphas.get(e.get("bucket")) is None]
    amp, pot = propagate(roots, edges, make(0.0)), propagate(roots, edges, make(1.0))
    return {"amplifier": amp, "pot": pot, "gap_edges": gaps,
            "interval": {n: (min(abs(amp[n]["impact"]), abs(pot[n]["impact"])),
                             max(abs(amp[n]["impact"]), abs(pot[n]["impact"]))) for n in amp}}


# -------------------------------------------------------------------- buckets

def _features(text: str, dim: int = 512) -> np.ndarray:
    t = re.sub(r"\s+", " ", text.lower())
    v = np.zeros(dim)
    for i in range(len(t) - 2):
        v[int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16) % dim] += 1
    n = np.linalg.norm(v)
    return v / n if n else v


def bucket_propose(texts: dict[str, str], threshold: float) -> dict:
    """A deterministic stand-in for the embedding step: character-trigram vectors, single-link groups at cosine
    ``threshold`` (explicit, not defaulted). It is a proposal generator. An embedding model or an LLM can replace it: any
    partition goes through ``bucket_partition_add``. Text similarity groups by topic; only a behavioural fit supports a bucket."""
    if not 0 < threshold < 1:
        raise Refused("threshold is between 0 and 1")
    keys = sorted(texts)
    vecs = np.array([_features(texts[k]) for k in keys])
    sim = vecs @ vecs.T
    parent = list(range(len(keys)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if sim[i, j] >= threshold:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i, k in enumerate(keys):
        groups[find(i)].append(k)
    ordered = sorted(groups.values(), key=lambda g: g[0])
    return {"status": "proposal", "buckets": {f"b{n + 1}": g for n, g in enumerate(ordered)}, "threshold": threshold,
            "method": "hashed-trigram single-link"}


def bucket_partition_add(db: DB, version_id: str, method: str, embedder: str, embedder_trained_through: str,
                         knowable_cutoff: str, assignments: dict, note: str = "") -> dict:
    """Record a partition of edges into buckets as a new ledger version. ``assignments`` maps an edge key to
    ``{bucket, text, text_knowable_from, label?}``. The text must have been knowable by ``knowable_cutoff`` (the
    lock it will be pinned by), and the embedder's training cutoff is recorded. A version is a proposal until fitted."""
    if db.one("bucket_versions", "version_id=?", (version_id,)):
        raise Refused(f"{version_id} exists; a re-grouping is a new version")
    ts(embedder_trained_through)
    cut = ts(knowable_cutoff)
    if not assignments:
        raise Refused("an empty partition")
    for k, a in assignments.items():
        if not {"bucket", "text", "text_knowable_from"} <= set(a):
            raise Refused(f"assignment {k} needs bucket, text and text_knowable_from")
        if ts(a["text_knowable_from"]) > cut:
            raise Refused(f"assignment {k}: its text became knowable after the cutoff; the bucket would be formed on the future")
    h = hashlib.sha256("|".join(f"{k}:{assignments[k]['bucket']}:{assignments[k]['text']}" for k in sorted(assignments)).encode()).hexdigest()
    db.append("bucket_versions", version_id=version_id, method=method, embedder=embedder,
              embedder_trained_through=embedder_trained_through, features_hash=h, knowable_cutoff=knowable_cutoff,
              status="proposal", note=note)
    for k, a in sorted(assignments.items()):
        db.append("bucket_assignments", version_id=version_id, edge_key=k, bucket=a["bucket"], label=a.get("label"),
                  text_hash=hashlib.sha256(a["text"].encode()).hexdigest(), text_knowable_from=a["text_knowable_from"])
    return {"version_id": version_id, "n_edges": len(assignments), "features_hash": h, "status": "proposal"}


def bucket_fit(db: DB, version_id: str, observations: list[dict], fitted_on: str) -> dict:
    """Fit alpha per bucket of a version from observations ``{edge_key, n, ratio}`` and append one fit row per bucket."""
    if not db.one("bucket_versions", "version_id=?", (version_id,)):
        raise Refused(f"no bucket version {version_id}")
    amap = {a["edge_key"]: a["bucket"] for a in db.rows("bucket_assignments", "version_id=?", (version_id,))}
    obs = []
    for o in observations:
        if o["edge_key"] not in amap:
            raise Refused(f"edge {o['edge_key']} is not in partition {version_id}")
        obs.append({"bucket": amap[o["edge_key"]], "n": o["n"], "ratio": o["ratio"]})
    res = fit_alpha(obs)
    for b in sorted(set(amap.values())):
        f = res["fits"].get(b) or {"status": "gap", "alpha": None, "alpha_raw": None, "se": None, "n_obs": 0, "information": 0.0}
        db.append("bucket_fits", version_id=version_id, bucket=b, status=f["status"], alpha=f["alpha"], alpha_raw=f["alpha_raw"],
                  se=f["se"], n_obs=f["n_obs"], information=f["information"], shrink_k=res["shrink_k"],
                  min_obs=res["min_obs"], fitted_on=fitted_on)
    return res


def latest_alphas(db: DB, version_id: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for a in db.rows("bucket_assignments", "version_id=?", (version_id,)):
        out.setdefault(a["bucket"], None)
    for f in db.rows("bucket_fits", "version_id=?", (version_id,), order="id"):   # later rows supersede
        out[f["bucket"]] = f["alpha"] if f["status"] == "measured" else None
    return out


def depth_profile(db: DB, roots: dict, edges: list[dict], version_id: str | None = None) -> dict:
    """The chain report: node impacts as an interval where a bucket has no measured alpha, the retention profile on
    each run and the bend. An edge names its ``key``; its bucket is read from the version's partition."""
    alphas: dict = {}
    if version_id:
        if not db.one("bucket_versions", "version_id=?", (version_id,)):
            raise Refused(f"no bucket version {version_id}")
        amap = {a["edge_key"]: a["bucket"] for a in db.rows("bucket_assignments", "version_id=?", (version_id,))}
        edges = [{**e, "bucket": amap.get(e.get("key"), e.get("bucket"))} for e in edges]
        alphas = latest_alphas(db, version_id)
    r = propagate_interval(roots, edges, alphas)
    out = {"gap_edges": r["gap_edges"], "interval": r["interval"], "profile_amplifier": profile(r["amplifier"]),
           "profile_pot": profile(r["pot"])}
    for name in ("amplifier", "pot"):
        try:
            out[f"bend_{name}"] = bend(out[f"profile_{name}"])
        except config.MissingAppetite as e:
            out[f"bend_{name}"] = {"status": "refused", "reason": str(e)}
    return out


# ------------------------------------------------------------- profile mode

def refuse_as_support(obj: dict) -> None:
    """A guard for anything that would consume a profile as support: a report-only object is refused."""
    if isinstance(obj, dict) and obj.get("report_only"):
        raise Refused("the dilution profile is report-only: it is never support for an ACK, call, basket, veto or lock")


def profile_expand(db: DB, roots: dict, edges: list[dict], version_id: str | None = None,
                   depth: int | None = None, budget: int | None = None) -> dict:
    """Report-only. Expand the candidate edges from the roots to ``PROFILE_DEPTH_MAX`` hops, **past**
    ``SUPPORT_THRESHOLD``, bounded by ``ENTITY_MATERIALISE_MAX``, and report impact, retention, where support
    ran out and where the dilution bends. Reads only: it writes no row and its output is marked
    ``report_only`` so ``refuse_as_support`` refuses it.

    Only edges that go strictly deeper (by fewest hops from a root) are followed, so no chain is longer than the
    depth limit; the number left out is reported. Over the budget, nodes are kept shallowest first, then by
    impact, and the truncation is reported, never silent."""
    depth = config.get("PROFILE_DEPTH_MAX") if depth is None else depth
    budget = config.get("ENTITY_MATERIALISE_MAX") if budget is None else budget
    thr = config.get("SUPPORT_THRESHOLD")
    alphas: dict = {}
    if version_id:
        if not db.one("bucket_versions", "version_id=?", (version_id,)):
            raise Refused(f"no bucket version {version_id}")
        amap = {a["edge_key"]: a["bucket"] for a in db.rows("bucket_assignments", "version_id=?", (version_id,))}
        edges = [{**e, "bucket": amap.get(e.get("key"), e.get("bucket"))} for e in edges]
        alphas = latest_alphas(db, version_id)
    out_edges = defaultdict(list)
    for e in edges:
        out_edges[e["from"]].append(e)
    mind = {r: 0 for r in roots}
    frontier = sorted(roots)
    while frontier:
        nxt = []
        for u in frontier:
            if mind[u] >= depth:
                continue
            for e in out_edges[u]:
                if e["to"] not in mind:
                    mind[e["to"]] = mind[u] + 1
                    nxt.append(e["to"])
        frontier = sorted(nxt)
    kept = [e for e in edges if e["from"] in mind and e["to"] in mind and mind[e["to"]] > mind[e["from"]]]
    left_out = sum(1 for e in edges if e["from"] in mind and e["to"] in mind) - len(kept)
    nodes = set(roots) | {e["from"] for e in kept} | {e["to"] for e in kept}
    truncated, dropped = False, []
    if len(nodes) > budget:
        full = propagate_interval(roots, kept, alphas)
        rank = sorted((n for n in nodes if n not in roots),
                      key=lambda n: (mind[n], -max(full["interval"][n]), n))
        keep_n = set(rank[:max(budget - len(roots), 0)])
        dropped = sorted(set(rank) - keep_n)
        truncated = True
        kept = [e for e in kept if (e["from"] in roots or e["from"] in keep_n) and (e["to"] in keep_n)]
        nodes = set(roots) | {e["from"] for e in kept} | {e["to"] for e in kept}
    r = propagate_interval(roots, kept, alphas)
    amp = r["amplifier"]
    levels = defaultdict(lambda: {"n": 0, "at_or_above_support": 0})
    for n, d in amp.items():
        if d["depth"]:
            root = d["dominant_root"]
            sup = abs(d["by_root"][root]) / abs(roots[root]) if roots[root] else 0.0
            lv = levels[d["depth"]]
            lv["n"] += 1
            lv["at_or_above_support"] += int(sup >= thr)
    horizon = max((k for k, v in levels.items() if v["at_or_above_support"]), default=0)
    res = {"report_only": True, "supports": False, "depth_max": depth, "support_threshold": thr,
           "budget": budget, "nodes": len(nodes), "truncated": truncated, "dropped": len(dropped),
           "edges_followed": len(kept), "edges_not_followed_not_deeper": left_out,
           "support_horizon": horizon, "by_depth": {k: dict(v) for k, v in sorted(levels.items())},
           "beyond_support_nodes": sum(v["n"] - v["at_or_above_support"] for v in levels.values()),
           "gap_edges": r["gap_edges"], "interval": r["interval"],
           "profile_amplifier": profile(r["amplifier"]), "profile_pot": profile(r["pot"])}
    for name in ("amplifier", "pot"):
        res[f"bend_{name}"] = bend(res[f"profile_{name}"])
    return res


def holds(first_fit: dict, later_obs: list[dict], min_obs: int | None = None) -> dict:
    """The ratification test for a bucket's alpha (RATIFICATIONS.md, 2026-09-30). It holds if the later block has at least
    ``min_obs`` observations of its own (at n > 1) and its raw, unshrunk alpha is within two standard errors of the first
    block's raw alpha. ``first_fit`` is one bucket's entry from ``fit_alpha`` (``alpha_raw`` and ``se``); ``later_obs`` are
    ``{n, ratio}`` for that bucket from a later block of rounds."""
    min_obs = config.get("BUCKET_MIN_OBS") if min_obs is None else min_obs
    if first_fit.get("status") != "measured" or first_fit.get("se") is None:
        return {"holds": False, "reason": "the first block has no measured alpha with a standard error"}
    pairs = [(math.log(o["n"]), math.log(o["ratio"])) for o in later_obs if o["n"] > 1]
    if len(pairs) < min_obs:
        return {"holds": False, "reason": f"the later block has {len(pairs)} observations of its own, fewer than {min_obs}",
                "n_later": len(pairs)}
    s = sum(x * x for x, _ in pairs)
    a2 = -sum(x * y for x, y in pairs) / s
    gap = abs(a2 - first_fit["alpha_raw"])
    limit = 2 * first_fit["se"]
    res = {"holds": gap <= limit, "alpha_first_raw": first_fit["alpha_raw"], "alpha_later_raw": a2, "gap": gap,
           "limit_2se": limit, "se_basis": "first block's standard error (the literal reading of the rule)", "n_later": len(pairs)}
    if len(pairs) > 1:   # information only: the same gap against the two blocks' combined standard error
        res_l = sum((y + a2 * x) ** 2 for x, y in pairs)
        se2 = math.sqrt(res_l / (len(pairs) - 1) / s)
        res["limit_2se_combined"] = 2 * math.sqrt(first_fit["se"] ** 2 + se2 ** 2)
        res["would_hold_on_combined_se"] = gap <= res["limit_2se_combined"]
    return res
