#!/usr/bin/env python3
"""Small deterministic circuit breaker for provider routing."""


def evaluate_breaker(metrics, now, failure_threshold=3, reset_after=60):
    failures = int(metrics.get("consecutive_failures", 0))
    last_failure = metrics.get("last_failure_ts")
    if failures < failure_threshold or last_failure is None:
        return {"state": "closed", "retry_after": None}
    retry_after = float(last_failure) + float(reset_after)
    if float(now) >= retry_after:
        return {"state": "half_open", "retry_after": retry_after}
    return {"state": "open", "retry_after": retry_after}


def request_allowed(state, now, probe=False):
    name = state.get("state", "open")
    if name == "closed":
        return True
    if name == "half_open":
        return bool(probe)
    return False
