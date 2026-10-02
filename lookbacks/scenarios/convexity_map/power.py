"""Post hoc: what could the convexity map have detected? Uses the same data and design as run.py, train half only.   python power.py"""
import re
src = open("run.py").read()
head = src[:src.index("rng = np.random.default_rng(0)")]      # data load, design, ols, c_t (everything before the analysis)
exec(head)
import numpy as np
print(f"\n{'variable':<9}{'sd(x)':>9}{'median se(c)':>14}{'min detectable slope gap (t=3)':>32}{'share of days |x|>1.5sd':>26}{'median R2 of fit':>18}")
for k in VARS:
    b, t = ols(design(X[k], tr, control=(k != "market")), Y[tr])
    se = np.abs(b[2] / t[2])
    x = X[k][tr]
    D = design(X[k], tr, control=(k != "market"))
    res = Y[tr] - D @ b
    r2 = 1 - res.var(axis=0) / Y[tr].var(axis=0)
    print(f"{k:<9}{x.std():>9.4f}{np.median(se):>14.4f}{2 * 3 * np.median(se):>32.3f}{np.mean(np.abs(x) > 1.5 * x.std()):>26.1%}{np.median(r2):>18.2f}")
print("\nReading: c = (b_up - b_dn) / 2 for a kink at zero, so a slope gap of g needs c = g/2. 'min detectable slope gap' is the gap between the up-side and down-side betas (per unit of x) that reaches t = 3 with a typical stock.")
# non-stationarity of the exposures: for stocks with the strongest train beta on crude, how much does the beta itself move between halves?
b1, _ = ols(design(X["crude"], tr, control=True), Y[tr]); b2, _ = ols(design(X["crude"], te, control=True), Y[te])
top = np.argsort(-np.abs(b1[1]))[:10]
print("\nCrude beta (linear term), train vs test, ten largest in train:")
for j in top:
    print(f"  {STK[j]:<6}{b1[1][j]:>+8.3f}{b2[1][j]:>+8.3f}")
print(f"  correlation of the linear crude beta across halves, all 100 stocks: {np.corrcoef(b1[1], b2[1])[0, 1]:+.2f}")
for k in ("rates", "vol", "gold"):
    a1, _ = ols(design(X[k], tr, control=True), Y[tr]); a2, _ = ols(design(X[k], te, control=True), Y[te])
    print(f"  correlation of the linear {k} beta across halves, all 100 stocks: {np.corrcoef(a1[1], a2[1])[0, 1]:+.2f}")
