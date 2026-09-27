from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any
import zipfile

from .bridge import nexus_development_tasks, summarize_nexus_handoff


READINESS_SCHEMA = "daedalus.nexus-confirmation-readiness.v1"
_NS = Decimal("1000000000")


def _split_archive_source_path(source_path: str) -> tuple[str, str]:
    if "!" not in source_path:
        raise ValueError(f"NEXUS source_path is not archive-qualified: {source_path!r}")
    archive_rel, member = source_path.split("!", 1)
    archive_rel = archive_rel.strip()
    member = member.lstrip("/")
    if not archive_rel or not member:
        raise ValueError(f"invalid archive-qualified NEXUS source_path: {source_path!r}")
    return archive_rel, member


def _time_to_ns(value: str) -> int | None:
    try:
        x = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return None
    if not x.is_finite():
        return None
    return int((x * _NS).to_integral_value(rounding=ROUND_HALF_EVEN))


def _read_member(corpus_root: Path, source_path: str) -> bytes:
    archive_rel, member = _split_archive_source_path(source_path)
    archive_path = corpus_root / archive_rel
    if not archive_path.exists():
        raise FileNotFoundError(f"archive not found: {archive_path}")
    with zipfile.ZipFile(archive_path) as zf:
        return zf.read(member)


def _future_time_summary(raw_bytes: bytes, cutoff_ns: int) -> tuple[int, int | None, int]:
    text = io.TextIOWrapper(io.BytesIO(raw_bytes), encoding="utf-8-sig", errors="replace", newline="")
    reader = csv.reader(text)
    header = next(reader, [])
    lower = [str(x).strip().lower() for x in header]
    time_i = next((i for i, c in enumerate(lower) if c == "time"), None)
    if time_i is None:
        raise ValueError("source is missing time column")
    future_count = 0
    last_future_ns: int | None = None
    invalid_time_rows = 0
    for row in reader:
        if time_i >= len(row):
            invalid_time_rows += 1
            continue
        ns = _time_to_ns(row[time_i])
        if ns is None:
            invalid_time_rows += 1
            continue
        if ns > cutoff_ns:
            future_count += 1
            last_future_ns = ns if last_future_ns is None else max(last_future_ns, ns)
    return future_count, last_future_ns, invalid_time_rows


def assess_nexus_confirmation_readiness(
    handoff_path: Path,
    corpus_root: Path,
    *,
    min_new_rows: int = 250,
) -> dict[str, Any]:
    """Check whether genuinely appended evidence exists after NEXUS discovery.

    The gate is intentionally byte-prefix strict. If a provider rewrites historical
    bytes, DAEDALUS refuses to call the new file an append-only continuation without a
    separate reviewed reconciliation. This function inspects only identity, bytes and
    timestamps; it does not inspect future returns/targets and does not spend a holdout.
    """
    if min_new_rows <= 0:
        raise ValueError("min_new_rows must be > 0")
    summary = summarize_nexus_handoff(handoff_path)
    tasks = nexus_development_tasks(handoff_path)
    rows: list[dict[str, Any]] = []

    for task in tasks:
        unique_evidence: dict[str, dict[str, Any]] = {}
        for evidence in task.source_evidence:
            key = str(evidence.get("raw_sha256") or evidence.get("source_path") or "")
            unique_evidence.setdefault(key, evidence)
        if len(unique_evidence) != 1:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "status": "BLOCKED_AMBIGUOUS_SOURCE_EVIDENCE",
                "confirmation_ready": False,
                "protected_outcomes_touched": False,
                "protected_holdout_spent": False,
                "production_authorized": False,
            })
            continue

        evidence = next(iter(unique_evidence.values()))
        source_path = str(evidence.get("source_path") or "")
        expected_sha = str(evidence.get("raw_sha256") or "")
        old_size_raw = evidence.get("raw_size_bytes")
        cutoff_raw = (task.clean_confirmation_rule or {}).get("max_discovery_last_event_ns")
        if not expected_sha or old_size_raw is None or cutoff_raw is None:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "source_path": source_path,
                "status": "BLOCKED_MISSING_DISCOVERY_PREFIX_PROVENANCE",
                "confirmation_ready": False,
                "protected_outcomes_touched": False,
                "protected_holdout_spent": False,
                "production_authorized": False,
            })
            continue
        old_size = int(old_size_raw)
        cutoff_ns = int(cutoff_raw)
        try:
            current = _read_member(corpus_root, source_path)
        except (OSError, KeyError, zipfile.BadZipFile, ValueError) as exc:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "source_path": source_path,
                "status": "WAITING_SOURCE_UNAVAILABLE",
                "error": f"{type(exc).__name__}: {exc}",
                "confirmation_ready": False,
                "protected_outcomes_touched": False,
                "protected_holdout_spent": False,
                "production_authorized": False,
            })
            continue

        if len(current) < old_size:
            status = "BLOCKED_SOURCE_TRUNCATED"
            prefix_matches = False
            future_count = 0
            last_future_ns = None
            invalid_time_rows = 0
        else:
            prefix_hash = hashlib.sha256(current[:old_size]).hexdigest()
            prefix_matches = prefix_hash == expected_sha
            if not prefix_matches:
                status = "BLOCKED_HISTORICAL_PREFIX_CHANGED"
                future_count = 0
                last_future_ns = None
                invalid_time_rows = 0
            elif len(current) == old_size:
                status = "WAITING_NO_NEW_BYTES"
                future_count = 0
                last_future_ns = None
                invalid_time_rows = 0
            else:
                try:
                    future_count, last_future_ns, invalid_time_rows = _future_time_summary(current, cutoff_ns)
                except (ValueError, csv.Error, UnicodeError) as exc:
                    rows.append({
                        "candidate_id": task.candidate_id,
                        "family": task.family,
                        "source_path": source_path,
                        "status": "BLOCKED_FUTURE_TIMESTAMP_AUDIT_ERROR",
                        "error": f"{type(exc).__name__}: {exc}",
                        "confirmation_ready": False,
                        "historical_prefix_matches": True,
                        "protected_outcomes_touched": False,
                        "protected_holdout_spent": False,
                        "production_authorized": False,
                    })
                    continue
                status = (
                    "READY_FOR_CONFIRMATORY_EVALUATION"
                    if future_count >= min_new_rows
                    else "WAITING_INSUFFICIENT_NEW_ROWS"
                )

        rows.append({
            "candidate_id": task.candidate_id,
            "family": task.family,
            "source_path": source_path,
            "discovery_raw_sha256": expected_sha,
            "discovery_raw_size_bytes": old_size,
            "current_raw_size_bytes": len(current),
            "discovery_last_event_ns": cutoff_ns,
            "historical_prefix_matches": prefix_matches,
            "new_rows_after_discovery_cutoff": int(future_count),
            "latest_new_event_ns": last_future_ns,
            "invalid_time_rows_during_readiness_scan": int(invalid_time_rows),
            "minimum_new_rows_required": int(min_new_rows),
            "status": status,
            "confirmation_ready": status == "READY_FOR_CONFIRMATORY_EVALUATION",
            "protected_outcomes_touched": False,
            "protected_holdout_spent": False,
            "production_authorized": False,
        })

    counts = Counter(str(x["status"]) for x in rows)
    ready = sum(bool(x.get("confirmation_ready")) for x in rows)
    return {
        "schema": READINESS_SCHEMA,
        "nexus_handoff": summary,
        "minimum_new_rows_required": int(min_new_rows),
        "candidate_count": len(rows),
        "confirmation_ready_count": int(ready),
        "status_counts": dict(sorted(counts.items())),
        "candidates": rows,
        "protected_outcomes_touched": False,
        "protected_holdout_spent": False,
        "statistical_promotion_performed": False,
        "production_authorized": False,
    }


def write_nexus_confirmation_readiness(
    handoff_path: Path,
    corpus_root: Path,
    output_path: Path,
    *,
    min_new_rows: int = 250,
) -> Path:
    payload = assess_nexus_confirmation_readiness(handoff_path, corpus_root, min_new_rows=min_new_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return output_path
