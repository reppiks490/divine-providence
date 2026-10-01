from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from typing import Any, Mapping

from .filename import timeframe_claim_to_ns
from .review_queue import verify_representation_review_queue_payload


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
    if not verify_representation_review_queue_payload(dict(review_queue)):
        raise ValueError("invalid or tampered representation review queue")
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
    body = {
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
    body["triage_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_representation_review_triage(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != SCHEMA:
        return False
    supplied=payload.get("triage_hash")
    if not isinstance(supplied,str) or len(supplied)!=64:
        return False
    try:
        int(supplied,16)
    except ValueError:
        return False
    body=dict(payload);body.pop("triage_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied!=expected:
        return False
    if (
        body.get("authoritative_resolution_required") is not True
        or body.get("auto_resolved_count") != 0
        or body.get("production_authorized") is not False
    ):
        return False
    clusters=body.get("clusters")
    if not isinstance(clusters,list) or body.get("cluster_count") != len(clusters):
        return False
    counts=Counter();stream_total=0;stream_ids=[]
    cluster_reason_counts=body.get("review_reason_counts")
    cluster_evidence_counts=body.get("evidence_requirement_counts")
    if not isinstance(cluster_reason_counts,Mapping) or not isinstance(cluster_evidence_counts,Mapping):
        return False
    for mapping in (cluster_reason_counts,cluster_evidence_counts):
        if any(
            not isinstance(k,str) or not k
            or type(v) is not int or v < 0
            for k,v in mapping.items()
        ):
            return False
    for row in clusters:
        if not isinstance(row,Mapping):
            return False
        cls=str(row.get("triage_class") or "")
        venue=str(row.get("venue") or "")
        claim=row.get("filename_claim")
        cadence=row.get("observed_cadence_ns")
        ids=row.get("stream_ids")
        symbols=row.get("symbols")
        count=row.get("stream_count")
        if (
            not cls or not venue or not isinstance(ids,list) or not ids
            or any(not isinstance(x,str) or not x for x in ids)
            or not isinstance(symbols,list) or not symbols
            or any(not isinstance(x,str) or not x for x in symbols)
            or len(set(symbols)) != len(symbols)
            or type(count) is not int or count < 1 or count != len(ids)
            or len(set(ids)) != len(ids)
            or row.get("authoritative_resolution_required") is not True
            or row.get("auto_resolved") is not False
        ):
            return False
        if cadence is not None and (type(cadence) is not int or cadence <= 0):
            return False
        if claim is not None and not isinstance(claim,str):
            return False
        counts[cls]+=count
        stream_total+=count
        stream_ids.extend(str(x) for x in ids)
    if len(set(stream_ids)) != len(stream_ids):
        return False
    return (
        body.get("p0_count") == stream_total
        and body.get("triage_class_counts") == dict(sorted(counts.items()))
        and type(body.get("p2_count")) is int
        and body["p2_count"] >= 0
        and body.get("cluster_count")==len(clusters)
    )
