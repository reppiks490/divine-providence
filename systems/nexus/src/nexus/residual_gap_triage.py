from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass
from math import ceil
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping
import hashlib
import json
import zipfile

from .contracts import StreamManifest
from .session_semantics import _load_times, verify_session_gap_resolution


SCHEMA = "nexus.residual-gap-triage.v1"


@dataclass(frozen=True, slots=True)
class ResidualGapTriage:
    candidate_id: str
    stream_id: str
    symbol: str
    venue: str | None
    classification: str
    evidence_strength: str
    residual_gap_count: int
    comparable_gap_count: int
    gaps_with_sibling_activity: int
    gaps_with_shared_silence: int
    sibling_count: int
    sibling_stream_ids: tuple[str, ...]
    coverage_ratio: float
    sibling_activity_ratio: float | None
    median_gap_multiple: float | None
    p95_gap_multiple: float | None
    data_loss_asserted: bool = False
    production_authorized: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sibling_stream_ids"] = list(self.sibling_stream_ids)
        return d


def _quantile_nearest(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    i = min(len(xs) - 1, max(0, ceil(q * len(xs)) - 1))
    return float(xs[i])


def _stream_id(m: StreamManifest) -> str:
    return m.identity.stream_id


def _dedupe_siblings(rows: Iterable[StreamManifest]) -> list[StreamManifest]:
    """Keep one evidence stream per logical/raw content identity.

    Multiple downloads of the same content must never gain extra evidentiary weight.
    """
    out: list[StreamManifest] = []
    seen: set[str] = set()
    for m in sorted(
        rows,
        key=lambda x: (
            int(x.observed_cadence_ns or 2**63 - 1),
            -int(x.row_count),
            x.identity.stream_id,
        ),
    ):
        key = str(m.metadata.get("logical_sha256") or m.identity.raw_sha256 or m.identity.stream_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _eligible_siblings(target: StreamManifest, manifests: Iterable[StreamManifest]) -> list[StreamManifest]:
    cadence = int(target.observed_cadence_ns or 0)
    if cadence <= 0:
        return []
    rows: list[StreamManifest] = []
    for m in manifests:
        if m.identity.stream_id == target.identity.stream_id:
            continue
        if m.identity.symbol != target.identity.symbol or m.identity.venue != target.identity.venue:
            continue
        if m.row_count <= 0 or "appledouble" in m.quality_flags:
            continue
        mc = int(m.observed_cadence_ns or 0)
        if mc <= 0 or mc > cadence:
            continue
        # Exact/logical copies of the target cannot independently corroborate a gap.
        if m.identity.raw_sha256 and m.identity.raw_sha256 == target.identity.raw_sha256:
            continue
        target_logical=str(target.metadata.get("logical_sha256") or "")
        sibling_logical=str(m.metadata.get("logical_sha256") or "")
        if target_logical and sibling_logical and target_logical == sibling_logical:
            continue
        rows.append(m)
    deduped = _dedupe_siblings(rows)
    t0, t1 = target.first_event_ns, target.last_event_ns

    def overlap_ns(m: StreamManifest) -> int:
        if None in (t0, t1, m.first_event_ns, m.last_event_ns):
            return 0
        return max(0, min(int(t1), int(m.last_event_ns)) - max(int(t0), int(m.first_event_ns)))

    # Evidence that actually overlaps the target window is more useful than a finer
    # sibling from a disjoint snapshot. Cadence is the tie-breaker, not the primary key.
    return sorted(
        deduped,
        key=lambda m: (
            -overlap_ns(m),
            int(m.observed_cadence_ns or 2**63 - 1),
            -int(m.row_count),
            m.identity.stream_id,
        ),
    )[:5]


def _gap_metrics(gaps: list[tuple[int, int]], cadence_ns: int) -> tuple[float | None, float | None]:
    if cadence_ns <= 0:
        return None, None
    multiples = [(b - a) / cadence_ns for a, b in gaps if b > a]
    if not multiples:
        return None, None
    return float(median(multiples)), _quantile_nearest(multiples, 0.95)


def classify_residual_gaps(
    *,
    candidate_id: str,
    target: StreamManifest,
    residual_gaps: list[tuple[int, int]],
    sibling_times: Mapping[str, list[int]],
    siblings: Iterable[StreamManifest],
) -> ResidualGapTriage:
    """Classify residual open-session gaps using only sibling-observation evidence.

    A sibling observation inside a target gap proves same-symbol activity was represented
    somewhere else; it does *not* prove the target file lost data because chart/export
    construction and timestamp semantics can differ. Conversely, silence across siblings
    does not prove there were no trades. Both conclusions therefore remain diagnostics.
    """
    sibs = list(siblings)
    cadence = int(target.observed_cadence_ns or 0)
    comparable = activity = shared_silence = 0

    if not isinstance(candidate_id,str) or not candidate_id.strip():
        raise ValueError("candidate_id is required")
    if cadence <= 0:
        raise ValueError("target observed_cadence_ns must be positive")
    for a,b in residual_gaps:
        if type(a) is not int or type(b) is not int or a < 0 or b <= a:
            raise ValueError("residual gaps must be non-negative increasing integer pairs")

    prepared: list[tuple[StreamManifest, list[int]]] = []
    seen_time_signatures: set[str] = set()
    for sibling in sibs:
        raw_times=sibling_times.get(sibling.identity.stream_id, [])
        if any(type(x) is not int or x < 0 for x in raw_times):
            raise ValueError("sibling timestamps must be non-negative integers")
        times=sorted(set(raw_times))
        if not times:
            continue
        h=hashlib.sha256()
        for ts in times:
            h.update(int(ts).to_bytes(8,"big",signed=False))
        signature=h.hexdigest()
        if signature in seen_time_signatures:
            continue
        seen_time_signatures.add(signature)
        prepared.append((sibling, times))

    for previous_ns, next_ns in residual_gaps:
        covered = False
        any_activity = False
        for sibling, times in prepared:
            first = sibling.first_event_ns
            last = sibling.last_event_ns
            if first is None or last is None or previous_ns < first or next_ns > last:
                continue
            covered = True
            # Strictly inside the target gap; endpoints are already observed by target.
            left = bisect_right(times, previous_ns)
            right = bisect_left(times, next_ns)
            if left < right:
                any_activity = True
                break
        if not covered:
            continue
        comparable += 1
        if any_activity:
            activity += 1
        else:
            shared_silence += 1

    total = len(residual_gaps)
    coverage = comparable / total if total else 0.0
    activity_ratio = activity / comparable if comparable else None
    min_comparable = min(20, max(5, ceil(total * 0.05))) if total else 0

    if not prepared or comparable < min_comparable:
        strength = "LIMITED"
        if prepared and total and coverage < 0.20:
            classification = "INSUFFICIENT_TEMPORAL_SIBLING_COVERAGE"
            reason = (
                "Independent finer/equal-cadence same-symbol siblings exist, but they overlap too little of the target gap history "
                "to support a broad cross-resolution conclusion. Recover same-symbol evidence spanning the uncovered interval; "
                "keep the target gaps unresolved and do not infer data loss."
            )
        else:
            classification = "INSUFFICIENT_CROSS_RESOLUTION_EVIDENCE"
            reason = (
                "Too few residual gaps are covered by an independent finer/equal-cadence same-symbol sibling. "
                "Keep the gaps as unresolved data-quality/no-trade diagnostics."
            )
    elif activity_ratio is not None and activity_ratio >= 0.80:
        classification = "CROSS_RESOLUTION_ACTIVITY_PRESENT_DOMINANT"
        strength = "SUPPORTIVE"
        reason = (
            "Same-symbol sibling streams contain observations inside most comparable target gaps. "
            "This supports source/export-specific thinning, bar suppression, or representation differences, "
            "but does not by itself prove target-file data loss."
        )
    elif activity_ratio is not None and activity_ratio >= 0.20:
        classification = "MIXED_CROSS_RESOLUTION_ACTIVITY_AND_SHARED_SILENCE"
        strength = "SUPPORTIVE"
        reason = (
            "Sibling evidence is mixed: some target gaps contain same-symbol activity in another representation "
            "while others are silent across the reviewed siblings. Keep both mechanisms in the diagnostic set."
        )
    else:
        classification = "SHARED_SILENCE_DOMINANT"
        strength = "SUPPORTIVE"
        reason = (
            "Most comparable target gaps are also silent in reviewed finer/equal-cadence siblings. "
            "This is consistent with shared no-trade/source silence or common upstream sampling, not proof of complete data."
        )

    med, p95 = _gap_metrics(residual_gaps, cadence)
    return ResidualGapTriage(
        candidate_id=str(candidate_id),
        stream_id=target.identity.stream_id,
        symbol=target.identity.symbol,
        venue=target.identity.venue,
        classification=classification,
        evidence_strength=strength,
        residual_gap_count=total,
        comparable_gap_count=comparable,
        gaps_with_sibling_activity=activity,
        gaps_with_shared_silence=shared_silence,
        sibling_count=len(prepared),
        sibling_stream_ids=tuple(m.identity.stream_id for m, _ in prepared),
        coverage_ratio=float(coverage),
        sibling_activity_ratio=float(activity_ratio) if activity_ratio is not None else None,
        median_gap_multiple=med,
        p95_gap_multiple=p95,
        data_loss_asserted=False,
        production_authorized=False,
        reason=reason,
    )


def build_residual_gap_triage(
    corpus_root: str | Path,
    manifests: Iterable[StreamManifest],
    session_gap_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    if not verify_session_gap_resolution(session_gap_resolution):
        raise ValueError("invalid or tampered session-gap resolution artifact")
    root = Path(corpus_root)
    manifest_rows = list(manifests)
    grouped:dict[str,list[StreamManifest]]={}
    for m in sorted(manifest_rows,key=lambda x:(x.identity.stream_id,x.identity.source_path)):
        grouped.setdefault(m.identity.stream_id,[]).append(m)
    by_id:dict[str,StreamManifest]={}
    for sid,rows in grouped.items():
        hashes={m.identity.raw_sha256 for m in rows}
        if len(hashes)>1:
            raise ValueError(f"stream_id collision with different raw hashes: {sid}")
        by_id[sid]=rows[0]
    archive_cache: dict[str, zipfile.ZipFile] = {}
    time_cache: dict[str, list[int]] = {}

    def load(m: StreamManifest) -> list[int]:
        archive_rel = str(m.metadata.get("archive_path") or "")
        member = str(m.metadata.get("archive_member") or "")
        if not archive_rel or not member:
            return []
        key = f"{archive_rel}!{member}"
        if key in time_cache:
            return time_cache[key]
        zf = archive_cache.get(archive_rel)
        if zf is None:
            zf = zipfile.ZipFile(root / archive_rel)
            archive_cache[archive_rel] = zf
        times = _load_times(zf, member)
        time_cache[key] = times
        return times

    results: list[ResidualGapTriage] = []
    try:
        for row in session_gap_resolution.get("resolutions", []):
            if not isinstance(row, Mapping) or not row.get("residual_data_quality_diagnostic_required"):
                continue
            sid = str(row.get("stream_id") or "")
            target = by_id.get(sid)
            if target is None:
                raise ValueError(
                    f"session resolution references missing target manifest: {sid}"
                )
            gaps = [
                (int(g["previous_event_ns"]), int(g["next_event_ns"]))
                for g in row.get("gap_assessments", [])
                if isinstance(g, Mapping)
                and str(g.get("classification", "")).startswith("RESIDUAL_OPEN_SESSION_GAP")
            ]
            sibs = _eligible_siblings(target, manifest_rows)
            sibling_times = {m.identity.stream_id: load(m) for m in sibs}
            results.append(classify_residual_gaps(
                candidate_id=str(row.get("candidate_id") or ""),
                target=target,
                residual_gaps=gaps,
                sibling_times=sibling_times,
                siblings=sibs,
            ))
    finally:
        for zf in archive_cache.values():
            zf.close()

    counts: dict[str, int] = {}
    for r in results:
        counts[r.classification] = counts.get(r.classification, 0) + 1
    comparable = sum(r.comparable_gap_count for r in results)
    activity = sum(r.gaps_with_sibling_activity for r in results)
    body = {
        "schema": SCHEMA,
        "candidate_count": len(results),
        "classification_counts": dict(sorted(counts.items())),
        "total_residual_gap_count": sum(r.residual_gap_count for r in results),
        "cross_resolution_comparable_gap_count": comparable,
        "gaps_with_sibling_activity": activity,
        "aggregate_sibling_activity_ratio": (activity / comparable) if comparable else None,
        "data_loss_asserted": False,
        "production_authorized": False,
        "resolutions": [r.to_dict() for r in results],
    }
    body["triage_hash"]=hashlib.sha256(
        json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return body


def verify_residual_gap_triage(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload,Mapping) or payload.get("schema") != SCHEMA:
        return False
    supplied=payload.get("triage_hash")
    if not isinstance(supplied,str) or len(supplied)!=64:
        return False
    try:
        int(supplied,16)
    except ValueError:
        return False
    body=dict(payload);body.pop("triage_hash",None)
    try:
        expected=hashlib.sha256(
            json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        ).hexdigest()
    except (TypeError,ValueError):
        return False
    if supplied!=expected or body.get("data_loss_asserted") is not False or body.get("production_authorized") is not False:
        return False
    rows=body.get("resolutions")
    if not isinstance(rows,list):
        return False
    ids=[];counts={};total=comparable=activity=0
    for row in rows:
        if not isinstance(row,Mapping):
            return False
        cid=str(row.get("candidate_id") or "")
        if not cid or row.get("data_loss_asserted") is not False or row.get("production_authorized") is not False:
            return False
        ids.append(cid)
        classification=str(row.get("classification") or "")
        if not classification:
            return False
        counts[classification]=counts.get(classification,0)+1
        numeric_names=(
            "residual_gap_count","comparable_gap_count",
            "gaps_with_sibling_activity","gaps_with_shared_silence","sibling_count",
        )
        vals={}
        for name in numeric_names:
            value=row.get(name)
            if type(value) is not int or value < 0:
                return False
            vals[name]=value
        if vals["gaps_with_sibling_activity"]+vals["gaps_with_shared_silence"] != vals["comparable_gap_count"]:
            return False
        if vals["comparable_gap_count"] > vals["residual_gap_count"]:
            return False
        coverage=row.get("coverage_ratio")
        if not isinstance(coverage,(int,float)) or not 0.0 <= float(coverage) <= 1.0:
            return False
        expected_coverage=(
            vals["comparable_gap_count"]/vals["residual_gap_count"]
            if vals["residual_gap_count"] else 0.0
        )
        if abs(float(coverage)-expected_coverage)>1e-12:
            return False
        ratio=row.get("sibling_activity_ratio")
        expected_ratio=(
            vals["gaps_with_sibling_activity"]/vals["comparable_gap_count"]
            if vals["comparable_gap_count"] else None
        )
        if expected_ratio is None:
            if ratio is not None:
                return False
        elif ratio is None or abs(float(ratio)-expected_ratio)>1e-12:
            return False
        sibling_ids=row.get("sibling_stream_ids")
        if not isinstance(sibling_ids,list) or len(sibling_ids)!=vals["sibling_count"] or len(set(sibling_ids))!=len(sibling_ids):
            return False
        total+=vals["residual_gap_count"]
        comparable+=vals["comparable_gap_count"]
        activity+=vals["gaps_with_sibling_activity"]
    if len(set(ids))!=len(ids):
        return False
    aggregate=body.get("aggregate_sibling_activity_ratio")
    expected_aggregate=activity/comparable if comparable else None
    if expected_aggregate is None:
        if aggregate is not None:
            return False
    elif aggregate is None or abs(float(aggregate)-expected_aggregate)>1e-12:
        return False
    return (
        body.get("candidate_count")==len(rows)
        and body.get("classification_counts")==dict(sorted(counts.items()))
        and body.get("total_residual_gap_count")==total
        and body.get("cross_resolution_comparable_gap_count")==comparable
        and body.get("gaps_with_sibling_activity")==activity
    )
