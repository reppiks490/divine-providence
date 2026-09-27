from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import DevelopmentGateConfig
from .validation import ValidationResult


@dataclass(frozen=True)
class DevelopmentGateDecision:
    passed: bool
    passed_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]
    evidence: dict[str, float | int]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_development_candidate(
    champion: ValidationResult,
    cfg: DevelopmentGateConfig,
) -> DevelopmentGateDecision:
    """Decide whether a development-only candidate is allowed to expose the final tail.

    This gate uses only walk-forward development evidence. Its purpose is not to prove
    an edge; it is to avoid spending pristine holdout data on candidates that have not
    earned a final test.
    """
    metrics = champion.aggregate
    evidence: dict[str, float | int] = {
        "auc": float(metrics.get("auc", 0.5)),
        "brier_improvement": float(metrics.get("brier_improvement", -1.0)),
        "fold_pass_rate": float(champion.fold_pass_rate),
        "trade_count": int(metrics.get("trade_count", 0)),
        "completed_folds": int(len(champion.folds)),
    }
    checks = {
        "auc": evidence["auc"] >= cfg.min_auc,
        "brier_improvement": evidence["brier_improvement"] >= cfg.min_brier_improvement,
        "fold_pass_rate": evidence["fold_pass_rate"] >= cfg.min_fold_pass_rate,
        "trade_count": evidence["trade_count"] >= cfg.min_trade_count,
        "completed_folds": evidence["completed_folds"] >= cfg.min_completed_folds,
    }
    passed = tuple(k for k, ok in checks.items() if ok)
    failed = tuple(k for k, ok in checks.items() if not ok)
    return DevelopmentGateDecision(
        passed=(not failed) or (not cfg.enabled),
        passed_checks=passed,
        failed_checks=failed if cfg.enabled else (),
        evidence=evidence,
    )
