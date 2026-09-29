"""Small shared helpers: time, float normalisation for hashing, network through curl."""
from __future__ import annotations

import math
import subprocess

import pandas as pd

from .db import Refused, canon, sha

BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) nomad16-harness"


def ts(s) -> pd.Timestamp:
    """Parse a date or datetime into a UTC-aware Timestamp. Date-only means 00:00 UTC."""
    if s is None or s == "":
        raise Refused("a time value is required and was empty")
    t = pd.Timestamp(s)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert("UTC")


def le(a, b) -> bool:
    """a <= b, with None on the left read as 'unknown' (False)."""
    if a is None or a == "":
        return False
    return ts(a) <= ts(b)


def day(s) -> str:
    return ts(s).strftime("%Y-%m-%d")


def norm(x, sig: int = 10):
    """Round floats recursively so an object's hash is stable across platforms."""
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return str(x)
        return float(f"{x:.{sig}g}")
    if isinstance(x, dict):
        return {str(k): norm(v, sig) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [norm(v, sig) for v in x]
    if hasattr(x, "tolist") and getattr(x, "ndim", 0) > 0:  # numpy array
        return norm(x.tolist(), sig)
    if hasattr(x, "item"):  # numpy scalar
        return norm(x.item(), sig)
    return x


def ohash(obj) -> str:
    return sha(canon(norm(obj)))


def curl(url: str, ua: str = BROWSER_UA, timeout: int = 90, binary: bool = False):
    """Fetch through curl (it honours the session proxy). Raises on failure: no silent swallow."""
    p = subprocess.run(["curl", "-sS", "-L", "--max-time", str(timeout), "-A", ua,
                        "-w", "\n__HTTP_STATUS__%{http_code}", url],
                       capture_output=True)
    if p.returncode != 0:
        raise Refused(f"fetch failed rc={p.returncode} for {url}: {p.stderr[:200].decode(errors='replace')}")
    body, _, code = p.stdout.rpartition(b"\n__HTTP_STATUS__")
    code = int(code or 0)
    if code >= 400:
        raise Refused(f"fetch returned HTTP {code} for {url}")
    return body if binary else body.decode("utf-8", errors="replace")
