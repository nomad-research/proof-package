"""Lock: compute every emergent object once, freeze it, hash it, write the manifest (§14).

* Runs the veto set **once** per lock (the v15 double ``assess_round`` is gone).
* A second lock of the same segment is refused.
* The manifest pins the canonical content of every mutable-store row, every price
  vintage, the ledger cutoff, the config hash and the budgets used, so replay reads the
  manifest, not the live stores, and must reproduce the lock hash (smoke 25).
"""
from __future__ import annotations

import numpy as np

from . import config, construct, derive, reach, stories, vetoes
from .db import DB, Refused, canon, now_iso, sha
from .rounds import current_segment, get_round, is_locked, meta, set_meta, set_state, state
from .util import norm, ohash
from .view import View


def _clean(x):
    if isinstance(x, np.ndarray):
        return [_clean(v) for v in x.tolist()]
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    return x


def ratified_acks(view, round_id: str) -> list[dict]:
    return sorted([a for a in view.mut("ack_nodes") if a.get("round_id") == round_id
                   and a.get("status") == "ratified"], key=lambda a: a["key"])


def latest_thesis(view, ack_id: str, seg_idx: int):
    rows = view.led("thesis_sets", "ack_id=? AND segment_idx=?", (ack_id, seg_idx))
    return rows[-1] if rows else None


def budgets(db: DB, round_id: str, tide_id: str | None) -> dict:
    """Committed maximum loss still open, read from baskets already locked (in lock order)."""
    open_by_round, open_by_tide = 0.0, 0.0
    closed = {e["basket_id"]: e for e in db.rows("paper_exits")}
    realised = {}
    for e in db.rows("paper_exits"):
        realised[e["basket_id"]] = realised.get(e["basket_id"], 0.0) + float(e["pnl"] or 0.0)
    for b in db.rows("constructed_baskets"):
        if b["status"] != "built":
            continue
        ml = float(b["max_loss"] or 0.0)
        if b["basket_id"] in closed:
            # released on close, less any realised loss
            ml = max(-realised.get(b["basket_id"], 0.0), 0.0)
            ml = 0.0 if ml == 0 else ml
            # a realised loss consumes budget permanently
        if b["round_id"] == round_id:
            open_by_round += ml
        if tide_id and b["tide_id"] == tide_id:
            open_by_tide += ml
    return {"round_used": open_by_round, "tide_used": open_by_tide,
            "round_remaining": max(float(config.get("LOSS_BUDGET_PER_ROUND")) - open_by_round, 0.0),
            "tide_remaining": max(float(config.get("LOSS_CAP_PER_TIDE")) - open_by_tide, 0.0)}


def compute_segment(view: View, round_row: dict, seg: dict, budget: dict) -> dict:
    """Pure over the view: every emergent object of one segment."""
    rid, idx, clock = round_row["round_id"], seg["idx"], seg["clock"]
    objs = {"round_id": rid, "segment": idx, "clock": clock}
    objs["derivations"] = [{k: d[k] for k in ("template_id", "bindings", "result", "fetch_list")}
                           | {"conditions": [(c["state"], c["why"]) for c in d["conditions"]]}
                           for d in derive.compute(view, round_row, clock)]
    acks = ratified_acks(view, rid)
    objs["acks"] = [{k: a.get(k) for k in ("key", "ack_kind", "origin", "notice_kind", "is_switch",
                                           "window_to", "due_at", "bindings", "template_id")} for a in acks]
    objs["calls"] = [{k: c[k] for k in ("call_id", "call_type", "claim_kind", "claim", "branches", "carrier",
                                        "due_at", "falsifier", "cited_rules")}
                     for c in view.led("predictions", "round_id=? AND segment_idx=?", (rid, idx))]
    try:
        ctx = stories.Context(view, round_row, clock)
    except Refused as e:
        ctx = None
        objs["context_refused"] = str(e)
    horizons = {a["key"]: stories.horizon(a, clock) for a in acks}
    vrows = vetoes.compute(view, round_row, clock, ctx, horizons)
    vetoed = {r["effect_id"] for r in vrows if r["status"] == "vetoed"}
    objs["vetoes"] = vrows
    objs["veto_rate"] = vetoes.veto_rate(vrows)
    objs["reach"], objs["thesis"], objs["stories"], objs["s_perp"], objs["baskets"] = {}, {}, {}, {}, []
    if ctx is None:
        for a in acks:
            objs["baskets"].append({"ack_id": a["key"], "status": "unbuildable",
                                    "reason": "no_instrument", "detail": {"context": objs["context_refused"]}})
        return norm(_clean(objs))
    objs["instruments_in_reach"] = [i["key"] for i in ctx.instruments]
    objs["context_gaps"] = ctx.gaps
    L = stories.loadings(ctx)
    objs["loadings"] = {k: {"vec": v["vec"], "se": v["se"], "kind": v["kind"], "active": v["active"],
                            "active_basis": v["active_basis"]} for k, v in L.items()}
    objs["index"] = ctx.index
    jflags = stories.junction_flags(ctx, L)
    treat = stories.junction_treatments(view, rid, idx)
    objs["junctions"] = [dict(j, treatment=treat.get(j["junction_id"])) for j in jflags]
    ctx._junction_vecs = {f"node:{j['shared_node']}": stories.junction_node_vec(ctx, j["shared_node"]) for j in jflags}
    held_j = sorted({f"node:{j['shared_node']}" for j in jflags if treat.get(j["junction_id"]) == "held"})
    per_ack = []
    for a in acks:
        rr = reach.compute(view, round_row, a, clock)
        th = latest_thesis(view, a["key"], idx)
        R = [r["outcome_id"] for r in rr if r["reach"] != "cut"]
        thesis = sorted(th["in_thesis"]) if th else R
        objs["reach"][a["key"]] = rr
        objs["thesis"][a["key"]] = {"in_thesis": thesis, "stated": th is not None,
                                    "exclusions": th["exclusions"] if th else {}}
        h = horizons[a["key"]]
        sv = stories.s_vectors(ctx, a, R, h, vetoed) if rr and ctx.index else {}
        shp, Sbar = stories.shape(sv, thesis) if sv else ("mixed", None)
        classes = stories.classify(L, Sbar, shp)
        names, H = stories.hedged_set(ctx, L, classes, jflags, treat)
        objs["stories"][a["key"]] = {"shape": shp, "s_ref_hash": ohash(_clean(Sbar)) if Sbar is not None else None,
                                     "classes": classes, "hedged_set": names}
        sp = {}
        for w, v in sv.items():
            S = v["S"]
            perp = stories.s_perp(S, H)
            nS = float(np.linalg.norm(S))
            sp[w] = {"S": S, "s_norm": nS, "s_perp_norm": float(np.linalg.norm(perp)),
                     "rho": float(np.linalg.norm(perp) / nS) if nS > 0 else None, "flat": v["flat"],
                     "unknown_terms": v["unknown"]}
        objs["s_perp"][a["key"]] = sp
        per_ack.append((a, rr, thesis, sv, shp, Sbar, classes, names, H))
    # budgets: remaining round budget / number of ACKs passing the pre-solve gates, capped by the tide
    passing = [p for p in per_ack if construct.build(ctx, p[0], p[1], p[2], p[3], p[4], p[5], L, p[6], p[7], p[8],
                                                     held_j, 1.0, pre_gate_only=True)["status"] == "passes_pre_gates"]
    n_pass = len(passing)
    base = min(budget["round_remaining"] / n_pass, budget["tide_remaining"]) if n_pass else 0.0
    for p in per_ack:
        a = p[0]
        B = base * (float(config.get("SWITCH_BUDGET_FRACTION")) if a.get("is_switch") else 1.0)
        b = construct.build(ctx, a, p[1], p[2], p[3], p[4], p[5], L, p[6], p[7], p[8], held_j, B)
        b["operator_size_factor"] = {"applied": 1.0, "basis": "operator term is a typed gap (not_covered); no shrink"}
        objs["baskets"].append(b)
    objs["budget"] = budget
    return norm(_clean(objs))


def manifest_for(view: View, db: DB, round_id: str, idx: int, budget: dict, tide_id, cutoff: str) -> dict:
    rows = view.snapshot_rows()
    for t, keyed in rows.items():
        for k, h in keyed.items():
            if db.one("store_snapshots", "content_hash=?", (h,)) is None:
                r = view.mget(t, k)
                db.append("store_snapshots", content_hash=h, tbl=t, row_key=k, canonical_json=canon(r))
    vids = sorted(r["vintage_id"] for r in db.rows("price_vintages") if r["recorded_at"] <= cutoff)
    lh = db.rows("library_history")
    return {"store_rows": rows, "vintage_ids": vids, "ledger_cutoff": cutoff,
            "library_history_version": lh[-1]["row_hash"][:16] if lh else "empty",
            "config_hash": config.config_hash(), "harness_version": config.harness_version(),
            "round_budget_used": budget["round_used"], "tide_budget_used": budget["tide_used"],
            "tide_id": tide_id, "budget": budget}


def lock(db: DB, round_id: str) -> dict:
    """nomad_lock_predictions / nomad_segment_lock: freeze the current segment."""
    rnd = get_round(db, round_id)
    st = state(db, round_id)
    if st != "pre_lock":
        raise Refused(f"round {round_id} is '{st}'; only a pre-lock segment can be locked")
    seg = current_segment(db, round_id)
    if is_locked(db, round_id, seg["idx"]):
        raise Refused(f"segment {seg['idx']} is already locked; a further lock is refused")
    man = db.one("operator_manifests", "round_id=?", (round_id,))
    if man is None or not man.get("hook_verified") or not man.get("operator_model") or not man.get("operator_cutoff"):
        raise Refused("no operator manifest with model, runtime, cutoff and a verified hook: a round "
                      "without one can't lock (fold smoke 15)")
    tide_id = meta(db, round_id, "tide_id")
    if not tide_id:
        raise Refused("declare the round's tide at lock (tide_declare)")
    view0 = View(db)
    ctx_ok = True
    try:
        ctx = stories.Context(view0, rnd, seg["clock"])
        L = stories.loadings(ctx)
        flags = stories.junction_flags(ctx, L)
        treat = stories.junction_treatments(view0, round_id, seg["idx"])
        untreated = [j["junction_id"] for j in flags if j["junction_id"] not in treat]
        if untreated:
            raise Refused(f"each flagged junction needs a treatment recorded before lock: {untreated}")
    except Refused as e:
        if "junction" in str(e):
            raise
        ctx_ok = False
    budget = budgets(db, round_id, tide_id)
    cutoff = now_iso()
    view = View(db, ledger_cutoff=cutoff)
    objs = compute_segment(view, rnd, seg, budget)
    manifest = manifest_for(view, db, round_id, seg["idx"], budget, tide_id, cutoff)
    mid = f"M:{round_id}:{seg['idx']}"
    mrow = db.append("lock_manifests", manifest_id=mid, round_id=round_id, segment_idx=seg["idx"],
                     store_rows=manifest["store_rows"], vintage_ids=manifest["vintage_ids"],
                     ledger_cutoff=cutoff, library_history_version=manifest["library_history_version"],
                     config_hash=manifest["config_hash"], harness_version=manifest["harness_version"],
                     round_budget_used=budget["round_used"], tide_budget_used=budget["tide_used"],
                     tide_id=tide_id)
    objects_hash = ohash(objs)
    lock_hash = sha(objects_hash + ohash({k: v for k, v in manifest.items()}))
    seq = len(db.rows("locks")) + 1
    for v in objs["vetoes"]:
        db.append("surviving_risk", round_id=round_id, segment_idx=seg["idx"], lock_seq=seq,
                  effect_id=v["effect_id"], status=v["status"], vetoes_fired=v["vetoes_fired"],
                  vetoes_unevaluable=v["vetoes_unevaluable"], terms=v["terms"], gap_reasons=v["gap_reasons"],
                  stake_basis=v["stake_basis"], operator_basis=v["operator_basis"], n=v["n"])
    for ack_id, s in objs.get("stories", {}).items():
        for sid, c in s["classes"].items():
            db.append("story_classes", story_id=sid, round_id=round_id, segment_idx=seg["idx"], key=ack_id,
                      active=c.get("active"), active_basis=objs["loadings"].get(sid, {}).get("active_basis"),
                      angle=c.get("angle"), cos=c.get("cos"), **{"class": c["class"]},
                      decomposition=c.get("decomposition"), s_ref_hash=s["s_ref_hash"], treatment=None)
    for sid, l in objs.get("loadings", {}).items():
        for j, inst in enumerate(objs.get("index", [])):
            db.append("story_loadings", story_id=sid, instrument_id=inst, round_id=round_id,
                      segment_idx=seg["idx"], key="lock", loading=l["vec"][j], se=l["se"][j],
                      window_from=None, window_to=seg["clock"], vintage_ids=[], kind=l["kind"])
    for j in objs.get("junctions", []):
        db.append("junctions", junction_id=j["junction_id"], round_id=round_id, segment_idx=seg["idx"],
                  story_a=j["story_a"], story_b=j["story_b"], shared_node=j["shared_node"], trigger_ack_id=None,
                  corr_before=None, corr_after=None, status="flagged", treatment=j["treatment"],
                  node_story_id=f"node:{j['shared_node']}")
    for ack_id, per in objs.get("s_perp", {}).items():
        for w, v in per.items():
            db.append("s_perp", round_id=round_id, segment_idx=seg["idx"], key="lock", ack_id=ack_id,
                      outcome_id=w, s_vec=v["S"], s_norm=v["s_norm"], s_perp_norm=v["s_perp_norm"],
                      rho=v["rho"], residual_noise_band=None,
                      hedged_set=objs["stories"][ack_id]["hedged_set"], flat=v["flat"])
    built = []
    for b in objs["baskets"]:
        bid = f"B:{round_id}:{seg['idx']}:{b['ack_id']}"
        db.append("constructed_baskets", basket_id=bid, round_id=round_id, segment_idx=seg["idx"],
                  ack_id=b["ack_id"], status=b["status"], reason=b.get("reason"), shape=b.get("shape"),
                  z_star=b.get("z_star"), b_basket=b.get("b_basket"), max_loss=b.get("max_loss", 0.0),
                  tide_id=tide_id, weights_hash=ohash(b.get("weights", [])), lock_hash=lock_hash,
                  flags=b.get("flags", []), detail=b.get("detail", {}))
        for w in b.get("weights", []):
            db.append("basket_weights", basket_id=bid, instrument_id=w["instrument_id"], w_long=w["w_long"],
                      w_short=w["w_short"], max_loss_contribution=w["max_loss_contribution"])
            pid = f"{bid}:{w['instrument_id']}:{'L' if w['side'] > 0 else 'S'}"
            entry_rule = "modelled" if w["modelled"] else ("live_first_quote" if rnd.get("live") else "backfill_first_close")
            db.append("paper_positions", paper_id=pid, basket_id=bid, instrument_id=w["instrument_id"],
                      side=w["side"], qty=w["qty"], entry_rule=entry_rule, max_loss=w["max_loss_contribution"],
                      exit_rules={"s_perp_below": config.get("RHO_EXIT"),
                                  "recovery_fraction": config.get("RECOVERY_FRACTION"),
                                  "attention_ack": True,
                                  "window_end": next((a["window_to"] or a["due_at"]) for a in objs["acks"]
                                                     if a["key"] == b["ack_id"]),
                                  "stop": config.get("STOP_RULE") if w["cap"] == "stress" else None,
                                  "stress_max_loss": w["max_loss_contribution"],
                                  "loadings": w["loadings"], "unit_cost": w["unit_cost"],
                                  "entry_price_model": w.get("entry_price_model")})
        for s in b.get("scenarios", []):
            db.append("scenarios", basket_id=bid, scenario_id=s["scenario_id"], outcome_id=s["outcome_id"],
                      in_thesis=s["in_thesis"], tide_state=s["tide_state"], payoffs=s["payoffs"],
                      payoff_worst=s["payoff_worst"],
                      upside_if_adopted=b.get("upside_if_adopted") if s["in_thesis"] else None)
        if b["status"] == "built":
            built.append(bid)
    db.append("locks", round_id=round_id, segment_idx=seg["idx"], lock_hash=lock_hash, manifest_id=mid,
              objects_hash=objects_hash, clock=seg["clock"])
    db.append("segments", round_id=round_id, idx=seg["idx"], clock=seg["clock"],
              opened_by_ack_id=seg.get("opened_by_ack_id"), opened_by_firing_id=seg.get("opened_by_firing_id"),
              locked_at=seg["clock"], lock_hash=lock_hash, manifest_id=mid, wall_clock=now_iso())
    provisional = [k for k in config.used_keys() if config.status(k) == "provisional_unratified"]
    set_meta(db, round_id, f"provisional_keys_read_seg{seg['idx']}", provisional)
    set_state(db, round_id, "live" if rnd.get("live") else "walking",
              f"segment {seg['idx']} locked, hash {lock_hash[:16]}")
    return {"lock_hash": lock_hash, "objects_hash": objects_hash, "manifest_id": mid, "segment": seg["idx"],
            "clock": seg["clock"], "baskets": [{"ack_id": b["ack_id"], "status": b["status"],
                                                  "reason": b.get("reason"), "shape": b.get("shape"),
                                                  "z_star": b.get("z_star"), "max_loss": b.get("max_loss")}
                                                 for b in objs["baskets"]],
            "built": built, "veto_rate": objs["veto_rate"], "context_ok": ctx_ok,
            "provisional_values_read": len(provisional), "state": state(db, round_id)}


def replay(db: DB, round_id: str, idx: int) -> dict:
    """Recompute a locked segment from its manifest and compare the lock hash."""
    lk = db.one("locks", "round_id=? AND segment_idx=?", (round_id, idx))
    if lk is None:
        raise Refused(f"segment {idx} of {round_id} is not locked")
    m = db.one("lock_manifests", "manifest_id=?", (lk["manifest_id"],))
    manifest = {"store_rows": m["store_rows"], "vintage_ids": m["vintage_ids"], "ledger_cutoff": m["ledger_cutoff"]}
    view = View(db, manifest=manifest)
    rnd = get_round(db, round_id)
    seg = {"idx": idx, "clock": lk["clock"]}
    budget = None
    for r in db.rows("lock_manifests", "manifest_id=?", (lk["manifest_id"],)):
        budget = r
    b = {"round_used": budget["round_budget_used"], "tide_used": budget["tide_budget_used"]}
    b["round_remaining"] = max(float(config.get("LOSS_BUDGET_PER_ROUND")) - b["round_used"], 0.0)
    b["tide_remaining"] = max(float(config.get("LOSS_CAP_PER_TIDE")) - b["tide_used"], 0.0)
    objs = compute_segment(view, rnd, seg, b)
    oh = ohash(objs)
    ok = oh == lk["objects_hash"]
    if not ok:
        set_meta(db, round_id, f"nondeterministic_seg{idx}", True)
    return {"segment": idx, "reproduces": ok, "objects_hash": oh, "locked_objects_hash": lk["objects_hash"]}
