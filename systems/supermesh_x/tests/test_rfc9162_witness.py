
import json
import pytest
from scripts.witnessed_transparency import (
    WitnessError, Witness, WitnessRegistry,
    rfc9162_root, rfc9162_consistency_proof, verify_rfc9162_consistency_proof,
    RFC9162WitnessedCheckpointLedger, GossipReceiptStore,
)

def witnesses():
    a,b=Witness.generate("a"),Witness.generate("b")
    r=WitnessRegistry(2)
    for w in (a,b): r.add(w.witness_id,w.public_key_bytes())
    return a,b,r

@pytest.mark.parametrize("m,n", [(1,2),(1,7),(2,7),(3,7),(4,7),(5,8),(7,9),(8,9),(16,31),(31,64)])
def test_rfc9162_compact_consistency_proofs_are_logarithmic(m,n):
    leaves=[f"e{i}".encode() for i in range(n)]
    p=rfc9162_consistency_proof(leaves[:m], leaves)
    assert "old_leaves" not in p and "new_leaves" not in p
    assert len(p["path"]) <= n.bit_length() + 1
    assert verify_rfc9162_consistency_proof(p)
    assert p["old_root"] == rfc9162_root(leaves[:m])
    assert p["new_root"] == rfc9162_root(leaves)

def test_rfc9162_mutated_consistency_proof_fails_closed():
    leaves=[f"e{i}".encode() for i in range(9)]
    p=rfc9162_consistency_proof(leaves[:5], leaves)
    p["path"][0]="00"*32
    with pytest.raises(WitnessError):
        verify_rfc9162_consistency_proof(p)

def test_rfc9162_non_prefix_generation_fails_closed():
    with pytest.raises(WitnessError):
        rfc9162_consistency_proof([b"a",b"x"], [b"a",b"b",b"c"])

def test_new_ledger_is_additive_and_uses_compact_evidence():
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    c1=l.checkpoint([b"a"],[a,b])
    c2=l.checkpoint([b"a",b"b",b"c"],[a,b])
    assert c1["tree_algorithm"]=="RFC9162_SHA256"
    assert c2["previous_tree_size"]==1
    assert c2["consistency_path"]
    assert "_leaves" not in c2

def test_snapshot_roundtrip_detects_tampering_and_contains_no_secrets(tmp_path):
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    l.checkpoint([b"a",b"b"],[a,b])
    p=tmp_path/"witness-state.json"
    l.save_snapshot(p)
    raw=p.read_text()
    assert "private_key" not in raw.lower() and "secretref://" not in raw.lower()
    restored=RFC9162WitnessedCheckpointLedger.load_snapshot(p,r)
    assert restored.last["root"]==l.last["root"]
    doc=json.loads(raw); doc["payload"]["last"]["root"]="00"*32
    p.write_text(json.dumps(doc))
    with pytest.raises(WitnessError):
        RFC9162WitnessedCheckpointLedger.load_snapshot(p,r)

def test_gossip_partition_recovery_and_equivocation_detection():
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    c1=l.checkpoint([b"a"],[a,b])
    left,right=GossipReceiptStore(),GossipReceiptStore()
    left.observe(c1); right.observe(c1)
    c2=l.checkpoint([b"a",b"b"],[a,b])
    left.observe(c2)               # right is partitioned/stale
    right.merge(left.export())     # recovery by gossip
    assert right.latest("log-A")["tree_size"]==2
    fork=dict(c2); fork["root"]="11"*32
    with pytest.raises(WitnessError):
        right.observe(fork)

def test_gossip_rejects_rollback():
    s=GossipReceiptStore()
    s.observe({"log_id":"L","tree_size":2,"root":"aa"})
    with pytest.raises(WitnessError):
        s.observe({"log_id":"L","tree_size":1,"root":"bb"})


def test_checkpoint_and_persist_rolls_back_memory_on_storage_failure(tmp_path, monkeypatch):
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    c1=l.checkpoint([b"a"],[a,b])
    before=dict(l.last)
    def boom(path):
        raise OSError("disk unavailable")
    monkeypatch.setattr(l, "save_snapshot", boom)
    with pytest.raises(WitnessError):
        l.checkpoint_and_persist([b"a",b"b"],[a,b],tmp_path/"state.json")
    assert l.last==before

def test_checkpoint_and_persist_is_restartable(tmp_path):
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    p=tmp_path/"state.json"
    c=l.checkpoint_and_persist([b"a",b"b"],[a,b],p)
    restored=RFC9162WitnessedCheckpointLedger.load_snapshot(p,r)
    assert restored.last["root"]==c["root"]

def test_authenticated_gossip_rejects_forged_checkpoint():
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    c=l.checkpoint([b"a"],[a,b])
    forged=dict(c); forged["root"]="ff"*32
    s=GossipReceiptStore(registry=r)
    with pytest.raises(WitnessError):
        s.observe(forged)


def test_snapshot_rejects_rechecksummed_consistency_path_tamper(tmp_path):
    import hashlib
    a,b,r=witnesses()
    l=RFC9162WitnessedCheckpointLedger(r, log_id="log-A")
    l.checkpoint([b"a"],[a,b])
    l.checkpoint([b"a",b"b",b"c"],[a,b])
    p=tmp_path/"state.json"; l.save_snapshot(p)
    doc=json.loads(p.read_text())
    assert doc["payload"]["last"]["consistency_path"]
    doc["payload"]["last"]["consistency_path"][0]="00"*32
    canon=json.dumps(doc["payload"],sort_keys=True,separators=(",",":")).encode()
    doc["sha256"]=hashlib.sha256(canon).hexdigest()
    p.write_text(json.dumps(doc,sort_keys=True,separators=(",",":")))
    with pytest.raises(WitnessError):
        RFC9162WitnessedCheckpointLedger.load_snapshot(p,r)
