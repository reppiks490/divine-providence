from __future__ import annotations

from ..contracts import DisagreementCase, ObservationEnvelope
from .validate import validate_same_instant


_TYPE_BY_DIMENSION = {
    "direction": "DIRECTIONAL",
    "confidence": "CONFIDENCE",
    "regime": "REGIME",
    "risk": "RISK",
}


def detect_disagreements(observations: tuple[ObservationEnvelope, ...]) -> tuple[DisagreementCase, ...]:
    validate_same_instant(observations)
    ordered = tuple(sorted(observations, key=lambda item: item.artifact_id))
    dimensions = sorted({name for item in ordered for name, _ in item.dimensions})
    cases: list[DisagreementCase] = []

    for dimension in dimensions:
        present: list[tuple[str, str]] = []
        for item in ordered:
            mapping = dict(item.dimensions)
            if dimension in mapping:
                present.append((item.artifact_id, mapping[dimension]))
        if len(present) < 2:
            continue
        values = tuple(value for _, value in present)
        if len(set(values)) <= 1:
            continue
        cases.append(
            DisagreementCase(
                decision_instant=ordered[0].decision_instant,
                dimension=dimension,
                observation_ids=tuple(identifier for identifier, _ in present),
                values=values,
                disagreement_type=_TYPE_BY_DIMENSION.get(dimension, "VALUE"),
            )
        )
    return tuple(cases)
