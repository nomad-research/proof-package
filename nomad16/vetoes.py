"""The veto set, per effect, and the five-term vector as a diagnostic (§8, §20.1, §21).

Only anchors veto: ``no_path``, ``signs_held``, ``absorbed_by_slack``, ``no_sink`` and
``below_band``. ``below_band`` is the one veto that reads prices (the pre-T_seg band of
the instrument's tide-hedged residual). A veto that can't be evaluated is absent: the
effect goes forward and the unknown widens its band in construction.

``absorbed_by_slack`` and ``no_sink`` point opposite ways and which applies to which
effect kind is an open call (§34). Each fires only on a stated fact for that effect
kind; otherwise it reads ``unevaluable``.
"""
from __future__ import annotations

from collections import defaultdict

from . import config
from .conditions import visible_positions
from .derive import scope_nodes
from .instruments import LINEAR, expression_term
from .util import le


def compute(view, round_row: dict, clock: str, ctx=None, horizons: dict | None = None,
            rho: dict | None = None) -> list[dict]:
    rid = round_row["round_id"]
    nodes = scope_nodes(view, round_row["node"])
    effects = view.led("effects", "round_id=?", (rid,))
    facts = [f for f in view.led("node_facts") if le(f["knowable_from"], clock)]
    mat = config.get("MATERIALITY_BAND")
    out = []
    for e in effects:
        fired, unevaluable = [], []
        # no_path: a refused composition, or degree >= 2 with no mechanism and no position
        if e.get("vetoed_by") == "no_path":
            fired.append({"veto": "no_path", "inputs": e.get("carried_by"), "evidence": []})
        elif int(e["depth"]) >= 2 and not e.get("cited_rules") and not e.get("position_ids"):
            fired.append({"veto": "no_path", "inputs": "degree>=2 with no cited mechanism and no stated position",
                          "evidence": []})
        # signs_held: documented exposure of both signs for this effect kind on the node
        signs = {p["value"] for p in visible_positions(view, clock, e["holder_id"], nodes, "exposure_sign")
                 if p["confidence"] == "stated" and (p.get("unit") in (None, e["effect_kind"]))}
        if {"+1", "-1"} <= signs or {"1", "-1"} <= signs:
            fired.append({"veto": "signs_held", "inputs": sorted(signs), "evidence": []})
        elif not signs:
            unevaluable.append("signs_held")
        for kind, veto in (("slack", "absorbed_by_slack"), ("no_sink", "no_sink")):
            f = [x for x in facts if x["kind"] == kind and x["node"] in (e["node"], *nodes)
                 and x.get("effect_kind") in (None, e["effect_kind"])]
            if f:
                fired.append({"veto": veto, "inputs": [x["text"] for x in f],
                              "evidence": [x["fact_id"] for x in f]})
            else:
                unevaluable.append(veto)
        # below_band: expected move under the hedged-residual band of the holder's instrument
        inst = None
        if ctx is not None:
            inst = next((i for i in ctx.linear if i.get("holder_id") == e["holder_id"]), None)
        if inst is None or e.get("magnitude_pct") is None:
            unevaluable.append("below_band")
            band = None
        else:
            h = (horizons or {}).get(e.get("ack_id")) or max((horizons or {63: 63}).values() or [63])
            band = ctx.band(inst["key"], int(h))
            if abs(float(e["magnitude_pct"])) / 100.0 < band:
                fired.append({"veto": "below_band", "inputs": {"move": abs(float(e["magnitude_pct"])) / 100.0,
                                                               "band": band, "horizon": h,
                                                               "instrument": inst["key"]},
                              "evidence": []})
        # the five terms, as a diagnostic vector with typed gaps
        holder = view.mget("holders", e["holder_id"]) or {}
        hc = holder.get("holder_class")
        terms, gaps = {}, {}
        stake_basis = None
        if hc == "authority":
            gaps["stake"] = "not_applicable"
        elif e.get("magnitude_pct") is None:
            gaps["stake"] = "not_disclosed"
        elif hc == "listed_instrument":
            if band:
                terms["stake"] = abs(float(e["magnitude_pct"])) / 100.0 / band
                stake_basis = "price_band"
            else:
                gaps["stake"] = "not_covered"
        elif hc == "unlisted_operating_asset":
            terms["stake"] = abs(float(e["magnitude_pct"])) / 100.0 / float(mat["unlisted_operating_asset"])
            stake_basis = "operating_scale"
        elif hc == "aggregate":
            terms["stake"] = abs(float(e["magnitude_pct"])) / 100.0 / float(mat["aggregate"])
            stake_basis = "class_scale"
        else:
            gaps["stake"] = "not_representable"
        terms["structural"] = float(e.get("transmission") or 0.0)
        if rho and e["holder_id"] in rho:
            terms["pricedness"] = rho[e["holder_id"]]
        else:
            gaps["pricedness"] = "not_representable" if hc != "listed_instrument" else "not_covered"
        gaps["operator"] = "not_covered"  # no clean resolutions yet for this operator model (OPERATOR_MIN_N)
        terms["expression"] = expression_term(view, e["holder_id"], clock)
        out.append({"effect_id": e["effect_id"], "holder_id": e["holder_id"], "depth": int(e["depth"]),
                    "effect_kind": e["effect_kind"], "status": "vetoed" if fired else "forward",
                    "vetoes_fired": fired, "vetoes_unevaluable": unevaluable, "terms": terms,
                    "gap_reasons": gaps, "stake_basis": stake_basis,
                    "operator_basis": "all_clean_calls", "n": 0})
    return out


def veto_rate(rows: list[dict]) -> dict:
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        for key in (f"depth={r['depth']}", f"kind={r['effect_kind']}"):
            by[key][1] += 1
            by[key][0] += r["status"] == "vetoed"
    return {k: {"vetoed": v[0], "n": v[1], "rate": v[0] / v[1] if v[1] else None} for k, v in sorted(by.items())}
