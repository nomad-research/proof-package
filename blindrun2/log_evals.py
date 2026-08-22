"""Append this session's screening evaluations to config_log.jsonl.

Every evaluation is logged, INCLUDING the abandoned ones. The count is the
multiple-testing denominator and understating it would make every downstream
significance figure wrong. Two of the four entries below are screens that were
built, run, and then thrown away; they are logged exactly like the one that
survived.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "config_log.jsonl"

REV = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                     capture_output=True, text=True).stdout.strip()

EVALS = [
    {
        "description": "blindrun2 screen attempt 3: EDGAR items= filter",
        "params": {"run": "blindrun2", "channel": "edgar_fts_items_param",
                   "items": ["1.03", "2.04", "2.05", "3.01"],
                   "D": "2026-06-01", "trigger_end": "2026-07-15"},
        "outcome": {"verdict": "ABANDONED - filter unreliable",
                    "evidence": "endpoint serves stale bodies computed for a "
                                "different items value; 4/5 then 8/8 probes "
                                "byte-identical across distinct codes",
                    "defeated_by_cache_buster": False,
                    "defeated_by_no_cache_header": False},
        "status": "abandoned", "reported": True,
    },
    {
        "description": "blindrun2 diagnostic: items= filter, spaced probes",
        "params": {"run": "blindrun2", "diagnostic": "diag_items",
                   "codes": ["1.03", "2.04", "2.05", "3.01", "5.02"], "pause_s": 1.5},
        "outcome": {"distinct_bodies": 2, "collisions": ["1.03", "2.04", "2.05", "5.02"],
                    "clean": ["3.01"],
                    "verdict": "throttling ruled out; filter genuinely unreliable"},
        "status": "completed", "reported": True,
    },
    {
        "description": "blindrun2 diagnostic: items= filter, cache-buster",
        "params": {"run": "blindrun2", "diagnostic": "diag_items2",
                   "codes": ["1.03", "2.04", "2.05", "3.01"],
                   "variants": ["plain", "cache-busted"]},
        "outcome": {"distinct_bodies": 1, "responses": 8,
                    "verdict": "not a client-defeatable edge cache"},
        "status": "completed", "reported": True,
    },
    {
        "description": "blindrun2 screen attempt 4: complete 8-K enumeration, "
                       "client-side item filtering",
        "params": {"run": "blindrun2", "channel": "edgar_fts_full_enumeration",
                   "items": ["1.03", "2.04", "2.05", "3.01"],
                   "forms": ["8-K", "N-8F", "497"],
                   "D": "2026-06-01", "trigger_end": "2026-07-15",
                   "page_validation": True},
        "outcome": {"total_8k_enumerated": 7413, "day_shortfalls": 0,
                    "stale_pages_rejected": 0,
                    "item_census": {"1.03": 7, "2.04": 17, "2.05": 24, "3.01": 125},
                    "distinct_8k_matching": 166, "n8f": 9, "form_497": 1492,
                    "candidate_pool_after_497_class_rejection": 175,
                    "corrects_prior_count": {"item_2.04_was": 51, "item_2.04_is": 17}},
        "status": "completed", "reported": True,
    },
]


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    before = sum(1 for _ in LOG.open())
    with LOG.open("a") as fh:
        for e in EVALS:
            rec = {
                "config_hash": hashlib.sha256(
                    json.dumps(e["params"], sort_keys=True).encode()).hexdigest()[:16],
                "description": e["description"],
                "eval_id": hashlib.sha256(
                    (e["description"] + now).encode()).hexdigest()[:12],
                "family": "blindrun2_screen",
                "git_rev": REV,
                "notes": "operator self-screen; logged including abandoned attempts",
                "operator": "operator",
                "outcome": e["outcome"],
                "params": e["params"],
                "python": platform.python_version(),
                "reported": e["reported"],
                "status": e["status"],
                "test": "blindrun2",
                "ts_utc": now,
            }
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    after = sum(1 for _ in LOG.open())
    print(f"config_log.jsonl: {before} -> {after}  (+{after - before})")
    print(f"multiple-testing denominator now {after}")


if __name__ == "__main__":
    main()
