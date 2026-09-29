"""Appetite and configuration. No verdict-governing number has a default (§17, §33).

``config/appetite.json`` holds every appetite value with its status:

* ``ratified``  — set by Rob.
* ``carried``   — carried from v15 / Event Requirements v3 as the spec lists it (§33.1).
* ``provisional_unratified`` — proposed by the builder so a round can run end to end,
  on the user's explicit instruction of 2026-09-29. **Any round that reads a
  provisional value is classed ``learning``** and never counts toward K9 or K13.

``get()`` refuses a missing key or a null value. There is no fallback anywhere.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .db import ROOT, canon, sha

APPETITE_PATH = Path(os.environ.get("NOMAD16_APPETITE") or ROOT / "config" / "appetite.json")
STATUSES = {"ratified", "carried", "provisional_unratified"}
LOGIC_VERSION = "v16"


class MissingAppetite(KeyError):
    """A verdict-governing value is missing. The harness refuses rather than defaults."""


_used: set[str] = set()


def _load(path: Path | None = None) -> dict:
    p = Path(path or APPETITE_PATH)
    if not p.exists():
        raise MissingAppetite(f"appetite file {p} does not exist")
    doc = json.loads(p.read_text())
    vals = doc.get("values")
    if not isinstance(vals, dict):
        raise MissingAppetite("appetite file has no 'values' table")
    for k, v in vals.items():
        if not isinstance(v, dict) or "value" not in v or v.get("status") not in STATUSES:
            raise MissingAppetite(f"appetite key {k} is malformed (needs value and a status in {sorted(STATUSES)})")
    return doc


def get(key: str, path: Path | None = None):
    vals = _load(path)["values"]
    if key not in vals or vals[key]["value"] is None:
        raise MissingAppetite(f"appetite value {key} is not set; the harness refuses to default it (§33)")
    _used.add(key)
    return vals[key]["value"]


def status(key: str, path: Path | None = None) -> str:
    vals = _load(path)["values"]
    if key not in vals:
        raise MissingAppetite(key)
    return vals[key]["status"]


def provisional_keys(path: Path | None = None) -> list[str]:
    return sorted(k for k, v in _load(path)["values"].items() if v["status"] == "provisional_unratified")


def used_keys() -> list[str]:
    return sorted(_used)


def config_hash(path: Path | None = None) -> str:
    return sha(canon(_load(path)))


def harness_version() -> str:
    here = Path(__file__).resolve().parent
    parts = []
    for f in sorted(here.glob("*.py")):
        parts.append(f.name + ":" + sha(f.read_bytes()))
    return sha("\n".join(parts))[:16]


def operator_model() -> str:
    """P0: DEFAULT_OPERATOR is removed. A round can't be admitted without it."""
    m = os.environ.get("NOMAD_OPERATOR_MODEL")
    if not m:
        raise MissingAppetite("NOMAD_OPERATOR_MODEL is not set; a round can't be admitted without "
                              "the operator model (§30.2 step 2)")
    return m
