import json, os, time
from recovery_lock import RecoveryChainLock, LockOwner

def write_owner(path,pid,nonce,created):
    path.parent.mkdir(parents=True,exist_ok=True)
    
    import recovery_lock as rl
    boot=rl._boot_identity(); start=rl._process_start_identity(pid); start = start if start != rl.UNKNOWN else 'dead-process'; fp=rl._fingerprint(rl.LOCK_FORMAT_VERSION,pid,nonce,created,boot,start)
    path.write_text(json.dumps({'pid':pid,'nonce':nonce,'created_unix':created,'version':rl.LOCK_FORMAT_VERSION,'boot_id':boot,'process_start':start,'owner_fingerprint':fp})+'\n')

def dead_pid():
    # Very high PID is absent on normal test hosts; verify before using it.
    for pid in (99999999, 99999998, 99999997):
        if RecoveryChainLock._pid_definitely_dead(pid): return pid
    raise RuntimeError('no demonstrably dead pid available')

def test_nonce_bound_owner_and_safe_release(tmp_path):
    p=tmp_path/'l'; lock=RecoveryChainLock(p,timeout_seconds=.01)
    assert lock.acquire(); own=lock.owner; assert own and len(own.nonce)>=32
    # Simulate successor/substitution: old owner must not unlink it.
    created=time.time(); import recovery_lock as rl; boot=rl._boot_identity(); start=rl._process_start_identity(os.getpid()); nonce='b'*32; fp=rl._fingerprint(rl.LOCK_FORMAT_VERSION,os.getpid(),nonce,created,boot,start)
    replacement={'pid':os.getpid(),'nonce':nonce,'created_unix':created,'version':rl.LOCK_FORMAT_VERSION,'boot_id':boot,'process_start':start,'owner_fingerprint':fp}
    p.write_text(json.dumps(replacement)+'\n')
    assert lock.release() is False and p.exists()

def test_stale_dead_owner_is_reclaimed(tmp_path):
    p=tmp_path/'l'; write_owner(p,dead_pid(),'a'*32,time.time()-100)
    lock=RecoveryChainLock(p,timeout_seconds=.05,poll_seconds=.001,stale_after_seconds=1)
    assert lock.acquire(); assert lock.owner.pid==os.getpid(); assert lock.release()

def test_live_owner_is_never_reclaimed_even_if_old(tmp_path):
    p=tmp_path/'l'; write_owner(p,os.getpid(),'a'*32,time.time()-1000)
    lock=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=0)
    assert lock.acquire() is False and p.exists()

def test_fresh_dead_owner_not_reclaimed_before_age(tmp_path):
    p=tmp_path/'l'; write_owner(p,dead_pid(),'a'*32,time.time())
    lock=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=100)
    assert lock.acquire() is False and p.exists()

def test_malformed_lock_fails_closed(tmp_path):
    p=tmp_path/'l'; p.write_text('not-json')
    lock=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=0)
    assert lock.acquire() is False and p.read_text()=='not-json'

def test_release_after_external_delete_does_not_claim_success(tmp_path):
    p=tmp_path/'l'; lock=RecoveryChainLock(p,timeout_seconds=.01); assert lock.acquire(); p.unlink()
    assert lock.release() is False

def test_lock_has_no_infrastructure_mutation_authority(tmp_path):
    lock=RecoveryChainLock(tmp_path/'l')
    assert {'execute','mutate','promote','rollback','scale','repair','isolate'}.isdisjoint(set(dir(lock)))
