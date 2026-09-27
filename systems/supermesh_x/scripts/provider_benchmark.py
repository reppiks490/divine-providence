#!/usr/bin/env python3
"""Summarize observed provider performance into a compact routing health score."""
import math


def _p95(values):
    if not values:
        return 0.0
    xs=sorted(float(v) for v in values)
    idx=max(0, min(len(xs)-1, math.ceil(0.95*len(xs))-1))
    return xs[idx]


def summarize(samples):
    if not samples:
        return {
            'state':'unverified',
            'success_rate':0.0,
            'latency_p95_ms':0.0,
            'quality_mean':0.0,
            'health':0.0,
            'sample_count':0,
        }
    n=len(samples)
    success=sum(1 for s in samples if bool(s.get('ok')))/n
    latencies=[max(0.0,float(s.get('latency_ms',0.0))) for s in samples]
    qualities=[max(0.0,min(1.0,float(s.get('quality',0.5)))) for s in samples]
    p95=_p95(latencies)
    q=sum(qualities)/n

    latency_score=1.0/(1.0+(p95/1000.0))
    health=max(0.0,min(1.0,0.60*success+0.25*q+0.15*latency_score))
    state='ready' if success>=0.95 else 'degraded' if success>=0.50 else 'unavailable'
    return {
        'state':state,
        'success_rate':round(success,6),
        'latency_p95_ms':round(p95,3),
        'quality_mean':round(q,6),
        'health':round(health,6),
        'sample_count':n,
    }
