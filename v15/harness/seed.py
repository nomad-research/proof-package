"""Seed loaders (§8). Everything goes through the same API as live play, so the chain and stamps hold.

Two layouts:
  * nested (seed_v1.json / seed_v4_template.json): keys local to the file, rounds as nested objects.
  * flat "nomad_harness_seed_v4": one list per table with human-readable string ids (lib.*, holder.*, pred.*,
    round.N, call.*, evd.*, pos.*). The string ids are kept as `key` on rules, predicates and holders so the
    operator can cite them; ledgers store UUIDs.

Both are idempotent: re-running skips what already exists (predicate name/key, rule key/text, holder name,
hypothesis text, event hash)."""
import json
import sqlite3
from pathlib import Path

from . import hypotheses, library, names, positions, predicates, rounds, scorer, t0
from .config import NULL_CALL_WEIGHT
from .db import verify_chain
from .errors import HarnessError

SEED_DIR = Path(__file__).parent / "seed"
DEFAULT_SEED = SEED_DIR / "seed_v4.json"


def load_seed(conn: sqlite3.Connection, path: str | Path = DEFAULT_SEED) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") == "nomad_harness_seed_v4":
        return load_seed_flat(conn, data, str(path))
    return load_seed_nested(conn, data, str(path))


# ---------------------------------------------------------------------------
# flat layout

def _criterion(v) -> str:
    """Seed criteria carry free text; the ledger needs pass|fail|unknown[ note]. Unrecognised -> unknown, text kept."""
    s = str(v).strip()
    if s.lower().startswith(("pass", "fail", "unknown")):
        return s
    return f"unknown: {s}"


def load_seed_flat(conn: sqlite3.Connection, data: dict, path: str) -> dict:
    rep: dict = {"seed": path, "schema": data.get("schema"), "predicates": 0, "library_rules": 0, "holders": 0,
                 "aliases": 0, "positions": 0, "retro_rounds": 0, "hypotheses": 0, "t0_candidates": 0,
                 "skipped": [], "warnings": []}
    cfg = data.get("config", {})
    if "NULL_CALL_WEIGHT" in cfg and float(cfg["NULL_CALL_WEIGHT"]) != NULL_CALL_WEIGHT:
        raise HarnessError(f"seed NULL_CALL_WEIGHT {cfg['NULL_CALL_WEIGHT']} != config {NULL_CALL_WEIGHT}; "
                           "changing it is a config commit, not a seed parameter")

    # predicates -----------------------------------------------------------
    pred_ids: dict[str, str] = {}
    for p in data.get("predicates", []):
        existing = conn.execute("SELECT id FROM predicates WHERE key = ? OR name = ?", (p["id"], p["name"])).fetchone()
        if existing:
            pred_ids[p["id"]] = existing["id"]
            rep["skipped"].append(f"predicate {p['id']}")
            continue
        r = predicates.predicate_add(conn, p["name"], p["kind"], p["source"], p["threshold"], p.get("date"),
                                     p.get("role_note") or None, p.get("active", True), key=p["id"])
        pred_ids[p["id"]] = r["predicate_id"]
        rep["predicates"] += 1

    # library rules: atomic first, then compositions ----------------------------
    rule_ids: dict[str, str] = {}
    rules = data.get("library_rules", [])
    for rule in sorted(rules, key=lambda r: bool(r.get("composed_of"))):
        existing = conn.execute("SELECT id FROM library_rules WHERE key = ? OR rule_text = ?",
                                (rule["id"], rule["rule_text"])).fetchone()
        if existing:
            rule_ids[rule["id"]] = existing["id"]
            rep["skipped"].append(f"rule {rule['id']}")
            continue
        parts = [rule_ids[k] for k in rule.get("composed_of", [])]
        r = _propose_seed_rule(conn, rule,
                            rule["provenance"], parts or None, key=rule["id"])
        rule_ids[rule["id"]] = r["rule_id"]
        rep["library_rules"] += 1

    # events + rounds (created only; played after holders/positions exist) -------------
    round_ids: dict[str, str] = {}
    events = {e["id"]: e for e in data.get("events", [])}
    pending_rounds: list[dict] = []
    for rr in data.get("rounds", []):
        ev = events[rr["event_id"]]
        h = rounds.event_hash(ev["event_text"].strip(), ev["event_date"])
        row = conn.execute("SELECT r.id FROM rounds r JOIN events e ON e.id = r.event_id WHERE e.event_hash = ?",
                           (h,)).fetchone()
        if row:
            round_ids[rr["id"]] = row["id"]
            rep["skipped"].append(f"round {rr['id']}")
            continue
        criteria = {k: _criterion(v) for k, v in ev["criteria_json"].items()}
        for k, v in ev["criteria_json"].items():
            if criteria[k] != str(v).strip():
                rep["warnings"].append(f"{rr['id']} {k}: recorded as unknown with note {str(v)!r}")
        sub = rounds.submit_event(conn, ev["event_text"], ev["event_date"], ev["source"], ev["selection_rule"],
                                  ev.get("rejected_before", 0), criteria, round_class="learning",
                                  operator_model=rr.get("operator"))
        round_ids[rr["id"]] = sub["round_id"]
        pending_rounds.append(rr)

    # holders (parents first), aliases, positions -----------------------------------
    holder_ids: dict[str, str] = {}
    holders = data.get("holders", [])
    order, seen = [], set()

    def visit(h):
        if h["id"] in seen:
            return
        if h.get("parent_id"):
            visit(next(x for x in holders if x["id"] == h["parent_id"]))
        seen.add(h["id"])
        order.append(h)

    for h in holders:
        visit(h)
    alias_by_holder: dict[str, list] = {}
    for a in data.get("aliases", []):
        alias_by_holder.setdefault(a["holder_id"], []).append(
            {"alias": a["alias"], "alias_kind": a.get("alias_kind", "name"), "source": a.get("source", "seed"),
             "knowable_from": a.get("knowable_from")})
    for h in order:
        r = names.holder_upsert(conn, h["canonical_name"], h["kind"], h.get("listed", False),
                                holder_ids.get(h["parent_id"]) if h.get("parent_id") else None,
                                h.get("ticker"), h.get("exchange"), alias_by_holder.get(h["id"], []),
                                source="seed", first_seen_round=round_ids.get(h.get("first_seen_round") or ""),
                                key=h["id"])
        holder_ids[h["id"]] = r["holder_id"]
        rep["holders"] += int(r["created"])
        rep["aliases"] += r["aliases_added"]
        if not r["created"]:
            rep["skipped"].append(f"holder {h['id']} (exists; aliases merged)")

    pos_ids: dict[str, str] = {}
    for pos in data.get("positions", []):
        if pos.get("superseded_by"):
            raise HarnessError(f"position {pos['id']}: superseded_by is not supported in seeds; order rows and use supersedes")
        hid = holder_ids[pos["holder_id"]]
        values = ["+", "-"] if pos["value"] == "both" else [pos["value"]]
        for v in values:
            dup = conn.execute(
                "SELECT id FROM positions WHERE holder_id=? AND lower(node)=lower(?) AND attribute=? AND value=? AND source=?",
                (hid, pos["node"], pos["attribute"], str(v), pos["source"])).fetchone()
            if dup:
                pos_ids[pos["id"]] = dup["id"]
                rep["skipped"].append(f"position {pos['id']}")
                continue
            r = positions.position_add(conn, hid, pos["node"], pos["attribute"], v, pos["source"], pos["confidence"],
                                       pos.get("unit"), pos.get("source_time"), pos.get("knowable_from"))
            pos_ids[pos["id"]] = r["position_id"]
            rep["positions"] += 1
        if pos["value"] == "both":
            rep["warnings"].append(f"position {pos['id']}: sign 'both' stored as two rows (+ and -); reads as self-hedged")

    # play the retro rounds ------------------------------------------------------------
    preds_by_round: dict[str, list] = {}
    for p in data.get("predictions", []):
        preds_by_round.setdefault(p["round_id"], []).append(p)
    evid_by_round: dict[str, list] = {}
    for e in data.get("evidence", []):
        evid_by_round.setdefault(e["round_id"], []).append(e)
    checks_by_round: dict[str, list] = {}
    for c in data.get("predicate_checks", []):
        checks_by_round.setdefault(c["round_id"], []).append(c)
    res_by_pred = {r["prediction_id"]: r for r in data.get("resolutions", [])}
    for rr in pending_rounds:
        rid = round_ids[rr["id"]]
        plist = preds_by_round.get(rr["id"], [])
        pin = []
        for p in plist:
            pin.append({k: p.get(k) for k in ("call_type", "target", "claim", "sign", "magnitude_rank", "lag_band",
                                               "carrier", "falsifier", "baseline_claim", "confidence_band")}
                       | {"mechanism_ids": [rule_ids[k] for k in p.get("mechanism_ids", [])],
                          "falsifier_window": p.get("falsifier_window", "scoring_window")})
        lock = rounds.lock_predictions(conn, rid, pin, lock_note="no-touched-set: retro seed round; positions carried in the seed",
                                       strict=False)
        call_ids = dict(zip((p["id"] for p in plist), lock["prediction_ids"]))
        rounds.open_retrieval(conn, rid)
        ev_ids = {}
        for e in evid_by_round.get(rr["id"], []):
            ev_ids[e["id"]] = rounds.add_evidence(conn, rid, e["url"], e["title"], e["excerpt"], e.get("source_time"),
                                                  e.get("knowable_from"), e.get("note"))["evidence_id"]
        if checks_by_round.get(rr["id"]):
            checks = []
            for c in checks_by_round[rr["id"]]:
                scope = c.get("scope")
                if scope is None and c["predicate_id"] == "pred.arm.first_traversal":
                    scope = "node" if "fails at node" in (c.get("note") or "").lower() else "event"
                checks.append({"predicate_id": pred_ids[c["predicate_id"]], "claimed": c["claimed"],
                               "observed": c.get("observed"), "note": c.get("note"), "scope": scope,
                               "basis": c.get("basis") or (c.get("note") or "session record (retro)") if c["claimed"] != "unknown" else None})
            predicates.predicate_check(conn, rid, checks)
        resolutions = []
        for p in plist:
            r = res_by_pred.get(p["id"])
            if not r:
                raise HarnessError(f"seed: no resolution for prediction {p['id']}")
            resolutions.append({
                "prediction_id": call_ids[p["id"]], "outcome": r["outcome"], "mechanism_outcome": r["mechanism_outcome"],
                "baseline_outcome": r["baseline_outcome"], "evidence_ids": [ev_ids[e] for e in r.get("evidence_ids", [])],
                "scorer_note": ("retro=true; " if rr.get("retro", True) else "") + r.get("scorer_note", ""),
                "source_coverage": r.get("source_coverage", "adequate" if r["outcome"] in ("hit", "untestable") else "thin"),
                "scorer": r.get("scorer", "self"),
            })
        card = scorer.score_round(conn, rid, resolutions)
        # the seed pre-computed quarantine and weight; the harness derives them and they must agree
        stored = rounds.latest_resolutions(conn, rid)
        for p in plist:
            r = res_by_pred[p["id"]]
            s = stored[call_ids[p["id"]]]
            if bool(s["quarantined"]) != bool(r.get("quarantined", False)) or float(s["weight"]) != float(r.get("weight", 1.0)):
                rep["warnings"].append(
                    f"{p['id']}: harness derived quarantined={bool(s['quarantined'])} weight={s['weight']} "
                    f"vs seed quarantined={r.get('quarantined')} weight={r.get('weight')}")
        rep.setdefault("scorecards", {})[rr["id"]] = {k: card[k] for k in
                                                       ("outcome_score", "mechanism_score", "baseline_score",
                                                        "edge_vs_baseline", "null_called", "arming_claimed", "arming_observed",
                                                        "any_arming_claimed", "any_arming_observed")}
        rep["retro_rounds"] += 1

    # hypotheses -------------------------------------------------------------------------
    existing_h = {r["text"] for r in conn.execute("SELECT text FROM hypotheses")}
    for hy in data.get("hypotheses", []):
        if hy["text"] in existing_h:
            rep["skipped"].append(f"hypothesis {hy['id']}")
            continue
        hypotheses.hypothesis_open(
            conn, hy["text"], [holder_ids[k] for k in hy.get("holder_ids", [])],
            [rule_ids[k] for k in hy.get("mechanism_ids", [])],
            [pred_ids[k] for k in hy["arming_predicate_ids"]], [pred_ids[k] for k in hy.get("disarming_predicate_ids", [])],
            hy["falsifier"], hy["granularity"], hy.get("node"),
            [pos_ids[k] for k in hy.get("position_ids") or []] or None,
            round_ids.get(hy.get("opened_in_round") or ""))
        rep["hypotheses"] += 1

    # t0 candidates ------------------------------------------------------------------------
    for c in data.get("t0_candidates", []):
        eid = round_ids.get(c["event_id"], c["event_id"])
        if conn.execute("SELECT 1 FROM t0_candidates WHERE event_id = ? AND window_label = ?", (eid, c["window_label"])).fetchone():
            rep["skipped"].append(f"t0 {c['event_id']}/{c['window_label']}")
            continue
        t0.submit_candidate(conn, eid, c["window_label"], c["criteria_pass"], c.get("arming_pass_single"),
                            c.get("arming_pass_pair"), c.get("listed_party"), c.get("pair_holders"), c.get("carrier"),
                            c.get("micro_macro_note"))
        rep["t0_candidates"] += 1

    rep["library_rebuild"] = library.rebuild_library_stats(conn)
    rep["chain_ok"] = verify_chain(conn)["ok"]
    return rep


# ---------------------------------------------------------------------------
# nested layout (seed_v1.json, seed_v4_template.json)

def load_seed_nested(conn: sqlite3.Connection, data: dict, path: str) -> dict:
    report: dict = {"seed": path, "predicates": 0, "library_rules": 0, "holders": 0, "positions": 0,
                    "hypotheses": 0, "retro_rounds": 0, "skipped": [], "notes": data.get("_notes", [])}
    pred_ids: dict[str, str] = {p["name"]: p["id"] for p in predicates.predicate_list(conn, include_inactive=True)}
    for p in data.get("predicates", []):
        if p["name"] in pred_ids:
            report["skipped"].append(f"predicate {p['name']}")
            continue
        r = predicates.predicate_add(conn, p["name"], p["kind"], p["source"], p["threshold"],
                                     p.get("date"), p.get("role_note"), p.get("active", True), key=p.get("key"))
        pred_ids[p["name"]] = r["predicate_id"]
        report["predicates"] += 1

    rule_ids: dict[str, str] = {}
    existing_rules = {r["rule_text"]: r["id"] for r in library.query(conn, limit=10_000)}
    for rule in data.get("library_rules", []):
        key = rule.get("key", rule["rule_text"])
        if rule["rule_text"] in existing_rules:
            rule_ids[key] = existing_rules[rule["rule_text"]]
            report["skipped"].append(f"rule {key}")
            continue
        parts = [rule_ids[k] for k in rule.get("composed_of", [])]
        r = _propose_seed_rule(conn, rule,
                            rule["provenance"], parts or None, key=rule.get("key"))
        rule_ids[key] = r["rule_id"]
        report["library_rules"] += 1

    holder_ids: dict[str, str] = {}
    for h in data.get("holders", []):
        key = h.get("key", h["canonical_name"])
        r = names.holder_upsert(conn, h["canonical_name"], h["kind"], h.get("listed", False),
                                holder_ids.get(h.get("parent")) if h.get("parent") else None,
                                h.get("ticker"), h.get("exchange"), h.get("aliases", []), source=h.get("source", "seed"),
                                key=h.get("key"))
        holder_ids[key] = r["holder_id"]
        if r["created"]:
            report["holders"] += 1
        else:
            report["skipped"].append(f"holder {key} (exists; aliases merged)")

    for pos in data.get("positions", []):
        hid = holder_ids[pos["holder"]]
        dup = conn.execute(
            "SELECT 1 FROM positions WHERE holder_id=? AND lower(node)=lower(?) AND attribute=? AND value=? AND source=?",
            (hid, pos["node"], pos["attribute"], str(pos["value"]), pos["source"])).fetchone()
        if dup:
            report["skipped"].append(f"position {pos['holder']}/{pos['node']}/{pos['attribute']}")
            continue
        positions.position_add(conn, hid, pos["node"], pos["attribute"], pos["value"], pos["source"],
                               pos["confidence"], pos.get("unit"), pos.get("source_time"), pos.get("knowable_from"))
        report["positions"] += 1

    for rr in data.get("retro_rounds", []):
        ev = rr["event"]
        h = rounds.event_hash(ev["event_text"].strip(), ev["event_date"])
        if conn.execute("SELECT 1 FROM events WHERE event_hash = ?", (h,)).fetchone():
            report["skipped"].append(f"retro round {ev['event_text'][:40]}")
            continue
        sub = rounds.submit_event(conn, ev["event_text"], ev["event_date"], ev["source"], ev["selection_rule"],
                                  ev.get("rejected_before", 0), ev["criteria_json"], round_class="learning",
                                  operator_model=rr.get("operator"))
        rid = sub["round_id"]
        preds = []
        for p in rr["predictions"]:
            p = dict(p)
            p["mechanism_ids"] = [rule_ids[k] for k in p.pop("mechanism_keys", [])]
            p.setdefault("falsifier_window", "scoring_window")
            preds.append(p)
        lock = rounds.lock_predictions(conn, rid, preds, lock_note="no-touched-set: retro seed round", strict=False)
        rounds.open_retrieval(conn, rid)
        ev_ids = []
        for e in rr.get("evidence", []):
            ev_ids.append(rounds.add_evidence(conn, rid, e["url"], e["title"], e["excerpt"], e.get("source_time"),
                                              e.get("knowable_from"), e.get("note"))["evidence_id"])
        if rr.get("predicate_checks"):
            predicates.predicate_check(conn, rid, rr["predicate_checks"])
        res = []
        for i, r in enumerate(rr["resolutions"]):
            r = dict(r)
            r["prediction_id"] = lock["prediction_ids"][r.pop("prediction_index", i)]
            r["evidence_ids"] = [ev_ids[j] for j in r.pop("evidence_indexes", [])]
            r["scorer_note"] = "retro=true; " + r.get("scorer_note", "")
            r.setdefault("source_coverage", "adequate" if r["outcome"] in ("hit", "untestable") else "thin")
            res.append(r)
        scorer.score_round(conn, rid, res)
        report["retro_rounds"] += 1

    existing_h = {r["text"] for r in conn.execute("SELECT text FROM hypotheses")}
    for hy in data.get("hypotheses", []):
        if hy["text"] in existing_h:
            report["skipped"].append(f"hypothesis {hy['text'][:40]}")
            continue
        hypotheses.hypothesis_open(
            conn, hy["text"], [holder_ids[k] for k in hy.get("holders", [])],
            [rule_ids[k] for k in hy.get("mechanisms", [])],
            [pred_ids[n] for n in hy["arming"]], [pred_ids[n] for n in hy.get("disarming", [])],
            hy["falsifier"], hy["granularity"], hy.get("node"))
        report["hypotheses"] += 1
    return report


def _propose_seed_rule(conn, rule, *args, **kw):
    """v8 A1: seed rules take carries from the seed, else the backfill table, else a generic pair (reported)."""
    from .errors import ValidationError
    carries = rule.get("carries") or library.backfill_lookup(rule.get("key") or rule.get("id"), rule["rule_text"])
    if carries is None:
        carries = [] if rule.get("layer") == "operator" else ["occurrence", "absence"]
    return library.propose(conn, rule["rule_text"], rule["forbids"], rule["obscurity"], rule["layer"], *args, carries=carries, **kw)
