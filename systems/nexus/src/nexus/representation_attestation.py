from __future__ import annotations

import re
import hashlib
import json
from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Mapping

from .contracts import StreamManifest
from .review_queue import verify_representation_review_queue_payload


SCHEMA = "nexus.representation-attestation-status.v1"
INPUT_SCHEMA = "nexus.representation-attestations.v1"

_UNKNOWN = {"", "UNKNOWN", "UNRESOLVED", "NOT_ATTESTED", "N/A"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _known(value: Any) -> bool:
    return _norm(value).upper() not in _UNKNOWN


def _required_dimensions(manifest: StreamManifest) -> tuple[str, ...]:
    required = [
        "source_vendor",
        "vendor_symbol",
        "chart_type",
        "timeframe_or_event_definition",
        "timestamp_semantics",
        "timezone",
        "session_definition",
    ]
    columns = {str(c).strip().lower() for c in manifest.columns}
    if "volume" in columns:
        required.append("volume_semantics")
    return tuple(required)


def _attestation_identity_valid(
    row: Mapping[str, Any],
    manifest: StreamManifest,
    source_paths: set[str] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if _norm(row.get("stream_id")) != manifest.identity.stream_id:
        errors.append("stream_id_mismatch")
    raw_sha = _norm(row.get("raw_sha256")).lower()
    if not _SHA256_RE.fullmatch(raw_sha):
        errors.append("raw_sha256_missing_or_invalid")
    elif raw_sha != manifest.identity.raw_sha256.lower():
        errors.append("raw_sha256_mismatch")
    source_path = _norm(row.get("source_path"))
    allowed_paths=source_paths or {manifest.identity.source_path}
    if source_path and source_path not in allowed_paths:
        errors.append("source_path_mismatch")
    return not errors, errors


def _attestation_evidence_valid(row: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if row.get("reviewed") is not True:
        errors.append("reviewed_true_required")
    if not _known(row.get("reviewed_by")):
        errors.append("reviewed_by_required")
    reviewed_at=_norm(row.get("reviewed_at"))
    if not reviewed_at:
        errors.append("reviewed_at_required")
    else:
        try:
            datetime.fromisoformat(reviewed_at.replace("Z","+00:00"))
        except ValueError:
            errors.append("reviewed_at_invalid")
    source_refs = row.get("evidence_sources") or []
    if (
        not isinstance(source_refs, list)
        or not any(isinstance(x,str) and _known(x) for x in source_refs)
    ):
        errors.append("evidence_source_required")
    evidence_hash = _norm(row.get("evidence_sha256")).lower()
    if not evidence_hash:
        errors.append("evidence_sha256_required")
    elif not _SHA256_RE.fullmatch(evidence_hash):
        errors.append("evidence_sha256_invalid")
    return not errors, errors


def build_representation_attestation_status(
    manifests: Iterable[StreamManifest],
    review_queue: Mapping[str, Any],
    attestations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate export-specific representation attestations fail-closed.

    General vendor documentation can clarify syntax, but a P0 review is only
    dischargeable when evidence is bound to the *exact stream bytes*. This
    evaluator therefore requires the manifest raw SHA-256 plus explicit answers
    for the representation dimensions that affect causal replay.

    A resolved attestation does not authorize production or statistical
    promotion. It only discharges representation-definition uncertainty for the
    exact attested bytes.
    """
    if "queue_hash" in review_queue and not verify_representation_review_queue_payload(dict(review_queue)):
        raise ValueError("invalid or tampered representation review queue")
    manifests_by_id:dict[str,list[StreamManifest]]={}
    for m in sorted(manifests,key=lambda x:(x.identity.stream_id,x.identity.source_path)):
        manifests_by_id.setdefault(m.identity.stream_id,[]).append(m)
    rows = [r for r in review_queue.get("candidates", []) if isinstance(r, Mapping)]
    p0_by_stream: dict[str, Mapping[str, Any]] = {}
    for row in sorted(
        (r for r in rows if str(r.get("priority")) == "P0"),
        key=lambda r: (_norm(r.get("stream_id")), _norm(r.get("source_path"))),
    ):
        sid=_norm(row.get("stream_id"))
        if not sid:
            continue
        p0_by_stream.setdefault(sid,row)
    p0 = list(p0_by_stream.values())

    payload = attestations if isinstance(attestations, Mapping) else {}
    input_schema = _norm(payload.get("schema")) if payload else ""
    input_rows = payload.get("attestations", []) if input_schema == INPUT_SCHEMA else []
    if not isinstance(input_rows, list):
        input_rows = []

    by_stream: dict[str, list[Mapping[str, Any]]] = {}
    for item in input_rows:
        if not isinstance(item, Mapping):
            continue
        sid = _norm(item.get("stream_id"))
        if sid:
            by_stream.setdefault(sid, []).append(item)

    statuses: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    resolved_ids: list[str] = []

    for q in sorted(p0, key=lambda r: (_norm(r.get("stream_id")), _norm(r.get("source_path")))):
        sid = _norm(q.get("stream_id"))
        matches = manifests_by_id.get(sid,[])
        raw_hashes={m.identity.raw_sha256 for m in matches}
        if len(raw_hashes)>1:
            status="BLOCKED_STREAM_ID_COLLISION"
            statuses.append({
                "stream_id":sid,
                "source_path":_norm(q.get("source_path")),
                "status":status,
                "identity_errors":["stream_id_maps_to_multiple_raw_hashes"],
                "missing_dimensions":[],
                "required_dimensions":[],
                "attestation_count":len(by_stream.get(sid,[])),
            })
            status_counts[status]+=1
            continue
        manifest = matches[0] if matches else None
        if manifest is None:
            status = "BLOCKED_MANIFEST_NOT_FOUND"
            row_out = {
                "stream_id": sid,
                "source_path": _norm(q.get("source_path")),
                "status": status,
                "identity_errors": ["stream_manifest_not_found"],
                "missing_dimensions": [],
                "required_dimensions": [],
                "attestation_count": len(by_stream.get(sid, [])),
            }
            statuses.append(row_out)
            status_counts[status] += 1
            continue

        source_paths={m.identity.source_path for m in matches}
        queue_path=_norm(q.get("source_path"))
        if queue_path in source_paths:
            manifest=next(m for m in matches if m.identity.source_path==queue_path)
        required = _required_dimensions(manifest)
        candidates = by_stream.get(sid, [])
        if not candidates:
            status = "WAITING_EXPORT_SPECIFIC_ATTESTATION"
            statuses.append({
                "stream_id": sid,
                "source_path": manifest.identity.source_path,
                "raw_sha256": manifest.identity.raw_sha256,
                "status": status,
                "identity_errors": [],
                "evidence_errors": [],
                "missing_dimensions": list(required),
                "required_dimensions": list(required),
                "attestation_count": 0,
            })
            status_counts[status] += 1
            continue

        # Multiple attestations are an audit trail, never a voting system.
        # Every fully valid exact-byte review must agree on all dimensions required
        # for causal replay; contradictory valid reviews keep the stream blocked.
        evaluated: list[tuple[int, Mapping[str, Any], list[str], list[str], list[str]]] = []
        valid: list[tuple[Mapping[str, Any], dict[str,str]]] = []
        for att in candidates:
            ident_ok, ident_errors = _attestation_identity_valid(att, manifest, source_paths)
            ev_ok, evidence_errors = _attestation_evidence_valid(att)
            dimensions = att.get("dimensions") if isinstance(att.get("dimensions"), Mapping) else {}
            missing = [name for name in required if not _known(dimensions.get(name))]
            timestamp_semantics=_norm(dimensions.get("timestamp_semantics")).upper()
            if timestamp_semantics not in {"BAR_OPEN","BAR_CLOSE","EVENT_COMPLETION"} and "timestamp_semantics" not in missing:
                missing.append("timestamp_semantics")
            penalty = len(ident_errors) * 100 + len(evidence_errors) * 10 + len(missing)
            evaluated.append((penalty, att, ident_errors, evidence_errors, missing))
            if ident_ok and ev_ok and not missing:
                normalized={
                    name:(
                        _norm(dimensions.get(name)).upper()
                        if name=="timestamp_semantics"
                        else _norm(dimensions.get(name)).casefold()
                    )
                    for name in required
                }
                valid.append((att,normalized))

        if valid:
            signatures={
                tuple((name,dims[name]) for name in required)
                for _,dims in valid
            }
            if len(signatures)>1:
                status="BLOCKED_ATTESTATION_CONFLICT"
                statuses.append({
                    "stream_id":sid,
                    "source_path":manifest.identity.source_path,
                    "raw_sha256":manifest.identity.raw_sha256,
                    "status":status,
                    "identity_errors":[],
                    "evidence_errors":["contradictory_valid_attestations"],
                    "missing_dimensions":[],
                    "required_dimensions":list(required),
                    "attestation_count":len(candidates),
                    "valid_attestation_count":len(valid),
                    "production_authorized":False,
                })
                status_counts[status]+=1
                continue

            valid.sort(key=lambda x:(
                _norm(x[0].get("reviewed_at")),
                _norm(x[0].get("reviewed_by")),
                repr(sorted(x[0].items())),
            ))
            att,normalized=valid[-1]
            dimensions=att.get("dimensions")
            status="RESOLVED_BY_EXACT_STREAM_ATTESTATION"
            resolved_ids.append(sid)
            statuses.append({
                "stream_id":sid,
                "source_path":manifest.identity.source_path,
                "raw_sha256":manifest.identity.raw_sha256,
                "status":status,
                "identity_errors":[],
                "evidence_errors":[],
                "missing_dimensions":[],
                "required_dimensions":list(required),
                "attestation_count":len(candidates),
                "valid_attestation_count":len(valid),
                "accepted_evidence_sources":sorted({
                    str(x).strip()
                    for valid_att,_ in valid
                    for x in (valid_att.get("evidence_sources") or [])
                    if isinstance(x,str) and _known(x)
                }),
                "accepted_dimensions":{
                    name:_norm(dimensions.get(name)) for name in required
                },
                "reviewed_by":_norm(att.get("reviewed_by")) or None,
                "reviewed_at":_norm(att.get("reviewed_at")) or None,
                "production_authorized":False,
            })
            status_counts[status]+=1
            continue

        evaluated.sort(key=lambda x: (x[0], repr(sorted(x[1].items()))))
        _, _, ident_errors, evidence_errors, missing = evaluated[0]
        if ident_errors:
            status = "REJECTED_ATTESTATION_IDENTITY_MISMATCH"
        elif evidence_errors:
            status = "BLOCKED_ATTESTATION_EVIDENCE_INCOMPLETE"
        else:
            status = "BLOCKED_ATTESTATION_DIMENSIONS_INCOMPLETE"
        statuses.append({
            "stream_id": sid,
            "source_path": manifest.identity.source_path,
            "raw_sha256": manifest.identity.raw_sha256,
            "status": status,
            "identity_errors": sorted(ident_errors),
            "evidence_errors": sorted(evidence_errors),
            "missing_dimensions": sorted(missing),
            "required_dimensions": list(required),
            "attestation_count": len(candidates),
            "valid_attestation_count": 0,
            "production_authorized": False,
        })
        status_counts[status] += 1

    body = {
        "schema": SCHEMA,
        "input_schema_expected": INPUT_SCHEMA,
        "input_schema_observed": input_schema or None,
        "p0_stream_count": len(p0),
        "resolved_by_attestation_count": len(resolved_ids),
        "remaining_p0_count": len(p0) - len(resolved_ids),
        "status_counts": dict(sorted(status_counts.items())),
        "resolved_stream_ids": sorted(resolved_ids),
        "streams": statuses,
        "resolution_rule": "exact stream identity + reviewed evidence source/digest + all causal representation dimensions",
        "general_documentation_alone_can_resolve_p0": False,
        "copy_or_sibling_attestation_inheritance_allowed": False,
        "statistical_promotion_performed": False,
        "production_authorized": False,
    }
    body["status_hash"] = hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_representation_attestation_status(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != SCHEMA:
        return False
    supplied=_norm(payload.get("status_hash")).lower()
    if not _SHA256_RE.fullmatch(supplied):
        return False
    body=dict(payload);body.pop("status_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied != expected or body.get("production_authorized") is not False:
        return False
    streams=body.get("streams")
    if not isinstance(streams,list):
        return False
    ids=[]
    resolved=[]
    counts=Counter()
    for row in streams:
        if not isinstance(row,Mapping):
            return False
        sid=_norm(row.get("stream_id"))
        status=_norm(row.get("status"))
        if not sid or not status:
            return False
        ids.append(sid);counts[status]+=1
        if status=="RESOLVED_BY_EXACT_STREAM_ATTESTATION":
            resolved.append(sid)
            if row.get("production_authorized") is not False:
                return False
            if row.get("identity_errors") or row.get("evidence_errors") or row.get("missing_dimensions"):
                return False
            if int(row.get("valid_attestation_count") or 0) < 1:
                return False
    if len(set(ids)) != len(ids):
        return False
    return (
        type(body.get("p0_stream_count")) is int
        and body["p0_stream_count"]==len(streams)
        and type(body.get("resolved_by_attestation_count")) is int
        and body["resolved_by_attestation_count"]==len(resolved)
        and type(body.get("remaining_p0_count")) is int
        and body["remaining_p0_count"]==len(streams)-len(resolved)
        and sorted(body.get("resolved_stream_ids") or [])==sorted(resolved)
        and body.get("status_counts")==dict(sorted(counts.items()))
        and body.get("statistical_promotion_performed") is False
    )
