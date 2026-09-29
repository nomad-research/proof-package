"""Schema, append-only triggers, hash chain, verify_chain.

Invariants enforced here:
 1. Append-only ledger tables: BEFORE UPDATE / BEFORE DELETE triggers RAISE(ABORT).
 2. Hash chain: row_hash = sha256(prev_row_hash || canonical_json(row)) per table, in rowid order.
    Hash form v2 drops NULL-valued columns, so nullable columns can be added later without breaking old chains.
    Rows written before the tightening pass (form v1: the original column set, NULLs kept) still verify.
 4. Bitemporal: recorded_at is set here and only here; callers passing it are rejected.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .errors import HarnessError, NotFound
from .util import canonical_json, now_iso, sha256_hex, uuid7

GENESIS_HASH = "0" * 64

LEDGER_TABLES: tuple[str, ...] = (
    "events", "rounds", "round_transitions", "round_classifications", "event_criteria", "round_notes", "reveal_context",
    "touched_set", "predictions", "prediction_factors", "evidence", "resolutions", "factor_resolutions", "second_scores",
    "scorecards", "predicate_checks", "t0_candidates", "aliases", "orphans", "positions", "node_facts",
    "hypothesis_checks", "hook_denials", "narrowing_log", "synthetic_legs", "pit_fetches",
    "round_tags", "event_rejections", "selection_windows", "notebook_rows",
    "scheduled_links", "enumeration_candidates", "price_observations", "grid_cells", "coverage_migrations",
    "replay_measurements", "leg_annotations", "scoring_sessions", "firewall_violations",
    "surviving_risk", "leg_claims", "move_log",
    # v15: the effect DAG, the ACK graph, segments, contradictions, declared synthetic exposure
    "effects", "ack_firings", "segments", "contradictions", "synthetic_exposures",
)

MUTABLE_TABLES: tuple[str, ...] = ("library_rules", "predicates", "holders", "hypotheses", "model_cutoffs", "ingest_targets",
                                   "carriers", "synthetic_rules", "snapshot_targets", "selector", "feeds", "risk_rules", "settings",
                                   "base_rates",
                                   # v15: relations, transforms, node kinds and the standing ACK graph are stores,
                                   # not ledgers -- they are built up and corrected, and what they date is on the
                                   # ledger in ack_firings
                                   "relations", "transforms", "nodes", "ack_nodes")

CALL_TYPES = ("sign", "magnitude_order", "lag_band", "predicate", "null", "meta", "map", "narrative")

KEYED_TABLES: tuple[str, ...] = ("library_rules", "predicates", "holders", "carriers", "synthetic_rules",
                                 "relations", "transforms", "nodes", "ack_nodes")

# Column sets as they were before the tightening pass (hash form v1). Used only to verify legacy rows.
V1_COLUMNS: dict[str, tuple[str, ...]] = {
    "events": ("id", "event_text", "event_date", "source", "selection_rule", "rejected_before", "criteria_json",
               "event_hash", "recorded_at"),
    "rounds": ("id", "event_id", "operator", "operator_cutoff", "state", "state_changed_at", "recorded_at"),
    "round_transitions": ("id", "round_id", "from_state", "to_state", "reason", "recorded_at"),
    "predictions": ("id", "round_id", "call_type", "target", "claim", "hypothesis_id", "sign", "magnitude_rank",
                    "lag_band", "carrier", "falsifier", "mechanism_ids", "baseline_claim", "confidence_band",
                    "locked_at", "recorded_at"),
    "evidence": ("id", "round_id", "url", "title", "source_time", "knowable_from", "excerpt", "note", "recorded_at"),
    "resolutions": ("id", "prediction_id", "outcome", "mechanism_outcome", "quarantined", "baseline_outcome",
                    "evidence_ids", "scorer_note", "weight", "null_call_weight", "supersedes", "recorded_at"),
    "scorecards": ("id", "round_id", "scorecard_json", "null_call_weight", "recorded_at"),
    "predicate_checks": ("id", "round_id", "predicate_id", "claimed", "observed", "note", "recorded_at"),
    "t0_candidates": ("id", "event_id", "window_label", "criteria_pass", "arming_pass_single", "arming_pass_pair",
                      "listed_party", "pair_holders", "carrier", "micro_macro_note", "recorded_at"),
    "aliases": ("id", "holder_id", "alias", "alias_norm", "alias_kind", "source", "knowable_from", "recorded_at"),
    "orphans": ("id", "raw_string", "raw_norm", "context", "round_id", "recorded_at"),
    "positions": ("id", "holder_id", "node", "attribute", "value", "unit", "source", "source_time", "knowable_from",
                  "confidence", "supersedes", "recorded_at"),
    "hypothesis_checks": ("id", "hypothesis_id", "predicate_id", "observed", "evidence_ids", "note", "recorded_at"),
}

SCHEMA = """
-- ---- v15 §A1: the effect row replaces the leg as the unit ----------------------------------------------------
-- An effect IS a claim, with a carrier and a falsifier, scored on its own. A holder with five effects has five
-- chances to be wrong, not five chances to be right. There is no sign field anywhere: sign is a projection applied
-- at generation time, which is the worst possible moment for it, and net direction is derived late (§A3).
CREATE TABLE IF NOT EXISTS effects (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  parent_effect_id TEXT,
  holder_id TEXT,
  node TEXT NOT NULL,
  effect_kind TEXT NOT NULL CHECK (effect_kind IN ('direction','volume','vol','timing','cost','obligation')),
  magnitude REAL,
  magnitude_basis TEXT,
  carrier TEXT,
  due_at TEXT,
  falsifier TEXT,
  relation_id TEXT,
  relation_type TEXT,
  transform_id TEXT,
  transform_weight REAL,
  depth INTEGER NOT NULL,
  attenuated_support REAL,
  root_effect_id TEXT,
  root_depth INTEGER,
  mechanism_ids TEXT,
  ack_id TEXT,
  segment_id TEXT,
  origin TEXT,
  basis TEXT,
  carried_by TEXT,
  migrated INTEGER NOT NULL DEFAULT 0,
  eliminated INTEGER NOT NULL DEFAULT 0,
  elimination_basis TEXT,
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS effects_round ON effects(round_id);
CREATE INDEX IF NOT EXISTS effects_parent ON effects(parent_effect_id);

-- ---- v15 §I: relations, with transmits on the edge -----------------------------------------------------------
-- "Orthogonal is known, not assumed" was only ever true of factors modelled as transmission paths. The
-- correlations that hurt live in edges nobody drew, so splitting the edge types stops the graph treating its own
-- silence as evidence. transmits=0 edges are summed in construction and never traversed.
CREATE TABLE IF NOT EXISTS relations (
  id TEXT PRIMARY KEY,
  key TEXT,
  from_holder_id TEXT,
  to_holder_id TEXT,
  node TEXT,
  relation_type TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('physical','contractual','accounting','attentional','analogical','attribute')),
  transmits INTEGER NOT NULL,
  hop_discount REAL,
  basis TEXT NOT NULL,
  source TEXT,
  knowable_from TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS relations_from ON relations(from_holder_id);

-- ---- v15 §A4: composition through a relation is a mapping, not a sign flip -----------------------------------
-- Most entries are "does not transmit". An absent entry is zero: a transform must be stated to exist.
CREATE TABLE IF NOT EXISTS transforms (
  id TEXT PRIMARY KEY,
  key TEXT,
  relation_type TEXT NOT NULL,
  from_kind TEXT NOT NULL,
  to_kind TEXT NOT NULL,
  weight REAL NOT NULL,
  basis TEXT NOT NULL,
  proposed_by TEXT,
  created_at TEXT NOT NULL
);

-- ---- v15 §I1: node kinds. An attribute node is a shared loading, never a transmission path -------------------
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  key TEXT,
  node TEXT NOT NULL,
  node_kind TEXT NOT NULL CHECK (node_kind IN ('event','attribute')),
  attribute_kind TEXT,
  basis TEXT,
  created_at TEXT NOT NULL
);

-- ---- v15 §B: the ACK graph -- knowability, not the world -----------------------------------------------------
-- We were storing this as fields on the effect (due_at, catalyst_class), which is why walks could not happen:
-- a field cannot branch. Scheduled ACKs are calendared. Forced ACKs are obligations whose timing is not public,
-- and they are the only place a walk can find something a calendar-driven market has not.
CREATE TABLE IF NOT EXISTS ack_nodes (
  id TEXT PRIMARY KEY,
  key TEXT,
  node TEXT NOT NULL,
  holder_id TEXT,
  ack_kind TEXT NOT NULL CHECK (ack_kind IN ('scheduled','forced')),
  fact TEXT NOT NULL,
  source TEXT NOT NULL,
  form TEXT,
  due_at TEXT,
  obligation TEXT,
  parent_ack_id TEXT,
  round_id TEXT,
  participant_class TEXT,
  attention INTEGER NOT NULL DEFAULT 0,
  standing INTEGER NOT NULL DEFAULT 0,
  basis TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ack_nodes_node ON ack_nodes(node);

-- §B5: a fired ACK must deliver a fact. "The date passed and nothing was said" is an absence fact: it prunes, it
-- does not advance. Without this, "advance the walk" becomes "keep the round alive".
CREATE TABLE IF NOT EXISTS ack_firings (
  id TEXT PRIMARY KEY,
  ack_id TEXT NOT NULL REFERENCES ack_nodes(id),
  round_id TEXT,
  fired_at TEXT NOT NULL,
  delivered INTEGER NOT NULL,
  delivered_fact TEXT,
  implied TEXT,
  gap TEXT,
  evidence_ids TEXT,
  opens_effect_ids TEXT,
  kills_effect_ids TEXT,
  successor_ack_ids TEXT,
  successor_query TEXT,
  segment_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- ---- v15 §C5: segment locking. Nothing is rewritten; the set grows a generation ------------------------------
CREATE TABLE IF NOT EXISTS segments (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  idx INTEGER NOT NULL,
  parent_segment_id TEXT,
  opened_by_ack_id TEXT,
  opened_by_firing_id TEXT,
  claim TEXT NOT NULL,
  effect_ids TEXT NOT NULL,
  next_ack_ids TEXT,
  locked_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- ---- v15 §D: contradictions are edge hypotheses --------------------------------------------------------------
-- Two effect paths contradict when they point at the same ACK node and imply opposite deliveries. The node
-- delivers what it delivers; what disagree are the paths, so the hypothesis is about an EDGE.
CREATE TABLE IF NOT EXISTS contradictions (
  id TEXT PRIMARY KEY,
  round_id TEXT,
  ack_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('internal','external','opposed_on_holder')),
  path_a TEXT NOT NULL,
  path_b TEXT NOT NULL,
  implies_a TEXT NOT NULL,
  implies_b TEXT NOT NULL,
  common_set TEXT,
  gap TEXT,
  dated_at TEXT,
  edge_hypotheses TEXT,
  exit_ack_id TEXT,
  resolved_by_firing_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- ---- v15 §H: a basket carries exposures nobody wrote down ----------------------------------------------------
-- Naming it at lock makes it a claim we can be wrong about rather than a surprise in the P&L. It is a floor and is
-- typed as one: the graph sees only modelled loadings, so the gap is honest ignorance rather than hidden risk.
CREATE TABLE IF NOT EXISTS synthetic_exposures (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  basket_key TEXT,
  declared TEXT NOT NULL,
  coverage REAL,
  attribute_coverage REAL,
  floor INTEGER NOT NULL DEFAULT 1,
  intended_residual REAL,
  declared_exposure REAL,
  basket_stake REAL,
  basis TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  event_text TEXT NOT NULL,
  event_date TEXT NOT NULL,
  source TEXT NOT NULL,
  selection_rule TEXT NOT NULL,
  rejected_before INTEGER NOT NULL,
  criteria_json TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  node_recent_incidents TEXT,
  node TEXT,
  event_kind TEXT,
  node_kind TEXT,
  rejections TEXT,
  size_band TEXT,
  candidate_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id),
  operator TEXT NOT NULL,
  operator_cutoff TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('created','locked','open','partially_scored','scored','void')),
  state_changed_at TEXT NOT NULL,
  round_class TEXT CHECK (round_class IN ('learning','clean') OR round_class IS NULL),
  contamination TEXT CHECK (contamination IN ('none','q2_fail','q2_unknown','peeked') OR contamination IS NULL),
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS round_transitions (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  from_state TEXT,
  to_state TEXT NOT NULL CHECK (to_state IN ('created','locked','open','partially_scored','scored','void')),
  reason TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS round_state AS
  SELECT r.id AS round_id,
         COALESCE(t.to_state, r.state) AS state,
         COALESCE(t.recorded_at, r.state_changed_at) AS state_changed_at
  FROM rounds r
  LEFT JOIN round_transitions t ON t.rowid = (
    SELECT rowid FROM round_transitions WHERE round_id = r.id ORDER BY rowid DESC LIMIT 1
  );

-- A1: contamination is a status. Latest row per round is truth; rounds.round_class is the initial value.
CREATE TABLE IF NOT EXISTS round_classifications (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  round_class TEXT NOT NULL CHECK (round_class IN ('learning','clean')),
  contamination TEXT NOT NULL CHECK (contamination IN ('none','q2_fail','q2_unknown','peeked')),
  reason TEXT,
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS round_classification AS
  SELECT r.id AS round_id,
         COALESCE(c.round_class, r.round_class, 'learning') AS round_class,
         COALESCE(c.contamination, r.contamination, 'q2_unknown') AS contamination,
         c.reason AS reason
  FROM rounds r
  LEFT JOIN round_classifications c ON c.rowid = (
    SELECT rowid FROM round_classifications WHERE round_id = r.id ORDER BY rowid DESC LIMIT 1
  );

-- A9: criteria corrections are new rows; events.criteria_json keeps the intake value.
CREATE TABLE IF NOT EXISTS event_criteria (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id),
  criteria_json TEXT NOT NULL,
  reason TEXT NOT NULL,
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- free-text notes on a round (e.g. a tide/contamination note); append-only
CREATE TABLE IF NOT EXISTS round_notes (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  kind TEXT NOT NULL,
  note TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- B5: what the operator's own store surfaced at reveal (pre-lock legal by definition; logged so "I didn't hold it" is checkable)
CREATE TABLE IF NOT EXISTS reveal_context (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  node TEXT,
  event_kind TEXT,
  context_json TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- B3: the touched set as a template: one row per holder x degree, same columns at every degree
CREATE TABLE IF NOT EXISTS touched_set (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  holder_id TEXT NOT NULL REFERENCES holders(id),
  degree INTEGER NOT NULL CHECK (degree BETWEEN 0 AND 3),
  node TEXT NOT NULL,
  position_summary TEXT NOT NULL,
  substitutability TEXT NOT NULL CHECK (substitutability IN ('low','med','high','unknown')),
  duration_factor TEXT,
  carrier TEXT,
  mechanism_ids TEXT,
  leg_source TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  call_type TEXT NOT NULL CHECK (call_type IN ('sign','magnitude_order','lag_band','predicate','null','meta','map','narrative')),
  target TEXT NOT NULL,
  claim TEXT NOT NULL,
  hypothesis_id TEXT,
  sign TEXT CHECK (sign IN ('+','-','0') OR sign IS NULL),
  magnitude_rank INTEGER,
  lag_band TEXT CHECK (lag_band IN ('days','weeks','months','never') OR lag_band IS NULL),
  carrier TEXT,
  falsifier TEXT,
  falsifier_window TEXT,
  mechanism_ids TEXT NOT NULL,
  baseline_claim TEXT NOT NULL,
  confidence_band TEXT,
  locked_at TEXT NOT NULL,
  aggregation TEXT CHECK (aggregation IN ('max','min','all') OR aggregation IS NULL),
  branches TEXT,
  conditional_on TEXT,
  narrative_sign TEXT CHECK (narrative_sign IN ('+','-','0') OR narrative_sign IS NULL),
  position_id TEXT,
  carrier_status TEXT,
  due_at TEXT,
  implied_method TEXT,
  implied_value REAL,
  implied_source TEXT,
  implied_as_of TEXT,
  implied_basis TEXT,
  base_rate_id TEXT,
  settling_document TEXT,
  settling_document_fetched INTEGER,
  effect_kind TEXT,
  window TEXT,
  space TEXT,
  covering_rule_id TEXT,
  grid_cell_id TEXT,
  effect_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- B1: decomposition of a duration or extent claim; the composite is derived, never scored directly
CREATE TABLE IF NOT EXISTS prediction_factors (
  id TEXT PRIMARY KEY,
  prediction_id TEXT NOT NULL REFERENCES predictions(id),
  idx INTEGER NOT NULL,
  factor TEXT NOT NULL,
  holder_id TEXT,
  node TEXT,
  estimate TEXT NOT NULL,
  carrier TEXT NOT NULL,
  falsifier TEXT NOT NULL,
  binding INTEGER NOT NULL,
  against INTEGER NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS factor_resolutions (
  id TEXT PRIMARY KEY,
  factor_id TEXT NOT NULL REFERENCES prediction_factors(id),
  prediction_id TEXT NOT NULL REFERENCES predictions(id),
  outcome TEXT NOT NULL CHECK (outcome IN ('hit','miss','unverified','untestable')),
  observed TEXT,
  evidence_ids TEXT NOT NULL,
  note TEXT,
  scorer TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  source_time TEXT,
  knowable_from TEXT,
  excerpt TEXT NOT NULL CHECK (length(excerpt) <= 500),
  note TEXT,
  carrier TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resolutions (
  id TEXT PRIMARY KEY,
  prediction_id TEXT NOT NULL REFERENCES predictions(id),
  outcome TEXT NOT NULL CHECK (outcome IN ('hit','miss','unverified','untestable')),
  mechanism_outcome TEXT NOT NULL CHECK (mechanism_outcome IN ('right','wrong','unknown')),
  quarantined INTEGER NOT NULL,
  baseline_outcome TEXT NOT NULL CHECK (baseline_outcome IN ('hit','miss','unverified')),
  evidence_ids TEXT NOT NULL,
  scorer_note TEXT NOT NULL,
  weight REAL NOT NULL,
  null_call_weight REAL NOT NULL,
  supersedes TEXT,
  source_coverage TEXT CHECK (source_coverage IN ('adequate','thin','english_only','none') OR source_coverage IS NULL),
  scorer TEXT CHECK (scorer IN ('self','second','human') OR scorer IS NULL),
  evidence_class TEXT CHECK (evidence_class IN ('stated_dated','inferred','none') OR evidence_class IS NULL),
  quality REAL,
  late_falsifier INTEGER,
  branch_arose TEXT,
  expired INTEGER,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- B2: the second scorer's resolutions live apart from the operator's; disputes are computed, the human breaks ties
CREATE TABLE IF NOT EXISTS second_scores (
  id TEXT PRIMARY KEY,
  prediction_id TEXT NOT NULL REFERENCES predictions(id),
  outcome TEXT NOT NULL CHECK (outcome IN ('hit','miss','unverified','untestable')),
  mechanism_outcome TEXT NOT NULL CHECK (mechanism_outcome IN ('right','wrong','unknown')),
  baseline_outcome TEXT NOT NULL CHECK (baseline_outcome IN ('hit','miss','unverified')),
  evidence_ids TEXT NOT NULL,
  scorer_note TEXT NOT NULL,
  source_coverage TEXT,
  scorer_session TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scorecards (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  scorecard_json TEXT NOT NULL,
  null_call_weight REAL NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS library_rules (
  id TEXT PRIMARY KEY,
  rule_text TEXT NOT NULL,
  forbids TEXT NOT NULL,
  obscurity INTEGER NOT NULL CHECK (obscurity BETWEEN 1 AND 5),
  layer TEXT NOT NULL CHECK (layer IN ('sequence','transmission','ownership','operator','other')),
  status TEXT NOT NULL CHECK (status IN ('candidate','validated','retired')),
  composed_of TEXT NOT NULL,
  provenance TEXT NOT NULL,
  proposed_in_round TEXT,
  hits INTEGER NOT NULL DEFAULT 0,
  misses INTEGER NOT NULL DEFAULT 0,
  false_alarms INTEGER NOT NULL DEFAULT 0,
  trials INTEGER NOT NULL DEFAULT 0,
  review_flag INTEGER NOT NULL DEFAULT 0,
  weight REAL NOT NULL DEFAULT 0,
  clean_hit_rounds INTEGER NOT NULL DEFAULT 0,
  key TEXT,
  created_at TEXT NOT NULL,
  superseded_by TEXT,
  retired_reason TEXT,
  carries TEXT,
  citations_excluded INTEGER NOT NULL DEFAULT 0
);

-- B0: point-in-time fetches (Wayback, Wikipedia revisions); every one logged with the operator's reason
CREATE TABLE IF NOT EXISTS pit_fetches (
  id TEXT PRIMARY KEY,
  round_id TEXT,
  source TEXT NOT NULL CHECK (source IN ('wayback','wikipedia','auto','live')),
  target TEXT NOT NULL,
  as_of TEXT NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL,
  snapshot_url TEXT,
  snapshot_date TEXT,
  chars INTEGER,
  path_served TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v8 D1: carriers registry (coverage is a property of carriers)
CREATE TABLE IF NOT EXISTS carriers (
  id TEXT PRIMARY KEY,
  key TEXT,
  name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('price_assessment','notice_feed','filing','newspaper','index','transcript')),
  access TEXT NOT NULL CHECK (access IN ('open','paywalled','blocked','unknown')),
  note TEXT,
  last_checked TEXT,
  node_kinds TEXT,
  fetch_paths TEXT,
  url TEXT,
  participant_class TEXT,
  created_at TEXT NOT NULL
);

-- v9 D2: pages the save-page-now scheduler snapshots (IR events pages, notice pages, live-blocked carriers)
CREATE TABLE IF NOT EXISTS snapshot_targets (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('ir_events','notices','carrier','other')),
  node TEXT NOT NULL,
  holder_id TEXT,
  carrier_key TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  last_snapshot TEXT,
  last_status TEXT,
  created_at TEXT NOT NULL
);

-- v9 B5: the selector's standing (Q9 streak, suspension); one row per selector key
CREATE TABLE IF NOT EXISTS selector (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  consecutive_q9_fails INTEGER NOT NULL DEFAULT 0,
  suspended INTEGER NOT NULL DEFAULT 0,
  suspended_at TEXT,
  cleared_at TEXT,
  cleared_reason TEXT,
  created_at TEXT NOT NULL
);

-- v8 E2: pre-registered synthetic construction rules
CREATE TABLE IF NOT EXISTS synthetic_rules (
  id TEXT PRIMARY KEY,
  key TEXT,
  text TEXT NOT NULL,
  shape TEXT NOT NULL CHECK (shape IN ('tradability','time','tide','convexity')),
  created_at TEXT NOT NULL
);

-- v8 E1: synthetic legs, a projection of position legs under one construction rule (signs only)
CREATE TABLE IF NOT EXISTS synthetic_legs (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  target_node TEXT NOT NULL,
  components TEXT NOT NULL,
  construction_rule_id TEXT NOT NULL REFERENCES synthetic_rules(id),
  support_weight REAL,
  shape TEXT NOT NULL,
  listed_components INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  cross_node INTEGER,
  space TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predicates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('arming','disarming','exit','catalyst')),
  source TEXT NOT NULL,
  threshold TEXT NOT NULL,
  date TEXT,
  role_note TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  key TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predicate_checks (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  predicate_id TEXT NOT NULL REFERENCES predicates(id),
  claimed TEXT NOT NULL CHECK (claimed IN ('holds','fails','unknown')),
  observed TEXT CHECK (observed IN ('holds','fails','unknown') OR observed IS NULL),
  note TEXT,
  scope TEXT CHECK (scope IN ('event','node') OR scope IS NULL),
  basis TEXT,
  position_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS t0_candidates (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  window_label TEXT NOT NULL,
  criteria_pass INTEGER NOT NULL,
  arming_pass_single INTEGER,
  arming_pass_pair INTEGER,
  listed_party TEXT,
  pair_holders TEXT,
  carrier TEXT,
  micro_macro_note TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holders (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  normalised_name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('company','plant','facility','authority','fund','other')),
  parent_id TEXT REFERENCES holders(id),
  listed INTEGER NOT NULL DEFAULT 0,
  ticker TEXT,
  exchange TEXT,
  first_seen_round TEXT,
  key TEXT,
  ir_url TEXT,
  cik TEXT,
  ir_press_url TEXT,
  options_listed INTEGER,
  price_symbol TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS holders_norm ON holders(normalised_name);

CREATE TABLE IF NOT EXISTS aliases (
  id TEXT PRIMARY KEY,
  holder_id TEXT NOT NULL REFERENCES holders(id),
  alias TEXT NOT NULL,
  alias_norm TEXT NOT NULL,
  alias_kind TEXT NOT NULL CHECK (alias_kind IN ('name','former_name','subsidiary','plant_name','ticker','abbreviation')),
  source TEXT NOT NULL,
  knowable_from TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS aliases_norm ON aliases(alias_norm);

CREATE TABLE IF NOT EXISTS orphans (
  id TEXT PRIMARY KEY,
  raw_string TEXT NOT NULL,
  raw_norm TEXT NOT NULL,
  context TEXT,
  round_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY,
  holder_id TEXT NOT NULL REFERENCES holders(id),
  node TEXT NOT NULL,
  attribute TEXT NOT NULL CHECK (attribute IN ('tier','priority','substitutability','share','duration','sign_of_exposure')),
  value TEXT NOT NULL,
  unit TEXT,
  source TEXT NOT NULL,
  source_time TEXT,
  knowable_from TEXT,
  confidence TEXT NOT NULL CHECK (confidence IN ('stated','inferred','implicit')),
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS positions_node ON positions(node);

CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  node TEXT,
  holder_ids TEXT NOT NULL,
  position_ids TEXT,
  mechanism_ids TEXT NOT NULL,
  arming_predicate_ids TEXT NOT NULL,
  disarming_predicate_ids TEXT NOT NULL,
  falsifier TEXT NOT NULL,
  granularity TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','armed','fired','falsified','expired','resolved')),
  status_changed_at TEXT NOT NULL,
  opened_in_round TEXT,
  resolved_in_round TEXT,
  support_weight REAL,
  next_check_at TEXT,
  hard_stop_at TEXT,
  check_cadence_days INTEGER,
  arming_note TEXT,
  spawned_from_prediction_id TEXT,
  spawned_from_factor_index INTEGER,
  created_at TEXT NOT NULL,
  superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS hypothesis_checks (
  id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
  predicate_id TEXT NOT NULL REFERENCES predicates(id),
  observed TEXT NOT NULL CHECK (observed IN ('holds','fails','unknown')),
  evidence_ids TEXT NOT NULL,
  note TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- B4: node facts that do not depend on any round. The only asset that cannot be backfilled.
CREATE TABLE IF NOT EXISTS node_facts (
  id TEXT PRIMARY KEY,
  node TEXT NOT NULL,
  holder_id TEXT,
  fact_type TEXT NOT NULL CHECK (fact_type IN ('force_majeure','allocation','port_notice','premium_assessment','enforcement','outage','restart','dependency','scheduled','snapshot','incident','closure','strike','mechanical','other')),
  text TEXT NOT NULL,
  url TEXT,
  source TEXT NOT NULL,
  source_time TEXT,
  knowable_from TEXT,
  supersedes TEXT,
  sched_kind TEXT,
  hindsight INTEGER,
  sched_source TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS node_facts_node ON node_facts(node);
CREATE INDEX IF NOT EXISTS node_facts_url ON node_facts(url);

-- B4: named things the ingest is looking for
CREATE TABLE IF NOT EXISTS ingest_targets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  node TEXT,
  question TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','found','expired')),
  found_fact_id TEXT,
  opened_in_round TEXT,
  created_at TEXT NOT NULL
);

-- v9 B3: round tags, immutable at intake; a re-tag is a new row with supersedes
CREATE TABLE IF NOT EXISTS round_tags (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  tag TEXT NOT NULL CHECK (tag IN ('lag_test','weather','late_headline','learning')),
  q1a TEXT NOT NULL,
  q1a_basis TEXT,
  q1b TEXT NOT NULL,
  q1b_detail TEXT,
  q2 TEXT NOT NULL,
  cap_override TEXT,
  reason TEXT,
  supersedes TEXT,
  size_band TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v9 B5: every event the selector skipped, with the question it failed (or 'cap')
CREATE TABLE IF NOT EXISTS event_rejections (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  start_date TEXT,
  event_date TEXT NOT NULL,
  event_text TEXT NOT NULL,
  failing_q TEXT NOT NULL,
  note TEXT,
  round_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v9 B5: the selector writes its source and start date before enumerating
CREATE TABLE IF NOT EXISTS selection_windows (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  start_date TEXT NOT NULL,
  note TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v9 F: per-round rows for the open notebook claims (E4 synthetics, F3 divergence), written from the basket view
CREATE TABLE IF NOT EXISTS notebook_rows (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  claim TEXT NOT NULL,
  row_json TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v10 E2: does a scheduled or mechanical fact concern the leg's node? Set at lock with basis; otherwise a tide candidate.
CREATE TABLE IF NOT EXISTS scheduled_links (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  fact_id TEXT NOT NULL REFERENCES node_facts(id),
  concerns_node INTEGER NOT NULL,
  basis TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v10 C2/C3: enumeration candidates, one row per dated feed item, and the human's decision on each
CREATE TABLE IF NOT EXISTS enumeration_candidates (
  id TEXT PRIMARY KEY,
  feed_set TEXT NOT NULL,
  window_from TEXT NOT NULL,
  window_to TEXT NOT NULL,
  feed_key TEXT NOT NULL,
  event_date TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  prompt TEXT NOT NULL,
  node_guess TEXT,
  node_kind_guess TEXT,
  q1a_basis TEXT,
  q1b TEXT,
  q2 TEXT,
  q7 TEXT,
  size_hint TEXT,
  materiality_hint REAL,
  materiality_basis TEXT,
  decision TEXT,
  decision_reason TEXT,
  round_id TEXT,
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v10 I1: price consulted only as an outcome timestamp, after a call's due date
CREATE TABLE IF NOT EXISTS price_observations (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  carrier TEXT NOT NULL,
  date TEXT NOT NULL,
  value REAL NOT NULL,
  band_low REAL,
  band_high REAL,
  band_method TEXT,
  attributed INTEGER NOT NULL,
  attribution_evidence_id TEXT,
  note TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v10 K1: the effect grid assigned at lock and frozen; every cell is a candidate leg in one space
CREATE TABLE IF NOT EXISTS grid_cells (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  holder_id TEXT NOT NULL,
  node TEXT NOT NULL,
  degree INTEGER,
  factor_kind TEXT NOT NULL,
  effect_kind TEXT NOT NULL,
  window TEXT NOT NULL,
  space TEXT NOT NULL CHECK (space IN ('positive','mirror')),
  covering_rule_id TEXT,
  prediction_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v10 K3: a new risk rule covering an open mirror cell is recorded, never rewritten
CREATE TABLE IF NOT EXISTS coverage_migrations (
  id TEXT PRIMARY KEY,
  grid_cell_id TEXT NOT NULL REFERENCES grid_cells(id),
  round_id TEXT NOT NULL,
  risk_rule_id TEXT NOT NULL,
  covered_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v11 B1: measurement applied to already-locked legs. Never touches resolutions; excluded from weights and calibration.
CREATE TABLE IF NOT EXISTS replay_measurements (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT,
  holder_id TEXT,
  node TEXT,
  leg_source TEXT,
  effect_kind TEXT NOT NULL,
  window TEXT NOT NULL,
  space TEXT NOT NULL CHECK (space IN ('positive','mirror')),
  covering_rule_id TEXT,
  reencode_date TEXT,
  latency_days INTEGER,
  residual_state TEXT,
  observations INTEGER NOT NULL DEFAULT 0,
  measurable INTEGER NOT NULL DEFAULT 1,
  note TEXT,
  as_of TEXT NOT NULL,
  replay INTEGER NOT NULL DEFAULT 1,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v12 E2: per-leg participant classes, set at lock. Which class demonstrably holds the fact, which class marks the
-- security, and whether a routine channel connects them.
CREATE TABLE IF NOT EXISTS leg_annotations (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  fact_holder_class TEXT NOT NULL,
  price_setter_class TEXT NOT NULL,
  channel_between TEXT,
  fact_carrier TEXT,
  basis TEXT NOT NULL,
  supersedes TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v12 0.4: retrieval is permitted only inside a scoring session, and every fetch is stamped against a due call.
-- v13 A4: one row per leg per round: does any risk survive this leg, which eliminators were run, which fired.
CREATE TABLE IF NOT EXISTS surviving_risk (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  holder_id TEXT,
  node TEXT,
  eliminators_fired TEXT NOT NULL,
  eliminators_checked TEXT NOT NULL,
  eliminators_unevaluable TEXT,
  survives INTEGER NOT NULL,
  magnitude REAL,
  magnitude_basis TEXT,
  basis TEXT NOT NULL,
  as_of TEXT NOT NULL,
  replay INTEGER NOT NULL DEFAULT 0,
  supersedes TEXT,
  effect_id TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v13 A1: the effect kinds survive as a template over legs that already exist, not as a source of them. Every leg
-- carries a direction claim and a vol/volume/timing claim, or a stated reason for having none.
CREATE TABLE IF NOT EXISTS leg_claims (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  position_id TEXT NOT NULL,
  holder_id TEXT,
  node TEXT,
  effect_kind TEXT,
  prediction_id TEXT,
  no_claim_reason TEXT,
  impact_pct REAL,
  impact_basis TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v14 A6c: the callable surface is wide, so the discipline moves off which tools may be called and onto what gets
-- written and when. A leg reached by seven deliberate hops is more auditable than one that appears unexplained.
CREATE TABLE IF NOT EXISTS move_log (
  id TEXT PRIMARY KEY,
  round_id TEXT,
  move TEXT NOT NULL,
  target TEXT,
  reason TEXT NOT NULL,
  result TEXT,
  cost TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scoring_sessions (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL REFERENCES rounds(id),
  call_ids TEXT NOT NULL,
  opened_at TEXT NOT NULL,
  closed_at TEXT,
  note TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v12 0.4: a fetch that no open scoring session can account for. Visible at the time, not in the recap.
CREATE TABLE IF NOT EXISTS firewall_violations (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  round_id TEXT,
  tool TEXT NOT NULL,
  detail TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- v12 F1: institutional frequencies, so an occurrence call knows the base rate it is departing from.
CREATE TABLE IF NOT EXISTS base_rates (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  class TEXT NOT NULL,
  condition TEXT NOT NULL,
  n INTEGER,
  k INTEGER,
  rate REAL,
  source TEXT NOT NULL,
  knowable_from TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

-- v10 C1: the selector's universe
CREATE TABLE IF NOT EXISTS feeds (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  url_pattern TEXT NOT NULL,
  kind TEXT NOT NULL,
  parser TEXT NOT NULL,
  feed_set TEXT NOT NULL,
  stratum TEXT,
  node_kind TEXT,
  outlet_class TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  confirmed INTEGER NOT NULL DEFAULT 0,
  last_pulled TEXT,
  last_status TEXT,
  created_at TEXT NOT NULL
);

-- v10 I6: rules the risk engine uses to veto, date or classify a leg
CREATE TABLE IF NOT EXISTS risk_rules (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  text TEXT NOT NULL,
  kind TEXT NOT NULL,
  covers TEXT NOT NULL,
  knowable_from TEXT NOT NULL,
  origin TEXT,
  library_rule_id TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

-- v10: programme settings the human sets once (freeze start, mix targets)
CREATE TABLE IF NOT EXISTS settings (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  value TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

-- A2: human-populated. The operator never writes its own cutoff.
CREATE TABLE IF NOT EXISTS model_cutoffs (
  id TEXT PRIMARY KEY,
  model_id TEXT NOT NULL UNIQUE,
  cutoff_date TEXT NOT NULL,
  source TEXT,
  created_at TEXT NOT NULL
);

-- A8: every retrieval denial by the hook.
CREATE TABLE IF NOT EXISTS hook_denials (
  id TEXT PRIMARY KEY,
  round_id TEXT,
  tool TEXT NOT NULL,
  reason TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);

-- A12: every narrowing decision (validation, arming) with the weight it read.
CREATE TABLE IF NOT EXISTS narrowing_log (
  id TEXT PRIMARY KEY,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  weight_read REAL,
  threshold REAL,
  detail TEXT,
  recorded_at TEXT NOT NULL,
  prev_row_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
"""

# Additive migrations for databases created before these columns existed (idempotent).
MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("events", "node_recent_incidents", "TEXT"),
    ("rounds", "round_class", "TEXT"),
    ("rounds", "contamination", "TEXT"),
    ("predictions", "falsifier_window", "TEXT"),
    ("resolutions", "source_coverage", "TEXT"),
    ("resolutions", "scorer", "TEXT"),
    ("resolutions", "evidence_class", "TEXT"),
    ("resolutions", "quality", "REAL"),
    ("resolutions", "late_falsifier", "INTEGER"),
    ("predicate_checks", "scope", "TEXT"),
    ("predicate_checks", "basis", "TEXT"),
    ("predicate_checks", "position_id", "TEXT"),
    ("events", "node", "TEXT"),
    ("events", "event_kind", "TEXT"),
    ("predictions", "aggregation", "TEXT"),
    ("hypotheses", "spawned_from_prediction_id", "TEXT"),
    ("hypotheses", "spawned_from_factor_index", "INTEGER"),
    ("library_rules", "weight", "REAL NOT NULL DEFAULT 0"),
    ("library_rules", "clean_hit_rounds", "INTEGER NOT NULL DEFAULT 0"),
    ("library_rules", "key", "TEXT"),
    ("predicates", "key", "TEXT"),
    ("holders", "key", "TEXT"),
    ("hypotheses", "support_weight", "REAL"),
    ("hypotheses", "next_check_at", "TEXT"),
    ("hypotheses", "hard_stop_at", "TEXT"),
    ("hypotheses", "check_cadence_days", "INTEGER"),
    ("hypotheses", "arming_note", "TEXT"),
    ("library_rules", "carries", "TEXT"),
    ("predictions", "branches", "TEXT"),
    ("predictions", "conditional_on", "TEXT"),
    ("predictions", "narrative_sign", "TEXT"),
    ("predictions", "position_id", "TEXT"),
    ("predictions", "carrier_status", "TEXT"),
    ("resolutions", "branch_arose", "TEXT"),
    ("carriers", "node_kinds", "TEXT"),
    ("library_rules", "citations_excluded", "INTEGER NOT NULL DEFAULT 0"),
    ("events", "node_kind", "TEXT"),
    ("events", "rejections", "TEXT"),
    ("touched_set", "mechanism_ids", "TEXT"),
    ("pit_fetches", "path_served", "TEXT"),
    ("carriers", "fetch_paths", "TEXT"),
    ("carriers", "url", "TEXT"),
    ("holders", "ir_url", "TEXT"),
    ("holders", "cik", "TEXT"),
    ("node_facts", "supersedes", "TEXT"),
    ("node_facts", "sched_kind", "TEXT"),
    ("events", "size_band", "TEXT"),
    ("events", "candidate_id", "TEXT"),
    ("round_tags", "size_band", "TEXT"),
    ("predictions", "due_at", "TEXT"),
    ("predictions", "effect_kind", "TEXT"),
    ("predictions", "window", "TEXT"),
    ("predictions", "space", "TEXT"),
    ("predictions", "covering_rule_id", "TEXT"),
    ("predictions", "grid_cell_id", "TEXT"),
    ("resolutions", "expired", "INTEGER"),
    ("node_facts", "hindsight", "INTEGER"),
    ("node_facts", "sched_source", "TEXT"),
    ("synthetic_legs", "cross_node", "INTEGER"),
    ("synthetic_legs", "space", "TEXT"),
    ("holders", "ir_press_url", "TEXT"),
    ("holders", "options_listed", "INTEGER"),
    ("touched_set", "leg_source", "TEXT"),
    ("feeds", "stratum", "TEXT"),
    ("predictions", "implied_method", "TEXT"),
    ("predictions", "implied_value", "REAL"),
    ("predictions", "implied_source", "TEXT"),
    ("predictions", "implied_as_of", "TEXT"),
    ("predictions", "implied_basis", "TEXT"),
    ("predictions", "base_rate_id", "TEXT"),
    ("carriers", "participant_class", "TEXT"),
    ("risk_rules", "origin", "TEXT"),
    ("holders", "price_symbol", "TEXT"),
    ("evidence", "carrier", "TEXT"),
    ("risk_rules", "precondition", "TEXT"),
    ("leg_claims", "impact_pct", "REAL"),
    ("surviving_risk", "origin", "TEXT"),
    ("surviving_risk", "proposed_by", "TEXT"),
    ("surviving_risk", "vector", "TEXT"),
    ("surviving_risk", "binding_term", "TEXT"),
    ("surviving_risk", "confidence", "REAL"),
    ("surviving_risk", "path_basis", "TEXT"),
    ("predictions", "settling_document", "TEXT"),
    ("predictions", "settling_document_fetched", "INTEGER"),
    ("leg_claims", "impact_basis", "TEXT"),
    ("price_observations", "band_reliable", "INTEGER"),
    ("price_observations", "turnover_usd", "REAL"),
    ("feeds", "reach_days", "INTEGER"),
    ("feeds", "reach_measured_at", "TEXT"),
    ("enumeration_candidates", "materiality_hint", "REAL"),
    ("enumeration_candidates", "materiality_basis", "TEXT"),
    # v15 §A2: the effect is the unit. position_id stays for history and is never removed.
    ("predictions", "effect_id", "TEXT"),
    ("surviving_risk", "effect_id", "TEXT"),
)

VIEWS_SQL = SCHEMA[SCHEMA.index("CREATE VIEW IF NOT EXISTS round_state"): SCHEMA.index("-- A1: contamination is a status")] +     SCHEMA[SCHEMA.index("CREATE VIEW IF NOT EXISTS round_classification"): SCHEMA.index("-- A9: criteria corrections")]

TRIGGER_TEMPLATE = """
CREATE TRIGGER IF NOT EXISTS no_update_{t} BEFORE UPDATE ON {t}
BEGIN SELECT RAISE(ABORT, '{t} is append-only: write a new row with supersedes set'); END;
CREATE TRIGGER IF NOT EXISTS no_delete_{t} BEFORE DELETE ON {t}
BEGIN SELECT RAISE(ABORT, '{t} is append-only: nothing is deleted; void or supersede instead'); END;
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    init_schema(conn)
    return conn


def _table_ddl(table: str) -> str:
    start = SCHEMA.index(f"CREATE TABLE IF NOT EXISTS {table} (")
    end = SCHEMA.index(");", start) + 2
    return SCHEMA[start:end]


def _rebuild_table(conn: sqlite3.Connection, table: str) -> None:
    """Recreate an existing table under the current DDL (SQLite cannot alter CHECK constraints). Rows are copied in
    rowid order so the hash chain is unchanged. Foreign keys are switched off for the copy; triggers are recreated."""
    if conn.in_transaction:
        raise HarnessError("table rebuild must run outside a transaction")
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(f"DROP TRIGGER IF EXISTS no_update_{table}")
        conn.execute(f"DROP TRIGGER IF EXISTS no_delete_{table}")
        ddl = _table_ddl(table).replace(f"CREATE TABLE IF NOT EXISTS {table} (", f"CREATE TABLE {table}__new (", 1)
        conn.execute(ddl)
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
        conn.execute(f"INSERT INTO {table}__new ({', '.join(cols)}) SELECT {', '.join(cols)} FROM {table} ORDER BY rowid")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}__new RENAME TO {table}")
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _needs_rebuild(conn: sqlite3.Connection, table: str, marker: str) -> bool:
    r = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return bool(r) and marker not in (r["sql"] or "")


def init_schema(conn: sqlite3.Connection) -> None:
    # views must be (re)created after column migrations; drop and recreate them each time
    conn.executescript("DROP VIEW IF EXISTS round_state; DROP VIEW IF EXISTS round_classification;")
    conn.executescript(SCHEMA)
    for table, col, decl in MIGRATIONS:
        if col not in [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    if _needs_rebuild(conn, "predictions", "'narrative'"):
        _rebuild_table(conn, "predictions")
    if _needs_rebuild(conn, "node_facts", "'snapshot'"):
        _rebuild_table(conn, "node_facts")
    if _needs_rebuild(conn, "pit_fetches", "'auto'"):
        _rebuild_table(conn, "pit_fetches")
    if _needs_rebuild(conn, "node_facts", "'mechanical'"):
        _rebuild_table(conn, "node_facts")
    if any(_needs_rebuild(conn, t, "'partially_scored'") for t in ("rounds", "round_transitions")):
        # the views read these tables; SQLite refuses the rename while they exist
        conn.executescript("DROP VIEW IF EXISTS round_state; DROP VIEW IF EXISTS round_classification;")
        for t in ("rounds", "round_transitions"):
            if _needs_rebuild(conn, t, "'partially_scored'"):
                _rebuild_table(conn, t)
        conn.executescript(VIEWS_SQL)
    for t in KEYED_TABLES:
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {t}_key ON {t}(key)")
    for t in LEDGER_TABLES:
        conn.executescript(TRIGGER_TEMPLATE.format(t=t))
    _COLUMN_CACHE.pop(id(conn), None)


@contextmanager
def transaction(conn: sqlite3.Connection):
    if conn.in_transaction:
        yield
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


_COLUMN_CACHE: dict[int, dict[str, list[tuple[str, str]]]] = {}


def columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    cache = _COLUMN_CACHE.setdefault(id(conn), {})
    if table not in cache:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not rows:
            raise HarnessError(f"unknown table {table!r}")
        cache[table] = [(r["name"], (r["type"] or "").upper()) for r in rows]
    return cache[table]


def _coerce(value, declared: str):
    if value is None:
        return None
    if isinstance(value, bool):
        value = int(value)
    if "INT" in declared:
        return int(value)
    if "REAL" in declared or "FLOA" in declared or "DOUB" in declared:
        return float(value)
    if "TEXT" in declared or "CHAR" in declared or "CLOB" in declared:
        return value if isinstance(value, str) else str(value)
    return value


def hash_row(prev_hash: str, row: dict) -> str:
    """Form v2: NULL-valued columns are dropped, so later nullable columns do not disturb old hashes."""
    return sha256_hex(prev_hash + canonical_json({k: v for k, v in row.items() if v is not None}))


def hash_row_v1(prev_hash: str, row: dict, table: str) -> str | None:
    cols = V1_COLUMNS.get(table)
    if not cols:
        return None
    return sha256_hex(prev_hash + canonical_json({c: row.get(c) for c in cols}))


def last_hash(conn: sqlite3.Connection, table: str) -> str:
    r = conn.execute(f"SELECT row_hash FROM {table} ORDER BY rowid DESC LIMIT 1").fetchone()
    return r["row_hash"] if r else GENESIS_HASH


def chain_heads(conn: sqlite3.Connection) -> dict[str, str]:
    return {t: last_hash(conn, t) for t in LEDGER_TABLES}


def append(conn: sqlite3.Connection, table: str, row: dict) -> dict:
    if table not in LEDGER_TABLES:
        raise HarnessError(f"{table} is not a ledger table; use insert_mutable")
    for forbidden in ("recorded_at", "prev_row_hash", "row_hash"):
        if forbidden in row:
            raise HarnessError(f"callers may not set {forbidden}; the harness stamps it")
    cols = columns(conn, table)
    names = [c for c, _ in cols]
    unknown = set(row) - set(names)
    if unknown:
        raise HarnessError(f"unknown columns for {table}: {sorted(unknown)}")
    full = {c: _coerce(row.get(c), t) for c, t in cols if c not in ("prev_row_hash", "row_hash")}
    if full.get("id") is None:
        full["id"] = uuid7()
    full["recorded_at"] = now_iso()
    with transaction(conn):
        prev = last_hash(conn, table)
        rh = hash_row(prev, full)
        stored = dict(full, prev_row_hash=prev, row_hash=rh)
        placeholders = ", ".join("?" for _ in stored)
        conn.execute(f"INSERT INTO {table} ({', '.join(stored)}) VALUES ({placeholders})", list(stored.values()))
    return stored


def insert_mutable(conn: sqlite3.Connection, table: str, row: dict) -> dict:
    if table not in MUTABLE_TABLES:
        raise HarnessError(f"{table} is a ledger table; use append")
    if "created_at" in row:
        raise HarnessError("callers may not set created_at; the harness stamps it")
    cols = columns(conn, table)
    unknown = set(row) - {c for c, _ in cols}
    if unknown:
        raise HarnessError(f"unknown columns for {table}: {sorted(unknown)}")
    full = {c: _coerce(row[c], t) for c, t in cols if c in row}
    if full.get("id") is None:
        full["id"] = uuid7()
    full["created_at"] = now_iso()
    names = {c for c, _ in cols}
    if "status_changed_at" in names and full.get("status_changed_at") is None:
        full["status_changed_at"] = full["created_at"]
    placeholders = ", ".join("?" for _ in full)
    conn.execute(f"INSERT INTO {table} ({', '.join(full)}) VALUES ({placeholders})", list(full.values()))
    return full


def verify_chain(conn: sqlite3.Connection, table: str | None = None) -> dict:
    tables = [table] if table else list(LEDGER_TABLES)
    result: dict = {"ok": True, "tables": {}, "first_break": None}
    for t in tables:
        if t not in LEDGER_TABLES:
            raise HarnessError(f"{t} is not a ledger table; ledgers are {', '.join(LEDGER_TABLES)}")
        prev = GENESIS_HASH
        n = legacy = 0
        broken = None
        for r in conn.execute(f"SELECT rowid AS _rowid, * FROM {t} ORDER BY rowid"):
            n += 1
            d = dict(r)
            rowid = d.pop("_rowid")
            stored_prev, stored_hash = d.pop("prev_row_hash"), d.pop("row_hash")
            if stored_prev != prev:
                broken = {"table": t, "rowid": rowid, "id": d.get("id"), "reason": "prev_row_hash mismatch (chain broken)"}
                break
            if stored_hash != hash_row(prev, d):
                if stored_hash == hash_row_v1(prev, d, t):
                    legacy += 1
                else:
                    broken = {"table": t, "rowid": rowid, "id": d.get("id"), "reason": "row_hash mismatch (row content tampered)"}
                    break
            prev = stored_hash
        if broken:
            result["ok"] = False
            result["tables"][t] = {"rows_checked": n, "ok": False, "break": broken}
            result["first_break"] = result["first_break"] or broken
        else:
            result["tables"][t] = {"rows_checked": n, "ok": True, "legacy_form_rows": legacy}
    return result


def get_row(conn: sqlite3.Connection, table: str, id_: str, what: str | None = None) -> dict:
    r = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id_,)).fetchone()
    if not r:
        raise NotFound(f"no {what or table.rstrip('s')} with id {id_!r}")
    return dict(r)
