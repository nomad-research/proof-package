"""Inference-family tagging and effective breadth (spec section 5.5).

Every enumerated link carries an inference family -- the *kind* of reasoning that
put it in the set, e.g. "covenant -> forced sale", "rating -> mandate
ineligibility", "product mechanic -> rebalance".

Once outcomes are known, errors are correlated within and across families. If
errors cluster tightly by family then effective breadth is roughly the number of
families, not the number of links, and position sizing that assumes the latter is
wrong by a factor of sqrt(links/families).

This has to be tagged at enumeration time. It cannot be retrofitted, because
after the fact the analyst knows which links worked and the family assignment
stops being independent of the outcome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


class InferenceFamily:
    """Canonical family labels. Add deliberately -- a proliferation of families
    silently inflates apparent breadth, which is the error this module exists to
    prevent."""

    COVENANT_FORCED_SALE = "covenant->forced_sale"
    RATING_MANDATE_INELIGIBILITY = "rating->mandate_ineligibility"
    INDEX_RULE_DELETION = "index_rule->deletion"
    PRODUCT_MECHANIC_REBALANCE = "product_mechanic->rebalance"
    REGULATORY_CAPITAL_DEADLINE = "regulatory_capital->deadline_sale"
    FUND_LIQUIDATION_REDEMPTION = "fund_liquidation->redemption"
    MARGIN_CALL_CASCADE = "margin_call->cascade"
    CORPORATE_ACTION_PRORATION = "corporate_action->proration"

    @classmethod
    def all(cls) -> list[str]:
        return [v for k, v in vars(cls).items() if isinstance(v, str) and not k.startswith("_")]


@dataclass
class Link:
    """One enumerated edge: root event -> condition -> rule -> actor -> destination."""

    link_id: str
    event_id: str
    family: str
    destination: str                     # instrument / issuer the forced capital must reach
    actor: str | None = None             # who is forced
    condition: str | None = None         # condition Y that triggers
    rule_ref: str | None = None          # rule Z that binds
    doc_id: str | None = None            # retrieved document in the PIT corpus
    clause_id: str | None = None         # located clause within it
    verified: bool = False
    quarantined: bool = False
    quarantine_reason: str | None = None
    tagged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.family:
            raise ValueError(f"link {self.link_id} has no inference family; tagging is mandatory at enumeration time")
        if self.verified and not (self.doc_id and self.clause_id):
            raise ValueError(
                f"link {self.link_id} claims verification without a document and located clause"
            )

    def to_dict(self) -> dict:
        return asdict(self)


class LinkRegistry:
    """Append-only registry of enumerated links, with a separate quarantine.

    Quarantined links -- those whose document could not be retrieved or whose
    clause could not be located -- are stored, never silently dropped, and the
    quarantine rate is reported.
    """

    def __init__(self, path: str | Path = "data/links.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._links: list[Link] = []
        if self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        self._links.append(Link(**json.loads(line)))

    def add(self, link: Link) -> None:
        self._links.append(link)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(link.to_dict(), sort_keys=True) + "\n")

    def quarantine(self, link: Link, reason: str) -> None:
        link.quarantined = True
        link.quarantine_reason = reason
        link.verified = False
        self.add(link)

    @property
    def links(self) -> list[Link]:
        return list(self._links)

    def active(self, event_id: str | None = None) -> list[Link]:
        """Links that entered the graph: verified and not quarantined."""
        out = [l for l in self._links if l.verified and not l.quarantined]
        if event_id is not None:
            out = [l for l in out if l.event_id == event_id]
        return out

    def quarantine_rate(self) -> dict[str, Any]:
        n = len(self._links)
        q = sum(1 for l in self._links if l.quarantined)
        by_family: dict[str, dict[str, int]] = {}
        for l in self._links:
            d = by_family.setdefault(l.family, {"total": 0, "quarantined": 0})
            d["total"] += 1
            d["quarantined"] += int(l.quarantined)
        return {
            "n_links": n,
            "n_quarantined": q,
            "rate": (q / n) if n else float("nan"),
            "by_family": by_family,
        }

    def family_counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for l in self.active():
            c[l.family] = c.get(l.family, 0) + 1
        return c


# ------------------------------------------------------------------ breadth


def error_matrix(outcomes: pd.DataFrame, error_col: str = "error",
                 link_col: str = "link_id", period_col: str = "period") -> pd.DataFrame:
    """Pivot per-link errors into a period x link matrix for correlation analysis."""
    return outcomes.pivot_table(index=period_col, columns=link_col, values=error_col)


def effective_breadth(errors: pd.DataFrame) -> dict[str, Any]:
    """Effective number of independent bets given correlated link errors.

    For N equally weighted unit-variance bets with correlation matrix C, the
    portfolio variance is (1'C1)/N^2, and N independent bets would give 1/N.
    Equating gives

        N_eff = N^2 / (1' C 1)

    which collapses to N when C is the identity and to 1 when every error is
    perfectly correlated.
    """
    C = errors.corr()
    n = C.shape[0]
    if n == 0:
        return {"n_links": 0, "effective_breadth": float("nan")}
    total = float(np.nansum(C.values))
    if total <= 0:
        return {"n_links": n, "effective_breadth": float("nan"),
                "note": "non-positive correlation sum; breadth undefined"}
    n_eff = n ** 2 / total
    off = C.values[~np.eye(n, dtype=bool)]
    return {
        "n_links": n,
        "effective_breadth": float(n_eff),
        "breadth_ratio": float(n_eff / n),
        "mean_pairwise_corr": float(np.nanmean(off)) if off.size else float("nan"),
        "sizing_overstatement_factor": float(np.sqrt(n / n_eff)) if n_eff > 0 else float("nan"),
    }


def family_error_correlation(errors: pd.DataFrame, families: dict[str, str]) -> dict[str, Any]:
    """Decompose error correlation into within-family and cross-family components.

    `families` maps link_id -> family label.

    If within-family correlation is high and cross-family correlation is near
    zero, effective breadth is approximately the family count, and that -- not the
    link count -- is what position sizing should use.
    """
    C = errors.corr()
    links = list(C.columns)
    fam = np.array([families.get(l, "unknown") for l in links])
    n = len(links)
    if n < 2:
        return {"note": "need >= 2 links", "n_links": n}

    same = fam[:, None] == fam[None, :]
    off_diag = ~np.eye(n, dtype=bool)
    vals = C.values

    within = vals[same & off_diag]
    across = vals[~same & off_diag]

    per_family: dict[str, Any] = {}
    for f in sorted(set(fam)):
        idx = np.where(fam == f)[0]
        if len(idx) >= 2:
            sub = vals[np.ix_(idx, idx)]
            o = sub[~np.eye(len(idx), dtype=bool)]
            per_family[f] = {"n_links": int(len(idx)), "mean_within_corr": float(np.nanmean(o))}
        else:
            per_family[f] = {"n_links": int(len(idx)), "mean_within_corr": float("nan")}

    n_families = len(set(fam))
    breadth = effective_breadth(errors)

    return {
        "n_links": n,
        "n_families": n_families,
        "mean_within_family_corr": float(np.nanmean(within)) if within.size else float("nan"),
        "mean_across_family_corr": float(np.nanmean(across)) if across.size else float("nan"),
        "per_family": per_family,
        "effective_breadth": breadth["effective_breadth"],
        "breadth_vs_links": breadth.get("breadth_ratio"),
        "breadth_vs_families": (breadth["effective_breadth"] / n_families) if n_families else float("nan"),
        "sizing_overstatement_factor": breadth.get("sizing_overstatement_factor"),
        "interpretation": _interpret(breadth["effective_breadth"], n, n_families),
    }


def _interpret(n_eff: float, n_links: int, n_families: int) -> str:
    if not np.isfinite(n_eff):
        return "effective breadth undefined"
    if n_eff >= 0.8 * n_links:
        return "errors largely independent; breadth approximately the link count"
    if n_eff <= 1.5 * n_families:
        return ("errors cluster by family; effective breadth is approximately the family count, "
                f"{n_families}, not the link count, {n_links}")
    return (f"partial clustering; effective breadth {n_eff:.1f} sits between "
            f"family count {n_families} and link count {n_links}")
