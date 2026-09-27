from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from .contracts import StreamManifest
from .quality import quality_score


@dataclass(frozen=True, slots=True)
class IntegrityPolicy:
    """Hard admission policy for model/factor inputs.

    Catalog preservation and model admission are intentionally separate: a stream
    can remain fully discoverable/replayable while failing this gate.
    """

    min_quality_score: float = 0.50
    max_invalid_timestamp_rate: float = 0.0
    max_nonnumeric_ohlc_rate: float = 0.0
    max_inconsistent_ohlc_rate: float = 0.0
    reject_backward_time: bool = True
    reject_duplicate_headers: bool = True
    reject_missing_ohlc: bool = True
    reject_bad_header: bool = True
    reject_appledouble: bool = True

    def __post_init__(self) -> None:
        for name in (
            "min_quality_score",
            "max_invalid_timestamp_rate",
            "max_nonnumeric_ohlc_rate",
            "max_inconsistent_ohlc_rate",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0,1]")


@dataclass(frozen=True, slots=True)
class IntegrityAssessment:
    stream_id: str
    admitted: bool
    quality_score: float
    usable_fraction: float
    invalid_timestamp_rate: float
    nonnumeric_ohlc_rate: float
    inconsistent_ohlc_rate: float
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_manifest(m: StreamManifest, policy: IntegrityPolicy | None = None) -> IntegrityAssessment:
    policy = policy or IntegrityPolicy()
    flags = set(m.quality_flags)
    rows = max(1, int(m.row_count))
    invalid = int(m.metadata.get("invalid_timestamp_rows", 0))
    nonnumeric = int(m.metadata.get("nonnumeric_ohlc_rows", 0))
    inconsistent = int(m.metadata.get("inconsistent_ohlc_rows", 0))
    usable = int(m.metadata.get("usable_ohlc_rows", max(0, m.row_count - nonnumeric - inconsistent)))

    invalid_rate = invalid / max(1, m.row_count + invalid)
    nonnumeric_rate = nonnumeric / rows
    inconsistent_rate = inconsistent / rows
    usable_fraction = usable / rows
    q = quality_score(m)

    blockers: list[str] = []
    warnings: list[str] = []
    if m.row_count <= 0:
        blockers.append("no_usable_rows")
    if policy.reject_appledouble and "appledouble" in flags:
        blockers.append("appledouble")
    if policy.reject_bad_header and "bad_header" in flags:
        blockers.append("bad_header")
    if policy.reject_missing_ohlc and "missing_ohlc" in flags:
        blockers.append("missing_ohlc")
    if policy.reject_duplicate_headers and "duplicate_header" in flags:
        blockers.append("duplicate_header")
    if policy.reject_backward_time and "backward_time" in flags:
        blockers.append("backward_time")
    if invalid_rate > policy.max_invalid_timestamp_rate:
        blockers.append("invalid_timestamp_rate")
    if nonnumeric_rate > policy.max_nonnumeric_ohlc_rate:
        blockers.append("nonnumeric_ohlc_rate")
    if inconsistent_rate > policy.max_inconsistent_ohlc_rate:
        blockers.append("inconsistent_ohlc_rate")
    if q < policy.min_quality_score:
        blockers.append("quality_below_floor")

    # These are uncertainty conditions, not automatic corruption.
    for flag in ("claim_mismatch", "cadence_ambiguous", "fractional_time", "repeated_time"):
        if flag in flags:
            warnings.append(flag)
    hyp = (m.metadata.get("representation_hypothesis") or {}).get("kind")
    if hyp and hyp != "fixed_time_candidate":
        warnings.append(f"representation:{hyp}")

    return IntegrityAssessment(
        stream_id=m.identity.stream_id,
        admitted=not blockers,
        quality_score=q,
        usable_fraction=max(0.0, min(1.0, usable_fraction)),
        invalid_timestamp_rate=invalid_rate,
        nonnumeric_ohlc_rate=nonnumeric_rate,
        inconsistent_ohlc_rate=inconsistent_rate,
        blockers=tuple(sorted(set(blockers))),
        warnings=tuple(sorted(set(warnings))),
    )


def partition_by_integrity(
    manifests: Iterable[StreamManifest], policy: IntegrityPolicy | None = None
) -> tuple[list[StreamManifest], list[IntegrityAssessment]]:
    admitted: list[StreamManifest] = []
    rejected: list[IntegrityAssessment] = []
    for m in manifests:
        a = assess_manifest(m, policy)
        if a.admitted:
            admitted.append(m)
        else:
            rejected.append(a)
    return admitted, rejected
