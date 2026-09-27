from pathlib import Path

def test_v260_manifest_preserves_prior_and_adds_runtime_driver_contracts():
    text=Path('manifest.yaml').read_text()
    import re
    m=re.search(r'version: (\d+)\.(\d+)\.(\d+)', text)
    assert m and tuple(map(int,m.groups())) >= (2,6,0)
    for cap in ('execution.runtime_driver','execution.runtime_fencing','execution.kill_escalation','execution.orphan_cleanup','execution.secret_handle_injection'):
        assert cap in text

def test_v260_docs_keep_real_swarm_deferred():
    text=Path('references/runtime-driver-enforcement.md').read_text()
    assert 'does **not** activate the 50+ logical-agent swarm' in text
    assert 'fencing token' in text
