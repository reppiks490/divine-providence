from pathlib import Path


def test_v250_manifest_preserves_v240_and_adds_workspace_remote_store_contracts():
    text = Path('manifest.yaml').read_text()
    version = next(line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('version:'))
    assert tuple(map(int, version.split('.'))) >= (2,5,0)
    assert 'compatibility_baseline: 0.3.0' in text
    for capability in (
        'execution.workspace_isolation',
        'execution.mount_policy',
        'execution.network_egress_guard',
        'execution.process_receipt',
        'execution.runtime_enforcement',
        'execution.remote_store_adapter',
        'execution.watchdog',
        'permissions.vault_broker',
    ):
        assert capability in text


def test_v250_docs_keep_actual_computers_and_swarm_deferred():
    text = Path('references/workspace-isolation-remote-store.md').read_text()
    assert 'does **not** launch a VM, container, browser computer, or agent swarm' in text
    assert 'deny-by-default' in text
    assert '50+ logical-agent' in text
    assert 'secretref://' in text
