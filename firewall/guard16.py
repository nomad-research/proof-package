#!/usr/bin/env python3
"""PreToolUse hook for Nomad v16 (spec §27 "Hooks", §9 time wall). Fails CLOSED.

The phase comes from ``state/phase.json``, written by the harness on every round-state
transition, so the hook and the harness always agree.

* **closed** (a round is ``admitted``, ``pre_lock`` or ``walking``):
  - WebSearch and WebFetch are denied outright. MCP tools are denied.
  - Bash is allowed when it is a single ``python -m nomad16 ...`` call: the harness itself
    bounds every read by the segment clock. Any other Bash that reaches the network,
    or that touches a quarantined path, is denied.
  - Read/Grep on quarantined paths is denied. Quarantined = material dated after
    2026-06-01 from earlier work in this repository (blind runs, fetched filings,
    the NRC page cache the harness enumerated from, the old guard logs, the record files).
* **open** (``live``/``scored``: the walk has ended): live retrieval is allowed.
* **idle** (no round in play): the blind-run policy of ``firewall/guard.py`` applies.

Every decision is logged to ``firewall/guard16_log.jsonl`` with its time and tool, which is
what ``operator_manifest`` reads to verify the hook is live (never asserted, §27).
"""
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOG = Path(os.environ.get("NOMAD16_GUARD_LOG") or HERE / "guard16_log.jsonl")
PHASE = Path(os.environ.get("NOMAD16_PHASE_FILE") or ROOT / "state" / "phase.json")

QUARANTINE = ["blindrun/", "blindrun2/", "firewall/fetched", "data/blindrun", "data/cache", "REPORT.md",
              "SUMMARY.md", "firewall/fetch_log.jsonl", "firewall/guard_log.jsonl", "firewall/guard16_log.jsonl",
              "config_log.jsonl", "methodology/", "tests_b3/", "firewall/hosts.backup", ".git/",
              "state/nomad16.db", "v15/", "lookbacks/"]
NET_TOOLS = re.compile(r"\b(curl|wget|httpie|nc|ncat|telnet|ssh|scp|rsync|lynx|w3m|links|aria2c|yt-dlp)\b")
URL_RE = re.compile(r"https?://")
CODE_NET = re.compile(r"\b(requests\.|urllib|urlopen|httpx|aiohttp|socket\.|fetch\(|axios)")
HARNESS = re.compile(r"^\s*(cd\s+\S+\s*&&\s*)?(NOMAD\w*=\S+\s+)*python3?\s+-m\s+nomad16(\s|$)")
CHAIN = re.compile(r"[;|`]|&&|\|\||\$\(|>\s*/")
# pre-lock the operator writes only under rounds/; the harness, config, docs, state and the
# firewall are protected (an operator who edits its own guard has no guard)
PROTECTED = ["nomad16/", "config/", "firewall/", ".claude/", "state/", "docs/", "STATE.md", "README.md"]
GIT_OK = re.compile(r"^\s*git\s+(add|commit|push|status|log\s+--oneline|diff\s+--stat)\b")
GIT_DENY = re.compile(r"\bgit\s+(show|log\s+.*-p|log\s+-p|fetch|pull|checkout|switch|cat-file|grep|blame|diff\s+\S*origin)")


def emit(permitted, reason, tool, payload=None):
    try:
        with open(LOG, "a") as fh:
            fh.write(json.dumps({"at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                 "tool": tool, "permitted": permitted, "reason": reason,
                                 "payload": payload}) + "\n")
    except Exception:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "allow" if permitted else "deny",
                                             "permissionDecisionReason": f"[nomad16-guard] {reason}"}}))
    sys.exit(0)


def phase():
    try:
        st = json.loads(PHASE.read_text()).get("state")
    except Exception:
        return "idle", None
    if st in {"admitted", "pre_lock", "walking"}:
        return "closed", st
    if st in {"live", "scored"}:
        return "open", st
    return "idle", st


def quarantined(text: str) -> str | None:
    t = text.replace(str(ROOT) + "/", "")
    for q in QUARANTINE:
        if q in t:
            return q
    return None


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except Exception as e:
        emit(False, f"FAIL-CLOSED: could not parse hook input ({e})", "?")
    tool = ev.get("tool_name") or ""
    ti = ev.get("tool_input") or {}
    ph, st = phase()
    if ph == "idle":
        # defer to the blind-run guard unchanged
        p = subprocess.run([sys.executable, str(HERE / "guard.py")], input=raw, capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        sys.exit(0)
    if ph == "open":
        emit(True, f"round is '{st}': live retrieval is open", tool)
    # ---- closed ----
    if tool in {"WebSearch", "WebFetch"}:
        emit(False, f"round is '{st}': {tool} is denied until the walk ends (spec §27 pre-lock hook). "
                    f"Use python -m nomad16 pit_fetch / alt_fetch, which are bounded by the clock.", tool,
             {"input": str(ti)[:300]})
    if tool.startswith("mcp__"):
        emit(False, f"round is '{st}': MCP tools are denied pre-lock", tool)
    if tool in {"Read", "Grep", "Glob", "NotebookEdit", "Edit", "Write"}:
        target = " ".join(str(ti.get(k, "")) for k in ("file_path", "path", "pattern", "glob", "notebook_path"))
        if tool in {"Edit", "Write", "NotebookEdit"}:
            rel = target.replace(str(ROOT) + "/", "").strip()
            if not rel.startswith("rounds/"):
                emit(False, f"round is '{st}': pre-lock the operator writes only under rounds/ "
                            f"(the harness, config, docs, state and firewall are protected)", tool, {"target": rel[:300]})
        q = quarantined(target)
        if q and tool != "Glob":
            emit(False, f"round is '{st}': {q} is quarantined pre-lock (post-cutoff material from earlier work)", tool,
                 {"target": target[:300]})
        if tool == "Grep" and not ti.get("path"):
            emit(False, f"round is '{st}': Grep must name a path outside the quarantine", tool)
        emit(True, "file tool on a permitted path", tool)
    if tool == "Bash":
        cmd = ti.get("command", "") or ""
        parts = [x for x in re.split(r"&&|\|\||;|\||`|\$\(", cmd) if x.strip()]
        git_only = bool(parts) and all(GIT_OK.search(x) for x in parts)
        if git_only:
            # add/commit/push/status read no content and fetch nothing; a URL inside a commit
            # message (the session trailer) is text, not egress
            emit(True, "plain git add/commit/push/status", tool)
        q = quarantined(cmd)
        if q:
            emit(False, f"round is '{st}': command touches quarantined {q}", tool, {"command": cmd[:300]})
        if not git_only and not HARNESS.search(cmd) and any(p in cmd for p in PROTECTED):
            emit(False, f"round is '{st}': command touches a protected path (harness, config, docs, state, "
                        f"firewall); read files with the Read tool", tool, {"command": cmd[:300]})
        if HARNESS.search(cmd) and not CHAIN.search(cmd.split("python", 1)[1] if "python" in cmd else cmd):
            emit(True, "single harness call; the harness bounds every read by the clock", tool)
        if URL_RE.search(cmd) or NET_TOOLS.search(cmd) or CODE_NET.search(cmd):
            emit(False, f"round is '{st}': network egress outside the harness is denied pre-lock", tool,
                 {"command": cmd[:300]})
        if GIT_DENY.search(cmd):
            emit(False, f"round is '{st}': git history/branch reads are denied pre-lock (other branches hold "
                        f"post-cutoff material)", tool, {"command": cmd[:300]})
        emit(True, "bash command with no detectable egress or quarantined path", tool)
    emit(True, f"{tool} is not a network tool", tool)


if __name__ == "__main__":
    main()
