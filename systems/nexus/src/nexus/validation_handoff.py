from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from typing import Any, Iterable, Mapping

from .contracts import StreamManifest
from .lineage_resolution import verify_representation_lineage_resolution
from .session_semantics import verify_session_gap_resolution
from .residual_gap_triage import verify_residual_gap_triage


HANDOFF_SCHEMA = "nexus.daedalus-validation-handoff.v1"

BEHAVIOR_FAMILIES = frozenset({
    "return_persistence",
    "return_reversal",
    "regime_volatility_shift",
})

SEMANTICS_BLOCKED_FAMILIES = frozenset({"sampling_gap_sensitivity"})
REPRESENTATION_BLOCKED_FAMILIES = frozenset({"representation_family_disagreement"})
OPERATIONAL_FAMILIES = frozenset({
    "corpus_recovery",
    "owner_coverage_gap",
    "representation_review",
    "integrity_rejections",
})


def _candidate_dict(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, Mapping):
        return dict(candidate)
    if hasattr(candidate, "to_dict"):
        return dict(candidate.to_dict())
    raise TypeError(f"unsupported candidate type: {type(candidate)!r}")


def _manifest_record(manifest: StreamManifest, admitted_ids: set[str]) -> dict[str, Any]:
    return {
        "stream_id": manifest.identity.stream_id,
        "source_path": manifest.identity.source_path,
        "source_id": manifest.identity.source_id,
        "venue": manifest.identity.venue,
        "symbol": manifest.identity.symbol,
        "filename_claim": manifest.identity.filename_claim,
        "representation": manifest.identity.representation,
        "raw_sha256": manifest.identity.raw_sha256,
        "raw_size_bytes": manifest.metadata.get("uncompressed_size"),
        "logical_sha256": manifest.metadata.get("logical_sha256"),
        "row_count": int(manifest.row_count),
        "first_event_ns": manifest.first_event_ns,
        "last_event_ns": manifest.last_event_ns,
        "observed_cadence_ns": manifest.observed_cadence_ns,
        "quality_flags": list(manifest.quality_flags),
        "admitted_default_integrity": manifest.identity.stream_id in admitted_ids,
    }


def _route_for_family(
    family: str,
    *,
    representation_resolution: Mapping[str, Any] | None = None,
    session_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if family in BEHAVIOR_FAMILIES:
        return {
            "route": "DAEDALUS_DEVELOPMENT_ONLY",
            "validation_owner": "DAEDALUS",
            "retrospective_diagnostics_allowed": True,
            "protected_holdout_eligible_on_current_history": False,
            "confirmatory_validation_allowed_on_current_history": False,
            "confirmatory_requires_new_evidence": True,
            "reason": (
                "NEXUS selected this hypothesis after scanning the full accessible stream history; "
                "therefore every row currently present in the same source is discovery-contaminated."
            ),
        }
    if family in SEMANTICS_BLOCKED_FAMILIES:
        if session_resolution and bool(session_resolution.get("session_semantics_resolved")):
            residual = bool(session_resolution.get("residual_data_quality_diagnostic_required"))
            if residual:
                return {
                    "route": "SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC",
                    "validation_owner": "NEXUS_DATA_QUALITY",
                    "retrospective_diagnostics_allowed": True,
                    "protected_holdout_eligible_on_current_history": False,
                    "confirmatory_validation_allowed_on_current_history": False,
                    "confirmatory_requires_new_evidence": False,
                    "reason": (
                        "A reviewed recurring session profile explains part of the gap structure, while one or more "
                        "residual gaps intersect a known open session. These are data-quality/no-trade diagnostics; "
                        "they are not automatically labeled missing data or predictive hypotheses."
                    ),
                    "data_loss_asserted": False,
                }
            return {
                "route": "RESOLVED_RECURRING_SESSION_CLOSURE",
                "validation_owner": "NEXUS_SESSION_CANONICALIZATION",
                "retrospective_diagnostics_allowed": False,
                "protected_holdout_eligible_on_current_history": False,
                "confirmatory_validation_allowed_on_current_history": False,
                "confirmatory_requires_new_evidence": False,
                "reason": (
                    "Observed sampling gaps are accounted for by the reviewed recurring session profile. "
                    "They must not be counted as evidence of data loss or as an independent statistical signal."
                ),
                "data_loss_asserted": False,
            }
        return {
            "route": "BLOCKED_PENDING_CALENDAR_SESSION_SEMANTICS",
            "validation_owner": "NEXUS_REVIEW_THEN_DAEDALUS",
            "retrospective_diagnostics_allowed": False,
            "protected_holdout_eligible_on_current_history": False,
            "confirmatory_validation_allowed_on_current_history": False,
            "confirmatory_requires_new_evidence": False,
            "reason": (
                "Fixed-cadence gap statistics cannot be interpreted as data loss until exchange/session/calendar "
                "semantics are reviewed for the representation."
            ),
        }
    if family in REPRESENTATION_BLOCKED_FAMILIES:
        if representation_resolution and representation_resolution.get("status") == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED":
            return {
                "route": "RESOLVED_REPRESENTATION_COPY_LINEAGE",
                "validation_owner": "NEXUS_CANONICALIZATION",
                "retrospective_diagnostics_allowed": False,
                "protected_holdout_eligible_on_current_history": False,
                "confirmatory_validation_allowed_on_current_history": False,
                "confirmatory_requires_new_evidence": False,
                "reason": (
                    "Overlapping timestamp/OHLC evidence identifies these exports as one copy/snapshot lineage. "
                    "Canonicalization is allowed, but copies may not be treated as independent statistical views."
                ),
                "canonical_stream_id": representation_resolution.get("canonical_stream_id"),
                "fusion_as_independent_views_allowed": False,
            }
        return {
            "route": "BLOCKED_PENDING_REPRESENTATION_IDENTITY",
            "validation_owner": "NEXUS_REVIEW_THEN_DAEDALUS",
            "retrospective_diagnostics_allowed": False,
            "protected_holdout_eligible_on_current_history": False,
            "confirmatory_validation_allowed_on_current_history": False,
            "confirmatory_requires_new_evidence": False,
            "reason": (
                "Same-symbol/filename-claim representations must be resolved by identity/lineage evidence before "
                "statistical fusion or comparative validation."
            ),
        }
    return {
        "route": "BLOCKING_DEPENDENCY",
        "validation_owner": "NEXUS_OR_CORPUS_RECOVERY",
        "retrospective_diagnostics_allowed": False,
        "protected_holdout_eligible_on_current_history": False,
        "confirmatory_validation_allowed_on_current_history": False,
        "confirmatory_requires_new_evidence": False,
        "reason": "This candidate represents an upstream evidence/integrity dependency rather than a statistical hypothesis.",
    }


def build_daedalus_validation_handoff(
    manifests: Iterable[StreamManifest],
    candidates: Iterable[Any],
    *,
    admitted_ids: set[str],
    corpus_manifest_hash: str,
    source_iteration: int,
    loop_code_version: str,
    representation_lineage_resolution: Mapping[str, Any] | None = None,
    session_gap_resolution: Mapping[str, Any] | None = None,
    residual_gap_triage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed NEXUS -> DAEDALUS validation handoff.

    NEXUS candidate discovery currently sweeps every accessible row before candidate
    selection. This function makes that contamination explicit: no protected tail from
    the same historical files may subsequently be presented as pristine confirmatory
    evidence. DAEDALUS may run development/retrospective diagnostics, but clean
    confirmation requires evidence not used by NEXUS discovery (normally rows strictly
    after the recorded discovery cutoff or an independently sourced non-overlapping
    period whose identity/semantics are reviewed).
    """
    if type(source_iteration) is not int or source_iteration < 0:
        raise ValueError("source_iteration must be a non-negative integer")
    if not isinstance(loop_code_version,str) or not loop_code_version.strip():
        raise ValueError("loop_code_version is required")
    if not isinstance(corpus_manifest_hash,str) or len(corpus_manifest_hash)!=64:
        raise ValueError("corpus_manifest_hash must be a SHA-256 hex digest")
    try:
        int(corpus_manifest_hash,16)
    except ValueError as exc:
        raise ValueError("corpus_manifest_hash must be a SHA-256 hex digest") from exc

    manifest_rows = list(manifests)
    all_candidate_rows = [_candidate_dict(c) for c in candidates]
    candidate_ids=[str(c.get("candidate_id") or "") for c in all_candidate_rows]
    if any(not x for x in candidate_ids) or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate_id values must be non-empty and unique")
    operational_rows=[
        c for c in all_candidate_rows
        if str(c.get("family") or "") in OPERATIONAL_FAMILIES
    ]
    candidate_rows=[
        c for c in all_candidate_rows
        if str(c.get("family") or "") not in OPERATIONAL_FAMILIES
    ]
    if representation_lineage_resolution is not None and not verify_representation_lineage_resolution(representation_lineage_resolution):
        raise ValueError("invalid or tampered representation-lineage resolution artifact")
    if session_gap_resolution is not None and not verify_session_gap_resolution(session_gap_resolution):
        raise ValueError("invalid or tampered session-gap resolution artifact")
    if residual_gap_triage is not None and not verify_residual_gap_triage(residual_gap_triage):
        raise ValueError("invalid or tampered residual-gap triage artifact")
    family_counts = Counter(str(c.get("family", "unknown")) for c in candidate_rows)
    representation_resolution_by_id: dict[str, Mapping[str, Any]] = {}
    if representation_lineage_resolution:
        for row in representation_lineage_resolution.get("resolutions", []):
            if isinstance(row, Mapping) and row.get("candidate_id"):
                representation_resolution_by_id[str(row["candidate_id"])] = row
    session_resolution_by_id: dict[str, Mapping[str, Any]] = {}
    if session_gap_resolution:
        for row in session_gap_resolution.get("resolutions", []):
            if isinstance(row, Mapping) and row.get("candidate_id"):
                session_resolution_by_id[str(row["candidate_id"])] = row

    residual_triage_by_id: dict[str, Mapping[str, Any]] = {}
    if residual_gap_triage:
        for row in residual_gap_triage.get("resolutions", []):
            if isinstance(row, Mapping) and row.get("candidate_id"):
                residual_triage_by_id[str(row["candidate_id"])] = row

    by_stream: dict[str, list[StreamManifest]] = defaultdict(list)
    for manifest in manifest_rows:
        by_stream[manifest.identity.stream_id].append(manifest)
    for sid,rows in by_stream.items():
        hashes={m.identity.raw_sha256 for m in rows}
        if len(hashes)>1:
            raise ValueError(f"stream_id collision across distinct raw contents: {sid}")

    handoff_candidates: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    for candidate in candidate_rows:
        family = str(candidate.get("family", "unknown"))
        candidate_id = str(candidate.get("candidate_id") or "")
        representation_resolution = representation_resolution_by_id.get(candidate_id)
        session_resolution = session_resolution_by_id.get(candidate_id)
        residual_triage = residual_triage_by_id.get(candidate_id)
        route = _route_for_family(
            family,
            representation_resolution=representation_resolution,
            session_resolution=session_resolution,
        )
        route_counts[route["route"]] += 1
        scope = [str(x) for x in candidate.get("scope", [])]
        if not scope or any(not x for x in scope):
            raise ValueError(f"candidate {candidate_id!r} must have a non-empty stream scope")

        if representation_resolution and representation_resolution.get("status") == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED":
            canonical_sid=str(representation_resolution.get("canonical_stream_id") or "")
            canonical_sha=str(representation_resolution.get("canonical_raw_sha256") or "")
            if canonical_sid not in scope:
                raise ValueError(
                    f"representation resolution for {candidate_id!r} is not bound to candidate scope"
                )
            canonical_matches=[
                m for m in by_stream.get(canonical_sid,[])
                if m.identity.raw_sha256 == canonical_sha
            ]
            if not canonical_matches:
                raise ValueError(
                    f"representation resolution for {candidate_id!r} does not match canonical manifest bytes"
                )
            for rel in representation_resolution.get("pairwise_relations",[]):
                if not isinstance(rel,Mapping):
                    raise ValueError("invalid pairwise lineage relation")
                left=str(rel.get("left_stream_id") or "")
                right=str(rel.get("right_stream_id") or "")
                if left not in scope or right not in scope:
                    raise ValueError(
                        f"pairwise lineage relation for {candidate_id!r} escapes candidate scope"
                    )

        if session_resolution and session_resolution.get("session_semantics_resolved") is True:
            sid=str(session_resolution.get("stream_id") or "")
            if sid not in scope:
                raise ValueError(
                    f"session resolution for {candidate_id!r} is not bound to candidate scope"
                )
            matches=by_stream.get(sid,[])
            if not matches:
                raise ValueError(
                    f"session resolution for {candidate_id!r} has no matching manifest"
                )
            venue=session_resolution.get("venue")
            symbol=session_resolution.get("symbol")
            if not any(m.identity.venue==venue and m.identity.symbol==symbol for m in matches):
                raise ValueError(
                    f"session resolution for {candidate_id!r} does not match manifest venue/symbol"
                )

        if residual_triage:
            sid=str(residual_triage.get("stream_id") or "")
            if sid not in scope:
                raise ValueError(
                    f"residual-gap triage for {candidate_id!r} is not bound to candidate scope"
                )
            matches=by_stream.get(sid,[])
            if not matches:
                raise ValueError(
                    f"residual-gap triage for {candidate_id!r} has no matching manifest"
                )
            if not any(
                m.identity.venue==residual_triage.get("venue")
                and m.identity.symbol==residual_triage.get("symbol")
                for m in matches
            ):
                raise ValueError(
                    f"residual-gap triage for {candidate_id!r} does not match manifest venue/symbol"
                )

        source_evidence: list[dict[str, Any]] = []
        per_stream_cutoffs: dict[str, int | None] = {}
        for stream_id in sorted(set(scope)):
            matches = sorted(by_stream.get(stream_id, []), key=lambda m: m.identity.source_path)
            if not matches:
                raise ValueError(
                    f"candidate {candidate_id!r} scope references unknown stream_id {stream_id!r}"
                )
            source_evidence.extend(_manifest_record(m, admitted_ids) for m in matches)
            seen = [m.last_event_ns for m in matches if m.last_event_ns is not None]
            per_stream_cutoffs[stream_id] = max(seen) if seen else None

        max_seen = max((x for x in per_stream_cutoffs.values() if x is not None), default=None)
        clean_rule: dict[str, Any] | None = None
        if family in BEHAVIOR_FAMILIES:
            clean_rule = {
                "rule": "UNSEEN_EVIDENCE_ONLY",
                "current_source_history_is_pristine": False,
                "per_stream_discovery_last_event_ns": per_stream_cutoffs,
                "max_discovery_last_event_ns": max_seen,
                "acceptable_confirmation_examples": [
                    "new rows whose event_ns is strictly greater than that stream's discovery_last_event_ns",
                    "an independently sourced, non-overlapping historical period with reviewed identity and timestamp semantics",
                ],
                "forbidden_as_clean_holdout": [
                    "any row already present in the source files scanned by this NEXUS iteration",
                    "a tail carved out after candidate selection from those already-scanned files",
                    "an alternate representation of the same overlapping market period unless independence is established",
                ],
            }

        handoff_candidates.append({
            "candidate": candidate,
            "route": route,
            "source_evidence": source_evidence,
            "selection_context": {
                "candidate_family_size_in_iteration": int(family_counts[family]),
                "candidate_was_selected_after_full_accessible_history_scan": True,
                "independent_confirmation_already_available": False,
                "multiple_testing_control_required": family in BEHAVIOR_FAMILIES,
            },
            "clean_confirmation_rule": clean_rule,
            "representation_lineage_resolution": dict(representation_resolution) if representation_resolution else None,
            "session_gap_resolution": dict(session_resolution) if session_resolution else None,
            "residual_gap_triage": dict(residual_triage) if residual_triage else None,
            "production_authorized": False,
        })

    body = {
        "schema": HANDOFF_SCHEMA,
        "source_iteration": int(source_iteration),
        "loop_code_version": str(loop_code_version),
        "corpus_manifest_hash": str(corpus_manifest_hash),
        "discovery_evidence_policy": {
            "full_accessible_history_scanned_before_candidate_selection": True,
            "current_history_selection_contaminated": True,
            "pristine_protected_holdout_available_inside_same_scanned_files": False,
            "policy": (
                "Development-only retrospective analysis may use current history, but confirmatory/protected-holdout claims "
                "must use genuinely unseen evidence."
            ),
        },
        "candidate_family_counts": dict(sorted(family_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "candidates": handoff_candidates,
        "upstream_operational_dependency_counts": dict(sorted(
            Counter(str(x.get("family") or "unknown") for x in operational_rows).items()
        )),
        "upstream_operational_dependencies": operational_rows,
        "statistical_promotion_performed": False,
        "protected_holdout_spent": False,
        "production_authorized": False,
    }
    body["handoff_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_daedalus_validation_handoff(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != HANDOFF_SCHEMA:
        return False
    supplied=payload.get("handoff_hash")
    if not isinstance(supplied,str) or len(supplied)!=64:
        return False
    try:
        int(supplied,16)
    except ValueError:
        return False
    body=dict(payload);body.pop("handoff_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied!=expected:
        return False
    if (
        type(body.get("source_iteration")) is not int
        or body["source_iteration"] < 0
        or not body.get("loop_code_version")
        or not isinstance(body.get("corpus_manifest_hash"),str)
        or len(body["corpus_manifest_hash"]) != 64
        or body.get("statistical_promotion_performed") is not False
        or body.get("protected_holdout_spent") is not False
        or body.get("production_authorized") is not False
    ):
        return False
    try:
        int(body["corpus_manifest_hash"],16)
    except ValueError:
        return False

    policy=body.get("discovery_evidence_policy")
    if not isinstance(policy,Mapping) or (
        policy.get("full_accessible_history_scanned_before_candidate_selection") is not True
        or policy.get("current_history_selection_contaminated") is not True
        or policy.get("pristine_protected_holdout_available_inside_same_scanned_files") is not False
    ):
        return False

    rows=body.get("candidates")
    operational=body.get("upstream_operational_dependencies")
    operational_counts=body.get("upstream_operational_dependency_counts")
    if not isinstance(rows,list) or not isinstance(operational,list) or not isinstance(operational_counts,Mapping):
        return False
    operational_ids=[]
    recomputed_operational=Counter()
    for candidate in operational:
        if not isinstance(candidate,Mapping):
            return False
        cid=str(candidate.get("candidate_id") or "")
        family=str(candidate.get("family") or "")
        scope=candidate.get("scope")
        if (
            not cid or family not in OPERATIONAL_FAMILIES
            or not isinstance(scope,list) or not scope
            or any(not str(x) for x in scope)
            or candidate.get("production_authorized") is not False
        ):
            return False
        operational_ids.append(cid)
        recomputed_operational[family]+=1
    if len(set(operational_ids)) != len(operational_ids):
        return False
    if dict(sorted(recomputed_operational.items())) != dict(operational_counts):
        return False

    ids=[];families=Counter();routes=Counter()
    for row in rows:
        if not isinstance(row,Mapping) or row.get("production_authorized") is not False:
            return False
        candidate=row.get("candidate")
        route=row.get("route")
        if not isinstance(candidate,Mapping) or not isinstance(route,Mapping):
            return False
        cid=str(candidate.get("candidate_id") or "")
        family=str(candidate.get("family") or "")
        route_name=str(route.get("route") or "")
        scope=candidate.get("scope")
        if not cid or not family or not route_name or not isinstance(scope,list) or not scope:
            return False
        if any(not str(x) for x in scope):
            return False
        ids.append(cid);families[family]+=1;routes[route_name]+=1

        expected_route=_route_for_family(
            family,
            representation_resolution=row.get("representation_lineage_resolution")
            if isinstance(row.get("representation_lineage_resolution"),Mapping) else None,
            session_resolution=row.get("session_gap_resolution")
            if isinstance(row.get("session_gap_resolution"),Mapping) else None,
        )
        if dict(route) != expected_route:
            return False
        if route.get("protected_holdout_eligible_on_current_history") is not False:
            return False
        if route.get("confirmatory_validation_allowed_on_current_history") is not False:
            return False

        evidence=row.get("source_evidence")
        if not isinstance(evidence,list) or not evidence:
            return False
        evidence_scope=set()
        per_stream_last={}
        for ev in evidence:
            if not isinstance(ev,Mapping):
                return False
            sid=str(ev.get("stream_id") or "")
            if sid not in scope:
                return False
            evidence_scope.add(sid)
            raw_sha=str(ev.get("raw_sha256") or "")
            if len(raw_sha)!=64:
                return False
            try:
                int(raw_sha,16)
            except ValueError:
                return False
            if type(ev.get("row_count")) is not int or ev["row_count"] < 0:
                return False
            if type(ev.get("admitted_default_integrity")) is not bool:
                return False
            first=ev.get("first_event_ns");last=ev.get("last_event_ns")
            if first is not None and (type(first) is not int or first < 0):
                return False
            if last is not None and (type(last) is not int or last < 0):
                return False
            if first is not None and last is not None and last < first:
                return False
            if last is not None:
                per_stream_last[sid]=max(per_stream_last.get(sid,last),last)
        if evidence_scope != set(scope):
            return False

        selection=row.get("selection_context")
        if not isinstance(selection,Mapping):
            return False
        if (
            selection.get("candidate_was_selected_after_full_accessible_history_scan") is not True
            or selection.get("independent_confirmation_already_available") is not False
            or type(selection.get("candidate_family_size_in_iteration")) is not int
            or selection["candidate_family_size_in_iteration"] < 1
        ):
            return False

        if family in BEHAVIOR_FAMILIES:
            rule=row.get("clean_confirmation_rule")
            if not isinstance(rule,Mapping) or rule.get("current_source_history_is_pristine") is not False:
                return False
            if rule.get("rule") != "UNSEEN_EVIDENCE_ONLY":
                return False
            cutoffs=rule.get("per_stream_discovery_last_event_ns")
            if not isinstance(cutoffs,Mapping) or set(cutoffs) != set(scope):
                return False
            if dict(cutoffs) != {sid:per_stream_last.get(sid) for sid in scope}:
                return False
            expected_max=max((x for x in per_stream_last.values()),default=None)
            if rule.get("max_discovery_last_event_ns") != expected_max:
                return False
        elif row.get("clean_confirmation_rule") is not None:
            return False
    if len(set(ids))!=len(ids):
        return False
    if set(ids) & set(operational_ids):
        return False
    return (
        body.get("candidate_family_counts")==dict(sorted(families.items()))
        and body.get("route_counts")==dict(sorted(routes.items()))
    )
