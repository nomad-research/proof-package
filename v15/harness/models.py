"""Pydantic input models (§6, tightened A4/A6/A7/A12/A13, decomposed B1/B2/B3/B4, v8 branches and narrative rows)."""
import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CallType = Literal["sign", "magnitude_order", "lag_band", "predicate", "null", "meta", "map", "narrative"]
Sign = Literal["+", "-", "0"]
LagBand = Literal["days", "weeks", "months", "never"]
Outcome = Literal["hit", "miss", "unverified", "untestable"]
MechanismOutcome = Literal["right", "wrong", "unknown"]
BaselineOutcome = Literal["hit", "miss", "unverified"]
Observed = Literal["holds", "fails", "unknown"]
Coverage = Literal["adequate", "thin", "english_only", "none"]
Scorer = Literal["self", "second", "human"]
Scope = Literal["event", "node"]
Aggregation = Literal["max", "min", "all"]

_WINDOW_RE = re.compile(r"^(scoring_window|days:\d{1,4}|until:\d{4}-\d{2}-\d{2})$")

# B4: one claim per row. A clause counts when it has at least four words and a verb.
_VERBS = frozenset({
    "is", "are", "was", "were", "be", "stays", "stay", "stayed", "closes", "close", "closed", "reopens", "reopen",
    "reopened", "remains", "remain", "holds", "hold", "fails", "fail", "moves", "move", "declares", "declare", "issues",
    "cites", "keeps", "lands", "goes", "comes", "rises", "falls", "reprices", "omits", "declines", "resumes", "opens",
    "restarts", "shuts", "suspends", "cuts", "shows", "sees", "gets", "has", "have", "does", "do", "lasts", "clears",
    "exceeds", "occurs", "appears", "emerges", "exists", "arrives", "leaves", "runs", "ran", "sits", "carries",
})
# B1: duration and extent claims are decomposable
_OPERATIONAL = re.compile(
    r"\b(operational|closed|shut|reopen\w*|out of (service|operation)|offline|restart\w*|resume\w*|stays? (open|shut|closed)|"
    r"part of|whole|entire|all of|confined to|contained within|out for|down for|lasts?)\b", re.I)
_TIME = re.compile(r"\b(within|for|after|over|beyond|at least|about)\s+(a |an |\d+ |\w+ )?(hour|day|week|month|year)s?\b|\b(hours|days|weeks|months)\b", re.I)
# F1: a narrative row's carrier is a channel that says things, never a series that prints numbers
PRICE_SERIES = re.compile(r"\b(price|prices|index|indices|assessment|assessments|close|closes|futures|spread|spreads|"
                          r"rate|rates|quote|quotes|yield|yields|differential|differentials|premia|premium|premiums)\b", re.I)


def independent_clauses(text: str) -> int:
    parts = re.split(r";|\band\b", text)
    n = 0
    for p in parts:
        words = [w.strip(",.:()'\"") for w in p.split()]
        if len(words) >= 4 and any(w.lower() in _VERBS for w in words):
            n += 1
    return n


# v13 B4: an absence claim carrying its own conditional. The two markers sit in different clauses, so a falsifier
# written for one limb silently leaves the other unfalsified. Word lists rather than a regex: the words are the point.
ABSENCE_WORDS = ("no", "none", "not", "nothing", "neither", "does not", "do not", "without", "never")
CONDITIONAL_WORDS = ("if any", "if it", "if they", "if either", "were to", "should any", "should it",
                     "in the event that", "if one", "if none", "if that", "if so")


def _says(words: tuple[str, ...], text: str) -> bool:
    t = " " + " ".join((text or "").lower().replace(",", " ").replace(".", " ").split()) + " "
    return any(" " + w + " " in t for w in words)


def conditional_conjunction(claim: str) -> bool:
    text = claim or ""
    for sep in (", with ", ", and ", "; ", ", where ", ", though "):
        head, found, tail = text.partition(sep)
        if found and _says(ABSENCE_WORDS, head) and _says(CONDITIONAL_WORDS, tail):
            return True
    return False


def is_decomposable(call_type: str, claim: str) -> bool:
    if call_type == "lag_band":
        return True
    if call_type in ("narrative", "meta", "map"):
        return False
    return bool(_OPERATIONAL.search(claim) and _TIME.search(claim))


class FactorIn(BaseModel):
    factor: str
    holder_id: Optional[str] = Field(default=None, description="holder id, key or alias this factor sits on")
    node: Optional[str] = None
    estimate: str = Field(description="for durations: days|weeks|months|never; for extents: the expected state")
    carrier: str
    falsifier: str
    binding: bool = Field(default=False, description="the operator thinks this factor sets the outcome")
    against: bool = Field(default=False, description="a factor that would make the claim false")

    @model_validator(mode="after")
    def _rules(self):
        for k in ("factor", "estimate", "carrier", "falsifier"):
            if not getattr(self, k).strip():
                raise ValueError(f"factor.{k} is required")
        return self


class ConditionalOn(BaseModel):
    prediction_ref: str = Field(description="the map call this row depends on: '#<index>' within the same lock batch, or an existing prediction id")
    branch: str = Field(description="the branch of that map call under which this row is scored")


class PredictionIn(BaseModel):
    call_type: CallType
    target: str = Field(description="entity, carrier, predicate name, or a (holder_id, node) position; 'none' for null calls")
    claim: str
    carrier: Optional[str] = Field(default=None, description="what will be checked to score this; required for all but meta")
    falsifier: Optional[str] = Field(default=None, description="what appearing first kills this call; required for sign/magnitude_order/narrative")
    falsifier_window: Optional[str] = Field(
        default=None,
        description="scoring_window | days:N | until:YYYY-MM-DD. Required for null and predicate calls; defaults to scoring_window otherwise.")
    mechanism_ids: list[str] = Field(default_factory=list, description="library rule ids or keys; [] only with a 'no-mechanism:' reason in claim")
    baseline_claim: str = Field(description="what the dumb baseline says for this target")
    sign: Optional[Sign] = None
    magnitude_rank: Optional[int] = None
    lag_band: Optional[LagBand] = None
    confidence_band: Optional[str] = None
    hypothesis_id: Optional[str] = Field(default=None, description="standing hypothesis this call resolves, if any")
    factors: list[FactorIn] = Field(default_factory=list, description="B1: required on lag_band calls and on duration/extent claims; >=1 binding and >=1 against")
    aggregation: Optional[Aggregation] = Field(default=None, description="max (durations: slowest factor sets the date) | min | all (extents)")
    branches: list[str] = Field(default_factory=list, description="v8 B1: on a map call with real uncertainty, >=2 named alternatives; downstream rows are written per branch")
    conditional_on: Optional[ConditionalOn] = Field(default=None, description="v8 B1: this row is scored only if the named branch of a map call arose; otherwise untestable, weight 0")
    implied_at_lock: Optional[dict] = Field(
        default=None,
        description="v12 D1: what was already priced, required on sign and magnitude_order calls on a listed leg. "
                    "{method: option_implied|realised_since_event|none, value: expected move over the window (%), "
                    "source: carrier, as_of: datetime, basis: text}. method 'none' needs a reason in basis and makes the leg non-executable.")
    base_rate_id: Optional[str] = Field(default=None, description="v12 F3: the institutional frequency this occurrence call departs from (id or key)")
    settling_document: Optional[str] = Field(
        default=None,
        description="v14 C3: on a map call, the primary document that would settle it (url or a named instrument). The "
                    "operator is 0-for-3 on map calls where the settling document existed at lock and was not fetched.")
    settling_document_fetched: Optional[bool] = Field(default=None, description="v14 C3: whether it was actually fetched at lock")
    due_at: Optional[str] = Field(default=None, description="v10 A2: the date (YYYY-MM-DD, <= event_date + 90 days) by which this call's carrier will have spoken; required (narrative rows default to event_date + 5)")
    effect_kind: Optional[Literal["direction", "volume", "vol", "timing"]] = Field(default=None, description="v10 J: the grid cell's effect kind; defaults by call type (lag_band -> timing, else direction)")
    window: Optional[Literal["event_day", "days", "weeks", "to_due"]] = Field(default=None, description="v10 J: the grid window; defaults from falsifier_window")
    narrative_sign: Optional[Sign] = Field(default=None, description="v8 F1: what the named channel says the event implies for the leg")
    position_id: Optional[str] = Field(default=None, description="v8 F1: the leg (positions row id) a narrative row measures; also accepted on sign calls")
    effect_id: Optional[str] = Field(default=None, description="v15 A1/A2: the effect this call scores. The effect IS the claim, with its own carrier and falsifier; position_id stays for history and is never removed.")

    @model_validator(mode="after")
    def _rules(self, info):
        strict = not (info.context or {}).get("lenient")     # retro seed rounds predate B1/B4
        errs: list[str] = []
        if not self.claim.strip():
            errs.append("claim is required")
        if not self.baseline_claim.strip():
            errs.append("baseline_claim is required (say what the dumb baseline predicts)")
        if self.call_type != "meta" and not (self.carrier or "").strip():
            errs.append("carrier is required for every call type except meta (name what will be checked to score it)")
        if self.call_type in ("sign", "magnitude_order", "narrative") and not (self.falsifier or "").strip():
            errs.append("falsifier is required for sign, magnitude_order and narrative calls (what appearing first kills this call)")
        if self.call_type == "sign" and self.sign is None:
            errs.append("sign call needs sign in {+, -, 0}")
        if self.call_type == "magnitude_order" and self.magnitude_rank is None:
            errs.append("magnitude_order call needs magnitude_rank (int)")
        if self.call_type == "lag_band" and self.lag_band is None:
            errs.append("lag_band call needs lag_band in {days, weeks, months, never}")
        if self.call_type == "null" and self.target != "none":
            errs.append('null call requires target="none"')
        if self.call_type == "narrative":
            if self.narrative_sign is None:
                errs.append("narrative row needs narrative_sign in {+, -, 0}: what the channel says the event implies for the leg")
            if not self.position_id:
                errs.append("narrative row needs position_id: the leg (positions row) it measures")
            if self.mechanism_ids:
                errs.append("narrative rows carry no mechanism: they measure what a channel said, not whether it was right")
            if self.carrier and PRICE_SERIES.search(self.carrier):
                errs.append("narrative carrier must be a channel that says things (bounded-channel set or carriers registry), never a price series")
        elif self.narrative_sign is not None:
            errs.append("narrative_sign is only accepted on narrative rows")
        # v14 C3: a map call names the document that would settle it, and says so if it could not be fetched. Round 9's
        # site ownership, round 10's repeat-filer base rate and round 13's ITC caption were all fetchable at lock and
        # none was fetched; that is three misses out of three with the answer sitting in a primary document.
        if strict and self.call_type == "map" and not (self.settling_document or "").strip() and "no-settling-document:" not in self.claim:
            errs.append("a map call names the primary document that would settle it (settling_document), and either "
                        "fetches it at lock or writes 'no-settling-document: <why>' in the claim. Three map calls have "
                        "been lost to a document that existed and was not read")
        if self.call_type == "map":
            if self.mechanism_ids and not (info.context or {}).get("allow_map_mechanism"):
                pass   # a rule that carries `map` may be cited; the carriage check at lock decides
            if self.branches:
                clean = [b.strip() for b in self.branches if b.strip()]
                if len(set(clean)) < 2:
                    errs.append("a map call with branches needs >=2 distinct named alternatives")
                self.branches = clean
        elif self.branches:
            errs.append("branches are only accepted on map calls")
        if self.call_type not in ("map", "narrative") and not self.mechanism_ids and "no-mechanism:" not in self.claim:
            errs.append('mechanism_ids is empty: cite library rule ids, or include "no-mechanism: <why>" in the claim')
        if self.call_type in ("null", "predicate") and not self.falsifier_window:
            errs.append("falsifier_window is required for null and predicate calls (scoring_window | days:N | until:YYYY-MM-DD)")
        if self.falsifier_window and not _WINDOW_RE.match(self.falsifier_window):
            errs.append("falsifier_window must be scoring_window, days:N or until:YYYY-MM-DD")
        if self.falsifier_window and self.falsifier_window.startswith("until:"):
            try:
                date.fromisoformat(self.falsifier_window[6:])
            except ValueError:
                errs.append("falsifier_window until: date is not a valid ISO date")
        if self.due_at:
            try:
                date.fromisoformat(self.due_at)
            except ValueError:
                errs.append("due_at must be YYYY-MM-DD")
        if self.implied_at_lock is not None:
            im = self.implied_at_lock
            if not isinstance(im, dict):
                errs.append("implied_at_lock must be an object {method, value, source, as_of, basis}")
            else:
                if im.get("method") not in ("option_implied", "realised_since_event", "none"):
                    errs.append("implied_at_lock.method must be option_implied, realised_since_event or none")
                if im.get("method") == "none" and not str(im.get("basis") or "").strip():
                    errs.append("implied_at_lock.method 'none' needs a basis saying why nothing could be read")
                if im.get("method") != "none":
                    try:
                        float(im.get("value"))
                    except (TypeError, ValueError):
                        errs.append("implied_at_lock.value must be a number: the expected move over the call's window, in per cent")
                    if not str(im.get("source") or "").strip():
                        errs.append("implied_at_lock.source is required: the carrier the reading came from")
        # B4: one claim per row
        if strict and self.call_type in ("sign", "map", "null") and independent_clauses(self.claim) >= 2:
            errs.append("split it: the claim joins two independently falsifiable statements (';' or ' and ' between clauses). "
                        "The falsifier is the negation of the whole row, or the row is two rows")
        # v13 B4: the shape round 12's call 6 got through - an absence claim conjoined with its own conditional, so one
        # limb can hold while the other fails and the falsifier only ever tests the second one.
        if strict and self.call_type in ("sign", "magnitude_order", "null") and conditional_conjunction(self.claim):
            errs.append("split it: this row conjoins an absence claim with a conditional about what would happen if the "
                        "absence failed ('none moves, with X ranked first if any were to'). One limb can hold while the "
                        "other fails and the falsifier tests only one of them. Write the absence, or write the ranking")
        # B1/B2: decompose or don't claim
        if strict and is_decomposable(self.call_type, self.claim):
            if not self.factors:
                errs.append("decompose or don't claim: a duration or extent claim needs factors[] "
                            "(factor, holder_id?, node?, estimate, carrier, falsifier, binding, against) and an aggregation")
            else:
                if not any(f.binding for f in self.factors):
                    errs.append("factors need at least one marked binding (the factor the operator thinks sets the outcome)")
                if not any(f.against for f in self.factors):
                    errs.append("factors need at least one marked against (a factor that would make the claim false)")
                if self.aggregation is None:
                    self.aggregation = "max" if self.call_type == "lag_band" else "all"
                if self.call_type == "lag_band" and self.aggregation in ("max", "min"):
                    bad = [f.estimate for f in self.factors if f.estimate not in ("days", "weeks", "months", "never")]
                    if bad:
                        errs.append(f"duration factors must estimate a lag band (days|weeks|months|never); got {bad}")
        elif self.factors:
            errs.append("factors are only accepted on lag_band calls and duration/extent claims")
        if errs:
            raise ValueError("; ".join(errs))
        if not self.falsifier_window:
            self.falsifier_window = "scoring_window"
        return self


class TouchedSetIn(BaseModel):
    holder_id: str = Field(description="holder id, key or alias")
    degree: int = Field(ge=0, le=3)
    node: str
    position_summary: str
    substitutability: Literal["low", "med", "high", "unknown"]
    duration_factor: Optional[str] = Field(default=None, description="text or none")
    carrier: Optional[str] = Field(default=None, description="text or none")
    mechanism_ids: list[str] = Field(default_factory=list, description="v9 C1: library rule ids or keys that support this leg; required on every component of a synthetic")

    @model_validator(mode="after")
    def _rules(self):
        if not self.node.strip() or not self.position_summary.strip():
            raise ValueError("node and position_summary are required on every touched_set row")
        if self.duration_factor and self.duration_factor.strip().lower() == "none":
            self.duration_factor = None
        if self.carrier and self.carrier.strip().lower() == "none":
            self.carrier = None
        return self


class FactorOutcomeIn(BaseModel):
    factor_index: int
    outcome: Outcome
    observed: Optional[str] = Field(default=None, description="for durations: the observed lag band")
    evidence_ids: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class ResolutionIn(BaseModel):
    prediction_id: str
    outcome: Outcome = Field(description="for decomposed calls this is overridden by the derived composite")
    mechanism_outcome: MechanismOutcome
    baseline_outcome: BaselineOutcome
    evidence_ids: list[str] = Field(default_factory=list)
    scorer_note: str = ""
    source_coverage: Optional[Coverage] = Field(
        default=None, description="adequate | thin | english_only | none. Required when outcome is miss or unverified.")
    scorer: Scorer = Field(default="self", description="self | second | human (who scored this)")
    late_falsifier: bool = Field(default=False, description="a falsifying fact was observed outside the falsifier window; it did not fire")
    supersedes: Optional[str] = Field(default=None, description="resolution id this corrects; the old row stays")
    factor_outcomes: list[FactorOutcomeIn] = Field(default_factory=list, description="required, one per factor, on decomposed calls")
    branch_arose: Optional[str] = Field(default=None, description="v8 B1: on a map call with branches, which branch arose (one of its branches, or 'none')")
    early: bool = Field(default=False, description="v10 A3: the scorer marks this call resolved before its due_at (say why in scorer_note)")

    @model_validator(mode="after")
    def _rules(self):
        errs: list[str] = []
        if self.outcome in ("miss", "unverified") and not self.source_coverage:
            errs.append(f"source_coverage is required when outcome is {self.outcome} (adequate | thin | english_only | none)")
        if self.outcome == "hit" and self.source_coverage == "none":
            errs.append("a hit cannot rest on source_coverage none; score it unverified")
        if errs:
            raise ValueError("; ".join(errs))
        return self


class PredicateCheckIn(BaseModel):
    predicate_id: str = Field(description="predicate id, key or unique name")
    claimed: Observed
    observed: Optional[Observed] = None
    note: Optional[str] = None
    scope: Optional[Scope] = Field(default=None, description="event | node; required for first traversal, one row each")
    basis: Optional[str] = Field(default=None, description="the specific observation the claim rests on; required when claimed is not unknown. A class prior is not a basis.")
    position_id: Optional[str] = Field(default=None, description="D3: the leg (positions row or synthetic leg) this check applies to; null for round-level facts")

    @model_validator(mode="after")
    def _rules(self):
        if self.claimed != "unknown" and not (self.basis or "").strip():
            raise ValueError("basis is required when claimed is holds or fails: cite the specific observation, or claim unknown")
        return self


class SecondScoreIn(BaseModel):
    prediction_id: str
    outcome: Outcome
    mechanism_outcome: MechanismOutcome
    baseline_outcome: BaselineOutcome
    evidence_ids: list[str] = Field(default_factory=list)
    scorer_note: str = ""
    source_coverage: Optional[Coverage] = None
    factor_outcomes: list[FactorOutcomeIn] = Field(default_factory=list)
    branch_arose: Optional[str] = None


class HypothesisCheckIn(BaseModel):
    predicate_id: str = Field(description="predicate id, key or unique name")
    observed: Observed
    evidence_ids: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class AliasIn(BaseModel):
    alias: str
    alias_kind: Literal["name", "former_name", "subsidiary", "plant_name", "ticker", "abbreviation"] = "name"
    source: str = "operator"
    knowable_from: Optional[str] = None
