"""MCP exposure (§6, tightened). Prefix nomad_. Every tool returns structured JSON plus a one-line `summary`."""
import sqlite3
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import (acks, basket, carriers, config, contradiction, edge, effects, enumeration, exposure, facts, generate,
               glossary, history, hypotheses, library, names, pit, positions, predicates, prices, replay, risk, rounds,
               scheduled, scorer, snapshots, surviving, synthetic, t0, vector, walk)
from .config import NULL_CALL_WEIGHT, db_path
from .db import connect, verify_chain
from .models import HypothesisCheckIn, PredicateCheckIn, PredictionIn, ResolutionIn, SecondScoreIn, TouchedSetIn

INSTRUCTIONS = """Nomad Harness: a firewalled, scored, append-only event-prediction instrument.
Round protocol (the firewall): nomad_submit_event (human) -> nomad_reveal_event (operator sees only event text + date)
-> nomad_lock_predictions (append-only, stamped) -> nomad_open_retrieval (ONLY now may you search the web)
-> nomad_add_evidence -> nomad_score_round -> nomad_export_round.
Retrieval before nomad_open_retrieval contaminates the round: void it with reason 'contaminated', peeked=true.
The operator model and its cutoff come from the environment and the model_cutoffs table; Q2 is computed, never claimed.
Rules in the library carry mechanisms, not names; nouns go in provenance.
NULL_CALL_WEIGHT, QUALITY_FACTORS and VALIDATION_THRESHOLD are pre-registered constants."""

mcp = FastMCP("nomad-harness", instructions=INSTRUCTIONS)

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WR = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
WR_IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)

_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = connect(db_path())
    return _conn


def set_connection(c: sqlite3.Connection) -> None:
    global _conn
    _conn = c


def _ok(data: dict, summary: str) -> dict:
    return {"summary": summary, **data}


# ---- rounds ---------------------------------------------------------------

@mcp.tool(name="nomad_event_window", annotations=RO)
def nomad_event_window() -> dict:
    """Clean event window for the current operator: [cutoff + 1 day, today - 28 days]. Events outside it are refused
    at intake unless round_class='learning' is passed explicitly."""
    r = rounds.event_window(conn())
    return _ok(r, f"operator {r['operator']}: clean window {r['window_start']} to {r['window_end']}" if r["known"]
               else f"operator {r['operator']} has no cutoff on file; rounds will be learning (q2_unknown)")


@mcp.tool(name="nomad_submit_event", annotations=WR)
def nomad_submit_event(event_text: str, event_date: str, source: str, selection_rule: str, rejected_before: int,
                       criteria_json: dict[str, str], node_recent_incidents: Optional[str] = None,
                       round_class: Optional[str] = None, node: Optional[str] = None, event_kind: Optional[str] = None,
                       node_kind: Optional[str] = None, rejections: Optional[list[str]] = None,
                       q1b_override: Optional[dict] = None, cap_override: Optional[str] = None,
                       selection_start_date: Optional[str] = None, window_events_seen: Optional[int] = None,
                       size_band: Optional[str] = None) -> dict:
    """Human intake. Creates the event (hash-before-reveal) and a round in state `created`.
    Q2 is computed from the operator's cutoff (any Q2 you pass is overwritten). The event must lie in the clean window
    unless round_class='learning'. node_recent_incidents: what the human knows about recent disruption at the node.
    node: the positions-store node the event sits on (B5: seeds the reveal context); event_kind: fire|leak|explosion|...
    (derived from the text when omitted). A criteria failure is admitted but logged as an intake note.
    node_kind (port|shipping|power|grid|refinery|petrochemical|chemical|agriculture|metals|mining|listed_company|regulator|other)
    runs the carrier-density check: no open carrier for the kind sets Q7 fail. rejections: the selector's rejected
    candidates, written straight into intake (Q9 stops being a note).
    v9: criteria carry Q1a ('pass|fail: <basis>', human); Q1b is computed from the ledger and open registries for `node`
    (q1b_override={value, basis} needs a basis); the round tag lag_test|weather|late_headline|learning is set here and is
    immutable; a weather/late_headline event is refused with reason 'cap' when the last three admitted rounds include one
    (cap_override='<reason>' admits it, logged); Q9 is computed from the selection window (selection_start_date after
    nomad_selection_window) and the rejections written for it (window_events_seen=1 declares a one-event window).
    Returns round_id and event_hash; deliberately does NOT echo event_text."""
    r = rounds.submit_event(conn(), event_text, event_date, source, selection_rule, rejected_before, criteria_json,
                            node_recent_incidents, round_class, node=node, event_kind=event_kind, node_kind=node_kind,
                            rejections=rejections, q1b_override=q1b_override, cap_override=cap_override,
                            selection_start_date=selection_start_date, window_events_seen=window_events_seen, size_band=size_band)
    return _ok(r, f"round {r['round_id']} created ({r['round_class']}, contamination {r['contamination']}, tag {r['tag']}, "
                  f"Q1b {r['q1b']['value']}, Q9 {r['q9']['text'].split(':')[0]}); next: nomad_reveal_event. "
                  "v10: hand-supplied events fail Q9; use nomad_enumerate / nomad_select_next / nomad_decide")


# ---- v10 §C enumeration ------------------------------------------------------------------------------------------

@mcp.tool(name="nomad_feeds", annotations=RO)
def nomad_feeds(feed_set: Optional[str] = None) -> dict:
    """v10 C1: the selector's universe (open, dated feeds), by set: trade_press | registries | gdelt | wires | all."""
    r = enumeration.list_feeds(conn(), feed_set)
    return _ok({"feeds": r}, f"{len(r)} feed(s)" + (f" in {feed_set}" if feed_set else ""))


@mcp.tool(name="nomad_feed_add", annotations=WR_IDEMPOTENT)
def nomad_feed_add(key: str, name: str, url_pattern: str, kind: str, parser: str, feed_set: str, node_kind: Optional[str] = None,
                   outlet_class: Optional[str] = None, confirmed: bool = False, stratum: Optional[str] = None) -> dict:
    """v10 C1: add or update a feed (kind rss|registry|gdelt|wire; parser rss|gdelt|tceq|none; outlet_class trade_press|local|wire|national|registry).
    The human confirms the set once (confirmed=true), not per round."""
    r = enumeration.feed_add(conn(), key, name, url_pattern, kind, parser, feed_set, node_kind, outlet_class, confirmed, stratum)
    return _ok(r, f"feed {key} {'added' if r['created'] else 'updated'}")


@mcp.tool(name="nomad_enumerate", annotations=WR)
def nomad_enumerate(feed_set: str, from_date: str, to_date: str) -> dict:
    """v10 C2: pull the feed set over [from, to] and write a dated, deduplicated candidate list: bare prompt, node and
    kind guess, computed Q1b/Q2/Q7, outlet-class size hint, and a Q1a basis from the same feeds over the prior 30 days."""
    r = enumeration.enumerate_window(conn(), feed_set, from_date, to_date)
    return _ok(r, f"{len(r['candidates'])} candidate(s) ({r['written']} new) over {r['items_pulled']} items from {len(r['feeds'])} feed(s)")


@mcp.tool(name="nomad_select_next", annotations=RO)
def nomad_select_next(feed_set: str, from_date: str, to_date: str, stratified: bool = True) -> dict:
    """v10 C3 / v11 D: the next undecided candidate, drawn in stratum order (largest shortfall against the quota first)
    and by date inside the stratum."""
    r = enumeration.select_next(conn(), feed_set, from_date, to_date, stratified)
    c = r["candidate"]
    return _ok(r, (f"candidate {c['id']} {c['event_date']}: {c['prompt'][:90]} (q1b {c['q1b'].split(':')[0]}, q2 {c['q2'].split(':')[0]}, "
                   f"q7 {c['q7'].split(':')[0]}, size hint {c['size_hint']}); {r['remaining']} remaining") if c else r["note"])


@mcp.tool(name="nomad_decide", annotations=WR)
def nomad_decide(candidate_id: str, decision: str, reason: Optional[str] = None, size_band: Optional[str] = None,
                 criteria: Optional[dict[str, str]] = None, node: Optional[str] = None, node_kind: Optional[str] = None,
                 event_kind: Optional[str] = None, prompt: Optional[str] = None, cap_override: Optional[str] = None,
                 q1b_override: Optional[dict] = None) -> dict:
    """v10 C3 / v11: the human's call on a candidate. reject(reason='Qn: why') writes the rejection; skip(reason) records
    a plain selection note without manufacturing a failing question; accept(size_band, criteria {Q3,Q4,Q6,Q8: 'pass: why'})
    submits the round through the enumeration path (Q9 pass), with the selection window recorded."""
    r = enumeration.decide(conn(), candidate_id, decision, reason, size_band, criteria, node, node_kind, event_kind, prompt,
                           cap_override=cap_override, q1b_override=q1b_override)
    return _ok(r, f"{decision}: " + (f"round {r['round']['round_id']} created (tag {r['round']['tag']})" if decision == "accept" else f"rejection {r.get('rejection_id')} ({r.get('failing_q')})"))


# ---- v10 §A live rounds --------------------------------------------------------------------------------------------

@mcp.tool(name="nomad_score_call", annotations=WR)
def nomad_score_call(round_id: str, resolution: ResolutionIn) -> dict:
    """v10 A3: score one call once its due_at has passed (or early=true with a reason). Narrative first (A4): a
    structural call on a leg is refused while the leg's narrative row is due and unscored. The round moves to
    partially_scored and to scored when nothing remains."""
    r = scorer.score_call(conn(), round_id, resolution)
    return _ok(r, f"round {round_id} {r['state']}: {len(r.get('remaining_calls', []))} call(s) remaining; outcome {r['outcome_score']} mechanism {r['mechanism_score']}")


@mcp.tool(name="nomad_open_scoring", annotations=WR)
def nomad_open_scoring(round_id: str, call_ids: list[str], note: Optional[str] = None) -> dict:
    """v12 0.4: open a scoring session. Retrieval on a partially scored round is permitted only inside one, and every
    fetch must be attributable to a call named here. Close it when the batch is scored."""
    r = scorer.open_scoring(conn(), round_id, call_ids, note)
    return _ok(r, f"scoring session {r['session_id']} open on round {round_id} for {len(r['calls'])} call(s)")


@mcp.tool(name="nomad_close_scoring", annotations=WR)
def nomad_close_scoring(session_id: Optional[str] = None) -> dict:
    """v12 0.4: close the open scoring session."""
    r = scorer.close_scoring(conn(), session_id)
    return _ok(r, f"closed {r['closed']}" if r["closed"] else r["note"])


@mcp.tool(name="nomad_firewall_violation", annotations=WR)
def nomad_firewall_violation(tool: str, detail: str, round_id: Optional[str] = None) -> dict:
    """v12 0.4: record a fetch that no open scoring session can account for. A breach is visible at the time, not in the recap."""
    r = scorer.firewall_violation(conn(), tool, detail, round_id)
    return _ok(r, f"firewall violation {r['violation_id']} recorded")


@mcp.tool(name="nomad_price_backfill", annotations=WR)
def nomad_price_backfill(round_id: str, write: bool = True) -> dict:
    """v12 0.1: fetch real daily closes for every listed leg of a round, compute the pre-registered 20-session band and
    write one observation per trading day in the window. Unattributed by construction: a band correction cannot invent
    attribution, so these change out-of-band counts, not re-encodes."""
    r = prices.backfill_round(conn(), round_id, write=write)
    return _ok(r, f"{r['observations']} observation(s) over {len(r['legs'])} listed leg(s); {r['out_of_band']} out of band")


@mcp.tool(name="nomad_base_rates", annotations=RO)
def nomad_base_rates(condition: Optional[str] = None, knowable_by: Optional[str] = None) -> dict:
    """v12 F1: institutional frequencies. Most occurrence calls are claims about what an institution will do, and those
    are frequencies, not market claims."""
    r = edge.base_rates(conn(), condition, knowable_by)
    return _ok({"base_rates": r}, f"{len(r)} base rate(s)")


@mcp.tool(name="nomad_base_rate_add", annotations=WR)
def nomad_base_rate_add(key: str, class_: str, condition: str, n: int, k: int, source: str, knowable_from: str,
                        note: Optional[str] = None) -> dict:
    """v12 F1: add a base rate with its denominator, numerator, source and knowable_from."""
    r = edge.base_rate_add(conn(), key, class_, condition, n, k, source, knowable_from, note)
    return _ok(r, f"base rate {key}: {r['rate']}")


@mcp.tool(name="nomad_annotate_leg", annotations=WR)
def nomad_annotate_leg(round_id: str, position_id: str, fact_holder_class: str, price_setter_class: str, basis: str,
                       channel_between: Optional[str] = None, fact_carrier: Optional[str] = None) -> dict:
    """v12 E2: which class demonstrably holds the fact, which class marks the security, and whether a routine channel
    connects them. Classes: contract, credit, equity_generalist, equity_specialist, options, compliance, physical_press,
    procurement. Divergence is derived: different classes and no channel between them."""
    r = edge.annotate_leg(conn(), round_id, position_id, fact_holder_class, price_setter_class, basis, channel_between, fact_carrier)
    return _ok(r, f"class distance {r['class_distance']}, divergence {r['class_divergence']}")


@mcp.tool(name="nomad_practice_date_rules", annotations=WR)
def nomad_practice_date_rules() -> dict:
    """v12 0.2: the seeded risk rules are ordinary practice long predating the programme, so dating them by when they
    became explicit to us made the coverage curve measure our learning. Sets them to the sentinel and marks origin."""
    r = risk.practice_date_rules(conn())
    return _ok(r, f"{len(r['changed'])} rule(s) re-dated to {r['sentinel']}")


@mcp.tool(name="nomad_score_batch", annotations=WR)
def nomad_score_batch(resolutions: list[ResolutionIn]) -> dict:
    """v11 E: score one due batch across every open round. Resolutions are grouped by their prediction's round; each
    round's gates (due date, narrative first) apply as usual. This is the primary scoring loop."""
    r = scorer.score_batch(conn(), resolutions)
    return _ok(r, f"{r['scored']} call(s) scored across {len(r['rounds'])} round(s); {len(r['still_due'])} still due")


@mcp.tool(name="nomad_second_scorer_batch", annotations=RO)
def nomad_second_scorer_batch(before: Optional[str] = None) -> dict:
    """v11 E/A5: one blind view over every call with a final operator resolution and no second score yet, across rounds."""
    r = scorer.second_scorer_batch(conn(), before)
    return _ok(r, f"{r['n_predictions']} call(s) awaiting a second score over {len(r['rounds'])} round(s)")


@mcp.tool(name="nomad_disputes", annotations=RO)
def nomad_disputes() -> dict:
    """v11 E: open disputes per call across rounds."""
    r = scorer.disputes_batch(conn())
    return _ok(r, f"{r['disputes']} open dispute(s)")


@mcp.tool(name="nomad_calibration", annotations=RO)
def nomad_calibration(include_learning: bool = False) -> dict:
    """v11 A1: operator calibration over clean rounds only (learning rounds are recorded and scored, never counted):
    hit rate overall, by call type, absence vs occurrence, by space, and mechanism-right rate."""
    r = scorer.calibration(conn(), include_learning)
    return _ok(r, f"{r['calls']} call(s) counted ({r['excluded_learning']} learning excluded); overall hit rate {r['overall']['rate']}")


@mcp.tool(name="nomad_replay", annotations=WR)
def nomad_replay(round_id: Optional[str] = None, write: bool = True, stack: str = "v12") -> dict:
    """v11 B1: apply the measurement layer to a round's already-locked legs: point-in-time coverage (rules knowable by
    the event date), re-encode detection against dated observations, latency and residual state. Writes
    replay_measurements (replay=true), never resolutions. round_id omitted replays every round, densest first."""
    r = (replay.replay_round(conn(), round_id, write=write, stack=stack) if round_id
         else replay.replay_all(conn(), write=write, stack=stack))
    return _ok(r, f"replayed round {round_id}: {r['cells']} cells, mirror share {r['mirror_share']}, {r['legs_measured']} of {r['legs']} legs measurable"
               if round_id else f"replayed {r['measured_rounds']} round(s); {len(r['failed'])} failed")


@mcp.tool(name="nomad_replay_stats", annotations=RO)
def nomad_replay_stats() -> dict:
    """v11 B3: the coverage-decay curve (mirror share by round), the latency distribution, and K5's rates."""
    c = conn()
    r = {"coverage_decay": replay.coverage_decay(c), "latency": replay.latency_distribution(c), "k5": replay.k5_rates(c)}
    return _ok(r, f"{len(r['coverage_decay'])} round(s) on the decay curve; {r['latency']['legs_with_reencode']} leg(s) with a re-encode; "
                  f"K5 mirror {r['k5']['mirror']['rate']} vs positive {r['k5']['positive']['rate']}")


@mcp.tool(name="nomad_generate_legs", annotations=WR)
def nomad_generate_legs(round_id: str, nodes: Optional[list[str]] = None, mechanism_ids: Optional[list[str]] = None) -> dict:
    """SUPERSEDED by nomad_generate_space (v14 §A2) and then by nomad_effect_root/nomad_effect_compose (v15 §A).
    Kept only for replaying rounds 1-11, which were generated this way. Do not use it on a live round: it writes
    legs, and a leg carries one sign, which the world does not.

    v11 A3: on a learning-class round or a replay, legs are generated from the positions store rather than selected
    by the operator; each row is marked leg_source 'mechanical'. Refused on a clean round."""
    r = rounds.generate_legs(conn(), round_id, nodes, mechanism_ids)
    return _ok(r, f"{r['generated']} mechanical leg(s) on round {round_id} (SUPERSEDED tool: v15 generates effects)")


@mcp.tool(name="nomad_strata", annotations=RO)
def nomad_strata() -> dict:
    """v11 D: admitted rounds by stratum over the rolling window, the pre-registered quota, and the draw order."""
    r = enumeration.stratum_counts(conn())
    return _ok(r, f"counts {r['counts']}; shortfall {r['shortfall']}; next draw order {r['order']}")


@mcp.tool(name="nomad_calls_due", annotations=RO)
def nomad_calls_due(before: Optional[str] = None, round_id: Optional[str] = None) -> dict:
    """v10 A3: unresolved calls due on or before a date across open and partially scored rounds."""
    r = scorer.calls_due(conn(), before, round_id)
    return _ok(r, f"{len(r['due'])} call(s) due by {r['before']}; {r['not_yet_due']} not yet due over {len(r['rounds'])} round(s)")


@mcp.tool(name="nomad_close_round", annotations=WR)
def nomad_close_round(round_id: str, note: Optional[str] = None) -> dict:
    """v10 A3: expire every unresolved call whose due_at has passed (unverified; hit at coverage thin for absence claims)
    and close the round when nothing remains."""
    r = scorer.close_round(conn(), round_id, note=note)
    return _ok(r, f"round {round_id} {r['state']}: {len(r['expired'])} call(s) expired, {len(r.get('remaining_calls', []))} remaining")


# ---- v10 §E scheduled links -----------------------------------------------------------------------------------------

@mcp.tool(name="nomad_catalyst_link", annotations=WR)
def nomad_catalyst_link(round_id: str, position_id: str, fact_id: str, concerns_node: bool, basis: str) -> dict:
    """v10 E2: does this scheduled or mechanical fact concern the leg's node? true = the statement is by a degree-0/1
    holder and the node is a named segment or material input of it (it dates the leg); false = a tide candidate."""
    r = scheduled.link_fact(conn(), round_id, position_id, fact_id, concerns_node, basis)
    return _ok(r, f"link {r['link_id']}: concerns_node={r['concerns_node']}")


@mcp.tool(name="nomad_mechanical_add", annotations=WR)
def nomad_mechanical_add(holder_id: str, kind: str, date: str, source: str, knowable_from: str, url: Optional[str] = None,
                         text: Optional[str] = None) -> dict:
    """v10 I5: a mechanical date (results_announced | index_rebalance | expiry | rebalance_window | margin_date | settlement | other)
    with its source and knowable_from. Dates legs the way ACKs do; the catalyst predicate records which."""
    r = scheduled.scheduled_add(conn(), holder_id, kind, date, source, knowable_from, url, text, fact_type="mechanical", sched_source="announcement")
    return _ok(r, f"mechanical {kind} {date} for holder {r['holder_id']} ({'new' if r['created'] else 'already recorded'})")


# ---- v10 §I/§K risk engine, grid, mirror ------------------------------------------------------------------------------

@mcp.tool(name="nomad_risk_rules", annotations=RO)
def nomad_risk_rules() -> dict:
    """v10 I6: the risk-rules registry with what each covers on the grid."""
    r = risk.list_risk_rules(conn())
    return _ok({"rules": r, "grid": {"effect_kinds": config.EFFECT_KINDS, "degrees": config.GRID_DEGREES, "windows": config.WINDOWS, "factor_kinds": config.FACTOR_KINDS}},
               f"{len(r)} risk rule(s)")


@mcp.tool(name="nomad_risk_rule_add", annotations=WR)
def nomad_risk_rule_add(key: str, text: str, kind: str, covers: dict, knowable_from: str, library_rule: Optional[str] = None) -> dict:
    """v10 I6/K3: add a risk rule (kind veto|date|classify; covers {effect_kinds, factor_kinds, degrees, windows} or '*').
    Only between rounds (no round created or locked). Open mirror cells it covers get coverage_migrations rows."""
    r = risk.risk_rule_add(conn(), key, text, kind, covers, knowable_from, library_rule)
    return _ok(r, f"risk rule {key} added; {len(r['migrations'])} coverage migration(s)")


@mcp.tool(name="nomad_grid", annotations=RO)
def nomad_grid(round_id: str, dry_run: bool = False) -> dict:
    """v10 K1/K6: the round's grid cells with space and covering rule (frozen at lock); dry_run=true computes today's
    assignment for a round locked before v10 without writing."""
    r = risk.dry_run_grid(conn(), round_id) if dry_run else {"cells": risk.grid_cells(conn(), round_id)}
    cells = r["cells"]
    return _ok(r, f"{len(cells)} cells: {sum(1 for c in cells if c['space'] == 'positive')} positive, {sum(1 for c in cells if c['space'] == 'mirror')} mirror" + (" (dry run)" if dry_run else ""))


# v15 §0b.6: `nomad_mirror_dry_run` is retired from the tool surface. v13 §A retired the mirror as a generator --
# absence of an opinion was never evidence -- and a retired mechanism left callable is how it gets used by accident.
# `risk.mirror_dry_run` stays in the module so the rounds that were played on it remain readable and replayable; it
# is no longer reachable from a tool call.


@mcp.tool(name="nomad_price_observe", annotations=WR)
def nomad_price_observe(round_id: str, position_id: str, carrier: str, date: str, value: float, attributed: bool,
                        attribution_evidence_id: Optional[str] = None, closes: Optional[list[float]] = None,
                        band_low: Optional[float] = None, band_high: Optional[float] = None, band_method: Optional[str] = None,
                        note: Optional[str] = None, scoring: bool = False) -> dict:
    """v10 I1: a price observation on a leg, written post-lock only and only once a call on the leg is due (or while
    scoring). Pass closes (prior sessions ending at the reference close) for the pre-registered 20-session band, or a band."""
    r = risk.price_observe(conn(), round_id, position_id, carrier, date, value, attributed, attribution_evidence_id, closes,
                           band_low, band_high, band_method, note, scoring)
    return _ok(r, f"observation {r['observation_id']} on {date}: {'out of band' if r['out_of_band'] else 'in band'}, {'attributed' if r['attributed'] else 'unattributed'}")


@mcp.tool(name="nomad_exposure", annotations=RO)
def nomad_exposure(round_id: Optional[str] = None) -> dict:
    """v10 I4: per shared factor, the sum of sign x support over legs still unrecovered, the earliest forcing date, and
    the shared-factor correlations. round_id omitted = every open or partially scored round. No sizing."""
    r = risk.exposure(conn(), round_id)
    return _ok(r, f"{len(r['factors'])} factor(s) with unrecovered legs over {len(r['rounds'])} round(s)")


@mcp.tool(name="nomad_settings", annotations=WR_IDEMPOTENT)
def nomad_settings(key: Optional[str] = None, value: Optional[str] = None, note: Optional[str] = None) -> dict:
    """v10: programme settings the human sets once (freeze_started_at, clean_lag_days, cap_lookback). No key = list."""
    if key and value is not None:
        r = risk.setting_set(conn(), key, value, note)
        return _ok(r, f"{key} = {value}")
    rows = [dict(x) for x in conn().execute("SELECT key, value, note FROM settings ORDER BY key")]
    return _ok({"settings": rows}, f"{len(rows)} setting(s)")


@mcp.tool(name="nomad_intake_dry_run", annotations=RO)
def nomad_intake_dry_run(event_text: str, event_date: str, criteria_json: dict[str, str], node: Optional[str] = None,
                         node_kind: Optional[str] = None, q1b_override: Optional[dict] = None) -> dict:
    """v9 B: what intake would compute for a candidate without writing anything: Q1b (ledger + registries), Q2, Q7
    density, the tag, and whether the cap would refuse it. The selector runs this per enumerated event."""
    r = rounds.intake_dry_run(conn(), event_text, event_date, criteria_json, node, node_kind, q1b_override=q1b_override)
    return _ok(r, f"tag {r['tag']} (Q1a {r['q1a']}, Q1b {r['q1b']['value']}, Q2 {r['q2']}); cap {'blocks' if r['cap']['blocked'] else 'clear'}")


@mcp.tool(name="nomad_node_history", annotations=RO)
def nomad_node_history(node: str, as_of: Optional[str] = None, node_kind: Optional[str] = None, registries: bool = True) -> dict:
    """v9 B1: recorded disruptions on a node: prior rounds and node_facts of kinds outage|closure|incident|strike|force_majeure
    from the ledger, plus the open incident registries the fetcher can read for the node kind (each with the path that served)."""
    r = history.node_history(conn(), node, as_of, node_kind, registries)
    return _ok(r, f"{r['n']} recorded disruption(s) on {node!r} before {r['as_of']}; registries {[x['registry'] + ':' + str(x['path_served']) for x in r['registries']]}")


@mcp.tool(name="nomad_reject_event", annotations=WR)
def nomad_reject_event(source: str, event_date: str, event_text: str, failing_q: str, note: Optional[str] = None,
                       start_date: Optional[str] = None) -> dict:
    """v9 B5: the selector writes every skipped event with the question it failed (Q1a..Q9, or 'cap') before submitting
    the qualifier. Intake reads these for Q9."""
    r = rounds.reject_event(conn(), source, event_date, event_text, failing_q, note, start_date)
    return _ok(r, f"rejection {r['rejection_id']} written: {event_date} failed {failing_q}")


@mcp.tool(name="nomad_selection_window", annotations=WR)
def nomad_selection_window(source: str, start_date: str, note: Optional[str] = None) -> dict:
    """v9 Q9: fix the source and start date on the ledger before enumerating; pass the same start_date to submit."""
    r = rounds.selection_window_open(conn(), source, start_date, note)
    return _ok(r, f"selection window {r['window_id']}: {source} from {start_date}")


@mcp.tool(name="nomad_selector_clear", annotations=WR_IDEMPOTENT)
def nomad_selector_clear(reason: str) -> dict:
    """v9 B5: human clears a selector suspended after three consecutive Q9 fails."""
    r = rounds.selector_clear(conn(), reason)
    return _ok(r, f"selector cleared; suspended={r['suspended']}")


@mcp.tool(name="nomad_round_tags", annotations=RO)
def nomad_round_tags(round_id: str) -> dict:
    """v9 B3: the round's tag (lag_test|weather|late_headline|learning) with its Q1a/Q1b/Q2 basis and history."""
    r = {"current": rounds.round_tag(conn(), round_id), "history": rounds.list_tags(conn(), round_id), "selector": rounds.selector_status(conn())}
    return _ok(r, f"round {round_id} tag {r['current']['tag'] if r['current'] else None}")


@mcp.tool(name="nomad_scheduled_add", annotations=WR)
def nomad_scheduled_add(holder_id: str, kind: str, date: str, source: str, knowable_from: Optional[str] = None,
                        url: Optional[str] = None, text: Optional[str] = None, supersedes: Optional[str] = None) -> dict:
    """v9 A1 manual fallback: a scheduled fact (results|agm|capital_markets_day|guidance|other) for a holder, with the page
    or filing that says so and when it became knowable. A moved date is a new row with supersedes."""
    r = scheduled.scheduled_add(conn(), holder_id, kind, date, source, knowable_from, url, text, supersedes)
    return _ok(r, f"scheduled {kind} {date} for holder {r['holder_id']} ({'new' if r['created'] else 'already recorded'})")


@mcp.tool(name="nomad_ingest_scheduled", annotations=WR)
def nomad_ingest_scheduled(holder_ids: Optional[list[str]] = None, as_of: Optional[str] = None) -> dict:
    """v9 A2: for each listed holder (or the ones named): EDGAR 8-K item 2.02 dates by filing date (needs cik on the holder)
    and the IR events page via the Wayback snapshot on or before as_of (needs ir_url). New items are appended with
    knowable_from = filing or snapshot date; nothing is overwritten."""
    r = scheduled.ingest_scheduled(conn(), holder_ids, as_of)
    return _ok(r, f"{r['new_facts']} new scheduled fact(s) over {len(r['holders'])} holder(s)")


@mcp.tool(name="nomad_catalyst_check", annotations=WR)
def nomad_catalyst_check(round_id: str, write: bool = False) -> dict:
    """v9 A3: the catalyst-class predicate per leg from the scheduled-facts store (holders at degree <= 1 on the leg,
    event_date < date <= event_date + scoring window). write=true appends predicate_checks on a live round; a scored
    round only gets the dry-run report (arming_status_if_dated), never a rescore."""
    r = scheduled.catalyst_check(conn(), round_id, write)
    return _ok(r, f"{r['legs_dated_observed']} of {len(r['legs'])} legs dated (observed), {r['legs_dated_claimable']} knowable by the event date; "
                  f"{'written' if write else 'dry run'}")


@mcp.tool(name="nomad_scheduled_backfill", annotations=WR)
def nomad_scheduled_backfill(round_ids: list[str], ingest: bool = True) -> dict:
    """v9 A4: populate scheduled facts for the listed holders those rounds touched (as of each round's window) and report,
    without rescoring, how many legs would have been dated: the cost of not having had the feed."""
    r = scheduled.backfill_report(conn(), round_ids, ingest=ingest)
    return _ok(r, f"{r['legs_would_be_dated']} leg(s) would have been dated ({r['legs_would_be_dated_claimable']} knowable by the event date) over {len(round_ids)} round(s)")


@mcp.tool(name="nomad_carrier_path_set", annotations=WR_IDEMPOTENT)
def nomad_carrier_path_set(carrier: str, path: str, status: str, url: Optional[str] = None) -> dict:
    """v9 D1: record a fetch path's status for a carrier: path in live|wayback|pit_api, status in ok|blocked|timeout|unknown.
    Q7 and the lock-time check read the best path, not the nominal access."""
    r = carriers.path_set(conn(), carrier, path, status, url)
    return _ok(r, f"{r['carrier']}: {path} {status}; best path {r['best_path']['path']}:{r['best_path']['status']} ({r['reachability']})")


@mcp.tool(name="nomad_carrier_probe", annotations=WR)
def nomad_carrier_probe(carrier: str, url: Optional[str] = None) -> dict:
    """v9 D1: try the live path and the Wayback availability api for a carrier's url and record both."""
    r = carriers.probe(conn(), carrier, url)
    return _ok(r, f"{r['carrier']}: live {r['live']}, wayback {r['wayback']} -> {r['reachability']}")


@mcp.tool(name="nomad_snapshot", annotations=WR)
def nomad_snapshot(url: str, node: Optional[str] = None, holder_id: Optional[str] = None, note: Optional[str] = None) -> dict:
    """v9 D2: submit a Wayback save-page-now request and record the snapshot url and date as a node_facts row of kind snapshot."""
    r = snapshots.snapshot(conn(), url, node, holder_id, note)
    return _ok(r, f"{r['status']}: {r['snapshot_url'] or r['reason']}")


@mcp.tool(name="nomad_snapshot_targets", annotations=RO)
def nomad_snapshot_targets() -> dict:
    """v9 D2: the pages the scheduler snapshots (IR events pages, notices pages, live-blocked carriers)."""
    r = snapshots.list_targets(conn())
    return _ok({"targets": r}, f"{len(r)} snapshot target(s)")


@mcp.tool(name="nomad_snapshot_target_add", annotations=WR_IDEMPOTENT)
def nomad_snapshot_target_add(url: str, kind: str, node: str, holder_id: Optional[str] = None, carrier_key: Optional[str] = None) -> dict:
    """v9 D2: add a page to the snapshot list (kind ir_events|notices|carrier|other)."""
    r = snapshots.target_add(conn(), url, kind, node, holder_id, carrier_key)
    return _ok(r, f"target {r['target_id']} ({'new' if r['created'] else 'updated'})")


@mcp.tool(name="nomad_snapshot_run", annotations=WR)
def nomad_snapshot_run(limit: Optional[int] = None, kind: Optional[str] = None) -> dict:
    """v9 D2: snapshot every active target (run on demand now, daily later)."""
    r = snapshots.run(conn(), limit=limit, kind=kind)
    return _ok(r, f"{r['saved']} of {r['targets']} target(s) saved")


@mcp.tool(name="nomad_intake_check", annotations=RO)
def nomad_intake_check(node_kind: str) -> dict:
    """Selection filter: does this node kind have open carriers in the registry? Use before choosing a candidate."""
    r = carriers.open_for_kind(conn(), node_kind)
    return _ok(r, f"{node_kind}: {'qualifies' if r['qualifies'] else 'does not qualify'}; open {r['open_carriers']}")


@mcp.tool(name="nomad_pit_fetch", annotations=RO)
def nomad_pit_fetch(source: str, target: str, as_of: str, reason: str) -> dict:
    """B0: point-in-time fetch. source 'wayback' (target = url), 'wikipedia' (target = article title), or v9 'auto'
    (target = url: live when the round is open and the registry does not mark the host blocked, else the nearest
    Wayback snapshot on or before as_of; path_served says which). Legal before lock only when as_of is strictly before
    the live round's event date. Every call is logged with your reason."""
    r = pit.pit_fetch(conn(), source, target, as_of, reason)
    return _ok(r, f"{source} {target!r} as of {as_of}: {r['status']} via {r.get('path_served')}" + (f", snapshot {r['snapshot_date']}" if r.get("found") else f" ({r.get('reason')})"))


@mcp.tool(name="nomad_pit_fetches", annotations=RO)
def nomad_pit_fetches(round_id: Optional[str] = None) -> dict:
    """B0: the log of point-in-time fetches (all, or one round's)."""
    r = pit.list_fetches(conn(), round_id)
    return _ok({"fetches": r}, f"{len(r)} fetches")


@mcp.tool(name="nomad_reveal_event", annotations=RO)
def nomad_reveal_event(round_id: str) -> dict:
    """Operator view: event_text, event_date, and (B5) the reveal context: holders and neighbours already on the node,
    node facts, and library rules matching the node or kind. The context is logged so the second scorer sees the same.
    Next: nomad_touched_set, then nomad_lock_predictions."""
    r = rounds.reveal_event(conn(), round_id)
    c = r.get("context") or {}
    return _ok(r, f"event revealed for round {round_id} (state {r['state']}); context: {len(c.get('holders', []))} holders, "
                  f"{len(c.get('neighbours', []))} neighbours, {len(c.get('node_facts', []))} node facts, {len(c.get('rules', []))} rules; "
                  "next: nomad_touched_set then nomad_lock_predictions")


@mcp.tool(name="nomad_node_context", annotations=RO)
def nomad_node_context(node: str, event_kind: Optional[str] = None) -> dict:
    """Read-only: what the store holds on a node (holders, neighbours, node facts, matching rules). Legal before lock:
    it reads the operator's own ledgers only."""
    r = rounds.reveal_context_for(conn(), node, event_kind)
    return _ok(r, f"{len(r['holders'])} holders, {len(r['neighbours'])} neighbours, {len(r['node_facts'])} facts, {len(r['rules'])} rules on {node!r}")


@mcp.tool(name="nomad_touched_set", annotations=WR)
def nomad_touched_set(round_id: str, rows: list[TouchedSetIn]) -> dict:
    """B3: one row per holder x degree (0 site, 1 direct counterparties, 2 their counterparties, 3 sector) with node,
    position_summary, substitutability (low|med|high|unknown), duration_factor, carrier. Required before lock unless
    lock_note declares 'no-touched-set: <why>'. v9 C1: mechanism_ids on a row cites the rule(s) that support the leg;
    every component of a synthetic needs one, and synthetics are built before lock."""
    r = rounds.touched_set_add(conn(), round_id, rows)
    return _ok(r, f"{r['count']} touched-set row(s) on round {round_id} ({r['total']} total)")


@mcp.tool(name="nomad_lock_predictions", annotations=WR)
def nomad_lock_predictions(round_id: str, predictions: list[PredictionIn], lock_note: Optional[str] = None,
                           leg_claims: Optional[list] = None) -> dict:
    """Append predictions (each stamped locked_at). Moves the round to `locked` on first call. Never editable.
    falsifier_window is required for null and predicate calls (scoring_window | days:N | until:YYYY-MM-DD).
    B1: lag_band calls and duration/extent claims need factors[] (>=1 binding, >=1 against); the composite is derived at
    scoring. B4: one claim per row. B3: a touched set must exist, or lock_note starts 'no-touched-set: <why>'.
    v8: a cited rule must carry the call's claim kind (A2); a map call with real uncertainty lists branches[] and
    downstream rows set conditional_on {prediction_ref '#i', branch} (B1); narrative rows (call_type narrative,
    narrative_sign, position_id, a channel carrier) measure what a channel said (F1); carriers are resolved against the
    registry and unreachable ones are flagged, Q7 computed (D2)."""
    r = rounds.lock_predictions(conn(), round_id, predictions, lock_note=lock_note, leg_claims=leg_claims)
    sr = r.get("surviving_risk") or {}
    return _ok(r, f"{len(r['prediction_ids'])} prediction(s) locked on round {round_id} ({r['n_locked_total']} total)"
                  + (f"; surviving risk on {sr.get('surviving')} of {sr.get('legs')} legs" if sr else "")
                  + "; next: nomad_open_retrieval")


@mcp.tool(name="nomad_open_retrieval", annotations=WR)
def nomad_open_retrieval(round_id: str, event_date_confirmed: Optional[str] = None,
                         date_source: Optional[str] = None) -> dict:
    """Requires `locked`. Opens retrieval and returns the frozen predictions with each falsifier window's end date.

    v13 B2: pass event_date_confirmed once retrieval establishes what the event actually is. Q2 is re-computed against
    it and the round is voided automatically if the event turns out to predate the operator cutoff. Scoring is refused
    until that has happened (nomad_confirm_event_date does it separately)."""
    r = rounds.open_retrieval(conn(), round_id, event_date_confirmed=event_date_confirmed, date_source=date_source)
    if r["state"] == "void":
        return _ok(r, f"round {round_id} voided at retrieval: {r['q2_recheck']['q2']}")
    return _ok(r, f"round {round_id} is open: {len(r['predictions'])} frozen prediction(s); retrieval permitted. "
                  "Record what you find with nomad_add_evidence, then nomad_score_round")


@mcp.tool(name="nomad_confirm_event_date", annotations=WR)
def nomad_confirm_event_date(round_id: str, event_date: str, source: str) -> dict:
    """v13 B2: record the event date as retrieval established it, re-compute Q2 against it and void on a fail. Q2 at
    intake can only test the date the submitter supplied; round 12 was misdated by a year and passed it."""
    r = rounds.confirm_event_date(conn(), round_id, event_date, source)
    return _ok(r, ("round voided: " + r["q2"]) if r["voided"] else r["q2"])


@mcp.tool(name="nomad_surviving_risk", annotations=WR)
def nomad_surviving_risk(round_id: str, as_of: Optional[str] = None, write: bool = True, replay: bool = False) -> dict:
    """v13 A2: does any risk survive this leg? Runs the silence rules as eliminators, each only where its declared
    precondition holds, and records per leg which fired, which were checked, which could not be evaluated at all, and
    the surviving magnitude. A leg no risk survives is a non-position, not a safe position."""
    r = surviving.assess_round(conn(), round_id, as_of=as_of, write=write, replay=replay)
    return _ok(r, f"{r['surviving']} of {r['legs']} legs carry surviving risk "
                  f"({r['legs_with_no_evaluable_eliminator']} with no evaluable eliminator)")


@mcp.tool(name="nomad_generate_space", annotations=WR)
def nomad_generate_space(round_id: str, nodes: Optional[list[str]] = None, proposals: Optional[list] = None,
                         hops: bool = True, write: bool = True) -> dict:
    """v14 A2: permissive generation. Every holder with a position on the round's nodes, at every degree the store can
    reach, plus everything one hop out (parent, child, same-node counterparty, chain-adjacent), plus anything a hunch
    proposes. A proposal may put a leg on the board and may never support one: only anchors and fetched facts keep it
    there, so a wrong analogy costs an eliminated leg rather than a scored miss. Returns `generation_width`."""
    r = generate.generate_space(conn(), round_id, nodes=nodes, proposals=proposals, hops=hops, write=write)
    return _ok(r, f"generation width {r['generation_width']} ({r['written']} new legs written)"
                  + (f"; {r['note']}" if r.get("note") else ""))


@mcp.tool(name="nomad_adjacent", annotations=RO)
def nomad_adjacent(holder_id: str, node: str, round_id: Optional[str] = None) -> dict:
    """v14 A6a: what shares factors with this leg and what the hop costs. No ranking and no recommendation - the
    harness will not tell you which neighbour to walk to, because a route-finder over thirteen contingent propagations
    would encode cascade priors that are limiting and wrong, and would only surface paths already walked."""
    r = generate.adjacent(conn(), holder_id, node, round_id)
    return _ok(r, f"{r['n']} neighbour(s) of {r['from']['holder']} on {node}; costs reported, no ranking")


@mcp.tool(name="nomad_glossary", annotations=RO)
def nomad_glossary() -> dict:
    """v14 A6a: the callable surface, stated plainly, with no claim about which move to use or in what order."""
    r = glossary.glossary()
    return _ok(r, f"{r['n']} moves")


@mcp.tool(name="nomad_index", annotations=RO)
def nomad_index() -> dict:
    """v14 A6b: what exists, what is callable, what is held, what has been done before."""
    return _ok(glossary.index(conn()), "index over the store")


@mcp.tool(name="nomad_precedent", annotations=RO)
def nomad_precedent(call_type: Optional[str] = None, node_kind: Optional[str] = None,
                    event_kind: Optional[str] = None) -> dict:
    """v14 A6b: what settled a claim of this shape before - the carriers that carried the resolution and the documents
    named. Precedent, never endorsement. This is the query that would have caught round 13's ITC caption."""
    r = glossary.precedent(conn(), call_type, node_kind, event_kind)
    return _ok(r, f"{r['n']} prior call(s) of this shape; outcomes {r['outcomes']}")


@mcp.tool(name="nomad_log_move", annotations=WR)
def nomad_log_move(move: str, reason: str, round_id: Optional[str] = None, target: Optional[str] = None,
                   result: Optional[str] = None, cost: Optional[str] = None) -> dict:
    """v14 A6c: log a move with the operator's stated reason. The discipline is what gets written and when, not which
    tools may be called: a leg reached by seven deliberate hops is more auditable than one that appears unexplained."""
    r = glossary.log_move(conn(), move, reason, round_id, target, result, cost)
    return _ok(r, f"move logged: {r['move']}")


@mcp.tool(name="nomad_operator_risk", annotations=RO)
def nomad_operator_risk() -> dict:
    """v14 A5: the operator's failure distribution, computed from clean resolutions and never asserted."""
    r = vector.operator_rates(conn())
    return _ok(r, f"computed over {r.get('_n')} resolved calls on clean rounds")


@mcp.tool(name="nomad_null_breakdown", annotations=RO)
def nomad_null_breakdown(round_id: Optional[str] = None) -> dict:
    """v13 A5: absence calls split by whether any risk survived the leg they were called on. Only a null on a surviving
    leg was ever a fadeable null; the rest are non-positions and are reported as such."""
    r = surviving.null_breakdown(conn(), round_id)
    return _ok(r, f"{r['absence_calls']} absence call(s): {r['counts']}")


@mcp.tool(name="nomad_set_preconditions", annotations=WR)
def nomad_set_preconditions() -> dict:
    """v13 A3: write each risk rule's pre-registered eliminator precondition onto its row."""
    r = risk.set_preconditions(conn())
    return _ok(r, f"{len(r['changed'])} rule(s) given a precondition")


@mcp.tool(name="nomad_add_evidence", annotations=WR)
def nomad_add_evidence(round_id: str, url: str, title: str, excerpt: str, source_time: Optional[str] = None,
                       knowable_from: Optional[str] = None, note: Optional[str] = None) -> dict:
    """Requires `open`. Appends an evidence row (excerpt <= 500 chars). source_time = time in the document;
    knowable_from = when it became publicly discoverable."""
    r = rounds.add_evidence(conn(), round_id, url, title, excerpt, source_time, knowable_from, note)
    return _ok(r, f"evidence {r['evidence_id']} recorded on round {round_id}")


@mcp.tool(name="nomad_add_evidence_batch", annotations=WR)
def nomad_add_evidence_batch(round_id: str, items: list[dict]) -> dict:
    """Requires `open`. Validates every item (url, title, excerpt <= 500, optional source_time/knowable_from/note) and
    writes them in one transaction; one bad item means nothing is written."""
    r = rounds.add_evidence_batch(conn(), round_id, items)
    return _ok(r, f"{r['count']} evidence row(s) recorded on round {round_id}")


@mcp.tool(name="nomad_round_note", annotations=WR)
def nomad_round_note(round_id: str, kind: str, note: str) -> dict:
    """Append a free-text note to a round (e.g. kind='tide' for a macro backdrop that made legs unscoreable)."""
    r = rounds.round_note(conn(), round_id, kind, note)
    return _ok(r, f"note {r['note_id']} ({kind}) recorded on round {round_id}")


@mcp.tool(name="nomad_score_round", annotations=WR)
def nomad_score_round(round_id: str, resolutions: list[ResolutionIn]) -> dict:
    """Requires `open` and exactly one resolution per prediction. source_coverage is required on miss/unverified;
    quality is computed from round class, scorer, coverage, call type and evidence class. Moves the round to `scored`."""
    r = scorer.score_round(conn(), round_id, resolutions)
    return _ok(r, f"round {round_id} scored ({r['round_class']}): outcome {r['outcome_score']} mechanism {r['mechanism_score']} "
                  f"baseline {r['baseline_score']} edge {r['edge_vs_baseline']} (null weight {NULL_CALL_WEIGHT})")


@mcp.tool(name="nomad_resolution_supersede", annotations=WR)
def nomad_resolution_supersede(round_id: str, resolution: ResolutionIn) -> dict:
    """Correction on a scored round: a new resolution whose `supersedes` names the current one. The old row stays;
    the scorecard is recomputed and the library rebuilt. Requires a scorer_note explaining the correction."""
    r = scorer.supersede_resolution(conn(), round_id, resolution)
    return _ok(r, f"resolution {r['superseded']} superseded by {r['resolution_id']}; mechanism now {r['mechanism_score']}")


@mcp.tool(name="nomad_second_scorer_view", annotations=RO)
def nomad_second_scorer_view(round_id: str, nodes: Optional[list[str]] = None) -> dict:
    """B2: what a second scorer may see on a scored round: the locked calls, the evidence, and the positions on the
    round's nodes (for calls whose carrier is the positions store). Nothing of the operator's scoring."""
    r = scorer.second_scorer_view(conn(), round_id, nodes)
    return _ok(r, f"round {round_id}: {len(r['predictions'])} calls, {len(r['evidence'])} evidence rows, "
                  f"positions on {len(r['positions'])} node(s); score them blind")


@mcp.tool(name="nomad_second_score", annotations=WR)
def nomad_second_score(round_id: str, resolutions: list[SecondScoreIn], scorer_session: Optional[str] = None) -> dict:
    """B2: append the second scorer's resolutions (own ledger) and return the disputes with the operator's scores."""
    r = scorer.second_score(conn(), round_id, resolutions, scorer_session)
    return _ok(r, f"round {round_id}: {r['disputes']} dispute(s) over {r['compared']} compared")


@mcp.tool(name="nomad_score_disputes", annotations=RO)
def nomad_score_disputes(round_id: str) -> dict:
    """B2: operator vs second scorer per prediction; the human breaks each dispute with nomad_resolution_supersede."""
    r = scorer.score_disputes(conn(), round_id)
    return _ok(r, f"round {round_id}: {r['disputes']} dispute(s) over {r['compared']} compared")


@mcp.tool(name="nomad_void_round", annotations=WR)
def nomad_void_round(round_id: str, reason: str, peeked: bool = False) -> dict:
    """Any state -> void, reason logged, nothing deleted. peeked=true records contamination 'peeked' (misconduct)."""
    r = rounds.void_round(conn(), round_id, reason, peeked)
    return _ok(r, f"round {round_id} voided from {r['from_state']}: {reason}")


@mcp.tool(name="nomad_criteria_supersede", annotations=WR)
def nomad_criteria_supersede(event_id: str, criteria_json: dict[str, str], reason: str) -> dict:
    """Human correction of an event's Q1-Q9 criteria: a new event_criteria row; the intake row stays."""
    r = rounds.criteria_supersede(conn(), event_id, criteria_json, reason)
    return _ok(r, f"criteria for event {event_id} superseded ({r['criteria_id']})")


@mcp.tool(name="nomad_round_status", annotations=RO)
def nomad_round_status(round_id: str) -> dict:
    """State, classification, counts, transitions, and the next step."""
    r = rounds.round_status(conn(), round_id)
    return _ok(r, f"round {round_id} is {r['state']} ({r['classification']['round_class']}): {r['counts']}. Next: {r['next_step']}")


@mcp.tool(name="nomad_export_round", annotations=RO)
def nomad_export_round(round_id: str) -> dict:
    """Full round as JSON, including classification history, criteria history and the chain heads of every ledger."""
    r = rounds.export_round(conn(), round_id)
    return _ok(r, f"round {round_id} exported ({len(r['predictions'])} predictions, {len(r['evidence'])} evidence); chain heads attached")


# ---- library ----------------------------------------------------------------

@mcp.tool(name="nomad_library_query", annotations=RO)
def nomad_library_query(text: Optional[str] = None, layer: Optional[str] = None, status: Optional[str] = None,
                        limit: int = 20) -> dict:
    """Search rules and compositions. Returns rule, counts and propagated weight."""
    rows = library.query(conn(), text, layer, status, limit)
    return _ok({"rules": rows, "count": len(rows), "validation_threshold": config.VALIDATION_THRESHOLD}, f"{len(rows)} rule(s)")


@mcp.tool(name="nomad_library_propose", annotations=WR)
def nomad_library_propose(rule_text: str, forbids: str, obscurity: int, layer: str, provenance: str,
                          composed_of: Optional[list[str]] = None, round_id: Optional[str] = None,
                          carries: Optional[list[str]] = None) -> dict:
    """Propose a rule (or a composition via composed_of). Rejects proper nouns in rule_text; nouns go in provenance.
    v8 A1: carries is required, one or more of occurrence | absence | ordering | magnitude | duration | map: the kinds
    of claim this rule can be cited on. Lock refuses a citation on any other kind."""
    r = library.propose(conn(), rule_text, forbids, obscurity, layer, provenance, composed_of, round_id, carries=carries)
    return _ok(r, f"{'composition' if r['is_composition'] else 'rule'} {r['rule_id']} proposed as candidate")


@mcp.tool(name="nomad_library_set_carries", annotations=WR_IDEMPOTENT)
def nomad_library_set_carries(rule_id: str, carries: list[str]) -> dict:
    """v8 A1: set or ratify what a rule carries (occurrence | absence | ordering | magnitude | duration | map)."""
    r = library.set_carries(conn(), rule_id, carries)
    return _ok(r, f"rule {r['key'] or r['rule_id']} carries {r['carries']}")


@mcp.tool(name="nomad_carrier_check", annotations=RO)
def nomad_carrier_check(carriers_named: list[str]) -> dict:
    """v8 D2: before lock, resolve the carriers you intend to name against the registry. Returns carrier_unreachable
    (paywalled or blocked only) and the Q7 the harness would compute. Name a fallback for each flagged one."""
    r = carriers.check(conn(), carriers_named)
    return _ok(r, f"{len(r['carrier_unreachable'])} of {len(carriers_named)} unreachable; Q7 would be {r['q7_computed']}")


@mcp.tool(name="nomad_carrier_upsert", annotations=WR_IDEMPOTENT)
def nomad_carrier_upsert(name: str, kind: str, access: str, note: Optional[str] = None, key: Optional[str] = None) -> dict:
    """v8 D1: add or update a carrier. kind: price_assessment|notice_feed|filing|newspaper|index|transcript;
    access: open|paywalled|blocked|unknown."""
    r = carriers.carrier_upsert(conn(), name, kind, access, note, key)
    return _ok(r, f"carrier {r['name']} {r['access']} ({'updated' if r['updated'] else 'new'})")


@mcp.tool(name="nomad_carriers", annotations=RO)
def nomad_carriers() -> dict:
    """v8 D1: the carriers registry."""
    r = carriers.list_carriers(conn())
    return _ok({"carriers": r}, f"{len(r)} carriers")


@mcp.tool(name="nomad_synthetic_rules", annotations=RO)
def nomad_synthetic_rules() -> dict:
    """v8 E2: pre-registered synthetic construction rules."""
    r = synthetic.list_rules(conn())
    return _ok({"rules": r}, f"{len(r)} construction rules")


@mcp.tool(name="nomad_synthetic_build", annotations=WR)
def nomad_synthetic_build(round_id: str, target_node: str, rule_id: str, dry_run: bool = False, space: str = "positive") -> dict:
    """v8 E2/E3: construct a synthetic leg mechanically under one pre-registered rule from the round's legs. Signs only.
    support_weight = min(component support) x COMPONENT_DISCOUNT^(n-1). Returns built=false with the reason when the
    rule's pattern is absent (never hand-built). v9 C1: refused after lock; every component cites a mechanism on its
    touched_set row."""
    r = synthetic.synthetic_build(conn(), round_id, target_node, rule_id, dry_run=dry_run, space=space)
    return _ok(r, f"synthetic {r['synthetic_id']} built: {r['n_components']} components, support {r['support_weight']}" if r["built"]
               else (f"dry run: {r['n_components']} components, support {r['support_weight']}" if r.get("dry_run") and "reason" not in r else f"not built: {r['reason']}"))


@mcp.tool(name="nomad_library_retire", annotations=WR_IDEMPOTENT)
def nomad_library_retire(rule_id: str, reason: str, superseded_by: Optional[str] = None) -> dict:
    """Retire a rule; optionally point at its replacement."""
    r = library.retire(conn(), rule_id, reason, superseded_by)
    return _ok(r, f"rule {rule_id} retired")


# ---- predicates ------------------------------------------------------------

@mcp.tool(name="nomad_predicate_list", annotations=RO)
def nomad_predicate_list(kind: Optional[str] = None, include_inactive: bool = False) -> dict:
    """Registry read. kind in arming|disarming|exit|catalyst."""
    rows = predicates.predicate_list(conn(), kind, include_inactive)
    return _ok({"predicates": rows, "count": len(rows)}, f"{len(rows)} predicate(s)")


@mcp.tool(name="nomad_predicate_check", annotations=WR)
def nomad_predicate_check(round_id: str, checks: list[PredicateCheckIn]) -> dict:
    """Record the operator's claim (and, at scoring time, the observation) for predicates on a round.
    First traversal takes two checks per round: scope 'event' and scope 'node'."""
    r = predicates.predicate_check(conn(), round_id, checks)
    return _ok(r, f"{len(r['checks'])} predicate check(s) recorded on round {round_id}")


@mcp.tool(name="nomad_model_cutoffs", annotations=RO)
def nomad_model_cutoffs() -> dict:
    """Human-maintained operator cutoffs (set with the CLI: nomad-harness model-cutoff set <model> <date>)."""
    rows = rounds.model_cutoffs_list(conn())
    return _ok({"model_cutoffs": rows, "current_operator": config.operator_model()}, f"{len(rows)} model(s) on file")


# ---- T0 --------------------------------------------------------------------

@mcp.tool(name="nomad_t0_submit_candidate", annotations=WR)
def nomad_t0_submit_candidate(event_id: str, window_label: str, criteria_pass: bool, arming_pass: Optional[bool] = None,
                              arming_pass_pair: Optional[bool] = None, listed_party: Optional[str] = None,
                              pair_holders: Optional[list[str]] = None, carrier: Optional[str] = None,
                              micro_macro_note: Optional[str] = None) -> dict:
    """Append a T0 candidate: criteria checklist result plus single- and pair-form arming results."""
    r = t0.submit_candidate(conn(), event_id, window_label, criteria_pass, arming_pass, arming_pass_pair, listed_party,
                            pair_holders, carrier, micro_macro_note)
    return _ok(r, f"T0 candidate {r['candidate_id']} recorded in window {window_label}")


@mcp.tool(name="nomad_t0_count", annotations=RO)
def nomad_t0_count(window_label: str) -> dict:
    """Counts over a window: candidates, criteria_pass, arming_pass (single/pair), distinct (event x listed_party x carrier)."""
    r = t0.count(conn(), window_label)
    return _ok(r, f"window {window_label}: {r['candidates']} candidates, {r['criteria_pass']} criteria_pass, "
                  f"{r['arming_pass']} arming_pass, {r['distinct_triples']} distinct triples")


# ---- names book ------------------------------------------------------------

@mcp.tool(name="nomad_holder_upsert", annotations=WR_IDEMPOTENT)
def nomad_holder_upsert(canonical_name: str, kind: str, listed: bool = False, parent_id: Optional[str] = None,
                        ticker: Optional[str] = None, exchange: Optional[str] = None,
                        aliases: Optional[list[str]] = None, source: str = "operator",
                        first_seen_round: Optional[str] = None, key: Optional[str] = None,
                        ir_url: Optional[str] = None, cik: Optional[str] = None) -> dict:
    """Create or update a holder (company|plant|facility|authority|fund|other) and append aliases. v9: ir_url (the IR
    events page, snapshotted and parsed for scheduled facts) and cik (EDGAR) fill the names book from dated pages."""
    r = names.holder_upsert(conn(), canonical_name, kind, listed, parent_id, ticker, exchange, aliases, source, first_seen_round,
                            key=key, ir_url=ir_url, cik=cik)
    return _ok(r, f"holder {r['holder_id']} {'created' if r['created'] else 'updated'}; {r['aliases_added']} alias(es) added")


@mcp.tool(name="nomad_resolve", annotations=WR)
def nomad_resolve(raw_string: str, context: Optional[str] = None, round_id: Optional[str] = None) -> dict:
    """Normalised exact match against aliases -> holder, else writes an orphan and returns unresolved."""
    r = names.resolve(conn(), raw_string, context, round_id)
    if r["resolved"]:
        return _ok(r, f"{raw_string!r} -> {r['holder']['canonical_name']} ({r['holder']['kind']})")
    return _ok(r, f"{raw_string!r} unresolved; orphan {r['orphan_id']} queued")


@mcp.tool(name="nomad_orphans", annotations=RO)
def nomad_orphans(limit: int = 50) -> dict:
    """Queue of unresolved names (those that still do not resolve)."""
    r = names.orphans(conn(), limit)
    return _ok(r, f"{r['unresolved']} unresolved of {r['total_recorded']} recorded")


# ---- positions -------------------------------------------------------------

@mcp.tool(name="nomad_position_add", annotations=WR)
def nomad_position_add(holder_id: str, node: str, attribute: str, value: str, source: str, confidence: str,
                       unit: Optional[str] = None, source_time: Optional[str] = None,
                       knowable_from: Optional[str] = None, supersedes: Optional[str] = None) -> dict:
    """Append a position fact. attribute in tier|priority|substitutability|share|duration|sign_of_exposure;
    confidence in stated|inferred|implicit. Populate sign_of_exposure first."""
    r = positions.position_add(conn(), holder_id, node, attribute, value, source, confidence, unit, source_time, knowable_from, supersedes)
    return _ok(r, f"position {r['position_id']}: {attribute}={value} on {node}")


@mcp.tool(name="nomad_positions_on_node", annotations=RO)
def nomad_positions_on_node(node: str, listed_only: bool = False) -> dict:
    """Current positions on a node grouped by holder; flags opposing-sign listed pairs and self-hedged holders."""
    r = positions.positions_on_node(conn(), node, listed_only)
    return _ok(r, f"{len(r['holders'])} holder(s) on {node}; {len(r['pairs'])} opposing listed pair(s); {len(r['self_hedged'])} self-hedged")


# ---- hypotheses ------------------------------------------------------------

@mcp.tool(name="nomad_hypothesis_open", annotations=WR)
def nomad_hypothesis_open(text: str, holder_ids: list[str], mechanism_ids: list[str], arming_predicate_ids: list[str],
                          disarming_predicate_ids: list[str], falsifier: str, granularity: str,
                          node: Optional[str] = None, position_ids: Optional[list[str]] = None,
                          round_id: Optional[str] = None, supersedes: Optional[str] = None,
                          spawned_from: Optional[dict] = None) -> dict:
    """Open a standing hypothesis (one falsifiable sentence, predicate-bound). Rejects missing falsifier or granularity.
    support_weight is the weakest cited rule's weight; arming needs it at or above the validation threshold.
    D1: spawned_from={prediction_id, factor_index} ties it to a factor; support then inherits that factor's evidence quality."""
    r = hypotheses.hypothesis_open(conn(), text, holder_ids, mechanism_ids, arming_predicate_ids,
                                   disarming_predicate_ids, falsifier, granularity, node, position_ids, round_id, supersedes,
                                   spawned_from=spawned_from)
    return _ok(r, f"hypothesis {r['hypothesis_id']} opened (support_weight {r['support_weight']}, threshold {r['validation_threshold']})")


@mcp.tool(name="nomad_hypothesis_check", annotations=WR)
def nomad_hypothesis_check(hypothesis_id: str, checks: list[HypothesisCheckIn]) -> dict:
    """Append predicate observations and recompute the derived status. Arming reads support_weight."""
    r = hypotheses.hypothesis_check(conn(), hypothesis_id, checks)
    return _ok(r, f"hypothesis {hypothesis_id}: {r['previous_status']} -> {r['status']}" + (f" ({r['arming_note']})" if r["arming_note"] else ""))


@mcp.tool(name="nomad_hypothesis_schedule", annotations=WR_IDEMPOTENT)
def nomad_hypothesis_schedule(hypothesis_id: str, next_check_at: Optional[str], hard_stop_at: Optional[str] = None,
                              check_cadence_days: Optional[int] = None) -> dict:
    """Human-set schedule: next_check_at (ISO date), hard_stop_at, cadence in days (advances next_check_at on each check)."""
    r = hypotheses.hypothesis_schedule(conn(), hypothesis_id, next_check_at, hard_stop_at, check_cadence_days)
    return _ok(r, f"hypothesis {hypothesis_id}: next check {r['next_check_at']}, hard stop {r['hard_stop_at']}")


@mcp.tool(name="nomad_hypotheses_due", annotations=RO)
def nomad_hypotheses_due(status: Optional[str] = None, limit: int = 50, due_only: bool = False) -> dict:
    """Open/armed hypotheses with last check, per-predicate status, support weight, and whether a check is due."""
    r = hypotheses.hypotheses_due(conn(), status, limit, due_only)
    return _ok(r, f"{r['count']} hypothesis(es) in {r['statuses']}")


# ---- B4: node facts -------------------------------------------------------

@mcp.tool(name="nomad_node_fact_add", annotations=WR)
def nomad_node_fact_add(node: str, fact_type: str, text: str, source: str, url: Optional[str] = None,
                        holder_id: Optional[str] = None, source_time: Optional[str] = None,
                        knowable_from: Optional[str] = None) -> dict:
    """Append a dated node fact independent of any round. fact_type in force_majeure|allocation|port_notice|
    premium_assessment|enforcement|outage|restart|dependency|other. Same url+node is not written twice."""
    r = facts.node_fact_add(conn(), node, fact_type, text, source, url, holder_id, source_time, knowable_from)
    return _ok(r, f"node fact {r['fact_id']} on {r['node']} ({'new' if r['created'] else 'already recorded'})")


@mcp.tool(name="nomad_node_facts", annotations=RO)
def nomad_node_facts(node: Optional[str] = None, fact_type: Optional[str] = None, since: Optional[str] = None,
                     limit: int = 50) -> dict:
    """Recent node facts, newest first."""
    rows = facts.node_facts(conn(), node, fact_type, since, limit)
    return _ok({"facts": rows, "count": len(rows)}, f"{len(rows)} node fact(s)")


@mcp.tool(name="nomad_ingest_target_add", annotations=WR)
def nomad_ingest_target_add(name: str, question: str, node: Optional[str] = None, round_id: Optional[str] = None) -> dict:
    """Name something the daily ingest should be looking for (e.g. a restart date a round could not verify)."""
    r = facts.target_add(conn(), name, question, node, round_id)
    return _ok(r, f"ingest target {r['target_id']} opened: {name}")


@mcp.tool(name="nomad_ingest_targets", annotations=RO)
def nomad_ingest_targets(status: Optional[str] = "open") -> dict:
    """Open (or all, status=None) ingest targets."""
    rows = facts.targets(conn(), status)
    return _ok({"targets": rows, "count": len(rows)}, f"{len(rows)} target(s)")


@mcp.tool(name="nomad_ingest_target_close", annotations=WR_IDEMPOTENT)
def nomad_ingest_target_close(target_id: str, status: str, found_fact_id: Optional[str] = None) -> dict:
    """Close a target as found (with the node fact that answers it) or expired."""
    r = facts.target_close(conn(), target_id, status, found_fact_id)
    return _ok(r, f"target {target_id} {status}")


# ---- integrity / programme ------------------------------------------------

@mcp.tool(name="nomad_verify_chain", annotations=RO)
def nomad_verify_chain(table: Optional[str] = None) -> dict:
    """Walk the hash chains (all ledgers, or one). Returns ok or the first break."""
    r = verify_chain(conn(), table)
    return _ok(r, "chain ok" if r["ok"] else f"CHAIN BROKEN at {r['first_break']}")


@mcp.tool(name="nomad_programme_stats", annotations=RO)
def nomad_programme_stats(include_learning: bool = False, criteria_pass_only: bool = False, tag: Optional[str] = None) -> dict:
    """Arming rate and mechanism-score distribution over clean rounds (include_learning=true for the second view;
    criteria_pass_only=true drops rounds whose current criteria carry a fail). v9 F: tag filters to one round tag
    (the lag hypothesis reads lag_test only); arming is three counts per tag (armed_dated / gate_pass_undated /
    gate_fail); scheduled-facts coverage and fetch-path health are reported; notebook rows E4/F3 per round."""
    r = scorer.programme_stats(conn(), include_learning, criteria_pass_only, tag)
    a = r["arming_counts"]
    return _ok(r, f"{r['rounds_scored']} counted ({r['rounds_scored_clean']} clean, {r['rounds_scored_learning']} learning); "
                  f"arming {a['armed_dated']}/{a['gate_pass_undated']}/{a['gate_fail']} (dated/undated/fail); "
                  f"scheduled coverage {r['scheduled_facts_coverage']['coverage']}; mean mechanism score {r['mechanism_score']['mean']}")


@mcp.tool(name="nomad_event_basket", annotations=RO)
def nomad_event_basket(round_id: str, space: str = "positive") -> dict:
    """D4: the round's legs (holder x node from the touched set, factor links and in-round positions) with sign,
    support weight, per-leg arming (D3) and correlation by shared node. A view; never scored as a whole."""
    r = basket.event_basket(conn(), round_id, space=space)
    return _ok(r, f"{r['n_legs']} legs, signs at lock {r['signs']}, {r['revised_legs']} revised post-lock, arming {r['arming_status_counts']}, "
                  f"{r['divergent_legs']} divergent; cells {r['cell_counts']}, mirror arming {r['mirror_arming']}, residual {r['residual_states']}")


@mcp.tool(name="nomad_shared_factors", annotations=RO)
def nomad_shared_factors(round_id: Optional[str] = None, hypothesis_ids: Optional[list[str]] = None) -> dict:
    """D2: pairs of legs or hypotheses that cite the same node, with each side's sign. Same node = correlated by construction."""
    r = basket.shared_factors(conn(), round_id, hypothesis_ids)
    return _ok(r, f"{len(r['pairs'])} shared-node pairs over {r['items']} items ({r['opposing_pairs']} opposing)")


@mcp.tool(name="nomad_scorer_bias", annotations=RO)
def nomad_scorer_bias() -> dict:
    """C4: over clean rounds, how the operator's original scores differ from the second scorer's, by direction."""
    r = scorer.scorer_bias(conn())
    return _ok(r, f"{r['compared']} compared; lenient {r['lenient']}, under-informed {r['under_informed']}, self stricter {r['self_stricter']}")


# ---- v15 §A: the effect DAG -----------------------------------------------------------------------------------

@mcp.tool(name="nomad_effect_root", annotations=WR)
def nomad_effect_root(round_id: str, node: str, effect_kind: str, carrier: str, falsifier: str,
                      holder_id: Optional[str] = None, magnitude: Optional[float] = None,
                      magnitude_basis: Optional[str] = None, due_at: Optional[str] = None,
                      mechanism_ids: Optional[list[str]] = None, ack_id: Optional[str] = None,
                      basis: Optional[str] = None, segment_id: Optional[str] = None) -> dict:
    """v15 A1: a root effect of the event. An effect IS a claim, with a carrier and a falsifier, scored on its own.
    kinds: direction | volume | vol | timing | cost | obligation. There is no sign field: sign is a projection
    applied at generation time, which is the worst possible moment for it (A3)."""
    r = effects.add_root(conn(), round_id, node, effect_kind, carrier, falsifier, holder_id, magnitude,
                         magnitude_basis, due_at, mechanism_ids, ack_id, basis, segment_id=segment_id)
    return _ok(r, f"root effect {r['effect_id']} ({effect_kind}) at depth 1")


@mcp.tool(name="nomad_effect_compose", annotations=WR)
def nomad_effect_compose(round_id: str, parent_effect_id: str, relation_id: str, effect_kind: str, node: str,
                         carrier: str, falsifier: str, holder_id: Optional[str] = None,
                         magnitude: Optional[float] = None, magnitude_basis: Optional[str] = None,
                         due_at: Optional[str] = None, ack_id: Optional[str] = None,
                         mechanism_ids: Optional[list[str]] = None, basis: Optional[str] = None,
                         write: bool = True) -> dict:
    """v15 A4/A6: compose a child effect through a relation. The transform is a property of the RELATION TYPE and
    most entries are 'does not transmit' -- a shortfall maps to a buyer's cost effect strongly, its volume effect
    strongly, and its delivery obligation not at all. Attenuation is per effect hop and there is no depth limit:
    decay is the limit, and it is a limit the world imposes rather than one we pick."""
    r = effects.compose(conn(), round_id, parent_effect_id, relation_id, effect_kind, holder_id, node, carrier,
                        falsifier, magnitude, magnitude_basis, due_at, ack_id, mechanism_ids, basis, write=write)
    return _ok(r, f"effect {r.get('effect_id')} at depth {r['depth']}, support {r['attenuated_support']} "
                  f"(transform {r['transform_weight']})")


@mcp.tool(name="nomad_effect_reroot", annotations=WR)
def nomad_effect_reroot(effect_id: str, carried_by: str, basis: str, evidence_id: Optional[str] = None) -> dict:
    """v15 A7: reset attenuation, ONLY where the effect is carried by its own document -- the buyer's own filing
    states the cost rise, not our inference that it must have risen. Re-rooting on inference is inference laundering
    and is refused, not discouraged."""
    r = effects.reroot(conn(), effect_id, carried_by, basis, evidence_id)
    return _ok(r, f"re-rooted as {r['effect_id']}; root_depth now {r['root_depth']}")


@mcp.tool(name="nomad_effect_eliminate", annotations=WR)
def nomad_effect_eliminate(effect_id: str, basis: str) -> dict:
    """v15 A5: anchors run PER EFFECT, not per holder. An effect dies where it has no path for that effect kind,
    where the receiving market has slack for that effect, where it is immaterial, or where it is already priced."""
    r = effects.eliminate(conn(), effect_id, basis)
    return _ok(r, f"effect {effect_id} eliminated")


@mcp.tool(name="nomad_effects", annotations=RO)
def nomad_effects(round_id: str, include_eliminated: bool = True) -> dict:
    """The round's effect DAG, with depth, attenuated support, root depth and elimination reasons."""
    rows = effects.list_effects(conn(), round_id, include_eliminated)
    return _ok({"round_id": round_id, "effects": rows, "n": len(rows)},
               f"{len(rows)} effect(s) over depths {sorted({e['depth'] for e in rows}) or [0]}")


@mcp.tool(name="nomad_effect_width", annotations=RO)
def nomad_effect_width(round_id: str) -> dict:
    """v15 A9: generation_width and elimination_rate per depth, plus root_depth (A7) and the frontier bound."""
    r = effects.width(conn(), round_id)
    return _ok(r, f"width {r['generation_width']}, elimination {r['elimination_rate']}, max depth {r['max_depth']}, "
                  f"{r['root_depth']['zero_rerooots']} effect(s) reach the event through zero re-roots")


@mcp.tool(name="nomad_net_direction", annotations=RO)
def nomad_net_direction(round_id: str, holder_id: str, window_start: str, window_end: str) -> dict:
    """v15 A3: net direction derived LATE, over a stated holding window, from magnitudes and dates already recorded.
    A holder whose effects net to zero over one window and to something over another is exactly what the leg model
    could not see."""
    r = effects.net_direction(conn(), round_id, holder_id, window_start, window_end)
    return _ok(r, f"net {r['net']} over {r['effects_in_window']} effect(s); opposed={r['opposed']}")


@mcp.tool(name="nomad_effect_migrate", annotations=WR)
def nomad_effect_migrate(round_id: Optional[str] = None, write: bool = True) -> dict:
    """v15 A2: every existing (holder, node) leg becomes one depth-1 `direction` effect, so rounds 1-14 stay readable
    and the wall map re-runs. The old columns stay for history."""
    r = effects.migrate_legs(conn(), round_id, write)
    return _ok(r, f"{r['effects_created']} effect(s) created over {r['rounds']} round(s)")


# ---- v15 §A4/§I: relations, transforms, node kinds -------------------------------------------------------------

@mcp.tool(name="nomad_relation_add", annotations=WR)
def nomad_relation_add(relation_type: str, basis: str, from_holder_id: Optional[str] = None,
                       to_holder_id: Optional[str] = None, node: Optional[str] = None,
                       source: Optional[str] = None, knowable_from: Optional[str] = None,
                       mode: Optional[str] = None) -> dict:
    """v15 I2: `transmits` is a property of the edge. True for physical, contractual and accounting relations; false
    for attribute edges, which are co-movement only. Traverse only transmitting edges; sum over all of them."""
    r = effects.relation_upsert(conn(), from_holder_id, to_holder_id, relation_type, basis, node, source,
                                knowable_from, mode)
    return _ok(r, f"relation {r['relation_id']} ({relation_type}, {r['mode']}, transmits={r['transmits']})")


@mcp.tool(name="nomad_transforms", annotations=RO)
def nomad_transforms(relation_type: Optional[str] = None) -> dict:
    """v15 A4: the transform table. Most entries are 'does not transmit', which makes it smaller and more honest than
    a sign matrix. An absent entry is zero: a transform must be stated to exist."""
    c = conn()
    sql = "SELECT * FROM transforms"
    args: list = []
    if relation_type:
        sql += " WHERE relation_type = ?"
        args.append(relation_type)
    rows = [dict(r) for r in c.execute(sql + " ORDER BY relation_type, from_kind, to_kind", args)]
    return _ok({"transforms": rows, "n": len(rows),
                "proposals": [r for r in rows if r["proposed_by"]]},
               f"{len(rows)} transform(s), {sum(1 for r in rows if r['proposed_by'])} stated by the operator")


@mcp.tool(name="nomad_transform_propose", annotations=WR)
def nomad_transform_propose(relation_type: str, from_kind: str, to_kind: str, weight: float, reason: str) -> dict:
    """v15 A4: state a transform where the table has none. Logged as a PROPOSAL, never merged into the seed."""
    r = effects.transform_propose(conn(), relation_type, from_kind, to_kind, weight, reason)
    return _ok(r, f"transform {r['key']} proposed at {weight} (logged as a proposal)")


@mcp.tool(name="nomad_node_kind", annotations=WR)
def nomad_node_kind(node: str, node_kind: str, attribute_kind: Optional[str] = None,
                    basis: Optional[str] = None) -> dict:
    """v15 I1: event node or attribute node. Listing venue, reporting currency, index membership, sector and size
    bucket are attribute nodes: they never propose an effect and are always summed in construction."""
    r = effects.node_upsert(conn(), node, node_kind, attribute_kind, basis)
    return _ok(r, f"node {node} is a {node_kind} node")


@mcp.tool(name="nomad_edge_traversal", annotations=RO)
def nomad_edge_traversal(relation_id: str) -> dict:
    """v15 I2: may this edge be traversed, or only summed? One place, so the distinction cannot be forgotten."""
    r = exposure.traverse_or_sum(conn(), relation_id)
    return _ok(r, f"{r['relation_type']}: traverse={r['may_traverse']}, summed=True")


# ---- v15 §B: the ACK graph ------------------------------------------------------------------------------------

@mcp.tool(name="nomad_ack_add", annotations=WR)
def nomad_ack_add(node: str, ack_kind: str, fact: str, source: str, due_at: Optional[str] = None,
                  obligation: Optional[str] = None, holder_id: Optional[str] = None, form: Optional[str] = None,
                  parent_ack_id: Optional[str] = None, round_id: Optional[str] = None,
                  participant_class: Optional[str] = None, attention: bool = False,
                  basis: Optional[str] = None) -> dict:
    """v15 B2/B3: an ACK node is a fact-with-a-date. `scheduled` carries a date. `forced` carries the OBLIGATION that
    generates it and NO date -- that is what makes it forced, and it is the only place a walk can find something a
    calendar-driven market has not."""
    r = acks.ack_add(conn(), node, ack_kind, fact, source, due_at, obligation, holder_id, form, parent_ack_id,
                     round_id, participant_class, attention, basis=basis)
    return _ok(r, f"ACK {r['ack_id']} ({ack_kind}) on {node}")


@mcp.tool(name="nomad_ack_graph", annotations=RO)
def nomad_ack_graph(node: str, round_id: Optional[str] = None, as_of: Optional[str] = None) -> dict:
    """v15 B4: the standing ACK graph on a node. Most of the graph is not about our event."""
    r = acks.graph_for_node(conn(), node, round_id, as_of)
    return _ok(r, f"{r['n']} ACK(s) on {node}: {len(r['scheduled'])} scheduled, {len(r['forced'])} forced, "
                  f"{len(r['undated_obligations'])} undated obligation(s)")


@mcp.tool(name="nomad_ack_build_standing", annotations=WR)
def nomad_ack_build_standing(node: str, holder_ids: Optional[list[str]] = None, as_of: Optional[str] = None) -> dict:
    """v15 B4: build the standing graph per node from the scheduled-facts store, BEFORE any event. This is the piece
    that has blocked catalyst since round 8 and is worth building even if the rest of v15 fails."""
    r = acks.build_standing(conn(), node, holder_ids, as_of)
    return _ok(r, f"{r['acks_created']} standing ACK(s) on {node} from {r['scheduled_facts_seen']} scheduled fact(s)")


@mcp.tool(name="nomad_ack_calendar", annotations=RO)
def nomad_ack_calendar(round_id: str, as_of: Optional[str] = None) -> dict:
    """v15 C2: every ACK on the round's nodes in date order. THE CALENDAR CHOOSES THE BRANCH, NOT THE OPERATOR."""
    r = acks.calendar(conn(), round_id, as_of)
    n = r["next_to_fire"]
    return _ok(r, f"{r['n_acks']} ACK(s); next to fire {n['fact'] if n else 'none dated'} "
                  f"{(n or {}).get('due_at') or ''}; {len(r['undated_forced'])} undated forced; "
                  f"{len(r['shared_acks'])} shared by more than one effect")


@mcp.tool(name="nomad_ack_fire", annotations=WR)
def nomad_ack_fire(ack_id: str, fired_at: str, delivered: bool, round_id: Optional[str] = None,
                   delivered_fact: Optional[str] = None, implied: Optional[str] = None,
                   successor_acks: Optional[list] = None, successor_query: Optional[str] = None,
                   opens_effect_ids: Optional[list[str]] = None, kills_effect_ids: Optional[list[str]] = None,
                   evidence_ids: Optional[list[str]] = None, segment_id: Optional[str] = None) -> dict:
    """v15 B5/C3/C6: a fired ACK must deliver a fact. 'The date passed and nothing was said' is an ABSENCE FACT: it
    prunes, it does not advance. Successors are named AT FIRING, never afterwards, or the graph grows to fit whatever
    happened. Direction comes from the GAP between what was implied and what was delivered."""
    r = acks.fire(conn(), ack_id, fired_at, delivered, round_id, delivered_fact, implied, successor_acks,
                  successor_query, opens_effect_ids, kills_effect_ids, evidence_ids, segment_id)
    return _ok(r, f"ACK {ack_id} fired {fired_at}: "
                  + ("delivered nothing, branch terminates" if r["prunes"]
                     else f"delivered; {len(r['successor_ack_ids'])} successor(s) named at firing"))


# ---- v15 §C/§E: the walk --------------------------------------------------------------------------------------

@mcp.tool(name="nomad_segment_lock", annotations=WR)
def nomad_segment_lock(round_id: str, claim: str, effect_ids: list[str], next_ack_ids: Optional[list[str]] = None,
                       opened_by_ack_id: Optional[str] = None, opened_by_firing_id: Optional[str] = None,
                       locked_at: Optional[str] = None) -> dict:
    """v15 C5: lock a segment. What is locked is a claim about what survives UNTIL THE NEXT ACK. Nothing earlier is
    rewritten; the set grows a generation, and scoring is per segment."""
    r = walk.lock_segment(conn(), round_id, claim, effect_ids, next_ack_ids, opened_by_ack_id, opened_by_firing_id,
                          locked_at)
    return _ok(r, f"segment {r['idx']} locked with {r['n_effects']} effect(s)")


@mcp.tool(name="nomad_walk_advance", annotations=RO)
def nomad_walk_advance(round_id: str, ack_id: str, as_of: Optional[str] = None) -> dict:
    """v15 C2/C4: advance the walk on a FIRED ACK. Refused otherwise -- the calendar chooses the branch, and picking
    one is selection at generation two, the largest fitting risk in this version. Depth-first."""
    r = walk.advance(conn(), round_id, ack_id, as_of)
    return _ok(r, f"advancing on {ack_id}: {len(r['successor_ack_ids'])} successor(s), "
                  f"{len(r['unfired_earlier_acks'])} earlier ACK(s) still open")


@mcp.tool(name="nomad_convergence", annotations=RO)
def nomad_convergence(round_id: str, as_of: Optional[str] = None) -> dict:
    """v15 E1-E3: how far each branch still differs from the price-implied path. Convergence to price is residual
    recovery. WATCH divergence_held: a frontier with zero divergence held has zero edge and reads as failure."""
    r = walk.convergence(conn(), round_id, as_of)
    return _ok(r, f"divergence_held {r['divergence_held']}; {len(r['converged'])} converged, "
                  f"{len(r['unreadable'])} unreadable")


@mcp.tool(name="nomad_prune", annotations=WR)
def nomad_prune(round_id: str, effect_ids: list[str], as_of: Optional[str] = None) -> dict:
    """v15 E3: prune CONVERGED branches only. A divergent branch offered for pruning is refused by name: the
    divergent branches are the position."""
    r = walk.prune(conn(), round_id, effect_ids, as_of)
    return _ok(r, f"{len(r['pruned'])} converged branch(es) pruned; divergence_held {r['divergence_held']}")


@mcp.tool(name="nomad_walk_report", annotations=RO)
def nomad_walk_report(round_id: str, as_of: Optional[str] = None) -> dict:
    """v15: everything the walk must show per round -- segments, firings, width and elimination by depth, root_depth,
    divergence_held, both support rankings, bridge paths and contradictions."""
    r = walk.walk_report(conn(), round_id, as_of)
    return _ok(r, f"generation {r['generation']}, width {r['generation_width']}, divergence_held "
                  f"{r['divergence_held']}, bridges {r['bridge_paths']}, contradictions {r['contradictions']}")


# ---- v15 §D: contradictions ------------------------------------------------------------------------------------

@mcp.tool(name="nomad_contradictions", annotations=RO)
def nomad_contradictions(round_id: str) -> dict:
    """v15 D1/D2: two effect paths contradict when they point at the same ACK node and imply opposite deliveries.
    Computable, not declared. Each generates hypotheses about EDGES, testable at that ACK because the delivery
    discriminates -- the first mechanism producing relation-level evidence as a byproduct of walking."""
    r = contradiction.detect(conn(), round_id)
    return _ok(r, f"{r['n']} contradiction(s) on round {round_id}")


@mcp.tool(name="nomad_contradiction_record", annotations=WR)
def nomad_contradiction_record(round_id: str, ack_id: str, kind: str, path_a: list[str], path_b: list[str],
                               implies_a: str, implies_b: str, common_set: Optional[list[str]] = None,
                               gap: Optional[dict] = None, edge_hypotheses: Optional[list] = None,
                               exit_ack_id: Optional[str] = None, dated_at: Optional[str] = None) -> dict:
    """v15 D: write a contradiction to the ledger with its common set, gap and exit ACK."""
    r = contradiction.record(conn(), round_id, ack_id, kind, path_a, path_b, implies_a, implies_b, common_set, gap,
                             edge_hypotheses, exit_ack_id, dated_at)
    return _ok(r, f"contradiction {r['contradiction_id']} dated {r['dated_at']}")


@mcp.tool(name="nomad_common_set_anchors", annotations=RO)
def nomad_common_set_anchors(round_id: str) -> dict:
    """v15 D4: the shared ancestry both branches needed. Both required it, so it is anchor-grade and feeds the
    eliminators."""
    r = contradiction.common_set_anchors(conn(), round_id)
    return _ok(r, f"{r['n']} anchor-grade edge(s) from the common sets")


@mcp.tool(name="nomad_exit_ack", annotations=RO)
def nomad_exit_ack(round_id: str, structural_ack_id: str) -> dict:
    """v15 D6: exit is the FIRST ATTENTION ACK AFTER the structural ACK. A structural ACK alone does not close a
    divergence -- a fact delivered to a channel nobody who marks the security reads changes nothing."""
    r = contradiction.exit_ack(conn(), round_id, structural_ack_id)
    return _ok(r, "no attention ACK after it: the divergence stays open" if r["open"]
               else f"exit at {r['exit_ack']['due_at']}, latency {r['latency_days']} day(s)")


# ---- v15 §F/§G: support, the implicit position, bridges --------------------------------------------------------

@mcp.tool(name="nomad_effect_support", annotations=RO)
def nomad_effect_support(round_id: str, holder_id: Optional[str] = None,
                         effect_kind: Optional[str] = None) -> dict:
    """v15 F3/F4/F7: support with and without the independence discount, BOTH rankings written every round. If they
    agree, the discount is doing nothing and the paths were never independent."""
    r = effects.support(conn(), round_id, holder_id, effect_kind)
    return _ok(r, f"{len(r['rows'])} effect group(s); rankings agree: {r['rankings_agree']}")


@mcp.tool(name="nomad_implicit_position", annotations=RO)
def nomad_implicit_position(round_id: str, as_of: Optional[str] = None) -> dict:
    """v15 F6: the implicit position needs support AND stake. The most cross-supported effect may be robust because
    it is INERT -- if nothing touches a holder, every path trivially implies nothing happens here."""
    r = effects.implicit_position(conn(), round_id, as_of)
    return _ok(r, f"{len(r['position'])} implied position(s), {len(r['inert'])} inert, "
                  f"{len(r['below_support'])} below the support threshold")


@mcp.tool(name="nomad_bridge_paths", annotations=RO)
def nomad_bridge_paths(round_id: str) -> dict:
    """v15 G: an effect path IS a position when some node in it clears expression and some ancestor has stake. There
    is no bridge object. Empty is a valid and reportable answer -- if it stays empty the anti-correlation is a law."""
    r = effects.bridge_paths(conn(), round_id)
    return _ok(r, f"{r['n']} bridge path(s), {r['n_near_misses']} near miss(es)")


# ---- v15 §H: basket totality and synthetic exposure ------------------------------------------------------------

@mcp.tool(name="nomad_synthetic_exposure_declare", annotations=WR)
def nomad_synthetic_exposure_declare(round_id: str, declared: list, intended_residual: float, basis: str,
                                     holder_ids: Optional[list[str]] = None,
                                     basket_key: Optional[str] = None) -> dict:
    """v15 H3/H5: declare the exposures the basket carries that nobody chose, AT CONSTRUCTION. Each row is
    {attribute_node, net_sign, magnitude}. basket_stake = intended residual / declared exposure; below 1.0 the basket
    is a position on something nobody chose. If it cannot be named, the construction is not understood well enough
    to hold."""
    r = exposure.declare(conn(), round_id, declared, intended_residual, basis, holder_ids, basket_key)
    return _ok(r, f"basket_stake {r['basket_stake']} (floor {r['basket_stake_floor']}), attribute coverage "
                  f"{r['attribute_coverage']}" + (" -- BELOW FLOOR" if r["below_floor"] else ""))


@mcp.tool(name="nomad_attribute_coverage", annotations=RO)
def nomad_attribute_coverage(holder_ids: list[str]) -> dict:
    """v15 I4: coverage grows by play. Reported next to every declared synthetic exposure, because until the data
    layer exists every basket-level number carries the floor caveat."""
    r = exposure.attribute_coverage(conn(), holder_ids)
    return _ok(r, f"attribute coverage {r['coverage']} over {r['holders']} holder(s)")


def run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765) -> None:
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="streamable-http")
