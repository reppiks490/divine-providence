from pathlib import Path

def test_manifest_v180_and_capabilities():
    t=Path('manifest.yaml').read_text()
    version=next(line.split(':',1)[1].strip() for line in t.splitlines() if line.startswith('version:'))
    assert tuple(map(int,version.split('.'))) >= (1,8,0)
    assert 'plugins.cross_sdk_mcp_conformance' in t
    assert 'evidence.conformance_receipt' in t
