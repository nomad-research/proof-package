"""Build lookbacks/k14/registry.json, the relation registry the K14 support check reads.

Extracted mechanically, nothing chosen here: v16's sixteen relations from config/seed.json (transform values) and
config/appetite.json (HOP_DISCOUNT, HOP_DISCOUNT_BUILDER); v17's new relations typed from docs/nomad_v17_open_entity.md §6.6.
A hop's support factor is transform value x hop discount, the rule of nomad16/effects.py effect_compose.
`python lookbacks/k14/registry.py` rewrites the file; its sha256 is recorded in K14_prereg.md at the freeze.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

V17 = {   # relation: (hop discount, {"from>to": value}) — §6.6, provisional_unratified
    "binds": (0.8, {"state>obligation": 0.9, "state>availability": 0.6, "state>cost": 0.5, "state>revenue": 0.5}),
    "governs": (0.6, {"state>availability": 0.8, "state>obligation": 0.7, "state>cost": 0.5, "state>timing": 0.5}),
    "amends": (0.9, {"state>state": 0.9}),
    "supersedes": (0.9, {"state>state": 0.9}),
    "controls": (0.75, {"control>direction": 0.6, "control>obligation": 0.5, "state>control": 0.7}),
    "holds_office_at": (0.6, {"state>control": 0.7}),
    "located_at": (0.6, {"availability>availability": 0.6, "timing>timing": 0.4}),
}
NON_TRANSMITTING = {   # discount 0 or no transform entry: scope, expression or provenance edges; they can be the documented last relation, never a transmitting hop
    "member_of": "computed by recomputation (§4.3); no table entry",
    "classified_as": "classificatory; proposes only", "references": "expression edge", "evidences": "provenance",
    "issued_by": "provenance", "reports_on": "provenance", "adjacent_to": "classificatory; scope only",
    "coverage": "attentional", "analogy": "analogical", "index_membership": "analogical", "listing_venue": "analogical",
    "reporting_currency": "analogical", "sector": "analogical", "size_bucket": "analogical",
}


def build() -> dict:
    app = json.loads((ROOT / "config" / "appetite.json").read_text())["values"]
    seed = json.loads((ROOT / "config" / "seed.json").read_text())
    disc = {**app["HOP_DISCOUNT"]["value"], **app["HOP_DISCOUNT_BUILDER"]["value"]}
    reg = {}
    for t in seed["transforms"]:
        r = reg.setdefault(t["relation"], {"discount": disc[t["relation"]], "source": "v16 seed.json transforms + appetite hop discount",
                                            "transforms": {}})
        r["transforms"][f"{t['from']}>{t['to']}"] = t["value"]
    for r, (d, tf) in V17.items():
        reg[r] = {"discount": d, "source": "v17 spec §6.6 (provisional_unratified)", "transforms": tf}
    for r, why in NON_TRANSMITTING.items():
        reg.setdefault(r, {"discount": 0.0, "source": why, "transforms": {}})
    return {"relations": dict(sorted(reg.items())), "support_threshold_key": "SUPPORT_THRESHOLD",
            "support_rule": "factor(hop) = transforms[from_effect>to_effect] x discount; support = product over hops"}


if __name__ == "__main__":
    (ROOT / "lookbacks" / "k14" / "registry.json").write_text(json.dumps(build(), indent=1) + "\n")
