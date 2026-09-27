import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.cross_runtime_vectors import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_node_verifies_v37_anchor_fixture_and_matches_python_canonical_bytes():
    node = shutil.which("node")
    if not node:
        pytest.skip("node runtime unavailable")
    fixture_path = ROOT/"conformance"/"v37_anchor_fixture.json"
    fixture = json.loads(fixture_path.read_text())
    expected = bytes.fromhex(fixture["canonical_hex"])
    assert canonical_json_bytes(fixture["statement"]) == expected
    proc = subprocess.run(
        [node, str(ROOT/"scripts"/"verify_v37_fixture.mjs"), str(fixture_path)],
        text=True, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out == {"canonical_match": True, "digest_match": True, "signature_verified": True}
