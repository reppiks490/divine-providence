#!/usr/bin/env python3
"""Feedback-aware capability director and self-healing replacement planner."""

from routing_kernel import route_capability


def _feedback_score(feedback, provider, capability):
    row = (feedback or {}).get(provider, {}).get(capability, {})
    return max(0.0, min(1.0, float(row.get("score", 0.5))))


def direct_capability(capability, states, catalog, runtime_profile, feedback=None, breaker_metrics=None, now=0, limit=3):
    routed = route_capability(
        capability=capability,
        states=states,
        catalog=catalog,
        runtime_profile=runtime_profile,
        breaker_metrics=breaker_metrics or {},
        now=now,
        limit=max(limit, len(catalog)),
    )
    selected = []
    for row in routed["selected"]:
        fb = _feedback_score(feedback, row["provider"], capability)
        base = float(row.get("combined_score", row.get("state_score", 0.0)))
        item = dict(row)
        item["feedback_score"] = fb
        item["adaptive_score"] = round(0.65 * base + 0.35 * fb, 6)
        selected.append(item)
    selected.sort(key=lambda x: x["adaptive_score"], reverse=True)
    return {
        "capability": capability,
        "selected": selected[:limit],
        "blocked": routed["blocked"],
        "policy": routed["policy"] + " -> capability-feedback",
    }


def replacement_plan(current_provider, capability, surface_change, states, catalog, runtime_profile, feedback=None, breaker_metrics=None, now=0):
    if not surface_change.get("breaking", False):
        return {"action": "keep", "current": current_provider, "replacement": None, "reason": "surface_compatible"}
    routed = direct_capability(
        capability,
        states,
        catalog,
        runtime_profile,
        feedback=feedback,
        breaker_metrics=breaker_metrics,
        now=now,
        limit=max(1, len(catalog)),
    )
    for row in routed["selected"]:
        if row["provider"] != current_provider:
            return {
                "action": "replace",
                "current": current_provider,
                "replacement": row["provider"],
                "reason": "breaking_surface_change",
                "candidate": row,
            }
    return {"action": "degrade", "current": current_provider, "replacement": None, "reason": "no_compatible_fallback"}
