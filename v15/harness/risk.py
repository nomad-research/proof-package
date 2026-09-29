"""v10 §I risk engine v0 (measurement only), §J effect grid, §K mirror basket.

Price never proposes. It is consulted only as an outcome timestamp, after a call's due date (I1). Every event casts two
baskets from the same store: the positive basket holds the cells some active risk rule covers, the mirror holds the
cells no rule covers (K1). Assignment happens at lock and is frozen; a rule added later is recorded as a coverage
migration, never rewritten onto the locked row (K3)."""
import math
import sqlite3
from datetime import date, timedelta

from . import config
from .db import append, get_row, insert_mutable
from .errors import NotFound, StateError, ValidationError
from .util import dumps, loads, now_iso

RISK_KINDS = ("veto", "date", "classify")

# I6 seed: what nine rounds made explicit. covers = {effect_kinds, factor_kinds, degrees, windows}; "*" = all.
RISK_SEED: tuple[dict, ...] = (
    {"key": "risk.tide_visibility", "kind": "veto", "library_key": "lib.equity_visibility_ratio", "knowable_from": "2026-04-03",
     "text": "an equity leg is vetoed for direction when event size over ambient tide is below the visibility ratio",
     "covers": {"effect_kinds": ["direction"], "factor_kinds": ["equity"], "degrees": [0, 1, 2, 3], "windows": ["event_day", "days", "weeks", "to_due"]}},
    {"key": "risk.weather", "kind": "veto", "library_key": "lib.recurring_disruption_weather", "knowable_from": "2026-04-09",
     "text": "a leg on a recurring-disruption node is vetoed for direction and volume beyond the event day",
     "covers": {"effect_kinds": ["direction", "volume"], "factor_kinds": "*", "degrees": [0, 1, 2, 3], "windows": ["days", "weeks", "to_due"]}},
    {"key": "risk.recovered_before_entry", "kind": "veto", "library_key": "lib.novelty_channels_not_events", "knowable_from": "2026-04-03",
     "text": "a leg on a channel already traversed by a crisis is vetoed for direction: the residual was recovered before entry",
     "covers": {"effect_kinds": ["direction"], "factor_kinds": "*", "degrees": [1, 2, 3], "windows": ["days", "weeks", "to_due"]}},
    {"key": "risk.catalyst_about_node", "kind": "date", "library_key": "lib.catalyst_not_about_node_is_tide", "knowable_from": "2026-09-08",
     "text": "a scheduled statement dates a direction or timing leg only when it concerns the node; otherwise it is a tide",
     "covers": {"effect_kinds": ["direction", "timing"], "factor_kinds": "*", "degrees": [0, 1], "windows": ["to_due"]}},
    {"key": "risk.slack", "kind": "classify", "library_key": "lib.demand_slump_mute", "knowable_from": "2026-04-09",
     "text": "a supply-side leg into a receiving market with slack is classified muted for direction and volume",
     "covers": {"effect_kinds": ["direction", "volume"], "factor_kinds": ["physical", "aggregate", "private"], "degrees": [1, 2, 3], "windows": ["days", "weeks", "to_due"]}},
    {"key": "risk.cut_into_glut", "kind": "veto", "library_key": "lib.cut_into_glut_silent", "knowable_from": "2026-03-12",
     "text": "a cut into a demonstrated surplus is vetoed for direction on the receiving market's legs",
     "covers": {"effect_kinds": ["direction"], "factor_kinds": ["physical", "aggregate", "private"], "degrees": [0, 1, 2, 3], "windows": ["event_day", "days", "weeks", "to_due"]}},
    {"key": "risk.self_hedged_owner", "kind": "veto", "library_key": "lib.wounded_owner_collects_premium", "knowable_from": "2026-04-03",
     "text": "an owner holding both signs on the node is vetoed for direction at degree 0 and 1",
     "covers": {"effect_kinds": ["direction"], "factor_kinds": ["equity"], "degrees": [0, 1], "windows": ["event_day", "days", "weeks", "to_due"]}},
)


# ---- settings ---------------------------------------------------------------------------------------------------

def setting(conn: sqlite3.Connection, key: str, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else default


def setting_set(conn: sqlite3.Connection, key: str, value: str, note: str | None = None) -> dict:
    if conn.execute("SELECT 1 FROM settings WHERE key = ?", (key,)).fetchone():
        conn.execute("UPDATE settings SET value = ?, note = COALESCE(?, note) WHERE key = ?", (str(value), note, key))
    else:
        insert_mutable(conn, "settings", {"key": key, "value": str(value), "note": note})
    return {"key": key, "value": str(value)}


# ---- I6 risk rules ------------------------------------------------------------------------------------------------

def _fmt_rule(r) -> dict:
    d = dict(r)
    d["covers"] = loads(d["covers"])
    d["active"] = bool(d["active"])
    return d


def list_risk_rules(conn: sqlite3.Connection, active_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM risk_rules" + (" WHERE active = 1" if active_only else "") + " ORDER BY rowid"
    return [_fmt_rule(r) for r in conn.execute(sql)]


def _validate_covers(covers: dict) -> dict:
    out = {}
    for k, allowed in (("effect_kinds", config.EFFECT_KINDS), ("factor_kinds", config.FACTOR_KINDS),
                       ("degrees", config.GRID_DEGREES), ("windows", config.WINDOWS)):
        v = covers.get(k, "*")
        if v == "*":
            out[k] = "*"
            continue
        if not isinstance(v, list) or not v:
            raise ValidationError(f"covers.{k} must be '*' or a non-empty list")
        bad = [x for x in v if x not in allowed]
        if bad:
            raise ValidationError(f"covers.{k}: {bad} not in the grid {allowed} (the grid is frozen; see §J)")
        out[k] = sorted(v, key=lambda x: list(allowed).index(x))
    return out


def _rounds_in(conn: sqlite3.Connection, states: tuple[str, ...]) -> list[str]:
    q = ",".join("?" for _ in states)
    return [r["round_id"] for r in conn.execute(f"SELECT round_id FROM round_state WHERE state IN ({q})", states)]


def risk_rule_add(conn: sqlite3.Connection, key: str, text: str, kind: str, covers: dict, knowable_from: str,
                  library_rule: str | None = None) -> dict:
    """Adding a risk rule happens only between rounds: refused while any round sits in created or locked (the moment
    of assignment). Open and partially scored rounds get coverage migrations on their mirror cells (K3)."""
    if kind not in RISK_KINDS:
        raise ValidationError(f"kind must be one of {RISK_KINDS}")
    if not key.strip() or not text.strip():
        raise ValidationError("key and text are required")
    date.fromisoformat(knowable_from)
    busy = _rounds_in(conn, ("created", "locked"))
    if busy:
        raise StateError(f"a risk rule is added only between rounds: round(s) {busy} are created or locked (assignment pending)")
    if conn.execute("SELECT 1 FROM risk_rules WHERE key = ?", (key,)).fetchone():
        raise ValidationError(f"risk rule {key!r} already exists")
    lib_id = None
    if library_rule:
        from .library import resolve_rule
        lib_id = resolve_rule(conn, library_rule)["id"]
    cov = _validate_covers(covers)
    row = insert_mutable(conn, "risk_rules", {"key": key.strip(), "text": text.strip(), "kind": kind, "covers": dumps(cov),
                                              "knowable_from": knowable_from, "library_rule_id": lib_id, "active": 1})
    migrations = migrate_coverage(conn, row["id"])
    return {"risk_rule_id": row["id"], "key": key.strip(), "covers": cov, "migrations": migrations}


PRACTICE_SENTINEL = "1900-01-01"

# v13 A3: which eliminator each seeded rule becomes, and therefore which precondition is declared with it. A silence
# rule does not cover every direction cell; it covers the legs its precondition is true on. That was the same error as
# the mirror basket, one layer down.
RULE_ELIMINATOR: dict[str, str] = {
    "risk.tide_visibility": "tide", "risk.recovered_before_entry": "traversed", "risk.weather": "weather",
    "risk.slack": "slack", "risk.cut_into_glut": "slack", "risk.self_hedged_owner": "self_hedged",
}


def set_preconditions(conn: sqlite3.Connection) -> dict:
    """Write each rule's pre-registered precondition onto its row. Declared once, never edited to move a leg."""
    changed = []
    for r in conn.execute("SELECT id, key, precondition FROM risk_rules ORDER BY rowid").fetchall():
        elim = RULE_ELIMINATOR.get(r["key"])
        pre = config.ELIMINATOR_PRECONDITION.get(elim) if elim else None
        text = f"{elim}: {pre}" if elim else "no eliminator: this rule dates a leg, it does not silence one"
        if text != r["precondition"]:
            conn.execute("UPDATE risk_rules SET precondition = ? WHERE id = ?", (text, r["id"]))
            changed.append({"key": r["key"], "eliminator": elim, "precondition": pre})
    return {"changed": changed, "eliminators": config.ELIMINATORS,
            "note": "A3: coverage is evaluated at lock against these and frozen"}


def practice_date_rules(conn: sqlite3.Connection) -> dict:
    """v12 0.2: the seeded rules are ordinary risk practice long predating the programme, so their knowable_from was
    measuring our learning, not the market's. Set them to the sentinel and mark the origin, so a rule that is genuinely
    novel to practice can still move the coverage curve."""
    changed = []
    for r in conn.execute("SELECT id, key, knowable_from, origin FROM risk_rules ORDER BY rowid").fetchall():
        seeded = any(s["key"] == r["key"] for s in RISK_SEED)
        origin = "practice" if seeded else (r["origin"] or "programme")
        kf = PRACTICE_SENTINEL if origin == "practice" else r["knowable_from"]
        if (kf, origin) != (r["knowable_from"], r["origin"]):
            conn.execute("UPDATE risk_rules SET knowable_from = ?, origin = ? WHERE id = ?", (kf, origin, r["id"]))
            changed.append({"key": r["key"], "from": r["knowable_from"], "to": kf, "origin": origin})
    return {"changed": changed, "sentinel": PRACTICE_SENTINEL,
            "note": "coverage decay is now measurable only against rules novel to practice (origin = programme)"}


def seed_risk_rules(conn: sqlite3.Connection) -> int:
    from .library import resolve_rule
    n = 0
    for r in RISK_SEED:
        if conn.execute("SELECT 1 FROM risk_rules WHERE key = ?", (r["key"],)).fetchone():
            continue
        lib_id = None
        if r["library_key"]:
            try:
                lib_id = resolve_rule(conn, r["library_key"])["id"]
            except NotFound:
                lib_id = None
        insert_mutable(conn, "risk_rules", {"key": r["key"], "text": r["text"], "kind": r["kind"], "covers": dumps(_validate_covers(r["covers"])),
                                            "knowable_from": r["knowable_from"], "library_rule_id": lib_id, "active": 1,
                                            "origin": "practice"})
        n += 1
    return n


def rule_covers(rule: dict, factor_kind: str, degree: int | None, effect_kind: str, window: str, as_of: str | None = None) -> bool:
    if not rule.get("active", True):
        return False
    if as_of and rule["knowable_from"] > as_of:
        return False
    c = rule["covers"]
    if c["effect_kinds"] != "*" and effect_kind not in c["effect_kinds"]:
        return False
    if c["windows"] != "*" and window not in c["windows"]:
        return False
    if c["factor_kinds"] != "*" and factor_kind not in c["factor_kinds"]:
        return False
    if c["degrees"] != "*" and degree is not None and degree not in c["degrees"]:
        return False
    return True


def covering_rule(conn: sqlite3.Connection, factor_kind: str, degree: int | None, effect_kind: str, window: str,
                  as_of: str | None = None) -> dict | None:
    for r in list_risk_rules(conn, active_only=True):
        if rule_covers(r, factor_kind, degree, effect_kind, window, as_of):
            return r
    return None


# ---- J/K1: the grid at lock ----------------------------------------------------------------------------------------

def factor_kind_for(conn: sqlite3.Connection, holder_id: str) -> str:
    h = conn.execute("SELECT kind, listed FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h:
        return "aggregate"
    if h["listed"]:
        return "equity"
    if h["kind"] in ("plant", "facility", "authority"):
        return "physical"
    if h["kind"] == "company":
        return "private"
    return "aggregate"


def window_for(falsifier_window: str | None, lag_band: str | None = None) -> str:
    fw = falsifier_window or "scoring_window"
    if fw.startswith("days:"):
        n = int(fw[5:])
        for w in ("event_day", "days", "weeks"):
            if n <= config.WINDOW_DAYS[w]:
                return w
        return "to_due"
    if lag_band in ("days",):
        return "days"
    if lag_band in ("weeks",):
        return "weeks"
    return "to_due"


def effect_kind_for(call_type: str) -> str:
    return {"lag_band": "timing", "magnitude_order": "direction"}.get(call_type, "direction")


def assign_grid(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """K1: for every natural leg x effect kind x window, ask the registry whether an active rule covers the cell.
    Writes grid_cells rows (frozen). Returns the cells and the counts. Idempotent per round: refuses a second pass."""
    from .basket import round_legs
    if conn.execute("SELECT 1 FROM grid_cells WHERE round_id = ? LIMIT 1", (round_id,)).fetchone():
        raise StateError(f"grid already assigned on round {round_id}; the assignment is frozen at lock")
    rules = list_risk_rules(conn, active_only=True)
    cells, covered = [], 0
    for leg in round_legs(conn, round_id):
        pid = next((p for p in leg["position_ids"]), None)
        if not pid:
            continue
        fk = factor_kind_for(conn, leg["holder_id"])
        for ek in config.EFFECT_KINDS:
            for w in config.WINDOWS:
                rule = next((r for r in rules if rule_covers(r, fk, leg.get("degree"), ek, w, as_of)), None)
                row = append(conn, "grid_cells", {
                    "round_id": round_id, "position_id": pid, "holder_id": leg["holder_id"], "node": leg["node"], "degree": leg.get("degree"),
                    "factor_kind": fk, "effect_kind": ek, "window": w, "space": "positive" if rule else "mirror",
                    "covering_rule_id": rule["id"] if rule else None})
                covered += bool(rule)
                cells.append({"cell_id": row["id"], "holder": leg["holder"], "node": leg["node"], "degree": leg.get("degree"), "factor_kind": fk,
                              "effect_kind": ek, "window": w, "space": row["space"], "covering_rule": rule["key"] if rule else None})
    return {"round_id": round_id, "cells": cells, "n_cells": len(cells), "covered": covered, "mirror": len(cells) - covered}


def grid_cells(conn: sqlite3.Connection, round_id: str, space: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM grid_cells WHERE round_id = ?", [round_id]
    if space:
        sql += " AND space = ?"
        args.append(space)
    return [dict(r) for r in conn.execute(sql + " ORDER BY rowid", args)]


def cell_for(conn: sqlite3.Connection, round_id: str, position_ids: list[str], effect_kind: str, window: str) -> dict | None:
    if not position_ids:
        return None
    q = ",".join("?" for _ in position_ids)
    r = conn.execute(f"SELECT * FROM grid_cells WHERE round_id = ? AND position_id IN ({q}) AND effect_kind = ? AND window = ? LIMIT 1",
                     [round_id, *position_ids, effect_kind, window]).fetchone()
    return dict(r) if r else None


def dry_run_grid(conn: sqlite3.Connection, round_id: str, as_of: str | None = None) -> dict:
    """K6: the assignment a round would get today, without writing (for rounds locked before v10)."""
    from .basket import round_legs
    rules = list_risk_rules(conn, active_only=True)
    cells, covered = [], 0
    for leg in round_legs(conn, round_id):
        fk = factor_kind_for(conn, leg["holder_id"])
        for ek in config.EFFECT_KINDS:
            for w in config.WINDOWS:
                rule = next((r for r in rules if rule_covers(r, fk, leg.get("degree"), ek, w, as_of)), None)
                covered += bool(rule)
                cells.append({"holder": leg["holder"], "holder_id": leg["holder_id"], "node": leg["node"], "degree": leg.get("degree"), "factor_kind": fk,
                              "effect_kind": ek, "window": w, "space": "positive" if rule else "mirror", "covering_rule": rule["key"] if rule else None,
                              "position_ids": leg["all_position_ids"], "listed": leg["listed"]})
    return {"round_id": round_id, "cells": cells, "n_cells": len(cells), "covered": covered, "mirror": len(cells) - covered, "dry_run": True}


# ---- K3: coverage migrations --------------------------------------------------------------------------------------

def migrate_coverage(conn: sqlite3.Connection, risk_rule_id: str) -> list[dict]:
    """A new rule covering an open mirror cell (a cell on a round not yet scored) is recorded; the cell keeps space mirror."""
    rule = _fmt_rule(get_row(conn, "risk_rules", risk_rule_id, "risk rule"))
    open_rounds = set(_rounds_in(conn, ("open", "partially_scored")))
    out = []
    for c in conn.execute("SELECT * FROM grid_cells WHERE space = 'mirror' ORDER BY rowid"):
        if c["round_id"] not in open_rounds:
            continue
        if conn.execute("SELECT 1 FROM coverage_migrations WHERE grid_cell_id = ? AND risk_rule_id = ?", (c["id"], risk_rule_id)).fetchone():
            continue
        if rule_covers(rule, c["factor_kind"], c["degree"], c["effect_kind"], c["window"]):
            row = append(conn, "coverage_migrations", {"grid_cell_id": c["id"], "round_id": c["round_id"], "risk_rule_id": risk_rule_id,
                                                       "covered_at": now_iso()[:10]})
            out.append({"migration_id": row["id"], "cell_id": c["id"], "round_id": c["round_id"], "effect_kind": c["effect_kind"], "window": c["window"]})
    return out


def migrations_for(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT m.*, r.key AS rule_key FROM coverage_migrations m JOIN risk_rules r ON r.id = m.risk_rule_id "
                                          "WHERE m.round_id = ? ORDER BY m.rowid", (round_id,))]


def now_covered(conn: sqlite3.Connection, cell: dict) -> dict | None:
    """K2 pred.disarm.now_covered: a rule added since lock that covers the cell."""
    return covering_rule(conn, cell["factor_kind"], cell["degree"], cell["effect_kind"], cell["window"])


# ---- I1: price observations --------------------------------------------------------------------------------------

def realised_band(closes: list[float], sessions: int = config.BAND_SESSIONS, sigma: float = config.BAND_SIGMA) -> dict:
    """Band around the last close from the prior `sessions` daily returns (pre-registered method, recorded per row)."""
    if len(closes) < 3:
        raise ValidationError("realised_band needs at least three closes")
    xs = closes[-(sessions + 1):]
    rets = [(xs[i] / xs[i - 1] - 1.0) for i in range(1, len(xs)) if xs[i - 1]]
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1))
    last = xs[-1]
    return {"band_low": round(last * (1 - sigma * sd), 6), "band_high": round(last * (1 + sigma * sd), 6),
            "band_method": f"{len(rets)}-session realised band, {sigma} sigma", "sessions": len(rets), "stdev": round(sd, 6)}


def percentile(xs: list[float], q: float) -> float:
    """Linear-interpolation percentile. No numpy in the dependency set, and the arithmetic is three lines."""
    if not xs:
        raise ValidationError("percentile of an empty sample")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    pos = (q / 100.0) * (len(ys) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (pos - lo)


def empirical_band(closes: list[float], sessions: int = config.BAND_SESSIONS_EMPIRICAL,
                   pctile: tuple[float, float] = config.BAND_PCTILE) -> dict:
    """v13 B1: the trailing empirical return distribution, not a normal fitted to it.

    A two-sigma parametric band was breached on 23 of 62 sessions on a thin Santiago listing. That is not a calibration
    error, it is a distributional claim the series never supported: a small cap's daily returns are nothing like normal,
    so two sigma is not a 5% tail there. The empirical percentiles make no such claim. They also cannot be wrong about
    the past, which is the only thing a band is entitled to describe."""
    if len(closes) < 11:
        raise ValidationError("an empirical band needs at least eleven closes; use a longer window or accept no band")
    xs = closes[-(sessions + 1):]
    rets = [(xs[i] / xs[i - 1] - 1.0) for i in range(1, len(xs)) if xs[i - 1]]
    lo_r, hi_r = percentile(rets, pctile[0]), percentile(rets, pctile[1])
    last = xs[-1]
    return {"band_low": round(last * (1 + lo_r), 6), "band_high": round(last * (1 + hi_r), 6),
            "band_method": f"{len(rets)}-session empirical band, {pctile[0]}th to {pctile[1]}th percentile of daily returns",
            "sessions": len(rets), "pctile_low": round(lo_r, 6), "pctile_high": round(hi_r, 6),
            "stdev": round((sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / max(1, len(rets) - 1)) ** 0.5, 6)}


def band_from(closes: list[float], method: str | None = None) -> dict:
    """The pre-registered method, which is `config.BAND_METHOD`. Parametric is kept so an old row can be re-derived."""
    return realised_band(closes) if (method or config.BAND_METHOD) == "parametric" else empirical_band(closes)


def _leg_ids(conn: sqlite3.Connection, position_id: str) -> list[str]:
    p = conn.execute("SELECT holder_id, node FROM positions WHERE id = ?", (position_id,)).fetchone()
    if not p:
        if conn.execute("SELECT 1 FROM synthetic_legs WHERE id = ?", (position_id,)).fetchone():
            return [position_id]
        raise NotFound(f"position_id {position_id!r} is not a positions row or synthetic leg")
    return [r["id"] for r in conn.execute("SELECT id FROM positions WHERE holder_id = ? AND lower(node) = lower(?)", (p["holder_id"], p["node"]))]


def price_observe(conn: sqlite3.Connection, round_id: str, position_id: str, carrier: str, date_: str, value: float,
                  attributed: bool, attribution_evidence_id: str | None = None, closes: list[float] | None = None,
                  band_low: float | None = None, band_high: float | None = None, band_method: str | None = None,
                  note: str | None = None, scoring: bool = False, today: str | None = None,
                  band_reliable: bool | None = None, turnover_usd: float | None = None) -> dict:
    """Written only post-lock and only for calls whose due_at has passed or which are being scored (scoring=true)."""
    from .rounds import round_state
    state = round_state(conn, round_id)
    if state in ("created", "locked"):
        raise StateError(f"price observations are written post-lock only: round {round_id} is {state}")
    if state == "void":
        raise StateError("round is void")
    date.fromisoformat(date_)
    today = today or date.today().isoformat()
    ids = _leg_ids(conn, position_id)
    q = ",".join("?" for _ in ids)
    due = [r["due_at"] for r in conn.execute(f"SELECT due_at FROM predictions WHERE round_id = ? AND position_id IN ({q})", [round_id, *ids])]
    if not scoring and not any(d and d <= today for d in due):
        raise StateError(f"the leg's calls are not due yet (due_at {sorted(x for x in due if x)}); price is an outcome timestamp, "
                         "written after due_at or while scoring (scoring=true)")
    if attributed and not attribution_evidence_id:
        raise ValidationError("an attributed observation needs attribution_evidence_id (the evidence row that cites the event)")
    if attribution_evidence_id and not conn.execute("SELECT 1 FROM evidence WHERE id = ? AND round_id = ?", (attribution_evidence_id, round_id)).fetchone():
        raise ValidationError("attribution_evidence_id must be an evidence row on this round")
    if closes:
        b = band_from(closes)
        band_low, band_high, band_method = b["band_low"], b["band_high"], b["band_method"]
    if band_low is None or band_high is None:
        raise ValidationError("pass closes (the prior sessions, last = the observation's reference close) or band_low/band_high with band_method")
    row = append(conn, "price_observations", {
        "round_id": round_id, "position_id": position_id, "carrier": carrier, "date": date_, "value": float(value),
        "band_low": band_low, "band_high": band_high, "band_method": band_method or "caller-supplied",
        "attributed": bool(attributed), "attribution_evidence_id": attribution_evidence_id, "note": note,
        "band_reliable": (None if band_reliable is None else int(bool(band_reliable))), "turnover_usd": turnover_usd})
    out_of_band = value < band_low or value > band_high
    return {"observation_id": row["id"], "position_id": position_id, "date": date_, "out_of_band": out_of_band,
            "attributed": bool(attributed), "band": [band_low, band_high],
            "band_reliable": band_reliable, "turnover_usd": turnover_usd,
            "counts_as_reencode": bool(out_of_band and attributed and band_reliable is not False)}


def observations_for(conn: sqlite3.Connection, round_id: str, position_ids: list[str]) -> list[dict]:
    if not position_ids:
        return []
    q = ",".join("?" for _ in position_ids)
    return [dict(r) for r in conn.execute(f"SELECT * FROM price_observations WHERE round_id = ? AND position_id IN ({q}) ORDER BY date, rowid",
                                          [round_id, *position_ids])]


# ---- I2/I3: re-encode and residual state ------------------------------------------------------------------------------

def reencode_for_leg(conn: sqlite3.Connection, round_id: str, position_ids: list[str], knowable_from: str, due_at: str | None) -> dict:
    """First date after knowable_from where an observation is out of band and attributed; null if none by due_at."""
    obs = observations_for(conn, round_id, position_ids)
    for o in obs:
        if o["date"] < knowable_from:
            continue          # the event day counts: an intraday statement re-encoded by the close is latency zero
        if due_at and o["date"] > due_at:
            break
        oob = o["value"] < (o["band_low"] if o["band_low"] is not None else -math.inf) or o["value"] > (o["band_high"] if o["band_high"] is not None else math.inf)
        if o.get("band_reliable") == 0:
            continue      # v13 B1: below the turnover floor the band carries no information; the row is kept, not counted
        if oob and o["attributed"]:
            lat = (date.fromisoformat(o["date"]) - date.fromisoformat(knowable_from)).days
            return {"reencode_date": o["date"], "latency_days": lat, "observation_id": o["id"], "observations": len(obs)}
    return {"reencode_date": None, "latency_days": None, "observation_id": None, "observations": len(obs)}


def existence_floor_holds(conn: sqlite3.Connection, round_id: str, listed: bool) -> bool | None:
    r = conn.execute("SELECT pc.observed, pc.claimed FROM predicate_checks pc JOIN predicates p ON p.id = pc.predicate_id "
                     "WHERE pc.round_id = ? AND p.key = 'pred.arm.existence_floor' ORDER BY pc.rowid DESC LIMIT 1", (round_id,)).fetchone()
    if r:
        v = r["observed"] or r["claimed"]
        return None if v == "unknown" else v == "holds"
    return listed or None


def residual_state(reencode: dict, floor: bool | None) -> str:
    if reencode["reencode_date"]:
        return "recovered"
    if floor is False:
        return "no_residual"
    return "unrecovered"


def leg_due_at(conn: sqlite3.Connection, round_id: str, position_ids: list[str], event_date: str) -> str:
    if position_ids:
        q = ",".join("?" for _ in position_ids)
        r = conn.execute(f"SELECT MAX(due_at) AS d FROM predictions WHERE round_id = ? AND position_id IN ({q})", [round_id, *position_ids]).fetchone()
        if r and r["d"]:
            return r["d"]
    return (date.fromisoformat(event_date) + timedelta(days=config.DUE_AT_MAX_DAYS)).isoformat()


# ---- I4: exposure --------------------------------------------------------------------------------------------------------

def exposure(conn: sqlite3.Connection, round_id: str | None = None) -> dict:
    """Per shared factor (node): sum of sign x support over legs in `unrecovered`, earliest forcing date, correlations.
    round_id None = every open or partially scored round. No sizing."""
    from .basket import event_basket, shared_factors
    rounds_ = [round_id] if round_id else _rounds_in(conn, ("open", "partially_scored"))
    factors: dict[str, dict] = {}
    for rid in rounds_:
        b = event_basket(conn, rid)
        for l in b["legs"]:
            if l.get("residual_state") != "unrecovered":
                continue
            sgn = {"+": 1, "-": -1}.get(l["sign"], 0)
            f = factors.setdefault(l["node"].lower(), {"node": l["node"], "sum_sign_x_support": 0.0, "legs": [], "earliest_forcing_date": None, "rounds": set()})
            f["sum_sign_x_support"] += sgn * (l["support_weight"] or 0.0)
            f["legs"].append({"round_id": rid, "holder": l["holder"], "sign": l["sign"], "support_weight": l["support_weight"], "forcing_date": l.get("forcing_date")})
            f["rounds"].add(rid)
            fd = l.get("forcing_date")
            if fd and (f["earliest_forcing_date"] is None or fd < f["earliest_forcing_date"]):
                f["earliest_forcing_date"] = fd
    out = []
    for f in factors.values():
        f["sum_sign_x_support"] = round(f["sum_sign_x_support"], 6)
        f["rounds"] = sorted(f["rounds"])
        out.append(f)
    corr = {rid: shared_factors(conn, rid)["pairs"] for rid in rounds_}
    return {"rounds": rounds_, "factors": out, "correlations": corr, "note": "measurement only; no sizing; price consulted after due dates only"}


# ---- K5: the notebook claim ----------------------------------------------------------------------------------------------

def mirror_rates(conn: sqlite3.Connection, round_id: str) -> dict:
    """Per space: cells on legs with an attributed re-encode within due_at over cells total (the K5 read)."""
    from .basket import event_basket
    b = event_basket(conn, round_id, space="both")
    by_leg = {tuple(sorted(l["all_position_ids"])): l for l in b["legs"]}
    out = {}
    for space in ("positive", "mirror"):
        cells = [c for c in b.get("cells", []) if c["space"] == space]
        rec = 0
        for c in cells:
            leg = next((l for l in b["legs"] if c["position_id"] in l["all_position_ids"]), None)
            rec += bool(leg and leg.get("reencode", {}).get("reencode_date"))
        out[space] = {"cells": len(cells), "reencoded": rec, "rate": (round(rec / len(cells), 6) if cells else None)}
    return out


# ---- K6: worked check on a round locked before v10 --------------------------------------------------------------------

def mirror_dry_run(conn: sqlite3.Connection, round_id: str, holder: str | None = None) -> dict:
    """What the positive and mirror baskets would hold today for a round locked before v10: per cell, space, covering
    rule, gate (recorded checks; options for vol cells), dating (scheduled or mechanical facts on the leg), status."""
    from .basket import dated_facts_for, event_basket
    from .predicates import armed_legs
    b = event_basket(conn, round_id)
    g = dry_run_grid(conn, round_id)
    gate_by_pid = {a["position_id"]: a for a in armed_legs(conn, round_id)}
    ev = get_row(conn, "events", get_row(conn, "rounds", round_id, "round")["event_id"], "event")
    out = []
    for c in g["cells"]:
        if holder and holder.lower() not in c["holder"].lower():
            continue
        leg = next((l for l in b["legs"] if l["holder_id"] == c["holder_id"] and l["node"].lower() == c["node"].lower()), None)
        arm = next((gate_by_pid[pid] for pid in c["position_ids"] if pid in gate_by_pid), None)
        gate_checked = bool(arm and arm["gate_checked"])
        gate_holds = bool(arm and any(v == "holds" for n, v in arm["predicates"].items() if "tradability" in n.lower()))
        if c["effect_kind"] == "vol":
            opt = conn.execute("SELECT options_listed FROM holders WHERE id = ?", (c["holder_id"],)).fetchone()
            gate_checked, gate_holds = True, bool(opt and opt["options_listed"])
        horizon = (date.fromisoformat(ev["event_date"]) + timedelta(days=config.DUE_AT_MAX_DAYS)).isoformat()
        facts = dated_facts_for(conn, leg, ev["event_date"], horizon) if leg else []
        # a positive cell is dated only by a fact that concerns the node; a mirror cell by any scheduled or mechanical fact
        facts = [f for f in facts if (not f["same_day"]) or c["window"] == "event_day"]
        if c["space"] == "positive":
            from .scheduled import links_for
            links = links_for(conn, round_id, c["position_ids"])
            dating = [f for f in facts if not f["same_day"] and (f["fact_type"] == "mechanical" or (links.get(f["id"]) or {}).get("concerns_node"))]
        else:
            dating = facts
        if not gate_checked:
            st = "unchecked"
        elif not gate_holds:
            st = "gate_fail"
        elif dating:
            st = "armed_dated"
        else:
            st = "gate_pass_undated"
        out.append({**{k: c[k] for k in ("holder", "node", "degree", "factor_kind", "effect_kind", "window", "space", "covering_rule")},
                    "arming_status": st, "gate": "holds" if gate_holds else ("fails" if gate_checked else "unchecked"),
                    "dated_by": [(f["fact_type"], f["sched_kind"], f["source_time"], f["knowable_from"]) for f in dating]})
    return {"round_id": round_id, "n_cells": len(out), "cells": out,
            "mirror_arming": {s: sum(1 for c in out if c["space"] == "mirror" and c["arming_status"] == s) for s in ("armed_dated", "gate_pass_undated", "gate_fail", "unchecked")},
            "positive_arming": {s: sum(1 for c in out if c["space"] == "positive" and c["arming_status"] == s) for s in ("armed_dated", "gate_pass_undated", "gate_fail", "unchecked")},
            "dry_run": True}
