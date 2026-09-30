"""Compact per-round view of primary, hedge events and claims, for the post-hoc structural-hedge classification."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def dump(rid):
    d = os.path.join(HERE, "packets", "R" + rid)
    s = open(os.path.join(d, "stage1b.txt")).read()
    ans = json.load(open(os.path.join(d, "answer_1b.json")))
    res = json.load(open(os.path.join(HERE, "results", "R" + rid + ".json")))
    prim = re.search(r"THE PRIMARY EVENT: (.*)", s).group(1)
    basket = re.search(r"YOUR PRIMARY BASKET: (.*)", s).group(1)
    titles = {m.group(1): m.group(2) for m in re.finditer(r"^(E\d+)  (.*?)  \(structure", s, re.M)}
    qs = {}
    for m in re.finditer(r"^\s+((?:C|E)\d+(?:\.\d+)?): (.*?)  \[", s, re.M):
        qs[m.group(1)] = m.group(2)
    out = [f"=== R{rid}  lift {res.get('lift') and round(res['lift'],1)}  primary_failed {res.get('primary_failed')}",
           f"PRIMARY: {prim}", f"BASKET: {basket}"]
    for h in ans["hedges"]:
        k = h.get("event") or h.get("contract", "").split(".")[0]
        out.append(f"HEDGE {h.get('contract') or (h['event']+' '+h['direction']+' '+h['tier'])} {h.get('side','')} -> {titles.get(k, qs.get(h.get('contract'), '?'))}")
    for c in ans["claims"]:
        out.append(f"CLAIM if {c['if']} then {c['then']}")
    return "\n".join(out)
if __name__ == "__main__":
    for r in sys.argv[1:]:
        print(dump(r))
