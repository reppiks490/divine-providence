from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from .config import FeatureConfig
from .features import build_predictor_features


@dataclass(frozen=True)
class FusionSourceDiagnostics:
    name: str
    input_rows: int
    predictor_rows: int
    matched_execution_rows: int
    max_source_time_minus_execution_time: float
    median_age_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FusionDiagnostics:
    execution_rows: int
    usable_rows: int
    feature_count: int
    target_horizon_bars: int
    target_entry: str
    target_exit: str
    sources: tuple[FusionSourceDiagnostics, ...]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sources"] = [x.to_dict() for x in self.sources]
        return d


def _validate_alignment_time(df: pd.DataFrame, name: str, *, require_unique: bool) -> np.ndarray:
    if "time" not in df.columns:
        raise ValueError(f"{name} is missing time")
    t = pd.to_numeric(df["time"], errors="coerce").to_numpy(dtype=float)
    if len(t) == 0 or not np.isfinite(t).all():
        raise ValueError(f"{name} contains empty/non-finite alignment timestamps")
    if np.any(np.diff(t) < 0):
        raise ValueError(f"{name} timestamps decrease; fusion will not silently sort source mechanics")
    if require_unique and len(np.unique(t)) != len(t):
        raise ValueError(
            f"{name} contains repeated timestamps. Cross-representation fusion refuses to choose an "
            "arbitrary same-timestamp event without an explicit sub-timestamp/event-order mapping."
        )
    return t


def build_execution_target(
    execution_df: pd.DataFrame,
    cfg: FeatureConfig,
) -> tuple[pd.Series, pd.Series]:
    """Build an executable open-to-future-close target on the designated price stream.

    Predictor information is required to come from bars/events strictly before the
    execution row. The trade enters at the execution row's open and exits at the close
    of the ``target_horizon``-th execution bar, avoiding a target that assumes an
    unknowable same-bar closing entry price.
    """
    horizon = int(cfg.target_horizon)
    if horizon < 1:
        raise ValueError("target_horizon must be >= 1")
    entry = execution_df["open"].astype(float).where(lambda s: s > 0)
    exit_close = execution_df["close"].astype(float).shift(-(horizon - 1)).where(lambda s: s > 0)
    future_log_return = np.log(exit_close / entry)
    threshold = float(cfg.target_threshold_bps) / 10_000.0
    if threshold > 0:
        y = pd.Series(
            np.where(
                future_log_return > threshold,
                1.0,
                np.where(future_log_return < -threshold, 0.0, np.nan),
            ),
            index=execution_df.index,
        )
    else:
        y = (future_log_return > 0.0).astype(float)
        y[future_log_return.isna()] = np.nan
    return y, future_log_return


def build_fused_dataset(
    execution_df: pd.DataFrame,
    representations: Mapping[str, pd.DataFrame],
    cfg: FeatureConfig,
    *,
    include_execution_features: bool = True,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, FusionDiagnostics]:
    """Causally fuse heterogeneous chart representations onto an execution timeline.

    Every representation is aligned with ``direction='backward'`` and
    ``allow_exact_matches=False``. Therefore an execution row can only consume a
    predictor snapshot timestamped strictly earlier than its entry time. Repeated
    timestamps are preserved in standalone research but rejected here because their
    intra-timestamp event order is unknowable without explicit metadata.
    """
    exec_time = _validate_alignment_time(execution_df, "execution source", require_unique=True)
    required = {"open", "high", "low", "close"}
    missing = required.difference(execution_df.columns)
    if missing:
        raise ValueError(f"execution source missing columns: {sorted(missing)}")

    sources: dict[str, pd.DataFrame] = dict(representations)
    if include_execution_features:
        sources = {"execution": execution_df, **sources}
    if not sources:
        raise ValueError("At least one predictor representation is required")

    base = pd.DataFrame({"_execution_time": exec_time, "_execution_pos": execution_df.index.to_numpy(dtype=int)})
    fused = base.copy()
    diagnostics: list[FusionSourceDiagnostics] = []

    for name, frame in sources.items():
        if not name or "__" in name:
            raise ValueError("representation names must be non-empty and cannot contain '__'")
        source_time = _validate_alignment_time(frame, f"representation {name}", require_unique=True)
        predictors = build_predictor_features(frame, cfg, drop_incomplete=True)
        if predictors.empty:
            raise ValueError(f"representation {name} has no complete causal predictor rows")
        aligned_times = source_time[predictors.index.to_numpy(dtype=int)]
        right = predictors.copy()
        right.insert(0, "_source_time", aligned_times)
        right = right.rename(columns={c: f"{name}__{c}" for c in predictors.columns})
        merged = pd.merge_asof(
            fused.sort_values("_execution_time"),
            right.sort_values("_source_time"),
            left_on="_execution_time",
            right_on="_source_time",
            direction="backward",
            allow_exact_matches=False,
        )
        age = merged["_execution_time"] - merged["_source_time"]
        merged[f"{name}__age_seconds"] = age
        matched = merged["_source_time"].notna()
        violation = (
            float((merged.loc[matched, "_source_time"] - merged.loc[matched, "_execution_time"]).max())
            if matched.any() else float("nan")
        )
        median_age = float(age[matched].median()) if matched.any() else float("nan")
        diagnostics.append(FusionSourceDiagnostics(
            name=name,
            input_rows=int(len(frame)),
            predictor_rows=int(len(predictors)),
            matched_execution_rows=int(matched.sum()),
            max_source_time_minus_execution_time=violation,
            median_age_seconds=median_age,
        ))
        fused = merged.drop(columns=["_source_time"])

    y, future_ret = build_execution_target(execution_df, cfg)
    fused = fused.set_index("_execution_pos", drop=True)
    feature_cols = [c for c in fused.columns if c != "_execution_time"]
    x = fused[feature_cols].replace([np.inf, -np.inf], np.nan)
    coverage = x.notna().mean(axis=1) if x.shape[1] else pd.Series(0.0, index=x.index)
    valid = (coverage >= cfg.min_row_feature_coverage) & y.reindex(x.index).notna() & future_ret.reindex(x.index).notna()
    x = x.loc[valid].astype(float)
    yy = y.reindex(x.index).astype(int)
    rr = future_ret.reindex(x.index).astype(float)
    diag = FusionDiagnostics(
        execution_rows=int(len(execution_df)),
        usable_rows=int(len(x)),
        feature_count=int(x.shape[1]),
        target_horizon_bars=int(cfg.target_horizon),
        target_entry="execution_open",
        target_exit=f"execution_close_bar_{int(cfg.target_horizon)}",
        sources=tuple(diagnostics),
    )
    return x, yy, rr, diag
