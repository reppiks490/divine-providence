from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_v360_manifest_and_documentation_contract():
    manifest = (ROOT / "manifest.yaml").read_text()
    version = tuple(map(int, re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)\s*$", manifest, re.M).groups()))
    assert version >= (3, 6, 0)
    for capability in (
        "trust.gossip_compaction_snapshot",
        "trust.gossip_compaction_anchor",
        "trust.gossip_compaction_external_pin",
    ):
        assert capability in manifest
    for rel in (
        "BUILD_REPORT_V360.md",
        "CHANGELOG_V360.md",
        "references/gossip-compaction.md",
    ):
        assert (ROOT / rel).exists()
