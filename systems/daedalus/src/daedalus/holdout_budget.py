from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from typing import Any

from .config import HoldoutBudgetConfig


@dataclass(frozen=True)
class HoldoutSelection:
    budget: int
    qualified: int
    selected_indices: tuple[int, ...]
    rejected_indices: tuple[int, ...]
    symbol_counts: dict[str, int]
    mechanics_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def development_rank_key(report: dict[str, Any]) -> tuple[float, float, float, float, int]:
    """Rank using development-only evidence; no protected-tail fields are consulted."""
    gate = report.get("development_gate") or {}
    evidence = gate.get("evidence") or {}
    champion = report.get("development_champion_metrics") or {}
    return (
        float(evidence.get("auc", champion.get("auc", 0.5))),
        float(evidence.get("brier_improvement", champion.get("brier_improvement", -1.0))),
        float(evidence.get("fold_pass_rate", report.get("development_weighted_fold_pass_rate", 0.0))),
        float(champion.get("trade_sharpe_like", -999.0)),
        int(evidence.get("trade_count", champion.get("trade_count", 0))),
    )


def select_holdout_exposures(
    reports: list[dict[str, Any]],
    cfg: HoldoutBudgetConfig,
) -> HoldoutSelection:
    qualified = [i for i, r in enumerate(reports) if r.get("status") == "development_qualified"]
    if not qualified:
        return HoldoutSelection(0, 0, (), (), {}, {})

    if cfg.enabled:
        fractional = max(1, ceil(len(qualified) * cfg.max_exposure_fraction))
        budget = min(cfg.max_exposures, fractional)
    else:
        budget = len(qualified)

    ordered = sorted(qualified, key=lambda i: development_rank_key(reports[i]), reverse=True)
    selected: list[int] = []
    symbol_counts: dict[str, int] = {}
    mechanics_counts: dict[str, int] = {}

    for i in ordered:
        if len(selected) >= budget:
            break
        report = reports[i]
        identity = report.get("identity") or {}
        profile = report.get("profile") or {}
        symbol = str(identity.get("canonical_symbol") or profile.get("symbol_hint") or "UNKNOWN")
        mechanics = str(profile.get("mechanics_class") or "UNKNOWN")
        if cfg.enabled:
            if symbol_counts.get(symbol, 0) >= cfg.max_per_canonical_symbol:
                continue
            if mechanics_counts.get(mechanics, 0) >= cfg.max_per_mechanics_class:
                continue
        selected.append(i)
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        mechanics_counts[mechanics] = mechanics_counts.get(mechanics, 0) + 1

    selected_set = set(selected)
    rejected = tuple(i for i in ordered if i not in selected_set)
    return HoldoutSelection(
        budget=budget,
        qualified=len(qualified),
        selected_indices=tuple(selected),
        rejected_indices=rejected,
        symbol_counts=symbol_counts,
        mechanics_counts=mechanics_counts,
    )
