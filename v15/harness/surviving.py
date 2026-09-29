"""v13 §A: surviving risk.

The mirror basket is retired as a generator. It took the complement of a structure that has no complement: hypotheses
come from the library over positions, shocked by the event, and the risk engine is something each one passes through.
Cell enumeration gave round 12 one hundred and twenty-six mirror legs of which perhaps eight had a reason behind them,
and mirror share turned out to be a geometric constant rather than a fact about any event.

What replaces it is one question per leg:

    **Does any risk survive this leg?**

No edge without risk. A leg where nothing can happen is not a safe position, it is a non-position, and the two are
indistinguishable in a ledger while being opposites in a book. The silence rules that used to be predictions are run
here as *eliminators*: each one, where its precondition holds, can kill the surviving risk on a leg. A leg that no
eliminator touches is one where something could still happen — which is the only kind of leg worth a call.

Two disciplines this module refuses to break:

* **Preconditions are declared with the rule and never edited to move a leg** (§A3). A rule does not cover every leg;
  it covers the legs its precondition is true on. Coverage is evaluated at lock and frozen.
* **An eliminator that cannot be evaluated is not an eliminator that did not fire.** Where the store cannot answer,
  the eliminator is recorded in `eliminators_unevaluable`, and a leg that survives only because nothing could be
  checked says so in its basis. This is the same disease as Q1b's "nothing in reachable registries": the harness must
  not report its own reach as a fact about the world.
"""
import re
import sqlite3
from datetime import date

from . import config
from .db import append, get_row
from .errors import StateError, ValidationError
from .util import dumps, loads

SMALL_WORDS = re.compile(r"\b(small|immaterial|negligible|rounding error|below the noise floor|de minimis)\b", re.I)
SLACK_WORDS = re.compile(r"\b(glut|surplus|oversupply|over-supplied|spare capacity|slack|destocking|demand slump|"
                         r"weak demand|soft demand|utilisation below|utilization below)\b", re.I)


# ---- leg properties -------------------------------------------------------------------------------------------------

def _round_tag(conn: sqlite3.Connection, round_id: str) -> dict:
    r = conn.execute("SELECT q1a, q1b, tag FROM round_tags WHERE round_id = ? ORDER BY rowid DESC LIMIT 1", (round_id,)).fetchone()
    return dict(r) if r else {"q1a": None, "q1b": None, "tag": None}


def _share(conn: sqlite3.Connection, holder_id: str, node: str) -> tuple[float | None, str | None]:
    """The holder's stated share of the node, as a fraction. The store holds both numbers and words ('small'), and the
    words are the more common form: an operator writes one precisely when they have judged the position immaterial."""
    r = conn.execute("SELECT value, unit, source FROM positions WHERE holder_id = ? AND lower(node) = lower(?) "
                     "AND attribute = 'share' ORDER BY rowid DESC LIMIT 1", (holder_id, node)).fetchone()
    if not r:
        return None, None
    txt = f"{r['value']} {r['unit'] or ''} {r['source'] or ''}"
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*$", str(r["value"]))
    if m:
        v = float(m.group(1))
        frac = v / 100.0 if v > 1.0 or "percent" in (r["unit"] or "").lower() or "%" in (r["unit"] or "") else v
        return frac, f"stated share {r['value']} {r['unit'] or ''}".strip()
    if SMALL_WORDS.search(txt):
        return 0.0, f"share recorded in words as immaterial: {str(r['value'])[:40]} ({(r['unit'] or 'no unit')})"
    return None, f"share row present but not readable as a fraction: {str(r['value'])[:40]}"


def _self_hedged(conn: sqlite3.Connection, holder_id: str, node: str) -> tuple[bool, str]:
    signs = {r["value"] for r in conn.execute(
        "SELECT value FROM positions WHERE holder_id = ? AND lower(node) = lower(?) AND attribute = 'sign_of_exposure'",
        (holder_id, node))}
    if "both" in signs or {"+", "-"} <= signs:
        return True, f"the holder carries both signs on {node} in the positions store"
    return False, f"signs on {node} for this holder: {sorted(signs) or 'none recorded'}"


def _slack(conn: sqlite3.Connection, node: str, as_of: str) -> tuple[bool | None, str]:
    """Slack is a fact about the receiving market, so it is read from node facts knowable before the event, never
    inferred from the outcome."""
    for r in conn.execute("SELECT text, source, knowable_from FROM node_facts WHERE lower(node) = lower(?) ORDER BY rowid", (node,)):
        if r["knowable_from"] and r["knowable_from"] > as_of:
            continue
        if SLACK_WORDS.search(r["text"] or ""):
            return True, f"node fact knowable {r['knowable_from'] or 'undated'}: {(r['text'] or '')[:110]}"
    n = conn.execute("SELECT COUNT(*) FROM node_facts WHERE lower(node) = lower(?)", (node,)).fetchone()[0]
    if n == 0:
        return None, "no node fact on the receiving market, so slack cannot be read either way"
    return False, f"{n} node fact(s) on the node, none stating spare capacity or a glut"


def _band_pct(conn: sqlite3.Connection, round_id: str, position_ids: list[str], holder_id: str | None = None,
              as_of: str | None = None, fetch=None) -> tuple[float | None, str]:
    """The leg's own ambient band, as a percentage.

    v14 C2: computed at lock where it can be. The band uses pre-event closes only, so there is nothing about it that
    has to wait for retrieval, and waiting made `stake` and `tide` unevaluable at exactly the moment they were wanted.
    Observations first (they are on the ledger); the pre-event series second."""
    if position_ids:
        q = ",".join("?" for _ in position_ids)
        rows = [dict(r) for r in conn.execute(
            f"SELECT value, band_low, band_high FROM price_observations WHERE round_id = ? AND position_id IN ({q}) "
            f"AND band_low IS NOT NULL ORDER BY date LIMIT 5", [round_id, *position_ids])]
        widths = [(r["band_high"] - r["band_low"]) / 2.0 / ((r["band_high"] + r["band_low"]) / 2.0) * 100
                  for r in rows if r["band_high"]]
        if widths:
            return round(sum(widths) / len(widths), 4), f"mean half-band over {len(widths)} observation(s)"
    if holder_id and as_of:
        band = _preevent_band(conn, holder_id, as_of, fetch)
        if band:
            return band
    if not position_ids:
        return None, "no position on the leg"
    q = ",".join("?" for _ in position_ids)
    rows = [dict(r) for r in conn.execute(
        f"SELECT value, band_low, band_high FROM price_observations WHERE round_id = ? AND position_id IN ({q}) "
        f"AND band_low IS NOT NULL ORDER BY date LIMIT 5", [round_id, *position_ids])]
    if not rows:
        return None, "no banded price observation on the leg"
    widths = [(r["band_high"] - r["band_low"]) / 2.0 / ((r["band_high"] + r["band_low"]) / 2.0) * 100 for r in rows if r["band_high"]]
    if not widths:
        return None, "observations carry no usable band"
    return round(sum(widths) / len(widths), 4), f"mean half-band over {len(widths)} observation(s)"


_BAND_CACHE: dict[tuple[str, str], tuple] = {}


def _preevent_band(conn: sqlite3.Connection, holder_id: str, as_of: str, fetch=None) -> tuple[float, str] | None:
    """C2: the pre-registered band from closes strictly before the event. Cached per (holder, date) so a wide generated
    space does not re-fetch the same series once per leg."""
    key = (holder_id, as_of)
    if key in _BAND_CACHE:
        return _BAND_CACHE[key]
    from . import prices
    h = conn.execute("SELECT canonical_name, ticker, exchange, price_symbol, listed FROM holders WHERE id = ?", (holder_id,)).fetchone()
    if not h or not h["listed"]:
        _BAND_CACHE[key] = None
        return None
    sym = prices.symbol_for(dict(h))
    if not sym:
        _BAND_CACHE[key] = None
        return None
    try:
        kw = {"fetch": fetch} if fetch else {}
        b = prices.band_for(sym, as_of, **kw)
        lo, hi = b.get("pctile_low"), b.get("pctile_high")
        width = ((hi - lo) / 2 * 100) if lo is not None else (config.BAND_SIGMA * b["stdev"] * 100)
        res = (round(width, 4), f"pre-event band on {sym} from {b['sessions_available']} sessions ending {b['reference_date']} "
                                f"(computed at lock, pre-event closes only)")
    except Exception as e:
        res = None
        conn.execute("SELECT 1")     # keep the connection warm; the failure is reported through the caller's basis
        _BAND_CACHE[key] = None
        return None
    _BAND_CACHE[key] = res
    return res


def _expected_move(conn: sqlite3.Connection, round_id: str, position_ids: list[str]) -> tuple[float | None, str]:
    """The event's expected impact on this leg, in per cent, as an estimate independent of the call's own direction.

    Only occurrence calls and implied readings count. An absence call's own expected move is zero by construction, and
    feeding that back in would make A5 circular: every null would eliminate its own leg and the split between
    `eliminated` and `surviving` would be a restatement of the call type rather than a fact about the leg."""
    from .edge import expected_move_from
    if not position_ids:
        return None, "no position on the leg"
    q = ",".join("?" for _ in position_ids)
    # v13, added after §C: the operator's own impact estimate, stated per leg at lock and independent of any call's
    # direction. Without it the tide eliminator had no numerator on 110 of the programme's 195 legs.
    stated = conn.execute(f"SELECT impact_pct, impact_basis FROM leg_claims WHERE round_id = ? AND position_id IN ({q}) "
                          f"AND impact_pct IS NOT NULL ORDER BY rowid DESC LIMIT 1", [round_id, *position_ids]).fetchone()
    if stated:
        return float(stated["impact_pct"]), f"impact stated at lock: {stated['impact_basis']}"
    rows = [dict(r) for r in conn.execute(
        f"SELECT call_type, sign, claim, implied_value, implied_method FROM predictions WHERE round_id = ? AND position_id IN ({q})",
        [round_id, *position_ids])]
    occurrence = [r for r in rows if not (r["call_type"] == "null" or (r["call_type"] == "sign" and r["sign"] == "0"))]
    moves = [m for m in (expected_move_from(r["claim"]) for r in occurrence) if m is not None]
    implied = [r["implied_value"] for r in rows if r["implied_value"] is not None]
    if moves:
        return max(moves), f"largest move named by an occurrence call on the leg ({len(moves)} of {len(occurrence)} name one)"
    if implied:
        return max(implied), "no occurrence call names a move; the implied reading at lock is used instead"
    if rows and not occurrence:
        return None, (f"all {len(rows)} call(s) on this leg are absence calls, whose own expected move is zero: using it "
                      "would make the eliminator a restatement of the call type")
    return None, f"{len(rows)} call(s) on the leg, none naming a per-cent move and none carrying an implied reading"


def _prior_traversal(conn: sqlite3.Connection, round_id: str, holder_id: str, node: str, as_of: str) -> tuple[bool, str]:
    """Did the ledger already carry this holder on this node before the event? Prior admitted rounds first, then dated
    disruption facts on the node naming the holder."""
    r = conn.execute(
        "SELECT e.event_date, e.event_text FROM rounds rd JOIN events e ON e.id = rd.event_id "
        "JOIN round_state s ON s.round_id = rd.id JOIN touched_set t ON t.round_id = rd.id "
        "WHERE s.state != 'void' AND rd.id != ? AND t.holder_id = ? AND lower(t.node) = lower(?) AND e.event_date < ? "
        "ORDER BY e.event_date DESC LIMIT 1", (round_id, holder_id, node, as_of)).fetchone()
    if r:
        return True, f"round on {r['event_date']}: {(r['event_text'] or '')[:80]}"
    f = conn.execute("SELECT source_time, text FROM node_facts WHERE holder_id = ? AND lower(node) = lower(?) "
                     "AND fact_type IN ('outage','closure','incident','strike','force_majeure') AND source_time < ? "
                     "ORDER BY source_time DESC LIMIT 1", (holder_id, node, as_of)).fetchone()
    if f:
        return True, f"dated disruption fact {f['source_time']}: {(f['text'] or '')[:80]}"
    return False, "no earlier round and no dated disruption on this holder and node"


def leg_properties(conn: sqlite3.Connection, round_id: str, leg: dict, as_of: str) -> dict:
    """Everything an eliminator's precondition or test can read. Nothing here is inferred from an outcome."""
    from .db import get_row as _get_row
    from .risk import factor_kind_for
    tag = _round_tag(conn, round_id)
    ev_node = (_get_row(conn, "events", _get_row(conn, "rounds", round_id, "round")["event_id"], "event")["node"] or "")
    traversed, traversed_basis = _prior_traversal(conn, round_id, leg["holder_id"], leg["node"], as_of)
    pids = leg.get("all_position_ids") or leg.get("position_ids") or []
    h = conn.execute("SELECT listed, options_listed, kind FROM holders WHERE id = ?", (leg["holder_id"],)).fetchone()
    share, share_basis = _share(conn, leg["holder_id"], leg["node"])
    hedged, hedged_basis = _self_hedged(conn, leg["holder_id"], leg["node"])
    slack, slack_basis = _slack(conn, leg["node"], as_of)
    band, band_basis = _band_pct(conn, round_id, pids, holder_id=leg["holder_id"], as_of=as_of)
    move, move_basis = _expected_move(conn, round_id, pids)
    ts = conn.execute("SELECT degree, mechanism_ids, leg_source FROM touched_set WHERE round_id = ? AND holder_id = ? "
                      "AND lower(node) = lower(?) ORDER BY rowid DESC LIMIT 1", (round_id, leg["holder_id"], leg["node"])).fetchone()
    mechanisms = loads(ts["mechanism_ids"]) if ts and ts["mechanism_ids"] else (leg.get("mechanism_ids") or [])
    confidences = {r["confidence"] for r in conn.execute(
        "SELECT confidence FROM positions WHERE holder_id = ? AND lower(node) = lower(?)", (leg["holder_id"], leg["node"]))}
    return {
        "factor_kind": factor_kind_for(conn, leg["holder_id"]),
        "degree": leg.get("degree") if leg.get("degree") is not None else (ts["degree"] if ts else None),
        "listed": bool(h["listed"]) if h else False,
        "options_listed": bool(h["options_listed"]) if h else False,
        "q1a": tag["q1a"], "q1b": tag["q1b"], "tag": tag["tag"], "node": leg["node"], "as_of": as_of,
        "class_annotation": _annotation(conn, round_id, leg),
        "origin": (ts["leg_source"] if ts else None),
        "on_event_node": (leg["node"] or "").lower() == ev_node.lower(),
        "prior_traversal": traversed, "prior_traversal_basis": traversed_basis,
        "position_share": share, "position_share_basis": share_basis,
        "self_hedged": hedged, "self_hedged_basis": hedged_basis,
        "slack": slack, "slack_basis": slack_basis,
        "band_pct": band, "band_basis": band_basis,
        "expected_move_pct": move, "expected_move_basis": move_basis,
        "mechanisms": mechanisms, "stated_position": "stated" in confidences,
    }


# ---- preconditions and eliminators ------------------------------------------------------------------------------------

def precondition_holds(name: str, props: dict) -> tuple[bool, str]:
    """§A3: the pre-registered expression over leg properties, evaluated. Never edited to move a leg after the fact."""
    expr = config.ELIMINATOR_PRECONDITION[name]
    if expr == "always":
        return True, expr
    ok = {
        "factor_kind == 'equity'": props["factor_kind"] == "equity",
        "q1a == 'fail'": props["q1a"] == "fail",
        "q1b == 'fail'": props["q1b"] == "fail",
        "factor_kind in ('physical', 'aggregate', 'private')": props["factor_kind"] in ("physical", "aggregate", "private"),
        "position_share is not None": props["position_share"] is not None,
    }.get(expr)
    if ok is None:
        raise ValidationError(f"precondition {expr!r} for eliminator {name!r} has no evaluator")
    return bool(ok), expr


def _tide(props: dict) -> tuple[bool | None, str]:
    """`lib.equity_visibility_ratio`: below a ratio of event size to ambient tide there is no trace to trade."""
    if props["degree"] == 0:
        return False, "the event is about this holder: no tide rule can fire on a company whose own episode is the event"
    move, band = props["expected_move_pct"], props["band_pct"]
    if move is not None and band:
        ratio = move / band
        fired = ratio < config.TIDE_RATIO_MIN
        return fired, (f"expected move {move}% over the leg's own band {band}% is a ratio of {round(ratio, 3)}, "
                       f"{'below' if fired else 'at or above'} the pre-registered {config.TIDE_RATIO_MIN}")
    if band is None and move is None:
        return None, ("neither an expected move nor a band on this leg: the visibility ratio has no numerator and no "
                      f"denominator ({props['expected_move_basis']}; {props['band_basis']})")
    if move is None:
        return None, f"no call on the leg names a move, so the ratio has no numerator ({props['expected_move_basis']})"
    return None, f"no band on the leg, so the ratio has no denominator ({props['band_basis']})"


def _traversed(props: dict) -> tuple[bool | None, str]:
    """`lib.novelty_channels_not_events`: the channel, not the event, is what can be new.

    Q1a is a fact about the *episode*, not about this leg, and firing on it alone would make the eliminator a
    round-level constant — the mirror basket's error one layer down, which is what §A3 exists to prevent. So the test
    is what the ledger can show about this leg: was this holder on this node already carried through an earlier
    instalment. Where the ledger holds no earlier round on the node, we cannot say, and we say that."""
    if props["prior_traversal"]:
        return True, ("the ledger already carried this holder on this node before the event: " + props["prior_traversal_basis"])
    return None, ("Q1a fails, so the episode had an earlier instalment, but the ledger holds no earlier round or dated "
                  "disruption on this holder and node: whether this particular leg was repriced then is unrecorded")


def _weather(props: dict) -> tuple[bool | None, str]:
    """The recurring-disruption finding is about the node Q1b was computed on, not about every node in the round."""
    if props["on_event_node"]:
        return True, "Q1b fails on this node: an incident here is the weather rather than news"
    return False, (f"Q1b fails on the event's node, but this leg sits on {props['node']}, which is not the node the "
                   "recurring-disruption count was computed over")


def _slack_elim(props: dict) -> tuple[bool | None, str]:
    if props["slack"] is None:
        return None, props["slack_basis"]
    return bool(props["slack"]), props["slack_basis"]


def _self_hedged_elim(props: dict) -> tuple[bool | None, str]:
    return bool(props["self_hedged"]), props["self_hedged_basis"]


def _immaterial(props: dict) -> tuple[bool | None, str]:
    share = props["position_share"]
    fired = share is not None and share < config.POSITION_SHARE_FLOOR
    return fired, f"{props['position_share_basis']}; floor {config.POSITION_SHARE_FLOOR}"


def _no_path(props: dict) -> tuple[bool | None, str]:
    """§6.4 admissibility: a path is physical, contractual or accounting, and somebody has to have stated it."""
    if props["degree"] in (0, 1):
        return False, f"degree {props['degree']}: the event reaches this holder directly or through one named step"
    if props["mechanisms"] or props["stated_position"]:
        return False, ("a path is on the ledger: " +
                       (f"{len(props['mechanisms'])} cited mechanism(s)" if props["mechanisms"] else "a stated position on the node"))
    return True, (f"degree {props['degree']} with no cited mechanism and no stated position on the node: the leg exists "
                  "because the store holds an inferred exposure, which is not a path")


TESTS = {"tide": _tide, "traversed": _traversed, "weather": _weather, "slack": _slack_elim,
         "self_hedged": _self_hedged_elim, "immaterial_position": _immaterial, "no_path": _no_path}


# ---- the per-leg record -------------------------------------------------------------------------------------------------

def _annotation(conn: sqlite3.Connection, round_id: str, leg: dict) -> dict | None:
    from .edge import annotations_for
    try:
        return annotations_for(conn, round_id, leg.get("all_position_ids") or [])
    except Exception:
        return None


def evaluate_leg(conn: sqlite3.Connection, round_id: str, leg: dict, as_of: str, rates: dict | None = None) -> dict:
    """v13 A4: surviving risk is a magnitude, not a boolean. v14 A4: and the magnitude is one term of five, kept as a
    vector, because a product cannot tell one wall apart from five mediocre terms."""
    from . import vector as vec_mod
    props = leg_properties(conn, round_id, leg, as_of)
    fired, checked, unevaluable, lines = [], [], [], []
    for name in config.ELIMINATORS:
        holds, expr = precondition_holds(name, props)
        if not holds:
            lines.append(f"{name}: precondition ({expr}) does not hold on this leg")
            continue
        verdict, why = TESTS[name](props)
        if verdict is None:
            unevaluable.append(name)
            lines.append(f"{name}: NOT EVALUABLE - {why}")
            continue
        checked.append(name)
        if verdict:
            fired.append(name)
        lines.append(f"{name}: {'FIRED' if verdict else 'survived'} - {why}")
    survives = not fired
    mag, mag_basis = magnitude(props)
    basis = " | ".join(lines)
    if survives and unevaluable and not checked:
        basis = ("survives only because nothing could be evaluated on it: " + basis)
    v = vec_mod.leg_vector(conn, round_id, leg, props, rates=rates)
    return {"round_id": round_id, "position_id": (leg.get("all_position_ids") or [leg.get("holder_id")])[0],
            "holder_id": leg.get("holder_id"), "node": leg.get("node"), "holder": leg.get("holder"),
            "eliminators_fired": fired, "eliminators_checked": checked, "eliminators_unevaluable": unevaluable,
            "survives": survives, "magnitude": mag, "magnitude_basis": mag_basis, "basis": basis, "as_of": as_of,
            "surviving_but_small": bool(survives and mag is not None and mag < config.SURVIVING_MAGNITUDE_MIN),
            "vector": v, "binding_term": v["binding_term"], "confidence": vec_mod.confidence(v, unevaluable),
            "origin": props.get("origin"), "degree": props.get("degree"),
            "properties": props}


def magnitude(props: dict) -> tuple[float | None, str]:
    """Expected move over implied where an implied reading exists, else over the leg's own ambient band (A4)."""
    move, band = props["expected_move_pct"], props["band_pct"]
    if move is None or not band:
        return None, f"not computable: {props['expected_move_basis']}; {props['band_basis']}"
    return round(move / band, 4), f"expected move {move}% over ambient band {band}%"


def write_leg(conn: sqlite3.Connection, round_id: str, rec: dict, replay: bool = False) -> str:
    prev = conn.execute("SELECT id FROM surviving_risk WHERE round_id = ? AND position_id = ? AND replay = ? "
                        "ORDER BY rowid DESC LIMIT 1", (round_id, rec["position_id"], int(replay))).fetchone()
    row = append(conn, "surviving_risk", {
        "round_id": round_id, "position_id": rec["position_id"], "holder_id": rec["holder_id"], "node": rec["node"],
        "eliminators_fired": dumps(rec["eliminators_fired"]), "eliminators_checked": dumps(rec["eliminators_checked"]),
        "eliminators_unevaluable": dumps(rec["eliminators_unevaluable"]), "survives": int(rec["survives"]),
        "magnitude": rec["magnitude"], "magnitude_basis": rec["magnitude_basis"], "basis": rec["basis"][:4000],
        "as_of": rec["as_of"], "replay": int(replay), "supersedes": prev["id"] if prev else None,
        "vector": dumps(rec.get("vector")) if rec.get("vector") else None, "binding_term": rec.get("binding_term"),
        "confidence": rec.get("confidence"), "origin": rec.get("origin"),
        "proposed_by": rec.get("proposed_by"), "path_basis": (rec.get("properties") or {}).get("prior_traversal_basis")})
    return row["id"]


def assess_round(conn: sqlite3.Connection, round_id: str, as_of: str | None = None, write: bool = True,
                 replay: bool = False) -> dict:
    """Every leg of a round, scored for surviving risk. Written at lock and frozen (§A3); re-runnable as a replay."""
    from .basket import round_legs
    from .rounds import round_state
    state = round_state(conn, round_id)
    if state == "void":
        raise StateError(f"round {round_id} is void")
    rd = get_row(conn, "rounds", round_id, "round")
    ev = get_row(conn, "events", rd["event_id"], "event")
    as_of = as_of or ev["event_date"]
    from . import vector as vec_mod
    rates = vec_mod.operator_rates(conn)
    from .effects import node_kind_of
    out, attribute_legs = [], []
    for leg in round_legs(conn, round_id):
        # v15 §I1: a shared venue, currency, index or size bucket is a loading on the basket, not a leg with a path.
        # It is summed in construction (§H) and never assessed as a position.
        if node_kind_of(conn, leg["node"]) == "attribute":
            attribute_legs.append({"holder": leg["holder"], "node": leg["node"]})
            continue
        rec = evaluate_leg(conn, round_id, leg, as_of, rates=rates)
        if write:
            rec["surviving_risk_id"] = write_leg(conn, round_id, rec, replay=replay)
        out.append(rec)
    surviving = [r for r in out if r["survives"]]
    return {"round_id": round_id, "as_of": as_of, "legs": len(out), "surviving": len(surviving),
            "attribute_legs_excluded": attribute_legs,
            "eliminated": len(out) - len(surviving),
            "surviving_but_small": sum(1 for r in out if r["surviving_but_small"]),
            "by_eliminator": {e: sum(1 for r in out if e in r["eliminators_fired"]) for e in config.ELIMINATORS},
            "unevaluable": {e: sum(1 for r in out if e in r["eliminators_unevaluable"]) for e in config.ELIMINATORS},
            "legs_with_no_evaluable_eliminator": sum(1 for r in out if not r["eliminators_checked"]),
            "magnitudes": sorted([r["magnitude"] for r in out if r["magnitude"] is not None]),
            # v14 A3a: an anchor that cannot be evaluated is absent, and must read as absent
            "unevaluable_rate": {e: (round(sum(1 for r in out if e in r["eliminators_unevaluable"]) / len(out), 4) if out else None)
                                 for e in config.ELIMINATORS},
            "binding_terms": vec_mod.summarise(out),
            "mean_confidence": (round(sum(r["confidence"] for r in out) / len(out), 4) if out else None),
            "clears_appetite": [r["holder"] for r in out if (r["vector"] or {}).get("clears_appetite")],
            "results": [{k: r[k] for k in ("holder", "node", "position_id", "survives", "magnitude", "binding_term",
                                           "confidence", "origin", "degree",
                                           "eliminators_fired", "eliminators_checked", "eliminators_unevaluable")}
                        | {"terms": r["vector"]["terms"], "ratio": r["vector"]["ratio_to_appetite"]} for r in out],
            "replay": replay, "written": write}


def latest_for_round(conn: sqlite3.Connection, round_id: str, replay: bool | None = None) -> dict[str, dict]:
    """position_id -> the standing record, superseded rows dropped."""
    sql = "SELECT * FROM surviving_risk WHERE round_id = ?"
    args: list = [round_id]
    if replay is not None:
        sql += " AND replay = ?"
        args.append(int(replay))
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY rowid", args)]
    superseded = {r["supersedes"] for r in rows if r["supersedes"]}
    out = {}
    for r in rows:
        if r["id"] in superseded:
            continue
        for k in ("eliminators_fired", "eliminators_checked", "eliminators_unevaluable"):
            r[k] = loads(r[k]) if r[k] else []
        r["survives"] = bool(r["survives"])
        out[r["position_id"]] = r
    return out


def survives_leg(conn: sqlite3.Connection, round_id: str, position_ids: list[str]) -> dict | None:
    """A6: what arming reads. None where the round was locked before v13 and has no record."""
    recs = latest_for_round(conn, round_id)
    for pid in position_ids or []:
        if pid in recs:
            return recs[pid]
    return None


# ---- A5: the null breakdown ---------------------------------------------------------------------------------------------

def null_breakdown(conn: sqlite3.Connection, round_id: str | None = None) -> dict:
    """An absence call on a leg where an eliminator fired is a non-position, not a win. Only a null on a leg with
    surviving risk had anything at stake. Reported separately; the score itself is unchanged."""
    from .rounds import list_predictions
    from .scorer import latest_resolutions
    rounds_ = ([round_id] if round_id else
               [r["round_id"] for r in conn.execute("SELECT round_id FROM round_state WHERE state != 'void'")])
    rows = []
    for rid in rounds_:
        recs = latest_for_round(conn, rid)
        if not recs:
            continue
        res = latest_resolutions(conn, rid)
        for p in list_predictions(conn, rid):
            absence = p["call_type"] == "null" or (p["call_type"] == "sign" and p.get("sign") == "0")
            if not absence:
                continue
            rec = recs.get(p.get("position_id")) if p.get("position_id") else None
            r = res.get(p["id"])
            rows.append({"round_id": rid, "prediction_id": p["id"], "target": p["target"], "call_type": p["call_type"],
                         "outcome": (r["outcome"] if r else None),
                         "breakdown": ("surviving" if rec and rec["survives"] else "eliminated" if rec else "unassessed"),
                         "eliminators_fired": (rec["eliminators_fired"] if rec else None),
                         "magnitude": (rec["magnitude"] if rec else None)})
    counts = {b: sum(1 for r in rows if r["breakdown"] == b) for b in ("surviving", "eliminated", "unassessed")}
    hits = {b: sum(1 for r in rows if r["breakdown"] == b and r["outcome"] == "hit") for b in counts}
    return {"rounds": len(rounds_), "absence_calls": len(rows), "counts": counts, "hits": hits,
            "fadeable": [r for r in rows if r["breakdown"] == "surviving"],
            "rows": rows,
            "note": "A5: only a null on a leg with surviving risk is a fadeable null; the rest are non-positions"}
