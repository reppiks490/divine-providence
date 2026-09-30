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
    """Return consensus, disagreement, agreement and effective coverage."""
    c = robust_representation_consensus(symbol, event_ns, values)
    if c.representation_count == 0:
        return math.nan, math.nan, math.nan, 0.0
    if not quality:
        return (
            c.consensus_return,
            c.disagreement,
            c.directional_agreement,
            float(c.representation_count),
        )

    raw = []
    xs = []
    for sid, rw in c.contributions.items():
        q = max(0.0, min(1.0, float(quality.get(sid, 1.0))))
        w = float(rw) * q
        if w > 0 and sid in values and math.isfinite(float(values[sid])):
            raw.append(w)
            xs.append(float(values[sid]))
    if not raw:
        return math.nan, math.nan, math.nan, 0.0

    w = np.asarray(raw, dtype=float)
    w /= w.sum()
    x = np.asarray(xs, dtype=float)
    consensus = float(np.dot(w, x))
    disagreement = float(np.sqrt(np.dot(w, (x - consensus) ** 2)))
    if abs(consensus) < 1e-15:
        agreement = float(np.mean(np.abs(x) < max(disagreement, 1e-12)))
    else:
        agreement = float(np.mean(np.sign(x) == np.sign(consensus)))
    effective = float(
        sum(max(0.0, min(1.0, float(quality.get(sid, 1.0)))) for sid in c.contributions)
    )
    return consensus, disagreement, agreement, effective


def fuse_representations_by_symbol(
    returns: pd.DataFrame,
    stream_to_symbol: Mapping[str, str],
    *,
    quality_weights: Mapping[str, float] | None = None,
    stream_to_family: Mapping[str, str] | None = None,
    stream_to_construction: Mapping[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fuse correlated market views without representation-count bias.

    Preferred hierarchy:
      streams -> sampling construction inside chart family -> chart family
      -> symbol.

    Example: five regular-candle timeframes do not get five votes against one
    regular-candle tick stream. Likewise, a chart family with three sampling
    constructions does not automatically get three votes against Heikin Ashi
    or Renko. Missing observations remain absent from each consensus step.

    For backward compatibility, if no construction map is provided the function
    performs the older streams -> family -> symbol hierarchy. If no family map
    is provided it performs a direct per-symbol robust consensus.
    """
    streams = [col for col in returns.columns if col in stream_to_symbol]
    symbol_groups: dict[str, list[str]] = {}
    for sid in streams:
        symbol_groups.setdefault(stream_to_symbol[sid], []).append(sid)
    symbols = sorted(symbol_groups)

    family_groups: dict[str, dict[str, list[str]]] = {}
    construction_groups: dict[str, dict[str, dict[str, list[str]]]] = {}
    if stream_to_family is not None:
        for sym, members in symbol_groups.items():
            fg: dict[str, list[str]] = {}
            cg: dict[str, dict[str, list[str]]] = {}
            for sid in members:
                family = str(stream_to_family.get(sid, "unknown"))
                fg.setdefault(family, []).append(sid)
                if stream_to_construction is not None:
                    construction = str(stream_to_construction.get(sid, "unknown"))
                    cg.setdefault(family, {}).setdefault(construction, []).append(sid)
            family_groups[sym] = fg
            if stream_to_construction is not None:
                construction_groups[sym] = cg

    consensus_rows = []
    disagreement_rows = []
    agreement_rows = []
    coverage_rows = []

    for ordinal, (idx, row) in enumerate(returns[streams].iterrows()):
        cv = {}
        dv = {}
        av = {}
        cov = {}
        try:
            event_ns = int(idx)
        except (TypeError, ValueError):
            event_ns = ordinal

        for sym in symbols:
            if stream_to_family is None:
                vals = {
                    sid: float(row[sid])
                    for sid in symbol_groups[sym]
                    if pd.notna(row[sid]) and math.isfinite(float(row[sid]))
                }
                cc, dd, aa, ee = _quality_adjusted_consensus(
                    sym, event_ns, vals, quality_weights
                )
                cv[sym], dv[sym], av[sym] = cc, dd, aa
                cov[sym] = ee / max(1, len(symbol_groups[sym]))
                continue

            family_values: dict[str, float] = {}
            family_quality: dict[str, float] = {}

            for family, family_members in family_groups[sym].items():
                if stream_to_construction is None:
                    vals = {
                        sid: float(row[sid])
                        for sid in family_members
                        if pd.notna(row[sid]) and math.isfinite(float(row[sid]))
                    }
                    fc, _, _, fe = _quality_adjusted_consensus(
                        f"{sym}:{family}", event_ns, vals, quality_weights
                    )
                    if math.isfinite(fc):
                        family_values[family] = fc
                        family_quality[family] = min(
                            1.0, fe / max(1, len(family_members))
                        )
                    continue

                construction_values: dict[str, float] = {}
                construction_quality: dict[str, float] = {}
                for construction, members in construction_groups[sym][family].items():
                    vals = {
                        sid: float(row[sid])
                        for sid in members
                        if pd.notna(row[sid]) and math.isfinite(float(row[sid]))
                    }
                    sc, _, _, se = _quality_adjusted_consensus(
                        f"{sym}:{family}:{construction}",
                        event_ns,
                        vals,
                        quality_weights,
                    )
                    if math.isfinite(sc):
                        construction_values[construction] = sc
                        construction_quality[construction] = min(
                            1.0, se / max(1, len(members))
                        )

                fc, _, _, fe = _quality_adjusted_consensus(
                    f"{sym}:{family}",
                    event_ns,
                    construction_values,
                    construction_quality,
                )
                if math.isfinite(fc):
                    family_values[family] = fc
                    family_quality[family] = min(
                        1.0,
                        fe / max(1, len(construction_groups[sym][family])),
                    )

            cc, dd, aa, ee = _quality_adjusted_consensus(
                sym, event_ns, family_values, family_quality
            )
            cv[sym], dv[sym], av[sym] = cc, dd, aa
            cov[sym] = ee / max(1, len(family_groups[sym]))

        consensus_rows.append(cv)
        disagreement_rows.append(dv)
        agreement_rows.append(av)
        coverage_rows.append(cov)

    return (
        pd.DataFrame(consensus_rows, index=returns.index, columns=symbols, dtype=float),
        pd.DataFrame(disagreement_rows, index=returns.index, columns=symbols, dtype=float),
        pd.DataFrame(agreement_rows, index=returns.index, columns=symbols, dtype=float),
        pd.DataFrame(coverage_rows, index=returns.index, columns=symbols, dtype=float),
    )


class HierarchicalFactorEngine:
    """Streams -> sampling strata -> chart families -> symbols -> factor."""

    def build(
        self,
        returns: pd.DataFrame,
        stream_to_symbol: Mapping[str, str],
        definition: EnsembleDefinition,
        *,
        quality_weights: Mapping[str, float] | None = None,
        stream_to_family: Mapping[str, str] | None = None,
        stream_to_construction: Mapping[str, str] | None = None,
    ) -> HierarchicalFusionResult:
        symbol_returns, disagreement, agreement, coverage = fuse_representations_by_symbol(
            returns,
            stream_to_symbol,
            quality_weights=quality_weights,
            stream_to_family=stream_to_family,
            stream_to_construction=stream_to_construction,
        )
        missing = [c for c in definition.components if c not in symbol_returns.columns]
        if missing:
            raise KeyError(f"factor definition references missing symbol consensus: {missing}")

        # Carry cumulative state through a missing decision instant, but keep the
        # actual level missing at that instant so absence is not exposed as a
        # fabricated flat observation.
        log_levels = symbol_returns.fillna(0.0).cumsum()
        levels = np.exp(log_levels).where(symbol_returns.notna())
        factor = FactorEnsembleEngine().build(levels, definition)
        return HierarchicalFusionResult(
            symbol_returns, disagreement, agreement, coverage, factor
        )

    def build_from_manifests(
        self,
        returns: pd.DataFrame,
        manifests,
        definition: EnsembleDefinition,
        *,
        quality_weights: Mapping[str, float] | None = None,
        require_reviewable_identity: bool = True,
    ) -> HierarchicalFusionResult:
        """Build the representation-safe symbol plane from stream manifests.

        Chart family and sampling construction are separate required dimensions.
        Unknown chart family or unknown sampling construction fails closed by
        default rather than being guessed from cadence.
        """
        by_id = {m.identity.stream_id: m for m in manifests}
        stream_to_symbol: dict[str, str] = {}
        stream_to_family: dict[str, str] = {}
        stream_to_construction: dict[str, str] = {}
        unresolved: list[str] = []

        for sid in returns.columns:
            manifest = by_id.get(sid)
            if manifest is None:
                continue
            claim = manifest.metadata.get("representation_claim", {})
            family = str(claim.get("family", "unknown"))
            construction = str(claim.get("construction", "unknown"))
            if require_reviewable_identity and (
                family in {"unknown", "time_bars_unspecified"}
                or construction == "unknown"
            ):
                unresolved.append(sid)
                continue
            stream_to_symbol[sid] = manifest.identity.symbol
            stream_to_family[sid] = family
            stream_to_construction[sid] = construction

        if unresolved:
            raise ValueError(
                "representation identity unresolved for streams: "
                + ", ".join(sorted(unresolved))
            )

        if quality_weights is None:
            from .quality import quality_score

            quality_weights = {
                sid: quality_score(by_id[sid]) for sid in stream_to_symbol
            }

        return self.build(
            returns,
            stream_to_symbol,
            definition,
            quality_weights=quality_weights,
            stream_to_family=stream_to_family,
            stream_to_construction=stream_to_construction,
        )
