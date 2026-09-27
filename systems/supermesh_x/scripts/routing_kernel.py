#!/usr/bin/env python3
"""Integrated capability routing with discovery, adapter negotiation, state and breakers."""

from capability_catalog import discover_candidates
from adapter_negotiation import negotiate_adapter
from circuit_breaker import evaluate_breaker, request_allowed
from provider_state import score_state


def route_capability(capability, states, catalog, runtime_profile, breaker_metrics=None, now=0, limit=3):
    breaker_metrics = breaker_metrics or {}
    candidates = discover_candidates([capability], catalog, runtime=runtime_profile.get("name") or runtime_profile.get("runtime") or "chatgpt")
    selected, blocked = [], []

    for provider in candidates:
        name = provider["name"]
        state = states.get(name, {"state": "unverified", "health": 0.0})
        routable, state_score = score_state(state)
        row = {
            "provider": name,
            "state": state.get("state", "unverified"),
            "state_score": state_score,
            "registry_priority": provider.get("priority", 0),
        }

        if not routable:
            row["block_reason"] = row["state"]
            blocked.append(row)
            continue

        adapter = negotiate_adapter(provider, runtime_profile)
        row["adapter"] = adapter
        if not adapter.get("compatible"):
            row["block_reason"] = adapter.get("reason", "adapter_incompatible")
            blocked.append(row)
            continue

        metrics = breaker_metrics.get(name, {})
        breaker = evaluate_breaker(metrics, now=now)
        row["breaker"] = breaker
        if not request_allowed(breaker, now=now, probe=False):
            row["block_reason"] = "circuit_open" if breaker["state"] == "open" else "circuit_probe_required"
            blocked.append(row)
            continue

        priority = max(0.0, min(100.0, float(provider.get("priority", 0)))) / 100.0
        row["combined_score"] = round(0.8 * state_score + 0.2 * priority, 6)
        row["block_reason"] = None
        selected.append(row)

    selected.sort(key=lambda r: r.get("combined_score", 0.0), reverse=True)
    blocked.sort(key=lambda r: (r.get("state_score", 0.0), r.get("registry_priority", 0)), reverse=True)
    return {
        "capability": capability,
        "selected": selected[:limit],
        "blocked": blocked,
        "policy": "discovery -> runtime-state -> adapter-negotiation -> circuit-breaker -> score",
    }
