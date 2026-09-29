"""v14 §A4/§A5: the risk vector, kept as a vector.

The arming conjunction is retired. Thirteen rounds and zero armed legs did not discover that arming is hard; an AND
over eight predicates specified it to be near-impossible and then measured that it was. And because arming commits no
capital, every predicate cost information and bought nothing.

What replaces it is five terms that are never multiplied together. Five terms at 0.6, and one term at 0.03 with four at
0.95, collapse to the same product and are opposite situations:

* uniformly mediocre — nothing to fix, nothing to route around;
* **one wall** — a fact about a specific thing, which might change, which we might be wrong about, or which a different
  leg routes around entirely.

Every term reads higher-is-better, so appetite is a floor per term and `binding_term` is the term furthest below its
own floor. Nothing is gated on it (§A7): arming still commits no capital, and the point of recording the vector is
that the terms can finally be calibrated against outcomes.

`operator` is computed from the clean ledger and never asserted (§A5). The operator is a component of every leg with a
measurable failure distribution, and it belongs in the engine rather than in a calibration table nobody reads."""
import sqlite3

from . import config
from .util import dumps

TERMS = config.VECTOR_TERMS


# ---- A5: operator risk, computed ------------------------------------------------------------------------------------

def _shape_of(pred: dict, leg_degree: int | None = None) -> dict:
    """The shape of a call, in the modifiers the ledger has shown to matter."""
    from .models import conditional_conjunction, independent_clauses
    claim = pred.get("claim") or ""
    absence = pred["call_type"] == "null" or (pred["call_type"] == "sign" and pred.get("sign") == "0")
    return {"call_type": pred["call_type"],
            "family": "absence" if absence else ("map" if pred["call_type"] == "map" else "occurrence"),
            "settling_document_fetched": bool(pred.get("settling_document_fetched")),
            "base_rate_cited": bool(pred.get("base_rate_id")),
            "claim_is_conjunction": bool(independent_clauses(claim) >= 2 or conditional_conjunction(claim)),
            "degree": leg_degree}


def operator_rates(conn: sqlite3.Connection) -> dict:
    """Hit rates by call family over clean, scored rounds only. Learning rounds never enter this, as they never enter
    rule weights: an operator that has read the aftermath is not a forecaster with a failure rate."""
    from .rounds import list_predictions
    from .scorer import latest_resolutions
    rows = []
    for r in conn.execute("SELECT s.round_id FROM round_state s JOIN rounds rd ON rd.id = s.round_id "
                          "WHERE s.state IN ('scored','partially_scored') AND rd.round_class = 'clean'"):
        rid = r["round_id"]
        res = latest_resolutions(conn, rid)
        for p in list_predictions(conn, rid):
            o = res.get(p["id"])
            if not o or o["outcome"] not in ("hit", "miss"):
                continue
            rows.append({**_shape_of(p), "outcome": o["outcome"]})
    out = {}
    for fam in ("absence", "occurrence", "map"):
        xs = [r for r in rows if r["family"] == fam]
        hits = sum(1 for r in xs if r["outcome"] == "hit")
        out[fam] = {"n": len(xs), "hits": hits, "rate": (round(hits / len(xs), 4) if xs else None)}
    for mod in ("settling_document_fetched", "base_rate_cited", "claim_is_conjunction"):
        for val in (True, False):
            xs = [r for r in rows if r[mod] is val]
            if not xs:
                continue
            out[f"{mod}={val}"] = {"n": len(xs), "hits": sum(1 for r in xs if r["outcome"] == "hit"),
                                   "rate": round(sum(1 for r in xs if r["outcome"] == "hit") / len(xs), 4)}
    out["_n"] = len(rows)
    return out


def operator_term(conn: sqlite3.Connection, preds: list[dict], leg_degree: int | None = None,
                  rates: dict | None = None) -> tuple[float | None, str]:
    """How often the operator is right on this shape of call, smoothed toward 0.5 where the ledger is thin."""
    rates = rates if rates is not None else operator_rates(conn)
    if not preds:
        return None, "no call on this leg yet, so there is no shape to score the operator on"
    shapes = [_shape_of(p, leg_degree) for p in preds]
    parts, notes = [], []
    for sh in shapes:
        base = rates.get(sh["family"]) or {}
        n, hits = base.get("n") or 0, base.get("hits") or 0
        rate = (hits + 0.5 * config.OPERATOR_PRIOR_N) / (n + config.OPERATOR_PRIOR_N)
        note = f"{sh['family']} calls: {hits}/{n} on the clean ledger, smoothed to {round(rate, 3)}"
        if sh["family"] == "map" and not sh["settling_document_fetched"]:
            rate *= 0.5
            note += "; map call with no settling document fetched, and the operator is 0-for-3 on exactly that"
        if sh["claim_is_conjunction"]:
            rate *= 0.7
            note += "; the claim is a conjunction, which has cost a row before"
        if sh["family"] == "occurrence" and not sh["base_rate_cited"]:
            rate *= 0.8
            note += "; occurrence call with no base rate cited"
        parts.append(rate)
        notes.append(note)
    return round(min(parts), 4), " | ".join(notes)


# ---- A4: the five terms -------------------------------------------------------------------------------------------

def stake_term(props: dict) -> tuple[float | None, str]:
    """Is anything at issue at all: the event's impact on this leg over the leg's own pre-event band."""
    move, band = props.get("expected_move_pct"), props.get("band_pct")
    if move is None or not band:
        return None, f"not computable: {props.get('expected_move_basis')}; {props.get('band_basis')}"
    return round(move / band, 4), f"impact {move}% over ambient band {band}%"


def structural_term(conn: sqlite3.Connection, props: dict, leg: dict) -> tuple[float, str]:
    """Is the relation and the sign right: path admissibility, the evidence class of the position, the weight of the
    rules cited on the leg."""
    from .library import resolve_rule
    score, notes = 0.0, []
    if props.get("degree") in (0, 1):
        score += 0.45
        notes.append(f"degree {props.get('degree')}: the event reaches this holder directly or through one named step")
    elif props.get("mechanisms") or props.get("stated_position"):
        score += 0.30
        notes.append("a path is on the ledger, but at degree 2 or worse")
    else:
        notes.append("no admissible path: degree 2 or worse with no cited mechanism and no stated position")
    if props.get("stated_position"):
        score += 0.25
        notes.append("the position on the node is stated, not inferred")
    else:
        score += 0.05
        notes.append("the position is inferred")
    # v15 0b.2: a rule id that will not resolve is not a rule carrying no weight -- it is a citation we cannot read.
    # Swallowing it dropped the row out of the weakest-cited-rule computation and the leg took no penalty at all, so a
    # leg citing nonsense scored as though it had cited nothing and needed nothing. Record it, and treat the leg as
    # no-rule-cited: the bonus is for a rule whose weight can actually be seen.
    ws, unresolved = [], []
    for rid in (props.get("mechanisms") or []):
        try:
            ws.append(resolve_rule(conn, rid)["weight"])
        except Exception as exc:
            unresolved.append(f"{rid} ({type(exc).__name__})")
    if unresolved:
        notes.append(f"rule_unresolved: {'; '.join(unresolved)} -- treated as no rule cited, not as no rule needed")
    if ws and not unresolved:
        w = min(ws)
        score += min(0.30, max(0.0, w / 20.0))
        notes.append(f"weakest cited rule carries weight {round(w, 3)}")
    elif not ws and not unresolved:
        notes.append("no rule cited on the leg")
    return round(min(1.0, score), 4), "; ".join(notes)


def pricedness_term(conn: sqlite3.Connection, props: dict, round_id: str, leg: dict) -> tuple[float | None, str]:
    """Already known, or already in. One term over four pieces of evidence that have been four separate demands for the
    same thing: first traversal, bounded-channel absence, slack, and the existence floor."""
    from .risk import existence_floor_holds, reencode_for_leg
    score, notes = 1.0, []
    if props.get("q1a") == "fail":
        score -= 0.30
        notes.append("Q1a fails: the episode has an earlier instalment, so the channel has been priced once already")
    if props.get("q1b") == "fail" and props.get("on_event_node"):
        score -= 0.25
        notes.append("Q1b fails on this node: incidents here are the weather")
    if props.get("prior_traversal"):
        score -= 0.25
        notes.append("the ledger already carried this holder on this node before the event")
    if props.get("slack"):
        score -= 0.20
        notes.append("the receiving market has slack, so there is nothing for a move to transmit into")
    # A re-encode is a fact about the holder's instrument, not about one (holder, node) row: the same equity cannot be
    # unpriced on one node and priced on another. Round 10's filer had two node rows and only one of them saw it, which
    # let the other clear appetite -- the exact failure §D2 says to stop and report on.
    pids = list(leg.get("all_position_ids") or [])
    if leg.get("holder_id"):
        pids += [r["id"] for r in conn.execute(
            "SELECT DISTINCT po.id FROM positions po WHERE po.holder_id = ?", (leg["holder_id"],))]
    if pids:
        ev_date = props.get("as_of")
        try:
            re_ = reencode_for_leg(conn, round_id, sorted(set(pids)), ev_date, None)
            if re_["reencode_date"] and (re_["latency_days"] or 0) <= 1:
                # catastrophic, not a deduction: it was in the price before it was knowable to us, and a conjunction
                # would have armed this leg on the strength of everything else
                score = min(score, 0.05)
                notes.append(f"re-encoded at latency {re_['latency_days']} on this holder's instrument: it was in the "
                             "price before it was knowable to us, which is not a discount but a wall")
            elif re_["reencode_date"]:
                score -= 0.25
                notes.append(f"re-encoded at latency {re_['latency_days']}")
        except Exception as exc:
            # v15 0b.1: this lookup is the only thing that fires the D2 wall. Swallowing it left pricedness at its
            # higher score, so the single failure mode the vector exists to catch could pass a leg in silence. No
            # load-bearing computation swallows an exception: the term reads unevaluable and can never pass.
            return None, "; ".join(notes + [
                f"unevaluable: the re-encode lookup failed ({type(exc).__name__}: {exc}), and the D2 wall is the "
                "thing this term is for -- an unread wall is not an absent one"])
    ann = props.get("class_annotation")
    if ann and ann.get("fact_holder_class") == ann.get("price_setter_class"):
        score -= 0.20
        notes.append("the class holding the fact is the class that marks the instrument: nobody has to be told")
    if not notes:
        notes.append("nothing on the ledger says this is already known or already in")
    return round(max(0.0, score), 4), "; ".join(notes)


def expression_term(conn: sqlite3.Connection, props: dict, round_id: str, leg: dict) -> tuple[float, str]:
    """Can it be held: an instrument exists, the band is reliable, the series clears the turnover floor, and something
    dates it."""
    score, notes = 0.0, []
    if props.get("listed"):
        score += 0.45
        notes.append("listed: an instrument exists")
    else:
        notes.append("unlisted: nothing to hold, whatever the analysis says")
    if props.get("options_listed"):
        score += 0.15
        notes.append("options listed, so vol is expressible too")
    pids = leg.get("all_position_ids") or []
    if pids:
        q = ",".join("?" for _ in pids)
        row = conn.execute(f"SELECT band_reliable, COUNT(*) AS n FROM price_observations WHERE round_id = ? AND position_id IN ({q})",
                           [round_id, *pids]).fetchone()
        if row and row["n"]:
            if row["band_reliable"] == 0:
                notes.append("the band is below the turnover floor: out-of-band carries no information here")
            else:
                score += 0.25
                notes.append("a banded series exists and clears the turnover floor")
        else:
            notes.append("no banded observation on the leg yet")
    if props.get("band_pct"):
        score += 0.15
        notes.append("the pre-event band is computable")
    return round(min(1.0, score), 4), "; ".join(notes)


# ---- the vector -----------------------------------------------------------------------------------------------------

def leg_vector(conn: sqlite3.Connection, round_id: str, leg: dict, props: dict, preds: list[dict] | None = None,
               rates: dict | None = None) -> dict:
    """The five terms, the binding term, and the distance from appetite. Never a product."""
    preds = preds if preds is not None else _preds_for(conn, round_id, leg)
    stake, stake_b = stake_term(props)
    structural, structural_b = structural_term(conn, props, leg)
    priced, priced_b = pricedness_term(conn, props, round_id, leg)
    op, op_b = operator_term(conn, preds, props.get("degree"), rates)
    expr, expr_b = expression_term(conn, props, round_id, leg)
    values = {"stake": stake, "structural": structural, "pricedness": priced, "operator": op, "expression": expr}
    bases = {"stake": stake_b, "structural": structural_b, "pricedness": priced_b, "operator": op_b, "expression": expr_b}
    shortfalls = {t: (None if values[t] is None else round(values[t] - config.APPETITE[t], 4)) for t in TERMS}
    ratios = {t: (None if values[t] is None else round(values[t] / config.APPETITE[t], 4)) for t in TERMS}
    scored = {t: r for t, r in ratios.items() if r is not None}
    unknown = [t for t in TERMS if values[t] is None]
    lowest = min(scored, key=lambda t: scored[t]) if scored else None
    # v15 0b.5: `binding = min(scored)` ranked over the terms that happen to have a value, so a leg whose stake was
    # unknown reported as binding on structural or expression. That is what produced v14 B2's headline -- structural
    # 51%, expression 43%, stake 2.7% -- while stake was uncomputable on 217 of 225 legs. An unknown term's ratio
    # could be anything from zero upward, so wherever it could bind below the lowest computable one, the honest
    # answer is that the binding term is not known. `lowest_computable_term` is kept beside it as information, never
    # as the answer.
    could_bind_lower = bool(unknown) and (not scored or scored[lowest] > 0.0)
    binding = "unassessable" if could_bind_lower else lowest
    named = binding if binding in TERMS else None
    return {"terms": values, "bases": bases, "appetite": dict(config.APPETITE), "shortfall": shortfalls,
            "ratio_to_appetite": ratios, "binding_term": binding,
            "binding_value": (values[named] if named else None),
            "binding_basis": (bases[named] if named else
                              ("the binding term cannot be named: " + ", ".join(unknown) + " unknown, and an unknown "
                               "term can bind below every computable one" if could_bind_lower else None)),
            "lowest_computable_term": lowest,
            "lowest_computable_ratio": (scored[lowest] if lowest else None),
            "clears_appetite": (bool(scored) and all(v >= 1.0 for v in scored.values()) and not unknown),
            "unknown_terms": unknown,
            "note": ("kept as a vector on purpose: the terms are never multiplied, because one wall and five mediocre "
                     "terms are opposite situations that a product cannot tell apart")}


def _preds_for(conn: sqlite3.Connection, round_id: str, leg: dict) -> list[dict]:
    from .rounds import list_predictions
    pids = set(leg.get("all_position_ids") or [])
    return [p for p in list_predictions(conn, round_id) if p.get("position_id") in pids]


def confidence(vec: dict, unevaluable: list[str]) -> float:
    """A3a: an anchor that cannot be evaluated is not constraining anything. It discounts confidence in the assessment
    rather than passing or failing the leg."""
    n_unknown = len(vec.get("unknown_terms") or []) + len(unevaluable or [])
    return round(max(0.0, 1.0 - 0.12 * n_unknown), 4)


def summarise(rows: list[dict]) -> dict:
    """B2: the distribution of binding terms over a set of assessed legs.

    v15 0b.5: legs whose binding term is unassessable are their own bucket and are never attributed to whichever
    computable term happens to bind lowest. `uncomputable` counts, per term, how often the ledger had no value at
    all -- which is the number v14 B2 should have led with."""
    out = {t: 0 for t in TERMS}
    out["unassessable"] = 0
    out["none"] = 0
    uncomputable = {t: 0 for t in TERMS}
    lowest = {t: 0 for t in TERMS}
    for r in rows:
        v = r.get("vector") or {}
        b = v.get("binding_term")
        out[b if b in out else "none"] += 1
        for t in (v.get("unknown_terms") or []):
            if t in uncomputable:
                uncomputable[t] += 1
        lc = v.get("lowest_computable_term")
        if lc in lowest:
            lowest[lc] += 1
    out["uncomputable"] = uncomputable
    out["lowest_computable"] = lowest
    out["n"] = len(rows)
    return out
