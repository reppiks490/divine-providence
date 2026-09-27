import json
from recovery_auth import HMACRecoveryAuthenticator
from recovery_chain import AuthenticatedRecoveryChain
from recovery_checkpoint import RecoveryCheckpoint
def cp(n=1):
 body={"schema":"infra-recovery-checkpoint/v1","journal_path":"/tmp/j","decision_hash":"d"*64,
       "last_good_offset":n,"original_file_size":n,"original_tail_status":"clean",
       "proof_restore_eligible":True,"accepted_transaction_hashes":["a"*64]}
 import hashlib,json
 h=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
 return RecoveryCheckpoint(body["schema"],body["journal_path"],body["decision_hash"],n,n,"clean",True,tuple(body["accepted_transaction_hashes"]),h)
def test_authenticated_chain_requires_valid_signature(tmp_path):
 a=HMACRecoveryAuthenticator("p",b"k"*32); c=AuthenticatedRecoveryChain(tmp_path,a)
 c.append(cp()); assert c.verify_chain().valid
 p=next(tmp_path.glob("auth-*.json")); m=json.loads(p.read_text()); m["envelope"]["signature"]="0"*64; p.write_text(json.dumps(m))
 assert not c.verify_chain().valid
def test_wrong_key_rejected(tmp_path):
 c=AuthenticatedRecoveryChain(tmp_path,HMACRecoveryAuthenticator("p",b"k"*32)); c.append(cp())
 assert not AuthenticatedRecoveryChain(tmp_path,HMACRecoveryAuthenticator("p",b"x"*32)).verify_chain().valid
def test_unsigned_downgrade_rejected(tmp_path):
 c=AuthenticatedRecoveryChain(tmp_path,HMACRecoveryAuthenticator("p",b"k"*32)); c.append(cp())
 p=next(tmp_path.glob("auth-*.json")); m=json.loads(p.read_text()); del m["envelope"]; p.write_text(json.dumps(m))
 assert not c.verify_chain().valid
def test_no_mutation_authority(tmp_path):
 c=AuthenticatedRecoveryChain(tmp_path,HMACRecoveryAuthenticator("p",b"k"*32))
 assert {"execute","mutate","promote","rollback"}.isdisjoint(dir(c))

def test_authenticated_chain_must_align_with_integrity_chain(tmp_path):
 from recovery_chain import AppendOnlyRecoveryChain
 auth=HMACRecoveryAuthenticator('p',b'k'*32,key_id='k1')
 base=AppendOnlyRecoveryChain(tmp_path); base.append(cp(1),fsync=False)
 side=AuthenticatedRecoveryChain(tmp_path,auth); side.append(cp(2),fsync=False)
 verdict=side.verify_against(base)
 assert not verdict.valid and 'mismatch' in verdict.reason
