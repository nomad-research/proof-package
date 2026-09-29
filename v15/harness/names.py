"""Names book (§4.10, §4.11): holders, aliases, exact/normalised resolution, orphan queue."""
import sqlite3

from .db import append, get_row, insert_mutable, transaction
from .errors import NotFound, ValidationError
from .models import AliasIn
from .util import normalise_name

KINDS = ("company", "plant", "facility", "authority", "fund", "other")


def _alias_owner(conn: sqlite3.Connection, norm: str) -> list[str]:
    return [r["holder_id"] for r in conn.execute(
        "SELECT DISTINCT holder_id FROM aliases WHERE alias_norm = ?", (norm,))]


def _add_alias(conn: sqlite3.Connection, holder_id: str, a: AliasIn) -> bool:
    norm = normalise_name(a.alias)
    if not norm:
        raise ValidationError(f"alias {a.alias!r} normalises to nothing")
    owners = _alias_owner(conn, norm)
    if holder_id in owners:
        return False
    if owners:
        raise ValidationError(
            f"alias {a.alias!r} already resolves to holder(s) {owners}; aliases are append-only, so pick a different "
            "canonical name or record this as a subsidiary/plant of that holder")
    append(conn, "aliases", {"holder_id": holder_id, "alias": a.alias, "alias_norm": norm,
                             "alias_kind": a.alias_kind, "source": a.source, "knowable_from": a.knowable_from})
    return True


def resolve_holder(conn: sqlite3.Connection, id_or_key: str) -> dict:
    r = conn.execute("SELECT * FROM holders WHERE id = ? OR key = ?", (id_or_key, id_or_key)).fetchone()
    if not r:
        raise NotFound(f"no holder with id or key {id_or_key!r}; use nomad_resolve or nomad_holder_upsert")
    return dict(r)


def holder_upsert(conn: sqlite3.Connection, canonical_name: str, kind: str, listed: bool = False,
                  parent_id: str | None = None, ticker: str | None = None, exchange: str | None = None,
                  aliases: list | None = None, source: str = "operator", first_seen_round: str | None = None,
                  key: str | None = None, ir_url: str | None = None, cik: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValidationError(f"kind must be one of {KINDS}")
    norm = normalise_name(canonical_name)
    if not norm:
        raise ValidationError("canonical_name normalises to nothing")
    if parent_id:
        parent_id = resolve_holder(conn, parent_id)["id"]
    parsed = [a if isinstance(a, AliasIn) else (AliasIn(alias=a) if isinstance(a, str) else AliasIn.model_validate(a))
              for a in (aliases or [])]
    with transaction(conn):
        existing = conn.execute("SELECT * FROM holders WHERE normalised_name = ?", (norm,)).fetchone()
        if existing:
            hid = existing["id"]
            if existing["kind"] != kind:
                raise ValidationError(
                    f"holder {canonical_name!r} exists with kind {existing['kind']!r}; kinds do not change (a plant is not a company)")
            if key and existing["key"] and existing["key"] != key:
                raise ValidationError(f"holder {canonical_name!r} already has key {existing['key']!r}")
            conn.execute("UPDATE holders SET listed = ?, ticker = COALESCE(?, ticker), exchange = COALESCE(?, exchange), "
                         "parent_id = COALESCE(?, parent_id), first_seen_round = COALESCE(first_seen_round, ?), "
                         "key = COALESCE(key, ?), ir_url = COALESCE(?, ir_url), cik = COALESCE(?, cik) WHERE id = ?",
                         (int(bool(listed)), ticker, exchange, parent_id, first_seen_round, key, ir_url, cik, hid))
            created = False
        else:
            owners = _alias_owner(conn, norm)
            if owners:
                raise ValidationError(
                    f"{canonical_name!r} is already an alias of holder(s) {owners}; use that holder id or choose a different canonical name")
            if key and conn.execute("SELECT 1 FROM holders WHERE key = ?", (key,)).fetchone():
                raise ValidationError(f"holder key {key!r} already exists")
            row = insert_mutable(conn, "holders", {
                "canonical_name": canonical_name.strip(), "normalised_name": norm, "kind": kind, "parent_id": parent_id,
                "listed": listed, "ticker": ticker, "exchange": exchange, "first_seen_round": first_seen_round,
                "key": key or None, "ir_url": ir_url, "cik": cik,
            })
            hid = row["id"]
            created = True
        added = 0
        added += _add_alias(conn, hid, AliasIn(alias=canonical_name.strip(), alias_kind="name", source=source))
        if ticker:
            added += _add_alias(conn, hid, AliasIn(alias=ticker, alias_kind="ticker", source=source))
        for a in parsed:
            added += _add_alias(conn, hid, a)
    return {"holder_id": hid, "created": created, "aliases_added": added, "normalised_name": norm}


def get_holder(conn: sqlite3.Connection, holder_id: str) -> dict:
    h = resolve_holder(conn, holder_id)
    holder_id = h["id"]
    h["parent"] = None
    if h["parent_id"]:
        p = get_row(conn, "holders", h["parent_id"], "parent holder")
        h["parent"] = {"holder_id": p["id"], "canonical_name": p["canonical_name"], "kind": p["kind"], "listed": p["listed"]}
    h["aliases"] = [dict(r) for r in conn.execute(
        "SELECT alias, alias_kind, source, knowable_from FROM aliases WHERE holder_id = ? ORDER BY rowid", (holder_id,))]
    return h


def resolve(conn: sqlite3.Connection, raw_string: str, context: str | None = None, round_id: str | None = None) -> dict:
    norm = normalise_name(raw_string)
    owners = _alias_owner(conn, norm) if norm else []
    if len(owners) == 1:
        h = get_holder(conn, owners[0])
        via = conn.execute("SELECT alias, alias_kind FROM aliases WHERE holder_id = ? AND alias_norm = ? LIMIT 1",
                           (owners[0], norm)).fetchone()
        return {"resolved": True, "status": "resolved", "raw_string": raw_string, "normalised": norm,
                "holder_id": h["id"], "holder": h, "via_alias": dict(via) if via else None}
    ctx = context
    if len(owners) > 1:
        ctx = f"ambiguous: matches holders {owners}. " + (context or "")
    row = append(conn, "orphans", {"raw_string": raw_string, "raw_norm": norm, "context": ctx, "round_id": round_id})
    return {"resolved": False, "status": "unresolved", "raw_string": raw_string, "normalised": norm,
            "orphan_id": row["id"], "ambiguous_holder_ids": owners or None,
            "next_step": "link it with nomad_holder_upsert (add the raw string as an alias of the right holder, or create the holder)"}


def orphans(conn: sqlite3.Connection, limit: int = 50) -> dict:
    rows = [dict(r) for r in conn.execute("SELECT * FROM orphans ORDER BY rowid")]
    still = []
    for r in rows:
        if len(_alias_owner(conn, r["raw_norm"])) == 1:
            continue  # cleared since: now resolves
        still.append({k: r[k] for k in ("id", "raw_string", "raw_norm", "context", "round_id", "recorded_at")})
    return {"total_recorded": len(rows), "unresolved": len(still), "orphans": still[: int(limit)]}
