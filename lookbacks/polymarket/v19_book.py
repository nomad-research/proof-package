"""v19 paper book, version 0 (decisions 12 to 17). Runs the new system on paper over the forward sweep's frozen batches.

    python lookbacks/polymarket/v19_book.py run      # network: resolutions re-read from Gamma; writes v19/book.json and v19/BOOK.md

What it does, layer by layer (docs/NOMAD_V19_STARTING_POINT.md §4):
- Selector and cold reader: the sweep's frozen batches (read only; nothing in them changes).
- Shadow book: every position the reader produces, both sides, every event (sweep §2: the session's chance beats the all-in cost at the lock ask).
- Armed book: A2 alone binds (decision 13). Non-mention events: NO at 50c or more with the reader 20+ points surer than the ask midpoint.
  Mention events: the starting point's mention rule, either side at 50c or more and 20+ points (its floor is an open question, decision 12).
- Labels: kind, occasion (addendum A3), depth at the lock (A5). A3, A4, A6, D1, D2, D3 are recorded as not yet available.
- Execution: paper fill at the lock ask plus the taker fee, sized at the lesser of $150 and the dollars on offer within 2c of the ask
  (the sweep's capacity reading, §3; C2 has no size yet). A 2c-worse fill is shown beside it until fills are measured.
- Ledger: settled from Gamma as contracts resolve. The book declares nothing: A2 is read only at its looks (V19_A2_prereg.md).
"""
import argparse, collections, datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_audit as A
import bt_t2 as T
import fwd_sweep as F
import v19_a2 as V

STAKE_CAP = 150.0                                  # $ per position: the sweep's capacity reading (§3), about median depth within 2c
WORSE = 0.02                                       # the fill sensitivity: every fill 2c worse than the ask
OUT = os.path.join(HERE, "v19")
NOT_YET = {"A3": "no record by kind yet", "A4": "no statistical baseline yet", "A6": "fills not measured yet",
           "D1": "news check not built", "D2": "the sweep's reader writes no falsifier", "D3": "nothing to go stale yet"}


def positions():
    out = []
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
                ev = fr[L["event_id"]]; byc = {c["cid"]: c for c in ev["contracts"]}
                for cl, cid in L["contracts"].items():
                    c = byc[cid]; lp = rec["lock_prices"].get(cid) or {}
                    ch = T.contract_chance(ev, ans, lab, cl, c)
                    if ch is None:
                        continue
                    lo, hi = ch; m = (lo + hi) / 2
                    q = (lp["ask_yes"]["ask"] + 1 - lp["ask_no"]["ask"]) / 2 if lp.get("ask_yes") and lp.get("ask_no") else None
                    for yes, want in ((True, lo), (False, 1 - hi)):
                        sa = lp.get("ask_yes" if yes else "ask_no")
                        if not sa:
                            continue
                        k = F.ask_cost(c, sa)
                        if want <= k:
                            continue
                        p = {"batch": b, "session": sid, "event": ev["id"], "title": ev["title"], "q": c["q"], "cid": cid, "side": "YES" if yes else "NO",
                             "token": c.get("token_yes") if yes else c.get("token_no"),
                             "lock": rec["lock"], "cost": k, "ask": sa["ask"], "usd_1c": sa.get("usd_1c"), "usd_2c": sa.get("usd_2c"),
                             "reader": want, "m": m, "mkt": q, "gap": V.gap_of(yes, m, q), "mention": ev["mention"],
                             "kind": V.market_type(ev), "subject": V.subject_of(ev), "end": V.scheduled_end(ev)}
                        p["armed"] = V.armed(p) and (p["mention"] or p["side"] == "NO")
                        p["book"] = "armed" if p["armed"] else "shadow only"
                        p["A5_usd_within_2c"] = p["usd_2c"]
                        p["stake"] = min(STAKE_CAP, p["usd_2c"]) if p["usd_2c"] else 0.0
                        p["labels_not_yet"] = NOT_YET
                        p["near_certain_at_lock"] = q is not None and (q <= 0.03 or q >= 0.97)     # the market already treats it as decided
                        p["slippage_bound"] = 0.01 if p["usd_1c"] and p["stake"] <= p["usd_1c"] else WORSE  # the stake fits within 1c (or 2c) of the ask
                        out.append(p)
    V.assign_occasions(out)
    return out


def settle(ps):
    cache = {}
    for p in ps:
        if p["event"] not in cache:
            cache[p["event"]] = F.outcomes(p["event"])
        res, _ = cache[p["event"]]
        r = res.get(p["cid"])
        if r is None:
            p["status"] = "open"; continue
        won, closed = r
        if closed and closed <= p["lock"]:
            p["status"] = "closed before the lock"; continue
        p["status"] = "won" if won == (p["side"] == "YES") else "lost"
        hit = 1.0 if p["status"] == "won" else 0.0
        shares = p["stake"] / p["cost"] if p["cost"] else 0.0
        p["pnl"] = shares * (hit - p["cost"])
        p["pnl_2c_worse"] = (p["stake"] / (p["cost"] + WORSE)) * (hit - p["cost"] - WORSE) if p["stake"] else 0.0
    return ps


def money(x):
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def report(ps):
    now = dt.datetime.now(dt.timezone.utc)
    arm = [p for p in ps if p["armed"]]; sh = [p for p in ps if not p["armed"]]
    L = [f"# v19 paper book (version 0), {now:%Y-%m-%d %H:%M} UTC", "",
         "The new system run on paper over the forward sweep's frozen batches. Nothing is traded. The book declares nothing: the rule's test is read only at its looks (`V19_A2_prereg.md`).", "",
         f"Paper fills are at the lock ask plus the fee, each sized at the lesser of ${STAKE_CAP:.0f} and the dollars on offer within 2c of the ask. The 2c-worse column shows the same fills 2c dearer, until real fills are measured.", ""]
    def block(name, rs):
        done = [p for p in rs if p["status"] in ("won", "lost")]; won = sum(p["status"] == "won" for p in done)
        staked = sum(p["stake"] for p in rs); open_ = [p for p in rs if p["status"] == "open"]
        pnl = sum(p["pnl"] for p in done); pnl2 = sum(p["pnl_2c_worse"] for p in done); st_done = sum(p["stake"] for p in done)
        return [f"| {name} | {len(rs)} | {len({p['event'] for p in rs})} | {money(staked)} | {len(done)} ({won} won) | {money(pnl)} | {money(pnl2)} | "
                f"{(100 * pnl / st_done):+.1f}% | {len(open_)} ({money(sum(p['stake'] for p in open_))}) |" if st_done else
                f"| {name} | {len(rs)} | {len({p['event'] for p in rs})} | {money(staked)} | 0 | – | – | – | {len(open_)} ({money(sum(p['stake'] for p in open_))}) |"]
    L += ["## The books", "", "| Book | Positions | Events | Staked | Settled | Paper P&L | 2c worse | Return on settled | Still open ($) |", "|---|---|---|---|---|---|---|---|---|"]
    L += block("**Armed**", arm)
    L += block("Armed, non-mention (the E1 book)", [p for p in arm if not p["mention"]])
    L += block("Armed, mention (the mention book)", [p for p in arm if p["mention"]])
    L += block("Shadow only: NO", [p for p in sh if p["side"] == "NO"])
    L += block("Shadow only: YES", [p for p in sh if p["side"] == "YES"])
    nc = [p for p in sh if p["near_certain_at_lock"]]; nc_done = [p for p in nc if p["status"] in ("won", "lost")]
    L += ["", "**Reading the ledger early.** A NO bet that loses usually settles early (the thing happens), while one that wins settles only at its deadline. Settled results lean towards losses until a batch's deadlines pass.", "",
          f"**Already decided at the lock.** {len(nc)} shadow positions sit on contracts the market priced at 3% or less, or 97% or more, at the lock; {len(nc_done)} have settled, {sum(p['status'] == 'won' for p in nc_done)} won. "
          "Most are YES long shots on asks of a fraction of a cent. The ones settled so far are outcomes already decided at the lock (a day's rain, a closing price) that the news-blind reader bet against. A2's 50c floor keeps all of them out of the armed book; D1's narrowed rule (\"the outcome already happened\") would flag the decided ones.", "",
          f"**Fill bound from the lock books.** {sum(p['slippage_bound'] == 0.01 for p in arm)} of {len(arm)} armed stakes fit within 1c of the ask, the rest within 2c (each stake is capped at the dollars on offer within 2c)."]
    L += ["", "## Armed book by kind of market", "", "| Kind | Positions | Settled (won) | Paper P&L | Open stake |", "|---|---|---|---|---|"]
    for k in sorted({p["kind"] for p in arm}):
        rs = [p for p in arm if p["kind"] == k]; done = [p for p in rs if p["status"] in ("won", "lost")]
        L.append(f"| {k} | {len(rs)} | {len(done)} ({sum(p['status'] == 'won' for p in done)}) | {money(sum(p['pnl'] for p in done))} | {money(sum(p['stake'] for p in rs if p['status'] == 'open'))} |")
    L += ["", "## Armed exposure by occasion: what is lost if every open bet in it goes wrong", "",
          "Occasions are addendum A3's: the same kind of market, the same place or asset, settling within 7 days. Shown largest first; this is the group a cap would act on.", "",
          "| Occasion | Open positions | Events | Worst case |", "|---|---|---|---|"]
    occ = collections.defaultdict(list)
    for p in arm:
        if p["status"] == "open":
            occ[p["occ"]].append(p)
    tot = sum(p["stake"] for rs in occ.values() for p in rs)
    for o, rs in sorted(occ.items(), key=lambda kv: -sum(p["stake"] for p in kv[1])):
        L.append(f"| {o} | {len(rs)} | {len({p['event'] for p in rs})} | {money(sum(p['stake'] for p in rs))} |")
    L += [f"| **All open armed** | {sum(len(rs) for rs in occ.values())} | | **{money(tot)}** |", "",
          "## Armed positions", "", "| Batch | Event | Contract | Side | Cost | Reader | Market | Stake | Depth 2c | Status | P&L |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(arm, key=lambda p: (p["status"] != "lost", p["occ"], p["event"])):
        L.append(f"| {p['batch']} | {p['title'][:48]} | {p['q'][:48]} | {p['side']} | {p['cost']:.2f} | {p['reader']:.2f} | {p['mkt']:.2f} | {money(p['stake'])} | "
                 f"{money(p['usd_2c']) if p['usd_2c'] else '–'} | {p['status']} | {money(p['pnl']) if 'pnl' in p else '–'} |")
    L += ["", "## Gaps this run shows", "",
          "- **No falsifier on any position (D2).** The sweep's reader is not asked for one, and its prompt is frozen. A falsifier needs a v19 reader pass or a separate step.",
          "- **Not yet available on any position:** A3 (record by kind), A4 (statistical baseline), A6 (fills measured), D1 (news check), D3 (staleness).",
          f"- **Positions with no depth recorded at the lock (A5 unassessable, stake $0):** {sum(1 for p in arm if not p['usd_2c'])} armed."]
    return "\n".join(L) + "\n"


def cmd_run(a):
    ps = settle(positions()); os.makedirs(OUT, exist_ok=True)
    A.jdump({"run_at": dt.datetime.now(dt.timezone.utc).isoformat(), "positions": ps}, os.path.join(OUT, "book.json"))
    text = report(ps); open(os.path.join(OUT, "BOOK.md"), "w", encoding="utf-8").write(text); print(text)


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True); sp.add_parser("run")
    a = ap.parse_args(); {"run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
