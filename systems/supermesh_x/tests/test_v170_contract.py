from pathlib import Path

def test_v170_capabilities_remain_backward_compatible():
    t=Path('manifest.yaml').read_text()
    version=next(line.split(':',1)[1].strip() for line in t.splitlines() if line.startswith('version:'))
    assert tuple(map(int,version.split('.'))) >= (1,7,0)
    assert 'plugins.distributed_provider_health_merge' in t
    assert 'plugins.quota_headroom_guard' in t
