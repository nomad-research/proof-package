"""Which calibration method should Nomad use? (post-hoc, 2026-10-01; declares nothing)

Data: every contract the no-evidence model priced in BT-A (April to September; January to March carry recall) and BT-T2's first pass (percent and
partition answers). Methods, each fitted only on earlier data and scored on later data:
  raw       the stated chance
  isotonic  pool-adjacent violators, a free monotone map
  platt     logit(q) = a + b * logit(p): one slope (over/under-confidence) and one shift
  beta      logit(q) = a*ln(p) - b*ln(1-p) + c (Kull et al. 2017): separate corrections at the low and the high end
Scores: log loss and Brier (lower is better), and expected calibration error over ten bins. Two tests:
  1. walk-forward inside BT-A: fit on months before m, score month m, m = May to September;
  2. transfer: fit on all of BT-A April to June, score BT-T2 (a different pipeline: as-of date given, priced at the lock).
"""
import glob, json, os, sys
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import bt_audit as A
import bt_t2 as T

EPS = 0.005
crawl = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "closed_2026-01-01_2026-10-01_v10000_scoped.json.gz"))}


def bta():
    draw = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "audit", "draw.json"))["events"]}; out = []
    for f in glob.glob(os.path.join(HERE, "bt", "audit", "answers", "S*.json")):
        ans = A.jload(f)["answers"]; L = A.jload(f.replace("answers", "sessions"))["labels"]
        for lab, l in L.items():
            ev = draw[l["event_id"]]
            if ev["month"] < "2026-04":
                continue
            mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
            for cl, cid in l["contracts"].items():
                out.append((ev["month"], ans[lab]["p"][cl] / 100, float(A.yes_won(mk[cid]))))
    return out


def bt2():
    fr = {e["id"]: e for e in A.jload(os.path.join(HERE, "bt", "t2", "frame.json"))["events"]}; out = []
    for f in glob.glob(os.path.join(HERE, "bt", "t2", "answers", "S*.json")):
        ans = T.intkeys(A.jload(f)["answers"]); L = A.jload(f.replace("answers", "sessions"))["labels"]
        for lab, l in L.items():
            ev = fr[l["event_id"]]
            if ev["kind"] not in ("partition", "percent"):
                continue
            mk = {m["cid"]: m for m in crawl[ev["id"]]["markets"]}
            for cl, cid in l["contracts"].items():
                out.append((ev["as_of"][:7], ans[lab]["p"][cl] / 100, float(A.yes_won(mk[cid]))))
    return out


def lg(p):
    p = np.clip(p, EPS, 1 - EPS); return np.log(p / (1 - p))


def fit(method, p, y):
    p = np.clip(np.asarray(p), EPS, 1 - EPS); y = np.asarray(y)
    if method == "raw":
        return lambda q: np.clip(q, EPS, 1 - EPS)
    if method == "isotonic":
        m = IsotonicRegression(out_of_bounds="clip", y_min=EPS, y_max=1 - EPS).fit(p, y); return lambda q: m.predict(np.clip(q, EPS, 1 - EPS))
    if method == "platt":
        m = LogisticRegression(C=1e4).fit(lg(p).reshape(-1, 1), y); return lambda q: m.predict_proba(lg(q).reshape(-1, 1))[:, 1]
    if method == "beta":
        X = np.c_[np.log(p), -np.log(1 - p)]; m = LogisticRegression(C=1e4).fit(X, y)
        return lambda q: m.predict_proba(np.c_[np.log(np.clip(q, EPS, 1 - EPS)), -np.log(1 - np.clip(q, EPS, 1 - EPS))])[:, 1]


def scores(q, y):
    q = np.clip(q, EPS, 1 - EPS); y = np.asarray(y)
    bins = np.minimum((q * 10).astype(int), 9)
    ece = sum(abs(q[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean() for b in range(10) if (bins == b).any())
    return {"log_loss": float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))), "brier": float(np.mean((q - y) ** 2)), "ece": float(ece)}


METHODS = ("raw", "isotonic", "platt", "beta")
a = bta(); b = bt2(); out = {"walk_forward_bta": {}, "transfer_bta_to_bt2": {}, "fitted_on_all_bta": {}}
for meth in METHODS:
    qs, ys = [], []
    for m in ("2026-05", "2026-06", "2026-07", "2026-08", "2026-09"):
        tr = [r for r in a if r[0] < m]; te = [r for r in a if r[0] == m]
        f = fit(meth, [r[1] for r in tr], [r[2] for r in tr]); qs += list(f(np.array([r[1] for r in te]))); ys += [r[2] for r in te]
    out["walk_forward_bta"][meth] = dict(scores(np.array(qs), ys), n=len(ys))
    tr = [r for r in a if r[0] <= "2026-06"]; f = fit(meth, [r[1] for r in tr], [r[2] for r in tr])
    out["transfer_bta_to_bt2"][meth] = dict(scores(f(np.array([r[1] for r in b])), [r[2] for r in b]), n=len(b))
fb = fit("beta", [r[1] for r in a], [r[2] for r in a])
out["fitted_on_all_bta"]["beta_map"] = {str(s): round(float(fb(np.array([s]))[0]), 3) for s in (0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99)}
fp = fit("platt", [r[1] for r in a], [r[2] for r in a])
out["fitted_on_all_bta"]["platt_map"] = {str(s): round(float(fp(np.array([s]))[0]), 3) for s in (0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99)}
json.dump(out, open(os.path.join(HERE, "bt", "calibration_methods.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
