#!/usr/bin/env python3
"""Primary fetch path for the blind run. Checks, fetches, logs.

Every document fetch is recorded per operating procedure section 6:
URL, document date, whether the clause was located.

This is the primary enforcement, not the hook. The hook is defence in depth:
project settings may be read at session start, so a mid-session hook edit
cannot be assumed live. This wrapper is live the moment it is written.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
FETCHED = HERE / "fetched"
LOG = HERE / "fetch_log.jsonl"
sys.path.insert(0, str(HERE))
from guard import _decide, _load  # noqa: E402


def fetch(url: str, doc_date: str | None = None, note: str = "") -> int:
    allow, deny = _load("allowlist.txt"), _load("denylist.txt")
    ok, why = _decide(urlparse(url).hostname, allow, deny)
    rec = {"ts_utc": datetime.now(timezone.utc).isoformat(), "url": url,
           "permitted": ok, "reason": why, "doc_date": doc_date, "note": note,
           "clause_located": None}
    if not ok:
        rec["outcome"] = "BLOCKED"
        _log(rec)
        print(f"BLOCKED: {why}")
        print("If this document is needed, ask the analyst for the URL and record "
              "the host in allowlist.txt with a reason.")
        return 2

    FETCHED.mkdir(parents=True, exist_ok=True)
    out = FETCHED / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".body")
    p = subprocess.run(["curl", "-sS", "-L", "--max-time", "90",
                        "-H", "User-Agent: nomad-research bato2912@gmail.com",
                        "-o", str(out), "-w", "%{http_code} %{size_download}", url],
                       capture_output=True, text=True)
    rec["curl_rc"] = p.returncode
    rec["http"] = p.stdout.strip()
    rec["saved_to"] = str(out)
    rec["outcome"] = "FETCHED" if p.returncode == 0 else "FETCH_FAILED"
    rec["sha256"] = (hashlib.sha256(out.read_bytes()).hexdigest()
                     if out.exists() else None)
    _log(rec)
    print(f"{rec['outcome']} http={rec['http']} -> {out}")
    if p.stderr.strip():
        print("stderr:", p.stderr.strip()[:300])
    return 0 if p.returncode == 0 else 1


def _log(rec):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fetch.py <url> [doc_date] [note]")
        sys.exit(64)
    sys.exit(fetch(sys.argv[1],
                   sys.argv[2] if len(sys.argv) > 2 else None,
                   " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""))
