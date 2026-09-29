"""v9 §D2: Wayback save-page-now scheduler. `snapshot(url)` submits a save request and records the resulting snapshot
url and timestamp as a node_facts row of kind `snapshot`. The target list (snapshot_targets) is seeded with every IR
events page and notices page in the names book plus every carrier whose live path is blocked. Run on demand now, daily
later: it is the cheapest possible ingest and it feeds both the scheduled-facts feed and the point-in-time fetcher."""
import re
import sqlite3
import urllib.request
from datetime import date

from .db import append, insert_mutable
from .errors import NotFound, ValidationError
from .util import now_iso

UA = "nomad-harness/0.1 (save-page-now; contact bato2912@gmail.com)"
KINDS = ("ir_events", "notices", "carrier", "other")
_TS = re.compile(r"/web/(\d{14})")


def _save(url: str, timeout: int = 90) -> dict:
    """GET https://web.archive.org/save/<url>. Returns the snapshot url and timestamp from Content-Location or the final url."""
    req = urllib.request.Request(f"https://web.archive.org/save/{url}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        loc = resp.headers.get("Content-Location") or resp.headers.get("Location") or resp.geturl()
        status = resp.status
    m = _TS.search(loc or "")
    if not m:
        return {"ok": False, "status": status, "reason": f"no snapshot timestamp in response location {loc!r}"}
    ts = m.group(1)
    path = loc if loc.startswith("http") else f"https://web.archive.org{loc}"
    return {"ok": True, "status": status, "snapshot_url": path, "timestamp": ts,
            "snapshot_date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"}


def snapshot(conn: sqlite3.Connection, url: str, node: str | None = None, holder_id: str | None = None,
             note: str | None = None, save=_save) -> dict:
    if not url.strip().startswith(("http://", "https://")):
        raise ValidationError("url must be absolute (http:// or https://)")
    url = url.strip()
    t = conn.execute("SELECT * FROM snapshot_targets WHERE url = ?", (url,)).fetchone()
    node = node or (t["node"] if t else f"snapshot:{urllib.request.urlparse(url).netloc}")
    holder_id = holder_id or (t["holder_id"] if t else None)
    try:
        r = save(url)
        status = "saved" if r["ok"] else "failed"
    except Exception as e:
        r, status = {"ok": False, "reason": f"{type(e).__name__}: {e}"[:300]}, "error"
    fact_id = None
    if r.get("ok"):
        row = append(conn, "node_facts", {
            "node": node, "holder_id": holder_id, "fact_type": "snapshot",
            "text": f"Wayback snapshot {r['timestamp']} of {url}" + (f" ({note})" if note else ""),
            "url": r["snapshot_url"], "source": "web.archive.org save-page-now", "source_time": r["snapshot_date"],
            "knowable_from": r["snapshot_date"]})
        fact_id = row["id"]
    if t:
        conn.execute("UPDATE snapshot_targets SET last_snapshot = COALESCE(?, last_snapshot), last_status = ? WHERE id = ?",
                     (r.get("snapshot_date"), status, t["id"]))
    return {"url": url, "status": status, "snapshot_url": r.get("snapshot_url"), "snapshot_date": r.get("snapshot_date"),
            "fact_id": fact_id, "reason": r.get("reason"), "node": node}


def target_add(conn: sqlite3.Connection, url: str, kind: str, node: str, holder_id: str | None = None,
               carrier_key: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValidationError(f"kind must be one of {KINDS}")
    if not url.strip().startswith(("http://", "https://")):
        raise ValidationError("url must be absolute")
    if holder_id:
        from .names import resolve_holder
        holder_id = resolve_holder(conn, holder_id)["id"]
    ex = conn.execute("SELECT id FROM snapshot_targets WHERE url = ?", (url.strip(),)).fetchone()
    if ex:
        conn.execute("UPDATE snapshot_targets SET kind = ?, node = ?, holder_id = COALESCE(?, holder_id), carrier_key = COALESCE(?, carrier_key), active = 1 WHERE id = ?",
                     (kind, node, holder_id, carrier_key, ex["id"]))
        return {"target_id": ex["id"], "url": url.strip(), "created": False}
    row = insert_mutable(conn, "snapshot_targets", {"url": url.strip(), "kind": kind, "node": node, "holder_id": holder_id,
                                                    "carrier_key": carrier_key, "active": 1})
    return {"target_id": row["id"], "url": url.strip(), "created": True}


def seed_targets(conn: sqlite3.Connection) -> dict:
    """Every holder with an IR events page, every carrier with a url whose live path is blocked."""
    from .carriers import best_path
    from .util import loads
    added = []
    for h in conn.execute("SELECT id, key, canonical_name, ir_url FROM holders WHERE ir_url IS NOT NULL AND ir_url != ''"):
        node = f"{h['key'] or h['canonical_name']}_calendar"
        r = target_add(conn, h["ir_url"], "ir_events", node, holder_id=h["id"])
        if r["created"]:
            added.append(h["ir_url"])
    for c in conn.execute("SELECT key, name, url, fetch_paths FROM carriers WHERE url IS NOT NULL AND url != ''"):
        paths = loads(c["fetch_paths"]) if c["fetch_paths"] else {}
        if (paths.get("live") or {}).get("status") == "blocked":
            r = target_add(conn, c["url"], "carrier", f"carrier:{c['key'] or c['name']}", carrier_key=c["key"])
            if r["created"]:
                added.append(c["url"])
    return {"added": added, "targets": conn.execute("SELECT COUNT(*) FROM snapshot_targets WHERE active = 1").fetchone()[0]}


def list_targets(conn: sqlite3.Connection, active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM snapshot_targets" + (" WHERE active = 1" if active_only else "") + " ORDER BY kind, rowid"
    return [dict(r) for r in conn.execute(sql)]


def run(conn: sqlite3.Connection, save=_save, limit: int | None = None, kind: str | None = None,
        pause_seconds: float = 15.0, retry_on_429: int = 2, skip_saved_since: str | None = None) -> dict:
    """save-page-now throttles bursts (429, then refused connections): pace requests and back off on 429.
    skip_saved_since=YYYY-MM-DD skips targets already snapshotted on or after that date (a daily run stays cheap)."""
    import time
    targets = [t for t in list_targets(conn) if not kind or t["kind"] == kind]
    if skip_saved_since:
        targets = [t for t in targets if not (t["last_snapshot"] and t["last_snapshot"] >= skip_saved_since)]
    if limit:
        targets = targets[: int(limit)]
    report = {"run_at": now_iso(), "targets": len(targets), "saved": 0, "results": []}
    for i, t in enumerate(targets):
        if i and pause_seconds:
            time.sleep(pause_seconds)
        attempt = 0
        while True:
            r = snapshot(conn, t["url"], node=t["node"], holder_id=t["holder_id"], save=save)
            if r["status"] == "saved" or "429" not in (r.get("reason") or "") or attempt >= retry_on_429:
                break
            attempt += 1
            if pause_seconds:
                time.sleep(pause_seconds * 4 * attempt)
        report["results"].append({"url": t["url"], "kind": t["kind"], "status": r["status"], "snapshot_date": r["snapshot_date"],
                                  "reason": r["reason"], "attempts": attempt + 1})
        report["saved"] += r["status"] == "saved"
    return report
