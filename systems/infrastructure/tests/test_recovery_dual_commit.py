import json
import pytest
from recovery_auth import HMACRecoveryAuthenticator
from recovery_chain import AppendOnlyRecoveryChain, AuthenticatedRecoveryChain
from recovery_checkpoint import RecoveryCheckpoint
from recovery_transaction import RecoveryDualChainCoordinator
from test_recovery_checkpoint import decision


def cp(tmp_path):
    return RecoveryCheckpoint.from_decision(decision(tmp_path))


def setup(tmp_path):
    base = AppendOnlyRecoveryChain(tmp_path / 'chain')
    auth = AuthenticatedRecoveryChain(tmp_path / 'chain', HMACRecoveryAuthenticator('producer', b'k'*32, key_id='k1'))
    coord = RecoveryDualChainCoordinator(tmp_path / 'chain')
    return base, auth, coord


def test_dual_commit_happy_path(tmp_path):
    base, auth, coord = setup(tmp_path)
    verdict = coord.stage_and_commit(cp(tmp_path), base, auth, fsync=False)
    assert verdict.valid and verdict.committed and verdict.generation == 1
    assert base.verify_chain().generation == 1
    assert auth.verify_against(base).valid
    assert coord.verify_transactions(base, auth).valid


def test_reconcile_crash_after_integrity_append(tmp_path):
    base, auth, coord = setup(tmp_path); checkpoint = cp(tmp_path)
    intent = coord.begin(checkpoint, base, auth, fsync=False)
    base.append(checkpoint, fsync=False)
    verdict = coord.reconcile(base, auth, fsync=False)
    assert verdict.valid and verdict.committed
    assert auth.verify_against(base).valid


def test_reconcile_crash_after_auth_append(tmp_path):
    base, auth, coord = setup(tmp_path); checkpoint = cp(tmp_path)
    coord.begin(checkpoint, base, auth, fsync=False)
    auth.append(checkpoint, fsync=False)
    verdict = coord.reconcile(base, auth, fsync=False)
    assert verdict.valid and verdict.committed
    assert auth.verify_against(base).valid


def test_reconcile_crash_after_both_before_commit(tmp_path):
    base, auth, coord = setup(tmp_path); checkpoint = cp(tmp_path)
    coord.begin(checkpoint, base, auth, fsync=False)
    base.append(checkpoint, fsync=False); auth.append(checkpoint, fsync=False)
    verdict = coord.reconcile(base, auth, fsync=False)
    assert verdict.valid and verdict.committed
    assert coord.verify_transactions(base, auth).valid


def test_partial_mismatch_fails_closed(tmp_path):
    base, auth, coord = setup(tmp_path); wanted = cp(tmp_path)
    coord.begin(wanted, base, auth, fsync=False)
    other = RecoveryCheckpoint.from_decision(decision(tmp_path / 'other'))
    base.append(other, fsync=False)
    verdict = coord.reconcile(base, auth, fsync=False)
    assert not verdict.valid and not verdict.committed
    assert auth.verify_chain().generation == 0


def test_tampered_intent_fails_closed(tmp_path):
    base, auth, coord = setup(tmp_path); coord.begin(cp(tmp_path), base, auth, fsync=False)
    p = next((tmp_path/'chain').glob('txn-intent-*.json'))
    m = json.loads(p.read_text()); m['checkpoint_hash'] = '0'*64; p.write_text(json.dumps(m))
    verdict = coord.reconcile(base, auth, fsync=False)
    assert not verdict.valid


def test_tampered_commit_fails_verification(tmp_path):
    base, auth, coord = setup(tmp_path); coord.stage_and_commit(cp(tmp_path), base, auth, fsync=False)
    p = next((tmp_path/'chain').glob('txn-commit-*.json'))
    m = json.loads(p.read_text()); m['auth_entry_hash'] = '0'*64; p.write_text(json.dumps(m))
    assert not coord.verify_transactions(base, auth).valid


def test_coordinator_has_no_infrastructure_authority(tmp_path):
    c = RecoveryDualChainCoordinator(tmp_path)
    assert {'execute','mutate','promote','rollback','acquire','release'}.isdisjoint(dir(c))


def test_partial_mismatch_writes_durable_quarantine_marker(tmp_path):
    base, auth, coord = setup(tmp_path); wanted = cp(tmp_path)
    intent = coord.begin(wanted, base, auth, fsync=False)
    other = RecoveryCheckpoint.from_decision(decision(tmp_path / 'other'))
    base.append(other, fsync=False)
    verdict = coord.reconcile(base, auth, fsync=False)
    assert not verdict.valid
    q = tmp_path/'chain'/f'txn-quarantine-{intent.generation:020d}.json'
    assert q.exists()
    m=json.loads(q.read_text())
    assert m['intent_hash']==intent.intent_hash and 'mismatch' in m['reason']


def test_intent_write_failure_never_advances_chains(monkeypatch,tmp_path):
    import recovery_transaction as rt
    base, auth, coord = setup(tmp_path)
    original=rt._atomic_write
    def boom(path,*args,**kwargs):
        if 'txn-intent-' in path.name: raise OSError('intent write failure')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(rt,'_atomic_write',boom)
    with pytest.raises(OSError): coord.stage_and_commit(cp(tmp_path),base,auth,fsync=False)
    assert base.verify_chain().generation==0 and auth.verify_chain().generation==0


def test_commit_write_failure_is_reconcilable(monkeypatch,tmp_path):
    import recovery_transaction as rt
    base, auth, coord = setup(tmp_path); checkpoint=cp(tmp_path)
    original=rt._atomic_write
    def boom(path,*args,**kwargs):
        if 'txn-commit-' in path.name: raise OSError('commit write failure')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(rt,'_atomic_write',boom)
    with pytest.raises(OSError): coord.stage_and_commit(checkpoint,base,auth,fsync=False)
    assert base.verify_chain().generation==1 and auth.verify_chain().generation==1
    monkeypatch.setattr(rt,'_atomic_write',original)
    assert coord.reconcile(base,auth,fsync=False).committed


def test_intent_fsync_failure_leaves_no_partial_target(monkeypatch,tmp_path):
    import recovery_transaction as rt
    base, auth, coord = setup(tmp_path)
    def boom(fd): raise OSError('fsync failure')
    monkeypatch.setattr(rt.os,'fsync',boom)
    with pytest.raises(OSError): coord.stage_and_commit(cp(tmp_path),base,auth,fsync=True)
    assert not list((tmp_path/'chain').glob('txn-intent-*.json'))
    assert not list((tmp_path/'chain').glob('*.tmp'))
    assert base.verify_chain().generation==0 and auth.verify_chain().generation==0


def test_intent_rename_failure_leaves_no_partial_target(monkeypatch,tmp_path):
    import recovery_transaction as rt
    base, auth, coord = setup(tmp_path)
    original=rt.os.replace
    def boom(src,dst):
        if 'txn-intent-' in str(dst): raise OSError('rename failure')
        return original(src,dst)
    monkeypatch.setattr(rt.os,'replace',boom)
    with pytest.raises(OSError): coord.stage_and_commit(cp(tmp_path),base,auth,fsync=False)
    assert not list((tmp_path/'chain').glob('txn-intent-*.json'))
    assert not list((tmp_path/'chain').glob('*.tmp'))
    assert base.verify_chain().generation==0 and auth.verify_chain().generation==0
