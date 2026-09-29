"""v16 smoke tests (§32), fixture-only. Numbering follows the spec."""
from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from nomad16 import calls, config, derive, effects, intake, lock, paper, positions, reach, rounds, stories, walk
from nomad16.db import DB, Refused
from nomad16.instruments import instrument_add
from nomad16.tests.conftest import admit_round, holders, make_world, manifest
from nomad16.view import View

PKG = Path(__file__).resolve().parent.parent


def P(db, h, attr, val, kf="2026-07-01", conf="stated", node="unit-x", unit=None):
    return positions.position_add(db, h, node, attr, val, source="fixture", knowable_from=kf, confidence=conf,
                                  source_document="fixture doc" if conf == "stated" else None, unit=unit)


def base(db, collinear=False):
    make_world(db, collinear=collinear)
    rid = admit_round(db)
    holders(db)
    return rid


# ---------------------------------------------------------------- P0 hygiene
def test_chain_verifies_and_ledger_is_append_only(db):
    db.append("notes", round_id="x", segment_idx=0, subject="s", text="t")
    assert db.verify_chain() == []
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("UPDATE notes SET text='changed'")
    db.conn.execute("DROP TRIGGER notes_no_update")
    db.conn.execute("UPDATE notes SET text='changed'")
    db.conn.commit()
    assert db.verify_chain(), "a tampered row must break the chain"


def test_loader_refuses_missing_appetite(tmp_path, monkeypatch):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"values": {"X": {"value": 1, "status": "ratified"}}}))
    with pytest.raises(config.MissingAppetite):
        config.get("RHO_MIN", path=p)
    monkeypatch.delenv("NOMAD_OPERATOR_MODEL", raising=False)
    with pytest.raises(config.MissingAppetite):
        config.operator_model()


def test_fold_15_no_manifest_no_lock(db):
    rid = base(db)
    intake.tide_declare(db, rid, "us_equity_beta", "fixture")
    with pytest.raises(Refused, match="manifest"):
        lock.lock(db, rid)


def test_second_lock_refused_and_one_row_per_effect(db):
    rid = base(db)
    intake.tide_declare(db, rid, "us_equity_beta", "fixture")
    manifest(db, rid)
    effects.effect_root(db, rid, "h.owner", "unit-x", "revenue", -1, ["ev"], magnitude_pct=-3.0)
    effects.effect_root(db, rid, "h.merchant", "unit-x", "revenue", 1, ["ev"], magnitude_pct=2.0)
    out = lock.lock(db, rid)
    sr = db.rows("surviving_risk", "round_id=?", (rid,))
    assert len(sr) == 2 and len({r["effect_id"] for r in sr}) == 2
    with pytest.raises(Refused):
        lock.lock(db, rid)
    assert out["lock_hash"]


# ---------------------------------------------------------------- P1
def test_1_and_2_stake_bases(db):
    rid = base(db)
    from nomad16 import vetoes
    effects.effect_root(db, rid, "h.unit", "unit-x", "volume", -1, ["ev"], magnitude_pct=-100.0)
    effects.effect_root(db, rid, "h.reg", "unit-x", "obligation", 1, ["ev"], magnitude_pct=5.0)
    rows = {r["holder_id"]: r for r in vetoes.compute(View(db), rounds.get_round(db, rid), "2026-07-15")}
    assert rows["h.unit"]["stake_basis"] == "operating_scale" and rows["h.unit"]["terms"]["stake"] > 0
    assert rows["h.reg"]["gap_reasons"]["stake"] == "not_applicable" and "stake" not in rows["h.reg"]["terms"]


def test_5_veto_set_differs_by_effect_kind(db):
    rid = base(db)
    from nomad16 import vetoes
    root = effects.effect_root(db, rid, "h.unit", "unit-x", "volume", -1, ["ev"], magnitude_pct=-100.0)
    ob = effects.effect_compose(db, root["effect_id"], "offtake", "h.coowner", "obligation", -1, magnitude_pct=-1.0)
    vol = effects.effect_compose(db, root["effect_id"], "offtake", "h.coowner", "volume", -1, magnitude_pct=-1.0,
                                 cited_rules=["lib.cut_into_glut_silent"])
    assert ob["vetoed_by"] == "no_path" and vol["vetoed_by"] is None
    rows = vetoes.compute(View(db), rounds.get_round(db, rid), "2026-07-15")
    rate = vetoes.veto_rate(rows)
    assert any(v["rate"] and v["rate"] > 0 for v in rate.values())


def test_6_and_7_calls(db):
    rid = base(db)
    with pytest.raises(Refused, match="other"):
        calls.call_add(db, rid, "map", "map", "which", "c", "f", "2026-08-01", "x",
                       branches=[{"branch": "a"}, {"branch": "b"}])
    calls.call_add(db, rid, "map", "map", "which", "c", "f", "2026-08-01", "x",
                   branches=[{"branch": "a"}, {"branch": "other", "falsifier": "a is delivered"}])
    c = calls.call_add(db, rid, "lag_band", "duration", "two hours", "c", "f", "2026-07-20", "x", lag_band="hours")
    assert c["lag_band"] == "hours"


def test_8_unseen_node_type_registers(db):
    positions.node_upsert(db, "strait-q", "strait_never_seen", "a strait")
    assert db.get("node_types", "strait_never_seen") is not None


def test_10_absence_unread_cannot_hit(db):
    rid = base(db)
    c = calls.call_add(db, rid, "null", "absence", "no notice", "c", "f", "2026-07-30", "a notice appears")
    rounds.set_state(db, rid, "walking", "fixture")
    with pytest.raises(Refused, match="silent"):
        calls.score_call(db, c["call_id"], "hit", "unread", "expired")
    calls.score_call(db, c["call_id"], "hit", "silent", "read in full")


# ---------------------------------------------------------------- P2
def test_16_derivation_forced_switch_none(db):
    rid = base(db)
    P(db, "h.unit", "unit_status", "offline")
    P(db, "h.unit", "daily_status_published", "true")
    res = derive.derive_acks(db, rid)
    forced = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"]
    assert forced and forced[0]["result"] == "forced"
    # one condition resting on an inferred position -> switch with it on the fetch list
    P(db, "h.unit", "daily_status_published", "true", conf="inferred")
    res = derive.derive_acks(db, rid)
    d = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"][0]
    assert d["result"] == "switch" and d["fetch_list"][0]["attribute"] == "daily_status_published"
    # documented false -> nothing
    P(db, "h.unit", "daily_status_published", "false")
    res = derive.derive_acks(db, rid)
    d = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"][0]
    assert d["result"] == "none"


def _ratified_restart(db, rid, component=True, lead=30):
    P(db, "h.unit", "unit_status", "offline")
    P(db, "h.unit", "daily_status_published", "true")
    if component:
        P(db, "h.unit", "failed_component_class", "main_transformer")
        positions.bound_add(db, "b.tx", "main_transformer", "repair_lead_days", lead, "days", "fixture vendor note",
                            "2026-06-01")
    res = derive.derive_acks(db, rid)
    ack = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"][0]["ack_id"]
    derive.ack_ratify(db, ack, "ratified", "fixture")
    return ack


def test_17_reach_cut_and_unknown(db):
    rid = base(db)
    ack = _ratified_restart(db, rid, component=False)
    r = {o["outcome_id"]: o for o in reach.reachable(db, ack)["outcomes"]}
    assert r["restart_lt_2w"]["reach"] == "kept_unknown"
    rid2 = admit_round(db, rid="R-T2", node="unit-y")
    ack2 = None
    for h in ("h.unit",):
        positions.position_add(db, h, "unit-y", "unit_status", "offline", "f", "2026-07-01", source_document="d")
        positions.position_add(db, h, "unit-y", "daily_status_published", "true", "f", "2026-07-01", source_document="d")
        positions.position_add(db, h, "unit-y", "failed_component_class", "main_transformer", "f", "2026-07-01", source_document="d")
    positions.bound_add(db, "b.tx", "main_transformer", "repair_lead_days", 30, "days", "fixture", "2026-06-01")
    res = derive.derive_acks(db, rid2)
    ack2 = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"][0]["ack_id"]
    derive.ack_ratify(db, ack2, "ratified", "fixture")
    r2 = {o["outcome_id"]: o for o in reach.reachable(db, ack2)["outcomes"]}
    assert r2["restart_lt_2w"]["reach"] == "cut" and r2["restart_lt_2w"]["evidence_ids"]
    assert r2["restart_2_6w"]["reach"] == "reachable"


def test_18_thesis_exclusion_on_unknown_refused(db):
    rid = base(db)
    ack = _ratified_restart(db, rid, component=False)
    inferred = P(db, "h.unit", "repair_lead_days", 60, conf="inferred")
    with pytest.raises(Refused, match="not documented"):
        reach.thesis_set(db, ack, ["restart_gt_6w"],
                         {"restart_lt_2w": {"position_ids": [inferred["position_id"]]},
                          "restart_2_6w": {"position_ids": [inferred["position_id"]]}}, "f", "c", "f")


def _lockable(db, rid, ack=None):
    intake.tide_declare(db, rid, "us_equity_beta", "fixture")
    manifest(db, rid)


def test_19_and_29_firing_and_segment_clock(db):
    rid = base(db)
    ack = _ratified_restart(db, rid)
    _lockable(db, rid)
    lk0 = lock.lock(db, rid)
    assert rounds.state(db, rid) == "walking"
    with pytest.raises(Refused, match="outcome_id"):
        walk.ack_fire(db, ack, True, "2026-08-20", ["ev"])
    out = walk.ack_fire(db, ack, True, "2026-08-20", ["ev"], outcome_id="restart_2_6w", delivered_fact="back at power")
    assert rounds.state(db, rid) == "pre_lock" and rounds.clock(db, rid) == "2026-08-20"
    # a position knowable after the new clock is ignored by derivation (smoke 29)
    P(db, "h.unit", "unit_status", "online", kf="2026-09-01")
    res = derive.derive_acks(db, rid)
    d = [d for d in res["derivations"] if d["template_id"] == "obl.unit_status_publication"][0]
    assert d["result"] == "forced"
    lk1 = lock.lock(db, rid)
    assert lk1["segment"] == 1 and lk1["lock_hash"] != lk0["lock_hash"]


# ---------------------------------------------------------------- P3
def _stories(db, collinear=False):
    stories.story_add(db, "s.power", "power prices up", ["unit-x", "grid"], proxy=["PWR"])
    stories.story_add(db, "s.gas", "gas up", ["gasnode", "grid"], proxy=["GAS"])
    if collinear:
        stories.story_add(db, "s.zmix", "energy complex", ["grid"], proxy=["MIX"])


def test_20_synthetic_story_decomposed(db):
    rid = base(db, collinear=True)
    _stories(db, collinear=True)
    intake.tide_declare(db, rid, "us_equity_beta", "fixture")
    for h in ("h.owner", "h.merchant", "h.coowner"):
        effects.effect_root(db, rid, h, "unit-x", "revenue", 1, ["ev"], magnitude_pct=1.0)
    ctx = stories.Context(View(db), rounds.get_round(db, rid), "2026-07-15")
    L = stories.loadings(ctx)
    # force exact collinearity in loading space: s.mix = 0.5 s.power + 0.5 s.gas
    L["s.zmix"]["vec"] = 0.5 * L["s.power"]["vec"] + 0.5 * L["s.gas"]["vec"]
    L["s.zmix"]["active"] = True
    c = stories.classify(L, np.ones(len(ctx.index)), "directional")
    assert c["s.zmix"]["class"] == "synthetic"
    assert {o for o, _ in c["s.zmix"]["decomposition"]} == {"s.power", "s.gas"}
    assert c["s.power"]["active"] and c["s.gas"]["active"]


def test_21_thesis_on_active_story_has_zero_rho(db):
    S = np.array([0.3, -0.2, 0.1])
    H = np.column_stack([np.array([1.0, 1.0, 1.0]), S * 2.0])
    perp = stories.s_perp(S, H)
    assert np.linalg.norm(perp) < 1e-10


def test_21_p4_rho_too_small_is_unbuildable(db):
    rid = base(db)
    ack = _ratified_restart(db, rid)
    _stories(db)
    intake.tide_declare(db, rid, "us_equity_beta", "fixture")
    for h in ("h.owner", "h.merchant", "h.coowner"):
        effects.effect_root(db, rid, h, "unit-x", "revenue", 1, ["ev"], magnitude_pct=1.0)
    ctx = stories.Context(View(db), rounds.get_round(db, rid), "2026-07-15")
    L = stories.loadings(ctx)
    # thesis exactly along the power story, which we mark active -> rho = 0
    from nomad16 import construct
    a = db.get("ack_nodes", ack)
    rr = reach.compute(View(db), rounds.get_round(db, rid), a, "2026-07-15")
    sv = {w: {"exp": L["s.power"]["vec"] * 0.05, "S": L["s.power"]["vec"], "unknown": np.zeros(3, dtype=int),
              "flat": False, "bands": np.zeros(3)} for w in ["restart_2_6w", "restart_gt_6w"]}
    L["s.power"]["active"] = True
    cls = stories.classify(L, L["s.power"]["vec"], "directional")
    names, H = stories.hedged_set(ctx, L, cls, [], {})
    b = construct.build(ctx, a, rr, ["restart_2_6w", "restart_gt_6w"], sv, "directional", L["s.power"]["vec"], L, cls,
                        names, H, [], 1000.0)
    assert b["status"] == "unbuildable" and b["reason"] == "rho_too_small"


def test_22_correlation_without_shared_node_is_a_piano(db):
    rid = base(db)
    _stories(db)
    rounds.set_meta(db, rid, "tide_id", "us_equity_beta")
    rounds.set_state(db, rid, "walking", "fixture")
    # make PWR and GAS move together after the trigger
    from nomad16.tests.conftest import write_prices
    import pandas as pd
    dates = pd.bdate_range(end="2026-09-25", periods=400).strftime("%Y-%m-%d").tolist()
    rng = np.random.default_rng(3)
    common = rng.normal(0, 0.02, 400)
    split = dates.index("2026-08-03")
    a = rng.normal(0, 0.01, 400); b = rng.normal(0, 0.01, 400)
    a[split:] += common[split:]; b[split:] += common[split:]
    write_prices(db, "PWR", dates, 100 * np.cumprod(1 + a)); write_prices(db, "GAS", dates, 100 * np.cumprod(1 + b))
    with pytest.raises(Refused, match="JUNCTION_WINDOW"):
        stories.junction_confirm(db, rid, 0, "2026-09-20")  # too few sessions after the trigger
    out = stories.junction_confirm(db, rid, 0, "2026-08-03")
    assert any(p["status"] == "piano" for p in out["pairs"])
    assert db.rows("pianos") and db.rows("pianos")[-1]["outside"] == "junction_without_node"


# ---------------------------------------------------------------- P4
def _full_round(db, switch=False):
    rid = base(db)
    ack = _ratified_restart(db, rid)
    if switch:
        db.upsert("ack_nodes", ack, is_switch=True)
    _stories(db)
    effects.effect_root(db, rid, "h.owner", "unit-x", "revenue", -1, ["ev"], magnitude_pct=-40.0, ack_id=ack)
    effects.effect_root(db, rid, "h.merchant", "unit-x", "revenue", 1, ["ev"], magnitude_pct=35.0, ack_id=ack)
    effects.effect_root(db, rid, "h.coowner", "unit-x", "revenue", -1, ["ev"], magnitude_pct=-20.0, ack_id=ack)
    _lockable(db, rid)
    return rid, ack


def test_23_24_caps(db):
    rid, ack = _full_round(db, switch=True)
    instrument_add(db, "o.AAA.put", "put", "AAA260918P", "2025-01-01", underlying="i.AAA", strikes=[90],
                   expiry="2026-12-18", multiplier=100)
    with pytest.raises(Refused):
        instrument_add(db, "naked", "sold_call", "X", "2025-01-01")
    out = lock.lock(db, rid)
    for b in db.rows("constructed_baskets", "round_id=?", (rid,)):
        for p in db.rows("paper_positions", "basket_id=?", (b["basket_id"],)):
            inst = db.get("instruments", p["instrument_id"])
            assert inst["cap_class"] == "hard", "a switch-derived basket holds hard-capped instruments only"


def test_25_replay_reproduces_after_store_change(db):
    rid, ack = _full_round(db)
    out = lock.lock(db, rid)
    db.upsert("bounds", "b.tx", value=999.0)  # a mutable store corrected after lock
    db.upsert("stories", "s.gas", label="changed")
    rep = lock.replay(db, rid, 0)
    assert rep["reproduces"], rep


def test_26_budget_committed_and_fill_rule(db):
    rid, ack = _full_round(db)
    out = lock.lock(db, rid)
    bs = db.rows("constructed_baskets", "round_id=?", (rid,))
    assert bs
    for b in bs:
        if b["status"] == "unbuildable" and b["detail"].get("z_star_if_committed") is not None:
            assert b["detail"]["z_star_if_committed"] != 0
    # fills: never before knowable_from
    for b in bs:
        if b["status"] == "built":
            rounds.set_meta(db, rid, "knowable_from", "2026-07-15")
            f = paper.fill(db, rid)
            for x in f["fills"]:
                assert x.get("at") is None or x["at"] > "2026-07-15"


def test_27_tide_cap(db):
    rid, ack = _full_round(db)
    lock.lock(db, rid)
    b = lock.budgets(db, rid, "us_equity_beta")
    assert b["tide_used"] <= float(config.get("LOSS_CAP_PER_TIDE")) + 1e-6
    assert b["round_used"] <= float(config.get("LOSS_BUDGET_PER_ROUND")) + 1e-6


def test_28_import_linter():
    price_mods = {"prices", "stories", "construct", "instruments", "paper", "vetoes"}
    for mod in ("derive", "reach", "conditions"):
        tree = ast.parse((PKG / f"{mod}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {a.name for a in node.names} | {(node.module or "").split(".")[-1]}
                assert not (names & price_mods), f"{mod} imports a price-reading module: {names & price_mods}"
    for mod in ("stories", "instruments", "construct"):
        src = (PKG / f"{mod}.py").read_text()
        for table in ("effects", "ack_nodes", "ack_derivations", "ack_outcomes", "thesis_sets"):
            assert f'append("{table}"' not in src and f'upsert("{table}"' not in src, (mod, table)


def test_alt_sources_typed_gap_without_key(db, monkeypatch):
    from nomad16 import altdata
    rid = base(db)
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    out = altdata.alt_fetch(db, rid, "firms", "2026-07-15", "fixture", bbox=[0, 0, 1, 1])
    assert out["status"] == "not_covered"
    with pytest.raises(Refused, match="probe"):
        altdata.alt_fetch(db, rid, "portwatch_chokepoint", "2026-07-15", "fixture", name="Strait of Hormuz")


def test_pit_bound_pre_lock(db):
    from nomad16 import pit
    rid = base(db)
    with pytest.raises(Refused, match="clock"):
        pit.bound(db, rid, "2026-07-16")
    assert pit.bound(db, rid, "2026-07-15") == "2026-07-15"


def test_construction_builds_a_structural_pair_and_hedges_the_tide(db):
    rid, ack = _full_round(db)
    out = lock.lock(db, rid)
    built = [b for b in out["baskets"] if b["status"] == "built"]
    assert built, out["baskets"]
    bid = f"B:{rid}:0:{ack}"
    pos = db.rows("paper_positions", "basket_id=?", (bid,))
    sides = {p["side"] for p in pos}
    assert sides == {1, -1}, "opposite holders on the node supply the hedge"
    tide_exp = sum(p["qty"] * p["exit_rules"]["loadings"]["tide"] for p in pos)
    notional = sum(p["qty"] * abs(p["exit_rules"]["loadings"]["tide"]) for p in pos)
    assert abs(tide_exp) <= 0.25 * notional + 1e-6
    for p in pos:
        assert p["exit_rules"]["stop"], "a stock position carries a stop (smoke 23)"


def test_paper_round_trip(db):
    rid, ack = _full_round(db)
    lock.lock(db, rid)
    f = paper.fill(db, rid)
    assert f["fills"] and all(x["at"] > "2026-07-15" for x in f["fills"])
    bid = f"B:{rid}:0:{ack}"
    ex = paper.exit_basket(db, bid, "2026-09-01", "window_end")
    s = ex["split"]
    assert abs((s["residual"] + s["narrowing"] + s["timing"] - s["costs"] - s["leaks"]) - ex["result"]) < 1e-6
    book = paper.paper_book(db, rid)
    assert book["baskets"][0]["closed"]


def test_walk_hit_holds_the_frontier(db):
    from nomad16 import pit
    rid = base(db)
    rounds.set_state(db, rid, "walking", "fixture")
    db.append("notes", round_id=rid, segment_idx=0, subject="walk_hit", text="2026-07-12 | nrc_status | EV1")
    db.append("notes", round_id=rid, segment_idx=0, subject="walk_read", text="2026-07-12 | x | read | auto")
    with pytest.raises(Refused, match="unresolved"):
        pit.bound(db, rid, "2026-07-13")
    walk.walk_read(db, rid, "2026-07-12", "nrc_status", "not_delivering", ["EV1"])
    assert pit.bound(db, rid, "2026-07-13") == "2026-07-13"


def test_replay_pins_the_appetite_it_locked_with(db, tmp_path, monkeypatch):
    rid, ack = _full_round(db)
    lock.lock(db, rid)
    doc = config.document()
    doc["values"]["EDGE_MARGIN"]["value"] = 0.9  # Rob changes a value after the lock
    p = tmp_path / "appetite_changed.json"
    p.write_text(json.dumps(doc))
    monkeypatch.setattr(config, "APPETITE_PATH", p)
    rep = lock.replay(db, rid, 0)
    assert rep["reproduces"] and "pinned" in rep["config"]
