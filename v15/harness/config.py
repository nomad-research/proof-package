"""Pre-registered constants. Changing any of these is a config commit, not a runtime parameter.
Reviewed once at twenty clean rounds (NULL_CALL_WEIGHT, QUALITY_FACTORS, VALIDATION_THRESHOLD), then locked again.
Never tuned to make a rule validate."""
import os
from pathlib import Path

# Invariant 6. Logged with every score.
NULL_CALL_WEIGHT: float = 0.2

# A2: the operator model id comes from the environment (set by the human in .mcp.json), never from the tool call.
OPERATOR_MODEL_ENV = "NOMAD_OPERATOR_MODEL"
DEFAULT_OPERATOR = "claude-fable-5-1"

# Seed values for the model_cutoffs table (human-populated; CLI `nomad-harness model-cutoff set`).
MODEL_CUTOFF_SEED: dict[str, str] = {
    "claude-fable-5-1": "2026-06-30",
    "claude-opus-5": "2026-06-30",
    "claude-sonnet-5": "2026-06-30",
}

# A3: clean window = [cutoff + 1 day, today - CLEAN_WINDOW_LAG_DAYS]
CLEAN_WINDOW_LAG_DAYS = 28

# A4: default falsifier window per lag band (days after event_date); None = until scoring.
SCORING_WINDOW_DAYS: dict[str | None, int | None] = {"days": 14, "weeks": 56, "months": 183, "never": None, None: 28}

# A12: quality factors. Each is a place the resolution could be wrong.
# v12 §0.5: the round_class factor is gone. v11 §A1 excludes learning resolutions from weights entirely, so a factor
# that scaled them was dead code pretending to be a policy.
QUALITY_FACTORS: dict[str, dict[str, float]] = {
    "round_class": {"clean": 1.0, "learning": 1.0},
    "scorer": {"self": 0.6, "second": 0.85, "human": 1.0},
    "source_coverage": {"adequate": 1.0, "thin": 0.7, "english_only": 0.7, "none": 0.0},
    "call_type": {"positive": 1.0, "null": NULL_CALL_WEIGHT},
    "evidence_class": {"stated_dated": 1.0, "inferred": 0.7, "none": 0.7},
}
# quality_m (misses) applies coverage, evidence and call-type factors; never the round-class or scorer factor.
MISS_FACTORS: tuple[str, ...] = ("source_coverage", "evidence_class", "call_type")

# A5: candidate -> validated needs weight >= threshold, hits in >= 2 distinct clean rounds, 0 undiscounted misses,
# >= 1 non-null hit. Two clean self-scored positive hits on stated-dated evidence = 1.2; two learning ones = 0.6.
VALIDATION_THRESHOLD: float = 1.0

# v8 §A1: what a rule can be cited on.
CARRIES: tuple[str, ...] = ("occurrence", "absence", "ordering", "magnitude", "duration", "map")

# v8 §E3: synthetic support = min(component support) x COMPONENT_DISCOUNT^(n-1). Pre-registered; reviewed with the rest.
COMPONENT_DISCOUNT: float = 0.85

# v8 §D3: scheduled statements surfaced at reveal when within this many days of the event.
SCHEDULED_WINDOW_DAYS: int = 7

# ---- v10 --------------------------------------------------------------------------------------------------------
# §A: per-call due dates. Every call names the date by which its carrier will have spoken.
DUE_AT_MAX_DAYS: int = 90
NARRATIVE_DUE_DAYS: int = 5          # A4: narrative rows are due five days after the event by default and are scored first

# §B: cap and required mix under the freeze (pre-registered; reviewed at twelve clean rounds)
CAP_TAGS: tuple[str, ...] = ("weather", "late_headline")
SIZE_BANDS: tuple[str, ...] = ("underread", "headline", "trivia")
FREEZE_ROUNDS: int = 7
REQUIRED_MIX: dict[str, int] = {"headline": 4, "lag_test": 3}

# §D: cross-node synthetic takes one extra discount step for the hop between nodes.
CROSS_NODE_DISCOUNT: float = 0.85

# §I: price as an outcome timestamp only. Band = last close x (1 +- BAND_SIGMA x stdev of the prior BAND_SESSIONS daily returns).
BAND_SESSIONS: int = 20
BAND_SIGMA: float = 2.0

# v11 §D: stratified enumeration. Carrier density sends selection to sectors with open registries, which are
# recurring-disruption nodes by construction (round 9). The selector draws in stratum order, not date order.
STRATA: tuple[str, ...] = ("chemical", "ports_logistics", "power_grid", "corporate_distress", "regulatory", "other")
# Per rolling ten admitted rounds. Pre-registered; reviewed at twenty like every other threshold.
# v12 §0.5: the quotas are ceilings that sum to the window, not floors that sum past it. As seeded they summed to 16
# over a rolling 10 and permitted exactly the concentration §D was written to prevent.
STRATUM_QUOTA: dict[str, int] = {"chemical": 2, "ports_logistics": 2, "power_grid": 1, "corporate_distress": 2, "regulatory": 2, "other": 1}
STRATUM_WINDOW_ROUNDS: int = 10

# v12 §E1: participant classes (pre-registered, closed) and the distance matrix behind E5. Adjacency is the routine
# channel between two classes in ordinary practice; distance is the shortest path, capped at 3.
PARTICIPANT_CLASSES: tuple[str, ...] = ("contract", "credit", "equity_generalist", "equity_specialist", "options",
                                        "compliance", "physical_press", "procurement")
CLASS_ADJACENCY: dict[str, tuple[str, ...]] = {
    "contract": ("procurement", "physical_press"),
    "procurement": ("contract", "physical_press"),
    "physical_press": ("contract", "procurement", "compliance", "equity_specialist"),
    "compliance": ("physical_press", "credit"),
    "credit": ("compliance", "equity_specialist"),
    "equity_specialist": ("equity_generalist", "options", "physical_press", "credit"),
    "equity_generalist": ("equity_specialist", "options"),
    "options": ("equity_specialist", "equity_generalist"),
}
# v12 §E2: the named channels that can carry a fact between classes.
CHANNELS: tuple[str, ...] = ("sell_side_coverage", "shared_data_vendor", "index_event", "rating_action", "trade_press_pickup")

# v12 §D3: implied methods, and the threshold above which implied counts as "materially above zero" for a fadeable null.
IMPLIED_METHODS: tuple[str, ...] = ("option_implied", "realised_since_event", "none")
FADEABLE_IMPLIED_MIN: float = 2.0        # per cent over the call's window; pre-registered, reviewed at twenty

# v11 §C: the three gates that still refuse an event. Everything else is a tag, filtered at analysis time.
INTAKE_GATES: tuple[str, ...] = ("Q3", "Q8", "Q9")

# §J: the effect grid. Declared at v10, frozen for seven admitted rounds. Extending it is a schema change.
EFFECT_KINDS: tuple[str, ...] = ("direction", "volume", "vol", "timing")
GRID_DEGREES: tuple[int, ...] = (0, 1, 2, 3)
WINDOWS: tuple[str, ...] = ("event_day", "days", "weeks", "to_due")
FACTOR_KINDS: tuple[str, ...] = ("equity", "private", "physical", "aggregate")
# falsifier_window -> grid window: days:N maps by N; scoring_window and until: map to to_due
WINDOW_DAYS: dict[str, int] = {"event_day": 2, "days": 14, "weeks": 56}

# The tradability gate (v4 §4.3 arming predicate 6). Matched by predicate key or name.
TRADABILITY_GATE_KEYS: tuple[str, ...] = (
    "pred.arm.tradability_gate",
    "tradability gate (single-name and pair forms)",
    "pair_gate_opposing_listed_positions",
)

# A8: MCP servers the retrieval hook does not treat as retrieval surfaces. Everything else under mcp__ is denied
# unless a round is open.
HOOK_ALLOWED_MCP_SERVERS: tuple[str, ...] = (
    "nomad", "ccd_session", "ccd_directory", "ccd_session_mgmt", "terminal", "visualize", "plugin_pdf-viewer_pdf",
)

# Invariant 5: capitalised tokens allowed inside rule text.
NOUN_ALLOWLIST: frozenset[str] = frozenset({
    "AI", "US", "EU", "UK", "UN",
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
    "Q1", "Q2", "Q3", "Q4",
})

SENTENCE_STARTERS: frozenset[str] = frozenset({
    "a", "an", "the", "this", "that", "these", "those", "it", "its", "they", "their",
    "if", "when", "whenever", "where", "wherever", "while", "once", "until", "unless",
    "before", "after", "as", "because", "since", "so", "then", "than",
    "who", "whoever", "what", "whatever", "which", "whichever", "how", "why",
    "no", "not", "never", "nothing", "nobody", "none", "every", "each", "any", "some",
    "all", "most", "many", "few", "more", "less", "first", "last", "second",
    "in", "on", "at", "by", "for", "from", "to", "with", "without", "under", "over",
    "between", "among", "across", "against", "into", "out", "up", "down",
    "and", "but", "or", "nor", "yet", "there", "here", "one", "two", "three",
    "expect", "assume", "treat", "prefer", "watch", "ignore", "count",
    "prices", "price", "insurance", "freight", "constraint", "constraints", "tolls", "toll",
    "cargo", "operators", "operator", "holders", "holder", "positions", "position",
    "markets", "market", "rules", "rule", "sequence", "transmission", "ownership",
})

CORPORATE_SUFFIXES: frozenset[str] = frozenset({
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "llc", "plc", "nv", "sa", "ag", "gmbh", "bv", "lp", "llp", "pte", "pty", "srl",
    "spa", "kk", "oyj", "ab", "as", "se", "sarl", "bhd", "sdn",
})


# ---- v13 §A: surviving risk ------------------------------------------------------------------------------------
# The mirror basket is retired as a generator: absence of an opinion was never evidence, and cell enumeration produced
# 126 legs on round 12 of which perhaps eight had a structural reason behind them. What replaces it is one question per
# leg -- does any risk survive it -- answered by running the silence rules as eliminators rather than as predictions.
ELIMINATORS: tuple[str, ...] = ("tide", "traversed", "weather", "slack", "self_hedged", "immaterial_position", "no_path")

# Pre-registered preconditions (§A3): an eliminator is evaluated on a leg only where its precondition holds, and is
# recorded as not-applicable elsewhere. A rule does not cover every leg; it covers the legs its precondition is true on.
ELIMINATOR_PRECONDITION: dict[str, str] = {
    "tide":                "factor_kind == 'equity'",
    "traversed":           "q1a == 'fail'",
    "weather":             "q1b == 'fail'",
    "slack":               "factor_kind in ('physical', 'aggregate', 'private')",
    "self_hedged":         "always",
    "immaterial_position": "position_share is not None",
    "no_path":             "always",
}
ELIMINATOR_RULE: dict[str, str] = {
    "tide": "lib.equity_visibility_ratio", "traversed": "lib.novelty_channels_not_events",
    "weather": "lib.recurring_disruption_weather", "slack": "lib.cut_into_glut_silent",
    "self_hedged": "lib.wounded_owner_collects_premium", "immaterial_position": "positions store",
    "no_path": "spec 6.4 admissibility",
}
# Thresholds, pre-registered and reviewed at twenty with everything else.
TIDE_RATIO_MIN: float = 1.0          # expected move over the leg's own band; below this the event is inside the tide
POSITION_SHARE_FLOOR: float = 0.05   # a holder's stated share of the node below which the position is immaterial
SURVIVING_MAGNITUDE_MIN: float = 1.0  # magnitude below this is recorded surviving-but-small, never a candidate

# ---- v13 §B1: empirical bands and a liquidity qualifier ----------------------------------------------------------
# A 2-sigma parametric band breached on 23 of 62 sessions is mis-specified, not mis-calibrated. The empirical trailing
# distribution makes no normality claim; the turnover floor says when the series is too thin to read at all.
BAND_METHOD: str = "empirical"       # empirical | parametric (parametric retained for replaying old rows)
BAND_SESSIONS_EMPIRICAL: int = 60
BAND_PCTILE: tuple[float, float] = (5.0, 95.0)
TURNOVER_FLOOR_USD: float = 2_000_000.0    # median daily turnover; below it observations are band_reliable = false
# Static, dated FX for the turnover floor only (never for a claim): rates as of 2026-09-01, one decimal of care.
# Build-only: no brief gives these. They exist so a floor stated in one currency can be applied to every listing.
FX_TO_USD: dict[str, float] = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "GBp": 0.0127, "SEK": 0.095, "NOK": 0.092,
                               "DKK": 0.145, "PLN": 0.25, "CHF": 1.13, "ZAR": 0.055, "ZAc": 0.00055, "CLP": 0.00105,
                               "INR": 0.012, "SGD": 0.74, "CAD": 0.73, "AUD": 0.66, "JPY": 0.0067, "HKD": 0.128,
                               "CNY": 0.14, "KRW": 0.00072, "TWD": 0.031, "BRL": 0.18, "MXN": 0.050}


# ---- v14 §A: generate wide, eliminate with anchors, diagnose what survives -----------------------------------------
# Thirteen rounds, zero armed legs. Arming was an AND over eight predicates, so we did not discover that arming is hard,
# we specified it to be near-impossible and then measured that it was. A filter never violated is a filter never tested.
# What replaces the conjunction is a vector kept AS a vector: five terms at 0.6 and one term at 0.03 with four at 0.95
# collapse to the same product and are completely different situations. The first is uniformly mediocre; the second is
# one wall, and a wall is a fact about a specific thing that might change or that a different leg routes around.
VECTOR_TERMS: tuple[str, ...] = ("stake", "structural", "pricedness", "operator", "expression")

# Appetite is a choice, stated once, reviewed at twenty, and never tuned to make legs arm. Every term reads
# higher-is-better, so appetite is a floor and the binding term is the one furthest below its own floor.
APPETITE: dict[str, float] = {"stake": 1.0, "structural": 0.60, "pricedness": 0.50, "operator": 0.40, "expression": 0.50}

# v14 A2: permissive generation. A hunch may propose a leg into the space and may never support one; only anchors and
# fetched facts keep it there. A wrong analogy costs an eliminated leg, not a scored miss.
GENERATION_ORIGINS: tuple[str, ...] = ("position", "hop_parent", "hop_child", "hop_counterparty", "hop_chain", "analogy", "operator")
GENERATION_MIN_WIDTH: int = 10          # round 13 generated ten legs by hand; that is the number to beat

# v14 A5: operator risk is computed from clean resolutions, never asserted. These are the modifiers already known to
# matter from the ledger; the structure is frozen and only the values move, and they move from counts.
OPERATOR_MODIFIERS: tuple[str, ...] = ("settling_document_fetched", "base_rate_cited", "claim_is_conjunction", "degree")
OPERATOR_PRIOR_N: int = 4               # pseudo-count for a shape the ledger has seen too little of


# ---- v15: the effect, not the leg, is the unit ----------------------------------------------------------------------
# A leg carries one sign and the world does not. A concentrate buyer facing a smelter outage has higher input cost AND
# volume shortfall AND a delivery obligation AND, if diversified, better pricing on its own competing output -- four
# effects, different magnitudes, different timings, different carriers, some opposed. Recording one arrow discards
# three of them before the work starts.

# §A1: effect kinds. Wider than the v10 grid, which had no room for a cost or an obligation.
EFFECT_KINDS_V15: tuple[str, ...] = ("direction", "volume", "vol", "timing", "cost", "obligation")

# §6.4 / §I2: how a relation carries. Only physical, contractual and accounting relations may support a resolution;
# attentional and analogical relations may propose and never support; attribute edges do not carry an effect at all.
RELATION_MODES: tuple[str, ...] = ("physical", "contractual", "accounting", "attentional", "analogical", "attribute")
TRANSMITTING_MODES: tuple[str, ...] = ("physical", "contractual", "accounting")

# §A4/§A6: relation types, the mode each one carries in, and the discount an effect takes crossing one hop of it.
# Pre-registered as appetite (§K3): reviewed on a schedule, never moved because a path needed to be longer.
RELATION_TYPES: dict[str, str] = {
    "offtake":           "contractual",
    "input_supply":      "contractual",
    "input_cost":        "contractual",
    "ownership":         "accounting",
    "shared_facility":   "physical",
    "shared_infrastructure": "physical",
    "logistics":         "physical",
    "regulatory_scope":  "contractual",
    "index_membership":  "attribute",
    "listing_venue":     "attribute",
    "reporting_currency": "attribute",
    "sector":            "attribute",
    "size_bucket":       "attribute",
    "coverage":          "attentional",
    "analogy":           "analogical",
}
HOP_DISCOUNT: dict[str, float] = {
    "offtake": 0.70, "input_supply": 0.70, "input_cost": 0.65, "ownership": 0.85, "shared_facility": 0.75,
    "shared_infrastructure": 0.70, "logistics": 0.65, "regulatory_scope": 0.60, "coverage": 0.40, "analogy": 0.0,
    "index_membership": 0.0, "listing_venue": 0.0, "reporting_currency": 0.0, "sector": 0.0, "size_bucket": 0.0,
}
DEFAULT_HOP_DISCOUNT: float = 0.5

# §A4: the transform seed. Composition through a relation is a mapping, not a sign flip: a shortfall maps strongly to
# a buyer's cost effect, strongly to its volume effect, and not at all to its delivery obligation. Most entries are
# "does not transmit", which is what makes the table smaller and more honest than a sign matrix. Absent entries are
# zero: a transform must be stated to exist. The operator may state one with a reason, and that is logged as a
# proposal rather than merged into the seed.
TRANSFORM_SEED: dict[tuple[str, str, str], float] = {
    # (relation_type, parent effect kind, child effect kind): weight
    ("offtake", "volume", "volume"): 0.9,
    ("offtake", "volume", "cost"): 0.8,
    ("offtake", "volume", "obligation"): 0.0,
    ("offtake", "volume", "timing"): 0.5,
    ("offtake", "cost", "cost"): 0.8,
    ("offtake", "direction", "direction"): 0.5,
    ("input_supply", "volume", "volume"): 0.9,
    ("input_supply", "volume", "cost"): 0.85,
    ("input_supply", "volume", "obligation"): 0.6,
    ("input_supply", "cost", "cost"): 0.8,
    ("input_cost", "cost", "cost"): 0.85,
    ("input_cost", "cost", "direction"): 0.5,
    ("input_cost", "cost", "obligation"): 0.0,
    ("ownership", "direction", "direction"): 0.9,
    ("ownership", "volume", "direction"): 0.7,
    ("ownership", "cost", "direction"): 0.7,
    ("ownership", "obligation", "obligation"): 0.5,
    ("shared_facility", "volume", "volume"): 0.8,
    ("shared_facility", "timing", "timing"): 0.7,
    ("shared_facility", "volume", "obligation"): 0.0,
    ("shared_infrastructure", "volume", "volume"): 0.75,
    ("shared_infrastructure", "timing", "timing"): 0.7,
    ("logistics", "timing", "timing"): 0.8,
    ("logistics", "volume", "timing"): 0.7,
    ("logistics", "volume", "volume"): 0.6,
    ("regulatory_scope", "obligation", "obligation"): 0.8,
    ("regulatory_scope", "timing", "timing"): 0.6,
    ("regulatory_scope", "obligation", "cost"): 0.5,
}

# §A9: the frontier bound. One event x four root effects x three children each is 40 nodes by depth three; anchors are
# what should hold the width, and this is what stops it when they do not. Pre-registered, never raised to fit a round.
FRONTIER_BOUND: int = 120

# §F4: independence from shared ancestry. Two paths that split early and reconverge are two pieces of evidence; two
# that split at the last node are one with a rounding error. Indexed by the depth of the most recent common ancestor
# relative to the shallower path: 0 = split at the root (independent), rising toward 1 = split at the last node.
INDEPENDENCE_DISCOUNT_AT_ROOT: float = 1.0
INDEPENDENCE_DISCOUNT_AT_LEAF: float = 0.15

# §F6: an effect below this support is not an implicit position; and support without stake is inert, not consensus.
SUPPORT_THRESHOLD: float = 0.30
INERT_STAKE_MAX: float = 0.25

# §E2: a branch has converged when its remaining implications differ from the price-implied path at the same nodes by
# less than this, in units of the leg's own band. Convergence prunes the converged and never the divergent (§E3).
CONVERGENCE_THRESHOLD: float = 0.5

# §H5: basket_stake = intended residual / declared synthetic exposure. Below this the basket is a position on
# something nobody chose, whatever the effect-level reasoning was.
BASKET_STAKE_FLOOR: float = 1.0

# §I1: node kinds. An attribute node is a shared loading, never a transmission path.
NODE_KINDS: tuple[str, ...] = ("event", "attribute")
ATTRIBUTE_KINDS: tuple[str, ...] = ("listing_venue", "reporting_currency", "index_membership", "sector", "size_bucket")


def db_path() -> Path:
    return Path(os.environ.get("NOMAD_HARNESS_DB", "nomad_harness.db"))


def operator_model() -> str:
    return os.environ.get(OPERATOR_MODEL_ENV) or DEFAULT_OPERATOR
