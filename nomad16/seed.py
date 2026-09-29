"""Load ``config/seed.json`` into the stores: attributes, library rules (obligation
templates are library rules of kind ``obligation``), vocabularies, bounds, transforms,
tides, carriers. Idempotent; every change is dated on the ledger by ``db.upsert``."""
from __future__ import annotations

import json

from .db import DB, ROOT
from .effects import transform_add
from .positions import attribute_add, bound_add
from .reach import outcome_vocab_add


def seed(db: DB, path=None) -> dict:
    doc = json.loads((path or ROOT / "config" / "seed.json").read_text())
    by = "seed"
    for a in doc["position_attributes"]:
        attribute_add(db, a["attribute"], a["type"], a.get("unit"), a.get("allowed"), a.get("description", ""))
    for r in doc["library_rules"]:
        db.upsert("library_rules", r["id"], by=by, rule_text=r["text"], forbids=r["forbids"], layer=r["layer"],
                  kind="mechanism", status="candidate" if r["layer"] == "candidate" else "active",
                  carries=r["carries"], weight=0.0, weight_state="untested_as_carried",
                  provenance=doc["_meta"]["authored"])
    for t in doc["obligation_templates"]:
        db.upsert("library_rules", t["id"], by=by, rule_text=t["text"], forbids=t["forbids"], layer="obligation",
                  kind="obligation", status="active", carries=["occurrence"], weight=0.0,
                  weight_state="untested_as_carried", provenance=doc["_meta"]["authored"])
        db.upsert("obligation_templates", t["id"], by=by, node_types=t["node_types"], roles=t["roles"],
                  conditions=t["conditions"], forces=t["forces"], carrier_kinds=t["carrier_kinds"],
                  window_rule=t["window_rule"], forbids=t["forbids"], authored_from=doc["_meta"]["authored"])
    for kind, outs in doc["outcome_vocabs"].items():
        outcome_vocab_add(db, kind, outs, doc["_meta"]["authored"])
    for b in doc["bounds"]:
        bound_add(db, b["id"], b["subject"], b["quantity"], b["value"], b["unit"], b["source_document"],
                  b["knowable_from"], authored_by="builder")
    for t in doc["transforms"]:
        transform_add(db, t["relation"], t["from"], t["to"], t["value"], t.get("basis", "builder seed"))
    for t in doc["tides"]:
        db.upsert("tides", t["id"], by=by, label=t["label"], declared_by="registry", from_date=None,
                  to_date=None, retro_declared=False, proxy=t["proxy"])
    for c in doc["carriers"]:
        db.upsert("carriers", c["id"], by=by, kind=c["kind"], node_types=c["node_types"],
                  fetch_path=c["fetch_path"], description="", read_in_full_rule=c["read_in_full_rule"])
    return {k: len(v) for k, v in doc.items() if k != "_meta"}


def library_as_of(db: DB, date: str) -> dict:
    """Rules and weights computed only from resolutions knowable by ``date`` (§9).

    No resolution has been banked under v16 yet, so every rule reads
    ``untested_as_carried`` with zero trials; the history table is where weights will land.
    """
    from .util import le
    hist = [h for h in db.rows("library_history") if le(h["valid_from"], date)]
    latest = {h["rule_id"]: h for h in hist}
    out = []
    for r in db.rows("library_rules"):
        h = latest.get(r["key"])
        out.append({"rule_id": r["key"], "kind": r["kind"], "layer": r["layer"], "status": r["status"],
                    "text": r["rule_text"], "forbids": r["forbids"], "carries": r["carries"],
                    "weight": h["weight"] if h else 0.0,
                    "weight_state": h["weight_state"] if h else "untested_as_carried",
                    "trials_as_carried": h["trials_as_carried"] if h else 0,
                    "tide_count": h["tide_count"] if h else 0})
    return {"as_of": date, "rules": out}
