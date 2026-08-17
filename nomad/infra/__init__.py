"""Shared infrastructure for the Nomad gate tests (spec section 5).

Built once, used across Tests A, B and C.
"""

from .config_logger import ConfigLogger, trial_count, read_log, summarise  # noqa: F401
from .cost_model import (  # noqa: F401
    CostParams,
    apply_costs,
    corwin_schultz_spread,
    cost_summary,
    realised_volatility,
    round_trip_cost_bps,
    tick_spread_bps,
)
from .deflated_sharpe import (  # noqa: F401
    deflated_sharpe_ratio,
    haircut_hurdle_t,
    probability_of_backtest_overfitting,
    sharpe_stats,
)
from .inference_family import (  # noqa: F401
    InferenceFamily,
    Link,
    LinkRegistry,
    effective_breadth,
    family_error_correlation,
)
from .pit_corpus import PITCorpus, Document, Clause  # noqa: F401

__all__ = [
    "ConfigLogger", "trial_count", "read_log", "summarise",
    "CostParams", "apply_costs", "corwin_schultz_spread", "cost_summary",
    "realised_volatility", "round_trip_cost_bps", "tick_spread_bps",
    "deflated_sharpe_ratio", "haircut_hurdle_t",
    "probability_of_backtest_overfitting", "sharpe_stats",
    "InferenceFamily", "Link", "LinkRegistry", "effective_breadth",
    "family_error_correlation",
    "PITCorpus", "Document", "Clause",
]
