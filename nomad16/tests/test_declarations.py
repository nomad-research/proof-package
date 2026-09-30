"""Every source Nomad reads declares itself; the support rule reads the declarations."""
import pytest

from nomad16 import altdata, declarations as D
from nomad16.db import Refused


def test_every_adapter_source_is_declared_and_an_undeclared_one_is_refused():
    for s in altdata.SOURCES | {"nrc_en", "nrc_status", "edgar_filings", "edgar_doc", "wayback"}:
        assert s in D.BY_ID, s
    with pytest.raises(Refused):
        D.declaration("some_new_feed")


def test_a_source_supports_only_claims_about_its_own_phenomenon():
    assert D.may_support("edgar_doc", "corporate_disclosure")["supports"] is True
    assert D.may_support("prices_yahoo", "corporate_disclosure")["supports"] is False      # trading activity proposes about a company
    assert D.may_support("gdelt_events", "corporate_disclosure")["supports"] is False
    assert D.may_support("nrc_status", "physical_state")["supports"] is True                # a recorded power level supports a statement about state
    assert D.may_support("prices_yahoo", "exchange_activity")["supports"] is True           # attention sources support claims about themselves


def test_a_modeled_measurement_is_analogical_until_validated():
    assert D.declaration("s2_image").evidence_mode == "analogical"
    assert D.may_support("s2_image", "physical_state")["supports"] is False
    validated = D.SourceDeclaration(**{**D.declaration("s2_image").__dict__, "validated_against": "nrc_status"})
    assert validated.evidence_mode == "supports"


def test_a_snapshot_with_unrecoverable_deletions_has_no_honest_history():
    bad = D.SourceDeclaration(source_id="x", dataset_kind="media_event", measurement_process="p", phenomenon="retail_discourse", truth_role="constitutive",
                              measurement_type="measured", retrieval="snapshot", survivorship="deletions_unrecoverable", historical_access="record_only")
    assert bad.has_honest_history is False
    assert D.check_historical("nrc_status")["retrieval"] == "as_of"


def test_the_prices_carry_their_known_limits_and_the_listing_names_what_is_unverified():
    assert "currently-listed names only" in D.declaration("prices_yahoo").known_biases
    assert D.source_declarations()["verified"] is False and D.source_declarations("keyed")["sources"][0]["source_id"] == "firms"
