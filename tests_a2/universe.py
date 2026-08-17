"""Test A-2 universe: leveraged and inverse ETFs on thinner underlyings.

Fixed before analysis. The index underlyings from Test A are retained as controls
-- they are the low-imbalance end of the cross-section and the decile test needs
that end to establish a gradient.

Leverage is **not** hardcoded. Several Direxion funds changed their stated
leverage mid-life (the 3x-to-2x reductions of 2020 hit ERX, ERY, NUGT, DUST,
JNUG, JDST, GUSH and DRIP), so a fixed table would silently mis-state
`L·(L−1)` for those fund-days -- and `L·(L−1)` is the whole signal. Instead each
fund's leverage is estimated from a rolling regression of its own daily return on
its underlying's, snapped to the nearest half-integer, and fund-days where the
fit is poor or the snap is ambiguous are dropped. This handles the changes
automatically and doubles as the data-quality check.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Underlying:
    key: str
    name: str
    proxy_etf: str          # liquidity denominator and traded instrument
    funds: tuple[str, ...]  # leveraged/inverse ETFs on this underlying
    control: bool = False   # True for the mega-cap index underlyings from Test A


UNIVERSE: tuple[Underlying, ...] = (
    # ---- thin underlyings: the regime the amendment is about ----
    Underlying("SEMI", "Semiconductors", "SOXX", ("SOXL", "SOXS", "USD", "SSG")),
    Underlying("BIOTECH", "Biotechnology", "XBI", ("LABU", "LABD", "BIB", "BIS")),
    Underlying("FIN", "Financials", "XLF", ("FAS", "FAZ", "UYG", "SKF")),
    Underlying("TECH", "Technology", "XLK", ("TECL", "TECS", "ROM", "REW")),
    Underlying("ENERGY", "Energy", "XLE", ("ERX", "ERY", "DIG", "DUG")),
    Underlying("REALESTATE", "Real estate", "IYR", ("DRN", "DRV", "URE", "SRS")),
    Underlying("UTIL", "Utilities", "XLU", ("UTSL", "UPW", "SDP")),
    Underlying("HEALTH", "Health care", "XLV", ("CURE", "RXL", "RXD")),
    Underlying("INDU", "Industrials", "XLI", ("DUSL", "UXI", "SIJ")),
    Underlying("MATERIALS", "Basic materials", "XLB", ("UYM", "SMN")),
    Underlying("CHINA", "China", "FXI", ("YINN", "YANG", "XPP", "FXP")),
    Underlying("BRAZIL", "Brazil", "EWZ", ("BRZU", "UBR", "BZQ")),
    Underlying("REGBANK", "Regional banks", "KRE", ("DPST",)),
    Underlying("HOMEBUILD", "Home construction", "ITB", ("NAIL",)),
    Underlying("RETAIL", "Retail", "XRT", ("RETL",)),
    Underlying("GOLDMINER", "Gold miners", "GDX", ("NUGT", "DUST")),
    Underlying("JRGOLD", "Junior gold miners", "GDXJ", ("JNUG", "JDST")),
    Underlying("OILGAS_EP", "Oil & gas E&P", "XOP", ("GUSH", "DRIP")),
    Underlying("INTERNET", "Internet", "FDN", ("WEBL", "WEBS")),

    # ---- mega-cap index controls: the regime Test A already tested ----
    Underlying("SPX", "S&P 500", "SPY", ("SPXL", "SPXS", "UPRO", "SPXU", "SSO", "SDS"),
               control=True),
    Underlying("NDX", "Nasdaq-100", "QQQ", ("TQQQ", "SQQQ", "QLD", "QID"), control=True),
    Underlying("RUT", "Russell 2000", "IWM", ("TNA", "TZA", "URTY", "SRTY", "UWM", "TWM"),
               control=True),
    Underlying("DJI", "Dow Jones Industrial Average", "DIA",
               ("UDOW", "SDOW", "DDM", "DXD"), control=True),
)

PROSHARES = {
    "USD", "SSG", "BIB", "BIS", "UYG", "SKF", "ROM", "REW", "DIG", "DUG", "URE", "SRS",
    "UPW", "SDP", "RXL", "RXD", "UXI", "SIJ", "UYM", "SMN", "XPP", "FXP", "UBR", "BZQ",
    "UPRO", "SPXU", "SSO", "SDS", "TQQQ", "SQQQ", "QLD", "QID",
    "URTY", "SRTY", "UWM", "TWM", "UDOW", "SDOW", "DDM", "DXD",
}
DIREXION = {
    "SOXL", "SOXS", "LABU", "LABD", "FAS", "FAZ", "TECL", "TECS", "ERX", "ERY",
    "DRN", "DRV", "UTSL", "CURE", "DUSL", "YINN", "YANG", "BRZU", "DPST", "NAIL",
    "RETL", "NUGT", "DUST", "JNUG", "JDST", "GUSH", "DRIP", "WEBL", "WEBS",
    "SPXL", "SPXS", "TNA", "TZA",
}

ALL_FUNDS = tuple(sorted({f for u in UNIVERSE for f in u.funds}))
ALL_PROXIES = tuple(sorted({u.proxy_etf for u in UNIVERSE}))

# --- pre-registered parameters (see preregistration.md) ---
SAMPLE_START = "2020-07-01"   # two N-PORT anchors plus leverage warm-up
ADV_WINDOW = 21
LEV_WINDOW = 120              # rolling window for implied leverage
LEV_MIN_R2 = 0.90             # below this the fund/underlying mapping is not trusted
LEV_MAX_SNAP_ERR = 0.35       # |implied − snapped| above this drops the fund-day
MIN_FUND_AUM = 25_000_000     # AUM floor: below this a fund is noise, not signal
N_DECILES = 10


def fund_underlying() -> dict[str, str]:
    return {f: u.key for u in UNIVERSE for f in u.funds}


def by_key(key: str) -> Underlying:
    for u in UNIVERSE:
        if u.key == key:
            return u
    raise KeyError(key)
