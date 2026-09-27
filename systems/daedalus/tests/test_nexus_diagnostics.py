import csv
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

from daedalus.nexus_diagnostics import diagnose_nexus_handoff


def _write_source(root: Path, *, alternating: bool = True) -> tuple[str, str, int]:
    archive = root / "corpus.zip"
    rows = [["time", "open", "high", "low", "close"]]
    close = 100.0
    for i in range(600):
        if alternating:
            r = 0.002 if i % 2 == 0 else -0.002
        else:
            r = 0.001 + (i % 7) * 0.00001
        new_close = close * math.exp(r)
        rows.append([1700000000 + i * 60, close, max(close, new_close), min(close, new_close), new_close])
        close = new_close
    text = "\n".join(",".join(map(str, row)) for row in rows) + "\n"
    raw = text.encode()
    member = "sample/BATS_TEST, 1.csv"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member, raw)
    return f"corpus.zip!{member}", hashlib.sha256(raw).hexdigest(), 1700000000 + 599 * 60


def _handoff(path: Path, source_path: str, raw_sha: str, last_event: int) -> Path:
    stream_id = f"zipcsv:TEST:{raw_sha[:12]}"
    payload = {
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
        "candidates": [{
            "candidate": {
                "candidate_id": "abc", "family": "return_reversal", "priority": "P1", "score": 150.0,
                "scope": [stream_id], "descriptive_only": True, "production_authorized": False,
            },
            "route": {
                "route": "DAEDALUS_DEVELOPMENT_ONLY", "validation_owner": "DAEDALUS",
                "retrospective_diagnostics_allowed": True,
                "protected_holdout_eligible_on_current_history": False,
                "confirmatory_validation_allowed_on_current_history": False,
                "confirmatory_requires_new_evidence": True,
                "reason": "full history scanned",
            },
            "source_evidence": [{
                "stream_id": stream_id, "source_path": source_path, "raw_sha256": raw_sha,
                "last_event_ns": last_event, "admitted_default_integrity": True,
            }],
            "selection_context": {"candidate_family_size_in_iteration": 1},
            "clean_confirmation_rule": {
                "rule": "UNSEEN_EVIDENCE_ONLY", "current_source_history_is_pristine": False,
                "max_discovery_last_event_ns": last_event,
            },
            "production_authorized": False,
        }],
        "statistical_promotion_performed": False,
        "protected_holdout_spent": False,
        "production_authorized": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_retrospective_reversal_diagnostic_preserves_holdout_firewall(tmp_path):
    source_path, sha, last = _write_source(tmp_path, alternating=True)
    handoff = _handoff(tmp_path / "handoff.json", source_path, sha, last)
    out = diagnose_nexus_handoff(handoff, tmp_path, requested_blocks=5, min_rows_per_block=50)
    assert out["diagnosed_candidate_count"] == 1
    row = out["candidates"][0]
    assert row["status"] == "RETROSPECTIVE_DIRECTION_STABLE"
    assert row["diagnostic"]["expected_sign_support_fraction"] == 1.0
    assert row["protected_holdout_touched"] is False
    assert row["independent_confirmation"] is False
    assert out["interpretation"]["can_confirm_hypotheses"] is False
    assert out["production_authorized"] is False


def test_diagnostic_rejects_tampered_source_bytes(tmp_path):
    source_path, sha, last = _write_source(tmp_path, alternating=True)
    handoff = _handoff(tmp_path / "handoff.json", source_path, "0" * 64, last)
    out = diagnose_nexus_handoff(handoff, tmp_path)
    row = out["candidates"][0]
    assert row["status"] == "DIAGNOSTIC_ERROR"
    assert "raw SHA mismatch" in row["error"]
    assert row["protected_holdout_touched"] is False
