"""K14 mechanical checks. A reader lists each find hop by hop; this script, not the reader, decides reach.

For each find it checks (spec §9.2 (i), with the definitions frozen in K14_prereg.md):
  * the chain starts at the round's node, is contiguous, and ends at the found entity;
  * every hop names a relation type in lookbacks/k14/registry.json, cites a lock-time document, and the quoted
    span occurs literally in that document's text (whitespace and case normalised);
  * every hop transmits (a transform entry for its effect-kind pair with value > 0 and a discount > 0), and the
    support, the product of transform value x discount along the chain, stays at or above SUPPORT_THRESHOLD;
  * the found entity's kind is in the v17 registry, is `reviewed` (an unreviewed kind proposes, never supports)
    and, for the open reading, is not a kind v16 could hold.
It also verifies the quote and the relation type of the "expression" leg. Whether that leg makes the entity fill a
role, be expressible, or sit one documented relation from something that is (§9.2 (ii)) is not decided here: a blind
second session judges it.

    python lookbacks/k14/support.py <round_dir>     reads package.json, docs/, finds_open.json, finds_closed.json,
                                                    writes support_report.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

V16_BASE = {"company", "facility", "sovereign", "agency", "central_bank", "fund", "index", "commodity_grade",
            "currency", "contract", "composite"}   # nomad16/entities.py LEGACY_KIND values, aggregate -> composite


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def load_registry() -> dict:
    return json.loads((ROOT / "lookbacks" / "k14" / "registry.json").read_text())["relations"]


def load_kinds() -> dict:
    return {k["kind"]: k for k in json.loads((ROOT / "config" / "seed_v17.json").read_text())["entity_kinds"]}


def v16_holdable(kinds: dict) -> set:
    out = set(V16_BASE)
    for name, k in kinds.items():
        p = k["parent"]
        while p:
            if p in V16_BASE:
                out.add(name)
                break
            p = kinds[p]["parent"]
    return out


def support_threshold() -> float:
    from nomad16 import config
    return float(config.get("SUPPORT_THRESHOLD"))


def quote_ok(docs: dict, doc: str, quote: str) -> bool:
    return bool(quote) and doc in docs and _norm(quote) in _norm(docs[doc])


def check_find(find: dict, node: str, docs: dict, reg: dict, kinds: dict, thr: float, closed: bool) -> dict:
    why, hops, cum = [], [], 1.0
    ent = find.get("entity", {})
    chain = find.get("chain") or []
    if not chain:
        why.append("no chain")
    elif _norm(chain[0].get("from", "")) != _norm(node):
        why.append(f"the chain does not start at the round's node ({node!r})")
    prev_to = None
    for i, h in enumerate(chain):
        rel = h.get("relation")
        r = reg.get(rel)
        row = {"i": i + 1, "from": h.get("from"), "relation": rel, "to": h.get("to"),
               "effect": f"{h.get('from_effect')}>{h.get('to_effect')}"}
        if prev_to is not None and _norm(h.get("from", "")) != _norm(prev_to):
            why.append(f"hop {i + 1} does not continue from hop {i}")
        prev_to = h.get("to", "")
        if r is None:
            why.append(f"hop {i + 1}: {rel!r} is not a registry relation type")
            row["factor"] = 0.0
        else:
            tv = r["transforms"].get(row["effect"], 0.0)
            factor = tv * r["discount"]
            row.update(transform=tv, discount=r["discount"], factor=factor)
            if factor <= 0:
                why.append(f"hop {i + 1}: {rel} with {row['effect']} does not transmit")
            cum *= factor
        row["cumulative"] = cum
        row["quote_verified"] = quote_ok(docs, h.get("doc", ""), h.get("quote", ""))
        if not row["quote_verified"]:
            why.append(f"hop {i + 1}: the quoted span is not in {h.get('doc')!r}")
        hops.append(row)
    if chain and _norm(chain[-1].get("to", "")) != _norm(ent.get("name", "")):
        why.append("the chain does not end at the found entity")
    if chain and cum < thr:
        why.append(f"support {cum:.3f} is below SUPPORT_THRESHOLD {thr}")
    kind = ent.get("kind")
    k = kinds.get(kind)
    if k is None:
        why.append(f"kind {kind!r} is not in the registry: a proposal, never support")
    elif k["review"] != "reviewed":
        why.append(f"kind {kind!r} is unreviewed: it proposes and never supports")
    holdable = kind in v16_holdable(kinds)
    if not closed and holdable:
        why.append(f"kind {kind!r} is one v16 could hold: not a find for the open count")
    if closed and k is not None and not holdable:
        why.append(f"kind {kind!r} is not one v16 could hold: not a closed-reading find")
    ev = ent.get("evidence") or {}
    if not quote_ok(docs, ev.get("doc", ""), ev.get("quote", "")):
        why.append("the entity's own evidence quote is not in its document")
    ex = find.get("expression") or {}
    expr = {"claim": ex.get("claim"), "relation": ex.get("relation"), "entity": ex.get("entity")}
    if ex.get("claim") not in {"role", "expressible", "one_hop_from_expressible"}:
        why.append("expression.claim is role, expressible or one_hop_from_expressible")
    if ex.get("claim") == "one_hop_from_expressible":
        if ex.get("relation") not in reg:
            why.append(f"expression relation {ex.get('relation')!r} is not a registry type")
        expr["quote_verified"] = quote_ok(docs, ex.get("doc", ""), ex.get("quote", ""))
        if not expr["quote_verified"]:
            why.append("the expression leg's quoted span is not in its document")
    return {"find_id": find.get("find_id"), "entity": ent.get("name"), "kind": kind, "kind_reviewed": bool(k and k["review"] == "reviewed"),
            "v16_holdable_kind": holdable, "hops": hops, "final_support": cum if chain else None,
            "reach_ok": not why, "reasons": why, "expression": expr}


def run(round_dir: Path) -> dict:
    pkg = json.loads((round_dir / "package.json").read_text())
    docs = {d["id"]: (round_dir / "docs" / d["file"]).read_text() for d in pkg["docs"]}
    reg, kinds, thr = load_registry(), load_kinds(), support_threshold()
    out = {"round": pkg["round"], "node": pkg["node"], "threshold": thr}
    for arm, closed in (("open", False), ("closed", True)):
        p = round_dir / f"finds_{arm}.json"
        finds = json.loads(p.read_text())["finds"] if p.exists() else []
        out[arm] = [check_find(f, pkg["node"], docs, reg, kinds, thr, closed) for f in finds]
    (round_dir / "support_report.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def round_result(report: dict, judge: dict | None) -> dict:
    """A round shows a K14 find if some open find passes (i) mechanically and the blind judge accepts (ii)."""
    verdicts = {j["find_id"]: j["verdict"] for j in (judge or {}).get("verdicts", [])}
    ok = [f for f in report["open"] if f["reach_ok"]]
    counted = [f["find_id"] for f in ok if verdicts.get(f["find_id"]) in {"role", "expressible", "one_hop_from_expressible"}]
    return {"round": report["round"], "open_finds": len(report["open"]), "reach_ok": len(ok), "judged_pass": counted,
            "round_shows_find": bool(counted), "closed_finds_reach_ok": sum(f["reach_ok"] for f in report["closed"]),
            "judge_present": judge is not None}


if __name__ == "__main__":
    d = Path(sys.argv[1])
    rep = run(d)
    print(json.dumps({arm: [(f["find_id"], f["reach_ok"], f["reasons"]) for f in rep[arm]] for arm in ("open", "closed")}, indent=1))
