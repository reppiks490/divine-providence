from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Mapping

from .contracts import StreamManifest


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


def _attestation_identity_valid(row: Mapping[str, Any], manifest: StreamManifest) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if _norm(row.get("stream_id")) != manifest.identity.stream_id:
        errors.append("stream_id_mismatch")
    raw_sha = _norm(row.get("raw_sha256")).lower()
    if not _SHA256_RE.fullmatch(raw_sha):
        errors.append("raw_sha256_missing_or_invalid")
    elif raw_sha != manifest.identity.raw_sha256.lower():
        errors.append("raw_sha256_mismatch")
    source_path = _norm(row.get("source_path"))
    if source_path and source_path != manifest.identity.source_path:
        errors.append("source_path_mismatch")
    return not errors, errors


def _attestation_evidence_valid(row: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if row.get("reviewed") is not True:
        errors.append("reviewed_true_required")
    source_refs = row.get("evidence_sources") or []
    if not isinstance(source_refs, list) or not any(_known(x) for x in source_refs):
        errors.append("evidence_source_required")
    evidence_hash = _norm(row.get("evidence_sha256")).lower()
    if evidence_hash and not _SHA256_RE.fullmatch(evidence_hash):
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
    manifests_by_id = {m.identity.stream_id: m for m in manifests}
    rows = [r for r in review_queue.get("candidates", []) if isinstance(r, Mapping)]
    p0 = [r for r in rows if str(r.get("priority")) == "P0"]

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
        manifest = manifests_by_id.get(sid)
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

        # Multiple attestations for the same exact stream are allowed as an
        # audit trail, but they may not "vote" around a bad identity. The first
        # fully valid attestation resolves the stream; otherwise expose all
        # reasons from the best (fewest-errors) candidate deterministically.
        evaluated: list[tuple[int, Mapping[str, Any], list[str], list[str], list[str]]] = []
        for att in candidates:
            ident_ok, ident_errors = _attestation_identity_valid(att, manifest)
            ev_ok, evidence_errors = _attestation_evidence_valid(att)
            dimensions = att.get("dimensions") if isinstance(att.get("dimensions"), Mapping) else {}
            missing = [name for name in required if not _known(dimensions.get(name))]
            penalty = len(ident_errors) * 100 + len(evidence_errors) * 10 + len(missing)
            evaluated.append((penalty, att, ident_errors, evidence_errors, missing))
            if ident_ok and ev_ok and not missing:
                status = "RESOLVED_BY_EXACT_STREAM_ATTESTATION"
                resolved_ids.append(sid)
                statuses.append({
                    "stream_id": sid,
                    "source_path": manifest.identity.source_path,
                    "raw_sha256": manifest.identity.raw_sha256,
                    "status": status,
                    "identity_errors": [],
                    "evidence_errors": [],
                    "missing_dimensions": [],
                    "required_dimensions": list(required),
                    "attestation_count": len(candidates),
                    "accepted_evidence_sources": sorted(str(x) for x in (att.get("evidence_sources") or []) if _known(x)),
                    "reviewed_by": _norm(att.get("reviewed_by")) or None,
                    "reviewed_at": _norm(att.get("reviewed_at")) or None,
                    "production_authorized": False,
                })
                status_counts[status] += 1
                break
        else:
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
                "production_authorized": False,
            })
            status_counts[status] += 1

    return {
        "schema": SCHEMA,
        "input_schema_expected": INPUT_SCHEMA,
        "input_schema_observed": input_schema or None,
        "p0_stream_count": len(p0),
        "resolved_by_attestation_count": len(resolved_ids),
        "remaining_p0_count": len(p0) - len(resolved_ids),
        "status_counts": dict(sorted(status_counts.items())),
        "resolved_stream_ids": sorted(resolved_ids),
        "streams": statuses,
        "resolution_rule": "exact stream identity + reviewed evidence source + all causal representation dimensions",
        "general_documentation_alone_can_resolve_p0": False,
        "copy_or_sibling_attestation_inheritance_allowed": False,
        "statistical_promotion_performed": False,
        "production_authorized": False,
    }
