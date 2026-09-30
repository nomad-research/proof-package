"""Exact payoffs for event contracts (Polymarket frame, proposed D33; V1 pre-registration ``lookbacks/polymarket/V1_prereg.md``).

An event contract pays 1 per share in the states where its condition holds and 0 in the others, so a basket's payoff in every state is arithmetic:
there is nothing to estimate. What is left uncertain is **the declared reachable set** (which combinations of outcomes a thesis claims cannot occur) and
resolution risk, both typed and tested elsewhere. This module holds the pure parts: the fee model, the all-in cost of a share, the state space and payoff
vectors, and the maximin floor. It reads no prices and writes nothing; the harness expresses a thesis by passing prices in (price is attentional, R6).

Fees are read from each market's own ``feeSchedule``, never assumed by category. The form used is ``shares x rate x (p (1 - p)) ** exponent``, taker only when
``takerOnly`` is true; the exponent's placement is **unverified against real fills** and must be checked against recorded trades before any live money.
"""
from __future__ import annotations

import itertools
import math
from typing import Callable

import numpy as np
from scipy.optimize import linprog

from .db import Refused

GAP = "__gap__"          # the winner is none of the named slots (an 'Other' or placeholder slot): a typed gap, never a zero


def fee_per_share(price: float, schedule: dict | None, taker: bool = True) -> float:
    """Fee on one share traded at ``price``. No schedule, no rate, or a maker trade under ``takerOnly``: zero."""
    if not schedule or not schedule.get("rate"):
        return 0.0
    if schedule.get("takerOnly", True) and not taker:
        return 0.0
    return float(schedule["rate"]) * (price * (1.0 - price)) ** float(schedule.get("exponent", 1))


def entry_price(price: float, slippage: float = 0.0, tick: float | None = None) -> float:
    """Price actually paid: the quote plus slippage, rounded up to the tick, never above 0.99."""
    e = price + slippage
    if tick:
        e = math.ceil(e / tick - 1e-9) * tick
    return min(e, 0.99)


def share_cost(price: float, schedule: dict | None, slippage: float = 0.0, tick: float | None = None) -> float:
    """All-in cost of one share bought and held to resolution: entry price plus the taker fee at that price (resolution itself pays no fee)."""
    e = entry_price(price, slippage, tick)
    return e + fee_per_share(e, schedule)


class StateSpace:
    """The joint states of several independent structures. ``components`` maps a name to its list of states; the joint space is their product.

    Partition: ``partition_states(slots, open_slot)``. Terminal ladder of n rungs: ``count_states(n)`` (how many rungs were exceeded), and the contract 'above rung i'
    pays when the count is greater than i. Touch ladders are two components, one for the reach side and one for the dip side, each nested on its own.
    """

    def __init__(self, components: dict[str, list]):
        if not components:
            raise Refused("a state space needs at least one component")
        self.names = list(components)
        self.components = components
        self.states = [dict(zip(self.names, combo)) for combo in itertools.product(*components.values())]

    def vec(self, comp: str, pred: Callable, side: str = "YES") -> np.ndarray:
        """Payoff vector over the joint states of one contract: 1 where ``pred`` holds for that component's state (YES), 1 where it does not (NO)."""
        if comp not in self.components:
            raise Refused(f"no component {comp!r}")
        if side not in ("YES", "NO"):
            raise Refused("side is YES or NO")
        yes = np.array([1.0 if pred(s[comp]) else 0.0 for s in self.states])
        return yes if side == "YES" else 1.0 - yes

    def mask(self, excluded: list[Callable[[dict], bool]] | None = None) -> np.ndarray:
        """True for the states that stay reachable after the thesis's claims that some combinations cannot occur."""
        excluded = excluded or []
        return np.array([not any(f(s) for f in excluded) for s in self.states])

    def index(self, state: dict) -> int:
        return self.states.index(state)


def partition_states(slots: list[str], open_slot: bool = False) -> list[str]:
    if len(set(slots)) != len(slots) or len(slots) < 2:
        raise Refused("a partition has at least two distinct slots")
    return list(slots) + ([GAP] if open_slot else [])


def count_states(n: int) -> list[int]:
    return list(range(n + 1))


def maximin(p_vec: np.ndarray, p_cost: float, p_budget: float, cands: list[dict], h_budget: float, mask: np.ndarray, ncap: int | None = None) -> dict:
    """Weights on hedge contracts that maximise the worst payoff over the reachable states.

    The primary is fixed: ``p_budget`` dollars of it at ``p_cost`` per share (fixing it is what stops the program from shrinking the primary to nothing).
    ``cands`` are dicts with ``vec`` (payoff vector), ``cost`` (all-in per share) and any labels. The hedge budget is ``h_budget``. Net payoff in a state is
    shares paid out less everything spent. Ties are broken by the lowest spend. With ``ncap``, the largest ``ncap`` weights are kept and the program re-solved.
    """
    if not mask.any():
        raise Refused("the reachable set is empty")
    n_p = p_budget / p_cost
    base = n_p * p_vec[mask] - p_budget
    floor_p = float(base.min())
    if not cands or h_budget <= 0:
        return {"weights": [], "floor": floor_p, "floor_primary_alone": floor_p, "lift": 0.0, "spend": 0.0, "primary_shares": n_p}

    def solve(cs: list[dict]) -> tuple[np.ndarray, float]:
        A = np.array([c["vec"][mask] for c in cs]).T
        cost = np.array([c["cost"] for c in cs])
        m = A.shape[0]
        # net(s) = base(s) + A x - cost.x >= t   ->   -(A - cost) x + t <= base
        A_ub = np.vstack([np.c_[-(A - cost), np.ones(m)], np.r_[cost, 0.0]])
        b_ub = np.r_[base, h_budget]
        bounds = [(0, None)] * len(cs) + [(None, None)]
        r = linprog(np.r_[np.zeros(len(cs)), -1.0], A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        if not r.success:
            raise Refused(f"the floor program failed: {r.message}")
        t = float(r.x[-1])
        # tie-break: same floor, least spend
        A_ub2 = np.vstack([np.c_[-(A - cost), np.zeros(m)], np.r_[cost, 0.0]])
        b_ub2 = np.r_[base - t + 1e-9, h_budget]
        r2 = linprog(np.r_[cost, 0.0], A_ub=A_ub2, b_ub=b_ub2, bounds=[(0, None)] * len(cs) + [(None, None)], method="highs")
        x = r2.x[:len(cs)] if r2.success else r.x[:len(cs)]
        return x, t

    x, t = solve(cands)
    if ncap is not None and (x > 1e-9).sum() > ncap:
        keep = list(np.argsort(-x)[:ncap])
        cands = [cands[i] for i in keep]
        x, t = solve(cands)
    if t < floor_p - 1e-9:          # holding no hedge is always feasible, so the program cannot do worse than that
        x, t = np.zeros(len(cands)), floor_p
    weights = [{**{k: v for k, v in c.items() if k != "vec"}, "shares": float(xi)} for c, xi in zip(cands, x) if xi > 1e-9]
    spend = float(sum(w["shares"] * w["cost"] for w in weights))
    return {"weights": weights, "floor": float(t), "floor_primary_alone": floor_p, "lift": float(t) - floor_p, "spend": spend, "primary_shares": n_p}


def equal_floor_outlay(p_vec: np.ndarray, p_cost: float, target_floor: float, mask: np.ndarray, cap: float = 100.0) -> float:
    """Dollars of the primary alone (the rest in cash) whose floor over the reachable states equals ``target_floor``: the plain de-risking comparator."""
    k = float((p_vec[mask] / p_cost - 1.0).min())        # floor per dollar of outlay
    if k >= 0:
        return cap
    return float(min(cap, max(0.0, target_floor / k)))


def realised(p_shares: float, p_cost: float, p_won: float, weights: list[dict], p_outlay: float | None = None) -> float:
    """Net payoff from the resolved outcomes: what the shares paid, less everything spent. ``won`` is 1 or 0 per contract, read from resolution."""
    spent = (p_shares * p_cost if p_outlay is None else p_outlay) + sum(w["shares"] * w["cost"] for w in weights)
    return p_shares * p_won + sum(w["shares"] * w["won"] for w in weights) - spent
