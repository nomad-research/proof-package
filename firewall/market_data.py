#!/usr/bin/env python3
"""Market data fetcher with a hard date ceiling.

Operating procedure section 1.1 permits market data up to and including the ACK
fire date and forbids it after. A domain allowlist cannot enforce that -- a
price endpoint returns whatever range it likes. So this wrapper truncates the
series to the fire date BEFORE anything is written to disk or printed. The
untruncated response is never surfaced.

Refuses to run until firewall/config.json carries a fire_date.
Set phase to "post-seal" only after prediction.md is committed; only then will
it serve data past the fire date, and it stamps every such file as post-seal.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CFG = HERE / "config.json"
OUT = HERE.parent / "data" / "blindrun"
LOG = HERE / "fetch_log.jsonl"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"


def load_cfg():
    cfg = json.loads(CFG.read_text())
    if not cfg.get("fire_date"):
        sys.exit("REFUSED: firewall/config.json has no fire_date. The analyst must "
                 "supply the ACK fire date before any market data may be fetched.")
    return cfg


def get(sym: str, start: str = "2024-01-01"):
    cfg = load_cfg()
    fire = pd.Timestamp(cfg["fire_date"])
    post = cfg.get("phase") == "post-seal"

    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int((pd.Timestamp.now(tz="UTC")).timestamp())
    url = f"{CHART.format(sym=sym)}?period1={p1}&period2={p2}&interval=1d"
    r = subprocess.run(["curl", "-sS", "--max-time", "60",
                        "-H", "User-Agent: Mozilla/5.0", url],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    tz = d["meta"]["exchangeTimezoneName"]
    df = pd.DataFrame({
        "date": pd.to_datetime(d["timestamp"], unit="s", utc=True)
                  .tz_convert(tz).normalize().tz_localize(None),
        "open": q["open"], "high": q["high"], "low": q["low"],
        "close": q["close"], "volume": q["volume"],
    }).dropna(subset=["close"])

    n_raw = len(df)
    if not post:
        df = df[df["date"] <= fire]          # <-- the control
    n_kept = len(df)

    OUT.mkdir(parents=True, exist_ok=True)
    tag = "postseal" if post else f"upto{fire.date()}"
    path = OUT / f"{sym.replace('^','IDX_')}_{tag}.csv"
    df.to_csv(path, index=False)
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"ts_utc": datetime.now(timezone.utc).isoformat(),
                             "kind": "market_data", "symbol": sym,
                             "fire_date": str(fire.date()), "phase": cfg.get("phase"),
                             "rows_returned": n_raw, "rows_kept": n_kept,
                             "truncated": n_raw - n_kept, "saved_to": str(path)}) + "\n")
    print(f"{sym}: kept {n_kept} rows (dropped {n_raw - n_kept} past the fire date) -> {path}")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: market_data.py <SYMBOL> [start]")
        sys.exit(64)
    get(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "2024-01-01")
