"""The paper book (§19.2). Nothing is traded; every built basket is booked at lock.

Fills: backfilled rounds take the first close after the fact was public
(``backfill_first_close``); options are ``modelled`` from the underlying's vintage
price and never count toward K13. Marks at ACK firings and on schedule. A basket exits
at the first of S⊥ recovered, the first attention ACK, the window end, or a stop.

``result = narrowing + timing + residual − costs − leaks`` (attribution fixed in
``config/appetite.json`` ATTRIBUTION before the first lock).
"""
from __future__ import annotations

import datetime as _dt
import math

import numpy as np

from . import config, prices
from .construct import bs
from .db import DB, Refused
from .rounds import get_round, meta, state
from .util import day, ts
from .view import View


def _inst(view, key):
    i = view.mget("instruments", key)
    if i is None:
        raise Refused(f"no instrument {key}")
    return i


def _ensure_prices(db: DB, symbol: str, upto: str):
    """Post-lock only: fetch a vintage up to (and including) a date, never past it."""
    view = View(db)
    fr = prices.frame(view, symbol)
    if not fr.empty and fr.index[-1] >= day(upto):
        return
    start = (ts(upto) - _dt.timedelta(days=700)).strftime("%Y-%m-%d")
    ceiling = (ts(upto) + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    prices.fetch_yahoo(db, symbol, start, day(upto), ceiling=ceiling)


def _positions(db, round_id):
    bids = [b["basket_id"] for b in db.rows("constructed_baskets", "round_id=? AND status='built'", (round_id,))]
    return [p for p in db.rows("paper_positions") if p["basket_id"] in bids]


def _open(db, round_id):
    exited = {e["paper_id"] for e in db.rows("paper_exits")}
    return [p for p in _positions(db, round_id) if p["paper_id"] not in exited]


def _entry_time(db, basket_id):
    b = db.one("constructed_baskets", "basket_id=?", (basket_id,))
    rnd = get_round(db, b["round_id"])
    seg = db.one("segments", "round_id=? AND idx=?", (b["round_id"], b["segment_idx"]))
    if int(b["segment_idx"]) == 0:
        return meta(db, b["round_id"], "knowable_from") or rnd["event_date"]
    return seg["clock"]


def fill(db: DB, round_id: str) -> dict:
    st = state(db, round_id)
    if st not in {"walking", "live", "scored"}:
        raise Refused("fills are written after lock")
    out = []
    filled = {f["paper_id"] for f in db.rows("paper_fills")}
    for p in _positions(db, round_id):
        if p["paper_id"] in filled:
            continue
        view = View(db)
        inst = _inst(view, p["instrument_id"])
        kf = _entry_time(db, p["basket_id"])
        sym = inst["symbol"] if inst["kind"] not in {"call", "put"} else _inst(view, inst["underlying"])["symbol"]
        first = prices.next_session_after(view, sym, kf)
        if first[0] is None:
            probe = (ts(kf) + _dt.timedelta(days=6)).strftime("%Y-%m-%d")
            _ensure_prices(db, sym, probe)
            view = View(db)
            first = prices.next_session_after(view, sym, kf)
        d, px = first
        if d is None:
            out.append({"paper_id": p["paper_id"], "status": "no price yet"})
            continue
        if ts(d) < ts(day(kf)):
            raise Refused("a backfilled fill may never use a price from before the fact was public (smoke 26)")
        er = p["exit_rules"]
        if inst["kind"] in {"call", "put"}:
            optm = config.get("OPTION_PRICING_MODEL")
            u = _inst(view, inst["underlying"])
            r = prices.returns(view, u["symbol"], before=d, n=int(config.get("LOADING_SESSIONS")))
            vol = float(np.std(r.values, ddof=1)) * math.sqrt(252)
            T = max((ts(inst["expiry"]) - ts(d)).days, 0) / 365.0
            px = bs(px, float(inst["strikes"][0]), T, vol, float(optm["rate"]), inst["kind"])
        cost = float(er.get("unit_cost") or 0.0) / 2 * float(p["qty"])
        db.append("paper_fills", paper_id=p["paper_id"], at=d, price=px, vintage_id=None, cost=cost)
        out.append({"paper_id": p["paper_id"], "at": d, "price": px, "entry_rule": p["entry_rule"]})
    return {"fills": out}


def _fill(db, pid):
    return db.one("paper_fills", "paper_id=?", (pid,))


def _price_at(db, inst, d):
    view = View(db)
    if inst["kind"] in {"call", "put"}:
        u = _inst(view, inst["underlying"])
        _ensure_prices(db, u["symbol"], d)
        view = View(db)
        dd, S = prices.last_before(view, u["symbol"], (ts(d) + _dt.timedelta(days=1)).strftime("%Y-%m-%d"))
        optm = config.get("OPTION_PRICING_MODEL")
        r = prices.returns(view, u["symbol"], before=dd, n=int(config.get("LOADING_SESSIONS")))
        vol = float(np.std(r.values, ddof=1)) * math.sqrt(252)
        T = max((ts(inst["expiry"]) - ts(dd)).days, 0) / 365.0
        return dd, bs(S, float(inst["strikes"][0]), T, vol, float(optm["rate"]), inst["kind"])
    _ensure_prices(db, inst["symbol"], d)
    view = View(db)
    return prices.last_before(view, inst["symbol"], (ts(d) + _dt.timedelta(days=1)).strftime("%Y-%m-%d"))


def mark(db: DB, round_id: str, at: str, trigger: str = "scheduled") -> dict:
    """Mark every open position at the close on/before ``at``; stress positions check their stop."""
    if trigger not in {"ack_fired", "scheduled", "exit_check"}:
        raise Refused("trigger is ack_fired, scheduled or exit_check")
    fill(db, round_id)
    out, stopped = [], set()
    view = View(db)
    for p in _open(db, round_id):
        f = _fill(db, p["paper_id"])
        if f is None:
            continue
        inst = _inst(view, p["instrument_id"])
        d, px = _price_at(db, inst, at)
        if d is None or ts(d) < ts(f["at"]):
            continue
        db.append("paper_marks", paper_id=p["paper_id"], at=d, price=px, vintage_id=None, trigger=trigger)
        mult = float(inst.get("multiplier") or 1.0)
        unreal = int(p["side"]) * float(p["qty"]) * (px - float(f["price"])) * mult
        out.append({"paper_id": p["paper_id"], "at": d, "price": px, "unrealised": unreal})
        er = p["exit_rules"]
        if er.get("stop") and unreal <= -float(er.get("stress_max_loss") or 0.0):
            stopped.add(p["basket_id"])
    for bid in sorted(stopped):
        out.append({"basket_id": bid, "exit": exit_basket(db, bid, at, "stop")})
    return {"marks": out}


def _factor_move(db, story_key, start, end, clock):
    """Realised move of a hedged factor in its own daily-sd units, from start to end."""
    view = View(db)
    if story_key == "tide":
        return None
    s = view.mget("stories", story_key)
    if not s or not s.get("proxy"):
        return None
    moves, sds = [], []
    for sym in s["proxy"]:
        _ensure_prices(db, sym, end)
        view = View(db)
        r = prices.returns(view, sym, before=(ts(end) + _dt.timedelta(days=1)).strftime("%Y-%m-%d"))
        pre = r[r.index < day(clock)].iloc[-int(config.get("LOADING_SESSIONS")):]
        hold = r[(r.index > day(start)) & (r.index <= day(end))]
        sds.append(float(np.std(pre.values, ddof=1)))
        moves.append(float(hold.sum()))
    sd = float(np.mean(sds)) if sds else 0.0
    return float(np.mean(moves)) / sd if sd > 0 else None


def exit_basket(db: DB, basket_id: str, at: str, reason: str) -> dict:
    reasons = {"s_perp_recovered", "attention_ack", "window_end", "stop", "void"}
    if reason not in reasons:
        raise Refused(f"exit reason is one of {sorted(reasons)}")
    b = db.one("constructed_baskets", "basket_id=?", (basket_id,))
    if b is None:
        raise Refused(f"no basket {basket_id}")
    fill(db, b["round_id"])
    view = View(db)
    exited = {e["paper_id"] for e in db.rows("paper_exits")}
    tide_id = b["tide_id"]
    tide = view.mget("tides", tide_id) or {}
    total = {"gross": 0.0, "costs": 0.0, "hedge_pnl": 0.0}
    rows = []
    for p in [p for p in db.rows("paper_positions", "basket_id=?", (basket_id,)) if p["paper_id"] not in exited]:
        f = _fill(db, p["paper_id"])
        inst = _inst(view, p["instrument_id"])
        if f is None:
            continue
        d, px = _price_at(db, inst, at)
        mult = float(inst.get("multiplier") or 1.0)
        gross = int(p["side"]) * float(p["qty"]) * (px - float(f["price"])) * mult
        costs = float(f["cost"] or 0.0) + float(p["exit_rules"].get("unit_cost") or 0.0) / 2 * float(p["qty"])
        seg_clock = _entry_time(db, basket_id)
        hedge = 0.0
        for k, a in (p["exit_rules"].get("loadings") or {}).items():
            if k == "tide":
                sym = tide.get("proxy")
                if not sym:
                    continue
                _ensure_prices(db, sym, d)
                v2 = View(db)
                r = prices.returns(v2, sym, before=(ts(d) + _dt.timedelta(days=1)).strftime("%Y-%m-%d"))
                pre = r[r.index < day(seg_clock)].iloc[-int(config.get("LOADING_SESSIONS")):]
                hold = r[(r.index > day(f["at"])) & (r.index <= day(d))]
                sd = float(np.std(pre.values, ddof=1))
                mv = float(hold.sum()) / sd if sd > 0 else 0.0
            else:
                mv = _factor_move(db, k, f["at"], d, seg_clock) or 0.0
            hedge += float(p["qty"]) * float(a) * mv
        split = {"narrowing": 0.0, "timing": 0.0, "costs": costs, "leaks": -hedge,
                 "residual": gross - hedge}
        pnl = gross - costs
        db.append("paper_exits", paper_id=p["paper_id"], basket_id=basket_id, at=d, price=px, reason=reason,
                  pnl=pnl, split=split)
        total["gross"] += gross
        total["costs"] += costs
        total["hedge_pnl"] += hedge
        rows.append({"paper_id": p["paper_id"], "at": d, "price": px, "pnl": pnl, "split": split})
    result = total["gross"] - total["costs"]
    residual = total["gross"] - total["hedge_pnl"]
    only_through_leaks = result > 0 and (residual - total["costs"]) <= 0
    db.append("basket_status", basket_id=basket_id, status="closed",
              reason=f"{reason}; result {result:.2f}" + ("; positive only through leaks: counts as a loss for K13"
                                                         if only_through_leaks else ""))
    return {"basket_id": basket_id, "reason": reason, "result": result,
            "split": {"narrowing": 0.0, "timing": 0.0, "residual": residual, "costs": total["costs"],
                      "leaks": -total["hedge_pnl"]},
            "k13_counts_as_loss": only_through_leaks, "positions": rows}


def exit_check(db: DB, round_id: str, at: str) -> dict:
    """Window end and the price test for every open basket at ``at`` (the span test runs in walk)."""
    out = []
    open_b = sorted({p["basket_id"] for p in _open(db, round_id)})
    for bid in open_b:
        b = db.one("constructed_baskets", "basket_id=?", (bid,))
        ps = db.rows("paper_positions", "basket_id=?", (bid,))
        wend = ps[0]["exit_rules"].get("window_end") if ps else None
        if wend and ts(at) >= ts(wend):
            out.append(exit_basket(db, bid, wend, "window_end"))
            continue
        # price test: cumulative residual P&L reaches RECOVERY_FRACTION of the expected residual
        sc = [s for s in db.rows("scenarios", "basket_id=?", (bid,)) if s["in_thesis"] and s["tide_state"] == "flat"]
        exp = float(np.mean([sum((lo + hi) / 2 for lo, hi in s["payoffs"].values()) for s in sc])) if sc else 0.0
        mk = mark(db, round_id, at, "exit_check")
        unreal = sum(m.get("unrealised", 0.0) for m in mk["marks"] if str(m.get("paper_id", "")).startswith(bid))
        if exp > 0 and unreal >= float(config.get("RECOVERY_FRACTION")) * exp:
            out.append(exit_basket(db, bid, at, "s_perp_recovered"))
        else:
            out.append({"basket_id": bid, "open": True, "unrealised": unreal, "expected_residual": exp})
    return {"at": at, "results": out}


def paper_book(db: DB, round_id: str | None = None) -> dict:
    where, params = ("round_id=?", (round_id,)) if round_id else ("", ())
    out = []
    for b in db.rows("constructed_baskets", where, params):
        exits = db.rows("paper_exits", "basket_id=?", (b["basket_id"],))
        pos = db.rows("paper_positions", "basket_id=?", (b["basket_id"],))
        out.append({"basket_id": b["basket_id"], "status": b["status"], "reason": b["reason"], "shape": b["shape"],
                    "z_star": b["z_star"], "b_basket": b["b_basket"], "max_loss": b["max_loss"], "tide": b["tide_id"],
                    "entry_rules": sorted({p["entry_rule"] for p in pos}),
                    "closed": bool(exits) and len(exits) == len(pos),
                    "pnl": sum(float(e["pnl"]) for e in exits) if exits else None,
                    "exit_reasons": sorted({e["reason"] for e in exits})})
    return {"baskets": out}
