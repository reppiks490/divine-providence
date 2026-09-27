from __future__ import annotations

from .contracts import Advisory, WorldState
from .uncertainty import Uncertainty


def govern(state: WorldState, uncertainty: Uncertainty, weights: dict[str, float], *, evidence_version: str,
           max_ood: float = 0.65, max_uncertainty: float = 0.70, min_state_confidence: float = 0.45) -> Advisory:
    reasons: list[str] = []
    if state.ood_score > max_ood:
        reasons.append("OOD_TOO_HIGH")
    if uncertainty.aggregate > max_uncertainty:
        reasons.append("UNCERTAINTY_TOO_HIGH")
    if state.confidence < min_state_confidence:
        reasons.append("STATE_CONFIDENCE_LOW")
    if not weights or sum(weights.values()) <= 0.0:
        reasons.append("NO_SUITABLE_EXPERT")
    abstain = bool(reasons)
    risk = 0.0 if abstain else max(0.0, min(1.0, state.confidence * (1.0 - uncertainty.aggregate)))
    return Advisory(
        state_id=state.state_id, state_confidence=state.confidence, ood_score=state.ood_score,
        expert_weights=weights, risk_multiplier=risk, abstain=abstain,
        reason_codes=tuple(reasons), evidence_version=evidence_version, production_authorized=False,
    )
