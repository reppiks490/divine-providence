import csv
import json
import zipfile
from pathlib import Path

from nexus.research_loop import AdvancedCSVResearchLoop, AdvancedLoopConfig, CoverageAnchor


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
    assert r1.summary["coverage_claim_allowed"] is True
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
    assert "native completion boundaries" in contract["native_clock_rule"]
    assert result.summary["production_authorized"] is False
