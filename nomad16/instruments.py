"""The instrument map, cap classes and the cost model (§20.6).

Cap classes: ``hard`` (bought option, bought event contract: maximum loss fixed at
entry), ``stress`` (stock or ETF, long or short, under a stop: maximum loss at the
stress quantile, enforced by the stop). ``uncapped`` instruments are never held and
can't be registered here: a short without a stop or a sold option is converted to a
capped form or dropped.
"""
from __future__ import annotations

from . import config
from .db import DB, Refused
from .util import le, ts

KINDS = {"stock": "stress", "etf": "stress", "call": "hard", "put": "hard", "event_contract": "hard"}
LINEAR = {"stock", "etf"}
OPTION = {"call", "put"}


def instrument_add(db: DB, instrument_id: str, kind: str, symbol: str, listed_from: str,
                   holder_id: str | None = None, venue: str | None = None,
                   underlying: str | None = None, strikes: list | None = None,
                   expiry: str | None = None, multiplier: float = 1.0,
                   ack_id: str | None = None, yes_outcomes: list | None = None,
                   quote_source: str = "yahoo_v8_chart") -> dict:
    if kind not in KINDS:
        raise Refused(f"kind must be one of {sorted(KINDS)}; uncapped forms are never held")
    if not listed_from:
        raise Refused("every instrument records listed_from (§20.6)")
    ts(listed_from)
    if kind in OPTION and (not underlying or not strikes or not expiry):
        raise Refused("an option names its underlying instrument, strike and expiry")
    if kind == "event_contract" and (not ack_id or not yes_outcomes):
        raise Refused("an event contract names its ACK and the outcomes that pay YES")
    if kind in LINEAR and not holder_id:
        raise Refused("a stock or ETF instrument belongs to a holder")
    if holder_id and db.get("holders", holder_id) is None:
        raise Refused(f"no holder {holder_id}")
    return db.upsert("instruments", instrument_id, holder_id=holder_id, ack_id=ack_id,
                     yes_outcomes=yes_outcomes or [], kind=kind, symbol=symbol, venue=venue,
                     listed_from=listed_from, cap_class=KINDS[kind], expiry=expiry,
                     strikes=strikes or [], multiplier=float(multiplier),
                     cost_model_id=kind, quote_source=quote_source, underlying=underlying)


def listed_before(inst: dict, clock: str) -> bool:
    return le(inst["listed_from"], clock) and ts(inst["listed_from"]) < ts(clock)


def unit_cost(inst: dict, price: float, adv_units: float | None, horizon_days: int, short: bool) -> float:
    """Linear per-unit cost: half spread + fee + slippage (at the LIQ_CAP participation) + borrow."""
    kind = "option" if inst["kind"] in OPTION else inst["kind"]
    spread = float(config.get("SPREAD_FALLBACK")[kind]) * price
    fee = float(config.get("FEE_PER_UNIT")[kind])
    slip = float(config.get("SLIPPAGE_COEF")) * float(config.get("LIQ_CAP")) * price
    borrow = float(config.get("BORROW_RATE")) * horizon_days / 365.0 * price if short else 0.0
    # entry and exit each pay half the spread and the slippage
    return 2 * (0.5 * spread + slip) + fee + borrow


def expression_term(view, holder_id: str, clock: str) -> float:
    """1.0 hard-capped instrument, 0.5 stress-capped only, 0.0 none (§20.1). Never a gap."""
    best = 0.0
    for i in view.mut("instruments"):
        if not listed_before(i, clock):
            continue
        linked = i.get("holder_id") == holder_id
        if not linked and i["kind"] in OPTION and i.get("underlying"):
            u = view.mget("instruments", i["underlying"])
            linked = bool(u and u.get("holder_id") == holder_id)
        if linked:
            best = max(best, 1.0 if i["cap_class"] == "hard" else 0.5)
    return best
