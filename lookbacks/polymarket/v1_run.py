"""V1 run tooling (V1_prereg.md A13 to A15). The blind sessions are spawned from the orchestrating conversation; this file does everything around them:
prepares each prompt, ingests and validates each answer, audits each session's transcript (zero tool calls, declared model), and freezes all answers by hash before any scoring.

    python lookbacks/polymarket/v1_run.py prepare1a <event_id> [--rehearsal]
    python lookbacks/polymarket/v1_run.py ingest1a  <event_id> <answer_text_file> [--rehearsal]
    python lookbacks/polymarket/v1_run.py prepare1b <event_id> [--rehearsal]
    python lookbacks/polymarket/v1_run.py ingest1b  <event_id> <answer_text_file> [--rehearsal]
    python lookbacks/polymarket/v1_run.py ingest-agent <event_id> <1a|1b> <agent_id> [--rehearsal]     # takes the answer from the session's own transcript
    python lookbacks/polymarket/v1_run.py audit     <event_id> <stage 1a|1b> <agent_id> [--rehearsal]
    python lookbacks/polymarket/v1_run.py manifest  [--partial] [--rehearsal]
A rehearsal uses events outside the pool (contaminated by design) and never counts toward V1.
"""
import argparse, glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE))); sys.path.insert(0, HERE)
import v1_packet as K
import v1_pool as P
from nomad16 import pmgraph as G

DECLARED_MODEL = "claude-opus-5-5"
PROMPT_DIR = os.environ.get("V1_PROMPT_DIR", "/tmp/claude-0/v1_prompts")      # outside the repository, so the only file a session is pointed at holds nothing but its prompt
INSTRUCTION = "Your task is in the file {path}. Read that file (it is the only tool call you may make), then answer exactly as it instructs."
IGNORED_TOOLS = {"SubagentHandback"}
MAX_CHUNKS = 4                                    # reads of one prompt file allowed (a long prompt is read in pieces)            # how a spawned session hands its final answer back; not a tool the session used


def prompt_path(eid, stage, rehearsal=False):
    return os.path.join(PROMPT_DIR, f"{'rh_' if rehearsal else ''}R{eid}_{stage}.txt")


def publish_prompt(eid, stage, rehearsal=False):
    """Copy a prepared prompt to the neutral directory and return (path, the instruction to send). The session is sent the instruction, never the prompt text."""
    os.makedirs(PROMPT_DIR, exist_ok=True)
    src = open(os.path.join(rdir(eid, rehearsal), f"stage{stage}.txt")).read(); dst = prompt_path(eid, stage, rehearsal)
    open(dst, "w").write(src)
    return dst, INSTRUCTION.format(path=dst)


def rdir(eid, rehearsal=False):
    d = os.path.join(HERE, "packets_rehearsal" if rehearsal else "packets", f"R{eid}")
    os.makedirs(d, exist_ok=True)
    return d


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def extract_json(text):
    """The one JSON object in a session's reply (a fenced block, or the outermost braces). Raises ValueError if there is none."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise ValueError("no JSON object in the reply")
    return json.loads(t[i:j + 1])


def first_user_text(path):
    """The first user message of a transcript, as text: the prompt the session actually received."""
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return None


def user_texts(path):
    """The user-role messages that carry text (a tool result is not one): the instructions the session was actually sent."""
    out = []
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        if m.get("role") != "user":
            continue
        c = m.get("content")
        t = c if isinstance(c, str) else ("".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else "")
        if t and not t.lstrip().startswith("<system-reminder>"):           # the harness injects reminders as user turns; they are not instructions we sent
            t = re.sub(r"^The coordinator sent a message while you were working:\s*", "", t)                   # and wraps a follow-up message in a notice
            out.append(re.sub(r"\s*Address this before completing your current task\.\s*$", "", t))
    return out


def final_answer(agent_id):
    """The session's final report, exactly as handed back: the message of its last hand-back call. No copying by hand."""
    last = None
    for line in open(find_transcript(agent_id), encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        c = (o.get("message") or {}).get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "SubagentHandback":
                    last = (b.get("input") or {}).get("message")
    if last is None:
        raise ValueError("the session handed back nothing")
    return last


def read_results(path):
    """{tool_use_id: (file_path, text returned)} for every Read the session made; line-number prefixes of the Read tool are stripped."""
    calls, out = {}, {}
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        c = (o.get("message") or {}).get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "Read":
                calls[b["id"]] = (b.get("input") or {}).get("file_path")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                t = b.get("content")
                t = t if isinstance(t, str) else "".join(x.get("text", "") for x in t if isinstance(x, dict))
                out[b["tool_use_id"]] = (calls[b["tool_use_id"]], "\n".join(re.sub(r"^\s*\d+[\t→]", "", ln) for ln in t.splitlines()))
    return out


def audit_transcript(path, declared=DECLARED_MODEL, expect_prompt=None, allowed_reads=None, expect_instructions=None):
    """Blindness audit. Allowed: the hand-back, and (if ``allowed_reads`` maps a path to its prompt text) one Read of each of those paths whose returned text equals that
    prompt. Any other tool call fails the audit. Every assistant turn must be on the declared model. ``expect_instructions``: the exact user messages the session was sent."""
    allowed_reads = allowed_reads or {}
    """Zero tool calls (the hand-back excepted) and every assistant turn on the declared model. Also counts tokens, for sizing."""
    tools, models, tok_in, tok_out, n = {}, {}, 0, 0, 0
    raw = open(path, "rb").read()
    for line in raw.decode().splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        if m.get("role") == "assistant":
            n += 1
            if m.get("model"):
                models[m["model"]] = models.get(m["model"], 0) + 1
            u = m.get("usage") or {}
            tok_in += (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
            tok_out += u.get("output_tokens") or 0
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") not in IGNORED_TOOLS:
                    if b.get("name") == "Read" and (b.get("input") or {}).get("file_path") in allowed_reads:
                        continue                                  # the one permitted read; its content is checked below
                    tools[b["name"]] = tools.get(b["name"], 0) + 1
    got = first_user_text(path)
    prompt_ok = True if expect_prompt is None else (got is not None and got.strip() == expect_prompt.strip())
    # a long prompt is read in chunks: every Read of an allowed path is counted, and the chunks together must reproduce the prompt exactly
    reads = read_results(path); reads_ok = True; seen, chunks = {}, {}
    for tid, (fp, text) in reads.items():
        if fp in allowed_reads:
            seen[fp] = seen.get(fp, 0) + 1
            chunks.setdefault(fp, []).append(text)
    for fp, want in allowed_reads.items():
        if seen.get(fp, 0) and "\n".join(chunks[fp]).strip() != want.strip():
            reads_ok = False
        if seen.get(fp, 0) > MAX_CHUNKS:
            reads_ok = False
    instr_ok = True
    if expect_instructions is not None:
        ut = user_texts(path); instr_ok = [t.strip() for t in ut[:len(expect_instructions)]] == [t.strip() for t in expect_instructions]
    ok = not tools and set(models) == {declared} and prompt_ok and reads_ok and instr_ok
    return {"ok": ok, "prompt_matches_file": prompt_ok, "read_content_matches": reads_ok, "instructions_match": instr_ok, "reads": {k: v for k, v in seen.items()}, "tool_calls": tools, "models": models, "assistant_turns": n, "input_tokens": tok_in, "output_tokens": tok_out, "transcript_sha256": hashlib.sha256(raw).hexdigest()}


def find_transcript(agent_id):
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/*/subagents/agent-{agent_id}.jsonl"))
    if not hits:
        raise FileNotFoundError(f"no transcript for agent {agent_id}")
    return hits[0]


def check_1a(text, packet):
    """(answer, status, errors). status: ok | void_recall | invalid."""
    try:
        obj = extract_json(text)
    except ValueError as e:
        return None, "invalid", [str(e)]
    errs = K.validate_1a(obj, packet)
    if errs:
        return obj, "invalid", errs
    return obj, ("void_recall" if obj["recalls_outcome"] else "ok"), []


def check_1b(text, pk1, pk2):
    try:
        obj = extract_json(text)
    except ValueError as e:
        return None, "invalid", [str(e)]
    errs = K.validate_1b(obj, pk1, pk2)
    if errs:
        return obj, "invalid", errs
    return obj, ("void_recall" if obj["recalls_outcome"] else "ok"), []


# ------------------------------------------------------------------ rounds
def round_row(eid, rehearsal):
    if not rehearsal:
        return {e["id"]: e for e in json.load(open(os.path.join(HERE, "v1_pool.json")))}[eid], json.load(open(os.path.join(HERE, "v1_pool_market_dates.json")))
    path = os.path.join(HERE, "packets_rehearsal", "rows.json"); os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = json.load(open(path)) if os.path.exists(path) else {}
    if eid not in rows:
        raw = P.page(f"{P.GAMMA}/{eid}")
        c = P.compact(raw); st = G.structure(c)
        c["class"] = st["class"]; c["ladder_kind"] = st.get("kind"); c["group"] = P.group(c)
        c["mkt_closed"] = {m.get("conditionId"): {"closed": m.get("closedTime")} for m in raw.get("markets", [])}
        rows[eid] = c; json.dump(rows, open(path, "w"))
    return rows[eid], rows[eid]["mkt_closed"]


def prepare1a(eid, rehearsal=False):
    e, mkt = round_row(eid, rehearsal); lock = K.lock_of(e)
    pk, pv, flags = K.stage1a(e, lock, K.price_fn_live, mkt)
    idx = K.load_index(); rows = K.live_rows(idx, lock); tpl = G.template(e["title"])
    live = len({G.template(r["title"]) for r in rows if r["id"] != eid} - {tpl})
    d = rdir(eid, rehearsal)
    open(f"{d}/stage1a.txt", "w").write(K.prompt_1a(pk)); json.dump(pk, open(f"{d}/stage1a.json", "w"), indent=1); json.dump(pv, open(f"{d}/private_1a.json", "w"), indent=1)
    meta = {"packet_sha256": sha(pk), "lock": lock, "as_of": pk["as_of"], "contracts_shown": len(pk["event"]["contracts"]), "of": len(e["markets"]), "leak_flags": flags,
            "live_templates": live, "ok": len(pk["event"]["contracts"]) >= 3 and not flags and live >= K.MIN_MENU_TEMPLATES}
    if not meta["ok"]:
        meta["replace_reason"] = [r for r, bad in (("shows fewer than 3 contracts", len(pk["event"]["contracts"]) < 3), ("leak flag", bool(flags)), ("fewer than 10 live templates", live < K.MIN_MENU_TEMPLATES)) if bad]
    json.dump(meta, open(f"{d}/meta_1a.json", "w"), indent=1)
    meta["instruction"] = publish_prompt(eid, "1a", rehearsal)[1]
    return meta


def ingest(eid, stage, text, rehearsal=False):
    d = rdir(eid, rehearsal); pk1 = json.load(open(f"{d}/stage1a.json"))
    obj, status, errs = check_1a(text, pk1) if stage == "1a" else check_1b(text, pk1, json.load(open(f"{d}/stage1b.json")))
    rec = {"status": status, "errors": errs}
    if obj is not None and status in ("ok", "void_recall"):
        json.dump(obj, open(f"{d}/answer_{stage}.json", "w"), indent=1); rec["answer_sha256"] = sha(obj)
    json.dump(rec, open(f"{d}/ingest_{stage}.json", "w"), indent=1)
    return rec


def prepare1b(eid, rehearsal=False):
    e, _ = round_row(eid, rehearsal); d = rdir(eid, rehearsal); lock = K.lock_of(e)
    ans = json.load(open(f"{d}/answer_1a.json")); pk1 = json.load(open(f"{d}/stage1a.json"))
    pk, pv, st = K.stage1b(K.load_index(), [t.lower() for t in ans["search_terms"]], lock, G.template(e["title"]), f"R{eid}", K.price_fn_live, exclude_id=eid)
    json.dump(pk, open(f"{d}/stage1b.json", "w"), indent=1); json.dump(pv, open(f"{d}/private_1b.json", "w"), indent=1); json.dump(dict(st, packet_sha256=sha(pk)), open(f"{d}/meta_1b.json", "w"), indent=1)
    if st["empty_menu"]:                    # nothing to choose from: recorded as 'no instrument', unscored, not replaced
        json.dump({"hedges": [], "no_instrument": True, "recalls_outcome": False, "auto": "empty menu"}, open(f"{d}/answer_1b.json", "w"), indent=1)
        return dict(st, auto_no_instrument=True)
    open(f"{d}/stage1b.txt", "w").write(K.prompt_1b(pk1, ans, pk))
    return dict(st, instruction=publish_prompt(eid, "1b", rehearsal)[1])


def audit(eid, stage, agent_id, rehearsal=False):
    d = rdir(eid, rehearsal); stages = ["1a"] if stage == "1a" else ["1a", "1b"]
    allowed = {prompt_path(eid, st, rehearsal): open(os.path.join(d, f"stage{st}.txt")).read() for st in stages}
    instr = [INSTRUCTION.format(path=prompt_path(eid, st, rehearsal)) for st in stages]
    a = audit_transcript(find_transcript(agent_id), allowed_reads=allowed, expect_instructions=instr); a["agent_id_sha256"] = hashlib.sha256(agent_id.encode()).hexdigest()[:16]
    json.dump(a, open(os.path.join(rdir(eid, rehearsal), f"audit_{stage}.json"), "w"), indent=1)
    return a


def manifest(partial=False, rehearsal=False):
    base = os.path.join(HERE, "packets_rehearsal" if rehearsal else "packets")
    ids = [d[1:] for d in sorted(os.listdir(base)) if d.startswith("R")] if os.path.isdir(base) else []
    if not rehearsal and not partial:
        want = json.load(open(os.path.join(HERE, "v1_rounds.json")))["rounds"]
        missing = [w for w in want if w not in ids or not os.path.exists(os.path.join(rdir(w), "answer_1b.json"))]
        if missing:
            raise SystemExit(f"rounds without a final answer: {missing}; use --partial to freeze what exists")
    out = {}
    for i in ids:
        d = rdir(i, rehearsal); e = {}
        for f in ("meta_1a.json", "answer_1a.json", "meta_1b.json", "answer_1b.json", "audit_1a.json", "audit_1b.json", "ingest_1a.json", "ingest_1b.json"):
            p = os.path.join(d, f)
            if os.path.exists(p):
                e[f] = sha(json.load(open(p)))
        out[i] = e
    m = {"rehearsal": rehearsal, "partial": partial, "rounds": out, "sha256": sha(out)}
    json.dump(m, open(os.path.join(HERE, "v1_answers_manifest_rehearsal.json" if rehearsal else "v1_answers_manifest.json"), "w"), indent=1)
    return {"rounds": len(out), "sha256": m["sha256"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); ap.add_argument("--rehearsal", action="store_true"); ap.add_argument("--partial", action="store_true")
    a = ap.parse_args(); r = a.rehearsal
    if a.cmd == "prepare1a":
        print(json.dumps(prepare1a(a.args[0], r), indent=1))
    elif a.cmd in ("ingest1a", "ingest1b"):
        print(json.dumps(ingest(a.args[0], a.cmd[-2:], open(a.args[1]).read(), r), indent=1))
    elif a.cmd == "ingest-agent":          # ingest-agent <event_id> <1a|1b> <agent_id>
        eid, stage, agent = a.args
        txt = final_answer(agent); open(os.path.join(rdir(eid, r), f"reply_{stage}.txt"), "w").write(txt)
        print(json.dumps(ingest(eid, stage, txt, r), indent=1))
    elif a.cmd == "prepare1b":
        print(json.dumps(prepare1b(a.args[0], r), indent=1))
    elif a.cmd == "audit":
        print(json.dumps(audit(a.args[0], a.args[1], a.args[2], r), indent=1))
    elif a.cmd == "manifest":
        print(json.dumps(manifest(a.partial, r), indent=1))
