#!/usr/bin/env python3
"""Capability-specific provider feedback profile using bounded EWMA signals."""


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def _latency_score(latency_ms):
    return 1.0 / (1.0 + max(0.0, float(latency_ms)) / 1000.0)


def update_profile(profile, capability, ok, quality=0.5, latency_ms=0.0, alpha=0.25):
    out = {k: dict(v) for k, v in (profile or {}).items()}
    row = dict(out.get(capability, {}))
    a = _clamp(alpha)
    success = 1.0 if ok else 0.0
    quality = _clamp(quality)
    latency = _latency_score(latency_ms)
    reward = 0.55 * success + 0.30 * quality + 0.15 * latency
    prior = float(row.get("score", 0.5))
    row.update({
        "score": round((1.0 - a) * prior + a * reward, 6),
        "success_ewma": round((1.0 - a) * float(row.get("success_ewma", 0.5)) + a * success, 6),
        "quality_ewma": round((1.0 - a) * float(row.get("quality_ewma", 0.5)) + a * quality, 6),
        "latency_ewma": round((1.0 - a) * float(row.get("latency_ewma", 0.5)) + a * latency, 6),
        "samples": int(row.get("samples", 0)) + 1,
    })
    out[capability] = row
    return out


def capability_score(profile, capability):
    return _clamp((profile or {}).get(capability, {}).get("score", 0.5))
