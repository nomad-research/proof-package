"""The pre-lock hook is the control (§27): it must refuse, not merely look in force."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[2] / "firewall" / "guard16.py"
EXAMPLE = "https" + "://example.org/page"


def run(tmp_path, state, tool, ti):
    phase = tmp_path / "phase.json"
    phase.write_text(json.dumps({"state": state}))
    env = dict(os.environ, NOMAD16_PHASE_FILE=str(phase), NOMAD16_GUARD_LOG=str(tmp_path / "log.jsonl"))
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_name": tool, "tool_input": ti}),
                       capture_output=True, text=True, env=env)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize("tool,ti,want", [
    ("WebSearch", {"query": "anything"}, "deny"),
    ("WebFetch", {"url": EXAMPLE}, "deny"),
    ("Bash", {"command": f"curl {EXAMPLE}"}, "deny"),
    ("Bash", {"command": "python3 -c 'import urllib.request'"}, "deny"),
    ("Bash", {"command": "python3 -m nomad16 pit_fetch '{\"source\":\"nrc_en\"}'"}, "allow"),
    ("Bash", {"command": f"python3 -m nomad16 round_status '{{}}' ; curl {EXAMPLE}"}, "deny"),
    ("Bash", {"command": "cat blindrun2/walk_log.md"}, "deny"),
    ("Bash", {"command": "git show origin/main:README.md"}, "deny"),
    ("Read", {"file_path": "/home/user/Nomad-Research/REPORT.md"}, "deny"),
    ("Read", {"file_path": "/home/user/Nomad-Research/docs/nomad_system_spec_v16_final.md"}, "allow"),
    ("Grep", {"pattern": "scram"}, "deny"),
    ("mcp__github__search_code", {}, "deny"),
    ("mcp__Claude_Code_Remote__create_session", {}, "deny"),
    ("Edit", {"file_path": "/home/user/Nomad-Research/firewall/guard16.py"}, "deny"),
    ("Write", {"file_path": "/home/user/Nomad-Research/config/appetite.json"}, "deny"),
    ("Write", {"file_path": "/home/user/Nomad-Research/rounds/R16-001/blind_pass.md"}, "allow"),
    ("Bash", {"command": "sed -i s/x/y/ nomad16/lock.py"}, "deny"),
    ("Bash", {"command": "git add rounds/R16-001 state/nomad16.db"}, "allow"),
    ("Bash", {"command": "git add rounds/R16-001 && git commit -m x && git push"}, "allow"),
    ("Bash", {"command": "git add rounds/R16-001 && cat state/nomad16.db"}, "deny"),
    ("Read", {"file_path": "/home/user/Nomad-Research/state/nomad16.db"}, "deny"),
    ("Bash", {"command": f"git commit -m 'x\n\nClaude-Session: {EXAMPLE}'"}, "allow"),
    ("Bash", {"command": f"git commit -m x && cu" + f"rl {EXAMPLE}"}, "deny"),
])
def test_closed_phase(tmp_path, tool, ti, want):
    assert run(tmp_path, "pre_lock", tool, ti) == want


def test_open_phase_allows_web(tmp_path):
    assert run(tmp_path, "live", "WebSearch", {"query": "x"}) == "allow"


def test_denials_are_logged_for_the_manifest(tmp_path):
    run(tmp_path, "pre_lock", "WebSearch", {"query": "x"})
    rows = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert rows[-1]["tool"] == "WebSearch" and rows[-1]["permitted"] is False and rows[-1]["at"]
