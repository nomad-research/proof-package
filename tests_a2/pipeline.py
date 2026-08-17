"""Test A-2 panel construction: leveraged ETF flow in thin underlyings.

Combines two AUM sources with very different resolution:
  ProShares -- exact daily AUM published by the issuer
  Direxion  -- quarterly SEC N-PORT net assets, interpolated to daily

and derives each fund's leverage from its own returns rather than assuming it,
because several Direxion funds changed leverage mid-sample.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from tests_a.pipeline import fetch_daily, fetch_fund_aum
from .nport import fetch_nport_aum, reconstruct_daily_aum, validate_reconstruction
from .universe import (
    ADV_WINDOW, ALL_FUNDS, ALL_PROXIES, DIREXION, LEV_MAX_SNAP_ERR, LEV_MIN_R2,
    LEV_WINDOW, MIN_FUND_AUM, PROSHARES, SAMPLE_START, UNIVERSE,
)


def _fund_prices(tickers) -> dict[str, pd.DataFrame]:
    out = {}
    for t in tickers:
        try:
            out[t] = fetch_daily(t, start="2018-01-01").set_index("date").sort_index()
        except Exception as e:
            print(f"    price fetch failed for {t}: {e}")
    return out


def rolling_leverage(fund_ret: pd.Series, proxy_ret: pd.Series) -> pd.DataFrame:
    """Rolling implied leverage and fit quality.

    slope = cov(fund, proxy) / var(proxy) over LEV_WINDOW days; R2 = corr^2.
    The slope is the fund's realised leverage whether or not it matches the
    prospectus, which is the point.
    """
    j = pd.concat([fund_ret.rename("f"), proxy_ret.rename("p")], axis=1).dropna()
    if len(j) < LEV_WINDOW:
        return pd.DataFrame(columns=["implied", "r2", "snapped", "ok"])
    cov = j["f"].rolling(LEV_WINDOW).cov(j["p"])
    var = j["p"].rolling(LEV_WINDOW).var()
    corr = j["f"].rolling(LEV_WINDOW).corr(j["p"])
    implied = cov / var
    snapped = (implied * 2).round() / 2.0
    ok = (corr ** 2 >= LEV_MIN_R2) & ((implied - snapped).abs() <= LEV_MAX_SNAP_ERR) \
         & (snapped.abs() >= 1.0)
    return pd.DataFrame({"implied": implied, "r2": corr ** 2,
                         "snapped": snapped, "ok": ok})


def build_aum(tickers, prices: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """Daily AUM per fund: exact for ProShares, reconstructed for Direxion."""
    nport = fetch_nport_aum(list(DIREXION))
    aum = {}
    for t in tickers:
        if t in PROSHARES:
            try:
                df = fetch_fund_aum(t)
                aum[t] = df.set_index("date")["aum"].dropna().sort_index()
            except Exception as e:
                print(f"    ProShares AUM failed for {t}: {e}")
        elif t in DIREXION:
            anc = nport[nport["ticker"] == t]
            if anc.empty or t not in prices:
                continue
            anchors = anc.set_index("report_date")["net_assets"].sort_index()
            fret = prices[t]["close"].pct_change()
            s = reconstruct_daily_aum(anchors, fret)
            if len(s):
                aum[t] = s
    return aum


def build_panel(verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    if verbose:
        print("Fetching proxy ETF prices...")
    proxies = _fund_prices(ALL_PROXIES)
    if verbose:
        print("Fetching leveraged fund prices...")
    fprices = _fund_prices(ALL_FUNDS)
    if verbose:
        print("Building AUM series...")
    aum = build_aum(ALL_FUNDS, fprices)

    diag = {"funds_with_aum": len(aum), "funds_requested": len(ALL_FUNDS),
            "missing_aum": sorted(set(ALL_FUNDS) - set(aum)), "per_underlying": {}}

    frames = []
    for u in UNIVERSE:
        if u.proxy_etf not in proxies:
            continue
        px = proxies[u.proxy_etf]
        cal = px.index[px.index >= pd.Timestamp(SAMPLE_START) - pd.Timedelta(days=400)]
        proxy_ret = px["close"].pct_change().reindex(cal)

        contribs, used, lev_rows = {}, [], []
        for f in u.funds:
            if f not in aum or f not in fprices:
                continue
            fret = fprices[f]["close"].pct_change()
            lev = rolling_leverage(fret, proxy_ret)
            if lev.empty:
                continue
            a = aum[f].reindex(cal).ffill(limit=5).shift(1)      # A[t-1], PIT
            L = lev["snapped"].reindex(cal)
            ok = lev["ok"].reindex(cal).fillna(False)
            a = a.where(a >= MIN_FUND_AUM)                       # AUM floor
            c = (a * L * (L - 1.0)).where(ok)
            if c.notna().sum() < 100:
                continue
            contribs[f] = c
            used.append(f)
            lev_rows.append({"fund": f, "underlying": u.key,
                             "median_implied": float(lev["implied"].median()),
                             "median_snapped": float(lev["snapped"].median()),
                             "median_r2": float(lev["r2"].median()),
                             "pct_days_ok": float(lev["ok"].mean() * 100),
                             "n_days": int(c.notna().sum())})

        if not contribs:
            diag["per_underlying"][u.key] = {"funds_used": 0, "rows": 0}
            continue

        C = pd.DataFrame(contribs)
        M = C.sum(axis=1, min_count=1)
        adv = (px["close"] * px["volume"]).reindex(cal).shift(1).rolling(
            ADV_WINDOW, min_periods=ADV_WINDOW).median()

        df = pd.DataFrame({
            "underlying": u.key, "control": u.control, "date": cal,
            "M": M.values, "n_funds": C.notna().sum(axis=1).values,
            "r_proxy": proxy_ret.values, "adv": adv.values,
            "proxy_close": px["close"].reindex(cal).values,
            "proxy_open": px["open"].reindex(cal).values,
            "proxy_high": px["high"].reindex(cal).values,
            "proxy_low": px["low"].reindex(cal).values,
        })
        df["r_on_next"] = df["proxy_open"].shift(-1) / df["proxy_close"] - 1.0
        df = df[df["date"] >= SAMPLE_START]
        n0 = len(df)
        df = df.dropna(subset=["M", "r_proxy", "adv", "r_on_next", "proxy_close"])
        df = df[df["M"] != 0]
        frames.append(df)
        diag["per_underlying"][u.key] = {
            "funds_used": len(used), "funds": used, "rows": len(df), "dropped": n0 - len(df),
            "leverage": lev_rows,
        }
        if verbose:
            print(f"  {u.key:11s} funds={len(used):2d} rows={len(df):5d} "
                  f"({', '.join(used)})")

    panel = pd.concat(frames, ignore_index=True)
    panel["scale"] = panel["M"] / panel["adv"]
    panel["imb_ratio"] = panel["M"] * panel["r_proxy"] / panel["adv"]
    panel["abs_imb"] = panel["imb_ratio"].abs()
    panel["year"] = panel["date"].dt.year
    panel = panel.sort_values(["date", "underlying"]).reset_index(drop=True)
    return panel, diag


def reconstruction_validation() -> pd.DataFrame:
    return validate_reconstruction(
        ["TQQQ", "SQQQ", "UPRO", "SPXU", "URTY", "SRTY", "UYG", "DIG", "BIB", "FXP"])


if __name__ == "__main__":
    p, d = build_panel()
    print(f"\nPanel: {len(p)} underlying-days, "
          f"{p['date'].min().date()} -> {p['date'].max().date()}")
    print(f"Underlyings: {p['underlying'].nunique()}")
    print("\nScale (M/ADV) by underlying, median:")
    print(p.groupby("underlying")["scale"].median().sort_values(ascending=False).to_string())
    print("\nReconstruction validation:")
    print(reconstruction_validation().to_string(index=False))
