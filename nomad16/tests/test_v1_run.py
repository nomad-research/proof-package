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
    assert V.check_1a(json.dumps(dict(GOOD_1A, hedge_thesis="a 70% chance of a fall")), pk)[1] == "invalid"


def test_audit_checks_that_the_session_received_exactly_the_prepared_prompt(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text("\n".join([json.dumps({"type": "user", "message": {"role": "user", "content": "PROMPT TEXT\n"}}), line("assistant", "claude-opus-5-5")]))
    assert V.first_user_text(str(f)) == "PROMPT TEXT\n"
    assert V.audit_transcript(str(f), expect_prompt="PROMPT TEXT")["ok"]
    a = V.audit_transcript(str(f), expect_prompt="PROMPT TEXT, abbreviated by hand")
    assert not a["ok"] and a["prompt_matches_file"] is False
    g = tmp_path / "u.jsonl"
    g.write_text("\n".join([json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "A"}, {"type": "text", "text": "B"}]}}), line("assistant", "claude-opus-5-5")]))
    assert V.first_user_text(str(g)) == "AB"


def _read_transcript(tmp_path, path_read, returned, extra_tool=None, second_read=False):
    f = tmp_path / "r.jsonl"
    L = [json.dumps({"type": "user", "message": {"role": "user", "content": "Your task is in the file /p/x.txt. Read it."}}),
         json.dumps({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": path_read}}]}}),
         json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": returned}]}})]
    if second_read:
        L += [json.dumps({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": path_read}}]}}),
              json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": returned}]}})]
    if extra_tool:
        L.append(json.dumps({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "tool_use", "id": "t3", "name": extra_tool, "input": {}}]}}))
    L.append(line("assistant", "claude-opus-5-5"))
    f.write_text("\n".join(L))
    return str(f)


def test_audit_allows_exactly_one_read_of_the_prompt_file_and_checks_what_it_returned(tmp_path):
    prompt = "LINE ONE\nLINE TWO\n"
    ret = "     1\tLINE ONE\n     2\tLINE TWO\n"                                       # the Read tool's numbered format
    instr = ["Your task is in the file /p/x.txt. Read it."]
    ok = V.audit_transcript(_read_transcript(tmp_path, "/p/x.txt", ret), allowed_reads={"/p/x.txt": prompt}, expect_instructions=instr)
    assert ok["ok"] and ok["reads"] == {"/p/x.txt": 1} and ok["tool_calls"] == {}
    assert not V.audit_transcript(_read_transcript(tmp_path, "/repo/v1_pool.json", ret), allowed_reads={"/p/x.txt": prompt}, expect_instructions=instr)["ok"]     # any other file
    assert not V.audit_transcript(_read_transcript(tmp_path, "/p/x.txt", ret, extra_tool="Grep"), allowed_reads={"/p/x.txt": prompt})["ok"]                     # any other tool
    assert not V.audit_transcript(_read_transcript(tmp_path, "/p/x.txt", ret, second_read=True), allowed_reads={"/p/x.txt": prompt})["ok"]                      # the same chunk twice does not reproduce the prompt
    assert not V.audit_transcript(_read_transcript(tmp_path, "/p/x.txt", "     1\tSOMETHING ELSE\n"), allowed_reads={"/p/x.txt": prompt})["ok"]               # the file did not hold the prompt
    bad = V.audit_transcript(_read_transcript(tmp_path, "/p/x.txt", ret), allowed_reads={"/p/x.txt": prompt}, expect_instructions=["a different instruction"])
    assert not bad["ok"] and bad["instructions_match"] is False


def test_system_reminders_are_not_instructions_and_the_final_answer_comes_from_the_handback(tmp_path, monkeypatch):
    f = tmp_path / "agent-zzz.jsonl"
    f.write_text("\n".join([json.dumps({"type": "user", "message": {"role": "user", "content": "INSTRUCTION"}}),
                            json.dumps({"type": "user", "message": {"role": "user", "content": "<system-reminder>\nhand back via SubagentHandback</system-reminder>"}}),
                            json.dumps({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "tool_use", "id": "h1", "name": "SubagentHandback", "input": {"message": "{\"a\": 1}"}}]}})]))
    assert V.user_texts(str(f)) == ["INSTRUCTION"]
    monkeypatch.setattr(V, "find_transcript", lambda agent_id: str(f))
    assert V.final_answer("zzz") == '{"a": 1}'
    g = tmp_path / "agent-none.jsonl"; g.write_text(line("assistant", "claude-opus-5-5"))
    monkeypatch.setattr(V, "find_transcript", lambda agent_id: str(g))
    with pytest.raises(ValueError):
        V.final_answer("none")


def test_a_long_prompt_may_be_read_in_chunks_and_a_wrapped_follow_up_is_recognised(tmp_path):
    prompt = "L1\nL2\nL3\nL4\n"
    f = tmp_path / "c.jsonl"
    rd = lambda tid, n: json.dumps({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "tool_use", "id": tid, "name": "Read", "input": {"file_path": "/p/y.txt", "offset": n}}]}})
    res = lambda tid, txt: json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": txt}]}})
    f.write_text("\n".join([json.dumps({"type": "user", "message": {"role": "user", "content": "Your task is in the file /p/y.txt. Read it."}}),
                            rd("a", 1), res("a", "     1\tL1\n     2\tL2\n"), rd("b", 3), res("b", "     3\tL3\n     4\tL4\n"),
                            json.dumps({"type": "user", "message": {"role": "user", "content": "The coordinator sent a message while you were working:\nSecond instruction\n\nAddress this before completing your current task."}}),
                            line("assistant", "claude-opus-5-5")]))
    a = V.audit_transcript(str(f), allowed_reads={"/p/y.txt": prompt}, expect_instructions=["Your task is in the file /p/y.txt. Read it.", "Second instruction"])
    assert a["ok"] and a["reads"] == {"/p/y.txt": 2}
    assert not V.audit_transcript(str(f), allowed_reads={"/p/y.txt": "L1\nL2\nL3\nDIFFERENT\n"})["ok"]                # the chunks must reproduce the prompt exactly
