"""The K14 mechanical support check: it recomputes support and refuses what a reader cannot show."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("k14s", Path(__file__).resolve().parents[2] / "lookbacks" / "k14" / "support.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

DOCS = {"D1": "The Ministry granted Acme a licence. Acme is owned 60% by ParentCo, which is listed.",
        "D2": "The licence conditions restart on a filing by the regulator."}
REG, KINDS, THR = S.load_registry(), S.load_kinds(), 0.3


def find(chain, kind="licence", name="the licence", **kw):
    return {"find_id": "F1", "entity": {"name": name, "kind": kind, "evidence": {"doc": "D1", "quote": "granted Acme a licence"}},
            "chain": chain, "expression": kw.get("expression", {"claim": "role"})}


def hop(frm, rel, to, fe, te, doc="D1", quote="granted Acme a licence"):
    return {"from": frm, "relation": rel, "to": to, "from_effect": fe, "to_effect": te, "doc": doc, "quote": quote}


def chk(f, closed=False):
    return S.check_find(f, "Acme plant", DOCS, REG, KINDS, THR, closed)


def test_support_is_recomputed_and_a_good_chain_passes():
    r = chk(find([hop("Acme plant", "governs", "the licence", "state", "availability")]))
    assert r["reach_ok"], r["reasons"]
    assert abs(r["final_support"] - 0.8 * 0.6) < 1e-9          # governs: transform 0.8 x discount 0.6


def test_a_chain_that_decays_below_the_threshold_fails():
    c = [hop("Acme plant", "governs", "x1", "state", "availability"),
         hop("x1", "governs", "x2", "state", "cost"), hop("x2", "governs", "the licence", "state", "cost")]
    r = chk(find(c))
    assert not r["reach_ok"] and any("below SUPPORT_THRESHOLD" in w for w in r["reasons"])


def test_an_unregistered_or_non_transmitting_relation_or_a_missing_quote_fails():
    assert not chk(find([hop("Acme plant", "related_to", "the licence", "state", "cost")]))["reach_ok"]
    assert not chk(find([hop("Acme plant", "adjacent_to", "the licence", "state", "cost")]))["reach_ok"]
    r = chk(find([hop("Acme plant", "governs", "the licence", "state", "availability", quote="invented sentence")]))
    assert not r["reach_ok"] and any("quoted span" in w for w in r["reasons"])


def test_the_chain_must_start_at_the_node_and_end_at_the_entity():
    assert not chk(find([hop("Elsewhere", "governs", "the licence", "state", "availability")]))["reach_ok"]
    assert not chk(find([hop("Acme plant", "governs", "other", "state", "availability")]))["reach_ok"]


def test_kind_rules_unreviewed_never_supports_and_v16_kinds_are_not_open_finds():
    hold = S.v16_holdable(KINDS)
    assert "company" in hold and "person" not in hold and "licence" not in hold
    c = [hop("Acme plant", "governs", "the licence", "state", "availability")]
    assert chk(find(c, kind="place"))["kind_reviewed"] is False                     # unreviewed: proposes only
    assert not chk(find(c, kind="place"))["reach_ok"]
    assert not chk(find(c, kind="company"))["reach_ok"]                              # v16 could hold it
    assert chk(find(c, kind="company"), closed=True)["v16_holdable_kind"] is True


def test_the_one_hop_expression_leg_is_verified_and_the_round_needs_the_blind_judge():
    ex = {"claim": "one_hop_from_expressible", "relation": "ownership", "entity": "ParentCo", "doc": "D1", "quote": "owned 60% by ParentCo"}
    f = find([hop("Acme plant", "governs", "the licence", "state", "availability")], expression=ex)
    rep = {"round": "t", "open": [chk(f)], "closed": []}
    assert rep["open"][0]["reach_ok"] and rep["open"][0]["expression"]["quote_verified"]
    assert S.round_result(rep, None)["round_shows_find"] is False                    # no judge, no count
    assert S.round_result(rep, {"verdicts": [{"find_id": "F1", "verdict": "none"}]})["round_shows_find"] is False
    assert S.round_result(rep, {"verdicts": [{"find_id": "F1", "verdict": "one_hop_from_expressible"}]})["round_shows_find"] is True
