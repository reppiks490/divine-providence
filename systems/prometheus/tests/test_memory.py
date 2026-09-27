from prometheus_loop.contracts import RejectedHypothesis
from prometheus_loop.memory.store import ResearchMemory


def rejected(experiment_id="experiment:abc"):
    return RejectedHypothesis(
        experiment_id=experiment_id,
        reason="Known brittle candidate.",
        evidence_ids=("replay:1",),
    )


def test_append_and_reload_preserves_artifact_identity(tmp_path):
    path = tmp_path / "memory.jsonl"
    memory = ResearchMemory(path)
    artifact = rejected()
    assert memory.append(artifact) is True
    reloaded = ResearchMemory(path)
    record = reloaded.find_by_id(artifact.artifact_id)
    assert record["artifact_id"] == artifact.artifact_id
    assert record["payload"]["reason"] == "Known brittle candidate."


def test_duplicate_artifact_write_is_idempotent(tmp_path):
    path = tmp_path / "memory.jsonl"
    memory = ResearchMemory(path)
    artifact = rejected()
    assert memory.append(artifact) is True
    before = path.read_text()
    assert memory.append(artifact) is False
    assert path.read_text() == before


def test_negative_result_is_searchable_by_experiment_id(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.jsonl")
    artifact = rejected("experiment:known-bad")
    memory.append(artifact)
    assert memory.has_negative("experiment:known-bad") is True
    prior = memory.negative_for("experiment:known-bad")
    assert prior.experiment_id == "experiment:known-bad"
    assert prior.reason == "Known brittle candidate."
