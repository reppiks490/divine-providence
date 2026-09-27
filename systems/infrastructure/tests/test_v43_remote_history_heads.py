import pytest
from recovery_asymmetric import Ed25519RecoverySigner
from recovery_remote_history_heads import RemoteHistoryHeadSigner, RemoteHistoryHeadVerifier

def test_signed_history_head_verifies_and_binds_time():
 s=Ed25519RecoverySigner.generate('peerA',key_id='p1'); signer=RemoteHistoryHeadSigner(s); v=RemoteHistoryHeadVerifier(s.verifier(),max_future_skew_seconds=5)
 h=signer.sign(peer='peerA',sequence=4,record_hash='a'*64,observed_at=1000)
 assert v.verify(h,now=1004).valid
 assert not v.verify(h,now=994).valid

def test_monotonic_observed_time_and_sequence():
 s=Ed25519RecoverySigner.generate('peerA',key_id='p1'); signer=RemoteHistoryHeadSigner(s); v=RemoteHistoryHeadVerifier(s.verifier(),max_future_skew_seconds=5)
 old=signer.sign(peer='peerA',sequence=4,record_hash='a'*64,observed_at=1000)
 new=signer.sign(peer='peerA',sequence=5,record_hash='b'*64,observed_at=999)
 assert not v.verify(new,now=1000,previous=old).valid
