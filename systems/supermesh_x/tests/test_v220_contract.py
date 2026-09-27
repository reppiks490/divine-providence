from pathlib import Path


def test_v220_capabilities_remain_present_in_newer_manifest():
    text = Path('manifest.yaml').read_text()
    version_line = next(line for line in text.splitlines() if line.startswith('version:'))
    major, minor, patch = map(int, version_line.split(':', 1)[1].strip().split('.'))
    assert (major, minor, patch) >= (2, 2, 0)
    assert 'compatibility_baseline: 0.3.0' in text
    assert 'plugins.authenticated_provider_health_state' in text
    assert 'plugins.official_conformance_vectors' in text
    assert 'plugins.frozen_requirement_set_guard' in text
