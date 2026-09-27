#!/usr/bin/env python3
"""Recency weighting for event-driven research without future leakage."""
from datetime import datetime, timezone
from math import exp, log


def _parse(ts):
    if isinstance(ts, datetime):
        dt=ts
    else:
        s=str(ts).strip().replace('Z','+00:00')
        dt=datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_seconds(event_time, now):
    event=_parse(event_time); current=_parse(now)
    seconds=(current-event).total_seconds()
    if seconds < -1:
        raise ValueError('event timestamp is in the future relative to analysis time')
    return max(0.0, seconds)


def recency_score(event_time, now, half_life_hours=48.0):
    hours=age_seconds(event_time, now)/3600.0
    if half_life_hours <= 0:
        raise ValueError('half_life_hours must be positive')
    return round(exp(-log(2.0)*hours/float(half_life_hours)), 8)


def freshness_bucket(event_time, now):
    minutes=age_seconds(event_time, now)/60.0
    if minutes <= 15: return 'breaking'
    if minutes <= 360: return 'intraday'
    if minutes <= 1440: return 'today'
    if minutes <= 10080: return 'recent'
    if minutes <= 43200: return 'current'
    return 'historical'
