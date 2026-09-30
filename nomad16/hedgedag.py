"""The hedge DAG (v17 amendment A1 §7, proposed D31; Rob, 2026-09-30). Report-only, like dilution.py: it computes, it never supports.

A thesis that wants a narrative hedge carries its own DAG whose **final node is the thesis**. Every hedge node feeds the sink by a cross-reference;
the hedging is one-way, there is exactly one sink, no edge leaves it, no node references another thesis, and a cycle is refused (a directed cyclic
graph is a later step). Both the thesis and its hedges stay long: nothing here is a short. What separates them is progressive decorrelation:
each node's **effect vector** across the thesis outcomes is built ex ante from documented exposures to channels (a crude price, a crack spread, a throughput
volume) times the thesis's own channel shocks per outcome, and the hedge is worth what its effect vector's misalignment with the thesis's buys in the worst case.

    v_i[w] = sum over channels c of exposure_i[c] * shock[w][c]        (a node with no documented exposure to a channel that is shocked is a gap, never a zero)

Anything without a documented exposure is a **typed gap**: it is excluded from the worst-case optimisation and reported, because an unknown never supports.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from .db import Refused


def _check(dag: dict) -> tuple[str, list[str]]:
    nodes, edges, sink = dag["nodes"], dag["edges"], dag["thesis"]
    if sink not in nodes:
        raise Refused(f"the thesis {sink!r} is not a node")
    if sum(1 for n in nodes.values() if n.get("kind") == "thesis") != 1 or nodes[sink].get("kind") != "thesis":
        raise Refused("exactly one node is the thesis, and it is the sink: a hedge DAG does not cross-reference another thesis")
    for e in edges:
        if e["to"] != sink:
            raise Refused(f"edge {e['from']}->{e['to']}: every edge ends at the thesis (one-way; no edges between hedges, none out of the sink)")
        if e["from"] == sink:
            raise Refused("an edge leaves the thesis: the thesis is hedged by the others and does not hedge them back")
        if e["from"] not in nodes or nodes[e["from"]].get("kind") != "hedge":
            raise Refused(f"edge source {e['from']!r} is not a hedge node")
    seen, hedges = set(), []
    for e in edges:                       # with all edges ending at the sink there is no cycle unless a node feeds itself
        if e["from"] == e["to"]:
            raise Refused("a cycle: a node references itself (a directed cyclic graph is a later step)")
        if e["from"] in seen:
            raise Refused(f"hedge {e['from']!r} is listed twice")
        seen.add(e["from"])
        hedges.append(e["from"])
    return sink, hedges


def _expo(v) -> tuple[float, str]:
    """An exposure is a number (stated) or ``{"value", "basis"}`` with basis stated or implicit. Implicit is an inference, not a document."""
    return (float(v["value"]), v.get("basis", "stated")) if isinstance(v, dict) else (float(v), "stated")


def effect_vector(node: dict, shocks: list[dict], allow_implicit: bool = False) -> tuple[np.ndarray | None, list[str], bool]:
    """Per outcome. None with the unusable channels named if a shocked channel has no documented exposure (or only an implicit one, unless allowed)."""
    expo = node.get("exposure") or {}
    channels = {c for s in shocks for c, v in s.items() if v}
    missing = sorted(c for c in channels if c not in expo or (not allow_implicit and _expo(expo[c])[1] != "stated"))
    if missing:
        return None, missing, False
    used = any(_expo(expo[c])[1] == "implicit" for c in channels)
    return np.array([sum(_expo(expo[c])[0] * s.get(c, 0.0) for c in channels) for s in shocks]), [], used


def cosine(u: np.ndarray, v: np.ndarray) -> float | None:
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    return None if nu == 0 or nv == 0 else float(u @ v / (nu * nv))


def maximin(vectors: list[np.ndarray], mask: np.ndarray) -> tuple[np.ndarray, float]:
    M = np.array(vectors).T[mask]
    n = M.shape[1]
    res = linprog(np.r_[np.zeros(n), -1.0], A_ub=np.c_[-M, np.ones(len(M))], b_ub=np.zeros(len(M)),
                  A_eq=[np.r_[np.ones(n), 0.0]], b_eq=[1.0], bounds=[(0, 1)] * n + [(None, None)])
    return res.x[:n], float(res.x[-1])


def evaluate(dag: dict, outcomes: list[str], shocks: list[dict], thesis_set: list[str] | None = None, allow_implicit: bool = False) -> dict:
    """``dag``: ``{thesis, nodes: {id: {kind, exposure: {channel: value}, depth?, source?}}, edges: [{from, to}]}``. ``shocks[w]`` is the channel
    shocks (band units) the thesis asserts for outcome ``outcomes[w]``. ``thesis_set`` restricts the worst case to those outcomes."""
    sink, hedges = _check(dag)
    if len(outcomes) != len(shocks):
        raise Refused("one shock dictionary per outcome")
    mask = np.array([(thesis_set is None) or (o in thesis_set) for o in outcomes])
    if not mask.any():
        raise Refused("the thesis set is empty")
    vt, miss, t_imp = effect_vector(dag["nodes"][sink], shocks, allow_implicit)
    if vt is None:
        raise Refused(f"the thesis node has no documented exposure to {miss}: nothing to hedge")
    rows, gaps, ok, implicit = {}, {}, [], (["thesis"] if t_imp else [])
    for h in hedges:
        v, m, imp = effect_vector(dag["nodes"][h], shocks, allow_implicit)
        if imp:
            implicit.append(h)
        if v is None:
            gaps[h] = m
            continue
        ok.append(h)
        rows[h] = {"vector": v.round(3).tolist(), "cosine_to_thesis": cosine(vt, v), "depth": dag["nodes"][h].get("depth"),
                   "worst_alone": float(v[mask].min()), "best_alone": float(v[mask].max())}
    out = {"report_only": True, "supports": False, "thesis_vector": vt.round(3).tolist(), "thesis_worst_alone": float(vt[mask].min()),
           "outcomes": outcomes, "hedges": rows, "gaps": gaps, "implicit_used": implicit,
           "status": "switch: uses implicit exposures, to be checked" if implicit else "documented"}
    if ok:
        w, worst = maximin([vt] + [np.array(rows[h]["vector"]) for h in ok], mask)
        out["maximin"] = {"weights": dict(zip(["thesis"] + ok, w.round(3).tolist())), "worst_case": worst,
                          "lift_over_thesis_alone": worst - float(vt[mask].min())}
        by = {}
        for h in ok:
            d = rows[h]["depth"]
            if d is not None and rows[h]["cosine_to_thesis"] is not None:
                by.setdefault(d, []).append(rows[h]["cosine_to_thesis"])
        out["alignment_by_depth"] = {d: float(np.mean(v)) for d, v in sorted(by.items())}
    return out
