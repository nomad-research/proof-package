"""A read view over the stores, bounded for one computation.

Every emergent object (derived ACKs, reachable sets, loadings, S⊥, baskets) is
computed from a ``View``. A live view reads the mutable stores as they stand; a
replay view reads them from a lock manifest's content-addressed snapshots (§14:
"Replay reads the manifest, not the live stores"). Ledger rows are read up to a
``ledger_cutoff`` (the lock's recorded time), so rows appended after a lock are
invisible to its replay.
"""
from __future__ import annotations

import json

from .db import DB, MUTABLE_TABLES, sha, canon


class View:
    def __init__(self, db: DB, manifest: dict | None = None, ledger_cutoff: str | None = None):
        self.db = db
        self.manifest = manifest
        self.ledger_cutoff = ledger_cutoff or (manifest or {}).get("ledger_cutoff")
        self._snap: dict[str, list[dict]] = {}
        self.read_tables: set[str] = set()
        if manifest is not None:
            for t, rows in (manifest.get("store_rows") or {}).items():
                out = []
                for row_key, h in rows.items():
                    s = db.one("store_snapshots", "content_hash=?", (h,))
                    if s is None:
                        raise RuntimeError(f"manifest names snapshot {h} which is missing")
                    cj = s["canonical_json"]
                    out.append(cj if isinstance(cj, dict) else json.loads(cj))
                self._snap[t] = sorted(out, key=lambda r: r["key"])

    # mutable stores ---------------------------------------------------------
    def mut(self, table: str) -> list[dict]:
        assert table in MUTABLE_TABLES, table
        self.read_tables.add(table)
        if self.manifest is not None:
            return [dict(r) for r in self._snap.get(table, [])]
        return [self.db.mutable_content(table, r) for r in self.db.rows(table)]

    def mget(self, table: str, key: str) -> dict | None:
        for r in self.mut(table):
            if r["key"] == key:
                return r
        return None

    # ledger ------------------------------------------------------------------
    def led(self, table: str, where: str = "", params: tuple = ()) -> list[dict]:
        if self.ledger_cutoff:
            w = f"({where}) AND recorded_at <= ?" if where else "recorded_at <= ?"
            return self.db.rows(table, w, tuple(params) + (self.ledger_cutoff,))
        return self.db.rows(table, where, params)

    def snapshot_rows(self) -> dict[str, dict[str, str]]:
        """Content hashes of every mutable-store row this view can see (for the manifest)."""
        out: dict[str, dict[str, str]] = {}
        for t in MUTABLE_TABLES:
            rows = self.mut(t)
            out[t] = {r["key"]: sha(canon(r)) for r in rows}
        return out
