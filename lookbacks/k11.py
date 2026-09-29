"""K11 look-back, exactly as pre-registered in K11_K12_prereg.md (commit 6110244).

Reads the frozen v15 ledger read-only; every price comes from the nomad16 vintage store (fetched here
with `--fetch`, hashed on write). Writes lookbacks/k11_result.json.
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nomad16 import prices  # noqa: E402
from nomad16.db import DB, Refused  # noqa: E402
from nomad16.view import View  # noqa: E402

V15 = ROOT / "v15" / "nomad_harness.db"
SUFFIX = {"XETRA": ".DE", "LSE": ".L", "Euronext Paris": ".PA"}
US = {"NYSE", "NASDAQ"}
HOME = {"NYSE": "SPY", "NASDAQ": "SPY", "XETRA": "^GDAXI", "LSE": "^FTSE", "Euronext Paris": "^FCHI",
        "HEL": "^OMXH25", "STO": "^OMX", "OSL": "OBX.OL", "CPH": "^OMXC25", "BIT": "FTSEMIB.MI",
        "WSE": "WIG20.WA", "JSE": "^J203.JO", "TYO": "^N225", "SSE": "000001.SS", "SZSE": "399001.SZ",
        "Santiago": "^IPSA", "IDX": "^JKSE"}
STORY = {8: "CRAK", 9: "XLY", 10: "EXV5.DE", 11: "WOOD", 13: "HG=F", 15: "XLK", 16: "HG=F"}
LOAD_N, BAND_N, H, Q, BLOCK, DRAWS = 120, 250, 10, 0.90, 5, 2000


def symbol(h):
    if h.get("price_symbol"):
        return h["price_symbol"]
    t = h["ticker"].rstrip(".")
    return t if h.get("exchange") in US else t + SUFFIX.get(h.get("exchange"), "")


def load_v15():
    c = sqlite3.connect(f"file:{V15}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rounds = []
    for n, r in enumerate(c.execute("SELECT r.id, r.round_class, e.event_date FROM rounds r JOIN events e "
                                    "ON e.id=r.event_id ORDER BY r.rowid"), 1):
        tr = [dict(x) for x in c.execute("SELECT to_state, recorded_at FROM round_transitions WHERE round_id=? "
                                         "ORDER BY rowid", (r["id"],))]
        if not (5 <= n <= 17) or any(x["to_state"] == "void" for x in tr):
            continue
        lock = next((x["recorded_at"] for x in tr if x["to_state"] == "locked"), None)
        narr = [dict(x) for x in c.execute("SELECT recorded_at FROM predictions WHERE round_id=? AND "
                                           "call_type='narrative'", (r["id"],))]
        story = STORY.get(n) if any(lock and x["recorded_at"] < lock for x in narr) else None
        rounds.append({"seq": n, "id": r["id"], "class": r["round_class"], "event_date": r["event_date"],
                       "lock": lock, "story": story, "narrative_rows": len(narr)})
    holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
    for r in rounds:
        hs = {e["holder_id"] for e in c.execute("SELECT holder_id FROM effects WHERE round_id=? AND "
                                                "(eliminated IS NULL OR eliminated=0)", (r["id"],))}
        r["units"] = sorted({(symbol(holders[h]), HOME.get(holders[h].get("exchange"), "ACWI"))
                             for h in hs if holders.get(h, {}).get("listed") == 1})
    return rounds


def fetch_all(db, rounds):
    syms = sorted({s for r in rounds for u in r["units"] for s in u} | {r["story"] for r in rounds if r["story"]}
                  | {"ACWI"})
    view = View(db)
    for s in syms:
        if not prices.frame(view, s).empty:
            continue
        try:
            print("fetch", s, prices.fetch_yahoo(db, s, "2024-01-01", "2026-09-28", ceiling=None)["n_sessions"])
        except Refused as e:
            print("fetch", s, "FAILED", e)
        time.sleep(4.0)


def rets(view, s):
    f = prices.frame(view, s)
    return f["adjclose"].astype(float).pct_change().dropna() if not f.empty else pd.Series(dtype=float)


def first_trade(db, s):
    v = db.rows("price_vintages", "symbol=?", (s,))
    ft = (v[-1]["metadata"] or {}).get("firstTradeDate") if v else None
    return pd.Timestamp(ft, unit="s").strftime("%Y-%m-%d") if isinstance(ft, (int, float)) else None


def run(db):
    view = View(db)
    rounds = load_v15()
    out_units, rounds_out = [], []
    for r in rounds:
        ed = r["event_date"]
        rows, excluded = [], []
        for sym, tide in r["units"]:
            ri, ti = rets(view, sym), rets(view, tide)
            if ti.empty:
                tide = "ACWI"
                ti = rets(view, "ACWI")
            ft = first_trade(db, sym)
            if ri.empty:
                excluded.append((sym, "no price series"))
                continue
            if ft and ft >= ed:
                excluded.append((sym, f"first trade {ft} not before the event"))
                continue
            df = pd.concat([ri.rename("r"), ti.rename("t")], axis=1).dropna()
            pre, post = df[df.index < ed], df[df.index > ed]
            if len(pre) < 60 or len(post) < H:
                excluded.append((sym, f"sessions pre {len(pre)} post {len(post)}"))
                continue
            est = pre.iloc[-LOAD_N:]
            X = np.column_stack([np.ones(len(est)), est["t"].values])
            b, *_ = np.linalg.lstsq(X, est["r"].values, rcond=None)
            e = est["r"].values - X @ b
            sig = float(np.std(e, ddof=1))
            hist = pre.iloc[-BAND_N:]
            eh = hist["r"].values - (b[0] + b[1] * hist["t"].values)
            band = prices.block_bootstrap_quantile(eh, H, Q, BLOCK, DRAWS)
            p10 = post.iloc[:H]
            move = float(np.sum(p10["r"].values - (b[0] + b[1] * p10["t"].values)))
            row = {"sym": sym, "tide": tide, "sigma": sig, "tau": b[1] * float(np.std(est["t"].values, ddof=1)) / sig,
                   "band": band, "move": move, "left": bool(abs(move) > band)}
            if r["story"]:
                fs = rets(view, r["story"])
                d2 = pd.concat([ri.rename("r"), ti.rename("t"), fs.rename("f")], axis=1).dropna()
                d2 = d2[d2.index < ed].iloc[-LOAD_N:]
                if len(d2) >= 60:
                    X2 = np.column_stack([np.ones(len(d2)), d2["t"].values, d2["f"].values])
                    b2, *_ = np.linalg.lstsq(X2, d2["r"].values, rcond=None)
                    row["ell"] = b2[2] * float(np.std(d2["f"].values, ddof=1)) / sig
                else:
                    row["ell"] = 0.0
                    row["story_gap"] = "fewer than 60 common sessions with the story proxy"
            rows.append(row)
        ncol = 2 if r["story"] else 1
        degenerate = len(rows) <= ncol
        if rows and not degenerate:
            Hm = np.column_stack([[x["tau"] for x in rows]] + ([[x.get("ell", 0.0) for x in rows]] if r["story"] else []))
            P = Hm @ np.linalg.pinv(Hm.T @ Hm) @ Hm.T
            for i, x in enumerate(rows):
                x["rho"] = math.sqrt(max(0.0, 1.0 - float(P[i, i])))
        for x in rows:
            x.update(seq=r["seq"], cls=r["class"], degenerate=degenerate)
        out_units += rows
        rounds_out.append({"seq": r["seq"], "class": r["class"], "event_date": ed, "story": r["story"],
                           "narrative_rows": r["narrative_rows"], "units": len(rows), "degenerate": degenerate,
                           "excluded": excluded,
                           "median_rho_left": float(np.median([x["rho"] for x in rows if x["left"] and "rho" in x]))
                           if any(x["left"] and "rho" in x for x in rows) else None,
                           "median_rho_stayed": float(np.median([x["rho"] for x in rows if not x["left"] and "rho" in x]))
                           if any((not x["left"]) and "rho" in x for x in rows) else None})

    def test(sel):
        u = [x for x in out_units if "rho" in x and not x["degenerate"] and sel(x)]
        a = [x["rho"] for x in u if x["left"]]
        b = [x["rho"] for x in u if not x["left"]]
        if len(a) < 5 or len(b) < 5:
            return {"n_left": len(a), "n_stayed": len(b), "verdict": "unreadable (a group has fewer than 5 units)"}
        s = mannwhitneyu(a, b, alternative="greater")
        return {"n_left": len(a), "n_stayed": len(b), "median_rho_left": float(np.median(a)),
                "median_rho_stayed": float(np.median(b)), "U": float(s.statistic), "p": float(s.pvalue),
                "verdict": "separates (K11 lives)" if s.pvalue < 0.05 else "no separation beyond noise (K11 dies)"}

    res = {"pooled": test(lambda x: True), "clean": test(lambda x: x["cls"] == "clean"),
           "learning": test(lambda x: x["cls"] == "learning"), "rounds": rounds_out, "units": out_units}
    (ROOT / "lookbacks" / "k11_result.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    return res


if __name__ == "__main__":
    db = DB()
    if "--fetch" in sys.argv:
        fetch_all(db, load_v15())
    r = run(db)
    print(json.dumps({k: r[k] for k in ("pooled", "clean", "learning")}, indent=1))
    for x in r["rounds"]:
        print(x["seq"], x["class"], x["event_date"], x["story"], "units", x["units"], "degenerate", x["degenerate"],
              "excluded", len(x["excluded"]), "med rho left/stayed", x["median_rho_left"], x["median_rho_stayed"])
