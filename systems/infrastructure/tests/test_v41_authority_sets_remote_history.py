import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_authority_governance import AuthoritySetEpoch, AuthoritySetStore
from recovery_remote_transparency import RemoteTransparencyHistory

def ss(prefix,n): return [Ed25519RecoverySigner.generate(f'{prefix}{i}',key_id=f'{prefix}{i}') for i in range(n)]
def epoch(n,prev,effective,threshold,signers):
 return AuthoritySetEpoch.issue(epoch=n,previous_epoch_hash=prev,effective_governance_epoch=effective,threshold=threshold,authority_verifiers=tuple(s.verifier() for s in signers))

def test_authority_set_rotation_requires_prior_quorum_overlap(tmp_path):
 a=ss('a',3); store=AuthoritySetStore(tmp_path/'a')
 e1=epoch(1,'0'*64,1,2,a); store.append(e1,fsync=False)
 b=[a[0],a[1],ss('b',1)[0]]; e2=epoch(2,e1.epoch_hash,2,2,b); store.append(e2,fsync=False)
 assert store.verify_chain().valid

def test_authority_set_threshold_cannot_decrease(tmp_path):
 a=ss('a',3); store=AuthoritySetStore(tmp_path/'a'); e1=epoch(1,'0'*64,1,2,a); store.append(e1,fsync=False)
 with pytest.raises(ValueError): store.append(epoch(2,e1.epoch_hash,2,1,a),fsync=False)

def test_authority_set_full_substitution_rejected(tmp_path):
 a=ss('a',3); store=AuthoritySetStore(tmp_path/'a'); e1=epoch(1,'0'*64,1,2,a); store.append(e1,fsync=False)
 with pytest.raises(ValueError): store.append(epoch(2,e1.epoch_hash,2,2,ss('b',3)),fsync=False)

def test_authority_set_head_rollback_fails(tmp_path):
 a=ss('a',3); store=AuthoritySetStore(tmp_path/'a'); e1=epoch(1,'0'*64,1,2,a); store.append(e1,fsync=False); old=(tmp_path/'a'/'HEAD').read_text()
 e2=epoch(2,e1.epoch_hash,2,2,a); store.append(e2,fsync=False); (tmp_path/'a'/'HEAD').write_text(old)
 assert not store.verify_chain().valid

def test_remote_history_append_and_rollback_detection(tmp_path):
 h=RemoteTransparencyHistory(tmp_path/'r')
 h.append('peer-a',1,'a'*64,100,fsync=False); h.append('peer-a',2,'b'*64,110,fsync=False)
 assert h.verify_peer('peer-a').valid
 with pytest.raises(ValueError): h.append('peer-a',1,'a'*64,120,fsync=False)

def test_remote_history_cross_log_disagreement(tmp_path):
 h=RemoteTransparencyHistory(tmp_path/'r'); [h.append('peer-a',i,('a'*64 if i==4 else str(i)*64)[:64],90+i,fsync=False) for i in range(1,5)]; [h.append('peer-b',i,('b'*64 if i==4 else str(i)*64)[:64],90+i,fsync=False) for i in range(1,5)]
 v=h.compare_sequence(4); assert not v.valid and v.equivocation

def test_remote_history_same_hash_agrees(tmp_path):
 h=RemoteTransparencyHistory(tmp_path/'r'); [h.append('peer-a',i,('a'*64 if i==4 else str(i)*64)[:64],90+i,fsync=False) for i in range(1,5)]; [h.append('peer-b',i,('a'*64 if i==4 else str(i)*64)[:64],90+i,fsync=False) for i in range(1,5)]
 assert h.compare_sequence(4).valid
