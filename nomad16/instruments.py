"""The instrument map, cap classes and the cost model (§20.6).

Cap classes: ``hard`` (bought option, bought event contract: maximum loss fixed at
entry), ``stress`` (stock or ETF, long or short, under a stop: maximum loss at the
stress quantile, enforced by the stop). ``uncapped`` instruments are never held and
can't be registered here: a short without a stop or a sold option is converted to a
capped form or dropped.
"""
from __future__ import annotations

from . import config
from . import exact
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


SLOT_KINDS = {"named", "placeholder", "other"}


def event_contract_meta_add(db: DB, instrument_id: str, condition_id: str, token_id: str, side: str, event_id: str | None = None,
                            neg_risk: bool = False, tick_size: float = 0.01, min_size: float = 5.0,
                            fee_schedule: dict | None = None, slot_kind: str = "named") -> dict:
    """The venue's own attributes of an event-contract instrument. Keyed by condition and token id, never by question text (several markets can share one text).
    ``slot_kind`` 'placeholder' or 'other' marks a slot whose winner is not pinned down: the state space carries it as a typed gap. ``fee_schedule`` is the
    market's own ``feeSchedule`` as read; None means the market charges no fee (never a category default)."""
    inst = db.get("instruments", instrument_id)
    if inst is None or inst["kind"] != "event_contract":
        raise Refused(f"{instrument_id} is not an event_contract instrument")
    if side not in ("YES", "NO"):
        raise Refused("side is YES or NO")
    if slot_kind not in SLOT_KINDS:
        raise Refused(f"slot_kind must be one of {sorted(SLOT_KINDS)}")
    if not condition_id or not token_id:
        raise Refused("an event contract names its condition id and token id")
    if tick_size <= 0 or min_size <= 0:
        raise Refused("tick size and minimum size are positive")
    return db.upsert("event_contract_meta", instrument_id, condition_id=condition_id, token_id=token_id, side=side, event_id=event_id,
                     neg_risk=bool(neg_risk), tick_size=float(tick_size), min_size=float(min_size), fee_schedule=fee_schedule or None, slot_kind=slot_kind)


def listed_before(inst: dict, clock: str) -> bool:
    return le(inst["listed_from"], clock) and ts(inst["listed_from"]) < ts(clock)


def unit_cost(inst: dict, price: float, adv_units: float | None, horizon_days: int, short: bool,
              meta: dict | None = None, hold_to_resolution: bool = False) -> float:
    """Linear per-unit cost: half spread + fee + slippage (at the LIQ_CAP participation) + borrow.

    An event contract with its venue attributes (``meta``) pays the market's own nonlinear taker fee, shares x rate x p(1 - p), at the price traded; held to
    resolution it has one leg (resolution pays $1 with no exit trade), otherwise two."""
    kind = "option" if inst["kind"] in OPTION else inst["kind"]
    spread = float(config.get("SPREAD_FALLBACK")[kind]) * price
    slip = float(config.get("SLIPPAGE_COEF")) * float(config.get("LIQ_CAP")) * price
    if inst["kind"] == "event_contract" and meta is not None:
        legs = 1 if hold_to_resolution else 2
        return legs * (0.5 * spread + slip + exact.fee_per_share(price, meta.get("fee_schedule")))
    fee = float(config.get("FEE_PER_UNIT")[kind])
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
