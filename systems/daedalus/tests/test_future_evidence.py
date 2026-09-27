import hashlib
import json
import zipfile
from pathlib import Path

from daedalus.future_evidence import assess_nexus_confirmation_readiness


def _csv_bytes(start: int, count: int, *, include_header: bool = True) -> bytes:
    rows = []
    if include_header:
        rows.append("time,open,high,low,close")
    for i in range(count):
        t = start + i * 60
        close = 100 + i * 0.01
        rows.append(f"{t},{close},{close+1},{close-1},{close}")
    return ("\n".join(rows) + "\n").encode()


def _write_archive(root: Path, raw: bytes) -> None:
    with zipfile.ZipFile(root / "corpus.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sample/BATS_TEST, 1.csv", raw)


def _handoff(path: Path, old_raw: bytes, cutoff_ns: int) -> Path:
    raw_sha = hashlib.sha256(old_raw).hexdigest()
    stream_id = f"zipcsv:TEST:{raw_sha[:12]}"
    payload = {
        "schema": "nexus.daedalus-validation-handoff.v1",
        "source_iteration": 7,
        "loop_code_version": "1.3.1",
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
                "candidate_id": "abc", "family": "return_reversal", "priority": "P1", "score": 120.0,
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
                "stream_id": stream_id,
                "source_path": "corpus.zip!sample/BATS_TEST, 1.csv",
                "raw_sha256": raw_sha,
                "raw_size_bytes": len(old_raw),
                "last_event_ns": cutoff_ns,
                "admitted_default_integrity": True,
            }],
            "selection_context": {"candidate_family_size_in_iteration": 1},
            "clean_confirmation_rule": {
                "rule": "UNSEEN_EVIDENCE_ONLY",
                "current_source_history_is_pristine": False,
                "max_discovery_last_event_ns": cutoff_ns,
            },
            "production_authorized": False,
        }],
        "statistical_promotion_performed": False,
        "protected_holdout_spent": False,
        "production_authorized": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_same_bytes_are_not_new_evidence(tmp_path):
    start = 1700000000
    old = _csv_bytes(start, 10)
    _write_archive(tmp_path, old)
    cutoff = (start + 9 * 60) * 1_000_000_000
    handoff = _handoff(tmp_path / "handoff.json", old, cutoff)
    out = assess_nexus_confirmation_readiness(handoff, tmp_path, min_new_rows=2)
    row = out["candidates"][0]
    assert row["status"] == "WAITING_NO_NEW_BYTES"
    assert row["confirmation_ready"] is False
    assert out["protected_outcomes_touched"] is False


def test_append_only_future_rows_can_become_ready_without_reading_outcomes(tmp_path):
    start = 1700000000
    old = _csv_bytes(start, 10)
    appended = _csv_bytes(start + 10 * 60, 3, include_header=False)
    _write_archive(tmp_path, old + appended)
    cutoff = (start + 9 * 60) * 1_000_000_000
    handoff = _handoff(tmp_path / "handoff.json", old, cutoff)
    out = assess_nexus_confirmation_readiness(handoff, tmp_path, min_new_rows=3)
    row = out["candidates"][0]
    assert row["historical_prefix_matches"] is True
    assert row["new_rows_after_discovery_cutoff"] == 3
    assert row["status"] == "READY_FOR_CONFIRMATORY_EVALUATION"
    assert row["confirmation_ready"] is True
    assert row["protected_outcomes_touched"] is False
    assert row["protected_holdout_spent"] is False


def test_rewritten_history_fails_closed(tmp_path):
    start = 1700000000
    old = _csv_bytes(start, 10)
    rewritten = bytearray(old + _csv_bytes(start + 10 * 60, 3, include_header=False))
    rewritten[5] = ord("X")
    _write_archive(tmp_path, bytes(rewritten))
    cutoff = (start + 9 * 60) * 1_000_000_000
    handoff = _handoff(tmp_path / "handoff.json", old, cutoff)
    out = assess_nexus_confirmation_readiness(handoff, tmp_path, min_new_rows=3)
    row = out["candidates"][0]
    assert row["status"] == "BLOCKED_HISTORICAL_PREFIX_CHANGED"
    assert row["confirmation_ready"] is False
    assert row["protected_holdout_spent"] is False
