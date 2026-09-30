from __future__ import annotations

import csv
import io
import json
import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping
import zipfile

from .contracts import StreamManifest


SCHEMA = "nexus.representation-lineage-resolution.v1"


@dataclass(frozen=True, slots=True)
class PairwiseLineageRelation:
    left_stream_id: str
    right_stream_id: str
    left_raw_sha256: str
    right_raw_sha256: str
    left_rows: int
    right_rows: int
    overlap_rows: int
    identical_overlap_rows: int
    conflicting_overlap_rows: int
    conflict_event_ns: tuple[int, ...]
    relation: str
    compatible_same_lineage: bool
    boundary_revision_only: bool

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["conflict_event_ns"] = list(self.conflict_event_ns)
        return d


@dataclass(frozen=True, slots=True)
class CandidateLineageResolution:
    candidate_id: str
    status: str
    canonical_stream_id: str | None
    canonical_raw_sha256: str | None
    unique_raw_stream_count: int
    duplicate_alias_count: int
    compatible_component_count: int
    unresolved_conflict_count: int
    independent_view_count: int
    canonicalization_allowed: bool
    fusion_as_independent_views_allowed: bool
    reason: str
    pairwise_relations: tuple[PairwiseLineageRelation, ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pairwise_relations"] = [x.to_dict() for x in self.pairwise_relations]
        return d


def _candidate_dict(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, Mapping):
        return dict(candidate)
    if hasattr(candidate, "to_dict"):
        return dict(candidate.to_dict())
    raise TypeError(f"unsupported candidate type: {type(candidate)!r}")


def _to_event_ns(raw: str) -> int | None:
    try:
        return int(Decimal(raw.strip()) * Decimal(1_000_000_000))
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _load_ohlc_rows(zf: zipfile.ZipFile, member: str) -> dict[int, tuple[Decimal, Decimal, Decimal, Decimal]]:
    out: dict[int, tuple[Decimal, Decimal, Decimal, Decimal]] = {}
    with zf.open(member, "r") as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = next(reader, [])
        lower = [str(x).strip().lower() for x in header]
        idx = {k: next((i for i, c in enumerate(lower) if c == k), None) for k in ("time", "open", "high", "low", "close")}
        if any(idx[k] is None for k in idx):
            return out
        for row in reader:
            try:
                t_raw = row[idx["time"]]  # type: ignore[index]
            except (IndexError, TypeError):
                continue
            event_ns = _to_event_ns(t_raw)
            if event_ns is None:
                continue
            values: list[Decimal] = []
            valid = True
            for key in ("open", "high", "low", "close"):
                i = idx[key]
                try:
                    value = _to_decimal(row[i])  # type: ignore[index]
                except (IndexError, TypeError):
                    value = None
                if value is None:
                    valid = False
                    break
                values.append(value)
            if valid:
                out[event_ns] = (values[0], values[1], values[2], values[3])
    return out


def _pair_relation(
    left: StreamManifest,
    left_rows: dict[int, tuple[Decimal, Decimal, Decimal, Decimal]],
    right: StreamManifest,
    right_rows: dict[int, tuple[Decimal, Decimal, Decimal, Decimal]],
) -> PairwiseLineageRelation:
    lk = set(left_rows)
    rk = set(right_rows)
    overlap = sorted(lk & rk)
    conflicts = tuple(t for t in overlap if left_rows[t] != right_rows[t])
    identical = len(overlap) - len(conflicts)

    boundary_revision_only = False
    if overlap and conflicts:
        # Trading/chart exports can differ on a still-forming terminal bar when two
        # snapshots are taken at slightly different times. We tolerate only this
        # auditable edge case: every disagreement must sit at the final timestamp
        # of at least one compared snapshot, never in the interior history.
        terminal = {max(lk), max(rk)} if lk and rk else set()
        boundary_revision_only = all(t in terminal for t in conflicts)

    if not overlap:
        relation = "DISJOINT"
        compatible = False
    elif not conflicts:
        if lk == rk:
            relation = "IDENTICAL_COVERAGE"
        elif lk < rk:
            relation = "LEFT_STRICT_SUBSET_IDENTICAL"
        elif rk < lk:
            relation = "RIGHT_STRICT_SUBSET_IDENTICAL"
        else:
            relation = "OVERLAP_IDENTICAL"
        compatible = True
    elif boundary_revision_only and (identical / max(1, len(overlap))) >= 0.995:
        relation = "TERMINAL_SNAPSHOT_REVISION_COMPATIBLE"
        compatible = True
    else:
        relation = "OVERLAP_CONFLICT"
        compatible = False

    return PairwiseLineageRelation(
        left_stream_id=left.identity.stream_id,
        right_stream_id=right.identity.stream_id,
        left_raw_sha256=left.identity.raw_sha256,
        right_raw_sha256=right.identity.raw_sha256,
        left_rows=len(lk),
        right_rows=len(rk),
        overlap_rows=len(overlap),
        identical_overlap_rows=identical,
        conflicting_overlap_rows=len(conflicts),
        conflict_event_ns=conflicts,
        relation=relation,
        compatible_same_lineage=compatible,
        boundary_revision_only=boundary_revision_only,
    )


def _component_count(nodes: set[str], edges: list[tuple[str, str]]) -> int:
    if not nodes:
        return 0
    graph: dict[str, set[str]] = {n: set() for n in nodes}
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    seen: set[str] = set()
    components = 0
    for start in sorted(nodes):
        if start in seen:
            continue
        components += 1
        q = deque([start])
        seen.add(start)
        while q:
            cur = q.popleft()
            for nxt in graph[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
    return components


def build_representation_lineage_resolution(
    corpus_root: str | Path,
    manifests: Iterable[StreamManifest],
    candidates: Iterable[Any],
) -> dict[str, Any]:
    """Resolve representation-disagreement candidates using only overlapping row evidence.

    This routine does not infer market semantics. It answers a narrower identity
    question: are the allegedly different representations actually repeated/sliced
    exports of the same observed price path? Exact-byte aliases are collapsed; unique
    raw files are compared on timestamp + OHLC overlap. A one-edge snapshot revision is
    tolerated only when the disagreement occurs at the final row of at least one export.
    """
    root = Path(corpus_root)
    manifest_rows = list(manifests)
    by_stream: dict[str, list[StreamManifest]] = defaultdict(list)
    for m in manifest_rows:
        by_stream[m.identity.stream_id].append(m)

    candidate_rows = [
        _candidate_dict(c) for c in candidates
        if str(_candidate_dict(c).get("family", "")) == "representation_family_disagreement"
    ]

    archive_cache: dict[str, zipfile.ZipFile] = {}
    row_cache: dict[str, dict[int, tuple[Decimal, Decimal, Decimal, Decimal]]] = {}
    resolutions: list[CandidateLineageResolution] = []
    try:
        for candidate in candidate_rows:
            candidate_id = str(candidate.get("candidate_id") or "")
            scope = [str(x) for x in candidate.get("scope", [])]
            scoped: list[StreamManifest] = []
            for stream_id in scope:
                scoped.extend(by_stream.get(stream_id, []))
            scoped.sort(key=lambda m: (m.identity.raw_sha256, m.identity.source_path))

            # Exact-byte copies are aliases, not independent representations.
            unique_by_raw: dict[str, StreamManifest] = {}
            duplicate_alias_count = 0
            for m in scoped:
                if m.identity.raw_sha256 in unique_by_raw:
                    duplicate_alias_count += 1
                    continue
                unique_by_raw[m.identity.raw_sha256] = m
            unique = list(unique_by_raw.values())

            rows_by_raw: dict[str, dict[int, tuple[Decimal, Decimal, Decimal, Decimal]]] = {}
            for m in unique:
                archive_rel = str(m.metadata.get("archive_path") or "")
                member = str(m.metadata.get("archive_member") or "")
                if not archive_rel or not member:
                    rows_by_raw[m.identity.raw_sha256] = {}
                    continue
                cache_key = f"{archive_rel}!{member}"
                if cache_key in row_cache:
                    rows_by_raw[m.identity.raw_sha256] = row_cache[cache_key]
                    continue
                zf = archive_cache.get(archive_rel)
                if zf is None:
                    zf = zipfile.ZipFile(root / archive_rel)
                    archive_cache[archive_rel] = zf
                parsed = _load_ohlc_rows(zf, member)
                row_cache[cache_key] = parsed
                rows_by_raw[m.identity.raw_sha256] = parsed

            pairwise: list[PairwiseLineageRelation] = []
            compatible_edges: list[tuple[str, str]] = []
            unresolved_conflicts = 0
            raw_nodes = {m.identity.raw_sha256 for m in unique}
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    left, right = unique[i], unique[j]
                    rel = _pair_relation(
                        left, rows_by_raw.get(left.identity.raw_sha256, {}),
                        right, rows_by_raw.get(right.identity.raw_sha256, {}),
                    )
                    pairwise.append(rel)
                    if rel.compatible_same_lineage:
                        compatible_edges.append((left.identity.raw_sha256, right.identity.raw_sha256))
                    elif rel.relation == "OVERLAP_CONFLICT":
                        unresolved_conflicts += 1

            components = _component_count(raw_nodes, compatible_edges)
            connected = len(raw_nodes) == 1 or (len(raw_nodes) > 1 and components == 1)
            resolved = bool(raw_nodes) and connected and unresolved_conflicts == 0

            canonical: StreamManifest | None = None
            if unique:
                canonical = sorted(
                    unique,
                    key=lambda m: (
                        -len(rows_by_raw.get(m.identity.raw_sha256, {})),
                        -int(m.row_count),
                        m.identity.source_path,
                    ),
                )[0]

            if resolved:
                status = "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED"
                reason = (
                    "All unique raw exports are connected by timestamp/OHLC-identical overlap or terminal-only "
                    "snapshot revisions. Volatility dispersion is attributable to differing sample windows/snapshot edges, "
                    "not evidence of independent representations. Canonicalize; never count copies as independent votes."
                )
                independent_views = 0
            else:
                status = "UNRESOLVED_REPRESENTATION_IDENTITY"
                if unresolved_conflicts:
                    reason = (
                        "At least one overlapping export contains interior/conflicting OHLC evidence that cannot be "
                        "explained as a terminal snapshot revision. Keep identity blocked."
                    )
                else:
                    reason = (
                        "Unique raw exports are not connected by sufficient overlapping OHLC evidence. "
                        "Keep identity blocked pending external lineage/representation evidence."
                    )
                independent_views = len(raw_nodes)

            resolutions.append(CandidateLineageResolution(
                candidate_id=candidate_id,
                status=status,
                canonical_stream_id=canonical.identity.stream_id if canonical else None,
                canonical_raw_sha256=canonical.identity.raw_sha256 if canonical else None,
                unique_raw_stream_count=len(raw_nodes),
                duplicate_alias_count=duplicate_alias_count,
                compatible_component_count=components,
                unresolved_conflict_count=unresolved_conflicts,
                independent_view_count=independent_views,
                canonicalization_allowed=resolved,
                fusion_as_independent_views_allowed=False,
                reason=reason,
                pairwise_relations=tuple(pairwise),
            ))
    finally:
        for zf in archive_cache.values():
            zf.close()

    rows = [r.to_dict() for r in sorted(resolutions, key=lambda r: r.candidate_id)]
    body = {
        "schema": SCHEMA,
        "candidate_count": len(rows),
        "resolved_count": sum(r["status"] == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED" for r in rows),
        "unresolved_count": sum(r["status"] != "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED" for r in rows),
        "resolutions": rows,
        "statistical_fusion_performed": False,
        "production_authorized": False,
    }
    body["resolution_hash"] = hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_representation_lineage_resolution(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != SCHEMA:
        return False
    supplied=payload.get("resolution_hash")
    if not isinstance(supplied,str) or len(supplied)!=64:
        return False
    try:
        int(supplied,16)
    except ValueError:
        return False
    body=dict(payload);body.pop("resolution_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied != expected:
        return False
    if body.get("production_authorized") is not False or body.get("statistical_fusion_performed") is not False:
        return False
    rows=body.get("resolutions")
    if not isinstance(rows,list):
        return False

    ids=[];resolved_count=0
    for row in rows:
        if not isinstance(row,Mapping):
            return False
        cid=str(row.get("candidate_id") or "")
        if not cid:
            return False
        ids.append(cid)

        count_names=(
            "unique_raw_stream_count","duplicate_alias_count",
            "compatible_component_count","unresolved_conflict_count",
            "independent_view_count",
        )
        counts={}
        for name in count_names:
            value=row.get(name)
            if type(value) is not int or value < 0:
                return False
            counts[name]=value

        if row.get("fusion_as_independent_views_allowed") is not False:
            return False
        pairwise=row.get("pairwise_relations")
        if not isinstance(pairwise,list):
            return False

        canonical_raw=str(row.get("canonical_raw_sha256") or "")
        raw_nodes=set()
        if canonical_raw:
            if len(canonical_raw)!=64:
                return False
            try:
                int(canonical_raw,16)
            except ValueError:
                return False
            raw_nodes.add(canonical_raw)

        compatible_edges=[]
        conflict_relations=0
        seen_pairs=set()
        for rel in pairwise:
            if not isinstance(rel,Mapping):
                return False
            left_sid=str(rel.get("left_stream_id") or "")
            right_sid=str(rel.get("right_stream_id") or "")
            left_raw=str(rel.get("left_raw_sha256") or "")
            right_raw=str(rel.get("right_raw_sha256") or "")
            if not left_sid or not right_sid or left_sid==right_sid:
                return False
            for digest in (left_raw,right_raw):
                if len(digest)!=64:
                    return False
                try:
                    int(digest,16)
                except ValueError:
                    return False
            if left_raw==right_raw:
                return False
            raw_nodes.update((left_raw,right_raw))
            pair=tuple(sorted((left_raw,right_raw)))
            if pair in seen_pairs:
                return False
            seen_pairs.add(pair)

            nums={}
            for name in (
                "left_rows","right_rows","overlap_rows",
                "identical_overlap_rows","conflicting_overlap_rows",
            ):
                value=rel.get(name)
                if type(value) is not int or value < 0:
                    return False
                nums[name]=value
            conflicts=rel.get("conflict_event_ns")
            if not isinstance(conflicts,list) or any(type(x) is not int or x < 0 for x in conflicts):
                return False
            if len(conflicts)!=nums["conflicting_overlap_rows"]:
                return False
            if nums["overlap_rows"] != nums["identical_overlap_rows"] + nums["conflicting_overlap_rows"]:
                return False
            compatible=rel.get("compatible_same_lineage")
            boundary=rel.get("boundary_revision_only")
            if type(compatible) is not bool or type(boundary) is not bool:
                return False
            relation=str(rel.get("relation") or "")
            if relation=="OVERLAP_CONFLICT":
                conflict_relations += 1
                if compatible:
                    return False
            if relation=="DISJOINT" and compatible:
                return False
            if compatible:
                compatible_edges.append((left_raw,right_raw))

        unique=counts["unique_raw_stream_count"]
        if unique==1 and not raw_nodes and canonical_raw:
            raw_nodes.add(canonical_raw)
        if unique != len(raw_nodes):
            return False
        if len(pairwise) != unique*(unique-1)//2:
            return False
        if counts["unresolved_conflict_count"] != conflict_relations:
            return False

        components=_component_count(raw_nodes,compatible_edges)
        if counts["compatible_component_count"] != components:
            return False

        status=row.get("status")
        if status=="SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED":
            resolved_count += 1
            if (
                unique < 1
                or components != 1
                or conflict_relations != 0
                or counts["independent_view_count"] != 0
                or row.get("canonicalization_allowed") is not True
                or not row.get("canonical_stream_id")
                or not canonical_raw
            ):
                return False
        elif status=="UNRESOLVED_REPRESENTATION_IDENTITY":
            if row.get("canonicalization_allowed") is not False:
                return False
            if counts["independent_view_count"] != unique:
                return False
        else:
            return False

    if len(set(ids)) != len(ids):
        return False
    return (
        type(body.get("candidate_count")) is int
        and type(body.get("resolved_count")) is int
        and type(body.get("unresolved_count")) is int
        and body["candidate_count"]==len(rows)
        and body["resolved_count"]==resolved_count
        and body["unresolved_count"]==len(rows)-resolved_count
    )


def resolution_by_candidate_id(payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("resolutions", []):
        if isinstance(row, Mapping) and row.get("candidate_id"):
            out[str(row["candidate_id"])] = dict(row)
    return out
