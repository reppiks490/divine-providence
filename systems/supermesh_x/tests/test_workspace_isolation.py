import pytest

from scripts.workspace_isolation import (
    WorkspacePolicyError,
    NetworkPolicyError,
    ExecutionSpecError,
    VaultBrokerError,
    build_mount_manifest,
    build_network_policy,
    egress_allowed,
    build_execution_spec,
    build_execution_receipt,
    build_runtime_enforcement,
    build_vault_broker_request,
    build_vault_broker_receipt,
    watchdog_plan,
)


def test_mount_manifest_rejects_host_and_parent_escape_paths():
    with pytest.raises(WorkspacePolicyError):
        build_mount_manifest('ws1', [{'name':'host','source_ref':'file:///etc','target':'etc','mode':'ro'}])
    with pytest.raises(WorkspacePolicyError):
        build_mount_manifest('ws1', [{'name':'escape','source_ref':'artifactref://a','target':'../host','mode':'ro'}])
    with pytest.raises(WorkspacePolicyError):
        build_mount_manifest('ws1', [{'name':'abs','source_ref':'artifactref://a','target':'/host','mode':'ro'}])


def test_mount_manifest_separates_readonly_scratch_and_outbox():
    manifest = build_mount_manifest('ws1', [
        {'name':'source','source_ref':'artifactref://pkg/source','target':'src','mode':'ro'},
        {'name':'scratch','source_ref':'scratch://ws1','target':'tmp','mode':'rw'},
        {'name':'out','source_ref':'artifactout://ws1','target':'out','mode':'output'},
    ])
    assert manifest['workspace_id'] == 'ws1'
    assert manifest['host_filesystem_visible'] is False
    assert manifest['mounts'][0]['mode'] == 'ro'
    assert manifest['mounts'][1]['mode'] == 'rw'
    assert manifest['mounts'][2]['mode'] == 'output'
    assert all('file://' not in m['source_ref'] for m in manifest['mounts'])


def test_network_egress_defaults_none_and_denies_internal_targets():
    none = build_network_policy('none')
    assert egress_allowed(none, 'https://example.com') is False

    public = build_network_policy('public_https')
    assert egress_allowed(public, 'https://example.com/path') is True
    for url in (
        'http://example.com',
        'https://127.0.0.1/',
        'https://10.1.2.3/',
        'https://169.254.169.254/latest/meta-data',
        'https://localhost/',
    ):
        assert egress_allowed(public, url) is False


def test_provider_allowlist_requires_explicit_host():
    policy = build_network_policy('provider_allowlist', allow_hosts=['api.example.com'])
    assert egress_allowed(policy, 'https://api.example.com/v1') is True
    assert egress_allowed(policy, 'https://sub.api.example.com/v1') is False
    assert egress_allowed(policy, 'https://other.example.com') is False
    with pytest.raises(NetworkPolicyError):
        build_network_policy('provider_allowlist', allow_hosts=[])


def test_execution_spec_is_argv_only_and_secrets_use_refs():
    spec = build_execution_spec(
        argv=['python', '-m', 'pytest', '-q'],
        cwd='src',
        env={'PYTHONUNBUFFERED':'1'},
        secret_env={'API_TOKEN':'secretref://vault/team/token'},
        timeout_ms=60_000,
    )
    assert spec['shell'] is False
    assert spec['argv'][0] == 'python'
    assert spec['secret_env']['API_TOKEN'].startswith('secretref://')

    with pytest.raises(ExecutionSpecError):
        build_execution_spec(argv='pytest -q', cwd='src', env={}, secret_env={}, timeout_ms=1000)
    with pytest.raises(ExecutionSpecError):
        build_execution_spec(argv=['sh','-c','echo hi'], cwd='src', env={}, secret_env={}, timeout_ms=1000, shell=True)
    with pytest.raises(ExecutionSpecError):
        build_execution_spec(argv=['python'], cwd='src', env={'API_TOKEN':'raw-secret'}, secret_env={}, timeout_ms=1000)
    with pytest.raises(ExecutionSpecError):
        build_execution_spec(argv=['python'], cwd='src', env={}, secret_env={'API_TOKEN':'raw-secret'}, timeout_ms=1000)


def test_execution_receipt_redacts_args_env_and_secret_refs():
    spec = build_execution_spec(
        argv=['python','script.py','--token','secret-looking-arg'],
        cwd='src',
        env={'MODE':'test'},
        secret_env={'API_TOKEN':'secretref://vault/team/token'},
        timeout_ms=1000,
    )
    receipt = build_execution_receipt(spec, exit_code=0, started_at_ms=10, ended_at_ms=25, stdout_bytes=20, stderr_bytes=0)
    rendered = repr(receipt)
    assert receipt['exit_code'] == 0
    assert receipt['executable'] == 'python'
    assert receipt['arg_count'] == 4
    assert 'secret-looking-arg' not in rendered
    assert 'vault/team/token' not in rendered
    assert 'MODE' in receipt['env_keys'] and 'API_TOKEN' in receipt['secret_env_keys']


def test_runtime_enforcement_cannot_exceed_reserved_resources_or_authority():
    reservation = {
        'run_id':'r1',
        'resources':{'cpu_millis':2000,'ram_mb':4096,'storage_mb':10000,'gpu_units':1,'concurrency':2},
        'granted_capabilities':['filesystem.read','terminal.sandbox'],
        'request_digest':'sha256:abc',
    }
    hook = build_runtime_enforcement(reservation, requested_limits={'cpu_millis':1500,'ram_mb':2048,'concurrency':1}, requested_capabilities=['terminal.sandbox'])
    assert hook['limits']['cpu_millis'] == 1500
    assert hook['capabilities'] == ['terminal.sandbox']
    assert hook['enforcement_required'] is True

    with pytest.raises(WorkspacePolicyError):
        build_runtime_enforcement(reservation, requested_limits={'ram_mb':8192}, requested_capabilities=[])
    with pytest.raises(WorkspacePolicyError):
        build_runtime_enforcement(reservation, requested_limits={}, requested_capabilities=['broker.orders'])


def test_vault_broker_keeps_secret_refs_out_of_receipts():
    req = build_vault_broker_request(
        run_id='r1',
        secret_refs=['secretref://vault/db/readonly'],
        purpose='database-read',
        authority_manifest={'granted':['secrets.resolve']},
    )
    assert req['secret_refs'] == ['secretref://vault/db/readonly']
    receipt = build_vault_broker_receipt(req, status='resolved', lease_ids=['lease-123'])
    rendered = repr(receipt)
    assert receipt['secret_ref_count'] == 1
    assert 'vault/db/readonly' not in rendered
    assert 'lease-123' not in rendered

    with pytest.raises(VaultBrokerError):
        build_vault_broker_request(run_id='r1', secret_refs=['secretref://vault/db/readonly'], purpose='read', authority_manifest={'granted':[]})


def test_watchdog_generates_cleanup_plan_without_executing_actions():
    runs = [
        {'run_id':'expired','status':'running','lease_expires_at_ms':100,'updated_at_ms':90},
        {'run_id':'done','status':'completed','lease_expires_at_ms':None,'updated_at_ms':90},
        {'run_id':'healthy','status':'running','lease_expires_at_ms':500,'updated_at_ms':90},
    ]
    reservations = {'expired':{}, 'done':{}, 'healthy':{}}
    plan = watchdog_plan(runs, reservations, now_ms=200)
    assert plan['executed'] is False
    assert {'run_id':'expired','action':'mark_worker_lost','reason':'lease_expired'} in plan['actions']
    assert {'run_id':'expired','action':'release_reservation','reason':'lease_expired'} in plan['actions']
    assert {'run_id':'done','action':'release_reservation','reason':'terminal_run'} in plan['actions']
    assert not any(a['run_id']=='healthy' for a in plan['actions'])
