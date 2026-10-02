"""POST-HOC, descriptive (not part of the registered bar, written after the scores were seen).
Labels each scored round's hedge as:
  S = at least one hedge leg is the same underlying as the primary (same Fed meeting in a multi-meeting ladder, a by-date rung on the same
      release/election, or a necessary condition of the primary), so its floor lift is partly or wholly arithmetic.
  X = every hedge leg is a different underlying; the lift exists only if the session's causal claims hold.
Labels are my reading of the primary and hedge event titles in v1_structural_dump.py; reasons are recorded per round."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v1_score as K
LABELS = {
 "155674": ("X", "Tread token launch vs other projects' launches (o1, GRVT, Solstice): market-wide launch-window claim"),
 "199763": ("S", "Next UK PM in 2026 vs 'Starmer out by': Starmer leaving is a necessary condition of a new PM in 2026"),
 "230191": ("X", "GRVT FDV vs o1 FDV and ETH dip: different tokens / asset"),
 "287395": ("S", "July Fed decision vs 'Fed rate hike by...' multi-meeting ladder that contains July (gold, crude legs are X)"),
 "333025": ("X", "Aligned Layer FDV vs Arcium / Cap FDV and ETH reach: different tokens / asset"),
 "481717": ("S", "September Fed decision vs Fed decisions (Jul-Oct) multi-meeting ladder that contains September"),
 "606437": ("S", "Fed decisions (Jul-Oct) vs the September decision and 'rate hike by': same meetings"),
 "624096": ("X", "UK Foreign Secretary vs Home/Defence/Culture Secretary partitions and leader-out: different offices (shared reshuffle claim)"),
 "627355": ("S", "Next GPT model Arena debut vs 'GPT-6 released by': the release is a necessary condition (best-AI-model leg is X)"),
 "655630": ("X", "Bitcoin July touch ladder vs Ethereum July touch ladder: cross-asset"),
 "655631": ("X", "Ethereum July touch ladder vs Bitcoin July touch ladder: cross-asset"),
 "674379": ("X", "UK Defence Secretary vs Home/Foreign Secretary and leader-out: different offices (shared reshuffle claim)"),
 "680764": ("S", "Clacton Farage vote share vs Clacton winner: same election"),
 "707496": ("X", "US-Iran ceasefire vs Israel airspace closure and venue of talks"),
 "731779": ("X", "Netanyahu NYC visit vs Israel airspace closure and venue of talks"),
 "850741": ("X", "Gemini Flash release vs OpenAI Astra and Claude Opus releases: competitor-launch claim"),
 "90434": ("X", "Florida governor primary vs KY-04 and Texas Senate primaries: Trump-endorsement claim"),
}
def main():
    R = {i: json.load(open(os.path.join(HERE, "results", f"R{i}.json"))) for i in LABELS}
    out = {"labels": {i: {"class": c, "why": w, "lift": R[i]["lift"], "primary_failed": R[i]["primary_failed"], "in_reachable_set": R[i]["in_reachable_set"],
                          "C_minus_D": R[i]["realised"]["C"] - R[i]["realised"]["D"]} for i, (c, w) in LABELS.items()}}
    for name, keep in (("all", lambda c: True), ("X_only", lambda c: c == "X"), ("S_only", lambda c: c == "S")):
        sub = [R[i] for i, (c, _) in LABELS.items() if keep(c)]
        out[name] = K.study(sub)
        out[name]["mean_lift"] = sum(r["lift"] for r in sub) / len(sub)
        out[name]["median_lift"] = sorted(r["lift"] for r in sub)[len(sub) // 2]
        xs = sorted(r["lift"] for r in sub); out[name]["mean_lift_ex_top"] = sum(xs[:-1]) / (len(xs) - 1)
    json.dump(out, open(os.path.join(HERE, "v1_structural_report.json"), "w"), indent=1)
    for n in ("all", "X_only", "S_only"):
        o = out[n]
        print(n, "n", o["scored"], "primary-loss", o["gates"]["primary_loss_rounds"], "mean lift %.1f median %.1f ex-top %.1f" % (o["mean_lift"], o["median_lift"], o["mean_lift_ex_top"]),
              "| B1 %.2f" % o["B1"]["in_set_share"], "| C-D %.2f ci %s" % (o["B2"]["mean_C_minus_D"], [round(x, 1) for x in o["B2"]["ci90"]]),
              "| C>R %.2f" % o["B3"]["C_above_R_mean"], "| means", {k: round(v, 1) for k, v in o["means"].items()})
    for i, v in out["labels"].items(): print(i, v["class"], round(v["lift"], 1), "failed" if v["primary_failed"] else "held", "in_set" if v["in_reachable_set"] else "OUT_OF_SET", round(v["C_minus_D"], 1))
main()
