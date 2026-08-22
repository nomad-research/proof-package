"""Log the chronological walk to config_log.jsonl."""

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

params = {
    "run": "blindrun2", "step": "chronological_walk",
    "D": "2026-06-01", "trigger_end": "2026-07-15",
    "criteria": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8a", "Q8b"],
    "application_order": "numerical, first failure recorded",
    "tie_break": "(filing_date, accession)",
    "pool": 175,
}
outcome = {
    "verdict": "NOT OPERABLE",
    "stop_condition": "spec v2 7.4 first clause -- no event satisfies Q1-Q8b",
    "candidates_walked": 175, "qualifiers": 0, "unresolved": 0,
    "first_failure_counts": {"Q1": 99, "Q7": 37, "Q2": 34, "Q3": 5},
    "reached_Q4_or_beyond": 0,
    "edges_attempted": 0,
    "quarantine_rate": "undefined -- terminated at the screen, before edge mapping",
    "prediction_sealed": False,
    "outcome_data_touched": False,
    "documents_opened": 175, "post_fire_filings_opened": 0, "websearch_calls": 0,
    "robustness": {
        "withdraw_Q7": "37/37 still rejected (34 on Q8a, 3 on Q1/Q2)",
        "withdraw_Q2": "34/34 still rejected (on Q7)",
        "verdict_depends_on_either": False,
    },
}

now = datetime.now(timezone.utc).isoformat()
rec = {
    "config_hash": hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16],
    "description": "blindrun2 chronological walk: 175 candidates, 0 qualifiers, NOT OPERABLE",
    "eval_id": hashlib.sha256(("blindrun2_walk" + now).encode()).hexdigest()[:12],
    "family": "blindrun2_screen", "git_rev": REV,
    "notes": "operator self-screened; no event selected, so no prediction sealed "
             "and no outcome data touched",
    "operator": "operator", "outcome": outcome, "params": params,
    "python": platform.python_version(), "reported": True,
    "status": "completed", "test": "blindrun2", "ts_utc": now,
}
before = sum(1 for _ in LOG.open())
with LOG.open("a") as fh:
    fh.write(json.dumps(rec, sort_keys=True) + "\n")
after = sum(1 for _ in LOG.open())
print(f"config_log.jsonl: {before} -> {after}")
print(f"multiple-testing denominator now {after}")
