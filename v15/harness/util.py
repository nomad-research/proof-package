import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone

from .config import CORPORATE_SUFFIXES


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


_last_uuid7_ms = 0
_uuid7_seq = 0


def uuid7() -> str:
    """UUIDv7 text. Uses stdlib on 3.14+, otherwise a monotonic fallback."""
    if hasattr(uuid, "uuid7"):
        return str(uuid.uuid7())
    global _last_uuid7_ms, _uuid7_seq
    ms = time.time_ns() // 1_000_000
    if ms == _last_uuid7_ms:
        _uuid7_seq += 1
    else:
        _last_uuid7_ms, _uuid7_seq = ms, 0
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ms << 80) | (0x7 << 76) | ((_uuid7_seq & 0xFFF) << 64) | (0b10 << 62) | (rand & ((1 << 62) - 1))
    return str(uuid.UUID(int=value))


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def dumps(obj) -> str:
    """JSON for storage in TEXT columns (lists/dicts)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def loads(s):
    if s is None:
        return None
    return json.loads(s)


def normalise_name(s: str) -> str:
    """Names-book normalisation (§4.11): casefold, strip punctuation and corporate suffixes."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold().replace("&", " and ")
    s = s.replace(".", "")
    s = re.sub(r"[^\w\s]", " ", s)
    tokens = s.split()
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    while tokens and tokens[-1] in CORPORATE_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)
