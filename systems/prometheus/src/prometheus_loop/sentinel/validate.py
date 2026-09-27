from __future__ import annotations

from ..contracts import ObservationEnvelope


def validate_same_instant(observations: tuple[ObservationEnvelope, ...]) -> None:
    if len(observations) < 2:
        raise ValueError("at least two observations are required")
    instants = {item.decision_instant for item in observations}
    if len(instants) != 1:
        raise ValueError("observations do not share one decision instant")
    unknown = [item.sibling for item in observations if item.availability_state != "KNOWN"]
    if unknown:
        raise ValueError(f"unknown or unverified availability for: {', '.join(sorted(unknown))}")
