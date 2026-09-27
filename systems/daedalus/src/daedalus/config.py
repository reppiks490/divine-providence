from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _positive(name: str, value: float | int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")


def _unit_interval(name: str, value: float, *, open_interval: bool = False) -> None:
    ok = 0.0 < value < 1.0 if open_interval else 0.0 <= value <= 1.0
    if not ok:
        bracket = "(0, 1)" if open_interval else "[0, 1]"
        raise ValueError(f"{name} must be in {bracket}, got {value}")


@dataclass(frozen=True)
class DataConfig:
    min_rows: int = 750
    max_rows_per_file: int | None = None
    required_columns: tuple[str, ...] = ("time", "open", "high", "low", "close")
    require_nondecreasing_time: bool = True
    reject_nonfinite_required_rows: bool = True

    def __post_init__(self) -> None:
        _positive("data.min_rows", self.min_rows)
        if self.max_rows_per_file is not None:
            _positive("data.max_rows_per_file", self.max_rows_per_file)
            if self.max_rows_per_file < self.min_rows:
                raise ValueError("data.max_rows_per_file cannot be smaller than data.min_rows")
        if not self.required_columns:
            raise ValueError("data.required_columns cannot be empty")


@dataclass(frozen=True)
class FeatureConfig:
    return_windows: tuple[int, ...] = (1, 2, 3, 5, 10, 20, 50)
    vol_windows: tuple[int, ...] = (5, 10, 20, 50)
    range_windows: tuple[int, ...] = (5, 20, 50)
    volume_windows: tuple[int, ...] = (5, 20, 50)
    target_horizon: int = 5
    target_threshold_bps: float = 0.0
    feature_lag_bars: int = 1
    include_bar_mechanics: bool = True
    include_utc_calendar: bool = True
    min_row_feature_coverage: float = 0.70

    def __post_init__(self) -> None:
        _positive("features.target_horizon", self.target_horizon)
        _positive("features.feature_lag_bars", self.feature_lag_bars)
        if self.target_threshold_bps < 0:
            raise ValueError("features.target_threshold_bps must be >= 0")
        _unit_interval("features.min_row_feature_coverage", self.min_row_feature_coverage, open_interval=True)
        for name, values in (
            ("return_windows", self.return_windows),
            ("vol_windows", self.vol_windows),
            ("range_windows", self.range_windows),
            ("volume_windows", self.volume_windows),
        ):
            if not values or any(int(v) <= 0 for v in values):
                raise ValueError(f"features.{name} must be non-empty and all values > 0")


@dataclass(frozen=True)
class ValidationConfig:
    n_splits: int = 5
    min_train_size: int = 500
    test_size: int = 250
    purge_bars: int = 5
    embargo_bars: int = 5
    protected_holdout_size: int | None = None
    protected_holdout_fraction: float = 0.20
    protected_holdout_min: int = 250
    protected_holdout_max: int = 2_000
    min_holdout_rows: int = 100
    min_development_folds: int = 2
    probability_threshold: float = 0.55
    transaction_cost_bps: float = 1.0
    slippage_bps: float = 0.5
    execution_stride_bars: int | None = None
    random_state: int = 42

    def __post_init__(self) -> None:
        for name in ("n_splits", "min_train_size", "test_size", "min_holdout_rows", "min_development_folds"):
            _positive(f"validation.{name}", int(getattr(self, name)))
        if self.purge_bars < 0 or self.embargo_bars < 0:
            raise ValueError("validation purge/embargo bars must be >= 0")
        if self.protected_holdout_size is not None:
            _positive("validation.protected_holdout_size", self.protected_holdout_size)
        _unit_interval("validation.protected_holdout_fraction", self.protected_holdout_fraction, open_interval=True)
        if self.protected_holdout_min < self.min_holdout_rows:
            raise ValueError("validation.protected_holdout_min must be >= min_holdout_rows")
        if self.protected_holdout_max < self.protected_holdout_min:
            raise ValueError("validation.protected_holdout_max must be >= protected_holdout_min")
        if self.protected_holdout_size is not None and self.protected_holdout_size < self.min_holdout_rows:
            raise ValueError("validation.protected_holdout_size must be >= min_holdout_rows")
        if not 0.5 < self.probability_threshold < 1.0:
            raise ValueError("validation.probability_threshold must be strictly between 0.5 and 1")
        if self.transaction_cost_bps < 0 or self.slippage_bps < 0:
            raise ValueError("validation transaction costs/slippage cannot be negative")
        if self.execution_stride_bars is not None:
            _positive("validation.execution_stride_bars", self.execution_stride_bars)


@dataclass(frozen=True)
class DevelopmentGateConfig:
    enabled: bool = True
    min_auc: float = 0.515
    min_brier_improvement: float = -0.01
    min_fold_pass_rate: float = 0.25
    min_trade_count: int = 20
    min_completed_folds: int = 2

    def __post_init__(self) -> None:
        _unit_interval("development_gate.min_auc", self.min_auc)
        _unit_interval("development_gate.min_fold_pass_rate", self.min_fold_pass_rate)
        _positive("development_gate.min_trade_count", self.min_trade_count)
        _positive("development_gate.min_completed_folds", self.min_completed_folds)


@dataclass(frozen=True)
class HoldoutBudgetConfig:
    """Corpus-level budget for spending pristine protected tails.

    Screening is performed only on development evidence. The budget then limits how
    many sources may cross the protected-holdout boundary in one corpus run while
    preserving diversity across symbols and observed bar-mechanics classes.
    """

    enabled: bool = True
    max_exposures: int = 64
    max_exposure_fraction: float = 0.20
    max_per_canonical_symbol: int = 12
    max_per_mechanics_class: int = 16

    def __post_init__(self) -> None:
        _positive("holdout_budget.max_exposures", self.max_exposures)
        _unit_interval("holdout_budget.max_exposure_fraction", self.max_exposure_fraction, open_interval=True)
        _positive("holdout_budget.max_per_canonical_symbol", self.max_per_canonical_symbol)
        _positive("holdout_budget.max_per_mechanics_class", self.max_per_mechanics_class)


@dataclass(frozen=True)
class EnsembleConfig:
    enabled: bool = True
    max_models: int = 3
    min_component_auc: float = 0.50
    min_component_brier_improvement: float = -0.02
    min_component_fold_pass_rate: float = 0.40
    min_models_for_ensemble: int = 2

    def __post_init__(self) -> None:
        _positive("ensemble.max_models", self.max_models)
        _positive("ensemble.min_models_for_ensemble", self.min_models_for_ensemble)
        if self.min_models_for_ensemble > self.max_models:
            raise ValueError("ensemble.min_models_for_ensemble cannot exceed ensemble.max_models")
        _unit_interval("ensemble.min_component_auc", self.min_component_auc)
        _unit_interval("ensemble.min_component_fold_pass_rate", self.min_component_fold_pass_rate)


@dataclass(frozen=True)
class DiscoveryConfig:
    fdr_alpha: float = 0.05
    interaction_seed_features: int = 10
    max_interactions: int = 30
    min_observations: int = 80

    def __post_init__(self) -> None:
        _unit_interval("discovery.fdr_alpha", self.fdr_alpha, open_interval=True)
        _positive("discovery.interaction_seed_features", self.interaction_seed_features)
        if self.max_interactions < 0:
            raise ValueError("discovery.max_interactions must be >= 0")
        _positive("discovery.min_observations", self.min_observations)


@dataclass(frozen=True)
class AdversarialConfig:
    permutation_iterations: int = 1_999
    permutation_method: str = "circular_shift"
    permutation_block_size: int | None = None
    bootstrap_iterations: int = 1_000
    bootstrap_block_size: int | None = None
    bootstrap_confidence: float = 0.95
    cost_multipliers: tuple[float, ...] = (0.0, 1.0, 1.5, 2.0, 3.0, 5.0)
    threshold_offsets: tuple[float, ...] = (-0.05, -0.025, 0.0, 0.025, 0.05)
    max_feature_ablation_groups: int = 8
    temporal_segments: int = 3
    min_regime_rows: int = 20

    def __post_init__(self) -> None:
        _positive("adversarial.permutation_iterations", self.permutation_iterations)
        if self.permutation_method not in {"circular_shift", "iid_permutation"}:
            raise ValueError("adversarial.permutation_method must be circular_shift or iid_permutation")
        if self.permutation_block_size is not None:
            _positive("adversarial.permutation_block_size", self.permutation_block_size)
        _positive("adversarial.bootstrap_iterations", self.bootstrap_iterations)
        if self.bootstrap_block_size is not None:
            _positive("adversarial.bootstrap_block_size", self.bootstrap_block_size)
        _unit_interval("adversarial.bootstrap_confidence", self.bootstrap_confidence, open_interval=True)
        if not self.cost_multipliers or any(v < 0 for v in self.cost_multipliers):
            raise ValueError("adversarial.cost_multipliers must be non-empty and nonnegative")
        if not self.threshold_offsets:
            raise ValueError("adversarial.threshold_offsets cannot be empty")
        _positive("adversarial.max_feature_ablation_groups", self.max_feature_ablation_groups)
        _positive("adversarial.temporal_segments", self.temporal_segments)
        _positive("adversarial.min_regime_rows", self.min_regime_rows)


@dataclass(frozen=True)
class PromotionConfig:
    min_auc: float = 0.53
    min_brier_improvement: float = 0.0
    min_trade_sharpe_like: float = 0.35
    max_drawdown: float = 0.30
    min_profit_factor: float = 1.05
    min_trade_count: int = 35
    max_permutation_pvalue: float = 0.10
    max_global_qvalue: float = 0.10
    max_drift_score: float = 0.35
    min_fold_pass_rate: float = 0.60
    min_robustness_score: float = 0.60
    min_threshold_survival_rate: float = 0.60
    min_cost_survival_rate: float = 0.50
    min_temporal_survival_rate: float = 0.50
    min_regime_survival_rate: float = 0.50
    max_mean_ensemble_disagreement: float = 0.20
    max_feature_ablation_auc_drop: float = 0.08
    require_execution_safe_identity: bool = True
    require_positive_bootstrap_median: bool = True
    min_bootstrap_positive_fraction: float = 0.55
    require_positive_worst_cost_return: bool = False

    def __post_init__(self) -> None:
        _unit_interval("promotion.min_auc", self.min_auc)
        _unit_interval("promotion.max_drawdown", self.max_drawdown)
        _positive("promotion.min_trade_count", self.min_trade_count)
        if self.min_profit_factor < 0:
            raise ValueError("promotion.min_profit_factor must be >= 0")
        if self.max_feature_ablation_auc_drop < 0:
            raise ValueError("promotion.max_feature_ablation_auc_drop must be >= 0")
        for name in (
            "max_permutation_pvalue", "max_global_qvalue", "max_drift_score",
            "min_fold_pass_rate", "min_robustness_score", "min_threshold_survival_rate",
            "min_cost_survival_rate", "min_temporal_survival_rate", "min_regime_survival_rate",
            "max_mean_ensemble_disagreement", "min_bootstrap_positive_fraction",
        ):
            _unit_interval(f"promotion.{name}", float(getattr(self, name)))


@dataclass(frozen=True)
class ShadowConfig:
    """Forward-only evidence policy for research candidates.

    Shadow evaluation may recommend review/degradation, but it never authorizes
    production trading or rewrites the model that emitted the recorded prediction.
    """

    min_mature_observations: int = 50
    recent_window: int = 100
    calibration_bins: int = 10
    min_signal_count: int = 20
    max_auc_drop_vs_reference: float = 0.08
    max_brier_degradation_vs_reference: float = 0.05
    max_expected_calibration_error: float = 0.12
    max_probability_ks_drift: float = 0.30
    max_recent_auc_drop: float = 0.08
    max_recent_brier_degradation: float = 0.05
    max_drawdown: float = 0.30
    min_directional_posterior_lower: float = 0.40
    watch_failures: int = 1
    degraded_failures: int = 2

    def __post_init__(self) -> None:
        _positive("shadow.min_mature_observations", self.min_mature_observations)
        _positive("shadow.recent_window", self.recent_window)
        _positive("shadow.calibration_bins", self.calibration_bins)
        _positive("shadow.min_signal_count", self.min_signal_count)
        for name in (
            "max_auc_drop_vs_reference",
            "max_brier_degradation_vs_reference",
            "max_expected_calibration_error",
            "max_probability_ks_drift",
            "max_recent_auc_drop",
            "max_recent_brier_degradation",
            "max_drawdown",
            "min_directional_posterior_lower",
        ):
            _unit_interval(f"shadow.{name}", float(getattr(self, name)))
        _positive("shadow.watch_failures", self.watch_failures)
        _positive("shadow.degraded_failures", self.degraded_failures)
        if self.degraded_failures < self.watch_failures:
            raise ValueError("shadow.degraded_failures cannot be smaller than shadow.watch_failures")


@dataclass(frozen=True)
class RuntimeConfig:
    registry_path: str = "artifacts/experiments.sqlite3"
    output_dir: str = "artifacts/runs"
    candidate_dir: str = "artifacts/candidates"
    shadow_path: str = "artifacts/shadow.sqlite3"
    holdout_ledger_path: str = "artifacts/holdout_ledger.sqlite3"
    identity_manifest: str = "config/source_identity.csv"
    strict_holdout_ledger: bool = True


@dataclass(frozen=True)
class DaedalusConfig:
    data: DataConfig = field(default_factory=DataConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    development_gate: DevelopmentGateConfig = field(default_factory=DevelopmentGateConfig)
    holdout_budget: HoldoutBudgetConfig = field(default_factory=HoldoutBudgetConfig)
    ensemble: EnsembleConfig = field(default_factory=EnsembleConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    adversarial: AdversarialConfig = field(default_factory=AdversarialConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    shadow: ShadowConfig = field(default_factory=ShadowConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    def __post_init__(self) -> None:
        if self.features.feature_lag_bars < 1:
            raise ValueError("DAEDALUS requires at least one-bar predictor lag")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_config(cfg: DaedalusConfig) -> DaedalusConfig:
    # Reconstruct to force every nested __post_init__ invariant in custom workflows.
    DaedalusConfig(
        data=cfg.data,
        features=cfg.features,
        validation=cfg.validation,
        development_gate=cfg.development_gate,
        holdout_budget=cfg.holdout_budget,
        ensemble=cfg.ensemble,
        discovery=cfg.discovery,
        adversarial=cfg.adversarial,
        promotion=cfg.promotion,
        shadow=cfg.shadow,
        runtime=cfg.runtime,
    )
    return cfg
