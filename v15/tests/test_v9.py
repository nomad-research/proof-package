"""v9 brief: §A scheduled facts feed, §B node history / tags / cap / selector, §C synthetic ordering and divergence at
lock, §D fetch paths and snapshots, §E arming categories, §F programme stats. §G smoke tests 1-7."""
import json

import pytest

from harness import basket, carriers, facts, history, names, pit, positions, predicates, rounds, scheduled, scorer, snapshots, synthetic
from harness.errors import StateError, ValidationError

from conftest import TEST_MODEL, TODAY, make_round, make_rule, pred, res

NODE = "sweeny_refinery_output"


def _gate(conn):
    r = conn.execute("SELECT id FROM predicates WHERE key = 'pred.arm.tradability_gate'").fetchone()
    if r:
        return r["id"]
    return predicates.predicate_add(conn, "tradability gate (single-name and pair forms)", "arming", "s", "t", key="pred.arm.tradability_gate")["predicate_id"]


def _catalyst(conn):
    r = conn.execute("SELECT id FROM predicates WHERE key = 'pred.arm.catalyst_class'").fetchone()
    if r:
        return r["id"]
    return predicates.predicate_add(conn, "catalyst class", "arming", "s", "t", key="pred.arm.catalyst_class")["predicate_id"]


def _round8_like(conn, rule, date="2026-07-27"):
    """A round shaped like round 8: three listed refiners on one node, opposing signs, a synthetic through the pair gate
    and no catalyst. Returns (round_id, synthetic_id, holders)."""
    rid = rounds.submit_event(conn, "a process upset at a refinery", date, "s", "first-qualifier", 0,
                              {"Q1": "unknown"}, node=NODE, node_kind="refinery", operator_model=TEST_MODEL, today=TODAY, registries=False)["round_id"]
    H = {}
    for key, name, cik in (("psx", "Phillips 66", "1534701"), ("vlo", "Valero Energy", "1035002"), ("mpc", "Marathon Petroleum", "1510295")):
        H[key] = names.holder_upsert(conn, name, "company", listed=True, ticker=key.upper(), key=f"holder.{key}", cik=cik,
                                     ir_url=f"https://investor.{key}.example/events")["holder_id"]
    P = {}
    for key, sign in (("psx", "-"), ("vlo", "+"), ("mpc", "+")):
        P[key] = positions.position_add(conn, H[key], NODE, "sign_of_exposure", sign, "s", "inferred")["position_id"]
    rounds.touched_set_add(conn, rid, [{"holder_id": H[k], "degree": d, "node": NODE, "position_summary": "x", "substitutability": "high",
                                        "mechanism_ids": [rule]} for k, d in (("psx", 0), ("vlo", 2), ("mpc", 2))])
    syn = synthetic.synthetic_build(conn, rid, NODE, "syn.tradability_opposing")
    assert syn["built"] and syn["n_components"] == 3
    rounds.lock_predictions(conn, rid, [pred(rule, sign="0", target="PSX equity", claim="no attributable move")])
    gate, cat = _gate(conn), _catalyst(conn)
    predicates.predicate_check(conn, rid, [
        {"predicate_id": gate, "claimed": "holds", "observed": "holds", "basis": "pair form", "position_id": syn["synthetic_id"]},
        {"predicate_id": cat, "claimed": "fails", "observed": "fails", "basis": "no dated statement", "position_id": syn["synthetic_id"]},
        {"predicate_id": gate, "claimed": "fails", "observed": "fails", "basis": "below visibility", "position_id": P["psx"]},
    ])
    return rid, syn["synthetic_id"], H, P


def _edgar_fake(dates_by_cik):
    def fetch(url, timeout=30):
        for cik, dates in dates_by_cik.items():
            if f"CIK{int(cik):010d}" in url:
                rec = {"form": ["8-K"] * len(dates), "filingDate": dates, "items": ["2.02,9.01"] * len(dates),
                       "accessionNumber": [f"0000000000-26-{i:06d}" for i in range(len(dates))], "primaryDocument": ["x.htm"] * len(dates)}
                return json.dumps({"filings": {"recent": rec}}).encode()
        if "wayback/available" in url:
            return b'{"archived_snapshots": {}}'
        raise AssertionError(url)
    return fetch


# §G.1 / A: scheduled facts ingested, catalyst re-run on the synthetic in the dry-run report only --------------------

def test_g1_scheduled_feed_dates_the_synthetic_in_dry_run(conn):
    a = make_rule(conn)
    rid, syn_id, H, P = _round8_like(conn, a)
    b = basket.event_basket(conn, rid)
    # v12 0.3: the synthetic is still gate_pass_undated; the natural legs now also carry a computed reading
    assert b["synthetics"][0]["arming_status"] == "gate_pass_undated" and b["arming_status_counts"]["gate_pass_undated"] >= 1
    assert b["legs"][0]["arming_status"] == "gate_fail"
    # score the round so the dry-run rule applies
    rounds.open_retrieval(conn, rid)
    ids = [p["id"] for p in rounds.list_predictions(conn, rid)]
    scorer.score_round(conn, rid, [res(ids[0], "hit", "right")])
    # ingest: PSX 5 Aug, VLO 23 Jul (before the event: not in window), MPC 4 Aug
    rep = scheduled.ingest_scheduled(conn, [H["psx"], H["vlo"], H["mpc"]], as_of="2026-08-24",
                                     fetch=_edgar_fake({"1534701": ["2026-08-05", "2026-04-29"], "1035002": ["2026-07-23"], "1510295": ["2026-08-04"]}))
    assert rep["new_facts"] == 4 and all(h["edgar"]["ok"] for h in rep["holders"])
    c = scheduled.catalyst_check(conn, rid)
    syn = next(l for l in c["legs"] if l["synthetic"])
    # v10 E1: EDGAR 2.02 rows are hindsight and never date a leg; the facts are surfaced, not dating
    assert not syn["holds_observed"] and syn["arming_status"] == "gate_pass_undated" and len(syn["facts"]) >= 1 and all(f["hindsight"] for f in syn["facts"])
    assert not syn["holds_claimable"]
    # a mechanical date (I5) on a component dates the synthetic in the dry run
    scheduled.scheduled_add(conn, H["psx"], "results_announced", "2026-08-05", "results-date announcement", "2026-07-20", fact_type="mechanical", sched_source="announcement")
    c = scheduled.catalyst_check(conn, rid)
    syn = next(l for l in c["legs"] if l["synthetic"])
    assert syn["holds_observed"] and syn["holds_claimable"] and syn["arming_status_if_dated"] == "armed_dated" and syn["dating"][0]["dated_by"] == "mechanical"
    assert c["dry_run"] and c["legs_dated_observed"] >= 1
    with pytest.raises(StateError, match="dry-run"):
        scheduled.catalyst_check(conn, rid, write=True)
    # the ledger is untouched: the synthetic is still gate_pass_undated
    assert basket.event_basket(conn, rid)["synthetics"][0]["arming_status"] == "gate_pass_undated"
    # a moved date is a new row with supersedes, never an overwrite
    old = [f for f in scheduled._current_scheduled(conn, H["psx"]) if f["source_time"] == "2026-08-05"][0]
    r = scheduled.scheduled_add(conn, H["psx"], "results", "2026-08-06", "IR page", "2026-07-01", supersedes=old["id"])
    cur = scheduled._current_scheduled(conn, H["psx"])
    assert r["created"] and old["id"] not in {f["id"] for f in cur} and any(f["source_time"] == "2026-08-06" for f in cur)
    with pytest.raises(ValidationError, match="same holder"):
        scheduled.scheduled_add(conn, H["vlo"], "results", "2026-08-07", "IR page", "2026-07-01", supersedes=old["id"])
    # A4 backfill report counts without rescoring
    rep = scheduled.backfill_report(conn, [rid], ingest=False)
    assert rep["legs_would_be_dated"] >= 1 and rep["rounds"][0]["legs_dated_observed"] >= 1
    assert rounds.latest_scorecard(conn, rid)["arming_status_counts"]["gate_pass_undated"] >= 1
    # F: coverage counts future facts only
    cov = scheduled.coverage(conn, today="2026-08-01")
    assert cov["listed_holders"] == 3 and cov["with_future_scheduled_fact"] == 2 and cov["coverage"] == pytest.approx(2 / 3)


def test_ir_events_page_parser():
    text = ("Events & Presentations. Second-Quarter 2026 Earnings Conference Call August 5, 2026 8:00 AM CT. "
            "Annual Meeting of Shareholders May 13, 2026. Some unrelated date: 12 March 2026 press release. "
            "Investor Day 2026-11-18.")
    items = {(i["kind"], i["date"]) for i in scheduled.parse_events_page(text)}
    assert ("results", "2026-08-05") in items and ("agm", "2026-05-13") in items and ("capital_markets_day", "2026-11-18") in items


def test_ingest_reads_ir_page_through_wayback_with_snapshot_knowable_from(conn):
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True, ir_url="https://ir.alpha.example/events")["holder_id"]

    def fetch(url, timeout=30):
        if "wayback/available" in url:
            return b'{"archived_snapshots": {"closest": {"available": true, "url": "https://web.archive.org/web/20260701/https://ir.alpha.example/events", "timestamp": "20260701000000"}}}'
        if "web.archive.org" in url:
            return b"<html>Q2 2026 Results webcast: August 12, 2026</html>"
        raise AssertionError(url)
    rep = scheduled.ingest_scheduled(conn, [h], as_of="2026-07-20", fetch=fetch)
    f = scheduled._current_scheduled(conn, h)
    assert rep["new_facts"] == 1 and f[0]["source_time"] == "2026-08-12" and f[0]["knowable_from"] == "2026-07-01" and f[0]["sched_kind"] == "results"
    # reveal surfaces it within the full scoring window for degree <= 1 and says it was knowable by the event date
    positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "s", "stated")
    rid = rounds.submit_event(conn, "fire at node x", "2026-07-16", "s", "r", 0, {"Q1": "pass"}, node="node x",
                              operator_model=TEST_MODEL, today=TODAY, registries=False)["round_id"]
    ctx = rounds.reveal_event(conn, rid)["context"]
    assert ctx["scheduled"][0]["source_time"] == "2026-08-12" and ctx["scheduled"][0]["knowable_by_event"] is True
    # and the catalyst check writes a per-leg row on the live round
    rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": 0, "node": "node x", "position_summary": "x", "substitutability": "low"}])
    _catalyst(conn)
    c = scheduled.catalyst_check(conn, rid, write=True)
    # v10 E2: without a concerns_node link the fact is undecided and does not date the leg
    assert not c["legs"][0]["holds_claimable"] and len(c["legs"][0]["undecided"]) == 1
    pid = c["legs"][0]["position_id"]
    scheduled.link_fact(conn, rid, pid, f[0]["id"], True, "node x is Alpha's named segment")
    c = scheduled.catalyst_check(conn, rid, write=True)
    assert c["legs"][0]["holds_claimable"] and len(c["written"]) == 1
    chk = predicates.round_checks(conn, rid)[-1]
    assert chk["claimed"] == "holds" and chk["observed"] == "holds" and chk["basis"].startswith("computed: results (scheduled) for Alpha Plc on 2026-08-12")


# §G.2 / B: node history from ledger + registry; Q1b computed; intake dry-run tags weather ---------------------------

TCEQ_PAGE = b"""<html><table>
<tr><td>01/09/2026</td><td>Phillips 66 Sweeny Refinery</td><td>Emissions event: fuel gas upset</td></tr>
<tr><td>07/13/2026</td><td>Phillips 66 Sweeny Refinery</td><td>Emissions event: power-related upset</td></tr>
<tr><td>07/27/2026</td><td>Phillips 66 Sweeny Refinery</td><td>Emissions event: lightning unit upset</td></tr>
</table></html>"""


def _tceq_fetch(url, timeout=30):
    if "tceq.texas.gov" in url:
        return TCEQ_PAGE
    raise AssertionError(url)


def test_g2_node_history_and_q1b_from_registry(conn):
    p66 = names.holder_upsert(conn, "Phillips 66", "company", listed=True, key="holder.phillips66")["holder_id"]
    plant = names.holder_upsert(conn, "Phillips 66 Sweeny Refinery", "plant", parent_id=p66, aliases=["Sweeny Refinery"])["holder_id"]
    positions.position_add(conn, plant, NODE, "sign_of_exposure", "-", "s", "stated")
    h = history.node_history(conn, "sweeny refinery", as_of="2026-07-28", node_kind="refinery", fetch=_tceq_fetch)
    assert [i["date"] for i in h["incidents"]] == ["2026-01-09", "2026-07-13", "2026-07-27"]
    assert h["registries"][0]["path_served"] == "live" and h["incidents"][0]["url"].startswith("https://www2.tceq")
    # the same via the ledger only (registries off): nothing yet
    assert history.node_history(conn, NODE, as_of="2026-07-28", registries=False)["n"] == 0
    q = history.q1b(conn, NODE, "2026-07-27", node_kind="refinery", fetch=_tceq_fetch)
    assert q["value"] == "fail" and q["in_90d"] == 1 and q["in_12m"] == 2       # the 27 July row is the event itself, excluded
    d = rounds.intake_dry_run(conn, "a lightning upset at a refinery in Sweeny", "2026-07-27", {"Q1a": "unknown"}, node=NODE,
                              node_kind="refinery", fetch=_tceq_fetch, operator_model=TEST_MODEL, today=TODAY)
    assert d["tag"] == "weather" and d["q1b"]["value"] == "fail" and not d["cap"]["blocked"]
    # a human override needs a basis
    with pytest.raises(ValueError, match="basis"):
        history.q1b(conn, NODE, "2026-07-27", node_kind="refinery", fetch=_tceq_fetch, override={"value": "pass"})
    q2 = history.q1b(conn, NODE, "2026-07-27", node_kind="refinery", fetch=_tceq_fetch, override={"value": "pass", "basis": "the July 13 row is a data-entry duplicate"})
    assert q2["value"] == "pass" and q2["computed"] == "fail" and "override" in q2["text"]
    # blocked live path falls back to wayback and says so
    def blocked(url, timeout=30):
        if "tceq.texas.gov" in url:
            raise ConnectionResetError("forcibly closed")
        if "wayback/available" in url:
            return b'{"archived_snapshots": {}}'
        raise AssertionError(url)
    h2 = history.node_history(conn, "sweeny refinery", as_of="2026-07-28", node_kind="refinery", fetch=blocked)
    assert h2["registries"][0]["path_served"] is None and "ConnectionResetError" in h2["registries"][0]["error"]
    # prior rounds on the node count on the ledger side
    rid = rounds.submit_event(conn, "a lightning upset at a refinery in Sweeny", "2026-07-27", "s", "r", 0, {"Q1a": "unknown"}, node=NODE,
                              node_kind="refinery", operator_model=TEST_MODEL, today=TODAY, fetch=_tceq_fetch)
    assert rid["tag"] == "weather" and rounds.round_tag(conn, rid["round_id"])["q1b"] == "fail"
    later = history.q1b(conn, NODE, "2026-08-20", node_kind="refinery", registries=False)
    assert later["in_90d"] == 1 and later["incidents"][0]["from"] == "ledger" and later["incidents"][0]["round_id"] == rid["round_id"]


def test_tags_are_computed_and_retag_supersedes(conn):
    r = rounds.submit_event(conn, "x", "2026-07-16", "s", "r", 0, {"Q1a": "pass: nothing on the channel in 30 days"}, node="n1",
                            operator_model=TEST_MODEL, today=TODAY, registries=False)
    assert r["tag"] == "lag_test" and r["q1a"] == "pass"
    with pytest.raises(ValidationError, match="basis"):
        rounds.submit_event(conn, "x2", "2026-07-16", "s", "r", 0, {"Q1a": "pass"}, operator_model=TEST_MODEL, today=TODAY)
    r2 = rounds.submit_event(conn, "x3", "2026-07-16", "s", "r", 0, {"Q1a": "fail: third headline on the channel that month"}, node="n2",
                             operator_model=TEST_MODEL, today=TODAY, registries=False)
    assert r2["tag"] == "late_headline"
    r3 = rounds.submit_event(conn, "x4", "2026-05-16", "s", "r", 0, {"Q1a": "pass: y"}, node="n3", operator_model=TEST_MODEL, today=TODAY, round_class="learning")
    assert r3["tag"] == "learning"
    t = rounds.retag(conn, r["round_id"], "weather", "human: a June strike at the node was found after intake", q1b="fail")
    cur = rounds.round_tag(conn, r["round_id"])
    assert cur["tag"] == "weather" and cur["supersedes"] and len(rounds.list_tags(conn, r["round_id"])) == 2
    assert rounds.export_round(conn, r["round_id"])["tag"]["tag"] == "weather"


# §G.3 / B4: the cap ----------------------------------------------------------------------------------------------------

def test_g3_cap_refuses_second_weather_and_logs_override(conn):
    facts.node_fact_add(conn, "n_weather", "outage", "an outage at the node", "ledger", source_time="2026-07-01")
    # admitted: lag_test, weather, lag_test  -> the last three include a weather round
    rounds.submit_event(conn, "a", "2026-07-10", "s", "r", 0, {"Q1a": "pass: y"}, node="n_a", operator_model=TEST_MODEL, today=TODAY, registries=False)
    w = rounds.submit_event(conn, "b", "2026-07-12", "s", "r", 0, {"Q1a": "pass: y"}, node="n_weather", operator_model=TEST_MODEL, today=TODAY, registries=False)
    assert w["tag"] == "weather" and not w["cap"]["blocked"]
    rounds.submit_event(conn, "c", "2026-07-14", "s", "r", 0, {"Q1a": "pass: y"}, node="n_c", operator_model=TEST_MODEL, today=TODAY, registries=False)
    # v11 §C: first traversal is a tag, so the cap warns and never refuses; the round is admitted with a cap note
    d = rounds.submit_event(conn, "d", "2026-07-20", "src", "r", 0, {"Q1a": "pass: y"}, node="n_weather", operator_model=TEST_MODEL, today=TODAY,
                            registries=False, cap_override="the human wants a fourth weather data point for the cap review")
    assert d["tag"] == "weather" and d["cap"]["blocked"] is True
    assert not [r for r in conn.execute("SELECT * FROM event_rejections WHERE failing_q = 'cap'")]
    assert any(n["kind"] == "cap" and "warning" in n["note"] for n in rounds.list_notes(conn, d["round_id"]))
    # a lag_test round is never capped
    e = rounds.submit_event(conn, "e", "2026-07-21", "s", "r", 0, {"Q1a": "pass: y"}, node="n_e", operator_model=TEST_MODEL, today=TODAY, registries=False)
    assert e["tag"] == "lag_test" and not e["cap"]["blocked"]


# §G.4 / C1: synthetics before lock, every component cited ----------------------------------------------------------------

def test_g4_synthetic_build_after_lock_refused(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    hs = {n: names.holder_upsert(conn, n, "company", listed=True)["holder_id"] for n in ("Long Co", "Short Co")}
    positions.position_add(conn, hs["Long Co"], "n", "sign_of_exposure", "+", "s", "stated")
    positions.position_add(conn, hs["Short Co"], "n", "sign_of_exposure", "-", "s", "stated")
    rounds.touched_set_add(conn, rid, [{"holder_id": hs["Long Co"], "degree": 1, "node": "n", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]},
                                       {"holder_id": hs["Short Co"], "degree": 1, "node": "n", "position_summary": "x", "substitutability": "low"}])
    r = synthetic.synthetic_build(conn, rid, "n", "syn.tradability_opposing")
    assert not r["built"] and "Short Co" in r["reason"] and "cited mechanism" in r["reason"]
    rounds.touched_set_add(conn, rid, [{"holder_id": hs["Short Co"], "degree": 1, "node": "n", "position_summary": "x", "substitutability": "low", "mechanism_ids": [a]}])
    r = synthetic.synthetic_build(conn, rid, "n", "syn.tradability_opposing")
    assert r["built"]
    b = basket.event_basket(conn, rid)
    assert b["legs"][0]["support_from"] == "touched-set rules" and not b["synthetics"][0]["built_after_lock"]
    rounds.lock_predictions(conn, rid, [pred(a)])
    with pytest.raises(StateError, match="post-hoc"):
        synthetic.synthetic_build(conn, rid, "n", "syn.tradability_opposing")


# §G.5 / C2: divergence from the sign at lock; revised_sign shown -----------------------------------------------------------

def test_g5_divergence_uses_sign_at_lock(conn):
    a = make_rule(conn)
    rid = make_round(conn)
    h = names.holder_upsert(conn, "Owner Plc", "company", listed=True)["holder_id"]
    pid = positions.position_add(conn, h, "node x", "sign_of_exposure", "-", "s", "stated")["position_id"]
    rounds.touched_set_add(conn, rid, [{"holder_id": h, "degree": 0, "node": "node x", "position_summary": "x", "substitutability": "low"}])
    ids = rounds.lock_predictions(conn, rid, [
        pred(None, call_type="narrative", target="Owner leg", claim="the press says it weighs on the owner", carrier="trade press commentary",
             falsifier="no such framing", narrative_sign="-", position_id=pid, sign=None),
        pred(a, target="Owner Plc", sign="0", claim="no attributable move", position_id=pid),
    ])["prediction_ids"]
    assert basket.event_basket(conn, rid)["legs"][0]["divergence"] is False
    rounds.open_retrieval(conn, rid)
    # post-lock revision: the structural sign moves to 0 in a new position row
    positions.position_add(conn, h, "node x", "sign_of_exposure", "0", "post-lock reading", "inferred", supersedes=pid)
    b = basket.event_basket(conn, rid)
    leg = b["legs"][0]
    assert leg["sign"] == "-" and leg["revised_sign"]["sign"] == "0" and leg["revised_sign"]["recorded_at"] > b["locked_at"]
    assert leg["divergence"] is False and b["divergent_legs"] == 0 and b["revised_legs"] == 1
    card = scorer.score_round(conn, rid, [res(ids[0], "miss", "unknown"), res(ids[1], "hit", "right")])
    nb = scorer.latest_notebook_rows(conn, rid)
    assert {"E4", "F3"} <= set(nb) and nb["F3"]["divergent_legs"] == 0 and nb["E4"]["synthetics"] == 0 and card["notebook_rows"]
    assert scorer.programme_stats(conn)["notebook_rows"][rid]["F3"]["divergent_legs"] == 0


# §G.6 / D: fetch paths and the auto path ------------------------------------------------------------------------------------

def test_g6_pit_fetch_auto_serves_from_wayback_when_live_blocked(conn):
    r = carriers.path_set(conn, "carrier.tceq_emissions", "live", "blocked", url="https://www2.tceq.texas.gov/oce/eer/index.cfm")
    assert r["best_path"] == {"path": "wayback", "status": "ok", "reachable": True} and r["reachability"] == "open"
    assert carriers.resolve(conn, "TCEQ emissions event report")["status"] == "open"
    calls = []

    def fake(url, timeout=30):
        calls.append(url)
        if "tceq.texas.gov" in url and "archive.org" not in url:
            raise AssertionError("live must not be tried when the registry marks it blocked")
        if "wayback/available" in url:
            return b'{"archived_snapshots": {"closest": {"available": true, "url": "https://web.archive.org/web/20260720/https://www2.tceq.texas.gov/oce/eer/index.cfm", "timestamp": "20260720000000"}}}'
        return b"<html>STEERS list</html>"
    r = pit.pit_fetch(conn, "auto", "https://www2.tceq.texas.gov/oce/eer/index.cfm?x=1", "2026-07-25", "read the list", fetch=fake)
    assert r["found"] and r["path_served"] == "wayback" and "registry marks" in r["tried"][0]
    assert pit.list_fetches(conn)[0]["path_served"] == "wayback"
    # an unregistered host is fetched live when no round is created/locked, and falls back on failure
    def flaky(url, timeout=30):
        if url.startswith("https://ok.example"):
            return b"<html>live page</html>"
        if url.startswith("https://down.example"):
            raise TimeoutError("timed out")
        if "wayback/available" in url:
            return b'{"archived_snapshots": {"closest": {"available": true, "url": "https://web.archive.org/web/20260720/https://down.example/", "timestamp": "20260720000000"}}}'
        return b"<html>archived</html>"
    assert pit.pit_fetch(conn, "auto", "https://ok.example/p", "2026-07-25", "x", fetch=flaky)["path_served"] == "live"
    r = pit.pit_fetch(conn, "auto", "https://down.example/p", "2026-07-25", "x", fetch=flaky)
    assert r["path_served"] == "wayback" and r["tried"][0].startswith("live: TimeoutError")
    # pre-lock the live path is refused outright
    rounds.submit_event(conn, "fire at node x", "2026-08-01", "s", "r", 0, {"Q1": "pass"}, operator_model=TEST_MODEL, today=TODAY, registries=False)
    r = pit.pit_fetch(conn, "auto", "https://ok.example/p", "2026-07-25", "x", fetch=flaky)
    assert r["tried"][0].startswith("live refused")
    # a carrier with every path blocked is unreachable even when its nominal access is open, and Q7 reads that
    carriers.path_set(conn, "carrier.eia", "live", "blocked")
    carriers.path_set(conn, "carrier.eia", "wayback", "blocked")
    assert carriers.reachability(dict(conn.execute("SELECT * FROM carriers WHERE key = 'carrier.eia'").fetchone())) == "unreachable"
    assert carriers.check(conn, ["EIA weekly"])["carrier_unreachable"] == ["EIA weekly"]
    ph = carriers.path_health(conn)
    assert ph["unreachable"] >= 1 and "live:blocked" in ph["by_best_path"]
    assert "EIA" not in carriers.open_for_kind(conn, "refinery")["open_carriers"]


def test_snapshot_records_node_fact_and_targets_seed(conn):
    h = names.holder_upsert(conn, "Alpha Plc", "company", listed=True, ir_url="https://ir.alpha.example/events")["holder_id"]
    carriers.path_set(conn, "carrier.tceq_emissions", "live", "blocked", url="https://www2.tceq.texas.gov/oce/eer/index.cfm")
    seeded = snapshots.seed_targets(conn)
    urls = {t["url"] for t in snapshots.list_targets(conn)}
    assert "https://ir.alpha.example/events" in urls and "https://www2.tceq.texas.gov/oce/eer/index.cfm" in urls
    saved = []

    def save(url):
        saved.append(url)
        return {"ok": True, "status": 200, "snapshot_url": f"https://web.archive.org/web/20260901120000/{url}", "timestamp": "20260901120000", "snapshot_date": "2026-09-01"}
    rep = snapshots.run(conn, save=save, pause_seconds=0)
    assert rep["saved"] == len(urls) and set(saved) == urls
    f = facts.node_facts(conn, fact_type="snapshot")
    assert len(f) == len(urls) and f[0]["source_time"] == "2026-09-01" and f[0]["url"].startswith("https://web.archive.org/web/20260901")
    t = next(t for t in snapshots.list_targets(conn) if t["url"] == "https://ir.alpha.example/events")
    assert t["last_snapshot"] == "2026-09-01" and t["last_status"] == "saved" and t["holder_id"] == h
    def broken(url):
        raise OSError("no route")
    assert snapshots.snapshot(conn, "https://x.example/", save=broken)["status"] == "error"


# §G.7 / B5: selection window without rejections -> Q9 fail; three in a row suspend the selector ---------------------------

def test_g7_q9_fail_without_rejections_and_selector_suspension(conn):
    rounds.selection_window_open(conn, "trade press A", "2026-07-01", "three events enumerated")
    r = rounds.submit_event(conn, "the second event", "2026-07-10", "trade press A", "first-qualifier", 0, {"Q1a": "pass: y"}, node="n1",
                            operator_model=TEST_MODEL, today=TODAY, registries=False, selection_start_date="2026-07-01", window_events_seen=3)
    assert r["q9"]["text"].startswith("fail: computed") and not r["criteria_pass"] and r["selector"]["consecutive_q9_fails"] == 1
    # with rejections written for the window, Q9 passes and the streak resets
    rounds.selection_window_open(conn, "trade press A", "2026-07-11")
    rounds.reject_event(conn, "trade press A", "2026-07-12", "a price move", "Q3", "not a world event", start_date="2026-07-11")
    r2 = rounds.submit_event(conn, "the qualifier", "2026-07-14", "trade press A", "first-qualifier", 0, {"Q1a": "pass: y"}, node="n2",
                             operator_model=TEST_MODEL, today=TODAY, registries=False, selection_start_date="2026-07-11", window_events_seen=2)
    assert r2["q9"]["text"].startswith("pass: computed") and r2["q9"]["rejections"] == 1 and r2["selector"]["consecutive_q9_fails"] == 0
    # three consecutive fails suspend the selector; intake refuses until the human clears it
    for i, d in enumerate(("2026-07-15", "2026-07-16", "2026-07-17")):
        rounds.selection_window_open(conn, "trade press A", d)
        rr = rounds.submit_event(conn, f"event {i}", d, "trade press A", "r", 0, {"Q1a": "pass: y"}, node=f"m{i}",
                                 operator_model=TEST_MODEL, today=TODAY, registries=False, selection_start_date=d)
    assert rr["selector"]["suspended"] and rr["selector"]["consecutive_q9_fails"] == 3
    with pytest.raises(ValidationError, match="selector suspended"):
        rounds.submit_event(conn, "another", "2026-07-18", "trade press A", "r", 0, {"Q1a": "pass: y"}, operator_model=TEST_MODEL, today=TODAY, registries=False)
    st = rounds.selector_clear(conn, "human reviewed the three windows")
    assert not st["suspended"] and st["cleared_reason"]
    # no window on the ledger: Q9 stays what the human said
    r3 = rounds.submit_event(conn, "another", "2026-07-18", "trade press A", "r", 0, {"Q1a": "pass: y", "Q9": "unknown: no window"},
                             operator_model=TEST_MODEL, today=TODAY, registries=False)
    assert r3["q9"]["window"] is None and r3["criteria_pass"]
    with pytest.raises(ValidationError, match="failing_q"):
        rounds.reject_event(conn, "s", "2026-07-01", "x", "Q11")


# §E/§F: arming categories on the scorecard, T0 and programme stats per tag ---------------------------------------------

def test_arming_categories_and_programme_stats_per_tag(conn):
    a = make_rule(conn)
    rid, syn_id, H, P = _round8_like(conn, a)
    rounds.open_retrieval(conn, rid)
    ids = [p["id"] for p in rounds.list_predictions(conn, rid)]
    card = scorer.score_round(conn, rid, [res(ids[0], "hit", "right")])
    c = card["arming_status_counts"]
    assert c["armed_dated"] == 0 and c["gate_pass_undated"] >= 1 and c["unchecked"] == 0      # v12 0.3: no leg is unchecked
    from harness import t0
    eid = rounds.round_status(conn, rid)["event_id"]
    t0.submit_candidate(conn, eid, "w1", True, False, True)
    assert t0.count(conn, "w1")["arming_status_counts"]["gate_pass_undated"] >= 1
    ps = scorer.programme_stats(conn)
    assert ps["arming_by_tag"]["lag_test"]["gate_pass_undated"] >= 1 and ps["arming_counts"]["gate_fail"] >= 1
    assert ps["rounds_by_tag"]["lag_test"] == 1 and ps["scheduled_facts_coverage"]["listed_holders"] == 3
    assert "reachable" in ps["fetch_path_health"]      # v12 0.3: natural legs now carry computed gates, so E4's
    assert ps["notebook_rows"][rid]["E4"]["synthetic_gate_pass"] >= 1      # "where the natural leg failed" no longer holds
    assert scorer.programme_stats(conn, tag="weather")["rounds_scored"] == 0 and scorer.programme_stats(conn, tag="lag_test")["rounds_scored"] == 1
    assert predicates.arming_status(True, True, True, True) == "armed_dated" and predicates.arming_status(False, False, False, False) == "unchecked"
