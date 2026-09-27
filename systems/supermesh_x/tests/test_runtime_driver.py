import pytest
from scripts.runtime_driver import (
    RuntimeDriverError, StaleRuntimeFence, InMemorySandboxBackend,
    IsolatedRuntimeDriver, validate_runtime_backend, classify_egress_target,
)


def reservation(run_id='r1'):
    return {'run_id':run_id,'resources':{'cpu_millis':1000,'ram_mb':1024},'granted_capabilities':['terminal.sandbox'],'request_digest':'sha256:r'}


def test_backend_contract_requires_fenced_lifecycle_and_enforcement():
    result = validate_runtime_backend(InMemorySandboxBackend())
    assert result['conformant'] is True
    class Broken: pass
    bad = validate_runtime_backend(Broken())
    assert bad['conformant'] is False and 'create' in bad['missing']


def test_runtime_lifecycle_is_fenced_and_receipts_hide_secrets():
    backend = InMemorySandboxBackend()
    driver = IsolatedRuntimeDriver(backend)
    created = driver.create('r1','worker-a',1,reservation(), secret_refs=['secretref://vault/api'])
    started = driver.start('r1','worker-a',1,now_ms=10)
    beat = driver.heartbeat('r1','worker-a',1,now_ms=20)
    stopped = driver.stop('r1','worker-a',1,now_ms=30,reason='complete')
    destroyed = driver.destroy('r1','worker-a',1,now_ms=40)
    assert [created['status'],started['status'],beat['status'],stopped['status'],destroyed['status']] == ['created','running','running','stopped','destroyed']
    assert 'vault/api' not in repr([created,started,beat,stopped,destroyed])


def test_stale_fence_cannot_control_replaced_runtime():
    backend = InMemorySandboxBackend(); driver = IsolatedRuntimeDriver(backend)
    driver.create('r1','worker-a',1,reservation())
    backend.force_takeover('r1','worker-b',2)
    with pytest.raises(StaleRuntimeFence): driver.stop('r1','worker-a',1,now_ms=20,reason='late')


def test_resource_limits_are_enforced_not_just_described():
    backend = InMemorySandboxBackend(); driver = IsolatedRuntimeDriver(backend)
    driver.create('r1','worker',1,reservation())
    state = backend.inspect('r1')
    assert state['enforced_limits']['cpu_millis'] == 1000
    assert state['enforced_limits']['ram_mb'] == 1024
    with pytest.raises(RuntimeDriverError):
        driver.create('r2','worker',1,{'run_id':'r2','resources':{'cpu_millis':0},'granted_capabilities':[],'request_digest':'x'})


def test_secret_injection_is_handle_only_and_ephemeral():
    backend = InMemorySandboxBackend(); driver = IsolatedRuntimeDriver(backend)
    receipt = driver.create('r1','worker',1,reservation(), secret_refs=['secretref://vault/api'])
    state = backend.inspect('r1')
    assert state['secret_handle_count'] == 1
    assert 'secretref://' not in repr(state)
    assert 'secretref://' not in repr(receipt)


def test_metadata_and_private_targets_fail_closed_in_egress_classifier():
    for host in ['169.254.169.254','127.0.0.1','10.0.0.1','localhost','[::1]']:
        assert classify_egress_target(host)['allowed'] is False
    assert classify_egress_target('api.example.com')['allowed'] is True


def test_kill_escalation_and_orphan_cleanup_are_deterministic():
    backend = InMemorySandboxBackend(); driver = IsolatedRuntimeDriver(backend)
    driver.create('r1','worker',1,reservation()); driver.start('r1','worker',1,now_ms=10)
    plan = driver.kill_plan('r1', grace_ms=500)
    assert [x['signal'] for x in plan['steps']] == ['TERM','KILL']
    backend.mark_orphan('r1')
    cleanup = driver.cleanup_orphans(now_ms=100)
    assert cleanup['cleaned'] == ['r1'] and backend.inspect('r1')['status']=='destroyed'
