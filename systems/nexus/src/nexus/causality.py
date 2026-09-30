from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Iterable
import math

import numpy as np
import pandas as pd

from .contracts import BarEvent


@dataclass(frozen=True, slots=True)
class CausalityViolation:
    cutpoint: int
    timestamp: str
    column: str
    prefix_value: float
    full_value: float
    absolute_error: float


@dataclass(frozen=True, slots=True)
class CausalityAudit:
    passed: bool
    checked_cutpoints: tuple[int, ...]
    comparisons: int
    violations: tuple[CausalityViolation, ...]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checked_cutpoints": list(self.checked_cutpoints),
            "comparisons": self.comparisons,
            "violations": [asdict(v) for v in self.violations],
        }


def audit_event_availability(events: Iterable[BarEvent]) -> tuple[str, ...]:
    """Return violations where a market event becomes visible before its event time.

    This is a conservative invariant for NEXUS bar/context streams.  Sources with
    different semantics must use a separately reviewed contract rather than bypass it.
    """
    errors=[]
    for e in events:
        if e.available_ns is not None and e.available_ns < e.event_ns:
            errors.append(f"{e.stream_id}:{e.source_sequence}:available_before_event")
        if e.source_timestamp_ns is not None and e.event_ns < e.source_timestamp_ns:
            errors.append(f"{e.stream_id}:{e.source_sequence}:event_before_source_timestamp")
    return tuple(errors)


def audit_prefix_invariance(
    build: Callable[[pd.DataFrame], pd.DataFrame],
    data: pd.DataFrame,
    *,
    cutpoints: Iterable[int] | None = None,
    atol: float = 1e-10,
    rtol: float = 1e-8,
    max_violations: int = 100,
) -> CausalityAudit:
    """Detect future leakage by requiring prefix output to match full-run history.

    A causal deterministic transformation must not rewrite already-emitted numeric
    values merely because future rows were appended. This test is method-agnostic and
    is useful for factor, topology, feature, and model-preprocessing code.
    """
    if not isinstance(data,pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")
    if not math.isfinite(float(atol)) or float(atol) < 0:
        raise ValueError("atol must be finite and non-negative")
    if not math.isfinite(float(rtol)) or float(rtol) < 0:
        raise ValueError("rtol must be finite and non-negative")
    if type(max_violations) is not int or max_violations < 1:
        raise ValueError("max_violations must be a positive integer")
    if cutpoints is None:
        n=len(data)
        cutpoints=tuple(sorted(set(x for x in (max(2,n//4),max(2,n//2),max(2,3*n//4),n) if x<=n)))
    cps=tuple(dict.fromkeys(int(c) for c in cutpoints if 1 <= int(c) <= len(data)))
    full=build(data.copy())
    violations=[]; comparisons=0
    for cp in cps:
        prefix=build(data.iloc[:cp].copy())
        common=prefix.index.intersection(full.index)
        if len(common)==0:continue
        numeric=[c for c in prefix.columns if c in full.columns and pd.api.types.is_numeric_dtype(prefix[c]) and pd.api.types.is_numeric_dtype(full[c])]
        for c in numeric:
            a=prefix.loc[common,c].to_numpy(float);b=full.loc[common,c].to_numpy(float)
            for idx,av,bv in zip(common,a,b):
                if not (math.isfinite(av) and math.isfinite(bv)):
                    if (math.isnan(av) if isinstance(av,float) else False) and (math.isnan(bv) if isinstance(bv,float) else False):
                        continue
                comparisons+=1
                if not np.isclose(av,bv,atol=atol,rtol=rtol,equal_nan=True):
                    violations.append(CausalityViolation(cp,str(idx),c,float(av),float(bv),float(abs(av-bv))))
                    if len(violations)>=max_violations:
                        return CausalityAudit(False,cps,comparisons,tuple(violations))
    return CausalityAudit(not violations and comparisons>0,cps,comparisons,tuple(violations))
