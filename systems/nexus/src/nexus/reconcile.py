from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

from .contracts import StreamManifest


@dataclass(frozen=True)
class CorpusFingerprint:
    label: str
    physical_entries: int
    usable_entries: int
    rows: int
    distinct_byte_hashes: int
    distinct_logical_hashes: int
    manifest_sha256: str


@dataclass(frozen=True)
class CorpusReconciliation:
    left: CorpusFingerprint
    right: CorpusFingerprint
    common_byte_hashes: int
    left_only_byte_hashes: int
    right_only_byte_hashes: int
    common_logical_hashes: int
    left_only_symbols: tuple[str, ...]
    right_only_symbols: tuple[str, ...]

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass(frozen=True)
class CatalogReconciliation:
    """Hash-first comparison between two catalog snapshots.

    Paths and filenames are intentionally not used as identity.  A file may be
    renamed or moved without becoming a different market-data object.
    """

    left_entries: int
    right_entries: int
    raw_hash_matches: int
    logical_hash_matches: int
    left_only_raw_hashes: tuple[str, ...]
    right_only_raw_hashes: tuple[str, ...]
    left_only_logical_hashes: tuple[str, ...]
    right_only_logical_hashes: tuple[str, ...]
    left_only_symbols: tuple[str, ...]
    right_only_symbols: tuple[str, ...]

    @property
    def common_byte_hashes(self) -> int:
        return self.raw_hash_matches

    @property
    def common_logical_hashes(self) -> int:
        return self.logical_hash_matches

    @property
    def exact_coverage(self) -> bool:
        return not self.left_only_raw_hashes and not self.right_only_raw_hashes

    def to_dict(self) -> dict:
        d = asdict(self)
        d["common_byte_hashes"] = self.common_byte_hashes
        d["common_logical_hashes"] = self.common_logical_hashes
        return d


@dataclass(frozen=True)
class DeclaredCheckpointGap:
    actual_usable_entries: int
    actual_rows: int
    declared_usable_entries: int
    declared_rows: int
    unresolved_entry_gap: int
    unresolved_row_gap: int
    coverage_claim_allowed: bool

    @property
    def checkpoint_reconciled(self) -> bool:
        return self.unresolved_entry_gap == 0 and self.unresolved_row_gap == 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["checkpoint_reconciled"] = self.checkpoint_reconciled
        return d


def _usable(ms: Iterable[StreamManifest]) -> list[StreamManifest]:
    return [
        m
        for m in ms
        if "appledouble" not in m.quality_flags and m.row_count > 0
    ]


def fingerprint(label: str, ms: list[StreamManifest]) -> CorpusFingerprint:
    usable = _usable(ms)
    payload = [m.to_dict() for m in sorted(ms, key=lambda x: x.identity.source_path)]
    h = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    logical = {
        m.metadata.get("logical_sha256")
        for m in usable
        if m.metadata.get("logical_sha256")
    }
    return CorpusFingerprint(
        label=label,
        physical_entries=len(ms),
        usable_entries=len(usable),
        rows=sum(m.row_count for m in usable),
        distinct_byte_hashes=len({m.identity.raw_sha256 for m in usable}),
        distinct_logical_hashes=len(logical),
        manifest_sha256=h,
    )


def reconcile(
    left_label: str,
    left: list[StreamManifest],
    right_label: str,
    right: list[StreamManifest],
) -> CorpusReconciliation:
    lf = fingerprint(left_label, left)
    rf = fingerprint(right_label, right)
    lu = _usable(left)
    ru = _usable(right)
    lh = {m.identity.raw_sha256 for m in lu}
    rh = {m.identity.raw_sha256 for m in ru}
    ll = {
        m.metadata.get("logical_sha256")
        for m in lu
        if m.metadata.get("logical_sha256")
    }
    rl = {
        m.metadata.get("logical_sha256")
        for m in ru
        if m.metadata.get("logical_sha256")
    }
    ls = {m.identity.symbol for m in lu}
    rs = {m.identity.symbol for m in ru}
    return CorpusReconciliation(
        left=lf,
        right=rf,
        common_byte_hashes=len(lh & rh),
        left_only_byte_hashes=len(lh - rh),
        right_only_byte_hashes=len(rh - lh),
        common_logical_hashes=len(ll & rl),
        left_only_symbols=tuple(sorted(ls - rs)),
        right_only_symbols=tuple(sorted(rs - ls)),
    )


def reconcile_catalogs(
    left: list[StreamManifest], right: list[StreamManifest]
) -> CatalogReconciliation:
    """Compare two usable catalog snapshots using content identity first."""

    lu = _usable(left)
    ru = _usable(right)
    lraw = {m.identity.raw_sha256 for m in lu if m.identity.raw_sha256}
    rraw = {m.identity.raw_sha256 for m in ru if m.identity.raw_sha256}
    llogical = {
        str(m.metadata["logical_sha256"])
        for m in lu
        if m.metadata.get("logical_sha256")
    }
    rlogical = {
        str(m.metadata["logical_sha256"])
        for m in ru
        if m.metadata.get("logical_sha256")
    }
    lsyms = {m.identity.symbol for m in lu if m.identity.symbol}
    rsyms = {m.identity.symbol for m in ru if m.identity.symbol}
    return CatalogReconciliation(
        left_entries=len(lu),
        right_entries=len(ru),
        raw_hash_matches=len(lraw & rraw),
        logical_hash_matches=len(llogical & rlogical),
        left_only_raw_hashes=tuple(sorted(lraw - rraw)),
        right_only_raw_hashes=tuple(sorted(rraw - lraw)),
        left_only_logical_hashes=tuple(sorted(llogical - rlogical)),
        right_only_logical_hashes=tuple(sorted(rlogical - llogical)),
        left_only_symbols=tuple(sorted(lsyms - rsyms)),
        right_only_symbols=tuple(sorted(rsyms - lsyms)),
    )


def compare_declared_checkpoint(
    manifests: list[StreamManifest],
    *,
    declared_usable_entries: int,
    declared_rows: int,
) -> DeclaredCheckpointGap:
    """Compare materialized counts to a declared checkpoint without authorizing coverage.

    Positive gaps mean the declared checkpoint contains material not present in
    the current catalog. Negative gaps are clamped to zero because having more
    material than an older checkpoint is not a count deficit. Matching counts
    reconcile the checkpoint only; semantic/session/identity completeness remains
    a separate reviewed gate.
    """

    usable = _usable(manifests)
    actual_entries = len(usable)
    actual_rows = sum(m.row_count for m in usable)
    entry_gap = max(0, int(declared_usable_entries) - actual_entries)
    row_gap = max(0, int(declared_rows) - actual_rows)
    return DeclaredCheckpointGap(
        actual_usable_entries=actual_entries,
        actual_rows=actual_rows,
        declared_usable_entries=int(declared_usable_entries),
        declared_rows=int(declared_rows),
        unresolved_entry_gap=entry_gap,
        unresolved_row_gap=row_gap,
        coverage_claim_allowed=False,
    )
