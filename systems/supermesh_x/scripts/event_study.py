#!/usr/bin/env python3
"""Small, dependency-free event-study primitives for market-impact analysis."""
from math import isfinite


def abnormal_return(actual_return, counterfactual_return):
    a=float(actual_return); c=float(counterfactual_return)
    if not (isfinite(a) and isfinite(c)):
        raise ValueError('returns must be finite')
    return a-c


def cumulative_abnormal_return(abnormal_returns):
    vals=[float(v) for v in abnormal_returns]
    if not all(isfinite(v) for v in vals):
        raise ValueError('returns must be finite')
    return sum(vals)


def placebo_check(pre_event_abnormal_returns, threshold=0.01):
    vals=[abs(float(v)) for v in pre_event_abnormal_returns]
    peak=max(vals, default=0.0)
    return {
        'pretrend_detected': peak > float(threshold),
        'peak_abs_pre_event_return': peak,
        'threshold': float(threshold),
        'interpretation': 'pre-event movement weakens clean event attribution' if peak > float(threshold) else 'no large pre-event abnormal move detected',
    }
