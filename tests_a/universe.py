"""Test A universe definition (pre-registration §3).

Fixed before analysis. Do not edit to improve a result; add an amendment to
tests_a/preregistration.md instead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fund:
    ticker: str
    leverage: float

    @property
    def rebalance_coeff(self) -> float:
        """L * (L - 1) -- the multiplier on A * r in the required rebalance trade.

        Positive for every |L| >= 2 fund, long or inverse: both buy on up days.
        Inverse funds carry the *larger* coefficient (-3 gives 12, +3 gives 6).
        """
        return self.leverage * (self.leverage - 1.0)


@dataclass(frozen=True)
class Underlying:
    key: str
    name: str
    index_symbol: str
    proxy_etf: str
    funds: tuple[Fund, ...]


UNIVERSE: tuple[Underlying, ...] = (
    Underlying(
        key="SPX", name="S&P 500", index_symbol="^GSPC", proxy_etf="SPY",
        funds=(Fund("SSO", 2.0), Fund("SDS", -2.0), Fund("UPRO", 3.0), Fund("SPXU", -3.0)),
    ),
    Underlying(
        key="NDX", name="Nasdaq-100", index_symbol="^NDX", proxy_etf="QQQ",
        funds=(Fund("QLD", 2.0), Fund("QID", -2.0), Fund("TQQQ", 3.0), Fund("SQQQ", -3.0)),
    ),
    Underlying(
        key="RUT", name="Russell 2000", index_symbol="^RUT", proxy_etf="IWM",
        funds=(Fund("UWM", 2.0), Fund("TWM", -2.0), Fund("URTY", 3.0), Fund("SRTY", -3.0)),
    ),
    Underlying(
        key="DJI", name="Dow Jones Industrial Average", index_symbol="^DJI", proxy_etf="DIA",
        funds=(Fund("DDM", 2.0), Fund("DXD", -2.0), Fund("UDOW", 3.0), Fund("SDOW", -3.0)),
    ),
)

SAMPLE_START = "2010-03-01"     # pre-registration §3; 3x inception Feb 2010 + 21d ADV warm-up
ADV_WINDOW = 21                 # trading days
FFILL_LIMIT = 5                 # pre-registration §5 rule 1
MIN_FUNDS_PER_DAY = 2           # pre-registration §5 rule 2 (half of 4)

ALL_FUNDS = tuple(f.ticker for u in UNIVERSE for f in u.funds)
ALL_SYMBOLS = tuple([u.index_symbol for u in UNIVERSE] + [u.proxy_etf for u in UNIVERSE])


def by_key(key: str) -> Underlying:
    for u in UNIVERSE:
        if u.key == key:
            return u
    raise KeyError(key)
