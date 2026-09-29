"""§B0: point-in-time fetcher. Wayback's availability API and Wikipedia's revision API, both free, give the operator
what a page said as of a date. Legal pre-lock because the snapshot predates the event; every fetch is logged with the
operator's stated reason and the snapshot date becomes knowable_from on anything derived from it."""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, timedelta

from .db import append
from .errors import StateError, ValidationError

MAX_CHARS = 6000
UA = "nomad-harness/0.1 (+point-in-time fetch)"


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;|&#160;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"&#39;|&rsquo;|&lsquo;", "'", html)
    return re.sub(r"\s+", " ", html).strip()


def _live_round(conn: sqlite3.Connection) -> dict | None:
    r = conn.execute(
        "SELECT s.round_id, s.state, e.event_date FROM round_state s JOIN rounds r ON r.id = s.round_id "
        "JOIN events e ON e.id = r.event_id WHERE s.state IN ('created','locked','open') ORDER BY s.state_changed_at DESC LIMIT 1"
    ).fetchone()
    return dict(r) if r else None


def guard_as_of(conn: sqlite3.Connection, as_of: str) -> dict | None:
    """Pre-lock the snapshot must predate the live round's event; once the round is open the ordinary retrieval applies."""
    try:
        d = date.fromisoformat(as_of)
    except ValueError:
        raise ValidationError("as_of must be YYYY-MM-DD")
    if d > date.today():
        raise ValidationError("as_of is in the future")
    live = _live_round(conn)
    if live and live["state"] in ("created", "locked") and d >= date.fromisoformat(live["event_date"]):
        raise StateError(f"round {live['round_id']} is {live['state']} with event date {live['event_date']}: a point-in-time fetch "
                         f"before lock must be dated strictly before the event (as_of {as_of}); open retrieval first for anything later")
    return live


def wayback(url: str, as_of: str, fetch=_get) -> dict:
    ts = as_of.replace("-", "") + "235959"
    q = urllib.parse.urlencode({"url": url, "timestamp": ts})
    data = json.loads(fetch(f"https://archive.org/wayback/available?{q}").decode("utf-8", "replace"))
    snap = (data.get("archived_snapshots") or {}).get("closest")
    if not snap or not snap.get("available"):
        return {"found": False, "reason": "no snapshot in the Wayback Machine for that url"}
    snap_ts = snap["timestamp"]
    snap_date = f"{snap_ts[:4]}-{snap_ts[4:6]}-{snap_ts[6:8]}"
    if snap_date > as_of:
        return {"found": False, "reason": f"closest snapshot is {snap_date}, after as_of {as_of}; nothing earlier is archived"}
    body = fetch(snap["url"]).decode("utf-8", "replace")
    return {"found": True, "snapshot_url": snap["url"], "snapshot_date": snap_date, "text": _strip_html(body)[:MAX_CHARS]}


def wikipedia(title: str, as_of: str, fetch=_get, lang: str = "en") -> dict:
    """The last revision of the article on or before as_of, as plain text extract."""
    end = (date.fromisoformat(as_of) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "titles": title, "rvlimit": 1, "rvdir": "older",
                                "rvstart": end, "rvprop": "ids|timestamp", "format": "json", "redirects": 1})
    data = json.loads(fetch(f"https://{lang}.wikipedia.org/w/api.php?{q}").decode("utf-8", "replace"))
    pages = (data.get("query") or {}).get("pages") or {}
    page = next(iter(pages.values()), None)
    if not page or "revisions" not in page:
        return {"found": False, "reason": f"no revision of {title!r} on or before {as_of}"}
    rev = page["revisions"][0]
    q2 = urllib.parse.urlencode({"action": "parse", "oldid": rev["revid"], "prop": "text", "format": "json", "disabletoc": 1})
    parsed = json.loads(fetch(f"https://{lang}.wikipedia.org/w/api.php?{q2}").decode("utf-8", "replace"))
    html = ((parsed.get("parse") or {}).get("text") or {}).get("*", "")
    return {"found": True, "snapshot_url": f"https://{lang}.wikipedia.org/w/index.php?title={urllib.parse.quote(page['title'])}&oldid={rev['revid']}",
            "snapshot_date": rev["timestamp"][:10], "revid": rev["revid"], "title": page["title"], "text": _strip_html(html)[:MAX_CHARS]}


def _live_blocked_in_registry(conn: sqlite3.Connection, url: str) -> dict | None:
    """A carrier whose url shares this host and whose live path is recorded blocked/timeout."""
    from .carriers import fetch_paths
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host:
        return None
    for r in conn.execute("SELECT * FROM carriers WHERE url IS NOT NULL"):
        if urllib.parse.urlparse(r["url"]).netloc.lower() == host:
            st = (fetch_paths(dict(r)).get("live") or {}).get("status")
            if st in ("blocked", "timeout"):
                return {"carrier": r["name"], "key": r["key"], "live": st}
    return None


def auto(conn: sqlite3.Connection, url: str, as_of: str, fetch=_get, live_allowed: bool = True) -> dict:
    """D3: live first when allowed and the registry does not mark the host blocked; else the nearest Wayback snapshot
    on or before as_of. Reports which path served."""
    reg = _live_blocked_in_registry(conn, url)
    tried = []
    if live_allowed and not reg:
        try:
            body = fetch(url).decode("utf-8", "replace")
            return {"found": True, "path_served": "live", "snapshot_url": url, "snapshot_date": as_of,
                    "text": _strip_html(body)[:MAX_CHARS], "tried": ["live"]}
        except Exception as e:
            tried.append(f"live: {type(e).__name__}: {e}"[:160])
    elif reg:
        tried.append(f"live skipped: registry marks {reg['carrier']} live {reg['live']}")
    else:
        tried.append("live refused: round not open (time wall)")
    r = wayback(url, as_of, fetch)
    r["path_served"] = "wayback" if r.get("found") else None
    r["tried"] = tried + ["wayback"]
    return r


def pit_fetch(conn: sqlite3.Connection, source: str, target: str, as_of: str, reason: str, fetch=_get) -> dict:
    """source: wayback (target = url) | wikipedia (target = article title) | auto (target = url: live when the round is
    open and the registry does not mark the host blocked, else Wayback on or before as_of; reports path_served).
    Logged to pit_fetches whatever the result."""
    if source not in ("wayback", "wikipedia", "auto", "live"):
        raise ValidationError("source must be wayback, wikipedia or auto")
    if not target.strip() or not reason.strip():
        raise ValidationError("target and reason are required: say what you are looking up and why (it is logged)")
    live = guard_as_of(conn, as_of)
    live_allowed = not (live and live["state"] in ("created", "locked"))
    try:
        if source == "wayback":
            r = wayback(target, as_of, fetch)
        elif source == "wikipedia":
            r = wikipedia(target, as_of, fetch)
        else:
            r = auto(conn, target, as_of, fetch, live_allowed)
        status = "found" if r["found"] else "not_found"
    except Exception as e:  # network or parse: logged, not raised
        r, status = {"found": False, "reason": f"{type(e).__name__}: {e}"[:300]}, "error"
    path_served = r.get("path_served") or ({"wayback": "wayback", "wikipedia": "pit_api"}.get(source) if r.get("found") else None)
    row = append(conn, "pit_fetches", {
        "round_id": live["round_id"] if live else None, "source": source, "target": target, "as_of": as_of, "reason": reason.strip(),
        "status": status, "snapshot_url": r.get("snapshot_url"), "snapshot_date": r.get("snapshot_date"),
        "chars": len(r.get("text") or ""), "path_served": path_served,
    })
    out = {"fetch_id": row["id"], "source": source, "target": target, "as_of": as_of, "status": status, "path_served": path_served, **r}
    if r.get("found"):
        out["knowable_from"] = r["snapshot_date"]
        out["note"] = "anything derived from this goes into positions/node_facts with knowable_from = snapshot_date"
    return out


def list_fetches(conn: sqlite3.Connection, round_id: str | None = None) -> list[dict]:
    if round_id:
        return [dict(r) for r in conn.execute("SELECT * FROM pit_fetches WHERE round_id = ? ORDER BY rowid", (round_id,))]
    return [dict(r) for r in conn.execute("SELECT * FROM pit_fetches ORDER BY rowid DESC LIMIT 100")]
