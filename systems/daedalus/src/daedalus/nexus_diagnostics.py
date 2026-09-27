from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any
import zipfile

import numpy as np

from .bridge import nexus_development_tasks, summarize_nexus_handoff


DIAGNOSTIC_SCHEMA = "daedalus.nexus-retrospective-diagnostics.v1"


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _split_archive_source_path(source_path: str) -> tuple[str, str]:
    if "!" not in source_path:
        raise ValueError(f"NEXUS source_path is not archive-qualified: {source_path!r}")
    archive_rel, member = source_path.split("!", 1)
    archive_rel = archive_rel.strip()
    member = member.lstrip("/")
    if not archive_rel or not member:
        raise ValueError(f"invalid archive-qualified NEXUS source_path: {source_path!r}")
    return archive_rel, member


def _read_close_series(corpus_root: Path, evidence: dict[str, Any]) -> np.ndarray:
    archive_rel, member = _split_archive_source_path(str(evidence["source_path"]))
    archive_path = corpus_root / archive_rel
    if not archive_path.exists():
        raise FileNotFoundError(f"NEXUS archive not found under corpus root: {archive_path}")
    with zipfile.ZipFile(archive_path) as zf:
        raw_bytes = zf.read(member)
    expected_sha = str(evidence.get("raw_sha256") or "")
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    if expected_sha and actual_sha != expected_sha:
        raise ValueError(
            f"raw SHA mismatch for {evidence.get('stream_id')}: expected {expected_sha}, got {actual_sha}"
        )
    text = io.TextIOWrapper(io.BytesIO(raw_bytes), encoding="utf-8-sig", errors="replace", newline="")
    reader = csv.reader(text)
    header = next(reader, [])
    lower = [str(x).strip().lower() for x in header]
    close_i = next((i for i, c in enumerate(lower) if c == "close"), None)
    if close_i is None:
        raise ValueError(f"source is missing close column: {evidence.get('source_path')}")
    closes: list[float] = []
    for row in reader:
        if close_i >= len(row):
            continue
        close = _safe_float(row[close_i])
        if close is not None and close > 0.0:
            closes.append(close)
    return np.asarray(closes, dtype=float)


def _log_returns(closes: np.ndarray) -> np.ndarray:
    if len(closes) < 2:
        return np.asarray([], dtype=float)
    ret = np.log(closes[1:] / closes[:-1])
    return ret[np.isfinite(ret)]


def _corr_lag1(values: np.ndarray) -> float | None:
    if len(values) < 3:
        return None
    x = values[:-1]
    y = values[1:]
    sx = float(np.std(x, ddof=1))
    sy = float(np.std(y, ddof=1))
    if sx <= 0.0 or sy <= 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _contiguous_blocks(values: np.ndarray, requested_blocks: int, min_rows_per_block: int) -> list[np.ndarray]:
    max_blocks = len(values) // max(1, int(min_rows_per_block))
    blocks = min(max(1, int(requested_blocks)), max_blocks)
    if blocks < 2:
        return []
    return [x for x in np.array_split(values, blocks) if len(x)]


def _return_diagnostic(
    family: str,
    returns: np.ndarray,
    *,
    requested_blocks: int,
    min_rows_per_block: int,
) -> dict[str, Any]:
    expected_sign = 1 if family == "return_persistence" else -1
    blocks = _contiguous_blocks(returns, requested_blocks, min_rows_per_block)
    correlations = [_corr_lag1(block) for block in blocks]
    valid = [x for x in correlations if x is not None and math.isfinite(x)]
    if len(valid) < 3:
        status = "INSUFFICIENT_RETROSPECTIVE_EVIDENCE"
        support = None
        median = None
    else:
        support = float(np.mean([expected_sign * x > 0.0 for x in valid]))
        median = float(np.median(valid))
        aligned_median = expected_sign * median > 0.0
        if support >= 0.80 and aligned_median:
            status = "RETROSPECTIVE_DIRECTION_STABLE"
        elif support >= 0.60 and aligned_median:
            status = "RETROSPECTIVE_DIRECTION_PARTIAL"
        else:
            status = "RETROSPECTIVE_DIRECTION_UNSTABLE"
    return {
        "diagnostic_type": "lag1_return_direction_stability",
        "expected_direction": "positive" if expected_sign > 0 else "negative",
        "return_count": int(len(returns)),
        "block_count": len(blocks),
        "block_return_counts": [int(len(x)) for x in blocks],
        "block_lag1_correlations": correlations,
        "expected_sign_support_fraction": support,
        "median_block_lag1_correlation": median,
        "status": status,
    }


def _volatility_diagnostic(
    returns: np.ndarray,
    *,
    requested_blocks: int,
    min_rows_per_block: int,
) -> dict[str, Any]:
    blocks = _contiguous_blocks(returns, requested_blocks, min_rows_per_block)
    vols = [float(np.std(x, ddof=1)) if len(x) >= 2 else None for x in blocks]
    valid = [x for x in vols if x is not None and x > 0.0 and math.isfinite(x)]
    if len(valid) < 3:
        status = "INSUFFICIENT_RETROSPECTIVE_EVIDENCE"
        max_min = None
        max_adj = None
        jump_count = 0
    else:
        max_min = float(max(valid) / min(valid))
        adjacent: list[float] = []
        for left, right in zip(vols[:-1], vols[1:]):
            if left is None or right is None or left <= 0.0 or right <= 0.0:
                continue
            adjacent.append(float(max(left, right) / min(left, right)))
        max_adj = max(adjacent) if adjacent else None
        jump_count = sum(x >= 1.5 for x in adjacent)
        if max_adj is not None and max_adj >= 2.0 and max_min >= 2.0:
            status = "RETROSPECTIVE_NONSTATIONARITY_STRONG"
        elif max_adj is not None and max_adj >= 1.5 and max_min >= 1.75:
            status = "RETROSPECTIVE_NONSTATIONARITY_PARTIAL"
        else:
            status = "RETROSPECTIVE_NONSTATIONARITY_WEAK"
    return {
        "diagnostic_type": "block_return_volatility_stability",
        "return_count": int(len(returns)),
        "block_count": len(blocks),
        "block_return_counts": [int(len(x)) for x in blocks],
        "block_return_std": vols,
        "max_to_min_block_volatility_ratio": max_min,
        "max_adjacent_block_volatility_ratio": max_adj,
        "adjacent_jump_count_ge_1_5": int(jump_count),
        "status": status,
    }


def diagnose_nexus_handoff(
    handoff_path: Path,
    corpus_root: Path,
    *,
    requested_blocks: int = 5,
    min_rows_per_block: int = 50,
) -> dict[str, Any]:
    """Run development-only block diagnostics on NEXUS behavioral hypotheses.

    These diagnostics can eliminate or deprioritize unstable hypotheses. They cannot
    confirm them because NEXUS selected the hypotheses after seeing the full current
    history. No protected holdout is spent or relabeled here.
    """
    if requested_blocks < 3:
        raise ValueError("requested_blocks must be >= 3")
    if min_rows_per_block < 20:
        raise ValueError("min_rows_per_block must be >= 20")

    handoff_summary = summarize_nexus_handoff(handoff_path)
    tasks = nexus_development_tasks(handoff_path)
    rows: list[dict[str, Any]] = []

    for task in tasks:
        unique_evidence: dict[str, dict[str, Any]] = {}
        for evidence in task.source_evidence:
            raw_sha = str(evidence.get("raw_sha256") or evidence.get("source_path") or "")
            unique_evidence.setdefault(raw_sha, evidence)
        if not unique_evidence:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "status": "MISSING_SOURCE_EVIDENCE",
                "retrospective_only": True,
                "protected_holdout_touched": False,
                "production_authorized": False,
            })
            continue

        # Exact-byte copies are not independent votes. One raw hash is one evidence path.
        evidence_rows = sorted(unique_evidence.values(), key=lambda x: str(x.get("source_path", "")))
        if len(evidence_rows) != 1:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "status": "AMBIGUOUS_MULTI_SOURCE_TASK",
                "unique_raw_source_count": len(evidence_rows),
                "retrospective_only": True,
                "protected_holdout_touched": False,
                "production_authorized": False,
            })
            continue

        evidence = evidence_rows[0]
        try:
            closes = _read_close_series(corpus_root, evidence)
            returns = _log_returns(closes)
            if task.family in {"return_persistence", "return_reversal"}:
                diagnostic = _return_diagnostic(
                    task.family, returns,
                    requested_blocks=requested_blocks,
                    min_rows_per_block=min_rows_per_block,
                )
            elif task.family == "regime_volatility_shift":
                diagnostic = _volatility_diagnostic(
                    returns,
                    requested_blocks=requested_blocks,
                    min_rows_per_block=min_rows_per_block,
                )
            else:
                diagnostic = {"status": "UNSUPPORTED_DIAGNOSTIC_FAMILY"}
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "priority": task.priority,
                "score": task.score,
                "stream_id": evidence.get("stream_id"),
                "source_path": evidence.get("source_path"),
                "raw_sha256": evidence.get("raw_sha256"),
                "physical_copy_count_for_same_raw_hash": sum(
                    1 for x in task.source_evidence if x.get("raw_sha256") == evidence.get("raw_sha256")
                ),
                "diagnostic": diagnostic,
                "status": diagnostic["status"],
                "retrospective_only": True,
                "independent_confirmation": False,
                "confirmatory_evidence_required": True,
                "protected_holdout_touched": False,
                "production_authorized": False,
            })
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, csv.Error) as exc:
            rows.append({
                "candidate_id": task.candidate_id,
                "family": task.family,
                "status": "DIAGNOSTIC_ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "retrospective_only": True,
                "independent_confirmation": False,
                "confirmatory_evidence_required": True,
                "protected_holdout_touched": False,
                "production_authorized": False,
            })

    status_counts = Counter(str(x.get("status", "UNKNOWN")) for x in rows)
    return {
        "schema": DIAGNOSTIC_SCHEMA,
        "nexus_handoff": handoff_summary,
        "requested_blocks": int(requested_blocks),
        "min_rows_per_block": int(min_rows_per_block),
        "diagnosed_candidate_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "candidates": rows,
        "interpretation": {
            "can_reject_or_deprioritize_unstable_hypotheses": True,
            "can_confirm_hypotheses": False,
            "reason_confirmation_is_blocked": "candidate selection already inspected the full current source history",
        },
        "protected_holdout_touched": False,
        "statistical_promotion_performed": False,
        "production_authorized": False,
    }


def write_nexus_diagnostics(
    handoff_path: Path,
    corpus_root: Path,
    output_path: Path,
    *,
    requested_blocks: int = 5,
    min_rows_per_block: int = 50,
) -> Path:
    payload = diagnose_nexus_handoff(
        handoff_path,
        corpus_root,
        requested_blocks=requested_blocks,
        min_rows_per_block=min_rows_per_block,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return output_path
