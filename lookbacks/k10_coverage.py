"""K10 companion: which attributes do the frozen templates test, and which did the v15 store ever hold?
Mechanical from K10_templates.json and the v15 positions table. usage: python lookbacks/k10_coverage.py DB TEMPLATES OUT.json"""
import collections, json, sqlite3, sys
db, tpl, out = sys.argv[1:4]
d = json.load(open(tpl))
c = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
stored = collections.Counter(r[0] for r in c.execute("SELECT attribute FROM positions"))
stated = collections.Counter(r[0] for r in c.execute("SELECT attribute FROM positions WHERE confidence='stated' AND knowable_from IS NOT NULL"))
tested = collections.Counter()
per_template = {}
for t in d["templates"]:
    attrs = sorted({x["attribute"] for x in t["conditions"] if "attribute" in x})
    per_template[t["template_id"]] = {"kind": t["notice_kind"], "attributes": attrs,
                                      "never_stored": [a for a in attrs if a not in stored],
                                      "stored_but_no_stated_stamped_row": [a for a in attrs if a in stored and a not in stated]}
    tested.update(attrs)
res = {"positions_by_attribute_all": dict(stored), "positions_by_attribute_stated_and_stamped": dict(stated),
       "templates_testing_each_attribute": dict(tested.most_common()),
       "attributes_tested_never_stored": [a for a, _ in tested.most_common() if a not in stored],
       "templates_with_no_never_stored_condition": [k for k, v in per_template.items() if not v["never_stored"]],
       "n_templates": len(per_template), "per_template": per_template}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("positions_by_attribute_stated_and_stamped", "templates_testing_each_attribute",
                                     "attributes_tested_never_stored", "templates_with_no_never_stored_condition")}, indent=1))
