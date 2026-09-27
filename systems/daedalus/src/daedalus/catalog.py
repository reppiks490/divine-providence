from __future__ import annotations

import csv
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .utils import sha256_file, stable_hash


@dataclass(frozen=True)
class SourceProfile:
    path: str
    filename: str
    symbol_hint: str
    suffix_hint: str
    rows: int
    columns: tuple[str, ...]
    has_volume: bool
    sha256: str
    exact_duplicate_group: str
    first_time: float | None
    last_time: float | None
    median_delta_seconds: float | None
    p05_delta_seconds: float | None
    p95_delta_seconds: float | None
    regularity_ratio: float
    duplicate_timestamp_ratio: float
    backward_timestamp_ratio: float
    fractional_timestamp_ratio: float
    zero_range_ratio: float
    median_true_range_bps: float | None
    volume_non_null_ratio: float | None
    mechanics_class: str
    mechanics_signature: str

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_name(path: Path) -> tuple[str, str]:
    stem = path.stem
    if "," in stem:
        symbol, suffix = stem.split(",", 1)
        return symbol.strip(), suffix.strip()
    return stem, ""


def discover_csvs(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    out: list[Path] = []
    for path in root.rglob("*.csv"):
        name = path.name
        if name.startswith("._") or "__MACOSX" in path.parts:
            continue
        if path.is_file():
            out.append(path)
    return sorted(out)


def _count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def profile_csv(path: Path, sample_rows: int = 50_000) -> SourceProfile:
    symbol, suffix = _parse_name(path)
    digest = sha256_file(path)
    try:
        df = pd.read_csv(path, nrows=sample_rows)
    except Exception as exc:
        raise ValueError(f"Unable to parse CSV {path}: {exc}") from exc
    cols = tuple(str(c) for c in df.columns)
    lower = {str(c).lower(): c for c in df.columns}
    has_volume = "volume" in lower
    rows = _count_rows(path)

    time_col = lower.get("time")
    if time_col is None or df.empty:
        first = last = med = p05 = p95 = None
        reg = dup = backward = frac = 0.0
    else:
        t = pd.to_numeric(df[time_col], errors="coerce").dropna().to_numpy(dtype=float)
        first = float(t[0]) if len(t) else None
        last = float(t[-1]) if len(t) else None
        frac = float(np.mean(np.abs(t - np.round(t)) > 1e-9)) if len(t) else 0.0
        dup = float(1.0 - len(np.unique(t)) / len(t)) if len(t) else 0.0
        d_all = np.diff(t)
        finite_d = d_all[np.isfinite(d_all)]
        backward = float(np.mean(finite_d < 0)) if len(finite_d) else 0.0
        d = finite_d[finite_d >= 0]
        positive = d[d > 0]
        if len(positive):
            med = float(np.median(positive))
            p05 = float(np.quantile(positive, 0.05))
            p95 = float(np.quantile(positive, 0.95))
            tol = max(1e-9, abs(med) * 0.01)
            reg = float(np.mean(np.abs(positive - med) <= tol))
        else:
            med = p05 = p95 = None
            reg = 0.0

    ohlc = {k: lower.get(k) for k in ("open", "high", "low", "close")}
    if all(ohlc.values()) and not df.empty:
        high = pd.to_numeric(df[ohlc["high"]], errors="coerce")
        low = pd.to_numeric(df[ohlc["low"]], errors="coerce")
        close = pd.to_numeric(df[ohlc["close"]], errors="coerce")
        rng = (high - low).abs()
        zero_range = float((rng.fillna(0) == 0).mean())
        base = close.abs().replace(0, np.nan)
        tr_bps = (rng / base * 10_000).replace([np.inf, -np.inf], np.nan).dropna()
        med_tr = float(tr_bps.median()) if len(tr_bps) else None
    else:
        zero_range = 0.0
        med_tr = None

    if has_volume:
        v = pd.to_numeric(df[lower["volume"]], errors="coerce")
        vol_ratio = float(v.notna().mean()) if len(v) else 0.0
    else:
        vol_ratio = None

    mechanics = {
        "median_delta_seconds": med,
        "p05_delta_seconds": p05,
        "p95_delta_seconds": p95,
        "regularity_ratio": round(reg, 6),
        "duplicate_timestamp_ratio": round(dup, 6),
        "backward_timestamp_ratio": round(backward, 6),
        "fractional_timestamp_ratio": round(frac, 6),
        "zero_range_ratio": round(zero_range, 6),
        "median_true_range_bps": None if med_tr is None else round(med_tr, 6),
        "has_volume": has_volume,
    }
    if dup > 0.01:
        mechanics_class = "repeated_timestamp_sequence"
    elif backward > 0.001:
        mechanics_class = "non_monotonic_sequence"
    elif med is not None and reg >= 0.95:
        mechanics_class = "fixed_cadence_like"
    elif med is not None:
        mechanics_class = "variable_cadence_like"
    else:
        mechanics_class = "unresolved"

    return SourceProfile(
        path=str(path), filename=path.name, symbol_hint=symbol, suffix_hint=suffix,
        rows=rows, columns=cols, has_volume=has_volume, sha256=digest,
        exact_duplicate_group=digest[:16], first_time=first, last_time=last,
        median_delta_seconds=med, p05_delta_seconds=p05, p95_delta_seconds=p95,
        regularity_ratio=reg, duplicate_timestamp_ratio=dup, backward_timestamp_ratio=backward,
        fractional_timestamp_ratio=frac, zero_range_ratio=zero_range,
        median_true_range_bps=med_tr, volume_non_null_ratio=vol_ratio,
        mechanics_class=mechanics_class, mechanics_signature=stable_hash(mechanics)[:20],
    )


def build_catalog(root: Path) -> pd.DataFrame:
    profiles = [profile_csv(p).to_dict() for p in discover_csvs(root)]
    if not profiles:
        return pd.DataFrame()
    df = pd.DataFrame(profiles)
    counts = df.groupby("sha256")["sha256"].transform("size")
    df["exact_duplicate_count"] = counts.astype(int)
    return df.sort_values(["symbol_hint", "suffix_hint", "filename"]).reset_index(drop=True)
