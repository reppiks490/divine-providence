from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import math

import numpy as np
import pandas as pd

from .representation import robust_representation_consensus
from .synthetic import EnsembleDefinition, FactorEnsembleEngine


@dataclass(frozen=True, slots=True)
class HierarchicalFusionResult:
    symbol_returns: pd.DataFrame
    representation_disagreement: pd.DataFrame
    representation_agreement: pd.DataFrame
    representation_coverage: pd.DataFrame
    factor: pd.DataFrame


def _quality_adjusted_consensus(
    symbol: str,
    event_ns: int,
    values: dict[str, float],
    quality: Mapping[str, float] | None,
) -> tuple[float, float, float, float]:
    """Return consensus, disagreement, agreement, effective coverage.

    Robust representation weights are multiplied by explicit source-quality
    weights.  Missing values never become zero-valued observations.
    """
    c = robust_representation_consensus(symbol, event_ns, values)
    if c.representation_count == 0:
        return math.nan, math.nan, math.nan, 0.0
    if not quality:
        return c.consensus_return, c.disagreement, c.directional_agreement, float(c.representation_count)
    raw = []
    xs = []
    for sid, rw in c.contributions.items():
        q = max(0.0, min(1.0, float(quality.get(sid, 1.0))))
        w = float(rw) * q
        if w > 0 and sid in values and math.isfinite(float(values[sid])):
            raw.append(w); xs.append(float(values[sid]))
    if not raw:
        return math.nan, math.nan, math.nan, 0.0
    w = np.asarray(raw, dtype=float); w /= w.sum(); x = np.asarray(xs, dtype=float)
    consensus = float(np.dot(w, x))
    disagreement = float(np.sqrt(np.dot(w, (x-consensus)**2)))
    if abs(consensus) < 1e-15:
        agreement = float(np.mean(np.abs(x) < max(disagreement, 1e-12)))
    else:
        agreement = float(np.mean(np.sign(x) == np.sign(consensus)))
    effective = float(sum(max(0.0, min(1.0, float(quality.get(sid, 1.0)))) for sid in c.contributions))
    return consensus, disagreement, agreement, effective


def fuse_representations_by_symbol(
    returns: pd.DataFrame,
    stream_to_symbol: Mapping[str, str],
    *,
    quality_weights: Mapping[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Collapse representation redundancy *within* symbols before cross-asset modeling.

    Every raw representation remains outside this output for lineage/replay. This
    function only constructs a derived symbol-level research plane.
    """
    streams = [c for c in returns.columns if c in stream_to_symbol]
    groups: dict[str, list[str]] = {}
    for sid in streams:
        groups.setdefault(stream_to_symbol[sid], []).append(sid)
    symbols = sorted(groups)
    consensus_rows=[]; disagreement_rows=[]; agreement_rows=[]; coverage_rows=[]
    for ordinal, (idx, row) in enumerate(returns[streams].iterrows()):
        cv={}; dv={}; av={}; cov={}
        # event_ns is diagnostic only here; support non-integer indexes deterministically.
        try: event_ns=int(idx)
        except (TypeError,ValueError): event_ns=ordinal
        for sym in symbols:
            vals={sid:float(row[sid]) for sid in groups[sym] if pd.notna(row[sid]) and math.isfinite(float(row[sid]))}
            c,d,a,e=_quality_adjusted_consensus(sym,event_ns,vals,quality_weights)
            cv[sym]=c;dv[sym]=d;av[sym]=a;cov[sym]=e/max(1,len(groups[sym]))
        consensus_rows.append(cv);disagreement_rows.append(dv);agreement_rows.append(av);coverage_rows.append(cov)
    return (
        pd.DataFrame(consensus_rows,index=returns.index,columns=symbols,dtype=float),
        pd.DataFrame(disagreement_rows,index=returns.index,columns=symbols,dtype=float),
        pd.DataFrame(agreement_rows,index=returns.index,columns=symbols,dtype=float),
        pd.DataFrame(coverage_rows,index=returns.index,columns=symbols,dtype=float),
    )


class HierarchicalFactorEngine:
    """Two-stage factor builder: representations -> symbols -> cross-asset factor.

    This prevents representation-count bias: adding another chart/export for one
    underlying symbol does not automatically increase that symbol's cross-asset weight.
    """
    def build(
        self,
        returns: pd.DataFrame,
        stream_to_symbol: Mapping[str, str],
        definition: EnsembleDefinition,
        *,
        quality_weights: Mapping[str, float] | None = None,
    ) -> HierarchicalFusionResult:
        symbol_returns, disagreement, agreement, coverage = fuse_representations_by_symbol(
            returns, stream_to_symbol, quality_weights=quality_weights
        )
        missing=[c for c in definition.components if c not in symbol_returns.columns]
        if missing:
            raise KeyError(f"factor definition references missing symbol consensus: {missing}")
        # Factor engine expects levels because it log-differences internally. Convert
        # fused returns to a strictly positive synthetic level path per symbol.
        levels=np.exp(symbol_returns.fillna(0.0).cumsum())
        factor=FactorEnsembleEngine().build(levels,definition)
        return HierarchicalFusionResult(symbol_returns,disagreement,agreement,coverage,factor)
