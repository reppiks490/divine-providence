from __future__ import annotations
from .contracts import StreamManifest

def quality_score(m: StreamManifest) -> float:
    """Transparent data usability score, not a truth/alpha score."""
    if "appledouble" in m.quality_flags or m.row_count <= 0: return 0.0
    score=1.0
    score *= min(1.0, max(0.0, m.cadence_confidence)) if m.observed_cadence_ns else 0.5
    if "backward_time" in m.quality_flags: score*=0.25
    if "missing_ohlc" in m.quality_flags: score*=0.1
    if "bad_header" in m.quality_flags: score*=0.0
    if "duplicate_header" in m.quality_flags: score*=0.95
    if "repeated_time" in m.quality_flags: score*=0.9
    if "fractional_time" in m.quality_flags: score*=0.98
    if "non_numeric" in m.quality_flags: score*=0.8
    if "ohlc_inconsistent" in m.quality_flags: score*=0.7
    denom=max(1,int(m.row_count))
    bad_num=float(m.metadata.get("nonnumeric_ohlc_rows",0))/denom
    bad_geom=float(m.metadata.get("inconsistent_ohlc_rows",0))/denom
    score*=max(0.0,1.0-min(1.0,bad_num))
    score*=max(0.0,1.0-min(1.0,bad_geom*2.0))
    # Duplicates are not lower-fidelity data, but they must not inflate independent sensor counts.
    return max(0.0,min(1.0,score))

def dynamic_state_quality(*,base_score:float,age_ns:int,cadence_ns:int|None,missing:bool=False,clock_uncertainty_ns:int=0)->float:
    if missing:return 0.0
    q=max(0.0,min(1.0,float(base_score)))
    if cadence_ns and cadence_ns>0:
        q*=max(0.0,min(1.0,2.0-(age_ns/max(1,cadence_ns))))
        q*=max(0.0,min(1.0,1.0-clock_uncertainty_ns/max(1,2*cadence_ns)))
    return max(0.0,min(1.0,q))
