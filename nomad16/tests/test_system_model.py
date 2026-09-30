"""The whole-system entity model (config/system_model.json, docs/nomad_v17_entity_model.md): it covers every table and its constraints are internally consistent."""
import json
from pathlib import Path

from nomad16.db import TABLES

ROOT = Path(__file__).resolve().parents[2]
M = json.loads((ROOT / "config" / "system_model.json").read_text())
V17 = json.loads((ROOT / "config" / "seed_v17.json").read_text())


def test_every_table_is_read_in_the_model_and_nothing_else_is():
    assert set(M["table_map"]) == set(TABLES)


def test_kinds_have_parents_and_relation_roles_name_real_kinds():
    have = {k["kind"] for k in M["kinds"]} | {k["kind"] for k in V17["entity_kinds"]} | {"statement", "*", "document_series", "instrument", "person", "event"}
    for k in M["kinds"]:
        assert k["parent"] is None or k["parent"] in have, k
    for r in M["relation_types"]:
        for role in r["roles"]:
            for f in role["filter"].split("|"):
                assert f in have, (r["type"], f)


def test_the_hedge_relation_is_one_way_single_sink_acyclic_long_only_and_shadows_are_never_traded():
    rel = {r["type"]: r for r in M["relation_types"]}
    assert all(rel["hedges"]["constraints"][c] for c in ("acyclic", "single_sink", "no_cross_thesis", "long_only"))
    assert rel["shadows"]["constraints"]["never_traded"]


def test_price_is_attentional_and_cannot_be_evidence_for_exposures():
    kinds = {k["kind"]: k for k in M["kinds"]}
    assert "attentional" in kinds["price_series"]["capabilities"] and kinds["price_series"]["parent"] == "dataset"
    rel = {r["type"]: r for r in M["relation_types"]}
    for name in ("states", "component", "exposed_to"):                   # R6: price is never the evidence for a statement, an exposure or an effect
        assert "price_series" in rel[name]["constraints"]["excludes_source_kinds"], name
    assert any(r.startswith("R6") for r in M["rules"])


def test_every_dataset_kind_has_an_evidence_mode_and_attention_never_supports():
    ds = [k for k in M["kinds"] if k["parent"] == "dataset"]
    assert {k["kind"] for k in ds} >= {"fundamental", "state_observation", "regulatory_record", "legal_filing", "media_event", "price_series", "quote", "calendar_fact"}
    for k in ds:
        assert k["evidence_mode"] in {"physical", "accounting", "regulatory", "scheduled", "attentional", "analogical", "structural"}, k["kind"]
    modes = {k["kind"]: k["evidence_mode"] for k in ds}
    assert modes["price_series"] == modes["media_event"] == modes["quote"] == "attentional" and modes["remote_sensing"] == "analogical"
    assert any(r.startswith("R13") for r in M["rules"])


def test_dataset_kinds_carry_ohmni_phenomenon_truth_role_and_measurement_type():
    e = M["ohmni_enums"]
    allowed_ph = set(e["phenomenon"]) | set(e["nomad_additions"])
    ds = [k for k in M["kinds"] if k["parent"] == "dataset" and k.get("evidence_mode") != "structural"]
    for k in ds:
        assert k["phenomenon"] in allowed_ph and k["truth_role"] in e["truth_role"] and k["measurement_type"] in e["measurement_type"], k["kind"]
    attention = {"information_seeking", "editorial_publication", "retail_discourse", "aggregated_belief", "exchange_activity", "off_exchange_routing"}
    for k in ds:                       # the mode follows the phenomenon and the measurement type
        if k["phenomenon"] in attention:
            assert k["evidence_mode"] == "attentional", k["kind"]
        if k["measurement_type"] == "modeled":
            assert k["evidence_mode"] == "analogical", k["kind"]


def test_the_enums_match_the_ohmni_clone_when_it_is_present():
    import pytest
    p = Path("/home/user/ohmni/contract/declaration.py")
    if not p.exists():
        pytest.skip("ohmni clone not present")
    src = p.read_text()
    for name in M["ohmni_enums"]["phenomenon"] + M["ohmni_enums"]["truth_role"] + M["ohmni_enums"]["measurement_type"]:
        assert f'"{name}"' in src, name
