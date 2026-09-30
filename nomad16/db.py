"""The store: SQLite in WAL mode, ledger tables hash-chained, mutable stores beside them.

Spec v16 §14 ("The ledger, as v15 built it") and §17-§18.

* Ledger tables are append-only. Every row carries ``prev_row_hash`` and
  ``row_hash``, chaining the rows of its table, and ``recorded_at`` is set here
  and nowhere else. UPDATE and DELETE are refused by triggers.
* Mutable stores are corrected in place. What a round read from them is pinned by
  the lock manifest (``lock.py``), which is what makes replay possible.

Fresh build (§30.3): the v15 harness is not available in this repository, so the
table set is the v16 minimum, not v15's tables evolved. ``STATE.md`` records it.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "state" / "nomad16.db"

GENESIS = "0" * 64

# ---------------------------------------------------------------------------
# Schema. (kind, columns). Ledger tables get id/recorded_at/prev_row_hash/row_hash;
# mutable tables get a text primary key ``key`` and ``updated_at``.
# JSON-valued columns are stored as canonical JSON text.
# ---------------------------------------------------------------------------
LEDGER = "ledger"
MUTABLE = "mutable"

TABLES: dict[str, tuple[str, list[str]]] = {
    # --- rounds and lifecycle -------------------------------------------------
    "rounds": (LEDGER, ["round_id", "event_line", "event_date", "event_time", "node",
                        "node_type", "stratum", "feed_set", "intake_mode", "round_class",
                        "live", "operator_model", "operator_cutoff", "operator_runtime",
                        "harness_version", "logic_version", "config_hash",
                        "presort_active", "domain_pref", "candidate_id", "q_results"]),
    "round_meta": (LEDGER, ["round_id", "field", "value", "supersedes"]),
    "round_tags": (LEDGER, ["round_id", "tag", "basis"]),
    "round_state": (LEDGER, ["round_id", "state", "reason"]),
    "operator_manifests": (LEDGER, ["round_id", "operator_model", "operator_runtime",
                                    "operator_cutoff", "cutoff_basis", "session_id",
                                    "hook_verified", "hook_evidence", "cold"]),
    "notes": (LEDGER, ["round_id", "segment_idx", "subject", "text"]),
    # --- intake ---------------------------------------------------------------
    "enumeration_runs": (LEDGER, ["run_id", "feed_set", "from_date", "to_date",
                                  "source_mode", "complete", "truncation_reason", "n_items"]),
    "intake_candidates": (LEDGER, ["cand_id", "run_id", "item_date", "source_record",
                                   "title", "q_results", "decision", "reason", "failing_q"]),
    # --- evidence -------------------------------------------------------------
    "evidence": (LEDGER, ["evidence_id", "round_id", "url", "source", "source_time",
                          "knowable_from", "carrier", "retrieved_pre_lock", "path",
                          "content_hash", "summary"]),
    "pit_fetches": (LEDGER, ["round_id", "source", "target", "as_of", "reason", "status",
                             "evidence_id", "detail"]),
    # --- names book, positions ------------------------------------------------
    "positions": (LEDGER, ["position_id", "holder_id", "node", "asset_ref", "attribute",
                           "value", "value_num", "unit", "source", "source_document",
                           "source_time", "knowable_from", "confidence", "supersedes",
                           "evidence_ids"]),
    "node_facts": (LEDGER, ["fact_id", "round_id", "node", "kind", "effect_kind", "text",
                            "knowable_from", "evidence_ids"]),
    # --- effects and vetoes ---------------------------------------------------
    "effects": (LEDGER, ["effect_id", "round_id", "segment_idx", "holder_id", "node",
                         "asset_ref", "effect_kind", "sign", "magnitude_pct",
                         "parent_effect_id", "relation", "depth", "root_effect_id",
                         "transmission", "ack_id", "outcome_id", "cited_rules",
                         "position_ids", "evidence_ids", "vetoed_by", "carried_by"]),
    "surviving_risk": (LEDGER, ["round_id", "segment_idx", "lock_seq", "effect_id",
                                "status", "vetoes_fired", "vetoes_unevaluable", "terms",
                                "gap_reasons", "stake_basis", "operator_basis", "n"]),
    # --- ACKs, derivation, reach ------------------------------------------------
    "ack_status": (LEDGER, ["ack_id", "status", "reason", "is_switch"]),
    "ack_derivations": (LEDGER, ["derivation_id", "round_id", "segment_idx", "clock",
                                 "template_id", "bindings", "conditions", "result",
                                 "fetch_list", "ack_id"]),
    "ack_outcomes": (LEDGER, ["ack_id", "round_id", "segment_idx", "outcome_id", "reach",
                              "cut_by", "evidence_ids", "need_states"]),
    "thesis_sets": (LEDGER, ["ack_id", "round_id", "segment_idx", "in_thesis",
                             "exclusions", "basis"]),
    "ack_firings": (LEDGER, ["firing_id", "ack_id", "round_id", "fired_at", "delivered",
                             "delivered_fact", "outcome_id", "knowable_from",
                             "successor_ack_ids", "evidence_ids", "segment_idx_opened"]),
    "segments": (LEDGER, ["round_id", "idx", "clock", "opened_by_ack_id",
                          "opened_by_firing_id", "locked_at", "lock_hash", "manifest_id",
                          "wall_clock"]),
    # --- calls and scoring ------------------------------------------------------
    "predictions": (LEDGER, ["call_id", "round_id", "segment_idx", "call_type",
                             "claim_kind", "claim", "branches", "lag_band", "carrier",
                             "fetch_path", "due_at", "falsifier", "cited_rules", "factors",
                             "effect_id", "ack_id", "narrative_sign"]),
    "resolutions": (LEDGER, ["call_id", "round_id", "outcome", "branch", "carrier_state",
                             "source_coverage", "expired", "quality", "evidence_ids",
                             "basis", "supersedes"]),
    # --- stories ----------------------------------------------------------------
    "story_classes": (LEDGER, ["story_id", "round_id", "segment_idx", "key", "active",
                               "active_basis", "angle", "cos", "class", "decomposition",
                               "s_ref_hash", "treatment"]),
    "story_loadings": (LEDGER, ["story_id", "instrument_id", "round_id", "segment_idx",
                                "key", "loading", "se", "window_from", "window_to",
                                "vintage_ids", "kind"]),
    "junctions": (LEDGER, ["junction_id", "round_id", "segment_idx", "story_a", "story_b",
                           "shared_node", "trigger_ack_id", "corr_before", "corr_after",
                           "status", "treatment", "node_story_id"]),
    "s_perp": (LEDGER, ["round_id", "segment_idx", "key", "ack_id", "outcome_id",
                        "s_vec", "s_norm", "s_perp_norm", "rho", "residual_noise_band",
                        "hedged_set", "flat"]),
    # --- prices -------------------------------------------------------------------
    "price_vintages": (LEDGER, ["vintage_id", "symbol", "source", "retrieved_at",
                                "from_date", "to_date", "payload", "payload_hash",
                                "metadata", "drift_of"]),
    # --- lock ---------------------------------------------------------------------
    "store_snapshots": (LEDGER, ["content_hash", "tbl", "row_key", "canonical_json"]),
    "lock_manifests": (LEDGER, ["manifest_id", "round_id", "segment_idx", "store_rows",
                                "vintage_ids", "ledger_cutoff", "library_history_version",
                                "config_hash", "harness_version", "round_budget_used",
                                "tide_budget_used", "tide_id"]),
    "locks": (LEDGER, ["round_id", "segment_idx", "lock_hash", "manifest_id", "objects_hash",
                       "clock"]),
    # --- construction and paper ---------------------------------------------------
    "constructed_baskets": (LEDGER, ["basket_id", "round_id", "segment_idx", "ack_id",
                                     "status", "reason", "shape", "z_star", "b_basket",
                                     "max_loss", "tide_id", "weights_hash", "lock_hash",
                                     "flags", "detail"]),
    "basket_weights": (LEDGER, ["basket_id", "instrument_id", "w_long", "w_short",
                                "max_loss_contribution"]),
    "scenarios": (LEDGER, ["basket_id", "scenario_id", "outcome_id", "in_thesis",
                           "tide_state", "payoffs", "payoff_worst", "upside_if_adopted"]),
    "basket_status": (LEDGER, ["basket_id", "status", "reason"]),
    "paper_positions": (LEDGER, ["paper_id", "basket_id", "instrument_id", "side", "qty",
                                 "entry_rule", "max_loss", "exit_rules"]),
    "paper_fills": (LEDGER, ["paper_id", "at", "price", "vintage_id", "cost"]),
    "paper_marks": (LEDGER, ["paper_id", "at", "price", "vintage_id", "trigger"]),
    "paper_exits": (LEDGER, ["paper_id", "basket_id", "at", "price", "reason", "pnl",
                             "split"]),
    "pianos": (LEDGER, ["piano_id", "round_id", "basket_id", "description", "outside",
                        "cost"]),
    # --- K7 ownership and instrument census ---------------------------------------
    "census_rows": (LEDGER, ["census_id", "holder_key", "holder_name", "instrument_symbol", "instrument_kind",
                             "relation", "concentration_pct", "concentrated", "basis", "source_document",
                             "knowable_from", "earliest_event_date", "status"]),
    # --- v17 (V0, V1): identity events, document links, statement links. New ledger tables that point
    # at existing rows by id; no existing ledger table gains a column (A18) --------------------------
    "entity_events": (LEDGER, ["event_id", "event_type", "entity_keys", "payload", "evidence_ids",
                               "knowable_from", "status", "reason", "by", "ref_event"]),
    "evidence_entities": (LEDGER, ["evidence_id", "entity_key", "content_hash"]),
    "statement_links": (LEDGER, ["statement_id", "evidence_entity", "role", "span", "span_verified",
                                 "published_at", "note"]),
    # --- v17 V2 slice: count-dilution buckets, a versioned post-hoc partition of edges (new tables only) -------------
    "bucket_versions": (LEDGER, ["version_id", "method", "embedder", "embedder_trained_through", "features_hash",
                                 "knowable_cutoff", "status", "note"]),
    "bucket_assignments": (LEDGER, ["version_id", "edge_key", "bucket", "label", "text_hash", "text_knowable_from"]),
    "bucket_fits": (LEDGER, ["version_id", "bucket", "status", "alpha", "alpha_raw", "se", "n_obs", "information",
                             "shrink_k", "min_obs", "fitted_on"]),
    # --- library ------------------------------------------------------------------
    "library_history": (LEDGER, ["rule_id", "weight", "weight_state", "trials_as_carried",
                                 "computed_from_resolutions", "valid_from", "tide_count"]),
    "store_changes": (LEDGER, ["tbl", "row_key", "content_hash", "action", "by"]),

    # ============================ mutable stores =================================
    "holders": (MUTABLE, ["name", "holder_class", "entity_kind", "listed", "ticker",
                          "exchange", "parent_id", "options_listed", "cik", "entity_ref"]),
    "nodes": (MUTABLE, ["node_kind", "node_type", "description", "neighbours"]),
    "node_types": (MUTABLE, ["description", "first_seen_round"]),
    "position_attributes": (MUTABLE, ["type", "unit", "allowed", "description"]),
    "bounds": (MUTABLE, ["subject", "quantity", "value", "unit", "source_document",
                         "knowable_from", "authored_by"]),
    "library_rules": (MUTABLE, ["rule_text", "forbids", "layer", "kind", "status",
                                "carries", "weight", "weight_state", "provenance"]),
    "obligation_templates": (MUTABLE, ["node_types", "roles", "conditions", "forces",
                                       "carrier_kinds", "window_rule", "forbids",
                                       "authored_from"]),
    "outcome_vocabs": (MUTABLE, ["notice_kind", "outcomes", "authored_from"]),
    "ack_nodes": (MUTABLE, ["round_id", "segment_idx", "ack_kind", "origin",
                            "derivation_id", "template_id", "notice_kind", "fact",
                            "source", "obligation", "due_at", "window_to", "window_basis",
                            "window_ratified", "holder_id", "bindings", "parent_ack_id",
                            "attention", "is_switch", "status", "fetch_list"]),
    "transforms": (MUTABLE, ["relation", "from_kind", "to_kind", "value", "basis"]),
    "stories": (MUTABLE, ["label", "path_nodes", "loading_kind", "proxy",
                          "construction_rule", "origin", "round_id"]),
    "instruments": (MUTABLE, ["holder_id", "ack_id", "yes_outcomes", "kind", "symbol",
                              "venue", "listed_from", "cap_class", "expiry", "strikes",
                              "multiplier", "cost_model_id", "quote_source", "underlying"]),
    "event_contract_meta": (MUTABLE, ["condition_id", "token_id", "side", "event_id", "neg_risk", "tick_size", "min_size",
                                      "fee_schedule", "slot_kind"]),
    "cost_models": (MUTABLE, ["kind", "spread_rule", "fee", "borrow", "slippage_rule",
                              "pricing_rule"]),
    "tides": (MUTABLE, ["label", "declared_by", "from_date", "to_date", "retro_declared",
                        "proxy"]),
    "carriers": (MUTABLE, ["kind", "node_types", "fetch_path", "description",
                           "read_in_full_rule"]),
    "procedural_models": (MUTABLE, ["process_type", "states", "transitions",
                                    "counted_through"]),
    # --- v17 mutable stores. holders, nodes and node_types stay as they are: v16 code paths and every old
    # lock manifest read them. ``entities`` is the one table of things; key_map ties the two together. -------
    "entities": (MUTABLE, ["canonical_name", "kind", "exists_from", "exists_from_knowable", "exists_to",
                           "exists_to_knowable", "declared_capabilities", "entity_refs", "aliases",
                           "state_attributes", "observable", "legacy", "document", "first_seen_round"]),
    "entity_kinds": (MUTABLE, ["parent", "description", "scale_attribute", "capabilities", "review", "seeded"]),
    "capabilities": (MUTABLE, ["meaning", "mode", "note"]),
    "key_map": (MUTABLE, ["entity_key", "source_table", "collision"]),
    "attribute_scope": (MUTABLE, ["kinds", "note"]),
}

LEDGER_TABLES = [t for t, (k, _) in TABLES.items() if k == LEDGER]
MUTABLE_TABLES = [t for t, (k, _) in TABLES.items() if k == MUTABLE]


class ChainBroken(RuntimeError):
    pass


class Refused(RuntimeError):
    """A tool refused an operation for a stated reason. Never swallowed."""


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canon(obj) -> str:
    """Canonical JSON: sorted keys, no whitespace, floats as repr."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode()
    return hashlib.sha256(s).hexdigest()


def _enc(v):
    if isinstance(v, (dict, list, tuple)):
        return canon(v)
    if isinstance(v, bool):
        return int(v)
    return v


def _dec(v):
    if isinstance(v, str) and v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


class DB:
    def __init__(self, path: str | os.PathLike | None = None, verify: bool = True):
        self.path = Path(path or os.environ.get("NOMAD16_DB") or DEFAULT_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create()
        if verify:
            bad = self.verify_chain()
            if bad:
                raise ChainBroken(f"hash chain broken at start-up: {bad}")

    # -- schema --------------------------------------------------------------
    def _create(self):
        c = self.conn
        for t, (kind, cols) in TABLES.items():
            if kind == LEDGER:
                coldefs = ", ".join(f'"{x}"' for x in cols)
                c.execute(f'CREATE TABLE IF NOT EXISTS "{t}" (id INTEGER PRIMARY KEY, {coldefs}, '
                          f'recorded_at TEXT NOT NULL, prev_row_hash TEXT NOT NULL, '
                          f'row_hash TEXT NOT NULL)')
                c.execute(f'CREATE TRIGGER IF NOT EXISTS "{t}_no_update" BEFORE UPDATE ON "{t}" '
                          f"BEGIN SELECT RAISE(ABORT, 'ledger table {t} is append-only'); END")
                c.execute(f'CREATE TRIGGER IF NOT EXISTS "{t}_no_delete" BEFORE DELETE ON "{t}" '
                          f"BEGIN SELECT RAISE(ABORT, 'ledger table {t} is append-only'); END")
            else:
                coldefs = ", ".join(f'"{x}"' for x in cols)
                c.execute(f'CREATE TABLE IF NOT EXISTS "{t}" (key TEXT PRIMARY KEY, {coldefs}, '
                          f'updated_at TEXT NOT NULL)')
        c.commit()

    # -- ledger ----------------------------------------------------------------
    def _head(self, t: str) -> str:
        r = self.conn.execute(f'SELECT row_hash FROM "{t}" ORDER BY id DESC LIMIT 1').fetchone()
        return r[0] if r else GENESIS

    def append(self, t: str, **fields) -> dict:
        kind, cols = TABLES[t]
        if kind != LEDGER:
            raise ValueError(f"{t} is not a ledger table")
        unknown = set(fields) - set(cols)
        if unknown:
            raise ValueError(f"{t}: unknown columns {sorted(unknown)}")
        # normalise through the storage encoding so the hash is what verify_chain will see
        row = {c: _dec(_enc(fields.get(c))) for c in cols}
        row["recorded_at"] = now_iso()
        prev = self._head(t)
        row_hash = sha(prev + canon({k: row[k] for k in sorted(row)}))
        vals = [_enc(row[c]) for c in cols] + [row["recorded_at"], prev, row_hash]
        q = ", ".join("?" * len(vals))
        names = ", ".join(f'"{c}"' for c in cols) + ", recorded_at, prev_row_hash, row_hash"
        cur = self.conn.execute(f'INSERT INTO "{t}" ({names}) VALUES ({q})', vals)
        self.conn.commit()
        row.update(id=cur.lastrowid, prev_row_hash=prev, row_hash=row_hash)
        return row

    def verify_chain(self) -> list[str]:
        broken = []
        for t in LEDGER_TABLES:
            _, cols = TABLES[t]
            prev = GENESIS
            for r in self.conn.execute(f'SELECT * FROM "{t}" ORDER BY id'):
                d = {c: _dec(r[c]) for c in cols}
                d["recorded_at"] = r["recorded_at"]
                if r["prev_row_hash"] != prev:
                    broken.append(f"{t}#{r['id']} prev mismatch")
                    break
                h = sha(prev + canon({k: d[k] for k in sorted(d)}))
                if h != r["row_hash"]:
                    broken.append(f"{t}#{r['id']} row hash mismatch")
                    break
                prev = h
        return broken

    def chain_heads(self) -> dict:
        return {t: self._head(t)[:12] for t in LEDGER_TABLES
                if self.conn.execute(f'SELECT 1 FROM "{t}" LIMIT 1').fetchone()}

    # -- mutable ---------------------------------------------------------------
    def upsert(self, t: str, key: str, by: str = "operator", **fields) -> dict:
        kind, cols = TABLES[t]
        if kind != MUTABLE:
            raise ValueError(f"{t} is not a mutable store")
        unknown = set(fields) - set(cols)
        if unknown:
            raise ValueError(f"{t}: unknown columns {sorted(unknown)}")
        existing = self.get(t, key)
        row = {c: (existing or {}).get(c) for c in cols}
        row.update({k: _dec(_enc(v)) for k, v in fields.items()})
        vals = [key] + [_enc(row[c]) for c in cols] + [now_iso()]
        names = "key, " + ", ".join(f'"{c}"' for c in cols) + ", updated_at"
        q = ", ".join("?" * len(vals))
        self.conn.execute(f'INSERT OR REPLACE INTO "{t}" ({names}) VALUES ({q})', vals)
        self.conn.commit()
        content = {"key": key, **{c: row[c] for c in cols}}
        # every mutable change is dated on the ledger (§14: "what they date goes on the ledger")
        self.append("store_changes", tbl=t, row_key=key, content_hash=sha(canon(content)),
                    action="update" if existing else "insert", by=by)
        return content

    def get(self, t: str, key: str) -> dict | None:
        r = self.conn.execute(f'SELECT * FROM "{t}" WHERE key=?', (key,)).fetchone()
        return self._row(t, r) if r else None

    # -- reads -------------------------------------------------------------------
    def _row(self, t, r) -> dict:
        kind, cols = TABLES[t]
        d = {c: _dec(r[c]) for c in cols}
        if kind == LEDGER:
            d.update(id=r["id"], recorded_at=r["recorded_at"], row_hash=r["row_hash"])
        else:
            d.update(key=r["key"], updated_at=r["updated_at"])
        return d

    def rows(self, t: str, where: str = "", params: tuple = (), order: str = "") -> list[dict]:
        q = f'SELECT * FROM "{t}"'
        if where:
            q += f" WHERE {where}"
        q += f" ORDER BY {order}" if order else (" ORDER BY id" if TABLES[t][0] == LEDGER else " ORDER BY key")
        return [self._row(t, r) for r in self.conn.execute(q, params)]

    def one(self, t: str, where: str, params: tuple = ()) -> dict | None:
        r = self.rows(t, where, params)
        return r[-1] if r else None

    def mutable_content(self, t: str, row: dict) -> dict:
        _, cols = TABLES[t]
        return {"key": row["key"], **{c: row[c] for c in cols}}

    def close(self):
        self.conn.close()
