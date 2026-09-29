"""Claude Code PreToolUse hook (§5 enforcement (c), A8): deny every retrieval surface unless a round is `open`.

Retrieval surfaces: WebSearch, WebFetch, and every MCP tool (mcp__<server>__<tool>) except servers listed in
config.HOOK_ALLOWED_MCP_SERVERS (the harness itself, session plumbing, local viewers). Each denial is appended to the
hook_denials ledger. Allows silently when NOMAD_HARNESS_HOOK_OFF is set or the DB does not exist.
The chat surface has no hook: there the wall is a promise.
"""
import json
import os
import sqlite3
import sys

from .config import HOOK_ALLOWED_MCP_SERVERS

BUILTIN_RETRIEVAL = {"WebSearch", "WebFetch"}


def is_retrieval_tool(name: str) -> bool:
    if name in BUILTIN_RETRIEVAL:
        return True
    if name.startswith("mcp__"):
        server = name[5:].split("__", 1)[0]
        return server not in HOOK_ALLOWED_MCP_SERVERS
    return False


def decide(db_path: str, tool_name: str) -> dict | None:
    """None = allow; dict = deny payload. Logs the denial."""
    if not is_retrieval_tool(tool_name):
        return None
    if not os.path.exists(db_path):
        return None
    try:
        from .db import append, connect
        conn = connect(db_path)
        # v11 §E: rounds run concurrently. The wall is that nothing is pre-lock, not that something is open:
        # a round in created or locked could still be contaminated, so any retrieval is denied while one exists.
        pre_lock = [r[0] for r in conn.execute("SELECT round_id FROM round_state WHERE state IN ('created','locked')")]
        live = [r[0] for r in conn.execute("SELECT round_id FROM round_state WHERE state = 'open'")]
        # v12 0.4: `partially_scored` no longer opens general retrieval — that is the hole round 11 fell through.
        # Retrieval there is permitted only inside an open scoring session, and every fetch is answerable to a due call.
        sessions = [r[0] for r in conn.execute("SELECT id FROM scoring_sessions WHERE closed_at IS NULL")]
        if not pre_lock and (live or sessions):
            return None
        if not pre_lock and not live and not sessions:
            partial = [r[0] for r in conn.execute("SELECT round_id FROM round_state WHERE state = 'partially_scored'")]
            if partial:
                reason = (f"Nomad firewall: {tool_name} is denied because no scoring session is open. Round(s) {partial} are "
                          "partially scored: open a session for the calls you are scoring with nomad_open_scoring(round_id, call_ids), "
                          "which stamps every fetch against a due call, then close it. Set NOMAD_HARNESS_HOOK_OFF=1 to search outside a round.")
                append(conn, "hook_denials", {"round_id": partial[0], "tool": tool_name, "reason": reason})
                return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                               "permissionDecisionReason": reason}}
        if pre_lock:
            reason = (f"Nomad firewall: {tool_name} is denied because round(s) {pre_lock} are pre-lock (created or locked). "
                      "Lock predictions and call nomad_open_retrieval on them first; retrieval anywhere contaminates a "
                      "round that has not locked. Set NOMAD_HARNESS_HOOK_OFF=1 to search outside a round.")
            round_id = pre_lock[0]
        else:
            latest = conn.execute(
                "SELECT round_id, state FROM round_state WHERE state != 'void' ORDER BY state_changed_at DESC LIMIT 1").fetchone()
            where = f"latest round {latest[0]} is '{latest[1]}'" if latest else "no rounds exist"
            reason = (f"Nomad firewall: {tool_name} is denied because no round is live ({where}). "
                      "Submit and lock a round, then nomad_open_retrieval. Set NOMAD_HARNESS_HOOK_OFF=1 to search outside a round.")
            round_id = latest[0] if latest else None
        append(conn, "hook_denials", {"round_id": round_id, "tool": tool_name, "reason": reason})
    except sqlite3.Error as e:
        reason = f"nomad harness DB unreadable ({e}); refusing retrieval"
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main() -> int:
    if os.environ.get("NOMAD_HARNESS_HOOK_OFF"):
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    db = os.environ.get("NOMAD_HARNESS_DB") or os.path.join(project, "nomad_harness.db")
    out = decide(db, str(payload.get("tool_name", "")))
    if out:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
