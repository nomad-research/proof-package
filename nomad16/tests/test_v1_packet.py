"""V1 packet builder: what a blind session may see, leak scan, eligibility, seeded retrieval, answer validators. Synthetic; no network."""
import datetime
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lookbacks", "polymarket"))
import v1_packet as K  # noqa: E402

DAY = 86400
T0 = 1_780_000_000                     # an arbitrary start; the lock is the midpoint
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mk(i, q, git=None, mclosed=None):
    return {"cid": f"0xcond{i}", "tokens": [f"tokyes{i}", f"tokno{i}"], "q": q, "git": git, "gthr": str(i).split("_")[-1], "nro": False, "mclosed": mclosed, "description": None}


def event(eid, title, tags, qs, cls="ladder", start=T0, closed=T0 + 20 * DAY, desc="This market will resolve to Yes if the level is reached.", neg=False):
    return {"id": str(eid), "title": title, "tags": tags, "start": iso(start), "closed_time": iso(closed) if closed else None, "negRisk": neg, "class": cls,
            "description": desc, "markets": [mk(f"{eid}_{k}", q) for k, q in enumerate(qs)]}


PRIMARY = event(1, "Fed decision in October?", ["fed", "economy"], ["Will the Fed cut 25?", "Will the Fed hold?", "Will the Fed hike?"], cls="partition_exact", neg=True)
LOCK = K.lock_of(PRIMARY)


BANNED_KEYS = {"price", "prices", "volume", "liquidity", "cid", "token_yes", "token_no", "tokens", "closed", "closed_time", "mclosed", "final", "outcome", "outcomes", "end", "uma", "fee", "feeschedule"}


def keys_of(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield str(k).lower()
            yield from keys_of(v)
    elif isinstance(o, list):
        for v in o:
            yield from keys_of(v)


def test_the_lock_is_the_midpoint_and_the_packet_shows_no_id_price_or_status():
    assert LOCK == T0 + 10 * DAY
    pk, pv, flags = K.stage1a(PRIMARY, LOCK, lambda tok, lock: True, {})
    blob = json.dumps(pk).lower()
    assert not (set(keys_of(pk)) & BANNED_KEYS) and "0xcond" not in blob and "tokyes" not in blob and "tokno" not in blob
    assert [c["label"] for c in pk["event"]["contracts"]] == ["C1", "C2", "C3"] and pk["as_of"] == K.as_of(LOCK) and flags == []
    assert pv["C2"]["cid"] == "0xcond1_1" and pv["C2"]["token_yes"] == "tokyes1_1"          # the map exists, privately


def test_only_contracts_that_could_be_traded_at_the_lock_are_shown():
    priced = {"tokyes1_0", "tokyes1_2"}                                                       # no price for the middle one
    mkt = {"0xcond1_2": {"closed": iso(LOCK - DAY)}}                                            # the last one had already closed
    pk, pv, _ = K.stage1a(PRIMARY, LOCK, lambda tok, lock: tok in priced, mkt)
    assert [c["question"] for c in pk["event"]["contracts"]] == ["Will the Fed cut 25?"]
    pk2, _, _ = K.stage1a(PRIMARY, LOCK, lambda tok, lock: True, {"0xcond1_2": {"closed": iso(LOCK + DAY)}})
    assert len(pk2["event"]["contracts"]) == 3                                                  # closing after the lock is fine


def test_leak_scan_flags_past_tense_resolution_language_and_not_the_normal_rules_wording():
    assert K.leak_flags('This market will resolve to "Yes" if X. Otherwise it resolves to "No".') == []
    assert K.leak_flags("This market has resolved to Yes.")
    assert K.leak_flags("UPDATE: the ruling came on 3 May") and K.leak_flags("The final outcome was No")
    e = dict(PRIMARY, description="Note. This market was resolved to No after review.")
    assert K.stage1a(e, LOCK, lambda t, l: True, {})[2]


GOOD_1A = {"primary": {"thesis": "hold", "basket": [{"contract": "C2", "side": "YES", "reason": "inflation sticky"}]}, "failure_narrative": "labour market cracks",
           "hedge_thesis": "a labour shock hits risk assets", "search_terms": ["bitcoin", "crypto", "nasdaq"]}


def test_stage1a_answer_validation():
    pk, _, _ = K.stage1a(PRIMARY, LOCK, lambda t, l: True, {})
    assert K.validate_1a(GOOD_1A, pk) == []
    bad = json.loads(json.dumps(GOOD_1A)); bad["primary"]["basket"][0]["contract"] = "C9"
    assert K.validate_1a(bad, pk)
    bad = json.loads(json.dumps(GOOD_1A)); bad["search_terms"] = ["one"]
    assert K.validate_1a(bad, pk)
    bad = json.loads(json.dumps(GOOD_1A)); bad["hedge_thesis"] = "BTC is 70% likely to fall"
    assert any("probability" in e for e in K.validate_1a(bad, pk))
    assert K.validate_1a({"primary": {}}, pk)


def index():
    rows = [event(10 + i, f"Bitcoin above ___ on October {i}?", ["bitcoin", "crypto"], [f"Will Bitcoin be above ${k},000 on October {i}?" for k in (80, 85, 90)]) for i in range(1, 4)]
    rows += [event(20, "What price will Ethereum hit?", ["ethereum", "crypto"], ["Will Ethereum reach $4,000?", "Will Ethereum reach $4,500?", "Will Ethereum reach $5,000?", "Will Ethereum dip to $2,000?", "Will Ethereum dip to $1,500?"])]
    rows += [event(99, "Best performing coin this week?", ["crypto"], ["Bitcoin", "Ethereum", "Solana"], cls="partition_exact", neg=True)]
    rows += [event(30, "Old bitcoin event", ["bitcoin", "crypto"], ["a $1", "b $2", "c $3"], start=T0 - 40 * DAY, closed=T0 - 20 * DAY)]      # not live at the lock
    rows += [event(40, "Future bitcoin event", ["bitcoin", "crypto"], ["a $1", "b $2", "c $3"], start=T0 + 15 * DAY, closed=T0 + 30 * DAY)]  # not yet open
    rows += [event(50 + i, f"Solana thing {i}", ["solana", "crypto"], [f"Will thing {i} reach $10?", f"Will thing {i} reach $20?", f"Will thing {i} reach $30?"]) for i in range(12)]
    return rows


def test_retrieval_is_live_at_the_lock_collapsed_by_template_and_priced():
    pk, pv, st = K.stage1b(index(), ["bitcoin", "crypto"], LOCK, K.G.template(PRIMARY["title"]), "R1", lambda t, l: True, exclude_id="1")
    titles = [c["title"] for c in pk["candidates"]]
    assert sum(t.startswith("Bitcoin above") for t in titles) == 1 and "Old bitcoin event" not in titles and "Future bitcoin event" not in titles
    assert next(c for c in pk["candidates"] if c["title"].startswith("Bitcoin above"))["similar_events"] == 3
    assert st["templates_found"] >= 3
    none = K.stage1b(index(), ["bitcoin"], LOCK, "x", "R1", lambda t, l: False, exclude_id="1")
    assert none[0]["candidates"] == [] and none[2]["empty_menu"]                                # nothing priced: an empty menu, not drawn


def test_retrieval_is_deterministic_seeded_by_round_and_carries_no_ids():
    a = K.stage1b(index(), ["crypto"], LOCK, "x", "R1", lambda t, l: True)[0]
    b = K.stage1b(index(), ["crypto"], LOCK, "x", "R1", lambda t, l: True)[0]
    c = K.stage1b(index(), ["crypto"], LOCK, "x", "R2", lambda t, l: True)[0]
    assert [x["title"] for x in a["candidates"]] == [x["title"] for x in b["candidates"]]
    assert [x["title"] for x in a["candidates"]] != [x["title"] for x in c["candidates"]]      # a different round, a different order
    blob = json.dumps(a).lower()
    assert not (set(keys_of(a)) & BANNED_KEYS) and "0xcond" not in blob and "tokyes" not in blob
    small = K.stage1b(index(), ["ethereum"], LOCK, "x", "R1", lambda t, l: True)[2]
    assert small["thin_menu"] and not small["empty_menu"] and small["live_templates"] >= 3      # a thin menu is a result, not a reason to replace the round; zero candidates is 'no instrument'


def test_stage1b_answer_validation():
    pk1, _, _ = K.stage1a(PRIMARY, LOCK, lambda t, l: True, {})
    pk, pv, _ = K.stage1b(index(), ["crypto"], LOCK, "x", "R1", lambda t, l: True)
    eth = next(c for c in pk["candidates"] if c["title"].startswith("What price will Ethereum"))
    btc = next(c for c in pk["candidates"] if c["title"].startswith("Bitcoin above"))
    coin = next(c for c in pk["candidates"] if c["title"].startswith("Best performing"))
    assert eth["kind"] == "touch ladder" and btc["kind"] == "price ladder" and coin["kind"] == "partition exact"
    ok = {"hedges": [{"contract": coin["contracts"][0]["label"], "side": "YES", "reason": "risk-off"}, {"event": btc["label"], "direction": "below", "tier": "moderate", "reason": "x"}],
          "claims": [{"if": {"contract": "C1", "resolves": "NO"}, "then": {"contract": coin["contracts"][0]["label"], "resolves": "YES"}, "reason": "y"}]}
    assert K.validate_1b(ok, pk1, pk) == []
    assert K.validate_1b({"hedges": [], "no_instrument": True}, pk1, pk) == []
    assert K.validate_1b({"hedges": [{"contract": "E1.1", "side": "YES"}], "no_instrument": True}, pk1, pk)
    assert K.validate_1b({"hedges": [{"event": eth["label"], "direction": "below", "tier": "moderate"}]}, pk1, pk)     # a touch ladder takes reach or dip, not 'below'
    assert K.validate_1b({"hedges": [{"event": eth["label"], "direction": "dip", "tier": "moderate"}]}, pk1, pk) == []
    assert K.validate_1b({"hedges": [{"contract": eth["contracts"][0]["label"], "side": "YES"}]}, pk1, pk)             # naming a rung on a ladder is refused
    assert K.validate_1b({"hedges": [{"event": coin["label"], "direction": "below", "tier": "mild"}]}, pk1, pk)        # a partition takes a contract, not a tier
    assert K.validate_1b({"hedges": [{"event": btc["label"], "direction": "sideways", "tier": "moderate"}]}, pk1, pk)
    assert K.validate_1b({"hedges": [{"contract": "E99.1", "side": "YES"}]}, pk1, pk)
    bad = json.loads(json.dumps(ok)); bad["claims"][0]["if"]["contract"] = "C9"
    assert K.validate_1b(bad, pk1, pk)
    bad = json.loads(json.dumps(ok)); bad["hedges"][0]["reason"] = "likely 80% to fall"
    assert K.validate_1b(bad, pk1, pk)
    text = K.prompt_1b(pk1, GOOD_1A, pk)
    assert "0xcond" not in text and "tokyes" not in text
    assert "Will the Fed hold?" in text and "C2:" in text                                       # a fresh stage-1b session can read what its primary labels mean
