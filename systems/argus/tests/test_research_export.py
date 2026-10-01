from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import EvidenceTier
from argus.orderblock_lifecycle import OrderBlockState
from argus.orderblock_study import (
    OrderBlockStudySubject,
    create_prospective_manifest,
    create_prospective_manifest_v2,
    lock_study_cohort,
)
from argus.orderblock_survival import OrderBlockSurvivalRecord
from argus.research_export import export_registered_survival_uncertainty


REVISION = "argus-orderblock-lifecycle:ebab6ea2"


def record(block_id, *, duration, invalidated):
    return OrderBlockSurvivalRecord(
        block_id=block_id,
        direction=1,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        duration_ns=duration,
        invalidated=invalidated,
        test_count=1,
        rejection_count=0,
        max_penetration_fraction=0.2,
        terminal_state=(
            OrderBlockState.INVALIDATED
            if invalidated
            else OrderBlockState.EXPIRED
        ),
    )


def subject(block_id, *, duration, invalidated, confirmation):
    return OrderBlockStudySubject(
        record=record(
            block_id,
            duration=duration,
            invalidated=invalidated,
        ),
        asset_id="NQ",
        confirmation_time_ns=confirmation,
        lifecycle_revision=REVISION,
    )


def study(alpha=0.05):
    manifest = create_prospective_manifest_v2(
        study_name="athena-bridge-study",
        created_time_ns=90,
        cohort_start_ns=100,
        cohort_end_ns=200,
        followup_cutoff_ns=300,
        lifecycle_revision=REVISION,
        asset_ids=("NQ",),
        evidence_tiers=(EvidenceTier.TRUE_DEPTH,),
        directions=(1,),
        analysis_horizon_ns=50,
        confidence_alpha=alpha,
    )
    cohort = lock_study_cohort(
        manifest,
        (
            subject(
                "event",
                duration=20,
                invalidated=True,
                confirmation=120,
            ),
            subject(
                "censor",
                duration=30,
                invalidated=False,
                confirmation=130,
            ),
            subject(
                "late",
                duration=100,
                invalidated=True,
                confirmation=140,
            ),
        ),
    )
    return manifest, cohort


def test_export_preserves_registered_study_and_authority_boundaries():
    manifest, cohort = study(alpha=0.01)

    packet = export_registered_survival_uncertainty(
        manifest,
        cohort,
        source_id="argus",
        representation_id="orderblock-survival",
        publication_time_ns=310,
        ingestion_time_ns=320,
    )

    assert packet["contract_version"] == "argus-athena-research-v1"
    assert packet["kind"] == "argus_orderblock_survival_uncertainty"
    assert packet["plane"] == "research"
    assert packet["event_time_ns"] == 300
    assert packet["available_ns"] == 310
    assert packet["ingestion_time_ns"] == 320
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["study_schema_version"] == "argus-orderblock-study-v2"
    assert packet["confidence_alpha"] == pytest.approx(0.01)
    assert packet["confidence_level"] == pytest.approx(0.99)
    assert packet["input_evidence_tiers"] == ["TRUE_DEPTH"]
    assert packet["records"] == 3
    assert packet["invalidations"] == 1
    assert packet["censored"] == 2
    assert packet["administrative_censored"] == 1
    assert packet["administrative_censored_block_ids"] == ["late"]
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False


def test_export_lineage_is_deterministic_and_identity_sensitive():
    manifest, cohort = study()
    kwargs = dict(
        source_id="argus",
        representation_id="orderblock-survival",
        publication_time_ns=310,
        ingestion_time_ns=320,
    )

    first = export_registered_survival_uncertainty(
        manifest,
        cohort,
        **kwargs,
    )
    second = export_registered_survival_uncertainty(
        manifest,
        cohort,
        **kwargs,
    )
    changed_representation = export_registered_survival_uncertainty(
        manifest,
        cohort,
        source_id="argus",
        representation_id="orderblock-survival-v2",
        publication_time_ns=310,
        ingestion_time_ns=320,
    )

    assert first["lineage_id"] == second["lineage_id"]
    assert first == second
    assert changed_representation["lineage_id"] != first["lineage_id"]


def test_export_never_claims_study_result_before_followup_cutoff():
    manifest, cohort = study()

    with pytest.raises(ValueError, match="follow-up cutoff"):
        export_registered_survival_uncertainty(
            manifest,
            cohort,
            source_id="argus",
            representation_id="orderblock-survival",
            publication_time_ns=299,
            ingestion_time_ns=320,
        )

    packet = export_registered_survival_uncertainty(
        manifest,
        cohort,
        source_id="argus",
        representation_id="orderblock-survival",
        publication_time_ns=300,
        ingestion_time_ns=300,
    )
    assert packet["event_time_ns"] == 300


def test_export_requires_ingestion_at_or_after_publication():
    manifest, cohort = study()

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_survival_uncertainty(
            manifest,
            cohort,
            source_id="argus",
            representation_id="orderblock-survival",
            publication_time_ns=310,
            ingestion_time_ns=309,
        )


def test_export_rejects_v1_study_and_tampered_v2_identity():
    v1 = create_prospective_manifest(
        study_name="legacy",
        created_time_ns=90,
        cohort_start_ns=100,
        cohort_end_ns=200,
        followup_cutoff_ns=300,
        lifecycle_revision=REVISION,
        asset_ids=("NQ",),
        evidence_tiers=(EvidenceTier.TRUE_DEPTH,),
        directions=(1,),
        analysis_horizon_ns=50,
    )
    v1_cohort = lock_study_cohort(
        v1,
        (
            subject(
                "legacy",
                duration=20,
                invalidated=True,
                confirmation=120,
            ),
        ),
    )
    with pytest.raises(ValueError, match="schema v2"):
        export_registered_survival_uncertainty(
            v1,
            v1_cohort,
            source_id="argus",
            representation_id="orderblock-survival",
            publication_time_ns=310,
            ingestion_time_ns=320,
        )

    manifest, cohort = study()
    tampered = replace(manifest, confidence_alpha=0.01)
    with pytest.raises(ValueError, match="manifest_id"):
        export_registered_survival_uncertainty(
            tampered,
            cohort,
            source_id="argus",
            representation_id="orderblock-survival",
            publication_time_ns=310,
            ingestion_time_ns=320,
        )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("source_id", "", "source_id"),
        ("source_id", " argus ", "source_id"),
        ("representation_id", "", "representation_id"),
        ("representation_id", " x ", "representation_id"),
        ("publication_time_ns", -1, "publication_time_ns"),
        ("ingestion_time_ns", -1, "ingestion_time_ns"),
    ],
)
def test_export_identity_and_clock_inputs_fail_closed(field, value, error):
    manifest, cohort = study()
    kwargs = dict(
        source_id="argus",
        representation_id="orderblock-survival",
        publication_time_ns=310,
        ingestion_time_ns=320,
    )
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=error):
        export_registered_survival_uncertainty(
            manifest,
            cohort,
            **kwargs,
        )
