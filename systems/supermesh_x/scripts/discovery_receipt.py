#!/usr/bin/env python3
"""Compact audit receipt for dynamic capability discovery."""

SAFE_FIELDS = ("id", "name", "score", "capabilities", "provider", "service", "version", "schema_fingerprint")


def _safe(candidate):
    return {k: candidate[k] for k in SAFE_FIELDS if k in candidate}


def build_receipt(query, candidates, limit=3, status="complete", stop_reason="satisfied", withheld_preview=5):
    limit = max(0, int(limit))
    ordered = sorted(candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True)
    exposed = ordered[:limit]
    withheld = ordered[limit:]
    return {
        "query": str(query),
        "status": status,
        "stop_reason": stop_reason,
        "candidate_count": len(ordered),
        "exposed": [_safe(x) for x in exposed],
        "withheld_count": len(withheld),
        "top_withheld": [_safe(x) for x in withheld[:max(0, int(withheld_preview))]],
    }
