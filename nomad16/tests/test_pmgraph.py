"""The open-set graph: structure classes, template collapsing, price-free neighbourhoods and search. Synthetic events in the recorder's universe-row shape."""
import pytest

from nomad16 import pmgraph as G


def mk(git=None, q=None, nro=False, gthr=None):
    return {"cid": "0x" + str(abs(hash((git, q)))), "git": git, "q": q, "nro": nro, "gthr": gthr, "vol": 1.0}


def ev(i, title, tags, markets, neg=False, start="2026-09-01T00:00:00Z", end="2026-12-31T00:00:00Z", **k):
    return {"id": str(i), "title": title, "tags": tags, "markets": markets, "negRisk": neg, "start": start, "end": end, **k}


FED = lambda i, mo: ev(i, f"Fed decision in {mo}?", ["fed", "economy", "fomc"], [mk(git=g, q=f"{g}?") for g in ("cut 50", "cut 25", "hold", "hike")], neg=True)
BTC = lambda i, d: ev(i, f"Bitcoin above ___ on October {d}?", ["bitcoin", "crypto"], [mk(q=f"Will the price of Bitcoin be above ${k},000 on October {d}?") for k in (80, 82, 84, 86)])
EVENTS = [
    FED(1, "October"), FED(2, "December"), BTC(3, 1), BTC(4, 2),
    ev(5, "What price will Bitcoin hit in October?", ["bitcoin", "crypto"], [mk(q=f"Will Bitcoin reach ${k},000 in October?") for k in (90, 95, 100)] + [mk(q=f"Will Bitcoin dip to ${k},000 in October?") for k in (70, 65)]),
    ev(6, "Who wins the race?", ["elections", "economy"], [mk(git="A"), mk(git="B"), mk(git="Other")], neg=True),
    {"id": "7", "title": "NBA finals", "tags": ["nba"], "header_only": True, "n_markets": 30},
    ev(8, "Old event", ["fed", "economy"], [mk(git="x"), mk(git="y"), mk(git="z")], neg=True, start="2025-01-01T00:00:00Z", end="2025-06-01T00:00:00Z"),
]


def graph():
    return G.Graph(EVENTS, generic_share=0.5)


def test_structure_classes_and_out_of_scope_headers():
    g = graph()
    assert g.struct["1"]["class"] == "partition_exact" and g.struct["6"]["class"] == "partition_open"
    assert g.struct["3"] == {"class": "ladder", "kind": "terminal"}
    assert g.struct["5"]["class"] == "ladder" and g.struct["5"]["kind"] == "touch"
    assert "7" not in g.events and g.headers == 1


def test_recurring_events_collapse_to_one_template_with_a_count():
    g = graph()
    assert g.template["3"] == g.template["4"] != g.template["5"]
    hits = g.search(["bitcoin"])
    assert sum(h["n_in_template"] for h in hits if h["class"] == "ladder" and h["title"].startswith("Bitcoin above")) == 2
    assert len([h for h in hits if h["title"].startswith("Bitcoin above")]) == 1


def test_neighbourhood_is_deterministic_excludes_self_respects_cap_and_liveness():
    g = graph()
    a = g.neighbourhood("1", cap=60)
    assert [b["event_id"] for b in a] == [b["event_id"] for b in g.neighbourhood("1", cap=60)] and "1" not in {b["event_id"] for b in a}
    assert a[0]["event_id"] == "2"                                             # the other Fed decision shares the rare tags
    assert len(g.neighbourhood("1", cap=1)) == 1
    live = {b["event_id"] for b in g.neighbourhood("1", at="2026-10-01T00:00:00Z")}
    assert "8" not in live and "8" in {b["event_id"] for b in a}                # ended in 2025: not open at the lock
    with pytest.raises(KeyError):
        g.neighbourhood("999")


def test_search_reads_the_thesis_words_and_can_be_limited_to_exact_structures():
    g = graph()
    assert {h["event_id"] for h in g.search(["crypto"])} >= {"3", "5"}
    assert g.search(["nothing-matches-this"]) == []
    only = g.search(["economy"], classes={"partition_open"})
    assert [h["event_id"] for h in only] == ["6"]


def test_no_price_or_volume_enters_an_edge_or_a_ranking():
    base = [b["event_id"] for b in graph().neighbourhood("1")] + [h["event_id"] for h in graph().search(["bitcoin"])]
    noisy = [dict(e, volume=1e9 * int(e["id"]), liquidity=5.0 * int(e["id"])) for e in EVENTS]
    g2 = G.Graph(noisy, generic_share=0.5)
    assert base == [b["event_id"] for b in g2.neighbourhood("1")] + [h["event_id"] for h in g2.search(["bitcoin"])]
