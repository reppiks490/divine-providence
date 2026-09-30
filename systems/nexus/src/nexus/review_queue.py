from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable

from .contracts import StreamManifest


_HIGH_FLAGS = {
    "backward_time", "bad_header", "missing_ohlc", "non_numeric",
    "duplicate_header", "ohlc_inconsistent", "claim_mismatch",
}
_MEDIUM_FLAGS = {
    "cadence_ambiguous", "fractional_time", "repeated_time",
    "event_driven_representation", "derived_representation",
}


@dataclass(frozen=True, slots=True)
class RepresentationReviewCandidate:
    stream_id: str
    source_path: str
    venue: str | None
    symbol: str
    filename_claim: str | None
    observed_cadence_ns: int | None
    cadence_confidence: float
    hypothesis_kind: str
    hypothesis_confidence: float
    quality_flags: tuple[str, ...]
    row_count: int
    priority: str
    priority_score: int
    review_reasons: tuple[str, ...]
    evidence_required: tuple[str, ...]
    fixed_interval_candidate_ns: int | None
    timestamp_semantics_candidate: str
    authoritative: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepresentationReviewQueue:
    schema: str
    candidates: tuple[RepresentationReviewCandidate, ...]
    family_counts: tuple[tuple[str, int], ...]
    queue_hash: str

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "candidates": [c.to_dict() for c in self.candidates],
            "family_counts": [[k, v] for k, v in self.family_counts],
            "queue_hash": self.queue_hash,
        }

    def verify(self) -> bool:
        body = {
            "schema": self.schema,
            "candidates": [c.to_dict() for c in self.candidates],
            "family_counts": [[k, v] for k, v in self.family_counts],
        }
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return digest == self.queue_hash


def _priority(manifest: StreamManifest) -> tuple[str, int, list[str]]:
    flags = set(manifest.quality_flags)
    reasons: list[str] = []
    score = 0
    high = sorted(flags & _HIGH_FLAGS)
    medium = sorted(flags & _MEDIUM_FLAGS)
    if high:
        score += 100 + 10 * len(high); reasons.extend(f"flag:{x}" for x in high)
    if medium:
        score += 40 + 5 * len(medium); reasons.extend(f"flag:{x}" for x in medium)
    hyp = manifest.metadata.get("representation_hypothesis") or {}
    kind = str(hyp.get("kind", "unknown"))
    confidence = float(hyp.get("confidence", 0.0) or 0.0)
    cadence_confidence=float(manifest.cadence_confidence)
    if kind not in {"fixed_time_candidate"}:
        score += 30; reasons.append(f"hypothesis:{kind}")
    if not math.isfinite(confidence):
        score += 100; reasons.append("hypothesis_confidence_nonfinite")
        confidence=0.0
    elif confidence < 0.95:
        score += 20; reasons.append("hypothesis_confidence_below_0.95")
    cadence=manifest.observed_cadence_ns
    if cadence is None:
        score += 25; reasons.append("observed_cadence_unknown")
    elif type(cadence) is not int or cadence <= 0:
        score += 100; reasons.append("observed_cadence_invalid")
    if not math.isfinite(cadence_confidence):
        score += 100; reasons.append("cadence_confidence_nonfinite")
    elif cadence_confidence < 0.95:
        score += 15; reasons.append("cadence_confidence_below_0.95")
    if not reasons:
        reasons.append("clean_but_unreviewed")
    label = "P0" if score >= 100 else ("P1" if score >= 50 else "P2")
    return label, score, reasons


def build_representation_review_queue(manifests: Iterable[StreamManifest]) -> RepresentationReviewQueue:
    candidates: list[RepresentationReviewCandidate] = []
    families: dict[str, int] = {}
    unique:dict[str,StreamManifest]={}
    for manifest in sorted(manifests,key=lambda m:(m.identity.stream_id,m.identity.source_path)):
        sid=manifest.identity.stream_id
        old=unique.get(sid)
        if old is not None:
            if old.identity.raw_sha256 != manifest.identity.raw_sha256:
                raise ValueError(f"stream_id collision with different raw hashes: {sid}")
            continue
        unique[sid]=manifest
    for manifest in unique.values():
        flags = set(manifest.quality_flags)
        if manifest.row_count <= 0 or "appledouble" in flags:
            continue
        hyp = manifest.metadata.get("representation_hypothesis") or {}
        kind = str(hyp.get("kind", "unknown"))
        confidence = float(hyp.get("confidence", 0.0) or 0.0)
        if not math.isfinite(confidence):
            confidence=0.0
        priority, score, reasons = _priority(manifest)
        family = f"{manifest.identity.venue or '?'}:{manifest.identity.symbol}:{kind}:{manifest.identity.filename_claim or '?'}"
        families[family] = families.get(family, 0) + 1
        # A cadence candidate is useful for review, but never establishes timestamp
        # semantics. BAR_OPEN vs BAR_CLOSE must come from source documentation or
        # another attested evidence artifact.
        fixed_candidate = manifest.observed_cadence_ns if (
            kind == "fixed_time_candidate"
            and isinstance(manifest.observed_cadence_ns,int)
            and manifest.observed_cadence_ns>0
        ) else None
        candidates.append(
            RepresentationReviewCandidate(
                stream_id=manifest.identity.stream_id,
                source_path=manifest.identity.source_path,
                venue=manifest.identity.venue,
                symbol=manifest.identity.symbol,
                filename_claim=manifest.identity.filename_claim,
                observed_cadence_ns=manifest.observed_cadence_ns if isinstance(manifest.observed_cadence_ns,int) and manifest.observed_cadence_ns>0 else None,
                cadence_confidence=float(manifest.cadence_confidence) if math.isfinite(float(manifest.cadence_confidence)) else 0.0,
                hypothesis_kind=kind,
                hypothesis_confidence=confidence,
                quality_flags=tuple(sorted(flags)),
                row_count=int(manifest.row_count),
                priority=priority,
                priority_score=score,
                review_reasons=tuple(reasons),
                evidence_required=(
                    "source/vendor representation definition",
                    "timestamp semantics evidence (bar-open/bar-close/event-completion)",
                    "timezone/session evidence",
                    "volume semantics evidence when volume is present",
                ),
                fixed_interval_candidate_ns=fixed_candidate,
                timestamp_semantics_candidate="UNKNOWN_REQUIRES_REVIEW",
                authoritative=False,
            )
        )
    candidates.sort(key=lambda c: (-c.priority_score, c.symbol, c.source_path, c.stream_id))
    family_counts = tuple(sorted(families.items()))
    body = {
        "schema": "nexus.representation-review-queue.v1",
        "candidates": [c.to_dict() for c in candidates],
        "family_counts": [[k, v] for k, v in family_counts],
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return RepresentationReviewQueue(body["schema"], tuple(candidates), family_counts, digest)
