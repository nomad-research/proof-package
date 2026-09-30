"""Assemble one K14 reading package: the documents, the frozen brief and the output schema.

    python lookbacks/k14/package.py <out_dir> <round_label> <node_id> <event_line> <event_date> <docs.json>

docs.json is a list of {"id", "title", "date", "text"}. Writes package.json, docs/D*.txt and brief.md."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import support as S  # noqa: E402

EFFECT_KINDS = ["volume", "cost", "price", "revenue", "obligation", "availability", "credit", "margin", "demand",
                "timing", "direction", "state", "control"]


def brief(node: str, event_line: str) -> str:
    kinds = S.load_kinds()
    hold = S.v16_holdable(kinds)
    reg = S.load_registry()
    seed = json.loads((ROOT / "config" / "seed.json").read_text())
    v17 = json.loads((ROOT / "config" / "seed_v17.json").read_text())
    thr = S.support_threshold()
    L = [f"# K14 reading brief\n", f"**Event line:** {event_line}\n", f"**Node (use this id verbatim as the `from` of your first hop):** `{node}`\n",
         "## What you are asked\n",
         "Read the documents in `docs/` (nothing else: no web, no memory of later events, no other files). Find entities that are "
         f"**within reach** of the node and either **fill a role in a forced or switch derivation**, or are **expressible**, or are **one documented relation from an entity that is expressible**.\n",
         f"- *Within reach:* a chain of documented relations from the node to the entity. Every hop names a relation type from the registry below, an effect kind pair (from-effect > to-effect) that the registry lists for that relation, a document id, and an **exact quoted span** from that document. A script (not you) multiplies transform value x discount along the chain and requires the product to stay at or above **{thr}**; do not compute it. A hop with no quotable support in the documents is not a hop.",
         "- *Fills a role in a forced or switch derivation:* the entity has the capability a template role requires (templates below), so it would be the obligor, the governing document or a carrier of an obligation that a documented fact forces or could switch.",
         "- *Expressible:* a listed instrument (a share, bond, option, future, ETF, event contract) references the entity directly, and a document says so.",
         "- *One documented relation from an entity that is expressible:* a relation from the entity to another entity that is expressible, documented with a quote. This is how a person (by office) or a document counts.",
         "- Persons: name the **office and organisation only** (\"the chief financial officer of X\"), never a personal name.",
         "- If you are unsure a hop is documented, leave the find out. A short list of well-supported finds is worth more than a long one. At most 8 finds per reading.\n",
         "## The two readings\n",
         "**Open reading:** any kind in the registry that is *not* marked v16-holdable, using any relation type. Kinds marked *unreviewed* propose only and cannot support: do not use them as finds.",
         "**Closed reading:** the same documents, but only kinds marked v16-holdable and only the sixteen v16 relation types (offtake, input_supply, input_cost, ownership, shared_facility, shared_infrastructure, logistics, regulatory_scope, customer, competitor, substitute, grid_neighbour, lender, insurer, regulator, counterparty).",
         "Do both in one session, in the order given in your instructions. The order alternates by round so that the second reading does not always benefit from the first.\n",
         "## Output\n",
         "Write `finds_open.json` and `finds_closed.json` next to `package.json`, each `{\"finds\": [...]}` with, per find:\n",
         "```json\n{\"find_id\": \"O1\", \"entity\": {\"name\": \"...\", \"kind\": \"<registry kind>\", \"evidence\": {\"doc\": \"D1\", \"quote\": \"exact span\"}},\n"
         " \"chain\": [{\"from\": \"<node id or previous to>\", \"relation\": \"<registry relation>\", \"to\": \"...\", \"from_effect\": \"state\", \"to_effect\": \"availability\", \"doc\": \"D1\", \"quote\": \"exact span\"}],\n"
         " \"expression\": {\"claim\": \"role|expressible|one_hop_from_expressible\", \"detail\": \"one or two sentences\", \"entity\": \"the expressible entity (if one_hop)\", \"relation\": \"registry relation (if one_hop)\", \"doc\": \"D?\", \"quote\": \"exact span (if one_hop)\"}}\n```\n",
         "The chain's last `to` must equal the entity's `name`. Also write `reading_notes.md`: two or three lines on what you found hard.\n",
         "## Registry: entity kinds\n", "| kind | parent | review | v16 could hold | capabilities |", "|---|---|---|---|---|"]
    for k in v17["entity_kinds"]:
        L.append(f"| {k['kind']} | {k['parent'] or ''} | {k['review']} | {'yes' if k['kind'] in hold else 'no'} | {', '.join(k['capabilities'])} |")
    L += ["\n## Registry: capabilities\n"] + [f"- `{c['capability']}`: {c['meaning']}" for c in v17["capabilities"]]
    L += ["\n## Registry: relation types (discount; effect pairs with transform value)\n", "| relation | discount | pairs |", "|---|---|---|"]
    for r, v in reg.items():
        pairs = "; ".join(f"{p} {x}" for p, x in v["transforms"].items()) or ("does not transmit: " + v["source"])
        L.append(f"| {r} | {v['discount']} | {pairs} |")
    L += ["\n## Effect kinds\n", ", ".join(EFFECT_KINDS), "\n## Obligation templates (what forces an ACK)\n"]
    for t in seed["obligation_templates"]:
        L.append(f"- `{t['id']}` ({', '.join(t['node_types'])}): {t['text']} Roles: " + ", ".join(f"{r['role']} (needs `{r['requires_attribute']}`)" for r in t["roles"]))
    return "\n".join(L) + "\n"


def build(out: Path, label: str, node: str, event_line: str, event_date: str, docs: list[dict]) -> None:
    (out / "docs").mkdir(parents=True, exist_ok=True)
    meta = []
    for d in docs:
        f = f"{d['id']}.txt"
        (out / "docs" / f).write_text(f"[{d['id']}] {d['title']} — dated {d['date']}\n\n{d['text']}\n")
        meta.append({"id": d["id"], "file": f, "title": d["title"], "date": d["date"], "chars": len(d["text"])})
    (out / "package.json").write_text(json.dumps({"round": label, "node": node, "event_line": event_line,
                                                   "event_date": event_date, "docs": meta}, indent=1) + "\n")
    (out / "brief.md").write_text(brief(node, event_line))


if __name__ == "__main__":
    out, label, node, line, date, dj = sys.argv[1:7]
    build(Path(out), label, node, line, date, json.loads(Path(dj).read_text()))
