"""Append-only evaluation log (spec section 1.2).

Every parameter combination, universe filter, window length and threshold that is
ever *evaluated* must land here -- not only the ones that get reported. The line
count of this file is the denominator for multiple-testing correction, so an
evaluation that is run and then abandoned is exactly the kind of record that must
not be dropped.

The file is opened in append mode and flushed per record. It is never rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

DEFAULT_LOG = Path(__file__).resolve().parents[2] / "config_log.jsonl"

_LOCK = threading.Lock()
_GIT_REV: str | None = None


def _git_rev() -> str:
    global _GIT_REV
    if _GIT_REV is None:
        try:
            _GIT_REV = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=Path(__file__).resolve().parents[2],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            _GIT_REV = "unknown"
    return _GIT_REV


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def config_hash(params: dict[str, Any]) -> str:
    """Stable hash of a parameter set, used to spot re-evaluations of the same config."""
    return hashlib.sha256(_canonical(params).encode()).hexdigest()[:16]


class ConfigLogger:
    """Append-only JSONL evaluation logger.

    Usage::

        log = ConfigLogger(test="A")
        with log.evaluation(params={"window": 30}, description="overnight reversal") as ev:
            ev.record(t_stat=2.1, n_obs=4000)

    The context manager guarantees a line is written even if the evaluation raises,
    which is the point: a crashed or abandoned run still consumed a researcher
    degree of freedom and still counts towards the trial denominator.
    """

    def __init__(self, test: str, path: str | os.PathLike[str] = DEFAULT_LOG, operator: str | None = None):
        self.test = test
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.operator = operator or os.environ.get("NOMAD_OPERATOR", "unspecified")

    def _write(self, record: dict[str, Any]) -> None:
        line = _canonical(record)
        with _LOCK:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())

    def log(
        self,
        params: dict[str, Any],
        *,
        description: str = "",
        outcome: dict[str, Any] | None = None,
        reported: bool = False,
        status: str = "completed",
        notes: str = "",
        family: str | None = None,
    ) -> str:
        """Write one evaluation record. Returns the evaluation id."""
        eval_id = uuid.uuid4().hex[:12]
        self._write(
            {
                "eval_id": eval_id,
                "ts_utc": datetime.now(timezone.utc).isoformat(),
                "test": self.test,
                "description": description,
                "params": params,
                "config_hash": config_hash(params),
                "outcome": outcome or {},
                "reported": reported,
                "status": status,
                "notes": notes,
                "family": family,
                "git_rev": _git_rev(),
                "operator": self.operator,
                "python": platform.python_version(),
            }
        )
        return eval_id

    def evaluation(self, params: dict[str, Any], **kw: Any) -> "_Evaluation":
        return _Evaluation(self, params, **kw)


class _Evaluation:
    def __init__(self, logger: ConfigLogger, params: dict[str, Any], **kw: Any):
        self.logger = logger
        self.params = params
        self.kw = kw
        self.outcome: dict[str, Any] = {}
        self.reported = bool(kw.pop("reported", False))

    def record(self, **outcome: Any) -> None:
        self.outcome.update(outcome)

    def mark_reported(self) -> None:
        self.reported = True

    def __enter__(self) -> "_Evaluation":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        status = "completed" if exc_type is None else f"failed:{exc_type.__name__}"
        notes = self.kw.pop("notes", "")
        if exc is not None:
            notes = (notes + " | " + str(exc)).strip(" |")
        self.logger.log(
            self.params,
            outcome=self.outcome,
            reported=self.reported,
            status=status,
            notes=notes,
            **self.kw,
        )
        return False  # never swallow


def read_log(path: str | os.PathLike[str] = DEFAULT_LOG) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def trial_count(path: str | os.PathLike[str] = DEFAULT_LOG, test: str | None = None) -> int:
    """Number of evaluations -- the N that goes into the Deflated Sharpe Ratio.

    Counts every record, including failed and unreported ones. That is deliberate.
    """
    records = read_log(path)
    if test is not None:
        records = [r for r in records if r.get("test") == test]
    return len(records)


def trial_sharpes(path: str | os.PathLike[str] = DEFAULT_LOG, test: str | None = None,
                  key: str = "sharpe") -> list[float]:
    """Sharpe ratios observed across logged trials, for the variance term in the DSR."""
    records = read_log(path)
    if test is not None:
        records = [r for r in records if r.get("test") == test]
    vals = []
    for r in records:
        v = r.get("outcome", {}).get(key)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return vals


def iter_log(path: str | os.PathLike[str] = DEFAULT_LOG) -> Iterator[dict[str, Any]]:
    yield from read_log(path)


def summarise(path: str | os.PathLike[str] = DEFAULT_LOG) -> dict[str, Any]:
    records = read_log(path)
    by_test: dict[str, int] = {}
    for r in records:
        by_test[r.get("test", "?")] = by_test.get(r.get("test", "?"), 0) + 1
    return {
        "total_evaluations": len(records),
        "by_test": by_test,
        "reported": sum(1 for r in records if r.get("reported")),
        "failed": sum(1 for r in records if str(r.get("status", "")).startswith("failed")),
        "distinct_configs": len({r.get("config_hash") for r in records}),
    }
