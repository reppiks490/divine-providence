from __future__ import annotations

from .contracts import ExpertEvidence, WorldState


def route_experts(state: WorldState, experts: list[ExpertEvidence]) -> dict[str, float]:
    raw: dict[str, float] = {}
    for e in experts:
        state_support = 1.0 if not e.supported_states or state.state_id in e.supported_states else 0.15
        competence = max(0.0, e.score)
        calibration = max(0.0, 1.0 - e.calibration_error)
        in_distribution = max(0.0, 1.0 - max(state.ood_score, e.ood_score))
        health = max(0.0, e.recent_health)
        raw[e.expert_id] = state_support * competence * calibration * in_distribution * health
    total = sum(raw.values())
    if total <= 0.0:
        return {k: 0.0 for k in raw}
    return {k: v / total for k, v in raw.items()}
