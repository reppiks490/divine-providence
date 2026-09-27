from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = ("time", "open", "high", "low", "close")


@dataclass(frozen=True)
class DataQualityReport:
    rows: int
    duplicate_timestamp_ratio: float
    decreasing_timestamp_ratio: float
    fractional_timestamp_ratio: float
    invalid_ohlc_rows: int
    nonfinite_required_rows: int

    @property
    def structurally_valid(self) -> bool:
        return self.invalid_ohlc_rows == 0 and self.nonfinite_required_rows == 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["structurally_valid"] = self.structurally_valid
        return d


def inspect_quality(df: pd.DataFrame, nonfinite_required_rows: int = 0) -> DataQualityReport:
    t = pd.to_numeric(df["time"], errors="coerce").to_numpy(dtype=float)
    d = np.diff(t)
    duplicate_ratio = float(np.mean(d == 0)) if len(d) else 0.0
    decreasing_ratio = float(np.mean(d < 0)) if len(d) else 0.0
    fractional_ratio = float(np.mean(np.abs(t - np.round(t)) > 1e-9)) if len(t) else 0.0

    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    invalid = (high < np.maximum.reduce([open_, close, low])) | (
        low > np.minimum.reduce([open_, close, high])
    )
    return DataQualityReport(
        rows=int(len(df)),
        duplicate_timestamp_ratio=duplicate_ratio,
        decreasing_timestamp_ratio=decreasing_ratio,
        fractional_timestamp_ratio=fractional_ratio,
        invalid_ohlc_rows=int(np.sum(invalid)),
        nonfinite_required_rows=int(nonfinite_required_rows),
    )


def load_bars_with_quality(
    path: Path,
    max_rows: int | None = None,
    require_nondecreasing_time: bool = True,
    reject_nonfinite_required_rows: bool = True,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Load a source without collapsing repeated timestamps or silently sorting rows."""
    df = pd.read_csv(path)
    mapping = {str(c).strip().lower(): c for c in df.columns}
    missing = [c for c in REQUIRED if c not in mapping]
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")

    rename = {mapping[c]: c for c in REQUIRED}
    if "volume" in mapping:
        rename[mapping["volume"]] = "volume"
    df = df.rename(columns=rename)
    keep = list(REQUIRED) + (["volume"] if "volume" in df.columns else [])
    df = df[keep].copy()
    for c in keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    required_array = df[list(REQUIRED)].to_numpy(dtype=float)
    nonfinite_before = int((~np.isfinite(required_array)).any(axis=1).sum())
    if reject_nonfinite_required_rows and nonfinite_before:
        raise ValueError(
            f"{path} contains {nonfinite_before} rows with non-finite required values; "
            "DAEDALUS refuses to silently drop bars because that can change path mechanics."
        )
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=list(REQUIRED)).reset_index(drop=True)
    if max_rows is not None and len(df) > max_rows:
        df = df.iloc[-max_rows:].reset_index(drop=True)

    quality = inspect_quality(df, nonfinite_required_rows=nonfinite_before)
    if quality.invalid_ohlc_rows:
        raise ValueError(f"{path} contains {quality.invalid_ohlc_rows} invalid OHLC rows")
    if require_nondecreasing_time and quality.decreasing_timestamp_ratio > 0:
        raise ValueError(
            f"{path} is not in nondecreasing source order "
            f"({quality.decreasing_timestamp_ratio:.4%} negative deltas); "
            "DAEDALUS will not silently sort alternate chart constructions."
        )
    return df, quality


def load_bars(
    path: Path,
    max_rows: int | None = None,
    require_nondecreasing_time: bool = True,
    reject_nonfinite_required_rows: bool = True,
) -> pd.DataFrame:
    """Compatibility loader returning only bars; use load_bars_with_quality for provenance/audit."""
    df, _ = load_bars_with_quality(
        path,
        max_rows,
        require_nondecreasing_time,
        reject_nonfinite_required_rows,
    )
    return df
