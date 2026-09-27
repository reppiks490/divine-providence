#!/usr/bin/env python3
"""Point-in-time guards for historical research and backtesting."""
from datetime import datetime, timezone


def _parse(ts):
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def point_in_time_usable(evidence, decision_time):
    """True only when evidence was available by the decision timestamp."""
    available = _parse(evidence.get("available_time"))
    decision = _parse(decision_time)
    if available is None or decision is None:
        return False
    return available <= decision


def temporal_status(evidence, decision_time):
    if point_in_time_usable(evidence, decision_time):
        return "usable"
    if evidence.get("available_time"):
        return "future_known"
    return "availability_unknown"
