#!/usr/bin/env python3
"""PreToolUse hook: contamination firewall for the Nomad blind run.

Fails CLOSED. Any parse error, any unrecognised shape, any doubt -> deny.
A firewall that fails open is not a firewall.

Enforces, per operating procedure v1 section 1.1:
  - WebSearch is denied unconditionally. There is no argument that unblocks it.
  - WebFetch is denied unless the host matches firewall/allowlist.txt and does
    not match firewall/denylist.txt.
  - Bash commands are scanned for network egress (any http(s) URL, or a
    network tool) and the same host rules are applied.
  - Any MCP tool whose name implies search is denied.

Rationale for banning search while permitting fetch: a search result set
carries post-dated material in snippets even when the target document predates
the fire date. One snippet describing what happened afterwards contaminates the
run and cannot be un-seen.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
LOG = HERE / "guard_log.jsonl"

NET_TOOLS = re.compile(r"\b(curl|wget|http|https|httpie|nc|ncat|telnet|ssh|scp|rsync|"
                       r"lynx|w3m|links|aria2c|youtube-dl|yt-dlp)\b")
URL_RE = re.compile(r"https?://([A-Za-z0-9._~%-]+(?::\d+)?)")
# python/node one-liners that could reach the network without a literal URL
CODE_NET = re.compile(r"\b(requests\.|urllib|urlopen|httpx|aiohttp|socket\.|fetch\(|axios)")


def _load(name):
    p = HERE / name
    out = []
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.split("#", 1)[0].strip().lower()
            if line:
                out.append(line)
    return out


def _decide(host, allow, deny):
    """Return (permitted: bool, reason: str) for one hostname."""
    h = (host or "").lower().split(":")[0].strip(".")
    if not h:
        return False, "no host could be parsed"
    for d in deny:
        if h == d or h.endswith("." + d):
            return False, f"host {h} matches denylist entry {d}"
    for a in allow:
        if h == a or h.endswith("." + a):
            return True, f"host {h} matches allowlist entry {a}"
    return False, f"host {h} is not on the allowlist"


def emit(permitted, reason, payload=None):
    try:
        with open(LOG, "a") as fh:
            fh.write(json.dumps({"permitted": permitted, "reason": reason,
                                 "payload": payload}) + "\n")
    except Exception:
        pass
    decision = "allow" if permitted else "deny"
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": f"[nomad-firewall] {reason}",
    }}))
    sys.exit(0)


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except Exception as e:
        emit(False, f"FAIL-CLOSED: could not parse hook input ({e})")

    tool = ev.get("tool_name") or ""
    ti = ev.get("tool_input") or {}
    allow, deny = _load("allowlist.txt"), _load("denylist.txt")

    # 1. search is never permitted
    if tool == "WebSearch":
        emit(False, "WebSearch is banned for the entire blind run. Search result "
                    "snippets leak post-dated material even when the target document "
                    "predates the fire date. Ask the analyst for the URL instead.")
    if tool.startswith("mcp__") and re.search(r"search|discover|find_", tool, re.I):
        emit(False, f"{tool} is a search-shaped tool; banned for the blind run.")

    # 2. direct fetch
    if tool == "WebFetch":
        url = ti.get("url", "")
        ok, why = _decide(urlparse(url).hostname, allow, deny)
        emit(ok, why + (" | fetch permitted" if ok else
                        " | not permitted. If you need this document, ask the analyst for "
                        "the URL and add the host to allowlist.txt with a recorded reason."),
             {"url": url})

    # 3. bash egress
    if tool == "Bash":
        cmd = ti.get("command", "") or ""
        hosts = URL_RE.findall(cmd)
        if hosts:
            for h in hosts:
                ok, why = _decide(h, allow, deny)
                if not ok:
                    emit(False, f"bash network egress blocked: {why}", {"command": cmd[:400]})
            emit(True, f"bash egress to allowlisted host(s): {', '.join(sorted(set(hosts)))}")
        # network tool or networking code with no literal URL -> cannot verify -> deny
        if NET_TOOLS.search(cmd) or CODE_NET.search(cmd):
            emit(False, "FAIL-CLOSED: command appears to reach the network but no URL could "
                        "be extracted to check against the allowlist. Route fetches through "
                        "firewall/fetch.py, which logs and checks them.",
                 {"command": cmd[:400]})
        emit(True, "bash command has no detectable network egress")

    emit(True, f"{tool} is not a network tool")


if __name__ == "__main__":
    main()
