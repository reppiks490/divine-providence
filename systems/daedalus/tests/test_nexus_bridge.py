import json
from pathlib import Path

import pytest

from daedalus.bridge import load_nexus_validation_handoff, nexus_development_tasks, summarize_nexus_handoff


def _payload():
    return {
        "schema": "nexus.daedalus-validation-handoff.v1",
        "source_iteration": 5,
        "loop_code_version": "1.3.0",
        "corpus_manifest_hash": "c" * 64,
        "discovery_evidence_policy": {
            "full_accessible_history_scanned_before_candidate_selection": True,
            "current_history_selection_contaminated": True,
            "pristine_protected_holdout_available_inside_same_scanned_files": False,
            "policy": "development only",
        },
        "candidate_family_counts": {"return_reversal": 1},
        "route_counts": {"DAEDALUS_DEVELOPMENT_ONLY": 1},
        "candidates": [
            {
                "candidate": {
                    "candidate_id": "abc",
                    "family": "return_reversal",
                    "priority": "P1",
                    "score": 120.0,
                    "scope": ["zipcsv:TEST:aaaaaaaaaaaa"],
                    "descriptive_only": True,
                    "production_authorized": False,
                },
                "route": {
                    "route": "DAEDALUS_DEVELOPMENT_ONLY",
                    "validation_owner": "DAEDALUS",
                    "retrospective_diagnostics_allowed": True,
                    "protected_holdout_eligible_on_current_history": False,
                    "confirmatory_validation_allowed_on_current_history": False,
                    "confirmatory_requires_new_evidence": True,
                    "reason": "full history scanned",
                },
                "source_evidence": [{"stream_id": "zipcsv:TEST:aaaaaaaaaaaa", "last_event_ns": 1000}],
                "selection_context": {"candidate_family_size_in_iteration": 1},
                "clean_confirmation_rule": {
                    "rule": "UNSEEN_EVIDENCE_ONLY",
                    "current_source_history_is_pristine": False,
                    "max_discovery_last_event_ns": 1000,
                },
                "production_authorized": False,
            }
        ],
        "statistical_promotion_performed": False,
        "protected_holdout_spent": False,
        "production_authorized": False,
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "handoff.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_nexus_handoff_import_is_development_only(tmp_path):
    p = _write(tmp_path, _payload())
    loaded = load_nexus_validation_handoff(p)
    assert loaded["production_authorized"] is False
    tasks = nexus_development_tasks(p)
    assert len(tasks) == 1
    assert tasks[0].candidate_id == "abc"
    assert tasks[0].allow_protected_holdout is False
    assert tasks[0].confirmatory_evidence_required is True
    assert tasks[0].production_authorized is False
    summary = summarize_nexus_handoff(p)
    assert summary["development_task_count"] == 1
    assert summary["protected_holdout_eligible_task_count"] == 0
    assert summary["production_authorized"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.__setitem__("production_authorized", True),
        lambda p: p["discovery_evidence_policy"].__setitem__("current_history_selection_contaminated", False),
        lambda p: p["candidates"][0]["route"].__setitem__("protected_holdout_eligible_on_current_history", True),
        lambda p: p["candidates"][0]["route"].__setitem__("confirmatory_validation_allowed_on_current_history", True),
        lambda p: p["candidates"][0]["clean_confirmation_rule"].__setitem__("current_source_history_is_pristine", True),
    ],
)
def test_nexus_handoff_tampering_fails_closed(tmp_path, mutate):
    payload = _payload()
    mutate(payload)
    with pytest.raises(ValueError):
        load_nexus_validation_handoff(_write(tmp_path, payload))


def test_nexus_handoff_route_summary_mismatch_fails_closed(tmp_path):
    payload = _payload()
    payload["route_counts"] = {"DAEDALUS_DEVELOPMENT_ONLY": 2}
    with pytest.raises(ValueError, match="route_counts"):
        load_nexus_validation_handoff(_write(tmp_path, payload))


def test_resolved_route_safety_flags_fail_closed(tmp_path):
    payload = _payload()
    row = payload["candidates"][0]
    row["route"] = {
        "route": "SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC",
        "validation_owner": "NEXUS_DATA_QUALITY",
        "retrospective_diagnostics_allowed": True,
        "protected_holdout_eligible_on_current_history": False,
        "confirmatory_validation_allowed_on_current_history": False,
        "confirmatory_requires_new_evidence": False,
        "data_loss_asserted": True,
    }
    row["clean_confirmation_rule"] = None
    payload["route_counts"] = {"SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC": 1}
    with pytest.raises(ValueError, match="data-loss"):
        load_nexus_validation_handoff(_write(tmp_path, payload))
