from pathlib import Path


def test_v240_manifest_preserves_v230_and_adds_durable_isolation_contracts():
    text = Path("manifest.yaml").read_text()
    version_line = next(line for line in text.splitlines() if line.startswith("version:"))
    version = tuple(int(part) for part in version_line.split(":", 1)[1].strip().split("."))
    assert version >= (2, 4, 0)
    assert "compatibility_baseline: 0.3.0" in text
    for capability in (
        "execution.domain",
        "execution.fencing",
        "execution.durable_store",
        "execution.cas",
        "execution.lifecycle",
        "execution.crash_recovery",
        "execution.isolation_admission",
        "execution.resource_reservation",
        "permissions.credential_reference_guard",
    ):
        assert capability in text


def test_v240_docs_keep_computers_and_swarm_deferred():
    text = Path("references/durable-execution-isolation.md").read_text()
    assert "does **not** launch computers or agents" in text
    assert "50+ logical-agent" in text
    assert "raw checkpoint state" in text
    assert "secretref://" in text
