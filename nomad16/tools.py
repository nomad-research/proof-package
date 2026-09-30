"""The tool surface (§27), as a CLI: ``python -m nomad16 <tool> '<json args>'``.

Names follow the spec's ``nomad_*`` tools without the prefix. Every response carries
``harness_version``, ``logic_version``, ``config_hash`` and the chain heads (§17). A
refusal prints ``{"refused": reason}`` and exits 2: a refusal is never swallowed.
"""
from __future__ import annotations

import inspect
import json
import sys

from . import (altdata, calls, census, dilution, documents, entities, config, construct, derive, effects, instruments, intake, lock, paper, pit,
               positions, prices, reach, report, rounds, seed, stories, walk)
from .db import DB, Refused
from .rounds import current_segment, state
from .util import day, ts


def price_fetch(db: DB, round_id: str, symbol: str, from_date: str = "2024-01-01") -> dict:
    """Fetch a symbol's daily bars into the vintage store, truncated to what the round may see."""
    st = state(db, round_id)
    if st == "pre_lock":
        ceiling = current_segment(db, round_id)["clock"]
    elif st == "walking":
        import datetime as _dt
        f = walk.frontier(db, round_id)
        ceiling = (ts(day(f)) + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    elif st in {"live", "scored"}:
        ceiling = None
    else:
        raise Refused(f"round is '{st}'")
    to = day(ceiling) if ceiling else day(ts("now"))
    return prices.fetch_yahoo(db, symbol, from_date, to, ceiling=ceiling)


def round_status(db: DB, round_id: str) -> dict:
    r = rounds.get_round(db, round_id)
    seg = current_segment(db, round_id)
    return {"round_id": round_id, "state": state(db, round_id), "class": r["round_class"],
            "segment": seg["idx"], "clock": seg["clock"], "locked": rounds.is_locked(db, round_id, seg["idx"]),
            "event_line": r["event_line"], "tide": rounds.meta(db, round_id, "tide_id"),
            "acks": [{"ack_id": a["key"], "status": a["status"], "notice_kind": a["notice_kind"],
                      "is_switch": a["is_switch"], "window_to": a["window_to"]}
                     for a in db.rows("ack_nodes") if a["round_id"] == round_id],
            "calls": len(db.rows("predictions", "round_id=?", (round_id,))),
            "effects": len(db.rows("effects", "round_id=?", (round_id,)))}


def preview(db: DB, round_id: str) -> dict:
    """Run the lock computation without locking: loadings, classes, junction flags, S⊥, baskets."""
    from .view import View
    rnd = rounds.get_round(db, round_id)
    seg = current_segment(db, round_id)
    b = lock.budgets(db, round_id, rounds.meta(db, round_id, "tide_id"))
    objs = lock.compute_segment(View(db), rnd, seg, b)
    keep = {k: objs.get(k) for k in ("clock", "acks", "instruments_in_reach", "context_gaps", "context_refused",
                                     "junctions", "veto_rate", "budget")}
    keep["stories"] = {a: {"shape": s["shape"], "hedged_set": s["hedged_set"],
                           "classes": {k: {"class": c["class"], "active": c.get("active"), "cos": c.get("cos")}
                                       for k, c in s["classes"].items()}} for a, s in (objs.get("stories") or {}).items()}
    keep["s_perp"] = {a: {w: {"rho": v["rho"], "s_norm": v["s_norm"], "s_perp_norm": v["s_perp_norm"], "flat": v["flat"]}
                          for w, v in per.items()} for a, per in (objs.get("s_perp") or {}).items()}
    keep["baskets"] = [{k: b.get(k) for k in ("ack_id", "status", "reason", "shape", "z_star", "b_basket", "max_loss",
                                              "detail", "flags")} | {"weights": [{k: w[k] for k in ("instrument_id", "side", "qty", "max_loss_contribution", "cap")}
                                                                                  for w in b.get("weights", [])]}
                       for b in objs["baskets"]]
    keep["vetoes"] = [{k: v[k] for k in ("effect_id", "status", "vetoes_fired", "vetoes_unevaluable", "terms", "gap_reasons")}
                      for v in objs["vetoes"]]
    return keep


def verify_chain(db: DB) -> dict:
    bad = db.verify_chain()
    return {"ok": not bad, "broken": bad, "heads": db.chain_heads()}


def veto_preview(db: DB, round_id: str) -> dict:
    from .view import View
    rnd = rounds.get_round(db, round_id)
    seg = current_segment(db, round_id)
    v = View(db)
    try:
        ctx = stories.Context(v, rnd, seg["clock"])
    except Refused:
        ctx = None
    from . import vetoes
    rows = vetoes.compute(v, rnd, seg["clock"], ctx)
    return {"vetoes": rows, "veto_rate": vetoes.veto_rate(rows)}


TOOLS = {
    # intake and lifecycle
    "enumerate": intake.enumerate_feed, "intake_decide": intake.intake_decide, "submit_event": intake.submit_event,
    "reveal_event": intake.reveal_event, "operator_manifest": intake.operator_manifest,
    "tide_declare": intake.tide_declare, "tide_add": intake.tide_add, "round_status": round_status,
    "lock_predictions": lock.lock, "segment_lock": lock.lock, "replay": lock.replay, "preview": preview,
    "verify_chain": verify_chain, "seed": seed.seed, "library_as_of": seed.library_as_of,
    # evidence
    "pit_fetch": pit.pit_fetch, "alt_fetch": altdata.alt_fetch, "alt_probe": altdata.alt_probe,
    "price_fetch": price_fetch,
    # names and positions
    "holder_upsert": positions.holder_upsert, "node_upsert": positions.node_upsert,
    "position_add": positions.position_add, "position_attribute_add": positions.attribute_add,
    "bound_add": positions.bound_add, "node_fact_add": positions.node_fact_add,
    # effects and vetoes
    "effect_root": effects.effect_root, "effect_compose": effects.effect_compose,
    "transform_add": effects.transform_add, "surviving_risk": veto_preview,
    # ACKs
    "derive_acks": derive.derive_acks, "ack_ratify": derive.ack_ratify, "ack_add": derive.ack_add,
    "ack_window": derive.ack_window, "outcomes": reach.outcomes, "reachable": reach.reachable,
    "thesis_set": reach.thesis_set, "outcome_vocab_add": reach.outcome_vocab_add,
    # calls and scoring
    "call_add": calls.call_add, "score_call": calls.score_call, "close_round": calls.close_round,
    "absence_record": calls.absence_record,
    # stories
    "story_add": stories.story_add, "story_active": stories.story_active, "junction_treat": stories.junction_treat,
    "junction_confirm": stories.junction_confirm,
    # instruments and paper
    "instrument_add": instruments.instrument_add, "paper_fill": paper.fill, "paper_mark": paper.mark,
    "paper_exit": paper.exit_basket, "exit_check": paper.exit_check, "paper_book": paper.paper_book,
    # walk
    "ack_fire": walk.ack_fire, "walk_read": walk.walk_read, "walk_end": walk.walk_end, "walk_scan": walk.walk_scan,
    # v17 V0: the open entity
    "seed_v17": seed.seed_v17, "migrate_v17": entities.migrate_v17, "entity_upsert": entities.entity_upsert,
    "entity_kind_add": entities.kind_add, "entity_kind_ratify": entities.kind_ratify,
    "attribute_scope_add": entities.attribute_scope_add, "entity_merge": entities.entity_merge,
    "entity_merge_ratify": entities.entity_merge_ratify, "entity_merge_decline": entities.entity_merge_decline, "entity_split": entities.entity_split,
    # v17 V1: documents as evidence, derived dating
    "document_from_evidence": documents.document_from_evidence, "admission_record": documents.admission_record,
    "statement_add": documents.statement_add, "document_state_set": documents.document_state_set,
    "dating_report": documents.dating_report,
    # v17 V2 slice: dilution buckets and the chain profile
    "bucket_propose": dilution.bucket_propose, "bucket_partition_add": dilution.bucket_partition_add,
    "bucket_fit": dilution.bucket_fit, "depth_profile": dilution.depth_profile,
    # K7 census
    "census_add": census.census_add, "census": census.census,
    # reports
    "report": report.round_report,
}


def envelope(db: DB, result) -> dict:
    return {"result": result, "harness_version": config.harness_version(), "logic_version": config.LOGIC_VERSION,
            "config_hash": config.config_hash()[:16], "chain_heads": db.chain_heads()}


def call(name: str, args: dict, db: DB | None = None):
    if name not in TOOLS:
        raise Refused(f"unknown tool {name}")
    fn = TOOLS[name]
    db = db or DB()
    params = inspect.signature(fn).parameters
    if "db" in params:
        return fn(db, **args)
    return fn(**args)


def help_text() -> str:
    lines = ["python -m nomad16 <tool> '<json args>'", ""]
    for n, fn in sorted(TOOLS.items()):
        sig = [p for p in inspect.signature(fn).parameters if p != "db"]
        doc = (inspect.getdoc(fn) or "").split("\n")[0]
        lines.append(f"  {n}({', '.join(sig)})  {doc}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"help", "-h", "--help"}:
        print(help_text())
        return 0
    name = argv[0]
    raw = argv[1] if len(argv) > 1 else "{}"
    if raw.startswith("@"):
        raw = open(raw[1:]).read()
    try:
        args = json.loads(raw)
    except ValueError as e:
        print(json.dumps({"refused": f"arguments must be one JSON object: {e}"}))
        return 2
    db = DB()
    try:
        res = call(name, args, db)
    except Refused as e:
        print(json.dumps({"refused": str(e)}, indent=1))
        return 2
    except config.MissingAppetite as e:
        print(json.dumps({"refused": f"missing appetite: {e}"}, indent=1))
        return 2
    except TypeError as e:
        print(json.dumps({"refused": f"bad arguments for {name}: {e}"}, indent=1))
        return 2
    print(json.dumps(envelope(db, res), indent=1, default=str))
    return 0
