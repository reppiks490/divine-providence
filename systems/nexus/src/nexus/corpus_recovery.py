from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Any

from .contracts import StreamManifest


SCHEMA = "nexus.corpus-recovery-plan.v1"


@dataclass(frozen=True, slots=True)
class HistoricalCorpusAnchor:
    usable_entries: int
    usable_rows: int
    distinct_byte_contents: int | None = None
    archive_count: int | None = None
    label: str = "historical-anchor"


def _usable(manifests: Iterable[StreamManifest]) -> list[StreamManifest]:
    return [m for m in manifests if m.row_count > 0 and "appledouble" not in set(m.quality_flags)]


def build_corpus_recovery_plan(
    manifests: Iterable[StreamManifest],
    anchor: HistoricalCorpusAnchor,
    *,
    owner_expected_min_entries: int | None = None,
) -> dict[str, Any]:
    """Build a content-addressed recovery target from current and historical facts.

    The historical distinct-byte count is treated as a lower-bound checkpoint,
    not as proof that the historical corpus was complete. Duplicate entries are
    preserved as lineage facts but do not count as new market evidence.
    """
    rows = _usable(manifests)
    current_entries = len(rows)
    current_rows = sum(int(m.row_count) for m in rows)
    current_distinct = len({m.identity.raw_sha256 for m in rows if m.identity.raw_sha256})
    current_duplicate_entries = max(0, current_entries - current_distinct)

    entry_gap = max(0, int(anchor.usable_entries) - current_entries)
    row_gap = max(0, int(anchor.usable_rows) - current_rows)

    hist_distinct = anchor.distinct_byte_contents
    if hist_distinct is not None:
        distinct_gap_floor = max(0, int(hist_distinct) - current_distinct)
        historical_duplicate_entries = max(0, int(anchor.usable_entries) - int(hist_distinct))
        duplicate_entry_gap = max(0, historical_duplicate_entries - current_duplicate_entries)
    else:
        distinct_gap_floor = None
        historical_duplicate_entries = None
        duplicate_entry_gap = None

    owner_gap = None
    if owner_expected_min_entries is not None:
        owner_gap = max(0, int(owner_expected_min_entries) - current_entries)

    priorities = [
        {
            "priority": 1,
            "objective": "recover_unique_byte_contents",
            "reason": "Unique content expands evidentiary coverage; duplicate downloads do not.",
            "target_missing_distinct_byte_contents_floor": distinct_gap_floor,
        },
        {
            "priority": 2,
            "objective": "reconstruct_archive_membership_and_lineage",
            "reason": "Historical checkpoint spans multiple ZIPs; preserve archive/member provenance and duplicate relationships.",
            "target_historical_archive_count": anchor.archive_count,
        },
        {
            "priority": 3,
            "objective": "reconcile_rows_and_stream_identity",
            "reason": "Recovered bytes must reproduce row counts, symbols, claims, hashes, and identity before any research coverage claim changes.",
            "target_missing_rows": row_gap,
        },
        {
            "priority": 4,
            "objective": "recover_duplicate_lineage_only_after_unique_content",
            "reason": "Duplicate entries matter for provenance but should not consume recovery effort before missing unique evidence.",
            "target_missing_duplicate_entries_relative_to_anchor": duplicate_entry_gap,
        },
    ]

    acceptance = {
        "historical_anchor_reconciled": (
            current_entries >= anchor.usable_entries
            and current_rows >= anchor.usable_rows
            and (hist_distinct is None or current_distinct >= hist_distinct)
        ),
        "owner_expected_min_entries_reached": (
            None if owner_expected_min_entries is None else current_entries >= owner_expected_min_entries
        ),
        "coverage_claim_allowed": False,
        "coverage_claim_rule": (
            "Do not enable corpus-wide coverage merely by hitting counts. Require content-addressed manifests, "
            "archive/member provenance, identity reconciliation, and explicit review of whether the historical anchor itself was complete."
        ),
    }

    return {
        "schema": SCHEMA,
        "historical_anchor": asdict(anchor),
        "current": {
            "usable_entries": current_entries,
            "usable_rows": current_rows,
            "distinct_byte_contents": current_distinct,
            "duplicate_entries": current_duplicate_entries,
        },
        "gaps_relative_to_historical_anchor": {
            "usable_entry_gap": entry_gap,
            "usable_row_gap": row_gap,
            "distinct_byte_content_gap_floor": distinct_gap_floor,
            "duplicate_entry_gap": duplicate_entry_gap,
        },
        "owner_expected_min_entry_gap": owner_gap,
        "recovery_priorities": priorities,
        "acceptance": acceptance,
        "counts_are_lower_bounds_not_completeness_proof": True,
        "duplicate_entries_do_not_receive_independent_evidence_weight": True,
        "production_authorized": False,
    }
