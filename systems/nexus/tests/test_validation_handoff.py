import hashlib
import json
import pytest

from nexus.contracts import StreamIdentity, StreamManifest
from nexus.validation_handoff import build_daedalus_validation_handoff


def _seal(payload):
    body=dict(payload)
    body["resolution_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def _manifest(stream_hash: str = "a" * 64) -> StreamManifest:
    identity = StreamIdentity(
        source_id="zipcsv", venue="BATS", symbol="TEST", filename_claim="1",
        representation="csv_export", source_path="corpus.zip!TEST.csv", raw_sha256=stream_hash,
    )
    return StreamManifest(
        identity=identity, row_count=1000, columns=["time", "open", "high", "low", "close"],
        first_event_ns=100, last_event_ns=1000, observed_cadence_ns=60_000_000_000,
        cadence_confidence=1.0, repeated_timestamp_count=0, backward_timestamp_count=0,
        fractional_timestamp_count=0, metadata={"logical_sha256": "b" * 64, "uncompressed_size": 12345},
    )


def test_behavior_handoff_requires_unseen_confirmation():
    m = _manifest()
    candidate = {
        "candidate_id": "abc",
        "family": "return_reversal",
        "priority": "P1",
        "score": 120.0,
        "scope": [m.identity.stream_id],
        "rationale": "descriptive",
        "required_next_test": "chronological validation",
        "descriptive_only": True,
        "production_authorized": False,
    }
    out = build_daedalus_validation_handoff(
        [m], [candidate], admitted_ids={m.identity.stream_id}, corpus_manifest_hash="c" * 64,
        source_iteration=4, loop_code_version="1.3.0",
    )
    row = out["candidates"][0]
    assert row["route"]["route"] == "DAEDALUS_DEVELOPMENT_ONLY"
    assert row["route"]["protected_holdout_eligible_on_current_history"] is False
    assert row["route"]["confirmatory_requires_new_evidence"] is True
    assert row["clean_confirmation_rule"]["max_discovery_last_event_ns"] == 1000
    assert row["source_evidence"][0]["raw_sha256"] == "a" * 64
    assert row["source_evidence"][0]["raw_size_bytes"] == 12345
    assert out["protected_holdout_spent"] is False
    assert out["production_authorized"] is False


def test_semantics_and_representation_candidates_fail_closed():
    m = _manifest()
    base = {
        "priority": "P1", "score": 100.0, "scope": [m.identity.stream_id],
        "rationale": "x", "required_next_test": "y", "descriptive_only": True,
        "production_authorized": False,
    }
    candidates = [
        {**base, "candidate_id": "gap", "family": "sampling_gap_sensitivity"},
        {**base, "candidate_id": "rep", "family": "representation_family_disagreement"},
    ]
    out = build_daedalus_validation_handoff(
        [m], candidates, admitted_ids={m.identity.stream_id}, corpus_manifest_hash="c" * 64,
        source_iteration=4, loop_code_version="1.3.0",
    )
    routes = {x["candidate"]["candidate_id"]: x["route"] for x in out["candidates"]}
    assert routes["gap"]["route"] == "BLOCKED_PENDING_CALENDAR_SESSION_SEMANTICS"
    assert routes["rep"]["route"] == "BLOCKED_PENDING_REPRESENTATION_IDENTITY"
    assert all(not x["protected_holdout_eligible_on_current_history"] for x in routes.values())


def test_resolved_representation_lineage_routes_to_canonicalization_not_blocker():
    m = _manifest()
    candidate = {
        "candidate_id": "rep", "family": "representation_family_disagreement",
        "priority": "P1", "score": 100.0, "scope": [m.identity.stream_id],
        "rationale": "x", "required_next_test": "y", "descriptive_only": True,
        "production_authorized": False,
    }
    lineage = _seal({
        "schema": "nexus.representation-lineage-resolution.v1",
        "candidate_count": 1,
        "resolved_count": 1,
        "unresolved_count": 0,
        "resolutions": [{
            "candidate_id": "rep",
            "status": "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED",
            "canonical_stream_id": m.identity.stream_id,
            "canonical_raw_sha256": m.identity.raw_sha256,
            "unique_raw_stream_count": 1,
            "duplicate_alias_count": 0,
            "compatible_component_count": 1,
            "unresolved_conflict_count": 0,
            "independent_view_count": 0,
            "canonicalization_allowed": True,
            "fusion_as_independent_views_allowed": False,
            "reason": "verified copy lineage",
            "pairwise_relations": [],
        }],
        "statistical_fusion_performed": False,
        "production_authorized": False,
    })
    out = build_daedalus_validation_handoff(
        [m], [candidate], admitted_ids={m.identity.stream_id}, corpus_manifest_hash="c" * 64,
        source_iteration=4, loop_code_version="1.4.0", representation_lineage_resolution=lineage,
    )
    row = out["candidates"][0]
    assert row["route"]["route"] == "RESOLVED_REPRESENTATION_COPY_LINEAGE"
    assert row["route"]["canonical_stream_id"] == m.identity.stream_id
    assert row["route"]["fusion_as_independent_views_allowed"] is False
    assert row["representation_lineage_resolution"]["status"] == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED"


def test_resolved_session_gap_routes_to_open_session_diagnostic_without_data_loss_claim():
    m = _manifest()
    candidate = {
        "candidate_id": "gap", "family": "sampling_gap_sensitivity",
        "priority": "P1", "score": 100.0, "scope": [m.identity.stream_id],
        "rationale": "x", "required_next_test": "y", "descriptive_only": True,
        "production_authorized": False,
    }
    session = _seal({
        "schema": "nexus.session-gap-resolution.v1",
        "candidate_count": 1,
        "session_semantics_resolved_count": 1,
        "residual_diagnostic_count": 1,
        "still_session_blocked_count": 0,
        "resolutions": [{
            "candidate_id": "gap",
            "stream_id": m.identity.stream_id,
            "venue": m.identity.venue,
            "symbol": m.identity.symbol,
            "profile_id": "reviewed-test-profile",
            "profile_status": "EXACT_PROFILE_REVIEWED",
            "gap_count": 6,
            "session_explained_gap_count": 5,
            "residual_open_session_gap_count": 1,
            "unsupported_effective_period_gap_count": 0,
            "coarse_calendar_gap_count": 0,
            "session_semantics_resolved": True,
            "residual_data_quality_diagnostic_required": True,
            "reason": "reviewed",
            "evidence_authority": "test authority",
            "evidence_summary": "test reviewed profile",
            "gap_assessments": [],
            "coarse_resolution_method": None,
            "coarse_evidence_stream_id": None,
        }],
        "data_loss_asserted": False,
        "production_authorized": False,
    })
    out = build_daedalus_validation_handoff(
        [m], [candidate], admitted_ids={m.identity.stream_id}, corpus_manifest_hash="c" * 64,
        source_iteration=5, loop_code_version="1.5.0", session_gap_resolution=session,
    )
    row = out["candidates"][0]
    assert row["route"]["route"] == "SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC"
    assert row["route"]["data_loss_asserted"] is False
    assert row["route"]["validation_owner"] == "NEXUS_DATA_QUALITY"
    assert row["session_gap_resolution"]["session_explained_gap_count"] == 5
    assert row["route"]["confirmatory_validation_allowed_on_current_history"] is False


def test_resolved_session_closures_do_not_route_to_daedalus():
    m = _manifest()
    candidate = {
        "candidate_id": "gap", "family": "sampling_gap_sensitivity",
        "priority": "P1", "score": 100.0, "scope": [m.identity.stream_id],
        "rationale": "x", "required_next_test": "y", "descriptive_only": True,
        "production_authorized": False,
    }
    session = _seal({
        "schema": "nexus.session-gap-resolution.v1",
        "candidate_count": 1,
        "session_semantics_resolved_count": 1,
        "residual_diagnostic_count": 0,
        "still_session_blocked_count": 0,
        "resolutions": [{
            "candidate_id": "gap",
            "stream_id": m.identity.stream_id,
            "venue": m.identity.venue,
            "symbol": m.identity.symbol,
            "profile_id": "reviewed-test-profile",
            "profile_status": "EXACT_PROFILE_REVIEWED",
            "gap_count": 5,
            "session_explained_gap_count": 5,
            "residual_open_session_gap_count": 0,
            "unsupported_effective_period_gap_count": 0,
            "coarse_calendar_gap_count": 0,
            "session_semantics_resolved": True,
            "residual_data_quality_diagnostic_required": False,
            "reason": "reviewed",
            "evidence_authority": "test authority",
            "evidence_summary": "test reviewed profile",
            "gap_assessments": [],
            "coarse_resolution_method": None,
            "coarse_evidence_stream_id": None,
        }],
        "data_loss_asserted": False,
        "production_authorized": False,
    })
    out = build_daedalus_validation_handoff(
        [m], [candidate], admitted_ids={m.identity.stream_id}, corpus_manifest_hash="c" * 64,
        source_iteration=5, loop_code_version="1.5.0", session_gap_resolution=session,
    )
    row = out["candidates"][0]
    assert row["route"]["route"] == "RESOLVED_RECURRING_SESSION_CLOSURE"
    assert row["route"]["data_loss_asserted"] is False
    assert row["route"]["validation_owner"] == "NEXUS_SESSION_CANONICALIZATION"
    assert row["route"]["retrospective_diagnostics_allowed"] is False


def test_handoff_rejects_tampered_or_scope_mismatched_resolution():
    m=_manifest()
    candidate={
        "candidate_id":"rep","family":"representation_family_disagreement",
        "priority":"P1","score":1.0,"scope":[m.identity.stream_id],
        "rationale":"x","required_next_test":"y",
    }
    lineage=_seal({
        "schema":"nexus.representation-lineage-resolution.v1",
        "candidate_count":1,"resolved_count":1,"unresolved_count":0,
        "resolutions":[{
            "candidate_id":"rep",
            "status":"SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED",
            "canonical_stream_id":m.identity.stream_id,
            "canonical_raw_sha256":m.identity.raw_sha256,
            "unique_raw_stream_count":1,"duplicate_alias_count":0,
            "compatible_component_count":1,"unresolved_conflict_count":0,
            "independent_view_count":0,"canonicalization_allowed":True,
            "fusion_as_independent_views_allowed":False,
            "reason":"x","pairwise_relations":[],
        }],
        "statistical_fusion_performed":False,"production_authorized":False,
    })
    tampered=dict(lineage);tampered["resolved_count"]=0
    with pytest.raises(ValueError,match='tampered'):
        build_daedalus_validation_handoff(
            [m],[candidate],admitted_ids={m.identity.stream_id},
            corpus_manifest_hash='c'*64,source_iteration=1,loop_code_version='x',
            representation_lineage_resolution=tampered,
        )

    wrong=dict(lineage)
    row=dict(wrong["resolutions"][0]);row["canonical_stream_id"]="other"
    wrong["resolutions"]=[row];wrong.pop("resolution_hash")
    wrong=_seal(wrong)
    with pytest.raises(ValueError,match='scope'):
        build_daedalus_validation_handoff(
            [m],[candidate],admitted_ids={m.identity.stream_id},
            corpus_manifest_hash='c'*64,source_iteration=1,loop_code_version='x',
            representation_lineage_resolution=wrong,
        )
