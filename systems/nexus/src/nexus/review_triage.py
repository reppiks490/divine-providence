from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from .filename import timeframe_claim_to_ns


SCHEMA = "nexus.representation-review-triage.v1"


def _classify(row: Mapping[str, Any]) -> str:
    kind = str(row.get("hypothesis_kind") or "")
    if kind in {"event_or_transformed_candidate", "event_bar_claim_candidate", "event_representation_candidate", "derived_event_candidate"}:
        return "EVENT_DRIVEN_REQUIRES_VENDOR_DEFINITION"
    if kind == "profile_view_candidate":
        return "PROFILE_VIEW_REQUIRES_EXPORT_DEFINITION"
    if kind == "derived_time_candidate":
        return "DERIVED_TIME_REQUIRES_EXPORT_PROVENANCE"
    if kind == "derived_time_mismatch_candidate":
        return "DERIVED_TIME_MISMATCH_REQUIRES_EXPORT_SETTING_EVIDENCE"
    if kind == "timeframe_mismatch_candidate":
        # A low-confidence cadence estimate can fall into the historical
        # timeframe_mismatch hypothesis even when the modal cadence numerically
        # equals the filename claim. Decide this from the actual claim/cadence,
        # not from a possibly incomplete quality-flag fixture.
        claim_ns = timeframe_claim_to_ns(row.get("filename_claim"))
        observed_ns = int(row.get("observed_cadence_ns") or 0)
        if claim_ns and observed_ns and abs(observed_ns / claim_ns - 1.0) <= 0.05:
            return "TIMEFRAME_CADENCE_MATCH_REQUIRES_EXPORT_PROVENANCE"
        return "TIMEFRAME_MISMATCH_REQUIRES_EXPORT_SETTING_EVIDENCE"
    if kind == "fixed_time_candidate":
        return "FIXED_TIME_LOW_CONFIDENCE_REQUIRES_TIMESTAMP_REVIEW"
    return "UNCLASSIFIED_REPRESENTATION_REVIEW"


def build_representation_review_triage(review_queue: Mapping[str, Any]) -> dict[str, Any]:
    """Compress representation-review work into evidence families without resolving it.

    This is an orchestration artifact only. A shared filename/cadence pattern is not
    authoritative evidence of representation type or timestamp semantics.
    """
    rows = [r for r in review_queue.get("candidates", []) if isinstance(r, Mapping)]
    p0 = [r for r in rows if str(r.get("priority")) == "P0"]
    class_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    clusters: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)

    for r in p0:
        cls = _classify(r)
        class_counts[cls] += 1
        for reason in r.get("review_reasons", []) or []:
            reason_counts[str(reason)] += 1
        for ev in r.get("evidence_required", []) or []:
            evidence_counts[str(ev)] += 1
        key = (
            cls,
            str(r.get("venue") or "?"),
            str(r.get("filename_claim") or "?"),
            int(r.get("observed_cadence_ns") or 0),
            tuple(sorted(str(x) for x in (r.get("quality_flags") or []))),
        )
        clusters[key].append(r)

    cluster_rows: list[dict[str, Any]] = []
    for key, members in clusters.items():
        cls, venue, claim, cadence, flags = key
        symbols = sorted({str(x.get("symbol") or "?") for x in members})
        stream_ids = sorted(str(x.get("stream_id") or "") for x in members if x.get("stream_id"))
        cluster_rows.append({
            "triage_class": cls,
            "venue": venue,
            "filename_claim": claim,
            "observed_cadence_ns": cadence or None,
            "quality_flags": list(flags),
            "stream_count": len(members),
            "symbols": symbols,
            "stream_ids": stream_ids,
            "authoritative_resolution_required": True,
            "auto_resolved": False,
        })

    cluster_rows.sort(key=lambda x: (-int(x["stream_count"]), x["triage_class"], x["venue"], x["filename_claim"], int(x["observed_cadence_ns"] or 0)))
    return {
        "schema": SCHEMA,
        "p0_count": len(p0),
        "p2_count": sum(str(r.get("priority")) == "P2" for r in rows),
        "triage_class_counts": dict(sorted(class_counts.items())),
        "review_reason_counts": dict(sorted(reason_counts.items())),
        "evidence_requirement_counts": dict(sorted(evidence_counts.items())),
        "cluster_count": len(cluster_rows),
        "clusters": cluster_rows,
        "authoritative_resolution_required": True,
        "auto_resolved_count": 0,
        "production_authorized": False,
    }
