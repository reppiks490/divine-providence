from pathlib import Path


def test_v230_manifest_preserves_baseline_and_adds_execution_domain_contracts():
    text = Path('manifest.yaml').read_text()
    version_line = next(line for line in text.splitlines() if line.startswith('version:'))
    version = tuple(map(int, version_line.split(':', 1)[1].strip().split('.')))
    assert version >= (2, 3, 0)
    assert 'compatibility_baseline: 0.3.0' in text
    assert 'plugins.official_conformance_vectors' in text
    assert 'execution.domain' in text
    assert 'execution.fencing' in text
    assert 'execution.resource_budget' in text
    assert 'permissions.authority_manifest' in text
    assert 'privacy.trace_context_guard' in text


def test_v230_docs_explicitly_defer_swarm_and_preserve_authority_boundary():
    text = Path('references/execution-domain-foundation.md').read_text()
    assert '50+ logical agents' in text
    assert 'does **not** yet launch' in text
    assert 'research does not imply brokerage execution' in text
