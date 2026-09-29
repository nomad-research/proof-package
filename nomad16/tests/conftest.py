"""Fixture world for the smoke tests (§17: fixture-only by default, no network).

One node (a generating unit), three listed holders on it (an owner hurt by the outage, a
merchant competitor helped by it, a utility co-owner), an unlisted operating asset, an
authority, a tide proxy and two story proxies. Prices are synthetic and written straight
into the vintage store.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from nomad16 import config, intake, rounds, seed as seedmod
from nomad16.db import DB, canon, sha


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(rounds, "PHASE_FILE", tmp_path / "phase.json")
    monkeypatch.setattr(intake, "GUARD_LOG", tmp_path / "guard16_log.jsonl")
    import nomad16.pit as pit
    import nomad16.report as report
    monkeypatch.setattr(pit, "ROOT", tmp_path)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(intake, "ROOT", tmp_path)
    monkeypatch.setenv("NOMAD_OPERATOR_MODEL", "test-model")
    d = DB(tmp_path / "t.db")
    seedmod.seed(d)
    yield d
    d.close()


def write_prices(db: DB, symbol: str, dates, closes, volume=5_000_000):
    rows = [{"date": d, "open": c, "high": c, "low": c, "close": float(c), "adjclose": float(c), "volume": volume}
            for d, c in zip(dates, closes)]
    payload = {"symbol": symbol, "rows": rows}
    vid = f"V{len(db.rows('price_vintages')) + 1:05d}"
    db.append("price_vintages", vintage_id=vid, symbol=symbol, source="fixture", retrieved_at="fixture",
              from_date=dates[0], to_date=dates[-1], payload=payload, payload_hash=sha(canon(payload)),
              metadata={"fixture": True}, drift_of=None)
    return vid


def make_world(db: DB, clock="2026-07-15", n=400, seed=7, collinear=False):
    """Synthetic returns: tide T, story factors F1 (power prices) and F2 (gas); three stocks."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2026-09-25", periods=n).strftime("%Y-%m-%d").tolist()
    T = rng.normal(0, 0.01, n)
    F1 = rng.normal(0, 0.012, n)
    F2 = rng.normal(0, 0.015, n)
    eA, eB, eC = (rng.normal(0, 0.012, n) for _ in range(3))
    rA = 0.9 * T + 0.6 * F1 + eA
    rB = 1.1 * T - 0.5 * F1 + 0.3 * F2 + eB
    rC = 0.6 * T + 0.2 * F1 + eC
    for sym, r in (("SPY", T), ("PWR", F1), ("GAS", F2), ("AAA", rA), ("BBB", rB), ("CCC", rC)):
        write_prices(db, sym, dates, 100 * np.cumprod(1 + r))
    if collinear:
        write_prices(db, "MIX", dates, 100 * np.cumprod(1 + 0.5 * F1 + 0.5 * F2))
    return dates


def admit_round(db: DB, rid="R-T1", event_date="2026-07-15", node="unit-x", node_type="power_plant",
                provisional=True, live=False):
    from nomad16.positions import node_upsert
    node_upsert(db, node, node_type, "fixture unit")
    db.append("rounds", round_id=rid, event_line="Unit X trips offline", event_date=event_date, event_time=None,
              node=node, node_type=node_type, stratum="energy", feed_set="fixture", intake_mode="strict_v3",
              round_class="learning", live=live, operator_model="test-model", operator_cutoff="2026-06-30",
              operator_runtime="pytest", harness_version=config.harness_version(), logic_version="v16",
              config_hash=config.config_hash(),
              presort_active=False, domain_pref=None, candidate_id=None, q_results={"event_date": event_date})
    rounds.set_meta(db, rid, "knowable_from", event_date)
    db.append("segments", round_id=rid, idx=0, clock=event_date, opened_by_ack_id=None, opened_by_firing_id=None,
              locked_at=None, lock_hash=None, manifest_id=None, wall_clock=None)
    rounds.set_state(db, rid, "pre_lock", "fixture reveal")
    return rid


def manifest(db: DB, rid: str):
    intake.GUARD_LOG.write_text(json.dumps({"at": "2999-01-01T00:00:00Z", "tool": "WebSearch", "permitted": False,
                                            "reason": "fixture denial"}) + "\n")
    rounds.set_meta(db, rid, "revealed_at", "2000-01-01T00:00:00Z")
    return intake.operator_manifest(db, rid, "test-model", "pytest", "2026-06-30", "fixture", "s1", True)


def holders(db: DB):
    from nomad16.positions import holder_upsert
    from nomad16.instruments import instrument_add
    holder_upsert(db, "h.owner", "Owner Co", "listed_instrument", "company", True, "AAA")
    holder_upsert(db, "h.merchant", "Merchant Co", "listed_instrument", "company", True, "BBB")
    holder_upsert(db, "h.coowner", "Co-owner Utility", "listed_instrument", "company", True, "CCC")
    holder_upsert(db, "h.unit", "Unit X", "unlisted_operating_asset", "company_asset")
    holder_upsert(db, "h.reg", "The regulator", "authority", "agency")
    for k, s, h in (("i.AAA", "AAA", "h.owner"), ("i.BBB", "BBB", "h.merchant"), ("i.CCC", "CCC", "h.coowner")):
        instrument_add(db, k, "stock", s, "2000-01-01", holder_id=h)
