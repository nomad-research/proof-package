"""V1 run tooling: JSON extraction, the transcript audit, and answer checks. Synthetic; no network."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lookbacks", "polymarket"))
import v1_packet as K  # noqa: E402
import v1_run as V  # noqa: E402
from nomad16.tests.test_v1_packet import GOOD_1A, LOCK, PRIMARY  # noqa: E402


def test_extract_json_from_a_fence_prose_or_nothing():
    assert V.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert V.extract_json('Here is my answer:\n{"a": {"b": 2}}\nThanks') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        V.extract_json("no braces here")
    with pytest.raises(ValueError):
        V.extract_json("{not json}")


def line(role, model=None, blocks=None, usage=None):
    return json.dumps({"type": role, "message": {"role": role, "model": model, "content": blocks or [{"type": "text", "text": "x"}], "usage": usage or {}}})


def test_audit_requires_zero_tool_calls_and_the_declared_model(tmp_path):
    ok = tmp_path / "ok.jsonl"
    ok.write_text("\n".join([line("user"), line("assistant", "claude-opus-5-5", usage={"input_tokens": 100, "output_tokens": 20}),
                             line("assistant", "claude-opus-5-5", [{"type": "tool_use", "name": "SubagentHandback"}], {"input_tokens": 5, "output_tokens": 3})]))
    a = V.audit_transcript(str(ok))
    assert a["ok"] and a["tool_calls"] == {} and a["input_tokens"] == 105 and a["output_tokens"] == 23 and a["assistant_turns"] == 2
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join([line("assistant", "claude-opus-5-5", [{"type": "tool_use", "name": "Grep"}])]))
    a = V.audit_transcript(str(bad)); assert not a["ok"] and a["tool_calls"] == {"Grep": 1}
    wrong = tmp_path / "wrong.jsonl"
    wrong.write_text(line("assistant", "claude-sonnet-5-5"))
    assert not V.audit_transcript(str(wrong))["ok"]
    mixed = tmp_path / "mixed.jsonl"
    mixed.write_text("\n".join([line("assistant", "claude-opus-5-5"), line("assistant", "claude-haiku-4-5-20251001")]))
    assert not V.audit_transcript(str(mixed))["ok"]


def test_answer_checks_ok_recall_and_invalid():
    pk, _, _ = K.stage1a(PRIMARY, LOCK, lambda t, l: True, {})
    obj, st, errs = V.check_1a("```json\n" + json.dumps(GOOD_1A) + "\n```", pk)
    assert st == "ok" and errs == [] and obj["search_terms"][0] == "bitcoin"
    recall = dict(GOOD_1A, recalls_outcome=True)
    assert V.check_1a(json.dumps(recall), pk)[1] == "void_recall"
    assert V.check_1a("I think the Fed holds", pk)[1] == "invalid"
    bad = dict(GOOD_1A, search_terms=["only"])
    assert V.check_1a(json.dumps(bad), pk)[1] == "invalid"
    assert V.check_1a(json.dumps(dict(GOOD_1A, hedge_thesis="70% chance of a fall")), pk)[1] == "invalid"
