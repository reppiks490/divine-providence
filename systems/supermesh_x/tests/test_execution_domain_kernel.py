import pytest

from scripts.execution_domain_kernel import (
    AuthorityViolation,
    BudgetExceeded,
    LeaseConflict,
    StaleFence,
    ExecutionDomainLedger,
    canonical_dispatch_key,
    sanitize_trace_context,
)


def test_lease_takeover_uses_monotonic_fence_and_rejects_stale_writer():
    ledger = ExecutionDomainLedger()
    first = ledger.acquire('run-001', 'worker-a', now_ms=1_000, ttl_ms=500)
    assert first['fencing_token'] == 1
    with pytest.raises(LeaseConflict):
        ledger.acquire('run-001', 'worker-b', now_ms=1_100, ttl_ms=500)
    second = ledger.acquire('run-001', 'worker-b', now_ms=1_501, ttl_ms=500)
    assert second['fencing_token'] == 2
    with pytest.raises(StaleFence):
        ledger.checkpoint('run-001', 'worker-a', 1, {'phase': 'late'}, now_ms=1_600)


def test_renew_preserves_fence_but_extends_expiry():
    ledger = ExecutionDomainLedger()
    lease = ledger.acquire('run-renew', 'worker-a', now_ms=1_000, ttl_ms=500)
    renewed = ledger.renew('run-renew', 'worker-a', lease['fencing_token'], now_ms=1_200, ttl_ms=900)
    assert renewed['fencing_token'] == lease['fencing_token']
    assert renewed['expires_at_ms'] == 2_100


def test_terminal_run_cannot_be_reopened():
    ledger = ExecutionDomainLedger()
    lease = ledger.acquire('run-terminal', 'worker-a', now_ms=100, ttl_ms=500)
    ledger.complete('run-terminal', 'worker-a', lease['fencing_token'], outcome='ok', now_ms=200)
    with pytest.raises(LeaseConflict):
        ledger.acquire('run-terminal', 'worker-b', now_ms=1_000, ttl_ms=500)


def test_checkpoint_is_content_addressed_and_secret_free():
    ledger = ExecutionDomainLedger()
    lease = ledger.acquire('run-cp', 'worker-a', now_ms=100, ttl_ms=500)
    receipt = ledger.checkpoint(
        'run-cp', 'worker-a', lease['fencing_token'],
        {'phase': 'compile', 'api_key': 'do-not-serialize', 'private_email': 'secret@example.com'},
        now_ms=200,
    )
    serialized = repr(receipt)
    assert receipt['state_hash'].startswith('sha256:')
    assert 'do-not-serialize' not in serialized
    assert 'secret@example.com' not in serialized
    assert 'state' not in receipt


def test_resource_budget_blocks_overrun_and_tracks_remaining():
    ledger = ExecutionDomainLedger()
    ledger.configure_budget('run-budget', {'provider_calls': 3, 'tokens': 1000, 'cpu_ms': 5000})
    remaining = ledger.consume_budget('run-budget', {'provider_calls': 2, 'tokens': 400, 'cpu_ms': 1250})
    assert remaining == {'provider_calls': 1, 'tokens': 600, 'cpu_ms': 3750}
    with pytest.raises(BudgetExceeded):
        ledger.consume_budget('run-budget', {'provider_calls': 2})


def test_negative_budget_usage_is_rejected():
    ledger = ExecutionDomainLedger()
    ledger.configure_budget('run-budget-neg', {'provider_calls': 1})
    with pytest.raises(ValueError):
        ledger.consume_budget('run-budget-neg', {'provider_calls': -1})


def test_authority_manifest_is_least_privilege_and_blocks_implicit_execution():
    ledger = ExecutionDomainLedger()
    manifest = ledger.set_authority(
        'run-auth',
        requested=['filesystem.read', 'terminal.sandbox', 'broker.orders'],
        granted=['filesystem.read', 'terminal.sandbox'],
    )
    assert manifest['granted'] == ['filesystem.read', 'terminal.sandbox']
    with pytest.raises(AuthorityViolation):
        ledger.require_authority('run-auth', 'broker.orders')


def test_external_write_requires_explicit_write_scope_even_with_read_scope():
    ledger = ExecutionDomainLedger()
    ledger.set_authority('run-auth2', requested=['repo.read'], granted=['repo.read'])
    with pytest.raises(AuthorityViolation):
        ledger.require_authority('run-auth2', 'repo.write')


def test_idempotency_key_is_deterministic_and_operation_specific():
    a = canonical_dispatch_key('run-1', 'task-9', 2, 'sha256:abc')
    b = canonical_dispatch_key('run-1', 'task-9', 2, 'sha256:abc')
    c = canonical_dispatch_key('run-1', 'task-9', 2, 'sha256:def')
    assert a == b
    assert a != c
    assert a.startswith('smx:')


def test_trace_sanitization_drops_secrets_and_untrusted_baggage():
    clean = sanitize_trace_context({
        'trace_id': '4bf92f3577b34da6a3ce929d0e0e4736',
        'span_id': '00f067aa0ba902b7',
        'authorization': 'Bearer secret',
        'api_key': 'secret-key',
        'baggage': {'user_email': 'secret@example.com'},
        'labels': {'provider': 'exa', 'run_kind': 'research', 'customer_id': 'private'},
    })
    assert clean == {
        'trace_id': '4bf92f3577b34da6a3ce929d0e0e4736',
        'span_id': '00f067aa0ba902b7',
        'labels': {'provider': 'exa', 'run_kind': 'research'},
    }


def test_checkpoint_rollback_requires_current_fence_and_existing_checkpoint():
    ledger = ExecutionDomainLedger()
    lease = ledger.acquire('run-rb', 'worker-a', now_ms=100, ttl_ms=500)
    cp = ledger.checkpoint('run-rb', 'worker-a', lease['fencing_token'], {'phase': 'one'}, now_ms=200)
    rolled = ledger.rollback('run-rb', 'worker-a', lease['fencing_token'], cp['checkpoint_id'], now_ms=250)
    assert rolled['rollback_to'] == cp['checkpoint_id']
    with pytest.raises(KeyError):
        ledger.rollback('run-rb', 'worker-a', lease['fencing_token'], 'missing', now_ms=260)
