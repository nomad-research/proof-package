"""A2 forward (V19_A2_prereg.md): the starting point's arming rule, read on the forward sweep's frozen batches.
Reads the sweep's files and writes only v19/a2_result.json; the sweep's own files and scorer are untouched.

    python lookbacks/polymarket/v19_a2.py score       # network: resolutions re-read from Gamma, as fwd_sweep.py score
    python lookbacks/polymarket/v19_a2.py backtest    # no network: the same rule on BT-T2 passes 1-3 and E3 passes 1-2 (the starting point's §6)
"""
import argparse, collections, datetime as dt, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import bt_audit as A
import bt_t2 as T
import fwd_sweep as F

ARM_COST, ARM_GAP = 0.50, 0.20                     # A2: NO costs 50c or more, the reader at least 20 points surer (starting point §5, basis §6)
LOOKS = (40, 80)                                   # resolved non-mention events with an armed NO position: a direction read, then the confirmation (addendum A1)
BANDS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40)
SEED = 20261001
OUT = os.path.join(HERE, "v19")


def market_type(e):
    """A first, fixed list of market kinds, set before any sweep outcome is read (addendum A2). Title and tags only."""
    t = (e.get("title") or "").lower(); tags = " ".join(e.get("tags") or []).lower()
    for name, pat in (("mention", r"\bsay\b|\bmention"), ("post counts", r"# ?posts|tweets|# of posts"),
                      ("crypto price", r"bitcoin|ethereum|solana|xrp|\bbtc\b|\beth\b|crypto|dogecoin|hyperliquid"),
                      ("stocks and earnings", r"\(([a-z]{1,5})\)|earnings|revenue|stock|close above|nasdaq|s&p|dow jones|market cap|ipo"),
                      ("macro and commodities", r"\bfed\b|cpi|inflation|interest rate|gdp|jobs|unemployment|payroll|treasury|yield|oil|gold|crude"),
                      ("elections and votes", r"election|primary|winner|by-election|nominee|seats|vote|referendum|poll"),
                      ("weather and nature", r"temperature|weather|hurricane|earthquake|rain|snow"),
                      ("deadlines and announcements", r" by |before |announce|sign|release|launch|deal|ceasefire|meet")):
        if re.search(pat, t + " " + tags if name == "crypto price" else t):
            return name
    return "other"


def gap_of(side_yes, m, q):
    """How much surer the reader is of its side than the market's midpoint, in chance points."""
    return None if q is None else (m - q if side_yes else q - m)


def forward_rows(outcomes=F.outcomes):
    """The sweep's rows and matched base exactly as fwd_sweep.cmd_score builds them, plus the reader's midpoint m and the market's q."""
    rows, contracts = [], []
    for b in sorted(os.listdir(F.D)):
        mp = os.path.join(F.bdir(b), "manifest.json")
        if not os.path.exists(mp):
            continue
        man = A.jload(mp); fr = {e["id"]: e for e in A.jload(os.path.join(F.bdir(b), "frame.json"))["events"]}
        for sid, row in man["sessions"].items():
            rec = A.jload(os.path.join(F.bdir(b), "answers", f"{sid}.json"))
            if A.sha(rec["answers"]) != row["answers_sha256"] or A.sha(rec["lock_prices"]) != row["lock_prices_sha256"]:
                raise SystemExit(f"{b}/{sid} changed after the freeze")
            if row["status"] != "ok":
                continue
            ans = T.intkeys(rec["answers"]); labels = A.jload(os.path.join(F.bdir(b), "sessions", f"{sid}.json"))["labels"]
            for lab, L in labels.items():
                ev = fr[L["event_id"]]; res, vol = outcomes(ev["id"]); byc = {c["cid"]: c for c in ev["contracts"]}
                counts = not ev.get("low_volume_at_snapshot") or (vol or 0) >= 10000          # sweep addendum A1
                for cl, cid in L["contracts"].items():
                    c = byc[cid]; lp = rec["lock_prices"].get(cid) or {}
                    if cid not in res or (res[cid][1] and res[cid][1] <= rec["lock"]):
                        continue
                    won = res[cid][0]
                    for yes in (True, False):
                        sa = lp.get("ask_yes" if yes else "ask_no")
                        if sa:
                            contracts.append({"batch": b, "event": ev["id"], "kind": ev["kind"], "mention": ev["mention"], "yes": yes, "counts": counts,
                                              "cost": F.ask_cost(c, sa), "hit": float(won == yes)})
                    ch = T.contract_chance(ev, ans, lab, cl, c)
                    if ch is None:
                        continue
                    lo, hi = ch; m = (lo + hi) / 2
                    q = (lp["ask_yes"]["ask"] + 1 - lp["ask_no"]["ask"]) / 2 if lp.get("ask_yes") and lp.get("ask_no") else None   # midpoint of the two asks
                    for yes, want in ((True, lo), (False, 1 - hi)):
                        sa = lp.get("ask_yes" if yes else "ask_no")
                        if not sa:
                            continue
                        k = F.ask_cost(c, sa)
                        if want > k:
                            rows.append({"batch": b, "event": ev["id"], "kind": ev["kind"], "mention": ev["mention"], "side": "YES" if yes else "NO",
                                         "counts": counts, "cost": k, "hit": float(won == yes), "money": float(won == yes) - k, "usd_2c": sa.get("usd_2c"),
                                         "m": m, "q": q, "gap": gap_of(yes, m, q), "closed": res[cid][1], "mtype": market_type(ev)})
    for r in rows:
        same = lambda x: x["counts"] and x["event"] != r["event"] and x["kind"] == r["kind"] and x["yes"] == (r["side"] == "YES") and abs(x["cost"] - r["cost"]) <= F.MATCH_BAND
        bs = [x["hit"] - x["cost"] for x in contracts if same(x)]
        both = [x["hit"] - x["cost"] for x in contracts if x["counts"] and x["mention"] and x["event"] != r["event"] and x["kind"] == r["kind"]
                and abs(x["cost"] - r["cost"]) <= F.MATCH_BAND]
        r["skill"] = r["money"] - (float(np.mean(bs)) if bs else 0.0)                       # the sweep's E1 skill
        r["skill_mention_both"] = r["money"] - (float(np.mean(both)) if both else 0.0)     # the sweep's E3b skill
        r["money_150"] = (min(150.0, r["usd_2c"]) / r["cost"]) * r["money"] if r.get("usd_2c") else None
    return rows


def armed(r, any_cost=False):
    return r["gap"] is not None and r["gap"] >= ARM_GAP and (any_cost or r["cost"] >= ARM_COST)


def read(rs, key, level, rng, unit="event"):
    """Mean, interval and the share of resamples above zero, resampling by event (or by batch, or by week of resolution)."""
    rs = [r for r in rs if r.get(key) is not None]
    if not rs:
        return None
    byu = collections.defaultdict(list)
    for r in rs:
        byu[r[unit]].append(r[key])
    keys = list(byu); ms = []
    for _ in range(4000):
        s = rng.choice(len(keys), len(keys)); ms.append(np.mean(np.concatenate([byu[keys[i]] for i in s])))
    lo, hi = np.percentile(ms, [(100 - level) / 2, 100 - (100 - level) / 2])
    return {"n": len(rs), "events": len({r["event"] for r in rs}), "units": len(keys), "mean": float(np.mean([r[key] for r in rs])),
            f"ci{level}": [float(lo), float(hi)], "p_positive": float(np.mean(np.array(ms) > 0))}


def week_of(r):
    return dt.datetime.fromtimestamp(r["closed"], dt.timezone.utc).strftime("%G-W%V") if r.get("closed") else f"batch {r['batch']}"


def summarise(rows):
    rng = np.random.default_rng(SEED)
    for r in rows:
        r["week"] = week_of(r)
    no = [r for r in rows if r["side"] == "NO" and r["counts"]]
    arm_all = [r for r in no if armed(r)]
    arm = [r for r in arm_all if not r["mention"]]                         # addendum A1: declared on the E1 book, non-mention events
    blocked = [r for r in no if not r["mention"] and not armed(r)]
    n_ev = len({r["event"] for r in arm}); look = 2 if n_ev >= LOOKS[1] else 1 if n_ev >= LOOKS[0] else 0
    res = read(arm, "skill", 97.5, rng); verdict = "not yet at a look"
    if look == 1 and res:                                                  # addendum A2: the halfway look neither confirms nor kills
        verdict = ("direction only; points the wrong way, so a revision is drafted (addendum A2)" if res["mean"] < 0 else
                   "direction only; reviewed, no revision required")
    elif look == 2 and res:
        verdict = "confirmed" if res["ci97.5"][0] > 0 else "killed" if res["ci97.5"][1] < 0 else "carried"
    weeks = sorted({r["week"] for r in arm})
    best = max(weeks, key=lambda w: sum(r["skill"] for r in arm if r["week"] == w)) if weeks else None
    types = sorted({r["mtype"] for r in arm})
    best_t = max(types, key=lambda t: sum(r["skill"] for r in arm if r["mtype"] == t)) if types else None
    men = [r for r in rows if r["mention"] and r["counts"]]
    return {
        "A2": {"events_resolved": n_ev, "look_reached": look, "looks_at": list(LOOKS), "statistic": res, "reading": verdict},
        "secondary": {
            "a2_by_resolution_week": {w: read([r for r in arm if r["week"] == w], "skill", 95, rng) for w in weeks},
            "a2_resampled_by_week": read(arm, "skill", 95, rng, unit="week"),
            "a2_without_its_best_week": {"week": best, "read": read([r for r in arm if r["week"] != best], "skill", 95, rng)} if best else None,
            "a2_by_batch": {b: read([r for r in arm if r["batch"] == b], "skill", 95, rng) for b in sorted({r["batch"] for r in arm})},
            "a2_by_market_type": {t: read([r for r in arm if r["mtype"] == t], "skill", 95, rng) for t in types},
            "a2_without_its_best_market_type": {"type": best_t, "read": read([r for r in arm if r["mtype"] != best_t], "skill", 95, rng)} if best_t else None,
            "a2_including_mention_events": read(arm_all, "skill", 95, rng),
            "blocked_no_positions": read(blocked, "skill", 95, rng),
            "a2_money": read(arm, "money", 95, rng),
            "a2_hit_rate_and_mean_cost": {"hit": float(np.mean([r["hit"] for r in arm])), "cost": float(np.mean([r["cost"] for r in arm]))} if arm else None,
            "a2_money_at_150_capped_by_depth": read(arm, "money_150", 95, rng),
            "near_the_line": {"armed_cost_50_to_55": read([r for r in arm if r["cost"] < 0.55], "skill", 95, rng),
                              "gap_20_cost_45_to_50_not_armed": read([r for r in no if not r["mention"] and r["gap"] is not None and r["gap"] >= ARM_GAP
                                                                       and 0.45 <= r["cost"] < ARM_COST], "skill", 95, rng)},
            "no_cost_50_up_by_gap": {f"{g:.2f}": read([r for r in no if not r["mention"] and r["cost"] >= ARM_COST and r["gap"] is not None and r["gap"] >= g], "skill", 95, rng) for g in BANDS},
            "no_positions_without_both_asks": sum(1 for r in no if r["q"] is None),
            "mention_never_pooled_with_e3": {
                "either_side_cost_50_up": read([r for r in men if armed(r)], "skill_mention_both", 95, rng),
                "either_side_any_cost": read([r for r in men if armed(r, any_cost=True)], "skill_mention_both", 95, rng),
                "not_armed_any_cost": read([r for r in men if not armed(r, any_cost=True)], "skill_mention_both", 95, rng)},
        }}


def cmd_score(a):
    rows = forward_rows(); out = summarise(rows)
    os.makedirs(OUT, exist_ok=True); A.jdump(dict(out, rows=rows), os.path.join(OUT, "a2_result.json")); print(json.dumps(out, indent=1))


def cmd_backtest(a):
    """The rule on the backtests. Their gap is the reader's midpoint against the last trade, not the ask midpoint, and their cost is the last trade plus 1c."""
    rng = np.random.default_rng(SEED); mention = re.compile(r"\bsay\b|\bmention", re.I); out = {}
    for name, dirs, key in (("E1, BT-T2 passes 1-3 (NO, same-side skill)", ("t2", "t2_pass2", "t2_pass3"), "skill_side"),
                            ("E3, mention passes 1-2 (both sides, skill)", ("e3_mentions", "e3_mentions_pass2"), "skill")):
        rows = []
        for d in dirs:
            r = A.jload(os.path.join(HERE, "bt", d, "result.json")); fr = {str(e["id"]): e for e in A.jload(os.path.join(HERE, "bt", d, "frame.json"))["events"]}
            for p in r["rows"]["positions"]:
                rows.append(dict(p, event=f"{d}/{p['event']}", mention=bool(mention.search(fr[str(p["event"])].get("title") or ""))))
        if key == "skill_side":
            rows = [p for p in rows if p["side"] == "NO"]
        arm = [p for p in rows if p["cost"] >= ARM_COST and p["gap"] >= ARM_GAP]
        out[name] = {"all": read(rows, key, 95, rng), "armed": read(arm, key, 95, rng),
                     "not_armed": read([p for p in rows if not (p["cost"] >= ARM_COST and p["gap"] >= ARM_GAP)], key, 95, rng),
                     "armed_without_mention": read([p for p in arm if not p["mention"]], key, 95, rng),
                     "gap_20_any_cost": read([p for p in rows if p["gap"] >= ARM_GAP], key, 95, rng),
                     "gap_20_under_50c": read([p for p in rows if p["gap"] >= ARM_GAP and p["cost"] < ARM_COST], key, 95, rng)}
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("score"); sp.add_parser("backtest")
    a = ap.parse_args()
    {"score": cmd_score, "backtest": cmd_backtest}[a.cmd](a)


if __name__ == "__main__":
    main()
