"""Point-in-time document corpus (spec section 5.3 and 1.4).

Three timestamps per record:

    valid_from    -- when the constraint began binding
    known_from    -- when it became publicly discoverable
    retrieved_at  -- when this system read it

Every query is answerable as of an arbitrary date and returns only records with
known_from <= as_of. That is the mechanism that stops a mapping run reading
post-dated text.

The gap `recognised_from - known_from` is itself a research object -- it is the
lag between a document being publicly available and anyone connecting it -- so it
is stored as a first-class field rather than derived on the fly.

Backed by SQLite so the corpus is a single committable file and queries stay
honest even when the corpus outgrows memory.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,
    source_url      TEXT,
    title           TEXT,
    body            TEXT NOT NULL,
    body_sha256     TEXT NOT NULL,
    valid_from      TEXT,
    known_from      TEXT NOT NULL,
    retrieved_at    TEXT NOT NULL,
    recognised_from TEXT,
    doc_type        TEXT,
    issuer          TEXT,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_known_from ON documents(known_from);
CREATE INDEX IF NOT EXISTS idx_valid_from ON documents(valid_from);
CREATE INDEX IF NOT EXISTS idx_issuer ON documents(issuer);

CREATE TABLE IF NOT EXISTS clauses (
    clause_id     TEXT PRIMARY KEY,
    doc_id        TEXT NOT NULL REFERENCES documents(doc_id),
    quote         TEXT NOT NULL,
    char_start    INTEGER,
    char_end      INTEGER,
    verified      INTEGER NOT NULL DEFAULT 0,
    verifiers     TEXT NOT NULL DEFAULT '[]',
    note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_clause_doc ON clauses(doc_id);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
    USING fts5(title, body, content='documents', content_rowid='rowid');
"""


def _iso(x: str | date | datetime | None) -> str | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        if x.tzinfo is None:
            x = x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc).isoformat()
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day, tzinfo=timezone.utc).isoformat()
    # assume already ISO-ish; normalise a bare date
    s = str(x)
    if len(s) == 10:
        return s + "T00:00:00+00:00"
    return s


@dataclass
class Document:
    doc_id: str
    body: str
    known_from: str
    retrieved_at: str
    source_url: str | None = None
    title: str | None = None
    valid_from: str | None = None
    recognised_from: str | None = None
    doc_type: str | None = None
    issuer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def recognition_lag_days(self) -> float | None:
        """recognised_from - known_from, in days. None until recognition is recorded."""
        if not self.recognised_from or not self.known_from:
            return None
        a = datetime.fromisoformat(self.known_from)
        b = datetime.fromisoformat(self.recognised_from)
        return (b - a).total_seconds() / 86400.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recognition_lag_days"] = self.recognition_lag_days
        return d


@dataclass
class Clause:
    clause_id: str
    doc_id: str
    quote: str
    char_start: int | None = None
    char_end: int | None = None
    verified: bool = False
    verifiers: list[str] = field(default_factory=list)
    note: str | None = None


class PITCorpus:
    """Point-in-time document store. All reads are as-of-date filtered."""

    def __init__(self, path: str | Path = "data/pit_corpus.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ---------------- writing ----------------

    def add(
        self,
        body: str,
        known_from: str | date | datetime,
        *,
        doc_id: str | None = None,
        retrieved_at: str | date | datetime | None = None,
        valid_from: str | date | datetime | None = None,
        source_url: str | None = None,
        title: str | None = None,
        doc_type: str | None = None,
        issuer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        doc_id = doc_id or sha[:16]
        retrieved_at = _iso(retrieved_at or datetime.now(timezone.utc))

        self.conn.execute(
            """INSERT OR REPLACE INTO documents
               (doc_id, source_url, title, body, body_sha256, valid_from, known_from,
                retrieved_at, recognised_from, doc_type, issuer, metadata_json)
               VALUES (?,?,?,?,?,?,?,?,
                       (SELECT recognised_from FROM documents WHERE doc_id = ?),
                       ?,?,?)""",
            (doc_id, source_url, title, body, sha, _iso(valid_from), _iso(known_from),
             retrieved_at, doc_id, doc_type, issuer, json.dumps(metadata or {})),
        )
        row = self.conn.execute("SELECT rowid FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        self.conn.execute("INSERT OR REPLACE INTO documents_fts(rowid, title, body) VALUES (?,?,?)",
                          (row["rowid"], title or "", body))
        self.conn.commit()
        return doc_id

    def mark_recognised(self, doc_id: str, recognised_from: str | date | datetime) -> None:
        """Record when this system (or an analyst) actually connected the document.

        known_from is when it was discoverable; this is when it was discovered. The
        gap is the quantity of interest.
        """
        self.conn.execute("UPDATE documents SET recognised_from = ? WHERE doc_id = ?",
                          (_iso(recognised_from), doc_id))
        self.conn.commit()

    def add_clause(
        self,
        doc_id: str,
        quote: str,
        *,
        clause_id: str | None = None,
        verified: bool = False,
        verifiers: Sequence[str] = (),
        note: str | None = None,
    ) -> str:
        """Attach a located clause to a document.

        The clause must appear verbatim in the stored body -- an assertion that
        cannot be located in the retrieved text is exactly the failure mode
        section 4.4 is guarding against, so it raises rather than storing.
        """
        row = self.conn.execute("SELECT body FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if row is None:
            raise KeyError(f"no such document: {doc_id}")
        start = row["body"].find(quote)
        if start < 0:
            raise ValueError(
                f"clause not found verbatim in document {doc_id}; "
                "unlocatable clauses must be quarantined, not stored"
            )
        clause_id = clause_id or hashlib.sha256((doc_id + quote).encode()).hexdigest()[:16]
        self.conn.execute(
            """INSERT OR REPLACE INTO clauses
               (clause_id, doc_id, quote, char_start, char_end, verified, verifiers, note)
               VALUES (?,?,?,?,?,?,?,?)""",
            (clause_id, doc_id, quote, start, start + len(quote),
             int(verified), json.dumps(list(verifiers)), note),
        )
        self.conn.commit()
        return clause_id

    # ---------------- reading ----------------

    def as_of(
        self,
        as_of: str | date | datetime,
        *,
        issuer: str | None = None,
        doc_type: str | None = None,
        binding_only: bool = False,
    ) -> list[Document]:
        """Every document publicly discoverable at `as_of`.

        binding_only additionally requires valid_from <= as_of, i.e. the constraint
        was already in force and not merely announced.
        """
        ts = _iso(as_of)
        q = "SELECT * FROM documents WHERE known_from <= ?"
        args: list[Any] = [ts]
        if binding_only:
            q += " AND valid_from IS NOT NULL AND valid_from <= ?"
            args.append(ts)
        if issuer:
            q += " AND issuer = ?"
            args.append(issuer)
        if doc_type:
            q += " AND doc_type = ?"
            args.append(doc_type)
        q += " ORDER BY known_from"
        return [self._row_to_doc(r) for r in self.conn.execute(q, args)]

    def search(self, query: str, as_of: str | date | datetime, limit: int = 50) -> list[Document]:
        """Full-text search restricted to documents discoverable at `as_of`."""
        ts = _iso(as_of)
        rows = self.conn.execute(
            """SELECT d.* FROM documents_fts f
               JOIN documents d ON d.rowid = f.rowid
               WHERE documents_fts MATCH ? AND d.known_from <= ?
               ORDER BY rank LIMIT ?""",
            (query, ts, limit),
        )
        return [self._row_to_doc(r) for r in rows]

    def get(self, doc_id: str) -> Document | None:
        r = self.conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        return self._row_to_doc(r) if r else None

    def clauses(self, doc_id: str | None = None, verified_only: bool = False) -> list[Clause]:
        q = "SELECT * FROM clauses WHERE 1=1"
        args: list[Any] = []
        if doc_id:
            q += " AND doc_id = ?"
            args.append(doc_id)
        if verified_only:
            q += " AND verified = 1"
        return [
            Clause(
                clause_id=r["clause_id"], doc_id=r["doc_id"], quote=r["quote"],
                char_start=r["char_start"], char_end=r["char_end"],
                verified=bool(r["verified"]), verifiers=json.loads(r["verifiers"]),
                note=r["note"],
            )
            for r in self.conn.execute(q, args)
        ]

    def recognition_lags(self) -> list[dict[str, Any]]:
        """The known_from -> recognised_from gap for every document where both exist."""
        out = []
        for r in self.conn.execute(
            "SELECT doc_id, title, known_from, recognised_from FROM documents "
            "WHERE recognised_from IS NOT NULL"
        ):
            a = datetime.fromisoformat(r["known_from"])
            b = datetime.fromisoformat(r["recognised_from"])
            out.append({
                "doc_id": r["doc_id"], "title": r["title"],
                "known_from": r["known_from"], "recognised_from": r["recognised_from"],
                "lag_days": (b - a).total_seconds() / 86400.0,
            })
        return out

    def assert_no_lookahead(self, as_of: str | date | datetime, docs: Iterable[Document]) -> None:
        """Hard check that a set of documents contains nothing post-dating `as_of`."""
        ts = _iso(as_of)
        bad = [d.doc_id for d in docs if d.known_from > ts]
        if bad:
            raise ValueError(f"look-ahead violation at {ts}: {bad}")

    def stats(self) -> dict[str, Any]:
        c = self.conn.execute
        return {
            "documents": c("SELECT COUNT(*) n FROM documents").fetchone()["n"],
            "clauses": c("SELECT COUNT(*) n FROM clauses").fetchone()["n"],
            "verified_clauses": c("SELECT COUNT(*) n FROM clauses WHERE verified=1").fetchone()["n"],
            "recognised": c("SELECT COUNT(*) n FROM documents WHERE recognised_from IS NOT NULL").fetchone()["n"],
            "path": str(self.path),
        }

    @staticmethod
    def _row_to_doc(r: sqlite3.Row) -> Document:
        return Document(
            doc_id=r["doc_id"], body=r["body"], known_from=r["known_from"],
            retrieved_at=r["retrieved_at"], source_url=r["source_url"], title=r["title"],
            valid_from=r["valid_from"], recognised_from=r["recognised_from"],
            doc_type=r["doc_type"], issuer=r["issuer"],
            metadata=json.loads(r["metadata_json"]),
        )

    def close(self) -> None:
        self.conn.close()
