from pathlib import Path
def test_manifest_v190_capabilities():
    t=Path('manifest.yaml').read_text()
    version=next(line.split(':',1)[1].strip() for line in t.splitlines() if line.startswith('version:'))
    assert tuple(map(int,version.split('.'))) >= (1,9,0)
    assert 'plugins.quota_normalization' in t
    assert 'plugins.half_open_probe_gate' in t
