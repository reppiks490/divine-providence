from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import BookLevel, BookSnapshot
from argus.execution_evidence import (
    ExecutionEvidenceKind,
    calibrate_lineaged_impact,
    create_execution_evidence_receipt,
)
from argus.impact import depth_impact_curve
from argus.impact_calibration_load_cluster_transfer import (
    create_prospective_load_cluster_transfer_plan,
)
from argus.impact_calibration_overlap import (
    create_prospective_overlap_plan,
    registered_overlap_audit,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40

LOAD_BANDS = (
    ("low-load", 0.0, 0.30),
    ("high-load", 0.30, None),
)


def curve(*, visible_size, sequence):
    first = visible_size * 0.4
    second = visible_size - first
    book = BookSnapshot(
        event_time_ns=100,
        sequence=sequence,
        bids=(BookLevel(99.0, 10.0), BookLevel(98.0, 20.0)),
        asks=(BookLevel(101.0, first), BookLevel(102.0, second)),
    )
    return depth_impact_curve(
        book,
        side=1,
        sizes=(5.0,),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )


def receipt(
    kind,
    execution_id,
    *,
    run_id,
    decision,
    completion,
):
    kwargs = dict(
        evidence_kind=kind,
        source_system=(
            "example-broker"
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else "icarus-paper-emulator"
        ),
        source_repo=(
            "broker/example-adapter"
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else "reppiks490/Icarus"
        ),
        source_commit=(
            BROKER_COMMIT
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else ICARUS_COMMIT
        ),
        source_run_id=run_id,
        source_execution_id=execution_id,
        symbol="NQ",
        decision_time_ns=decision,
        completion_time_ns=completion,
        observed_time_ns=completion + 1,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.5,
        source_payload={
            "execution_id": execution_id,
            "run_id": run_id,
        },
    )
    if kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        kwargs.update(
            broker_name="Example Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )
    return create_execution_evidence_receipt(**kwargs)


def subject(
    kind,
    execution_id,
    *,
    run_id,
    visible_size,
    sequence,
    decision,
    completion,
):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(
                visible_size=visible_size,
                sequence=sequence,
            ),
            receipt(
                kind,
                execution_id,
                run_id=run_id,
                decision=decision,
                completion=completion,
            ),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def manifest():
    return create_impact_calibration_study_manifest(
        study_name="overlap-study",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        ),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=8,
        max_snapshot_age_ns=100,
        max_completion_latency_ns=100,
    )


def transfer_plan(m):
    metric = "mean_fill_fraction_error"
    return create_prospective_load_cluster_transfer_plan(
        m,
        created_time_ns=95,
        load_bands=LOAD_BANDS,
        metrics=(metric,),
        tolerances={
            ("low-load", metric): 1.0,
            ("high-load", metric): 1.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=2,
    )


def study():
    m = manifest()
    subjects = []
    sequence = 1

    # Low-load support is intentionally matched between broker and paper.
    low_times = (
        (120, 130),
        (120, 140),
        (130, 140),
        (130, 150),
    )
    for kind, prefix in (
        (ExecutionEvidenceKind.BROKER_CONFIRMED, "b"),
        (ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR, "p"),
    ):
        for i, (decision, completion) in enumerate(low_times):
            subjects.append(
                subject(
                    kind,
                    f"{prefix}-low-{i}",
                    run_id=f"{prefix}-low-run-{i // 2}",
                    visible_size=50.0,
                    sequence=sequence,
                    decision=decision,
                    completion=completion,
                )
            )
            sequence += 1

    # High-load broker evidence is fresh/fast; paper evidence is stale/slow.
    broker_high = (
        (120, 130),
        (120, 130),
        (130, 140),
        (130, 140),
    )
    paper_high = (
        (160, 200),
        (160, 200),
        (170, 220),
        (170, 220),
    )
    for i, (decision, completion) in enumerate(broker_high):
        subjects.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-high-{i}",
                run_id=f"b-high-run-{i // 2}",
                visible_size=10.0,
                sequence=sequence,
                decision=decision,
                completion=completion,
            )
        )
        sequence += 1

    for i, (decision, completion) in enumerate(paper_high):
        subjects.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-high-{i}",
                run_id=f"p-high-run-{i // 2}",
                visible_size=10.0,
                sequence=sequence,
                decision=decision,
                completion=completion,
            )
        )
        sequence += 1

    cohort = lock_impact_calibration_study_cohort(
        m,
        tuple(subjects),
        lock_time_ns=260,
    )
    return m, transfer_plan(m), cohort


def overlap_plan(
    m,
    transfer,
    *,
    max_tv=0.25,
    minimum=4,
):
    covariates = (
        "snapshot_age_ns",
        "completion_latency_ns",
    )
    return create_prospective_overlap_plan(
        m,
        transfer,
        created_time_ns=95,
        covariates=covariates,
        covariate_bins={
            "snapshot_age_ns": (
                (0.0, 40.0),
                (40.0, None),
            ),
            "completion_latency_ns": (
                (0.0, 20.0),
                (20.0, None),
            ),
        },
        max_total_variation={
            (band, covariate): max_tv
            for band, _, _ in LOAD_BANDS
            for covariate in covariates
        },
        min_observations_per_kind_per_band=minimum,
    )


def test_overlap_plan_is_prospective_content_addressed_and_deterministic():
    m, transfer, _ = study()
    first = overlap_plan(m, transfer)
    same = overlap_plan(m, transfer)
    changed = overlap_plan(m, transfer, max_tv=0.50)

    assert first == same
    assert first.plan_id.startswith("impact-calibration-overlap-plan:")
    assert first.schema_version == "argus-impact-calibration-overlap-plan-v1"
    assert first.load_cluster_transfer_plan_id == transfer.plan_id
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed.plan_id != first.plan_id


def test_overlap_audit_detects_high_load_covariate_shift():
    m, transfer, cohort = study()
    plan = overlap_plan(m, transfer)

    audit = registered_overlap_audit(
        plan,
        m,
        transfer,
        cohort,
    )
    rows = {
        (row.band_label, row.covariate): row
        for row in audit.results
    }

    low_snapshot = rows[("low-load", "snapshot_age_ns")]
    low_latency = rows[("low-load", "completion_latency_ns")]
    high_snapshot = rows[("high-load", "snapshot_age_ns")]
    high_latency = rows[("high-load", "completion_latency_ns")]

    assert low_snapshot.total_variation_distance == pytest.approx(0.0)
    assert low_latency.total_variation_distance == pytest.approx(0.0)
    assert low_snapshot.support_adequate is True
    assert low_latency.support_adequate is True

    assert high_snapshot.total_variation_distance == pytest.approx(1.0)
    assert high_latency.total_variation_distance == pytest.approx(1.0)
    assert high_snapshot.overlap_coefficient == pytest.approx(0.0)
    assert high_latency.overlap_coefficient == pytest.approx(0.0)
    assert high_snapshot.support_adequate is False
    assert high_latency.support_adequate is False
    assert audit.all_support_adequate is False

    for row in audit.results:
        assert row.broker_clusters == 2
        assert row.paper_clusters == 2
        assert sum(
            bin_.broker_probability for bin_ in row.bins
        ) == pytest.approx(1.0)
        assert sum(
            bin_.paper_probability for bin_ in row.bins
        ) == pytest.approx(1.0)
        assert row.execution_authorized is False
        assert row.production_decision_authorized is False


def test_overlap_plan_rejects_posthoc_or_non_exhaustive_design():
    m, transfer, _ = study()

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_overlap_plan(
            m,
            transfer,
            created_time_ns=111,
            covariates=("snapshot_age_ns",),
            covariate_bins={
                "snapshot_age_ns": ((0.0, None),),
            },
            max_total_variation={
                ("low-load", "snapshot_age_ns"): 0.5,
                ("high-load", "snapshot_age_ns"): 0.5,
            },
        )

    with pytest.raises(ValueError, match="contiguous"):
        create_prospective_overlap_plan(
            m,
            transfer,
            created_time_ns=95,
            covariates=("snapshot_age_ns",),
            covariate_bins={
                "snapshot_age_ns": (
                    (0.0, 10.0),
                    (20.0, None),
                ),
            },
            max_total_variation={
                ("low-load", "snapshot_age_ns"): 0.5,
                ("high-load", "snapshot_age_ns"): 0.5,
            },
        )

    with pytest.raises(ValueError, match="must be <= 1"):
        create_prospective_overlap_plan(
            m,
            transfer,
            created_time_ns=95,
            covariates=("snapshot_age_ns",),
            covariate_bins={
                "snapshot_age_ns": ((0.0, None),),
            },
            max_total_variation={
                ("low-load", "snapshot_age_ns"): 1.1,
                ("high-load", "snapshot_age_ns"): 0.5,
            },
        )


def test_overlap_minimum_is_enforced_inside_each_load_band():
    m, transfer, cohort = study()
    plan = overlap_plan(
        m,
        transfer,
        minimum=5,
    )

    with pytest.raises(
        ValueError,
        match="low-load overlap audit requires at least 5",
    ):
        registered_overlap_audit(
            plan,
            m,
            transfer,
            cohort,
        )


def test_overlap_rejects_cross_lineage_source_run_collision():
    other_commit = "3" * 40
    m = create_impact_calibration_study_manifest(
        study_name="overlap-source-run-collision",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        ),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
            ("broker/other-adapter", other_commit),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=4,
        max_snapshot_age_ns=100,
        max_completion_latency_ns=100,
    )

    def broker_subject(execution_id, repo, commit, run_id, sequence):
        receipt_value = create_execution_evidence_receipt(
            evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
            source_system="example-broker",
            source_repo=repo,
            source_commit=commit,
            source_run_id=run_id,
            source_execution_id=execution_id,
            symbol="NQ",
            decision_time_ns=120,
            completion_time_ns=130,
            observed_time_ns=140,
            side=1,
            requested_size=5.0,
            filled_size=5.0,
            average_price=101.5,
            source_payload={"fill_id": execution_id, "run_id": run_id},
            broker_name="Example Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )
        return ImpactCalibrationStudySubject(
            row=calibrate_lineaged_impact(
                curve(visible_size=50.0, sequence=sequence),
                receipt_value,
            ),
            impact_model_revision="impact-v1",
            calibration_revision="calibration-v1",
        )

    rows = (
        broker_subject(
            "b-low-a",
            "broker/example-adapter",
            BROKER_COMMIT,
            "reused-low-run",
            201,
        ),
        broker_subject(
            "b-low-b",
            "broker/other-adapter",
            other_commit,
            "reused-low-run",
            202,
        ),
        broker_subject(
            "b-high-a",
            "broker/example-adapter",
            BROKER_COMMIT,
            "b-high-a",
            203,
        ),
        broker_subject(
            "b-high-b",
            "broker/example-adapter",
            BROKER_COMMIT,
            "b-high-b",
            204,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-a",
            run_id="p-low-a",
            visible_size=50.0,
            sequence=211,
            decision=120,
            completion=130,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-b",
            run_id="p-low-b",
            visible_size=50.0,
            sequence=212,
            decision=130,
            completion=140,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-a",
            run_id="p-high-a",
            visible_size=10.0,
            sequence=213,
            decision=120,
            completion=130,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-b",
            run_id="p-high-b",
            visible_size=10.0,
            sequence=214,
            decision=130,
            completion=140,
        ),
    )
    cohort = lock_impact_calibration_study_cohort(
        m,
        rows,
        lock_time_ns=260,
    )
    metric = "mean_fill_fraction_error"
    transfer = create_prospective_load_cluster_transfer_plan(
        m,
        created_time_ns=95,
        load_bands=LOAD_BANDS,
        metrics=(metric,),
        tolerances={
            ("low-load", metric): 1.0,
            ("high-load", metric): 1.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=1,
        min_metric_observations_per_kind_per_band=2,
    )
    plan = create_prospective_overlap_plan(
        m,
        transfer,
        created_time_ns=95,
        covariates=("snapshot_age_ns",),
        covariate_bins={
            "snapshot_age_ns": ((0.0, None),),
        },
        max_total_variation={
            ("low-load", "snapshot_age_ns"): 1.0,
            ("high-load", "snapshot_age_ns"): 1.0,
        },
        min_observations_per_kind_per_band=2,
    )

    with pytest.raises(
        ValueError,
        match="source_run_id collision across execution-source lineage",
    ):
        registered_overlap_audit(
            plan,
            m,
            transfer,
            cohort,
        )


def test_overlap_plan_and_cohort_tampering_fail_closed():
    m, transfer, cohort = study()
    plan = overlap_plan(m, transfer)

    with pytest.raises(ValueError, match="plan_id"):
        registered_overlap_audit(
            replace(
                plan,
                min_observations_per_kind_per_band=3,
            ),
            m,
            transfer,
            cohort,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_overlap_audit(
            plan,
            m,
            transfer,
            replace(cohort, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different load-cluster"):
        registered_overlap_audit(
            replace(
                plan,
                load_cluster_transfer_plan_id="wrong",
            ),
            m,
            transfer,
            cohort,
        )


def test_overlap_plan_authority_escalation_is_rejected():
    m, transfer, cohort = study()
    plan = overlap_plan(m, transfer)

    with pytest.raises(ValueError, match="carries authority"):
        registered_overlap_audit(
            replace(plan, execution_authorized=True),
            m,
            transfer,
            cohort,
        )
