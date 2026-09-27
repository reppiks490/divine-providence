import pytest

from scripts.execution_domain_kernel import LeaseConflict, StaleFence
from scripts.remote_store_adapter import (
    MemoryCASBackend,
    RemoteRunStoreAdapter,
    RemoteStoreUnavailable,
    RemoteVersionConflict,
    validate_remote_backend,
)


def test_remote_backend_conformance_requires_read_and_atomic_cas():
    result = validate_remote_backend(MemoryCASBackend())
    assert result['conformant'] is True
    assert result['atomic_cas'] is True
    assert result['durable_contract_version'] == 1


class BrokenBackend:
    def read(self, run_id):
        return None


def test_remote_backend_missing_cas_is_rejected():
    result = validate_remote_backend(BrokenBackend())
    assert result['conformant'] is False
    assert 'compare_and_swap' in result['missing']


def test_remote_adapter_fences_stale_owner_after_takeover():
    backend = MemoryCASBackend()
    a = RemoteRunStoreAdapter(backend)
    b = RemoteRunStoreAdapter(backend)
    lease1 = a.acquire('run1','worker-a',now_ms=1000,ttl_ms=100)
    with pytest.raises(LeaseConflict):
        b.acquire('run1','worker-b',now_ms=1050,ttl_ms=100)
    lease2 = b.acquire('run1','worker-b',now_ms=1100,ttl_ms=100)
    assert lease2['fencing_token'] == lease1['fencing_token'] + 1
    with pytest.raises(StaleFence):
        a.checkpoint('run1','worker-a',lease1['fencing_token'],{'secret':'old'},now_ms=1110)


def test_remote_checkpoint_is_secret_free_and_content_addressed():
    backend = MemoryCASBackend()
    store = RemoteRunStoreAdapter(backend)
    lease = store.acquire('run2','worker',now_ms=10,ttl_ms=100)
    receipt = store.checkpoint('run2','worker',lease['fencing_token'],{'phase':'x','secret':'do-not-store'},now_ms=20,state_ref='artifactref://checkpoints/r2')
    assert receipt['state_hash'].startswith('sha256:')
    assert receipt['state_ref'] == 'artifactref://checkpoints/r2'
    assert 'do-not-store' not in repr(receipt)
    assert 'do-not-store' not in repr(backend.read('run2'))


def test_remote_adapter_surfaces_atomic_cas_conflict_without_fallback():
    backend = MemoryCASBackend()
    store = RemoteRunStoreAdapter(backend)
    lease = store.acquire('run3','worker',now_ms=10,ttl_ms=100)
    backend.fail_next_cas = True
    with pytest.raises(RemoteVersionConflict):
        store.renew('run3','worker',lease['fencing_token'],now_ms=20,ttl_ms=100)
    assert backend.read('run3')['version'] == lease['version']


def test_remote_backend_outage_blocks_ownership_mutation():
    backend = MemoryCASBackend()
    backend.available = False
    store = RemoteRunStoreAdapter(backend)
    with pytest.raises(RemoteStoreUnavailable):
        store.acquire('run4','worker',now_ms=10,ttl_ms=100)
    assert backend._records == {}


def test_remote_adapter_cancel_fences_current_worker():
    backend = MemoryCASBackend()
    store = RemoteRunStoreAdapter(backend)
    lease = store.acquire('run5','worker',now_ms=10,ttl_ms=100)
    cancelled = store.cancel('run5',expected_version=lease['version'],now_ms=20,reason='operator')
    assert cancelled['status'] == 'cancelled'
    assert cancelled['fencing_token'] == lease['fencing_token'] + 1
    with pytest.raises(StaleFence):
        store.checkpoint('run5','worker',lease['fencing_token'],{'late':True},now_ms=21)
