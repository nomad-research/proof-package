"""v11 §B: replay rounds under the frozen instrument.

The existing rounds hold calls locked blind at the time; they simply predate the measurement layer. Replay applies
v10's machinery to already-locked legs: point-in-time coverage assignment (§A2), re-encode detection against whatever
dated observations exist (§I2), latency, residual state and exposure. It writes to `replay_measurements` and **never**
to `resolutions` — no new predictions, no rescoring. Every row is tagged `replay = true` and is excluded from rule
weights, validation and calibration everywhere (§B4)."""
import sqlite3
from datetime import date

from . import config
from .db import append, get_row
from .errors import StateError, ValidationError
from .util import dumps


V11_DATES = {"risk.tide_visibility": "2026-04-03", "risk.weather": "2026-04-09", "risk.recovered_before_entry": "2026-04-03",
             "risk.catalyst_about_node": "2026-09-08", "risk.slack": "2026-04-09", "risk.cut_into_glut": "2026-03-12",
             "risk.self_hedged_owner": "2026-04-03"}


def _cells_for_leg(conn: sqlite3.Connection, leg: dict, as_of: str, stack: str = "v12") -> list[dict]:
    from .risk import factor_kind_for, list_risk_rules, rule_covers
    fk = factor_kind_for(conn, leg["holder_id"])
    rules = list_risk_rules(conn, active_only=True)
    if stack == "v11":
        rules = [dict(r, knowable_from=V11_DATES.get(r["key"], r["knowable_from"])) for r in rules]
    out = []
    for ek in config.EFFECT_KINDS:
        for w in config.WINDOWS:
            rule = next((r for r in rules if rule_covers(r, fk, leg.get("degree"), ek, w, as_of)), None)
            out.append({"factor_kind": fk, "effect_kind": ek, "window": w,
                        "space": "positive" if rule else "mirror", "covering_rule_id": rule["id"] if rule else None,
                        "covering_rule": rule["key"] if rule else None})
    return out


def replay_round(conn: sqlite3.Connection, round_id: str, as_of: str | None = None, write: bool = True,
                 stack: str = "v12") -> dict:
    """B1: measure one round's locked legs. as_of defaults to the event date (point-in-time coverage).

    v12 H5: `stack` selects which coverage dating the replay reads. 'v12' uses the risk rules as they stand (practice
    dated, §0.2); 'v11' re-reads them at their programme dates, so the two stacks stay comparable after later changes."""
    from .basket import round_legs
    from .risk import existence_floor_holds, leg_due_at, observations_for, reencode_for_leg, residual_state
    from .rounds import round_state
    state = round_state(conn, round_id)
    if state in ("created", "locked"):
        raise StateError(f"round {round_id} is {state}: replay measures locked legs after retrieval opened, never before")
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    as_of = as_of or ev["event_date"]
    prior = conn.execute("SELECT COUNT(*) FROM replay_measurements WHERE round_id = ?", (round_id,)).fetchone()[0]
    legs = round_legs(conn, round_id)
    src = {t["holder_id"]: (t["leg_source"] or "operator") for t in conn.execute(
        "SELECT holder_id, leg_source FROM touched_set WHERE round_id = ?", (round_id,))}
    rows, unmeasured, measured = [], [], 0
    for leg in legs:
        pos_ids = leg["all_position_ids"]
        due = leg_due_at(conn, round_id, pos_ids, ev["event_date"])
        obs = observations_for(conn, round_id, pos_ids)
        reenc = reencode_for_leg(conn, round_id, pos_ids, ev["event_date"], due)
        floor = existence_floor_holds(conn, round_id, leg["listed"])
        rstate = residual_state(reenc, floor) if obs else None
        measurable = bool(obs)
        if not measurable:
            unmeasured.append({"holder": leg["holder"], "node": leg["node"], "why": "no dated observation on the leg's carrier"})
        else:
            measured += 1
        oob = sum(1 for o in obs if (o["band_low"] is not None and o["value"] < o["band_low"])
                  or (o["band_high"] is not None and o["value"] > o["band_high"]))
        for c in _cells_for_leg(conn, leg, as_of, stack):
            row = {"round_id": round_id, "position_id": (pos_ids[0] if pos_ids else None), "holder_id": leg["holder_id"],
                   "node": leg["node"], "leg_source": src.get(leg["holder_id"], "operator"), "effect_kind": c["effect_kind"],
                   "window": c["window"], "space": c["space"], "covering_rule_id": c["covering_rule_id"],
                   "reencode_date": reenc["reencode_date"], "latency_days": reenc["latency_days"], "residual_state": rstate,
                   "observations": len(obs), "measurable": int(measurable), "as_of": as_of, "replay": 1,
                   "note": f"leg {leg['holder']} on {leg['node']}; covering rule {c['covering_rule']}; stack {stack}; "
                           f"out_of_band {oob} of {len(obs)}"}
            rows.append(row)
    if write:
        for r in rows:
            append(conn, "replay_measurements", r)
    cov = {"positive": sum(1 for r in rows if r["space"] == "positive"), "mirror": sum(1 for r in rows if r["space"] == "mirror")}
    oob_total = sum(1 for leg in legs if any((o["band_low"] is not None and o["value"] < o["band_low"])
                                             or (o["band_high"] is not None and o["value"] > o["band_high"])
                                             for o in observations_for(conn, round_id, leg["all_position_ids"])))
    return {"round_id": round_id, "as_of": as_of, "event_date": ev["event_date"], "legs": len(legs), "cells": len(rows),
            "coverage": cov, "mirror_share": (round(cov["mirror"] / len(rows), 6) if rows else None),
            "legs_measured": measured, "legs_unmeasured": unmeasured, "written": len(rows) if write else 0,
            "reencodes": sum(1 for r in rows if r["reencode_date"] and r["effect_kind"] == "direction" and r["window"] == "event_day"),
            "replay": True, "stack": stack, "out_of_band": oob_total, "prior_measurements": prior,
            "note": "measurements only; no resolutions row was touched"}


def replay_all(conn: sqlite3.Connection, round_ids: list[str] | None = None, write: bool = True, stack: str = "v12") -> dict:
    """B2: rounds 8, 9, 10 first (dense positions), then 5-7, then 1-4 best-effort."""
    if round_ids is None:
        ordered = [r["round_id"] for r in conn.execute(
            "SELECT s.round_id FROM round_state s JOIN rounds r ON r.id = s.round_id WHERE s.state IN ('open','partially_scored','scored') ORDER BY r.rowid")]
        round_ids = ordered[7:] + ordered[4:7] + ordered[:4]
    out, failed = [], []
    for rid in round_ids:
        try:
            out.append(replay_round(conn, rid, write=write, stack=stack))
        except Exception as e:
            failed.append({"round_id": rid, "error": f"{type(e).__name__}: {e}"[:200]})
    return {"stack": stack, "rounds": out, "failed": failed, "measured_rounds": len(out),
            "out_of_band_legs": sum(1 for r in out for k in [r] if r.get("out_of_band")),
            "coverage_decay": coverage_decay(conn), "note": "B3: mirror share by round is the effect-side decay curve"}


LATEST = ("SELECT m.* FROM replay_measurements m WHERE m.rowid = (SELECT MAX(x.rowid) FROM replay_measurements x "
          "WHERE x.round_id = m.round_id AND x.holder_id IS m.holder_id AND x.node IS m.node "
          "AND x.effect_kind = m.effect_kind AND x.window = m.window)")


def latest_measurements(conn: sqlite3.Connection, extra: str = "") -> list[dict]:
    """Replay is append-only and a round may be measured again under a corrected stack: the readers take the last pass."""
    return [dict(r) for r in conn.execute(LATEST + (" AND " + extra if extra else ""))]


def coverage_decay(conn: sqlite3.Connection) -> list[dict]:
    """B3: mirror share by round, in event-date order. Point-in-time coverage means an early round is nearly all mirror."""
    rows = []
    for r in conn.execute(
            f"SELECT m.round_id, e.event_date, SUM(m.space = 'mirror') AS mirror, COUNT(*) AS cells "
            f"FROM ({LATEST}) m JOIN rounds rd ON rd.id = m.round_id JOIN events e ON e.id = rd.event_id "
            f"JOIN round_state s ON s.round_id = rd.id WHERE s.state != 'void' "
            f"GROUP BY m.round_id ORDER BY e.event_date"):
        rows.append({"round_id": r["round_id"], "event_date": r["event_date"], "cells": r["cells"], "mirror": r["mirror"],
                     "mirror_share": round(r["mirror"] / r["cells"], 6) if r["cells"] else None})
    # the live grid (round 10 onwards) is measured the same way
    for r in conn.execute(
            "SELECT g.round_id, e.event_date, SUM(g.space = 'mirror') AS mirror, COUNT(*) AS cells FROM grid_cells g "
            "JOIN rounds rd ON rd.id = g.round_id JOIN events e ON e.id = rd.event_id "
            "JOIN round_state s ON s.round_id = rd.id "
            "WHERE s.state != 'void' AND g.round_id NOT IN (SELECT DISTINCT round_id FROM replay_measurements) "
            "GROUP BY g.round_id ORDER BY e.event_date"):
        rows.append({"round_id": r["round_id"], "event_date": r["event_date"], "cells": r["cells"], "mirror": r["mirror"],
                     "mirror_share": round(r["mirror"] / r["cells"], 6) if r["cells"] else None, "live_grid": True})
    return sorted(rows, key=lambda x: x["event_date"])


def latency_distribution(conn: sqlite3.Connection) -> dict:
    """B3: latency by degree and node kind, over replay measurements with a re-encode. The first empirical content for
    Claim 1: how long a residual survives before the market prices it."""
    rows = [dict(r) for r in conn.execute(
        f"SELECT m.*, h.listed, e.node_kind FROM ({LATEST}) m LEFT JOIN holders h ON h.id = m.holder_id "
        f"JOIN rounds rd ON rd.id = m.round_id JOIN events e ON e.id = rd.event_id WHERE m.reencode_date IS NOT NULL")]
    seen, legs = set(), []
    for r in rows:      # one row per leg, not per cell
        k = (r["round_id"], r["holder_id"], r["node"])
        if k in seen:
            continue
        seen.add(k)
        legs.append(r)
    def agg(items):
        lat = sorted(x["latency_days"] for x in items if x["latency_days"] is not None)
        return {"n": len(items), "median_days": (lat[len(lat) // 2] if lat else None), "min": (lat[0] if lat else None),
                "max": (lat[-1] if lat else None)}
    return {"legs_with_reencode": len(legs), "overall": agg(legs),
            "by_node_kind": {k: agg([x for x in legs if (x["node_kind"] or "unknown") == k]) for k in sorted({x["node_kind"] or "unknown" for x in legs})},
            "by_listed": {"listed": agg([x for x in legs if x["listed"]]), "unlisted": agg([x for x in legs if not x["listed"]])},
            "note": "replay measurements only; excluded from rule weights, validation and calibration (B4)"}


def k5_rates(conn: sqlite3.Connection) -> dict:
    """B3: K5's denominator over every replayed round: mirror vs positive re-encode rate."""
    out = {}
    for space in ("positive", "mirror"):
        rows = [r for r in latest_measurements(conn) if r["space"] == space and r["measurable"]]
        rec = sum(1 for r in rows if r["reencode_date"])
        out[space] = {"cells": len(rows), "reencoded": rec, "rate": (round(rec / len(rows), 6) if rows else None)}
    out["claim"] = ("K5: mirror legs resolve with an attributed price or volume move at a higher rate than positive legs "
                    "on the same events; falsifier is ten clean rounds with the mirror rate not above the positive rate")
    return out
