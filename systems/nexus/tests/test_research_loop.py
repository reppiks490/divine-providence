import csv
import json
import zipfile
from pathlib import Path

from nexus.research_loop import AdvancedCSVResearchLoop, AdvancedLoopConfig, CoverageAnchor, _digest


def _write_zip(path: Path) -> None:
    rows = [
        ["time", "open", "high", "low", "close", "Volume"],
        [1700000000, 100, 101, 99, 100, 10],
        [1700000060, 100, 102, 100, 101, 11],
        [1700000120, 101, 103, 101, 102, 12],
        [1700000180, 102, 104, 102, 103, 13],
    ]
    text = "\n".join(",".join(map(str, r)) for r in rows) + "\n"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sample/BATS_TEST, 1.csv", text)
        zf.writestr("sample/._BATS_TEST, 1.csv", "appledouble")


def test_loop_runs_and_resumes(tmp_path):
    archive = tmp_path / "corpus.zip"
    _write_zip(archive)
    state = tmp_path / "state"
    cfg = AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test", 1, 4),
        min_owner_expected_entries=1,
        min_returns_for_behavior_candidate=2,
    )
    loop = AdvancedCSVResearchLoop(tmp_path, cfg)
    r1 = loop.run_once()
    assert r1.iteration == 1
    assert r1.summary["usable_entries"] == 1
    assert r1.summary["production_authorized"] is False
    assert r1.summary["historical_checkpoint_reconciled"] is True
    assert r1.summary["coverage_claim_allowed"] is False
    r2 = loop.run_once()
    assert r2.iteration == 2
    assert r2.corpus_manifest_hash == r1.corpus_manifest_hash
    assert r2.summary["delta"]["corpus_changed"] is False
    assert r2.summary["stability"]["same_corpus_reproducible"] is True
    assert r2.summary["stability"]["unexpected_nondeterminism"] is False
    assert r2.summary["stability"]["changed_core_artifact_count"] == 0
    assert r2.summary["stability"]["new_research_candidates"] == 0
    assert r2.summary["stability"]["resolved_research_candidates"] == 0
    stability = json.loads((state / "iteration_0002" / "stability_report.json").read_text())
    assert stability["research_candidates"]["persistent_count"] == r2.summary["research_candidate_count"]
    s = json.loads(Path(r2.state_path).read_text())
    assert s["status"] == "completed"
    assert s["production_authorized"] is False
    assert s["paths_relative_to_state_dir"] is True
    assert s["latest_iteration_dir"] == "iteration_0002"
    assert s["latest_summary_path"] == "iteration_0002/iteration_summary.json"
    assert len(s["state_hash"]) == 64
    assert r2.summary["corpus_manifest_hash"] == r2.corpus_manifest_hash


def test_loop_handoff_never_relabels_scanned_history_as_pristine(tmp_path):
    archive = tmp_path / "corpus.zip"
    _write_zip(archive)
    state = tmp_path / "state"
    cfg = AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test", 1, 4),
        min_owner_expected_entries=1,
        min_returns_for_behavior_candidate=2,
        persistence_abs_threshold=0.0,
    )
    result = AdvancedCSVResearchLoop(tmp_path, cfg).run_once()
    handoff = json.loads((state / "iteration_0001" / "daedalus_validation_handoff.json").read_text())
    assert handoff["production_authorized"] is False
    assert handoff["protected_holdout_spent"] is False
    assert handoff["discovery_evidence_policy"]["current_history_selection_contaminated"] is True
    assert handoff["discovery_evidence_policy"]["pristine_protected_holdout_available_inside_same_scanned_files"] is False
    assert result.summary["production_authorized"] is False
    for row in handoff["candidates"]:
        assert row["production_authorized"] is False
        assert row["route"]["protected_holdout_eligible_on_current_history"] is False
        if row["candidate"]["family"] in {"return_persistence", "return_reversal", "regime_volatility_shift"}:
            assert row["route"]["route"] == "DAEDALUS_DEVELOPMENT_ONLY"
            assert row["clean_confirmation_rule"]["current_source_history_is_pristine"] is False


def test_event_or_transformed_representation_never_becomes_fixed_cadence_gap_candidate():
    from nexus.contracts import StreamIdentity, StreamManifest
    from nexus.research_loop import StreamSweep, _build_candidates
    from collections import Counter

    ident = StreamIdentity("zipcsv", "CBOE", "VXN", "1", "csv_export", "x.csv", "a" * 64)
    manifest = StreamManifest(
        ident, 1000, ["time", "open", "high", "low", "close"],
        0, 1_000_000_000, 1_000_000, 0.7, 0, 0, 100,
        quality_flags=["claim_mismatch", "fractional_time"],
        metadata={"representation_hypothesis": {"kind": "event_or_transformed_candidate", "confidence": 0.8}},
    )
    sweep = StreamSweep(
        stream_id=ident.stream_id, symbol="VXN", venue="CBOE", source_path="x.csv",
        row_count=1000, usable_close_rows=1000, return_count=999,
        mean_log_return=0.0, std_log_return=0.01, lag1_return_corr=0.0,
        sign_persistence=0.5, efficiency_ratio=0.1, mean_range_fraction=0.01,
        gap_rate=0.5, first_half_return_std=0.01, second_half_return_std=0.01,
        regime_vol_ratio=1.0, volume_nonmissing_fraction=None, quality_score=1.0, admitted=True,
    )
    cfg = AdvancedLoopConfig(state_dir="unused", prior_anchor=CoverageAnchor("test", 1, 1), min_owner_expected_entries=1)
    out = _build_candidates(
        [manifest], [sweep], config=cfg, usable_entries=1, usable_rows=1000,
        admitted_count=1, review_counts=Counter(),
    )
    assert all(c.family != "sampling_gap_sensitivity" for c in out)


def test_loop_emits_representation_aggregation_contract(tmp_path):
    archive = tmp_path / "corpus.zip"
    _write_zip(archive)
    state = tmp_path / "state"
    cfg = AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test", 1, 4),
        min_owner_expected_entries=1,
    )
    result = AdvancedCSVResearchLoop(tmp_path, cfg).run_once()
    universe = json.loads((state / "iteration_0001" / "factor_universe.json").read_text())
    contract = universe["representation_aggregation_contract"]
    assert contract["raw_representations_are_independent_votes"] is False
    assert contract["required_engine"] == "HierarchicalFactorEngine.build_from_manifests"
    assert contract["orthogonal_identity_axes"] == [
        "chart_view_family", "price_geometry", "sampling_domain", "sampling_construction"
    ]
    assert "native completion boundaries" in contract["native_clock_rule"]
    assert result.summary["production_authorized"] is False


def test_loop_owner_exclusions_do_not_enter_model_admitted_plane(tmp_path):
    archive=tmp_path/"corpus.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        text="time,open,high,low,close\n1700000000,1,2,0,1\n1700000060,1,2,0,1.1\n1700000120,1.1,2,1,1.2\n"
        zf.writestr("INDEX_ETHUSD, 1.csv",text)
        zf.writestr("CME_MINI_NQ1!, 1.csv",text)
    state=tmp_path/"state"
    cfg=AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test",2,6),
        min_owner_expected_entries=2,
        min_returns_for_behavior_candidate=2,
    )
    result=AdvancedCSVResearchLoop(tmp_path,cfg).run_once()
    assert result.summary["owner_excluded_stream_count"]==1
    assert result.summary["model_admitted_entries_after_owner_exclusions"]==1
    universe=json.loads((state/"iteration_0001"/"factor_universe.json").read_text())
    blocked=[d for d in universe["decisions"] if d["reason"]=="owner_excluded_symbol"]
    assert len(blocked)==1
    assert blocked[0]["symbol"]=="ETHUSD"


def test_checkpoint_counts_never_auto_authorize_coverage(tmp_path):
    archive = tmp_path / "corpus.zip"
    _write_zip(archive)
    state = tmp_path / "state"
    cfg = AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test", 1, 4),
        min_owner_expected_entries=1,
    )
    result = AdvancedCSVResearchLoop(tmp_path, cfg).run_once()
    assert result.summary["historical_checkpoint_reconciled"] is True
    assert result.summary["coverage_claim_allowed"] is False
    universe = json.loads((state / "iteration_0001" / "factor_universe.json").read_text())
    assert universe["selected_stream_ids_are_independent_components"] is False
    assert universe["model_plane_ready"] is False


def _make_completed_loop(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    archive=tmp_path/"corpus.zip"
    _write_zip(archive)
    state=tmp_path/"state"
    cfg=AdvancedLoopConfig(
        state_dir=str(state),
        prior_anchor=CoverageAnchor("test",1,4),
        min_owner_expected_entries=1,
        min_returns_for_behavior_candidate=2,
    )
    loop=AdvancedCSVResearchLoop(tmp_path,cfg)
    result=loop.run_once()
    return loop,result,state


def test_loop_resume_rejects_tampered_state_summary_and_artifact(tmp_path):
    import pytest

    loop,_,state=_make_completed_loop(tmp_path/"state-case")
    state_path=state/"loop_state.json"
    body=json.loads(state_path.read_text())
    body["iteration"]=99
    state_path.write_text(json.dumps(body))
    with pytest.raises(RuntimeError,match="state_hash mismatch"):
        loop.run_once()

    loop,_,state=_make_completed_loop(tmp_path/"summary-case")
    summary=state/"iteration_0001"/"iteration_summary.json"
    body=json.loads(summary.read_text())
    body["usable_rows"]+=1
    summary.write_text(json.dumps(body))
    with pytest.raises(RuntimeError,match="summary hash mismatch"):
        loop.run_once()

    loop,_,state=_make_completed_loop(tmp_path/"artifact-case")
    artifact=state/"iteration_0001"/"research_queue.json"
    body=json.loads(artifact.read_text())
    body["production_authorized"]=True
    artifact.write_text(json.dumps(body))
    with pytest.raises(RuntimeError,match="artifact failed hash verification"):
        loop.run_once()


def test_loop_resume_rejects_path_escape_even_with_resealed_state(tmp_path):
    import pytest
    loop,_,state=_make_completed_loop(tmp_path)
    state_path=state/"loop_state.json"
    body=json.loads(state_path.read_text())
    body["latest_summary_path"]="../outside.json"
    body.pop("state_hash",None)
    body["state_hash"]=_digest(body)
    state_path.write_text(json.dumps(body))
    with pytest.raises(RuntimeError,match="escapes state_dir"):
        loop.run_once()


def test_loop_resume_migrates_verified_legacy_unsealed_state(tmp_path):
    loop,_,state=_make_completed_loop(tmp_path)
    state_path=state/"loop_state.json"
    body=json.loads(state_path.read_text())
    body.pop("state_hash",None)
    state_path.write_text(json.dumps(body))
    second=loop.run_once()
    assert second.iteration==2
    migrated=json.loads(state_path.read_text())
    assert len(migrated["state_hash"])==64
