from pathlib import Path

def test_v280_manifest_and_docs():
    text=Path('manifest.yaml').read_text()
    import re
    v=tuple(map(int,re.search(r'version: (\d+)\.(\d+)\.(\d+)',text).groups()))
    assert v >= (2,8,0)
    for cap in ('execution.launch_attestation','execution.connect_pin','execution.mount_attestation','execution.crash_reconciliation'):
        assert cap in text
    doc=Path('references/runtime-launch-attestation.md').read_text()
    assert 'does **not** activate the 50+ logical-agent swarm' in doc
