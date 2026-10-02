"""What each source says about itself (v17 A2). An idea adopted from Ohmni's source declarations, built for Nomad's own adapters; Nomad has no dependency on Ohmni.

Every adapter Nomad has, and every source the look-backs used, is declared here: what it measures (the phenomenon), the truth role of its records, whether a measurement is measured or modeled, whether a historical query returns
what stood then (``as_of``) or the present value (``snapshot``), whether deleted records are recoverable, how far it can be backfilled, and what it needs. The declarations are the builder's, not verified against each source's own documentation
(``verified`` is False until someone checks), and they are data: the rules below read them.

Rule R13 (config/system_model.json): a dataset supports a statement about X only if its phenomenon is the one X consists of and its truth role is constitutive, attested or observed, and a modeled measurement is analogical until it is validated
against a measured one. A dataset of a different phenomenon proposes only. ``may_support`` is that rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .db import Refused

PHENOMENA = {"corporate_disclosure", "exchange_activity", "off_exchange_routing", "information_seeking", "editorial_publication",
             "retail_discourse", "regulatory_action", "aggregated_belief", "physical_state", "schedule"}
ATTENTION = {"information_seeking", "editorial_publication", "retail_discourse", "aggregated_belief", "exchange_activity", "off_exchange_routing"}
TRUTH_ROLES = {"constitutive", "attested", "observed", "reported", "echoed", "derived"}
SUPPORTIVE_ROLES = {"constitutive", "attested", "observed"}


@dataclass(frozen=True)
class SourceDeclaration:
    source_id: str
    dataset_kind: str
    measurement_process: str
    phenomenon: str
    truth_role: str
    measurement_type: str              # measured | modeled
    retrieval: str                     # as_of | snapshot
    survivorship: str                  # complete | deletions_unrecoverable
    historical_access: str             # bulk | metered | rate_limited | record_only
    backfilled: bool = False
    status: str = "built"              # built | keyed | not_built | look_back_only
    needs: tuple[str, ...] = ()
    known_biases: tuple[str, ...] = ()
    validated_against: str | None = None   # the measured source a modeled one has been checked against
    verified: bool = False

    def __post_init__(self):
        if self.phenomenon not in PHENOMENA:
            raise Refused(f"{self.source_id}: phenomenon {self.phenomenon!r} is not declared")
        if self.truth_role not in TRUTH_ROLES:
            raise Refused(f"{self.source_id}: truth role {self.truth_role!r} is not declared")
        if self.measurement_type not in {"measured", "modeled"}:
            raise Refused(f"{self.source_id}: measurement_type is measured or modeled")

    @property
    def evidence_mode(self) -> str:
        if self.phenomenon in ATTENTION:
            return "attentional"
        if self.measurement_type == "modeled" and not self.validated_against:
            return "analogical"
        return "supports" if self.truth_role in SUPPORTIVE_ROLES else "proposes"

    @property
    def has_honest_history(self) -> bool:
        return not (self.retrieval == "snapshot" and self.survivorship == "deletions_unrecoverable")


def _d(**kw) -> SourceDeclaration:
    return SourceDeclaration(**kw)


DECLARATIONS: tuple[SourceDeclaration, ...] = (
    _d(source_id="nrc_en", dataset_kind="regulatory_record", measurement_process="NRC daily event notification reports, one text file per day",
       phenomenon="regulatory_action", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="nrc_status", dataset_kind="state_observation", measurement_process="NRC daily power reactor status: percent power per unit, as reported to the NRC",
       phenomenon="physical_state", truth_role="observed", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="edgar_filings", dataset_kind="legal_filing", measurement_process="SEC submissions index: what a filer had filed, with filing dates",
       phenomenon="corporate_disclosure", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="edgar_doc", dataset_kind="legal_filing", measurement_process="the text of a filed document at its accession",
       phenomenon="corporate_disclosure", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="wayback", dataset_kind="legal_filing", measurement_process="an Internet Archive capture of a page as it stood at a capture time",
       phenomenon="editorial_publication", truth_role="echoed", measurement_type="measured", retrieval="as_of", survivorship="deletions_unrecoverable", historical_access="rate_limited",
       known_biases=("captures are sparse and not random", "an uncaptured page or revision is unrecoverable")),
    _d(source_id="s2_scenes", dataset_kind="remote_sensing", measurement_process="Sentinel-2 scene catalogue search",
       phenomenon="physical_state", truth_role="observed", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="s2_image", dataset_kind="remote_sensing", measurement_process="a model reading of a Sentinel-2 image: a count of bright pixels above a threshold",
       phenomenon="physical_state", truth_role="observed", measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk",
       known_biases=("cloud cover", "the threshold is the builder's")),
    _d(source_id="portwatch_chokepoint", dataset_kind="state_observation", measurement_process="IMF PortWatch daily vessel transits at a chokepoint, estimated from ship-tracking data",
       phenomenon="physical_state", truth_role="observed", measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="portwatch_port", dataset_kind="state_observation", measurement_process="IMF PortWatch daily port calls, estimated from ship-tracking data",
       phenomenon="physical_state", truth_role="observed", measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk"),
    _d(source_id="gdelt_events", dataset_kind="media_event", measurement_process="GDELT 2.0 machine-coded events from worldwide news, 15-minute exports",
       phenomenon="editorial_publication", truth_role="observed", measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk",
       known_biases=("coding is automatic", "counts reflect media volume, not events")),
    _d(source_id="ioda", dataset_kind="state_observation", measurement_process="IODA internet connectivity signals for a country",
       phenomenon="physical_state", truth_role="observed", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="rate_limited"),
    _d(source_id="usgs_quakes", dataset_kind="state_observation", measurement_process="USGS earthquake catalogue",
       phenomenon="physical_state", truth_role="observed", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk",
       known_biases=("magnitudes are revised",)),
    _d(source_id="firms", dataset_kind="state_observation", measurement_process="NASA FIRMS VIIRS active-fire detections (an algorithm on thermal imagery)",
       phenomenon="physical_state", truth_role="observed", measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk", status="keyed", needs=("FIRMS_MAP_KEY",)),
    _d(source_id="gfw", dataset_kind="state_observation", measurement_process="Global Fishing Watch vessel presence", phenomenon="physical_state", truth_role="observed",
       measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="metered", status="not_built", needs=("GFW_TOKEN",)),
    _d(source_id="acled", dataset_kind="media_event", measurement_process="ACLED coded conflict events", phenomenon="editorial_publication", truth_role="reported",
       measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="metered", status="not_built", needs=("ACLED_KEY", "ACLED_EMAIL")),
    _d(source_id="black_marble", dataset_kind="remote_sensing", measurement_process="NASA Black Marble night lights", phenomenon="physical_state", truth_role="observed",
       measurement_type="modeled", retrieval="as_of", survivorship="complete", historical_access="bulk", status="not_built", needs=("EARTHDATA_TOKEN",)),
    _d(source_id="prices_yahoo", dataset_kind="price_series", measurement_process="daily closes from Yahoo's chart endpoint, stored in the vintage store",
       phenomenon="exchange_activity", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="deletions_unrecoverable", historical_access="metered",
       known_biases=("currently-listed names only", "closes are adjusted retroactively", "metadata drifts between fetches")),
    _d(source_id="sec_xbrl_facts", dataset_kind="fundamental", measurement_process="SEC structured facts: line items per period with filing dates, restatements kept as separate facts",
       phenomenon="corporate_disclosure", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk", status="look_back_only"),
    _d(source_id="fed_statements", dataset_kind="regulatory_record", measurement_process="Federal Reserve policy statements and the FOMC calendar",
       phenomenon="regulatory_action", truth_role="constitutive", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk", status="look_back_only"),
    _d(source_id="hurdat2", dataset_kind="state_observation", measurement_process="NHC best-track archive of Atlantic tropical cyclones",
       phenomenon="physical_state", truth_role="observed", measurement_type="measured", retrieval="as_of", survivorship="complete", historical_access="bulk", status="look_back_only",
       known_biases=("tracks are revised after the season",)),
)
BY_ID = {d.source_id: d for d in DECLARATIONS}


def declaration(source_id: str) -> SourceDeclaration:
    if source_id not in BY_ID:
        raise Refused(f"no declaration for source {source_id!r}: an undeclared source is not read")
    return BY_ID[source_id]


def may_support(source_id: str, claim_phenomenon: str) -> dict:
    """R13. A source supports a claim only about its own phenomenon, with a supportive truth role, and not while it is modeled and unvalidated."""
    d = declaration(source_id)
    if claim_phenomenon not in PHENOMENA:
        raise Refused(f"claim phenomenon {claim_phenomenon!r} is not declared")
    if d.phenomenon != claim_phenomenon:
        return {"supports": False, "why": f"{source_id} measures {d.phenomenon}, not {claim_phenomenon}: it may propose"}
    if d.truth_role not in SUPPORTIVE_ROLES:
        return {"supports": False, "why": f"truth role {d.truth_role} does not support"}
    if d.measurement_type == "modeled" and not d.validated_against:
        return {"supports": False, "why": "a modeled measurement is analogical until validated against a measured source"}
    return {"supports": True, "why": "same phenomenon, supportive truth role"}


def check_historical(source_id: str) -> dict:
    d = declaration(source_id)
    if not d.has_honest_history:
        raise Refused(f"{source_id} has no honest historical mode (a snapshot with unrecoverable deletions): forward recording only")
    return {"source_id": source_id, "historical_access": d.historical_access, "retrieval": d.retrieval, "survivorship": d.survivorship}


def source_declarations(status: str | None = None) -> dict:
    """Every declared source, its evidence mode and what it needs."""
    rows = [{"source_id": d.source_id, "kind": d.dataset_kind, "phenomenon": d.phenomenon, "truth_role": d.truth_role, "measurement_type": d.measurement_type,
             "evidence_mode": d.evidence_mode, "historical_access": d.historical_access, "status": d.status, "needs": list(d.needs), "verified": d.verified}
            for d in DECLARATIONS if status in (None, d.status)]
    return {"sources": rows, "verified": False, "note": "declared by the builder; not checked against each source's own documentation"}
