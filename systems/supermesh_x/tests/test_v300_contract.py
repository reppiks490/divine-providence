from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v300_manifest_and_artifacts():
    text=(ROOT/'manifest.yaml').read_text()
    import re
    v=tuple(map(int,re.search(r'version: (\d+)\.(\d+)\.(\d+)',text).groups()))
    assert v >= (3,0,0)
    for cap in ('evidence.signed_runtime','evidence.key_rotation','evidence.signed_reconciliation','execution.adapter_conformance_receipt'):
        assert cap in text
    assert (ROOT/'scripts/signed_runtime_evidence.py').exists()
    assert (ROOT/'references/signed-runtime-evidence.md').exists()
