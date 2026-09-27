import pytest
from scripts.runtime_launch_attestation import (
    LaunchAttestationError, build_launch_request, attest_launch,
    verify_connect_pin, verify_mount_attestation, reconcile_runtime,
)

def test_launch_request_is_fenced_and_secret_free():
    req=build_launch_request('r1','worker-a',7,{'cpu_millis':1000,'ram_mb':512},['8.8.8.8'],['/workspace/in'])
    assert req['fencing_token']==7 and req['requested_limits']['cpu_millis']==1000
    assert 'secretref://' not in repr(req)

def test_attestation_rejects_under_enforced_resources_and_mutable_input():
    req=build_launch_request('r1','w',1,{'cpu_millis':1000,'ram_mb':512},['8.8.8.8'],['/workspace/in'])
    with pytest.raises(LaunchAttestationError):
        attest_launch(req,{'cpu_millis':500,'ram_mb':512},{'/workspace/in':'rw'},pid=12)

def test_attestation_accepts_equal_or_stronger_limits_and_readonly_inputs():
    req=build_launch_request('r1','w',1,{'cpu_millis':1000,'ram_mb':512},['8.8.8.8'],['/workspace/in'])
    a=attest_launch(req,{'cpu_millis':1000,'ram_mb':512},{'/workspace/in':'ro','/workspace/out':'rw'},pid=12)
    assert a['verified'] is True and a['pid']==12

def test_connect_pin_requires_original_public_answer_and_blocks_rebind():
    assert verify_connect_pin('api.example.com',['8.8.8.8'],'8.8.8.8')['allowed'] is True
    assert verify_connect_pin('api.example.com',['8.8.8.8'],'1.1.1.1')['allowed'] is False
    assert verify_connect_pin('api.example.com',['8.8.8.8'],'169.254.169.254')['allowed'] is False

def test_mount_attestation_requires_exact_readonly_inputs_and_separate_outbox():
    ok=verify_mount_attestation(['/workspace/in'],{'/workspace/in':'ro','/workspace/out':'rw'},'/workspace/out')
    assert ok['verified'] is True
    with pytest.raises(LaunchAttestationError): verify_mount_attestation(['/workspace/in'],{'/workspace/in':'rw','/workspace/out':'rw'},'/workspace/out')

def test_crash_reconciliation_never_resurrects_stale_owner():
    stale=reconcile_runtime({'worker_id':'old','fencing_token':1,'status':'running'},{'worker_id':'new','fencing_token':2,'status':'running'})
    assert stale['action']=='destroy_stale_runtime'
    missing=reconcile_runtime(None,{'worker_id':'new','fencing_token':2,'status':'running'})
    assert missing['action']=='mark_lost_and_requeue'
