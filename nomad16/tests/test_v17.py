"""v17 V0 and V1 acceptance checks (docs/nomad_v17_open_entity.md §9.2): A1, A2, A3, A8, A9, A12, A18."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from nomad16 import config, documents, entities, lock, pit, rounds, seed
from nomad16.db import DB, LEDGER, ROOT, TABLES, Refused, now_iso
from nomad16.tests.conftest import admit_round, holders
from nomad16.view import View

FIX = Path(__file__).resolve().parent / "fixtures" / "v16_ledger_columns.json"
REAL = ROOT / "state" / "nomad16.db"


@pytest.fixture
def d17(db):
    seed.seed_v17(db)
    return db


def v17_round(db, rid="R-V17"):
    seed.seed_v17(db)
    admit_round(db, rid=rid, logic="v17")
    rounds.set_meta(db, rid, "knowable_from", "2026-07-15")
    return rid


def evidence(db, rid, text, kf, name="a.txt", source="edgar_doc"):
    return pit._save(db, rid, source, name, text, f"http://fixture/{name}", kf, "edgar", text[:60])


# ---------------------------------------------------------------- A18 and A1
def test_A18_no_ledger_table_gains_a_column():
    frozen = json.loads(FIX.read_text())["tables"]
    for t, cols in frozen.items():
        assert TABLES[t][1] == cols, f"ledger table {t} changed its columns (would break every row hash)"
    new = [t for t, (k, _) in TABLES.items() if k == LEDGER and t not in frozen]
    assert set(new) == {"entity_events", "evidence_entities", "statement_links"}


HEADS = Path(__file__).resolve().parent / "fixtures" / "r16_001_v16_heads.json"


@pytest.mark.skipif(not REAL.exists(), reason="needs the committed R16-001 store")
def test_A1_A18_v17_leaves_the_r16_001_record_identical(tmp_path):
    """Every v16 ledger row is exactly where it was before V0 (same count at the same head hash), the chain
    verifies, and both locks still replay to their hashes, on the store that has been migrated."""
    dst = tmp_path / "real.db"
    shutil.copy(REAL, dst)
    db = DB(dst)  # verifies the chain at start-up
    for t, h in json.loads(HEADS.read_text())["tables"].items():
        rows = db.rows(t)
        assert len(rows) >= h["rows"], t
        if h["rows"]:
            assert rows[h["rows"] - 1]["row_hash"] == h["head"], f"{t}: a v16 row changed"
    assert db.verify_chain() == []
    assert all(lock.replay(db, "R16-001", i)["reproduces"] for i in (0, 1))
    assert len(db.rows("entities")) >= 9 and len(db.rows("key_map")) >= 9  # the migration has been applied
    n = len(db.rows("entities"))
    assert entities.migrate_v17(db)["entities"] == n  # idempotent
    proposed = [e for e in db.rows("entity_events") if e["event_type"] == "merge"]
    assert proposed and all(e["status"] == "proposed" for e in proposed)  # never applied automatically
    assert entities.canonical_map(View(db), "2026-12-31") == {}


def test_migration_proposes_only_compatible_merges(d17):
    from nomad16.positions import holder_upsert, node_upsert
    holder_upsert(d17, "fermi2_unit", "Fermi 2", "unlisted_operating_asset", "company_asset")
    node_upsert(d17, "fermi-2", "power_reactor", "Fermi 2")
    holder_upsert(d17, "miso_lrz7_energy", "MISO LRZ7 price", "aggregate", "commodity")
    node_upsert(d17, "miso-lrz7", "power_market_zone", "the zone")
    out = entities.migrate_v17(d17)
    pairs = [set(p[0]) for p in out["merge_proposals"]]
    assert {"fermi2_unit", "fermi-2"} in pairs             # a facility and its reactor_unit: one thing
    assert {"miso_lrz7_energy", "miso-lrz7"} not in pairs  # a market (composite) and its footprint (place): two things
    with pytest.raises(Refused, match="different kinds"):
        entities.entity_merge(d17, "miso_lrz7_energy", "miso-lrz7", "alias", ["EV1"], "2026-08-01", ratified_by="op", reason="x")


# ---------------------------------------------------------------- A2
def test_A2_open_kinds_unreviewed_cannot_support(d17):
    e = entities.entity_upsert(d17, "corridor-1", "A corridor", "strait_zz", state_attributes=["transit_status"])
    assert d17.get("entity_kinds", "strait_zz")["review"] == "unreviewed" and e["observable"] == "unobservable"
    assert not entities.kind_can_support(d17, "strait_zz")
    with pytest.raises(Refused, match="state test"):
        entities.entity_upsert(d17, "a-sector", "a sector label", "sector_label")
    with pytest.raises(Refused, match="no attribute is registered"):
        entities.kind_ratify(d17, "strait_zz", "r", scale_attribute="none", no_capabilities=True)
    entities.attribute_scope_add(d17, "capacity", ["strait_zz"])
    entities.kind_ratify(d17, "strait_zz", "reviewed after a scoped attribute exists", scale_attribute="none", no_capabilities=True)
    assert entities.kind_can_support(d17, "strait_zz")
    assert "operates_assets" in entities.capabilities_of(d17, entities.entity_upsert(
        d17, "co-1", "Co", "company", state_attributes=["listed"]).get("key", "co-1"))


def test_holder_upsert_alias_mirrors_only_after_seeding(db):
    from nomad16.positions import holder_upsert
    holder_upsert(db, "h.a", "A", "listed_instrument", "company", True, "AAA")
    assert db.get("entities", "h.a") is None  # before the v17 registry exists it behaves exactly as in v16
    seed.seed_v17(db)
    holder_upsert(db, "h.b", "B", "unlisted_operating_asset", "company_asset")
    e = db.get("entities", "h.b")
    assert e["kind"] == "facility" and "has_operating_scale" in entities.capabilities_of(db, "h.b")


# ---------------------------------------------------------------- A8
def test_A8_merge_and_split_are_events_visible_as_of(d17):
    for k, cik in (("e1", "0001"), ("e2", "0001"), ("e3", "0002")):
        entities.entity_upsert(d17, k, k, "company", state_attributes=["listed"], entity_refs={"cik": cik})
    t0 = now_iso()
    with pytest.raises(Refused, match="exact-identifier"):
        entities.entity_merge(d17, "e1", "e3", "exact_identifier", ["EV1"], "2026-08-01", id_type="cik")
    m = entities.entity_merge(d17, "e1", "e2", "exact_identifier", ["EV1"], "2026-08-01", id_type="cik")
    v = View(d17)
    ids = lambda clock: [x["key"] for x in entities.entities_as_of(View(d17), clock)]
    before = ids("2026-07-01")
    assert before == ["e1", "e2", "e3"]                      # a clock before the evidence sees two entities
    assert ids("2026-09-01") == ["e1", "e3"]                 # and after it, one
    assert [x["key"] for x in entities.entities_as_of(View(d17, ledger_cutoff=t0), "2026-09-01")] == ["e1", "e2", "e3"]
    entities.entity_split(d17, m["event_id"], ["EV2"], "2026-10-01", "wrong merge", "op")
    assert ids("2026-09-15") == ["e1", "e3"]                 # between the merge and the split
    assert ids("2026-10-15") == before                       # the split restores the earlier graph
    assert d17.verify_chain() == []


def test_A8_a_name_alone_never_merges_persons_and_aliases_need_ratification(d17):
    with config.pinned(_ingest_on()):
        entities.entity_upsert(d17, "p1", "J. Smith", "person", state_attributes=["office_held"])
        entities.entity_upsert(d17, "p2", "J Smith", "person", state_attributes=["office_held"])
        with pytest.raises(Refused, match="name alone"):
            entities.entity_merge(d17, "p1", "p2", "alias", ["EV1"], "2026-08-01", ratified_by="op", reason="same name")
    entities.entity_upsert(d17, "c1", "Acme Co", "company", state_attributes=["listed"])
    entities.entity_upsert(d17, "c2", "ACME Company", "company", state_attributes=["listed"])
    with pytest.raises(Refused, match="ratification"):
        entities.entity_merge(d17, "c1", "c2", "alias", ["EV1"], "2026-08-01")
    entities.entity_merge(d17, "c1", "c2", "alias", ["EV1"], "2026-08-01", ratified_by="op", reason="same registered name")


# ---------------------------------------------------------------- A9
def _ingest_on():
    doc = json.loads(json.dumps(config.document()))
    doc["values"]["PERSON_INGEST"]["value"] = "on"
    return doc


def test_A9_person_refused_while_ingest_is_off_and_scope_limited_when_on(d17):
    assert config.get("PERSON_INGEST") == "off"
    with pytest.raises(Refused, match="PERSON_INGEST is off"):
        entities.entity_upsert(d17, "p1", "An officer", "person", state_attributes=["office_held"])
    with pytest.raises(Refused, match="PERSON_INGEST is off"):  # any descendant of person too
        entities.kind_add(d17, "officer", "person")
        entities.entity_upsert(d17, "p2", "x", "officer", state_attributes=["office_held"])
    for bad in ("residence_address", "health_status", "sanction_listing", "criminal_proceeding"):
        d17.upsert("position_attributes", bad, type="text", unit=None, allowed=[], description="")
        with pytest.raises(Refused, match="public capacity"):
            entities.attribute_scope_add(d17, bad, ["person"])
    rid = v17_round(d17)
    with config.pinned(_ingest_on()):
        entities.entity_upsert(d17, "p1", "An officer", "person", state_attributes=["office_held"])
    with pytest.raises(Refused, match="not registered for kind person"):
        documents.statement_add(d17, rid, "p1", "share", 5, "inferred")  # a generic attribute is not a person's


def test_A9_fails_closed_when_the_switch_is_missing(d17):
    doc = json.loads(json.dumps(config.document()))
    del doc["values"]["PERSON_INGEST"]
    with config.pinned(doc):
        with pytest.raises(Refused, match="PERSON_INGEST is off"):
            entities.entity_upsert(d17, "p1", "x", "person", state_attributes=["office_held"])


# ---------------------------------------------------------------- A12
def test_A12_entities_honour_exists_from_and_knowable(d17):
    entities.entity_upsert(d17, "co-x", "Co X", "company", state_attributes=["listed"], exists_from="2026-07-01",
                           exists_from_knowable="2026-07-05", exists_to="2026-08-01", exists_to_knowable="2026-09-01")
    has = lambda c: "co-x" in [x["key"] for x in entities.entities_as_of(View(d17), c)]
    assert not has("2026-07-03")    # it existed from 07-01, but that wasn't knowable until 07-05
    assert has("2026-07-10")
    assert has("2026-08-15")        # delisted 08-01, but that isn't knowable until 09-01
    assert not has("2026-09-15")


# ---------------------------------------------------------------- A3
def test_A3_derived_dating(d17):
    rid = v17_round(d17)
    entities.entity_upsert(d17, "unit", "Unit X", "reactor_unit", state_attributes=["unit_status", "capacity"])
    early = evidence(d17, rid, "Status report: Unit X is offline as of the morning. Capacity 1,141 MW.", "2026-07-03", "early.txt")
    late = evidence(d17, rid, "Filing: the unit's four days restart history.", "2026-07-20", "late.txt")
    # (1) a verified states link dates the statement by its own document
    s = documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated",
                                links=[{"evidence_id": early, "role": "states", "span": "Unit X is offline"},
                                       {"evidence_id": late, "role": "component"}])
    assert s["knowable_from"] == "2026-07-03" and s["basis"] == "earliest states link"
    # (2) a states link whose span isn't in the text is stored as component; the latest component dates it
    s = documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated",
                                links=[{"evidence_id": early, "role": "states", "span": "the reactor exploded"},
                                       {"evidence_id": late, "role": "component"}])
    assert s["knowable_from"] == "2026-07-20" and s["links"][0]["role"] == "component"
    assert "span" in s["links"][0]["note"]
    # (3) a numeric attribute's span must contain the value
    s = documents.statement_add(d17, rid, "unit", "capacity", 1141, "stated",
                                links=[{"evidence_id": early, "role": "states", "span": "Capacity 1,141 MW"}])
    assert s["links"][0]["role"] == "component"  # "1,141" is not "1141": the check is literal
    s = documents.statement_add(d17, rid, "unit", "capacity", 1141, "stated",
                                links=[{"evidence_id": early, "role": "states", "span": "Capacity 1,141 MW. 1141"}])
    assert s["links"][0]["role"] == "component"  # the span must occur in the text as quoted
    # (4) a typed date is refused; an inferred statement with no links takes its own recorded time
    with pytest.raises(Refused, match="typed knowable_from is refused"):
        documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated", links=[{"evidence_id": early}],
                                knowable_from="2026-01-01")
    s = documents.statement_add(d17, rid, "unit", "unit_status", "reduced", "inferred")
    p = d17.one("positions", "position_id=?", (s["position_id"],))
    assert p["knowable_from"] <= p["recorded_at"] and s["basis"].startswith("recorded_at")
    with pytest.raises(Refused, match="cites at least one document"):
        documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated")
    # (5) an embargo may only make a statement later
    s = documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated", links=[{"evidence_id": early}],
                                embargo_until="2026-07-09", embargo_reason="operator holds it until the notice")
    assert s["knowable_from"] == "2026-07-09"
    with pytest.raises(Refused, match="earlier than the derived"):
        documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated", links=[{"evidence_id": late}],
                                embargo_until="2026-07-01", embargo_reason="x")
    with pytest.raises(Refused, match="reason"):
        documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated", links=[{"evidence_id": late}],
                                embargo_until="2026-08-01")
    assert d17.verify_chain() == []


def test_A3_the_admission_record_is_a_document_so_the_first_statement_has_one(d17):
    rid = v17_round(d17)
    entities.entity_upsert(d17, "unit", "Unit X", "reactor_unit", state_attributes=["unit_status"])
    doc = documents.admission_record(d17, rid)
    assert doc["document"]["published_at"] == "2026-07-15" and doc["kind"] == "notice"
    s = documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated",
                                links=[{"document": doc["key"], "role": "states", "span": "Unit X trips offline"}])
    assert s["knowable_from"] == "2026-07-15" and s["links"][0]["role"] == "states"


def test_a_v17_round_refuses_the_typed_v16_write_path(d17, tmp_path):
    from nomad16.positions import position_add
    rid = v17_round(d17)
    rounds.write_phase(d17, rid)  # phase.json now names a v17 round
    entities.entity_upsert(d17, "unit", "Unit X", "reactor_unit", state_attributes=["unit_status"])
    with pytest.raises(Refused, match="statement_add"):
        position_add(d17, "unit", "unit", "unit_status", "offline", "f", "2026-07-01", "inferred")


def test_null_node_statements_are_visible_for_the_subject(d17):
    from nomad16.conditions import visible_positions
    rid = v17_round(d17)
    entities.entity_upsert(d17, "unit", "Unit X", "reactor_unit", state_attributes=["unit_status"])
    ev = evidence(d17, rid, "Status report: unit offline.", "2026-07-03", "r.txt")
    documents.statement_add(d17, rid, "unit", "unit_status", "offline", "stated", links=[{"evidence_id": ev}])
    v = View(d17)
    assert len(visible_positions(v, "2026-08-01", holder_id="unit", nodes=["some-node"])) == 1
    assert visible_positions(v, "2026-08-01", nodes=["some-node"]) == []  # a node-only read never sees it


def test_document_lifecycle_transitions_and_evidence(d17):
    rid = v17_round(d17)
    ev = evidence(d17, rid, "Order dated 2026-07-10: the licence is revoked.", "2026-07-10", "order.txt")
    lic = documents.document_from_evidence(d17, evidence(d17, rid, "Licence text", "2026-01-01", "lic.txt"), kind="licence")
    assert documents.document_from_evidence(d17, d17.one("evidence", "content_hash=?", (lic["document"]["content_hash"],))["evidence_id"], kind="licence")["key"] == lic["key"]
    documents.document_state_set(d17, rid, lic["key"], "in_force", [{"evidence_id": ev}])
    with pytest.raises(Refused, match="not a lifecycle transition"):
        documents.document_state_set(d17, rid, lic["key"], "draft", [{"evidence_id": ev}])
    with pytest.raises(Refused, match="evidenced by another document"):
        documents.document_state_set(d17, rid, lic["key"], "revoked", [])
    documents.document_state_set(d17, rid, lic["key"], "revoked", [{"evidence_id": ev, "role": "states", "span": "the licence is revoked"}])
    with pytest.raises(Refused, match="terminal"):
        documents.document_state_set(d17, rid, lic["key"], "in_force", [{"evidence_id": ev}])


@pytest.mark.skipif(not REAL.exists(), reason="needs the committed R16-001 store")
def test_dating_report_on_the_v16_record(tmp_path):
    dst = tmp_path / "real.db"
    shutil.copy(REAL, dst)
    rep = documents.dating_report(DB(dst))
    c = rep["counts"]
    assert sum(c.values()) == 25 and c["no_evidence"] == 3  # the document's figures for R16-001
