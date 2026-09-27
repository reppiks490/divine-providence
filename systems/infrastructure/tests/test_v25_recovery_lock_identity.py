import json, os, time
import recovery_lock as rl
from recovery_lock import RecoveryChainLock, LockOwner, LOCK_FORMAT_VERSION

def write(path,o): path.write_text(json.dumps(o.__dict__)+'\n')

def owner(pid=None,created=None,boot=None,start=None):
    pid=os.getpid() if pid is None else pid; created=time.time()-100 if created is None else created
    nonce='a'*32; boot=rl._boot_identity() if boot is None else boot; start=rl._process_start_identity(pid) if start is None else start
    fp=rl._fingerprint(LOCK_FORMAT_VERSION,pid,nonce,created,boot,start)
    return LockOwner(pid,nonce,created,LOCK_FORMAT_VERSION,boot,start,fp)

def test_owner_is_versioned_and_fingerprinted(tmp_path):
    l=RecoveryChainLock(tmp_path/'l',timeout_seconds=.01); assert l.acquire(); o=l.owner
    assert o.version==25 and o.boot_id!='unknown' and o.process_start!='unknown' and len(o.owner_fingerprint)==64; assert l.release()

def test_pid_reuse_identity_mismatch_allows_stale_reclaim(tmp_path,monkeypatch):
    p=tmp_path/'l'; o=owner(); write(p,o)
    monkeypatch.setattr(rl,'_process_start_identity',lambda pid:'different-start')
    l=RecoveryChainLock(p,timeout_seconds=.05,poll_seconds=.001,stale_after_seconds=1)
    assert l.acquire(); assert l.owner.owner_fingerprint!=o.owner_fingerprint; assert l.release()

def test_boot_mismatch_allows_stale_reclaim(tmp_path):
    p=tmp_path/'l'; o=owner(boot='prior-boot'); write(p,o)
    l=RecoveryChainLock(p,timeout_seconds=.05,poll_seconds=.001,stale_after_seconds=1)
    assert l.acquire(); assert l.release()

def test_clock_skew_future_timestamp_fails_closed(tmp_path):
    p=tmp_path/'l'; o=owner(created=time.time()+3600); write(p,o)
    l=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=0)
    assert l.acquire() is False and p.exists()

def test_legacy_v24_format_fails_closed(tmp_path):
    p=tmp_path/'l'; p.write_text(json.dumps({'pid':99999999,'nonce':'a'*32,'created_unix':time.time()-100})+'\n')
    l=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=0)
    assert l.acquire() is False and p.exists()

def test_tampered_fingerprint_fails_closed(tmp_path):
    p=tmp_path/'l'; o=owner(); d=o.__dict__.copy(); d['owner_fingerprint']='0'*64; p.write_text(json.dumps(d)+'\n')
    l=RecoveryChainLock(p,timeout_seconds=.005,poll_seconds=.001,stale_after_seconds=0)
    assert l.acquire() is False and p.exists()
