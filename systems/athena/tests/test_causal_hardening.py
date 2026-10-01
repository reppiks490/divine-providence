import pytest

from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal
from athena.learning import CompetenceMemory, OutcomeRecord


def prov(*, event=10, ingest=20, source="nexus", flags=()):
    return Provenance(
        event_time_ns=event,
        ingestion_time_ns=ingest,
        source_id=source,
        representation_id="market-state",
        version="v2",
        plane=DataPlane.RESEARCH,
        lineage_id=f"{source}:{event}:{ingest}",
        quality_flags=flags,
    )


def test_actual_ingestion_time_is_hard_replay_boundary():
    journal = AdvisoryJournal()
    journal.append(AdvisoryEvent(
        provenance=prov(event=10, ingest=30),
        kind="market_state",
        available_ns=20,
        payload={"trend": 0.4},
        sequence=1,
    ))
    assert journal.asof(20) == []
    assert journal.asof(29) == []
    assert len(journal.asof(30)) == 1


def test_sequence_gap_and_bad_quality_force_abstention_until_recovery():
    journal = AdvisoryJournal()
    journal.append(AdvisoryEvent(prov(event=10, ingest=20), "state", 20, {"x": 1}, 1))
    journal.append(AdvisoryEvent(prov(event=11, ingest=21), "state", 21, {"x": 2}, 3))
    assert journal.frame(21, max_age_ns=100)["abstain_required"] is True
    assert journal.frame(21, max_age_ns=100)["gap_sources"] == ["nexus"]

    journal.append(AdvisoryEvent(
        prov(event=12, ingest=22, flags=("provider_recovery",)),
        "state", 22, {"x": 3}, 4,
    ))
    recovered = journal.frame(22, max_age_ns=100)
    assert recovered["gap_sources"] == []
    assert recovered["abstain_required"] is False

    journal.append(AdvisoryEvent(
        prov(event=13, ingest=23, flags=("availability_unknown",)),
        "state", 23, {"x": 4}, 5,
    ))
    blocked = journal.frame(23, max_age_ns=100)
    assert blocked["abstain_required"] is True
    assert blocked["rejected"][0]["flags"] == ["availability_unknown"]
    assert journal.verify()["verified"] is True


def test_competence_waits_for_actual_recording_not_claimed_availability():
    memory = CompetenceMemory()
    memory.append(OutcomeRecord(
        "expert-a", 10, 20, 0.8, 1.0, "labels", True,
        state_id="trend", outcome_event_ns=15, recorded_ns=50, prediction_id="pred-1",
    ))
    assert memory.metrics(40, state_id="trend") == {}
    assert memory.metrics(50, state_id="trend")["expert-a"]["samples"] == 1


def test_prediction_identity_is_immutable_and_production_updates_are_blocked():
    memory = CompetenceMemory()
    original = OutcomeRecord(
        "expert-a", 10, 20, 0.8, 1.0, "labels", True,
        prediction_id="pred-1",
    )
    memory.append(original)
    assert memory.append(original) == original.record_id
    with pytest.raises(ValueError, match="different immutable"):
        memory.append(OutcomeRecord(
            "expert-a", 10, 20, -0.8, -1.0, "labels", True,
            prediction_id="pred-1",
        ))
    with pytest.raises(ValueError, match="research/shadow"):
        OutcomeRecord(
            "expert-a", 10, 20, 0.8, 1.0, "labels", True,
            prediction_id="prod", plane=DataPlane.PRODUCTION,
        )


def test_missing_ood_detector_fails_conservatively():
    memory = CompetenceMemory()
    memory.append(OutcomeRecord("expert-a", 10, 20, 1.0, 1.0, "labels", True))
    evidence = memory.expert_evidence(20, min_samples=1)
    assert evidence[0].ood_score == 1.0
    assert evidence[0].score == 1.0
