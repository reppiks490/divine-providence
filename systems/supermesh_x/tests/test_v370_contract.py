from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def test_v370_manifest_docs_and_smoke_contract():
    manifest = (ROOT / "manifest.yaml").read_text()
    version = tuple(map(int, re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)\s*$", manifest, re.M).groups()))
    assert version >= (3, 7, 0)
    for capability in (
        "trust.witness_policy_expiry",
        "trust.trusted_time_contract",
        "trust.trusted_time_floor",
        "trust.freeze_guard",
    ):
        assert capability in manifest
    for rel in (
        "BUILD_REPORT_V370.md",
        "CHANGELOG_V370.md",
        "references/trusted-time-freeze-guard.md",
        "references/trusted-time-research-provenance.md",
    ):
        assert (ROOT / rel).exists()

    # Executable smoke must expose the v3.7 path, not merely document it.
    from scripts.smoke_check import run_checks
    result = run_checks()
    assert result["package_version"] == "3.7.0"
    assert result["checks"]["trusted_time_freeze_guard"] is True
