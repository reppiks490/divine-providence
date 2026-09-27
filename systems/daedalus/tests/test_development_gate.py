import numpy as np

from daedalus.config import DevelopmentGateConfig
from daedalus.development_gate import assess_development_candidate
from daedalus.validation import ValidationResult


def _result(auc=0.60, brier=0.01, pass_rate=0.5, trades=40, folds=2):
    fake_folds = tuple(object() for _ in range(folds))
    return ValidationResult(
        model_name="x",
        folds=fake_folds,  # only len() is used by the gate
        aggregate={"auc": auc, "brier_improvement": brier, "trade_count": trades},
        fold_pass_rate=pass_rate,
        dev_end=100,
        oof_positions=np.arange(10),
        oof_y=np.zeros(10, dtype=int),
        oof_probabilities=np.full(10, 0.5),
        oof_future_returns=np.zeros(10),
    )


def test_development_gate_passes_candidate_that_earned_holdout():
    d = assess_development_candidate(_result(), DevelopmentGateConfig())
    assert d.passed
    assert not d.failed_checks


def test_development_gate_rejects_weak_candidate_before_holdout():
    d = assess_development_candidate(
        _result(auc=0.49, brier=-0.2, pass_rate=0.0),
        DevelopmentGateConfig(),
    )
    assert not d.passed
    assert "auc" in d.failed_checks
    assert "brier_improvement" in d.failed_checks
    assert "fold_pass_rate" in d.failed_checks


def test_development_gate_can_be_disabled_for_diagnostics():
    d = assess_development_candidate(
        _result(auc=0.49, brier=-0.2, pass_rate=0.0),
        DevelopmentGateConfig(enabled=False),
    )
    assert d.passed
    assert d.failed_checks == ()
