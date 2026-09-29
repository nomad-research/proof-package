"""The K7 ownership and instrument census (§27.2 ``nomad_census``, §31 K7).

For an unlisted holder: is there a listed equity or bond that carries it as a *concentrated* share of the
instrument's exposure? Rules and the find criterion are in ``lookbacks/K7_prereg.md``. Control alone (parent,
majority owner) is not a find; only a concentration figure at or above ``CENSUS_CONCENTRATION_PCT`` is.
The pass share ``K7_SHARE`` is Rob's and isn't in the appetite file until he sets it: until then this
reports counts and refuses to state a verdict.
"""
from __future__ import annotations

from . import config
from .db import DB, Refused
from .util import ts

RELATIONS = {"listed_parent", "majority_owner", "sole_customer", "major_customer", "lender", "bond_issuer",
             "other"}
STATUS = {"found", "unquantified_control", "not_found", "unresolved"}


def census_add(db: DB, holder_key: str, holder_name: str, status: str, knowable_from: str,
               earliest_event_date: str, instrument_symbol: str | None = None,
               instrument_kind: str | None = None, relation: str | None = None,
               concentration_pct: float | None = None, basis: str = "", source_document: str | None = None) -> dict:
    """One census row. ``found`` needs an instrument, a relation, a source and a concentration at or above the
    threshold; the threshold is read from the appetite file (``CENSUS_CONCENTRATION_PCT``)."""
    if status not in STATUS:
        raise Refused(f"status is one of {sorted(STATUS)}")
    if not basis:
        raise Refused("a census row states its basis")
    ts(knowable_from)
    ts(earliest_event_date)
    if status in {"found", "unquantified_control"}:
        if not (instrument_symbol and relation and source_document):
            raise Refused("a find names the instrument, the relation and the source document")
        if instrument_kind not in {"equity", "bond"}:
            raise Refused("instrument_kind is equity or bond")
        if relation not in RELATIONS:
            raise Refused(f"relation is one of {sorted(RELATIONS)}")
        if ts(knowable_from) > ts(earliest_event_date):
            raise Refused("the source became public after the earliest event the holder appears in: not a find "
                          "(time guard); record it as not_found or unresolved")
    if status == "found":
        thr = float(config.get("CENSUS_CONCENTRATION_PCT"))
        if concentration_pct is None or float(concentration_pct) < thr:
            raise Refused(f"a find needs a concentration figure of at least {thr}%; control alone is recorded as "
                          f"unquantified_control")
    n = len(db.rows("census_rows")) + 1
    return db.append("census_rows", census_id=f"K7-{n:03d}", holder_key=holder_key, holder_name=holder_name,
                     instrument_symbol=instrument_symbol, instrument_kind=instrument_kind, relation=relation,
                     concentration_pct=concentration_pct, concentrated=status == "found", basis=basis,
                     source_document=source_document, knowable_from=knowable_from,
                     earliest_event_date=earliest_event_date, status=status)


def census(db: DB, candidates: int | None = None) -> dict:
    """The census so far, per holder (best status wins), and the K7 share against ``K7_SHARE`` if it is set."""
    order = {"found": 3, "unquantified_control": 2, "unresolved": 1, "not_found": 0}
    best: dict[str, dict] = {}
    for r in db.rows("census_rows"):
        cur = best.get(r["holder_key"])
        if cur is None or order[r["status"]] > order[cur["status"]]:
            best[r["holder_key"]] = r
    n = len(best)
    denom = candidates or n
    by = {k: sum(1 for r in best.values() if r["status"] == k) for k in order}
    finds = [r for r in best.values() if r["status"] == "found"]
    rel = {}
    for r in finds:
        rel[r["relation"]] = rel.get(r["relation"], 0) + 1
    out = {"holders_censused": n, "denominator": denom, "by_status": by,
           "share_found": round(by["found"] / denom, 3) if denom else None, "finds_by_relation": rel,
           "finds_with_figure": sum(1 for r in finds if r["concentration_pct"] is not None)}
    try:
        share = float(config.get("K7_SHARE"))
    except config.MissingAppetite:
        out["verdict"] = "not stated: K7_SHARE is unset. Rob sets it in a dated commit before the census starts"
        return out
    if candidates and n < candidates:
        out["verdict"] = f"incomplete: {n} of {candidates} candidates censused"
    else:
        out["verdict"] = ("K7 lives: share found meets K7_SHARE" if out["share_found"] >= share
                          else "K7 dies: share found is below K7_SHARE; close the equity thesis, move to shapes B and C")
    out["K7_SHARE"] = share
    return out
