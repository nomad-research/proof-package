"""v12 §D, §E, §F: making edge expressible.

**§D implied at lock.** Edge is our claim minus the implied claim, and only the first term had ever been measured.
Reading implied state at lock is measurement, exactly like a narrative row; it may not propose a leg.

**§E participant-class divergence.** The premise says no single participant's book is organised around all the facts.
Per leg that is checkable without price proposing anything: which class demonstrably holds the fact, which class marks
the security, and whether a routine channel connects them.

**§F institutional base rates.** Most occurrence calls were never market claims — will a producer declare force
majeure, will a regulator order inspections, will both parties respond in five days. Those are frequencies."""
import re
import sqlite3
from collections import deque
from datetime import date

from . import config
from .db import append, get_row, insert_mutable
from .errors import NotFound, StateError, ValidationError

# §F: an occurrence call about an institution's behaviour is a frequency claim, not a market claim.
INSTITUTIONAL = re.compile(
    r"\b(regulator\w*|commission|court|agency|authority|ministry|inspector\w*|prosecut\w*|administrator|receiver|"
    r"files?|filing|declares?|declaration|force majeure|order|orders|ordered|ruling|rules|sanction\w*|"
    r"report(s|ed|ing)?|announce\w*|confirm\w*|statement|notice|licen[cs]e|permit|investigat\w*|hearing|deadline)\b", re.I)


# ---- §E1/E5: classes and distance ---------------------------------------------------------------------------------

def class_distance(a: str, b: str) -> int:
    """Shortest path on the pre-registered adjacency, capped at 3. Same class 0, a routine channel apart 1."""
    for c in (a, b):
        if c not in config.PARTICIPANT_CLASSES:
            raise ValidationError(f"participant class must be one of {config.PARTICIPANT_CLASSES}; got {c!r}")
    if a == b:
        return 0
    seen, q = {a}, deque([(a, 0)])
    while q:
        node, d = q.popleft()
        if d >= 3:
            break
        for nb in config.CLASS_ADJACENCY.get(node, ()):
            if nb == b:
                return d + 1
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return 3


def carrier_class(conn: sqlite3.Connection, carrier_text: str | None) -> tuple[str | None, str | None]:
    """E2: the class of whoever published the fact, from the carriers registry."""
    from .carriers import resolve
    if not carrier_text:
        return None, None
    r = resolve(conn, carrier_text)
    for m in r["matched"]:
        row = conn.execute("SELECT name, participant_class FROM carriers WHERE lower(name) = lower(?)", (m["name"],)).fetchone()
        if row and row["participant_class"]:
            return row["participant_class"], row["name"]
    return None, (r["matched"][0]["name"] if r["matched"] else None)


def default_price_setter(conn: sqlite3.Connection, holder_id: str, node: str = "") -> str:
    """E2: the class that marks this leg's instrument. Bonds and creditor legs are credit; a covered small cap is
    equity_specialist; a large diversified listing is equity_generalist; anything unlisted is priced by contract."""
    h = conn.execute("SELECT canonical_name, kind, listed, options_listed FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h:
        return "contract"
    name = (h["canonical_name"] or "").lower() + " " + (node or "").lower()
    if any(w in name for w in ("bond", "note", "creditor", "debt", "loan")):
        return "credit"
    if not h["listed"]:
        return "procurement" if any(w in name for w in ("buyer", "customer", "converter", "publisher", "printer")) else "contract"
    return "equity_generalist" if h["options_listed"] else "equity_specialist"


def annotate_leg(conn: sqlite3.Connection, round_id: str, position_id: str, fact_holder_class: str,
                 price_setter_class: str, basis: str, channel_between: str | None = None,
                 fact_carrier: str | None = None) -> dict:
    """E2: set at lock. channel_between names a pre-registered channel or is left null."""
    from .rounds import round_state
    if round_state(conn, round_id) in ("scored", "void"):
        raise StateError("leg annotations are set while the round is live")
    for c, label in ((fact_holder_class, "fact_holder_class"), (price_setter_class, "price_setter_class")):
        if c not in config.PARTICIPANT_CLASSES:
            raise ValidationError(f"{label} must be one of {config.PARTICIPANT_CLASSES}")
    if channel_between and channel_between not in config.CHANNELS:
        raise ValidationError(f"channel_between must be one of {config.CHANNELS} or null")
    if not basis.strip():
        raise ValidationError("basis is required: which carrier published the fact, and what marks the instrument")
    if not (conn.execute("SELECT 1 FROM positions WHERE id = ?", (position_id,)).fetchone()
            or conn.execute("SELECT 1 FROM synthetic_legs WHERE id = ?", (position_id,)).fetchone()):
        raise ValidationError("position_id must be a positions row or a synthetic leg")
    latest = conn.execute("SELECT id FROM leg_annotations WHERE round_id = ? AND position_id = ? ORDER BY rowid DESC LIMIT 1",
                          (round_id, position_id)).fetchone()
    row = append(conn, "leg_annotations", {
        "round_id": round_id, "position_id": position_id, "fact_holder_class": fact_holder_class,
        "price_setter_class": price_setter_class, "channel_between": channel_between, "fact_carrier": fact_carrier,
        "basis": basis.strip(), "supersedes": latest["id"] if latest else None})
    return {"annotation_id": row["id"], **divergence(fact_holder_class, price_setter_class, channel_between)}


def divergence(fact_holder_class: str, price_setter_class: str, channel_between: str | None) -> dict:
    """E3: a checkable negative over a bounded set."""
    d = class_distance(fact_holder_class, price_setter_class)
    return {"fact_holder_class": fact_holder_class, "price_setter_class": price_setter_class,
            "channel_between": channel_between, "class_distance": d,
            "class_divergence": bool(fact_holder_class != price_setter_class and not channel_between)}


def annotations_for(conn: sqlite3.Connection, round_id: str, position_ids: list[str]) -> dict | None:
    if not position_ids:
        return None
    q = ",".join("?" for _ in position_ids)
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM leg_annotations WHERE round_id = ? AND position_id IN ({q}) ORDER BY rowid", [round_id, *position_ids])]
    superseded = {r["supersedes"] for r in rows if r["supersedes"]}
    rows = [r for r in rows if r["id"] not in superseded]
    if not rows:
        return None
    r = rows[-1]
    return {**r, **divergence(r["fact_holder_class"], r["price_setter_class"], r["channel_between"])}


# ---- §D3: executability ---------------------------------------------------------------------------------------------

def executability(call_type: str, sign: str | None, implied_value: float | None, implied_method: str | None,
                  expected_move: float | None = None) -> dict:
    """D3, derived at lock and reported per leg.

    fadeable_null: an absence call where implied is materially above zero — the only null with money in it, because
    calling silence is worth something only where the market is paying for noise.
    exceeds_implied: an occurrence call whose expected move is larger than implied over the same window."""
    absence = call_type == "null" or (call_type == "sign" and sign == "0")
    occurrence = call_type in ("sign", "magnitude_order") and not absence
    if implied_method in (None, "none") or implied_value is None:
        return {"executable": "no", "why": "no implied reading on the leg, so the claim cannot be netted against what is priced"}
    if absence:
        if implied_value >= config.FADEABLE_IMPLIED_MIN:
            return {"executable": "fadeable_null", "why": f"implied {implied_value}% over the window is materially above zero "
                                                          f"(threshold {config.FADEABLE_IMPLIED_MIN}%): the market is paying for noise this call says will not come"}
        return {"executable": "no", "why": f"implied {implied_value}% is not materially above zero: silence is already priced, so calling it pays nothing"}
    if occurrence:
        if expected_move is None:
            return {"executable": "no", "why": "no expected move stated on the call, so it cannot be compared with implied"}
        if expected_move > implied_value:
            return {"executable": "exceeds_implied", "why": f"expected {expected_move}% against implied {implied_value}% over the same window"}
        return {"executable": "no", "why": f"expected {expected_move}% is inside implied {implied_value}%: the move is already in"}
    return {"executable": "no", "why": f"{call_type} calls are not executability-tested"}


def expected_move_from(claim: str) -> float | None:
    """The per-cent figure a call names for its own move, if it names one ('at least 30% below', 'more than 3%')."""
    m = re.search(r"(\d+(?:\.\d+)?)\s?(?:%|per ?cent)", claim or "")
    return float(m.group(1)) if m else None


# ---- §F: base rates -------------------------------------------------------------------------------------------------

BASE_RATE_SEED: tuple[dict, ...] = (
    {"key": "br.phase2_so_to_prohibition", "class": "compliance",
     "condition": "eu merger phase ii statement of objections -> prohibition",
     "n": 40, "k": 4, "source": "Commission merger statistics 1990-2025: about 30 prohibitions against several hundred Phase II cases; "
                                "conditional on an SO the prohibition share is roughly one in ten, most cases ending in remedies or withdrawal",
     "knowable_from": "1900-01-01", "note": "seeded as an order of magnitude from the published case register, not a fitted number"},
    {"key": "br.phase2_so_to_remedies", "class": "compliance",
     "condition": "eu merger phase ii statement of objections -> remedies or withdrawal",
     "n": 40, "k": 36, "source": "Commission merger statistics: after an SO the modal outcomes are commitments or abandonment",
     "knowable_from": "1900-01-01"},
    {"key": "br.repeat_filing_self_administration", "class": "compliance",
     "condition": "german corporate insolvency -> self-administration (eigenverwaltung)",
     "n": 100, "k": 5, "source": "German insolvency statistics: self-administration is a small single-digit share of corporate filings; "
                                 "regular proceedings with a provisional administrator are the base case",
     "knowable_from": "1900-01-01", "note": "round 10's map call assumed the company's own 2009 precedent instead of this"},
    {"key": "br.fatal_accident_inspection_order", "class": "compliance",
     "condition": "fatal industrial accident -> jurisdiction-wide inspection order within 30 days",
     "n": 20, "k": 4, "source": "rounds 2 and 4 plus regulator practice: a site-level investigation is near certain, a jurisdiction-wide "
                                "order is not",
     "knowable_from": "1900-01-01"},
    {"key": "br.listed_party_confirms_regulatory_step", "class": "compliance",
     "condition": "listed party receives a regulatory step -> public confirmation within 5 days",
     "n": 20, "k": 18, "source": "disclosure practice: a listed party in the EEA discloses a material regulatory step promptly; the "
                                 "uncertainty is whether both parties speak in their own names",
     "knowable_from": "1900-01-01"},
    {"key": "br.mine_fatal_collapse_suspension", "class": "compliance",
     "condition": "underground mine fatal collapse -> operations suspended at the affected sector",
     "n": 20, "k": 17, "source": "mining regulator practice: a fatal underground event stops the affected sector pending investigation; "
                                 "whole-mine suspension is the exception",
     "knowable_from": "1900-01-01"},
    {"key": "br.producer_force_majeure_after_outage", "class": "contract",
     "condition": "producer outage with contracted offtake -> public force majeure declaration",
     "n": 20, "k": 6, "source": "rounds 2, 5 and 7: force majeure is declared where contracted offtake cannot be served, not on every outage",
     "knowable_from": "1900-01-01"},
)


def base_rate_seed(conn: sqlite3.Connection) -> int:
    n = 0
    for b in BASE_RATE_SEED:
        if conn.execute("SELECT 1 FROM base_rates WHERE key = ?", (b["key"],)).fetchone():
            continue
        row = dict(b)
        row["rate"] = round(row["k"] / row["n"], 4) if row.get("n") else None
        insert_mutable(conn, "base_rates", row)
        n += 1
    return n


def base_rate_add(conn: sqlite3.Connection, key: str, class_: str, condition: str, n: int, k: int, source: str,
                  knowable_from: str, note: str | None = None) -> dict:
    if class_ not in config.PARTICIPANT_CLASSES:
        raise ValidationError(f"class must be one of {config.PARTICIPANT_CLASSES}")
    date.fromisoformat(knowable_from)
    if n <= 0 or k < 0 or k > n:
        raise ValidationError("n must be positive and 0 <= k <= n")
    if conn.execute("SELECT 1 FROM base_rates WHERE key = ?", (key,)).fetchone():
        raise ValidationError(f"base rate {key!r} already exists")
    row = insert_mutable(conn, "base_rates", {"key": key, "class": class_, "condition": condition, "n": n, "k": k,
                                              "rate": round(k / n, 4), "source": source, "knowable_from": knowable_from, "note": note})
    return {"base_rate_id": row["id"], "key": key, "rate": row["rate"]}


def resolve_base_rate(conn: sqlite3.Connection, id_or_key: str) -> dict:
    r = conn.execute("SELECT * FROM base_rates WHERE id = ? OR key = ?", (id_or_key, id_or_key)).fetchone()
    if not r:
        raise NotFound(f"no base rate {id_or_key!r}; see nomad_base_rates")
    return dict(r)


def base_rates(conn: sqlite3.Connection, condition_like: str | None = None, knowable_by: str | None = None) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM base_rates ORDER BY class, key")]
    if condition_like:
        toks = [t for t in re.split(r"\W+", condition_like.lower()) if len(t) > 3]
        rows = [r for r in rows if any(t in r["condition"].lower() for t in toks)]
    if knowable_by:
        rows = [r for r in rows if r["knowable_from"] <= knowable_by]
    return rows


def is_institutional(call_type: str, sign: str | None, target: str, claim: str) -> bool:
    """F3: a sign + call about what an institution will do is a frequency claim."""
    if call_type != "sign" or sign != "+":
        return False
    return bool(INSTITUTIONAL.search(f"{target} {claim}"))
