#!/usr/bin/env python3
"""Polymarket WebSocket recorder (optional): the market channel's full message stream for the watched tokens, one JSONL line per message, timestamped on arrival.

    pip install websockets
    python3 polymarket_ws_recorder.py --record-dir ./polymarket_record --top 100        # reads the watched tokens the main recorder wrote to state.json

Run it beside polymarket_recorder.py; it needs that recorder's state.json. Messages are kept whole (the raw text), so book deltas, price changes and trades can be replayed.
It re-reads state.json every 10 minutes and resubscribes when the top tokens change; it reconnects with backoff after a drop. Public channel only; no keys.
"""
import argparse
import asyncio
import datetime as dt
import gzip
import json
import os
import signal

URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
STOP = False


def top_tokens(record_dir, n):
    st = json.load(open(os.path.join(record_dir, "state.json")))
    return [tk for tk, _ in sorted(st["watched"].items(), key=lambda kv: -kv[1]["volume24hr"])[:n]]


async def run(record_dir, n):
    import websockets
    backoff = 1
    while not STOP:
        tokens = top_tokens(record_dir, n)
        try:
            async with websockets.connect(URL, open_timeout=20, ping_interval=20) as ws:
                await ws.send(json.dumps({"type": "market", "assets_ids": tokens}))
                backoff = 1
                t_end = asyncio.get_event_loop().time() + 600
                while not STOP and asyncio.get_event_loop().time() < t_end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), 30)
                    except asyncio.TimeoutError:
                        continue
                    now = dt.datetime.now(dt.timezone.utc)
                    path = os.path.join(record_dir, "ws", now.strftime("%Y/%m/%d"), now.strftime("%H") + ".jsonl.gz")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with gzip.open(path, "ab") as f:
                        f.write((json.dumps({"at": now.isoformat(), "raw": msg if isinstance(msg, str) else msg.decode("utf8", "replace")}) + "\n").encode())
        except Exception as e:
            print("ws error", type(e).__name__, str(e)[:80])
            await asyncio.sleep(min(backoff, 60)); backoff *= 2


def main():
    global STOP
    ap = argparse.ArgumentParser(); ap.add_argument("--record-dir", required=True); ap.add_argument("--top", type=int, default=100)
    a = ap.parse_args()
    signal.signal(signal.SIGINT, lambda *_: globals().update(STOP=True)); signal.signal(signal.SIGTERM, lambda *_: globals().update(STOP=True))
    asyncio.run(run(a.record_dir, a.top))


if __name__ == "__main__":
    main()
