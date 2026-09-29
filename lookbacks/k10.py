"""K10 look-back over the v15 ledger, per K10_prereg.md. Read-only.

usage: python lookbacks/k10.py v15/nomad_harness.db TEMPLATES.json NOTICES.json OUT.json
       python lookbacks/k10.py --selftest

Derivation follows spec v16 section 22.2 on the v15 schema. The template file is the cold author's, frozen
before this ran; the notices file is the enumerators', frozen before the template file was opened.
"""
import collections, datetime as dt, itertools, json, sqlite3, sys

ROWS = (8, 9, 10, 11, 13, 15, 16, 17)
X10 = 0.5                    # config/appetite.json, provisional_unratified
BINDINGS_MAX = 500           # DERIVATION_BINDINGS_MAX
DUE_AT_MAX_DAYS = 90
# variant: (knowable_from required, stated confidence required, touched_set rows count as positions)
VARIANTS = {
    "guarded": (True, True, False),
    "S1_no_knowable_from": (False, True, False),
    "S2_inferred_accepted": (True, False, False),
    "S3_touched_set_rows": (True, True, True),
    "upper_bound": (False, False, True),
}
RANK = {"forced": 0, "switch": 1, "none": 2}


def connect(path):
    c = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    c.row_factory = sqlite3.Row
    return c


def load_rounds(c):
    out = []
    q = "SELECT r.id, r.round_class, e.event_date, e.node FROM rounds r JOIN events e ON e.id=r.event_id ORDER BY r.rowid"
    for n, r in enumerate(c.execute(q), 1):
        lock = None
        for t in c.execute("SELECT to_state, recorded_at FROM round_transitions WHERE round_id=? ORDER BY rowid", (r["id"],)):
            if t["to_state"] == "locked":
                lock = t["recorded_at"]
                break
        ts = [dict(t) for t in c.execute("SELECT * FROM touched_set WHERE round_id=?", (r["id"],))]
        nodes = {r["node"]} | {t["node"] for t in ts}
        out.append({"row": n, "id": r["id"], "class": r["round_class"], "event_date": r["event_date"], "event_node": r["node"],
                    "lock": lock, "touched": ts, "nodes": {x for x in nodes if x}})
    return out


def build_store(c, rnd, variant):
    kf_req, stated_only, touched = VARIANTS[variant]
    rows = []
    for p in c.execute("SELECT * FROM positions ORDER BY rowid"):
        if not p["recorded_at"] < rnd["lock"]:
            continue
        if kf_req and not (p["knowable_from"] and p["knowable_from"][:10] <= rnd["event_date"]):
            continue
        if stated_only and p["confidence"] != "stated":
            continue
        rows.append(dict(p))
    sup = {r["supersedes"] for r in rows if r["supersedes"]}
    rows = [r for r in rows if r["id"] not in sup]
    idx = collections.defaultdict(list)
    for r in rows:
        idx[(r["holder_id"], r["node"], r["attribute"])].append((r["value"], r["unit"], r["id"]))
    if touched:
        for t in rnd["touched"]:
            if t.get("substitutability"):
                idx[(t["holder_id"], t["node"], "substitutability")].append((t["substitutability"], None, "ts:" + t["id"]))
            if t.get("duration_factor"):
                idx[(t["holder_id"], t["node"], "duration_factor")].append((t["duration_factor"], None, "ts:" + t["id"]))
    return idx, len(rows)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _test(op, have, want):
    """have is a stored value (str) or a bound value; True, False, or None when it can't be tested."""
    if op in ("ge", "gt", "le", "lt"):
        a, b = _num(have), _num(want)
        if a is None or b is None:
            return None
        return {"ge": a >= b, "gt": a > b, "le": a <= b, "lt": a < b}[op]
    if op in ("eq", "ne"):
        a, b = _num(have), _num(want)
        same = (a == b) if (a is not None and b is not None) else str(have).strip().lower() == str(want).strip().lower()
        return same if op == "eq" else not same
    if op == "in":
        opts = [str(w).strip().lower() for w in want]
        return str(have).strip().lower() in opts
    return None


def _unit_ok(attr, unit):
    """A numeric row can test a numeric attribute only if its unit is compatible with the registry's."""
    want = (attr or {}).get("unit")
    if not want or not unit:
        return True
    a, b = str(want).lower(), str(unit).lower()
    return a in b or b in a


def eval_condition(cond, binding, idx, node, bounds, attrs, stats):
    if "bound" in cond:
        b = bounds.get(cond["bound"])
        if b is None:
            return "unknown"
        r = _test(cond["op"], b["value"], cond["value"])
        return "unknown" if r is None else ("true" if r else "false")
    holder = binding.get(cond["role"])
    rows = idx.get((holder, node, cond["attribute"]), []) if holder else []
    if not rows:
        return "unknown"
    a = attrs.get(cond["attribute"], {})
    states = set()
    for value, unit, _rid in rows:
        if a.get("type") == "numeric" and not _unit_ok(a, unit):
            stats["unit_mismatch"] += 1
            states.add("unknown")
            continue
        r = _test(cond["op"], value, cond["value"])
        states.add("unknown" if r is None else ("true" if r else "false"))
    return next(iter(states)) if len(states) == 1 else "unknown"


def derive_notice(n, rnd, idx, templates, bounds, attrs, holders, stats):
    """Best result of every template of the notice's kind, and the audit trail."""
    node = n["node"]
    ev = dt.date.fromisoformat(rnd["event_date"])
    audit, best = [], None
    same_kind = [t for t in templates if t["notice_kind"] == n["kind"]]
    if not same_kind:
        return {"status": "no_template_kind", "best": None, "audit": []}
    issuer_id, issuer_class = n.get("issuer_holder_id"), n.get("issuer_class")
    holder_ids_on_node = {h for (h, nd, _a) in idx if nd == node}
    touched_ids = {t["holder_id"] for t in rnd["touched"] if t["holder_id"]}
    any_issuer_bound = False
    for t in same_kind:
        roles = t["roles"]
        ir = roles[t["issuer_role"]]
        kinds = set(ir.get("holder_kinds") or [])
        if issuer_id:
            h = holders.get(issuer_id)
            ok = h is not None and (not kinds or h["kind"] in kinds) and (ir.get("binds_without_position") or issuer_id in holder_ids_on_node)
            issuer_binding = issuer_id if ok else None
        else:
            ok = bool(ir.get("binds_without_position")) and (not kinds or issuer_class in kinds)
            issuer_binding = "<unnamed:%s>" % issuer_class if ok else None
        if not ok:
            audit.append({"template": t["template_id"], "result": "issuer_unbound"})
            continue
        any_issuer_bound = True
        cands = {}
        for rname, r in roles.items():
            if rname == t["issuer_role"]:
                cands[rname] = [issuer_binding]
                continue
            k = set(r.get("holder_kinds") or [])
            pool = touched_ids if r.get("binds_without_position") else holder_ids_on_node
            cands[rname] = sorted(h for h in pool if h in holders and (not k or holders[h]["kind"] in k))
        size = 1
        for v in cands.values():
            size *= len(v)
        if size == 0:
            audit.append({"template": t["template_id"], "result": "no_binding", "empty_roles": [r for r, v in cands.items() if not v]})
            continue
        if size > BINDINGS_MAX:
            audit.append({"template": t["template_id"], "result": "bindings_exceeded", "size": size})
            stats["bindings_exceeded"] += 1
            continue
        window_days = (t.get("window_rule") or {}).get("days")
        window_days = window_days if isinstance(window_days, int) else DUE_AT_MAX_DAYS
        in_window = dt.date.fromisoformat(n["date_arrived"]) <= ev + dt.timedelta(days=window_days)
        names = list(cands)
        tbest = None
        for combo in itertools.product(*[cands[r] for r in names]):
            binding = dict(zip(names, combo))
            states = {c["id"]: eval_condition(c, binding, idx, node, bounds, attrs, stats) for c in t["conditions"]}
            vals = list(states.values())
            result = "none" if "false" in vals else ("forced" if all(v == "true" for v in vals) else "switch")
            unknown = [c for c in t["conditions"] if states[c["id"]] == "unknown"]
            key = (RANK[result], len(unknown))
            if tbest is None or key < tbest[0]:
                tbest = (key, {"template": t["template_id"], "result": result, "binding": binding, "states": states,
                               "n_unknown": len(unknown),
                               "unknown": [c.get("attribute") and f'{c["role"]}.{c["attribute"]}' or f'bound:{c["bound"]}' for c in unknown],
                               "in_window": in_window, "window_days": window_days})
        audit.append(tbest[1])
        if best is None or (RANK[tbest[1]["result"]], tbest[1]["n_unknown"]) < (RANK[best["result"]], best["n_unknown"]):
            best = tbest[1]
    tiers = {"forced": False, "switch_le1": False, "switch_any": False}
    for a in audit:
        if a.get("result") in RANK and a.get("in_window"):
            if a["result"] == "forced":
                tiers["forced"] = True
            if a["result"] in ("forced", "switch") and a["n_unknown"] <= 1:
                tiers["switch_le1"] = True
            if a["result"] in ("forced", "switch"):
                tiers["switch_any"] = True
    status = "evaluated" if any_issuer_bound else "issuer_unbound"
    return {"status": status, "tiers": tiers, "best": best, "audit": audit}


def resolve_coverage(c, ids):
    found, cov = [], []
    for i in ids or []:
        rows = list(c.execute("SELECT id, source_coverage FROM resolutions WHERE id=? OR id LIKE ?", (i, i + "%")))
        if len(rows) == 1:
            found.append(rows[0]["id"])
            cov.append(rows[0]["source_coverage"])
    return found, cov


def run(db, templates_path, notices_path):
    c = connect(db)
    tf = json.load(open(templates_path))
    templates = tf["templates"]
    bounds = {b["bound_id"]: b for b in tf.get("bounds", [])}
    attrs = {a["name"]: a for a in tf.get("attributes", [])}
    holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
    rounds = {r["row"]: r for r in load_rounds(c)}
    nf = json.load(open(notices_path))
    notices = [dict(n, row=row["row"]) for row in nf["rows"] for n in row["notices"]]
    res = {"variants": {}, "notices": [], "store_rows": {}}
    stats = collections.Counter()
    for n in notices:
        rnd = rounds[n["row"]]
        ids, cov = resolve_coverage(c, n.get("resolution_ids"))
        n["read_in_full"] = any(x == "adequate" for x in cov)
        n["resolution_coverage"] = cov
        n["unlinked_resolution_ids"] = len(n.get("resolution_ids") or []) - len(ids)
    for vname in VARIANTS:
        stores = {}
        for row in ROWS:
            idx, count = build_store(c, rounds[row], vname)
            stores[row] = idx
            res["store_rows"].setdefault(vname, {})[row] = count
        per = []
        for n in notices:
            d = derive_notice(n, rounds[n["row"]], stores[n["row"]], templates, bounds, attrs, holders, stats)
            per.append({"notice_id": n["notice_id"], "row": n["row"], "kind": n["kind"], "forced": n["forced"], "read_in_full": n["read_in_full"],
                        "status": d["status"], "tiers": d.get("tiers"), "best": d["best"], "audit": d["audit"]})
        res["variants"][vname] = per
    res["notices"] = notices
    res["engine_stats"] = dict(stats)
    res["summary"] = summarise(res)
    res["templates_meta"] = {"n_templates": len(templates), "kinds": sorted({t["notice_kind"] for t in templates}),
                             "n_attributes": len(attrs), "n_bounds": len(bounds)}
    return res


def summarise(res):
    def sel(kind):
        return {"primary_clear_read_in_full": lambda n: n["forced"] == "clear" and n["read_in_full"],
                "all_clear": lambda n: n["forced"] == "clear",
                "clear_and_doubtful": lambda n: True}[kind]
    out = {}
    for vname, per in res["variants"].items():
        out[vname] = {}
        for dn in ("primary_clear_read_in_full", "all_clear", "clear_and_doubtful"):
            keep = [p for p in per if sel(dn)(p)]
            row = {"n": len(keep)}
            for tier in ("forced", "switch_le1", "switch_any"):
                k = sum(1 for p in keep if p["tiers"] and p["tiers"][tier])
                row[tier] = {"derived": k, "share": round(k / len(keep), 3) if keep else None}
            row["by_row"] = {}
            for r in ROWS:
                kr = [p for p in keep if p["row"] == r]
                row["by_row"][r] = {"n": len(kr), "forced": sum(1 for p in kr if p["tiers"] and p["tiers"]["forced"])}
            row["status_counts"] = dict(collections.Counter(p["status"] for p in keep))
            out[vname][dn] = row
    # fetch list on the guarded reading: unknown conditions in each notice's best template
    fl = collections.Counter()
    for p in res["variants"]["guarded"]:
        if p["best"] and p["best"]["result"] == "switch":
            fl.update(p["best"]["unknown"])
    out["fetch_list_guarded"] = fl.most_common()
    # verdict
    g = out["guarded"]["primary_clear_read_in_full"]
    ub = out["upper_bound"]["primary_clear_read_in_full"]
    if g["n"] < 5:
        verdict = "unreadable"
    elif g["forced"]["share"] >= X10:
        verdict = "survives"
    elif ub["forced"]["share"] < X10:
        verdict = "dies"
    else:
        verdict = "dies_under_guards_only"
    out["verdict"] = {"value": verdict, "x10": X10, "guarded_share": g["forced"]["share"], "upper_bound_share": ub["forced"]["share"],
                      "primary_denominator": g["n"]}
    return out


def selftest():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE rounds(id, event_id, round_class);
    CREATE TABLE events(id, event_date, node);
    CREATE TABLE round_transitions(round_id, to_state, recorded_at);
    CREATE TABLE holders(id, kind, canonical_name);
    CREATE TABLE positions(id, holder_id, node, attribute, value, unit, source, source_time, knowable_from, confidence, supersedes, recorded_at);
    CREATE TABLE touched_set(id, round_id, holder_id, node, substitutability, duration_factor);
    CREATE TABLE resolutions(id, source_coverage);
    INSERT INTO events VALUES ('e1','2026-08-01','n1');
    INSERT INTO rounds VALUES ('r1','e1','clean');
    INSERT INTO round_transitions VALUES ('r1','locked','2026-09-01T00:00:00Z');
    INSERT INTO holders VALUES ('hP','plant','P'),('hB','company','B'),('hR','authority','R');
    INSERT INTO positions VALUES
      ('p1','hP','n1','sign_of_exposure','-',NULL,'doc','2026-07-01','2026-07-01','stated',NULL,'2026-08-30T00:00:00Z'),
      ('p2','hB','n1','share','0.6','fraction','doc','2026-07-01','2026-07-01','stated',NULL,'2026-08-30T00:00:00Z'),
      ('p3','hB','n1','substitutability','low',NULL,'guess',NULL,NULL,'inferred',NULL,'2026-08-30T00:00:00Z'),
      ('p4','hP','n1','share','620','kt/yr capacity','doc','2026-07-01','2026-07-01','stated',NULL,'2026-08-30T00:00:00Z'),
      ('p5','hP','n1','duration','5','months','doc','2026-08-05','2026-09-15','stated',NULL,'2026-08-30T00:00:00Z');
    INSERT INTO touched_set VALUES ('t1','r1','hB','n1','low','x');
    INSERT INTO resolutions VALUES ('res1','adequate'),('res2','thin');
    """)
    rnd = load_rounds(c)[0]
    tpl = [{"template_id": "t.fm", "notice_kind": "force_majeure_declaration", "issuer_role": "sup",
            "roles": {"sup": {"holder_kinds": ["plant"]}, "buy": {"holder_kinds": ["company"]}},
            "conditions": [{"id": "c1", "role": "sup", "attribute": "sign_of_exposure", "op": "eq", "value": "-"},
                           {"id": "c2", "role": "buy", "attribute": "share", "op": "ge", "value": 0.3},
                           {"id": "c3", "role": "buy", "attribute": "substitutability", "op": "eq", "value": "low"}],
            "window_rule": {"basis": "none", "days": None}},
           {"template_id": "t.reg", "notice_kind": "regulatory_decision", "issuer_role": "reg",
            "roles": {"reg": {"holder_kinds": ["authority"], "binds_without_position": True}},
            "conditions": [{"id": "c1", "bound": "b1", "op": "le", "value": 30}],
            "window_rule": {"basis": "statute", "days": 10}}]
    attrs = {"share": {"name": "share", "type": "numeric", "unit": "fraction"}, "sign_of_exposure": {"type": "enum"},
             "substitutability": {"type": "enum"}, "duration": {"type": "numeric", "unit": "months"}}
    bounds = {"b1": {"bound_id": "b1", "value": 21}}
    holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
    n_fm = {"notice_id": "T1", "kind": "force_majeure_declaration", "issuer_holder_id": "hP", "issuer_class": "plant", "node": "n1", "date_arrived": "2026-08-10"}
    st = collections.Counter()
    idx, count = build_store(c, rnd, "guarded")
    assert count == 3, count                       # p1, p2, p4 (p3 inferred, p5 knowable_from after the clock)
    d = derive_notice(n_fm, rnd, idx, tpl, bounds, attrs, holders, st)
    assert d["best"]["result"] == "switch" and d["best"]["unknown"] == ["buy.substitutability"], d["best"]   # inferred row is unknown
    assert d["tiers"] == {"forced": False, "switch_le1": True, "switch_any": True}
    idx2, _ = build_store(c, rnd, "S2_inferred_accepted")     # p3 is inferred AND unstamped: S2 alone still drops it
    assert derive_notice(n_fm, rnd, idx2, tpl, bounds, attrs, holders, st)["tiers"]["forced"] is False
    idx2b, _ = build_store(c, rnd, "upper_bound")               # both guards dropped: p3 counts
    assert derive_notice(n_fm, rnd, idx2b, tpl, bounds, attrs, holders, st)["tiers"]["forced"] is True
    idx3, _ = build_store(c, rnd, "S3_touched_set_rows")
    assert derive_notice(n_fm, rnd, idx3, tpl, bounds, attrs, holders, st)["tiers"]["forced"] is True   # touched_set gives substitutability
    idx4, c4 = build_store(c, rnd, "S1_no_knowable_from")
    assert c4 == 4                                                                 # p5 now counts, p3 still inferred
    # unit guard: capacity 620 kt/yr must not satisfy a fraction-valued share test
    tpl_u = [dict(tpl[0], conditions=[{"id": "c1", "role": "sup", "attribute": "share", "op": "ge", "value": 0.3}], roles={"sup": {"holder_kinds": ["plant"]}})]
    du = derive_notice(n_fm, rnd, idx, tpl_u, bounds, attrs, holders, st)
    assert du["best"]["result"] == "switch" and st["unit_mismatch"] >= 1, du["best"]
    # a bound-only role with no position rows, unnamed issuer, and the window
    n_reg = {"notice_id": "T2", "kind": "regulatory_decision", "issuer_holder_id": None, "issuer_class": "authority", "node": "n1", "date_arrived": "2026-08-09"}
    assert derive_notice(n_reg, rnd, idx, tpl, bounds, attrs, holders, st)["tiers"]["forced"] is True
    n_late = dict(n_reg, date_arrived="2026-08-20")                                 # after the 10-day statutory window
    assert derive_notice(n_late, rnd, idx, tpl, bounds, attrs, holders, st)["tiers"]["forced"] is False
    n_none = {"notice_id": "T3", "kind": "allocation_notice", "issuer_holder_id": "hP", "issuer_class": "plant", "node": "n1", "date_arrived": "2026-08-10"}
    assert derive_notice(n_none, rnd, idx, tpl, bounds, attrs, holders, st)["status"] == "no_template_kind"
    assert resolve_coverage(c, ["res1", "res2", "nope"]) == (["res1", "res2"], ["adequate", "thin"])
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        db, tpl, notices, out = sys.argv[1:5]
        result = run(db, tpl, notices)
        json.dump(result, open(out, "w"), indent=1, default=str)
        print(json.dumps(result["summary"]["verdict"]))
