from __future__ import annotations

import math
from .contracts import StreamManifest


def _counter(m:StreamManifest,name:str)->int|None:
    value=m.metadata.get(name,0)
    if type(value) is not int or value < 0 or value > m.row_count:
        return None
    return value


def quality_score(m:StreamManifest)->float:
    """Transparent data-usability score, never an alpha/truth score.

    Corrupted telemetry fails closed to zero instead of being clamped into an
    apparently valid quality value.
    """
    if not isinstance(m,StreamManifest):
        raise TypeError("m must be StreamManifest")
    if type(m.row_count) is not int or m.row_count <= 0:
        return 0.0
    if "appledouble" in m.quality_flags:
        return 0.0
    confidence=float(m.cadence_confidence)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        return 0.0
    if m.observed_cadence_ns is not None and (
        type(m.observed_cadence_ns) is not int or m.observed_cadence_ns <= 0
    ):
        return 0.0
    bad_num=_counter(m,"nonnumeric_ohlc_rows")
    bad_geom=_counter(m,"inconsistent_ohlc_rows")
    if bad_num is None or bad_geom is None:
        return 0.0

    score=1.0
    score *= confidence if m.observed_cadence_ns else 0.5
    if "backward_time" in m.quality_flags: score*=0.25
    if "missing_ohlc" in m.quality_flags: score*=0.1
    if "bad_header" in m.quality_flags: score*=0.0
    if "duplicate_header" in m.quality_flags: score*=0.95
    if "repeated_time" in m.quality_flags: score*=0.9
    if "fractional_time" in m.quality_flags: score*=0.98
    if "non_numeric" in m.quality_flags: score*=0.8
    if "ohlc_inconsistent" in m.quality_flags: score*=0.7

    denom=m.row_count
    score*=1.0-(bad_num/denom)
    score*=max(0.0,1.0-min(1.0,(bad_geom/denom)*2.0))
    # Duplicates are not lower-fidelity data, but they must not inflate
    # independent sensor counts; duplicate handling belongs to universe/fusion.
    return max(0.0,min(1.0,float(score)))


def dynamic_state_quality(
    *,base_score:float,age_ns:int,cadence_ns:int|None,missing:bool=False,
    clock_uncertainty_ns:int=0,
)->float:
    if not math.isfinite(float(base_score)) or not 0.0 <= float(base_score) <= 1.0:
        raise ValueError("base_score must be finite and in [0,1]")
    if type(age_ns) is not int or age_ns < 0:
        raise ValueError("age_ns must be a non-negative integer")
    if type(clock_uncertainty_ns) is not int or clock_uncertainty_ns < 0:
        raise ValueError("clock_uncertainty_ns must be a non-negative integer")
    if cadence_ns is not None and (type(cadence_ns) is not int or cadence_ns <= 0):
        raise ValueError("cadence_ns must be a positive integer or None")
    if type(missing) is not bool:
        raise TypeError("missing must be bool")
    if missing:
        return 0.0

    q=float(base_score)
    if cadence_ns is not None:
        q*=max(0.0,min(1.0,2.0-(age_ns/cadence_ns)))
        q*=max(0.0,min(1.0,1.0-clock_uncertainty_ns/(2*cadence_ns)))
    return max(0.0,min(1.0,q))
