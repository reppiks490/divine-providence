import pytest

from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryJournal, AdvisoryEvent
from athena.learning import CompetenceMemory, OutcomeRecord


def provenance(event=10, ingest=12, source="nexus", representation="market-state"):
    return Provenance(
        event_time_ns=event,
        ingestion_time_ns=ingest,
        source_id=source,
        representation_id=representation,
        version="v1",
        plane=DataPlane.RESEARCH,
        lineage_id=f"{source}:{event}",
    )


def test_advisory_journal_hides_future_evidence_and_abstains_on_stale():
    journal = AdvisoryJournal()
    event = AdvisoryEvent(
        provenance=provenance(event=10, ingest=20),
        kind="market_state",
        available_ns=20,
        payload={"trend": 0.4},
        sequence=1,
    )
    first = journal.append(event)
    assert first["idempotent"] is False
    assert journal.append(event)["idempotent"] is True
    assert journal.asof(19) == []
    frame = journal.frame(20, max_age_ns=5)
    assert frame["abstain_required"] is False
    assert frame["production_authorized"] is False
    stale = journal.frame(30, max_age_ns=5)
    assert stale["abstain_required"] is True
    assert stale["stale"][0]["age_ns"] == 10
    assert journal.verify()["verified"] is True


def test_advisory_journal_rejects_backwards_sequence_and_clock_claims():
    journal = AdvisoryJournal()
    journal.append(AdvisoryEvent(
        provenance=provenance(event=10, ingest=12),
        kind="state",
        available_ns=12,
        payload={"x": 1},
        sequence=2,
    ))
    with pytest.raises(ValueError, match="increase"):
        journal.append(AdvisoryEvent(
            provenance=provenance(event=11, ingest=13),
            kind="state",
            available_ns=13,
            payload={"x": 2},
            sequence=1,
        ))
    with pytest.raises(ValueError, match="availability cannot follow ingestion"):
        AdvisoryEvent(
            provenance=provenance(event=10, ingest=11),
            kind="state",
            available_ns=12,
            payload={},
        )


def test_competence_memory_does_not_leak_future_or_unverified_outcomes():
    memory = CompetenceMemory()
    memory.append(OutcomeRecord("expert-a", 10, 20, 0.8, 1.0, "verified-labels", True))
    memory.append(OutcomeRecord("expert-a", 20, 30, -0.8, -1.0, "unverified-labels", False))
    memory.append(OutcomeRecord("expert-a", 30, 40, 0.5, 1.0, "verified-labels", True))

    assert memory.metrics(19) == {}
    at_25 = memory.metrics(25, min_samples=2)["expert-a"]
    assert at_25["samples"] == 1
    assert at_25["ready"] is False
    assert at_25["production_authorized"] is False

    at_35 = memory.metrics(35, min_samples=2)["expert-a"]
    assert at_35["samples"] == 1
    assert at_35["ready"] is False

    at_40 = memory.metrics(40, min_samples=2)["expert-a"]
    assert at_40["samples"] == 2
    assert at_40["ready"] is True
    assert 0 <= at_40["calibration_error"] <= 1
    assert 0 <= at_40["score"] <= 1


def test_competence_evidence_is_deterministic_and_state_scoped():
    memory = CompetenceMemory()
    rows = [
        OutcomeRecord("a", 1, 2, 1, 1, "labels", True),
        OutcomeRecord("a", 2, 3, -1, -1, "labels", True),
        OutcomeRecord("b", 1, 2, 1, -1, "labels", True),
        OutcomeRecord("b", 2, 3, -1, 1, "labels", True),
    ]
    for row in reversed(rows):
        memory.append(row)

    evidence = memory.expert_evidence(
        3,
        supported_states={"a": ("trend",), "b": ("range",)},
        ood_scores={"a": 0.1, "b": 0.2},
        min_samples=2,
    )
    assert [x.expert_id for x in evidence] == ["a", "b"]
    assert evidence[0].score > evidence[1].score
    assert evidence[0].supported_states == ("trend",)
    assert evidence[0].recent_health == 1.0


def test_outcome_must_arrive_after_decision():
    with pytest.raises(ValueError, match="after the decision"):
        OutcomeRecord("a", 10, 10, 0.0, 0.0, "labels", True)
