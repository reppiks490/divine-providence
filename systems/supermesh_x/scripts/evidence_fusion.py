#!/usr/bin/env python3
"""Evidence-family aware claim fusion for SuperMesh-X."""


def _weight(record):
    authority = max(0.0, min(1.0, float(record.get("authority", 0.5))))
    freshness = max(0.0, min(1.0, float(record.get("freshness", 1.0))))
    completeness = max(0.0, min(1.0, float(record.get("completeness", 1.0))))
    return authority * freshness * completeness


def fuse_claim(records):
    families = {}
    for record in records:
        family = record.get("source_family") or record.get("source") or "unknown"
        w = _weight(record)
        current = families.get(family)
        if current is None or w > current[0]:
            families[family] = (w, record.get("stance", "mention"))

    support = sum(w for w, stance in families.values() if stance == "support")
    contrast = sum(w for w, stance in families.values() if stance == "contrast")
    total = support + contrast
    confidence = 0.0 if total == 0 else abs(support - contrast) / total
    return {
        "independent_families": len(families),
        "support_weight": round(support, 6),
        "contrast_weight": round(contrast, 6),
        "has_conflict": support > 0 and contrast > 0,
        "confidence": round(confidence, 6),
        "dominant_stance": "support" if support > contrast else "contrast" if contrast > support else "unresolved",
    }
