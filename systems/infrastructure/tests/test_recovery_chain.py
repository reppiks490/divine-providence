import json
from recovery_chain import AppendOnlyRecoveryChain, ChainedRecoveryCheckpoint, GENESIS
from recovery_checkpoint import RecoveryCheckpoint
from test_recovery_checkpoint import decision

def cp(tmp_path): return RecoveryCheckpoint.from_decision(decision(tmp_path))

def test_genesis_and_monotonic_append(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); a=s.append(cp(tmp_path),fsync=False); b=s.append(cp(tmp_path),fsync=False)
    assert a.generation==1 and a.previous_checkpoint_hash==GENESIS
    assert b.generation==2 and b.previous_checkpoint_hash==a.chain_hash
    assert s.verify_chain().valid

def test_history_is_preserved(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); a=s.append(cp(tmp_path),fsync=False); s.append(cp(tmp_path),fsync=False)
    assert s._entry_path(1).exists() and s._read_entry(1).chain_hash==a.chain_hash

def test_tampered_old_entry_detected(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); s.append(cp(tmp_path),fsync=False); s.append(cp(tmp_path),fsync=False)
    m=json.loads(s._entry_path(1).read_text()); m["generation"]=9; s._entry_path(1).write_text(json.dumps(m))
    assert not s.verify_chain().valid

def test_stale_head_replay_detected(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); a=s.append(cp(tmp_path),fsync=False); s.append(cp(tmp_path),fsync=False)
    s.head_path.write_text(json.dumps({"generation":1,"chain_hash":a.chain_hash}))
    v=s.verify_chain(); assert not v.valid and "HEAD" in v.reason

def test_fork_linkage_detected(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); s.append(cp(tmp_path),fsync=False); s.append(cp(tmp_path),fsync=False)
    m=json.loads(s._entry_path(2).read_text()); m["previous_checkpoint_hash"]="f"*64
    body={k:v for k,v in m.items() if k!="chain_hash"}
    import hashlib
    m["chain_hash"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    s._entry_path(2).write_text(json.dumps(m))
    assert not s.verify_chain().valid

def test_generation_gap_detected(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path); s.append(cp(tmp_path),fsync=False); s.append(cp(tmp_path),fsync=False)
    s._entry_path(1).unlink(); assert not s.verify_chain().valid

def test_invalid_checkpoint_cannot_issue(tmp_path):
    import dataclasses, pytest
    bad=dataclasses.replace(cp(tmp_path),checkpoint_hash="0"*64)
    with pytest.raises(ValueError): ChainedRecoveryCheckpoint.issue(bad,generation=1,previous_checkpoint_hash=GENESIS)

def test_chain_has_no_infrastructure_authority(tmp_path):
    s=AppendOnlyRecoveryChain(tmp_path)
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(set(dir(s)))
