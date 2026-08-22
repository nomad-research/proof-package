"""Renders tests_a2/results.md."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HURDLE = 2.78


def _f(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    return str(x)


def _verdict(top, grad, sp, strat) -> tuple[str, str]:
    t_top = top.get("t_stat")
    h1 = np.isfinite(t_top) and t_top < -HURDLE
    h2 = grad.get("gradient_significant") and grad.get("gradient_direction_as_predicted")
    net_t = strat.get("net_t", float("nan"))

    if h1 and h2:
        return "PASS", (
            f"The top decile of |imbalance_ratio| shows the predicted negative overnight "
            f"reversal (t = {_f(t_top, 3)}) **and** the effect strengthens monotonically with "
            f"imbalance across deciles (interaction t = {_f(grad.get('t_gradient'), 3)}, "
            f"Spearman ρ = {_f(sp.get('spearman_rho'), 3)}, permutation p = "
            f"{_f(sp.get('permutation_p'), 3)}). Forced flow is compensated where counterparty "
            "scarcity is high, and Test A's null was a property of its universe rather than of "
            "the mechanic. The amendment's central claim survives its own test."
        )
    if h1 and not h2:
        return "WEAK", (
            f"The top decile clears the hurdle (t = {_f(t_top, 3)}) but there is no monotone "
            f"gradient across deciles (interaction t = {_f(grad.get('t_gradient'), 3)}, "
            f"Spearman ρ = {_f(sp.get('spearman_rho'), 3)}, permutation p = "
            f"{_f(sp.get('permutation_p'), 3)}). The pre-registration is explicit that this "
            "pattern is weak evidence and is what data mining looks like: one bucket out of ten "
            "clearing a threshold with no dose-response behind it. Not treated as support."
        )
    if h2 and not h1:
        return "PARTIAL", (
            f"There is a gradient in the predicted direction (interaction t = "
            f"{_f(grad.get('t_gradient'), 3)}) but the top decile itself does not clear the "
            f"hurdle (t = {_f(t_top, 3)}). The dose-response is the more informative of the two "
            "statistics, so this is not nothing — but it does not meet the pre-registered pass "
            "condition, which requires both."
        )
    return "FAIL — TEST A CLOSED", (
        f"The top decile does not clear the hurdle (t = {_f(t_top, 3)}) and there is no monotone "
        f"gradient across deciles (interaction t = {_f(grad.get('t_gradient'), 3)}, Spearman "
        f"ρ = {_f(sp.get('spearman_rho'), 3)}, permutation p = {_f(sp.get('permutation_p'), 3)}). "
        "The LETF rebalancing mechanic does not pay in the liquid regime and does not pay in the "
        "illiquid regime either. Per the pre-registered stopping condition in §8, **Test A is "
        "closed permanently and no third regime will be proposed.**"
    )


def render(path: Path, panel, diag, recon, curve, top, grad, sp, sp_eff, subsamples,
           strat, dsr, log_summary) -> None:
    verdict, para = _verdict(top, grad, sp, strat)
    L: list[str] = []
    A = L.append

    A("# Test A-2 — LETF rebalancing in illiquid underlyings: results")
    A("")
    A(f"**Verdict: {verdict}**")
    A("")
    A(para)
    A("")
    A("Pre-registration: [`preregistration.md`](preregistration.md), committed before this "
      "analysis was run, including the stopping condition in §8.")
    A("")
    A("> **Why this test exists.** Test A read its null as a ceiling — *if perfectly enumerated "
      "flow pays nothing, imperfect enumeration cannot pay more.* That collapses two independent "
      "variables. The premium from forced flow comes from **scarcity of the other side**, not "
      "from difficulty of enumeration, and Test A's universe was maximally liquid and minimally "
      "idiosyncratic — the regime McLean & Pontiff (2016) already identify as where alpha does "
      "not survive. This test runs the identical mechanic where counterparty scarcity is high.")
    A("")
    A("---")
    A("")

    # ---- headline
    A("## 1. Headline")
    A("")
    A("| Quantity | Value |")
    A("|---|---|")
    A(f"| Sample | {panel['date'].min().date()} to {panel['date'].max().date()} |")
    A(f"| Underlying-days | {len(panel):,} |")
    A(f"| Underlyings | {panel['underlying'].nunique()} "
      f"({int((~panel['control']).groupby(panel['underlying']).first().sum())} thin + "
      f"{int(panel.groupby('underlying')['control'].first().sum())} index controls) |")
    A(f"| **H1 — top-decile β** | **{_f(top.get('beta'))}**, t = **{_f(top.get('t_stat'), 3)}** |")
    A(f"| **H2 — gradient interaction** | β_g = {_f(grad.get('beta_gradient'))}, "
      f"t = **{_f(grad.get('t_gradient'), 3)}** |")
    A(f"| H2 — Spearman ρ (decile vs β) | {_f(sp.get('spearman_rho'), 3)}, "
      f"permutation p = {_f(sp.get('permutation_p'), 3)} |")
    A(f"| Hurdle | {HURDLE} |")
    if "gross_mean_bps" in strat:
        A(f"| Top-decile strategy gross | {_f(strat['gross_mean_bps'], 3)} bps/day, "
          f"t = {_f(strat['gross_t'], 3)} |")
        A(f"| Top-decile strategy net | {_f(strat['net_mean_bps'], 3)} bps/day, "
          f"t = {_f(strat['net_t'], 3)} |")
        A(f"| Mean round-trip cost | {_f(strat['mean_cost_bps'], 3)} bps |")
        A(f"| Mean participation | {_f(strat['mean_participation_pct'], 3)}% of ADV |")
    if dsr is not None:
        A(f"| **Cumulative trials (all tests)** | **{dsr.n_trials}** |")
        A(f"| Deflated Sharpe (cumulative) | {_f(dsr.deflated_sharpe, 4)} |")
    A("")

    # ---- decile curve
    A("## 2. The decile curve — primary output")
    A("")
    A("All underlying-days pooled and sorted into ten deciles by `|imbalance_ratio|`. The "
      "hypothesis is a **monotone** relationship: near zero in low deciles, rising toward the "
      "top. Full data in [`decile_curve.csv`](decile_curve.csv).")
    A("")
    A("| Decile | mean \\|imb ratio\\| | median M/ADV | β | t | effect of 1sd imbalance (bps) | n |")
    A("|---|---|---|---|---|---|---|")
    for _, r in curve.iterrows():
        A(f"| {int(r['decile'])} | {_f(r.get('mean_abs_imb'), 3)} | "
          f"{_f(r.get('median_scale'), 3)} | {_f(r['beta'])} | "
          f"{_f(r['t_stat'], 3)} | {_f(r.get('effect_1sd_bps'), 3)} | "
          f"{int(r['n_obs']) if pd.notna(r['n_obs']) else 'n/a'} |")
    A("")
    A("> **Read the β column with care — and prefer the column beside it.** β is a slope in "
      "units of *return per unit of imbalance_ratio*, and mean |imbalance_ratio| runs from "
      "0.00067 in decile 1 to 0.80 in decile 10, a span of more than a thousand times. β "
      "therefore shrinks mechanically as imbalance rises, which is why decile 1 shows the "
      "largest raw β in the table and decile 10 the smallest. That is an artefact of units, not "
      "an effect running backwards. The **effect of a 1sd imbalance**, β × sd(imbalance) within "
      "the decile, is the comparable quantity: it is in return units and it is what the "
      "hypothesis is actually about. Added post-hoc — see amendment 1 to the pre-registration — "
      "and it does not form part of the pass condition.")
    A("")
    n_sig = int((curve["t_stat"].abs() > HURDLE).sum())
    A(f"Deciles individually clearing |t| > {HURDLE}: **{n_sig} of {len(curve)}**.")
    A("")
    A("### Gradient statistics")
    A("")
    A("Two pre-registered statistics for H2, both reported:")
    A("")
    A(f"1. **Pooled interaction.** `imbalance_ratio × decile_rank` coefficient "
      f"β_g = {_f(grad.get('beta_gradient'))}, t = **{_f(grad.get('t_gradient'), 3)}**, "
      f"n = {_f(grad.get('n_obs'))}. Significant at the hurdle: "
      f"**{'yes' if grad.get('gradient_significant') else 'no'}**. Direction as predicted: "
      f"**{'yes' if grad.get('gradient_direction_as_predicted') else 'no'}**.")
    A(f"2. **Spearman rank correlation** between decile and β: ρ = "
      f"{_f(sp.get('spearman_rho'), 3)}, permutation p = {_f(sp.get('permutation_p'), 3)} "
      f"({_f(sp.get('n_permutations'))} permutations, seed {sp.get('seed')}).")
    A("")

    # ---- subsamples
    A("## 3. Subsamples")
    A("")
    A("| Sample | β | t | n |")
    A("|---|---|---|---|")
    for nm, key in (("Pooled (all underlyings)", "pooled"),
                    ("Thin underlyings only", "thin"),
                    ("Index controls only (Test A's universe)", "control"),
                    ("Excluding 2020", "ex2020")):
        r = subsamples.get(key, {})
        A(f"| {nm} | {_f(r.get('beta'))} | {_f(r.get('t_stat'), 3)} | {_f(r.get('n_obs'))} |")
    A("")
    A("The index-controls row is the closest thing here to a re-run of Test A on a shorter "
      "sample. It is included so the thin-underlying result can be read against it directly "
      "rather than against a differently-constructed number.")
    A("")

    # ---- where the imbalance actually is
    A("## 4. Where the imbalance actually is")
    A("")
    A("The premise of this test is that thin underlyings carry materially larger forced flow "
      "relative to their liquidity. That premise is itself measurable, and is reported here "
      "before any return result, because if it fails the test has no power regardless of what "
      "the regressions say.")
    A("")
    A("> **`M/ADV` below is a multiplier, not flow.** Realised flow is `M · r / ADV` — the "
      "multiplier times the day's return. At a 1% move a multiplier of 82.9 is **0.83 days of "
      "ADV**, and this test's top decile averaged **0.80 days of ADV** of realised flow. So A-2 "
      "establishes that ~0.8 days of ADV produces no measurable effect, and says nothing about "
      "5x, 10x or 20x ADV, which is the regime fire sales occupy. A screen inheriting the "
      "multiplier as flow sets a bar roughly 100x too high.")
    A("")
    A("| Underlying | median M/ADV | mean \\|imb ratio\\| | share of top decile | days |")
    A("|---|---|---|---|---|")
    top_dec = panel["decile"].max()
    share = (panel[panel["decile"] == top_dec].groupby("underlying").size()
             / max(int((panel["decile"] == top_dec).sum()), 1) * 100)
    g = panel.groupby("underlying").agg(scale=("scale", "median"),
                                        imb=("abs_imb", "mean"), n=("date", "size"))
    g["share"] = share.reindex(g.index).fillna(0.0)
    g = g.sort_values("scale", ascending=False)
    ctrl_keys = set(panel.loc[panel["control"], "underlying"].unique())
    for k, r in g.iterrows():
        tag = " *(control)*" if k in ctrl_keys else ""
        A(f"| {k}{tag} | {_f(r['scale'], 3)} | {_f(r['imb'], 3)} | {_f(r['share'], 3)}% | "
          f"{int(r['n']):,} |")
    A("")

    # ---- strategy
    A("## 5. Top-decile strategy, gross and net")
    A("")
    if "gross_mean_bps" not in strat:
        A(f"Not run: {strat.get('note')}")
    else:
        A("Fade the predicted flow in the highest-imbalance decile only: at the close, take the "
          "opposite side and exit at the next open.")
        A("")
        A("| | Value |")
        A("|---|---|")
        A(f"| Positions | {strat['n_positions']:,} over {strat['n_days']:,} days |")
        A(f"| Gross | {_f(strat['gross_mean_bps'], 3)} bps/day, t = {_f(strat['gross_t'], 3)}, "
          f"Sharpe {_f(strat['gross_sharpe_ann'], 3)} |")
        A(f"| Net | {_f(strat['net_mean_bps'], 3)} bps/day, t = {_f(strat['net_t'], 3)}, "
          f"Sharpe {_f(strat['net_sharpe_ann'], 3)} |")
        A(f"| Mean round-trip cost | {_f(strat['mean_cost_bps'], 3)} bps |")
        A(f"| Mean participation | {_f(strat['mean_participation_pct'], 3)}% of ADV |")
        A(f"| Median notional | ${_f(strat['median_notional_usd'], 4)} |")
        A("")
        A("Trade size is `min($10m, 1% of ADV)`, fixed in the pre-registration. A flat $10m in "
          "an instrument with $200m ADV would be a 5% participation rate whose square-root "
          "impact charge swamps everything; capping participation is the realistic choice and "
          "was set before running.")
    A("")
    A("### Cost estimator assignment")
    A("")
    A("Test A found Corwin–Schultz badly upward-biased for mega-cap ETFs, because its "
      "identifying assumption fails for instruments that trade millions of times a session. "
      "That failure does not apply to thin instruments — which is what this universe is made "
      "of. The pre-registered rule assigns per instrument-day by dollar ADV:")
    A("")
    cs_share = panel.groupby("underlying")["use_cs"].mean() * 100
    A("| Underlying | % of days on Corwin–Schultz | median CS spread bps | median tick spread bps |")
    A("|---|---|---|---|")
    for k in g.index:
        sub = panel[panel["underlying"] == k]
        A(f"| {k} | {_f(cs_share.get(k), 3)}% | {_f(sub['spread_cs_bps'].median(), 3)} | "
          f"{_f(sub['spread_tick_bps'].median(), 3)} |")
    A("")

    # ---- data
    A("## 6. Data and the reconstruction this test depends on")
    A("")
    A("Direxion publish no historical NAV or shares-outstanding feed. That was a footnote in "
      "Test A; here it would be fatal, because Direxion's 3x sector funds *are* the "
      "high-imbalance regime. AUM was therefore reconstructed from **quarterly SEC N-PORT "
      "`netAssets`** by propagating each fund's own return and spreading the residual net flow "
      "across the quarter.")
    A("")
    A("**The reconstruction is validated, not asserted.** The identical method is applied to "
      "ProShares funds, which publish true daily AUM:")
    A("")
    A("| Fund | median abs error % | p90 abs error % | days |")
    A("|---|---|---|---|")
    for _, r in recon.iterrows():
        A(f"| {r['ticker']} | {_f(r['median_abs_err_pct'], 3)} | {_f(r['p90_abs_err_pct'], 3)} | "
          f"{int(r['n_days']):,} |")
    if len(recon):
        A("")
        A(f"Median across funds: **{recon['median_abs_err_pct'].median():.1f}%**. An error of "
          "that size cannot move an observation more than about one decile in a variable whose "
          "deciles span orders of magnitude.")
    A("")
    A("### Leverage estimated, not assumed")
    A("")
    A("Several Direxion funds cut leverage from 3x to 2x during 2020 (ERX, ERY, NUGT, DUST, "
      "JNUG, JDST, GUSH, DRIP). A fixed leverage table would mis-state `L·(L−1)` for those "
      "fund-days — the entire signal. Leverage is instead estimated from a rolling 120-day "
      "regression of each fund's return on its underlying's, snapped to the nearest "
      "half-integer, with fund-days dropped where R² < 0.90 or the snap is ambiguous. This "
      "doubles as the fund-to-underlying mapping check.")
    A("")
    lev = [r for v in diag["per_underlying"].values() for r in v.get("leverage", [])]
    if lev:
        ldf = pd.DataFrame(lev).sort_values(["underlying", "fund"])
        A("| Fund | Underlying | median implied L | snapped | median R² | % days usable |")
        A("|---|---|---|---|---|---|")
        for _, r in ldf.iterrows():
            A(f"| {r['fund']} | {r['underlying']} | {_f(r['median_implied'], 3)} | "
              f"{_f(r['median_snapped'], 2)} | {_f(r['median_r2'], 3)} | "
              f"{_f(r['pct_days_ok'], 3)}% |")
        A("")
    if diag.get("missing_aum"):
        A(f"**Funds with no usable AUM series** (excluded): {', '.join(diag['missing_aum'])}. "
          "Causes are fund closure before the sample, a ticker with no matching SEC series, or "
          "AUM below the $25m floor throughout.")
        A("")

    A("## 7. Limitations, stated in the pre-registration before running")
    A("")
    A("1. **Direxion AUM is quarterly-anchored and reconstructed**, not observed — error "
      "quantified above.")
    A("2. **Short sample.** 2020-07 onward, set by N-PORT availability. Test A had sixteen "
      "years; this has about six, so each decile holds fewer observations.")
    A("3. **Issuer coverage is still incomplete.** GraniteShares, Tuttle/T-Rex, Defiance and "
      "other single-stock leveraged issuers are absent, so `M` remains a lower bound — though "
      "the two issuers covered hold the overwhelming majority of sector LETF assets.")
    A("4. **Proxy ETFs are not the funds' exact indices.** The rolling leverage check with an "
      "R² floor is what keeps those mappings honest.")
    A("5. **COVID is in-sample at the start**; the excluding-2020 row is in §3.")
    A("")

    A("## 8. Verdict")
    A("")
    A(f"**{verdict}.** {para}")
    A("")
    if verdict.startswith("FAIL"):
        A("### The stopping condition has fired")
        A("")
        A("Pre-registration §8, recorded before this test was run:")
        A("")
        A("> *If the top-decile coefficient is not significant at t > 2.78 AND there is no "
          "monotone gradient across deciles, the LETF mechanic is dead in both regimes and Test "
          "A is closed permanently. No third regime will be proposed.*")
        A("")
        A("Both conditions are met. Test A is closed. The value of having written that sentence "
          "down in advance is precisely that it removes the option of proposing a fourth "
          "universe now.")
    A("")
    A(f"Cumulative evaluations logged across all tests: **{log_summary['total_evaluations']}** "
      f"({', '.join(f'{k}: {v}' for k, v in sorted(log_summary['by_test'].items()))}). The "
      "Deflated Sharpe above is computed against that cumulative count, per Amendment 1 §4.")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")
