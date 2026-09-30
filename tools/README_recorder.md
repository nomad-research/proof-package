# Polymarket forward recorder

Run on any always-on machine with Python 3.9 or newer and internet access. No packages, no keys, no wallet: it reads public endpoints only.

```
python3 polymarket_recorder.py --out ~/polymarket_record          # runs until Ctrl-C; safe to stop and restart, it resumes from state.json
python3 polymarket_recorder.py --out /tmp/x --once --top 5       # one pass, to check it works
```
Keep it running under `tmux`, `screen`, `nohup`, or a launchd/systemd unit. A sleeping laptop leaves gaps; the manifest shows them.

It stores everything whole (nothing summarised): market metadata pages and every version of every event, order-book snapshots for the top tokens, a daily price history per token, and trades. Every request is logged in `manifest.jsonl` with its UTC time and the sha256 of the raw body, so a later reader can prove nothing was altered.
Disk: a few hundred MB a day at the defaults. To hand the record back: zip the folder (or just `manifest.jsonl` and `state.json` for a hash-only check) to wherever we agree.
