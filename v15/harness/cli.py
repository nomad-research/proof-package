"""`nomad-harness init | serve | verify | status | model-cutoff | window`"""
import argparse
import json
import os
import sys
from pathlib import Path

from .config import MODEL_CUTOFF_SEED, db_path
from .db import connect, verify_chain


def _seed_model_cutoffs(conn) -> int:
    from .rounds import model_cutoff, model_cutoff_set
    n = 0
    for model_id, cutoff in MODEL_CUTOFF_SEED.items():
        if model_cutoff(conn, model_id) is None:
            model_cutoff_set(conn, model_id, cutoff, "config.MODEL_CUTOFF_SEED")
            n += 1
    return n


def bootstrap(conn) -> dict:
    """v8/v9: registries that every DB carries (idempotent): carries backfill, carriers and their fetch paths,
    synthetic construction rules, the selector row, snapshot targets."""
    from .carriers import seed_carriers, seed_fetch_paths
    from .library import backfill_carries
    from .rounds import selector_status
    from .snapshots import seed_targets
    from .synthetic import seed_synthetic_rules
    from .edge import base_rate_seed
    from .enumeration import seed_feeds
    from .prices import seed_carrier
    from .risk import seed_risk_rules, set_preconditions, setting, setting_set
    out = {"carries_backfill": backfill_carries(conn), "carriers_seeded": seed_carriers(conn),
           "synthetic_rules_seeded": seed_synthetic_rules(conn), "fetch_paths_seeded": seed_fetch_paths(conn)}
    selector_status(conn)
    out["snapshot_targets"] = seed_targets(conn)
    out["feeds_seeded"] = seed_feeds(conn)
    out["risk_rules_seeded"] = seed_risk_rules(conn)
    out["base_rates_seeded"] = base_rate_seed(conn)
    out["price_carrier"] = seed_carrier(conn)
    out["preconditions"] = set_preconditions(conn)          # v13 A3
    from .effects import seed_transforms                     # v15 A4
    out["transforms_seeded"] = seed_transforms(conn)
    # v13 is switched on for the ledger by an explicit setting, never by bootstrap: it changes what lock refuses, and a
    # round admitted before the switch is not retried under rules that did not exist when it was locked.
    out["v13_started_at"] = setting(conn, "v13_started_at")
    return out


def cmd_init(args) -> int:
    from .seed import DEFAULT_SEED, load_seed
    path = Path(args.db or db_path())
    existed = path.exists()
    conn = connect(path)
    cutoffs = _seed_model_cutoffs(conn)
    report = load_seed(conn, args.seed or DEFAULT_SEED)
    report["bootstrap"] = bootstrap(conn)
    chain = verify_chain(conn)
    print(json.dumps({"db": str(path.resolve()), "existed": existed, "model_cutoffs_seeded": cutoffs, "seed": report,
                      "chain_ok": chain["ok"]}, indent=2))
    return 0 if chain["ok"] else 1


def cmd_migrate(args) -> int:
    """Apply schema migrations to an existing DB, seed model_cutoffs, rebuild stats, verify."""
    from .library import rebuild_library_stats
    conn = connect(Path(args.db or db_path()))
    cutoffs = _seed_model_cutoffs(conn)
    boot = bootstrap(conn)
    lib = rebuild_library_stats(conn)
    chain = verify_chain(conn)
    print(json.dumps({"model_cutoffs_seeded": cutoffs, "bootstrap": boot, "library_rebuild": lib, "chain_ok": chain["ok"],
                      "legacy_rows": {t: v.get("legacy_form_rows", 0) for t, v in chain["tables"].items()}}, indent=2))
    return 0 if chain["ok"] else 1


def cmd_serve(args) -> int:
    if args.db:
        os.environ["NOMAD_HARNESS_DB"] = args.db
    from .server import run
    run("streamable-http" if args.http else "stdio", args.host, args.port)
    return 0


def cmd_verify(args) -> int:
    conn = connect(Path(args.db or db_path()))
    r = verify_chain(conn, args.table)
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


def cmd_status(args) -> int:
    conn = connect(Path(args.db or db_path()))
    from .scorer import programme_stats
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("events", "rounds", "predictions", "evidence", "resolutions", "library_rules", "predicates",
                        "holders", "aliases", "orphans", "positions", "hypotheses", "t0_candidates", "hook_denials",
                        "narrowing_log")}
    states = {r["state"]: r["n"] for r in conn.execute("SELECT state, COUNT(*) AS n FROM round_state GROUP BY state")}
    classes = {f"{r['round_class']}/{r['contamination']}": r["n"] for r in conn.execute(
        "SELECT round_class, contamination, COUNT(*) AS n FROM round_classification GROUP BY 1, 2")}
    print(json.dumps({"db": str(Path(args.db or db_path()).resolve()), "rows": counts, "round_states": states,
                      "round_classes": classes, "programme_clean": programme_stats(conn),
                      "programme_all": programme_stats(conn, include_learning=True)}, indent=2))
    return 0


def cmd_model_cutoff(args) -> int:
    from .rounds import model_cutoff_set, model_cutoffs_list
    conn = connect(Path(args.db or db_path()))
    if args.action == "set":
        print(json.dumps(model_cutoff_set(conn, args.model_id, args.cutoff, args.source)))
    else:
        print(json.dumps(model_cutoffs_list(conn), indent=2))
    return 0


def cmd_ingest(args) -> int:
    from .facts import DEFAULT_SOURCES, ingest
    conn = connect(Path(args.db or db_path()))
    report = ingest(conn, args.sources or DEFAULT_SOURCES)
    print(json.dumps(report, indent=2))
    return 0


def cmd_facts(args) -> int:
    from .facts import node_facts, targets
    conn = connect(Path(args.db or db_path()))
    print(json.dumps({"targets_open": targets(conn, "open"), "facts": node_facts(conn, args.node, None, args.since, args.limit)},
                     indent=2))
    return 0


def cmd_retag(args) -> int:
    """v9 §0.2: human re-tag of a round (new round_tags row with supersedes)."""
    from .rounds import retag
    conn = connect(Path(args.db or db_path()))
    print(json.dumps(retag(conn, args.round_id, args.tag, args.reason, q1a=args.q1a, q1a_basis=args.q1a_basis, q1b=args.q1b), indent=2))
    return 0


def cmd_reclassify(args) -> int:
    """Human reclassification of a round (append-only round_classifications row)."""
    from .rounds import classification, classify
    conn = connect(Path(args.db or db_path()))
    cur = classification(conn, args.round_id)
    row = classify(conn, args.round_id, args.round_class, cur["contamination"], f"human: {args.reason}")
    print(json.dumps({"round_id": args.round_id, "from": cur["round_class"], "to": args.round_class, "row": row["id"]}, indent=2))
    return 0


def cmd_ingest_scheduled(args) -> int:
    from .scheduled import ingest_scheduled
    conn = connect(Path(args.db or db_path()))
    print(json.dumps(ingest_scheduled(conn, args.holders or None, args.as_of), indent=2))
    return 0


def cmd_snapshot_run(args) -> int:
    from .snapshots import run
    conn = connect(Path(args.db or db_path()))
    print(json.dumps(run(conn, limit=args.limit, kind=args.kind), indent=2))
    return 0


def cmd_probe_carriers(args) -> int:
    from .carriers import probe
    conn = connect(Path(args.db or db_path()))
    out = []
    for r in conn.execute("SELECT key, name, url FROM carriers WHERE url IS NOT NULL ORDER BY name"):
        if args.carrier and args.carrier not in (r["key"], r["name"]):
            continue
        try:
            out.append(probe(conn, r["key"] or r["name"]))
        except Exception as e:
            out.append({"carrier": r["name"], "error": str(e)[:200]})
    print(json.dumps(out, indent=2))
    return 0


def cmd_freeze(args) -> int:
    """v10 §H1: declare the freeze (schema and protocol fixed for seven admitted rounds) and switch on the v10 intake rules."""
    from .risk import setting_set
    from .util import now_iso
    conn = connect(Path(args.db or db_path()))
    out = {"freeze_started_at": setting_set(conn, "freeze_started_at", args.at or now_iso(), args.reason),
           "clean_lag_days": setting_set(conn, "clean_lag_days", "0", "v10 A1: age leaves Q7"),
           "cap_lookback": setting_set(conn, "cap_lookback", "1", "v10 B2: at most one weather/late_headline in any two consecutive admitted")}
    print(json.dumps(out, indent=2))
    return 0


def cmd_calls_due(args) -> int:
    from .scorer import calls_due
    conn = connect(Path(args.db or db_path()))
    print(json.dumps(calls_due(conn, args.before), indent=2))
    return 0


def cmd_replay(args) -> int:
    from .replay import replay_all, replay_round
    conn = connect(Path(args.db or db_path()))
    r = (replay_round(conn, args.round_id, write=not args.dry_run, stack=args.stack) if args.round_id
         else replay_all(conn, write=not args.dry_run, stack=args.stack))
    print(json.dumps(r, indent=2))
    return 0


def cmd_window(args) -> int:
    from .rounds import event_window
    conn = connect(Path(args.db or db_path()))
    print(json.dumps(event_window(conn, args.model), indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="nomad-harness")
    ap.add_argument("--db", help="SQLite path (default: $NOMAD_HARNESS_DB or ./nomad_harness.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="create the DB and load a seed (idempotent)")
    p.add_argument("--seed", help="seed JSON path (default: harness/seed/seed_v4.json)")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("migrate", help="apply schema migrations to an existing DB and rebuild stats")
    p.set_defaults(fn=cmd_migrate)
    p = sub.add_parser("serve", help="run the MCP server (stdio by default)")
    p.add_argument("--http", action="store_true")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(fn=cmd_serve)
    p = sub.add_parser("verify", help="walk the hash chains")
    p.add_argument("--table")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("status", help="row counts, round states and classes, programme stats")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("model-cutoff", help="human-maintained operator cutoffs (A2)")
    p.add_argument("action", choices=["set", "list"])
    p.add_argument("model_id", nargs="?")
    p.add_argument("cutoff", nargs="?", help="YYYY-MM-DD")
    p.add_argument("--source")
    p.set_defaults(fn=cmd_model_cutoff)
    p = sub.add_parser("ingest", help="B4: pull the configured feeds into node_facts (run daily)")
    p.add_argument("--sources", help="sources JSON (default: harness/ingest_sources.json)")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("facts", help="B4: open ingest targets and recent node facts")
    p.add_argument("--node")
    p.add_argument("--since", help="ISO date")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_facts)
    p = sub.add_parser("retag", help="v9: human re-tag of a round (new round_tags row)")
    p.add_argument("round_id")
    p.add_argument("tag", choices=["lag_test", "weather", "late_headline", "learning"])
    p.add_argument("--reason", required=True)
    p.add_argument("--q1a")
    p.add_argument("--q1a-basis", dest="q1a_basis")
    p.add_argument("--q1b")
    p.set_defaults(fn=cmd_retag)
    p = sub.add_parser("reclassify", help="human reclassification of a round (append-only)")
    p.add_argument("round_id")
    p.add_argument("round_class", choices=["clean", "learning"])
    p.add_argument("--reason", required=True)
    p.set_defaults(fn=cmd_reclassify)
    p = sub.add_parser("ingest-scheduled", help="v9 A2: scheduled facts from EDGAR and IR events pages")
    p.add_argument("--holders", nargs="*")
    p.add_argument("--as-of", dest="as_of")
    p.set_defaults(fn=cmd_ingest_scheduled)
    p = sub.add_parser("snapshot-run", help="v9 D2: Wayback save-page-now over the snapshot targets")
    p.add_argument("--limit", type=int)
    p.add_argument("--kind")
    p.set_defaults(fn=cmd_snapshot_run)
    p = sub.add_parser("probe-carriers", help="v9 D1: probe live and Wayback paths for carriers with a url")
    p.add_argument("--carrier")
    p.set_defaults(fn=cmd_probe_carriers)
    p = sub.add_parser("freeze", help="v10: declare the freeze and switch on live rounds, the size band and the two-round cap")
    p.add_argument("--at", help="ISO timestamp (default now)")
    p.add_argument("--reason", default="v10 §H1 freeze declaration")
    p.set_defaults(fn=cmd_freeze)
    p = sub.add_parser("calls-due", help="v10 A3: unresolved calls due across live rounds")
    p.add_argument("--before")
    p.set_defaults(fn=cmd_calls_due)
    p = sub.add_parser("replay", help="v11 B: measure locked legs under the frozen instrument (never touches resolutions)")
    p.add_argument("round_id", nargs="?")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--stack", choices=["v11", "v12"], default="v12", help="v12 H5: which coverage dating to read")
    p.set_defaults(fn=cmd_replay)
    p = sub.add_parser("window", help="clean event window for an operator (A3)")
    p.add_argument("--model")
    p.set_defaults(fn=cmd_window)
    args = ap.parse_args(argv)
    if args.cmd == "model-cutoff" and args.action == "set" and not (args.model_id and args.cutoff):
        ap.error("model-cutoff set needs MODEL_ID and CUTOFF")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
