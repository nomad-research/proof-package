# Polymarket forward recorder

Two scripts, public read endpoints only: no keys, no wallet, no orders, no account. Run on an always-on machine with Python 3.9 or newer.

**Why now.** Polymarket keeps 1-minute price bars for about 7 days, 5-minute bars for about 60 days and 30-minute bars for about 90 days; older history comes back only in 12-hour buckets. It keeps no historical order books (a closed market returns "No orderbook exists"). Rules text can be clarified after a market is created.
So the finest bars are taken every day before they age out, every version of every event is kept whole and hashed, and books and the live message stream are recorded from now on. Whatever is not recorded is unrecoverable.

## Start (both, in two terminals or two `tmux` panes)
```
python3 polymarket_recorder.py --out ~/polymarket_record
pip install websockets
python3 polymarket_ws_recorder.py --record-dir ~/polymarket_record --top 100
```
Safe to stop and restart (it resumes from `state.json`). A sleeping machine leaves gaps; `manifest.jsonl` shows them. Check it works first: `python3 polymarket_recorder.py --out /tmp/x --once --top 5`.

## What is stored (everything whole; nothing summarised)
- `gamma/event_snapshots/<event>/<sha256>.json.gz`: one file per distinct version of an event (rules text, fee schedule, status, UMA resolution fields, prices). A rules edit is a new file.
- `gamma/events/...`: whole metadata pages every 6 hours (each page's hash is logged every sweep).
- `clob/book/<token>/<day>/<time>.json.gz`: order-book snapshots every 15 minutes for the top tokens.
- `clob/history/<token>/<day>_1d_f1` (1-minute bars, last day), `_1w_f5` (5-minute bars, last week), `_max_f30` (30-minute bars, whole range, weekly).
- `data/trades/<condition>.jsonl`: trades, de-duplicated on transaction hash.
- `ws/<Y>/<M>/<D>/<hour>.jsonl.gz`: every WebSocket market-channel message, raw, timestamped on arrival.
- Events that leave the active list keep being fetched until closed and every market shows `umaResolutionStatus` resolved, so the proposal, challenge, any dispute and the final state are kept.
- `manifest.jsonl`: every request with its UTC time, status, bytes and the sha256 of the raw body. `state.json`: what is watched, and a count of every tag seen.

## Scope
Geopolitical and adjacent (finance, STEM, business, manufacturing and so on). Left out by default: sport, gaming, entertainment and the daily-temperature ladders (`--exclude-tags` to change; `--include-tags` to narrow). `state.json` counts every tag so the list can be tuned.

## Disk
About 12 MB for one metadata pass over 100 events; a few hundred MB a day at the defaults (`--top 300`). You have room for months. Lower with `--top`, `--max-events`, `--book-every`.

## Getting it back to me
The raw record stays on your machine. Drive returns files into my context as base64, so it suits small files only. I write analysis scripts, you run them where the data is, and the small result files (JSON or markdown) go into the repo or Drive for me to read.

## Universe sweep (added 2026-09-30)
Once a day the recorder now lists **every open event** (union of ten API orderings; one ordering is capped near 2,100) into `universe/YYYY/MM/DD_HHMMSS.jsonl.gz`: tags, dates, negRisk, and per market the condition and token ids, thresholds, fee schedule and a hash of the rules text. Sports and gaming events are kept as header rows only. About 12,700 open events on the first test, roughly 190 seconds, and the file is small enough for daily use (a few MB to about 15 MB). The log line shows how many new ids each ordering added, so coverage can be judged. To use it, `git pull` and restart the recorder (Ctrl-C, then the same command; it resumes from `state.json`).
