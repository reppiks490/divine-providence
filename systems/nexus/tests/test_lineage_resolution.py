import zipfile
from pathlib import Path

from nexus.contracts import StreamIdentity, StreamManifest
from nexus.lineage_resolution import (
    build_representation_lineage_resolution,
    verify_representation_lineage_resolution,
)


def _manifest(raw_hash: str, member: str, rows: int) -> StreamManifest:
    ident = StreamIdentity(
        source_id="zipcsv", venue="CME", symbol="TEST", filename_claim="1",
        representation="csv_export", source_path=f"corpus.zip!{member}", raw_sha256=raw_hash,
    )
    return StreamManifest(
        identity=ident, row_count=rows, columns=["time", "open", "high", "low", "close"],
        first_event_ns=1_000_000_000, last_event_ns=rows * 1_000_000_000,
        observed_cadence_ns=1_000_000_000, cadence_confidence=1.0,
        repeated_timestamp_count=0, backward_timestamp_count=0, fractional_timestamp_count=0,
        metadata={"archive_path": "corpus.zip", "archive_member": member},
    )


def _candidate(manifests):
    return {
        "candidate_id": "rep", "family": "representation_family_disagreement",
        "priority": "P1", "score": 1.0,
        "scope": [m.identity.stream_id for m in manifests],
        "rationale": "x", "required_next_test": "y",
    }


def _write(zf, member, rows):
    text = "time,open,high,low,close\n"
    text += "\n".join(",".join(map(str, r)) for r in rows) + "\n"
    zf.writestr(member, text)


def test_subset_exports_resolve_to_one_copy_lineage(tmp_path: Path):
    a = _manifest("a" * 64, "a.csv", 3)
    b = _manifest("b" * 64, "b.csv", 5)
    with zipfile.ZipFile(tmp_path / "corpus.zip", "w") as zf:
        _write(zf, "a.csv", [[2, 10, 11, 9, 10], [3, 11, 12, 10, 11], [4, 12, 13, 11, 12]])
        _write(zf, "b.csv", [[1, 9, 10, 8, 9], [2, 10, 11, 9, 10], [3, 11, 12, 10, 11], [4, 12, 13, 11, 12], [5, 13, 14, 12, 13]])
    out = build_representation_lineage_resolution(tmp_path, [a, b], [_candidate([a, b])])
    assert verify_representation_lineage_resolution(out)
    row = out["resolutions"][0]
    assert row["status"] == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED"
    assert row["canonical_stream_id"] == b.identity.stream_id
    assert row["independent_view_count"] == 0
    assert row["fusion_as_independent_views_allowed"] is False


def test_terminal_snapshot_revision_is_compatible_but_interior_revision_is_not(tmp_path: Path):
    base_rows = [[i, 100 + i, 101 + i, 99 + i, 100 + i] for i in range(1, 302)]
    a_rows = [list(r) for r in base_rows[1:301]]
    b_rows = [list(r) for r in base_rows]
    a = _manifest("a" * 64, "a.csv", len(a_rows))
    b = _manifest("b" * 64, "b.csv", len(b_rows))
    # Difference occurs only on A's terminal snapshot row.
    b_rows[300 - 0][2] += 0.5
    with zipfile.ZipFile(tmp_path / "corpus.zip", "w") as zf:
        _write(zf, "a.csv", a_rows)
        _write(zf, "b.csv", b_rows)
    out = build_representation_lineage_resolution(tmp_path, [a, b], [_candidate([a, b])])
    assert out["resolutions"][0]["status"] == "SAME_REPRESENTATION_COPY_LINEAGE_RESOLVED"
    assert out["resolutions"][0]["pairwise_relations"][0]["boundary_revision_only"] is True

    # Move the disagreement into the interior; this must fail closed.
    b_rows = [list(r) for r in base_rows]
    b_rows[150][2] += 50
    with zipfile.ZipFile(tmp_path / "corpus.zip", "w") as zf:
        _write(zf, "a.csv", a_rows)
        _write(zf, "b.csv", b_rows)
    out = build_representation_lineage_resolution(tmp_path, [a, b], [_candidate([a, b])])
    assert out["resolutions"][0]["status"] == "UNRESOLVED_REPRESENTATION_IDENTITY"
    assert out["resolutions"][0]["unresolved_conflict_count"] == 1


def test_lineage_resolution_seal_detects_tampering(tmp_path: Path):
    a=_manifest("a"*64,"a.csv",2)
    with zipfile.ZipFile(tmp_path/"corpus.zip","w") as zf:
        _write(zf,"a.csv",[[1,1,2,0,1],[2,2,3,1,2]])
    out=build_representation_lineage_resolution(
        tmp_path,[a],[_candidate([a])]
    )
    assert verify_representation_lineage_resolution(out)
    tampered=dict(out)
    tampered["resolved_count"]=999
    assert not verify_representation_lineage_resolution(tampered)


def test_empty_scope_cannot_resolve_copy_lineage(tmp_path: Path):
    candidate={
        "candidate_id":"missing","family":"representation_family_disagreement",
        "scope":["not-present"],"priority":"P1","score":1.0,
        "rationale":"x","required_next_test":"y",
    }
    out=build_representation_lineage_resolution(tmp_path,[],[candidate])
    row=out["resolutions"][0]
    assert row["status"]=="UNRESOLVED_REPRESENTATION_IDENTITY"
    assert row["canonical_stream_id"] is None
    assert verify_representation_lineage_resolution(out)


def test_lineage_verifier_rejects_rehashed_impossible_graph(tmp_path: Path):
    import hashlib,json
    a=_manifest("a"*64,"a.csv",3)
    b=_manifest("b"*64,"b.csv",3)
    with zipfile.ZipFile(tmp_path/"corpus.zip","w") as zf:
        rows=[[1,1,2,0,1],[2,2,3,1,2],[3,3,4,2,3]]
        _write(zf,"a.csv",rows);_write(zf,"b.csv",rows)
    out=build_representation_lineage_resolution(tmp_path,[a,b],[_candidate([a,b])])
    assert verify_representation_lineage_resolution(out)
    broken=dict(out); rows=[dict(x) for x in broken["resolutions"]]
    rows[0]["compatible_component_count"]=2
    broken["resolutions"]=rows
    broken.pop("resolution_hash")
    broken["resolution_hash"]=hashlib.sha256(
        json.dumps(broken,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    assert not verify_representation_lineage_resolution(broken)
