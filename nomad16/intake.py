"""Intake (§15, Event Requirements v3): enumeration, dry-run, admission, reveal; and the
operator manifest (§28) and tide declaration.

Feed ``nrc_en_power_reactor``: the NRC daily Event Notification Reports, power-reactor
events only, in date order. Q9 passes when the harness enumerated a fixed feed over a
fixed window, every earlier item carries a written rejection, and the first pass is taken.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

from . import config
from .db import DB, ROOT, Refused, now_iso
from .pit import NRC_EN, parse_en
from .rounds import get_round, set_meta, set_state, state
from .seed import library_as_of
from .util import curl, day, ts

CACHE = ROOT / "data" / "cache" / "nrc_en"
GUARD_LOG = ROOT / "firewall" / "guard16_log.jsonl"


def git_state() -> tuple[str | None, list[str]]:
    """(HEAD commit, uncommitted paths under the code the operator clones)."""
    import subprocess
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        st = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "nomad16", "config", "firewall",
                             ".claude"], capture_output=True, text=True).stdout.splitlines()
    except OSError:
        return None, []
    return head or None, [x[3:] for x in st if not x.endswith("guard16_log.jsonl")]


def _page(d: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{d}.html"
    if p.exists():
        return p.read_text()
    try:
        t = curl(NRC_EN.format(y=d[:4], ymd=d.replace("-", "")))
    except Refused:
        return None
    p.write_text(t)
    return t


def _mdy(s: str | None) -> str | None:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else None


def power_events(d_from: str, d_to: str) -> list[dict]:
    out, seen = [], set()
    d = ts(d_from)
    while d <= ts(d_to):
        ds = d.strftime("%Y-%m-%d")
        page = _page(ds)
        if page:
            for e in parse_en(page):
                if e.get("category") != "Power Reactor" or e["event_number"] in seen:
                    continue
                seen.add(e["event_number"])
                f = e["fields"]
                out.append({"report_date": ds, "event_number": e["event_number"], "facility": f.get("Facility"),
                            "unit": f.get("Unit"), "event_date": _mdy(f.get("Event Date")),
                            "notification_date": _mdy(f.get("Notification Date")),
                            "section": f.get("10 CFR Section"), "title": e["title"],
                            "emergency_class": f.get("Emergency Class"), "units": e.get("units"),
                            "text": e["text"]})
        d += _dt.timedelta(days=1)
    return out


DISRUPTIVE = re.compile(r"SCRAM|REACTOR TRIP|MANUAL REACTOR|AUTOMATIC REACTOR|SHUTDOWN|SHUT DOWN", re.I)


def disruptive(e: dict) -> bool:
    """A power-reactor event that took output: a scram code, power below its initial level,
    or a title naming a trip, scram, shutdown, loss or fire."""
    units = e.get("units") or []
    for u in units:
        if u.get("SCRAM Code") not in (None, "", "N"):
            return True
        try:
            if int(u.get("Current PWR") or 0) < int(u.get("Initial PWR") or 0):
                return True
        except ValueError:
            pass
    if units:
        return False  # the unit table is authoritative where the report carries one
    return bool(DISRUPTIVE.search(e.get("title") or ""))


def enumerate_feed(db: DB, d_from: str, d_to: str, operator_cutoff: str, stop_at_first: bool = True) -> dict:
    """Enumerate the feed in date order and dry-run the harness-computable questions."""
    look = (ts(d_from) - _dt.timedelta(days=365)).strftime("%Y-%m-%d")
    hist = power_events(look, (ts(d_from) - _dt.timedelta(days=1)).strftime("%Y-%m-%d"))
    n_runs = len(db.rows("enumeration_runs", "from_date=? AND to_date=?", (d_from, d_to)))
    run_id = f"ENUM-{d_from}-{d_to}-r{n_runs + 1}"
    items = []
    d = ts(d_from)
    while d <= ts(d_to):
        ds = d.strftime("%Y-%m-%d")
        day_items = [e for e in power_events(ds, ds)
                     if e["event_number"] not in {h["event_number"] for h in hist}]
        for e in day_items:
            ed = e["event_date"] or e["report_date"]
            prior = [h for h in hist if h["facility"] == e["facility"]]
            p30 = [h for h in prior if 0 <= (ts(ed) - ts(h["report_date"])).days <= 30]
            p90 = [h for h in prior if 0 <= (ts(ed) - ts(h["report_date"])).days <= 90 and disruptive(h)]
            p365 = [h for h in prior if 0 <= (ts(ed) - ts(h["report_date"])).days <= 365 and disruptive(h)]
            q = {"Q1a": "fail" if p30 else "pass", "Q1a_basis": [f"{h['event_number']} {h['report_date']} {h['title']}" for h in p30],
                 "Q1b": "fail" if (p90 or len(p365) >= 3) else "pass",
                 "Q1b_basis": [f"{h['event_number']} {h['report_date']} {h['title']}" for h in p365],
                 "Q2": "pass" if ts(ed) > ts(operator_cutoff) else "fail",
                 "disruptive": disruptive(e), "units": e.get("units"),
                 "Q5_hint": "underread (regulator feed / trade press)", "Q7": "pass (carriers registered for power_reactor)",
                 "event_date": ed}
            items.append((e, q))
            hist.append(e)
        if stop_at_first and any(disruptive(e) and q["Q2"] == "pass" for e, q in items):
            d_to_eff = ds
            break
        d += _dt.timedelta(days=1)
    else:
        d_to_eff = d_to
    db.append("enumeration_runs", run_id=run_id, feed_set="nrc_en_power_reactor", from_date=d_from, to_date=d_to,
              source_mode="manual", complete=True,
              truncation_reason=(f"stopped reading at {d_to_eff}: first candidate the harness proposes to pass"
                                 if stop_at_first else None), n_items=len(items))
    out = []
    for n, (e, q) in enumerate(items, 1):
        cid = f"{run_id}:{n:03d}"
        db.append("intake_candidates", cand_id=cid, run_id=run_id, item_date=e["report_date"],
                  source_record={k: e[k] for k in e if k != "text"} | {"text": e["text"][:4000]},
                  title=f"{e['facility']}: {e['title']}", q_results=q, decision="pending", reason=None, failing_q=None)
        out.append({"cand_id": cid, "report_date": e["report_date"], "event_date": q["event_date"],
                    "facility": e["facility"], "title": e["title"], "section": e["section"],
                    "Q1a": q["Q1a"], "Q1b": q["Q1b"], "Q2": q["Q2"]})
    return {"run_id": run_id, "read_through": d_to_eff, "candidates": out}


def intake_decide(db: DB, cand_id: str, decision: str, reason: str, failing_q: str | None = None) -> dict:
    c = db.one("intake_candidates", "cand_id=?", (cand_id,))
    if c is None:
        raise Refused(f"no candidate {cand_id}")
    if decision not in {"reject", "confirm"}:
        raise Refused("decision is reject or confirm")
    if decision == "reject" and not (reason and failing_q):
        raise Refused("a rejection names the failing question and its reason")
    return db.append("intake_candidates", cand_id=cand_id, run_id=c["run_id"], item_date=c["item_date"],
                     source_record=c["source_record"], title=c["title"], q_results=c["q_results"],
                     decision=decision, reason=reason, failing_q=failing_q)


def submit_event(db: DB, cand_id: str, round_id: str, event_line: str, node: str, node_type: str,
                 stratum: str, knowable_from: str, confirmed_by: str, size_band: str,
                 operator_cutoff: str, cutoff_basis: str, human_q: dict, logic_version: str = "v16") -> dict:
    """Admission: the human has confirmed Q3, Q4, Q6, Q8 and picked the size band.

    ``logic_version`` is ``v16`` (default) or ``v17``. A v17 round writes its admission record as a document
    entity (so its first ``stated`` statement has something to cite) and refuses typed ``knowable_from`` dates."""
    if logic_version not in {"v16", "v17"}:
        raise Refused("logic_version is v16 or v17")
    if logic_version == "v17" and db.get("entity_kinds", "organisation") is None:
        raise Refused("a v17 round needs the v17 registry: run seed_v17 (and migrate_v17 on an old store) first")
    from .positions import node_upsert
    op_model = config.operator_model()
    head, dirty = git_state()
    if dirty and not os.environ.get("NOMAD_ALLOW_DIRTY"):
        raise Refused("admit a round on the exact commit the operator will clone: nomad16/, config/ or "
                      f"firewall/ has uncommitted changes ({dirty[:5]}). Commit and push them, then admit "
                      "(R16-001 was admitted and played on different harness versions)")
    c = db.one("intake_candidates", "cand_id=?", (cand_id,))
    if c is None or c["decision"] != "confirm":
        raise Refused("the candidate must be confirmed by the human first (intake_decide confirm)")
    for q in ("Q3", "Q4", "Q6", "Q8"):
        if human_q.get(q) != "pass":
            raise Refused(f"{q} must be confirmed pass by the human")
    if size_band not in {"underread", "headline"}:
        raise Refused("size band is underread or headline (trivia is a rejection)")
    if db.one("rounds", "round_id=?", (round_id,)):
        raise Refused(f"round {round_id} exists")
    q = dict(c["q_results"])
    q.update(human_q)
    q["Q5"] = size_band
    # Q9: fixed feed, fixed window, every earlier item rejected in writing, first pass taken
    run = c["run_id"]
    latest = {}
    for r in db.rows("intake_candidates", "run_id=?", (run,)):
        latest[r["cand_id"]] = r
    earlier = [r for k, r in latest.items() if k < cand_id]
    q["Q9"] = "pass" if all(r["decision"] == "reject" and r["reason"] for r in earlier) else "fail"
    tags = []
    if q["Q1a"] == "pass" and q["Q1b"] == "pass" and size_band == "underread":
        tags.append("lag_test")
    if size_band == "headline":
        tags.append("headline")
    if q["Q1b"] == "fail":
        tags.append("weather")
    if q["Q1a"] == "fail" and q["Q1b"] == "pass":
        tags.append("late_headline")
    reasons = []
    if q["Q2"] != "pass":
        reasons.append("Q2 fail (event not after the operator cutoff)")
    prov = config.provisional_keys()
    if prov:
        reasons.append(f"{len(prov)} appetite values are provisional_unratified (user instruction 2026-09-29)")
    if q["Q9"] != "pass":
        reasons.append("Q9 fail")
    rclass = "learning" if reasons else "clean"
    if rclass == "learning":
        tags.append("learning")
    node_upsert(db, node, node_type, description=event_line, round_id=round_id)
    db.append("rounds", round_id=round_id, event_line=event_line, event_date=q["event_date"], event_time=None,
              node=node, node_type=node_type, stratum=stratum, feed_set="nrc_en_power_reactor",
              intake_mode="strict_v3", round_class=rclass, live=False, operator_model=op_model,
              operator_cutoff=operator_cutoff, operator_runtime=None, harness_version=config.harness_version(),
              logic_version=logic_version, config_hash=config.config_hash(), presort_active=False,
              domain_pref="not applied (single passing candidate)", candidate_id=cand_id, q_results=q)
    for t in tags:
        db.append("round_tags", round_id=round_id, tag=t, basis="Event Requirements v3 tag rules")
    set_meta(db, round_id, "knowable_from", knowable_from)
    set_meta(db, round_id, "class_reasons", reasons)
    set_meta(db, round_id, "cutoff_basis", cutoff_basis)
    set_meta(db, round_id, "confirmed_by", confirmed_by)
    set_meta(db, round_id, "admitted_commit", head)
    db.append("segments", round_id=round_id, idx=0, clock=q["event_date"], opened_by_ack_id=None,
              opened_by_firing_id=None, locked_at=None, lock_hash=None, manifest_id=None, wall_clock=None)
    set_state(db, round_id, "admitted", f"admitted by {confirmed_by}; class {rclass}")
    out = {"round_id": round_id, "class": rclass, "class_reasons": reasons, "tags": tags, "q": q,
           "logic_version": logic_version}
    if logic_version == "v17":
        from .documents import admission_record
        out["admission_record"] = admission_record(db, round_id)["key"]
    return out


def reveal_event(db: DB, round_id: str) -> dict:
    """Step 1 of §16: write the reveal and open the pre-lock phase."""
    rnd = get_round(db, round_id)
    if state(db, round_id) != "admitted":
        raise Refused("reveal follows admission")
    clock = rnd["event_date"]
    lib = library_as_of(db, clock)
    node = db.get("nodes", rnd["node"])
    temps = [t for t in db.rows("obligation_templates") if rnd["node_type"] in (t["node_types"] or [])]
    carriers = [c for c in db.rows("carriers") if rnd["node_type"] in c["node_types"] or "*" in c["node_types"]]
    rev = {
        "round_id": round_id, "event_line": rnd["event_line"], "event_date": clock, "node": rnd["node"],
        "node_type": rnd["node_type"], "stratum": rnd["stratum"], "class": rnd["round_class"],
        "tags": [t["tag"] for t in db.rows("round_tags", "round_id=?", (round_id,))],
        "holders_and_positions": "the names book is empty in this fresh build: author holders and positions "
                                 "per asset from documents knowable by the clock (pit_fetch, alt_fetch)",
        "node_facts": [], "scheduled_facts": "none registered; add scheduled ACKs from the calendar if any",
        "library_as_of": lib["rules"],
        "obligation_templates": [{k: t[k] for k in ("key", "roles", "conditions", "forces", "window_rule", "forbids")} for t in temps],
        "outcome_vocabs": {t["forces"]: (db.get("outcome_vocabs", t["forces"]) or {}).get("outcomes") for t in temps},
        "q1a_window_search": rnd["q_results"].get("Q1a_basis"), "q1b_registry": rnd["q_results"].get("Q1b_basis"),
        "carrier_registry": [{k: c[k] for k in ("key", "kind", "fetch_path", "read_in_full_rule")} for c in carriers],
        "instrument_map": "empty: add instruments (instrument_add) for holders in reach, listed before the clock",
        "story_registry": [s["key"] for s in db.rows("stories")],
        "tide_registry": [{"id": t["key"], "label": t["label"], "proxy": t["proxy"]} for t in db.rows("tides")],
        "point_in_time_fetcher": "python -m nomad16 pit_fetch / alt_fetch; nothing after the clock is readable",
    }
    d = ROOT / "rounds" / round_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "reveal.json").write_text(json.dumps(rev, indent=1, default=str) + "\n")
    set_state(db, round_id, "pre_lock", "reveal issued")
    set_meta(db, round_id, "revealed_at", now_iso())
    return {"reveal": str((d / "reveal.json").relative_to(ROOT)), "event_line": rnd["event_line"],
            "event_date": clock, "state": "pre_lock"}


def operator_manifest(db: DB, round_id: str, operator_model: str, operator_runtime: str, operator_cutoff: str,
                      cutoff_basis: str, session_id: str, cold: bool) -> dict:
    """§28. hook_verified is computed from the guard's own log, never asserted: a denied
    WebSearch or WebFetch must be on record after the reveal."""
    rnd = get_round(db, round_id)
    if state(db, round_id) != "pre_lock":
        raise Refused("the manifest is written pre-lock, after reveal")
    revealed = None
    for m in db.rows("round_meta", "round_id=? AND field='revealed_at'", (round_id,)):
        revealed = m["value"]
    denials = []
    if GUARD_LOG.exists():
        for line in GUARD_LOG.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("tool") in {"WebSearch", "WebFetch"} and not r.get("permitted") and r.get("at", "") >= (revealed or ""):
                denials.append(r)
    verified = bool(denials)
    if ts(operator_cutoff) >= ts(rnd["event_date"]):
        set_meta(db, round_id, "q2_operator_cutoff_note", "operator cutoff is not before the event: Q2 fails, learning")
    mine, admitted = config.harness_version(), rnd["harness_version"]
    cmine, cadm = config.config_hash(), rnd["config_hash"]
    set_meta(db, round_id, "operator_harness_version", mine)
    set_meta(db, round_id, "operator_config_hash", cmine)
    set_meta(db, round_id, "harness_match", bool(mine == admitted and cmine == cadm))
    row = db.append("operator_manifests", round_id=round_id, operator_model=operator_model,
                    operator_runtime=operator_runtime, operator_cutoff=operator_cutoff, cutoff_basis=cutoff_basis,
                    session_id=session_id, hook_verified=verified,
                    hook_evidence=denials[-1] if denials else "no denied WebSearch/WebFetch on the guard log since reveal",
                    cold=bool(cold))
    match = mine == admitted and cmine == cadm
    return {"hook_verified": verified, "harness_match": match,
            "harness": {"admitted": admitted, "operator": mine, "config_admitted": str(cadm)[:16],
                        "config_operator": cmine[:16]},
            "manifest": {k: row[k] for k in ("operator_model", "operator_runtime",
                                                                      "operator_cutoff", "session_id", "cold")},
            "next": (None if verified and match else
                     ("attempt a WebSearch now (it must be refused), then write the manifest again" if not verified else
                      "the harness or config in this clone differs from the one the round was admitted on; "
                      "the round can't lock. Ask the builder to re-admit on the commit you cloned"))}


def tide_declare(db: DB, round_id: str, tide_id: str, basis: str) -> dict:
    from .rounds import require_pre_lock
    require_pre_lock(db, round_id)
    if db.get("tides", tide_id) is None:
        raise Refused(f"no tide {tide_id}; add one with tide_add (label and proxy)")
    set_meta(db, round_id, "tide_id", tide_id)
    set_meta(db, round_id, "tide_basis", basis)
    return {"round_id": round_id, "tide_id": tide_id}


def tide_add(db: DB, tide_id: str, label: str, proxy: str) -> dict:
    return db.upsert("tides", tide_id, label=label, declared_by="operator", from_date=None, to_date=None,
                     retro_declared=False, proxy=proxy)
