"""Worked example: a hedge DAG for an oil-supply-shock thesis, from documented exposures in real 10-K filings (FY2024, filed Feb 2025).
Illustration of the pipeline, not a test. The thesis's channel shocks per outcome are ASSERTIONS by the thesis, chosen for the example (they are not documented and are not anchored).
Exposures are the companies' own disclosed sensitivities, each quote checked literally against the stored filing text.
    python lookbacks/scenarios/hedge_dag_example/run.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lookbacks" / "k14"))
from support import _norm  # noqa: E402
from nomad16 import hedgedag as H  # noqa: E402

FIL = Path(__file__).parent / "filings"
TXT = {t: _norm((FIL / f"{t}_10K_FY2024.txt").read_text()) for t in ("OXY", "MPC")}
ACC = {"OXY": "0000797468-25-000029 (filed 2025-02-18)", "MPC": "0001510295-25-000012 (filed 2025-02-27)"}

# (company, what, value, quote)
EVID = [
    ("OXY", "oil sensitivity, $M pre-tax per +$1/bbl", 250, "approximately $250 million for a $1 per barrel change in oil prices"),
    ("OXY", "FY2024 pre-tax income, $M", 4070, "Income from continuing operations before taxes $ 4,070"),
    ("MPC", "blended crack sensitivity, $M R&M adj. EBITDA per +$1/bbl", 1100, "Blended crack spread sensitivity (a) (per $1.00/barrel change) $ 1,100"),
    ("MPC", "FY2024 pre-tax income, $M", 5957, "Income from continuing operations before income taxes $ 5,957"),
]
for c, what, v, q in EVID:
    assert _norm(q) in TXT[c], f"quote not in {c} filing: {q}"
print("quotes verified literally against the stored filings:", len(EVID))
e = {(c, w.split(",")[0]): v for c, w, v, q in EVID}
oxy_crude = 100 * e[("OXY", "oil sensitivity")] / e[("OXY", "FY2024 pre-tax income")]     # % of FY2024 pre-tax income per +$1/bbl
mpc_crack = 100 * e[("MPC", "blended crack sensitivity")] / e[("MPC", "FY2024 pre-tax income")]
print(f"documented: OXY +{oxy_crude:.2f}% of pre-tax income per +$1/bbl crude; MPC +{mpc_crack:.2f}% of pre-tax income per +$1/bbl crack spread (the two disclose only their own channel)")

OUT = ["w1 short outage", "w2 persistent", "w3 severe"]
SHOCKS = [{"crude": 3, "crack": 6}, {"crude": 12, "crack": 4}, {"crude": 25, "crack": 8}]          # thesis assertions ($/bbl), not documents


def dag(implicit):
    zero = lambda: {"value": 0.0, "basis": "implicit"}
    T = {"kind": "thesis", "exposure": {"crude": oxy_crude, **({"crack": zero()} if implicit else {})}}
    H1 = {"kind": "hedge", "depth": 2, "exposure": {"crack": mpc_crack, **({"crude": zero()} if implicit else {})}}
    return {"thesis": "OXY", "nodes": {"OXY": T, "MPC": H1}, "edges": [{"from": "MPC", "to": "OXY"}]}


for label, imp in (("strict: documented exposures only", False), ("switch: the undisclosed cross-channel exposures set to zero (implicit)", True)):
    print(f"\n== {label}")
    try:
        r = H.evaluate(dag(imp), OUT, SHOCKS, allow_implicit=imp)
    except Exception as ex:
        print("  refused:", ex)
        continue
    print("  status:", r["status"], "| gaps:", r["gaps"])
    print("  thesis (OXY) effect vector, % of FY2024 pre-tax income:", [round(x) for x in r["thesis_vector"]], " worst alone", round(r["thesis_worst_alone"]))
    for h, row in r["hedges"].items():
        print(f"  hedge {h}: vector {[round(x) for x in row['vector']]}  cosine to thesis {row['cosine_to_thesis']:.2f}  worst alone {row['worst_alone']:.0f}")
    if "maximin" in r:
        print("  maximin weights", r["maximin"]["weights"], " worst case", round(r["maximin"]["worst_case"]), " lift over the thesis alone", round(r["maximin"]["lift_over_thesis_alone"]))
