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
        q = float(quality.get(sid, 1.0))
        if not math.isfinite(q) or not 0.0 <= q <= 1.0:
            raise ValueError(f"quality weight for {sid!r} must be finite and in [0,1]")
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
    effective = float(sum(float(quality.get(sid,1.0)) for sid in c.contributions))
    return consensus, disagreement, agreement, effective


def _row_values(row: pd.Series, members: list[str]) -> dict[str, float]:
    return {
        sid: float(row[sid])
        for sid in members
        if pd.notna(row[sid]) and math.isfinite(float(row[sid]))
    }


def fuse_representations_by_symbol(
    returns: pd.DataFrame,
    stream_to_symbol: Mapping[str, str],
    *,
    quality_weights: Mapping[str, float] | None = None,
    stream_to_family: Mapping[str, str] | None = None,
    stream_to_geometry: Mapping[str, str] | None = None,
    stream_to_construction: Mapping[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fuse correlated views without count inflation.

    Preferred hierarchy:
      streams -> sampling construction -> price geometry -> chart/view family
      -> symbol.

    Each tier emits one quality-adjusted value to the next tier. This prevents
    many files/timeframes/geometry variants in one branch from receiving extra
    evidence weight merely because more physical CSVs exist.

    Backward compatibility:
    - no family map: direct stream -> symbol robust consensus;
    - family but no geometry: construction -> family -> symbol;
    - family+geometry but no construction: streams -> geometry -> family -> symbol.
    """
    if not isinstance(returns,pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")
    if returns.columns.duplicated().any():
        raise ValueError("returns columns must be unique")
    try:
        numeric=returns.astype(float)
    except (TypeError,ValueError) as exc:
        raise ValueError("representation returns must be numeric") from exc
    if np.isinf(numeric.to_numpy(dtype=float,copy=False)).any():
        raise ValueError("representation returns contain infinite values")
    returns=numeric
    for sid,sym in stream_to_symbol.items():
        if not isinstance(sid,str) or not sid or not isinstance(sym,str) or not sym:
            raise ValueError("stream_to_symbol requires non-empty string identities")
    if quality_weights is not None:
        for sid,value in quality_weights.items():
            q=float(value)
            if not math.isfinite(q) or not 0.0 <= q <= 1.0:
                raise ValueError(f"quality weight for {sid!r} must be finite and in [0,1]")
    streams = [col for col in returns.columns if col in stream_to_symbol]
    symbol_groups: dict[str, list[str]] = {}
    for sid in streams:
        symbol_groups.setdefault(stream_to_symbol[sid], []).append(sid)
    symbols = sorted(symbol_groups)

    consensus_rows = []
    disagreement_rows = []
    agreement_rows = []
    coverage_rows = []

    for ordinal, (idx, row) in enumerate(returns[streams].iterrows()):
        try:
            event_ns = int(idx)
        except (TypeError, ValueError):
            event_ns = ordinal

        cv: dict[str, float] = {}
        dv: dict[str, float] = {}
        av: dict[str, float] = {}
        cov: dict[str, float] = {}

        for sym in symbols:
            members = symbol_groups[sym]

            if stream_to_family is None:
                vals = _row_values(row, members)
                cc, dd, aa, ee = _quality_adjusted_consensus(
                    sym, event_ns, vals, quality_weights
                )
                cv[sym], dv[sym], av[sym] = cc, dd, aa
                cov[sym] = ee / max(1, len(members))
                continue

            families: dict[str, list[str]] = {}
            for sid in members:
                families.setdefault(str(stream_to_family.get(sid, "unknown")), []).append(sid)

            family_values: dict[str, float] = {}
            family_quality: dict[str, float] = {}

            for family, family_members in families.items():
                if stream_to_geometry is None:
                    if stream_to_construction is None:
                        vals = _row_values(row, family_members)
                        fc, _, _, fe = _quality_adjusted_consensus(
                            f"{sym}:{family}", event_ns, vals, quality_weights
                        )
                        denom = len(family_members)
                    else:
                        constructions: dict[str, list[str]] = {}
                        for sid in family_members:
                            constructions.setdefault(
                                str(stream_to_construction.get(sid, "unknown")), []
                            ).append(sid)
                        construction_values: dict[str, float] = {}
                        construction_quality: dict[str, float] = {}
                        for construction, cmembers in constructions.items():
                            vals = _row_values(row, cmembers)
                            sc, _, _, se = _quality_adjusted_consensus(
                                f"{sym}:{family}:{construction}",
                                event_ns,
                                vals,
                                quality_weights,
                            )
                            if math.isfinite(sc):
                                construction_values[construction] = sc
                                construction_quality[construction] = min(
                                    1.0, se / max(1, len(cmembers))
                                )
                        fc, _, _, fe = _quality_adjusted_consensus(
                            f"{sym}:{family}",
                            event_ns,
                            construction_values,
                            construction_quality,
                        )
                        denom = len(constructions)
                    if math.isfinite(fc):
                        family_values[family] = fc
                        family_quality[family] = min(1.0, fe / max(1, denom))
                    continue

                geometries: dict[str, list[str]] = {}
                for sid in family_members:
                    geometries.setdefault(
                        str(stream_to_geometry.get(sid, "unknown")), []
                    ).append(sid)

                geometry_values: dict[str, float] = {}
                geometry_quality: dict[str, float] = {}

                for geometry, geometry_members in geometries.items():
                    if stream_to_construction is None:
                        vals = _row_values(row, geometry_members)
                        gc, _, _, ge = _quality_adjusted_consensus(
                            f"{sym}:{family}:{geometry}",
                            event_ns,
                            vals,
                            quality_weights,
                        )
                        gden = len(geometry_members)
                    else:
                        constructions: dict[str, list[str]] = {}
                        for sid in geometry_members:
                            constructions.setdefault(
                                str(stream_to_construction.get(sid, "unknown")), []
                            ).append(sid)

                        construction_values: dict[str, float] = {}
                        construction_quality: dict[str, float] = {}
                        for construction, cmembers in constructions.items():
                            vals = _row_values(row, cmembers)
                            sc, _, _, se = _quality_adjusted_consensus(
                                f"{sym}:{family}:{geometry}:{construction}",
                                event_ns,
                                vals,
                                quality_weights,
                            )
                            if math.isfinite(sc):
                                construction_values[construction] = sc
                                construction_quality[construction] = min(
                                    1.0, se / max(1, len(cmembers))
                                )

                        gc, _, _, ge = _quality_adjusted_consensus(
                            f"{sym}:{family}:{geometry}",
                            event_ns,
                            construction_values,
                            construction_quality,
                        )
                        gden = len(constructions)

                    if math.isfinite(gc):
                        geometry_values[geometry] = gc
                        geometry_quality[geometry] = min(1.0, ge / max(1, gden))

                fc, _, _, fe = _quality_adjusted_consensus(
                    f"{sym}:{family}",
                    event_ns,
                    geometry_values,
                    geometry_quality,
                )
                if math.isfinite(fc):
                    family_values[family] = fc
                    family_quality[family] = min(
                        1.0, fe / max(1, len(geometries))
                    )

            cc, dd, aa, ee = _quality_adjusted_consensus(
                sym, event_ns, family_values, family_quality
            )
            cv[sym], dv[sym], av[sym] = cc, dd, aa
            cov[sym] = ee / max(1, len(families))

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
    """Streams -> constructions -> geometries -> view families -> symbols -> factor."""

    def build(
        self,
        returns: pd.DataFrame,
        stream_to_symbol: Mapping[str, str],
        definition: EnsembleDefinition,
        *,
        quality_weights: Mapping[str, float] | None = None,
        stream_to_family: Mapping[str, str] | None = None,
        stream_to_geometry: Mapping[str, str] | None = None,
        stream_to_construction: Mapping[str, str] | None = None,
    ) -> HierarchicalFusionResult:
        symbol_returns, disagreement, agreement, coverage = fuse_representations_by_symbol(
            returns,
            stream_to_symbol,
            quality_weights=quality_weights,
            stream_to_family=stream_to_family,
            stream_to_geometry=stream_to_geometry,
            stream_to_construction=stream_to_construction,
        )
        missing = [c for c in definition.components if c not in symbol_returns.columns]
        if missing:
            raise KeyError(f"factor definition references missing symbol consensus: {missing}")

        # Build independent contiguous level segments. A missing return breaks
        # the level chain; it is never treated as a zero-return bridge.
        levels=pd.DataFrame(np.nan,index=symbol_returns.index,columns=symbol_returns.columns,dtype=float)
        for col in symbol_returns.columns:
            s=symbol_returns[col]
            groups=s.isna().cumsum()
            cumulative=s.groupby(groups).cumsum()
            level=np.exp(cumulative).where(s.notna())
            if np.isinf(level.to_numpy(dtype=float,copy=False)).any():
                raise ValueError(f"symbol return accumulation overflow for {col!r}")
            levels[col]=level
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
        require_authoritative_identity: bool = True,
        reviewed_registry=None,
    ) -> HierarchicalFusionResult:
        """Build a fail-closed, four-axis representation-safe model plane."""
        grouped:dict[str,list]={}
        for m in sorted(manifests,key=lambda x:(x.identity.stream_id,x.identity.source_path)):
            grouped.setdefault(m.identity.stream_id,[]).append(m)
        by_id={}
        for sid,rows in grouped.items():
            hashes={m.identity.raw_sha256 for m in rows}
            if len(hashes)>1:
                raise ValueError(f"stream_id collision across distinct raw contents: {sid}")
            by_id[sid]=rows[0]
        stream_to_symbol: dict[str, str] = {}
        stream_to_family: dict[str, str] = {}
        stream_to_geometry: dict[str, str] = {}
        stream_to_construction: dict[str, str] = {}
        unresolved: list[str] = []

        for sid in returns.columns:
            manifest = by_id.get(sid)
            if manifest is None:
                unresolved.append(str(sid))
                continue
            manifest_claim = manifest.metadata.get("representation_claim", {})
            claim = dict(manifest_claim) if isinstance(manifest_claim,Mapping) else {}

            if reviewed_registry is not None:
                from .review_registry import ReviewedRepresentationRegistry
                if not isinstance(reviewed_registry,ReviewedRepresentationRegistry):
                    raise TypeError("reviewed_registry must be ReviewedRepresentationRegistry or None")
                record=reviewed_registry.get(sid)
                if record is not None:
                    reviewed_claim=record.authoritative_claim_for_manifest(manifest)
                    if claim.get("authoritative") is True:
                        keys=("family","price_geometry","sampling_domain","construction")
                        if any(str(claim.get(k)) != str(reviewed_claim.get(k)) for k in keys):
                            raise ValueError(
                                f"conflicting authoritative representation identity for stream {sid}"
                            )
                    else:
                        claim=reviewed_claim

            family = str(claim.get("family", "unknown"))
            geometry = str(claim.get("price_geometry", "unknown"))
            construction = str(claim.get("construction", "unknown"))

            if require_reviewable_identity and (
                family in {"unknown", "time_bars_unspecified"}
                or geometry == "unknown"
                or construction == "unknown"
            ):
                unresolved.append(sid)
                continue
            if require_authoritative_identity and claim.get("authoritative") is not True:
                unresolved.append(sid)
                continue

            stream_to_symbol[sid] = manifest.identity.symbol
            stream_to_family[sid] = family
            stream_to_geometry[sid] = geometry
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
            stream_to_geometry=stream_to_geometry,
            stream_to_construction=stream_to_construction,
        )
