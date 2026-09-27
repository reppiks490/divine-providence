#!/usr/bin/env python3
"""Provider readiness and health scoring for SuperMesh-X."""

STATE_BASE = {
    "ready": (True, 1.0),
    "quota_constrained": (True, 0.55),
    "degraded": (True, 0.60),
    "preflight_required": (False, 0.05),
    "auth_required": (False, 0.02),
    "unavailable": (False, 0.0),
}


def _clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(value)))


def score_state(state):
    name = state.get("state", "unavailable")
    routable, multiplier = STATE_BASE.get(name, (False, 0.0))
    health = _clamp(state.get("health", 1.0))
    if name == "quota_constrained":
        quota = _clamp(state.get("quota_remaining_ratio", 0.0))
        multiplier *= 0.5 + 0.5 * quota
    return routable, round(health * multiplier, 6)


def rank_candidates(candidates, states):
    ranked = []
    for provider in candidates:
        state = states.get(provider, {"state": "unavailable", "health": 0.0})
        routable, score = score_state(state)
        ranked.append({
            "provider": provider,
            "state": state.get("state", "unavailable"),
            "routable": routable,
            "score": score,
        })
    ranked.sort(key=lambda row: (row["routable"], row["score"]), reverse=True)
    return ranked
