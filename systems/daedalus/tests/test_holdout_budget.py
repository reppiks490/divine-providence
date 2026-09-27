from daedalus.config import HoldoutBudgetConfig
from daedalus.holdout_budget import select_holdout_exposures


def _report(symbol: str, mechanics: str, auc: float):
    return {
        "status": "development_qualified",
        "identity": {"canonical_symbol": symbol},
        "profile": {"mechanics_class": mechanics, "symbol_hint": symbol},
        "development_gate": {
            "evidence": {
                "auc": auc,
                "brier_improvement": 0.01,
                "fold_pass_rate": 0.75,
                "trade_count": 50,
            }
        },
        "development_champion_metrics": {"trade_sharpe_like": 0.5},
    }


def test_budget_ranks_on_development_only_and_limits_exposures():
    reports = [
        _report("NQ", "time_regular", 0.56),
        _report("ES", "time_regular", 0.61),
        _report("YM", "event_irregular", 0.58),
        _report("VXN", "event_irregular", 0.54),
    ]
    cfg = HoldoutBudgetConfig(max_exposures=2, max_exposure_fraction=0.50)
    selected = select_holdout_exposures(reports, cfg)
    assert selected.budget == 2
    assert selected.qualified == 4
    assert selected.selected_indices == (1, 2)


def test_budget_enforces_symbol_and_mechanics_diversity():
    reports = [
        _report("NQ", "time_regular", 0.64),
        _report("NQ", "time_regular", 0.63),
        _report("ES", "time_regular", 0.62),
        _report("YM", "event_irregular", 0.61),
    ]
    cfg = HoldoutBudgetConfig(
        max_exposures=4,
        max_exposure_fraction=0.99,
        max_per_canonical_symbol=1,
        max_per_mechanics_class=2,
    )
    selected = select_holdout_exposures(reports, cfg)
    assert 0 in selected.selected_indices
    assert 1 not in selected.selected_indices
    assert len(selected.selected_indices) == 3
    assert selected.symbol_counts["NQ"] == 1
    assert selected.mechanics_counts["time_regular"] == 2
