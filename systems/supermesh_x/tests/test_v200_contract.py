from pathlib import Path

def test_manifest_v200_capabilities():
    t=Path('manifest.yaml').read_text()
    assert 'compatibility_baseline: 0.3.0' in t
    assert 'plugins.authenticated_provider_health_state' in t
    assert 'plugins.provider_health_replay_guard' in t
