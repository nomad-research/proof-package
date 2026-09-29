"""v15 §D: contradictions are edge hypotheses.

**Computable, not declared.** Two effect paths contradict when they point at the **same ACK node** and imply opposite
deliveries. That falls out of the DAG; no operator judgment is involved in finding one.

**The contradiction lives in the edges.** The node delivers what it delivers; what disagree are the *paths*. So a
contradiction generates hypotheses about **edges** — this chain transmits, that one does not; this relation is real at
this magnitude, that one is not — each testable at the same ACK, because the delivery discriminates between them.
**This is the first mechanism producing relation-level evidence as a byproduct of walking**, rather than waiting for a
whole round to score. Thirty-odd library rules and one validated is how it stands; this is how that changes.

**Internal and external contradictions are one object.** Ours-versus-market and ours-versus-ours differ only in whose
transmission model is in question, and "ours might be wrong" is the same claim with a different subject. That includes
§A8's opposed effects on a single holder.

**Common set and gap.** The common set is the shared ancestry — the edges both paths needed. Both required it, so it
is anchor-grade and feeds the eliminators. The gap is the divergent segment, and it is **dated by construction**,
because the contradiction is defined at an ACK node with a date. Every divergence gets a direction and a clock from
the same structure.

**The market's branch is not special.** It is a path of attentional edges on the attention calendar, and it can be
wrong exactly like ours. We are never positioned against "the market" but against a specific chain of attentional
transmission; when we win it is because that chain does not carry."""
import sqlite3

from .db import append, get_row
from .errors import ValidationError
from .util import dumps, loads


def _opposite(a: str, b: str) -> bool:
    """Two implied deliveries are opposite when one asserts what the other denies. Deliberately crude and
    conservative: the operator states the implication in a canonical form, and anything ambiguous is not a
    contradiction rather than a maybe."""
    a_, b_ = (a or "").strip().lower(), (b or "").strip().lower()
    if not a_ or not b_:
        return False
    neg = ("no ", "not ", "never ", "without ", "absent ", "none ")
    a_neg = a_.startswith(neg) or a_.startswith("no_")
    b_neg = b_.startswith(neg) or b_.startswith("no_")
    if a_neg == b_neg:
        return False
    strip = lambda x: x.lstrip()  # noqa: E731
    for p in neg:
        a_ = a_[len(p):] if a_.startswith(p) else a_
        b_ = b_[len(p):] if b_.startswith(p) else b_
    a_, b_ = strip(a_.replace("no_", "")), strip(b_.replace("no_", ""))
    return a_ == b_ or a_ in b_ or b_ in a_


def detect(conn: sqlite3.Connection, round_id: str) -> dict:
    """§D1: computable, not declared. Two paths pointing at the same ACK with opposite implied deliveries, plus §A8's
    opposed effects on one holder, which §D3 says is the same object with a different subject."""
    from .effects import list_effects, path_to_root
    live = list_effects(conn, round_id, include_eliminated=False)
    by_id = {e["id"]: e for e in live}
    by_ack: dict[str, list[dict]] = {}
    for e in live:
        if e["ack_id"]:
            by_ack.setdefault(e["ack_id"], []).append(e)
    out = []
    for ack_id, es in by_ack.items():
        ack = conn.execute("SELECT * FROM ack_nodes WHERE id = ?", (ack_id,)).fetchone()
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                a, b = es[i], es[j]
                imp_a, imp_b = (a["basis"] or a["effect_kind"]), (b["basis"] or b["effect_kind"])
                same_holder = a["holder_id"] == b["holder_id"]
                opposed_mag = (a["magnitude"] is not None and b["magnitude"] is not None
                               and a["magnitude"] * b["magnitude"] < 0)
                if not (_opposite(imp_a, imp_b) or opposed_mag):
                    continue
                pa, pb = path_to_root(conn, a["id"], by_id), path_to_root(conn, b["id"], by_id)
                common = [x["id"] for x, y in zip(pa, pb) if x["id"] == y["id"]]
                gap_a = [x["id"] for x in pa if x["id"] not in common]
                gap_b = [x["id"] for x in pb if x["id"] not in common]
                out.append({
                    "ack_id": ack_id, "dated_at": (ack["due_at"] if ack else None),
                    "kind": "opposed_on_holder" if same_holder else "internal",
                    "path_a": [x["id"] for x in pa], "path_b": [x["id"] for x in pb],
                    "implies_a": imp_a, "implies_b": imp_b,
                    "common_set": common, "gap": {"a": gap_a, "b": gap_b},
                    "edge_hypotheses": _edge_hypotheses(conn, pa, pb, common),
                    "why": ("two effects on one holder pointing opposite ways and resolving at the same ACK: a "
                            "signal, not an error (§A8)" if same_holder else
                            "two paths point at the same ACK node and imply opposite deliveries")})
    return {"round_id": round_id, "contradictions": out, "n": len(out),
            "note": ("no two paths in this round point at one ACK with opposite implications; a contradiction is "
                     "computable and this round has none" if not out else
                     "the node delivers what it delivers; what disagree are the paths, so each contradiction "
                     "generates hypotheses about EDGES, testable at the same ACK because the delivery discriminates")}


def _edge_hypotheses(conn: sqlite3.Connection, pa: list[dict], pb: list[dict], common: list[str]) -> list[dict]:
    """§D2: the contradiction lives in the edges, so the hypotheses are about edges. This is the first mechanism
    producing relation-level evidence as a byproduct of walking rather than at the end of a round."""
    out = []
    for path, label in ((pa, "a"), (pb, "b")):
        for e in path:
            if e["id"] in common or not e["relation_id"]:
                continue
            rel = conn.execute("SELECT relation_type, mode, transmits FROM relations WHERE id = ?",
                               (e["relation_id"],)).fetchone()
            if not rel:
                continue
            out.append({"branch": label, "effect_id": e["id"], "relation_id": e["relation_id"],
                        "relation_type": rel["relation_type"], "mode": rel["mode"],
                        "hypothesis": (f"the {rel['relation_type']} edge into {e['effect_kind']} transmits at the "
                                       f"claimed magnitude ({e['transform_weight']})"),
                        "falsifier": "the ACK's delivery matches the other branch, which does not need this edge",
                        # §D7: an attentional edge losing tells you attention did not travel -- real, and never on
                        # its own a validation of the structural claim.
                        "may_support": bool(rel["transmits"]),
                        "note": (None if rel["transmits"] else
                                 "attentional or analogical: this edge may propose and may never support a "
                                 "resolution. Its losing tells you attention did not travel, which is real and is "
                                 "not a validation of the structural claim.")})
    return out


def record(conn: sqlite3.Connection, round_id: str, ack_id: str, kind: str, path_a: list[str], path_b: list[str],
           implies_a: str, implies_b: str, common_set: list[str] | None = None, gap: dict | None = None,
           edge_hypotheses: list[dict] | None = None, exit_ack_id: str | None = None,
           dated_at: str | None = None) -> dict:
    """Write a detected contradiction to the ledger, with its exit ACK (§D6)."""
    if kind not in ("internal", "external", "opposed_on_holder"):
        raise ValidationError("kind is internal | external | opposed_on_holder -- and D3 says they are one object "
                              "differing only in whose transmission model is in question")
    ack = get_row(conn, "ack_nodes", ack_id, "ACK")
    row = append(conn, "contradictions", {
        "round_id": round_id, "ack_id": ack_id, "kind": kind, "path_a": dumps(path_a), "path_b": dumps(path_b),
        "implies_a": implies_a, "implies_b": implies_b, "common_set": dumps(common_set or []),
        "gap": dumps(gap or {}), "dated_at": dated_at or ack["due_at"],
        "edge_hypotheses": dumps(edge_hypotheses or []), "exit_ack_id": exit_ack_id})
    return {"contradiction_id": row["id"], "dated_at": row["dated_at"], "exit_ack_id": exit_ack_id}


def common_set_anchors(conn: sqlite3.Connection, round_id: str) -> dict:
    """§D4: the common set is the shared ancestry — the edges both paths needed. **Both required it, so it is
    anchor-grade** and feeds the eliminators."""
    d = detect(conn, round_id)
    counts: dict[str, int] = {}
    for c in d["contradictions"]:
        for eid in c["common_set"]:
            counts[eid] = counts.get(eid, 0) + 1
    rows = []
    for eid, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        e = conn.execute("SELECT * FROM effects WHERE id = ?", (eid,)).fetchone()
        if not e:
            continue
        rows.append({"effect_id": eid, "required_by_n_contradictions": n, "holder_id": e["holder_id"],
                     "node": e["node"], "effect_kind": e["effect_kind"], "relation_type": e["relation_type"]})
    return {"round_id": round_id, "anchors": rows, "n": len(rows),
            "note": "both branches of every contradiction needed these edges, which is what makes them anchor-grade "
                    "rather than merely agreed"}


def exit_ack(conn: sqlite3.Connection, round_id: str, structural_ack_id: str) -> dict:
    """§D6: **exit is derivable.** A divergence closes when the fact is delivered **and** the price-setting class is
    forced to look. A structural ACK alone does not close it — a fact delivered to a channel nobody who marks the
    security reads changes nothing, which is round 10 in one sentence.

    Exit is the **first attention ACK after the structural ACK**, and the distance between them is
    latency-by-class-distance as a calendar date rather than a number measured afterwards."""
    from . import acks
    s = get_row(conn, "ack_nodes", structural_ack_id, "ACK")
    fired = {f["ack_id"]: f for f in acks.firings(conn)}
    when = (fired[structural_ack_id]["fired_at"] if structural_ack_id in fired else s["due_at"])
    cands = [dict(r) for r in conn.execute(
        "SELECT * FROM ack_nodes WHERE attention = 1 AND (round_id IS NULL OR round_id = ?) ORDER BY rowid",
        (round_id,))]
    after = sorted([c for c in cands if c["due_at"] and when and c["due_at"] >= when], key=lambda c: c["due_at"])
    first = after[0] if after else None
    return {"round_id": round_id, "structural_ack_id": structural_ack_id, "structural_at": when,
            "exit_ack": first,
            "latency_days": (None if not (first and when) else
                             (__import__("datetime").date.fromisoformat(first["due_at"])
                              - __import__("datetime").date.fromisoformat(when)).days),
            "open": first is None,
            "note": ("a structural ACK has fired with no attention ACK after it: the divergence stays open and exit "
                     "is not signalled. A fact delivered to a channel nobody who marks the security reads changes "
                     "nothing." if first is None else
                     "exit is the first attention ACK after the structural one; the distance between them is "
                     "latency-by-class-distance as a calendar date rather than a number measured afterwards")}
