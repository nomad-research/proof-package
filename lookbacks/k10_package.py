"""Build the K10 authoring package: rounds 1-7 material only, per K10_prereg.md.

Read-only on the frozen v15 ledger (immutable=1, so no -shm/-wal is created). The filter is a timestamp:
everything created before the creation time of ledger row 8 (the first round under test). The output is
scanned for named entities of rounds 8-17 and the build fails on a hit.
usage: python lookbacks/k10_package.py v15/nomad_harness.db docs/nomad_system_spec_v16_final.md OUT.md
"""
import re, sqlite3, sys

DB, SPEC, OUT = sys.argv[1:4]
c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute("SELECT id, recorded_at FROM rounds ORDER BY rowid")]
CUT = rows[7]["recorded_at"]          # ledger row 8 = programme round 8, first round under test
assert all(r["recorded_at"] < CUT for r in rows[:7]) and CUT > rows[6]["recorded_at"]

spec = open(SPEC, encoding="utf-8").read().split("\n")
def between(start, stop):
    i = next(n for n, l in enumerate(spec) if l.startswith(start))
    j = next(n for n, l in enumerate(spec) if n > i and l.startswith(stop))
    return "\n".join(spec[i:j]).strip()
def line(prefix):
    return next(l for l in spec if l.startswith(prefix))

out = []
w = out.append
w("# K10 authoring package: rounds 1-7 only\n")
w(f"Built from the frozen v15 ledger. Every ledger-derived item below was created before `{CUT}`, the creation "
  "time of the first round under test. Nothing later is in this file.\n")

w("## A. What an obligation template is (format-defining extracts of the v16 spec)\n")
w("### A1. From section 3\n")
w(line("- **Obligation templates are a new rule kind**") + "\n")
w("### A2. From section 4\n")
w(between("**Three timing classes:**", "**The ACK graph is a DAG**"))
w("")
w(line("**Derived ACKs: the AND runs over positions**") + "\n")
w("### A3. Section 22.2 in full\n")
w(between("### 22.2 Derivation", "### 22.3 Outcome vocabularies"))
w("\n### A4. From section 18.3: the four tables a template file feeds\n")
w("| Table | Kind | Key fields |\n|---|---|---|")
for p in ("| `position_attributes`", "| `bounds`", "| `obligation_templates`", "| `ack_derivations`"):
    w(line(p))
w("\nThe spec asks for: templates, bounds and position attributes authored from rounds 1-7 only.\n")

w("## B. The record of rounds 1-3 (played in chat, imported)\n")
w(open("v15/docs/nomad_session_record_rounds_1-3.md", encoding="utf-8").read().strip() + "\n")
for n in (4, 5, 6, 7):
    w(f"## B{n}. Round {n} recap\n")
    w(open(f"v15/docs/rounds/round{n}_recap.md", encoding="utf-8").read().strip() + "\n")

w("## C. Positions recorded in the names book before the cut\n")
w("Columns are as stored. `knowable_from` blank means the row carries no stamp. `confidence` is "
  "`stated` (a document says it), `inferred` or `implicit`. `sign_of_exposure` is the sign of the holder's "
  "exposure to the event on that node.\n")
w("| id | holder | holder kind | listed | node | attribute | value | unit | source | source_time | knowable_from | confidence | supersedes |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
holders = {h["id"]: dict(h) for h in c.execute("SELECT * FROM holders")}
n_pos = 0
for p in c.execute("SELECT * FROM positions WHERE recorded_at < ? ORDER BY rowid", (CUT,)):
    h = holders.get(p["holder_id"], {})
    cell = lambda v: "" if v is None else str(v).replace("|", "/").replace("\n", " ")
    w("| " + " | ".join(cell(x) for x in (p["id"][:8], h.get("canonical_name"), h.get("kind"),
        "yes" if h.get("listed") else "no", p["node"], p["attribute"], p["value"], p["unit"], p["source"],
        p["source_time"], p["knowable_from"], p["confidence"], (p["supersedes"] or "")[:8])) + " |")
    n_pos += 1
w("")

w("## D. Library rules created before the cut\n")
w("Text, what each forbids, its layer and its provenance only. Hit and miss counts are omitted on purpose "
  "(later rounds updated them).\n")
n_rules = 0
for r in c.execute("SELECT * FROM library_rules WHERE created_at < ? ORDER BY rowid", (CUT,)):
    w(f"- **[{r['layer']}]** {r['rule_text']}\n  - {r['forbids']}\n  - provenance: {r['provenance']}")
    n_rules += 1
w("")

w("## E. Carriers known before the cut\n")
w("| name | kind | access | note | participant class |\n|---|---|---|---|---|")
for k in c.execute("SELECT * FROM carriers WHERE created_at < ? ORDER BY rowid", (CUT,)):
    w(f"| {k['name']} | {k['kind']} | {k['access']} | {(k['note'] or '').replace('|', '/')} | {k['participant_class']} |")
w("")
w("## F. Holder kinds and authority holders in the names book before the cut\n")
w("Holder kinds in use: `company`, `plant`, `facility`, `authority`, `other`.\n")
for h in c.execute("SELECT * FROM holders WHERE created_at < ? AND kind='authority' ORDER BY rowid", (CUT,)):
    w(f"- authority: {h['canonical_name']}")

text = "\n".join(out) + "\n"
# Operator model identifiers appear in the v15 recaps. They are irrelevant to authoring and are not copied
# into a new artifact; the cutoff dates beside them are kept.
text = re.sub(r"claude-[a-z0-9.-]+", "[operator model]", text)
LEAK = [r"Sweeny", r"Phillips 66", r"CPChem", r"trichlor", r"TCCA", r"\bparagon\b", r"Paragon", r"\bUPM\b", r"Stora Enso",
        r"Codelco", r"El Teniente", r"Irico", r"Gresik", r"Smelting", r"Google Cloud", r"us-west1", r"Statement of Objections",
        r"Section 337", r"\bITC\b", r"round (8|9|1[0-7])\b", r"Round (8|9|1[0-7])\b"]
hits = [(p, m.group(0), text[max(0, m.start() - 60):m.end() + 60].replace("\n", " "))
        for p in LEAK for m in re.finditer(p, text)]
if hits:
    for h in hits:
        print("LEAK", h)
    sys.exit("REFUSED: the package mentions rounds 8-17")
open(OUT, "w", encoding="utf-8").write(text)
print(f"ok: {len(text)} chars, cut {CUT}, {n_pos} positions, {n_rules} rules -> {OUT}")
